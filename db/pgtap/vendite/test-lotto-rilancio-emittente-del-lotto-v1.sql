-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: vendite.fn_get_or_create_lotto — per un lotto ESISTENTE l'emittente
--   e' quello del lotto; il ripiego sul predefinito vale solo per il lotto nuovo.
-- Riferimento: richiesta BE del 2026-10-21 (§9.10 di brief-be-utenti-di-
--   sviluppo); changeSet 20261022-01.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un lotto MASSIVO di un emittente NON predefinito si rilancia col solo
--     lotto_id (il FE manda solo quello, su «Avanza» e dopo un ERRORE): torna
--     lo stesso lotto, non E_LOTTO_PARAMETRO_NON_COERENTE;
--   - un emittente indicato dal chiamante, diverso da quello del lotto, resta
--     rifiutato: il confronto c'e', ma solo con cio' che il chiamante dice;
--   - un lotto NUOVO senza BA e senza emittente prende ancora il predefinito.
--
-- Elenco test (plan 4):
--   1) il lotto nasce sull'emittente non predefinito chiesto
--   2) rilancio col solo lotto_id: torna lo stesso lotto
--   3) rilancio con un emittente diverso da quello del lotto: rifiutato
--   4) lotto nuovo senza BA ne' emittente: l'emittente predefinito
--
-- ⚠️ Il mondo ha due aziende: la prima costruita (che su un database
--   ricostruito diventa il PREDEFINITO) e quella dell'operatore, che non e' il
--   predefinito per costruzione.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- ============================================================
-- Fixture
-- ============================================================

-- Due aziende in due istruzioni. Su un database ricostruito il predefinito non
-- c'e', e lo diventa il PRIMO emittente costruito; dove c'e' gia' (dbdev),
-- nessuna delle due lo diventa. In entrambi i casi l'azienda dell'operatore
-- (la seconda) non e' il predefinito.
CREATE TEMP TABLE t_primo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

CREATE TEMP TABLE t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_mondo));
END $ctx$;

-- Il predefinito, letto dalla regola di produzione (la riga di gestore
-- globale): e' lui che il ripiego restituisce.
CREATE TEMP TABLE t_pred AS
SELECT efba.emittente_soggetto_ruolo_id AS sr
  FROM anagrafiche.emittenti_fiscali_billing_account efba
 WHERE efba.billing_account_id IS NULL;

CREATE TEMP TABLE t_dim AS
SELECT (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo ORDER BY t.id LIMIT 1) AS tipo_doc,
       (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1)                       AS utility,
       date_trunc('month', script.fn_data_operativa())::date                            AS mese;

-- Il lotto MASSIVO dell'azienda dell'operatore, con l'emittente esplicito.
CREATE TEMP TABLE t_lotto AS
SELECT vendite.fn_get_or_create_lotto(
           p_competenza_mese             => d.mese,
           p_tipo_doc_fiscale_id         => d.tipo_doc,
           p_utility_id                  => d.utility,
           p_tipo_lotto                  => 'MASSIVO',
           p_emittente_soggetto_ruolo_id => m.soggetto_ruolo_id) AS lotto_id
  FROM t_dim d, t_mondo m;

-- ============================================================
-- 1) Il lotto e' dell'emittente non predefinito
-- ============================================================
SELECT is(
    (SELECT (l.emittente_soggetto_ruolo_id = m.soggetto_ruolo_id)::text
         || ' ' || (l.emittente_soggetto_ruolo_id IS DISTINCT FROM p.sr)::text
       FROM vendite.fatturazione_lotti l, t_mondo m, t_pred p
      WHERE l.id = (SELECT lotto_id FROM t_lotto)),
    'true true',
    '1) il lotto nasce sull''emittente chiesto, che non e'' il predefinito'
);

-- ============================================================
-- 2) Rilancio col solo lotto_id
-- ============================================================
SELECT is(
    vendite.fn_get_or_create_lotto(p_lotto_id => (SELECT lotto_id FROM t_lotto)),
    (SELECT lotto_id FROM t_lotto),
    '2) rilancio col solo lotto_id: torna lo stesso lotto (l''emittente e'' quello del lotto)'
);

-- ============================================================
-- 3) Un emittente indicato e diverso resta rifiutato
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'SELECT vendite.fn_get_or_create_lotto(p_lotto_id => %s, p_emittente_soggetto_ruolo_id => %s)',
        (SELECT lotto_id FROM t_lotto), (SELECT sr FROM t_pred))),
    'E_LOTTO_PARAMETRO_NON_COERENTE',
    '3) rilancio con un emittente diverso da quello del lotto -> E_LOTTO_PARAMETRO_NON_COERENTE'
);

-- ============================================================
-- 4) Lotto nuovo senza BA ne' emittente: il predefinito
-- ============================================================
-- Lo chiede un SUPER ADMIN senza emittente scelto: il predefinito non e'
-- l'azienda dell'operatore (e su dbdev nemmeno della prima), e il perimetro
-- di un operatore lo rifiuterebbe. Il super admin lo crea l'operatore (sotto la
-- RLS chi crea ha un contesto); si legge in un'istruzione separata.
CREATE TEMP TABLE t_sa AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('rilancio lotto SA', p_super_admin := true);

DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_sa));
    PERFORM set_config('app.current_emittente_id', '', true);
END $ctx$;

CREATE TEMP TABLE t_nuovo AS
SELECT vendite.fn_get_or_create_lotto(
           p_competenza_mese     => d.mese,
           p_tipo_doc_fiscale_id => d.tipo_doc,
           p_utility_id          => d.utility,
           p_tipo_lotto          => 'GIORNALIERO') AS lotto_id
  FROM t_dim d;

SELECT is(
    (SELECT l.emittente_soggetto_ruolo_id FROM vendite.fatturazione_lotti l
      WHERE l.id = (SELECT lotto_id FROM t_nuovo)),
    (SELECT sr FROM t_pred),
    '4) lotto nuovo senza BA ne'' emittente: prende il predefinito'
);

SELECT * FROM finish();
ROLLBACK;
