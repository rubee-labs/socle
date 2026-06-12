# Bench Forge — 2026-05-24T09:42:40

- Project : `/Users/bhamon/git/claude-enterprise`
- Corpus : `/tmp/forge-bench-corpus.json`
- Retrievers : R1, R2, R3
- Questions : 123
- Total calls : 369
- Wall-clock : 57440 ms

## Récap par retriever

| Retriever | Label | Exact | Substring | Erreurs | Latence p50 | Latence p95 |
|---|---|---|---|---|---|---|
| R1 | cascade | 123/123 (100%) | 123/123 (100%) | 0 | 0 ms | 0 ms |
| R2 | grep-aggregated | 119/123 (97%) | 119/123 (97%) | 0 | 0 ms | 0 ms |
| R3 | filesystem-grep | 123/123 (100%) | 123/123 (100%) | 0 | 450 ms | 520 ms |

## Verdict

- Meilleur exact-match : **R1** (cascade) — 100%
- Plus rapide (p50) : **R1** (cascade) — 0 ms

