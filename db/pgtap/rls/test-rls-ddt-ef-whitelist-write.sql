-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgtap-contesto: escluso — la ragione e' scritta per esteso piu' sotto in
--   questo stesso file. Dichiarazione leggibile dal cancello
--   scripts/guardrail_pgtap_preambolo.py: distingue «escluso apposta» da
--   «dimenticato», che una nota in prosa non fa.
--   ⚠️ Da riguardare: le esclusioni `rls/` furono fatte IN BLOCCO, e almeno
--   una non ne aveva diritto (brief pgtap-runner-rls-baseline §30.2).
-- pgtap-runner: owner
-- pgtap-runner-motivo: ALTER TABLE vendite.ddt ENABLE + FORCE ROW LEVEL SECURITY, locale alla
--   transazione: e' il FORCE a rendere l'owner soggetto alle policy.
-- pgTAP test FUNZIONALE scrittura/lettura RLS — vendite.ddt (ef_whitelist)
--
-- Addendum SCOPE §15: policy rls_ddt_ef_whitelist (FOR ALL, dry-run) su
-- vendite.ddt. La RLS non e' attiva permanentemente (mirror ordini): qui si
-- attiva ENABLE + FORCE LOCALE alla transazione per verificare lo scope, poi
-- ROLLBACK ripristina lo stato.
--
-- ⭐ Rev 2026-10-07 (brief-db-fixture-rls-documenti-costruiti, giro 1): IL
--   MONDO SI COSTRUISCE. Fino a oggi il file pescava BA, soggetto, articolo e
--   «i primi due emittenti», costruiva ordine e DDT dentro un
--   `EXCEPTION WHEN OTHERS THEN NULL` e, se qualcosa mancava, andava in
--   SOFT-SKIP: su zeroerp_ci (da zero) i casi passavano senza misurare, e un
--   guard che rifiutava la fixture veniva inghiottito senza dirlo. Ora due
--   aziende costruite — A possiede la bolla, B e' l'estranea — e la bolla di A
--   (dbops.fn_pgtap_crea_ddt). Se qualcosa non si costruisce il file va ROSSO.
--   Modello: test-rls-resi-ef-whitelist-write.
--
-- Ordine (importante):
--   1) costruisci le due aziende e la bolla di A, PRIMA del FORCE (da owner,
--      nessuna policy filtra la fixture);
--   2) ALTER ENABLE/FORCE: i builder escono IMMEDIATE, nessun evento in sospeso
--      (un ALTER TABLE con eventi in sospeso e' rifiutato);
--   3) crea gli operatori dalla madre, completi;
--   4) casi in-scope / off-scope / no-ruolo con UPDATE no-op (SET meta=meta).
-- Niente kill-switch DISABLE (richiederebbe un secondo ALTER in conflitto con i
-- trigger deferred degli UPDATE).
--
-- Conteggio righe aggiornate:
--   in-scope  -> 1 (policy FOR ALL permette lo scope)
--   off-scope -> 0 (USING isola per emittente)
--   no ruolo  -> 0 (gate fail-closed)
--
-- Indice test (0..3):
--   0. fixture: bolla di A costruita, B e' un'altra azienda
--   1. OPERATORE in-scope  -> UPDATE 1 riga
--   2. OPERATORE off-scope -> UPDATE 0 righe
--   3. nessun ruolo        -> UPDATE 0 righe
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. In testa e non in coda: in coda
--   scatterebbero dopo il cleanup, su righe ormai cancellate.
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(4);

-- 1) Le due aziende e la bolla di A.
-- B prima di tutto, e PRIMA di qualunque contesto: e' un builder atomico.
CREATE TEMP TABLE _b AS
SELECT * FROM dbops.fn_pgtap_crea_emittente_operatore();

-- A: senza contesto aperto, il mondo cliente costruisce l'azienda, l'operatore
-- (tecnico) e il cliente, e apre il contesto su di lui: la bolla nasce con
-- l'emittente di chi agisce (script.fn_pgtap_emittente_operatore).
CREATE TEMP TABLE _a AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('rls ddt');

CREATE TEMP TABLE _ddt AS
SELECT dbops.fn_pgtap_crea_ddt(a.billing_account_id, a.cliente_soggetto_ruolo_id, 'VENDITA') AS ddt_id,
       a.emittente_fiscale_id AS emit_pk,
       b.emittente_fiscale_id AS other_pk
  FROM _a a, _b b;

-- ⚠️ Il builder ha lasciato aperto il contesto del SUO operatore. Qui l'identita'
--   la dichiara ogni caso: si riparte da «nessuno».
SELECT set_config('app.ruolo_applicativo', '', false),
       set_config('app.current_user_id',   '', false);

SELECT ok(
    (SELECT d.emittente_fiscale_id = x.emit_pk AND x.emit_pk <> x.other_pk
       FROM _ddt x JOIN vendite.ddt d ON d.id = x.ddt_id),
    '0. Fixture: bolla di A costruita, B e'' un''altra azienda');

-- 2) ENABLE/FORCE.
ALTER TABLE vendite.ddt ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.ddt FORCE  ROW LEVEL SECURITY;

-- 3) Operatori (whitelist emittente in config.user_emittenti_fiscali).
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
      FROM dbops.fn_pgtap_crea_operatore_umano('rls ddt ' || p_tag);

    -- Istruzione separata: cio' che il builder scrive si legge da qui in poi.
    PERFORM script.fn_change_user_emittenti_scope(v_op.auth_user_id, ARRAY[p_emit]);

    INSERT INTO _op VALUES (p_tag, v_op.auth_user_id);
END
$fn$;

DO $ops$
BEGIN
    PERFORM pg_temp.mk_op('in',  (SELECT emit_pk  FROM _ddt));
    PERFORM pg_temp.mk_op('out', (SELECT other_pk FROM _ddt));
END
$ops$;

CREATE TEMP TABLE _res (caso text, n_righe integer);

-- Caso 1: in-scope -> 1 riga
DO $c1$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
    UPDATE vendite.ddt SET meta = meta WHERE id = (SELECT ddt_id FROM _ddt);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c1', v_n);
END
$c1$;

-- Caso 2: off-scope -> 0 righe
DO $c2$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
    UPDATE vendite.ddt SET meta = meta WHERE id = (SELECT ddt_id FROM _ddt);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', '', true);
    INSERT INTO _res VALUES ('c2', v_n);
END
$c2$;

-- Caso 3: nessun ruolo -> 0 righe (fail-closed)
DO $c3$
DECLARE v_n integer;
BEGIN
    PERFORM set_config('app.ruolo_applicativo', '', true);
    PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
    UPDATE vendite.ddt SET meta = meta WHERE id = (SELECT ddt_id FROM _ddt);
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO _res VALUES ('c3', v_n);
END
$c3$;

-- ===================== Asserzioni =====================
SELECT ok((SELECT n_righe = 1 FROM _res WHERE caso='c1'),
    '1. OPERATORE in-scope: UPDATE tocca la riga (scope emittente ok)');
SELECT ok((SELECT n_righe = 0 FROM _res WHERE caso='c2'),
    '2. OPERATORE off-scope: UPDATE tocca 0 righe (USING isola per emittente)');
SELECT ok((SELECT n_righe = 0 FROM _res WHERE caso='c3'),
    '3. Nessun ruolo: UPDATE tocca 0 righe (gate fail-closed)');

SELECT * FROM finish();
ROLLBACK;
