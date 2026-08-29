<?php
declare(strict_types=1);

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Robots-Tag: noindex, nofollow', true);

function h($value) {
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

$configPath = __DIR__ . '/prediction_ingest_config.php';
$error = null;
$latestRound = null;
$rows = array();

try {
    if (!is_file($configPath)) {
        throw new RuntimeException('DB設定ファイルが見つかりません。');
    }

    $config = require $configPath;
    $pdo = new PDO(
        (string)$config['db_dsn'],
        (string)$config['db_user'],
        (string)$config['db_password'],
        array(
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_EMULATE_PREPARES => false,
            PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC
        )
    );

    $latestRoundStmt = $pdo->query(
        'SELECT MAX(CAST(target_round AS UNSIGNED)) AS latest_round FROM loto7_predictions WHERE is_active = 1'
    );
    $latestRoundRow = $latestRoundStmt->fetch();
    if ($latestRoundRow && $latestRoundRow['latest_round'] !== null) {
        $latestRound = (string)$latestRoundRow['latest_round'];

        $stmt = $pdo->prepare(<<<'SQL'
SELECT
    p.prediction_id,
    p.prediction_created_at_jst,
    p.base_round,
    p.target_round,
    p.target_draw_date_estimate,
    p.ticket,
    p.predicted_numbers,
    p.model_version,
    r.actual_draw_date,
    r.actual_main_numbers,
    r.actual_bonus_numbers,
    r.main_hits,
    r.bonus_hits,
    r.grade,
    r.prize_amount_yen,
    r.purchase_cost_yen,
    r.net_result_yen
FROM loto7_predictions p
LEFT JOIN loto7_prediction_results r
  ON r.prediction_id = p.prediction_id
WHERE p.is_active = 1
  AND CAST(p.target_round AS UNSIGNED) = :target_round
ORDER BY p.ticket ASC, p.prediction_created_at_jst ASC
SQL
        );
        $stmt->execute(array(':target_round' => (int)$latestRound));
        $rows = $stmt->fetchAll();
    }
} catch (Throwable $e) {
    error_log('LOTO7 latest predictions view error: ' . $e->getMessage());
    $error = 'データベースから予測を取得できませんでした。';
}

function number_badges($numbers) {
    $parts = preg_split('/[\s,\-]+/', trim((string)$numbers));
    $html = '';
    foreach ($parts as $part) {
        if ($part === '') {
            continue;
        }
        $html .= '<span class="ball">' . h(str_pad($part, 2, '0', STR_PAD_LEFT)) . '</span>';
    }
    return $html;
}
?>
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>LOTO7 最新予測</title>
<style>
:root {
  color-scheme: light;
  --bg: #f5f7fb;
  --panel: #ffffff;
  --text: #172033;
  --muted: #667085;
  --line: #e4e7ec;
  --accent: #1849a9;
  --accent-soft: #eff4ff;
  --ok: #067647;
  --warn: #b54708;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", sans-serif;
  background: var(--bg);
  color: var(--text);
}
.wrap { width: min(1120px, calc(100% - 28px)); margin: 32px auto; }
.hero {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 24px;
  margin-bottom: 18px;
}
h1 { margin: 0 0 8px; font-size: clamp(24px, 4vw, 36px); }
.sub { color: var(--muted); margin: 0; }
.round { color: var(--accent); font-weight: 800; }
.grid { display: grid; gap: 14px; }
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 18px;
}
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.ticket { font-weight: 800; font-size: 18px; }
.date { color: var(--muted); font-size: 14px; }
.balls { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 16px; }
.ball {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  background: var(--accent-soft);
  border: 1px solid #c7d7fe;
  color: var(--accent);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
  border-top: 1px solid var(--line);
  padding-top: 14px;
  font-size: 14px;
}
.meta .label { color: var(--muted); display: block; font-size: 12px; margin-bottom: 2px; }
.result {
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f9fafb;
  border: 1px solid var(--line);
}
.result.ok { background: #ecfdf3; border-color: #abefc6; }
.result.pending { color: var(--muted); }
.error {
  background: #fef3f2;
  border: 1px solid #fecdca;
  border-radius: 14px;
  padding: 16px;
  color: #b42318;
}
.empty {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 24px;
  color: var(--muted);
}
.footer { color: var(--muted); font-size: 12px; margin: 18px 4px 0; }
@media (max-width: 640px) {
  .wrap { margin: 16px auto; width: min(100% - 18px, 1120px); }
  .hero, .card { border-radius: 14px; }
  .meta { grid-template-columns: 1fr; }
  .ball { width: 40px; height: 40px; }
}
</style>
</head>
<body>
<main class="wrap">
  <section class="hero">
    <h1>LOTO7 最新予測</h1>
    <?php if ($latestRound !== null): ?>
      <p class="sub">最新対象回：<span class="round">第<?= h($latestRound) ?>回</span> ／ 有効予測 <?= count($rows) ?>口</p>
    <?php else: ?>
      <p class="sub">最新の有効予測をデータベースから表示します。</p>
    <?php endif; ?>
  </section>

  <?php if ($error !== null): ?>
    <div class="error"><?= h($error) ?></div>
  <?php elseif (count($rows) === 0): ?>
    <div class="empty">現在、表示できる有効な予測はありません。</div>
  <?php else: ?>
    <section class="grid">
      <?php foreach ($rows as $row): ?>
        <article class="card">
          <div class="card-head">
            <div class="ticket">Ticket <?= h($row['ticket']) ?></div>
            <div class="date">抽せん予定 <?= h($row['target_draw_date_estimate'] ?: '未設定') ?></div>
          </div>

          <div class="balls"><?= number_badges($row['predicted_numbers']) ?></div>

          <div class="meta">
            <div><span class="label">モデル</span><?= h($row['model_version']) ?></div>
            <div><span class="label">基準回</span>第<?= h($row['base_round']) ?>回</div>
            <div><span class="label">予測作成</span><?= h($row['prediction_created_at_jst']) ?></div>
            <div><span class="label">Prediction ID</span><?= h($row['prediction_id']) ?></div>
          </div>

          <?php if ($row['actual_draw_date'] !== null): ?>
            <div class="result ok">
              <strong>結果確定</strong><br>
              本数字的中 <?= h($row['main_hits']) ?> / ボーナス的中 <?= h($row['bonus_hits']) ?>
              <?php if (!empty($row['grade'])): ?> ／ <?= h($row['grade']) ?><?php endif; ?>
              ／ 収支 <?= number_format((int)$row['net_result_yen']) ?>円
            </div>
          <?php else: ?>
            <div class="result pending">結果待ち</div>
          <?php endif; ?>
        </article>
      <?php endforeach; ?>
    </section>
  <?php endif; ?>

  <p class="footer">5分ごとに自動更新します。表示対象はデータベース内の最新回かつ is_active = 1 の予測のみです。</p>
</main>
</body>
</html>
