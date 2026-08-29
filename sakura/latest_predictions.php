<?php
declare(strict_types=1);

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Robots-Tag: noindex, nofollow', true);

function h($value) {
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function number_badges($numbers) {
    $parts = preg_split('/[\s,\-]+/', trim((string)$numbers));
    $html = '';
    foreach ($parts as $part) {
        if ($part === '') continue;
        $html .= '<span class="ball">' . h(str_pad($part, 2, '0', STR_PAD_LEFT)) . '</span>';
    }
    return $html;
}

$configPath = __DIR__ . '/prediction_ingest_config.php';
$error = null;
$rows = array();
$latestTargetRound = null;

try {
    if (!is_file($configPath)) {
        throw new RuntimeException('DB config missing');
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

    $latestStmt = $pdo->query(<<<'SQL'
SELECT target_round
FROM loto7_predictions
WHERE target_round IS NOT NULL AND target_round <> ''
ORDER BY
    CAST(REPLACE(REPLACE(target_round, '第', ''), '回', '') AS UNSIGNED) DESC,
    target_draw_date_estimate DESC,
    prediction_created_at_jst DESC
LIMIT 1
SQL
    );
    $latestRow = $latestStmt->fetch();

    if ($latestRow && !empty($latestRow['target_round'])) {
        $latestTargetRound = (string)$latestRow['target_round'];

        $stmt = $pdo->prepare(<<<'SQL'
SELECT
    prediction_created_at_jst,
    target_round,
    target_draw_date_estimate,
    ticket,
    predicted_numbers,
    model_version
FROM loto7_predictions
WHERE target_round = :target_round
ORDER BY ticket ASC, prediction_created_at_jst DESC
SQL
        );
        $stmt->execute(array(':target_round' => $latestTargetRound));
        $rows = $stmt->fetchAll();
    }
} catch (Throwable $e) {
    error_log('LOTO7 latest predictions view error: ' . $e->getMessage());
    $error = 'loto7_predictions を取得できませんでした。';
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
:root{--bg:#07111f;--panel:#0d1b2a;--line:rgba(255,255,255,.09);--text:#eef6ff;--muted:#8ca3ba;--cyan:#55e6d7;--shadow:0 24px 70px rgba(0,0,0,.28)}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;background:radial-gradient(circle at 12% 0%,rgba(46,123,255,.17),transparent 30%),radial-gradient(circle at 88% 12%,rgba(50,220,199,.11),transparent 28%),linear-gradient(180deg,#07111f 0%,#091521 100%)}
.wrap{width:min(1080px,calc(100% - 28px));margin:28px auto 56px}
.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,rgba(16,38,64,.96),rgba(8,24,41,.96));border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);padding:28px;margin-bottom:18px}
.hero:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;right:-80px;top:-120px;background:radial-gradient(circle,rgba(85,230,215,.24),transparent 65%)}
.eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);font-weight:800}
h1{font-size:clamp(28px,4vw,44px);margin:8px 0 6px;letter-spacing:-.03em}.subtitle{color:var(--muted);margin:0}.latest-round{margin-top:22px;font-size:clamp(24px,4vw,38px);font-weight:900;letter-spacing:-.02em}
.panel{border:1px solid var(--line);border-radius:20px;background:rgba(12,27,42,.88);box-shadow:var(--shadow);overflow:hidden}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:780px}thead th{padding:13px 14px;background:#102238;color:#9eb5cb;font-size:11px;letter-spacing:.07em;text-transform:uppercase;text-align:left;border-bottom:1px solid var(--line)}tbody td{padding:16px 14px;border-bottom:1px solid rgba(255,255,255,.06);vertical-align:middle;font-size:13px}tbody tr:hover{background:rgba(90,167,255,.055)}tbody tr:last-child td{border-bottom:0}
.round{font-size:16px;font-weight:900;white-space:nowrap}.ticket{display:inline-flex;align-items:center;justify-content:center;min-width:38px;height:30px;padding:0 10px;border-radius:999px;background:rgba(90,167,255,.11);border:1px solid rgba(90,167,255,.24);color:#9dccff;font-weight:800}.balls{display:flex;gap:6px;flex-wrap:wrap;min-width:310px}.ball{width:34px;height:34px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#173b62,#102b49);border:1px solid rgba(112,185,255,.35);box-shadow:inset 0 1px 0 rgba(255,255,255,.09),0 4px 12px rgba(0,0,0,.16);color:#dff1ff;font-weight:900}.model{max-width:220px;word-break:break-word;color:#c9d9e8}.date{white-space:nowrap;color:#aac0d4}
.mobile-list{display:none}.card{padding:16px;border-bottom:1px solid var(--line)}.card:last-child{border-bottom:0}.card-top{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:12px}.card-meta{margin-top:12px;color:var(--muted);font-size:12px;display:grid;gap:4px}.empty,.error{padding:28px;color:var(--muted)}.error{color:#ff9ca8}.footer{color:#617990;font-size:11px;text-align:center;margin-top:12px}
@media(max-width:820px){.table-wrap{display:none}.mobile-list{display:block}.wrap{width:min(100% - 16px,1080px);margin-top:10px}.hero{border-radius:18px;padding:20px}.balls{min-width:0}}
@media(max-width:520px){.balls{gap:5px}.ball{width:32px;height:32px;font-size:12px}}
</style>
</head>
<body>
<main class="wrap">
  <section class="hero">
    <div class="eyebrow">Latest Prediction Round</div>
    <h1>LOTO7 最新予測</h1>
    <p class="subtitle">loto7_predictions の最新回のみ表示</p>
    <div class="latest-round"><?= $latestTargetRound !== null ? h($latestTargetRound) : '—' ?></div>
  </section>

  <?php if ($error !== null): ?>
    <section class="panel"><div class="error"><?= h($error) ?></div></section>
  <?php else: ?>
    <section class="panel">
      <?php if (count($rows) === 0): ?>
        <div class="empty">最新回の予測データがありません。</div>
      <?php else: ?>
        <div class="table-wrap">
          <table>
            <thead><tr><th>対象回</th><th>口</th><th>予測番号</th><th>抽せん予定日</th><th>モデル</th><th>作成日時</th></tr></thead>
            <tbody>
            <?php foreach ($rows as $row): ?>
              <tr>
                <td><span class="round"><?= h($row['target_round']) ?></span></td>
                <td><span class="ticket"><?= h($row['ticket']) ?>口</span></td>
                <td><div class="balls"><?= number_badges($row['predicted_numbers']) ?></div></td>
                <td class="date"><?= h($row['target_draw_date_estimate'] ?: '—') ?></td>
                <td class="model"><?= h($row['model_version'] ?: '—') ?></td>
                <td class="date"><?= h($row['prediction_created_at_jst'] ?: '—') ?></td>
              </tr>
            <?php endforeach; ?>
            </tbody>
          </table>
        </div>

        <div class="mobile-list">
          <?php foreach ($rows as $row): ?>
            <article class="card">
              <div class="card-top"><div><div class="round"><?= h($row['target_round']) ?></div><div style="margin-top:5px"><span class="ticket"><?= h($row['ticket']) ?>口</span></div></div></div>
              <div class="balls"><?= number_badges($row['predicted_numbers']) ?></div>
              <div class="card-meta"><div>抽せん予定：<?= h($row['target_draw_date_estimate'] ?: '—') ?></div><div>モデル：<?= h($row['model_version'] ?: '—') ?></div><div>作成：<?= h($row['prediction_created_at_jst'] ?: '—') ?></div></div>
            </article>
          <?php endforeach; ?>
        </div>
      <?php endif; ?>
    </section>
  <?php endif; ?>
  <div class="footer">最新対象回のみ・5分ごとに自動更新</div>
</main>
</body>
</html>
