-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test — il verdetto «lotto fermo» nasce a DB, e da li' il presidio
--   (P-1 di brief-db-osservabilita-lotto-fermo-r6-indici; D-1 di Tid, 18-09:
--   «la regola va a DB»). ChangeSet: 20260919-01 (la sede,
--   vendite.vw_lotti_segnalazioni_summary), -02 (la funzione lettrice, con
--   `fermo` undicesima), -03 (dbops.vw_lotti_fermi_da_guardare) + la riga in
--   presidi.csv.
--
-- ⭐ COSA PRESIDIA QUESTO FILE, IN UNA RIGA:
--     il predicato «questo lotto e' fermo» ha UNA sede (la vista), la funzione
--     che il backend legge e il presidio che il digest conta sono due LETTORI
--     della stessa riga, e la spartizione con vw_lotti_congelati_con_gruppi_in_errore
--     (sull'asse fiscale) e la soglia di un'ora stanno nel presidio e non nella sede.
--
-- ⛔ IL MONDO SI COSTRUISCE, NON SI CERCA: azienda, operatore, cliente,
--   registro, lotti e fattura li scrive il file (builder del 18-09), quindi
--   gira identico su dbdev e su un database ricostruito dai changelog. Nessuno
--   skip. Un solo caso per addendo: e' cio' che i dati di oggi non sanno
--   fabbricare, e cio' che AGENTS §Regola zero chiede.
--
-- ⚠️ Gira come l'applicazione (zeroerp_app + contesto operatore, RLS attiva).
--   Il test 18 toglie la veste per provare la CECITA' della vista e l'onesta'
--   del contatore DEFINER, e la rimette subito dopo.
--
-- Elenco test (plan 24):
--  1) struttura: la sede esiste con fermo, fermo_motivo, fermo_da
--  2) struttura: la funzione ha UNDICI colonne e l'ultima e' `fermo`
--  3) lotto pulito: non fermo, motivo e orologio NULL
--  4) critica viva su una fattura del lotto → fermo, motivo CRITICHE, fermo_da = data_ora
--  5) la funzione lettrice dice la stessa cosa (fermo = true)
--  6) critica ritirata → non fermo
--  7) riga di ponte in ERRORE → fermo, motivo FATTURE_IN_ERRORE
--  8) ponte tornata COMPLETED → non fermo
--  9) esito ERRORE su un documento → fermo, motivo ESITI_IN_ERRORE
-- 10) lo stesso documento con esito COMPLETED → non fermo
-- 11) esito ERRORE poi ESCLUSO → non fermo (la via d'uscita non conta)
-- 12) critica di DOCUMENTO il cui esito e' ESCLUSO → non fermo (il filtro della
--     sede e' quello della funzione: il documento non e' piu' in gioco)
-- 13) precedenza: critica del giro + esito ERRORE insieme → motivo CRITICHE,
--     fermo_da = il piu' recente dei due fatti
-- 14) parita': i dieci conteggi della funzione sono quelli della sede
-- 15) presidio: fermo da meno di un'ora → NON in _da_guardare
-- 16) presidio: fermo_da spostato a due ore fa → UNA riga, motivo e da_quanto
-- 17) spartizione: lotto DEFINITIVA con critica del giro da due ore → la sede
--     dice fermo, il presidio NON lo elenca
-- 18) DEFINER onesto: senza veste la vista risponde ZERO (cecita') e
--     fn_conta_presidio conta comunque la riga costruita (delta = 1)
-- 19) catalogo: la riga e' ZERO / DEFINER / GIORNALIERA
-- 20) lotto inesistente: la funzione risponde UNA riga di zeri con fermo = false
-- 21) la funzione rifiuta p_lotto_id NULL (P0001, E_PARAMETRO_INVALIDO)
-- 22) congelato + job IN_ESECUZIONE + esito ERRORE → nei congelati, non nei fermi
-- 23) COMPLETATO in bozza + esito ERRORE da due ore → nei fermi, non nei congelati
-- 24) stato fiscale ignoto + esito ERRORE → nei congelati, non nei fermi
-- ------------------------------------------------------------

BEGIN;

-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore.
CREATE TEMP TABLE _mondo AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondo)); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(24);

-- ============================================================
-- Fixture: due lotti (DRAFT e DEFINITIVA) e una fattura DRAFT nel primo
-- ============================================================
CREATE TEMP TABLE _cli AS
SELECT c.* FROM dbops.fn_pgtap_crea_cliente_ba('lotti fermi') c;

CREATE TEMP TABLE _rif AS
SELECT m.soggetto_ruolo_id                                   AS emittente_sr_id,
       c.billing_account_id,
       script.fn_pgtap_registro_fattura(m.soggetto_ruolo_id) AS registro_id,
       config.fn_get_natura_doc_fiscale_id('FATTURA')        AS natura_fattura_id,
       (SELECT t.id FROM config.tipi_doc_fiscale t
         WHERE t.codice_interno = 'BACKOFFICE')              AS tipo_doc_fiscale_id,
       -- ⛔ codice_interno, mai un id: DRAFT e' pre-fiscale, DEFINITIVA no.
       (SELECT s.id FROM config.stati_doc_fiscale s
         WHERE s.codice_interno = 'DRAFT')                   AS stato_draft_id,
       (SELECT s.id FROM config.stati_doc_fiscale s
         WHERE s.codice_interno = 'DEFINITIVA')              AS stato_definitiva_id
  FROM _mondo m, _cli c;

-- ⚠️ Lo stato serve: vw_lotti_fase.pre_fiscale e' FAIL-CLOSED sull'ignoto, e
--   un lotto senza stato non entrerebbe mai nel presidio — verde per sottrazione.
CREATE TEMP TABLE _lotto AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, tipo_doc_fiscale_id, competenza_mese,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id, meta)
    SELECT 'PGTAP-FERMO-A-' || r.emittente_sr_id, r.tipo_doc_fiscale_id,
           date_trunc('month', script.fn_data_operativa())::date, r.emittente_sr_id,
           r.stato_draft_id, jsonb_build_object('test_scope', 'pgtap_lotti_fermi')
      FROM _rif r
    RETURNING id
)
SELECT id FROM ins;

-- Il lotto CHIUSO (DEFINITIVA): l'INSERT non passa dal guard di transizione,
-- che e' su UPDATE — e' il modo in cui il test 17 costruisce il caso.
CREATE TEMP TABLE _lotto_def AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, tipo_doc_fiscale_id, competenza_mese,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id, meta)
    SELECT 'PGTAP-FERMO-D-' || r.emittente_sr_id, r.tipo_doc_fiscale_id,
           date_trunc('month', script.fn_data_operativa())::date, r.emittente_sr_id,
           r.stato_definitiva_id, jsonb_build_object('test_scope', 'pgtap_lotti_fermi')
      FROM _rif r
    RETURNING id
)
SELECT id FROM ins;

-- La fattura, nello STESSO stato del lotto: il guard di coerenza
-- (fn_guard_lotto_fatture_stato_coerente, IMMEDIATE qui) lo pretende.
CREATE TEMP TABLE _fattura AS
WITH ins AS (
    INSERT INTO vendite.fatture
        (registro_id, data, emittente_soggetto_ruolo_id, billing_account_id,
         tasso_cambio, natura_doc_id, stato_doc_fiscale_id, meta)
    SELECT r.registro_id, script.fn_data_operativa(), r.emittente_sr_id, r.billing_account_id,
           1, r.natura_fattura_id, r.stato_draft_id,
           jsonb_build_object('test_scope', 'pgtap_lotti_fermi')
      FROM _rif r
    RETURNING id
)
SELECT id FROM ins;

-- Il ponte lotto → fattura, nato PENDING (il default).
INSERT INTO vendite.fatturazione_lotti_fatture (lotto_id, fattura_id)
SELECT l.id, f.id FROM _lotto l, _fattura f;

-- Il contatore DEFINER PRIMA che il lotto costruito diventi fermo da un'ora:
-- il test 18 misura il DELTA, cosi' non dipende da quanti lotti fermi ha la
-- macchina (su dbdev ce ne sono; su un database da zero, nessuno).
CREATE TEMP TABLE _conta_prima AS
SELECT dbops.fn_conta_presidio('dbops.vw_lotti_fermi_da_guardare') AS n;

-- ============================================================
-- 1-2) Struttura
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_views
             WHERE schemaname = 'vendite' AND viewname = 'vw_lotti_segnalazioni_summary')
    AND (SELECT count(*) FROM information_schema.columns
          WHERE table_schema = 'vendite' AND table_name = 'vw_lotti_segnalazioni_summary'
            AND column_name IN ('fermo', 'fermo_motivo', 'fermo_da')) = 3,
    '1. la sede unica esiste con fermo, fermo_motivo, fermo_da'
);

-- ⚠️ Il backend legge la riga per POSIZIONE: l'undicesima e' `fermo`, e sta in coda.
SELECT is(
    (SELECT array_length(a.proargnames, 1) - 1 || ':' || a.proargnames[array_upper(a.proargnames, 1)]
       FROM pg_proc a JOIN pg_namespace n ON n.oid = a.pronamespace
      WHERE n.nspname = 'vendite' AND a.proname = 'fn_get_lotto_segnalazioni_summary'),
    '11:fermo',
    '2. la funzione lettrice ha undici colonne e l''ultima e'' `fermo`'
);

-- ============================================================
-- 3) Lotto pulito
-- ============================================================
SELECT is(
    (SELECT (s.fermo, s.fermo_motivo, s.fermo_da)::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    (false, NULL::text, NULL::timestamptz)::text,
    '3. lotto pulito: non fermo, motivo e orologio NULL'
);

-- ============================================================
-- 4-6) Primo addendo: la critica viva sulla fattura
-- ============================================================
INSERT INTO vendite.fatture_log (fattura_id, messaggio, status)
SELECT f.id, 'pgTAP: critica sulla fattura', 'C' FROM _fattura f;

SELECT is(
    (SELECT (s.fermo, s.fermo_motivo,
             s.fermo_da = (SELECT max(fl.data_ora) FROM vendite.fatture_log fl
                            WHERE fl.fattura_id = (SELECT id FROM _fattura)))::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    (true, 'CRITICHE', true)::text,
    '4. critica viva sulla fattura: fermo, motivo CRITICHE, fermo_da = la sua data_ora'
);

SELECT is(
    (SELECT f.fermo FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT id FROM _lotto)) f),
    true,
    '5. la funzione lettrice dice fermo = true'
);

UPDATE vendite.fatture_log SET disabilitato = true
 WHERE fattura_id = (SELECT id FROM _fattura);

SELECT is(
    (SELECT s.fermo FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    false,
    '6. critica ritirata: non fermo'
);

-- ============================================================
-- 7-8) Secondo addendo: la riga di ponte in ERRORE
-- ============================================================
UPDATE vendite.fatturazione_lotti_fatture SET stato_esecuzione = 'ERRORE'
 WHERE lotto_id = (SELECT id FROM _lotto);

SELECT is(
    (SELECT (s.fermo, s.fermo_motivo, s.fatture_stato_esecuzione_errore_count)::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    (true, 'FATTURE_IN_ERRORE', 1::bigint)::text,
    '7. riga di ponte in ERRORE: fermo, motivo FATTURE_IN_ERRORE'
);

UPDATE vendite.fatturazione_lotti_fatture SET stato_esecuzione = 'COMPLETED'
 WHERE lotto_id = (SELECT id FROM _lotto);

SELECT is(
    (SELECT s.fermo FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    false,
    '8. ponte tornata COMPLETED: non fermo'
);

-- ============================================================
-- 9-11) Terzo addendo: l'esito ERRORE, e la via d'uscita
-- ============================================================
INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
SELECT l.id, 'PGTAP:FERMO:doc1', 'ERRORE', 'E_PULL_COMMESSA', 'rotto per la prova'
  FROM _lotto l;

SELECT is(
    (SELECT (s.fermo, s.fermo_motivo, s.esiti_stato_esecuzione_errore_count,
             s.documenti_presi_in_carico_count)::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    (true, 'ESITI_IN_ERRORE', 1::bigint, 1::bigint)::text,
    '9. esito ERRORE su un documento: fermo, motivo ESITI_IN_ERRORE'
);

UPDATE vendite.fatturazione_lotti_esiti SET stato_esecuzione = 'COMPLETED'
 WHERE lotto_id = (SELECT id FROM _lotto) AND gruppo_key = 'PGTAP:FERMO:doc1';

SELECT is(
    (SELECT s.fermo FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    false,
    '10. lo stesso documento con esito COMPLETED: non fermo'
);

-- Un secondo documento: rotto, poi USCITO dal giro.
INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
SELECT l.id, 'PGTAP:FERMO:doc2', 'ERRORE', 'E_PULL_COMMESSA', 'rotto, poi uscira'''
  FROM _lotto l;

UPDATE vendite.fatturazione_lotti_esiti
   SET stato_esecuzione = 'ESCLUSO', uscita_motivo = 'pgTAP: tolto dal giro'
 WHERE lotto_id = (SELECT id FROM _lotto) AND gruppo_key = 'PGTAP:FERMO:doc2';

SELECT is(
    (SELECT (s.fermo, s.esiti_stato_esecuzione_errore_count,
             s.documenti_presi_in_carico_count)::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    (false, 0::bigint, 2::bigint)::text,
    '11. esito ERRORE poi ESCLUSO: non fermo (la via d''uscita non conta, il denominatore si'')'
);

-- ============================================================
-- 12) La critica di un documento USCITO non ferma il giro
-- ============================================================
INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio, status, gruppo_key)
SELECT l.id, 'pgTAP: critica del documento uscito', 'C', 'PGTAP:FERMO:doc2'
  FROM _lotto l;

SELECT is(
    (SELECT (s.fermo, s.lotto_critical_count, s.documenti_bloccanti_count)::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    (false, 0::bigint, 0::bigint)::text,
    '12. critica di un documento ESCLUSO: non conta, non fermo (stesso filtro della funzione)'
);

-- ============================================================
-- 13) Precedenza e orologio: critica del GIRO + esito ERRORE insieme
-- ============================================================
UPDATE vendite.fatturazione_lotti_esiti SET stato_esecuzione = 'ERRORE'
 WHERE lotto_id = (SELECT id FROM _lotto) AND gruppo_key = 'PGTAP:FERMO:doc1';

-- La critica del giro (gruppo_key NULL) datata DUE ORE FA: l'esito appena
-- riscritto e' il fatto piu' recente, e l'orologio deve seguire quello.
INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio, status, data_ora)
SELECT l.id, 'pgTAP: critica del giro', 'C', now() - interval '2 hours'
  FROM _lotto l;

SELECT is(
    (SELECT (s.fermo, s.fermo_motivo, s.critiche_giro_count,
             s.fermo_da = (SELECT COALESCE(e.errore_quando, e.data_update)
                             FROM vendite.fatturazione_lotti_esiti e
                            WHERE e.lotto_id = (SELECT id FROM _lotto)
                              AND e.gruppo_key = 'PGTAP:FERMO:doc1'))::text
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    (true, 'CRITICHE', 1::bigint, true)::text,
    '13. critica del giro + esito ERRORE: motivo CRITICHE, fermo_da = il fatto piu'' recente (l''esito)'
);

-- ============================================================
-- 14) Parita' funzione ↔ sede
-- ============================================================
SELECT is(
    (SELECT to_jsonb(f) FROM vendite.fn_get_lotto_segnalazioni_summary((SELECT id FROM _lotto)) f),
    (SELECT to_jsonb(s) - 'lotto_id' - 'fermo_motivo' - 'fermo_da'
       FROM vendite.vw_lotti_segnalazioni_summary s
      WHERE s.lotto_id = (SELECT id FROM _lotto)),
    '14. la funzione lettrice consegna esattamente i dieci conteggi e il fermo della sede'
);

-- ============================================================
-- 15-16) Il presidio e la soglia
-- ============================================================
-- Adesso l'orologio e' l'esito di pochi istanti fa: fermo, ma non da un'ora.
SELECT is(
    (SELECT count(*)::int FROM dbops.vw_lotti_fermi_da_guardare
      WHERE lotto_id = (SELECT id FROM _lotto)),
    0,
    '15. fermo da meno di un''ora: non in vw_lotti_fermi_da_guardare'
);

-- Si porta l'ultimo fatto a due ore fa: l'esito (l'ultimo scritto) e la
-- critica del giro sono gia' li'. Restano: l'orologio dice due ore.
UPDATE vendite.fatturazione_lotti_esiti
   SET errore_quando = now() - interval '2 hours'
 WHERE lotto_id = (SELECT id FROM _lotto) AND gruppo_key = 'PGTAP:FERMO:doc1';

SELECT is(
    (SELECT (count(*), min(motivo), bool_and(da_quanto > interval '1 hour'),
             bool_and(stato_codice_interno = 'DRAFT'))::text
       FROM dbops.vw_lotti_fermi_da_guardare
      WHERE lotto_id = (SELECT id FROM _lotto)),
    (1::bigint, 'CRITICHE', true, true)::text,
    '16. fermo da due ore: UNA riga nel presidio, motivo CRITICHE, da_quanto > 1h, lotto pre-fiscale'
);

-- ============================================================
-- 17) La spartizione con vw_lotti_congelati_con_gruppi_in_errore (anche 22-24)
-- ============================================================
INSERT INTO vendite.fatturazione_lotti_log (lotto_id, messaggio, status, data_ora)
SELECT l.id, 'pgTAP: critica del giro su lotto chiuso', 'C', now() - interval '2 hours'
  FROM _lotto_def l;

SELECT is(
    (SELECT (
        (SELECT s.fermo FROM vendite.vw_lotti_segnalazioni_summary s
          WHERE s.lotto_id = (SELECT id FROM _lotto_def)),
        (SELECT count(*)::int FROM dbops.vw_lotti_fermi_da_guardare
          WHERE lotto_id = (SELECT id FROM _lotto_def)),
        (SELECT f.pre_fiscale FROM vendite.vw_lotti_fase f
          WHERE f.lotto_id = (SELECT id FROM _lotto_def))
    )::text),
    (true, 0, false)::text,
    '17. lotto DEFINITIVA con critica da due ore: la sede dice fermo, il presidio NON lo elenca (non pre-fiscale)'
);

-- ============================================================
-- 18) DEFINER onesto: senza veste la vista e' cieca, il contatore no
-- ============================================================
-- ⚠️ Si toglie la VESTE, non l'utente: `app.current_user_id` vuoto vale
--   «nessuna restrizione» (memoria: svuotare l'utente non e' fail-closed); il
--   cancello che chiude e' app.ruolo_applicativo.
SELECT set_config('app.ruolo_applicativo', '', true);

SELECT is(
    (SELECT (
        (SELECT count(*)::int FROM dbops.vw_lotti_fermi_da_guardare),
        (SELECT dbops.fn_conta_presidio('dbops.vw_lotti_fermi_da_guardare')
              - (SELECT n FROM _conta_prima))
    )::text),
    (0, 1::bigint)::text,
    '18. senza veste la vista risponde ZERO (cecita''); fn_conta_presidio vede comunque la riga costruita (delta = 1)'
);

SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);

-- ============================================================
-- 19) Il catalogo
-- ============================================================
SELECT is(
    (SELECT (p.natura, p.perimetro, p.cadenza, p.attivo, p.obsoleto_dal IS NULL)::text
       FROM dbops.presidi p
      WHERE p.vista = 'dbops.vw_lotti_fermi_da_guardare'),
    ('ZERO', 'DEFINER', 'GIORNALIERA', true, true)::text,
    '19. a catalogo: ZERO, DEFINER (le tabelle hanno la RLS), GIORNALIERA, attivo'
);

-- ============================================================
-- 20-21) La funzione lettrice: una riga sempre, e il guard
-- ============================================================
SELECT is(
    (SELECT to_jsonb(f) FROM vendite.fn_get_lotto_segnalazioni_summary(999999999) f),
    jsonb_build_object(
        'fatture_critical_count', 0, 'fatture_warning_count', 0,
        'lotto_critical_count', 0, 'lotto_warning_count', 0, 'lotto_info_count', 0,
        'fatture_stato_esecuzione_errore_count', 0,
        'documenti_bloccanti_count', 0, 'documenti_presi_in_carico_count', 0,
        'critiche_giro_count', 0, 'esiti_stato_esecuzione_errore_count', 0,
        'fermo', false),
    '20. lotto inesistente: una riga di zeri con fermo = false'
);

SELECT throws_ok(
    $$ SELECT * FROM vendite.fn_get_lotto_segnalazioni_summary(NULL) $$,
    'P0001',
    NULL,
    '21. p_lotto_id NULL: rifiutato (P0001)'
);

-- ============================================================
-- 22-24) L'asse fiscale dei due presidi (rev 2026-11-07, brief-db-revisione-dbops
--   giro 6, Q14 ⑦): pre-fiscale -> vw_lotti_fermi_da_guardare, congelato o
--   ignoto -> vw_lotti_congelati_con_gruppi_in_errore, qualunque stato_lotto.
-- ============================================================
-- Un lotto congelato con un esito in ERRORE e il job ancora IN_ESECUZIONE (il
-- default della colonna): e' il BUCO di prima, che non vedeva nessuno.
INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio, errore_quando)
SELECT l.id, 'PGTAP:FERMO:def1', 'ERRORE', 'E_PULL_COMMESSA', 'rotto dopo il congelamento',
       now() - interval '2 hours'
  FROM _lotto_def l;

SELECT is(
    (SELECT (
        (SELECT l.stato_lotto FROM vendite.fatturazione_lotti l WHERE l.id = (SELECT id FROM _lotto_def)),
        (SELECT c.gruppi_in_errore::int FROM vendite.vw_lotti_congelati_con_gruppi_in_errore c
          WHERE c.lotto_id = (SELECT id FROM _lotto_def)),
        (SELECT count(*)::int FROM dbops.vw_lotti_congelati_con_errori_da_guardare d
          WHERE d.lotto_id = (SELECT id FROM _lotto_def)),
        (SELECT count(*)::int FROM dbops.vw_lotti_fermi_da_guardare
          WHERE lotto_id = (SELECT id FROM _lotto_def))
    )::text),
    ('IN_ESECUZIONE', 1, 1, 0)::text,
    '22. congelato + job IN_ESECUZIONE + esito ERRORE: lo vedono i congelati (vendite e dbops), non i fermi'
);

-- Un lotto ancora in bozza che NASCE COMPLETATO (il guard del COMPLETATO e' su
-- UPDATE) con un esito in ERRORE da due ore: e' il DOPPIONE di prima.
CREATE TEMP TABLE _lotto_compl AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, tipo_doc_fiscale_id, competenza_mese,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id, stato_lotto, meta)
    SELECT 'PGTAP-FERMO-C-' || r.emittente_sr_id, r.tipo_doc_fiscale_id,
           date_trunc('month', script.fn_data_operativa())::date, r.emittente_sr_id,
           r.stato_draft_id, 'COMPLETATO', jsonb_build_object('test_scope', 'pgtap_lotti_fermi')
      FROM _rif r
    RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio, errore_quando)
SELECT l.id, 'PGTAP:FERMO:compl1', 'ERRORE', 'E_PULL_COMMESSA', 'rotto in bozza',
       now() - interval '2 hours'
  FROM _lotto_compl l;

SELECT is(
    (SELECT (
        (SELECT count(*)::int FROM dbops.vw_lotti_fermi_da_guardare
          WHERE lotto_id = (SELECT id FROM _lotto_compl)),
        (SELECT count(*)::int FROM vendite.vw_lotti_congelati_con_gruppi_in_errore
          WHERE lotto_id = (SELECT id FROM _lotto_compl))
    )::text),
    (1, 0)::text,
    '23. COMPLETATO in bozza + esito ERRORE da due ore: lo vedono i fermi, non i congelati (niente doppione)'
);

-- Un lotto con lo stato fiscale IGNOTO: pre_fiscale e' COALESCE(..., false),
-- quindi cade fra i congelati, dove un esito in errore resta visibile.
CREATE TEMP TABLE _lotto_ignoto AS
WITH ins AS (
    INSERT INTO vendite.fatturazione_lotti
        (codice, tipo_doc_fiscale_id, competenza_mese,
         emittente_soggetto_ruolo_id, stato_doc_fiscale_id, meta)
    SELECT 'PGTAP-FERMO-I-' || r.emittente_sr_id, r.tipo_doc_fiscale_id,
           date_trunc('month', script.fn_data_operativa())::date, r.emittente_sr_id,
           NULL, jsonb_build_object('test_scope', 'pgtap_lotti_fermi')
      FROM _rif r
    RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.fatturazione_lotti_esiti
    (lotto_id, gruppo_key, stato_esecuzione, errore_codice, errore_messaggio)
SELECT l.id, 'PGTAP:FERMO:ign1', 'ERRORE', 'E_PULL_COMMESSA', 'rotto, stato ignoto'
  FROM _lotto_ignoto l;

SELECT is(
    (SELECT (
        (SELECT c.stato_codice_interno IS NULL FROM vendite.vw_lotti_congelati_con_gruppi_in_errore c
          WHERE c.lotto_id = (SELECT id FROM _lotto_ignoto)),
        (SELECT count(*)::int FROM dbops.vw_lotti_fermi_da_guardare
          WHERE lotto_id = (SELECT id FROM _lotto_ignoto))
    )::text),
    (true, 0)::text,
    '24. stato fiscale ignoto + esito ERRORE: lo vedono i congelati, con lo stato NULL; non i fermi'
);

SELECT * FROM finish();
ROLLBACK;
