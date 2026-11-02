-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: un billing account, un cliente; la pratica sa di quale cliente parla;
--       un gestore per ruolo.
-- Riferimento: brief-db-istanza-nasce-col-ba (R-8, R-9; D-5, D-6, D-8, D-9 di
--   Tid del 2026-10-08).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - un'istanza ha tanti clienti quanti billing account, e un BA ne ha uno;
--   - la pratica porta il BA del cliente di cui parla: nasce da un preventivo
--     col BA del preventivo; il BA e' dell'istanza e del ruolo della pratica;
--   - «il BA dell'istanza» non e' una domanda: il resolver per istanza e'
--     ritirato (rev 2026-10-10), come lo stato del cliente per istanza (vista
--     e funzione ritirate);
--   - un gestore per ruolo.
--
-- Elenco test (plan 12):
--    1) struttura: uq_clienti_billing_account c'e', uq_clienti_istanza_utility no
--    2) due clienti sulla stessa istanza, su due BA -> vive
--    3) un secondo cliente sullo stesso BA -> 23505 uq_clienti_billing_account
--    4) pratica generata dal preventivo: porta il BA del preventivo
--    5) pratica col BA ma senza ruolo -> E_PRATICHE_BA_NON_COERENTE
--    6) pratica col BA ma senza istanza -> 23514 chk_pratiche_ba_con_istanza
--    7) pratica col BA di un'altra istanza -> 23503 fk_pratiche_billing_account_istanza
--    8) la funzione fn_get_billing_account_by_istanza non c'e' piu'
--       (rev 2026-10-10, brief-db-istanza-nasce-col-ba-residui R-4: fino a
--       quel giorno i test 8-9 provavano «istanza con due BA -> NULL» e
--       «istanza con un BA -> quel BA»)
--    9) la vista view_clienti_istanza_states non c'e' piu'
--   10) la funzione fn_get_stato_cliente_by_istanza non c'e' piu'
--   11) struttura: uq_gestori_soggetto_ruolo c'e'
--   12) struttura: fn_resolve_termini_pagamento aggancia il cliente per BA
--       (il livello 3 lo provano i suoi pgTAP: qui si presidia la sola forma
--       del join, che con piu' clienti per istanza sbaglierebbe in silenzio)
--
-- ⚠️ Non provato qui: la copia del BA nella pratica generata da un flusso
--   (fn_genera_pratica_da_flusso) — serve un flusso completato con una regola
--   di generazione. Dichiarato nel brief.
-- ⚠️ Il tipo di prestazione della pratica si pesca (attivo, non obsoleto, con
--   definizione risolvibile), come in test-fn-genera-pratica-da-preventivo-v1:
--   su un database senza definizioni il test 4..7 fanno skip dichiarato.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: in testa. I casi che li vogliono differiti riaprono
--   la finestra da se'.
SET CONSTRAINTS ALL IMMEDIATE;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_preventivo
--   (mondo con emittente e operatore propri): preventivo, BA e pratica devono
--   parlare dello STESSO emittente, quello del mondo.

SELECT plan(12);

-- Il codice di dominio di un errore (canale CONSTRAINT su P0001), o SQLSTATE
-- e nome del vincolo per gli errori di vincolo. NULL se non solleva.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN NULL;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' THEN v_c ELSE v_s || ' ' || coalesce(v_c, '') END;
END $$;

-- ============================================================
-- Fixture: il mondo (emittente, operatore in sessione, cliente con BA X sulla
-- coppia (istanza A, utility U), preventivo P). ⛔ Si legge separato.
-- ============================================================
CREATE TEMP TABLE t_w AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('un BA un cliente');

CREATE TEMP TABLE t_v AS
SELECT (SELECT iu.soggetto_id FROM anagrafiche.istanze_utilities iu
         WHERE iu.id = w.istanza_utility_id)                        AS soggetto_id,
       (SELECT ba.categoria_cliente_id FROM anagrafiche.billing_account ba
         WHERE ba.id = w.billing_account_id)                        AS categoria_id,
       (SELECT u.id FROM config.utilities u
         WHERE u.id <> w.utility_id ORDER BY u.id LIMIT 1)          AS utility_2,
       (SELECT sc.id FROM config.stati_cliente sc ORDER BY sc.id LIMIT 1) AS stato_cliente_id,
       (SELECT tp.id
          FROM pratiche.tipi_prestazione tp
         WHERE tp.attivo IS TRUE
           AND (tp.obsoleto_dal IS NULL OR tp.obsoleto_dal > script.fn_data_operativa())
           AND pratiche.fn_risolvi_definizione(tp.id, NULL) IS NOT NULL
         ORDER BY tp.id LIMIT 1)                                    AS tipo_prestazione_id,
       NULL::bigint AS ba_2,
       NULL::bigint AS istanza_b,
       NULL::bigint AS ba_b,
       NULL::bigint AS pratica_id,
       NULL::bigint AS istanza_c,
       NULL::bigint AS ba_c1,
       NULL::bigint AS ba_c2
  FROM t_w w;

-- Secondo BA sulla stessa istanza (utility 2), e un'istanza B del soggetto
-- col suo BA.
DO $fix$
DECLARE v_ba2 bigint; v_ist bigint; v_bab bigint;
BEGIN
    INSERT INTO anagrafiche.billing_account
        (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id)
    SELECT w.istanza_utility_id, w.cliente_soggetto_ruolo_id, v.utility_2, v.categoria_id
      FROM t_w w, t_v v
    RETURNING id INTO v_ba2;

    SET CONSTRAINTS ALL DEFERRED;
    INSERT INTO anagrafiche.istanze_utilities (fittizia, proprietario_inquilino, soggetto_id)
    VALUES (true, 'I', (SELECT soggetto_id FROM t_v))
    RETURNING id INTO v_ist;
    INSERT INTO anagrafiche.billing_account
        (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id)
    SELECT v_ist, w.cliente_soggetto_ruolo_id, w.utility_id, v.categoria_id
      FROM t_w w, t_v v
    RETURNING id INTO v_bab;
    SET CONSTRAINTS ALL IMMEDIATE;

    UPDATE t_v SET ba_2 = v_ba2, istanza_b = v_ist, ba_b = v_bab;
END $fix$;

-- Un'istanza C con due BA su due utility che NON chiedono un PDP (dati di
-- catalogo: config.utilities.richiede_pdp = false), per poterci appendere due
-- clienti: un cliente su una utility «con PDP» pretende il PDP
-- (E_PDP_OBBLIGATORIO), e non e' il caso di questo file.
DO $fixc$
DECLARE v_ist bigint; v_c1 bigint; v_c2 bigint; v_u integer[];
BEGIN
    SELECT array_agg(u.id ORDER BY u.id) INTO v_u
      FROM (SELECT u.id FROM config.utilities u
             WHERE u.richiede_pdp IS FALSE ORDER BY u.id LIMIT 2) u;
    IF coalesce(array_length(v_u, 1), 0) < 2 THEN
        RAISE EXCEPTION 'fixture: servono due utility senza PDP a catalogo';
    END IF;

    SET CONSTRAINTS ALL DEFERRED;
    INSERT INTO anagrafiche.istanze_utilities (fittizia, proprietario_inquilino, soggetto_id)
    VALUES (true, 'I', (SELECT soggetto_id FROM t_v))
    RETURNING id INTO v_ist;
    INSERT INTO anagrafiche.billing_account
        (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id)
    SELECT v_ist, w.cliente_soggetto_ruolo_id, v_u[1], v.categoria_id FROM t_w w, t_v v
    RETURNING id INTO v_c1;
    INSERT INTO anagrafiche.billing_account
        (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id)
    SELECT v_ist, w.cliente_soggetto_ruolo_id, v_u[2], v.categoria_id FROM t_w w, t_v v
    RETURNING id INTO v_c2;
    SET CONSTRAINTS ALL IMMEDIATE;

    UPDATE t_v SET istanza_c = v_ist, ba_c1 = v_c1, ba_c2 = v_c2;
END $fixc$;

-- ============================================================
-- 1) Struttura del vincolo dei clienti
-- ============================================================
SELECT is(
    (SELECT string_agg(c.conname, ',' ORDER BY c.conname)
       FROM pg_constraint c
      WHERE c.conrelid = 'anagrafiche.clienti'::regclass
        AND c.conname IN ('uq_clienti_billing_account', 'uq_clienti_istanza_utility')),
    'uq_clienti_billing_account',
    '1. clienti: un cliente per BA (uq_clienti_billing_account), non piu'' uno per istanza'
);

-- ============================================================
-- 2) Due clienti sulla stessa istanza, su due BA -> vive
-- ============================================================
SELECT lives_ok(
    $sql$
    INSERT INTO anagrafiche.clienti
        (soggetto_ruolo_id, istanza_utility_id, billing_account_id, stato_cliente_id, data_attivazione)
    SELECT w.cliente_soggetto_ruolo_id, v.istanza_c, b.id, v.stato_cliente_id, script.fn_data_operativa()
      FROM t_w w, t_v v
      JOIN anagrafiche.billing_account b ON b.id IN (v.ba_c1, v.ba_c2)
    $sql$,
    '2. Due clienti sulla stessa istanza, uno per ciascun BA: vivono'
);

-- ============================================================
-- 3) Un secondo cliente sullo stesso BA -> 23505
-- ============================================================
SELECT is(
    pg_temp.esito($sql$
        INSERT INTO anagrafiche.clienti
            (soggetto_ruolo_id, istanza_utility_id, billing_account_id, stato_cliente_id, data_attivazione)
        SELECT w.cliente_soggetto_ruolo_id, v.istanza_c, v.ba_c1, v.stato_cliente_id, script.fn_data_operativa()
          FROM t_w w, t_v v $sql$),
    '23505 uq_clienti_billing_account',
    '3. Un secondo cliente sullo stesso billing account: uq_clienti_billing_account'
);

-- ============================================================
-- 4) Pratica generata dal preventivo: porta il BA del preventivo
-- ============================================================
DO $p$
BEGIN
    IF (SELECT tipo_prestazione_id FROM t_v) IS NOT NULL THEN
        UPDATE t_v SET pratica_id = (
            SELECT r.pratica_id
              FROM vendite.fn_genera_pratica_da_preventivo(
                       (SELECT preventivo_id FROM t_w),
                       (SELECT tipo_prestazione_id FROM t_v),
                       NULL, 'pgTAP un BA un cliente') r);
    END IF;
END $p$;

SELECT CASE WHEN (SELECT pratica_id FROM t_v) IS NULL
    THEN skip('4. nessun tipo di prestazione con definizione su questo database', 1)
    ELSE is(
        (SELECT p.billing_account_id FROM pratiche.pratiche p
          WHERE p.id = (SELECT pratica_id FROM t_v)),
        (SELECT billing_account_id FROM t_w),
        '4. La pratica nata dal preventivo porta il billing account del preventivo')
END;

-- ============================================================
-- 5) Pratica col BA ma senza ruolo -> E_PRATICHE_BA_NON_COERENTE
-- ============================================================
SELECT CASE WHEN (SELECT pratica_id FROM t_v) IS NULL
    THEN skip('5. nessuna pratica costruita', 1)
    ELSE is(
        pg_temp.esito($sql$
            UPDATE pratiche.pratiche SET soggetto_ruolo_id = NULL
             WHERE id = (SELECT pratica_id FROM t_v) $sql$),
        'E_PRATICHE_BA_NON_COERENTE',
        '5. Pratica col billing account ma senza il suo ruolo: E_PRATICHE_BA_NON_COERENTE')
END;

-- ============================================================
-- 6) Pratica col BA ma senza istanza -> 23514
-- ============================================================
SELECT CASE WHEN (SELECT pratica_id FROM t_v) IS NULL
    THEN skip('6. nessuna pratica costruita', 1)
    ELSE is(
        pg_temp.esito($sql$
            UPDATE pratiche.pratiche SET istanza_utility_id = NULL
             WHERE id = (SELECT pratica_id FROM t_v) $sql$),
        '23514 chk_pratiche_ba_con_istanza',
        '6. Pratica col billing account ma senza istanza: chk_pratiche_ba_con_istanza')
END;

-- ============================================================
-- 7) Pratica col BA di un'altra istanza -> 23503
-- ============================================================
SELECT CASE WHEN (SELECT pratica_id FROM t_v) IS NULL
    THEN skip('7. nessuna pratica costruita', 1)
    ELSE is(
        pg_temp.esito($sql$
            UPDATE pratiche.pratiche SET istanza_utility_id = (SELECT istanza_b FROM t_v)
             WHERE id = (SELECT pratica_id FROM t_v) $sql$),
        '23503 fk_pratiche_billing_account_istanza',
        '7. Pratica col billing account di un''altra istanza: fk_pratiche_billing_account_istanza')
END;

-- ============================================================
-- 8) «Il BA dell'istanza» non e' una domanda: il resolver e' ritirato
--    ⚠️ rev 2026-10-10 (brief-db-istanza-nasce-col-ba-residui, R-4): con piu'
--    utility per istanza il BA dell'istanza ha una risposta solo se e' uno,
--    e il dettaglio pratica legge pratiche.billing_account_id (D-9).
-- ============================================================
SELECT hasnt_function('script', 'fn_get_billing_account_by_istanza',
    '8. script.fn_get_billing_account_by_istanza ritirata');

-- ============================================================
-- 9-10) Lo stato del cliente per istanza e' ritirato (D-8)
-- ============================================================
SELECT hasnt_view('script', 'view_clienti_istanza_states',
    '9. script.view_clienti_istanza_states ritirata');

SELECT hasnt_function('script', 'fn_get_stato_cliente_by_istanza',
    '10. script.fn_get_stato_cliente_by_istanza ritirata');

-- ============================================================
-- 11) Un gestore per ruolo
-- ============================================================
SELECT ok(
    EXISTS (SELECT 1 FROM pg_constraint c
             WHERE c.conrelid = 'anagrafiche.gestori'::regclass
               AND c.conname = 'uq_gestori_soggetto_ruolo'
               AND c.contype = 'u'),
    '11. gestori: un gestore per ruolo (uq_gestori_soggetto_ruolo)'
);

-- ============================================================
-- 12) I termini di pagamento: il cliente del BA, non dell'istanza
-- ============================================================
SELECT ok(
    (SELECT p.prosrc ~ 'cl\.billing_account_id\s*=\s*ba\.id'
            AND p.prosrc !~ 'cl\.istanza_utility_id\s*=\s*ba\.istanza_utility_id'
       FROM pg_proc p
      WHERE p.oid = 'vendite.fn_resolve_termini_pagamento(bigint)'::regprocedure),
    '12. fn_resolve_termini_pagamento aggancia il cliente per BA, non per istanza'
);

SELECT * FROM finish();
ROLLBACK;
