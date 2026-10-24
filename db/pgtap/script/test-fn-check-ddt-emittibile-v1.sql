-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: script.fn_check_ddt_emittibile (single source dei motivi ostativi
--       all'emissione DDT) + capability fn_available_actions_ddt che la
--       consuma + regressione guard post-refactor.
--       Brief: brief-db-guard-righe-avanzamento-stato §1a-bis Rev 2
--       (migrations 20260719-01/-02/-03).
-- ------------------------------------------------------------
-- Indice test (1..10):
--   1) fn_check_ddt_emittibile esiste
--   2) DDT completo, causale NON fatturabile, righe senza prezzo -> [] (il
--      "solo trasporto" e' emittibile: righe senza prezzo, non zero righe)
--   3) DDT senza causale -> motivi contengono E_DDT_CAUSALE_OBBLIGATORIA
--   4) DDT senza righe attive -> motivi contengono E_DDT_EMISSIONE_SENZA_RIGHE
--   5) causale fatturabile (VENDITA) + riga senza prezzo risolvibile ->
--      motivi contengono E_DDT_PREZZO_NON_RISOLVIBILE
--   6) DDT senza indirizzi -> motivi contengono E_INDIRIZZO_DOC_OBBLIGATORIO
--      (skip se il seed non definisce indirizzi obbligatori per ambito DDT)
--   7) capability: DDT senza causale -> azione verso EMESSO enabled=false
--   8) capability: ...con reason='CAUSALE_MANCANTE' e reasons array valorizzato
--   9) regressione guard: UPDATE a EMESSO senza causale -> P0001 (544 invariato)
--  10) regressione guard: DDT completo non fatturabile -> emissione PASSA
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

SELECT plan(10);

-- ⛔ L'UTENTE DI SESSIONE NON SI FISSA A MANO (2026-09-23). Queste due righe
--   sovrascrivevano il contesto appena aperto con l'utente 1, che su un
--   database ricostruito non esiste e non ha nessun emittente: la fixture
--   scriveva come nessuno. La veste e l'utente li mette gia' la riga di
--   contesto, che sceglie un operatore VERO (e lo costruisce se non c'e').

-- ============================================================
-- Riferimenti (stessa forma di test-ddt-solo-trasporto-causale-v1)
-- ============================================================
-- ⛔ IL CLIENTE SI COSTRUISCE (2026-09-23). La riga di contesto costruisce
--   azienda e operatore, non un cliente: su un database ricostruito
--   `anagrafiche.billing_account` resta a ZERO e il riferimento pescato usciva
--   NULL. Il BB costruisce il cliente legato all'azienda di chi agisce.
CREATE TEMP TABLE tmp_mondo_bb AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('check ddt emittibile');

CREATE TEMP TABLE tmp_chk_refs AS
SELECT
  (SELECT billing_account_id FROM tmp_mondo_bb)                                              AS billing_account_id,
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): il ruolo del cliente
  --   e' quello del BA scelto qui (prima: il primo ruolo del database,
  --   scollegato dal BA; le FK composte verso il BA lo rifiutano).
  (SELECT b_sr.soggetto_ruolo_id FROM anagrafiche.billing_account b_sr
    WHERE b_sr.id = (SELECT billing_account_id FROM tmp_mondo_bb)) AS soggetto_ruolo_id,
-- 🔴 rev 2026-10-13 (brief-db-articoli-ammessi-per-documento D-1/D-2): l'articolo si
--   COSTRUISCE. Prima si pescava dal catalogo (il primo per id, o il piu' recente):
--   il primo per id e' l'onere del seed ONERE_SENZA_CONTRATTO (natura servizio), e
--   da 20261013-42 ordine e bolla portano solo merce. Un articolo costruito ha solo
--   le proprieta' che il test gli da' (merce, non gestito a magazzino).
  dbops.fn_pgtap_crea_articolo('PGT-CDE-ART', false)                      AS articolo_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)              AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1) AS iva_id,
  -- ⛔ L'emittente NON si pesca, si DERIVA (2026-09-23, guida pgTAP §5).
  script.fn_pgtap_emittente_operatore()  AS emittente_fiscale_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='DRAFT'  LIMIT 1) AS stato_draft_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO' LIMIT 1) AS stato_emesso_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' LIMIT 1)      AS causale_vendita_id,
  (SELECT c.id FROM config.causali_trasporto c
    WHERE c.attivo IS TRUE AND c.fatturabile IS FALSE ORDER BY c.id LIMIT 1)          AS causale_non_fatt_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')     AS tipo_ind_con_id;

-- Helper: DDT standalone in DRAFT, causale parametrica, con/senza riga e indirizzo.
CREATE OR REPLACE FUNCTION pg_temp.mk_ddt(p_causale bigint, p_con_riga boolean, p_con_indirizzo boolean)
RETURNS bigint AS $$
DECLARE r RECORD; v_ddt bigint;
BEGIN
  SELECT * INTO r FROM tmp_chk_refs;
  INSERT INTO vendite.ddt (destinatario_soggetto_ruolo_id, stato_doc_ddt_id, data,
    billing_account_id, valuta_id, causale_trasporto_id, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.stato_draft_id, DATE '2026-07-19',
          r.billing_account_id, r.valuta_id, p_causale,
          r.emittente_fiscale_id, false, jsonb_build_object('test_scope','pgtap_chk_emittibile'))
  RETURNING id INTO v_ddt;
  IF p_con_riga THEN
    INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
      qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ddt, 1, r.articolo_id, 'Riga senza prezzo', 5, 5, NULL, r.iva_id, true, false,
            jsonb_build_object('test_scope','pgtap_chk_emittibile'));
  END IF;
  IF p_con_indirizzo THEN
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  END IF;
  RETURN v_ddt;
END $$ LANGUAGE plpgsql;

-- Helper: motivi della fn_check per un ddt_id (passa la ROW come da firma).
CREATE OR REPLACE FUNCTION pg_temp.motivi(p_ddt_id bigint)
RETURNS jsonb AS $$
  SELECT script.fn_check_ddt_emittibile(d) FROM vendite.ddt d WHERE d.id = p_ddt_id;
$$ LANGUAGE sql;

-- ============================================================
-- 1) la fn esiste
-- ============================================================
SELECT has_function('script', 'fn_check_ddt_emittibile',
  '1) esiste script.fn_check_ddt_emittibile');

-- ============================================================
-- Fixture: i 4 DDT dei casi
-- ============================================================
CREATE TEMP TABLE tmp_chk_ddt AS
SELECT
  pg_temp.mk_ddt((SELECT causale_non_fatt_id FROM tmp_chk_refs), true,  true)  AS ddt_ok,
  pg_temp.mk_ddt(NULL,                                            true,  true)  AS ddt_senza_causale,
  pg_temp.mk_ddt((SELECT causale_non_fatt_id FROM tmp_chk_refs), false, true)  AS ddt_senza_righe,
  pg_temp.mk_ddt((SELECT causale_vendita_id  FROM tmp_chk_refs), true,  true)  AS ddt_prezzo_ko;

-- ============================================================
-- 2) solo trasporto (non fatturabile, righe senza prezzo) -> emittibile
-- ============================================================
SELECT is(
  pg_temp.motivi((SELECT ddt_ok FROM tmp_chk_ddt)),
  '[]'::jsonb,
  '2) DDT completo con causale non fatturabile -> nessun motivo ostativo'
);

-- ============================================================
-- 3) causale mancante
-- ============================================================
SELECT ok(
  pg_temp.motivi((SELECT ddt_senza_causale FROM tmp_chk_ddt))
    @> '[{"codice": "E_DDT_CAUSALE_OBBLIGATORIA"}]'::jsonb,
  '3) DDT senza causale -> motivo E_DDT_CAUSALE_OBBLIGATORIA'
);

-- ============================================================
-- 4) zero righe attive
-- ============================================================
SELECT ok(
  pg_temp.motivi((SELECT ddt_senza_righe FROM tmp_chk_ddt))
    @> '[{"codice": "E_DDT_EMISSIONE_SENZA_RIGHE"}]'::jsonb,
  '4) DDT senza righe attive -> motivo E_DDT_EMISSIONE_SENZA_RIGHE'
);

-- ============================================================
-- 5) causale fatturabile + prezzo non risolvibile (standalone: nessun
--    ordine da cui ereditare)
-- ============================================================
SELECT ok(
  pg_temp.motivi((SELECT ddt_prezzo_ko FROM tmp_chk_ddt))
    @> '[{"codice": "E_DDT_PREZZO_NON_RISOLVIBILE"}]'::jsonb,
  '5) causale VENDITA + riga senza prezzo risolvibile -> motivo E_DDT_PREZZO_NON_RISOLVIBILE'
);

-- ============================================================
-- 6) indirizzi mancanti — data-dependent: skip se il seed non definisce
--    indirizzi obbligatori per l'ambito DDT
-- ============================================================
SELECT CASE WHEN array_length(script.fn_indirizzi_obbligatori_mancanti('DDT', NULL), 1) IS NOT NULL
  THEN ok(
    pg_temp.motivi(pg_temp.mk_ddt((SELECT causale_non_fatt_id FROM tmp_chk_refs), true, false))
      @> '[{"codice": "E_INDIRIZZO_DOC_OBBLIGATORIO"}]'::jsonb,
    '6) DDT senza indirizzi -> motivo E_INDIRIZZO_DOC_OBBLIGATORIO')
  ELSE skip('6) nessun indirizzo obbligatorio per ambito DDT nel seed', 1)
END;

-- ============================================================
-- 7-8) capability: azione verso EMESSO disabled + reason dal primo motivo
-- ============================================================
SELECT is(
  (SELECT a FROM jsonb_array_elements(
      script.fn_available_actions_ddt((SELECT ddt_senza_causale FROM tmp_chk_ddt))
        -> 'available_actions') AS a
    WHERE a ->> 'target_state' = 'EMESSO') -> 'enabled',
  'false'::jsonb,
  '7) capability: DDT senza causale -> azione verso EMESSO disabled'
);

SELECT ok(
  (SELECT (a ->> 'reason') = 'CAUSALE_MANCANTE'
      AND jsonb_array_length(a -> 'reasons') >= 1
     FROM jsonb_array_elements(
       script.fn_available_actions_ddt((SELECT ddt_senza_causale FROM tmp_chk_ddt))
         -> 'available_actions') AS a
    WHERE a ->> 'target_state' = 'EMESSO'),
  '8) capability: reason=CAUSALE_MANCANTE e array reasons valorizzato'
);

-- ============================================================
-- 9) regressione guard: il click (ipotetico) fallisce ancora con P0001
-- ============================================================
SELECT throws_ok(
  format(
    $$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$$,
    (SELECT stato_emesso_id FROM tmp_chk_refs),
    (SELECT ddt_senza_causale FROM tmp_chk_ddt)
  ),
  'P0001',
  NULL,
  '9) emissione senza causale -> bloccata dal guard (544 invariato post-refactor)'
);

-- ============================================================
-- 10) regressione guard: il DDT in regola si emette
-- ============================================================
SELECT lives_ok(
  format(
    $$UPDATE vendite.ddt SET stato_doc_ddt_id = %s WHERE id = %s$$,
    (SELECT stato_emesso_id FROM tmp_chk_refs),
    (SELECT ddt_ok FROM tmp_chk_ddt)
  ),
  '10) DDT completo (solo trasporto) -> emissione passa'
);

SELECT * FROM finish();
ROLLBACK;
