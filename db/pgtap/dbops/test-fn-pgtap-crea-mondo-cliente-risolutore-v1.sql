-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'azienda di chi agisce, nei builder, la dice il risolutore di
--   produzione (script.fn_resolve_emittente_for_user) — anche per il super
--   admin che ha scelto l'emittente in alto (app.current_emittente_id).
--   dbops.fn_pgtap_crea_mondo_cliente (ramo con contesto) e
--   script.fn_pgtap_emittente_operatore.
-- Riferimento: richiesta BE del 2026-10-21 (R-2: i builder accettano chi
--   agisce come dev.smoke, l'utente degli smoke Python, SUPER_ADMIN senza
--   whitelist che sceglie l'emittente di prova). changeSet 20261021-67/-68.
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - il super admin che NON ha scelto un emittente non ha un'azienda su cui
--     scrivere: il mondo parla, invece di tornare un NULL;
--   - il super admin che ha scelto un emittente ha il mondo su QUELL'azienda,
--     e il cliente ci e' legato: la stessa risposta del trigger che lega il BA;
--   - i builder a valle (qui la fattura) seguono la stessa azienda;
--   - per un operatore normale non cambia niente: un emittente scelto fuori
--     dal suo perimetro non lo sposta.
--
-- Elenco test (plan 6):
--   1) super admin senza emittente scelto: il mondo solleva
--   2) super admin con emittente scelto: il mondo e' su quell'emittente
--   3) e il cliente del mondo e' legato a quell'emittente
--   4) script.fn_pgtap_emittente_operatore risponde quell'emittente
--   5) la fattura del mondo e' di quell'emittente
--   6) operatore normale con un emittente altrui scelto: resta sul suo
--
-- ⚠️ Ciò che un builder scrive si legge in un'istruzione separata
--   (fn_is_super_admin e il risolutore sono STABLE).
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. Gli helper aprono e RICHIUDONO da se' la
--   finestra dove serve (e' il loro contratto).
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture: due aziende e un super admin, PRIMA del contesto
-- ============================================================
CREATE TEMP TABLE t_mondi AS
SELECT 'SCELTA' AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore()
UNION ALL
SELECT 'ALTRA'  AS lato, * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- Il super admin nasce senza azienda (nessuna riga in
-- config.user_emittenti_fiscali): e' la forma di dev.smoke. Lo crea un
-- operatore: sotto la RLS soggetto, risorsa umana e identita' le scrive solo
-- chi ha un contesto (come in test-totp-obbligo-v1).
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'SCELTA'));
END $ctx$;

CREATE TEMP TABLE t_sa AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano(
                 'presidio mondo super admin', p_super_admin := true);

-- Il contesto del super admin, senza emittente scelto.
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM t_sa));
    PERFORM set_config('app.current_emittente_id', '', true);
END $ctx$;

-- ============================================================
-- 1) Senza emittente scelto: niente azienda
-- ============================================================
SELECT throws_like(
    $$SELECT dbops.fn_pgtap_crea_mondo_cliente('presidio senza scelta')$$,
    '%non ha un''azienda su cui scrivere%',
    '1) super admin senza emittente scelto: il mondo parla invece di tornare un NULL'
);

-- ============================================================
-- 2-5) Con l'emittente scelto, come lo sceglie l'operatore in alto
-- ============================================================
SELECT set_config('app.current_emittente_id',
                  (SELECT emittente_fiscale_id::text FROM t_mondi WHERE lato = 'SCELTA'),
                  true);

CREATE TEMP TABLE t_m AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('presidio con scelta');

SELECT is(
    (SELECT m.emittente_fiscale_id::text || ' ' || (m.auth_user_id = s.auth_user_id)::text
       FROM t_m m, t_sa s),
    (SELECT emittente_fiscale_id::text || ' true' FROM t_mondi WHERE lato = 'SCELTA'),
    '2) super admin con emittente scelto: il mondo e'' su quell''azienda, e chi agisce e'' lui'
);

SELECT is(
    (SELECT efba.emittente_soggetto_ruolo_id
       FROM anagrafiche.emittenti_fiscali_billing_account efba
      WHERE efba.billing_account_id = (SELECT billing_account_id FROM t_m)),
    (SELECT soggetto_ruolo_id FROM t_mondi WHERE lato = 'SCELTA'),
    '3) il cliente del mondo e'' legato all''emittente scelto (la risposta del trigger del BA)'
);

SELECT is(
    script.fn_pgtap_emittente_operatore(),
    (SELECT emittente_fiscale_id FROM t_mondi WHERE lato = 'SCELTA'),
    '4) script.fn_pgtap_emittente_operatore risponde l''emittente scelto'
);

CREATE TEMP TABLE t_f AS
SELECT * FROM dbops.fn_pgtap_crea_fattura(
                 'presidio con scelta', 'DRAFT', (SELECT billing_account_id FROM t_m));

SELECT is(
    (SELECT emittente_fiscale_id FROM t_f),
    (SELECT emittente_fiscale_id FROM t_mondi WHERE lato = 'SCELTA'),
    '5) la fattura del mondo e'' dell''emittente scelto: i builder a valle seguono'
);

-- ============================================================
-- 6) Operatore normale: un emittente altrui scelto non lo sposta
-- ============================================================
DO $ctx$
BEGIN
    PERFORM script.fn_pgtap_set_contesto_operatore(
        (SELECT auth_user_id FROM t_mondi WHERE lato = 'SCELTA'));
    PERFORM set_config('app.current_emittente_id',
                       (SELECT emittente_fiscale_id::text FROM t_mondi WHERE lato = 'ALTRA'),
                       true);
END $ctx$;

SELECT is(
    script.fn_pgtap_emittente_operatore(),
    (SELECT emittente_fiscale_id FROM t_mondi WHERE lato = 'SCELTA'),
    '6) operatore normale con un emittente altrui scelto: resta sul suo'
);

SELECT * FROM finish();
ROLLBACK;
