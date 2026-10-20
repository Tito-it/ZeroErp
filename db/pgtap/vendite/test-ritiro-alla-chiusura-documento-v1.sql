-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2d/2e): chiavi del push e ambito degli indirizzi col codice della sorgente.
-- pgTAP test per Zero ERP
-- Test: l'AGGANCIO del ritiro — freno e ritiro sulla chiusura del documento
--       (brief-db-lavoro-che-non-torna-indietro, lotto L7b / Q-9 e Q-10;
--        rev 2026-10-11, brief-db-annullo-documento-con-legami D-5)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Chiudere un documento deve ritirare il lavoro che aveva spinto e che
--   nessuno ha ancora emesso, e deve NON riuscire finche' c'e' lavoro gia'
--   emesso. Sono due meta' della stessa regola, e da sole non valgono.
--
-- ⭐ IL VERO SOGGETTO E' CHE NESSUNO DEVE RICORDARSELO (Q-10)
--   La regola sta sulla tabella, non nei servizi: lo stato di una testata si
--   cambia da molti posti, e con la chiamata esplicita basta UNO distratto
--   perche' il buco torni. Il test 4 fa un UPDATE nudo sulla testata.
-- ⭐ rev 2026-10-11 (brief-db-annullo-documento-con-legami D-5): il ritiro
--   NON e' piu' silenzioso. Fino a qui un trigger _z90_ ritirava le righe
--   NON_EMESSA all'annullo, senza che chi annullava lo vedesse. Ora le righe
--   NON_EMESSA sono LEGAMI: l'UPDATE nudo e' rifiutato con
--   E_DOC_ANNULLO_CON_LEGAMI (l'avviso, guard _m10_ sulla tabella: vale per
--   ogni strada, che e' l'argomento di Q-10), e il ritiro lo fa il verbo
--   vendite.fn_annulla_ordine dopo la conferma, con la stessa primitiva e lo
--   stesso registro. Il freno sulle righe EMESSA resta, e parla PRIMA.
--
-- ⛔ E QUESTO FILE E' ANCHE IL PRESIDIO DI Q-9
--   I due divieti «ha gia' spinto in commessa» sono stati RITIRATI
--   (E_PREV_GIA_IN_COMMESSA, E_ORD_ANNULLA_IN_COMMESSA). Il test 2 verifica
--   che un ordine con sole righe NON_EMESSA adesso si annulli: prima veniva
--   rifiutato, e se qualcuno rimettesse quel motivo tornerebbe rosso.
--
-- ⚠️ FIXTURE COSTRUITE: cliente e articolo dai builder (rev 2026-10-11: prima
--   il billing account e l'articolo si pescavano dai dati, e da zero il file
--   si fermava al primo INSERT); commessa, righe di commessa e ordine sono
--   INSERITI da questo file, con una chiave sorgente che e' l'`uid` dell'ordine
--   vero — perche' e' cio' che le fn_list_*_da_pushare scrivono, e usare
--   l'altra chiave (quella di commesse_sorgenti) darebbe un ritiro che non
--   ritira.
--
-- Indice test
-- 1) Fixture: un ordine con due righe di commessa spinte (NON_EMESSA + EMESSA)
-- 2) ⛔ Il freno: con una riga EMESSA l annullamento e RIFIUTATO, col suo codice
-- 3) La check di dominio nomina lo stesso motivo (le due meta non si separano)
-- 4) 🔴 Tolta la riga emessa, l'UPDATE nudo e' rifiutato: le NON_EMESSA sono
--    legami e chiedono conferma (E_DOC_ANNULLO_CON_LEGAMI)
-- 5) 🔴 Il verbo confermato annulla e RITIRA: righe ANNULLATA, traccia col motivo
-- 6) ⛔ Le righe di ALTRI documenti non sono state toccate
-- 7) Un secondo UPDATE sullo stesso stato non ritira niente (nessun doppione)
-- 8) la conferma era di due legami: il verbo li restituisce
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(8);

-- ============================================================
-- Fixture
-- ============================================================
CREATE TEMP TABLE tmp_rc_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('ritiro alla chiusura');

CREATE TEMP TABLE tmp_rc_refs AS
WITH ba AS (
  SELECT c.billing_account_id AS id, c.utility_id, c.istanza_utility_id
    FROM tmp_rc_cli c)
SELECT (SELECT id FROM ba)                 AS billing_account_id,
       (SELECT utility_id FROM ba)         AS utility_id,
       (SELECT istanza_utility_id FROM ba) AS istanza_utility_id,
       dbops.fn_pgtap_crea_articolo('PGT-RC-RITIRO', false) AS articolo_id,
       (SELECT u.id FROM catalogo.unita_misura u
         WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)  AS uom_id,
       (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)  AS tipo_doc_fiscale_id,
       (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1) AS valuta_id,
       (SELECT sc.id FROM vendite.stati_commessa sc
         WHERE sc.attivo IS TRUE AND sc.codice_interno <> 'ANNULLATA'
         ORDER BY sc.id LIMIT 1)           AS stato_commessa_id,
       (SELECT c.soggetto_ruolo_id FROM tmp_rc_cli c) AS soggetto_ruolo_id,
       -- ⚠️ L'ordine vuole l'emittente FISCALE, non il soggetto_ruolo: la
       --   funzione del contesto restituisce il secondo, e l'INSERT sul primo
       --   fallirebbe sul guard di scope con un messaggio che parla d'altro.
       (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()
         ORDER BY ef.id LIMIT 1)           AS emittente_fiscale_id,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA') AS sorgente_tipo_id,
       script.fn_pgtap_emittente_sr_operatore() AS emittente_sr_id,
       -- ⭐ Gli stati si prendono per `is_abortito`, non per codice: e' lo
       --   stesso asse su cui il trigger si aggancia.
       (SELECT so.id FROM config.stati_doc_ordini so
         WHERE so.is_abortito IS NOT TRUE AND so.codice_interno = 'DRAFT'
         ORDER BY so.id LIMIT 1)           AS stato_vivo_id,
       (SELECT so.id FROM config.stati_doc_ordini so
         WHERE so.is_abortito IS TRUE ORDER BY so.id LIMIT 1) AS stato_abortito_id;

CREATE TEMP TABLE tmp_rc_ordine AS
WITH ins AS (
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, utility_id,
                              stato_doc_ordine_id, valuta_id, data,
                              fatturazione_trigger, emittente_fiscale_id, storicizza)
  SELECT r.soggetto_ruolo_id, r.billing_account_id, r.utility_id,
         r.stato_vivo_id, r.valuta_id, script.fn_data_operativa(),
         'CONFERMATO', r.emittente_fiscale_id, false
    FROM tmp_rc_refs r
  RETURNING id, uid)
SELECT * FROM ins;

CREATE TEMP TABLE tmp_rc_commessa AS
WITH ins AS (
  INSERT INTO vendite.commesse (codice, billing_account_id, utility_id,
                                emittente_soggetto_ruolo_id, stato_commessa_id)
  SELECT 'PGTAP-RC-' || substr(md5(clock_timestamp()::text), 1, 8),
         r.billing_account_id, r.utility_id, r.emittente_sr_id, r.stato_commessa_id
    FROM tmp_rc_refs r
  RETURNING id)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_rc_ca (slot text PRIMARY KEY, attivita_id bigint);

-- Due righe spinte dallo STESSO ordine: una ancora da emettere, una emessa.
-- ⛔ `sorgente_uid` e' l'`uid` dell'ordine: e' cio' che
--    fn_list_ordini_da_pushare scrive. La chiave di commesse_sorgenti (l'id)
--    darebbe un ritiro che non ritira, e nessun errore.
DO $fx$
DECLARE s text;
BEGIN
  FOREACH s IN ARRAY ARRAY['DA_EMETTERE', 'EMESSA'] LOOP
    WITH ins AS (
      INSERT INTO vendite.commesse_attivita (
        commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
        uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
        tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
        stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
      SELECT (SELECT id FROM tmp_rc_commessa),
             'ORDINE_VENDITA:' || (SELECT uid FROM tmp_rc_ordine)::text || ':R:' || s,
             r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
             date_trunc('month', script.fn_data_operativa())::date,
             date_trunc('month', script.fn_data_operativa())::date,
             (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
             r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
             'BOZZA',
             CASE WHEN s = 'EMESSA' THEN 'EMESSA' ELSE 'NON_EMESSA' END,
             r.sorgente_tipo_id,
             (SELECT uid FROM tmp_rc_ordine)::text
        FROM tmp_rc_refs r
      RETURNING id)
    INSERT INTO tmp_rc_ca(slot, attivita_id) SELECT s, ins.id FROM ins;
  END LOOP;
END
$fx$;

-- Una riga di UN ALTRO documento, che non deve essere toccata (test 6).
CREATE TEMP TABLE tmp_rc_estranea AS
WITH ins AS (
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, competenza_mese, competenza_dal, competenza_al,
    tipo_doc_fiscale_id, valuta_id, prezzo_snapshot, pricing_mode,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid)
  SELECT (SELECT id FROM tmp_rc_commessa),
         'ORDINE_VENDITA:PGTAP-RC-ESTRANEA:' || substr(md5(clock_timestamp()::text), 1, 10),
         r.articolo_id, r.istanza_utility_id, script.fn_data_operativa(), r.uom_id, 1,
         date_trunc('month', script.fn_data_operativa())::date,
         date_trunc('month', script.fn_data_operativa())::date,
         (date_trunc('month', script.fn_data_operativa()) + INTERVAL '1 month - 1 day')::date,
         r.tipo_doc_fiscale_id, r.valuta_id, 10.000000, 'FIXED',
         'BOZZA', 'NON_EMESSA', r.sorgente_tipo_id, gen_random_uuid()::text
    FROM tmp_rc_refs r
  RETURNING id)
SELECT id FROM ins;

SELECT ok(
  (SELECT count(*) = 2 FROM tmp_rc_ca)
  AND (SELECT uid IS NOT NULL FROM tmp_rc_ordine)
  AND (SELECT r.stato_abortito_id IS NOT NULL AND r.stato_vivo_id IS NOT NULL
          AND r.emittente_fiscale_id IS NOT NULL AND r.soggetto_ruolo_id IS NOT NULL
         FROM tmp_rc_refs r),
  '1) fixture: un ordine con due righe di commessa spinte (NON_EMESSA + EMESSA)'
);

-- ============================================================
-- 2) ⛔ Il freno
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.rc_chiudi() RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  UPDATE vendite.ordini
     SET stato_doc_ordine_id = (SELECT stato_abortito_id FROM tmp_rc_refs)
   WHERE id = (SELECT id FROM tmp_rc_ordine);
  RETURN 'NESSUN ERRORE';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN COALESCE(NULLIF(v_cod, ''), 'SQLSTATE:' || SQLSTATE);
END $$ LANGUAGE plpgsql;

SELECT is(
  pg_temp.rc_chiudi(),
  'E_SORGENTE_CON_RIGHE_EMESSE',
  '2) il freno: con una riga EMESSA la chiusura e rifiutata, e col codice giusto'
);

-- ============================================================
-- 3) Le due meta non si separano
-- ============================================================
-- ⭐ Il guard ferma, la fn_check_* spiega: se divergessero, l interfaccia
--   direbbe «si puo fare» e la scrittura risponderebbe di no.
SELECT is(
  script.fn_check_sorgente_chiudibile(
    (SELECT sorgente_tipo_id FROM tmp_rc_refs),
    (SELECT uid FROM tmp_rc_ordine)::text) -> 0 ->> 'codice',
  'E_SORGENTE_CON_RIGHE_EMESSE',
  '3) la check di dominio nomina lo stesso motivo che il guard solleva'
);

-- ============================================================
-- 4) 🔴 Tolta la riga emessa, l'UPDATE nudo e' rifiutato: conferma
-- ============================================================
-- ⭐ E' cio' che «Riporta da emettere» fa nella vita vera: riporta la riga a
--   NON_EMESSA, e da li' il ritiro la prende. Qui si simula quello stato.
UPDATE vendite.commesse_attivita
   SET stato_emissione = 'NON_EMESSA'
 WHERE id = (SELECT attivita_id FROM tmp_rc_ca WHERE slot = 'EMESSA');

-- ⚠️ UPDATE NUDO sulla testata: nessuna funzione di dominio, nessun servizio.
--   ⭐ rev 2026-10-11 (D-5): le due righe NON_EMESSA sono legami, e annullare
--   senza conferma e' rifiutato. Il freno sulle EMESSA (test 2) ha parlato
--   prima: questo e' il secondo rifiuto, quello che chiede conferma.
SELECT is(
  pg_temp.rc_chiudi(),
  'E_DOC_ANNULLO_CON_LEGAMI',
  '4) senza righe emesse l''UPDATE nudo e'' rifiutato: le NON_EMESSA sono legami e chiedono conferma'
);

-- ============================================================
-- 5) 🔴 Il verbo confermato annulla e RITIRA
-- ============================================================
CREATE TEMP TABLE tmp_rc_esito AS
SELECT vendite.fn_annulla_ordine((SELECT id FROM tmp_rc_ordine), 2) AS legami;

SELECT ok(
  (SELECT count(*) = 2
     FROM vendite.commesse_attivita ca
     JOIN tmp_rc_ca t ON t.attivita_id = ca.id
    WHERE ca.stato_emissione = 'ANNULLATA')
  AND (SELECT count(*) = 2
         FROM vendite.commesse_attivita_log l
         JOIN tmp_rc_ca t ON t.attivita_id = l.commessa_attivita_id
        WHERE l.evento = 'RIGA_RITIRATA_DA_SORGENTE'
          AND l.dettaglio ->> 'motivo' LIKE 'Ritiro all''annullo confermato%'
          AND l.dettaglio ->> 'stato_precedente' = 'NON_EMESSA')
  AND (SELECT o.stato_doc_ordine_id = r.stato_abortito_id
         FROM vendite.ordini o, tmp_rc_refs r WHERE o.id = (SELECT id FROM tmp_rc_ordine)),
  '5) confermato: l''ordine e'' annullato, le due righe ritirate, la traccia col motivo e lo stato precedente'
);

-- ============================================================
-- 6) ⛔ Le righe di ALTRI documenti non si toccano
-- ============================================================
-- ⛔ Se questo diventa rosso, il ritiro sta lavorando per commessa invece che
--   per SORGENTE: annullerebbe lavoro di documenti che nessuno ha chiuso.
SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT id FROM tmp_rc_estranea)),
  'NON_EMESSA'::character varying,
  '6) la riga di un altro documento, nella stessa commessa, non e stata toccata'
);

-- ============================================================
-- 7) Nessun doppione
-- ============================================================
-- ⚠️ Il trigger si sveglia su UPDATE OF della colonna di stato. Riscrivere lo
--   STESSO stato non e' una chiusura, e non deve produrre un secondo giro di
--   registro: un ritiro contato due volte renderebbe il diario inaffidabile.
UPDATE vendite.ordini
   SET stato_doc_ordine_id = (SELECT stato_abortito_id FROM tmp_rc_refs)
 WHERE id = (SELECT id FROM tmp_rc_ordine);

SELECT is(
  (SELECT count(*) FROM vendite.commesse_attivita_log l
     JOIN tmp_rc_ca t ON t.attivita_id = l.commessa_attivita_id
    WHERE l.evento = 'RIGA_RITIRATA_DA_SORGENTE'),
  2::bigint,
  '7) riscrivere lo stesso stato non ritira di nuovo: nessun doppione nel registro'
);

-- ============================================================
-- 8) La conferma era di due legami
-- ============================================================
SELECT is(
  (SELECT legami FROM tmp_rc_esito),
  2,
  '8) il verbo restituisce i legami confermati: le due righe di commessa'
);

SELECT * FROM finish();

ROLLBACK;
