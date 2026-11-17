-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: il numero di una versione di template lo assegna il database, per
--   ogni strada (versione scritta da zero e copia), in fila per modello; dopo
--   la nascita non cambia; il codice della gara sul numero e' ritirato.
-- Oggetti:
--   documenti.trgfn_template_documenti_versioni_assegna_numero
--   trg_template_documenti_versioni_a04_assegna_numero_ins
--   documenti.fn_crea_bozza_da_versione
--   il lucchetto di colonna di versione (dbops.automation_lock_columns)
--
-- Elenco test (plan 13):
--   La forma
--   1) il trigger e' montato una volta, BEFORE INSERT per riga
--   2) ... e scatta prima dei rifiuti a05 della tabella, che citano il numero
--   3) il corpo prende il lock di transazione sul modello prima del massimo
--   La versione scritta da zero
--   4) senza numero, in un modello vuoto: 1
--   5) ... la successiva: 2
--   6) un numero scelto dall'applicazione si sostituisce: 3, non 99
--   7) un INSERT di due righe le numera in fila: 4 e 5
--   8) la nascita tiene il lock del modello fino alla fine della transazione
--   La copia
--   9) nello stesso modello: il successivo all'ultimo, 6
--  10) in un altro modello dello stesso documento, vuoto: 1
--   Dopo la nascita
--  11) il numero di una bozza non cambia: E_CODICE_NON_MODIFICABILE
--   Il codice della gara
--  12) E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE e' ritirato nel catalogo
--  13) ... e nessuna funzione e nessun trigger lo nomina
--
-- ⭐ Senza i changeSet 20261116-23 e -24 (prova sullo scratch, 2026-11-17) sono
--   rossi 1-10 e 12-13: senza trigger un numero assente viola il NOT NULL e un
--   numero scelto resta; la copia legge il massimo da se' e nomina il codice.
--   L'11 lo fa verde il lucchetto che ci_apply genera dalla riga di
--   dbops.automation_lock_columns: prima dell'apply e' rosso anche col giro.
-- ⚠️ Che due nascite contemporanee si mettano in fila non si prova in una
--   sessione sola (guida pgTAP, «Ciò che una sessione sola non prova»): l'8
--   asserisce che il lock c'e', con la chiave del modello, fino alla fine
--   della transazione; il 3 che il corpo lo prende prima di leggere.
-- ⚠️ Gira come applicazione. Il proprietario della tabella che scrive un
--   numero lo tiene: e' la strada dei seed degli standard (80_data), che
--   girano da proprietario; i pgTAP che costruiscono standard da owner
--   (test-documenti-template-standard-v1, -personalizza-v1) la attraversano.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(13);

-- ============================================================
-- Fixture: due modelli dello stesso documento (preventivo), dell'emittente
-- di chi agisce, senza versioni.
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT script.fn_pgtap_emittente_operatore()                                                   AS emittente,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                AS sorg,
       (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO') AS tipo,
       (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT') AS render;

CREATE TEMP TABLE _m ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo)
    SELECT k.tipo, 'PGTAP-NV-' || x.k, 'PGTAP_NV_' || x.k, 'Template pgTAP numero versione ' || x.k,
           k.sorg, 'pgtap.builder', k.emittente, false, true
      FROM _k k, (VALUES ('A'), ('B')) x(k)
    RETURNING id, codice_interno
)
SELECT id, right(codice_interno, 1) AS k FROM ins;

-- Una versione in bozza del modello indicato, col numero indicato (NULL: nessuno).
-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
CREATE FUNCTION pg_temp.nuova_versione(p_k text, p_versione integer)
RETURNS integer LANGUAGE plpgsql AS $f$
DECLARE
    v_numero documenti.template_documenti_versioni.versione%TYPE;
BEGIN
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template,
        render_engine_id, versione_contesto)
    VALUES ((SELECT id FROM _m WHERE k = p_k), p_versione, 'BOZZA', 'Versione pgTAP',
            '<p>numero</p>', (SELECT render FROM _k), 1)
    RETURNING versione INTO v_numero;
    RETURN v_numero;
END;
$f$;

-- ============================================================
-- 1-3) La forma
-- ============================================================
SELECT is(
    (SELECT string_agg(split_part(pg_get_triggerdef(t.oid), ' ON ', 1), ' | ')
       FROM pg_trigger t
      WHERE t.tgrelid = 'documenti.template_documenti_versioni'::regclass
        AND t.tgfoid = 'documenti.trgfn_template_documenti_versioni_assegna_numero'::regproc),
    'CREATE TRIGGER trg_template_documenti_versioni_a04_assegna_numero_ins BEFORE INSERT',
    '1) il trigger del numero e'' montato una volta, BEFORE INSERT');

-- Fra i BEFORE della stessa riga l'ordine e' alfabetico (linee guida trigger,
-- «La fase»): chi cita il numero gira dopo chi lo assegna.
SELECT is(
    (SELECT array_agg(t.tgname::text ORDER BY t.tgname)
       FROM pg_trigger t
      WHERE t.tgrelid = 'documenti.template_documenti_versioni'::regclass
        AND t.tgfoid IN ('documenti.trgfn_template_documenti_versioni_protect_pubblicata'::regproc,
                         'documenti.trgfn_template_standard_guard_sola_lettura'::regproc)
        AND t.tgname COLLATE "C" <
            (SELECT a.tgname COLLATE "C" FROM pg_trigger a
              WHERE a.tgrelid = 'documenti.template_documenti_versioni'::regclass
                AND a.tgfoid = 'documenti.trgfn_template_documenti_versioni_assegna_numero'::regproc)),
    NULL::text[],
    '2) i rifiuti a05 della tabella girano dopo il trigger del numero');

-- Il lock sta nella struttura: in una sessione sola e' rientrante (guida pgTAP).
-- La chiave e' il modello, e il lock viene prima della lettura del massimo.
SELECT ok(
    (SELECT position('pg_advisory_xact_lock(' IN p.prosrc) > 0
        AND p.prosrc LIKE '%hashtext(''documenti.template_documenti_versioni.versione'')%'
        AND p.prosrc LIKE '%hashtext(NEW.template_documento_id::text)%'
        AND position('pg_advisory_xact_lock(' IN p.prosrc) < position('max(v.versione)' IN p.prosrc)
       FROM pg_proc p
      WHERE p.oid = 'documenti.trgfn_template_documenti_versioni_assegna_numero'::regproc),
    '3) il corpo prende il lock del modello prima di leggere il massimo');

-- ============================================================
-- 4-8) La versione scritta da zero
-- ============================================================
SELECT is(pg_temp.nuova_versione('A', NULL), 1,
    '4) senza numero, in un modello vuoto: 1');

SELECT is(pg_temp.nuova_versione('A', NULL), 2,
    '5) la successiva: 2');

SELECT is(pg_temp.nuova_versione('A', 99), 3,
    '6) un numero scelto dall''applicazione si sostituisce: 3, non 99');

-- La lettura del trigger vede le righe gia' inserite dalla stessa istruzione.
CREATE TEMP TABLE _due ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, stato, titolo, html_template, render_engine_id, versione_contesto)
    SELECT (SELECT id FROM _m WHERE k = 'A'), 'BOZZA', 'Versione pgTAP ' || n, '<p>numero</p>',
           (SELECT render FROM _k), 1
      FROM generate_series(1, 2) n
    RETURNING versione
)
SELECT versione FROM ins;

SELECT is(
    (SELECT array_agg(versione ORDER BY versione) FROM _due),
    ARRAY[4, 5],
    '7) un INSERT di due righe le numera in fila: 4 e 5');

-- ⚠️ hashtext e' un intero con segno, pg_locks lo stampa senza: modulo 2^32.
SELECT is(
    (SELECT count(*)::int FROM pg_locks l
      WHERE l.locktype = 'advisory'
        AND l.pid = pg_backend_pid()
        AND l.granted
        AND l.objsubid = 2
        AND l.classid::bigint = (hashtext('documenti.template_documenti_versioni.versione')::bigint & 4294967295)
        AND l.objid::bigint   = (hashtext((SELECT id FROM _m WHERE k = 'A')::text)::bigint & 4294967295)),
    1,
    '8) la nascita tiene il lock del modello fino alla fine della transazione');

-- ============================================================
-- 9-10) La copia
-- ============================================================
-- Chiamare prima, asserire dopo: la copia si chiama una volta sola.
CREATE TEMP TABLE _copie ON COMMIT DROP AS
SELECT x.k,
       documenti.fn_crea_bozza_da_versione(
           (SELECT v.id FROM documenti.template_documenti_versioni v
             WHERE v.template_documento_id = (SELECT id FROM _m WHERE k = 'A')
               AND v.versione = 1),
           (SELECT id FROM _m WHERE k = x.k)) AS id
  FROM (VALUES (1, 'A'), (2, 'B')) x(n, k)
 ORDER BY x.n;

SELECT is(
    (SELECT v.versione FROM documenti.template_documenti_versioni v
      WHERE v.id = (SELECT id FROM _copie WHERE k = 'A')),
    6,
    '9) la copia nello stesso modello: il successivo all''ultimo, 6');

SELECT is(
    (SELECT v.versione FROM documenti.template_documenti_versioni v
      WHERE v.id = (SELECT id FROM _copie WHERE k = 'B')),
    1,
    '10) la copia in un altro modello dello stesso documento, vuoto: 1');

-- ============================================================
-- 11) Dopo la nascita il numero non cambia
-- ============================================================
SELECT is(
    dbops.fn_pgtap_codice_errore(format(
        'UPDATE documenti.template_documenti_versioni SET versione = 50 WHERE template_documento_id = %s AND versione = 2',
        (SELECT id FROM _m WHERE k = 'A'))),
    'E_CODICE_NON_MODIFICABILE',
    '11) il numero di una bozza non cambia: E_CODICE_NON_MODIFICABILE');

-- ============================================================
-- 12-13) Il codice della gara e' ritirato
-- ============================================================
SELECT ok(
    (SELECT c.obsoleto_dal IS NOT NULL FROM config.codici_errore c
      WHERE c.codice = 'E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE'),
    '12) E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE e'' ritirato nel catalogo');

-- Le due superfici dove sta un codice (linee guida SQL §5c): il testo delle
-- funzioni e gli argomenti dei trigger, per uguaglianza.
SELECT is(
    (SELECT array_agg(x ORDER BY x) FROM (
        SELECT p.oid::regprocedure::text AS x
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
           AND p.prokind IN ('f', 'p')
           AND pg_get_functiondef(p.oid) LIKE '%E\_DOCUMENTI\_VERSIONE\_NUMERO\_CONCORRENTE%'
        UNION ALL
        SELECT t.tgname::text
          FROM pg_trigger t
         WHERE NOT t.tgisinternal
           AND 'E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE' = ANY (dbops.fn_trigger_argomenti(t.tgargs))
    ) s),
    NULL::text[],
    '13) nessuna funzione e nessun trigger nomina il codice ritirato');

SELECT * FROM finish();
ROLLBACK;
