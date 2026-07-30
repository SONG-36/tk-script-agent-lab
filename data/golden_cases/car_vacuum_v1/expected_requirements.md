# Expected Requirements

This Golden Case is a minimal Phase 1A fixture for a car vacuum cleaner schema.

Requirements for future phases:

- Do not treat unverified product attributes as facts.
- Do not invent power, suction, runtime, battery capacity, certifications, discounts, or compatibility claims.
- Keep factual claims separate from creative copy.
- Require source tracking before a claim can appear in a generated script.
- Preserve uncertainty when source evidence is missing.

Phase 0 does not implement these requirements. It only records the target behavior.

## Phase 1A Fixture Boundary

The verified facts in this fixture are limited to schema-safe facts such as product category and generic car-interior cleanup context. They do not represent a confirmed real SKU.

The fixture intentionally keeps unverified facts for wattage and runtime so validation can distinguish unknown data from confirmed product claims.

No suction strength, power rating, runtime, noise level, discount, certification, or compatibility claim is asserted as a real product fact.
