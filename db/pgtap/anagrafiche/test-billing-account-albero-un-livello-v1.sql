-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: l'albero dei billing account ha un livello solo, e un solo padre per
--       cliente e per azienda.
-- Oggetti: anagrafiche.trgfn_billing_account_guard_normalize,
--   anagrafiche.fn_check_ba_padre (20261126-37).
-- Riferimento: brief-db-revisione-anagrafiche §24.5 (D-T4-5, S28).
--
-- Semantica attesa (il contratto, non l'implementazione):
--   - chi ha un padre non fa da padre: E_PARENT_CON_PADRE;
--   - chi fa da padre non prende un padre: E_PARENT_HA_FIGLI (chiude anche il
--     ciclo: per fare A padre di B e B padre di A, uno dei due dovrebbe
--     avere un padre e dei figli insieme);
--   - un cliente (stessa identita' fiscale) ha un solo padre per azienda:
--     E_PARENT_SECONDO_PADRE;
--   - il padre si cambia, o si toglie, solo senza attivita' non fatturate:
--     E_DISSOCIAZIONE_PARENT_CON_ATTIVITA.
--   La fattura va al padre diretto (fn_build_fattura_key): con un livello
--   solo, padre diretto e padre di testata sono la stessa cosa.
--
-- Elenco test (plan 6):
--    1) X prende per padre C1, che ha gia' un padre -> E_PARENT_CON_PADRE
--    2) P, che fa da padre, prende un padre -> E_PARENT_HA_FIGLI
--    3) il ciclo: P prende per padre il suo figlio C1 -> rifiutato
--    4) Y prende per padre X: sarebbe un secondo padre dello stesso cliente
--       sulla stessa azienda -> E_PARENT_SECONDO_PADRE, e la frase nomina P
--    5) C1, con attivita' non fatturate e unico figlio di P, passa sotto X
--       -> E_DISSOCIAZIONE_PARENT_CON_ATTIVITA (il cambio vale come lo stacco)
--    6) Y prende per padre P -> passa
-- ------------------------------------------------------------

BEGIN;

-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente
--   (azienda e operatore propri).
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- ============================================================
-- Fixture
-- ⛔ Cio' che un builder scrive si legge in un'istruzione SEPARATA.
-- ============================================================
CREATE TEMP TABLE _t_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('albero un livello');

CREATE TEMP TABLE _t_ref AS
SELECT m.cliente_soggetto_id       AS soggetto_id,
       m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
       m.utility_id,
       dbops.fn_pgtap_crea_articolo('PGTAP-ALB1-' || m.billing_account_id,
                                    p_gestito := false) AS articolo_id,
       (SELECT id FROM anagrafiche.categorie_clienti
         WHERE codice_interno = 'STANDARD') AS categoria_cliente_id
  FROM _t_mondo m;

-- Quattro BA dello stesso cliente, ognuno con la sua istanza: P padre di C1;
-- X e Y senza padre. Una saga (ogni istanza pretende il suo BA al COMMIT):
-- la finestra differita si apre e si richiude.
CREATE TEMP TABLE _t_ba (etichetta text PRIMARY KEY, ba_id bigint);

SET CONSTRAINTS ALL DEFERRED;

DO $fx$
DECLARE
    r      record;
    v_iu   anagrafiche.istanze_utilities.id%TYPE;
    v_ba   anagrafiche.billing_account.id%TYPE;
    v_p    anagrafiche.billing_account.id%TYPE;
    -- l'etichetta del BA nella fixture: nessuna colonna dietro
    e      text;
BEGIN
    SELECT * INTO r FROM _t_ref;
    FOREACH e IN ARRAY ARRAY['P', 'C1', 'X', 'Y'] LOOP
        INSERT INTO anagrafiche.istanze_utilities (soggetto_id, fittizia, codice)
        VALUES (r.soggetto_id, true, 'TST-ALB1-' || e) RETURNING id INTO v_iu;
        INSERT INTO anagrafiche.billing_account
               (istanza_utility_id, soggetto_ruolo_id, utility_id, categoria_cliente_id,
                valido_dal, parent_account_id)
        VALUES (v_iu, r.soggetto_ruolo_id, r.utility_id, r.categoria_cliente_id,
                script.fn_data_operativa(), CASE WHEN e = 'C1' THEN v_p END)
        RETURNING id INTO v_ba;
        IF e = 'P' THEN
            v_p := v_ba;
        END IF;
        INSERT INTO _t_ba VALUES (e, v_ba);
    END LOOP;
END
$fx$;

SET CONSTRAINTS ALL IMMEDIATE;

-- Le attivita' non fatturate di C1: commessa e attivita' dai builder,
-- l'attivita' fatturabile dall'emissione della madre.
DO $att$
DECLARE
    v_commessa vendite.commesse.id%TYPE;
BEGIN
    SELECT c.commessa_id INTO v_commessa
      FROM dbops.fn_pgtap_crea_commessa('albero un livello', NULL,
                                        (SELECT ba_id FROM _t_ba WHERE etichetta = 'C1'),
                                        p_con_sorgente_root => true) c;
    PERFORM dbops.fn_pgtap_crea_commessa_attivita(v_commessa, 10.00,
                                                  (SELECT articolo_id FROM _t_ref));
    PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(v_commessa, true, false);
END
$att$;

CREATE OR REPLACE FUNCTION pg_temp.ba(p_etichetta text) RETURNS bigint
LANGUAGE sql AS $f$ SELECT ba_id FROM _t_ba WHERE etichetta = p_etichetta $f$;

-- ============================================================
-- Un livello solo
-- ============================================================
SELECT throws_like(
    $$UPDATE anagrafiche.billing_account SET parent_account_id = pg_temp.ba('C1')
       WHERE id = pg_temp.ba('X')$$,
    '%ha gia'' un padre%',
    '1) X prende per padre C1, che ha gia'' un padre -> E_PARENT_CON_PADRE');

SELECT throws_like(
    $$UPDATE anagrafiche.billing_account SET parent_account_id = pg_temp.ba('X')
       WHERE id = pg_temp.ba('P')$$,
    '%fa da padre%',
    '2) P, che fa da padre, prende un padre -> E_PARENT_HA_FIGLI');

SELECT throws_like(
    $$UPDATE anagrafiche.billing_account SET parent_account_id = pg_temp.ba('C1')
       WHERE id = pg_temp.ba('P')$$,
    '%padre%',
    '3) il ciclo: P prende per padre il suo figlio C1 -> rifiutato');

-- ============================================================
-- Un solo padre per cliente e per azienda
-- ============================================================
-- La frase nomina, per codice, il padre che il cliente ha gia'.
SELECT throws_like(
    $$UPDATE anagrafiche.billing_account SET parent_account_id = pg_temp.ba('X')
       WHERE id = pg_temp.ba('Y')$$,
    '%ha gia'' il conto padre '
        || (SELECT codice FROM anagrafiche.billing_account WHERE id = pg_temp.ba('P')) || '%',
    '4) Y sotto X: un secondo padre dello stesso cliente sulla stessa azienda -> E_PARENT_SECONDO_PADRE, col padre che c''e''');

-- ============================================================
-- Il cambio di padre vale come lo stacco
-- ============================================================
SELECT throws_like(
    $$UPDATE anagrafiche.billing_account SET parent_account_id = pg_temp.ba('X')
       WHERE id = pg_temp.ba('C1')$$,
    '%attivita%non fatturate%',
    '5) C1, con attivita'' non fatturate, passa sotto X -> E_DISSOCIAZIONE_PARENT_CON_ATTIVITA');

SELECT lives_ok(
    $$UPDATE anagrafiche.billing_account SET parent_account_id = pg_temp.ba('P')
       WHERE id = pg_temp.ba('Y')$$,
    '6) Y prende per padre P, il padre che il cliente ha gia'' -> passa');

SELECT * FROM finish();
ROLLBACK;
