<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');

function fail_json(int $status, string $message): never {
    http_response_code($status);
    echo json_encode(['ok' => false, 'error' => $message], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    fail_json(405, 'POST required');
}

$configPath = __DIR__ . '/prediction_ingest_config.php';
if (!is_file($configPath)) {
    fail_json(500, 'server config missing');
}
$config = require $configPath;

$raw = file_get_contents('php://input');
if ($raw === false || $raw === '' || strlen($raw) > 1048576) {
    fail_json(400, 'invalid request body');
}

$timestamp = $_SERVER['HTTP_X_LOTO7_TIMESTAMP'] ?? '';
$signature = $_SERVER['HTTP_X_LOTO7_SIGNATURE'] ?? '';
if (!ctype_digit($timestamp) || !preg_match('/^[a-f0-9]{64}$/', $signature)) {
    fail_json(401, 'missing signature');
}
$maxSkew = (int)($config['max_clock_skew_seconds'] ?? 300);
if (abs(time() - (int)$timestamp) > $maxSkew) {
    fail_json(401, 'stale request');
}
$expected = hash_hmac('sha256', $timestamp . '.' . $raw, (string)$config['hmac_secret']);
if (!hash_equals($expected, $signature)) {
    fail_json(401, 'bad signature');
}

$payload = json_decode($raw, true);
if (!is_array($payload) || ($payload['schema_version'] ?? '') !== 'loto7-db-sync-v1') {
    fail_json(400, 'unsupported payload');
}
$predictions = $payload['predictions'] ?? [];
$results = $payload['results'] ?? [];
if (!is_array($predictions) || !is_array($results)) {
    fail_json(400, 'invalid rows');
}

try {
    $pdo = new PDO(
        (string)$config['db_dsn'],
        (string)$config['db_user'],
        (string)$config['db_password'],
        [
            PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
            PDO::ATTR_EMULATE_PREPARES => false,
        ]
    );
    $pdo->beginTransaction();

    $predictionSql = <<<'SQL'
INSERT INTO loto7_predictions (
  prediction_id, prediction_created_at_jst, base_round, base_draw_date,
  target_round, target_draw_date_estimate, ticket, predicted_numbers,
  model_version, git_sha, data_sha256, strategy_weights_json,
  is_active, invalidated_at_jst, invalidation_reason
) VALUES (
  :prediction_id, :prediction_created_at_jst, :base_round, :base_draw_date,
  :target_round, :target_draw_date_estimate, :ticket, :predicted_numbers,
  :model_version, :git_sha, :data_sha256, :strategy_weights_json,
  :is_active, :invalidated_at_jst, :invalidation_reason
)
ON DUPLICATE KEY UPDATE
  prediction_created_at_jst=VALUES(prediction_created_at_jst),
  base_round=VALUES(base_round), base_draw_date=VALUES(base_draw_date),
  target_round=VALUES(target_round), target_draw_date_estimate=VALUES(target_draw_date_estimate),
  ticket=VALUES(ticket), predicted_numbers=VALUES(predicted_numbers),
  model_version=VALUES(model_version), git_sha=VALUES(git_sha),
  data_sha256=VALUES(data_sha256), strategy_weights_json=VALUES(strategy_weights_json),
  is_active=VALUES(is_active), invalidated_at_jst=VALUES(invalidated_at_jst),
  invalidation_reason=VALUES(invalidation_reason)
SQL;
    $predictionStmt = $pdo->prepare($predictionSql);

    foreach ($predictions as $row) {
        if (!is_array($row) || empty($row['prediction_id']) || empty($row['target_round'])) {
            throw new RuntimeException('invalid prediction row');
        }
        $predictionStmt->execute([
            ':prediction_id' => (string)$row['prediction_id'],
            ':prediction_created_at_jst' => (string)($row['prediction_created_at_jst'] ?? ''),
            ':base_round' => (string)($row['base_round'] ?? ''),
            ':base_draw_date' => $row['base_draw_date'] ?: null,
            ':target_round' => (string)$row['target_round'],
            ':target_draw_date_estimate' => $row['target_draw_date_estimate'] ?: null,
            ':ticket' => (int)($row['ticket'] ?? 0),
            ':predicted_numbers' => (string)($row['predicted_numbers'] ?? ''),
            ':model_version' => (string)($row['model_version'] ?? ''),
            ':git_sha' => $row['git_sha'] ?: null,
            ':data_sha256' => $row['data_sha256'] ?: null,
            ':strategy_weights_json' => json_encode($row['strategy_weights'] ?? new stdClass(), JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
            ':is_active' => !empty($row['is_active']) ? 1 : 0,
            ':invalidated_at_jst' => $row['invalidated_at_jst'] ?: null,
            ':invalidation_reason' => $row['invalidation_reason'] ?: null,
        ]);
    }

    $resultSql = <<<'SQL'
INSERT INTO loto7_prediction_results (
  prediction_id, result_id, target_round, ticket, actual_draw_date,
  actual_main_numbers, actual_bonus_numbers, main_hits, bonus_hits,
  grade, prize_amount_yen, purchase_cost_yen, net_result_yen, model_version
) VALUES (
  :prediction_id, :result_id, :target_round, :ticket, :actual_draw_date,
  :actual_main_numbers, :actual_bonus_numbers, :main_hits, :bonus_hits,
  :grade, :prize_amount_yen, :purchase_cost_yen, :net_result_yen, :model_version
)
ON DUPLICATE KEY UPDATE
  result_id=VALUES(result_id), target_round=VALUES(target_round), ticket=VALUES(ticket),
  actual_draw_date=VALUES(actual_draw_date), actual_main_numbers=VALUES(actual_main_numbers),
  actual_bonus_numbers=VALUES(actual_bonus_numbers), main_hits=VALUES(main_hits),
  bonus_hits=VALUES(bonus_hits), grade=VALUES(grade), prize_amount_yen=VALUES(prize_amount_yen),
  purchase_cost_yen=VALUES(purchase_cost_yen), net_result_yen=VALUES(net_result_yen),
  model_version=VALUES(model_version)
SQL;
    $resultStmt = $pdo->prepare($resultSql);

    foreach ($results as $row) {
        if (!is_array($row) || empty($row['prediction_id']) || empty($row['target_round'])) {
            throw new RuntimeException('invalid result row');
        }
        $resultStmt->execute([
            ':prediction_id' => (string)$row['prediction_id'],
            ':result_id' => $row['result_id'] ?: null,
            ':target_round' => (string)$row['target_round'],
            ':ticket' => (int)($row['ticket'] ?? 0),
            ':actual_draw_date' => $row['actual_draw_date'] ?: null,
            ':actual_main_numbers' => $row['actual_main_numbers'] ?: null,
            ':actual_bonus_numbers' => $row['actual_bonus_numbers'] ?: null,
            ':main_hits' => isset($row['main_hits']) ? (int)$row['main_hits'] : null,
            ':bonus_hits' => isset($row['bonus_hits']) ? (int)$row['bonus_hits'] : null,
            ':grade' => $row['grade'] ?: null,
            ':prize_amount_yen' => (int)($row['prize_amount_yen'] ?? 0),
            ':purchase_cost_yen' => (int)($row['purchase_cost_yen'] ?? 300),
            ':net_result_yen' => (int)($row['net_result_yen'] ?? -300),
            ':model_version' => $row['model_version'] ?: null,
        ]);
    }

    $pdo->commit();
    echo json_encode([
        'ok' => true,
        'predictions_upserted' => count($predictions),
        'results_upserted' => count($results),
    ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo instanceof PDO && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    error_log('LOTO7 ingest error: ' . $e->getMessage());
    fail_json(500, 'database write failed');
}
