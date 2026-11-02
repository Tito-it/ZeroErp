-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: allineamento lotti/attivita stato_esecuzione (changeset 20260222-01..07)
-- rev 2026-10-27 (brief-modello-documento-vendita §15, giro 11, F-4):
--   vendite.fn_set_fatturazione_lotto_stato e' ritirata (20261027-07): nessuno la
--   chiamava, e la regola dello stato del job sta nella matrice
--   config.transizioni_stati_lotto_job, applicata dal guard a ogni scrittura. I test
--   6, 9, 11 scrivono lo stato come lo scrive il runner (UPDATE, giudicato dal guard);
--   i test 7, 8, 12 provano la mappatura stato del job -> stato_esecuzione sul BB che
--   la fa per tutti, vendite.fn_resolve_stato_esecuzione (la funzione ritirata ne era
--   una chiamante, come la sync del lotto).
-- ⚠️ Attese cambiate: 7, 8, 12 guardano il BB e non piu' le righe del ponte (che la
--   funzione ritirata riscriveva da se'); il 10 guarda il solo stato del lotto,
--   perche' lo stato_esecuzione del ponte non lo scriveva il percorso vivo.
-- ------------------------------------------------------------
-- Indice test (1..15):
-- 1) Riferimenti minimi presenti
-- 2) Colonna attivita_fatturabili.stato_esecuzione presente
-- 3) attivita_fatturabili.stato_esecuzione nullable
-- 4) CHECK stato_esecuzione ammette COMPLETED e rifiuta OK
-- 5) stato_esecuzione=OK non ammesso su fatturazione_lotti_fatture
-- 6) COMPLETATO -> IN_ESECUZIONE, la scrittura del runner (rev 2026-10-27)
-- 7) Il BB della mappatura: non critical, lotto IN_ESECUZIONE -> RUNNING
-- 8) Il BB della mappatura: critical -> ERRORE
-- 9) COMPLETATO RIFIUTATO con una fattura in ERRORE (rev 2026-09-23, 20260923-30)
-- 10) ...e niente e' cambiato: lotto IN_ESECUZIONE
-- 11) tolta la fattura in errore, COMPLETATO passa
-- 12) Il BB della mappatura: non critical, lotto COMPLETATO -> COMPLETED
-- 13) fn_resolve_lotto_utility_emittente risolve utility
-- 14) fn_resolve_lotto_utility_emittente blocca utility incoerente
-- 15) fn_resolve_stato_esecuzione: IN_ESECUZIONE -> RUNNING
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

SELECT plan(15);

CREATE TEMP TABLE tmp_costanti_las AS
SELECT
  ('pgtap_las_' || to_char(clock_timestamp(), 'YYMMDDHH24MISSMS'))::text AS test_scope,
  uuidv7() AS lock_batch_id;

-- rev 2026-10-27 (lotto 4 di D7): cliente e articolo si COSTRUISCONO
--   (dbops.fn_pgtap_crea_cliente_ba, dbops.fn_pgtap_crea_articolo) e
--   l'emittente e' quello di chi agisce (script.fn_pgtap_emittente_sr_operatore).
--   Prima BA, utility, emittente, istanza e articolo si pescavano dal primo BA
--   con un emittente e dall'ultimo articolo del DB: da zero non c'erano. Tipo
--   documento (dal ponte tipo->registro), valuta e stato sono letture di
--   catalogo di seed; il registro lo scrive l'UPDATE qui sotto, per emittente.
CREATE TEMP TABLE tmp_cli_las AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('lotti attivita stato esecuzione');

CREATE TEMP TABLE tmp_refs_las AS
SELECT
  NULL::bigint AS registro_id,
  (
    SELECT m.tipo_doc_fiscale_id
    FROM vendite.tipi_doc_fiscale_registri m
    JOIN config.tipi_doc_fiscale t ON t.id = m.tipo_doc_fiscale_id
    WHERE t.attivo IS TRUE
    ORDER BY m.id
    LIMIT 1
  ) AS tipo_doc_fiscale_id,
  c.billing_account_id,
  c.utility_id,
  script.fn_pgtap_emittente_sr_operatore() AS emittente_soggetto_ruolo_id,
  (
    SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1
  ) AS valuta_id,
  (
    SELECT s.id
    FROM config.stati_doc_fiscale s
    WHERE s.codice_interno = 'DRAFT' AND s.attivo IS TRUE
    ORDER BY s.id
    LIMIT 1
  ) AS stato_draft_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-LAS-V2') AS articolo_id,
  c.istanza_utility_id
FROM tmp_cli_las c;

-- ⛔ IL REGISTRO SI ALLINEA ALL'EMITTENTE, e prima non lo faceva.
--   La riga sopra sceglieva «un registro qualunque» accanto a un emittente che
--   viene da un'altra parte: che i due coincidessero era un CASO, e dal
--   2026-08-30 vendite.trgfn_fatture_guard_registro_emittente non lo ammette
--   piu'. L'helper risponde con il registro di QUESTO emittente, creandolo se
--   non ce n'e' uno — la riga vive nella transazione del test.
UPDATE tmp_refs_las SET registro_id = script.fn_pgtap_registro_fattura(emittente_soggetto_ruolo_id);
SELECT ok(
  (
    SELECT registro_id IS NOT NULL
       AND tipo_doc_fiscale_id IS NOT NULL
       AND billing_account_id IS NOT NULL
       AND utility_id IS NOT NULL
       AND emittente_soggetto_ruolo_id IS NOT NULL
       AND valuta_id IS NOT NULL
       AND stato_draft_id IS NOT NULL
       AND articolo_id IS NOT NULL
       AND istanza_utility_id IS NOT NULL
    FROM tmp_refs_las
  ),
  'Riferimenti minimi presenti'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'stato_esecuzione'
  ),
  'Colonna attivita_fatturabili.stato_esecuzione presente'
);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'vendite'
      AND c.table_name = 'attivita_fatturabili'
      AND c.column_name = 'stato_esecuzione'
      AND c.is_nullable = 'YES'
  ),
  'attivita_fatturabili.stato_esecuzione ammessa a NULL fuori pipeline'
);

SELECT ok(
  (
    SELECT pg_get_constraintdef(c.oid) ~ '''COMPLETED'''
       AND pg_get_constraintdef(c.oid) NOT LIKE '%''OK''%'
    FROM pg_constraint c
    WHERE c.conrelid = 'vendite.attivita_fatturabili'::regclass
      AND c.conname = 'chk_attivita_fatt_stato_esecuzione'
  ),
  'CHECK stato_esecuzione ammette COMPLETED e rifiuta OK'
);

CREATE TEMP TABLE tmp_lotto_fat_las AS
SELECT vendite.fn_create_fatturazione_lotto(
  p_competenza_mese => date_trunc('month', script.fn_data_operativa())::date,
  p_tipo_doc_fiscale_id => (SELECT tipo_doc_fiscale_id FROM tmp_refs_las),
  p_utility_id => (SELECT utility_id FROM tmp_refs_las),
  p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_las),
  p_lock_batch_id => NULL,
  p_meta => jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'lotto_fat'),
  p_emittente_soggetto_ruolo_id => (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_las)
) AS lotto_id;

CREATE TEMP TABLE tmp_fatture_las AS
WITH ins AS (
  INSERT INTO vendite.fatture (
    registro_id,
    data,
    emittente_soggetto_ruolo_id,
    billing_account_id,
    tipo_doc_fiscale_id,
    stato_doc_fiscale_id,
    valuta_id,
    totale_a_pagare,
    critical,
    meta
  )
  SELECT
    (SELECT registro_id FROM tmp_refs_las),
    script.fn_data_operativa(),
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_las),
    (SELECT billing_account_id FROM tmp_refs_las),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_las),
    (SELECT stato_draft_id FROM tmp_refs_las),
    (SELECT valuta_id FROM tmp_refs_las),
    10.00,
    false,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'non_critical')
  UNION ALL
  SELECT
    (SELECT registro_id FROM tmp_refs_las),
    script.fn_data_operativa(),
    (SELECT emittente_soggetto_ruolo_id FROM tmp_refs_las),
    (SELECT billing_account_id FROM tmp_refs_las),
    (SELECT tipo_doc_fiscale_id FROM tmp_refs_las),
    (SELECT stato_draft_id FROM tmp_refs_las),
    (SELECT valuta_id FROM tmp_refs_las),
    12.00,
    true,
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'critical')
  RETURNING id, critical, stato_doc_fiscale_id
)
SELECT * FROM ins;

SELECT throws_ok(
  $$
  INSERT INTO vendite.fatturazione_lotti_fatture (
    lotto_id,
    fattura_id,
    stato_doc_fiscale_id,
    stato_esecuzione,
    meta
  )
  SELECT
    (SELECT lotto_id FROM tmp_lotto_fat_las),
    (SELECT id FROM tmp_fatture_las ORDER BY id LIMIT 1),
    (SELECT stato_draft_id FROM tmp_refs_las),
    'OK',
    jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'invalid_enum_lotto_fatture');
  $$,
  '23514',
  NULL,
  'stato_esecuzione=OK non ammesso su fatturazione_lotti_fatture'
);

INSERT INTO vendite.fatturazione_lotti_fatture (
  lotto_id,
  fattura_id,
  stato_doc_fiscale_id,
  stato_esecuzione,
  meta
)
SELECT
  (SELECT lotto_id FROM tmp_lotto_fat_las),
  f.id,
  f.stato_doc_fiscale_id,
  'PENDING',
  jsonb_build_object('test_scope', (SELECT test_scope FROM tmp_costanti_las), 'case', 'seed_pendente')
FROM tmp_fatture_las f;

UPDATE vendite.fatturazione_lotti
   SET stato_lotto = 'COMPLETATO',
       stato_operativo = 'APERTO',
       data_update = now(),
       user_update = current_user
 WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las);

SELECT lives_ok(
  $$
  UPDATE vendite.fatturazione_lotti
     SET stato_lotto = 'IN_ESECUZIONE'
   WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las);
  $$,
  'COMPLETATO -> IN_ESECUZIONE ammesso dalla matrice (la scrittura del runner)'
);

SELECT is(
  vendite.fn_resolve_stato_esecuzione(
    p_stato_source => (SELECT stato_lotto FROM vendite.fatturazione_lotti
                        WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las)),
    p_has_critical => false),
  'RUNNING',
  'Non critical -> RUNNING con lotto IN_ESECUZIONE (il BB della mappatura)'
);

SELECT is(
  vendite.fn_resolve_stato_esecuzione(
    p_stato_source => (SELECT stato_lotto FROM vendite.fatturazione_lotti
                        WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las)),
    p_has_critical => true),
  'ERRORE',
  'Critical -> ERRORE con lotto IN_ESECUZIONE (il BB della mappatura)'
);

-- ⛔ rev 2026-10-27: la fattura in ERRORE il 9 la deve TROVARE. Prima la scriveva
--   la funzione ritirata (riscriveva il ponte col BB della mappatura); senza questa
--   riga il lotto non e' fermo e il 9 non trova nulla da rifiutare. Il ponte si
--   scrive col BB, come lo scriveva lei.
UPDATE vendite.fatturazione_lotti_fatture lf
   SET stato_esecuzione = vendite.fn_resolve_stato_esecuzione(
         p_stato_source => (SELECT l.stato_lotto FROM vendite.fatturazione_lotti l
                             WHERE l.id = lf.lotto_id),
         p_has_critical => f.critical)
  FROM tmp_fatture_las f
 WHERE lf.fattura_id = f.id
   AND lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_fat_las);

-- ⛔ REV 2026-09-23 (20260923-30, brief-db-annullamento-chiude-la-vita §9.3).
--   Fino a quel giorno qui il lotto andava COMPLETATO con la fattura critica in
--   ERRORE, e il vecchio test 11 fissava come ATTESO «Critical resta ERRORE con
--   lotto COMPLETATO»: cioe' la contraddizione che vw_lotti_chiusi_con_gruppi_in_errore
--   esiste per segnalare. Da quel giorno il database la rifiuta: COMPLETATO su
--   un lotto fermo non si scrive (trg_fatturazione_lotti_a10_guard_completato_upd).
--   ⇒ Il 9 prova il rifiuto; la mappatura COMPLETATO -> COMPLETED (vecchio 10)
--   si prova DOPO aver tolto dal lotto la fattura in errore, che e' il gesto
--   vero con cui un lotto si sblocca.
SELECT throws_like(
  $$
  UPDATE vendite.fatturazione_lotti
     SET stato_lotto = 'COMPLETATO'
   WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las);
  $$,
  '%risultare completato%',
  'COMPLETATO rifiutato: nel lotto c''e'' una fattura in ERRORE (E_LOTTO_COMPLETATO_NON_GUADAGNATO)'
);

SELECT is(
  (SELECT l.stato_lotto FROM vendite.fatturazione_lotti l
    WHERE l.id = (SELECT lotto_id FROM tmp_lotto_fat_las)),
  'IN_ESECUZIONE',
  'Rifiutato: il lotto resta IN_ESECUZIONE'
);

-- La fattura in errore esce dal lotto: da qui il lotto non e' piu' fermo.
DELETE FROM vendite.fatturazione_lotti_fatture lf
 USING tmp_fatture_las f
 WHERE lf.fattura_id = f.id
   AND lf.lotto_id = (SELECT lotto_id FROM tmp_lotto_fat_las)
   AND f.critical IS TRUE;

SELECT lives_ok(
  $$
  UPDATE vendite.fatturazione_lotti
     SET stato_lotto = 'COMPLETATO'
   WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las);
  $$,
  'IN_ESECUZIONE -> COMPLETATO, tolta la fattura in errore'
);

SELECT is(
  vendite.fn_resolve_stato_esecuzione(
    p_stato_source => (SELECT stato_lotto FROM vendite.fatturazione_lotti
                        WHERE id = (SELECT lotto_id FROM tmp_lotto_fat_las)),
    p_has_critical => false),
  'COMPLETED',
  'Non critical -> COMPLETED con lotto COMPLETATO (il BB della mappatura)'
);

SELECT is(
  (
    SELECT r.resolved_utility_id
    FROM vendite.fn_resolve_lotto_utility_emittente(
      p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_las),
      p_utility_id => NULL,
      p_emittente_soggetto_ruolo_id => NULL,
      p_scope => 'TEST',
      p_caller => 'test_lotti_attivita_stato_esecuzione_v2',
      p_check_emittente_attivo => true
    ) r
  ),
  (SELECT utility_id FROM tmp_refs_las),
  'fn_resolve_lotto_utility_emittente risolve utility da BA'
);

SELECT throws_ok(
  $$
  SELECT *
  FROM vendite.fn_resolve_lotto_utility_emittente(
    p_billing_account_id => (SELECT billing_account_id FROM tmp_refs_las),
    p_utility_id => (SELECT utility_id + 99999 FROM tmp_refs_las),
    p_emittente_soggetto_ruolo_id => NULL,
    p_scope => 'TEST',
    p_caller => 'test_lotti_attivita_stato_esecuzione_v2',
    p_check_emittente_attivo => true
  );
  $$,
  'P0001',
  NULL,
  'fn_resolve_lotto_utility_emittente blocca utility incoerente con BA'
);

SELECT is(
  vendite.fn_resolve_stato_esecuzione(
    p_stato_source => 'IN_ESECUZIONE',
    p_has_critical => false,
    p_fatturato => false,
    p_default_stato_esecuzione => 'PENDING'
  ),
  'RUNNING'::varchar,
  'fn_resolve_stato_esecuzione mappa IN_ESECUZIONE -> RUNNING'
);

-- Adeguamento 2026-08-04 (D-M, changeSet 20260804-19): il test
-- «esclusa=true mantiene stato corrente» E' STATO RIMOSSO, non riscritto.
-- Verificava il primo ramo dell'helper, che con il flag `esclusa` e' stato
-- eliminato: `p_esclusa` e `p_current_stato_esecuzione` non esistono piu'
-- nella firma (da sei parametri a quattro). Non c'e' un comportamento
-- equivalente da spostare altrove — il ramo non c'e' proprio piu', quindi
-- riscrivere il test vorrebbe dire inventargli un soggetto.
-- Il plan scende da 15 a 14.

SELECT * FROM finish();
ROLLBACK;
