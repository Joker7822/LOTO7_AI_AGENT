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
        if ($part === '') {
            continue;
        }
        $html .= '<span class="ball">' . h(str_pad($part, 2, '0', STR_PAD_LEFT)) . '</span>';
    }
    return $html;
}

$configPath = __DIR__ . '/prediction_ingest_config.php';
$error = null;
$latestRound = null;
$rows = array();

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

    $roundStmt = $pdo->query(
        'SELECT MAX(CAST(target_round AS UNSIGNED)) AS latest_round FROM loto7_predictions WHERE is_active = 1'
    );
    $roundRow = $roundStmt->fetch();

    if ($roundRow && $roundRow['latest_round'] !== null) {
        $latestRound = (int)$roundRow['latest_round'];

        $stmt = $pdo->prepare(<<<'SQL'
SELECT p.ticket, p.predicted_numbers
FROM loto7_predictions p
WHERE p.is_active = 1
  AND CAST(p.target_round AS UNSIGNED) = :target_round
  AND NOT EXISTS (
      SELECT 1
      FROM loto7_predictions newer
      WHERE newer.is_active = 1
        AND CAST(newer.target_round AS UNSIGNED) = CAST(p.target_round AS UNSIGNED)
        AND newer.ticket = p.ticket
        AND (
            newer.prediction_created_at_jst > p.prediction_created_at_jst
            OR (
                newer.prediction_created_at_jst = p.prediction_created_at_jst
                AND newer.prediction_id > p.prediction_id
            )
        )
  )
ORDER BY p.ticket ASC
SQL
        );
        $stmt->execute(array(':target_round' => $latestRound));
        $rows = $stmt->fetchAll();
    }
} catch (Throwable $e) {
    error_log('LOTO7 latest predictions view error: ' . $e->getMessage());
    $error = '予測データを取得できませんでした。';
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
* { box-sizing: border-box; }
body {
  margin: 0;
  background: #f6f7f9;
  color: #111827;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans JP", sans-serif;
}
.wrap {
  width: min(760px, calc(100% - 24px));
  margin: 28px auto;
}
.panel {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  overflow: hidden;
}
.header {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
}
h1 {
  margin: 0;
  font-size: 26px;
}
.round {
  margin-top: 6px;
  font-size: 19px;
  font-weight: 800;
  color: #1d4ed8;
}
.row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  border-bottom: 1px solid #eef0f3;
}
.row:last-child { border-bottom: 0; }
.ticket {
  flex: 0 0 42px;
  color: #6b7280;
  font-weight: 700;
}
.balls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.ball {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.message {
  padding: 22px;
  color: #6b7280;
}
.error { color: #b42318; }
.note {
  margin: 10px 4px 0;
  color: #9ca3af;
  font-size: 12px;
}
@media (max-width: 560px) {
  .wrap { margin: 12px auto; width: calc(100% - 14px); }
  .header { padding: 16px; }
  .row { padding: 14px 12px; gap: 8px; }
  .ticket { flex-basis: 34px; }
  .ball { width: 36px; height: 36px; font-size: 14px; }
}
</style>
</head>
<body>
<main class="wrap">
  <section class="panel">
    <header class="header">
      <h1>LOTO7 最新予測</h1>
      <?php if ($latestRound !== null): ?>
        <div class="round">第<?= h($latestRound) ?>回</div>
      <?php endif; ?>
    </header>

    <?php if ($error !== null): ?>
      <div class="message error"><?= h($error) ?></div>
    <?php elseif (count($rows) === 0): ?>
      <div class="message">表示できる予測はありません。</div>
    <?php else: ?>
      <?php foreach ($rows as $row): ?>
        <div class="row">
          <div class="ticket"><?= h($row['ticket']) ?>口</div>
          <div class="balls"><?= number_badges($row['predicted_numbers']) ?></div>
        </div>
      <?php endforeach; ?>
    <?php endif; ?>
  </section>

  <div class="note">最新回のみ表示・5分ごとに自動更新</div>
</main>
</body>
</html>
