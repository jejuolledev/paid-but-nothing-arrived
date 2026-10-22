-- Zetaris Lightning SQL — one statement per call (run via the JDBC driver or the SQL editor).
-- Registers the five synthetic sources and builds the `order_journey` semantic layer.
--
-- Source layout for the local Docker platform: the synthetic CSVs are loaded into a `demo`
-- database on the bundled Postgres (see zetaris/load_postgres.sh). Zetaris reads them in
-- place over JDBC; nothing is copied into Zetaris. In production each source would be its
-- own system: the PSP ledger (REST), the app database (Postgres), log exports (files on S3),
-- the mail provider (REST) — same SQL for the agent either way.

CREATE DATASOURCE demo_pg DESCRIBE BY "synthetic seller sources (payments, orders, grants, server_logs, mail_events)"
OPTIONS (
  jdbcdriver "org.postgresql.Driver",
  jdbcurl "jdbc:postgresql://postgres:5432/demo",
  username "zetaris",
  password "${POSTGRES_PASSWORD}"
);

REGISTER DATASOURCE TABLES FROM demo_pg;

-- Unified Semantic Layer: how the five tables relate (the keys the agent joins on).
COMPILE USL IF NOT EXISTS order_journey DDL
  CREATE TABLE orders (order_id string, payment_id string, email string, reward_key string, amount string, status string, credited string, created_at string, updated_at string, CONSTRAINT pk_orders PRIMARY KEY (order_id));
  CREATE TABLE payments (payment_id string, amount string, currency string, status string, card_last4 string, customer_email string, created_at string, CONSTRAINT pk_payments PRIMARY KEY (payment_id), CONSTRAINT fk_pay_order FOREIGN KEY (payment_id) REFERENCES orders(payment_id));
  CREATE TABLE grants (grant_id string, email string, reward_key string, credits string, status string, order_id string, created_at string, CONSTRAINT pk_grants PRIMARY KEY (grant_id), CONSTRAINT fk_grant_order FOREIGN KEY (order_id) REFERENCES orders(order_id));
  CREATE TABLE server_logs (ts string, route string, order_id string, http_status string, message string, CONSTRAINT fk_log_order FOREIGN KEY (order_id) REFERENCES orders(order_id));
  CREATE TABLE mail_events (email_id string, "to" string, event string, ts string, tag string, CONSTRAINT fk_mail_order FOREIGN KEY (tag) REFERENCES orders(order_id));

ACTIVATE USL TABLE order_journey.orders AS SELECT * FROM demo_pg.orders;
ACTIVATE USL TABLE order_journey.payments AS SELECT * FROM demo_pg.payments;
ACTIVATE USL TABLE order_journey.grants AS SELECT * FROM demo_pg.grants;
ACTIVATE USL TABLE order_journey.server_logs AS SELECT * FROM demo_pg.server_logs;
ACTIVATE USL TABLE order_journey.mail_events AS SELECT * FROM demo_pg.mail_events;

-- Smoke test: the join the agent relies on.
SELECT o.order_id, o.status, p.status AS psp_status, g.grant_id
FROM order_journey.orders o
LEFT JOIN order_journey.payments p ON p.payment_id = o.payment_id
LEFT JOIN order_journey.grants g ON g.order_id = o.order_id
WHERE o.order_id IN ('ord_0901','ord_0902','ord_0903','ord_0904','ord_0905');
