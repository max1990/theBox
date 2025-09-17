"""
Pydantic schema for environment variable validation and casting
Used by the Settings page for robust validation and type conversion
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class EnvSchema(BaseModel):
    """Schema for validating and casting environment variables"""

    # Networking
    SEACROSS_HOST: str = Field(
        default="255.255.255.255", description="SeaCross host IP or broadcast address"
    )
    SEACROSS_PORT: int = Field(
        default=2000, ge=1, le=65535, description="SeaCross port number"
    )

    # Offsets and angles (will be normalized to [0,360))
    BOW_ZERO_DEG: float = Field(
        default=0.0, description="Global bow zero offset in degrees"
    )
    DRONESHIELD_BEARING_OFFSET_DEG: float = Field(
        default=0.0, description="DroneShield bearing offset in degrees"
    )
    TRAKKA_BEARING_OFFSET_DEG: float = Field(
        default=0.0, description="Trakka bearing offset in degrees"
    )
    VISION_BEARING_OFFSET_DEG: float = Field(
        default=0.0, description="Vision bearing offset in degrees"
    )
    ACOUSTIC_BEARING_OFFSET_DEG: float = Field(
        default=0.0, description="Acoustic bearing offset in degrees"
    )

    # Vision
    VISION_BACKEND: Literal["onnxruntime", "cpu"] = Field(
        default="cpu", description="Vision backend"
    )
    VISION_MODEL_PATH: str = Field(default="", description="Path to vision model file")
    VISION_INPUT_RES: Literal[320, 416, 512, 640, 896, 960] = Field(
        default=640, description="Vision input resolution"
    )
    VISION_ROI_HALF_DEG: float = Field(
        default=15.0, ge=0, le=180, description="Vision ROI half-width in degrees"
    )
    VISION_FRAME_SKIP: int = Field(
        default=2, ge=0, description="Frames to skip between analysis"
    )
    VISION_N_CONSEC_FOR_TRUE: int = Field(
        default=3,
        ge=1,
        description="Consecutive frames required for positive detection",
    )
    VISION_LATENCY_MS: int = Field(
        default=5000, ge=50, description="Vision processing latency in milliseconds"
    )
    VISION_MAX_DWELL_MS: int = Field(
        default=7000, ge=1000, description="Maximum dwell time in milliseconds"
    )
    VISION_SWEEP_STEP_DEG: float = Field(
        default=12.0, ge=0, le=180, description="Sweep step in degrees"
    )
    VISION_PRIORITY: Literal["EOfirst", "IRfirst", "balanced"] = Field(
        default="balanced", description="Vision priority mode"
    )
    VISION_VERDICT_DEFAULT: bool = Field(
        default=True, description="Default vision verdict"
    )
    VISION_LABEL_DEFAULT: str = Field(
        default="Object", description="Default vision label"
    )

    # Confidence
    CONFIDENCE_BASE: float = Field(
        default=0.75, ge=0, le=1, description="Base confidence level"
    )
    CONFIDENCE_TRUE: float = Field(
        default=1.0, ge=0, le=1, description="True detection confidence"
    )
    CONFIDENCE_FALSE: float = Field(
        default=0.5, ge=0, le=1, description="False detection confidence"
    )
    CONF_FUSION_METHOD: Literal["bayes"] = Field(
        default="bayes", description="Confidence fusion method"
    )
    WEIGHT_RF: float = Field(default=0.6, ge=0, description="RF weight for fusion")
    WEIGHT_VISION: float = Field(
        default=0.4, ge=0, description="Vision weight for fusion"
    )
    WEIGHT_IR: float = Field(default=0.4, ge=0, description="IR weight for fusion")
    WEIGHT_ACOUSTIC: float = Field(
        default=0.25, ge=0, description="Acoustic weight for fusion"
    )
    CONF_HYSTERESIS: float = Field(
        default=0.05, gt=0, lt=1, description="Confidence hysteresis threshold"
    )

    # Range
    RANGE_MODE: Literal["RF", "EO", "IR", "ACOUSTIC", "HYBRID", "FIXED"] = Field(
        default="FIXED", description="Range estimation mode"
    )
    RANGE_FIXED_KM: float = Field(
        default=2.0, ge=0, description="Fixed range in kilometers"
    )
    RANGE_RSSI_REF_DBM: float = Field(
        default=-50.0, description="RSSI reference in dBm"
    )
    RANGE_RSSI_REF_KM: float = Field(
        default=2.0, ge=0, description="RSSI reference distance in km"
    )
    RANGE_MIN_KM: float = Field(
        default=0.1, gt=0, description="Minimum range in kilometers"
    )
    RANGE_MAX_KM: float = Field(
        default=8.0, gt=0, description="Maximum range in kilometers"
    )
    RANGE_EWMA_ALPHA: float = Field(
        default=0.4, gt=0, lt=1, description="EWMA smoothing factor"
    )

    # FOV settings
    EO_FOV_WIDE_DEG: float = Field(
        default=54.0, ge=0, le=180, description="EO wide FOV in degrees"
    )
    EO_FOV_NARROW_DEG: float = Field(
        default=2.0, ge=0, le=180, description="EO narrow FOV in degrees"
    )
    IR_FOV_WIDE_DEG: float = Field(
        default=27.0, ge=0, le=180, description="IR wide FOV in degrees"
    )
    IR_FOV_NARROW_DEG: float = Field(
        default=1.3, ge=0, le=180, description="IR narrow FOV in degrees"
    )

    # Capture/Demo
    CAPTURE_API: Literal["decklink", "opencv"] = Field(
        default="opencv", description="Capture API"
    )
    CAPTURE_RES: str = Field(default="1920x1080@30", description="Capture resolution")
    CAMERA_CONNECTED: bool = Field(
        default=False, description="Camera connection status"
    )
    DRONESHIELD_INPUT_FILE: str = Field(
        default="./data/DroneShield_Detections.txt",
        description="DroneShield input file",
    )
    LOG_PATH: str = Field(default="./mvp_demo.log", description="Log file path")

    # Trakka detection mode
    TRAKKA_DETECTION_MODE: Literal["builtin", "none", "ours"] = Field(
        default="builtin", description="Trakka detection mode"
    )

    # Optional protection settings
    SETTINGS_PROTECT: bool | None = Field(
        default=None, description="Enable settings protection"
    )
    SETTINGS_PASSWORD: str | None = Field(
        default=None, description="Settings password"
    )
    TEST_DRY_RUN: bool | None = Field(default=None, description="Test dry run mode")
    TRAKKA_BUILTIN_ENABLE: bool | None = Field(
        default=None, description="Enable Trakka built-in detector"
    )

    @field_validator("SEACROSS_HOST")
    @classmethod
    def validate_seacross_host(cls, v):
        if v == "255.255.255.255":
            return v
        try:
            import ipaddress

            ipaddress.IPv4Address(v)
            return v
        except ValueError:
            raise ValueError("Must be a valid IPv4 address or 255.255.255.255")

    @field_validator("RANGE_MAX_KM")
    @classmethod
    def validate_range_max(cls, v):
        # This will be handled in model_validator since it needs access to other fields
        return v

    @field_validator("RANGE_FIXED_KM")
    @classmethod
    def validate_range_fixed(cls, v):
        # This will be handled in model_validator since it needs access to other fields
        return v

    @model_validator(mode="after")
    def validate_confidence_hierarchy(self):
        base = self.CONFIDENCE_BASE
        true_val = self.CONFIDENCE_TRUE
        false_val = self.CONFIDENCE_FALSE

        if all(v is not None for v in [base, true_val, false_val]):
            if not (true_val >= base >= false_val):
                raise ValueError(
                    "CONFIDENCE_TRUE must be >= CONFIDENCE_BASE >= CONFIDENCE_FALSE"
                )

        return self

    @model_validator(mode="after")
    def validate_weights(self):
        weights = [
            self.WEIGHT_RF,
            self.WEIGHT_VISION,
            self.WEIGHT_IR,
            self.WEIGHT_ACOUSTIC,
        ]
        if sum(weights) == 0:
            raise ValueError("At least one weight must be positive")
        return self

    @model_validator(mode="after")
    def validate_range_constraints(self):
        if self.RANGE_MAX_KM <= self.RANGE_MIN_KM:
            raise ValueError("RANGE_MAX_KM must be greater than RANGE_MIN_KM")

        if not (self.RANGE_MIN_KM <= self.RANGE_FIXED_KM <= self.RANGE_MAX_KM):
            raise ValueError(
                f"RANGE_FIXED_KM must be between {self.RANGE_MIN_KM} and {self.RANGE_MAX_KM}"
            )

        return self

    def normalize_angles(self) -> "EnvSchema":
        """Normalize all angle fields to [0, 360) degrees"""
        angle_fields = [
            "BOW_ZERO_DEG",
            "DRONESHIELD_BEARING_OFFSET_DEG",
            "TRAKKA_BEARING_OFFSET_DEG",
            "VISION_BEARING_OFFSET_DEG",
            "ACOUSTIC_BEARING_OFFSET_DEG",
            "VISION_SWEEP_STEP_DEG",
        ]

        data = self.model_dump()
        for field in angle_fields:
            if field in data:
                angle = data[field]
                while angle < 0:
                    angle += 360
                while angle >= 360:
                    angle -= 360
                data[field] = angle

        return EnvSchema(**data)

    def to_env_dict(self) -> dict:
        """Convert to environment variable dictionary"""
        result = {}
        for field, value in self.model_dump().items():
            if value is None:
                continue
            if isinstance(value, bool):
                result[field] = "true" if value else "false"
            else:
                result[field] = str(value)
        return result

    @classmethod
    def from_env_dict(cls, env_dict: dict) -> "EnvSchema":
        """Create schema from environment dictionary"""
        data = {}
        for field in cls.model_fields:
            if field in env_dict:
                value = env_dict[field]
                # Handle boolean conversion
                if field in [
                    "CAMERA_CONNECTED",
                    "VISION_VERDICT_DEFAULT",
                    "SETTINGS_PROTECT",
                    "TEST_DRY_RUN",
                    "TRAKKA_BUILTIN_ENABLE",
                ]:
                    if isinstance(value, str):
                        data[field] = value.lower() in ["true", "1", "yes", "on"]
                    else:
                        data[field] = bool(value)
                else:
                    data[field] = value
        return cls(**data)
