import logging
import math
import os
from typing import Optional, Dict, Tuple
from mvp.env_loader import get_float, get_str
from mvp.schemas import RangeEstimate


log = logging.getLogger("plugins.range")


def _clamp(x: float, lo: float, hi: float) -> float:
    """Clamp value between lo and hi"""
    return max(lo, min(hi, x))


def _rssi_to_bars(rssi_dbm: float) -> int:
    """Convert RSSI dBm to signal bars (0-10)"""
    # RSSI mapping: [-100, -88, -80, -72, -64, -56] -> [0, 2, 4, 6, 8, 10]
    if rssi_dbm >= -56:
        return 10
    elif rssi_dbm >= -64:
        return 8
    elif rssi_dbm >= -72:
        return 6
    elif rssi_dbm >= -80:
        return 4
    elif rssi_dbm >= -88:
        return 2
    else:
        return 0


class RangePlugin:
    def __init__(self):
        # Environment knobs
        self.mode = get_str("RANGE_MODE", "fixed").strip().lower()
        self.fixed_km = get_float("RANGE_FIXED_KM", 2.0)
        self.rssi_ref_dbm = get_float("RANGE_RSSI_REF_DBM", -50.0)
        self.rssi_ref_km = get_float("RANGE_RSSI_REF_KM", 2.0)
        self.min_km = get_float("RANGE_MIN_KM", 0.1)
        self.max_km = get_float("RANGE_MAX_KM", 8.0)
        self.ewma_alpha = get_float("RANGE_EWMA_ALPHA", 0.4)
        
        # FOV settings
        self.eo_fov_wide = get_float("EO_FOV_WIDE_DEG", 54.0)
        self.eo_fov_narrow = get_float("EO_FOV_NARROW_DEG", 2.0)
        self.ir_fov_wide = get_float("IR_FOV_WIDE_DEG", 27.0)
        self.ir_fov_narrow = get_float("IR_FOV_NARROW_DEG", 1.3)
        
        # State for EWMA
        self.ewma_state: Dict[str, float] = {}
        self.estimates = 0

    def estimate_km(self, signal: Optional[Dict] = None, eo: Optional[Dict] = None, 
                   ir: Optional[Dict] = None, ac: Optional[Dict] = None) -> RangeEstimate:
        """
        Estimate range using available sensor cues
        
        Args:
            signal: RF signal data (RSSI, SignalBars, etc.)
            eo: EO camera data (pixel height, frame size, etc.)
            ir: IR camera data (pixel height, frame size, etc.)
            ac: Acoustic data (SPL, etc.)
            
        Returns:
            RangeEstimate with range, uncertainty, mode, and details
        """
        self.estimates += 1
        
        if self.mode == "fixed":
            return self._fixed_mode()
        
        # Collect available cues
        cues = {}
        
        # RF cue
        if signal:
            rf_range, rf_sigma = self._rf_range(signal)
            if rf_range is not None:
                cues['rf'] = (rf_range, rf_sigma)
        
        # EO cue
        if eo:
            eo_range, eo_sigma = self._eo_range(eo)
            if eo_range is not None:
                cues['eo'] = (eo_range, eo_sigma)
        
        # IR cue
        if ir:
            ir_range, ir_sigma = self._ir_range(ir)
            if ir_range is not None:
                cues['ir'] = (ir_range, ir_sigma)
        
        # Acoustic cue
        if ac:
            ac_range, ac_sigma = self._acoustic_range(ac)
            if ac_range is not None:
                cues['acoustic'] = (ac_range, ac_sigma)
        
        if not cues:
            # No cues available, return fixed
            return self._fixed_mode()
        
        if len(cues) == 1:
            # Single cue
            cue_name, (range_km, sigma_km) = next(iter(cues.items()))
            return RangeEstimate(
                range_km=range_km,
                sigma_km=sigma_km,
                mode=cue_name,
                details={cue_name: {"range_km": range_km, "sigma_km": sigma_km}}
            )
        else:
            # Multiple cues - use inverse-variance fusion
            return self._fuse_cues(cues)

    def _fixed_mode(self) -> RangeEstimate:
        """Fixed range mode"""
        sigma_km = 0.1 * self.fixed_km
        return RangeEstimate(
            range_km=self.fixed_km,
            sigma_km=sigma_km,
            mode="FIXED",
            details={"fixed_km": self.fixed_km, "sigma_km": sigma_km}
        )

    def _rf_range(self, signal: Dict) -> Tuple[Optional[float], Optional[float]]:
        """RF-only range estimation using log-distance model"""
        rssi = signal.get("RSSI")
        if rssi is None:
            return None, None
        
        try:
            rssi = float(rssi)
        except (ValueError, TypeError):
            return None, None
        
        # Log-distance model: d = d0 * 10^((P0 - P) / (10*n))
        # n = 2.2 for typical environments
        n = 2.2
        delta_db = self.rssi_ref_dbm - rssi
        range_km = self.rssi_ref_km * (10 ** (delta_db / (10 * n)))
        
        # Clamp to bounds
        range_km = _clamp(range_km, self.min_km, self.max_km)
        
        # Apply EWMA smoothing
        track_key = "rf_default"  # Could be more specific per track
        if track_key in self.ewma_state:
            range_km = self.ewma_alpha * range_km + (1 - self.ewma_alpha) * self.ewma_state[track_key]
        self.ewma_state[track_key] = range_km
        
        # Uncertainty: clamp(0.4 * range, [0.05*range, 1.0*range])
        sigma_km = _clamp(0.4 * range_km, 0.05 * range_km, 1.0 * range_km)
        
        return range_km, sigma_km

    def _eo_range(self, eo: Dict) -> Tuple[Optional[float], Optional[float]]:
        """EO camera range estimation using pixel/FOV geometry"""
        pixel_height = eo.get("pixel_height")
        frame_height = eo.get("frame_height")
        fov_deg = eo.get("fov_deg")
        
        if pixel_height is None or frame_height is None:
            return None, None
        
        try:
            pixel_height = float(pixel_height)
            frame_height = float(frame_height)
        except (ValueError, TypeError):
            return None, None
        
        # Use provided FOV or default
        if fov_deg is None:
            fov_deg = self.eo_fov_wide
        else:
            fov_deg = float(fov_deg)
        
        # Convert to radians
        fov_rad = math.radians(fov_deg)
        
        # Small angle approximation: theta = (h_px / H_px) * FOV
        theta_rad = (pixel_height / frame_height) * fov_rad
        
        if theta_rad <= 0:
            return None, None
        
        # Range: d = L_typ / theta (in meters), then convert to km
        L_typ = 0.5  # Typical object size in meters
        range_m = L_typ / theta_rad
        range_km = range_m / 1000.0
        
        # Clamp to bounds
        range_km = _clamp(range_km, self.min_km, self.max_km)
        
        # Uncertainty: sqrt((1/h_px)^2 + (0.15)^2) * range
        # Double if backlit/poor contrast
        sigma_rel = math.sqrt((1.0 / pixel_height) ** 2 + 0.15 ** 2)
        if eo.get("backlit", False) or eo.get("poor_contrast", False):
            sigma_rel *= 2.0
        
        sigma_km = _clamp(sigma_rel * range_km, 0.05 * range_km, 1.0 * range_km)
        
        return range_km, sigma_km

    def _ir_range(self, ir: Dict) -> Tuple[Optional[float], Optional[float]]:
        """IR camera range estimation using pixel/FOV geometry"""
        pixel_height = ir.get("pixel_height")
        frame_height = ir.get("frame_height")
        fov_deg = ir.get("fov_deg")
        
        if pixel_height is None or frame_height is None:
            return None, None
        
        try:
            pixel_height = float(pixel_height)
            frame_height = float(frame_height)
        except (ValueError, TypeError):
            return None, None
        
        # Use provided FOV or default
        if fov_deg is None:
            fov_deg = self.ir_fov_wide
        else:
            fov_deg = float(fov_deg)
        
        # Convert to radians
        fov_rad = math.radians(fov_deg)
        
        # Small angle approximation: theta = (h_px / H_px) * FOV
        theta_rad = (pixel_height / frame_height) * fov_rad
        
        if theta_rad <= 0:
            return None, None
        
        # Range: d = L_typ / theta (in meters), then convert to km
        L_typ = 0.5  # Typical object size in meters
        range_m = L_typ / theta_rad
        range_km = range_m / 1000.0
        
        # Clamp to bounds
        range_km = _clamp(range_km, self.min_km, self.max_km)
        
        # Uncertainty: sqrt((1/h_px)^2 + (0.15)^2) * range
        # Double if backlit/poor contrast
        sigma_rel = math.sqrt((1.0 / pixel_height) ** 2 + 0.15 ** 2)
        if ir.get("backlit", False) or ir.get("poor_contrast", False):
            sigma_rel *= 2.0
        
        sigma_km = _clamp(sigma_rel * range_km, 0.05 * range_km, 1.0 * range_km)
        
        return range_km, sigma_km

    def _acoustic_range(self, ac: Dict) -> Tuple[Optional[float], Optional[float]]:
        """Acoustic range estimation using spherical spreading model"""
        spl = ac.get("spl_dba")
        if spl is None:
            return None, None
        
        try:
            spl = float(spl)
        except (ValueError, TypeError):
            return None, None
        
        # Spherical spreading: L = L0 - 20*log10(d/d0)
        # L0 = 80 dBA @ d0 = 1 m
        L0 = 80.0  # dBA
        d0 = 1.0   # meters
        
        # Solve for distance: d = d0 * 10^((L0 - L) / 20)
        range_m = d0 * (10 ** ((L0 - spl) / 20.0))
        range_km = range_m / 1000.0
        
        # Clamp to bounds
        range_km = _clamp(range_km, self.min_km, self.max_km)
        
        # Base uncertainty 0.4*range, inflate by SNR/sea-state
        sigma_km = 0.4 * range_km
        
        # Inflate by SNR if available
        snr = ac.get("snr_db")
        if snr is not None:
            try:
                snr = float(snr)
                if snr < 10:  # Poor SNR
                    sigma_km *= 1.5
            except (ValueError, TypeError):
                pass
        
        # Inflate by sea state if available
        sea_state = ac.get("sea_state")
        if sea_state is not None:
            try:
                sea_state = float(sea_state)
                if sea_state > 3:  # Rough seas
                    sigma_km *= 1.2
            except (ValueError, TypeError):
                pass
        
        sigma_km = _clamp(sigma_km, 0.05 * range_km, 1.0 * range_km)
        
        return range_km, sigma_km

    def _fuse_cues(self, cues: Dict[str, Tuple[float, float]]) -> RangeEstimate:
        """Inverse-variance fusion of multiple range cues"""
        if not cues:
            return self._fixed_mode()
        
        # Pre-scale sigmas as specified
        scaled_cues = {}
        for cue_name, (range_km, sigma_km) in cues.items():
            if cue_name == "rf":
                # RF scaling based on SNR/jitter
                scale_factor = 1.0  # Could be enhanced with actual SNR data
            elif cue_name in ["eo", "ir"]:
                # Vision scaling based on visibility/backlit
                scale_factor = 1.0  # Could be enhanced with actual visibility data
            else:
                scale_factor = 1.0
            
            scaled_sigma = sigma_km * scale_factor
            scaled_cues[cue_name] = (range_km, scaled_sigma)
        
        # Inverse-variance weights: w_i = 1/sigma_i^2
        weights = []
        ranges = []
        sigmas = []
        
        for cue_name, (range_km, sigma_km) in scaled_cues.items():
            weight = 1.0 / (sigma_km ** 2)
            weights.append(weight)
            ranges.append(range_km)
            sigmas.append(sigma_km)
        
        # Fused range: d_fused = sum(w_i * d_i) / sum(w_i)
        total_weight = sum(weights)
        if total_weight <= 0:
            return self._fixed_mode()
        
        fused_range = sum(w * r for w, r in zip(weights, ranges)) / total_weight
        
        # Fused uncertainty: sigma_fused = sqrt(1 / sum(w_i))
        fused_sigma = math.sqrt(1.0 / total_weight)
        
        # Clamp to bounds
        fused_range = _clamp(fused_range, self.min_km, self.max_km)
        fused_sigma = _clamp(fused_sigma, 0.05 * fused_range, 1.0 * fused_range)
        
        # Build details dict
        details = {}
        for cue_name, (range_km, sigma_km) in scaled_cues.items():
            details[cue_name] = {"range_km": range_km, "sigma_km": sigma_km}
        details["fused"] = {"range_km": fused_range, "sigma_km": fused_sigma}
        
        return RangeEstimate(
            range_km=fused_range,
            sigma_km=fused_sigma,
            mode="HYBRID",
            details=details
        )


