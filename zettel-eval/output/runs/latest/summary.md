# Retrieval Benchmark Summary

## Best Method Per Dataset

- `andy-matuschak` / `bm25`: MAP=0.2965, Hit@5=0.7500, Hit@10=0.8800, MRR=0.5760, params={"b": 0.75, "k1": 1.8}
- `andy-matuschak` / `dense`: MAP=0.3706, Hit@5=0.7800, Hit@10=0.9300, MRR=0.6301, params={"dimensions": 1536}
- `andy-matuschak` / `dense_nomic`: MAP=0.1705, Hit@5=0.5100, Hit@10=0.6700, MRR=0.3672, params={"dimensions": 768}
- `andy-matuschak` / `hybrid`: MAP=0.3600, Hit@5=0.8400, Hit@10=0.9700, MRR=0.6421, params={"alpha": 0.7, "b": 0.75, "dimensions": 1536, "k1": 1.2}
- `andy-matuschak` / `hybrid_nomic`: MAP=0.3063, Hit@5=0.7800, Hit@10=0.8800, MRR=0.5793, params={"alpha": 0.1, "b": 0.75, "dimensions": 768, "k1": 1.2}
- `braindump-jethro` / `bm25`: MAP=0.0659, Hit@5=0.1200, Hit@10=0.3500, MRR=0.0708, params={"b": 0.75, "k1": 1.8}
- `braindump-jethro` / `dense`: MAP=0.3383, Hit@5=0.5100, Hit@10=0.5600, MRR=0.3824, params={"dimensions": 1536}
- `braindump-jethro` / `dense_nomic`: MAP=0.1430, Hit@5=0.2300, Hit@10=0.2800, MRR=0.1695, params={"dimensions": 768}
- `braindump-jethro` / `hybrid`: MAP=0.3533, Hit@5=0.5300, Hit@10=0.5800, MRR=0.4029, params={"alpha": 0.9, "b": 0.75, "dimensions": 1536, "k1": 1.2}
- `braindump-jethro` / `hybrid_nomic`: MAP=0.2340, Hit@5=0.4100, Hit@10=0.4200, MRR=0.2765, params={"alpha": 0.7, "b": 0.75, "dimensions": 768, "k1": 1.2}
- `steph-ango` / `bm25`: MAP=0.1096, Hit@5=0.2600, Hit@10=0.3700, MRR=0.1366, params={"b": 0.75, "k1": 1.2}
- `steph-ango` / `dense`: MAP=0.2094, Hit@5=0.3800, Hit@10=0.4400, MRR=0.2483, params={"dimensions": 1536}
- `steph-ango` / `dense_nomic`: MAP=0.1912, Hit@5=0.3500, Hit@10=0.4100, MRR=0.2635, params={"dimensions": 768}
- `steph-ango` / `hybrid`: MAP=0.2099, Hit@5=0.3600, Hit@10=0.4300, MRR=0.2507, params={"alpha": 0.9, "b": 0.75, "dimensions": 1536, "k1": 1.2}
- `steph-ango` / `hybrid_nomic`: MAP=0.2262, Hit@5=0.3500, Hit@10=0.4500, MRR=0.2867, params={"alpha": 0.9, "b": 0.75, "dimensions": 768, "k1": 1.2}

## Aggregate Diagnostics

- `andy-matuschak`: bm25=0.6256, dense=0.6777, dense_nomic=0.4294, hybrid=0.7030, hybrid_nomic=0.6364
- `braindump-jethro`: bm25=0.1517, dense=0.4477, dense_nomic=0.2056, hybrid=0.4665, hybrid_nomic=0.3351
- `steph-ango`: bm25=0.2190, dense=0.3194, dense_nomic=0.3037, hybrid=0.3127, hybrid_nomic=0.3282
