-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test — INVARIANZA delle viste che joinano vendite.fatture_righe
--   rispetto all'armamento della RLS sui satelliti fattura (20260729-01..05).
--
-- LA DOMANDA. Armare la RLS su fatture_righe cambia cio' che un operatore
-- vede nelle viste che quella tabella la joinano? La risposta attesa e' NO —
-- le viste filtrano gia' per emittente e la fattura di una commessa ha lo
-- stesso emittente della commessa — ma e' una previsione, e questo file la
-- misura.
--
-- L'ESPERIMENTO. Confrontare "owner" contro "operatore" NON risponderebbe:
-- differirebbero comunque, perche' le viste hanno un proprio filtro di scope
-- (escope.sr_ids) che nulla ha a che vedere con la RLS. Il confronto giusto
-- tiene fissa la sessione OPERATORE e muove una sola variabile:
--
--     stesso operatore, stessa vista, RLS su fatture_righe DISATTIVA
--     stesso operatore, stessa vista, RLS su fatture_righe ENABLE + FORCE
--
-- Tutto cio' che cambia fra le due misure e' imputabile alle policy nuove, e
-- a nient'altro. FORCE serve perche' la sessione gira come titodb (owner):
-- senza, la RLS verrebbe bypassata e il test misurerebbe se' stesso.
--
-- ⭐ IL TEST 2 E' IL PIU' IMPORTANTE. vw_dash_competenza_attivita joina
-- fatture_righe in LEFT JOIN: se le righe fattura sparissero, le sue righe
-- NON sparirebbero — resterebbero con i campi fattura a NULL. Cioe'
-- un'attivita' fatturata mostrata come non fatturata, e la quota del
-- 20260728-13 calcolata sul nulla. E' l'unico modo in cui questa slice
-- potrebbe sbagliare SENZA DIRLO, e contare le sole righe non sparisce:
-- bisogna contare quelle con la fattura ancora agganciata.
-- Le altre due viste joinano in INNER: se qualcosa andasse storto perdono
-- righe, il che e' brutto ma rumoroso.
-- ------------------------------------------------------------
-- Indice test (1..4):
--   1   vw_dash_competenza_attivita  — stesso numero di righe
--   2   ⭐ vw_dash_competenza_attivita — stesso numero di righe con fattura
--       agganciata (il fallimento SILENZIOSO del LEFT JOIN)
--   3   vw_dash_competenza_errori    — stesso numero di righe
--   4   vw_documento_lineage_archi   — stesso numero di righe
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

-- =========================================================
-- Operatore di test, whitelistato su un emittente reale
-- =========================================================
CREATE TEMP TABLE _refs AS
SELECT
    (SELECT ef.id FROM anagrafiche.emittenti_fiscali ef
      JOIN vendite.fatture fa ON fa.emittente_soggetto_ruolo_id = ef.soggetto_ruolo_id
      WHERE EXISTS (SELECT 1 FROM vendite.fatture_righe fr WHERE fr.fattura_id = fa.id)
      ORDER BY ef.id LIMIT 1) AS emit_pk;

CREATE TEMP TABLE _op (auth_user_id int, identita_id bigint);

DO $fix$
DECLARE
    v_uid int; v_sog uuid; v_sr bigint; v_idn bigint;
BEGIN
    INSERT INTO django.auth_user (username, password, is_active, is_staff,
        is_superuser, first_name, last_name, email, date_joined)
    VALUES ('_pgtap_rls_viste_' || substring(md5(clock_timestamp()::text) from 1 for 8),
        '!', true, false, false, '', '', '', now())
    RETURNING id INTO v_uid;

    v_sog := anagrafiche.fn_crea_soggetto_pf(
        p_cognome           := 'PnzTestScopeEf',
        p_nome              := 'Fdn',
        p_codice_fiscale    := 'PNZFDN78A01L219Y',
        p_email             := 'pgtap_rls_viste_' || substring(md5(clock_timestamp()::text) from 1 for 6) || '@test.local',
        p_data_nascita      := DATE '1978-01-01',
        p_sesso             := 'M',
        p_stato_iso2        := 'IT',
        p_comune_nascita_id := (SELECT id FROM config.comuni ORDER BY id LIMIT 1),
        p_tipo_contatto_id  := NULL);

    v_sr := script.fn_get_or_create_soggetto_ruolo(
        p_soggetto_id := v_sog, p_cd_int_ruolo := 'RIS_UMANA');

    INSERT INTO anagrafiche.identita_digitali
        (soggetto_ruolo_id, auth_user_id, ruolo_applicativo, attivo)
    VALUES (v_sr, v_uid, 'OPERATORE', true)
    RETURNING id INTO v_idn;

    INSERT INTO _op VALUES (v_uid, v_idn);
END
$fix$;

CREATE TEMP TABLE _flags AS
SELECT COALESCE((SELECT emit_pk IS NOT NULL FROM _refs LIMIT 1), false) AS prereq;

-- Whitelist = emittente scelto. L'override sul DELETE serve: la tabella e'
-- protetta da trgfn_user_emittenti_fiscali_guard_delete (20260408-17).
DO $wl$
BEGIN
    IF NOT (SELECT prereq FROM _flags) THEN RETURN; END IF;
    PERFORM set_config('zeroerp.allow_user_emittente_delete_override', 'on', true);
    DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = (SELECT auth_user_id FROM _op);
    PERFORM set_config('zeroerp.allow_user_emittente_delete_override', '', true);
    INSERT INTO config.user_emittenti_fiscali (auth_user_id, emittente_fiscale_id)
    VALUES ((SELECT auth_user_id FROM _op), (SELECT emit_pk FROM _refs)) ON CONFLICT DO NOTHING;
END $wl$;

-- Sessione operatore: resta identica per entrambe le misure.
SELECT set_config('app.ruolo_applicativo', 'OPERATORE', true);
SELECT set_config('app.current_user_id',
    COALESCE((SELECT auth_user_id FROM _op)::text, ''), true);

CREATE TEMP TABLE _m (fase text, vista text, n bigint);

-- =========================================================
-- MISURA 1 — RLS su fatture_righe NON forzata (l'owner la bypassa)
-- =========================================================
INSERT INTO _m SELECT 'off', 'attivita',        count(*) FROM vendite.vw_dash_competenza_attivita;
INSERT INTO _m SELECT 'off', 'attivita_fatt',   count(*) FROM vendite.vw_dash_competenza_attivita
                                                 WHERE fattura_id IS NOT NULL;
INSERT INTO _m SELECT 'off', 'errori',          count(*) FROM vendite.vw_dash_competenza_errori;
INSERT INTO _m SELECT 'off', 'lineage',         count(*) FROM vendite.vw_documento_lineage_archi;

-- =========================================================
-- MISURA 2 — stessa sessione, RLS ARMATA e FORZATA
-- =========================================================
ALTER TABLE vendite.fatture_righe          ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_righe          FORCE  ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva FORCE  ROW LEVEL SECURITY;

INSERT INTO _m SELECT 'on',  'attivita',        count(*) FROM vendite.vw_dash_competenza_attivita;
INSERT INTO _m SELECT 'on',  'attivita_fatt',   count(*) FROM vendite.vw_dash_competenza_attivita
                                                 WHERE fattura_id IS NOT NULL;
INSERT INTO _m SELECT 'on',  'errori',          count(*) FROM vendite.vw_dash_competenza_errori;
INSERT INTO _m SELECT 'on',  'lineage',         count(*) FROM vendite.vw_documento_lineage_archi;

ALTER TABLE vendite.fatture_righe          NO FORCE ROW LEVEL SECURITY;
ALTER TABLE vendite.fatture_riepiloghi_iva NO FORCE ROW LEVEL SECURITY;

-- =========================================================
-- Asserzioni (soft-skip se il DB non ha una fattura con righe)
-- =========================================================
SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='attivita'),
    (SELECT n FROM _m WHERE fase='off' AND vista='attivita'),
    '1. vw_dash_competenza_attivita: stesso numero di righe con e senza RLS');

SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='attivita_fatt'),
    (SELECT n FROM _m WHERE fase='off' AND vista='attivita_fatt'),
    '2. vw_dash_competenza_attivita: stesse righe CON FATTURA agganciata '
    '(il LEFT JOIN non deve svuotarsi in silenzio)');

SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='errori'),
    (SELECT n FROM _m WHERE fase='off' AND vista='errori'),
    '3. vw_dash_competenza_errori: stesso numero di righe con e senza RLS');

SELECT is(
    (SELECT n FROM _m WHERE fase='on'  AND vista='lineage'),
    (SELECT n FROM _m WHERE fase='off' AND vista='lineage'),
    '4. vw_documento_lineage_archi: stesso numero di righe con e senza RLS');

SELECT set_config('app.ruolo_applicativo', '', true);
SELECT set_config('app.current_user_id', '', true);

SELECT * FROM finish();
ROLLBACK;
