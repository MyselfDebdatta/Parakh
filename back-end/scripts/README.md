# Backend Scripts

Utility scripts for data generation and development.

## Files

- `port_seed.py`: Generates the 6 ground-truth seed JSON files into `seed/` from `front-end/src/data/mock.ts` with byte-identical literal preservation and deterministic cohort formulas.

## Usage

```bash
python scripts/port_seed.py
```
