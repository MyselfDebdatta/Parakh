# Seed Data

Ground-truth static datasets for the PARAKH backend engine.

## Datasets

- `users.json`: 6 customer baseline profiles with median amounts and typical hours.
- `calls.json`: 1 flagged coercive call transcript (`CALL-1421`).
- `transactions.json`: 16 alert transactions (7 star cases + 9 pad transactions).
- `citizen.json`: Citizen dashboard summary and transaction ledger.
- `cohort.json`: 500-customer synthetic risk cohort.
- `display.json`: Dashboard KPI metrics and status distribution.

> **Note**: These files are generated deterministically by `scripts/port_seed.py`. Do not edit them manually.
