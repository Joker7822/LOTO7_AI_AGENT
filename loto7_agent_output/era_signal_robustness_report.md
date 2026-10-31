# Research Parent Era Signal Robustness

- model: **signal-g05690-c01-7b9859bf53**
- use: **Research robustness diagnostic only**

| Era | rounds | Signal objective | Top7 edge | log edge | Brier edge |
|---|---:|---:|---:|---:|---:|
| 101-250 | 150 | -0.03505 | +0.1223 | -0.01757 | -0.001384 |
| 251-400 | 150 | -0.04728 | -0.0177 | -0.01710 | -0.001273 |
| 401-550 | 150 | -0.06995 | -0.0977 | -0.02199 | -0.001465 |
| 551-latest | 151 | -0.02900 | +0.0995 | -0.01460 | -0.001138 |

- positive eras: **0/4**
- worst-era Signal objective: **-0.06995**

> 全期間平均だけでなく、時代をまたいで同じ方向のSignalが出ているかを確認します。
