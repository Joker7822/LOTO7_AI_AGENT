#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LOTO7 Self-Evolving Agent
-------------------------
目的:
  過去抽せん履歴を使って複数の予測シグナルをウォークフォワード検証し、
  新しい抽せん結果がCSVに追加されるたびに戦略重みを再評価・自動更新する。

重要:
  このプログラムは宝くじの将来当せんを保証・実証するものではありません。
  出力は「履歴から計算した相対スコア」と「候補組合せ」です。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


N_NUMBERS = 37
PICKS = 7
RANDOM_HIT_MEAN = PICKS * PICKS / N_NUMBERS


def read_csv_flexible(path: Path) -> pd.DataFrame:
    errors = []
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception as e:
            errors.append(f"{enc}: {e}")
    raise RuntimeError("CSVを読み込めませんでした: " + " / ".join(errors))


def parse_main_numbers(value: str) -> List[int]:
    nums = [int(x) for x in str(value).replace(",", " ").split()]
    if len(nums) != PICKS:
        raise ValueError(f"本数字は7個必要です: {value!r}")
    if len(set(nums)) != PICKS:
        raise ValueError(f"本数字に重複があります: {value!r}")
    if min(nums) < 1 or max(nums) > N_NUMBERS:
        raise ValueError(f"本数字は1〜37の範囲です: {value!r}")
    return nums


def make_history(df: pd.DataFrame) -> Tuple[np.ndarray, pd.DataFrame]:
    required = {"抽せん日", "本数字"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"必要列がありません: {sorted(missing)}")

    tmp = df.copy()
    tmp["抽せん日"] = pd.to_datetime(tmp["抽せん日"], errors="raise")
    tmp = tmp.sort_values("抽せん日").reset_index(drop=True)

    if tmp["抽せん日"].duplicated().any():
        raise ValueError("抽せん日に重複があります。")

    x = np.zeros((len(tmp), N_NUMBERS), dtype=np.int8)
    for i, value in enumerate(tmp["本数字"]):
        nums = parse_main_numbers(value)
        x[i, np.array(nums) - 1] = 1
    return x, tmp


def zsoftmax(scores: np.ndarray, temperature: float = 1.25) -> np.ndarray:
    scores = np.asarray(scores, dtype=float)
    sd = float(scores.std())
    if sd < 1e-12:
        return np.ones(N_NUMBERS, dtype=float) / N_NUMBERS
    z = (scores - scores.mean()) / sd
    z = np.clip(z / temperature, -6.0, 6.0)
    e = np.exp(z - z.max())
    return e / e.sum()


def expert_probabilities(hist: np.ndarray) -> Dict[str, np.ndarray]:
    """各戦略は「次回に選びやすい相対重み」を37数字に付ける。"""
    t = len(hist)
    if t < 20:
        raise ValueError("最低20回分の履歴が必要です。")

    out: Dict[str, np.ndarray] = {}

    for w in (20, 50, 100, 200):
        h = hist[-min(w, t):]
        out[f"hot_{w}"] = zsoftmax(h.mean(axis=0), 1.25)

    for hl in (10, 30, 60):
        ages = np.arange(t - 1, -1, -1, dtype=float)
        weights = 0.5 ** (ages / hl)
        freq = (hist * weights[:, None]).sum(axis=0) / weights.sum()
        out[f"ewma_{hl}"] = zsoftmax(freq, 1.25)

    gap_now = np.zeros(N_NUMBERS, dtype=float)
    mean_gap = np.full(N_NUMBERS, N_NUMBERS / PICKS, dtype=float)
    for j in range(N_NUMBERS):
        idx = np.flatnonzero(hist[:, j])
        gap_now[j] = (t - 1 - idx[-1]) if len(idx) else t
        if len(idx) >= 3:
            mean_gap[j] = np.diff(idx).mean()
    out["overdue"] = zsoftmax(gap_now / (mean_gap + 1e-9), 1.50)

    out["recent_cold"] = zsoftmax(
        -hist[-min(30, t):].mean(axis=0), 1.50
    )

    short = hist[-min(20, t):].mean(axis=0)
    long = hist[-min(120, t):].mean(axis=0)
    out["momentum"] = zsoftmax(short - long, 1.30)

    last = np.flatnonzero(hist[-1])
    co = hist.T @ hist
    denom = hist.sum(axis=0).astype(float)
    pair = np.zeros(N_NUMBERS, dtype=float)
    for j in range(N_NUMBERS):
        vals = [co[j, k] / max(denom[k], 1.0) for k in last]
        pair[j] = float(np.mean(vals))
    out["pair_context"] = zsoftmax(pair, 1.40)

    return out


@dataclass
class BacktestResult:
    keys: List[str]
    final_weights: np.ndarray
    mean_hits: float
    mean_mass: float
    z_vs_random: float
    approx_two_sided_p: float
    draws_tested: int
    expert_summary: pd.DataFrame


def walk_forward_evolve(
    x: np.ndarray,
    min_train: int = 100,
    eta: float = 3.0,
    decay: float = 0.995,
    expert_uniform_mix: float = 0.15,
) -> BacktestResult:
    """
    Hedge型のオンライン重み更新。
    各時点tでは t より前だけで予測し、結果を見た後に重み更新する。
    """
    if len(x) <= min_train:
        raise ValueError(f"ウォークフォワード検証には{min_train+1}回以上必要です。")

    keys = list(expert_probabilities(x[:min_train]).keys())
    logw = np.zeros(len(keys), dtype=float)

    hits = []
    masses = []
    expert_hits = {k: [] for k in keys}
    expert_mass = {k: [] for k in keys}

    for t in range(min_train, len(x)):
        ex = expert_probabilities(x[:t])

        raw_w = np.exp(logw - logw.max())
        raw_w /= raw_w.sum()
        w = (1.0 - expert_uniform_mix) * raw_w + expert_uniform_mix / len(keys)

        q = np.zeros(N_NUMBERS, dtype=float)
        for i, k in enumerate(keys):
            q += w[i] * ex[k]
        q /= q.sum()

        actual = np.flatnonzero(x[t])
        top7 = np.argsort(q)[-PICKS:]
        hits.append(len(set(top7) & set(actual)))
        masses.append(float(q[actual].sum()))

        rewards = []
        for k in keys:
            qk = ex[k]
            rewards.append(float(qk[actual].sum()))
            expert_mass[k].append(float(qk[actual].sum()))
            expert_hits[k].append(
                len(set(np.argsort(qk)[-PICKS:]) & set(actual))
            )

        logw = decay * logw + eta * (np.array(rewards) - PICKS / N_NUMBERS)
        logw = np.clip(logw, -20.0, 20.0)

    raw_w = np.exp(logw - logw.max())
    raw_w /= raw_w.sum()
    final_w = (1.0 - expert_uniform_mix) * raw_w + expert_uniform_mix / len(keys)

    var_single = (
        PICKS
        * (PICKS / N_NUMBERS)
        * (1 - PICKS / N_NUMBERS)
        * ((N_NUMBERS - PICKS) / (N_NUMBERS - 1))
    )
    se = math.sqrt(var_single / len(hits))
    z = (float(np.mean(hits)) - RANDOM_HIT_MEAN) / se
    p2 = math.erfc(abs(z) / math.sqrt(2.0))

    rows = []
    for k in keys:
        h = np.asarray(expert_hits[k], dtype=float)
        m = np.asarray(expert_mass[k], dtype=float)
        rows.append(
            {
                "expert": k,
                "weight": float(final_w[keys.index(k)]),
                "mean_hits_all": float(h.mean()),
                "mean_hits_last100": float(h[-100:].mean()),
                "mean_mass_all": float(m.mean()),
                "mean_mass_last100": float(m[-100:].mean()),
            }
        )
    summary = pd.DataFrame(rows).sort_values("weight", ascending=False)

    return BacktestResult(
        keys=keys,
        final_weights=final_w,
        mean_hits=float(np.mean(hits)),
        mean_mass=float(np.mean(masses)),
        z_vs_random=float(z),
        approx_two_sided_p=float(p2),
        draws_tested=len(hits),
        expert_summary=summary,
    )


def final_score(x: np.ndarray, bt: BacktestResult, uniform_mix: float = 0.20) -> np.ndarray:
    ex = expert_probabilities(x)
    q = np.zeros(N_NUMBERS, dtype=float)
    for i, k in enumerate(bt.keys):
        q += bt.final_weights[i] * ex[k]
    q /= q.sum()
    q = (1.0 - uniform_mix) * q + uniform_mix / N_NUMBERS
    return q / q.sum()


def weighted_sample_without_replacement(
    rng: np.random.Generator, q: np.ndarray, k: int = PICKS
) -> Tuple[int, ...]:
    nums = rng.choice(np.arange(1, N_NUMBERS + 1), size=k, replace=False, p=q)
    return tuple(sorted(int(v) for v in nums))


def make_ticket_portfolio(
    q: np.ndarray,
    n_tickets: int,
    seed: int,
    pool_size: int = 15000,
    overlap_penalty: float = 0.65,
) -> List[Tuple[int, ...]]:
    """
    高スコア候補を多数サンプルし、既採用券との重複を罰して複数券を分散。
    個々の組合せの抽せん確率を高めると主張するものではない。
    """
    rng = np.random.default_rng(seed)
    pool = set()
    target_pool = max(pool_size, n_tickets * 100)
    max_trials = target_pool * 5

    for _ in range(max_trials):
        pool.add(weighted_sample_without_replacement(rng, q))
        if len(pool) >= target_pool:
            break

    candidates = list(pool)
    logq = np.log(q + 1e-15)

    def base_score(ticket):
        return float(sum(logq[n - 1] for n in ticket))

    candidates.sort(key=base_score, reverse=True)
    candidates = candidates[: min(len(candidates), 5000)]

    selected: List[Tuple[int, ...]] = []
    while candidates and len(selected) < n_tickets:
        best = None
        best_score = -1e100
        for ticket in candidates:
            s = base_score(ticket)
            if selected:
                max_overlap = max(len(set(ticket) & set(prev)) for prev in selected)
                s -= overlap_penalty * max_overlap
            if s > best_score:
                best_score = s
                best = ticket
        selected.append(best)
        candidates.remove(best)
    return selected


def fingerprint_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(csv_path: Path, out_dir: Path, tickets: int, seed: int, min_train: int) -> None:
    df = read_csv_flexible(csv_path)
    x, clean = make_history(df)

    bt = walk_forward_evolve(x, min_train=min_train)
    q = final_score(x, bt)

    ranking = np.argsort(q)[::-1] + 1
    pred = pd.DataFrame(
        {
            "rank": np.arange(1, N_NUMBERS + 1),
            "number": ranking,
            "relative_score": [float(q[n - 1]) for n in ranking],
            "score_index_vs_uniform": [
                float(q[n - 1] / (1.0 / N_NUMBERS)) for n in ranking
            ],
        }
    )

    portfolio = make_ticket_portfolio(q, tickets, seed)
    ticket_rows = []
    for i, t in enumerate(portfolio, 1):
        ticket_rows.append(
            {
                "ticket": i,
                "numbers": " ".join(f"{n:02d}" for n in t),
                "sum": sum(t),
                "odd_count": sum(n % 2 for n in t),
            }
        )
    ticket_df = pd.DataFrame(ticket_rows)

    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / "prediction_ranking.csv"
    ticket_path = out_dir / "candidate_tickets.csv"
    expert_path = out_dir / "expert_backtest.csv"
    state_path = out_dir / "agent_state.json"

    pred.to_csv(pred_path, index=False, encoding="utf-8-sig")
    ticket_df.to_csv(ticket_path, index=False, encoding="utf-8-sig")
    bt.expert_summary.to_csv(expert_path, index=False, encoding="utf-8-sig")

    latest_date = clean["抽せん日"].iloc[-1].date().isoformat()
    latest_round = str(clean["回別"].iloc[-1]) if "回別" in clean.columns else None

    state = {
        "csv_sha256": fingerprint_file(csv_path),
        "rows": int(len(clean)),
        "latest_draw_date": latest_date,
        "latest_round": latest_round,
        "walk_forward_draws": bt.draws_tested,
        "mean_top7_hits": bt.mean_hits,
        "random_theoretical_mean_hits": RANDOM_HIT_MEAN,
        "z_vs_random": bt.z_vs_random,
        "approx_two_sided_p": bt.approx_two_sided_p,
        "signal_claim": (
            "not_confirmed"
            if bt.approx_two_sided_p >= 0.05
            else "requires_independent_validation"
        ),
        "expert_weights": {
            k: float(bt.final_weights[i]) for i, k in enumerate(bt.keys)
        },
        "top15": [
            {
                "number": int(n),
                "relative_score": float(q[n - 1]),
                "score_index_vs_uniform": float(q[n - 1] / (1 / N_NUMBERS)),
            }
            for n in ranking[:15]
        ],
        "seed": int(seed),
    }
    state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("=" * 64)
    print("LOTO7 Self-Evolving Agent")
    print("=" * 64)
    print(f"data: {len(clean)} draws | latest: {latest_date} {latest_round or ''}")
    print(
        f"walk-forward: {bt.draws_tested} draws | "
        f"mean top7 hits={bt.mean_hits:.3f} | "
        f"random theory={RANDOM_HIT_MEAN:.3f}"
    )
    print(
        f"z={bt.z_vs_random:.3f} | approx two-sided p={bt.approx_two_sided_p:.3f}"
    )
    if bt.approx_two_sided_p >= 0.05:
        print("signal: 統計的優位は確認できません。")
    else:
        print("signal: 見かけの差あり。独立期間での再検証が必要です。")

    print("\nTop 15 relative-score numbers:")
    for rank, n in enumerate(ranking[:15], 1):
        print(
            f"{rank:2d}. {n:02d}  score={q[n-1]:.6f}  "
            f"index={q[n-1]/(1/N_NUMBERS):.2f}"
        )

    print("\nCandidate tickets:")
    for row in ticket_rows:
        print(f"{row['ticket']:2d}. {row['numbers']}")

    print("\nFiles:")
    for p in (pred_path, ticket_path, expert_path, state_path):
        print(f"  {p}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="LOTO7 self-evolving prediction agent")
    p.add_argument("--csv", required=True, type=Path, help="LOTO7履歴CSV")
    p.add_argument("--out-dir", type=Path, default=Path("loto7_output"))
    p.add_argument("--tickets", type=int, default=5)
    p.add_argument("--seed", type=int, default=691)
    p.add_argument("--min-train", type=int, default=100)
    return p


if __name__ == "__main__":
    args = build_parser().parse_args()
    if args.tickets < 1:
        raise SystemExit("--tickets は1以上にしてください。")
    run(
        csv_path=args.csv,
        out_dir=args.out_dir,
        tickets=args.tickets,
        seed=args.seed,
        min_train=args.min_train,
    )
