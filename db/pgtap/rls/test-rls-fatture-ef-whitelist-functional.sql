-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.fatture ENABLE + FORCE ROW LEVEL SECURITY, locale alla
--   transazione: e' il FORCE a rendere l'owner soggetto alle policy.
-- pgTAP test FUNZIONALE RLS — vendite.fatture (policy EF_WHITELIST)
--
-- Brief RLS §11. A differenza di test-rls-policies-structure.sql (che
-- verifica solo l'ESISTENZA delle policy), questo esercita il RUNTIME.
--
-- Meccanismo (l'utente di test = titodb, owner NON-superuser):
--   - ENABLE + FORCE ROW LEVEL SECURITY locale alla transazione: FORCE
--     assoggetta anche l'owner (titodb) alla RLS, senza bisogno di SET ROLE
--     (titodb non e' superuser, non potrebbe cambiare ruolo). Il ROLLBACK
--     finale annulla ENABLE/FORCE.
--   - GUC simulati via set_config(...,is_local=true); la canonica
--     fn_check_user_emittente_scope e gli helper sono letti con i privilegi
--     di titodb (owner: ha accesso a tutte le tabelle del predicato).
--
-- ⭐ Rev 2026-10-07 (brief-db-fixture-rls-documenti-costruiti, giro 1): IL
--   MONDO SI COSTRUISCE. Fino a oggi il file pescava «la prima fattura con un
--   emittente» e «il primo altro emittente», e senza dati andava in SOFT-SKIP:
--   su zeroerp_ci (da zero) i sette casi passavano senza misurare niente.
--   Ora due aziende costruite — A possiede la fattura, B e' l'estranea — e la
--   fattura di A (dbops.fn_pgtap_crea_fattura), tutto PRIMA del FORCE. Se
--   qualcosa non si costruisce il file va ROSSO: e' l'informazione utile.
--   Modello: test-rls-resi-ef-whitelist-write.
--
-- Indice test (0..7) — visibilita' della fattura di A sotto RLS attiva:
--   0. fixture: fattura di A costruita, B e' un'altra azienda
--   1. operatore, whitelist VUOTA            -> NON visibile (fail-closed, P-2a)
--   2. operatore, whitelist = A              -> visibile
--   3. operatore, whitelist = B              -> NON visibile
--   4. ruolo non OPERATORE (gate fallisce)   -> NON visibile
--   5. identita OPERATORE non attiva         -> NON visibile (fail-closed)
--   6. SUPER_ADMIN con whitelist = B         -> visibile (fix C7)
--   7. DISABLE RLS (kill-switch)             -> di nuovo visibile
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

SELECT plan(8);

-- =========================================================
-- Fixture: due aziende costruite e la fattura di A
-- =========================================================
-- B prima di tutto, e PRIMA di qualunque contesto: e' un builder atomico.
CREATE TEMP TABLE _b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- A: senza contesto aperto, il mondo cliente costruisce l'azienda, l'operatore
-- (tecnico) e il cliente, apre il contesto su di lui e scrive la testata.
CREATE TEMP TABLE _a AS
SELECT * FROM dbops.fn_pgtap_crea_fattura('rls fatture ef');

-- ⚠️ Il builder ha lasciato aperto il contesto del SUO operatore. Qui l'identita'
--   la dichiara ogni caso: si riparte da «nessuno».
SELECT set_config('app.ruolo_applicativo', '', false),
       set_config('app.current_user_id',   '', false);

CREATE TEMP TABLE _refs AS
SELECT a.fattura_id,
       a.emittente_soggetto_ruolo_id AS emit_sr,
       a.emittente_fiscale_id        AS emit_pk,
       b.emittente_fiscale_id        AS other_pk
  FROM _a a, _b b;

SELECT ok(
    (SELECT fattura_id IS NOT NULL AND emit_pk IS NOT NULL AND other_pk IS NOT NULL
            AND emit_pk <> other_pk FROM _refs),
    '0. Fixture: fattura di A costruita, B e'' un''altra azienda');

-- QUATTRO operatori, uno per stato da collaudare: operatore dalla madre +
-- (eventuale) riga di whitelist.
--
--   'vuoto'  nessuna riga di whitelist, identita attiva                -> caso 1
--   'in'     whitelist = emittente della fattura                       -> casi 2 e 4
--   'out'    whitelist = ALTRO emittente                               -> casi 3 e 6
--   'spento' whitelist = emittente della fattura, identita NON attiva  -> caso 5
--
-- ⚠️ QUATTRO UTENTI, E NON UNO CHE SI RIPUNTA. Il giro originale era «DELETE
--   dalla whitelist + INSERT dell'altro emittente» sullo stesso utente: era
--   lecito quando il file e' stato scritto, oggi no.
--   config.user_emittenti_fiscali ha un guard sul DELETE
--   (E_USER_EMITTENTE_DELETE_VIETATO) che ammette la cancellazione solo se
--   l'utente Django e' disattivato: l'associazione si toglie solo dismettendo
--   l'utente. Il file moriva li', con ZERO asserzioni eseguite.
--
-- ⭐ E il caso 5 ci ha guadagnato. Prima cancellava la whitelist E spegneva
--   l'identita': due negazioni insieme, quindi passava anche se `attivo` fosse
--   stato ignorato del tutto — bastava la whitelist vuota, che e' il caso 1.
--   L'operatore 'spento' ha la whitelist GIUSTA: l'unica differenza col caso 2
--   e' l'identita' spenta, ed e' cio' che il caso dichiara di misurare.
CREATE TEMP TABLE _op (tag text, auth_user_id int, soggetto_id uuid, sr_id bigint, identita_id bigint);

-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): l'operatore viene dalla
--   MADRE (dbops.fn_pgtap_crea_operatore_umano: persona fisica completa,
--   risorsa umana, veste OPERATORE accesa come all'invito accettato) e
--   l'emittente gli si da' con la funzione di dominio
--   script.fn_change_user_emittenti_scope. Prima la fixture costruiva
--   soggetto, soggetto_ruolo e veste a mano, senza risorsa umana: uno stato
--   che la madre non produce, e che da D-2 (l'operatore umano vale finche'
--   vale il suo rapporto, script.fn_veste_utilizzabile) non e' piu' un
--   operatore valido. Il builder esce con i vincoli IMMEDIATE: niente piu'
--   finestra differita da riaprire per lui.
CREATE FUNCTION pg_temp.mk_op(p_tag text, p_emit bigint, p_identita_attiva boolean DEFAULT true)
RETURNS void LANGUAGE plpgsql AS $fn$
DECLARE v_op record;
BEGIN
    SELECT * INTO v_op
      FROM dbops.fn_pgtap_crea_operatore_umano('rls fatture ' || p_tag);

    -- Lo spegnimento e' un UPDATE dopo l'accensione, non un INSERT a false:
    -- e' il percorso con cui un'identita' viene dismessa davvero.
    IF NOT p_identita_attiva THEN
        UPDATE anagrafiche.identita_digitali SET attivo = false WHERE id = v_op.identita_id;
    END IF;

    IF p_emit IS NOT NULL THEN
        PERFORM script.fn_change_user_emittenti_scope(v_op.auth_user_id, ARRAY[p_emit]);
    END IF;

    INSERT INTO _op VALUES (p_tag, v_op.auth_user_id, v_op.soggetto_id,
                            v_op.soggetto_ruolo_id, v_op.identita_id);
END $fn$;

DO $ops$
BEGIN
    PERFORM pg_temp.mk_op('vuoto',  NULL);
    PERFORM pg_temp.mk_op('in',     (SELECT emit_pk  FROM _refs));
    PERFORM pg_temp.mk_op('out',    (SELECT other_pk FROM _refs));
    PERFORM pg_temp.mk_op('spento', (SELECT emit_pk  FROM _refs), false);
END $ops$;

-- Attiva RLS + FORCE solo dentro questa transazione: FORCE assoggetta
-- l'owner titodb (non-superuser) senza SET ROLE. Rollback annulla tutto.
ALTER TABLE vendite.fatture ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, visibile boolean);

-- ---- Caso 1: whitelist VUOTA -> NON visibile (fail-closed) ----
-- 🔴 CAMBIATO il 2026-08-18 (changeSet 20260818-11/-12, passo 2 / P-2a).
--    Gemello del caso 1 di test-rls-fatture-satelliti-functional: prima
--    asseriva «whitelist vuota = accesso globale», cioe' il fail-OPEN.
DO $c1$
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'vuoto')::text, true);
    INSERT INTO _res SELECT 'c1', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c1$;

-- ---- Caso 2: whitelist = emittente della fattura -> visibile ----
DO $c2$
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'in')::text, true);
    INSERT INTO _res SELECT 'c2', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c2$;

-- ---- Caso 3: whitelist = ALTRO emittente -> NON visibile ----
DO $c3$
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'out')::text, true);
    INSERT INTO _res SELECT 'c3', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c3$;

-- ---- Caso 4: ruolo NON OPERATORE (gate policy fallisce) -> NON visibile ----
DO $c4$
BEGIN
    -- Operatore 'in', cioe' whitelist che MATCHA: la negazione deve venire dal
    -- gate sul ruolo, non dal perimetro.
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'in')::text, true);
    INSERT INTO _res SELECT 'c4', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c4$;

-- ---- Caso 5: identita OPERATORE NON attiva -> NON visibile ----
DO $c5$
BEGIN
    -- L'operatore 'spento' ha la whitelist GIUSTA: l'unica differenza col caso 2
    -- e' l'identita' non attiva.
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'spento')::text, true);
    INSERT INTO _res SELECT 'c5', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c5$;

-- ---- Caso 6: SUPER_ADMIN -> visibile anche con whitelist non-matching (fix C7) ----
DO $c6$
BEGIN
    -- Si usa l'operatore 'out' (whitelist = altro emittente): senza super_admin
    -- la fattura gli e' nascosta, e il caso 3 lo ha appena dimostrato.
    -- binding SUPER_ADMIN sulla sua identita OPERATORE.
    PERFORM config.fn_lega_profilo_identita((SELECT id FROM config.profili_accesso
          WHERE tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso AND attivo = true
          ORDER BY id LIMIT 1), (SELECT identita_id FROM _op WHERE tag = 'out'));
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'out')::text, true);
    INSERT INTO _res SELECT 'c6', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));
END $c6$;

-- ---- Caso 7: DISABLE RLS (kill-switch) -> di nuovo visibile ----
ALTER TABLE vendite.fatture NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture DISABLE ROW LEVEL SECURITY;
INSERT INTO _res
SELECT 'c7', EXISTS (SELECT 1 FROM vendite.fatture WHERE id = (SELECT fattura_id FROM _refs));

-- =========================================================
-- Asserzioni
-- =========================================================
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c1'),
    '1. operatore whitelist vuota -> fattura NON visibile (fail-closed, P-2a)');
SELECT ok((SELECT visibile FROM _res WHERE caso='c2'),
    '2. operatore whitelist = emittente fattura -> visibile');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c3'),
    '3. operatore whitelist = altro emittente -> NON visibile');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c4'),
    '4. ruolo non OPERATORE -> NON visibile (gate policy)');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c5'),
    '5. identita OPERATORE non attiva -> NON visibile (fail-closed)');
SELECT ok((SELECT visibile FROM _res WHERE caso='c6'),
    '6. SUPER_ADMIN -> visibile nonostante whitelist non-matching (fix C7)');
SELECT ok((SELECT visibile FROM _res WHERE caso='c7'),
    '7. DISABLE RLS (kill-switch) -> fattura di nuovo visibile');

SELECT * FROM finish();
ROLLBACK;
