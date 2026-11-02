-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.preventivi ENABLE + FORCE ROW LEVEL SECURITY, locale alla
--   transazione: e' il FORCE a rendere l'owner soggetto alle policy.
-- pgTAP test FUNZIONALE scrittura RLS — vendite.preventivi (ef_whitelist)
--
-- Brief RLS Ondata 2 ("insert bloccati"): la migration 20260603-16 estende
-- rls_preventivi_ef_whitelist da FOR SELECT a FOR ALL con WITH CHECK = USING.
-- Prima del fix, con RLS attiva, ogni scrittura operatore (anche in-scope)
-- falliva perche' nessuna policy copriva INSERT/UPDATE/DELETE.
--
-- Obiettivo: dimostrare che dopo il fix una SCRITTURA in-scope passa
-- (la policy FOR ALL la consente), mentre fuori-scope / senza ruolo no.
-- Tecnica (come gli altri test RLS funzionali del repo):
--   - UPDATE no-op (SET meta = meta) sul preventivo di A: l'emittente resta
--     invariato -> WITH CHECK valutata sulla stessa riga in-scope.
--   - ENABLE + FORCE locale alla tx (owner titodb non-superuser -> soggetto).
--   - GUC via set_config.
--
-- ⭐ Rev 2026-10-07 (brief-db-fixture-rls-documenti-costruiti, giro 2): IL
--   MONDO SI COSTRUISCE. Fino a oggi il file pescava «il primo preventivo con un
--   emittente» e «il primo altro emittente», e senza dati andava in SOFT-SKIP:
--   su zeroerp_ci (da zero) i casi passavano senza misurare niente. Ora due
--   aziende costruite — A possiede il preventivo, B e' l'estranea — e il preventivo
--   di A (dbops.fn_pgtap_crea_preventivo), tutto PRIMA del FORCE. Se qualcosa non si
--   costruisce il file va ROSSO. Modello: test-rls-resi-ef-whitelist-write.
--
-- NB di modello: config.user_emittenti_fiscali ha UNIQUE su auth_user_id
-- (1 sola riga/utente), DELETE vietato (guard) e emittente_fiscale_id
-- immutabile (lock). Quindi in/off-scope si testano con DUE operatori
-- distinti, non flippando la whitelist.
--
-- Il conteggio righe aggiornate distingue la copertura scrittura:
--   in-scope  -> 1 riga (la policy FOR ALL permette UPDATE)
--   off-scope -> 0 righe (USING nasconde la riga)
--   no ruolo  -> 0 righe (gate fail-closed)
--
-- Indice test (0..4):
--   0. fixture: preventivo di A costruito, B e' un'altra azienda
--   1. OPERATORE in-scope (whitelist = emittente preventivo) -> UPDATE 1 riga
--   2. OPERATORE off-scope (whitelist = ALTRO emittente)       -> UPDATE 0 righe
--   3. nessun ruolo (GUC vuoto)                                -> UPDATE 0 righe
--   4. DISABLE RLS (kill-switch)                               -> UPDATE 1 riga
--
-- BEGIN; + ROLLBACK a fine file (isolamento completo).
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
-- ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): fino a oggi questo file non
--   la aveva, perche' costruiva l'operatore a mano con fn_crea_soggetto_pf e
--   lasciava il soggetto senza indirizzo, contando sul ROLLBACK (§22.4). Ora
--   l'operatore viene dalla madre (dbops.fn_pgtap_crea_operatore_umano), che
--   lo consegna COMPLETO: la riga torna, e i guard del soggetto si esercitano.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- Le due aziende e il preventivo di A.
-- B prima di tutto, e PRIMA di qualunque contesto: e' un builder atomico.
CREATE TEMP TABLE _b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- A: senza contesto aperto, il builder costruisce l'azienda, l'operatore
-- (tecnico), il cliente e il preventivo, e apre il contesto su quell'operatore.
CREATE TEMP TABLE _a AS
SELECT * FROM dbops.fn_pgtap_crea_preventivo('rls preventivi');

-- ⚠️ Il builder ha lasciato aperto il contesto del SUO operatore. Qui l'identita'
--   la dichiara ogni caso: si riparte da «nessuno».
SELECT set_config('app.ruolo_applicativo', '', false),
       set_config('app.current_user_id',   '', false);

CREATE TEMP TABLE _refs AS
SELECT a.preventivo_id        AS prev_id,
       a.emittente_fiscale_id AS emit_pk,
       b.emittente_fiscale_id AS other_pk
  FROM _a a, _b b;

SELECT ok(
    (SELECT p.emittente_fiscale_id = r.emit_pk AND r.emit_pk <> r.other_pk
       FROM _refs r JOIN vendite.preventivi p ON p.id = r.prev_id),
    '0. Fixture: preventivo di A costruito, B e'' un''altra azienda');

-- Due operatori OPERATORE distinti: in-scope e off-scope.
CREATE TEMP TABLE _op (ruolo text, auth_user_id int);

-- Scopo: crea un operatore con whitelist = un emittente, e lo registra in _op
-- col tag passato.
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
      FROM dbops.fn_pgtap_crea_operatore_umano('rls preventivi ' || p_tag);

    -- Istruzione separata: cio' che il builder scrive si legge da qui in poi.
    PERFORM script.fn_change_user_emittenti_scope(v_op.auth_user_id, ARRAY[p_emit]);

    INSERT INTO _op VALUES (p_tag, v_op.auth_user_id);
END
$fn$;

DO $fix$
BEGIN
    PERFORM pg_temp.mk_op('in',  (SELECT emit_pk  FROM _refs));
    PERFORM pg_temp.mk_op('out', (SELECT other_pk FROM _refs));
END
$fix$;

-- Attiva RLS + FORCE solo dentro questa transazione.
ALTER TABLE vendite.preventivi ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, n_righe integer);

-- ---- Caso 1: operatore in-scope -> UPDATE tocca 1 riga ----
DO $c1$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
    UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c1', v_n);
END
$c1$;

-- ---- Caso 2: operatore off-scope -> UPDATE tocca 0 righe (USING nasconde) ----
DO $c2$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
    UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c2', v_n);
END
$c2$;

-- ---- Caso 3: nessun ruolo (GUC vuoto) -> UPDATE tocca 0 (fail-closed) ----
DO $c3$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
    UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res VALUES ('c3', v_n);
END
$c3$;

-- ---- Caso 4: DISABLE RLS (kill-switch) -> UPDATE tocca 1 ----
ALTER TABLE vendite.preventivi NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi DISABLE ROW LEVEL SECURITY;
DO $c4$
DECLARE v_n integer;
BEGIN
    UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res VALUES ('c4', v_n);
END
$c4$;

-- ===================== Asserzioni =====================
SELECT ok((SELECT n_righe = 1 FROM _res WHERE caso='c1'),
    '1. OPERATORE in-scope: UPDATE tocca la riga (FOR ALL sblocca la scrittura)');
SELECT ok((SELECT n_righe = 0 FROM _res WHERE caso='c2'),
    '2. OPERATORE off-scope: UPDATE tocca 0 righe (USING isola per emittente)');
SELECT ok((SELECT n_righe = 0 FROM _res WHERE caso='c3'),
    '3. Nessun ruolo: UPDATE tocca 0 righe (gate fail-closed)');
SELECT ok((SELECT n_righe = 1 FROM _res WHERE caso='c4'),
    '4. Kill-switch DISABLE: UPDATE di nuovo libero');

SELECT * FROM finish();
ROLLBACK;
