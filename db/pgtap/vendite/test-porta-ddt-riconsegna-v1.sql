-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Copyright (C) 2026 Tid (Michele Carlo Titini)
--
-- Rilasciato sotto GNU AGPLv3 o versione successiva.
-- Vedi LICENSE.md per il testo completo della licenza.
-- ------------------------------------------------------------
-- rev 2026-11-27 (brief-db-porte-aperte-dalla-sola-guc §15, giro 10-quater): gli override utente sono in sola lettura per l'app; l'override d'oggetto su vendite.reso lo scrive dbops.fn_pgtap_scrivi_override dal verbo. Attese invariate.
--
-- Test: la porta 11, la riconsegna di un reso, si apre solo dal verbo, col suo
--   permesso e nel suo perimetro.
-- Riferimento: brief-db-porte-aperte-dalla-sola-guc §12 (giro 11; D-A a di Tid,
--   2026-11-23); changeSet 20_code/script/20261124-10 (la porta: GUC sul reso E
--   proprietario), 20_code/vendite/20261124-11 (il verbo SECURITY DEFINER col
--   guard del livello su vendite.reso e il perimetro del reso all'ingresso). Che
--   cosa fa la madre lo provano test-fn-genera-ddt-riconsegna-eredita-v1 e
--   test-resi-motore-v1; l'esenzione dell'articolo test-righe-articolo-ammesso-v1.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il verbo e' SECURITY DEFINER col search_path fissato; il guard
--     dell'articolo resta INVOKER;
--   - il permesso e' il livello TUTTO sull'oggetto vendite.reso, con la ricaduta
--     sull'area: con l'area vendite a TUTTO e l'oggetto a LETTURA il verbo rifiuta
--     (E_PERMESSO_NEGATO) e non scrive;
--   - l'applicazione non apre la porta: con la GUC sull'id del reso un INSERT
--     diretto di una riga di bolla con l'articolo del reso, che la bolla non
--     ammette piu' (solo componente), resta rifiutato;
--   - DUE EMITTENTI: il reso dell'altra azienda «non c'e'» (E_RESO_NOT_FOUND, la
--     stessa risposta di un reso inesistente), e niente si scrive;
--   - col permesso il verbo genera la bolla, l'articolo del reso passa (la porta
--     si apre dentro il verbo), e dopo il verbo la GUC e' vuota.
--
-- ⛔ IL MONDO SI COSTRUISCE: due aziende coi loro operatori e clienti
--   (dbops.fn_pgtap_crea_mondo_cliente, dbops.fn_pgtap_crea_emittente_operatore
--   per l'operatore di B). Le cose di B si costruiscono nel
--   contesto dell'operatore di B, poi il contesto passa ad A, che e' chi agisce.
--   Il reso confermato lo da' dbops.fn_pgtap_crea_reso, che concede a chi e' in
--   contesto conferma_reso, e con essa l'area vendite al suo minimo (TUTTO): il
--   rifiuto del permesso si costruisce con un override sull'oggetto, che col
--   tetto d'area vince (il piu' restrittivo dei due).
-- ⚠️ Gira come l'applicazione (runner di default). Da proprietario chi scrive e'
--   il proprietario, e la porta col valore giusto gli si apre: 4 e' rosso per
--   costruzione.
--
-- Elenco test (plan 8):
--    1) il verbo: SECURITY DEFINER, search_path fissato; il guard: INVOKER
--    2) area vendite a TUTTO, oggetto vendite.reso a LETTURA: E_PERMESSO_NEGATO
--    3) … e non scrive: nessuna riconsegna sul reso di A
--    4) ⭐ l'app scrive la GUC con l'id del reso e la riga diretta: rifiutata, la
--       porta chiede anche il proprietario
--    5) ⭐ il reso di B: per A non c'e' (E_RESO_NOT_FOUND)
--    6) … e niente scritto sul reso di B (letto nel contesto di B)
--    7) col permesso il verbo genera la bolla con l'articolo del reso: la porta
--       si apre dentro il verbo
--    8) dopo il verbo la GUC e' vuota
-- ------------------------------------------------------------

-- ⚠️ 1. TRANSAZIONE.
BEGIN;

-- Due aziende, ciascuna col suo operatore e il suo cliente.
-- ⚠️ Con un contesto aperto il builder del mondo riusa l'azienda di chi agisce:
--   A nasce senza contesto (il builder la costruisce), B nasce dal suo operatore,
--   e il suo mondo si costruisce nel suo contesto.
CREATE TEMP TABLE _mondi AS
SELECT 'A' AS lato, m.* FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP porta riconsegna A') m;

CREATE TEMP TABLE _op_b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- ⚠️ 2. CONTESTO APPLICATIVO: prima B, per costruirne le cose.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _op_b)); END $ctx$;

INSERT INTO _mondi
SELECT 'B', m.* FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP porta riconsegna B') m;

-- ⚠️ 3. VINCOLI DIFFERITI.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture
-- ============================================================
-- K: merce, vendibile; dopo la consegna diventera' solo componente.
CREATE TEMP TABLE _art AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-PRIC-K', false,
           p_natura_vendita_id => (SELECT nv.id FROM config.nature_vendita nv
                                    WHERE nv.destinazione_tipo = 'ORDINE_VENDITA' AND nv.attivo
                                    ORDER BY nv.id LIMIT 1)) AS k;

CREATE TEMP TABLE _resi (lato text, reso_id bigint, resi_riga_id bigint);

-- Una bolla CONSEGNATA con K e il suo reso per ri-consegna confermato, nel
-- contesto di chi la costruisce.
CREATE OR REPLACE FUNCTION pg_temp.reso(p_lato text)
RETURNS void LANGUAGE plpgsql AS $f$
DECLARE
  v_ddt  bigint;
  v_riga bigint;
BEGIN
  SELECT b.ddt_id, b.ddt_riga_id INTO v_ddt, v_riga
    FROM dbops.fn_pgtap_crea_ddt_senza_ordine('porta riconsegna ' || p_lato, 'CONSEGNATO',
             p_billing_account_id => (SELECT billing_account_id FROM _mondi WHERE lato = p_lato),
             p_quantita           => 3,
             p_prezzo             => 10,
             p_articolo_id        => (SELECT k FROM _art)) b;
  INSERT INTO _resi
  SELECT p_lato, r.reso_id, r.resi_riga_id
    FROM dbops.fn_pgtap_crea_reso('porta riconsegna ' || p_lato, v_ddt, 1, 'RESO_PER_RICONSEGNA',
             p_ddt_riga_id => v_riga) r;
END
$f$;

SELECT pg_temp.reso('B');

DO $ctxa$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'A')); END $ctxa$;

SELECT pg_temp.reso('A');

-- Una bolla di A in bozza, per la riga scritta a mano.
CREATE TEMP TABLE _bozza AS
SELECT dbops.fn_pgtap_crea_ddt((SELECT billing_account_id FROM _mondi WHERE lato = 'A'),
                               (SELECT cliente_soggetto_ruolo_id FROM _mondi WHERE lato = 'A'),
                               'VENDITA') AS id;

-- K diventa solo componente: la bolla non lo ammette piu', la riconsegna si'.
SELECT dbops.fn_pgtap_articolo_correggi_struttura(
    (SELECT k FROM _art), jsonb_build_object('is_solo_componente', true));

-- Il verbo su un reso, come istruzione da provare.
CREATE OR REPLACE FUNCTION pg_temp.riconsegna(p_lato text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format('SELECT vendite.fn_genera_ddt_riconsegna(%s)',
                (SELECT reso_id FROM _resi WHERE lato = p_lato));
$f$;

-- Quante riconsegne ha la riga del reso.
CREATE OR REPLACE FUNCTION pg_temp.riconsegne(p_lato text)
RETURNS bigint LANGUAGE sql AS $f$
  SELECT count(*) FROM vendite.resi_righe_riconsegne rr
   WHERE rr.resi_riga_id = (SELECT resi_riga_id FROM _resi WHERE lato = p_lato);
$f$;

-- ============================================================
-- 1 La forma
-- ============================================================
SELECT is(
  (SELECT p.prosecdef AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search\_path=%')
     FROM pg_catalog.pg_proc p
    WHERE p.oid = 'vendite.fn_genera_ddt_riconsegna'::regproc)
  AND NOT (SELECT p.prosecdef FROM pg_catalog.pg_proc p
            WHERE p.oid = 'script.trgfn_righe_guard_articolo_ammesso'::regproc),
  true,
  '1) il verbo: SECURITY DEFINER, search_path fissato; il guard dell''articolo: INVOKER');

-- ============================================================
-- 2-4 Senza il permesso, e senza il verbo
-- ============================================================
SELECT dbops.fn_pgtap_scrivi_override(
           'config.user_override_oggetti', auth_user_id,
           '{"app_label": "vendite", "model_name": "reso"}'::jsonb,
           '{"livello": "LETTURA", "motivo": "pgTAP porta riconsegna: oggetto in sola lettura"}'::jsonb)
  FROM _mondi WHERE lato = 'A';

SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riconsegna('A')), 'E_PERMESSO_NEGATO',
          '2) area vendite a TUTTO, oggetto vendite.reso a LETTURA: il verbo rifiuta');

SELECT is(pg_temp.riconsegne('A'), 0::bigint,
          '3) … e non scrive: nessuna riconsegna sul reso di A');

SELECT is(dbops.fn_pgtap_codice_errore(format(
            $q$WITH porta AS (
                 SELECT set_config('zeroerp.ddt_riconsegna', %L, true))
               INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa)
               SELECT %s, 1, %L, 'a mano con la porta', 1
                 FROM porta$q$,
            (SELECT reso_id FROM _resi WHERE lato = 'A')::text,
            (SELECT id FROM _bozza),
            (SELECT k FROM _art))),
          'E_ARTICOLO_SOLO_COMPONENTE',
          '4) l''app scrive la GUC con l''id del reso e la riga diretta: rifiutata, la porta chiede anche il proprietario');

-- La GUC del caso 4 si svuota qui: da proprietario la scrittura riesce, e la GUC
-- resterebbe accesa sui casi che seguono.
DO $gucvuota$ BEGIN PERFORM set_config('zeroerp.ddt_riconsegna', '', true); END $gucvuota$;

SELECT dbops.fn_pgtap_scrivi_override(
           'config.user_override_oggetti', (SELECT auth_user_id FROM _mondi WHERE lato = 'A'),
           '{"app_label": "vendite", "model_name": "reso"}'::jsonb,
           '{"livello": "TUTTO", "motivo": "pgTAP porta riconsegna"}'::jsonb);

-- ============================================================
-- 5-6 Due emittenti
-- ============================================================
SELECT is(dbops.fn_pgtap_codice_errore(pg_temp.riconsegna('B')), 'E_RESO_NOT_FOUND',
          '5) il reso di B: per A non c''e''');

-- ⚠️ Il reso di B si legge nel contesto dell'operatore di B: come A, sotto la row
--   security, le sue riconsegne non si vedono (ed e' proprio il caso 5).
DO $ctxb$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'B')); END $ctxb$;

SELECT is(pg_temp.riconsegne('B'), 0::bigint,
          '6) … e niente scritto sul reso di B');

DO $ctxa2$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(
    (SELECT auth_user_id FROM _mondi WHERE lato = 'A')); END $ctxa2$;

-- ============================================================
-- 7-8 Col permesso, dal verbo
-- ============================================================
-- ⚠️ La scrittura in un'istruzione e la rilettura nelle successive.
CREATE TEMP TABLE _esito ON COMMIT DROP AS
SELECT coalesce(dbops.fn_pgtap_codice_errore(pg_temp.riconsegna('A')), 'ok') AS esito;

SELECT is(
  (SELECT esito FROM _esito) || ' / '
  || (SELECT count(*) FROM vendite.resi_righe_riconsegne rr
        JOIN vendite.ddt_righe dr ON dr.id = rr.ddt_riga_id
       WHERE rr.resi_riga_id = (SELECT resi_riga_id FROM _resi WHERE lato = 'A')
         AND dr.articolo_id = (SELECT k FROM _art)),
  'ok / 1',
  '7) col permesso il verbo genera la bolla con l''articolo del reso, diventato solo componente');

SELECT is(coalesce(current_setting('zeroerp.ddt_riconsegna', true), ''), '',
          '8) dopo il verbo la GUC e'' vuota');

SELECT * FROM finish();
ROLLBACK;
