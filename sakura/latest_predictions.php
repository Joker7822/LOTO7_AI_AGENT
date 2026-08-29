<?php
declare(strict_types=1);

header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-store, no-cache, must-revalidate, max-age=0');
header('Pragma: no-cache');
header('X-Robots-Tag: noindex, nofollow', true);

function h($value) {
    return htmlspecialchars((string)$value, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

function round_number($value) {
    if (preg_match('/(\d+)/u', (string)$value, $m)) {
        return (int)$m[1];
    }
    return 0;
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
$totalCount = 0;
$activeCount = 0;
$inactiveCount = 0;
$latestRound = null;

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

    $rows = $pdo->query(<<<'SQL'
SELECT
    prediction_created_at_jst,
    target_round,
    target_draw_date_estimate,
    ticket,
    predicted_numbers,
    model_version,
    is_active
FROM loto7_predictions
ORDER BY
    CAST(REPLACE(REPLACE(target_round, '第', ''), '回', '') AS UNSIGNED) DESC,
    ticket ASC,
    prediction_created_at_jst DESC
SQL
    )->fetchAll();

    $totalCount = count($rows);
    foreach ($rows as $row) {
        if ((int)$row['is_active'] === 1) {
            $activeCount++;
        } else {
            $inactiveCount++;
        }
        $round = round_number($row['target_round']);
        if ($latestRound === null || $round > $latestRound) {
            $latestRound = $round;
        }
    }
} catch (Throwable $e) {
    error_log('LOTO7 predictions view error: ' . $e->getMessage());
    $error = 'loto7_predictions を取得できませんでした。';
}
?>
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="300">
<title>LOTO7 Predictions</title>
<style>
:root{
  --bg:#07111f;--panel:#0d1b2a;--line:rgba(255,255,255,.09);--text:#eef6ff;
  --muted:#8ca3ba;--blue:#5aa7ff;--cyan:#55e6d7;--green:#55d98d;--red:#ff7081;
  --shadow:0 24px 70px rgba(0,0,0,.28);
}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans JP",sans-serif;background:radial-gradient(circle at 12% 0%,rgba(46,123,255,.17),transparent 30%),radial-gradient(circle at 88% 12%,rgba(50,220,199,.11),transparent 28%),linear-gradient(180deg,#07111f 0%,#091521 100%)}
.wrap{width:min(1280px,calc(100% - 28px));margin:28px auto 56px}
.hero{position:relative;overflow:hidden;background:linear-gradient(135deg,rgba(16,38,64,.96),rgba(8,24,41,.96));border:1px solid var(--line);border-radius:24px;box-shadow:var(--shadow);padding:28px}
.hero:after{content:"";position:absolute;width:260px;height:260px;border-radius:50%;right:-80px;top:-120px;background:radial-gradient(circle,rgba(85,230,215,.24),transparent 65%)}
.eyebrow{font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--cyan);font-weight:800}
h1{font-size:clamp(28px,4vw,44px);margin:8px 0 6px;letter-spacing:-.03em}.subtitle{color:var(--muted);margin:0}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:24px}.stat{background:rgba(255,255,255,.045);border:1px solid var(--line);border-radius:16px;padding:16px}.stat-label{font-size:12px;color:var(--muted);margin-bottom:6px}.stat-value{font-size:25px;font-weight:900}.active-color{color:var(--green)}.inactive-color{color:var(--red)}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:18px 0 12px}.search{flex:1 1 320px}.search input,.toolbar select{width:100%;appearance:none;color:var(--text);background:#0d1d2c;border:1px solid var(--line);border-radius:14px;padding:13px 14px;outline:none}.search input:focus,.toolbar select:focus{border-color:rgba(90,167,255,.7);box-shadow:0 0 0 3px rgba(90,167,255,.11)}.toolbar select{width:auto;min-width:145px}
.panel{border:1px solid var(--line);border-radius:20px;background:rgba(12,27,42,.88);box-shadow:var(--shadow);overflow:hidden}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:930px}thead th{padding:13px 14px;background:#102238;color:#9eb5cb;font-size:11px;letter-spacing:.07em;text-transform:uppercase;text-align:left;border-bottom:1px solid var(--line)}tbody td{padding:16px 14px;border-bottom:1px solid rgba(255,255,255,.06);vertical-align:middle;font-size:13px}tbody tr{transition:background .18s ease}tbody tr:hover{background:rgba(90,167,255,.055)}tbody tr.latest{background:linear-gradient(90deg,rgba(90,167,255,.06),transparent 70%)}tbody tr:last-child td{border-bottom:0}
.round{font-size:16px;font-weight:900;white-space:nowrap}.ticket{display:inline-flex;align-items:center;justify-content:center;min-width:38px;height:30px;padding:0 10px;border-radius:999px;background:rgba(90,167,255,.11);border:1px solid rgba(90,167,255,.24);color:#9dccff;font-weight:800}.balls{display:flex;gap:6px;flex-wrap:wrap;min-width:310px}.ball{width:34px;height:34px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;background:linear-gradient(145deg,#173b62,#102b49);border:1px solid rgba(112,185,255,.35);box-shadow:inset 0 1px 0 rgba(255,255,255,.09),0 4px 12px rgba(0,0,0,.16);color:#dff1ff;font-weight:900}.status{display:inline-flex;align-items:center;gap:7px;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:900;white-space:nowrap}.status:before{content:"";width:7px;height:7px;border-radius:50%}.status.active{background:rgba(85,217,141,.10);color:#8bf0b4;border:1px solid rgba(85,217,141,.22)}.status.active:before{background:var(--green);box-shadow:0 0 10px rgba(85,217,141,.75)}.status.inactive{background:rgba(255,112,129,.09);color:#ff9ca8;border:1px solid rgba(255,112,129,.20)}.status.inactive:before{background:var(--red)}.model{max-width:220px;word-break:break-word;color:#c9d9e8}.date{white-space:nowrap;color:#aac0d4}
.mobile-list{display:none}.card{padding:16px;border-bottom:1px solid var(--line)}.card:last-child{border-bottom:0}.card-top{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:12px}.card-meta{margin-top:12px;color:var(--muted);font-size:12px;display:grid;gap:4px}.empty,.error{padding:28px;color:var(--muted)}.error{color:#ff9ca8}.footer{color:#617990;font-size:11px;text-align:center;margin-top:12px}.hide{display:none!important}
@media(max-width:900px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.table-wrap{display:none}.mobile-list{display:block}.wrap{width:min(100% - 16px,1280px);margin-top:10px}.hero{border-radius:18px;padding:20px}.toolbar select{flex:1}}
@media(max-width:520px){.stats{grid-template-columns:1fr 1fr}.stat{padding:12px}.stat-value{font-size:21px}.balls{min-width:0;gap:5px}.ball{width:32px;height:32px;font-size:12px}}
</style>
</head>
<body>
<main class="wrap">
  <section class="hero">
    <div class="eyebrow">Prediction Board</div>
    <h1>LOTO7 Predictions</h1>
    <p class="subtitle">予測データをシンプルに一覧表示</p>
    <div class="stats">
      <div class="stat"><div class="stat-label">総レコード</div><div class="stat-value"><?= h($totalCount) ?></div></div>
      <div class="stat"><div class="stat-label">有効</div><div class="stat-value active-color"><?= h($activeCount) ?></div></div>
      <div class="stat"><div class="stat-label">無効</div><div class="stat-value inactive-color"><?= h($inactiveCount) ?></div></div>
      <div class="stat"><div class="stat-label">最新対象回</div><div class="stat-value"><?= $latestRound !== null ? '第' . h($latestRound) . '回' : '—' ?></div></div>
    </div>
  </section>

  <?php if ($error !== null): ?>
    <section class="panel" style="margin-top:18px"><div class="error"><?= h($error) ?></div></section>
  <?php else: ?>
    <div class="toolbar">
      <div class="search"><input id="searchBox" type="search" placeholder="回・予測番号・モデルを検索…" autocomplete="off"></div>
      <select id="statusFilter"><option value="all">すべての状態</option><option value="active">有効のみ</option><option value="inactive">無効のみ</option></select>
      <select id="roundFilter">
        <option value="all">すべての回</option>
        <?php $seenRounds=array(); foreach($rows as $r){$rn=round_number($r['target_round']);if($rn>0)$seenRounds[$rn]=true;} krsort($seenRounds); foreach(array_keys($seenRounds) as $rn): ?>
          <option value="<?= h($rn) ?>">第<?= h($rn) ?>回</option>
        <?php endforeach; ?>
      </select>
    </div>

    <section class="panel">
      <?php if (count($rows) === 0): ?>
        <div class="empty">表示できる予測データがありません。</div>
      <?php else: ?>
        <div class="table-wrap">
          <table>
            <thead><tr><th>対象回</th><th>口</th><th>予測番号</th><th>状態</th><th>抽せん予定日</th><th>モデル</th><th>作成日時</th></tr></thead>
            <tbody>
            <?php foreach ($rows as $row): $rn=round_number($row['target_round']); $active=(int)$row['is_active']===1; $searchText=mb_strtolower(implode(' ',array($row['target_round'],$row['predicted_numbers'],$row['model_version'])),'UTF-8'); ?>
              <tr class="filter-row <?= ($latestRound!==null && $rn===$latestRound)?'latest':'' ?>" data-status="<?= $active?'active':'inactive' ?>" data-round="<?= h($rn) ?>" data-search="<?= h($searchText) ?>">
                <td><span class="round"><?= h($row['target_round']) ?></span></td>
                <td><span class="ticket"><?= h($row['ticket']) ?>口</span></td>
                <td><div class="balls"><?= number_badges($row['predicted_numbers']) ?></div></td>
                <td><span class="status <?= $active?'active':'inactive' ?>"><?= $active?'ACTIVE':'INVALID' ?></span></td>
                <td class="date"><?= h($row['target_draw_date_estimate'] ?: '—') ?></td>
                <td class="model"><?= h($row['model_version'] ?: '—') ?></td>
                <td class="date"><?= h($row['prediction_created_at_jst'] ?: '—') ?></td>
              </tr>
            <?php endforeach; ?>
            </tbody>
          </table>
        </div>

        <div class="mobile-list">
          <?php foreach ($rows as $row): $rn=round_number($row['target_round']); $active=(int)$row['is_active']===1; $searchText=mb_strtolower(implode(' ',array($row['target_round'],$row['predicted_numbers'],$row['model_version'])),'UTF-8'); ?>
            <article class="card filter-row" data-status="<?= $active?'active':'inactive' ?>" data-round="<?= h($rn) ?>" data-search="<?= h($searchText) ?>">
              <div class="card-top"><div><div class="round"><?= h($row['target_round']) ?></div><div style="margin-top:5px"><span class="ticket"><?= h($row['ticket']) ?>口</span></div></div><span class="status <?= $active?'active':'inactive' ?>"><?= $active?'ACTIVE':'INVALID' ?></span></div>
              <div class="balls"><?= number_badges($row['predicted_numbers']) ?></div>
              <div class="card-meta"><div>抽せん予定：<?= h($row['target_draw_date_estimate'] ?: '—') ?></div><div>モデル：<?= h($row['model_version'] ?: '—') ?></div><div>作成：<?= h($row['prediction_created_at_jst'] ?: '—') ?></div></div>
            </article>
          <?php endforeach; ?>
        </div>
      <?php endif; ?>
    </section>
  <?php endif; ?>
  <div class="footer">5分ごとに自動更新</div>
</main>
<script>
(function(){const search=document.getElementById('searchBox'),status=document.getElementById('statusFilter'),round=document.getElementById('roundFilter');if(!search||!status||!round)return;function apply(){const q=search.value.trim().toLowerCase(),s=status.value,r=round.value;document.querySelectorAll('.filter-row').forEach(function(row){const okQ=!q||(row.dataset.search||'').includes(q),okS=s==='all'||row.dataset.status===s,okR=r==='all'||row.dataset.round===r;row.classList.toggle('hide',!(okQ&&okS&&okR));});}search.addEventListener('input',apply);status.addEventListener('change',apply);round.addEventListener('change',apply);})();
</script>
</body>
</html>
