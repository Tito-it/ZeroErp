-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: la regola del PERIODO — valido_al non precede valido_dal — ha UNA
--       sede, script.trgfn_guard_date_validita, e l'automazione DATE_VALIDITA
--       la monta su OGNI tabella che porta la coppia di date.
-- Oggetti:
--   script.trgfn_guard_date_validita()             (20260923-40)
--   dbops.fn_run_automations_date_validita()       (20260923-41)
--   90_end 20260923-47 (convergenza a ogni migrate)
-- Brief: brief-db-guard-date-validita.md
--
-- Elenco test (plan 12):
--  1) ⭐ nessuna tabella con valido_dal/valido_al e' senza il guard (lista
--     letta da pg_attribute, non scritta qui)
--  2) nessuna tabella ne ha DUE (l'automazione e' idempotente)
--  3) ogni guard e' BEFORE ROW, su INSERT e UPDATE OF valido_dal, valido_al
--  4) lo storico e' escluso: nessuna tabella ombra ha il guard
--  5) risorse_umane (validita generata + CHECK): date invertite -> il guard,
--     non il daterange
--  6) risorse_umane: stesso giorno -> passa (il periodo di un giorno esiste)
--  7) risorse_umane: valido_al NULL -> passa (periodo aperto)
--  8) articoli_uom_operativa (validita generata, NESSUN CHECK): date
--     invertite -> il guard
--  9) articoli_uom_operativa: stesso giorno -> passa
-- 10) identita_digitali (niente validita, solo CHECK): date invertite -> il
--     guard, non il CHECK
-- 11-12) i due canali strutturati: CONSTRAINT = il codice, COLUMN = il campo
--
-- Scopo:
--  - ⭐ le tre tabelle dei test 5-10 coprono le tre FORME in cui la regola
--    parlava prima (brief §2): il daterange della colonna generata (22000), il
--    CHECK (23514), e — nella forma senza CHECK — soltanto il daterange. Che
--    ora parli il guard in tutte e tre e' la prova che il BEFORE arriva prima
--    del calcolo di `validita`;
--  - ⛔ il presidio 1 NON elenca le tabelle: le legge dalla struttura. Un elenco
--    scritto qui sarebbe verde anche il giorno in cui una tabella nuova nasce
--    senza guard — che e' esattamente il difetto da presidiare;
--  - i trigger si cercano per FUNZIONE, mai per nome: il nome oltre i 63
--    caratteri PostgreSQL lo tronca.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(12);

-- ============================================================
-- 1-4) La STRUTTURA: dove c'e' la coppia di date, c'e' il guard
-- ============================================================
CREATE TEMP TABLE tmp_gdv_tabelle AS
SELECT c.oid AS relid, n.nspname AS schema_name, c.relname AS table_name
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
 WHERE c.relkind = 'r'
   AND n.nspname = ANY(dbops.fn_resolve_scope(NULL))
   AND n.nspname <> 'storico'
   AND dbops.fn_table_in_scope(n.nspname, c.relname)
   AND EXISTS (SELECT 1 FROM pg_attribute a
                WHERE a.attrelid = c.oid AND a.attname = 'valido_dal' AND NOT a.attisdropped)
   AND EXISTS (SELECT 1 FROM pg_attribute a
                WHERE a.attrelid = c.oid AND a.attname = 'valido_al' AND NOT a.attisdropped);

CREATE TEMP TABLE tmp_gdv_trigger AS
SELECT t.tgrelid AS relid, t.tgtype, t.tgattr
  FROM pg_trigger t
  JOIN pg_proc p      ON p.oid = t.tgfoid
  JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE NOT t.tgisinternal
   AND n.nspname = 'script'
   AND p.proname = 'trgfn_guard_date_validita';

SELECT is(
    (SELECT string_agg(x.schema_name || '.' || x.table_name, ', ' ORDER BY 1)
       FROM tmp_gdv_tabelle x
      WHERE NOT EXISTS (SELECT 1 FROM tmp_gdv_trigger t WHERE t.relid = x.relid)),
    NULL,
    '1) ogni tabella con valido_dal e valido_al ha il guard delle date (lista letta dalla struttura)'
);

SELECT is(
    (SELECT count(*)::int FROM (
        SELECT t.relid FROM tmp_gdv_trigger t GROUP BY t.relid HAVING count(*) > 1) d),
    0,
    '2) nessuna tabella ha il guard due volte: l''automazione riconosce il suo trigger'
);

-- tgtype: 1 = ROW, 2 = BEFORE, 4 = INSERT, 16 = UPDATE. tgattr: le colonne
-- di UPDATE OF, confrontate per NOME.
SELECT is(
    (SELECT count(*)::int
       FROM tmp_gdv_trigger t
      WHERE (t.tgtype & 1) = 0 OR (t.tgtype & 2) = 0
         OR (t.tgtype & 4) = 0 OR (t.tgtype & 16) = 0
         OR (SELECT array_agg(a.attname::text ORDER BY a.attname)
               FROM pg_attribute a
              WHERE a.attrelid = t.relid AND a.attnum = ANY(t.tgattr::int2[]))
            IS DISTINCT FROM ARRAY['valido_al', 'valido_dal']),
    0,
    '3) ogni guard e'' BEFORE ROW, su INSERT e su UPDATE OF valido_dal, valido_al'
);

SELECT is(
    (SELECT count(*)::int
       FROM tmp_gdv_trigger t
       JOIN pg_class c ON c.oid = t.relid
      WHERE c.relnamespace = 'storico'::regnamespace),
    0,
    '4) lo storico e'' escluso: le tabelle ombra ricordano, non si giudicano'
);

-- ============================================================
-- Fixture: un operatore umano (risorsa umana + identita') e un articolo
-- ============================================================
CREATE TEMP TABLE tmp_gdv_op AS
SELECT * FROM dbops.fn_pgtap_crea_operatore_umano('guard date');

-- Articolo NON gestito: il caso e' una sua mappatura dell'unita' operativa.
CREATE TEMP TABLE tmp_gdv_art AS
SELECT dbops.fn_pgtap_crea_articolo('PGTAP-GDV-' || o.auth_user_id, p_gestito := false) AS articolo_id
  FROM tmp_gdv_op o;

-- Una mappatura che non e' la base: la riga base non ha date (le vieta
--   chk_articoli_uom_operativa_base_fissa, brief-db-revisione-catalogo giro 2).
--   L'unita' si sceglie dal catalogo di sistema, col suo ORDER BY.
-- ⚠️ In un'istruzione separata dal builder: nella stessa leggerebbe la
--   snapshot di prima e non troverebbe l'articolo.
CREATE FUNCTION pg_temp.gdv_mappatura()
 RETURNS bigint
 LANGUAGE sql
AS $f$
    INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base)
    SELECT a.id, u.id, 2
      FROM catalogo.articoli a
      JOIN catalogo.unita_misura u ON u.attivo AND u.id <> a.uom_id
     WHERE a.id = (SELECT articolo_id FROM tmp_gdv_art)
     ORDER BY u.id
     LIMIT 1
    RETURNING id;
$f$;

CREATE TEMP TABLE tmp_gdv_uom AS SELECT pg_temp.gdv_mappatura() AS id;

-- ============================================================
-- 5-7) risorse_umane: validita generata + CHECK
-- ============================================================
SELECT throws_like(
    format($q$UPDATE anagrafiche.risorse_umane
                 SET valido_dal = DATE '2026-03-10', valido_al = DATE '2026-03-09'
               WHERE id = %s$q$, (SELECT risorsa_umana_id FROM tmp_gdv_op)),
    '%è inferiore alla data dal%',
    '5) risorse_umane, date invertite: parla il guard, non il daterange della colonna generata'
);

SELECT lives_ok(
    format($q$UPDATE anagrafiche.risorse_umane
                 SET valido_dal = DATE '2026-03-10', valido_al = DATE '2026-03-10'
               WHERE id = %s$q$, (SELECT risorsa_umana_id FROM tmp_gdv_op)),
    '6) risorse_umane, stesso giorno: il periodo di un giorno esiste'
);

SELECT lives_ok(
    format($q$UPDATE anagrafiche.risorse_umane
                 SET valido_al = NULL
               WHERE id = %s$q$, (SELECT risorsa_umana_id FROM tmp_gdv_op)),
    '7) risorse_umane, valido_al vuoto: periodo aperto, niente da giudicare'
);

-- ============================================================
-- 8-9) articoli_uom_operativa: validita generata, NESSUN CHECK
-- ============================================================
SELECT throws_like(
    format($q$UPDATE catalogo.articoli_uom_operativa
                 SET valido_dal = DATE '2026-03-10', valido_al = DATE '2026-03-01'
               WHERE id = %s$q$, (SELECT id FROM tmp_gdv_uom)),
    '%è inferiore alla data dal%',
    '8) articoli_uom_operativa (nessun CHECK), date invertite: parla il guard'
);

-- ⚠️ 2026-11-10 (brief-db-revisione-catalogo, giro 2-bis, Q26): l'inizio di una
--   mappatura scritta non si sposta (catalogo.trgfn_uom_guard_storia). Il periodo di
--   un giorno si prova su una mappatura nuova, in un'altra unita' dello stesso articolo:
--   la regola delle date vale anche all'inserimento.
SELECT lives_ok(
    format($q$INSERT INTO catalogo.articoli_uom_operativa (articolo_id, uom_id, factor_to_base, valido_dal, valido_al)
              SELECT o.articolo_id, u.id, 3, DATE '2026-03-10', DATE '2026-03-10'
                FROM catalogo.articoli_uom_operativa o
                JOIN catalogo.articoli a ON a.id = o.articolo_id
                JOIN catalogo.unita_misura u ON u.attivo AND u.id NOT IN (o.uom_id, a.uom_id)
               WHERE o.id = %s
               ORDER BY u.id
               LIMIT 1$q$, (SELECT id FROM tmp_gdv_uom)),
    '9) articoli_uom_operativa, stesso giorno: passa'
);

-- ============================================================
-- 10) identita_digitali: niente validita, solo CHECK
-- ============================================================
SELECT throws_like(
    format($q$UPDATE anagrafiche.identita_digitali
                 SET valido_al = valido_dal - 1
               WHERE id = %s$q$, (SELECT identita_id FROM tmp_gdv_op)),
    '%è inferiore alla data dal%',
    '10) identita_digitali (solo CHECK), date invertite: parla il guard, non il CHECK'
);

-- ============================================================
-- 11-12) I due canali strutturati: il codice e il campo
-- ============================================================
-- La frase la legge l'operatore; il CODICE lo legge il backend (CONSTRAINT) e
-- il CAMPO da accendere il frontend (COLUMN). throws_like guarda solo la
-- frase: i due canali si leggono catturando l'eccezione.
CREATE TEMP TABLE tmp_gdv_diag (vincolo text, campo text);

DO $diag$
DECLARE v_cst text; v_col text;
BEGIN
    BEGIN
        UPDATE anagrafiche.risorse_umane
           SET valido_dal = DATE '2026-03-10', valido_al = DATE '2026-03-09'
         WHERE id = (SELECT risorsa_umana_id FROM tmp_gdv_op);
        INSERT INTO tmp_gdv_diag VALUES (NULL, NULL);
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS v_cst = CONSTRAINT_NAME, v_col = COLUMN_NAME;
        INSERT INTO tmp_gdv_diag VALUES (nullif(v_cst, ''), nullif(v_col, ''));
    END;
END $diag$;

SELECT is(
    (SELECT vincolo FROM tmp_gdv_diag),
    'E_DATA_AL_MINORE_DAL',
    '11) canale CONSTRAINT: il codice di dominio, non il nome di un vincolo'
);

SELECT is(
    (SELECT campo FROM tmp_gdv_diag),
    'valido_al',
    '12) canale COLUMN: il campo da accendere e'' valido_al'
);

SELECT * FROM finish();
ROLLBACK;
