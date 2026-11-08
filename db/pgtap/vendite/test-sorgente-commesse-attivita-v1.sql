-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la RIGA DI COMMESSA (vendite.commesse_attivita) nella grammatica del
--   modello. La chiave del documento sta in sorgente_id (tipi a chiave id) o in
--   sorgente_uid uuid (tipi a chiave uid), la riga del documento in
--   sorgente_riga; la madre le scrive dal BB, il guard unico le valida, i lettori
--   le cercano con la regola d'incontro. La chiave del gruppo fatturabile resta
--   CODICE:<uid> anche per i tipi a chiave id, letta dalla chiave del push (D-6),
--   e un guard verifica che la chiave del push nomini il documento.
-- Brief: brief-db-sorgente-documento-e-riga §7.2 lotto C, giro C.3 (S-5)
-- ------------------------------------------------------------
-- Indice test (plan 22):
--   LA FORMA
--    1) sorgente_id bigint, sorgente_uid uuid, sorgente_riga bigint, tutte NULL ammesse
--    2) CHECK di forma al posto di quello della coppia; i tre indici «chi deriva da X»
--    3) guard unico (DOCUMENTO, BLOCCA); perimetro degli orfani UNICO
--    4) l'ordine dei BEFORE ROW: prima il guard unico, poi quello della chiave del push
--    5) una firma sola per madre, ritiro e chiudibilita', sulle colonne del modello
--   LA MADRE
--    6) la riga dell'ordine passato per uid in testo, come il push: sorgente_id, la riga, il link
--    7) la riga del preventivo: sorgente_uid uuid e la riga
--    8) la chiave del gruppo: l'UID anche per l'ordine (D-6), e il gruppo della vista
--    9) senza riga (il documento intero): passa
--   IL GUARD UNICO E QUELLO DELLA CHIAVE (scritture a mano)
--   10) la riga del preventivo citata da una riga dell'ordine: E_SORG_RIGA_NON_DEL_DOCUMENTO
--   11) un ordine che non c'e': E_SORG_NOT_FOUND (dalla madre)
--   12) la chiave del push col preventivo per una riga dell'ordine: E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO
--   13) una chiave fuori grammatica con la provenienza: E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO
--   14) un UPDATE della sola chiave verso un altro documento: rifiutato (UPDATE OF)
--   I LETTORI
--   15) chiudibilita': la riga EMESSA dell'ordine conta con id e uid, e col solo id
--   16) la lista: sorgente_uid e' l'uid del documento in testo, sorgente_documento_id l'id
--   17) legami dell'ordine: le righe di commessa NON_EMESSA
--   18) il ritiro: le NON_EMESSA dell'ordine col solo id; l'uid da solo non e' la chiave dell'ordine
--   IL BUILDER DELLE FIXTURE
--   19) senza sorgente: un consumo vero, sorgente_id, nessuna riga, la chiave del push dei consumi
--   20) la chiave del gruppo del consumo e' ATTIVITA_CONSUMI:<uid>
--   LA CANCELLAZIONE (BLOCCA)
--   21) il consumo citato da una riga di commessa non si cancella: E_SORG_ORIGINE_REFERENZIATA
--   GLI ORFANI
--   22) il presidio degli orfani non vede le righe del test
--
-- ⚠️ Il mondo si COSTRUISCE: preventivo, ordine e commessa dai builder
--   dbops.fn_pgtap_*, sullo stesso billing account (un solo emittente). Gira come
--   l'applicazione (operatore in sessione, RLS attiva). Le righe di commessa le
--   scrive la madre (dal builder); i casi rifiutati si scrivono a mano, perche' la
--   madre non li produce.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(22);

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
  (SELECT string_agg(a.attname || ':' || format_type(a.atttypid, a.atttypmod) || ':' || a.attnotnull, '|' ORDER BY a.attname)
     FROM pg_attribute a
    WHERE a.attrelid = 'vendite.commesse_attivita'::regclass
      AND a.attname IN ('sorgente_id', 'sorgente_uid', 'sorgente_riga') AND NOT a.attisdropped),
  'sorgente_id:bigint:false|sorgente_riga:bigint:false|sorgente_uid:uuid:false',
  '1) la chiave del documento in due colonne tipizzate, la riga in sorgente_riga');

-- ⚠️ Nomi da pg_class, non da regclass::text: il testo dipende dal search_path.
SELECT is(
  (SELECT concat_ws(' | ',
      (SELECT string_agg(k.conname || '=' || pg_get_constraintdef(k.oid), ' ; ' ORDER BY k.conname)
         FROM pg_constraint k
        WHERE k.conrelid = 'vendite.commesse_attivita'::regclass
          AND k.conname IN ('chk_commesse_attivita_sorgente_forma', 'chk_commesse_attivita_sorgente_pair')),
      (SELECT string_agg(c.relname, ',' ORDER BY c.relname)
         FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
        WHERE i.indrelid = 'vendite.commesse_attivita'::regclass
          AND c.relname LIKE 'ix_commesse_attivita_sorgente%'))),
  'chk_commesse_attivita_sorgente_forma=CHECK ((((sorgente_tipo_id IS NULL) AND (sorgente_id IS NULL) AND (sorgente_uid IS NULL) AND (sorgente_riga IS NULL)) OR ((sorgente_tipo_id IS NOT NULL) AND (num_nonnulls(sorgente_id, sorgente_uid) = 1))))'
  ' | ix_commesse_attivita_sorgente_id,ix_commesse_attivita_sorgente_riga,ix_commesse_attivita_sorgente_uid',
  '2) il CHECK di forma al posto di quello della coppia; i tre indici al posto di (sorgente_uid, competenza_mese)');

SELECT is(
  (SELECT concat_ws('|',
      (SELECT m.livello_minimo || '/' || m.azione_cancellazione
         FROM script.fn_sorgente_guard_montaggi() m
        WHERE m.schema_tabella = 'vendite' AND m.nome_tabella = 'commesse_attivita'),
      (SELECT p.grammatica || '/' || coalesce(p.orfani_esclusi_perche, 'nessuna esenzione')
         FROM dbops.fn_sorgenti_orfane_perimetro() p
        WHERE p.schema_tabella = 'vendite' AND p.nome_tabella = 'commesse_attivita'))),
  'DOCUMENTO/BLOCCA|UNICO/nessuna esenzione',
  '3) guard unico (DOCUMENTO, BLOCCA); la tabella sta nel perimetro degli orfani');

SELECT is(
  (SELECT string_agg(t.tgname || '(' || (SELECT string_agg(a.attname, ',' ORDER BY a.attname)
                                            FROM pg_attribute a
                                           WHERE a.attrelid = t.tgrelid AND a.attnum = ANY (t.tgattr)) || ')',
                     ' < ' ORDER BY t.tgname)
     FROM pg_trigger t
    WHERE t.tgrelid = 'vendite.commesse_attivita'::regclass
      AND t.tgname LIKE 'trg_commesse_attivita_a10_guard_sorgente%'),
  'trg_commesse_attivita_a10_guard_sorgente_ins_upd(sorgente_id,sorgente_riga,sorgente_tipo_id,sorgente_uid)'
  ' < trg_commesse_attivita_a10_guard_sorgente_segment_ins_upd(segment_key,sorgente_id,sorgente_tipo_id,sorgente_uid)',
  '4) prima il guard unico, poi quello della chiave del push');

-- ⚠️ Schema e firma da pg_namespace e oidvectortypes, non da regprocedure::text.
SELECT is(
  (SELECT string_agg(n.nspname || '.' || p.proname || '(' ||
                     CASE WHEN p.proname = 'fn_upsert_commessa_attivita'
                          THEN (SELECT string_agg(x, ', ') FROM unnest((string_to_array(oidvectortypes(p.proargtypes), ', '))[33:41]) x)
                          ELSE oidvectortypes(p.proargtypes) END || ')', ' | ' ORDER BY p.proname)
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (('vendite', 'fn_upsert_commessa_attivita'),
                                     ('vendite', 'fn_ritira_commessa_attivita_da_sorgente'),
                                     ('script',  'fn_check_sorgente_chiudibile'))),
  'script.fn_check_sorgente_chiudibile(bigint, bigint, uuid) | '
  'vendite.fn_ritira_commessa_attivita_da_sorgente(bigint, bigint, uuid, text, bigint) | '
  'vendite.fn_upsert_commessa_attivita(bigint, text, character varying, jsonb, bigint, bigint, bigint, bigint, bigint)',
  '5) una firma sola: ritiro e chiudibilita'' sulle colonne del modello; la madre con la riga in coda');

-- ============================================================
-- Fixture: un preventivo e un ordine con una riga e una commessa, sullo
--   stesso billing account (un emittente solo)
-- ============================================================
CREATE TEMP TABLE _pv AS
SELECT p.* FROM dbops.fn_pgtap_crea_preventivo_con_righe('ca sorgente prev', 'DRAFT') p;

CREATE TEMP TABLE _or AS
SELECT o.* FROM dbops.fn_pgtap_crea_ordine_con_righe('ca sorgente ordine', 'DRAFT',
                                                     (SELECT billing_account_id FROM _pv)) o;

CREATE TEMP TABLE _comm AS
SELECT c.* FROM dbops.fn_pgtap_crea_commessa('ca sorgente', NULL,
                                             (SELECT billing_account_id FROM _pv), false, false) c;

CREATE TEMP TABLE _t AS
SELECT (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ORDINE_VENDITA')   AS t_ord,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')       AS t_prev,
       (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'ATTIVITA_CONSUMI') AS t_cons;

-- ============================================================
-- LA MADRE (dal builder, che compone la chiave come il push)
-- ============================================================
CREATE TEMP TABLE _a AS
SELECT 'ORD'::text AS k, a.*
  FROM dbops.fn_pgtap_crea_commessa_attivita(
         p_commessa_id      => (SELECT commessa_id FROM _comm),
         p_sorgente_codice  => 'ORDINE_VENDITA',
         p_sorgente_chiave  => (SELECT ordine_uid::text FROM _or),
         p_sorgente_riga_id => (SELECT ordine_riga_id FROM _or)) a;
INSERT INTO _a
SELECT 'PREV', a.*
  FROM dbops.fn_pgtap_crea_commessa_attivita(
         p_commessa_id      => (SELECT commessa_id FROM _comm),
         p_sorgente_codice  => 'PREVENTIVO',
         p_sorgente_chiave  => (SELECT preventivo_uid::text FROM _pv),
         p_sorgente_riga_id => (SELECT preventivo_riga_id FROM _pv)) a;

CREATE FUNCTION pg_temp.att(p text) RETURNS bigint LANGUAGE sql STABLE AS
$fx$ SELECT attivita_id FROM _a WHERE k = p $fx$;

SELECT is(
  (SELECT concat_ws('|', ca.sorgente_tipo_id = t.t_ord, ca.sorgente_id = o.ordine_id, ca.sorgente_uid IS NULL,
                    ca.sorgente_riga = o.ordine_riga_id,
                    EXISTS (SELECT 1 FROM vendite.commesse_sorgenti cs
                             WHERE cs.commessa_id = ca.commessa_id AND cs.sorgente_tipo_id = t.t_ord
                               AND cs.sorgente_id = o.ordine_id))
     FROM vendite.commesse_attivita ca, _t t, _or o
    WHERE ca.id = pg_temp.att('ORD')),
  't|t|t|t|t',
  '6) la riga dell''ordine passato per uid in testo: l''id in sorgente_id, la riga in sorgente_riga, il link alla commessa');

SELECT is(
  (SELECT concat_ws('|', ca.sorgente_tipo_id = t.t_prev, ca.sorgente_uid = p.preventivo_uid, ca.sorgente_id IS NULL,
                    ca.sorgente_riga = p.preventivo_riga_id)
     FROM vendite.commesse_attivita ca, _t t, _pv p
    WHERE ca.id = pg_temp.att('PREV')),
  't|t|t|t',
  '7) la riga del preventivo: l''uid in sorgente_uid, la riga in sorgente_riga');

SELECT is(
  (SELECT string_agg(vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id)
                     || '=' || (e.gruppo_key IS NOT DISTINCT FROM
                                vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id)),
                     ' | ' ORDER BY ca.id)
     FROM vendite.commesse_attivita ca
     JOIN vendite.vw_commesse_attivita_emittibilita e ON e.commessa_attivita_id = ca.id
    WHERE ca.id IN (pg_temp.att('ORD'), pg_temp.att('PREV'))),
  (SELECT 'ORDINE_VENDITA:' || o.ordine_uid || '=true | PREVENTIVO:' || p.preventivo_uid || '=true' FROM _or o, _pv p),
  '8) la chiave del gruppo: l''uid del documento anche per l''ordine (D-6), la stessa nella vista di emittibilita''');

SELECT is(
  pg_temp.esito(format($q$SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
                           p_commessa_id => %s, p_sorgente_codice => 'ORDINE_VENDITA', p_sorgente_chiave => %L)$q$,
                       (SELECT commessa_id FROM _comm), (SELECT ordine_id::text FROM _or))),
  'PASSA',
  '9) senza riga, la provenienza e'' il documento intero: il livello DOCUMENTO la ammette');

-- ============================================================
-- I RIFIUTI (scritture a mano: la madre non le produce)
-- ============================================================
-- Una copia della riga dell'ordine, con le colonne della provenienza e la chiave date.
CREATE FUNCTION pg_temp.copia(p_seg text, p_tipo bigint, p_id bigint, p_uid uuid, p_riga bigint) RETURNS text
LANGUAGE sql AS $fx$
SELECT format(
  $q$INSERT INTO vendite.commesse_attivita (
       commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
       factor_to_base, competenza_mese, competenza_dal, competenza_al, prezzo_snapshot, prezzo_bloccato,
       pricing_mode, prezzo_da_riallineare, stato_approvazione, stato_emissione, tipo_movimento, meta,
       natura_doc_id, tipo_doc_fiscale_id, sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga)
     SELECT commessa_id, %L, articolo_id, istanza_utility_id, data_attivita, uom_id, quantita,
            factor_to_base, competenza_mese, competenza_dal, competenza_al, prezzo_snapshot, prezzo_bloccato,
            pricing_mode, prezzo_da_riallineare, stato_approvazione, stato_emissione, tipo_movimento, meta,
            natura_doc_id, tipo_doc_fiscale_id, %s, %s, %s, %s
       FROM vendite.commesse_attivita WHERE id = %s$q$,
  p_seg, p_tipo, coalesce(p_id::text, 'NULL'), coalesce(quote_literal(p_uid) || '::uuid', 'NULL'),
  coalesce(p_riga::text, 'NULL'), pg_temp.att('ORD'))
$fx$;

SELECT is(
  pg_temp.esito(pg_temp.copia(
    (SELECT script.fn_segment_key('ORDINE_VENDITA', o.ordine_uid::text, p.preventivo_riga_id) FROM _or o, _pv p),
    (SELECT t_ord FROM _t), (SELECT ordine_id FROM _or), NULL, (SELECT preventivo_riga_id FROM _pv))),
  'E_SORG_RIGA_NON_DEL_DOCUMENTO',
  '10) la riga del preventivo citata da una riga dell''ordine: rifiutata dal guard unico');

SELECT is(
  pg_temp.esito(format($q$SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(
                           p_commessa_id => %s, p_sorgente_codice => 'ORDINE_VENDITA', p_sorgente_chiave => %L)$q$,
                       (SELECT commessa_id FROM _comm), (SELECT (max(id) + 1000000)::text FROM vendite.ordini))),
  'E_SORG_NOT_FOUND',
  '11) un ordine che non c''e'': la madre lo rifiuta prima di scrivere');

SELECT is(
  pg_temp.esito(pg_temp.copia(
    (SELECT script.fn_segment_key('ORDINE_VENDITA', p.preventivo_uid::text, o.ordine_riga_id) || '#T12' FROM _or o, _pv p),
    (SELECT t_ord FROM _t), (SELECT ordine_id FROM _or), NULL, (SELECT ordine_riga_id FROM _or))),
  'E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO',
  '12) la chiave del push con l''uid del preventivo per una riga dell''ordine: il gruppo sarebbe sbagliato');

SELECT is(
  pg_temp.esito(pg_temp.copia('PGT-SEG-T13', (SELECT t_ord FROM _t), (SELECT ordine_id FROM _or), NULL,
                              (SELECT ordine_riga_id FROM _or))),
  'E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO',
  '13) una chiave fuori grammatica con la provenienza: il gruppo non si costruirebbe');

SELECT is(
  pg_temp.esito(format($q$UPDATE vendite.commesse_attivita SET segment_key = %L WHERE id = %s$q$,
                       (SELECT script.fn_segment_key('ORDINE_VENDITA', p.preventivo_uid::text, o.ordine_riga_id) || '#T14'
                          FROM _or o, _pv p),
                       pg_temp.att('ORD'))),
  'E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO',
  '14) un UPDATE della sola chiave verso un altro documento: rifiutato');

-- ============================================================
-- I LETTORI
-- ============================================================
-- La riga del caso 9 (l'ordine intero, passato per id) diventa EMESSA: stessa chiave
-- del push, quindi la madre aggiorna quella riga. L'ordine ha cosi' una riga
-- NON_EMESSA (con la riga) e una EMESSA (senza).
CREATE TEMP TABLE _em AS
SELECT a.* FROM dbops.fn_pgtap_crea_commessa_attivita(
         p_commessa_id      => (SELECT commessa_id FROM _comm),
         p_sorgente_codice  => 'ORDINE_VENDITA',
         p_sorgente_chiave  => (SELECT ordine_id::text FROM _or),
         p_stato_emissione  => 'EMESSA') a;

SELECT is(
  (SELECT concat_ws('|',
      (SELECT m ->> 'codice' || ':' || (m ->> 'quante')
         FROM jsonb_array_elements(script.fn_check_sorgente_chiudibile(t.t_ord, o.ordine_id, o.ordine_uid)) m),
      (SELECT m ->> 'quante'
         FROM jsonb_array_elements(script.fn_check_sorgente_chiudibile(t.t_ord, o.ordine_id, NULL)) m),
      jsonb_array_length(script.fn_check_sorgente_chiudibile(t.t_ord, NULL, o.ordine_uid)))
     FROM _t t, _or o),
  'E_SORGENTE_CON_RIGHE_EMESSE:1|1|0',
  '15) chiudibilita'': la riga EMESSA dell''ordine conta con id e uid e col solo id; l''uid da solo non e'' la chiave dell''ordine');

SELECT is(
  (SELECT concat_ws('|', l.sorgente_uid = o.ordine_uid::text, l.sorgente_documento_id = o.ordine_id,
                    l.gruppo_key = 'ORDINE_VENDITA:' || o.ordine_uid)
     FROM vendite.fn_list_commessa_attivita((SELECT commessa_id FROM _comm), p_limit => 1000) l, _or o
    WHERE l.id = pg_temp.att('ORD')),
  't|t|t',
  '16) la lista: sorgente_uid e'' l''uid del documento in testo, come prima; id e gruppo dal modello');

SELECT is(
  (SELECT string_agg(l.origine_riga_id::text, ',' ORDER BY l.origine_riga_id)
     FROM vendite.fn_documento_legami('ORDINE_VENDITA', (SELECT ordine_id FROM _or)) l
    WHERE l.origine = 'COMMESSA'),
  (SELECT string_agg(ca.id::text, ',' ORDER BY ca.id)
     FROM vendite.commesse_attivita ca, _t t, _or o
    WHERE ca.sorgente_tipo_id = t.t_ord AND ca.sorgente_id = o.ordine_id AND ca.stato_emissione = 'NON_EMESSA'),
  '17) legami dell''ordine: le sue righe di commessa NON_EMESSA, cercate per id');

SELECT is(
  (SELECT concat_ws('|',
      vendite.fn_ritira_commessa_attivita_da_sorgente(t.t_ord, NULL, o.ordine_uid, 'pgTAP C.3: l''uid non e'' la chiave'),
      vendite.fn_ritira_commessa_attivita_da_sorgente(t.t_ord, o.ordine_id, NULL, 'pgTAP C.3: ritiro'))
     FROM _t t, _or o),
  (SELECT concat_ws('|', 0, count(*))
     FROM vendite.commesse_attivita ca, _t t, _or o
    WHERE ca.sorgente_tipo_id = t.t_ord AND ca.sorgente_id = o.ordine_id AND ca.stato_emissione = 'NON_EMESSA'),
  '18) il ritiro: col solo id ritira le NON_EMESSA dell''ordine; l''uid da solo non ritira niente');

-- ============================================================
-- IL BUILDER DELLE FIXTURE
-- ============================================================
CREATE TEMP TABLE _b AS
SELECT a.* FROM dbops.fn_pgtap_crea_commessa_attivita((SELECT commessa_id FROM _comm)) a;

SELECT is(
  (SELECT concat_ws('|', ca.sorgente_tipo_id = t.t_cons, ca.sorgente_id = c.id, ca.sorgente_uid IS NULL,
                    ca.sorgente_riga IS NULL, ca.segment_key = 'ATTIVITA_CONSUMI:' || c.uid,
                    c.billing_account_id = (SELECT billing_account_id FROM _comm))
     FROM vendite.commesse_attivita ca
     JOIN vendite.attivita_consumi c ON c.id = ca.sorgente_id, _t t
    WHERE ca.id = (SELECT attivita_id FROM _b)),
  't|t|t|t|t|t',
  '19) senza sorgente, la riga nasce da un consumo vero del billing account: sorgente_id, nessuna riga, la chiave dei consumi');

SELECT is(
  (SELECT vendite.fn_gruppo_fatturabile_key_di_attivita(ca.sorgente_tipo_id, ca.segment_key, ca.commessa_id)
          = 'ATTIVITA_CONSUMI:' || c.uid
     FROM vendite.commesse_attivita ca JOIN vendite.attivita_consumi c ON c.id = ca.sorgente_id
    WHERE ca.id = (SELECT attivita_id FROM _b)),
  true,
  '20) la chiave del gruppo del consumo: ATTIVITA_CONSUMI:<uid>');

-- ============================================================
-- LA CANCELLAZIONE (BLOCCA)
-- ============================================================
SELECT is(
  pg_temp.esito(format('DELETE FROM vendite.attivita_consumi WHERE id = %s',
                       (SELECT ca.sorgente_id FROM vendite.commesse_attivita ca WHERE ca.id = (SELECT attivita_id FROM _b)))),
  'E_SORG_ORIGINE_REFERENZIATA',
  '21) il consumo citato da una riga di commessa non si cancella');

-- ============================================================
-- GLI ORFANI
-- ============================================================
SELECT is(
  (SELECT count(*)::integer FROM dbops.vw_sorgenti_orfane o
    WHERE o.tabella = 'vendite.commesse_attivita'::regclass
      AND o.riga_id IN (SELECT ca.id FROM vendite.commesse_attivita ca
                         WHERE ca.commessa_id = (SELECT commessa_id FROM _comm))),
  0,
  '22) il presidio degli orfani non vede le righe del test');

SELECT * FROM finish();
ROLLBACK;
