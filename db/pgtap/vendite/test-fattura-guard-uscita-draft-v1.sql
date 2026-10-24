-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU GPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- Test: vendite.trgfn_fatture_guard_uscita_draft (changeSet 20260731-11)
--       montata su vendite.fatture (changeSet 20260731-12)
-- Piano: piano-db-satelliti-fattura.md Fase 2.5, criterio allargato dal
--        brief-db-snapshot-intestazione-fattura.md §3.5 (passo I.4)
-- ------------------------------------------------------------
-- rev 2026-10-24 (brief-modello-documento-vendita N-1): le fatture nascono in
--   bozza; la «gia_fuori» si completa, si porta in EMESSA con
--   dbops.fn_pgtap_porta_a_stato e poi si rende di nuovo NUDA (indirizzo
--   cancellato, intestazione a NULL: in EMESSA non c'e' congelamento), cosi'
--   l'8 prova ancora l'uscita in testa sullo stato di partenza (prima nasceva
--   gia' EMESSA).
-- rev 2026-10-24 (brief-modello-documento-vendita Q-2/Q-4): le tre fatture le
--   costruisce dbops.fn_pgtap_crea_fattura sullo stesso cliente; la «gia_fuori»
--   arriva in EMESSA gia' spogliata dal builder (p_spoglia_indirizzi,
--   p_spoglia_intestazione) invece degli snapshot finti scritti e tolti a mano.
--   Il registro, il tipo e la valuta non si pescano piu'. Il 2 conta le
--   fatture vere nella forma dichiarata, non la temp table.
-- Indice test (plan 12; il 6-bis e' del 2026-10-21):
--   1) Cablaggio: BEFORE UPDATE OF stato_doc_fiscale_id, FOR EACH ROW
--   2) Fixture: tre fatture nude create (due DRAFT, una EMESSA)
--   3) DRAFT -> EMESSA a mani vuote: rifiutato
--   4) ...e il messaggio nomina ENTRAMBE le mancanze
--   5) Con il solo indirizzo FATT: ancora rifiutato, e solo per l'intestazione
--   6) Intestazione a '{}' e non NULL: ancora rifiutata (jsonb_typeof, non IS NULL)
--   6-bis) Intestazione senza la sede legale del cedente: rifiutata, e il
--      messaggio dice che manca la sede (brief-db-modelli-documento-standard
--      §10.7 R-5, changeSet 20261021-13)
--   7) Fattura completa, con la sede del cedente: DRAFT -> EMESSA passa
--   8) Fattura gia' oltre la bozza: EMESSA -> DEFINITIVA passa anche se nuda
--   9) Riscrittura dello stato con lo stesso valore: nessun presidio
--  10) UPDATE di un'altra colonna: il trigger non scatta affatto
--  11) Ordine dei guard: una transizione illegale parla come transizione
-- ------------------------------------------------------------
-- PERCHE' IL TEST 4 NON E' UN DOPPIONE DEL 3. Il 3 prova che il guard blocca;
-- il 4 prova CHE COSA sta bloccando. Senza, un guard che controllasse i soli
-- indirizzi (cioe' la Fase 2.5 come era scritta PRIMA del brief intestazione)
-- renderebbe verde il 3 pur avendo perso meta' del criterio. Il 5 chiude la
-- tenaglia dall'altro lato: con l'indirizzo a posto deve restare rosso, e per
-- l'intestazione soltanto.
--
-- PERCHE' IL TEST 6 ESISTE. fn_snapshot_intestazione_fattura applica
-- jsonb_strip_nulls: uno snapshot senza dati arriva in colonna come '{}' e non
-- come NULL. Un guard che controllasse il solo IS NULL lo dichiarerebbe
-- presente — cioe' proprio il caso «snapshot mai scritto» che il brief §3.5
-- chiede di intercettare. E' il test che distingue jsonb_typeof da IS NULL.
--
-- PERCHE' L'8 USA UNA FATTURA NUDA. Se riusasse quella completata dal 7 non
-- proverebbe nulla: passerebbe perche' e' completa, non perche' il guard esce
-- in testa sullo stato di partenza. La fattura nuda in EMESSA e' l'unico modo
-- di distinguere le due ragioni.
--
-- PERCHE' L'11 USA throws_like E NON throws_ok. Entrambi i guard sollevano
-- P0001: il codice SQLSTATE non distingue chi ha parlato. La verifica sta nel
-- MESSAGGIO — se un giorno la descrizione breve del trigger venisse cambiata in
-- modo da anticipare trgfn_fatture_guard_stato, una transizione illegale
-- verrebbe segnalata come «documento incompleto» e manderebbe a cercare il
-- problema dalla parte sbagliata. Questo test e' il presidio di quell'ordine.
--
-- Idempotente: BEGIN ... ROLLBACK.
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
-- ⛔ L'AZIENDA SI COSTRUISCE, e il contesto e' quello del SUO operatore
--   (rev 2026-10-21, brief-db-modelli-documento-standard §10.7 R-5). Fino a quel
--   giorno la fixture pescava «il primo BA con un emittente risolvibile»: su un
--   database ricostruito da zero (lo scratch, la CI) non ce n'e' uno, e il file
--   era rosso dal test 2 in poi, cioe' non verificava niente.
CREATE TEMP TABLE tmp_mondo_gud AS
SELECT m.* FROM dbops.fn_pgtap_crea_emittente_operatore() m;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM tmp_mondo_gud)); END $ctx$;

SELECT plan(12);

-- ============================================================
-- 1) Cablaggio sul catalogo.
--    tgtype = 19 -> ROW(1) + BEFORE(2) + UPDATE(16).
--    tgattr porta la colonna della clausola UPDATE OF: il suo output testuale
--    per un solo elemento e' il numero d'attributo.
-- ============================================================
SELECT is(
  (SELECT count(*)::int
     FROM pg_trigger t
     JOIN pg_class c     ON c.oid = t.tgrelid
     JOIN pg_namespace n ON n.oid = c.relnamespace
     JOIN pg_proc p      ON p.oid = t.tgfoid
    WHERE n.nspname = 'vendite'
      AND c.relname = 'fatture'
      AND p.proname = 'trgfn_fatture_guard_uscita_draft'
      AND NOT t.tgisinternal
      AND t.tgtype = 19
      AND t.tgattr::text = (SELECT a.attnum::text
                              FROM pg_attribute a
                             WHERE a.attrelid = 'vendite.fatture'::regclass
                               AND a.attname  = 'stato_doc_fiscale_id')),
  1,
  '1) guard montato BEFORE UPDATE OF stato_doc_fiscale_id FOR EACH ROW'
);

-- ============================================================
-- Riferimenti e fixture: le tre fatture dal builder, sullo STESSO cliente
-- ============================================================
-- ⭐ rev 2026-10-24 (Q-2/Q-4): le fatture le costruisce dbops.fn_pgtap_crea_fattura
--   (registro dell'azienda di chi agisce, tipo e valuta col loro ORDER BY). La
--   prima costruisce il cliente, le altre due lo riusano (terzo parametro).
--   La «gia_fuori» arriva in EMESSA NUDA (quarto e quinto parametro): il
--   builder la completa coi building block, la porta in EMESSA per la matrice
--   e la spoglia li', dove congela_fiscale e' false. Senza la spoliazione l'8
--   passerebbe perche' la fattura e' completa, non perche' il guard esce sullo
--   stato di partenza.
CREATE TEMP TABLE tmp_f_lav_gud AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('guard uscita draft lavorata');

CREATE TEMP TABLE tmp_f_int_gud AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'guard uscita draft intatta', 'DRAFT', (SELECT billing_account_id FROM tmp_f_lav_gud));

CREATE TEMP TABLE tmp_f_fuori_gud AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
    'guard uscita draft gia fuori', 'EMESSA', (SELECT billing_account_id FROM tmp_f_lav_gud),
    true, true);

CREATE TEMP TABLE tmp_fatture_gud AS
SELECT fattura_id AS id, 'lavorata'::text AS caso FROM tmp_f_lav_gud
UNION ALL SELECT fattura_id, 'intatta'   FROM tmp_f_int_gud
UNION ALL SELECT fattura_id, 'gia_fuori' FROM tmp_f_fuori_gud;

CREATE TEMP TABLE tmp_refs_gud AS
SELECT
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE)      AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'EMESSA' AND s.attivo IS TRUE)     AS stato_emessa_id,
  (SELECT s.id FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DEFINITIVA' AND s.attivo IS TRUE) AS stato_def_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'FATT') AS fatt_id;

-- ⚠️ Il 2 conta le fatture VERE nella forma dichiarata (stato, nessun
--   indirizzo, intestazione a NULL), non le righe della temp table: con il
--   builder quel conteggio sarebbe stato vero per costruzione.
SELECT is(
  (SELECT count(*)::int
     FROM tmp_fatture_gud t
     JOIN vendite.fatture f          ON f.id = t.id
     JOIN config.stati_doc_fiscale s ON s.id = f.stato_doc_fiscale_id
    WHERE s.codice_interno = CASE t.caso WHEN 'gia_fuori' THEN 'EMESSA' ELSE 'DRAFT' END
      AND f.emittente_snapshot IS NULL
      AND f.cliente_snapshot IS NULL
      AND NOT EXISTS (SELECT 1 FROM vendite.fatture_indirizzi i WHERE i.fattura_id = f.id)),
  3,
  '2) fixture: tre fatture nude create (due DRAFT, una EMESSA)'
);

-- ============================================================
-- 3-4) A mani vuote non si esce dalla bozza, e si sa perche'.
-- ============================================================
SELECT throws_ok(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_emessa_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata')),
  'P0001', NULL,
  '3) DRAFT -> EMESSA senza indirizzi ne'' intestazione: rifiutato'
);

SELECT throws_like(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_emessa_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata')),
  '%indirizzi obbligatori mancanti: FATT%intestazione non congelata: emittente_snapshot, cliente_snapshot%',
  '4) il messaggio nomina entrambe le mancanze, non solo gli indirizzi'
);

-- ============================================================
-- 5) Con il solo indirizzo a posto il criterio ALLARGATO deve restare rosso —
--    ed e' l'unica meta' che deve ancora comparire nel messaggio.
-- ============================================================
INSERT INTO vendite.fatture_indirizzi (fattura_id, tipo_indirizzo_id, snapshot)
SELECT f.id, r.fatt_id,
       '{"intestazione":"Cliente pgTAP","via":"Via Guard 1","cap":"83100"}'::jsonb
  FROM tmp_fatture_gud f, tmp_refs_gud r
 WHERE f.caso = 'lavorata';

SELECT throws_like(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_emessa_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata')),
  '%intestazione non congelata: emittente_snapshot, cliente_snapshot%',
  '5) con il solo indirizzo FATT: rifiutato, e solo per l''intestazione'
);

-- ============================================================
-- 6) Lo snapshot vuoto e' il caso che jsonb_strip_nulls produce davvero:
--    valorizzato, ma senza dentro nulla. Non deve valere come congelato.
-- ============================================================
UPDATE vendite.fatture
   SET emittente_snapshot = '{}'::jsonb,
       cliente_snapshot   = '{}'::jsonb
 WHERE id = (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata');

SELECT throws_like(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_emessa_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata')),
  '%intestazione non congelata: emittente_snapshot, cliente_snapshot%',
  '6) intestazione a ''{}'' e non NULL: ancora rifiutata'
);

-- ============================================================
-- 6-bis) L'intestazione dell'emittente c'e', ma senza la sede legale del
--    cedente: e' quello che lo snapshot scrive quando l'azienda non ha la sede
--    (la chiave manca). Non e' completa, e il messaggio lo dice.
-- ============================================================
UPDATE vendite.fatture
   SET emittente_snapshot = '{"denominazione":"Emittente pgTAP","id_fiscale":"00000000000"}'::jsonb,
       cliente_snapshot   = '{"denominazione":"Cliente pgTAP","id_fiscale":"11111111111"}'::jsonb
 WHERE id = (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata');

SELECT throws_like(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_emessa_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata')),
  '%intestazione incompleta: manca la sede legale dell''emittente%',
  '6-bis) intestazione senza la sede legale del cedente: rifiutata'
);

-- ============================================================
-- 7) Documento completo: la porta si apre. E' il test di NON-REGRESSIONE che
--    dice che la pipeline reale non e' ostacolata. ⚠️ Dal 2026-10-21 completo
--    vuol dire anche con la sede del cedente nell'intestazione.
-- ============================================================
UPDATE vendite.fatture
   SET emittente_snapshot = '{"denominazione":"Emittente pgTAP","id_fiscale":"00000000000","sede":{"via":"Via Cedente 1","cap":"83100"}}'::jsonb,
       cliente_snapshot   = '{"denominazione":"Cliente pgTAP","id_fiscale":"11111111111"}'::jsonb
 WHERE id = (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata');

SELECT lives_ok(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_emessa_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'lavorata')),
  '7) fattura completa: DRAFT -> EMESSA ammesso'
);

-- ============================================================
-- 8) Il presidio e' sull'USCITA dalla bozza, non su ogni avanzamento: oltre
--    DRAFT tocca al guard di congelamento dei satelliti, non a questo.
-- ============================================================
SELECT lives_ok(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_def_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'gia_fuori')),
  '8) fattura nuda gia'' in EMESSA: EMESSA -> DEFINITIVA ammesso'
);

-- ============================================================
-- 9-10) Il guard non deve intralciare la lavorazione della bozza, che la
--       pipeline riscrive di continuo.
-- ============================================================
SELECT lives_ok(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_draft_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'intatta')),
  '9) riscrittura dello stato con lo stesso valore: nessun presidio'
);

SELECT lives_ok(
  format($$ UPDATE vendite.fatture SET data_contabilizzazione = script.fn_data_operativa() WHERE id = %s $$,
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'intatta')),
  '10) UPDATE di un''altra colonna su fattura nuda in DRAFT: ammesso'
);

-- ============================================================
-- 11) ORDINE DEI GUARD. DRAFT -> DEFINITIVA non e' una transizione ammessa per
--     la fattura (config.stati_doc_fiscale_transizioni ha la coppia 1->8 solo
--     con solo_lotto = true). Deve rispondere trgfn_fatture_guard_stato, che
--     scatta prima per ordine lessicografico del nome — e non questo guard, che
--     direbbe «documento incompleto» su un problema che incompleto non e'.
-- ============================================================
SELECT throws_like(
  format($$ UPDATE vendite.fatture SET stato_doc_fiscale_id = %s WHERE id = %s $$,
         (SELECT stato_def_id FROM tmp_refs_gud),
         (SELECT id FROM tmp_fatture_gud WHERE caso = 'intatta')),
  '%Parametro non coerente%',
  '11) transizione illegale da DRAFT: parla il guard di transizione, non questo'
);

SELECT * FROM finish();
ROLLBACK;
