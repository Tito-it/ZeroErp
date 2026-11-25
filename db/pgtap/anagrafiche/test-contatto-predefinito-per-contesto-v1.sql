-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Il contatto predefinito e' della riga di contesto (soggetto, ruolo,
-- istanza), un contesto con contatti ha sempre il suo, e la lettura dei
-- contatti. Giro 5 (T7b) di brief-db-revisione-anagrafiche §22, decisioni
-- D-T7b-1 … -5 di Tid (2026-11-25) e le correzioni senza scelta (S8, S46).
--
-- ⭐ Scritto ROSSO prima dei changeSet: su ogni caso segnato «(rosso)» il
--   comportamento di prima dava un altro esito.
--
-- Elenco test (plan 20):
--   la forma
--    1) l'indice unico del predefinito: (soggetto, ruolo, istanza),
--       NULLS NOT DISTINCT, WHERE is_default                        (rosso)
--    2) il CHECK: un contatto d'istanza ha il ruolo                 (rosso)
--   D-T7b-1, il predefinito per ruolo
--    3) due ruoli dello stesso soggetto: il primo contatto di
--       ciascuno nasce predefinito                                  (rosso)
--    4) marcare il secondo contatto del fornitore non tocca il cliente
--                                                                   (rosso)
--    5) ... e toglie il segno al primo contatto del fornitore, con
--       default_context NULL
--   D-T7b-2, il segno tolto e il predefinito cancellato
--    6) togliere il segno all'unico predefinito: rifiutato,
--       E_CONTATTO_PREDEFINITO_OBBLIGATORIO sul campo is_default    (rosso)
--    7) modificare un altro contatto del contesto non sposta il segno
--    8) cancellare il predefinito con un altro accanto: rifiutato,
--       E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE                        (rosso)
--    9) marcato l'altro, il vecchio predefinito si cancella
--   10) l'ultimo contatto del contesto si cancella
--   D-T7b-3
--   11) un contatto d'istanza senza ruolo: 23514 sul CHECK          (rosso)
--   D-T7b-4
--   12) fn_get_contatti senza reparto trova il contatto che ha un
--       reparto                                                     (rosso)
--   13) col reparto vince ancora il contatto del reparto
--   fn_get_contatto_default (S8, senza scelta)
--   14) vince il predefinito del contesto piu' specifico, anche se
--       nato dopo quello del soggetto                               (rosso)
--   fn_crea_contatto (D-T7b-5 e S46)
--   15) il doppione del tipo: E_CONTATTO_TIPO_DUPLICATO sul campo
--       tipo_contatto_id                                            (rosso)
--   16) ... la frase dice il livello                                (rosso)
--   17) il tipo non numerico: E_CONTATTO_INCOMPLETO, campo tipo_contatto_id
--                                                                   (rosso)
--   18) il tipo che non esiste: E_TIPO_CONTATTO_NON_TROVATO          (rosso)
--   19) default_context passato: E_CAMPO_NON_AMMESSO                (rosso)
--   il cambio di contesto
--   20) il predefinito unico del suo contesto che passa a un ruolo
--       che ha gia' il suo entra non predefinito (verde anche prima:
--       prima il contatto nasceva gia' senza segno, per il caso 3)
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(20);

-- L'esito di un'istruzione: 'ok'; per un errore di dominio il codice e il
-- campo (canali CONSTRAINT e COLUMN di script.fn_log_and_raise_error); per
-- ogni altro errore lo SQLSTATE e il vincolo.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE
    v_codice text;
    v_campo  text;
    v_stato  text;
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_codice = CONSTRAINT_NAME, v_campo = COLUMN_NAME,
                            v_stato = RETURNED_SQLSTATE;
    IF v_stato = 'P0001' AND v_codice <> '' THEN
        RETURN v_codice || '/' || COALESCE(NULLIF(v_campo, ''), '-');
    END IF;
    RETURN v_stato || '/' || COALESCE(NULLIF(v_codice, ''), '-');
END;
$f$;

-- La frase di un errore, per i casi in cui conta che cosa legge l'operatore.
CREATE FUNCTION pg_temp.frase(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE
    v_msg text;
BEGIN
    EXECUTE p_sql;
    RETURN 'ok';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_msg = MESSAGE_TEXT;
    RETURN v_msg;
END;
$f$;

-- Un contatto nuovo dal verbo, col suo id.
CREATE FUNCTION pg_temp.contatto(p_soggetto uuid, p_sr bigint, p_campi jsonb) RETURNS bigint
LANGUAGE sql AS $f$
    SELECT (anagrafiche.fn_crea_contatto(p_soggetto, p_sr, p_campi) ->> 'id')::bigint
$f$;

-- ============================================================
-- Fixture: un soggetto con due ruoli, cliente e fornitore
-- ============================================================
-- Il builder scrive il contatto del soggetto, predefinito, col tipo
-- proposto: i tipi del test sono gli altri, cosi' nessun caso urta
-- uq_contatti_soggetto_tipo senza volerlo.
CREATE TEMP TABLE _f AS
SELECT s.soggetto_id,
       dbops.fn_pgtap_crea_soggetto_ruolo(s.soggetto_id, 'CL') AS sr_cl,
       dbops.fn_pgtap_crea_soggetto_ruolo(s.soggetto_id, 'FO') AS sr_fo,
       (SELECT array_agg(t.id ORDER BY t.id)
          FROM config.tipi_contatti t
         WHERE t.id NOT IN (SELECT c.tipo_contatto_id FROM anagrafiche.contatti c
                             WHERE c.soggetto_id = s.soggetto_id)) AS tipi,
       (SELECT u.id FROM config.unita_organizzative u WHERE u.attivo ORDER BY u.id LIMIT 1) AS uo_id,
       (SELECT c.id FROM anagrafiche.contatti c
         WHERE c.soggetto_id = s.soggetto_id AND c.is_default) AS c_sogg
  FROM (SELECT dbops.fn_pgtap_crea_soggetto_pg('Contatto predefinito pgTAP') AS soggetto_id) s;

-- ============================================================
-- La forma
-- ============================================================
SELECT is(
    (SELECT format('%s|%s|%s', i.indisunique::text, i.indnullsnotdistinct::text,
                   regexp_replace(pg_get_indexdef(i.indexrelid), '^.* USING ', ''))
       FROM pg_index i
       JOIN pg_class c ON c.oid = i.indexrelid
      WHERE i.indrelid = 'anagrafiche.contatti'::regclass
        AND c.relname = 'uq_contatti_predefinito_contesto'),
    'true|true|btree (soggetto_id, soggetto_ruolo_id, istanza_utility_id) NULLS NOT DISTINCT WHERE is_default',
    '1) l''indice del predefinito: soggetto, ruolo e istanza, NULLS NOT DISTINCT, WHERE is_default');

SELECT is(
    (SELECT pg_get_constraintdef(k.oid)
       FROM pg_constraint k
      WHERE k.conrelid = 'anagrafiche.contatti'::regclass
        AND k.conname = 'chk_contatti_istanza_con_ruolo'),
    'CHECK (((istanza_utility_id IS NULL) OR (soggetto_ruolo_id IS NOT NULL)))',
    '2) il CHECK: un contatto d''istanza ha il ruolo');

-- ============================================================
-- D-T7b-1: il predefinito e' del ruolo
-- ============================================================
CREATE TEMP TABLE _c AS
SELECT pg_temp.contatto(f.soggetto_id, f.sr_cl,
           jsonb_build_object('tipo_contatto_id', f.tipi[1], 'nominativo', 'Cliente uno')) AS c_cl1,
       NULL::bigint AS c_fo1,
       NULL::bigint AS c_fo2
  FROM _f f;
UPDATE _c SET c_fo1 = pg_temp.contatto(f.soggetto_id, f.sr_fo,
                  jsonb_build_object('tipo_contatto_id', f.tipi[1], 'nominativo', 'Fornitore uno'))
  FROM _f f;

SELECT is(
    (SELECT string_agg(format('%s:%s', CASE c.id WHEN k.c_cl1 THEN 'cl1' ELSE 'fo1' END, c.is_default::text), ' ' ORDER BY c.id)
       FROM anagrafiche.contatti c, _c k
      WHERE c.id IN (k.c_cl1, k.c_fo1)),
    'cl1:true fo1:true',
    '3) due ruoli dello stesso soggetto: il primo contatto di ciascuno nasce predefinito');

UPDATE _c SET c_fo2 = pg_temp.contatto(f.soggetto_id, f.sr_fo,
                  jsonb_build_object('tipo_contatto_id', f.tipi[2], 'nominativo', 'Fornitore due',
                                     'is_default', true))
  FROM _f f;

SELECT is(
    (SELECT c.is_default FROM anagrafiche.contatti c, _c k WHERE c.id = k.c_cl1),
    true,
    '4) marcare il secondo contatto del fornitore non tocca il predefinito del cliente');

SELECT is(
    (SELECT format('%s|%s|%s', f1.is_default::text, COALESCE(f1.default_context, '<NULL>'), f2.default_context)
       FROM _c k
       JOIN anagrafiche.contatti f1 ON f1.id = k.c_fo1
       JOIN anagrafiche.contatti f2 ON f2.id = k.c_fo2),
    'false|<NULL>|ruolo',
    '5) ... e lo toglie al primo contatto del fornitore, che resta senza etichetta');

-- ============================================================
-- D-T7b-2: un contesto con contatti ha sempre il suo predefinito
-- ============================================================
SELECT is(
    pg_temp.esito(format('UPDATE anagrafiche.contatti SET is_default = false WHERE id = %s',
                         (SELECT c_fo2 FROM _c))),
    'E_CONTATTO_PREDEFINITO_OBBLIGATORIO/is_default',
    '6) togliere il segno all''unico predefinito del contesto e'' rifiutato');

UPDATE anagrafiche.contatti SET note = 'una correzione' WHERE id = (SELECT c_fo1 FROM _c);

SELECT is(
    (SELECT format('%s|%s', f1.is_default::text, f2.is_default::text)
       FROM _c k
       JOIN anagrafiche.contatti f1 ON f1.id = k.c_fo1
       JOIN anagrafiche.contatti f2 ON f2.id = k.c_fo2),
    'false|true',
    '7) modificare un altro contatto del contesto non sposta il segno');

SELECT is(
    pg_temp.esito(format('DELETE FROM anagrafiche.contatti WHERE id = %s', (SELECT c_fo2 FROM _c))),
    'E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE/is_default',
    '8) cancellare il predefinito con un altro contatto accanto e'' rifiutato');

UPDATE anagrafiche.contatti SET is_default = true WHERE id = (SELECT c_fo1 FROM _c);

SELECT is(
    pg_temp.esito(format('DELETE FROM anagrafiche.contatti WHERE id = %s', (SELECT c_fo2 FROM _c))),
    'ok',
    '9) marcato l''altro, il vecchio predefinito si cancella');

SELECT is(
    pg_temp.esito(format('DELETE FROM anagrafiche.contatti WHERE id = %s', (SELECT c_fo1 FROM _c))),
    'ok',
    '10) l''ultimo contatto del contesto si cancella');

-- ============================================================
-- D-T7b-3: il contatto d'istanza ha il ruolo
-- ============================================================
-- Un'istanza del soggetto, perche' a parlare sia il CHECK e non il guard
-- del contesto (E_ISTANZA_ALTRO_SOGGETTO).
SET CONSTRAINTS anagrafiche.trg_istanze_utilities_z90_require_utility_dichiarata_ins DEFERRED;
CREATE TEMP TABLE _i AS
WITH n AS (
    INSERT INTO anagrafiche.istanze_utilities (fittizia, codice, soggetto_id)
    SELECT true, 'PGTAPT7B' || substr(md5(clock_timestamp()::text), 1, 8), f.soggetto_id
      FROM _f f
    RETURNING id)
SELECT id FROM n;

SELECT is(
    pg_temp.esito(format(
        'SELECT anagrafiche.fn_crea_contatto(%L, NULL, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        jsonb_build_object('tipo_contatto_id', (SELECT tipi[3] FROM _f),
                           'nominativo', 'Istanza senza ruolo',
                           'istanza_utility_id', (SELECT id FROM _i)))),
    '23514/chk_contatti_istanza_con_ruolo',
    '11) un contatto d''istanza senza ruolo non si scrive');

-- ============================================================
-- D-T7b-4: fn_get_contatti senza reparto
-- ============================================================
CREATE TEMP TABLE _r AS
SELECT pg_temp.contatto(f.soggetto_id, NULL,
           jsonb_build_object('tipo_contatto_id', f.tipi[2], 'nominativo', 'Amministrazione',
                              'unita_organizzativa_id', f.uo_id)) AS c_rep
  FROM _f f;

SELECT is(
    (SELECT count(*)::int
       FROM _f f, _r r, script.fn_get_contatti(f.soggetto_id) g
      WHERE g.id = r.c_rep),
    1,
    '12) senza reparto, fn_get_contatti trova il contatto che ne ha uno');

SELECT is(
    (SELECT g.id
       FROM _f f, script.fn_get_contatti(f.soggetto_id, NULL, NULL, f.tipi[2], f.uo_id) g),
    (SELECT c_rep FROM _r),
    '13) col reparto vince il contatto del reparto');

-- ============================================================
-- fn_get_contatto_default: il contesto piu' specifico
-- ============================================================
-- Il predefinito del soggetto (del builder) e' nato prima di quello del
-- cliente: con l'ordine per id vinceva lui.
SELECT is(
    (SELECT d.id FROM _f f, script.fn_get_contatto_default(f.soggetto_id, f.sr_cl) d),
    (SELECT c_cl1 FROM _c),
    '14) fn_get_contatto_default: vince il predefinito del ruolo, nato dopo quello del soggetto');

-- ============================================================
-- fn_crea_contatto: il doppione e il tipo
-- ============================================================
SELECT is(
    pg_temp.esito(format(
        'SELECT anagrafiche.fn_crea_contatto(%L, %s, %L::jsonb)',
        (SELECT soggetto_id FROM _f), (SELECT sr_cl FROM _f),
        jsonb_build_object('tipo_contatto_id', (SELECT tipi[1] FROM _f), 'nominativo', 'Doppione'))),
    'E_CONTATTO_TIPO_DUPLICATO/tipo_contatto_id',
    '15) il doppione del tipo nello stesso contesto ha il suo codice, sul campo del tipo');

SELECT matches(
    pg_temp.frase(format(
        'SELECT anagrafiche.fn_crea_contatto(%L, %s, %L::jsonb)',
        (SELECT soggetto_id FROM _f), (SELECT sr_cl FROM _f),
        jsonb_build_object('tipo_contatto_id', (SELECT tipi[1] FROM _f), 'nominativo', 'Doppione'))),
    'ruolo',
    '16) ... e la frase dice il livello');

SELECT is(
    pg_temp.esito(format(
        'SELECT anagrafiche.fn_crea_contatto(%L, NULL, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        jsonb_build_object('tipo_contatto_id', 'abc', 'nominativo', 'Tipo non numerico'))),
    'E_CONTATTO_INCOMPLETO/tipo_contatto_id',
    '17) il tipo non numerico: E_CONTATTO_INCOMPLETO sul campo del tipo');

SELECT is(
    pg_temp.esito(format(
        'SELECT anagrafiche.fn_crea_contatto(%L, NULL, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        jsonb_build_object('tipo_contatto_id', (SELECT max(t.id) + 1000 FROM config.tipi_contatti t),
                           'nominativo', 'Tipo che non esiste'))),
    'E_TIPO_CONTATTO_NON_TROVATO/tipo_contatto_id',
    '18) il tipo che non esiste: E_TIPO_CONTATTO_NON_TROVATO sul campo del tipo');

SELECT is(
    pg_temp.esito(format(
        'SELECT anagrafiche.fn_crea_contatto(%L, NULL, %L::jsonb)',
        (SELECT soggetto_id FROM _f),
        jsonb_build_object('tipo_contatto_id', (SELECT tipi[3] FROM _f), 'nominativo', 'Contesto',
                           'default_context', 'soggetto'))),
    'E_CAMPO_NON_AMMESSO/default_context',
    '19) default_context non e'' piu'' una chiave ammessa');

-- ============================================================
-- Il cambio di contesto
-- ============================================================
-- Il contatto del reparto e' l'unico del suo tipo, ma non il predefinito
-- del soggetto. Un contatto del fornitore, unico e quindi predefinito, passa
-- al cliente, che ha il suo: entra senza segno, e il cliente tiene il suo.
CREATE TEMP TABLE _m AS
SELECT pg_temp.contatto(f.soggetto_id, f.sr_fo,
           jsonb_build_object('tipo_contatto_id', f.tipi[3], 'nominativo', 'Da spostare')) AS c_mv
  FROM _f f;
UPDATE anagrafiche.contatti SET soggetto_ruolo_id = (SELECT sr_cl FROM _f) WHERE id = (SELECT c_mv FROM _m);

SELECT is(
    (SELECT format('%s|%s', mv.is_default::text, cl.is_default::text)
       FROM _m m, _c k
       JOIN anagrafiche.contatti cl ON cl.id = k.c_cl1
       JOIN anagrafiche.contatti mv ON true
      WHERE mv.id = m.c_mv),
    'false|true',
    '20) il predefinito del fornitore che passa al cliente entra senza segno, e il cliente tiene il suo');

SELECT * FROM finish();
ROLLBACK;
