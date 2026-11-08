-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: il LINK documento -> pratica (pratiche.pratiche_sorgenti) e il log del
--   reconcile (pratiche.reconcile_errori) nella grammatica del modello. La
--   chiave del documento sta in sorgente_id (tipi a chiave id) o in sorgente_uid
--   uuid (tipi a chiave uid); i verbi la scrivono dal BB, i lettori la cercano
--   sulle colonne del modello, il guard unico la valida.
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto P, giro P.1 (S-4)
-- ------------------------------------------------------------
-- Indice test (plan 24):
--   LA FORMA
--    1) sorgente_id bigint, sorgente_uid uuid, entrambe NULL ammesse (link e log)
--    2) CHECK di forma e unicita' per pratica e ruolo sulla chiave nuova (NULLS NOT DISTINCT)
--    3) guard unico (DOCUMENTO, BLOCCA) al posto del testuale, che non esiste piu'; perimetro UNICO
--    4) il log: CHECK «al piu' una chiave», nessun guard, esenzione dichiarata nel perimetro
--    5) una firma sola, tipizzata, per la pratica del documento, lo stato e il reconcile
--    6) il trigger del reconcile sul preventivo passa il CODICE del tipo
--   GLI SCRITTORI
--    7) la pratica dal preventivo: il link ROOT tiene l'uid in sorgente_uid
--   LA PRATICA DEL DOCUMENTO
--    8) con id e uid del documento, con la sola chiave del modello, per preventivo e ordine
--    9) le liste del preventivo e dell'ordine mostrano la pratica
--   10) la sintesi della lineage, dal seme testuale di preventivo e ordine
--   LO STATO DEL DOCUMENTO
--   11) il preventivo per uid e l'ordine per id: risolti, con la chiave nelle colonne del modello
--   12) un documento che non c'e': la sentinella UNKNOWN, con la chiave ricevuta
--   13) senza chiave: E_STATO_SORGENTE_PARAM_INVALIDO
--   LE VISTE
--   14) vw_pratica_doc_sorgente: il documento piu' vivo, con la chiave tipizzata
--   15) vw_preventivi_pratiche: l'id del link si chiama pratica_sorgente_id
--   IL GUARD UNICO
--   16) l'uid in sorgente_uid per un tipo a chiave id: E_SORG_CHIAVE_NON_CONFORME
--   17) un ordine che non c'e': E_SORG_NOT_FOUND
--   18) la riga del preventivo: passa
--   19) la riga di un ALTRO preventivo: E_SORG_RIGA_NON_DEL_DOCUMENTO
--   LA CANCELLAZIONE (BLOCCA)
--   20) il preventivo collegato a una pratica non si cancella: E_SORG_ORIGINE_REFERENZIATA
--   IL RECONCILE
--   21) senza aggancio: 0, senza errore; con la chiave del preventivo: nessun errore nel log
--   22) un trigger montato con un codice che non e' un tipo: riga E_SORG_CONF, il cambio resta
--   23) il log rifiuta due chiavi (CHECK)
--   GLI ORFANI
--   24) il presidio degli orfani non vede i link del test
--
-- ⚠️ Il mondo si COSTRUISCE: due preventivi con una riga e un ordine dai
--   builder dbops.fn_pgtap_*, sullo stesso billing account; la pratica dal verbo
--   vendite.fn_genera_pratica_da_preventivo. Gira come l'applicazione (operatore
--   in sessione, RLS attiva). Il link all'ordine e i casi rifiutati dal guard si
--   scrivono a mano: nessun verbo li produce cosi'.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(24);

-- L'esito di un'istruzione: PASSA, il codice d'errore applicativo (dal
-- CONSTRAINT dell'errore di fn_log_and_raise_error), o SQLSTATE + vincolo.
CREATE FUNCTION pg_temp.esito(p_sql text) RETURNS text
LANGUAGE plpgsql AS $f$
DECLARE v_s text; v_c text;
BEGIN
    EXECUTE p_sql;
    RETURN 'PASSA';
EXCEPTION WHEN OTHERS THEN
    GET STACKED DIAGNOSTICS v_s = RETURNED_SQLSTATE, v_c = CONSTRAINT_NAME;
    RETURN CASE WHEN v_s = 'P0001' AND coalesce(v_c, '') <> '' THEN v_c
                ELSE v_s || coalesce(' ' || nullif(v_c, ''), '') END;
END
$f$;

-- ============================================================
-- LA FORMA
-- ============================================================
SELECT is(
  (SELECT string_agg(c.relname || '.' || a.attname || ':' || format_type(a.atttypid, a.atttypmod) || ':' || a.attnotnull,
                     '|' ORDER BY c.relname, a.attname)
     FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
    WHERE a.attrelid IN ('pratiche.pratiche_sorgenti'::regclass, 'pratiche.reconcile_errori'::regclass)
      AND a.attname IN ('sorgente_id', 'sorgente_uid') AND NOT a.attisdropped),
  'pratiche_sorgenti.sorgente_id:bigint:false|pratiche_sorgenti.sorgente_uid:uuid:false'
  '|reconcile_errori.sorgente_id:bigint:false|reconcile_errori.sorgente_uid:uuid:false',
  '1) la chiave del documento sta in due colonne tipizzate, nel link e nel log');

SELECT is(
  (SELECT string_agg(k.conname || '=' || pg_get_constraintdef(k.oid), ' | ' ORDER BY k.conname)
     FROM pg_constraint k
    WHERE k.conrelid = 'pratiche.pratiche_sorgenti'::regclass
      AND k.conname IN ('chk_pratiche_sorgenti_sorgente_forma', 'uq_pratiche_sorgenti_pratica_sorgente_ruolo')),
  'chk_pratiche_sorgenti_sorgente_forma=CHECK ((num_nonnulls(sorgente_id, sorgente_uid) = 1)) | '
  'uq_pratiche_sorgenti_pratica_sorgente_ruolo=UNIQUE NULLS NOT DISTINCT (pratica_id, sorgente_tipo_id, sorgente_id, sorgente_uid, ruolo_link)',
  '2) CHECK di forma e unicita'' per pratica e ruolo sulla chiave nuova, NULLS NOT DISTINCT');

-- ⚠️ Schema e nome da pg_proc + pg_namespace, non da regproc::text: il testo
--   dipende dal search_path di chi guarda (e un regproc di un nome che non
--   esiste e' un errore, non uno zero).
SELECT is(
  (SELECT concat_ws('|',
      (SELECT m.livello_minimo || '/' || m.azione_cancellazione
         FROM script.fn_sorgente_guard_montaggi() m
        WHERE m.schema_tabella = 'pratiche' AND m.nome_tabella = 'pratiche_sorgenti'),
      (SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'script' AND p.proname = 'trgfn_guard_sorgente_polimorfa_testuale'),
      (SELECT p.grammatica || '/' || coalesce(p.orfani_esclusi_perche, 'nessuna esenzione')
         FROM dbops.fn_sorgenti_orfane_perimetro() p
        WHERE p.schema_tabella = 'pratiche' AND p.nome_tabella = 'pratiche_sorgenti'))),
  'DOCUMENTO/BLOCCA|0|UNICO/nessuna esenzione',
  '3) guard unico (DOCUMENTO, BLOCCA); il guard testuale non esiste piu''; la tabella sta nel perimetro degli orfani');

SELECT is(
  (SELECT concat_ws('|',
      (SELECT pg_get_constraintdef(k.oid) FROM pg_constraint k
        WHERE k.conrelid = 'pratiche.reconcile_errori'::regclass AND k.conname = 'chk_reconcile_errori_sorgente_forma'),
      (SELECT count(*) FROM script.fn_sorgente_guard_montaggi() m
        WHERE m.schema_tabella = 'pratiche' AND m.nome_tabella = 'reconcile_errori'),
      (SELECT (p.orfani_esclusi_perche IS NOT NULL AND p.guard_esente_perche IS NOT NULL)::text
         FROM dbops.fn_sorgenti_orfane_perimetro() p
        WHERE p.schema_tabella = 'pratiche' AND p.nome_tabella = 'reconcile_errori'))),
  'CHECK ((num_nonnulls(sorgente_id, sorgente_uid) <= 1))|0|true',
  '4) il log: al piu'' una chiave, nessun guard, esenzione dichiarata (orfani e guard)');

SELECT is(
  (SELECT string_agg(n.nspname || '.' || p.proname || '(' || oidvectortypes(p.proargtypes) || ')', ' | ' ORDER BY p.proname)
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'pratiche'
      AND p.proname IN ('fn_pratica_del_documento', 'fn_stato_sorgente', 'fn_reconcile_sorgente')),
  'pratiche.fn_pratica_del_documento(bigint, bigint, uuid) | '
  'pratiche.fn_reconcile_sorgente(bigint, bigint, uuid) | '
  'pratiche.fn_stato_sorgente(bigint, bigint, uuid)',
  '5) una firma sola, sulle colonne del modello: la firma testuale non c''e'' piu''');

SELECT is(
  (SELECT encode(t.tgargs, 'escape')
     FROM pg_trigger t
    WHERE t.tgrelid = 'vendite.preventivi'::regclass
      AND t.tgname = 'trg_preventivi_z90_reconcile_proiezione_upd'),
  'PREVENTIVO\000',
  '6) il trigger del reconcile sul preventivo passa il codice del tipo, non il suo id');

-- ============================================================
-- Fixture: due preventivi con una riga e un ordine, sul billing account del
--   preventivo A; la pratica dal verbo, sul preventivo A
-- ============================================================
CREATE TEMP TABLE _pv AS
SELECT v.k, p.*
  FROM (VALUES ('A'), ('B')) v(k),
       LATERAL dbops.fn_pgtap_crea_preventivo_con_righe('ps sorgenti ' || v.k, 'DRAFT') p;

CREATE TEMP TABLE _or AS
SELECT o.* FROM dbops.fn_pgtap_crea_ordine('ps sorgenti ordine', 'DRAFT',
                                           (SELECT billing_account_id FROM _pv WHERE k = 'A')) o;

CREATE TEMP TABLE _t AS
SELECT (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA') AS t_ord,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')     AS t_prev;

-- tipo_prestazione attivo, non obsoleto e con definizione risolvibile, dal
-- catalogo di seed (come in vendite/test-fn-genera-pratica-da-preventivo-v1).
CREATE TEMP TABLE _tp AS
SELECT tp.id
  FROM pratiche.tipi_prestazione tp
 WHERE tp.attivo IS TRUE
   AND (tp.obsoleto_dal IS NULL OR tp.obsoleto_dal > script.fn_data_operativa())
   AND pratiche.fn_risolvi_definizione(tp.id, NULL) IS NOT NULL
 ORDER BY tp.id
 LIMIT 1;

CREATE TEMP TABLE _pr AS
SELECT g.pratica_id
  FROM vendite.fn_genera_pratica_da_preventivo(
         (SELECT preventivo_id FROM _pv WHERE k = 'A'), (SELECT id FROM _tp), NULL, 'pgTAP lotto P') g;

-- ============================================================
-- GLI SCRITTORI
-- ============================================================
SELECT is(
  (SELECT concat_ws('|', ps.sorgente_tipo_id = t.t_prev, ps.sorgente_uid = p.preventivo_uid,
                    ps.sorgente_id IS NULL, ps.ruolo_link)
     FROM pratiche.pratiche_sorgenti ps, _t t, _pv p
    WHERE ps.pratica_id = (SELECT pratica_id FROM _pr) AND p.k = 'A'),
  't|t|t|ROOT',
  '7) la pratica dal preventivo: il link ROOT tiene l''uid del preventivo in sorgente_uid');

-- Il link all'ordine, a mano: il tipo a chiave id, l'id in sorgente_id.
INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link)
SELECT (SELECT pratica_id FROM _pr), t.t_ord, o.ordine_id, 'COLLEGATO' FROM _t t, _or o;

-- ============================================================
-- LA PRATICA DEL DOCUMENTO
-- ============================================================
SELECT is(
  (SELECT concat_ws('|',
      (SELECT d.pratica_id || '/' || d.n_pratiche FROM pratiche.fn_pratica_del_documento(t.t_prev, p.preventivo_id, p.preventivo_uid) d),
      (SELECT d.pratica_id || '/' || d.n_pratiche FROM pratiche.fn_pratica_del_documento(t.t_prev, NULL, p.preventivo_uid) d),
      (SELECT d.pratica_id || '/' || d.n_pratiche FROM pratiche.fn_pratica_del_documento(t.t_ord, o.ordine_id, o.ordine_uid) d),
      (SELECT d.pratica_id || '/' || d.n_pratiche FROM pratiche.fn_pratica_del_documento(t.t_ord, o.ordine_id, NULL) d),
      (SELECT coalesce(d.pratica_id::text, 'nessuna') || '/' || d.n_pratiche FROM pratiche.fn_pratica_del_documento(t.t_ord, NULL, o.ordine_uid) d))
     FROM _t t, _pv p, _or o WHERE p.k = 'A'),
  (SELECT concat_ws('|', pratica_id || '/1', pratica_id || '/1', pratica_id || '/1', pratica_id || '/1', 'nessuna/0') FROM _pr),
  '8) con id e uid del documento, o con la sola chiave del modello: la pratica del link (l''uid non e'' la chiave dell''ordine)');

SELECT is(
  (SELECT concat_ws('|',
      (SELECT l.pratica_id || '/' || l.n_pratiche FROM vendite.vw_preventivi_lista l, _pv p WHERE p.k = 'A' AND l.id = p.preventivo_id),
      (SELECT l.pratica_id || '/' || l.n_pratiche FROM vendite.vw_ordini_lista l, _or o WHERE l.id = o.ordine_id),
      (SELECT coalesce(l.pratica_id::text, 'nessuna') || '/' || l.n_pratiche FROM vendite.vw_preventivi_lista l, _pv p WHERE p.k = 'B' AND l.id = p.preventivo_id))),
  (SELECT concat_ws('|', pratica_id || '/1', pratica_id || '/1', 'nessuna/0') FROM _pr),
  '9) le liste del preventivo e dell''ordine mostrano la pratica; il preventivo B non ne ha');

SELECT is(
  (SELECT string_agg(s.tipo_id || ':' || coalesce(s.pratica_id::text, 'nessuna'), ' | ' ORDER BY s.tipo_id)
     FROM _t t, _pv p, _or o,
          LATERAL vendite.fn_documento_lineage_sintesi(ARRAY[t.t_prev, t.t_ord], ARRAY[p.preventivo_uid::text, o.ordine_id::text]) s
    WHERE p.k = 'A'
      AND (s.tipo_id, s.uid) IN ((t.t_prev, p.preventivo_uid::text), (t.t_ord, o.ordine_id::text))),
  (SELECT string_agg(x.tipo || ':' || pr.pratica_id, ' | ' ORDER BY x.tipo)
     FROM _pr pr, (SELECT t_prev AS tipo FROM _t UNION ALL SELECT t_ord FROM _t) x),
  '10) la sintesi della lineage, dal seme testuale di preventivo e ordine: la pratica di tutti e due');

-- ============================================================
-- LO STATO DEL DOCUMENTO
-- ============================================================
SELECT is(
  (SELECT concat_ws('|',
      (SELECT d.risolto || '/' || (d.sorgente_uid = p.preventivo_uid) || '/' || (d.sorgente_id IS NULL)
         FROM pratiche.fn_stato_sorgente(t.t_prev, NULL, p.preventivo_uid) d),
      (SELECT d.risolto || '/' || (d.sorgente_id = o.ordine_id) || '/' || (d.sorgente_uid IS NULL)
         FROM pratiche.fn_stato_sorgente(t.t_ord, o.ordine_id, NULL) d),
      (SELECT d.risolto || '/' || (d.sorgente_id = o.ordine_id)
         FROM pratiche.fn_stato_sorgente(t.t_ord, o.ordine_id, o.ordine_uid) d))
     FROM _t t, _pv p, _or o WHERE p.k = 'A'),
  'true/true/true|true/true/true|true/true',
  '11) il preventivo per uid, l''ordine per id e con tutte e due le chiavi: risolti, la chiave nelle colonne del modello');

SELECT is(
  (SELECT d.risolto || '/' || d.stato_codice_interno || '/' || d.fase || '/' || (d.sorgente_id = 0)
     FROM _t t, LATERAL pratiche.fn_stato_sorgente(t.t_ord, 0, NULL) d),
  'false/UNKNOWN/APERTO/true',
  '12) un ordine che non c''e'': la sentinella UNKNOWN, con la chiave ricevuta');

SELECT is(
  pg_temp.esito(format('SELECT * FROM pratiche.fn_stato_sorgente(%s, NULL, NULL)', (SELECT t_ord FROM _t))),
  'E_STATO_SORGENTE_PARAM_INVALIDO',
  '13) senza chiave: rifiutato');

-- ============================================================
-- LE VISTE
-- ============================================================
SELECT is(
  (SELECT concat_ws('|', v.sorgente_tipo_id = t.t_prev, v.sorgente_uid = p.preventivo_uid, v.sorgente_id IS NULL,
                    v.ruolo_link, v.risolto)
     FROM script.vw_pratica_doc_sorgente v, _t t, _pv p
    WHERE v.pratica_id = (SELECT pratica_id FROM _pr) AND p.k = 'A'),
  't|t|t|ROOT|t',
  '14) vw_pratica_doc_sorgente: a pari risolto e vivo vince il ROOT (il preventivo), con la chiave tipizzata');

SELECT is(
  (SELECT concat_ws('|', count(*), bool_and(v.pratica_sorgente_id = ps.id), bool_and(v.ruolo_link = 'ROOT'))
     FROM vendite.vw_preventivi_pratiche v
     JOIN pratiche.pratiche_sorgenti ps ON ps.pratica_id = v.pratica_id AND ps.sorgente_uid = v.preventivo_uid
    WHERE v.pratica_id = (SELECT pratica_id FROM _pr)),
  '1|t|t',
  '15) vw_preventivi_pratiche: una riga per il link al preventivo, il suo id in pratica_sorgente_id');

-- ============================================================
-- IL GUARD UNICO (scritture a mano: i verbi non le producono)
-- ============================================================
SELECT is(
  pg_temp.esito(format(
    $q$INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_uid, ruolo_link)
       VALUES (%s, %s, %L, 'ROOT')$q$,
    (SELECT pratica_id FROM _pr), (SELECT t_ord FROM _t), (SELECT ordine_uid FROM _or))),
  'E_SORG_CHIAVE_NON_CONFORME',
  '16) l''uid dell''ordine in sorgente_uid: non e'' la chiave del suo tipo');

SELECT is(
  pg_temp.esito(format(
    $q$INSERT INTO pratiche.pratiche_sorgenti (pratica_id, sorgente_tipo_id, sorgente_id, ruolo_link)
       VALUES (%s, %s, %s, 'ROOT')$q$,
    (SELECT pratica_id FROM _pr), (SELECT t_ord FROM _t), (SELECT max(id) + 1000000 FROM vendite.ordini))),
  'E_SORG_NOT_FOUND',
  '17) un ordine che non c''e'': rifiutato');

SELECT is(
  pg_temp.esito(format(
    $q$UPDATE pratiche.pratiche_sorgenti SET sorgente_riga = %s WHERE pratica_id = %s AND ruolo_link = 'ROOT'$q$,
    (SELECT preventivo_riga_id FROM _pv WHERE k = 'A'), (SELECT pratica_id FROM _pr))),
  'PASSA',
  '18) la riga del preventivo sul suo link: passa (prima la riga non la verificava nessuno)');

SELECT is(
  pg_temp.esito(format(
    $q$UPDATE pratiche.pratiche_sorgenti SET sorgente_riga = %s WHERE pratica_id = %s AND ruolo_link = 'ROOT'$q$,
    (SELECT preventivo_riga_id FROM _pv WHERE k = 'B'), (SELECT pratica_id FROM _pr))),
  'E_SORG_RIGA_NON_DEL_DOCUMENTO',
  '19) la riga di un ALTRO preventivo: rifiutata');

-- ============================================================
-- LA CANCELLAZIONE (BLOCCA)
-- ============================================================
SELECT is(
  pg_temp.esito(format($q$DELETE FROM vendite.preventivi WHERE id = %s$q$, (SELECT preventivo_id FROM _pv WHERE k = 'A'))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '20) il preventivo collegato a una pratica non si cancella, anche in bozza');

-- ============================================================
-- IL RECONCILE
-- ============================================================
CREATE TEMP TABLE _log0 AS SELECT count(*) AS n FROM pratiche.reconcile_errori;

SELECT is(
  (SELECT concat_ws('|',
      pratiche.fn_reconcile_sorgente(t.t_prev, NULL, (SELECT preventivo_uid FROM _pv WHERE k = 'B')),
      pratiche.fn_reconcile_sorgente(t.t_prev, NULL, (SELECT preventivo_uid FROM _pv WHERE k = 'A')),
      (SELECT count(*) FROM pratiche.reconcile_errori) - (SELECT n FROM _log0))
     FROM _t t),
  '0|0|0',
  '21) il reconcile: senza aggancio 0; con la chiave del preventivo agganciato nessun milestone in attesa, nessun errore');

-- Un trigger montato con un codice che non e' un tipo: si registra, il cambio resta.
CREATE TEMP TABLE _doc_finto (id bigint, uid uuid, stato int);
INSERT INTO _doc_finto VALUES (1, gen_random_uuid(), 1);
CREATE TRIGGER trg_doc_finto_reconcile AFTER UPDATE OF stato ON _doc_finto
    FOR EACH ROW EXECUTE FUNCTION pratiche.trgfn_documento_reconcile_proiezione('PGTAP_NON_UN_TIPO');
UPDATE _doc_finto SET stato = 2;

SELECT is(
  (SELECT concat_ws('|', (SELECT stato FROM _doc_finto),
                    (SELECT r.errcode || '/' || (r.sorgente_tipo_id IS NULL) || '/' || num_nonnulls(r.sorgente_id, r.sorgente_uid)
                       FROM pratiche.reconcile_errori r
                      WHERE r.messaggio LIKE '%PGTAP_NON_UN_TIPO%'))),
  '2|E_SORG_CONF/true/0',
  '22) un codice che non e'' un tipo: riga E_SORG_CONF senza tipo e senza chiave, il cambio di stato resta');

SELECT is(
  pg_temp.esito(format(
    $q$INSERT INTO pratiche.reconcile_errori (sorgente_tipo_id, sorgente_id, sorgente_uid, errcode, messaggio)
       VALUES (%s, 1, %L, 'PGTAP', 'pgTAP')$q$,
    (SELECT t_ord FROM _t), gen_random_uuid())),
  '23514 chk_reconcile_errori_sorgente_forma',
  '23) il log rifiuta due chiavi del documento');

-- ============================================================
-- GLI ORFANI
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM dbops.vw_sorgenti_orfane o
    WHERE o.tabella = 'pratiche.pratiche_sorgenti'::regclass
      AND o.riga_id IN (SELECT ps.id FROM pratiche.pratiche_sorgenti ps WHERE ps.pratica_id = (SELECT pratica_id FROM _pr))),
  0,
  '24) il presidio degli orfani non vede i link del test, che citano documenti veri');

SELECT * FROM finish();
ROLLBACK;
