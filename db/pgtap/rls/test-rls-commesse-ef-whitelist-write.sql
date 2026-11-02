-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.commesse / commesse_attivita ENABLE + FORCE ROW LEVEL
--   SECURITY, locale alla transazione: e' il FORCE a rendere l'owner soggetto
--   alle policy. L'identita' la simulano le GUC app.*, non il ruolo di connessione.
-- pgTAP test FUNZIONALE scrittura/lettura RLS — vendite.commesse +
--   vendite.commesse_attivita (ef_whitelist).
--
-- Policy rls_commesse_ef_whitelist (via_sr) e rls_commesse_attivita_ef_whitelist
-- (via_commessa, delega al padre). La RLS non e' attiva permanentemente (mirror
-- famiglia): qui si attiva ENABLE + FORCE LOCALE alla transazione per verificare
-- lo scope, poi ROLLBACK ripristina lo stato.
--
-- ⭐ Rev 2026-10-07 (brief-db-fixture-rls-documenti-costruiti, giro 3): IL
--   MONDO SI COSTRUISCE. Fino a oggi il file pescava «la prima commessa con un
--   emittente e almeno un'attivita'» e «il primo altro emittente», e senza dati
--   andava in SOFT-SKIP: su zeroerp_ci (da zero) i casi passavano senza
--   misurare niente. Ora due aziende costruite — A possiede la commessa, B e'
--   l'estranea — e la commessa di A con un'attivita'
--   (dbops.fn_pgtap_crea_commessa + fn_pgtap_crea_commessa_attivita, dalle
--   madri del dominio), tutto PRIMA del FORCE. Se qualcosa non si costruisce il
--   file va ROSSO. Modello: test-rls-resi-ef-whitelist-write.
--
-- Ordine (mirror test-rls-resi-ef-whitelist-write):
--   1) le due aziende, la commessa di A e la sua attivita';
--   2) ENABLE/FORCE su commesse e commesse_attivita;
--   3) crea gli operatori dalla madre, completi (i vincoli restano IMMEDIATE);
--   4) casi in-scope / off-scope / no-ruolo con UPDATE no-op (SET meta=meta).
--
-- Indice test (0..5):
--   0. fixture: commessa di A con un'attivita', B e' un'altra azienda
--   1. OPERATORE in-scope  -> UPDATE commesse 1 riga
--   2. OPERATORE off-scope -> UPDATE commesse 0 righe (USING isola per emittente)
--   3. nessun ruolo        -> UPDATE commesse 0 righe (gate fail-closed)
--   4. OPERATORE in-scope  -> UPDATE commesse_attivita 1 riga (scope via padre)
--   5. OPERATORE off-scope -> UPDATE commesse_attivita 0 righe
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. In testa e non in coda: in coda
--   scatterebbero dopo il cleanup, su righe ormai cancellate.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(6);

-- 1) Le due aziende, la commessa di A e la sua attivita'.
-- B prima di tutto, e PRIMA di qualunque contesto: e' un builder atomico.
CREATE TEMP TABLE _b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- A: senza contesto aperto, il builder costruisce l'azienda, l'operatore
-- (tecnico), il cliente e la commessa, e apre il contesto su quell'operatore.
CREATE TEMP TABLE _a AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('rls commesse');

CREATE TEMP TABLE _att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM _a));

-- ⚠️ Il builder ha lasciato aperto il contesto del SUO operatore. Qui l'identita'
--   la dichiara ogni caso: si riparte da «nessuno».
SELECT set_config('app.ruolo_applicativo', '', false),
       set_config('app.current_user_id',   '', false);

CREATE TEMP TABLE _refs AS
SELECT a.commessa_id,
       a.emittente_soggetto_ruolo_id AS emit_sr,
       a.emittente_fiscale_id        AS emit_in_fiscale,
       b.emittente_fiscale_id        AS emit_out_fiscale
  FROM _a a, _b b;

SELECT ok(
    (SELECT c.emittente_soggetto_ruolo_id = r.emit_sr
            AND r.emit_in_fiscale <> r.emit_out_fiscale
            AND (SELECT count(*) FROM vendite.commesse_attivita ca
                  WHERE ca.commessa_id = r.commessa_id) = 1
       FROM _refs r JOIN vendite.commesse c ON c.id = r.commessa_id),
    '0. Fixture: commessa di A con un''attivita'', B e'' un''altra azienda');

-- 2) ENABLE/FORCE su padre e satellite (i builder escono IMMEDIATE: nessun
--    evento in sospeso, che un ALTER TABLE rifiuterebbe).
ALTER TABLE vendite.commesse           ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse           FORCE  ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita  ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.commesse_attivita  FORCE  ROW LEVEL SECURITY;

-- 3) Operatori DOPO l'ALTER (whitelist emittente in config.user_emittenti_fiscali).
CREATE TEMP TABLE _op (ruolo text, auth_user_id int);

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
      FROM dbops.fn_pgtap_crea_operatore_umano('rls commesse ' || p_tag);

    -- Istruzione separata: cio' che il builder scrive si legge da qui in poi.
    PERFORM script.fn_change_user_emittenti_scope(v_op.auth_user_id, ARRAY[p_emit]);

    INSERT INTO _op VALUES (p_tag, v_op.auth_user_id);
END
$fn$;

DO $ops$
BEGIN
    PERFORM pg_temp.mk_op('in',  (SELECT emit_in_fiscale  FROM _refs));
    PERFORM pg_temp.mk_op('out', (SELECT emit_out_fiscale FROM _refs));
END
$ops$;

CREATE TEMP TABLE _res (caso text, n_righe integer);

-- Caso 1: in-scope commesse -> 1
DO $c1$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
    UPDATE vendite.commesse SET meta = meta WHERE id = (SELECT commessa_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c1', v_n);
END
$c1$;

-- Caso 2: off-scope commesse -> 0
DO $c2$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
    UPDATE vendite.commesse SET meta = meta WHERE id = (SELECT commessa_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c2', v_n);
END
$c2$;

-- Caso 3: nessun ruolo -> 0 (fail-closed)
DO $c3$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
    UPDATE vendite.commesse SET meta = meta WHERE id = (SELECT commessa_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c3', v_n);
END
$c3$;

-- Caso 4: in-scope commesse_attivita -> >0 (scope delegato al padre)
DO $c4$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
    UPDATE vendite.commesse_attivita SET meta = meta WHERE commessa_id = (SELECT commessa_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c4', v_n);
END
$c4$;

-- Caso 5: off-scope commesse_attivita -> 0
DO $c5$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
    UPDATE vendite.commesse_attivita SET meta = meta WHERE commessa_id = (SELECT commessa_id FROM _refs);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c5', v_n);
END
$c5$;

-- ===================== Asserzioni =====================
SELECT ok((SELECT n_righe = 1 FROM _res WHERE caso='c1'),
    '1. OPERATORE in-scope: UPDATE commesse tocca la riga (scope emittente via_sr ok)');
SELECT ok((SELECT n_righe = 0 FROM _res WHERE caso='c2'),
    '2. OPERATORE off-scope: UPDATE commesse tocca 0 righe (USING isola per emittente)');
SELECT ok((SELECT n_righe = 0 FROM _res WHERE caso='c3'),
    '3. Nessun ruolo: UPDATE commesse tocca 0 righe (gate fail-closed)');
SELECT ok((SELECT n_righe = 1 FROM _res WHERE caso='c4'),
    '4. OPERATORE in-scope: UPDATE commesse_attivita tocca la sua riga (scope via padre)');
SELECT ok((SELECT n_righe = 0 FROM _res WHERE caso='c5'),
    '5. OPERATORE off-scope: UPDATE commesse_attivita tocca 0 righe (scope via padre)');

SELECT * FROM finish();
ROLLBACK;
