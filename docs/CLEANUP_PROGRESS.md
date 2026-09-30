# Cleanup checkpoint — September 29, 2026

Resumed September 30 at the user's request, with staged uploads. Work in progress: NOT yet validated for merge or production.

Branch: cleanup/map-reliability-20260929
Base commit: cbfa2a33a8674dcb8aac7597e22f93d4ee025d35
Production remains https://satx-land-map.netlify.app/ on main.

## Implemented, pending full browser validation

- Removed map-wide parcel hit-testing/cursor overrides and duplicate target click handler; use native Leaflet feature events.
- Lowered target/assemblage panes beneath popups and separated CAD, ownership, infrastructure, and diligence panes.
- Converted Bexar CAD raster/identify interaction to native clickable features, limited to parcel-detail zoom; Comal and Guadalupe also load at zoom 14+.
- Added grouped layer headings using Leaflet's native layer inputs; kept satellite and acquisition context as defaults.
- Consolidated overlapping UI CSS; reduced line widths; made number markers non-interactive; improved popup and mobile sizing.
- Shared compact CAD/H-E-B/sewer popup formats, source dates, and honest clipboard feedback.
- Deferred road queries until enabled; removed cache-busting on static opportunity files.
- Top Land restores the target layer if it has been disabled.
- Tightened Comal and Guadalupe H-E-B filters to business names observed in their source records. Previous substring matching included unrelated owners such as Hebert.
- Separated approximate Bulverde corridor from physical sewer mains; kept it optional and labeled as approximate, with 2016 acceptance date.
- Legacy geometry now uses neutral gray instead of acquisition yellow.

## Source audit findings

Metadata and one-feature geometry queries succeeded for Bexar, Comal, Guadalupe, SAWS, NBU, GBRA gravity/force, GVSUD, TxDOT inventory, AADT, preliminary plats, future land use, Bexar development sublayers, and flood buffer. Field lists and samples are in SOURCE_AUDIT_CHECKPOINT.json.

- Bexar: December 2025 snapshot per existing provenance.
- Comal: data edit November 22, 2024; schema edit is newer and must not be confused with data freshness.
- Guadalupe: February 2022 acquisition date; downloaded August 2022.
- SAWS: July 21, 2021 snapshot.
- NBU: January 17, 2024 snapshot; existing filter returned 2,207 records.
- GBRA Stein Falls gravity/force: line geometry and fields present; snapshot date not published.
- GVSUD: sample notes identify PIR-PDF-derived geometry; excluded from visible sewer group pending accuracy verification.
- Schertz and FEMA: repeated HTTP 502 responses from this environment. This does not prove permanent service failure. Schertz removed from the sewer group; FEMA retained with audit warning, off by default and excluded from Research preset.
- Future roads: endpoint and expected fields exist, but existing current-ROW/name filter returned ZERO records. Named MTP records contain current ROW values and do not establish future-only geometry. Removed the empty/misleading layer, without substituting existing roads or researching new alignments.
- Broad original H-E-B matching returned 57 Bexar, 53 Comal, 23 Guadalupe records; Comal/Guadalupe included unrelated personal surnames. Revised filters need final count/browser validation.

## Validation completed

- Inline JavaScript passed Node syntax check after popup changes.
- Initial headless browser load completed without uncaught JavaScript errors; 30 opportunity parcels loaded and satellite layer was selected.
- Screenshot was captured before satellite tiles finished; actual imagery loading is NOT yet validated.
- Full desktop/mobile interaction suite was started but paused before any checks completed. Do not treat clicks, menu, dragging, or mobile as validated yet.

## Next steps

1. Review checkpoint diff and rerun syntax check after all final source exclusions.
2. Validate satellite imagery completion, layer-menu headings/order/toggles, target and overlapping CAD clicks, Top Land, modes, dragging/zooming, popup close/copy, and mobile layout.
3. Validate actual live H-E-B/CAD/sewer/road feature clicks and revised SQL filters. Confirm source-error presentation and road loading retries.
4. Audit remaining small inconsistencies (e.g. source metadata dates and menu status messaging), then record results.
5. Create PR and merge only after validation; verify existing Netlify production deploy and unchanged URL.

## Intentionally unchanged

All data files, scripts/generate_opportunities.py, ranking methodology, opportunity selections, netlify.toml, repository/site identity, and production branch. No framework, build system, server, new datasets, or broad land research added.


## Stage 1 — September 30: core interaction checkpoint

- Corrected grouped-menu label handling to preserve Leaflet checkbox/radio input elements. The first browser regression run caught the issue.
- Removed transient startup activation of research heat map and information panel; acquisition defaults apply immediately.
- Added reusable browser smoke checks and an existing-endpoint audit script (developer test tools only; no site build/dependency changes).
- Browser checks have passed: 30 opportunity parcels, default OFF states, grouped headings, target checkbox toggles, yellow parcel hover/click/popup/close, and target click while Bexar CAD is enabled.
- Remaining core/mobile/satellite checks are in progress; a popup fade-animation race was identified in the test and the test now waits for popup removal.
- Refreshed live ownership query counts: Bexar 57, Comal 16, Guadalupe 4. Revised filters exclude the unrelated surname matches. All retained CAD/sewer schemas and sample queries passed; FEMA still returned HTTP 502.
- No production change or merge at this checkpoint.


## Stage 2 — September 30: live source interaction checkpoint

- Passed real live feature hover/click/popup/close checks for Bexar CAD, Comal CAD, Guadalupe CAD, H-E-B in each of those three counties, SAWS sewer, NBU sewer, and GBRA gravity and force mains.
- Passed Top Land (including restoring a hidden target layer), map dragging, zoom controls, and Acquisition/Research mode switching.
- Added visible service-request failure messages, retryable road loads, color keys in the menu, sewer diameter units, consistent road popups, and metadata-driven opportunity snapshot date.
- Reduced unnecessary intermediate satellite requests while zooming/dragging.
- Satellite direct tile retrieval succeeds, but full-map browser tile completion still needs resolution. No production merge yet.
- Road geometry loads; the test needs to center on the returned geometry rather than assume the first response is the US 90 corridor.
- Mobile checks and final core rerun remain pending.


## Stage 3 — September 30: final browser validation checkpoint

- Added a finite map max zoom of 20 so Leaflet MarkerCluster always has a valid zoom ceiling; major-development markers still disable clustering at zoom 11.
- Deferred satellite imagery until the opportunity-parcel dataset chooses the initial map extent, with a 4-second fallback if parcel loading stalls or fails.
- Added a branch-only GitHub Actions browser validation workflow using the runner's installed Chrome; production remains untouched.
- Final committed validation run passed desktop/mobile layout, actual Esri satellite imagery loading, grouped layer toggles, target parcel hover/click/popups, target clicks with Bexar CAD enabled, Top Land restore behavior, dragging/zooming, Acquisition/Research modes, existing endpoint audit, and live feature clicks for Bexar/Comal/Guadalupe CAD, H-E-B ownership in all three counties, SAWS, NBU, GBRA gravity/force mains, and TxDOT road geometry.
- JavaScript syntax checks also pass for the inline application script and the smoke-test script.
- Draft PR #32 remains unmerged at this checkpoint; merge only after the validation workflow is green on the final branch head.
