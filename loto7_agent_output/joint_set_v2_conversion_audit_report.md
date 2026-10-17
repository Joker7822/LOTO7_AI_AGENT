# Joint Set v2 — Rank / Calibration / Gate / Portfolio Conversion Audit

- Research-only, historically reused data: **YES**
- New independent real-world OOS: **NO**
- Production promotion: **NO**
- evaluated saved strict-nested rounds: **60**
- baseline five-ticket scores independently reconstructed: **60/60**

## Raw rank versus gated inclusion
- mean raw Top7 hits: **1.5833**
- mean gated Top7 hits: **1.5833**
- raw/gated Top7 membership agreement: **100.0%**
- mean uniform gate: **0.0624**; exactly-zero gate rounds: **0**
- raw/gated log-score edge vs uniform: **-0.007085 / +0.000026**
- raw/gated Brier improvement vs uniform: **-0.002139 / +0.000007**

## Raw-rank-bucket calibration
| Raw rank | Realized inclusion | Raw probability | Gated probability |
|---|---:|---:|---:|
| 1-7 | 0.2262 | 0.2752 | 0.1944 |
| 8-14 | 0.1524 | 0.2104 | 0.1904 |
| 15-21 | 0.1952 | 0.1851 | 0.1889 |
| 22-28 | 0.1738 | 0.1626 | 0.1876 |
| 29-37 | 0.1963 | 0.1297 | 0.1857 |

## Five-ticket objective-alignment diagnostic
- Original-objective mean realized score: **2.8947**
- Exact-evaluation-objective mean realized score: **2.7513**
- aligned-minus-original paired score: **-0.1433** (historical bootstrap CI -0.3288 to +0.0297)
- original train / independent MC score: **3.0230 / 2.8153**
- aligned train / independent MC score: **3.0246 / 2.8148**
- original / aligned MC optimism: **+0.2076 / +0.2098**

> The MC validation scenarios are independent samples of the **same** fitted
> generator; they are not independent winning-draw evidence.
> Historical rounds were reused to motivate this design. No candidate is adopted
> based on this report. The 26-draw prospective shadow and Production remain frozen.
