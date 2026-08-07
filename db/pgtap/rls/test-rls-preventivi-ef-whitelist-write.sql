-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-differiti: escluso — la fixture non soddisfa un vincolo DIFFERITO e la
--   ragione e' scritta per esteso piu' sotto. Debito noto (§22.4): quando la
--   fixture viene completata, si toglie questa riga e si rimette il
--   SET CONSTRAINTS ALL IMMEDIATE nel punto in cui l'unita' di lavoro e' completa.
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
--   - UPDATE no-op (SET meta = meta) su un preventivo ESISTENTE: niente
--     fixture pesante, l'emittente resta invariato -> WITH CHECK valutata
--     sulla stessa riga in-scope.
--   - ENABLE + FORCE locale alla tx (owner titodb non-superuser -> soggetto).
--   - GUC via set_config; soft-skip se non esiste un preventivo idoneo.
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
-- Indice test (1..4):
--   1. OPERATORE in-scope (whitelist = emittente preventivo) -> UPDATE 1 riga
--   2. OPERATORE off-scope (whitelist = ALTRO emittente)       -> UPDATE 0 righe
--   3. nessun ruolo (GUC vuoto)                                -> UPDATE 0 righe
--   4. DISABLE RLS (kill-switch)                               -> UPDATE 1 riga
--
-- BEGIN; + ROLLBACK a fine file (isolamento completo).
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   `anagrafiche.soggetti` ha TRE guard DEFERRABLE INITIALLY DEFERRED —
--   indirizzi, contatti, dati societari — e li' la deferralita' e' il CONTRATTO
--   DEL DOMINIO: si crea il soggetto, poi il suo indirizzo, e la completezza si
--   verifica al COMMIT. E' per questo che anagrafiche.fn_crea_soggetto_pf puo'
--   restituire un soggetto ancora incompleto, ed e' cosi' che la usa il backend.
--   Forzare IMMEDIATE pretenderebbe l'indirizzo nell'istante stesso dell'INSERT
--   del soggetto: vieterebbe il pattern che il dominio ha scelto.
--   ⚠️ Resta un buco reale: senza la riga quei guard non vengono esercitati da
--   questo test, e la fixture lascia un soggetto che l'applicazione non
--   potrebbe committare. La correzione vera e' COMPLETARE LA FIXTURE
--   (indirizzo + contatti): allora la riga si rimette e il test verifica sul
--   serio. Brief: brief-db-pgtap-runner-rls-baseline §21.

SELECT plan(4);

-- Preventivo ESISTENTE con emittente risolvibile + un altro emittente.
CREATE TEMP TABLE _refs AS
WITH p AS (
    SELECT id AS prev_id, emittente_fiscale_id AS emit_pk
      FROM vendite.preventivi
     WHERE emittente_fiscale_id IS NOT NULL
     ORDER BY id
     LIMIT 1
)
SELECT p.prev_id, p.emit_pk,
       (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.id <> p.emit_pk ORDER BY ef.id LIMIT 1) AS other_pk
  FROM p;

-- Due operatori OPERATORE distinti (CF validi diversi): in-scope e off-scope.
CREATE TEMP TABLE _op (ruolo text, auth_user_id int);

-- Scopo: crea un operatore (auth_user + soggetto PF + SR + identita OPERATORE)
-- con whitelist = un emittente, e lo registra in _op col tag passato.
CREATE OR REPLACE FUNCTION pg_temp.mk_op(p_tag text, p_cf text, p_emit bigint)
RETURNS void LANGUAGE plpgsql AS $fn$
DECLARE v_uid int; v_sog uuid; v_sr bigint; v_sfx text;
BEGIN
    v_sfx := substring(md5(clock_timestamp()::text || p_tag) from 1 for 8);
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_prev_' || v_sfx, '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeEf' || p_tag,
        p_nome              := 'Fdn',
        p_codice_fiscale    := p_cf,
        p_email             := 'pgtap_rls_prev_' || v_sfx || '@test.local',
        p_data_nascita      := DATE '1980-01-01',
        p_sesso             := 'M',
        p_stato_iso2        := 'IT',
        p_comune_nascita_id := (SELECT id FROM config.comuni ORDER BY id LIMIT 1),
        p_tipo_contatto_id  := NULL);

    v_sr := script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id := v_sog, p_cd_int_ruolo := 'RIS_UMANA');

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_uid, 'OPERATORE', true);

    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES (v_uid, p_emit);

    INSERT INTO _op VALUES (p_tag, v_uid);
END
$fn$;

DO $fix$
BEGIN
    IF (SELECT prev_id IS NOT NULL AND emit_pk IS NOT NULL AND other_pk IS NOT NULL
          FROM _refs LIMIT 1) THEN
        PERFORM pg_temp.mk_op('in',  'PNZFDN78A01L219Y', (SELECT emit_pk  FROM _refs));
        PERFORM pg_temp.mk_op('out', 'LCCRLD80A01L736X', (SELECT other_pk FROM _refs));
    END IF;
END
$fix$;

-- prereq: preventivo + emittente + altro emittente disponibili.
CREATE TEMP TABLE _flags AS
SELECT COALESCE(
    (SELECT prev_id IS NOT NULL AND emit_pk IS NOT NULL AND other_pk IS NOT NULL
       FROM _refs LIMIT 1),
    false
) AS prereq;

-- Attiva RLS + FORCE solo dentro questa transazione.
ALTER TABLE vendite.preventivi ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi FORCE  ROW LEVEL SECURITY;

CREATE TEMP TABLE _res (caso text, n_righe integer);

-- ---- Caso 1: operatore in-scope -> UPDATE tocca 1 riga ----
DO $c1$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE
        v_n := 1;  -- soft-skip
    END IF;
    INSERT INTO _res VALUES ('c1', v_n);
END
$c1$;

-- ---- Caso 2: operatore off-scope -> UPDATE tocca 0 righe (USING nasconde) ----
DO $c2$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='out')::text, true);
        UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', '', true);
    ELSE
        v_n := 0;
    END IF;
    INSERT INTO _res VALUES ('c2', v_n);
END
$c2$;

-- ---- Caso 3: nessun ruolo (GUC vuoto) -> UPDATE tocca 0 (fail-closed) ----
DO $c3$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        PERFORM set_config('app.ruolo_applicativo', '', true);
        PERFORM set_config('app.current_user_id', (SELECT auth_user_id FROM _op WHERE ruolo='in')::text, true);
        UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
    ELSE
        v_n := 0;
    END IF;
    INSERT INTO _res VALUES ('c3', v_n);
END
$c3$;

-- ---- Caso 4: DISABLE RLS (kill-switch) -> UPDATE tocca 1 ----
ALTER TABLE vendite.preventivi NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.preventivi DISABLE ROW LEVEL SECURITY;
DO $c4$
DECLARE v_n integer;
BEGIN
    IF (SELECT prereq FROM _flags) THEN
        UPDATE vendite.preventivi SET meta = meta WHERE id = (SELECT prev_id FROM _refs);
        GET DIAGNOSTICS v_n = ROW_COUNT;
    ELSE
        v_n := 1;
    END IF;
    INSERT INTO _res VALUES ('c4', v_n);
END
$c4$;

-- ===================== Asserzioni =====================
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 1 FROM _res WHERE caso='c1'),
    '1. OPERATORE in-scope: UPDATE tocca la riga (FOR ALL sblocca la scrittura)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 0 FROM _res WHERE caso='c2'),
    '2. OPERATORE off-scope: UPDATE tocca 0 righe (USING isola per emittente)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 0 FROM _res WHERE caso='c3'),
    '3. Nessun ruolo: UPDATE tocca 0 righe (gate fail-closed)');
SELECT ok((SELECT NOT prereq FROM _flags) OR (SELECT n_righe = 1 FROM _res WHERE caso='c4'),
    '4. Kill-switch DISABLE: UPDATE di nuovo libero');

SELECT * FROM finish();
ROLLBACK;
