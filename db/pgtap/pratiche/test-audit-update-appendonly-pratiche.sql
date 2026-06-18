-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: audit utente reale sulle tabelle ex-append-only di pratiche
--       (brief-db-audit-utente-reale-pratiche, Parte B).
--       Si sono aggiunte data_update/user_update alle 5 tabelle (20260618-04)
--       cosi' l'automation AUDIT_UPDATE le copre (trg_{table}_audit_data_user_upd
--       -> trgfn_audit_data_user_generic, che su INSERT imposta user_insert
--       dalla GUC app.jwt_user). Caso chiave: il GIORNALE registra l'utente reale.
--
-- NB: i test comportamentali (3-4) richiedono che l'automation audit sia stata
--     eseguita (CI: 90_end/ci_apply; manuale altrove) cosi' i trigger esistono.
--
-- Indice test:
-- 0)  Precondizioni
-- 1)  Le 5 tabelle hanno ORA data_update + user_update (verifica il changeset DDL)
-- 2)  Setup tipo prestazione
-- 3)  Con GUC app.jwt_user='mario.rossi' -> riga giornale user_insert='mario.rossi'
-- 4)  Senza GUC -> riga giornale user_insert=current_user (fallback)
-- 5)  Cleanup
-- ------------------------------------------------------------
SELECT plan(4);

-- =========================================================
-- 0) Precondizioni
-- =========================================================
INSERT INTO config.stati_pratiche (codice, codice_interno, descrizione, attivo)
VALUES ('BOZZA', 'BOZZA', 'Bozza', true)
ON CONFLICT (codice_interno) DO NOTHING;

INSERT INTO config.priorita_pratiche (codice, codice_interno, descrizione, sequenza, attivo)
VALUES ('NORMALE', 'NORMALE', 'Normale', 20, true)
ON CONFLICT (codice_interno) DO NOTHING;

CREATE TEMP TABLE tmp_auu_refs AS
SELECT
  (SELECT id FROM anagrafiche.emittenti_fiscali WHERE attivo = true LIMIT 1) AS emittente_id,
  (SELECT id FROM config.stati_pratiche WHERE codice_interno = 'BOZZA') AS st_bozza,
  (SELECT id FROM config.priorita_pratiche WHERE codice_interno = 'NORMALE') AS priorita_id;

SELECT ok(
    (SELECT emittente_id IS NOT NULL AND st_bozza IS NOT NULL AND priorita_id IS NOT NULL
       FROM tmp_auu_refs),
    '0. Precondizioni soddisfatte'
);

-- =========================================================
-- 1) Le 5 tabelle hanno ORA data_update + user_update
-- =========================================================
SELECT is(
    (SELECT count(*)::int
       FROM information_schema.columns
      WHERE table_schema = 'pratiche'
        AND column_name IN ('data_update','user_update')
        AND table_name IN ('giornale','allegati_pratiche','allegati_flussi',
                           'template_flussi_prerequisiti','template_flussi_canali')),
    10,
    '1. Le 5 tabelle append-only hanno ora entrambe data_update + user_update (5x2)'
);

-- =========================================================
-- 2) Setup tipo prestazione
-- =========================================================
CREATE TEMP TABLE tmp_auu_tp AS WITH ins AS (
  INSERT INTO pratiche.tipi_prestazione (codice, codice_interno, descrizione, attivo)
  VALUES ('TEST_AUU', 'TEST_AUU', 'Tipo test audit update append-only', true)
  ON CONFLICT (codice_interno) DO UPDATE SET descrizione = EXCLUDED.descrizione
  RETURNING id
)
SELECT id AS tp_id FROM ins;

-- =========================================================
-- 3) Con GUC -> giornale.user_insert = utente reale
--    (INSERT pratica -> trgfn_pratiche_giornale_ins inserisce nel giornale
--     SENZA user_insert -> lo forza il trigger audit dell'automation)
-- =========================================================
SELECT set_config('app.jwt_user', 'mario.rossi', false);

CREATE TEMP TABLE tmp_auu_p1 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_auu_refs),
    (SELECT tp_id FROM tmp_auu_tp),
    (SELECT st_bozza FROM tmp_auu_refs),
    (SELECT priorita_id FROM tmp_auu_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT is(
    (SELECT user_insert FROM pratiche.giornale
      WHERE pratica_id = (SELECT pratica_id FROM tmp_auu_p1)
      ORDER BY id LIMIT 1),
    'mario.rossi',
    '3. Giornale: user_insert = utente reale dalla GUC app.jwt_user'
);

-- =========================================================
-- 4) Senza GUC -> fallback CURRENT_USER
-- =========================================================
SELECT set_config('app.jwt_user', '', false);

CREATE TEMP TABLE tmp_auu_p2 AS WITH ins AS (
  INSERT INTO pratiche.pratiche (emittente_fiscale_id, tipo_prestazione_id, stato_id, priorita_id)
  VALUES (
    (SELECT emittente_id FROM tmp_auu_refs),
    (SELECT tp_id FROM tmp_auu_tp),
    (SELECT st_bozza FROM tmp_auu_refs),
    (SELECT priorita_id FROM tmp_auu_refs)
  )
  RETURNING id
)
SELECT id AS pratica_id FROM ins;

SELECT is(
    (SELECT user_insert FROM pratiche.giornale
      WHERE pratica_id = (SELECT pratica_id FROM tmp_auu_p2)
      ORDER BY id LIMIT 1),
    current_user::text,
    '4. Giornale: user_insert = CURRENT_USER quando la GUC non e'' impostata'
);

-- =========================================================
-- 5) Cleanup
-- =========================================================
SELECT set_config('app.jwt_user', '', false);
DELETE FROM pratiche.giornale
WHERE pratica_id IN (
    SELECT id FROM pratiche.pratiche
    WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_auu_tp)
);
DELETE FROM pratiche.pratiche
WHERE tipo_prestazione_id = (SELECT tp_id FROM tmp_auu_tp);
DELETE FROM pratiche.tipi_prestazione
WHERE id = (SELECT tp_id FROM tmp_auu_tp);

SELECT * FROM finish();
