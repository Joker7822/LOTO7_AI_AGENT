# Sakura Internet DB bridge

This directory contains the server-side bridge used to persist canonical LOTO7 Production predictions and reconciliation results into Sakura Internet MySQL.

## Why an HTTPS bridge

Sakura Rental Server does not accept MySQL connections from external hosts. GitHub Actions therefore sends a signed HTTPS JSON payload to `prediction_ingest.php`, and the PHP endpoint performs the MySQL writes from inside Sakura's server environment.

## Setup

1. Create a MySQL database in Sakura's control panel.
2. Apply `sql/schema.sql` using phpMyAdmin or the mysql command on Sakura.
3. Copy `prediction_ingest.php` and `prediction_ingest_config.php.example` to a non-publicly-listed directory under your Sakura web space.
4. Rename the example config to `prediction_ingest_config.php` and fill in the DB settings and a long random HMAC secret.
5. Protect the config file from direct HTTP access. The sample endpoint loads it server-side only.
6. In GitHub repository Actions secrets, add:
   - `SAKURA_PREDICTION_API_URL` — HTTPS URL of `prediction_ingest.php`
   - `SAKURA_PREDICTION_HMAC_SECRET` — same secret as the PHP config
7. Run the `Sync Production Predictions to Sakura DB` workflow once manually. Afterwards it runs when canonical prediction/reconciliation CSV files change.

## Security

The request body is authenticated with `HMAC-SHA256(secret, timestamp + "." + raw_body)`. The endpoint rejects stale timestamps (>5 minutes), bad signatures, non-POST methods, oversized payloads, and unsupported operations. SQL uses PDO prepared statements.

The GitHub workflow does not contain DB credentials. Only the HTTPS endpoint URL and HMAC secret are stored as GitHub Actions secrets.
