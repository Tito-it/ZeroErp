-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: coerenza tx_id — dbops.fn_get_or_create_session_tx_id
--       + dbops.trgfn_tx_id_managed (ramo "id non registrato")
-- Brief: brief-db-coerenza-tx-id-non-registrato.md §5.1
-- ------------------------------------------------------------
-- Indice test
--  1) Senza canale di log: la funzione ritorna la sentinella uuid_nil
--  2) Senza canale: la GUC dbops.tx_id NON viene pubblicata (niente id fantasma)
--  3) Senza canale: INSERT su tabella tracciata RIESCE (riproduce il caso CI)
--  4) Senza canale: il tx_id scritto e' uuid_nil
--  5) GUC forzata a un id NON registrato: l'INSERT non solleva (era il blocco)
--  6) Non-regressione: con bypass attivo l'INSERT riesce
--  7) Canale attivo (skip condizionale): l'id ritornato e' registrato
-- ------------------------------------------------------------
-- COSA PRESIDIA QUESTO FILE
-- Il difetto originale: fn_get_or_create_session_tx_id, senza canale dblink,
-- generava un uuidv7() NON registrato in dbops.transaction_ids e lo pubblicava
-- nella GUC dbops.tx_id con scope di SESSIONE. Il trigger trgfn_tx_id_managed
-- poi non lo trovava nel registro e SOLLEVAVA. Poiche' Liquibase usa una sola
-- connessione, la prima scrittura tracciata avvelenava tutta la run.
--
-- Sintomo reale (CI "standard no provision", 2026-07-22): fallimento del seed
-- 80_data/20260720-10 su dbops.coda_lavori_tipi con W_TXID_NOT_REGISTERED.
-- I test 3 e 5 sono la riproduzione diretta di quel fallimento.
-- ------------------------------------------------------------
BEGIN;
SELECT plan(7);

-- Scope univoco: la tabella ha UNIQUE su codice.
CREATE TEMP TABLE tmp_costanti_txid AS
SELECT ('PGTAP_TXID_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS scope;

-- ------------------------------------------------------------
-- Scenario A — nessun canale di log.
-- connstring vuota => ramo di ripiego (a), deterministico e indipendente
-- dall'ambiente (in CI la GUC non c'e', in dev potrebbe esserci).
-- dbops.tx_id vuota => la funzione non riusa un id di sessione preesistente.
-- ------------------------------------------------------------
SET LOCAL myapp.dblink_log_connection = '';
SET LOCAL dbops.tx_id = '';

SELECT is(
  dbops.fn_get_or_create_session_tx_id(),
  script.uuid_nil(),
  '1) Senza canale: la funzione ritorna la sentinella uuid_nil'
);

-- Il cuore della correzione: nessun id fantasma pubblicato in sessione.
SELECT is(
  coalesce(current_setting('dbops.tx_id', true), ''),
  '',
  '2) Senza canale: la GUC dbops.tx_id NON viene pubblicata'
);

SELECT lives_ok(
  format(
    $q$ INSERT INTO dbops.coda_lavori_tipi
          (codice, handler_code, descrizione, run_as_default, max_tentativi_default, attivo)
        VALUES (%L, %L, 'pgTAP coerenza tx_id', 'OPERATORE', 3, TRUE) $q$,
    (SELECT scope || '_A' FROM tmp_costanti_txid),
    'pgtap_handler_txid'
  ),
  '3) Senza canale: INSERT su tabella tracciata riesce (riproduce il caso CI)'
);

SELECT is(
  (SELECT t.tx_id FROM dbops.coda_lavori_tipi t
    WHERE t.codice = (SELECT scope || '_A' FROM tmp_costanti_txid)),
  script.uuid_nil(),
  '4) Senza canale: il tx_id scritto e'' uuid_nil'
);

-- ------------------------------------------------------------
-- Scenario B — GUC forzata a un id NON registrato.
-- Simula una sessione gia' avvelenata (o una GUC impostata a mano). Prima della
-- correzione questo INSERT sollevava W_TXID_NOT_REGISTERED e da li' in poi
-- falliva tutto; ora deve solo avvertire e proseguire.
--
-- NB: il tx_id scritto sara' l'id della GUC, non uuid_nil: la COALESCE finale
-- del trigger preferisce current_setting('dbops.tx_id') a v_new_tx_id. E' una
-- residua discrepanza con la guida ("assegna nil"), innocua dopo lo step 1
-- perche' la GUC puo' contenere solo id registrati. Vedi §4.2 del brief.
-- ------------------------------------------------------------
SET LOCAL dbops.tx_id = '11111111-1111-4111-8111-111111111111';

SELECT lives_ok(
  format(
    $q$ INSERT INTO dbops.coda_lavori_tipi
          (codice, handler_code, descrizione, run_as_default, max_tentativi_default, attivo)
        VALUES (%L, %L, 'pgTAP coerenza tx_id', 'OPERATORE', 3, TRUE) $q$,
    (SELECT scope || '_B' FROM tmp_costanti_txid),
    'pgtap_handler_txid'
  ),
  '5) GUC con id NON registrato: l''INSERT non solleva (prima era il blocco)'
);

-- ------------------------------------------------------------
-- Scenario C — non-regressione del bypass.
-- Il bypass resta la deroga documentata per test e migrazioni.
-- ------------------------------------------------------------
SET LOCAL myapp.bypass_tx_id_check = 'true';

SELECT lives_ok(
  format(
    $q$ INSERT INTO dbops.coda_lavori_tipi
          (codice, handler_code, descrizione, run_as_default, max_tentativi_default, attivo)
        VALUES (%L, %L, 'pgTAP coerenza tx_id', 'OPERATORE', 3, TRUE) $q$,
    (SELECT scope || '_C' FROM tmp_costanti_txid),
    'pgtap_handler_txid'
  ),
  '6) Non-regressione: con bypass attivo l''INSERT riesce'
);

SET LOCAL myapp.bypass_tx_id_check = 'false';

-- ------------------------------------------------------------
-- Scenario D — canale attivo. Esercitabile solo dove il dblink di log e'
-- davvero OPERATIVO: altrove si salta, invece di fallire a sproposito.
--
-- La condizione di skip guarda il RISULTATO, non la configurazione: la GUC
-- myapp.dblink_log_connection puo' essere valorizzata mentre la connessione
-- non si apre (credenziali, pg_service, rete). In quel caso la funzione
-- ritorna la sentinella, ed e' proprio quello il segnale che il percorso
-- nominale non e' esercitabile qui.
--
-- Quando invece il canale funziona, si verifica l'invariante centrale:
-- se un id e' stato pubblicato, quell'id E' nel registro.
-- ------------------------------------------------------------
RESET myapp.dblink_log_connection;
SET LOCAL dbops.tx_id = '';

CREATE TEMP TABLE tmp_nominale_txid AS
SELECT dbops.fn_get_or_create_session_tx_id() AS tx_id;

SELECT CASE
  WHEN (SELECT tx_id FROM tmp_nominale_txid) = script.uuid_nil()
    THEN skip('7) canale dblink non operativo in questo ambiente: percorso nominale non esercitabile')
  ELSE ok(
    EXISTS (
      SELECT 1 FROM dbops.transaction_ids t
       WHERE t.id = (SELECT tx_id FROM tmp_nominale_txid)
    )
    AND current_setting('dbops.tx_id', true)::uuid = (SELECT tx_id FROM tmp_nominale_txid),
    '7) Canale attivo: l''id e'' registrato ed e'' quello pubblicato nella GUC'
  )
END;

SELECT * FROM finish();
ROLLBACK;
