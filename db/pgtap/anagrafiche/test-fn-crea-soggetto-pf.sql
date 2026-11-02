-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
-- pgTAP test per Zero ERP
--
-- Test fn_crea_soggetto_pf (building block):
--   1. Creazione soggetto PF con successo
--   2. Verifica tipo_soggetto_dettaglio_id = PR
--   3. Verifica ragione_sociale_completa normalizzata
--   4. Verifica contatto default creato
--   5. Errore: codice fiscale già presente
--   6. Errore: cognome vuoto
--   7. Errore: email NULL
--   8. Creazione con p_comune_nascita_id valorizzato
--   9. Verifica comune_id salvato correttamente su soggetti
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
--   anagrafiche.fn_crea_soggetto_pf restituisce un soggetto ancora incompleto
--   (esenzione dichiarata sopra): vuole i guard di `soggetti` DIFFERITI.
--   ⛔ Ma la riga di contesto qui sopra, quando COSTRUISCE il mondo (database
--   senza operatori: lo scratch `zeroerp_ci`, la CI), ESCE CON I VINCOLI
--   IMMEDIATE (rev 20260921-18, come ogni helper pgTAP). Fino al 2026-09-23 lo
--   mascherava un residuo: `create-gestore-conto-*` committavano l'operatore
--   `PGTR0001` e da li' la riga non costruiva piu'. Tolto quel COMMIT (brief
--   fixture-che-costruiscono giro 2), lo scratch appena ricostruito ha dato
--   rossi di ASSERZIONE: la creazione rifiutata all'INSERT.
--   La finestra la riapre il file, e dice da se' cosa vuole.
SET CONSTRAINTS ALL DEFERRED;

SELECT plan(9);

-- =========================================================
-- Setup
-- CF validi con checksum corretto (hardcoded, rollback a fine test)
-- =========================================================
CREATE TEMP TABLE tmp_sogg_pf_ctx (
  soggetto_id  uuid,
  test_cf      text,
  test_email   text
);

INSERT INTO tmp_sogg_pf_ctx (test_cf, test_email)
VALUES (
  'PNZFDN78A01L219Y',
  'test_sogg_pf_' || floor(random() * 1000000)::text || '@test.local'
);

-- =========================================================
-- 1) Creazione soggetto PF con successo
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'Ponzi',
        p_nome := 'Ferdinando',
        p_codice_fiscale := %L,
        p_email := %L,
        p_data_nascita := '1978-01-01',
        p_sesso := 'M',
        p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
      ) $$,
      (SELECT test_cf FROM tmp_sogg_pf_ctx),
      (SELECT test_email FROM tmp_sogg_pf_ctx)
    ),
    '1. fn_crea_soggetto_pf eseguita senza errori'
  );

-- Salva soggetto_id
UPDATE tmp_sogg_pf_ctx
SET soggetto_id = (
    SELECT id FROM anagrafiche.soggetti
    WHERE id_fiscale_univoco_cf_piva = UPPER((SELECT test_cf FROM tmp_sogg_pf_ctx))
  );

-- =========================================================
-- 2) Verifica tipo_soggetto_dettaglio_id = PR
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM anagrafiche.soggetti s
        JOIN config.tipi_soggetto_dettaglio tsd ON tsd.id = s.tipo_soggetto_dettaglio_id
      WHERE s.id = (SELECT soggetto_id FROM tmp_sogg_pf_ctx)
        AND tsd.codice_interno = 'PR'
    ),
    '2. Soggetto ha tipo_soggetto_dettaglio = PR'
  );

-- =========================================================
-- 3) Verifica ragione_sociale_completa normalizzata
-- =========================================================
SELECT ok(
    (SELECT ragione_sociale_completa FROM anagrafiche.soggetti
     WHERE id = (SELECT soggetto_id FROM tmp_sogg_pf_ctx)
    ) IS NOT NULL,
    '3. ragione_sociale_completa calcolata dal trigger'
  );

-- =========================================================
-- 4) Verifica contatto default creato
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM anagrafiche.contatti
      WHERE soggetto_id = (SELECT soggetto_id FROM tmp_sogg_pf_ctx)
        AND is_default = true
        AND email = (SELECT test_email FROM tmp_sogg_pf_ctx)
    ),
    '4. Contatto default creato con email corretta'
  );

-- =========================================================
-- 5) Errore: codice fiscale duplicato (stesso CF del test 1)
-- =========================================================
SELECT throws_matching(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'Bianchi',
        p_nome := 'Anna',
        p_codice_fiscale := %L,
        p_email := 'altro_' || %L,
        p_sesso := 'M',
        p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
      ) $$,
      (SELECT test_cf FROM tmp_sogg_pf_ctx),
      (SELECT test_email FROM tmp_sogg_pf_ctx)
    ),
    'Codice fiscale gia',
    '5. Errore codice fiscale duplicato'
  );

-- =========================================================
-- 6) Errore: cognome vuoto
-- Guard scatta PRIMA della validazione CF, quindi il CF
-- non viene mai verificato dal trigger.
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_soggetto_pf(
      p_cognome := '',
      p_nome := 'Test',
      p_codice_fiscale := 'LCCRLD80A01L736X',
      p_email := 'cognome_vuoto@test.local',
      p_sesso := 'M',
      p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
    ) $$,
    'Cognome obbligatorio',
    '6. Errore cognome vuoto'
  );

-- =========================================================
-- 7) Errore: email NULL
-- Guard scatta PRIMA della validazione CF.
-- =========================================================
SELECT throws_matching(
    $$SELECT anagrafiche.fn_crea_soggetto_pf(
      p_cognome := 'Test',
      p_nome := 'EmailNull',
      p_codice_fiscale := 'LCCRLD80A01L736X',
      p_email := NULL,
      p_sesso := 'M',
      p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
    ) $$,
    'Email obbligatoria',
    '7. Errore email NULL'
  );

-- =========================================================
-- 8) Creazione con p_comune_nascita_id valorizzato
-- =========================================================
SELECT lives_ok(
    format(
      $$SELECT anagrafiche.fn_crea_soggetto_pf(
        p_cognome := 'Pra',
        p_nome := 'Franco',
        p_codice_fiscale := 'PRAFNC80A01F205N',
        p_email := %L,
        p_data_nascita := '1980-01-01',
        p_sesso := 'M',
        p_comune_nascita_id := (SELECT id FROM config.comuni ORDER BY id LIMIT 1),
        p_tipo_soggetto_dettaglio_id := (SELECT id FROM config.tipi_soggetto_dettaglio WHERE codice_interno = 'PR')
      ) $$,
      'test_comune_nasc_' || floor(random() * 1000000)::text || '@test.local'
    ),
    '8. Creazione con p_comune_nascita_id senza errori'
  );

-- =========================================================
-- 9) Verifica comune_id salvato correttamente su soggetti
-- =========================================================
SELECT ok(
    EXISTS (
      SELECT 1 FROM anagrafiche.soggetti
      WHERE cognome = 'Pra' AND nome = 'Franco'
        AND comune_id = (SELECT id FROM config.comuni ORDER BY id LIMIT 1)
    ),
    '9. comune_id salvato correttamente su soggetti'
  );

SELECT * FROM finish();
ROLLBACK;
