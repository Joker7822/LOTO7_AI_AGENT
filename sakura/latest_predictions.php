<?php
declare(strict_types=1);

ini_set('session.use_strict_mode', '1');
session_set_cookie_params(array(
    'lifetime' => 0,
    'path' => '/',
    'secure' => (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off'),
    'httponly' => true,
    'samesite' => 'Strict'
));
session_start();

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Robots-Tag: noindex, nofollow', true);
header('X-Frame-Options: DENY');
header('X-Content-Type-Options: nosniff');
header('Referrer-Policy: no-referrer');

const VIEW_PASSWORD_HASH = '$2y$12$HFmUIa7fjckS6fI2YqX77OzWr4RRFScJtD3RbtN/NrJsWNTU4jLzK';

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

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['logout'])) {
    $_SESSION = array();
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'] ?? '', $params['secure'], $params['httponly']);
    }
    session_destroy();
    header('Location: ' . strtok($_SERVER['REQUEST_URI'], '?'));
    exit;
}

$loginError = null;
if (empty($_SESSION['loto7_view_authenticated'])) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['password'])) {
        $password = (string)$_POST['password'];
        if (password_verify($password, VIEW_PASSWORD_HASH)) {
            session_regenerate_id(true);
            $_SESSION['loto7_view_authenticated'] = true;
            header('Location: ' . strtok($_SERVER['REQUEST_URI'], '?'));
            exit;
        }
        usleep(500000);
        $loginError = 'パスワードが違います。';
    }

    ?>
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>LOTO7 Login</title>
<style>
:root{--bg:#07111f;--panel:#0d1b2a;--line:rgba(255,255,255,.1);--text:#eef6ff;--muted:#8ca3ba;--cyan:#55e6d7;--danger:#ff8896;--shadow:0 24px 70px rgba(0,0,0,.34)}
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:20px;color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;background:radial-gradient(circle at 15% 0%,rgba(46,123,255,.2),transparent 34%),radial-gradient(circle at 85% 10%,rgba(50,220,199,.13),transparent 30%),linear-gradient(180deg,#07111f 0%,#091521 100%)}
.login{width:min(430px,100%);background:linear-gradient(145deg,rgba(16,38,64,.97),rgba(8,24,41,.97));border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);padding:30px}.eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);font-weight:800}h1{font-size:32px;margin:10px 0 8px}.sub{margin:0 0 24px;color:var(--muted);line-height:1.6}.field{display:grid;gap:8px}.field label{font-size:12px;color:#a9bed0;font-weight:700}.field input{width:100%;border:1px solid var(--line);border-radius:14px;background:#081827;color:var(--text);padding:14px 15px;font-size:16px;outline:none}.field input:focus{border-color:rgba(85,230,215,.65);box-shadow:0 0 0 3px rgba(85,230,215,.1)}button{width:100%;margin-top:14px;border:0;border-radius:14px;padding:14px 16px;background:linear-gradient(135deg,#2979ff,#38cfc1);color:white;font-weight:900;font-size:15px;cursor:pointer}.error{margin-top:14px;padding:11px 12px;border-radius:12px;border:1px solid rgba(255,112,129,.24);background:rgba(255,112,129,.08);color:var(--danger);font-size:13px}.note{margin-top:18px;color:#667f96;font-size:11px;text-align:center}
</style>
</head>
<body>
<form class="login" method="post" autocomplete="off">
  <div class="eyebrow">Private Access</div>
  <h1>LOTO7 最新予測</h1>
  <p class="sub">閲覧するにはパスワードを入力してください。</p>
  <div class="field">
    <label for="password">PASSWORD</label>
    <input id="password" name="password" type="password" required autofocus autocomplete="current-password">
  </div>
  <button type="submit">アクセス</button>
  <?php if ($loginError !== null): ?><div class="error"><?= h($loginError) ?></div><?php endif; ?>
  <div class="note">認証後のみ予測データを表示します</div>
</form>
</body>
</html>
<?php
    exit;
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
*{box-sizing:border-box}body{margin:0;min-height:100vh;color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;background:radial-gradient(circle at 12% 0%,rgba(46,123,255,.17),transparent 30%),radial-gradient(circle at 88% 12%,rgba(50,220,199,.11),transparent 28%),linear-gradient(180deg,#07111f 0%,#091521 100%)}
.wrap{width:min(1080px,calc(100% - 28px));margin:28px auto 56px}.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,rgba(16,38,64,.96),rgba(8,24,41,.96));border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);padding:28px;margin-bottom:18px}.hero:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;right:-80px;top:-120px;background:radial-gradient(circle,rgba(85,230,215,.24),transparent 65%)}
.topline{position:relative;z-index:2;display:flex;align-items:flex-start;justify-content:space-between;gap:16px}.eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);font-weight:800}h1{font-size:clamp(28px,4vw,44px);margin:8px 0 6px;letter-spacing:-.03em}.subtitle{color:var(--muted);margin:0}.latest-round{margin-top:22px;font-size:clamp(24px,4vw,38px);font-weight:900;letter-spacing:-.02em}.logout{position:relative;z-index:3}.logout button{border:1px solid var(--line);border-radius:12px;padding:9px 12px;background:rgba(255,255,255,.05);color:#aac0d4;cursor:pointer;font-weight:700}
.panel{border:1px solid var(--line);border-radius:20px;background:rgba(12,27,42,.88);box-shadow:var(--shadow);overflow:hidden}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:780px}thead th{padding:13px 14px;background:#102238;color:#9eb5cb;font-size:11px;letter-spacing:.07em;text-transform:uppercase;text-align:left;border-bottom:1px solid var(--line)}tbody td{padding:16px 14px;border-bottom:1px solid rgba(255,255,255,.06);vertical-align:middle;font-size:13px}tbody tr:hover{background:rgba(90,167,255,.055)}tbody tr:last-child td{border-bottom:0}
.round{font-size:16px;font-weight:900;white-space:nowrap}.ticket{display:inline-flex;align-items:center;justify-content:center;min-width:38px;height:30px;padding:0 10px;border-radius:999px;background:rgba(90,167,255,.11);border:1px solid rgba(90,167,255,.24);color:#9dccff;font-weight:800}.balls{display:flex;gap:6px;flex-wrap:wrap;min-width:310px}.ball{width:34px;height:34px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#173b62,#102b49);border:1px solid rgba(112,185,255,.35);box-shadow:inset 0 1px 0 rgba(255,255,255,.09),0 4px 12px rgba(0,0,0,.16);color:#dff1ff;font-weight:900}.model{max-width:220px;word-break:break-word;color:#c9d9e8}.date{white-space:nowrap;color:#aac0d4}
.mobile-list{display:none}.card{padding:16px;border-bottom:1px solid var(--line)}.card:last-child{border-bottom:0}.card-top{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:12px}.card-meta{margin-top:12px;color:var(--muted);font-size:12px;display:grid;gap:4px}.empty,.error{padding:28px;color:var(--muted)}.error{color:#ff9ca8}.footer{color:#617990;font-size:11px;text-align:center;margin-top:12px}
@media(max-width:820px){.table-wrap{display:none}.mobile-list{display:block}.wrap{width:min(100% - 16px,1080px);margin-top:10px}.hero{border-radius:18px;padding:20px}.balls{min-width:0}}
@media(max-width:520px){.balls{gap:5px}.ball{width:32px;height:32px;font-size:12px}.topline{display:block}.logout{margin-top:14px}}
</style>
</head>
<body>
<main class="wrap">
  <section class="hero">
    <div class="topline">
      <div>
        <div class="eyebrow">Latest Prediction Round</div>
        <h1>LOTO7 最新予測</h1>
        <p class="subtitle">loto7_predictions の最新回のみ表示</p>
        <div class="latest-round"><?= $latestTargetRound !== null ? h($latestTargetRound) : '—' ?></div>
      </div>
      <form class="logout" method="post"><button type="submit" name="logout" value="1">ログアウト</button></form>
    </div>
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
