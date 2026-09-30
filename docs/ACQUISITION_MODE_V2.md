# Acquisition Mode V2

Acquisition Mode V2 is the parcel-ranking engine behind the highlighted acquisition targets.

## Decision architecture

The engine now evaluates land in this order:

1. Rank emerging commercial nodes.
2. Search parcels around qualified nodes.
3. Apply hard parcel filters before ranking.
4. Score location/node quality separately from parcel execution.
5. Verify finalist geometry against SARA/BCAD.
6. Add a data-confidence score.
7. Assign an acquisition tier: PRIORITY, WATCH, or EARLY SPECULATION.

The final opportunity score is 60% node/location quality and 40% parcel execution.

## Node score — 60% of final score

- Residential growth: 20
- Intersection / road-network strength: 15
- Retail catalyst proximity: 10
- Traffic volume and trajectory: 10
- Timing / residential-commercial demand gap: 5

Only credible nodes proceed to parcel search. The generator currently searches up to 14 qualifying nodes.

## Parcel execution — 40% of final score

- Frontage / access proxy: 12
- Size and shape: 10
- Utility-path proxy: 8
- Flood constraints: 5
- Acquisition complexity / raw-land economics: 5

## Hard gates

A highlighted parcel must:

- contain at least 3 acres;
- be within 1 mile of a selected node by parcel-edge distance;
- have a credible road/frontage signal;
- remain predominantly raw or low-improvement land;
- meet minimum shape quality;
- pass FEMA screening with less than 10% floodway, less than 50% SFHA, and at least a 3-acre usable-area proxy;
- avoid public/institutional/major-anchor ownership and common residential-homebuilder ownership; and
- be re-verified against SARA/BCAD geometry before appearing in Acquisition Mode.

## Acquisition tiers

### PRIORITY

Bright yellow. These are the parcels that deserve immediate ownership, access, utility and pricing investigation.

Current rule requires, among other conditions:

- opportunity score at least 78;
- confidence at least 68;
- within 0.60 miles of the node;
- credible major-road exposure and usable frontage/corner geometry;
- flood score at least 75;
- parcel execution score at least 68; and
- at least a mapped utility-path proxy.

A utility proxy does **not** equal confirmed capacity.

### WATCH

Amber. Strong enough to track closely, but one or more acquisition/execution items still need verification or improvement.

### EARLY SPECULATION

Gray outline. Strong node thesis but lower parcel certainty. The generator does not force any parcel into this tier; none will display if none clear the minimum standard.

## Confidence

Confidence is separate from opportunity. It reflects the completeness/reliability of node data, BCAD geometry, road evidence, FEMA screening, traffic, utility context and ownership verification.

A high opportunity score with weaker diligence data does not automatically become Priority.

## Important limitations

- Road frontage is a GIS proximity/overlap proxy, not legal access.
- Median cuts, turn movements, driveway permits and cross-access require diligence.
- Utility scoring is a mapped proximity/path proxy, not a capacity commitment.
- FEMA screening is not a substitute for survey, drainage or engineering.
- The current exact opportunity generator is strongest in Bexar County because finalist geometry is verified against the SARA/BCAD parcel service.
- Scores are screening tools, not valuations or acquisition recommendations without follow-up diligence.
