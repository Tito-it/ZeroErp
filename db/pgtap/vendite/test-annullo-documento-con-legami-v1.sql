-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-modello-documento-vendita §9, giro 7): il test 7 annullava l'ordine
--   con un UPDATE diretto dello stato, che ora la porta ferma (E_DOC_STATO_SOLO_DAL_VERBO).
--   Passa dal verbo di stato vendite.fn_cambia_stato_ordine (DRAFT -> ANNULLATO: nessuna
--   azione); il guard dell'annullo da' lo stesso rifiuto. Attesa invariata.
-- rev 2026-10-25 (brief-modello-documento-vendita §8, giro 6): il test 25
--   («23) il verbo di stato del preventivo…») chiama vendite.fn_cambia_stato_preventivo
--   con la firma nuova a DUE argomenti (id, stato): p_user e' uscito, user_update
--   lo scrive il trigger di audit. L'attesa non cambia: l'annullo della bozza
--   con un legame e' rifiutato dal guard dell'annullo (E_DOC_ANNULLO_CON_LEGAMI,
--   «Serve una conferma»); dalla bozza non serve l'azione emetti_preventivo.
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2b, 20261019-87 … -99):
--   l'ordine da offerta porta documento_origine_tipo = OFFERTA_COMMERCIALE, e il legame di
--   provenienza ha origine OFFERTA_COMMERCIALE (il codice della sorgente, era OFFERTA).
-- pgTAP test per Zero ERP
-- ⚠️ rev 2026-10-19 (brief-db-grammatica-unica-documenti, lotto 2a, 20261019-40 … -79):
--   il documento passato ai lettori delle testate, ai legami e ai montaggi del
--   lock e' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA,
--   OFFERTA_COMMERCIALE, RESO_VENDITA). Restano corti i prefissi delle chiavi
--   (G-8), l'origine dei legami (V7) e l'ambito degli indirizzi (G-6).
-- Test: annullare un documento con legami — si riapre l'origine, con conferma
--   vendite.fn_documento_legami, vendite.fn_documento_ritira_legami,
--   vendite.fn_doc_porta_ritiro_ammette, vendite.trgfn_doc_guard_annullo_con_legami,
--   i verbi vendite.fn_annulla_ordine / _preventivo / _contratto,
--   vendite.fn_offerta_documenti_vivi, vendite.trgfn_doc_snapshot_da_stato,
--   gli indici unici sui vivi (contratto e ordine da offerta), l'arco
--   EVASO -> ACCETTATO del preventivo.
-- ChangeSet: 20261011-68 … -91
-- Brief: brief-db-annullo-documento-con-legami (§7; D-1 … D-6)
-- ------------------------------------------------------------
-- Indice test (plan 30):
--  A — la forma
--   1) gli oggetti nuovi esistono e i quattro avvisi _m10_ sono montati
--   2) i ritirati non ci sono piu' (lettore della bolla, ritiro automatico
--      dalla commessa, snapshot del contratto); la Regola 4 non e' piu' nel guard
--   3) il codice nuovo e' a catalogo (CONFLITTO_STATO) e il vecchio e' obsoleto
--   4) l'arco EVASO -> ACCETTATO del preventivo c'e', non manuale
--   5) i due indici unici valgono sui soli vivi
--  B — caso 2: preventivo -> ordine (D-2)
--   6) il push: ordine in bozza, preventivo EVASO, un legame PREVENTIVO di consumo
--   7) l'annullo dal verbo di stato, senza la conferma dei legami, e' rifiutato: E_DOC_ANNULLO_CON_LEGAMI
--   8) il verbo con una conferma che non corrisponde: stesso rifiuto
--   9) confermato: ordine ANNULLATO, riga staccata, preventivo ACCETTATO, riga di nuovo smistabile
--  10) un secondo push dallo stesso preventivo riesce (il UNIQUE sulla riga regge)
--  11) ordine CONFERMATO: il verbo stacca la riga anche fuori bozza (la porta nel lock)
--  C — caso 3: offerta -> contratto (D-3, D-6)
--  12) il legame del contratto e' l'offerta, di PROVENIENZA
--  13) l'annullo diretto del contratto e' rifiutato
--  14) confermato: contratto ANNULLATO, offerta_id resta, snapshot abortito
--  15) l'offerta torna trasformabile: documenti vivi zero, capability accesa
--  16) un secondo push dalla stessa offerta crea il contratto
--  17) un terzo push e' rifiutato: c'e' un contratto vivo (E_OFFERTA_CONTRATTO_GIA_GENERATO)
--  D — caso 4: offerta -> ordine
--  18) un secondo ordine dalla stessa offerta, col primo vivo: unicita' violata
--  19) confermato l'annullo del primo: ANNULLATO, provenienza conservata
--  20) ora un ordine nuovo dalla stessa offerta entra
--  21) e la mutua esclusivita' regge: il push a contratto vede l'ordine vivo
--  E — caso 5: il ritiro dalla commessa (D-5)
--  22) il legame del preventivo e' la riga di commessa NON_EMESSA
--  23) il verbo di stato del preventivo (la strada del backend) e' rifiutato
--  24) confermato: preventivo ANNULLATO, riga ANNULLATA, registro col motivo
--  25) la riga di commessa di un altro documento non si tocca
--  F — lo snapshot di stato
--  26) uno snapshot scritto a mano si ricalcola
--  G — la porta senza il proprietario
--  27) ⚠️ GUC del ritiro accesa a mano: la riga d'ordine confermato non si
--      stacca. ROSSO DA OWNER, VERDE COME APP: da proprietario della tabella la
--      porta si apre per costruzione. Per ultimo.
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: cliente, listino, articolo, preventivi e
--   commessa dai builder; ordini e contratti dai push veri, o dall'INSERT del
--   backend (ordine da offerta). Nessun documento preso dai dati.
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: qui il COMMIT non arriva mai, e senza IMMEDIATE non
--   verrebbero esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

-- Il test gira come l'applicazione (OPERATORE + RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(30);

-- ============================================================
-- A — La forma
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE (n.nspname, p.proname) IN (('vendite', 'fn_documento_legami'),
                                     ('vendite', 'fn_documento_ritira_legami'),
                                     ('vendite', 'fn_doc_porta_ritiro_ammette'),
                                     ('vendite', 'trgfn_doc_guard_annullo_con_legami'),
                                     ('vendite', 'fn_offerta_documenti_vivi'),
                                     ('vendite', 'trgfn_doc_snapshot_da_stato'),
                                     ('vendite', 'fn_annulla_ddt'),
                                     ('vendite', 'fn_annulla_ordine'),
                                     ('vendite', 'fn_annulla_preventivo'),
                                     ('vendite', 'fn_annulla_contratto')))
  + (SELECT count(*)::int FROM pg_trigger t
      WHERE NOT t.tgisinternal
        AND (t.tgrelid, t.tgname) IN (
              ('vendite.ddt'::regclass,        'trg_ddt_m10_guard_annullo_con_legami_upd'),
              ('vendite.ordini'::regclass,     'trg_ordini_m10_guard_annullo_con_legami_upd'),
              ('vendite.preventivi'::regclass, 'trg_preventivi_m10_guard_annullo_con_legami_upd'),
              ('vendite.contratti'::regclass,  'trg_contratti_m10_guard_annullo_con_legami_upd'),
              ('vendite.ordini'::regclass,     'trg_ordini_z90_snapshot_da_stato_ins_upd'),
              ('vendite.contratti'::regclass,  'trg_contratti_z90_snapshot_da_stato_ins_upd'))),
  16,
  '1) le dieci funzioni esistono, i quattro avvisi _m10_ e i due snapshot di stato sono montati');

SELECT ok(
  NOT EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
               WHERE (n.nspname, p.proname) IN (('vendite', 'fn_ddt_legami'),
                                                ('vendite', 'trgfn_doc_ritira_commessa_attivita'),
                                                ('vendite', 'trgfn_contratti_sync_is_abortito_snapshot')))
  AND NOT EXISTS (SELECT 1 FROM pg_trigger t
                   WHERE NOT t.tgisinternal
                     AND t.tgname LIKE 'trg\_%\_z90\_ritira\_commessa\_attivita\_upd')
  -- la Regola 4 della bolla: il corpo senza commenti non solleva piu' il codice vecchio
  AND (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') NOT LIKE '%E_DDT_ANNULLO_CON_LEGAMI%'
         FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_ddt_guard_transizione'),
  '2) ritirati: il lettore della sola bolla, il ritiro automatico dalla commessa, lo snapshot del contratto, la Regola 4');

SELECT is(
  (SELECT string_agg(c.codice || '=' || c.classe || '/' || COALESCE(c.obsoleto_dal::text, '-'), ' ' ORDER BY c.codice)
     FROM config.codici_errore c
    WHERE c.codice IN ('E_DOC_ANNULLO_CON_LEGAMI', 'E_DDT_ANNULLO_CON_LEGAMI')),
  'E_DDT_ANNULLO_CON_LEGAMI=CONFLITTO_STATO/2026-10-11 E_DOC_ANNULLO_CON_LEGAMI=CONFLITTO_STATO/-',
  '3) E_DOC_ANNULLO_CON_LEGAMI a catalogo (CONFLITTO_STATO); E_DDT_ANNULLO_CON_LEGAMI obsoleto dal 2026-10-11');

SELECT ok(
  EXISTS (SELECT 1 FROM config.transizioni_stati_preventivi t
            JOIN config.stati_doc_preventivi da ON da.id = t.stato_da_id
            JOIN config.stati_doc_preventivi a  ON a.id  = t.stato_a_id
           WHERE da.codice_interno = 'EVASO' AND a.codice_interno = 'ACCETTATO'
             AND t.attivo AND (t.meta ->> 'manuale')::boolean IS FALSE),
  '4) l''arco EVASO -> ACCETTATO del preventivo c''e'', attivo e non manuale');

SELECT is(
  (SELECT count(*)::int FROM pg_indexes i
    WHERE i.schemaname = 'vendite'
      AND i.indexname IN ('uq_contratti_offerta_id', 'uq_ordini_v_documento_origine_offerta')
      AND i.indexdef LIKE 'CREATE UNIQUE INDEX%'
      AND i.indexdef LIKE '%NOT is_abortito_snapshot%'),
  2,
  '5) uq_contratti_offerta_id e uq_ordini_v_documento_origine_offerta sono unici sui soli vivi');

-- ============================================================
-- Fixture — COSTRUITE coi builder
-- ============================================================
-- Cliente su una utility senza tipi_utenze (niente guard tipo/classe sulla
-- fornitura dell'offerta), listino sulla stessa utility, articolo MERCE non
-- gestito a magazzino.
CREATE TEMP TABLE tmp_al_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'annullo con legami',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_al_listino AS
SELECT * FROM dbops.fn_pgtap_crea_listino((SELECT utility_id FROM tmp_al_cli), 'annullo con legami');

CREATE TEMP TABLE tmp_al_refs AS
SELECT
  c.billing_account_id, c.istanza_utility_id, c.utility_id, c.soggetto_ruolo_id,
  script.fn_pgtap_emittente_operatore()                                                   AS emittente_fiscale_id,
  script.fn_pgtap_emittente_sr_operatore()                                                AS emittente_sr_id,
  dbops.fn_pgtap_crea_articolo('PGT-AL-PIPPO', false)                                     AS articolo_id,
  -- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5):
  --   l'OVERRIDE dell'offerta modifica una riga del listino, quindi il suo
  --   articolo ci sta. Un articolo suo, per non cambiare tipologia a quello delle
  --   righe di preventivo e d'ordine; a listino subito sotto.
  dbops.fn_pgtap_crea_articolo('PGT-AL-OFFERTA', false)                                   AS articolo_off_id,
  (SELECT l.listino_id FROM tmp_al_listino l)                                             AS listino_id,
  (SELECT l.listino_versione_id FROM tmp_al_listino l)                                    AS listino_versione_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT')       AS prev_draft_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'DRAFT')           AS ord_draft_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno = 'ANNULLATO')       AS ord_annullato_id,
  (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno = 'ANNULLATO')    AS contr_annullato_id,
  (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'BOZZA')          AS off_bozza_id,
  (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'EMESSA')         AS off_emessa_id,
  (SELECT s.id FROM config.stati_doc_offerte s WHERE s.codice_interno = 'ACCETTATA')      AS off_accettata_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO')              AS sorg_preventivo_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo ORDER BY t.id LIMIT 1)       AS tipo_doc_fiscale_id
FROM tmp_al_cli c;

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM tmp_al_refs), ARRAY[(SELECT articolo_off_id FROM tmp_al_refs)]);

CREATE TEMP TABLE tmp_al_fix(chiave text PRIMARY KEY, id bigint);
CREATE TEMP TABLE tmp_al_esito(caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

CREATE OR REPLACE FUNCTION pg_temp.al_fix(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_al_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

-- Esegue un'istruzione e ne cattura l'esito (righe toccate, o SQLSTATE + frase).
CREATE OR REPLACE FUNCTION pg_temp.al_prova(p_caso text, p_sql text)
RETURNS void AS $$
DECLARE v_n int;
BEGIN
  BEGIN
    EXECUTE p_sql;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO tmp_al_esito VALUES (p_caso, NULL, NULL, v_n);
  EXCEPTION WHEN OTHERS THEN
    INSERT INTO tmp_al_esito VALUES (p_caso, SQLSTATE, SQLERRM, NULL);
  END;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.al_rifiuto(p_caso text, p_frammento text) RETURNS boolean AS $$
  SELECT COALESCE(e.sqlstate = 'P0001' AND e.messaggio LIKE '%' || p_frammento || '%', false)
    FROM tmp_al_esito e WHERE e.caso = p_caso
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.al_stato(p_tabella text, p_id bigint) RETURNS text AS $$
DECLARE v text;
BEGIN
  EXECUTE CASE p_tabella
            WHEN 'ordini'     THEN 'SELECT s.codice_interno FROM vendite.ordini t JOIN config.stati_doc_ordini s ON s.id = t.stato_doc_ordine_id WHERE t.id = $1'
            WHEN 'preventivi' THEN 'SELECT s.codice_interno FROM vendite.preventivi t JOIN config.stati_doc_preventivi s ON s.id = t.stato_doc_preventivo_id WHERE t.id = $1'
            WHEN 'contratti'  THEN 'SELECT s.codice_interno FROM vendite.contratti t JOIN config.stati_doc_contratti s ON s.id = t.stato_doc_contratto_id WHERE t.id = $1'
          END
     INTO v USING p_id;
  RETURN v;
END $$ LANGUAGE plpgsql;

-- Un preventivo con una riga MERCE, nato DRAFT e portato allo stato chiesto.
CREATE OR REPLACE FUNCTION pg_temp.al_mk_preventivo(p_chiave text, p_stato text)
RETURNS void AS $$
DECLARE r RECORD; v_prev bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_al_refs;
  INSERT INTO vendite.preventivi (rev, billing_account_id, istanza_utility_id, utility_id,
      validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
      fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  VALUES (0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          script.fn_data_operativa(), script.fn_data_operativa() + 30, r.valuta_id, r.prev_draft_id,
          script.fn_data_operativa(), false, false,
          jsonb_build_object('test_scope', 'pgtap_annullo_legami'), r.emittente_fiscale_id)
  RETURNING id INTO v_prev;
  INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
      iva_id, attivo, meta)
  VALUES (v_prev, r.articolo_id, 4, 25, r.iva_id, true,
          jsonb_build_object('test_scope', 'pgtap_annullo_legami'))
  RETURNING id INTO v_riga;
  IF p_stato <> 'DRAFT' THEN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_prev, p_stato);
  END IF;
  INSERT INTO tmp_al_fix VALUES (p_chiave || '_prev', v_prev), (p_chiave || '_prev_riga', v_riga);
END $$ LANGUAGE plpgsql;

-- Un'offerta ACCETTATA del listino, con una riga OVERRIDE e la sua fornitura
-- (righe e fornitura si scrivono in bozza, poi le transizioni).
CREATE OR REPLACE FUNCTION pg_temp.al_mk_offerta(p_chiave text, p_dal date)
RETURNS void AS $$
DECLARE r RECORD; v_off bigint;
BEGIN
  SELECT * INTO r FROM tmp_al_refs;
  INSERT INTO vendite.offerte_commerciali (emittente_fiscale_id, billing_account_id,
      istanza_utility_id, utility_id, listino_id, listino_versione_id,
      validita_dal, validita_al, stato_doc_offerta_id)
  VALUES (r.emittente_fiscale_id, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          r.listino_id, r.listino_versione_id, p_dal, p_dal + 364, r.off_bozza_id)
  RETURNING id INTO v_off;
  -- rev 2026-10-13 (Lotto 3b): l'articolo a listino prende la tipologia del
  --   listino, che dipende dalla utility: erogazione e fonte le eredita il DB.
  INSERT INTO vendite.offerte_commerciali_eccezioni (offerta_id, articolo_id, tipo_eccezione,
      tipo_erogazione, fonte_quantita_attesa, prezzo_unitario, attivo, qta_operativa)
  VALUES (v_off, r.articolo_off_id, 'OVERRIDE'::vendite.tipo_eccezione_contratto,
          NULL, NULL, 200, true,
          (SELECT 1.00 FROM vendite.fn_articolo_erogazioni(r.articolo_off_id) e
            WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1));
  INSERT INTO vendite.offerte_commerciali_utilities (offerta_id, istanza_utility_id, utility_id)
  VALUES (v_off, r.istanza_utility_id, r.utility_id);
  UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = r.off_emessa_id WHERE id = v_off;
  UPDATE vendite.offerte_commerciali SET stato_doc_offerta_id = r.off_accettata_id WHERE id = v_off;
  INSERT INTO tmp_al_fix VALUES (p_chiave || '_off', v_off);
END $$ LANGUAGE plpgsql;

-- L'ordine da offerta come lo scrive il backend (crea_ordine_da_offerta).
CREATE OR REPLACE FUNCTION pg_temp.al_ordine_da_offerta(p_offerta bigint) RETURNS bigint AS $$
DECLARE r RECORD; v_ord bigint;
BEGIN
  SELECT * INTO r FROM tmp_al_refs;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, emittente_fiscale_id,
      stato_doc_ordine_id, valuta_id, data, storicizza, documento_origine_tipo, documento_origine_id)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.emittente_fiscale_id, r.ord_draft_id,
          r.valuta_id, script.fn_data_operativa(), false, 'OFFERTA_COMMERCIALE', p_offerta)
  RETURNING id INTO v_ord;
  RETURN v_ord;
END $$ LANGUAGE plpgsql;

-- ============================================================
-- B — caso 2: preventivo -> ordine
-- ============================================================
SELECT pg_temp.al_mk_preventivo('b', 'ACCETTATO');
INSERT INTO tmp_al_fix
SELECT 'b1_ord', vendite.fn_push_preventivo_a_ordine(pg_temp.al_fix('b_prev'));

SELECT ok(
  pg_temp.al_stato('ordini', pg_temp.al_fix('b1_ord')) = 'DRAFT'
  AND pg_temp.al_stato('preventivi', pg_temp.al_fix('b_prev')) = 'EVASO'
  AND (SELECT count(*) = 1
            AND bool_and(l.origine = 'PREVENTIVO' AND l.natura = 'CONSUMO'
                         AND l.origine_id = pg_temp.al_fix('b_prev')
                         AND l.origine_riga_id = pg_temp.al_fix('b_prev_riga'))
         FROM vendite.fn_documento_legami('ORDINE_VENDITA', pg_temp.al_fix('b1_ord')) l),
  '6) il push: ordine in bozza, preventivo EVASO, un legame PREVENTIVO di consumo');

SELECT pg_temp.al_prova('7_ord_diretto',
  format($q$SELECT * FROM vendite.fn_cambia_stato_ordine(%s, 'ANNULLATO')$q$, pg_temp.al_fix('b1_ord')));
SELECT ok(pg_temp.al_rifiuto('7_ord_diretto', 'Serve una conferma'),
  '7) l''annullo dell''ordine dal verbo di stato, senza la conferma dei legami, e'' rifiutato: E_DOC_ANNULLO_CON_LEGAMI');

SELECT pg_temp.al_prova('8_ord_conferma_errata',
  format('SELECT vendite.fn_annulla_ordine(%s, 0)', pg_temp.al_fix('b1_ord')));
SELECT ok(pg_temp.al_rifiuto('8_ord_conferma_errata', 'Serve una conferma'),
  '8) il verbo con una conferma che non corrisponde: stesso rifiuto');

SELECT is(vendite.fn_annulla_ordine(pg_temp.al_fix('b1_ord'), 1), 1,
  '9a) confermato: il verbo restituisce il legame confermato');
SELECT ok(
  pg_temp.al_stato('ordini', pg_temp.al_fix('b1_ord')) = 'ANNULLATO'
  AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe orr
                   WHERE orr.ordine_id = pg_temp.al_fix('b1_ord') AND orr.preventivo_riga_id IS NOT NULL)
  AND pg_temp.al_stato('preventivi', pg_temp.al_fix('b_prev')) = 'ACCETTATO'
  AND EXISTS (SELECT 1 FROM vendite.vw_preventivi_righe_smistabili_ordine v
               WHERE v.id = pg_temp.al_fix('b_prev_riga')),
  '9) confermato: ordine ANNULLATO, riga staccata, preventivo ACCETTATO, riga di nuovo smistabile');

INSERT INTO tmp_al_fix
SELECT 'b2_ord', vendite.fn_push_preventivo_a_ordine(pg_temp.al_fix('b_prev'));
SELECT ok(
  pg_temp.al_stato('preventivi', pg_temp.al_fix('b_prev')) = 'EVASO'
  AND EXISTS (SELECT 1 FROM vendite.ordini_righe orr
               WHERE orr.ordine_id = pg_temp.al_fix('b2_ord')
                 AND orr.preventivo_riga_id = pg_temp.al_fix('b_prev_riga')),
  '10) un secondo push dallo stesso preventivo riesce, e lo riporta EVASO');

DO $b11$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', pg_temp.al_fix('b2_ord'), 'CONFERMATO');
  PERFORM vendite.fn_annulla_ordine(pg_temp.al_fix('b2_ord'), 1);
END $b11$;
SELECT ok(
  pg_temp.al_stato('ordini', pg_temp.al_fix('b2_ord')) = 'ANNULLATO'
  AND NOT EXISTS (SELECT 1 FROM vendite.ordini_righe orr
                   WHERE orr.ordine_id = pg_temp.al_fix('b2_ord') AND orr.preventivo_riga_id IS NOT NULL)
  AND pg_temp.al_stato('preventivi', pg_temp.al_fix('b_prev')) = 'ACCETTATO',
  '11) ordine CONFERMATO: il verbo stacca la riga anche fuori bozza, il preventivo torna ACCETTATO');

-- ============================================================
-- C — caso 3: offerta -> contratto
-- ============================================================
SELECT pg_temp.al_mk_offerta('c', DATE '2098-01-01');
INSERT INTO tmp_al_fix
SELECT 'c1_contr', vendite.fn_push_offerta_a_contratto(pg_temp.al_fix('c_off'), NULL::bigint);

SELECT ok(
  (SELECT count(*) = 1
          AND bool_and(l.origine = 'OFFERTA_COMMERCIALE' AND l.natura = 'PROVENIENZA'
                       AND l.origine_id = pg_temp.al_fix('c_off') AND l.riga_id IS NULL)
     FROM vendite.fn_documento_legami('CONTRATTO', pg_temp.al_fix('c1_contr')) l),
  '12) il legame del contratto e'' l''offerta da cui nasce, di PROVENIENZA');

SELECT pg_temp.al_prova('13_contr_diretto',
  format('UPDATE vendite.contratti SET stato_doc_contratto_id = %s WHERE id = %s',
         (SELECT contr_annullato_id FROM tmp_al_refs), pg_temp.al_fix('c1_contr')));
SELECT ok(pg_temp.al_rifiuto('13_contr_diretto', 'Serve una conferma'),
  '13) l''annullo diretto del contratto e'' rifiutato: E_DOC_ANNULLO_CON_LEGAMI');

SELECT vendite.fn_annulla_contratto(pg_temp.al_fix('c1_contr'), 1);
SELECT ok(
  (SELECT s.codice_interno = 'ANNULLATO' AND c.offerta_id = pg_temp.al_fix('c_off')
          AND c.is_abortito_snapshot AND NOT c.is_draft_snapshot
     FROM vendite.contratti c JOIN config.stati_doc_contratti s ON s.id = c.stato_doc_contratto_id
    WHERE c.id = pg_temp.al_fix('c1_contr')),
  '14) confermato: contratto ANNULLATO, offerta_id resta (provenienza), snapshot abortito');

SELECT ok(
  NOT EXISTS (SELECT 1 FROM vendite.fn_offerta_documenti_vivi(pg_temp.al_fix('c_off')))
  AND (script.fn_available_actions_offerta(pg_temp.al_fix('c_off')) ->> 'can_push_contratto')::boolean
  AND (script.fn_available_actions_offerta(pg_temp.al_fix('c_off')) ->> 'can_genera_ordine')::boolean,
  '15) l''offerta torna trasformabile: nessun documento vivo, push e genera ordine accesi');

INSERT INTO tmp_al_fix
SELECT 'c2_contr', vendite.fn_push_offerta_a_contratto(pg_temp.al_fix('c_off'), NULL::bigint);
SELECT ok(
  pg_temp.al_stato('contratti', pg_temp.al_fix('c2_contr')) = 'DRAFT'
  AND (SELECT array_agg(d.documento_id) = ARRAY[pg_temp.al_fix('c2_contr')]
         FROM vendite.fn_offerta_documenti_vivi(pg_temp.al_fix('c_off')) d),
  '16) un secondo push dalla stessa offerta crea il contratto: e'' l''unico vivo');

SELECT pg_temp.al_prova('17_terzo_push',
  format('SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)', pg_temp.al_fix('c_off')));
SELECT ok(pg_temp.al_rifiuto('17_terzo_push', ''),
  '17) un terzo push e'' rifiutato: c''e'' un contratto vivo (E_OFFERTA_CONTRATTO_GIA_GENERATO)');

-- ============================================================
-- D — caso 4: offerta -> ordine
-- ============================================================
SELECT pg_temp.al_mk_offerta('d', DATE '2099-01-01');
INSERT INTO tmp_al_fix SELECT 'd1_ord', pg_temp.al_ordine_da_offerta(pg_temp.al_fix('d_off'));

SELECT pg_temp.al_prova('18_secondo_ordine',
  format('SELECT pg_temp.al_ordine_da_offerta(%s)', pg_temp.al_fix('d_off')));
SELECT is((SELECT sqlstate FROM tmp_al_esito WHERE caso = '18_secondo_ordine'), '23505',
  '18) un secondo ordine dalla stessa offerta, col primo vivo: unicita'' violata');

SELECT is(vendite.fn_annulla_ordine(pg_temp.al_fix('d1_ord'), 1), 1,
  '19a) confermato l''annullo del primo ordine: un legame (l''offerta)');
SELECT ok(
  (SELECT s.codice_interno = 'ANNULLATO' AND o.is_abortito_snapshot
          AND o.documento_origine_tipo = 'OFFERTA_COMMERCIALE' AND o.documento_origine_id = pg_temp.al_fix('d_off')
     FROM vendite.ordini o JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
    WHERE o.id = pg_temp.al_fix('d1_ord')),
  '19) ANNULLATO, snapshot abortito, provenienza conservata');

INSERT INTO tmp_al_fix SELECT 'd2_ord', pg_temp.al_ordine_da_offerta(pg_temp.al_fix('d_off'));
SELECT ok(pg_temp.al_fix('d2_ord') IS NOT NULL,
  '20) ora un ordine nuovo dalla stessa offerta entra (unico sui vivi)');

SELECT pg_temp.al_prova('21_push_contratto',
  format('SELECT vendite.fn_push_offerta_a_contratto(%s, NULL::bigint)', pg_temp.al_fix('d_off')));
SELECT ok(pg_temp.al_rifiuto('21_push_contratto', ''),
  '21) la mutua esclusivita'' regge: il push a contratto vede l''ordine vivo (E_OFFERTA_ORDINE_GIA_GENERATO)');

-- ============================================================
-- E — caso 5: il ritiro dalla commessa
-- ============================================================
SELECT pg_temp.al_mk_preventivo('e', 'DRAFT');

-- Una commessa del mondo, e due righe NON_EMESSA: una spinta dal preventivo
-- (chiave sorgente = uid::text, come scrivono le fn_list_*_da_pushare), una
-- di un altro documento.
CREATE TEMP TABLE tmp_al_commessa AS
SELECT * FROM dbops.fn_pgtap_crea_commessa('annullo con legami');

DO $e$
DECLARE r RECORD; v_uid text; v_ca bigint; v_commessa bigint;
BEGIN
  SELECT * INTO r FROM tmp_al_refs;
  SELECT c.commessa_id INTO v_commessa FROM tmp_al_commessa c;
  SELECT p.uid::text INTO v_uid FROM vendite.preventivi p WHERE p.id = pg_temp.al_fix('e_prev');
  SELECT a.attivita_id INTO v_ca FROM dbops.fn_pgtap_crea_commessa_attivita(v_commessa) a;
  UPDATE vendite.commesse_attivita
     SET sorgente_tipo_id = r.sorg_preventivo_id, sorgente_uid = v_uid
   WHERE id = v_ca;
  INSERT INTO tmp_al_fix VALUES ('e_ca', v_ca);
  SELECT a.attivita_id INTO v_ca FROM dbops.fn_pgtap_crea_commessa_attivita(v_commessa) a;
  INSERT INTO tmp_al_fix VALUES ('e_ca_altra', v_ca);
END $e$;

SELECT ok(
  (SELECT count(*) = 1
          AND bool_and(l.origine = 'COMMESSA' AND l.natura = 'CONSUMO'
                       AND l.origine_riga_id = pg_temp.al_fix('e_ca'))
     FROM vendite.fn_documento_legami('PREVENTIVO', pg_temp.al_fix('e_prev')) l),
  '22) il legame del preventivo e'' la riga di commessa NON_EMESSA che ha spinto');

SELECT pg_temp.al_prova('23_prev_verbo_stato',
  format('SELECT * FROM vendite.fn_cambia_stato_preventivo(%s, ''ANNULLATO'')', pg_temp.al_fix('e_prev')));
SELECT ok(pg_temp.al_rifiuto('23_prev_verbo_stato', 'Serve una conferma'),
  '23) il verbo di stato del preventivo (la strada del backend) e'' rifiutato: niente ritiro silenzioso');

SELECT is(vendite.fn_annulla_preventivo(pg_temp.al_fix('e_prev'), 1), 1,
  '24a) confermato: il verbo restituisce il legame confermato');
SELECT ok(
  pg_temp.al_stato('preventivi', pg_temp.al_fix('e_prev')) = 'ANNULLATO'
  AND (SELECT ca.stato_emissione = 'ANNULLATA' FROM vendite.commesse_attivita ca
        WHERE ca.id = pg_temp.al_fix('e_ca'))
  AND EXISTS (SELECT 1 FROM vendite.commesse_attivita_log l
               WHERE l.commessa_attivita_id = pg_temp.al_fix('e_ca')
                 AND l.evento = 'RIGA_RITIRATA_DA_SORGENTE'
                 AND l.dettaglio ->> 'motivo' LIKE 'Ritiro all''annullo confermato%'),
  '24) confermato: preventivo ANNULLATO, riga di commessa ANNULLATA, registro col motivo');

SELECT is(
  (SELECT ca.stato_emissione FROM vendite.commesse_attivita ca WHERE ca.id = pg_temp.al_fix('e_ca_altra')),
  'NON_EMESSA'::character varying,
  '25) la riga di commessa di un altro documento non si tocca');

-- ============================================================
-- F — lo snapshot di stato non si scrive a mano
-- ============================================================
UPDATE vendite.contratti SET is_abortito_snapshot = false WHERE id = pg_temp.al_fix('c1_contr');
SELECT ok(
  (SELECT c.is_abortito_snapshot FROM vendite.contratti c WHERE c.id = pg_temp.al_fix('c1_contr')),
  '26) uno snapshot di stato scritto a mano si ricalcola dallo stato (contratto annullato resta abortito)');

-- ============================================================
-- G — 27) ⚠️ La porta senza il proprietario. ROSSO DA OWNER, VERDE COME APP.
-- ============================================================
INSERT INTO tmp_al_fix
SELECT 'b3_ord', vendite.fn_push_preventivo_a_ordine(pg_temp.al_fix('b_prev'));
DO $g$ BEGIN
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', pg_temp.al_fix('b3_ord'), 'CONFERMATO');
END $g$;
SELECT set_config('zeroerp.doc_ritira_legami', 'ORDINE_VENDITA:' || pg_temp.al_fix('b3_ord'), true);
SELECT pg_temp.al_prova('27_porta_a_mano',
  format('UPDATE vendite.ordini_righe SET preventivo_riga_id = NULL WHERE ordine_id = %s',
         pg_temp.al_fix('b3_ord')));
SELECT set_config('zeroerp.doc_ritira_legami', '', true);
SELECT ok((SELECT COALESCE(sqlstate = 'P0001', false) FROM tmp_al_esito WHERE caso = '27_porta_a_mano'),
  '27) la GUC del ritiro accesa a mano non stacca la riga di un ordine confermato: serve il proprietario');

SELECT * FROM finish();
ROLLBACK;
