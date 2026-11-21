-- Q11 di brief-db-revisione-documenti (Tid, 2026-11-14): correzione A MANO, solo su dbdev.
-- Non e' un changeSet: la macchina e' rimasta indietro rispetto al seed; un'installazione
-- nuova nasce gia' con storicizza = true.
--
-- Rivisto il 2026-11-17: SQL puro, senza comandi psql (\set, \echo), cosi' gira anche nel
-- Query Tool di pgAdmin. Solo tre tabelle: i quattro vocabolari (tipi_documento_output,
-- tipi_asset_documento, tipi_file_documento, render_engine_documento) hanno perso la colonna
-- storicizza col giro 2 (Q14).
--
-- Come si lancia, come zeroerp_owner (passa il guard degli standard):
--   * pgAdmin: Query Tool sul DB zeroerp, esegui tutto lo script (F5);
--   * psql:    set -a; . db/internal.env; set +a
--              psql -X -v ON_ERROR_STOP=1 -f <questo file>
-- Lo script e' rilanciabile: la seconda volta non tocca nessuna riga.
--
-- Effetti collaterali attesi: data_update / user_update / tx_id delle righe toccate cambiano
-- (trigger d'audit), e lo storico generico registra la riga. Provato su dbdev il 2026-11-17 in
-- una transazione chiusa da ROLLBACK: 10 modelli, 40 versioni, 1 asset, nessun trigger rifiuta.

BEGIN;

UPDATE documenti.template_documenti          SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.template_documenti_versioni SET storicizza = true WHERE NOT storicizza;
UPDATE documenti.template_asset              SET storicizza = true WHERE NOT storicizza;

-- Se resta una riga a false, l'errore annulla tutto prima del COMMIT.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM documenti.template_documenti          WHERE NOT storicizza)
    OR EXISTS (SELECT 1 FROM documenti.template_documenti_versioni WHERE NOT storicizza)
    OR EXISTS (SELECT 1 FROM documenti.template_asset              WHERE NOT storicizza)
    THEN
        RAISE EXCEPTION 'storicizza: restano righe a false, correzione annullata';
    END IF;
END
$$;

COMMIT;

-- Il riepilogo (pgAdmin mostra il risultato dell'ultima istruzione): deve essere zero ovunque.
SELECT 'template_documenti' AS tabella, count(*) FILTER (WHERE NOT storicizza) AS a_false, count(*) AS righe
  FROM documenti.template_documenti
UNION ALL
SELECT 'template_documenti_versioni', count(*) FILTER (WHERE NOT storicizza), count(*)
  FROM documenti.template_documenti_versioni
UNION ALL
SELECT 'template_asset', count(*) FILTER (WHERE NOT storicizza), count(*)
  FROM documenti.template_asset;
