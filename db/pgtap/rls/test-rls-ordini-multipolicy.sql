-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.ordini ENABLE + FORCE ROW LEVEL SECURITY, locale alla
--   transazione: e' il FORCE a rendere l'owner soggetto alle policy.
-- pgTAP test FUNZIONALE RLS multi-policy — vendite.ordini
--
-- Brief RLS §5/§11. ordini ha TRE policy PERMISSIVE (combinate in OR),
-- ciascuna gated sul proprio ruolo_applicativo:
--   - rls_ordini_cliente_ownership (CLIENTE_PORTALE, per soggetto_ruolo)
--   - rls_ordini_shop              (SHOP_CUSTOMER, canale SHOP)
--   - rls_ordini_ef_whitelist      (OPERATORE, per emittente_fiscale_id)
-- Obiettivo: dimostrare che un OPERATORE vede solo per emittente e NON
-- eredita visibilita' dalle policy cliente/shop (e viceversa il gate per
-- ruolo isola le facce).
--
-- Meccanismo identico a test-rls-fatture-ef-whitelist-functional.sql:
-- ENABLE+FORCE locale alla tx (titodb owner non-superuser -> soggetto),
-- GUC via set_config.
--
-- ⭐ Rev 2026-10-07 (brief-db-fixture-rls-documenti-costruiti, giro 2): IL
--   MONDO SI COSTRUISCE. Fino a oggi il file pescava «il primo ordine con un
--   emittente» e «il primo altro emittente», e senza dati andava in SOFT-SKIP:
--   su zeroerp_ci (da zero) i casi passavano senza misurare niente. Ora due
--   aziende costruite — A possiede l'ordine, B e' l'estranea — e l'ordine
--   di A (dbops.fn_pgtap_crea_ordine), tutto PRIMA del FORCE. Se qualcosa non si
--   costruisce il file va ROSSO. Modello: test-rls-resi-ef-whitelist-write.
--
-- Indice test (0..5) — visibilita' dell'ordine di A:
--   0. fixture: ordine di A costruito, B e' un'altra azienda
--   1. OPERATORE, whitelist = emittente ordine  -> visibile (policy EF)
--   2. OPERATORE, whitelist = ALTRO emittente    -> NON visibile
--      (EF fallisce; cliente/shop gated off -> nessun leak)
--   3. CLIENTE_PORTALE, identita non proprietaria-> NON visibile
--      (policy cliente non concede; EF gated off) -> "non eredita"
--   4. nessun ruolo (GUC vuoto)                   -> NON visibile (fail-closed)
--   5. DISABLE RLS (kill-switch)                  -> di nuovo visibile
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

SELECT plan(6);

-- Le due aziende e l'ordine di A.
-- B prima di tutto, e PRIMA di qualunque contesto: e' un builder atomico.
CREATE TEMP TABLE _b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- A: senza contesto aperto, il builder costruisce l'azienda, l'operatore
-- (tecnico), il cliente e l'ordine, e apre il contesto su quell'operatore.
CREATE TEMP TABLE _a AS
SELECT * FROM dbops.fn_pgtap_crea_ordine('rls ordini');

-- ⚠️ Il builder ha lasciato aperto il contesto del SUO operatore. Qui l'identita'
--   la dichiara ogni caso: si riparte da «nessuno».
SELECT set_config('app.ruolo_applicativo', '', false),
       set_config('app.current_user_id',   '', false);

CREATE TEMP TABLE _refs AS
SELECT a.ordine_id,
       a.emittente_fiscale_id      AS emit_pk,
       a.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
       b.emittente_fiscale_id      AS other_pk
  FROM _a a, _b b;

SELECT ok(
    (SELECT o.emittente_fiscale_id = r.emit_pk AND r.emit_pk <> r.other_pk
       FROM _refs r JOIN vendite.ordini o ON o.id = r.ordine_id),
    '0. Fixture: ordine di A costruito, B e'' un''altra azienda');

-- Due operatori di test, uno per emittente: operatore dalla madre + UNA riga
-- di whitelist.
--
-- ⚠️ DUE UTENTI, E NON UNO CHE SI RIPUNTA. Il giro originale era «DELETE dalla
--   whitelist + INSERT dell'altro emittente» sullo stesso utente: era lecito
--   quando il file e' stato scritto, oggi no. config.user_emittenti_fiscali ha
--   un guard sul DELETE (E_USER_EMITTENTE_DELETE_VIETATO) che ammette la
--   cancellazione solo se l'utente Django e' disattivato — l'associazione si
--   toglie solo dismettendo l'utente. Il file moriva li'.
--   Con due utenti il perimetro si esprime come esiste davvero in produzione,
--   e la fixture non ha piu' bisogno di scrivere dove l'applicazione non scrive.
CREATE TEMP TABLE _op (tag text, auth_user_id int, identita_id bigint);

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
CREATE OR REPLACE FUNCTION pg_temp.mk_op(p_tag text, p_emit bigint)
RETURNS void LANGUAGE plpgsql AS $fn$
DECLARE v_op record;
BEGIN
    SELECT * INTO v_op
      FROM dbops.fn_pgtap_crea_operatore_umano('rls ordini ' || p_tag);

    -- Istruzione separata: cio' che il builder scrive si legge da qui in poi.
    PERFORM script.fn_change_user_emittenti_scope(v_op.auth_user_id, ARRAY[p_emit]);

    INSERT INTO _op VALUES (p_tag, v_op.auth_user_id, v_op.identita_id);
END
$fn$;

DO $ops$
BEGIN
    PERFORM pg_temp.mk_op('in',  (SELECT emit_pk  FROM _refs));
    PERFORM pg_temp.mk_op('out', (SELECT other_pk FROM _refs));
END $ops$;

-- RLS gia' ENABLED (Ondata 2-A); aggiungo FORCE locale per assoggettare
-- l'owner titodb (non-superuser). Rollback ripristina lo stato committato.
ALTER TABLE vendite.ordini ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, visibile boolean);

-- c1: OPERATORE, whitelist = emittente ordine -> visibile
DO $c1$
BEGIN
    -- L'operatore 'in' ha in whitelist l'emittente dell'ordine.
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'in')::text, true);
    INSERT INTO _res SELECT 'c1', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c1$;

-- c2: OPERATORE, whitelist = ALTRO emittente -> NON visibile (no leak cliente/shop)
DO $c2$
BEGIN
    -- L'operatore 'out' ha in whitelist un ALTRO emittente.
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'out')::text, true);
    INSERT INTO _res SELECT 'c2', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c2$;

-- c3: CLIENTE_PORTALE con identita NON proprietaria -> NON visibile (non eredita)
DO $c3$
BEGIN
    -- whitelist match (irrilevante: ef policy gated off perche' ruolo != OPERATORE)
    PERFORM set_config('app.ruolo_applicativo', 'CLIENTE_PORTALE', true);
    PERFORM set_config('app.current_identita_id', (SELECT identita_id FROM _op WHERE tag = 'in')::text, true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'in')::text, true);
    INSERT INTO _res SELECT 'c3', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c3$;

-- c4: nessun ruolo -> NON visibile (fail-closed)
DO $c4$
BEGIN
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_identita_id', '', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE tag = 'in')::text, true);
    INSERT INTO _res SELECT 'c4', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));
END $c4$;

-- c5: DISABLE RLS (kill-switch) -> di nuovo visibile
ALTER TABLE vendite.ordini NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.ordini DISABLE ROW LEVEL SECURITY;
INSERT INTO _res
SELECT 'c5', EXISTS (SELECT 1 FROM vendite.ordini WHERE id = (SELECT ordine_id FROM _refs));

-- Asserzioni
SELECT ok((SELECT visibile FROM _res WHERE caso='c1'),
    '1. OPERATORE whitelist = emittente ordine -> visibile (policy EF)');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c2'),
    '2. OPERATORE whitelist = altro emittente -> NON visibile (no leak cliente/shop)');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c3'),
    '3. CLIENTE_PORTALE identita non proprietaria -> NON visibile (non eredita)');
SELECT ok(NOT (SELECT visibile FROM _res WHERE caso='c4'),
    '4. nessun ruolo -> NON visibile (fail-closed)');
SELECT ok((SELECT visibile FROM _res WHERE caso='c5'),
    '5. DISABLE RLS (kill-switch) -> ordine di nuovo visibile');

SELECT * FROM finish();
ROLLBACK;
