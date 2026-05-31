# MW PRE-PLANNING LITE SYSTEM
## PLANNER RULEBOOK
Version: 1.0

---

# 1. PURPOSE

This document defines:
- RF engineering rules
- terrain evaluation logic
- candidate filtering logic
- scoring logic
- engineering thresholds

This file is the engineering source-of-truth for the MW Pre-planning Lite System.

The application must load these rules dynamically through:
```text
planner_config.yaml
```

---

# 2. SYSTEM PHILOSOPHY

The system is:
- a pre-planning assistant
- a candidate screening engine
- a route ranking system

The system is NOT:
- a detailed RF propagation simulator
- a replacement for Pathloss
- a final acceptance engineering tool

---

# 3. PLANNING OBJECTIVES

The engine shall prioritize:
1. LOS availability
2. Fresnel clearance
3. operational feasibility
4. deployment simplicity
5. future maintainability

The engine shall avoid:
- marginal links
- excessive tower requirements
- overextended distance
- high-risk obstruction paths

---

# 4. CANDIDATE SEARCH RULES

## 4.1 Candidate Radius

Default:
```yaml
candidate_radius_km: 30
```

Meaning:
- maximum search radius around new site

Impact:
- larger radius:
  - more candidate links
  - higher CPU usage
  - slower planning
- smaller radius:
  - faster planning
  - may miss optimal candidates

Recommended:
- urban: 0-2 km
- suburban: 2-10 km
- rural: 11-30 km

---

# 5. TERRAIN SAMPLING RULES

## 5.1 Terrain Sampling Interval

Default:
```yaml
terrain_step_m: 30
```

Meaning:
- distance between DEM sample points

Impact:
- smaller interval:
  - higher precision
  - slower computation
- larger interval:
  - faster
  - may miss obstacles

Recommended:
- SRTM30:
  - 30 m

---

# 6. LOS RULES

## 6.1 LOS Pass Condition

Condition:
```text
No terrain point crosses LOS line
```

Output:
```text
PASS / FAIL
```

---

## 6.2 LOS Margin

Recommended:
```yaml
minimum_los_margin_m: 1
```

Meaning:
- minimum terrain clearance above obstruction

Impact:
- low margin:
  - risky path
- high margin:
  - safer path
  - may require taller towers

---

# 7. FRESNEL RULES

# 7.1 Fresnel Requirement

Default:
```yaml
minimum_fresnel_clearance_percent: 60
```

Meaning:
- minimum Fresnel zone clearance

Engineering convention:
- 60% is acceptable minimum
- 80% preferred
- below 60% considered risky

---

# 7.2 Fresnel Risk Classification

| Clearance | Risk |
|---|---|
| >= 80% | Excellent |
| 60-79% | Acceptable |
| 40-59% | Risky |
| < 40% | Reject |

---

# 8. BAND RULES

# 8.0 Automatic Band Selection

The system shall automatically select the working band for a new candidate link.

The planner UI shall not require the user to manually choose the band for the new link.

Band selection is distance-based and calibrated from `MW_data_2026.csv`.

Historical data summary:
- `18GHz`: p95 ~= 4.8 km, max observed 8.9 km
- `15GHz`: p95 ~= 8.4 km, max observed 12.7 km
- `11GHz`: p95 ~= 10.7 km, max observed 10.7 km
- `7/8GHz`: used as the historical low-band reference for planner `6GHz`
- `23GHz`: not present in current MW history, so it is not selected automatically

| Distance | Selected Band |
|---|---|
| <= 5 km | 18 GHz |
| > 5 km and <= 8 km | 15 GHz |
| > 8 km and <= 11 km | 11 GHz |
| > 11 km and <= 45 km | 6 GHz |
| > 45 km | 6 GHz with excessive-distance risk/rejection |

Selection order:
```text
18 GHz -> 15 GHz -> 11 GHz -> 6 GHz
```

The backend implementation shall load the actual distance limits from:

```text
planner_config.yaml
```

The rulebook is the engineering source of truth. The YAML config is the executable representation.

# 8.1 6 GHz

```yaml
max_distance_km: 45
```

Characteristics:
- long distance
- better diffraction
- larger antenna

Use case:
- rural
- backbone

---

# 8.2 11 GHz

```yaml
max_distance_km: 11
```

Characteristics:
- balanced
- medium distance

Use case:
- aggregation
- suburban

---

# 8.3 18 GHz

```yaml
max_distance_km: 5
```

Characteristics:
- common urban band
- moderate rain sensitivity

Use case:
- metro transmission

---

# 8.4 15 GHz

```yaml
max_distance_km: 8
```

Characteristics:
- mid-distance urban/suburban band
- useful where 18 GHz is near distance limit
- smaller antennas than low bands

Use case:
- suburban aggregation
- medium-distance access hops

---

# 9. DISTANCE RULES

## 9.1 Distance Evaluation

The engine shall:
- penalize links near maximum distance
- reward balanced distance

Reason:
- near-limit links:
  - less stable
  - more weather-sensitive
  - harder future expansion

---

# 10. TOWER HEIGHT RULES

## 10.1 Tower Margin

Definition:
```text
available_height - required_height
```

Classification:

| Margin | Status |
|---|---|
| > 10m | Excellent |
| 5-10m | Good |
| 0-5m | Risky |
| < 0m | Reject |

---

# 11. RISK FLAGS

The engine shall generate flags.

Examples:
- LOW_FRESNEL_MARGIN
- EXCESSIVE_DISTANCE
- HIGH_TOWER_REQUIREMENT
- NEAR_OBSTRUCTION
- TERRAIN_BLOCKED

These flags must appear:
- API output
- frontend
- export reports

---

# 12. SCORING SYSTEM

# 12.1 Scoring Weights

Default:
```yaml
scoring:
  los_weight: 40
  fresnel_weight: 30
  distance_weight: 15
  tower_margin_weight: 15
  diverse_routing_bonus: 8
  overload_penalty: 30
  overlink_penalty: 25
  extended_rru_penalty: 10
```

---

# 12.2 LOS Scoring

| Condition | Score |
|---|---|
| Clear LOS | Full |
| Marginal LOS | Partial |
| Blocked | Zero |

LOS is the highest priority.

---

# 12.3 Fresnel Scoring

| Clearance | Score |
|---|---|
| >= 80% | Full |
| 60-79% | Medium |
| < 60% | Low |

---

# 12.4 Distance Scoring

The engine shall:
- prefer mid-range links
- penalize near-limit links

---

# 12.5 Tower Margin Scoring

The engine shall:
- reward low required tower height
- penalize excessive height

---

# 13. REJECTION RULES

The engine shall reject:
- blocked LOS
- Fresnel < 40%
- distance > max_distance
- impossible tower height

Rejected links shall still appear in:
```text
rejected_links
```

for engineering visibility.

---

# 14. SITE PRIORITIZATION RULES

Operational rules:
- Sites with `overload >= 1` are still scanned, but are marked `DANGER`, receive an overload penalty, and show `Overload` in notes.
- Sites with two or more existing MW links are still scanned, but are marked `OVERLINK`, receive an overlink penalty, and show `Overlink` in notes.
- Sites whose `site_code` contains `-` are still scanned, but receive an extended RRU penalty and show `RRU kéo dài` in notes.
- Sites marked `VH` / diverse routing receive the configured diverse routing bonus when the link is not technically rejected.

---

# 14.1 CALLOFF DESIGN RULES

Default:
```yaml
calloff:
  azimuth_overlap_threshold_deg: 15
  overlap_height_step_down_m: 3
```

Rules:
- `Device` is intentionally left blank for detailed design.
- Antenna diameter is selected from imported MW link history by matching band and distance bucket.
- If the planner band is `6GHz`, imported `7GHz/8GHz` history is used as the low-band reference.
- `High` and `Low` are per-link endpoint roles: each MW route has one High end and one Low end.
- For a new route using the same band group as an existing route on the root site, the root-site end must use a High/Low side that is not already used by that root site in that band group.
- If both High and Low are already used by existing same-band routes at the root site, the planner must not assign a duplicate side; it marks `Band side conflict` and leaves the calloff side blank for detailed review.
- If the root site has existing MW routes, new root antenna height must be equal to or lower than the lowest existing MW antenna height on that tower.
- If a same-band existing route at the root site has an azimuth within `azimuth_overlap_threshold_deg`, the new root antenna height is reduced below the overlapping existing antenna by `overlap_height_step_down_m`.
- The UI must display the executable distance-to-band and distance-to-antenna rule table returned by the backend.
- Calloff output includes azimuth and tilt for both A and B ends.

Future optional rules:
- prioritize backbone sites
- prioritize ring topology
- prioritize sites with spare ports

These are not mandatory in MVP.

---

# 15. ENGINEERING ASSUMPTIONS

Assumptions:
- Earth curvature included
- Standard atmosphere approximation
- DEM accuracy acceptable for pre-planning
- Clutter/building data unavailable

---

# 16. LIMITATIONS

The engine does NOT model:
- detailed clutter
- rain attenuation
- multipath fading
- interference
- frequency coordination
- detailed availability calculations

---

# 17. OUTPUT OBJECTIVE

The engine must answer:

```text
Which existing site is the best candidate
for connecting a new microwave site?
```

NOT:
```text
Can this link pass final carrier-grade acceptance?
```

---

# 18. FUTURE AI INTEGRATION

Future AI may:
- explain engineering results
- summarize risks
- suggest alternatives
- assist planners

AI must NEVER replace:
- LOS calculation
- Fresnel calculation
- terrain evaluation
