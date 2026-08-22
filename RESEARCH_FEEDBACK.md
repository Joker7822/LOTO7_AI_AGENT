# Continuous Research Replay Feedback

Research Winnerが更新されるたびに、そのモデルを過去の全対象回へstrict walk-forwardで再適用し、次世代のResearch Parentを決めるためのフィードバックを生成します。

## Flow

1. `loto7_v4_runner.py` が30/60/120回窓からprovisional Research Winnerを選ぶ。
2. `research_feedback.py` がWinner変更または`loto7.csv`変更を検出する。
3. 対象モデルを第101回相当以降の全履歴へ再予測する。各対象回の予測には、その回より前の履歴だけを使う。
4. full / last120 / last60 / last30 の5口scoreをdeterministic Random referenceと比較する。
5. 過去全体のfeedback objectiveが改善し、full最大一致数と直近120回scoreに大きな後退がなければ候補を採用する。
6. 採用モデルを`v4_research_state.json`の`research_parent_config`へ書き戻す。次世代のmutationはこの再評価済みParentから開始する。
7. 候補が悪化していれば前のResearch Parentを維持する。

同一データ・同一モデルの結果は`research_feedback_cache.json`に保存し、同じ全履歴計算を繰り返しません。

## Outputs

- `loto7_agent_output/research_feedback_state.json` — 現在採用されているResearch Parentと累積回数
- `loto7_agent_output/research_feedback_summary.json` — 最新候補と現Parentの比較・採否
- `loto7_agent_output/research_feedback_report.md` — 人間向け最新レポート
- `loto7_agent_output/research_feedback_candidate_rounds.csv` — 最新の新規候補を全履歴へ再予測した回別結果
- `loto7_agent_output/research_feedback_history.jsonl` — replay判定履歴
- `loto7_agent_output/research_feedback_cache.json` — model/data SHA単位の再計算キャッシュ

## Statistical boundary

この仕組みはResearch探索を改善するための**retrospective training feedback**です。最新モデル自体が過去データから探索・選択されているため、この結果を独立した予測精度の証明として扱いません。

Production Championの昇格条件は変更しません。Champion昇格に使える証拠は、抽せん前に凍結したshadowモデルを未知だった未来結果で採点したFuture OOSだけです。

この分離により、過去データから継続的にResearchモデルを改善しながら、過学習したモデルが過去スコアだけでProductionへ昇格することを防ぎます。
