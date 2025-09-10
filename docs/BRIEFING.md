# TheBox → SeaCross Integration — Comprehensive Briefing (handoff for new chat)

**Purpose:** This single doc summarizes everything discussed so a brand‑new chat (or teammate) can get fully up to speed without re‑hashing prior context. It captures constraints, design decisions, plugin architecture, event contracts, UI notes, env knobs, and a lightweight test plan. The code itself will live in the repo and does not need to be pasted here.

---

## 0) Personal context & operating constraints

* Author/operator is under heavy load this week (finals, capstone reports/presentations) and flagged ADHD/exhaustion. Time to first working demo is **< 4 days**.
* Preference: **bulletproof, robust, and simple now**; we can optimize or add AI later.
* There is an **offline, high‑end workstation** available but not required for the MVP.
* Goal for the display: SeaCross must show detections and updates **ASAP**; operator can filter by **confidence** (0–100 integer). Default confidence **75**.

---

## 1) Ground truth about SeaCross I/O

* SeaCross ingests only two message types over UDP:

  * **CLS** (classification): `$XACLS,...`
  * **SGT** (position update by **bearing + distance**): `$XASGT,...`
* **SGC (lat/lon)** is **not** consumed by SeaCross in this integration. **Do not send SGC.**
* Typical broadcast target (from field capture): **`192.168.0.255:62000`** (configurable).
* “Talker ID” (the `$XA` prefix) is **per‑computer**; we generate it dynamically (see env knobs below).

### Example NMEA lines from SeaCross capture (for reference)

```
$XACLS,8710a64b84f346e1a36c9b24e2a6cd55,UNKNOWN,,DJI Mavic,UNKNOWN,details_url=http://<BOX_IP>/drone/<id>*CS
$XASGT,8710a64b84f346e1a36c9b24e2a6cd55,20250828,233824.64,217.9,5.0,358.4,2.0,1.8,5.0*CS
```

---

## 2) Inputs we have (examples)

### DroneShield (two distinct JSON v2 message types)

* **Detection** (RF only): includes angle/angle‑error, RSSI, SignalBars, etc.; **no lat/lon**.
* **DetectionRemoteDroneID**: can include **bearing**, **lat/lon**, alt, IDs, etc. (wartime may not be available).

### Sample RF‑only directional fields (from the vendor spec)

* `AbsoluteAngleOfArrivalRadians`, `AngleOfArrivalRadians`, `AngleOfArrivalErrorRadians`, `RSSI`, `SignalBars`, `Vendor`, `Name`, `CorrelationKey`, `TimeUTC`, etc.

### Other sources mentioned

* **Mara**: sends pose (x,y,z), velocity, per‑object `score`, `sensor_id`, etc. (bearing/range may be derivable depending on ownship frame).
* **Silvus**: per‑cluster logs with summed power, center frequency, bandwidth, **two AoAs** (ambiguity), sensor heading/position lines.

---

## 3) Architecture (clean separation of concerns)

```
[input plugins]  →  [normalizers]  →  [core pipeline]  →  [outputs]
(DroneShield,        (vendor→          (range_estimator_simple,   (SeaCross NMEA,
 Mara, Silvus, …)     object.* events)  tracker/fuser later)        future outputs)
```

* **Inputs (vendor plugins)**: connect to each company and publish raw events (e.g., `droneshield_detection`).
* **Normalizers**: convert each vendor’s raw payload into **generic** events:

  * `object.classification`
  * `object.sighting.directional` (bearing‑only)
  * *Optional if you truly have range*: `object.sighting.relative`
* **Core pipeline**:

  * **Range Estimator (simple)**: converts bearing‑only → bearing+synthetic‑range (`object.sighting.relative`). Replaceable later with AI/triangulation or a better estimator.
  * **Tracker/Fuser (future)**: multi‑sensor correlation, smoothing, deleting stale tracks, etc.
* **Outputs**:

  * **SeaCross Sender (vendor‑agnostic)**: subscribes to `object.classification` + `object.sighting.relative`, emits **CLS + SGT** only.

**Why:** We can add/replace vendors or estimators without touching SeaCross. SeaCross stays minimal and reliable.

---

## 4) Normalized event contracts (authoritative schema)

### 4.1 `object.classification`

```json
{
  "object_id": "string",          
  "domain": "AIR|SURFACE|UNDERWATER|UNKNOWN",
  "type": "string",               
  "brand": "string",
  "model": "string",
  "affiliation": "UNKNOWN|FRIENDLY|ENEMY|NOT_DRONE",
  "details_url": "http://<host>:<port>/drone/<object_id>",
  "confidence": 75                  
}
```

**Notes**

* `object_id` must be **stable** for the same track; we commonly compute a UUIDv5 from vendor fields (e.g., DroneSerialNumber/UUID/CorrelationKey/Vendor/Name).
* `confidence` is **0–100 integer** (no decimals). Default **75**. RemoteID with IDs/serials ⇒ **99**.

### 4.2 `object.sighting.directional` (bearing only)

```json
{
  "object_id": "string",
  "time_utc": "2025-08-28T23:38:24.640Z",
  "bearing_deg_true": 358.7,
  "bearing_error_deg": 2.0,
  "signal_bars": 8,
  "rssi": -55,
  "altitude_m": 0.0,
  "altitude_error_m": 20.0,
  "confidence": 80
}
```

**Published by:** normalizers (e.g., DroneShield) when only direction is known.

### 4.3 `object.sighting.relative` (bearing + distance ⇒ ready for SGT)

```json
{
  "object_id": "string",
  "time_utc": "2025-08-28T23:38:24.640Z",
  "distance_m": 650.0,
  "distance_error_m": 200.0,
  "bearing_deg_true": 358.7,
  "bearing_error_deg": 5.0,
  "altitude_m": 0.0,
  "altitude_error_m": 20.0,
  "confidence": 80,
  "range_is_synthetic": true,
  "range_method": "rf_strength_v1"
}
```

**Published by:** the **range estimator** (or a real ranging sensor/fuser) — never by SeaCross.

---

## 5) SeaCross Sender (final behavior)

* Subscribes to **`object.classification`** and **`object.sighting.relative`** only.
* Emits:

  * `$XACLS,<ID>,<TYPE>,,<BRAND MODEL>,<AFFILIATION>,details_url=<URL>*CS`
  * `$XASGT,<ID>,<YYYYMMDD>,<HHMMSS.hh>,<DIST>,<DIST_ERR>,<BRG>,<BRG_ERR>,<ALT>,<ALT_ERR>*CS`
* Writes to in‑memory DB for UI/persistence:

  * `tracks.<id>.{affiliation,details_url,domain,brand,model,fused_confidence,fused_bearing_deg,fused_distance_m,fused_altitude_m,last_update,range_is_synthetic,range_method}`
  * `detections.<id>.<epoch_ms>.{time_utc,bearing_deg,distance_m,altitude_m,confidence}`
* **Dynamic Talker ID**: `THEBOX_TALKER_ID` (two letters) or derive from hostname (first two letters); fallback `XA`.
* **UDP target**: default `192.168.0.255:62000` (override via env).
* **details\_url**: `http://<host>:<port>/drone/<object_id>` (built from config/env if not provided).

---

## 6) Range Estimation (current simple policy) — central plugin

* We **must** emit SGT even for RF‑only sightings → we generate a **synthetic range** that is plausible and conservative.
* Current policy (v1):

  * Map **SignalBars (0..10)** or **RSSI (-90..-25 dBm)** to a range within `[MIN, MAX]` meters.
  * Smooth with previous fused range (`EMA` with `alpha`).
  * Report a conservative `distance_error_m = max(MIN_ERR, ERR_FRAC * range)`.
  * Mark `range_is_synthetic=true`, `range_method="rf_strength_v1"`.
* Tunable env vars (defaults in parentheses):

  * `THEBOX_MIN_SYNTH_RANGE_M (150)`
  * `THEBOX_MAX_SYNTH_RANGE_M (1500)`
  * `THEBOX_DEFAULT_SYNTH_RANGE_M (600)`
  * `THEBOX_SYNTH_SMOOTHING_ALPHA (0.30)`
  * `THEBOX_SYNTH_MIN_DIST_ERR_M (150)`
  * `THEBOX_SYNTH_DIST_ERR_FRAC (0.30)`
  * `THEBOX_SYNTH_DEFAULT_BRG_ERR (5.0)`
  * `THEBOX_SYNTH_DEFAULT_ALT_M (0.0)`
  * `THEBOX_SYNTH_DEFAULT_ALT_ERR (20.0)`

> Later we can replace this estimator with TDOA, multi‑sensor triangulation, or an AI model that outputs the same `object.sighting.relative` schema.

---

## 7) UI / Templates / Styling notes

* **Labels UI**: shows tracks & per‑detection info; clicking a drone in SeaCross opens our details URL (web‑view back to the box). Initial user actions supported: set **Affiliation** to Friendly/Enemy/Not Drone.
* **SeaCross Sender plugin page**:

  * Shows target IP/port and **Talker ID**; status table lists recent `$XACLS`/`$XASGT`.
  * Ensure the `/status` route returns `target_ip`, `target_port`, `talker_id`, `sent_nmea[]`, `errors[]` as used in the template.
  * Template JS should fetch `./status` (relative), not an absolute path.
* **Persistence Disk plugin**:

  * Persisted namespaces: `tracks`, `detections`, `sensor_id_map`, `droneshield_messages`.
  * Routes live at the **plugin root** (`/plugins/DiskPersistencePlugin/`): `GET /` (page), `GET /status`, `POST /save`, `POST /load`.
  * Template forms should post to `./save` and `./load` (relative), not absolute `/persistence/...`.
  * If text color is unreadable, scope a page class (e.g., `.persistence-page`) and set `color: var(--primary, #0d6efd);` either inline or in `static/css/main.css`.

---

## 8) DB snapshots & file persistence

* File path: `data/state.json` (override with `THEBOX_STATE_PATH`).
* Auto‑save interval: `3s` (override with `THEBOX_STATE_SAVE_EVERY_SEC`).
* On restore, we touch `tracks.*.last_update` so pages sort sensibly.

---

## 9) Config / Env quick reference

* **Plugin order** (example):

  1. `droneshield_listener` (or other vendor listeners)
  2. `droneshield_normalizer` (maps raw → object.\*)
  3. `range_estimator_simple` (bearing→relative)
  4. `seacross_sender` (CLS + SGT)
  5. `labels_ui`
  6. `persistence_disk`
* **Env knobs:**

  * `THEBOX_TALKER_ID` → two letters (overrides talker)
  * `THEBOX_BROADCAST_IP` (default `192.168.0.255`)
  * `THEBOX_BROADCAST_PORT` (default `62000`)
  * `THEBOX_WEB_HOST` / `THEBOX_WEB_PORT` for building `details_url`
  * All the synthetic range vars (see §6)
  * `THEBOX_STATE_PATH`, `THEBOX_STATE_SAVE_EVERY_SEC`

---

## 10) Confidence policy (current)

* `confidence` is **integer 0..100**.
* Defaults to **75** if unknown.
* Boost to **99** when strong identifiers exist (e.g., Remote ID serials/RegistrationID/UUID).
* Operators can filter displayed objects by confidence threshold.

---

## 11) Security/ops considerations

* Ownship GPS may be **spoofed** or withheld; hence we base updates on **relative SGT** (bearing/distance) which does **not** require ownship lat/lon.
* `range_is_synthetic` flag makes it clear to operators when range is provisional.
* Affiliation is set/changed via the web UI; SeaCross CLS will re‑emit if affiliation changes.

---

## 12) Minimal test plan (no vendor hardware needed)

1. **Publish a classification** (via a test/injector or Python shell):

   ```json
   {
     "object_id": "abc123...", "domain": "AIR", "type": "RF",
     "brand": "UNKNOWN", "model": "UNKNOWN", "affiliation": "UNKNOWN",
     "details_url": "http://<host>:<port>/drone/abc123", "confidence": 75
   }
   ```

   Expect: `$XACLS` over UDP; track appears in Labels UI; `/seacross_sender/status` shows CLS.

2. **Publish a relative sighting** (synthetic or real):

   ```json
   {
     "object_id": "abc123...", "time_utc": "2025-08-28T23:38:24.640Z",
     "distance_m": 600, "distance_error_m": 200,
     "bearing_deg_true": 358.4, "bearing_error_deg": 5.0,
     "altitude_m": 0.0, "altitude_error_m": 20.0,
     "confidence": 80, "range_is_synthetic": true, "range_method": "rf_strength_v1"
   }
   ```

   Expect: `$XASGT` over UDP; SeaCross plot updates.

3. **Directional only → estimator**: publish `object.sighting.directional` with `bearing_deg_true` (+ `signal_bars`/`rssi`). Estimator should emit `object.sighting.relative`; SeaCross sender should emit `$XASGT` with **synthetic** range.

4. **Wire sniff**: `tcpdump -n -A udp port 62000` (or Wireshark) to confirm NMEA lines.

5. **Affiliation change**: publish `object.classification` with a new `affiliation`; SeaCross sender re‑emits `$XACLS`.

---

## 13) Git repo notes (GitLab vs GitHub)

* Either is fine; Univ prefers **GitLab**. Typical steps:

  1. `git init` in project root; add remote to GitLab; `git add .` / `git commit -m "init"` / `git push -u origin main`.
  2. Add `.gitignore` to exclude: `data/`, `*.log`, `__pycache__/`, `.env`, and other local artifacts.
  3. CI/CD (optional later). For now keep it simple.

---

## 14) Open questions / future items

* Precise mapping of **AngleOfArrivalRadians (sensor‑relative)** to degrees **true** when sensors are not compass‑aligned — likely belongs in the vendor input plugin (apply heading offset) before publishing `object.sighting.directional`.
* **Silvus/Mara** normalizers: define how to compute/derive bearing (and possibly range) from their outputs.
* **Better range estimation**: triangulation, TDOA, kinematics, or learned models.
* **Object lifecycle**: when/how to retire stale tracks, merge/split logic, etc.
* **Operator UX**: expose `range_is_synthetic` as a badge in Labels UI; quick affiliation controls.

---

## 15) TL;DR for a brand‑new assistant/new chat

1. The Box uses a plugin pipeline. Vendors → **normalize to `object.*`** → core (range estimator) → **SeaCross sender**.
2. **SeaCross consumes only CLS + SGT.** Never send SGC.
3. If only bearing is known, **central estimator** generates a **synthetic range** and sets `range_is_synthetic=true`.
4. Confidence is **int 0..100**, default 75; RemoteID with serials ⇒ 99.
5. UDP target usually **192.168.0.255:62000**; **talker ID** dynamic from env/hostname.
6. **details\_url** is `http://<host>:<port>/drone/<object_id>`; SeaCross click opens our web‑view back to the Box.
7. Persisted namespaces: `tracks`, `detections`, `sensor_id_map`, `droneshield_messages` to `data/state.json`.
8. The repo contains final SeaCross sender (vendor‑agnostic) and templates; do not re‑introduce vendor logic there.

---

*End of briefing.*
