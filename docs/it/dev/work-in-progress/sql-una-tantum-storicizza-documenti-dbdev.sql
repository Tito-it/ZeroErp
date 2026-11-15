-- Q11 di brief-db-revisione-documenti (Tid, 2026-11-14): correzione A MANO, solo su dbdev.
-- Non e' un changeSet: la macchina e' rimasta indietro rispetto al seed; un'installazione
-- nuova nasce gia' con storicizza = true.
--
-- Come si lancia (come zeroerp_owner, che passa il guard degli standard):
--   set -a; . db/internal.env; set +a
--   psql -X -v ON_ERROR_STOP=1 -f <questo file>
--
-- Effetti collaterali attesi: data_update / user_update / tx_id delle righe toccate cambiano
-- (trigger d'audit); nessun altro trigger guarda la colonna storicizza.

\set ON_ERROR_STOP on
BEGIN;

\echo '--- prima: righe con storicizza = false'
SELECT 'tipi_documento_output'       AS tabella, count(*) FROM documenti.tipi_documento_output       WHERE NOT storicizza
UNION ALL SELECT 'tipi_asset_documento',        count(*) FROM documenti.tipi_asset_documento        WHERE NOT storicizza
UNION ALL SELECT 'tipi_file_documento',         count(*) FROM documenti.tipi_file_documento         WHERE NOT storicizza
UNION ALL SELECT 'render_engine_documento',     count(*) FROM documenti.render_engine_documento     WHERE NOT storicizza
UNION ALL SELECT 'template_documenti',          count(*) FROM documenti.template_documenti          WHERE NOT storicizza
UNION ALL SELECT 'template_documenti_versioni', count(*) FROM documenti.template_documenti_versioni WHERE NOT storicizza
UNION ALL SELECT 'template_asset',              count(*) FROM documenti.template_asset              WHERE NOT storicizza;

UPDATE documenti.tipi_documento_output       SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.tipi_asset_documento        SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.tipi_file_documento         SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.render_engine_documento     SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.template_documenti          SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.template_documenti_versioni SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.template_asset              SET storicizza = true WHERE NOT storicizza;

\echo '--- dopo: deve essere zero ovunque'
SELECT 'tipi_documento_output'       AS tabella, count(*) FROM documenti.tipi_documento_output       WHERE NOT storicizza
UNION ALL SELECT 'tipi_asset_documento',        count(*) FROM documenti.tipi_asset_documento        WHERE NOT storicizza
UNION ALL SELECT 'tipi_file_documento',         count(*) FROM documenti.tipi_file_documento         WHERE NOT storicizza
UNION ALL SELECT 'render_engine_documento',     count(*) FROM documenti.render_engine_documento     WHERE NOT storicizza
UNION ALL SELECT 'template_documenti',          count(*) FROM documenti.template_documenti          WHERE NOT storicizza
UNION ALL SELECT 'template_documenti_versioni', count(*) FROM documenti.template_documenti_versioni WHERE NOT storicizza
UNION ALL SELECT 'template_asset',              count(*) FROM documenti.template_asset              WHERE NOT storicizza;

COMMIT;
