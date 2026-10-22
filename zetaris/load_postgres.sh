#!/usr/bin/env bash
# Load the synthetic CSVs into a `demo` database on the Zetaris bundle's Postgres so that
# Zetaris can register them as a JDBC datasource (the local platform reads files only from S3).
# Usage: ZETARIS_BUNDLE=../zetaris-platform ./zetaris/load_postgres.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
BUNDLE="${ZETARIS_BUNDLE:-$HERE/../zetaris-platform}"
DATA="$HERE/data/out"
cd "$BUNDLE"
PG="docker compose exec -T postgres psql -U zetaris -v ON_ERROR_STOP=1"
$PG -d metastore -tc "SELECT 1 FROM pg_database WHERE datname='demo'" | grep -q 1 || $PG -d metastore -c "CREATE DATABASE demo"
$PG -d demo <<'SQL'
DROP TABLE IF EXISTS payments, orders, grants, server_logs, mail_events;
CREATE TABLE payments (payment_id text, amount text, currency text, status text, card_last4 text, customer_email text, created_at text);
CREATE TABLE orders (order_id text, payment_id text, email text, reward_key text, amount text, status text, credited text, created_at text, updated_at text);
CREATE TABLE grants (grant_id text, email text, reward_key text, credits text, status text, order_id text, created_at text);
CREATE TABLE server_logs (ts text, route text, order_id text, http_status text, message text);
CREATE TABLE mail_events (email_id text, "to" text, event text, ts text, tag text);
SQL
for t in payments orders grants server_logs mail_events; do
  docker compose exec -T postgres psql -U zetaris -d demo -c "\\copy $t FROM STDIN WITH (FORMAT csv, HEADER true)" < "$DATA/$t.csv"
done
$PG -d demo -c "SELECT (SELECT count(*) FROM payments) payments, (SELECT count(*) FROM orders) orders, (SELECT count(*) FROM grants) grants, (SELECT count(*) FROM server_logs) server_logs, (SELECT count(*) FROM mail_events) mail_events"
