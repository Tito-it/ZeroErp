-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--  8) tx_id esplicito: INSERT riesce (uscita anticipata)
--  9) tx_id esplicito: il valore fornito e' conservato tale e quale
-- 10) tx_id esplicito + GUC avvelenata: il valore fornito non viene contaminato
-- 11) [strutturale] l'uscita anticipata precede la lettura di config.parameters
-- 12) GUC forzata a un id NON registrato: il tx_id scritto e' la sentinella uuid_nil
--     (D12-bis, brief-db-revisione-dbops giro 10a: prima vinceva l'id della GUC)
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

-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(12);

-- ⭐ IL VEICOLO: una tabella temporanea col trigger montato (rev 2026-11-08).
--   Fino al giro 7-bis di brief-db-revisione-dbops (§23) il veicolo era
--   dbops.coda_lavori_tipi, che portava tx_id e il trigger a mano. Il catalogo
--   dei tipi lo scrive solo il migratore, e 20261108-90 gli ha tolto colonna e
--   trigger. Questo file collauda il TRIGGER, non una tabella: il soggetto se lo
--   fabbrica, con la sola colonna che il trigger legge e scrive. Montato come lo
--   monta il framework (BEFORE INSERT OR UPDATE, FOR EACH ROW). Nessun INSERT
--   passa dal trigger prima dello scenario A: l'asserzione 2 resta pulita.
CREATE TEMP TABLE tmp_veicolo_txid (
  codice text PRIMARY KEY,
  tx_id  uuid NULL
);
CREATE TRIGGER trg_tmp_veicolo_txid_gen_tx_id_ins_upd
  BEFORE INSERT OR UPDATE ON pg_temp.tmp_veicolo_txid
  FOR EACH ROW EXECUTE FUNCTION dbops.trgfn_tx_id_managed();

-- Scope univoco: il veicolo ha la chiave su codice.
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
    $q$ INSERT INTO pg_temp.tmp_veicolo_txid (codice) VALUES (%L) $q$,
    (SELECT scope || '_A' FROM tmp_costanti_txid)
  ),
  '3) Senza canale: INSERT su tabella tracciata riesce (riproduce il caso CI)'
);

SELECT is(
  (SELECT t.tx_id FROM pg_temp.tmp_veicolo_txid t
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
-- Il tx_id scritto e' la sentinella uuid_nil, come promettono W_TXID_NOT_REGISTERED
-- e la guida ("assegna nil"): lo prova il test 12, subito sotto.
-- ------------------------------------------------------------
SET LOCAL dbops.tx_id = '11111111-1111-4111-8111-111111111111';

SELECT lives_ok(
  format(
    $q$ INSERT INTO pg_temp.tmp_veicolo_txid (codice) VALUES (%L) $q$,
    (SELECT scope || '_B' FROM tmp_costanti_txid)
  ),
  '5) GUC con id NON registrato: l''INSERT non solleva (prima era il blocco)'
);

SELECT is(
  (SELECT t.tx_id FROM pg_temp.tmp_veicolo_txid t
    WHERE t.codice = (SELECT scope || '_B' FROM tmp_costanti_txid)),
  script.uuid_nil(),
  '12) GUC con id NON registrato: il tx_id scritto e'' la sentinella uuid_nil, non l''id della GUC'
);

-- ------------------------------------------------------------
-- Scenario C — non-regressione del bypass.
-- Il bypass resta la deroga documentata per test e migrazioni.
-- ------------------------------------------------------------
SET LOCAL myapp.bypass_tx_id_check = 'true';

SELECT lives_ok(
  format(
    $q$ INSERT INTO pg_temp.tmp_veicolo_txid (codice) VALUES (%L) $q$,
    (SELECT scope || '_C' FROM tmp_costanti_txid)
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

-- ------------------------------------------------------------
-- Scenario E — uscita anticipata quando il tx_id e' GIA' fornito.
--   (brief-db-tx-id-uscita-anticipata.md, 2026-07-24)
--
-- Dal 2026-07-24 il trigger normalizza il tx_id "stringa vuota" e, se il
-- valore e' gia' valorizzato, RITORNA SUBITO: tutto il corpo sottostante
-- serve solo a calcolare il valore da assegnare quando manca. Due effetti:
-- 280 tabelle tracciate smettono di leggere config.parameters su ogni
-- scrittura, e la sessione remota del canale di log -- che fornisce sempre
-- il proprio tx_id e ha grant sul solo schema dbops -- non chiede piu'
-- permessi su config e script (era "permesso negato per lo schema script").
--
-- NOTA sui test 1..7: nessuno di essi fornisce un tx_id esplicito (inseriscono
-- solo colonne di business e lasciano riempire al trigger), quindi vivono
-- tutti sul percorso NEW.tx_id IS NULL, che questa modifica non tocca. Se uno
-- di loro diventasse rosso sarebbe una REGRESSIONE vera, non un test da
-- allineare.
-- ------------------------------------------------------------

CREATE TEMP TABLE tmp_txid_esplicito AS
SELECT '00000000-0000-4000-8000-0000000000e1'::uuid AS tx_id;

SELECT lives_ok(
  format(
    $q$ INSERT INTO pg_temp.tmp_veicolo_txid (codice, tx_id) VALUES (%L, %L::uuid) $q$,
    (SELECT scope || '_E' FROM tmp_costanti_txid),
    (SELECT tx_id FROM tmp_txid_esplicito)
  ),
  '8) tx_id esplicito: INSERT riesce (uscita anticipata, nessun giro lungo)'
);

SELECT is(
  (SELECT t.tx_id FROM pg_temp.tmp_veicolo_txid t
    WHERE t.codice = (SELECT scope || '_E' FROM tmp_costanti_txid)),
  (SELECT tx_id FROM tmp_txid_esplicito),
  '9) tx_id esplicito: il valore fornito e'' conservato tale e quale'
);

-- Con la GUC avvelenata (id non registrato) il valore fornito dal chiamante
-- NON deve essere contaminato: e' la prova che il percorso lungo -- quello che
-- consulta la GUC e il registro -- viene davvero saltato.
SET LOCAL dbops.tx_id = '00000000-0000-4000-8000-00000000dead';

INSERT INTO pg_temp.tmp_veicolo_txid (codice, tx_id)
SELECT c.scope || '_F', e.tx_id
  FROM tmp_costanti_txid c, tmp_txid_esplicito e;

SELECT is(
  (SELECT t.tx_id
     FROM pg_temp.tmp_veicolo_txid t
    WHERE t.codice = (SELECT scope || '_F' FROM tmp_costanti_txid)),
  (SELECT tx_id FROM tmp_txid_esplicito),
  '10) tx_id esplicito + GUC avvelenata: il valore fornito non viene contaminato'
);

-- I test 8..10 fissano l'INVARIANTE (il valore fornito sopravvive), ma passano
-- sia prima sia dopo la modifica: anche la versione con i blocchi in fondo
-- restituiva NEW invariato, solo dopo aver fatto il giro lungo. Che il lavoro
-- venga SALTATO non e' osservabile dall'esterno, quindi il solo modo di
-- presidiarlo e' guardare il corpo vivo della funzione: l'uscita anticipata
-- deve precedere la lettura di config.parameters. E' questo il test che
-- diventerebbe rosso se qualcuno rimettesse i blocchi in fondo.
SELECT ok(
  strpos(pg_get_functiondef('dbops.trgfn_tx_id_managed()'::regprocedure),
         'IF NEW.tx_id IS NOT NULL THEN')
  <
  strpos(pg_get_functiondef('dbops.trgfn_tx_id_managed()'::regprocedure),
         'FROM config.parameters'),
  '11) uscita anticipata in testa: precede la lettura di config.parameters'
);

SELECT * FROM finish();
ROLLBACK;
