CREATE TABLE IF NOT EXISTS loto7_predictions (
  prediction_id VARCHAR(40) PRIMARY KEY,
  prediction_created_at_jst VARCHAR(40) NOT NULL,
  base_round VARCHAR(32) NOT NULL,
  base_draw_date DATE NULL,
  target_round VARCHAR(32) NOT NULL,
  target_draw_date_estimate DATE NULL,
  ticket TINYINT UNSIGNED NOT NULL,
  predicted_numbers VARCHAR(64) NOT NULL,
  model_version VARCHAR(128) NOT NULL,
  git_sha VARCHAR(64) NULL,
  data_sha256 VARCHAR(64) NULL,
  strategy_weights_json JSON NULL,
  synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_target_ticket (target_round, ticket),
  KEY idx_target_round (target_round),
  KEY idx_model_version (model_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS loto7_prediction_results (
  prediction_id VARCHAR(40) PRIMARY KEY,
  result_id VARCHAR(40) NULL,
  target_round VARCHAR(32) NOT NULL,
  ticket TINYINT UNSIGNED NOT NULL,
  actual_draw_date DATE NULL,
  actual_main_numbers VARCHAR(64) NULL,
  actual_bonus_numbers VARCHAR(32) NULL,
  main_hits TINYINT UNSIGNED NULL,
  bonus_hits TINYINT UNSIGNED NULL,
  grade VARCHAR(32) NULL,
  prize_amount_yen INT NOT NULL DEFAULT 0,
  purchase_cost_yen INT NOT NULL DEFAULT 300,
  net_result_yen INT NOT NULL DEFAULT -300,
  model_version VARCHAR(128) NULL,
  synced_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_prediction_result_prediction
    FOREIGN KEY (prediction_id) REFERENCES loto7_predictions(prediction_id)
    ON DELETE CASCADE,
  KEY idx_result_target_round (target_round),
  KEY idx_result_id (result_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
