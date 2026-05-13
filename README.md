# DF-164 LexVance-Mandanten-Pipeline [CRUX-MK]

**Status:** SKELETON-CONDITIONAL (Welle-51 W51-B Skeleton-Wave-2)
**Domain:** K_0 (LexVance Revenue + Mandanten-Pipeline)
**Welle:** 25

## Mission

Mandanten-Pipeline-Tracking fuer LexVance. Tracking:
- Pipeline-Value-EUR-Total
- New-Mandanten-30d
- Conversion-Rate-Pct
- Stale-Pipeline-90d

**NIEMALS Mandanten-Outreach oder Auto-Akquise.**

## Usage

```bash
cd ~/Projects/dark-factories/df-164
python df-164-engine.py        # Mock-Mode default
pytest tests/                   # Existing tests
```

## Output

- Reports: `reports/df-164-{date}.json`
- STOP-Flag: `/tmp/df-164.stop`

[CRUX-MK]
