-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgTAP test per Zero ERP
--
-- Test fn_crea_indirizzo_soggetto (building block):
--   1. Precondizioni: stradario e tipo indirizzo RESID esistono
--   2. Setup: crea soggetto PF di supporto + indirizzo_dettaglio
--   3. Creazione indirizzo normalizzato (RESID) con successo
--   4. Verifica record creato in indirizzi_soggetti
--   5. Errore: duplicato (stesso soggetto + stesso tipo)
--   6. Creazione secondo tipo (DOMFISC) con successo
--   7. Errore: chiave estranea nell'oggetto (E_CAMPO_NON_AMMESSO)
--   8. Errore: l'indirizzo non e' un oggetto (E_SCRIPT_CHIAMATA_NON_VALIDA)
--   9. Errore: p_soggetto_id NULL
--  10. Errore: tipo_indirizzo_codice_interno vuoto (E_TIPO_INDIRIZZO_NON_TROVATO)
--  11. Errore: tipo indirizzo inesistente (E_TIPO_INDIRIZZO_NON_TROVATO)
--  12. Errore: la chiave ritirata tipo_indirizzo_codice (E_CAMPO_NON_AMMESSO)
--
-- Rev 2026-11-01 (20261101-08): il tipo per codice interno si chiama
--   tipo_indirizzo_codice_interno (§6c); tipo_indirizzo_codice in ingresso si
--   rifiuta, senza alias (il 12 lo fissa).
--
-- ⭐ Rev 2026-10-18 (20261018-96, D-4 di Tid): la madre prende l'indirizzo in
--   jsonb, con la grammatica della gemella del ruolo (BB
--   anagrafiche.fn_indirizzo_elemento). I vecchi 7 e 8 provavano due guard
--   della madre che non ci sono piu': «dettaglio E libero» ora vale il
--   dettaglio (il normalize svuota i campi liberi, come nella madre del
--   ruolo), e la completezza la dice il guard della tabella (pgTAP
--   anagrafiche/test-indirizzo-libero-due-forme-v1). Al loro posto i rifiuti
--   dell'oggetto.
-- ------------------------------------------------------------
BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   `anagrafiche.soggetti` ha TRE guard DEFERRABLE INITIALLY DEFERRED —
--   indirizzi, contatti, dati societari — e li' la deferralita' e' il CONTRATTO
--   DEL DOMINIO: si crea il soggetto, poi il suo indirizzo, e la completezza si
--   verifica al COMMIT. E' per questo che anagrafiche.fn_crea_soggetto_pf puo'
--   restituire un soggetto ancora incompleto, ed e' cosi' che la usa il backend.
--   Forzare IMMEDIATE pretenderebbe l'indirizzo nell'istante stesso dell'INSERT
--   del soggetto: vieterebbe il pattern che il dominio ha scelto.
--   ⚠️ Resta un buco reale: senza la riga quei guard non vengono esercitati da
--   questo test, e la fixture lascia un soggetto che l'applicazione non
--   potrebbe committare. La correzione vera e' COMPLETARE LA FIXTURE
--   (indirizzo + contatti): allora la riga si rimette e il test verifica sul
--   serio. Brief: brief-db-pgtap-runner-rls-baseline §21.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

-- ⚠️ VINCOLI DIFFERITI — ⭐ LA FINESTRA SI RIAPRE, NON SI PRESUME.
--   Il soggetto nasce, POI riceve l'indirizzo: e' il contratto del dominio
--   (esenzione dichiarata sopra), e vuole i guard di `soggetti` DIFFERITI.
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   rossi di ASSERZIONE: il soggetto rifiutato all'INSERT, prima
--   dell'indirizzo che l'avrebbe completato.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(12);

-- =========================================================
-- Setup
-- =========================================================
CREATE TEMP TABLE tmp_ind_sogg_ctx (
    stradario_id          integer,
    indirizzo_dettaglio_id bigint,
    soggetto_id           uuid,
    indirizzo_soggetto_id bigint
);

-- Trova uno stradario attivo
INSERT INTO tmp_ind_sogg_ctx (stradario_id)
SELECT id FROM config.stradario ORDER BY id LIMIT 1;

-- =========================================================
-- 1) Precondizioni: stradario e tipo indirizzo RESID esistono
-- =========================================================
SELECT ok(
    (SELECT stradario_id FROM tmp_ind_sogg_ctx) IS NOT NULL
    AND EXISTS (SELECT 1 FROM config.tipi_indirizzi WHERE codice_interno = 'RES'),
    '1. Stradario e tipo indirizzo RESID esistono'
  );

-- =========================================================
-- 2) Setup: crea soggetto PF e indirizzo_dettaglio
-- =========================================================

-- Crea indirizzo_dettaglio via building block
UPDATE tmp_ind_sogg_ctx
SET indirizzo_dettaglio_id = (
    SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        p_stradario_id := (SELECT stradario_id FROM tmp_ind_sogg_ctx),
        p_civico := 88880
    )
  );

-- Crea soggetto PF di supporto
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'TestIndSogg',
        p_nome := 'Primo',
        p_codice_fiscale := %L,
        p_email := %L,
        p_sesso := 'M',
        p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
      ) $$,
      'PNZFDN78A01L219Y',
      'test_ind_sogg_' || floor(random() * 1000000)::text || '@test.local'
    ),
    '2. Soggetto PF di supporto creato'
  );

UPDATE tmp_ind_sogg_ctx
SET soggetto_id = (
    SELECT id FROM anagrafiche.soggetti
    WHERE cognome = 'TestIndSogg' AND nome = 'Primo'
    ORDER BY data_insert DESC LIMIT 1
  );

-- =========================================================
-- 3) Creazione indirizzo normalizzato (RESID) con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      jsonb_build_object('tipo_indirizzo_codice_interno', 'RES',
                         'indirizzo_dettaglio_id', (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx))
    ),
    '3. Creazione indirizzo RESID normalizzato senza errori'
  );

-- Salva id creato
UPDATE tmp_ind_sogg_ctx
SET indirizzo_soggetto_id = (
    SELECT id FROM anagrafiche.indirizzi_soggetti
    WHERE soggetto_id = (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
      AND tipo_indirizzo_id = (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'RES')
  );

-- =========================================================
-- 4) Verifica record creato in indirizzi_soggetti
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM anagrafiche.indirizzi_soggetti
      WHERE id = (SELECT indirizzo_soggetto_id FROM tmp_ind_sogg_ctx)
        AND soggetto_id = (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
        AND indirizzo_dettaglio_id = (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx)
        AND indirizzo_libero IS NULL
    ),
    '4. Record indirizzi_soggetti creato correttamente'
  );

-- =========================================================
-- 5) Errore: duplicato (stesso soggetto + stesso tipo RESID)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      jsonb_build_object('tipo_indirizzo_codice_interno', 'RES',
                         'indirizzo_dettaglio_id', (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx))
    ),
    'uq_indirizzi_soggetti_soggetto_tipo',
    '5. Errore duplicato soggetto + tipo indirizzo'
  );

-- =========================================================
-- 6) Creazione secondo tipo (DOMFISC) con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      jsonb_build_object('tipo_indirizzo_codice_interno', 'DOMFISC',
                         'indirizzo_dettaglio_id', (SELECT indirizzo_dettaglio_id FROM tmp_ind_sogg_ctx))
    ),
    '6. Creazione indirizzo DOMFISC senza errori'
  );

-- =========================================================
-- 7) Errore: chiave estranea (il nome di un parametro della firma vecchia)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      jsonb_build_object('tipo_indirizzo_codice_interno', 'SEDEOP',
                         'p_indirizzo_libero', 'Via Test 1')
    ),
    'campo p_indirizzo_libero non si pu',
    '7. Errore chiave estranea: E_CAMPO_NON_AMMESSO'
  );

-- =========================================================
-- 8) Errore: l'indirizzo non e' un oggetto
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, '[]'::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx)
    ),
    'un indirizzo non e'' un oggetto',
    '8. Errore indirizzo che non e'' un oggetto: E_SCRIPT_CHIAMATA_NON_VALIDA'
  );

-- =========================================================
-- 9) Errore: p_soggetto_id NULL
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(
      NULL::uuid,
      jsonb_build_object('tipo_indirizzo_codice_interno', 'RES', 'indirizzo_dettaglio_id', 1)) $$,
    'manca il soggetto',
    '9. Errore p_soggetto_id NULL'
  );

-- =========================================================
-- 10) Errore: tipo_indirizzo_codice_interno vuoto
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      jsonb_build_object('tipo_indirizzo_codice_interno', '', 'indirizzo_dettaglio_id', 1)
    ),
    'tipo di indirizzo - non esiste',
    '10. Errore tipo indirizzo codice vuoto'
  );

-- =========================================================
-- 11) Errore: tipo indirizzo inesistente
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      jsonb_build_object('tipo_indirizzo_codice_interno', 'ZZZZINESISTENTE', 'indirizzo_dettaglio_id', 1)
    ),
    'tipo di indirizzo ZZZZINESISTENTE non esiste',
    '11. Errore tipo indirizzo inesistente'
  );

-- =========================================================
-- 12) Errore: la chiave ritirata tipo_indirizzo_codice (20261101-08)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_indirizzo_soggetto(%L::uuid, %L::jsonb)$$,
      (SELECT soggetto_id FROM tmp_ind_sogg_ctx),
      jsonb_build_object('tipo_indirizzo_codice', 'SEDEOP', 'indirizzo_dettaglio_id', 1)
    ),
    'campo tipo_indirizzo_codice non si pu',
    '12. Errore chiave ritirata tipo_indirizzo_codice: E_CAMPO_NON_AMMESSO'
  );

SELECT * FROM finish();
ROLLBACK;
