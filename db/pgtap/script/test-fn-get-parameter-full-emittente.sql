-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: script.fn_get_parameter_full (firma con emittente_fiscale_id)
--
-- Elenco test:
--  1) Funzione presente con la firma VIVA a 7 argomenti
--  2) Vecchia firma (integer) non esiste piu'
--  3) Riferimenti minimi: tabelle parameters e parameter_overrides
--  4) Setup parametro test e emittente fiscale di riferimento
--  5) Risoluzione default senza override
--  6) Override emittente restituito
--  7) Priorita': user > emittente
--  8) Priorita': group > emittente
--  9) GUARDRAIL: nessun overload a 6 argomenti (ambiguita' di risoluzione)
-- ------------------------------------------------------------
-- rev 2026-07-27: il caso 1 asseriva la firma a 6 argomenti (bigint), che era
--   "la nuova" quando il test fu scritto (20260403-15). Dal 20260515-08 e'
--   arrivata la firma a 7 argomenti (p_categoria_cliente_id) SENZA rimuovere
--   la precedente: avendo entrambe i DEFAULT su tutti i parametri tranne il
--   primo, OGNI chiamata con meno di 7 argomenti diventava ambigua — cast
--   compreso. Due chiamanti erano rotti a runtime
--   (ai_assistant/tool_registry.py con 1 arg, script.fn_get_default_by_param
--   con 6). La firma a 6 argomenti e' stata droppata (20260727-25) e il caso 1
--   ora punta a quella viva. Il caso 9 e' il presidio perche' non ricapiti.
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

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(9);

-- ============================================================
-- 1) Funzione presente con la firma VIVA (7 argomenti, dal 20260515-08)
-- ============================================================
SELECT has_function(
    'script', 'fn_get_parameter_full',
    ARRAY['text', 'bigint', 'integer', 'integer[]', 'text', 'text', 'smallint'],
    '1) fn_get_parameter_full presente con firma a 7 argomenti (categoria_cliente)'
);

-- ============================================================
-- 2) Vecchia firma (integer come secondo parametro) non esiste piu'
-- ============================================================
SELECT hasnt_function(
    'script', 'fn_get_parameter_full',
    ARRAY['text', 'integer', 'integer', 'integer[]', 'text', 'text'],
    '2) vecchia firma (text, integer, ...) rimossa'
);

-- ============================================================
-- 3) Riferimenti minimi
-- ============================================================
SELECT ok(
    EXISTS(SELECT 1 FROM config.parameters LIMIT 1)
    AND EXISTS(
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'config' AND table_name = 'parameter_overrides'
    ),
    '3) tabelle parameters e parameter_overrides esistono'
);

-- ============================================================
-- 0. Setup dati test
-- ============================================================

-- Parametro di test
-- 2026-10-25 (brief-db-parametri-senza-override): config.parameters.ammette_override
-- e' NOT NULL senza DEFAULT, un parametro dichiara la sua famiglia.
INSERT INTO config.parameters (id, code, default_value, description, ammette_override, tipo_valore)
VALUES (99990, '_TEST_PARAM_EMIT_', 'DEFAULT_VAL', 'Parametro test emittente', true, 'TESTO')
ON CONFLICT (id) DO NOTHING;

-- Garantisce che esista almeno un gruppo di test (ROLLBACK ripristina)
INSERT INTO django.auth_group (name)
SELECT '_test_group_param_'
WHERE NOT EXISTS (SELECT 1 FROM django.auth_group LIMIT 1);

-- Riferimenti reali: emittente, auth_user, auth_group
CREATE TEMP TABLE tmp_refs_param AS
SELECT
    ef.id  AS emittente_id,
    au.id  AS user_id,
    ag.id  AS group_id
FROM anagrafiche.emittenti_fiscali ef
CROSS JOIN (SELECT id FROM django.auth_user ORDER BY id LIMIT 1) au
CROSS JOIN (SELECT id FROM django.auth_group ORDER BY id LIMIT 1) ag
WHERE ef.attivo = true
ORDER BY ef.id
LIMIT 1;

-- ============================================================
-- 4) Setup OK
-- ============================================================
SELECT ok(
    (SELECT emittente_id FROM tmp_refs_param) IS NOT NULL
    AND (SELECT user_id FROM tmp_refs_param) IS NOT NULL
    AND (SELECT group_id FROM tmp_refs_param) IS NOT NULL,
    '4) setup: emittente, user e group di riferimento trovati'
);

-- ============================================================
-- 5) Risoluzione default senza override
-- ============================================================
SELECT is(
    script.fn_get_parameter_full('_TEST_PARAM_EMIT_'),
    'DEFAULT_VAL',
    '5) senza override restituisce default_value'
);

-- ============================================================
-- 6) Override emittente restituito
-- ============================================================
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, emittente_fiscale_id)
VALUES (99990, 99990, 'EMIT_VAL', (SELECT emittente_id FROM tmp_refs_param));

SELECT is(
    script.fn_get_parameter_full(
        '_TEST_PARAM_EMIT_',
        p_emittente_fiscale_id := (SELECT emittente_id FROM tmp_refs_param)
    ),
    'EMIT_VAL',
    '6) override emittente restituito correttamente'
);

-- ============================================================
-- 7) Priorita': user > emittente
-- ============================================================
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, django_user_id)
VALUES (99991, 99990, 'USER_VAL', (SELECT user_id FROM tmp_refs_param));

SELECT is(
    script.fn_get_parameter_full(
        '_TEST_PARAM_EMIT_',
        p_emittente_fiscale_id := (SELECT emittente_id FROM tmp_refs_param),
        p_django_user_id := (SELECT user_id FROM tmp_refs_param)
    ),
    'USER_VAL',
    '7) priorita: user override vince su emittente'
);

-- ============================================================
-- 8) Priorita': group > emittente
-- ============================================================
INSERT INTO config.parameter_overrides (id, parameter_id, overridden_value, django_group_id)
VALUES (99992, 99990, 'GROUP_VAL', (SELECT group_id FROM tmp_refs_param));

SELECT is(
    script.fn_get_parameter_full(
        '_TEST_PARAM_EMIT_',
        p_emittente_fiscale_id := (SELECT emittente_id FROM tmp_refs_param),
        p_group_ids := ARRAY[(SELECT group_id FROM tmp_refs_param)]
    ),
    'GROUP_VAL',
    '8) priorita: group override vince su emittente'
);

-- ============================================================
-- ============================================================
-- 9) GUARDRAIL — deve esistere UNA SOLA firma.
--   Non e' una ripetizione del caso 1: quello verifica che la funzione ci sia,
--   questo che non ce ne sia una SECONDA. Due overload con default su tutti i
--   parametri tranne il primo non sono distinguibili da PostgreSQL per nessuna
--   arieta' inferiore alla massima: il risultato e' "la funzione non e' unica"
--   su ogni chiamata breve, cioe' percorsi applicativi rotti in silenzio
--   finche' qualcuno non li esegue.
--   Se domani serve un altro livello di cascata: NON creare un overload
--   "backward compatible" (fu l'intenzione del 20260515-08, e non funziono'),
--   ma estendere questa firma con un parametro opzionale in coda.
-- ============================================================
SELECT is(
    (SELECT count(*)::int
       FROM pg_proc p
       JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'script'
        AND p.proname = 'fn_get_parameter_full'),
    1,
    '9) guardrail: una sola firma di fn_get_parameter_full (nessun overload ambiguo)'
);

SELECT * FROM finish();
ROLLBACK;
