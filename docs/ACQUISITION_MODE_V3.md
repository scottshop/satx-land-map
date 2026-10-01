# Acquisition Mode V3 — Multi-County

Acquisition Mode V3 is the parcel-ranking engine behind the highlighted acquisition targets on the San Antonio land map.

## Core architecture

The engine evaluates land in this order:

1. Rank emerging commercial nodes.
2. Select qualified nodes by county.
3. Search the county parcel universe around those nodes.
4. Apply hard parcel filters.
5. Score node/location quality separately from parcel execution.
6. Screen FEMA flood constraints.
7. Verify/corroborate county parcel records.
8. Calculate a separate data-confidence score.
9. Assign an acquisition tier: PRIORITY, WATCH, or EARLY SPECULATION.

The final opportunity score remains 60% node/location quality and 40% parcel execution.

## Node score — 60% of final score

- Residential growth / housing evidence: 20
- Intersection and road-network strength: 15
- Retail catalyst proximity: 10
- Traffic volume and trajectory: 10
- Timing / demand-gap signal: 5

Bexar has the strongest detailed plat, permit and land-use evidence.

Outside Bexar, the engine does **not** pretend missing countywide housing data is zero. Comal and Guadalupe nodes use statewide road/traffic evidence plus a conservative regional-corridor prior, and their node confidence is capped until comparable countywide subdivision/permit feeds are added.

## Parcel execution — 40% of final score

- Frontage / access proxy: 12
- Size and shape: 10
- Mapped sewer proximity: 8
- Flood constraints: 5
- Acquisition complexity / raw-land economics: 5

Sewer scoring is based on distance from the parcel to a mapped existing sewer feature when available. It is not a capacity commitment.

## County parcel sources and freshness policy

### Bexar

Candidate universe comes from the Bexar public parcel layer. Finalists are batch re-verified against the SARA / BCAD parcel service.

Bexar is currently the only county allowed to earn **PRIORITY** because it has the strongest parcel-verification pipeline.

### Comal

Candidates come from the public Comal CAD ArcGIS parcel layer. Its underlying data edit date is November 22, 2024.

Comal parcel geometry is screened directly from that county parcel source, but the source is treated as **AGING**. Comal parcels are therefore capped at **WATCH** until a fresher countywide parcel source is available.

The engine also corrects inconsistent Comal acreage fields by cross-checking reported acreage against GIS polygon area and using geometry-derived acres when the values materially disagree.

### Guadalupe

The available countywide public parcel extract is February 2022 vintage and is treated as **STALE**.

Guadalupe parcels cannot become PRIORITY. A stale Guadalupe parcel can only become WATCH if a newer GBRA project parcel feed independently corroborates the parcel/owner; otherwise its maximum tier is EARLY SPECULATION.

The engine is allowed to return zero Guadalupe highlights rather than forcing stale candidates onto the map.

## Hard gates

A highlighted parcel must generally:

- contain at least 3 usable acres;
- lie within 1 mile of a selected node by parcel-edge distance;
- have credible road/frontage evidence;
- remain predominantly raw or low-improvement land;
- meet minimum shape quality;
- pass FEMA screening with less than 10% floodway, less than 50% mapped SFHA, and at least a 3-acre usable-area proxy;
- avoid public, institutional, major-anchor, common residential-homebuilder and obvious operating-user ownership; and
- pass the applicable county geometry/source verification rule.

Internal GIS segment IDs are not treated as public-road frontage.

## Acquisition tiers

### PRIORITY — bright yellow

Priority means the parcel deserves immediate ownership, access, sewer and pricing diligence.

Current Priority requirements include:

- Bexar County only;
- recent configured parcel source;
- opportunity score at least 78;
- confidence at least 68;
- within 0.60 miles of the target node;
- credible major-road exposure;
- at least 200 feet of frontage proxy **or** a strong corner signal;
- flood score at least 75;
- parcel execution score at least 68; and
- mapped sewer within the close-proximity proxy threshold.

### WATCH — amber

Strong enough to monitor or investigate, but one or more execution, freshness or verification items prevent Priority.

Comal currently tops out at Watch.

### EARLY SPECULATION — gray outline

Interesting node/parcel thesis, but data freshness or execution certainty is not strong enough for active pursuit.

The engine does not force parcels into this tier.

## Confidence is separate from opportunity

A high opportunity score does not automatically become a high-priority acquisition.

Confidence reflects the completeness and freshness of:

- node evidence;
- county parcel geometry/ownership;
- road/frontage evidence;
- FEMA screening;
- traffic evidence;
- mapped sewer evidence; and
- source corroboration.

County-specific confidence caps prevent older regional data from appearing more certain than it is.

## Reliability improvements

V3 is designed to refresh without making hundreds of fragile one-off GIS requests:

- FEMA polygons are fetched by active-node envelope and intersected against parcels locally.
- Bexar finalist verification is batch-loaded from SARA / BCAD by Property ID.
- Comal candidates are not redundantly re-queried from the same CAD service that supplied them.
- NBU / GBRA project parcel feeds are batch-loaded only as secondary corroboration.
- ArcGIS requests retry transient failures with backoff.
- Failed flood or parcel verification is fail-closed rather than silently treated as clean.

## Important limitations

- Frontage is a GIS proximity/overlap proxy, not legal access.
- A hard-corner signal is not a driveway or TxDOT access permit.
- Median cuts, turn movements, cross-access and deceleration requirements require diligence.
- Sewer distance is not confirmation of depth, capacity, lift requirements or service commitment.
- FEMA screening is not a substitute for survey, drainage or engineering.
- Tax/CAD data is not title work.
- Scores are acquisition-screening tools, not valuations.
