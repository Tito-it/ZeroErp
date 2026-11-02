-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: utilita fattura (critical, termini, fondi)
-- ------------------------------------------------------------
-- Indice test
-- 1) Riferimenti minimi presenti
-- 2) Inserimento fattura di test
-- 3) Tipo fondo fattura disponibile
-- 4) Totale fondi iniziale a zero
-- 5) Totale fondi considera solo righe attive
-- 6) Sync critical senza log critical
-- 7) Sync critical con log critical attivo
-- 8) Sync critical dopo disabilitazione log
-- 9) Resolve termini fallback su TP_1RATA
-- 10) Resolve termini errore su attivita_id non valido
-- 11) Cleanup completato
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

SELECT plan(14);

-- ============================================================
-- 0) Costanti e riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_costanti_fu AS
SELECT
  'pgtap_fattura_utils_critical_termini'::text AS test_scope;

CREATE TEMP TABLE tmp_tp_default_fu AS
WITH existing AS (
  SELECT tp.id, false AS created_by_test
  FROM config.termini_pagamento tp
  WHERE tp.codice_interno = 'TP_1RATA'
    AND tp.attivo IS TRUE
  ORDER BY tp.id
  LIMIT 1
), ins AS (
  -- rev 2026-07-31 (piano-db-satelliti-fattura 3a.2, D-I/D-E): la fixture
  -- valorizzava `unita_intervallo` (colonna eliminata) e `tipo_offset`
  -- (sostituito da `fine_mese`). Il vecchio 'N' -- «nessun offset» -- si
  -- scrive ora con gli offset a zero e fine_mese false.
  INSERT INTO config.termini_pagamento (
    codice,
    codice_interno,
    descrizione,
    numero_rate,
    intervallo,
    primo_offset_giorni,
    fine_mese,
    ripartizione,
    arrotondamento_metodo,
    arrotondamento_decimali,
    attivo
  )
  SELECT
    'TP1RATA_TEST_' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'),
    'TP_1RATA',
    'Termine default test pgTap',
    1,
    0,
    0,
    FALSE,
    'UGUALI',
    'HALF_UP',
    2,
    TRUE
  WHERE NOT EXISTS (SELECT 1 FROM existing)
  RETURNING id, true AS created_by_test
)
SELECT * FROM existing
UNION ALL
SELECT * FROM ins;

-- rev 2026-10-27 (lotto 4 di D7): il cliente si COSTRUISCE
--   (dbops.fn_pgtap_crea_cliente_ba, BA dell'azienda di chi agisce) e
--   l'emittente e' quello dell'operatore di contesto, col suo registro.
--   Prima il BA si pescava (l'ultimo inserito) e l'emittente da
--   emittenti_fiscali_billing_account: da zero non c'era niente. La
--   fattura resta scritta a mano: l'inserimento e' il test 2.
CREATE TEMP TABLE tmp_cli_fu AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('fattura utils critical');

CREATE TEMP TABLE tmp_refs_fu AS
SELECT
  script.fn_pgtap_registro_fattura(
    script.fn_pgtap_emittente_sr_operatore()
  ) AS registro_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
  (
    SELECT id
    FROM config.tipi_doc_fiscale
    WHERE attivo IS TRUE
    ORDER BY id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  (
    SELECT id
    FROM config.valute
    ORDER BY id
    LIMIT 1
  ) AS valuta_id,
  (
    SELECT t.id
    FROM tmp_tp_default_fu t
    LIMIT 1
  ) AS tp_default_id,
  (SELECT billing_account_id FROM tmp_cli_fu) AS billing_account_id;

SELECT ok(
  (
    SELECT registro_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
       AND tipo_doc_fiscale_id IS NOT NULL
       AND valuta_id IS NOT NULL
       AND tp_default_id IS NOT NULL
       AND billing_account_id IS NOT NULL
    FROM tmp_refs_fu
  ),
  'Riferimenti minimi presenti'
);

-- ============================================================
-- 1) Fattura di test
-- ============================================================
CREATE TEMP TABLE tmp_fattura_fu AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    valuta_id,
    totale_a_pagare,
    meta
  )
  SELECT
    r.registro_id,
    script.fn_data_operativa(),
    r.emittente_soggetto_ruolo_id,
    r.billing_account_id,
    r.tipo_doc_fiscale_id,
    r.valuta_id,
    50.00,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fu))
  FROM tmp_refs_fu r
  RETURNING id
)
SELECT * FROM ins;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_fattura_fu),
  'Inserimento fattura di test'
);

-- ============================================================
-- 2) Tipo fondo fattura
-- ============================================================
CREATE TEMP TABLE tmp_tipo_fondo_fu AS
SELECT t.id
FROM vendite.tipi_fondi_fattura t
WHERE t.attivo IS TRUE
  AND t.codice_interno = 'F_F_ADD_ACC'
ORDER BY t.id
LIMIT 1;

SELECT ok(
  (SELECT id IS NOT NULL FROM tmp_tipo_fondo_fu),
  'Tipo fondo fattura disponibile'
);

-- ============================================================
-- 3) Totale fondi fattura
-- ============================================================
SELECT is(
  vendite.fn_get_totale_fondi_fattura((SELECT id FROM tmp_fattura_fu)),
  0::numeric,
  'Totale fondi iniziale a zero'
);

INSERT INTO vendite.fatture_fondi_fattura (
  fattura_id,
  riferimento_fattura_id,
  tipo_fondo_fattura_id,
  importo,
  meta,
  attivo
)
SELECT
  (SELECT id FROM tmp_fattura_fu),
  NULL,
  (SELECT id FROM tmp_tipo_fondo_fu),
  x.importo,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fu), 'idx', x.idx),
  x.attivo
FROM (VALUES
  (1, 10.50::numeric, true),
  (2, 2.25::numeric, false)
) AS x(idx, importo, attivo);

SELECT is(
  vendite.fn_get_totale_fondi_fattura((SELECT id FROM tmp_fattura_fu)),
  10.50::numeric,
  'Totale fondi considera solo righe attive'
);

-- ============================================================
-- 4) Sync critical su fattura
-- ============================================================
SELECT lives_ok(
  format(
    'SELECT vendite.fn_sync_fattura_critical(%s)',
    (SELECT id::text FROM tmp_fattura_fu)
  ),
  'Sync critical senza log critical'
);

SELECT is(
  (SELECT critical FROM vendite.fatture WHERE id = (SELECT id FROM tmp_fattura_fu)),
  false,
  'Sync critical con stato iniziale false'
);

INSERT INTO vendite.fatture_log (
  fattura_id,
  data_ora,
  messaggio,
  status,
  disabilitato,
  meta
)
SELECT
  (SELECT id FROM tmp_fattura_fu),
  now(),
  'Errore critico test',
  'C',
  false,
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_fu));

SELECT lives_ok(
  format(
    'SELECT vendite.fn_sync_fattura_critical(%s)',
    (SELECT id::text FROM tmp_fattura_fu)
  ),
  'Sync critical con log critical attivo'
);

SELECT is(
  (SELECT critical FROM vendite.fatture WHERE id = (SELECT id FROM tmp_fattura_fu)),
  true,
  'Sync critical imposta true'
);

UPDATE vendite.fatture_log
SET disabilitato = true,
    data_update = now(),
    user_update = current_user
WHERE fattura_id = (SELECT id FROM tmp_fattura_fu)
  AND status = 'C';

SELECT lives_ok(
  format(
    'SELECT vendite.fn_sync_fattura_critical(%s)',
    (SELECT id::text FROM tmp_fattura_fu)
  ),
  'Sync critical dopo disabilitazione log'
);

SELECT is(
  (SELECT critical FROM vendite.fatture WHERE id = (SELECT id FROM tmp_fattura_fu)),
  false,
  'Sync critical torna false dopo disabilitazione'
);

-- ============================================================
-- 5) Resolve termini pagamento
-- ============================================================
-- ⚠️ 2026-08-01: adeguato alla firma nuova. 3b.1 ha riscritto
--   `fn_resolve_termini_pagamento` **per attivita'** — un solo parametro
--   `p_attivita_id`, ritorno a coppia `(termine, modalita')` — e questo test
--   la invocava ancora con la terna `(p_fattura_id, p_billing_account_id,
--   p_attivita_ids)`. Il file moriva qui, quindi da 3b.1 in poi non eseguiva
--   piu' NESSUNA asserzione: la nota di 3b.1 «nessun chiamante da adeguare»
--   guardava le funzioni DB e il backend, e non i pgTAP — che sono chiamanti
--   a tutti gli effetti.
-- Il fallback si esercita scegliendo un'attivita' per cui NESSUN livello a
-- monte del default risponde: niente termine sulla commessa e niente sul
-- cliente del BA padre. Il criterio di selezione e' lo STESSO della catena,
-- altrimenti il test misura un livello diverso da quello che crede.
-- rev 2026-10-27 (lotto 4 di D7): l'attivita' si COSTRUISCE — commessa del
--   cliente del test con una sua attivita' e la sorgente ROOT che
--   l'emissione pretende (dbops.fn_pgtap_crea_commessa), emessa dalla madre della pipeline — e il filtro della catena resta, sulla
--   sola attivita' costruita. Prima si pescava la prima attivita' del DB che
--   passava il filtro: da zero non c'era (skip), su dev era una qualunque.
CREATE TEMP TABLE tmp_cmm_fu AS
SELECT * FROM dbops.fn_pgtap_crea_commessa(
  'fattura utils termini', NULL,
  (SELECT billing_account_id FROM tmp_cli_fu), true, true);

DO $emit$ BEGIN
  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(
    p_commessa_id => (SELECT commessa_id FROM tmp_cmm_fu));
END $emit$;

CREATE TEMP TABLE tmp_att_fallback_fu AS
SELECT a.id
  FROM vendite.attivita_fatturabili a
  JOIN anagrafiche.billing_account ba  ON ba.id  = a.billing_account_id
  JOIN anagrafiche.billing_account bap ON bap.id = COALESCE(ba.parent_account_id, ba.id)
  LEFT JOIN vendite.commesse c   ON c.id = a.commessa_id
  LEFT JOIN anagrafiche.clienti cl ON cl.istanza_utility_id = bap.istanza_utility_id
 WHERE a.commessa_attivita_id = (SELECT attivita_id FROM tmp_cmm_fu)
   AND c.termine_pagamento_id IS NULL
   AND cl.termine_pagamento_id IS NULL
 ORDER BY a.id
 LIMIT 1;

SELECT CASE
  WHEN (SELECT count(*) FROM tmp_att_fallback_fu) = 0
    THEN skip('nessuna attivita con commessa e cliente privi di termine', 1)
  ELSE is(
    (
      SELECT x.termine_pagamento_id
      FROM vendite.fn_resolve_termini_pagamento(
        (SELECT id FROM tmp_att_fallback_fu)
      ) x
      LIMIT 1
    ),
    (SELECT tp_default_id FROM tmp_refs_fu),
    'Resolve termini fallback su TP_1RATA'
  )
END;

SELECT throws_ok(
  $$
    SELECT * FROM vendite.fn_resolve_termini_pagamento(-1);
  $$,
  'P0001',
  NULL,
  'Resolve termini errore su attivita_id non valido'
);

-- ============================================================
-- Cleanup
-- ============================================================
SELECT set_config('zeroerp.maintenance_allow_delete_logs', 'on', true);

DELETE FROM vendite.fatture_log
WHERE fattura_id = (SELECT id FROM tmp_fattura_fu);

DELETE FROM vendite.fatture_fondi_fattura
WHERE fattura_id = (SELECT id FROM tmp_fattura_fu);

UPDATE vendite.fatture
SET storicizza = false
WHERE id = (SELECT id FROM tmp_fattura_fu);

DELETE FROM vendite.fatture
WHERE id = (SELECT id FROM tmp_fattura_fu);

DELETE FROM config.termini_pagamento
WHERE id IN (
  SELECT t.id
  FROM tmp_tp_default_fu t
  WHERE t.created_by_test IS TRUE
);

SELECT ok(true, 'Cleanup completato');

SELECT * FROM finish();

ROLLBACK;
