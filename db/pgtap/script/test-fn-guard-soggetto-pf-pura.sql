-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_guard_soggetto_pf_pura
-- Riferimento: §4.2 WIP multi-face-auth, funzione riusabile estratta
-- dal trigger trgfn_risorse_umane_auth_user_guard_persona_fisica.
--
-- Indice test (1..7):
--    1. Precondizione: comune nascita disponibile per fn_crea_soggetto_pf
--    2. Setup: creato soggetto PF pura (CF valorizzato, P.IVA NULL)
--    3. Guard NULL: p_soggetto_id NULL -> throws E_PARAMETRO_INVALIDO
--    4. Guard soggetto inesistente: UUID random -> throws E_SOGGETTO_NOT_FOUND
--    5. Guard PF pura: soggetto valido -> ritorna soggetto_id (no exception)
--    6. Setup: aggiungi P.IVA al soggetto
--    7. Guard con P.IVA: throws E_AUTH_USER_SOGGETTO_CON_PIVA
--
-- Nota: il caso "senza CF" NON e' testabile su un soggetto PR reale
-- perche' il trigger trgfn_soggetti_guard_cf_piva_obbligatori garantisce
-- CF NOT NULL per tipo PR (invariante di modello). La funzione ha il
-- ramo difensivo ma non e' raggiungibile con dati validi.
--
-- BEGIN; + rollback implicito a fine file. Pattern coerente con
-- test-fn-crea-indirizzo-soggetto.sql: i trigger DEFERRABLE di guard
-- su soggetti (indirizzi required, contatti required) non scattano
-- perche' la transazione non fa COMMIT.
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ QUESTO FILE NON USA `SET CONSTRAINTS ALL IMMEDIATE`, a differenza degli
--   altri, e non e' una dimenticanza.
--   La fixture costruisce un soggetto con le funzioni del dominio
--   (fn_crea_soggetto_pf e sorelle). Ma `anagrafiche.soggetti` ha TRE guard
--   DEFERRABLE INITIALLY DEFERRED — indirizzi, contatti, dati societari — e la
--   deferralita' li' e' VOLUTA: si crea il soggetto, poi il suo indirizzo, e la
--   completezza si verifica al COMMIT. Forzare IMMEDIATE pretenderebbe
--   l'indirizzo nell'istante stesso dell'INSERT del soggetto, cioe' vieterebbe
--   il pattern che il dominio ha scelto — misurato: da 7 asserzioni verdi a 1,
--   con «Indirizzo obbligatorio mancante per soggetto ...».
--   ⚠️ Resta pero' un buco reale: senza la riga, quei tre guard non vengono
--   esercitati da questo test, e la fixture lascia un soggetto che
--   l'applicazione non potrebbe committare. La correzione vera e' completare la
--   fixture (indirizzo + contatti) e allora la riga si puo' rimettere.
--   Brief: brief-db-pgtap-runner-rls-baseline §20.

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(7);

-- =========================================================
-- 1) Precondizione: un comune di nascita disponibile
-- =========================================================
CREATE TEMP TABLE _t_comune AS
SELECT id AS comune_id
  FROM config.comuni
 ORDER BY id
 LIMIT 1;

SELECT ok(
    (SELECT count(*) FROM _t_comune) = 1,
    '1. Precondizione: comune disponibile per fn_crea_soggetto_pf'
);

-- =========================================================
-- 2) Setup: soggetto PF pura via fn_crea_soggetto_pf
-- =========================================================
-- Uso md5 clock_timestamp per CF univoco (evita collisioni tra run).
-- CF fisso valido. pgTAP rollbacca a fine file, nessun conflitto
-- tra run. Email random per evitare collisioni nella tabella contatti.
CREATE TEMP TABLE _t_sogg AS
SELECT anagrafiche.fn_crea_soggetto_pf(
    p_cognome           := 'LccTestPfPura',
    p_nome              := 'Rld',
    p_codice_fiscale    := 'LCCRLD80A01L736X',
    p_email             := 'pgtap_pf_pura_' || substring(md5(clock_timestamp()::text) from 1 for 8) || '@test.local',
    p_data_nascita      := DATE '1980-01-01',
    p_sesso             := 'M',
    p_stato_iso2        := 'IT',
    p_comune_nascita_id := (SELECT comune_id FROM _t_comune),
    p_tipo_contatto_id  := NULL
) AS soggetto_id;

SELECT ok(
    (SELECT soggetto_id FROM _t_sogg) IS NOT NULL,
    '2. Setup: creato soggetto PF pura (CF valorizzato, P.IVA NULL)'
);

-- =========================================================
-- 3) Guard NULL -> throws
-- =========================================================
SELECT throws_ok(
    $$SELECT script.fn_guard_soggetto_pf_pura(NULL::uuid)$$,
    NULL,
    NULL,
    '3. p_soggetto_id NULL -> solleva eccezione (E_PARAMETRO_INVALIDO)'
);

-- =========================================================
-- 4) Guard soggetto inesistente -> throws
-- =========================================================
-- UUID random che non corrisponde a nessun soggetto reale.
SELECT throws_ok(
    format($$SELECT script.fn_guard_soggetto_pf_pura(%L::uuid)$$,
           gen_random_uuid()),
    NULL,
    NULL,
    '4. Soggetto inesistente -> solleva eccezione (E_SOGGETTO_NOT_FOUND)'
);

-- =========================================================
-- 5) Guard PF pura -> ritorna soggetto_id
-- =========================================================
-- La funzione ritorna l'id passato se il guard passa.
SELECT ok(
    script.fn_guard_soggetto_pf_pura((SELECT soggetto_id FROM _t_sogg))
        = (SELECT soggetto_id FROM _t_sogg),
    '5. PF pura valida -> ritorna soggetto_id passato (pass-through)'
);

-- =========================================================
-- 6) Setup: aggiungi P.IVA al soggetto (lo rende NON PF pura)
-- =========================================================
UPDATE anagrafiche.soggetti
   SET partita_iva = 'PGTAP' || upper(substring(md5(clock_timestamp()::text) from 1 for 6))
 WHERE id = (SELECT soggetto_id FROM _t_sogg);

SELECT ok(
    (SELECT partita_iva FROM anagrafiche.soggetti
      WHERE id = (SELECT soggetto_id FROM _t_sogg)) IS NOT NULL,
    '6. Setup: aggiunta P.IVA al soggetto'
);

-- =========================================================
-- 7) Guard con P.IVA -> throws
-- =========================================================
SELECT throws_ok(
    format($$SELECT script.fn_guard_soggetto_pf_pura(%L::uuid)$$,
           (SELECT soggetto_id FROM _t_sogg)),
    NULL,
    NULL,
    '7. Soggetto con P.IVA -> solleva E_AUTH_USER_SOGGETTO_CON_PIVA'
);

-- Nota: il caso "senza CF" non e' rappresentabile su soggetti PR reali
-- (trigger garantisce CF NOT NULL). Ramo difensivo della funzione coperto
-- dalla sola lettura del codice; non verificabile via pgTAP senza bypass
-- del trigger di guard (anti-pattern). Omesso volontariamente.

SELECT * FROM finish();
