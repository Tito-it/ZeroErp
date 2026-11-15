-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il LINK documento -> commessa (vendite.commesse_sorgenti) nella
--   grammatica del modello. La chiave del documento sta in sorgente_id (tipi a
--   chiave id) o in sorgente_uid uuid (tipi a chiave uid); la porta la scrive dal
--   BB, i lettori la cercano con la regola d'incontro, il guard unico la valida.
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto C, giro C.2 (S-4)
-- ------------------------------------------------------------
-- Indice test (plan 22):
--   LA FORMA
--    1) sorgente_id bigint, sorgente_uid uuid, entrambe NULL ammesse
--    2) CHECK di forma e unicita' sulla chiave nuova (NULLS NOT DISTINCT)
--    3) guard unico (DOCUMENTO, BLOCCA) al posto del testuale; perimetro UNICO
--    4) l'ordine dei BEFORE ROW: prima il guard unico, poi l'emittente, che vede sorgente_id
--    5) una firma sola per commessa viva, check e guard dell'emittente; il ponte testuale non c'e'
--   LA PORTA
--    6) l'ordine passato per uid in testo (come il push): sorgente_id = l'id, ROOT
--    7) il preventivo passato per uid in testo: sorgente_uid = l'uid, COLLEGATO
--    8) l'ordine passato per id in testo: lo stesso link (idempotente)
--    9) l'ordine su una seconda commessa aperta: E_COMMESSA_SORGENTE_ALTRA_COMMESSA
--   LA COMMESSA VIVA
--   10) con id e uid del documento, con la sola chiave del modello, per tutti e due i tipi
--   11) la commessa annullata non trattiene il documento
--   IL GUARD UNICO
--   12) l'uid in sorgente_uid per un tipo a chiave id: E_SORG_CHIAVE_NON_CONFORME
--   13) un ordine che non c'e': E_SORG_NOT_FOUND
--   14) tutte e due le chiavi: E_SORG_CHIAVE_NON_CONFORME (il guard parla prima del CHECK)
--   15) la riga del preventivo: passa
--   16) la riga di un ALTRO preventivo: E_SORG_RIGA_NON_DEL_DOCUMENTO
--   L'EMITTENTE
--   17) il check dell'emittente sulle colonne del modello: omogeneo
--   IL FLAG DI CORSIA
--   18) l'ordine in una commessa aperta: E_FATT_IMMEDIATA_NON_MODIFICABILE
--   LA CANCELLAZIONE (BLOCCA)
--   19) l'ordine collegato non si cancella: E_SORG_ORIGINE_REFERENZIATA
--   LA LINEAGE
--   20) gli archi E (ordine -> commessa) e B (preventivo -> commessa), dal seme dell'ordine e del preventivo
--   21) ... e nel modo «tutti», dalla vista
--   GLI ORFANI
--   22) il presidio degli orfani non vede i link del test
--
-- ⚠️ Il mondo si COSTRUISCE: preventivi, ordine e commesse dai builder
--   dbops.fn_pgtap_*, sullo stesso billing account (un solo emittente). Gira come
--   l'applicazione (operatore in sessione, RLS attiva). I link li scrive la porta;
--   i casi rifiutati dal guard si scrivono a mano, perche' la porta non li produce.
-- rev 2026-11-08 (brief-db-sorgente-documento-e-riga lotto P, giro P.1): il guard testuale si cerca per nome da pg_proc (e' ritirato).
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT is(
  (SELECT string_agg(a.attname || ':' || format_type(a.atttypid, a.atttypmod) || ':' || a.attnotnull, '|' ORDER BY a.attname)
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.commesse_sorgenti'::regclass
      AND a.attname IN ('sorgente_id', 'sorgente_uid')),
  'sorgente_id:bigint:false|sorgente_uid:uuid:false',
  '1) la chiave del documento sta in due colonne tipizzate, una delle due NULL');

SELECT is(
  (SELECT string_agg(k.conname || '=' || pg_get_constraintdef(k.oid), ' | ' ORDER BY k.conname)
     FROM pg_constraint k
    WHERE k.conrelid = 'vendite.commesse_sorgenti'::regclass
      AND k.conname IN ('chk_commesse_sorgenti_sorgente_forma', 'uq_commesse_sorgenti_sorgente_commessa')),
  'chk_commesse_sorgenti_sorgente_forma=CHECK ((num_nonnulls(sorgente_id, sorgente_uid) = 1)) | '
  'uq_commesse_sorgenti_sorgente_commessa=UNIQUE NULLS NOT DISTINCT (sorgente_tipo_id, sorgente_id, sorgente_uid, commessa_id)',
  '2) CHECK di forma e unicita'' per commessa sulla chiave nuova, NULLS NOT DISTINCT');

-- ⚠️ Schema e nome da pg_class + pg_namespace, non da regclass::text: il testo
--   di un regclass dipende dal search_path di chi guarda.
SELECT is(
  (SELECT concat_ws('|',
      (SELECT m.livello_minimo || '/' || m.azione_cancellazione
         FROM script.fn_sorgente_guard_montaggi() m
        WHERE m.schema_tabella = 'vendite' AND m.nome_tabella = 'commesse_sorgenti'),
      (SELECT count(*) FROM pg_trigger t
        WHERE t.tgrelid = 'vendite.commesse_sorgenti'::regclass
          -- Per nome da pg_proc, non ::regproc: la _testuale e' ritirata (giro P.1),
          -- e un cast sul nome di una funzione che non c'e' e' un errore, non uno zero.
          AND t.tgfoid IN (SELECT p.oid FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
                            WHERE n.nspname = 'script' AND p.proname = 'trgfn_guard_sorgente_polimorfa_testuale')),
      (SELECT p.grammatica || '/' || coalesce(p.orfani_esclusi_perche, 'nessuna esenzione')
         FROM dbops.fn_sorgenti_orfane_perimetro() p
        WHERE p.schema_tabella = 'vendite' AND p.nome_tabella = 'commesse_sorgenti'))),
  'DOCUMENTO/BLOCCA|0|UNICO/nessuna esenzione',
  '3) guard unico (DOCUMENTO, BLOCCA) al posto del testuale; la tabella sta nel perimetro degli orfani');

-- I BEFORE ROW scattano in ordine alfabetico: il guard dell'emittente deve
-- parlare dopo quello che verifica che il documento esista.
SELECT is(
  (SELECT string_agg(t.tgname || '(' || (SELECT string_agg(a.attname, ',' ORDER BY a.attname)
                                            FROM pg_attribute a
                                           WHERE a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)) || ')',
                     ' < ' ORDER BY t.tgname)
     FROM pg_trigger t
    WHERE t.tgrelid = 'vendite.commesse_sorgenti'::regclass
      AND t.tgname LIKE 'trg_commesse_sorgenti_a10_guard_sorgente%'),
  'trg_commesse_sorgenti_a10_guard_sorgente_ins_upd(sorgente_id,sorgente_riga,sorgente_tipo_id,sorgente_uid)'
  ' < trg_commesse_sorgenti_a10_guard_sorgente_omogeneita_ins_upd(commessa_id,sorgente_id,sorgente_tipo_id,sorgente_uid)',
  '4) prima il guard unico, poi l''emittente; tutti e due vedono sorgente_id');

SELECT is(
  -- ⚠️ Schema e firma da pg_namespace e oidvectortypes, non da regprocedure::text:
  --   quel testo dipende dal search_path di chi guarda.
  (SELECT string_agg(n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')', ' | ' ORDER BY p.proname)
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (('vendite', 'fn_commessa_viva_di_sorgente'),
                                     ('vendite', 'fn_check_commessa_sorgente_emittente_omogeneo'),
                                     ('vendite', 'fn_guard_commessa_sorgente_emittente'),
                                     ('script',  'fn_get_sorgente_emittente_sr_id'))),
  'vendite.fn_check_commessa_sorgente_emittente_omogeneo(bigint, bigint, bigint, uuid) | '
  'vendite.fn_commessa_viva_di_sorgente(bigint, bigint, uuid) | '
  'script.fn_get_sorgente_emittente_sr_id(bigint, bigint, uuid) | '
  'vendite.fn_guard_commessa_sorgente_emittente(bigint, bigint, bigint, uuid)',
  '5) una firma sola, sulle colonne del modello; il ponte testuale dell''emittente non c''e''');

-- ============================================================
-- Fixture: due preventivi con una riga, un ordine e due commesse, tutti
--   sul billing account del preventivo A (un emittente solo)
-- ============================================================
CREATE TEMP TABLE _pv AS
SELECT v.k, p.*
  FROM (VALUES ('A'), ('B')) v(k),
       LATERAL dbops.fn_pgtap_crea_preventivo_con_righe('cs sorgenti ' || v.k, 'DRAFT') p;

CREATE TEMP TABLE _or AS
SELECT o.* FROM dbops.fn_pgtap_crea_ordine('cs sorgenti ordine', 'DRAFT',
                                           (SELECT billing_account_id FROM _pv WHERE k = 'A')) o;

CREATE TEMP TABLE _comm AS
SELECT v.k, c.*
  FROM (VALUES ('M1'), ('M2'), ('M3')) v(k),
       LATERAL dbops.fn_pgtap_crea_commessa('cs sorgenti ' || v.k, NULL,
                                            (SELECT billing_account_id FROM _pv WHERE k = 'A'),
                                            false, false) c;

CREATE TEMP TABLE _t AS
SELECT (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA') AS t_ord,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')     AS t_prev;

CREATE FUNCTION pg_temp.comm(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT commessa_id FROM _comm WHERE k = p $fx$;

-- ============================================================
-- LA PORTA
-- ============================================================
CREATE TEMP TABLE _link AS
SELECT 'ORD'::text AS k,
       vendite.fn_link_commessa_sorgente(pg_temp.comm('M1'), (SELECT t_ord FROM _t),
                                         (SELECT ordine_uid::text FROM _or)) AS link_id;
INSERT INTO _link
SELECT 'PREV', vendite.fn_link_commessa_sorgente(pg_temp.comm('M1'), (SELECT t_prev FROM _t),
                                                 (SELECT preventivo_uid::text FROM _pv WHERE k = 'A'));

SELECT is(
  (SELECT concat_ws('|', cs.sorgente_id = o.ordine_id, cs.sorgente_uid IS NULL, cs.ruolo_link)
     FROM vendite.commesse_sorgenti cs, _or o
    WHERE cs.id = (SELECT link_id FROM _link WHERE k = 'ORD')),
  't|t|ROOT',
  '6) l''ordine passato per uid in testo, come il push: il link tiene l''id in sorgente_id, ROOT');

SELECT is(
  (SELECT concat_ws('|', cs.sorgente_uid = p.preventivo_uid, cs.sorgente_id IS NULL, cs.ruolo_link)
     FROM vendite.commesse_sorgenti cs, _pv p
    WHERE cs.id = (SELECT link_id FROM _link WHERE k = 'PREV') AND p.k = 'A'),
  't|t|COLLEGATO',
  '7) il preventivo passato per uid in testo: il link tiene l''uid in sorgente_uid, COLLEGATO');

SELECT is(
  vendite.fn_link_commessa_sorgente(pg_temp.comm('M1'), (SELECT t_ord FROM _t),
                                    (SELECT ordine_id::text FROM _or)),
  (SELECT link_id FROM _link WHERE k = 'ORD'),
  '8) l''ordine passato per id in testo: lo stesso link, idempotente');

SELECT is(
  dbops.fn_pgtap_codice_errore(format('SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L)',
                       pg_temp.comm('M2'), (SELECT t_ord FROM _t), (SELECT ordine_uid::text FROM _or))),
  'E_COMMESSA_SORGENTE_ALTRA_COMMESSA',
  '9) l''ordine su una seconda commessa aperta: rifiutato');

-- ============================================================
-- LA COMMESSA VIVA
-- ============================================================
SELECT is(
  (SELECT concat_ws('|',
      vendite.fn_commessa_viva_di_sorgente(t.t_ord, o.ordine_id, o.ordine_uid),
      vendite.fn_commessa_viva_di_sorgente(t.t_ord, o.ordine_id, NULL),
      vendite.fn_commessa_viva_di_sorgente(t.t_prev, p.preventivo_id, p.preventivo_uid),
      vendite.fn_commessa_viva_di_sorgente(t.t_prev, NULL, p.preventivo_uid),
      coalesce(vendite.fn_commessa_viva_di_sorgente(t.t_ord, NULL, o.ordine_uid)::text, 'nessuna'))
     FROM _t t, _or o, _pv p WHERE p.k = 'A'),
  concat_ws('|', pg_temp.comm('M1'), pg_temp.comm('M1'), pg_temp.comm('M1'), pg_temp.comm('M1'), 'nessuna'),
  '10) con id e uid del documento, o con la sola chiave del modello: la commessa del link (l''uid non e'' la chiave dell''ordine)');

-- Annullata M1, il link resta come storia e l'ordine torna libero.
DO $ann$ BEGIN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.commesse'::regclass, pg_temp.comm('M1'), 'ANNULLATA');
END $ann$;

-- ⚠️ Tre istruzioni: la commessa viva e' STABLE e legge la fotografia
--   dell'istruzione, quindi non vedrebbe il link scritto nella stessa.
CREATE TEMP TABLE _m2 AS
SELECT coalesce(vendite.fn_commessa_viva_di_sorgente(t.t_ord, o.ordine_id, o.ordine_uid)::text, 'nessuna') AS prima
  FROM _t t, _or o;
ALTER TABLE _m2 ADD COLUMN link text;
UPDATE _m2 SET link = COALESCE(dbops.fn_pgtap_codice_errore(format('SELECT vendite.fn_link_commessa_sorgente(%s, %s, %L)',
                                           pg_temp.comm('M2'), (SELECT t_ord FROM _t), (SELECT ordine_uid::text FROM _or))), 'PASSA');

SELECT is(
  (SELECT concat_ws('|', m.prima, m.link,
                    vendite.fn_commessa_viva_di_sorgente(t.t_ord, o.ordine_id, o.ordine_uid) = pg_temp.comm('M2'))
     FROM _m2 m, _t t, _or o),
  'nessuna|PASSA|t',
  '11) la commessa annullata non trattiene l''ordine: va su M2, che diventa la sua commessa aperta');

-- ============================================================
-- IL GUARD UNICO (scritture a mano: la porta non le produce)
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
       VALUES (%s, %s, %L, 'COLLEGATO')$q$,
    pg_temp.comm('M3'), (SELECT t_ord FROM _t), (SELECT ordine_uid FROM _or))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '12) l''uid dell''ordine in sorgente_uid: non e'' la chiave del suo tipo');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_id, ruolo_link)
       VALUES (%s, %s, %s, 'COLLEGATO')$q$,
    pg_temp.comm('M3'), (SELECT t_ord FROM _t), (SELECT max(id) + 1000000 FROM vendite.ordini))),
  'E_SORG_NOT_FOUND',
  '13) un ordine che non c''e'': rifiutato');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$INSERT INTO vendite.commesse_sorgenti (commessa_id, sorgente_tipo_id, sorgente_id, sorgente_uid, ruolo_link)
       VALUES (%s, %s, %s, %L, 'COLLEGATO')$q$,
    pg_temp.comm('M3'), (SELECT t_ord FROM _t), (SELECT ordine_id FROM _or), (SELECT ordine_uid FROM _or))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '14) tutte e due le chiavi del documento: rifiutato dal guard, prima del CHECK di forma');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$UPDATE vendite.commesse_sorgenti SET sorgente_riga = %s WHERE id = %s$q$,
    (SELECT preventivo_riga_id FROM _pv WHERE k = 'A'), (SELECT link_id FROM _link WHERE k = 'PREV'))),
  NULL,
  '15) la riga del preventivo sul suo link: passa');

SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$UPDATE vendite.commesse_sorgenti SET sorgente_riga = %s WHERE id = %s$q$,
    (SELECT preventivo_riga_id FROM _pv WHERE k = 'B'), (SELECT link_id FROM _link WHERE k = 'PREV'))),
  'E_SORG_RIGA_NON_DEL_DOCUMENTO',
  '16) la riga di un ALTRO preventivo: rifiutata');

-- ============================================================
-- L'EMITTENTE
-- ============================================================
SELECT ok(
  (SELECT vendite.fn_check_commessa_sorgente_emittente_omogeneo(pg_temp.comm('M3'), t.t_ord, o.ordine_id, NULL)
      AND vendite.fn_check_commessa_sorgente_emittente_omogeneo(pg_temp.comm('M3'), t.t_prev, NULL, p.preventivo_uid)
     FROM _t t, _or o, _pv p WHERE p.k = 'A'),
  '17) il check dell''emittente sulle colonne del modello: ordine e preventivo dello stesso billing account sono omogenei');

-- ============================================================
-- IL FLAG DI CORSIA
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format(
    $q$UPDATE vendite.ordini SET fatturazione_immediata = NOT fatturazione_immediata WHERE id = %s$q$,
    (SELECT ordine_id FROM _or))),
  'E_FATT_IMMEDIATA_NON_MODIFICABILE',
  '18) l''ordine sta in una commessa aperta (M2): il flag di corsia non si cambia');

-- ============================================================
-- LA CANCELLAZIONE (BLOCCA)
-- ============================================================
SELECT is(
  dbops.fn_pgtap_codice_errore(format($q$DELETE FROM vendite.ordini WHERE id = %s$q$, (SELECT ordine_id FROM _or))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '19) l''ordine collegato a una commessa non si cancella, anche in bozza');

-- ============================================================
-- LA LINEAGE
-- ============================================================
SELECT is(
  (SELECT string_agg(a.arco || ':' || a.to_uid || ':' || a.ruolo, ' | ' ORDER BY a.arco, a.to_uid)
     FROM _t t, _or o, _pv p,
          LATERAL vendite.fn_documento_lineage_archi(ARRAY[t.t_ord, t.t_prev], ARRAY[o.ordine_id::text, p.preventivo_uid::text]) a
    WHERE p.k = 'A' AND a.arco IN ('B', 'E')),
  concat('B:', pg_temp.comm('M1'), ':COLLEGATO | E:', pg_temp.comm('M1'), ':ROOT | E:', pg_temp.comm('M2'), ':ROOT'),
  '20) dal seme: l''ordine verso le sue due commesse (E, la storia resta), il preventivo verso M1 (B)');

SELECT is(
  (SELECT string_agg(a.arco || ':' || a.from_uid || '->' || a.to_uid, ' | ' ORDER BY a.arco, a.to_uid)
     FROM vendite.vw_documento_lineage_archi a
    WHERE a.arco IN ('B', 'E')
      AND a.to_uid IN (pg_temp.comm('M1')::text, pg_temp.comm('M2')::text)),
  (SELECT concat('B:', p.preventivo_uid, '->', pg_temp.comm('M1'),
                 ' | E:', o.ordine_id, '->', pg_temp.comm('M1'),
                 ' | E:', o.ordine_id, '->', pg_temp.comm('M2'))
     FROM _or o, _pv p WHERE p.k = 'A'),
  '21) nel modo «tutti», dalla vista: gli stessi archi, con la chiave del documento dalla colonna del suo tipo');

-- ============================================================
-- GLI ORFANI
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM dbops.vw_sorgenti_orfane o
    WHERE o.tabella = 'vendite.commesse_sorgenti'::regclass
      AND o.riga_id IN (SELECT cs.id FROM vendite.commesse_sorgenti cs
                         WHERE cs.commessa_id IN (SELECT commessa_id FROM _comm))),
  0,
  '22) il presidio degli orfani non vede i link del test, che citano documenti veri');

SELECT * FROM finish();
ROLLBACK;
