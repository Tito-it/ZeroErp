-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un utente di sessione illeggibile non fa nascere un billing account
--       senza controllo.
-- Oggetti: anagrafiche.trgfn_billing_account_guard_admin_globale
--   (20261126-28), anagrafiche.trgfn_billing_account_link_ef (20261126-27),
--   script.fn_utente_di_sessione.
-- Riferimento: brief-db-revisione-anagrafiche §24.5 (S31).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un app.current_user_id che non e' l'id di un utente e' rifiutato da
--     script.fn_utente_di_sessione (E_SCRIPT_CHIAMATA_NON_VALIDA), e il
--     rifiuto sale dai trigger del billing account: non diventa «nessun
--     utente», il ramo dei seed che non controlla niente;
--   - un app.current_user_id vuoto resta «nessun utente».
--
-- Elenco test (plan 2):
--   1) app.current_user_id = 'non-un-id', nasce un BA -> rifiutato
--   2) i due trigger non hanno piu' un blocco EXCEPTION intorno alla lettura
--      dell'utente (forma: il corpo vivo)
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente;
--   il test 1 lo guasta di proposito, nella sua istruzione.
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(2);

CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('utente illeggibile');

CREATE TEMP TABLE _t_ref AS
SELECT m.cliente_soggetto_id       AS soggetto_id,
       m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
       m.utility_id,
       (SELECT id FROM anagrafiche.categorie_clienti
         WHERE codice_interno = 'STANDARD') AS categoria_cliente_id
  FROM _t_mondo m;

-- L'istanza nasce col contesto buono; il BA con l'utente guasto.
-- Una saga (l'istanza pretende il suo BA al COMMIT): la finestra differita
-- resta aperta fino in fondo, il file si chiude in ROLLBACK.
SET CONSTRAINTS ALL DEFERRED;

CREATE TEMP TABLE _t_iu AS
WITH ins AS (
    INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
    SELECT soggetto_id, true, 'TST-UTILL-IU' FROM _t_ref
    RETURNING id
)
SELECT id FROM ins;

SELECT throws_like(
    $t$DO $u$ BEGIN
        PERFORM set_config('app.current_user_id', 'non-un-id', true);
        INSERT INTO anagrafiche.billing_account
               (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id, valido_dal)
        SELECT (SELECT id FROM _t_iu), r.soggetto_ruolo_id, r.utility_id, r.categoria_cliente_id,
               script.fn_data_operativa()
          FROM _t_ref r;
      END $u$$t$,
    '%non e'' l''id di un utente%',
    '1) app.current_user_id illeggibile, nasce un BA -> rifiutato da script.fn_utente_di_sessione');

-- Forma: la lettura dell'utente non e' piu' dentro un blocco che la ingoia.
SELECT is(
    (SELECT count(*)::int FROM pg_catalog.pg_proc p
       JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'anagrafiche'
        AND p.proname IN ('trgfn_billing_account_guard_admin_globale',
                          'trgfn_billing_account_link_ef')
        AND p.prosrc ~* 'EXCEPTION\s+WHEN\s+OTHERS'),
    0,
    '2) i due trigger leggono l''utente senza un EXCEPTION WHEN OTHERS che ne ingoi il rifiuto');

SELECT * FROM finish();
ROLLBACK;
