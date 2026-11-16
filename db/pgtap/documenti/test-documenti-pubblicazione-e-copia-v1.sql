-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: lo stato di una versione di template ha un verbo solo, la
--   pubblicazione; una bozza spenta non si pubblica; la copia di una versione
--   va in un modello dello stesso documento.
-- Oggetti:
--   documenti.trgfn_template_documenti_versioni_protect_pubblicata
--   documenti.fn_pubblica_template_documento_versione
--   documenti.fn_crea_bozza_da_versione
--   chk_template_documenti_versioni_valido_dal_fuori_bozza
--
-- Elenco test (plan 27):
--   La forma
--   1) valido_dal e' obbligatorio per ogni stato fuori bozza (la definizione)
--   2) il CHECK della sola PUBBLICATA non c'e' piu'
--   3) il guard dello stato e' montato una volta, su INSERT e UPDATE
--   4) ... e scatta prima del guard comune delle date
--   Uno stato fuori bozza si scrive solo dalla pubblicazione
--   5) una versione non nasce PUBBLICATA
--   6) ... ne' OBSOLETA
--   7) una bozza non diventa PUBBLICATA con un UPDATE
--   8) ... ne' OBSOLETA
--   9) a porta aperta, la pubblicazione con l'HTML cambiato e' rifiutata
--  10) a porta aperta, una bozza non diventa OBSOLETA
--  11) sulle date di una PUBBLICATA parla l'immutabilita', non il guard delle date
--  12) una bozza si modifica come prima
--   La bozza spenta
--  13) una bozza spenta non si pubblica, con la frase
--  14) ... e il rifiuto non tocca niente: la pubblicata resta aperta
--   La pubblicazione, i rifiuti
--  15) versione NULL -> E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO
--  16) valido_dal NULL -> E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO
--  17) versione inesistente -> E_DOCUMENTI_VERSIONE_NOT_FOUND
--  18) una PUBBLICATA non si ripubblica -> E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO
--  19) lo stesso inizio di una pubblicata: la chiusura non lo risolve -> 23P01
--   La copia
--  20) in un modello di un altro tipo -> E_DOCUMENTI_COPIA_DOCUMENTO_DIVERSO
--  21) in un modello di un'altra sorgente -> E_DOCUMENTI_COPIA_DOCUMENTO_DIVERSO
--  22) in un modello che non esiste -> E_PARAMETRO_INVALIDO
--  23) origine NULL -> E_PARAMETRO_INVALIDO
--  24) destinazione NULL -> E_PARAMETRO_INVALIDO
--  25) origine che non esiste -> E_PARAMETRO_INVALIDO
--  26) nello stesso modello: una BOZZA col numero successivo
--  27) il vincolo che il verbo traduce in E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE
--      esiste col nome che il verbo cerca
--
-- ⭐ Senza i changeSet 20261116-01 … -04 (prova sullo scratch, 2026-11-16) sono
--   verdi 8 su 27. Rossi: 1-2 (il CHECK della sola PUBBLICATA); 3-11 (il guard
--   guardava solo OLD.stato, in a10 sul solo UPDATE; 9 e 10 anche per la porta
--   col nome del verbo); 13-14 (la bozza spenta si pubblicava e chiudeva la V1);
--   20-22 e 27 (la copia passava, il modello inesistente era un 23503). 12 e 19
--   a cascata: senza il guard il 7 pubblica la V2 con un UPDATE, e la V2 non e'
--   piu' una bozza.
-- ⚠️ La gara vera sul numero (27) non si costruisce in una sessione sola: due
--   copie concorrenti vogliono due transazioni. Si fissa il patto fra il verbo e
--   il vincolo che riconosce per nome: un vincolo rinominato rende rosso il test
--   prima che il verbo torni a dare il 23505 grezzo.
-- ⚠️ Gira come applicazione. Il proprietario della tabella scrive lo stato senza
--   porta: lo provano i pgTAP che girano da owner e costruiscono standard
--   pubblicati e obsoleti (test-documenti-template-standard-v1,
--   -personalizza-v1, -template-porta-unica-v1).
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(27);

-- ============================================================
-- Fixture: tre modelli dell'emittente di chi agisce. A e' il documento di
-- riferimento; B ha la sorgente di A e un altro tipo; C il tipo di A e
-- un'altra sorgente.
-- ============================================================
CREATE TEMP TABLE _k ON COMMIT DROP AS
SELECT script.fn_pgtap_emittente_operatore()                                                   AS emittente,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')                AS sorg,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'CONTRATTO')                 AS sorg2,
       (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'PREVENTIVO') AS tipo,
       (SELECT t.id FROM documenti.tipi_documento_output t WHERE t.codice_interno = 'CONTRATTO')  AS tipo2,
       (SELECT r.id FROM documenti.render_engine_documento r WHERE r.codice_interno = 'WEASYPRINT') AS render;

CREATE TEMP TABLE _m ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, emittente_fiscale_id,
        is_default, attivo)
    SELECT x.tipo, 'PGTAP-PC-' || x.k, 'PGTAP_PC_' || x.k, 'Template pgTAP pubblicazione ' || x.k,
           x.sorg, 'pgtap.builder', k.emittente, false, true
      FROM _k k,
           LATERAL (VALUES ('A', k.tipo,  k.sorg),
                           ('B', k.tipo2, k.sorg),
                           ('C', k.tipo,  k.sorg2)) x(k, tipo, sorg)
    RETURNING id, codice_interno
)
SELECT id, right(codice_interno, 1) AS k FROM ins;

-- ⚠️ In un'istruzione separata dal padre (guida pgTAP, «Padre e figlio»).
-- V1 e V2 accese, V3 spenta: tutte nate in bozza.
CREATE TEMP TABLE _v ON COMMIT DROP AS
WITH ins AS (
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template, render_engine_id,
        versione_contesto, attivo)
    SELECT (SELECT id FROM _m WHERE k = 'A'), n, 'BOZZA', 'Versione ' || n, '<p>v' || n || '</p>',
           (SELECT render FROM _k), 1, n <> 3
      FROM generate_series(1, 3) n
    RETURNING id, versione
)
SELECT id, versione FROM ins;

-- La V1, dal verbo: aperta dal 2026-01-01.
SELECT documenti.fn_pubblica_template_documento_versione(
    (SELECT id FROM _v WHERE versione = 1), DATE '2026-01-01', 1, NULL);

-- L'INSERT di una versione del modello A nello stato chiesto.
CREATE FUNCTION pg_temp.insert_versione(p_stato text)
RETURNS text LANGUAGE sql AS $f$
  SELECT format($i$
    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo, html_template, render_engine_id,
        valido_dal, valido_al, versione_contesto)
    VALUES (%s, 9, %L, 'Versione nata fuori bozza', '<p>v9</p>', %s,
            DATE '2027-01-01', DATE '2027-06-30', 1)$i$,
    (SELECT id FROM _m WHERE k = 'A'), p_stato, (SELECT render FROM _k));
$f$;

-- ============================================================
-- 1-4) La forma
-- ============================================================
SELECT is(
    (SELECT pg_get_constraintdef(c.oid) FROM pg_constraint c
      WHERE c.conrelid = 'documenti.template_documenti_versioni'::regclass
        AND c.conname = 'chk_template_documenti_versioni_valido_dal_fuori_bozza'),
    'CHECK ((((stato)::text = ''BOZZA''::text) OR (valido_dal IS NOT NULL)))',
    '1) valido_dal e'' obbligatorio per ogni stato fuori bozza');

SELECT is(
    (SELECT count(*)::int FROM pg_constraint c
      WHERE c.conrelid = 'documenti.template_documenti_versioni'::regclass
        AND c.conname = 'chk_template_documenti_versioni_valido_dal_pubblicata'),
    0,
    '2) il CHECK della sola PUBBLICATA non c''e'' piu''');

SELECT is(
    (SELECT string_agg(split_part(pg_get_triggerdef(t.oid), ' ON ', 1), ' | ')
       FROM pg_trigger t
      WHERE t.tgrelid = 'documenti.template_documenti_versioni'::regclass
        AND t.tgfoid = 'documenti.trgfn_template_documenti_versioni_protect_pubblicata'::regproc),
    'CREATE TRIGGER trg_template_documenti_versioni_a05_protect_pubblicata_ins_upd BEFORE INSERT OR UPDATE OF html_template, css_template, markdown_template, render_engine_id, formato_template, page_format, page_orientation, margin_top_mm, margin_right_mm, margin_bottom_mm, margin_left_mm, valido_dal, valido_al, context_schema, versione_contesto, template_documento_id, versione, stato',
    '3) il guard dello stato e'' montato una volta, su INSERT e UPDATE, con lo stato nell''elenco');

-- Fra i BEFORE della stessa riga l'ordine e' alfabetico: l'immutabilita' prima
-- del guard comune delle date (linee guida trigger, «La fase»).
SELECT ok(
    (SELECT t.tgname COLLATE "C" FROM pg_trigger t
      WHERE t.tgrelid = 'documenti.template_documenti_versioni'::regclass
        AND t.tgfoid = 'documenti.trgfn_template_documenti_versioni_protect_pubblicata'::regproc)
    <
    (SELECT t.tgname COLLATE "C" FROM pg_trigger t
      WHERE t.tgrelid = 'documenti.template_documenti_versioni'::regclass
        AND t.tgfoid = 'script.trgfn_guard_date_validita'::regproc),
    '4) il guard dello stato scatta prima del guard comune delle date');

-- ============================================================
-- 5-12) Uno stato fuori bozza si scrive solo dalla pubblicazione
-- ============================================================
SELECT throws_like(
    pg_temp.insert_versione('PUBBLICATA'),
    '%nasce in bozza e ne esce solo con la pubblicazione%',
    '5) una versione non nasce PUBBLICATA: E_DOCUMENTI_VERSIONE_STATO_FUORI_VERBO');

SELECT throws_like(
    pg_temp.insert_versione('OBSOLETA'),
    '%nasce in bozza e ne esce solo con la pubblicazione%',
    '6) una versione non nasce OBSOLETA');

SELECT throws_like(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET stato = 'PUBBLICATA', valido_dal = DATE '2026-09-01' WHERE id = %s$q$,
           (SELECT id FROM _v WHERE versione = 2)),
    '%La versione 2 non cambia stato%',
    '7) una bozza non diventa PUBBLICATA con un UPDATE: salterebbe la forma dei dati e la chiusura');

SELECT throws_like(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET stato = 'OBSOLETA', valido_dal = DATE '2025-01-01', valido_al = DATE '2025-06-30'
               WHERE id = %s$q$,
           (SELECT id FROM _v WHERE versione = 2)),
    '%nasce in bozza e ne esce solo con la pubblicazione%',
    '8) una bozza non diventa OBSOLETA con un UPDATE');

-- A porta aperta passa solo la forma della pubblicazione: le sole date.
SELECT throws_like(
    format($q$WITH porta AS (
                  SELECT set_config('zeroerp.allow_template_versione_pubblicazione_override', 'on', true))
              UPDATE documenti.template_documenti_versioni
                 SET stato = 'PUBBLICATA', valido_dal = DATE '2026-09-01',
                     html_template = '<p>di contrabbando</p>'
               WHERE id = %s AND EXISTS (SELECT 1 FROM porta)$q$,
           (SELECT id FROM _v WHERE versione = 2)),
    '%nasce in bozza e ne esce solo con la pubblicazione%',
    '9) a porta aperta, la pubblicazione con l''HTML cambiato e'' rifiutata');

SELECT throws_like(
    format($q$WITH porta AS (
                  SELECT set_config('zeroerp.allow_template_versione_pubblicazione_override', 'on', true))
              UPDATE documenti.template_documenti_versioni
                 SET stato = 'OBSOLETA', valido_dal = DATE '2025-01-01', valido_al = DATE '2025-06-30'
               WHERE id = %s AND EXISTS (SELECT 1 FROM porta)$q$,
           (SELECT id FROM _v WHERE versione = 2)),
    '%nasce in bozza e ne esce solo con la pubblicazione%',
    '10) a porta aperta, una bozza non diventa OBSOLETA');

-- ⭐ Prima del -02 qui parlava il guard comune delle date (a10_date_validita
--    veniva prima di a10_protect_pubblicata): mandava a correggere una data che
--    non si puo' cambiare.
SELECT throws_like(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET valido_al = DATE '2025-12-01' WHERE id = %s$q$,
           (SELECT id FROM _v WHERE versione = 1)),
    '%Una versione pubblicata di un template documentale non puo%',
    '11) sulle date di una PUBBLICATA parla l''immutabilita'', non il guard delle date');

SELECT lives_ok(
    format($q$UPDATE documenti.template_documenti_versioni
                 SET html_template = '<p>v2 ritoccata</p>', valido_dal = DATE '2026-05-01'
               WHERE id = %s$q$,
           (SELECT id FROM _v WHERE versione = 2)),
    '12) una bozza si modifica come prima, date comprese');

-- ============================================================
-- 13-14) La bozza spenta non si pubblica
-- ============================================================
SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-06-01', 1, NULL)$q$,
           (SELECT id FROM _v WHERE versione = 3)),
    '%La versione 3 del template «Template pgTAP pubblicazione A» non si pubblica%spenta%',
    '13) una bozza spenta non si pubblica: E_DOCUMENTI_VERSIONE_PUBBLICA_SPENTA, con numero e template');

SELECT is(
    (SELECT string_agg(t.versione || '=' || t.stato || '[' || coalesce(t.valido_al::text, 'aperta') || ']',
                       ', ' ORDER BY t.versione)
       FROM documenti.template_documenti_versioni t
      WHERE t.id IN (SELECT id FROM _v WHERE versione IN (1, 3))),
    '1=PUBBLICATA[aperta], 3=BOZZA[aperta]',
    '14) il rifiuto non tocca niente: la V1 resta pubblicata e aperta, la V3 resta bozza');

-- ============================================================
-- 15-19) La pubblicazione, i rifiuti
-- ============================================================
SELECT throws_like(
    $q$SELECT documenti.fn_pubblica_template_documento_versione(NULL, DATE '2026-06-01', 1, NULL)$q$,
    '%versione_id deve essere un intero positivo%',
    '15) versione NULL: E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO');

SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, NULL, 1, NULL)$q$,
           (SELECT id FROM _v WHERE versione = 2)),
    '%valido_dal e'' obbligatorio%',
    '16) valido_dal NULL: E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO');

SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-06-01', 1, NULL)$q$,
           (SELECT max(id) + 1000000 FROM documenti.template_documenti_versioni)),
    '%La versione template documento con id % non esiste%',
    '17) versione inesistente: E_DOCUMENTI_VERSIONE_NOT_FOUND');

SELECT throws_like(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-06-01', 1, NULL)$q$,
           (SELECT id FROM _v WHERE versione = 1)),
    '%atteso BOZZA%',
    '18) una PUBBLICATA non si ripubblica: E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO');

-- La chiusura prende solo le pubblicate che iniziano PRIMA: lo stesso inizio
-- resta una sovrapposizione, e la ferma il vincolo.
SELECT throws_ok(
    format($q$SELECT documenti.fn_pubblica_template_documento_versione(%s, DATE '2026-01-01', 1, NULL)$q$,
           (SELECT id FROM _v WHERE versione = 2)),
    '23P01',
    NULL,
    '19) lo stesso inizio della V1 pubblicata: la chiusura non lo risolve, il vincolo si');

-- ============================================================
-- 20-27) La copia
-- ============================================================
SELECT throws_like(
    format($q$SELECT documenti.fn_crea_bozza_da_versione(%s, %s)$q$,
           (SELECT id FROM _v WHERE versione = 1), (SELECT id FROM _m WHERE k = 'B')),
    '%La versione 1 non si copia in questo template%documento diverso%',
    '20) in un modello di un altro tipo: E_DOCUMENTI_COPIA_DOCUMENTO_DIVERSO');

SELECT throws_like(
    format($q$SELECT documenti.fn_crea_bozza_da_versione(%s, %s)$q$,
           (SELECT id FROM _v WHERE versione = 1), (SELECT id FROM _m WHERE k = 'C')),
    '%La versione 1 non si copia in questo template%documento diverso%',
    '21) in un modello di un''altra sorgente: E_DOCUMENTI_COPIA_DOCUMENTO_DIVERSO');

SELECT throws_like(
    format($q$SELECT documenti.fn_crea_bozza_da_versione(%s, %s)$q$,
           (SELECT id FROM _v WHERE versione = 1),
           (SELECT max(id) + 1000000 FROM documenti.template_documenti)),
    '%il modello non esiste%',
    '22) in un modello che non esiste: E_PARAMETRO_INVALIDO, non il 23503 della chiave esterna');

SELECT throws_like(
    format($q$SELECT documenti.fn_crea_bozza_da_versione(NULL, %s)$q$, (SELECT id FROM _m WHERE k = 'A')),
    '%p_versione_origine_id obbligatorio%',
    '23) origine NULL: E_PARAMETRO_INVALIDO');

SELECT throws_like(
    format($q$SELECT documenti.fn_crea_bozza_da_versione(%s, NULL)$q$, (SELECT id FROM _v WHERE versione = 1)),
    '%p_template_documento_id obbligatorio%',
    '24) destinazione NULL: E_PARAMETRO_INVALIDO');

SELECT throws_like(
    format($q$SELECT documenti.fn_crea_bozza_da_versione(%s, %s)$q$,
           (SELECT max(id) + 1000000 FROM documenti.template_documenti_versioni),
           (SELECT id FROM _m WHERE k = 'A')),
    '%la versione non esiste%',
    '25) origine che non esiste: E_PARAMETRO_INVALIDO');

CREATE TEMP TABLE _copia ON COMMIT DROP AS
SELECT documenti.fn_crea_bozza_da_versione(
    (SELECT id FROM _v WHERE versione = 1), (SELECT id FROM _m WHERE k = 'A')) AS id;

SELECT is(
    (SELECT t.versione || '=' || t.stato || '/' || t.html_template
       FROM documenti.template_documenti_versioni t WHERE t.id = (SELECT id FROM _copia)),
    '4=BOZZA/<p>v1</p>',
    '26) nello stesso modello: una BOZZA col numero successivo e il corpo della V1');

SELECT ok(
    (SELECT count(*) = 1 FROM pg_constraint c
      WHERE c.conrelid = 'documenti.template_documenti_versioni'::regclass
        AND c.conname = 'uq_template_documenti_versioni_template_versione'
        AND c.contype = 'u')
    AND (SELECT p.prosrc LIKE '%''uq_template_documenti_versioni_template_versione''%'
                     AND p.prosrc LIKE '%E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE%'
           FROM pg_proc p WHERE p.oid = 'documenti.fn_crea_bozza_da_versione'::regproc),
    '27) il vincolo che il verbo traduce in E_DOCUMENTI_VERSIONE_NUMERO_CONCORRENTE esiste col nome che cerca');

SELECT * FROM finish();
ROLLBACK;
