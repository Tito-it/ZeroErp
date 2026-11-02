-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: anagrafiche.fn_crea_risorsa_umana_v2 — UNA PERSONA E' UNA RISORSA
--   UMANA SOLA (uq_risorse_umane_soggetto_ruolo, non parziale).
--   ChangeSet: 20261002-01 (il guard), codice E_RISORSA_UMANA_GIA_PRESENTE.
--   Richiesta del team BE, 2026-10-02.
--
-- ⛔ COSA PRESIDIA. Il secondo operatore sullo stesso soggetto (flusso B di
--   fn_crea_operatore_v2) arrivava fino all'INSERT e il client riceveva un
--   23505 nudo, E_DATABASE. Ora rifiuta PRIMA, con un codice a catalogo, il
--   campo (soggetto_id) e il nome della persona nella frase — e lo fa anche
--   quando la risorsa umana che c'e' e' SPENTA, perche' il vincolo non e'
--   parziale.
--
-- ⭐ Casi COSTRUITI: l'operatore esistente lo fabbrica
--   dbops.fn_pgtap_crea_operatore_umano (la madre di produzione); il secondo
--   tentativo usa un'email NUOVA, cosi' la credenziale nasce e i controlli
--   sulla credenziale (E_CREDENZIALE_*) non parlano prima del guard.
--
-- ⚠️ pg_temp.esito cattura QUALUNQUE errore e ne restituisce il SQLSTATE se
--   non e' un P0001: un 23505 tornato indietro esce come «SQLSTATE 23505» in
--   un rosso leggibile, non come un'eccezione che ferma il file.
--
-- Elenco test (plan 8):
--   Risorsa umana ATTIVA
--    1) flusso B sullo stesso soggetto, email nuova -> E_RISORSA_UMANA_GIA_PRESENTE
--    2) ...il campo e' soggetto_id (il canale che accende il campo a video)
--    3) ...la frase porta il nome della persona, non un buco
--    4) ...e niente e' rimasto scritto: nessuna credenziale con quell'email,
--       una sola risorsa umana sul soggetto
--    5) il building block chiamato direttamente -> stesso codice (vale per
--       ogni chiamante, non solo per fn_crea_operatore_v2)
--   Risorsa umana SPENTA
--    6) precondizione: identita' e risorsa umana spente davvero
--    7) flusso B sullo stesso soggetto -> E_RISORSA_UMANA_GIA_PRESENTE
--    8) il building block chiamato direttamente -> stesso codice
-- ------------------------------------------------------------
BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(8);

-- ============================================================
-- Fixture
-- ============================================================
-- Codice (CONSTRAINT_NAME), campo (COLUMN_NAME) e frase dell'errore; per un
-- errore che non e' un P0001, il suo SQLSTATE.
CREATE OR REPLACE FUNCTION pg_temp.esito(p_sql text)
RETURNS TABLE (codice text, campo text, frase text)
LANGUAGE plpgsql AS $$
DECLARE v_c text; v_col text; v_m text; v_st text;
BEGIN
    EXECUTE p_sql;
    RETURN QUERY SELECT NULL::text, NULL::text, NULL::text;
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_c = CONSTRAINT_NAME, v_col = COLUMN_NAME,
                            v_m = MESSAGE_TEXT, v_st = RETURNED_SQLSTATE;
    IF v_st <> 'P0001' THEN
        RETURN QUERY SELECT 'SQLSTATE ' || v_st, NULL::text, v_m;
    ELSE
        RETURN QUERY SELECT v_c, v_col, v_m;
    END IF;
END $$;

-- L'operatore che c'e' gia'.
CREATE TEMP TABLE _op AS
SELECT o.auth_user_id, o.identita_id, o.risorsa_umana_id, o.soggetto_ruolo_id, o.soggetto_id
  FROM dbops.fn_pgtap_crea_operatore_umano('risorsa gia presente', false) o;

CREATE TEMP TABLE _q AS
SELECT q.id AS qualifica_id FROM config.qualifiche q WHERE q.codice_interno = 'DIPENDENTE';

-- Il secondo operatore sullo STESSO soggetto (flusso B), con un'email nuova.
CREATE OR REPLACE FUNCTION pg_temp.secondo_operatore(p_tag text) RETURNS text
LANGUAGE sql AS $$
    SELECT format(
        $f$SELECT * FROM anagrafiche.fn_crea_operatore_v2(
               p_soggetto_id   := %L::uuid,
               p_username      := %L,
               p_email         := %L,
               p_password_hash := 'pgtap-nessun-login',
               p_qualifica_id  := %s)$f$,
        (SELECT soggetto_id FROM _op),
        '_pgtap_ru_' || p_tag,
        'pgtap.ru.' || p_tag || '@example.com',
        (SELECT qualifica_id FROM _q))
$$;

-- Il building block, chiamato direttamente sullo stesso soggetto.
CREATE OR REPLACE FUNCTION pg_temp.bb_diretto() RETURNS text
LANGUAGE sql AS $$
    SELECT format(
        $f$SELECT anagrafiche.fn_crea_risorsa_umana_v2(
               p_soggetto_id  := %L::uuid,
               p_qualifica_id := %s)$f$,
        (SELECT soggetto_id FROM _op), (SELECT qualifica_id FROM _q))
$$;

CREATE TEMP TABLE _tag AS
SELECT substring(md5(clock_timestamp()::text || random()::text) from 1 for 10) AS k;

-- ============================================================
-- 1-5) Risorsa umana ATTIVA
-- ============================================================
CREATE TEMP TABLE _e1 AS
SELECT * FROM pg_temp.esito(pg_temp.secondo_operatore((SELECT k FROM _tag) || '_a'));

SELECT is((SELECT codice FROM _e1), 'E_RISORSA_UMANA_GIA_PRESENTE',
    '1) flusso B sullo stesso soggetto, email nuova: E_RISORSA_UMANA_GIA_PRESENTE (non piu'' 23505)');

SELECT is((SELECT campo FROM _e1), 'soggetto_id',
    '2) il campo e'' soggetto_id: e'' il canale che accende il campo a video');

-- La frase: il nome della persona davanti, mai «  e' gia'...» con un buco.
SELECT ok(
    (SELECT frase ~ '^\S.*gia'' una risorsa umana\.$'
            AND frase LIKE (SELECT '%' || s.cognome || '%' FROM anagrafiche.soggetti s
                             WHERE s.id = (SELECT soggetto_id FROM _op))
       FROM _e1),
    '3) la frase porta il nome della persona, non un segnaposto vuoto');

SELECT is(
    (SELECT (SELECT count(*) FROM django.auth_user
              WHERE lower(email) = 'pgtap.ru.' || (SELECT k FROM _tag) || '_a@example.com')::text
            || '|' ||
            (SELECT count(*) FROM anagrafiche.risorse_umane
              WHERE soggetto_id = (SELECT soggetto_id FROM _op))::text),
    '0|1',
    '4) niente scritto: nessuna credenziale con l''email nuova, una sola risorsa umana sul soggetto');

SELECT is((SELECT codice FROM pg_temp.esito(pg_temp.bb_diretto())), 'E_RISORSA_UMANA_GIA_PRESENTE',
    '5) il building block chiamato direttamente: stesso codice, vale per ogni chiamante');

-- ============================================================
-- 6-8) Risorsa umana SPENTA — il vincolo non e' parziale
-- ============================================================
-- Figli prima, padre poi (trgfn_risorse_umane_guard_identita_attiva).
UPDATE anagrafiche.identita_digitali
   SET attivo = false
 WHERE id = (SELECT identita_id FROM _op);

UPDATE anagrafiche.risorse_umane
   SET attivo = false
 WHERE id = (SELECT risorsa_umana_id FROM _op);

SELECT is(
    (SELECT i.attivo::text || '|' || ru.attivo::text
       FROM anagrafiche.identita_digitali i
       JOIN anagrafiche.risorse_umane ru ON ru.soggetto_ruolo_id = i.soggetto_ruolo_id
      WHERE i.id = (SELECT identita_id FROM _op)),
    'false|false',
    '6) precondizione: identita'' OPERATORE e risorsa umana spente davvero');

SELECT is((SELECT codice FROM pg_temp.esito(pg_temp.secondo_operatore((SELECT k FROM _tag) || '_b'))),
    'E_RISORSA_UMANA_GIA_PRESENTE',
    '7) risorsa umana SPENTA, flusso B sullo stesso soggetto: stesso rifiuto (lo slot e'' occupato)');

SELECT is((SELECT codice FROM pg_temp.esito(pg_temp.bb_diretto())), 'E_RISORSA_UMANA_GIA_PRESENTE',
    '8) risorsa umana SPENTA, building block diretto: stesso rifiuto');

SELECT * FROM finish();
ROLLBACK;
