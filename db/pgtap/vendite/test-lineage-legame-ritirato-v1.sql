-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): ritirato pg_temp.lr_mk_ordine, copia della strada dell'ordine confermato definita e mai chiamata (con le colonne di tmp_lr_refs che solo lei leggeva, e due gia' senza lettori); nessun builder serve: l'ordine del caso C nasce dal push del preventivo, che e' il caso.
-- pgTAP test per Zero ERP
-- Test: il LEGAME di un arco della lineage, oltre allo stato del nodo
--   vendite.fn_documento_lineage_legami (il decoratore degli archi) e la colonna
--   is_legame_ritirato di vendite.fn_documento_lineage.
-- ChangeSet: 20261013-69, 20261013-70, 20261013-71 (la sintesi, D-15 di Tid)
-- Richiesta: R-17/R-18/R-19 del BE (collaudo 2026-10-13, PRV0000144): dal
--   preventivo annullato il pannello «Passaggi» indicava la commessa
--   PRONTA_FATTURAZIONE come se il preventivo ci fosse ancora.
-- ------------------------------------------------------------
-- Indice test (plan 18):
--  A — la forma
--   1) il decoratore esiste, SECURITY DEFINER con search_path; la lineage ha la
--      colonna in coda
--   2) ⭐ il censimento e' completo: ogni lettera di fn_documento_lineage_archi
--      ha il suo ramo nel decoratore (nessuna risposta NULL)
--  B — preventivo -> commessa (arco B), sul percorso reale (lister + madre)
--   3) due righe vive: legame vivo
--   4) una riga annullata, l'altra viva: ancora vivo
--   5) ⭐ il preventivo annullato (il verbo, che ritira la riga rimasta): legame
--      RITIRATO, e la commessa resta viva (to_is_abortito false) — il caso del
--      collaudo
--   6) la stessa risposta dal nodo commessa, all'indietro: e' del legame
--   7) una riga EMESSA e l'altra annullata: vivo (li' il preventivo e' fatturato)
--   8) commessa annullata: ritirato, insieme a to_is_abortito
--  C — preventivo -> ordine (arco A)
--   9) dopo il push: vivo
--  10) l'ordine in bozza perde la riga venuta dal preventivo: ritirato, e
--      l'ordine resta vivo
--  D — gli archi senza ritiro con i nodi vivi
--  11) C, D, G, N, S, T rispondono false
--  12) una lettera non censita risponde NULL («non so»), non false
--  E — la colonna non cambia il resto
--  13) la lineage di un preventivo senza commessa ha la colonna valorizzata solo
--      sugli archi che ha
--  14) il pannello senza legami ritirati: nessuna riga con la colonna NULL
--  F — la sintesi (D-15: un legame ritirato non e' destinazione ne' sorgente)
--  15) ⭐ il preventivo ritirato dalla commessa: frontiera e' lui stesso, nessun
--      discendente, non transitato — prima la frontiera era la commessa viva
--  16) la commessa dal lato suo: la sorgente ritirata non conta, nessuna radice
--  17) il legame vivo (riga EMESSA) resta: frontiera la commessa, un discendente
--  18) il preventivo il cui ordine ha perso le sue righe: non transitato
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO: la forma di test-annullo-commessa-v1 (cliente,
--   articoli, preventivi, commesse dai builder e dalla madre
--   vendite.fn_get_or_create_commessa; righe di commessa dal lister e dalla madre
--   delle righe, come l'orchestratore). Nessun documento preso dai dati.
-- ------------------------------------------------------------
BEGIN;
-- ⚠️ Vincoli DIFFERITI: qui il COMMIT non arriva mai, e senza IMMEDIATE non
--   verrebbero esercitati.
SET CONSTRAINTS ALL IMMEDIATE;

-- Il test gira come l'applicazione (OPERATORE + RLS attiva).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SELECT plan(18);

-- ============================================================
-- A — La forma
-- ============================================================
SELECT ok(
  (SELECT p.prosecdef AND EXISTS (SELECT 1 FROM unnest(p.proconfig) c WHERE c LIKE 'search_path=%')
     FROM pg_proc p
    WHERE p.oid = to_regprocedure('vendite.fn_documento_lineage_legami(text[], bigint[], text[], bigint[], text[])'))
  AND (SELECT pg_get_function_result(p.oid) LIKE '%, is_legame_ritirato boolean)'
         FROM pg_proc p WHERE p.oid = to_regprocedure('vendite.fn_documento_lineage(bigint, text, text)')),
  '1) il decoratore esiste, SECURITY DEFINER con search_path; la lineage ha is_legame_ritirato in coda');

-- ⭐ Le lettere sono quelle che la grammatica degli archi scrive ('X'::text):
--    un arco nuovo senza il suo ramo qui risponderebbe NULL, e questo diventa rosso.
SELECT is(
  (SELECT string_agg(l.arco, ',' ORDER BY l.arco)
     FROM (SELECT DISTINCT m[1] AS arco
             FROM regexp_matches(pg_get_functiondef('vendite.fn_documento_lineage_archi(bigint[], text[])'::regprocedure),
                                 '''([A-Z])''::text', 'g') AS m) l
     JOIN vendite.fn_documento_lineage_legami(ARRAY[l.arco], ARRAY[0::bigint], ARRAY['0'],
                                              ARRAY[0::bigint], ARRAY['0']) g ON true
    WHERE g.is_legame_ritirato IS NOT NULL),
  -- rev 2026-10-31 (brief-modello-documento-vendita §18): V, la revisione
  --   dell'offerta (20261031-23), col suo ramo nel decoratore (20261031-24).
  'A,B,C,D,E,F,G,H,N,R,S,T,U,V',
  '2) il censimento e'' completo: le quattordici lettere di fn_documento_lineage_archi hanno tutte una risposta');

-- ============================================================
-- Fixture — COSTRUITE (la forma di test-annullo-commessa-v1)
-- ============================================================
CREATE TEMP TABLE tmp_lr_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'legame ritirato',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_lr_refs AS
SELECT
  c.billing_account_id, c.istanza_utility_id, c.utility_id,
  script.fn_pgtap_emittente_operatore()                                                   AS emittente_fiscale_id,
  -- La natura di riga la da' l'articolo: uno per strada, scelta alla nascita.
  dbops.fn_pgtap_crea_articolo('PGT-LR-MERCE', false,
    p_natura_vendita_id => (SELECT id FROM config.nature_vendita WHERE codice_interno = 'MERCE'))
                                                                                          AS art_merce_id,
  dbops.fn_pgtap_crea_articolo('PGT-LR-SERV', false,
    p_natura_vendita_id => (SELECT id FROM config.nature_vendita WHERE codice_interno = 'SERVIZIO_UNA_TANTUM'))
                                                                                          AS art_serv_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT s.id FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'DRAFT')       AS prev_draft_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo ORDER BY t.id LIMIT 1)       AS tipo_doc_fiscale_id
FROM tmp_lr_cli c;

CREATE TEMP TABLE tmp_lr_fix(chiave text PRIMARY KEY, id bigint);
CREATE TEMP TABLE tmp_lr_esito(caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

CREATE OR REPLACE FUNCTION pg_temp.lr_fix(p_chiave text) RETURNS bigint
  AS $$ SELECT id FROM tmp_lr_fix WHERE chiave = p_chiave $$ LANGUAGE sql;

-- Esegue un'istruzione e ne cattura l'esito (righe toccate, o SQLSTATE + frase).
CREATE OR REPLACE FUNCTION pg_temp.lr_prova(p_caso text, p_sql text)
RETURNS void AS $$
DECLARE v_n int;
BEGIN
  BEGIN
    EXECUTE p_sql;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO tmp_lr_esito VALUES (p_caso, NULL, NULL, v_n);
  EXCEPTION WHEN OTHERS THEN
    INSERT INTO tmp_lr_esito VALUES (p_caso, SQLSTATE, SQLERRM, NULL);
  END;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.lr_rifiuto(p_caso text, p_frammento text) RETURNS boolean AS $$
  SELECT COALESCE(e.sqlstate = 'P0001' AND e.messaggio LIKE '%' || p_frammento || '%', false)
    FROM tmp_lr_esito e WHERE e.caso = p_caso
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.lr_stato(p_tabella text, p_id bigint) RETURNS text AS $$
DECLARE v text;
BEGIN
  EXECUTE CASE p_tabella
            WHEN 'ordini'     THEN 'SELECT s.codice_interno FROM vendite.ordini t JOIN config.stati_doc_ordini s ON s.id = t.stato_doc_ordine_id WHERE t.id = $1'
            WHEN 'preventivi' THEN 'SELECT s.codice_interno FROM vendite.preventivi t JOIN config.stati_doc_preventivi s ON s.id = t.stato_doc_preventivo_id WHERE t.id = $1'
            WHEN 'commesse'   THEN 'SELECT s.codice_interno FROM vendite.commesse t JOIN vendite.stati_commessa s ON s.id = t.stato_commessa_id WHERE t.id = $1'
          END
     INTO v USING p_id;
  RETURN v;
END $$ LANGUAGE plpgsql;

-- Un preventivo con p_merce righe MERCE e p_serv righe di servizio, nato
-- DRAFT (le righe si scrivono in bozza) e portato ACCETTATO.
CREATE OR REPLACE FUNCTION pg_temp.lr_mk_preventivo(p_chiave text, p_merce int, p_serv int,
                                                    p_stato text DEFAULT 'ACCETTATO')
RETURNS void AS $$
DECLARE r RECORD; v_prev bigint; v_riga bigint; i int;
BEGIN
  SELECT * INTO r FROM tmp_lr_refs;
  INSERT INTO vendite.preventivi (rev, billing_account_id, istanza_utility_id, utility_id,
      validita_dal, validita_al, valuta_id, stato_doc_preventivo_id, data,
      fatturazione_immediata, storicizza, meta, emittente_fiscale_id)
  VALUES (0, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          script.fn_data_operativa(), script.fn_data_operativa() + 30, r.valuta_id, r.prev_draft_id,
          script.fn_data_operativa(), false, false,
          jsonb_build_object('test_scope', 'pgtap_legame_ritirato'), r.emittente_fiscale_id)
  RETURNING id INTO v_prev;
  INSERT INTO tmp_lr_fix VALUES (p_chiave || '_prev', v_prev);
  FOR i IN 1 .. p_merce LOOP
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
        iva_id, attivo, meta)
    VALUES (v_prev, r.art_merce_id, 4, 25, r.iva_id, true,
            jsonb_build_object('test_scope', 'pgtap_legame_ritirato'))
    RETURNING id INTO v_riga;
    INSERT INTO tmp_lr_fix VALUES (p_chiave || '_m' || i, v_riga);
  END LOOP;
  FOR i IN 1 .. p_serv LOOP
    INSERT INTO vendite.preventivi_righe (preventivo_id, articolo_id, qta_operativa, prezzo_unitario,
        iva_id, attivo, meta)
    VALUES (v_prev, r.art_serv_id, 2, 30, r.iva_id, true,
            jsonb_build_object('test_scope', 'pgtap_legame_ritirato'))
    RETURNING id INTO v_riga;
    INSERT INTO tmp_lr_fix VALUES (p_chiave || '_s' || i, v_riga);
  END LOOP;
  IF p_stato <> 'DRAFT' THEN
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.preventivi', v_prev, p_stato);
  END IF;
END $$ LANGUAGE plpgsql;

-- Una commessa nuova del cliente (come il push: fn_get_or_create_commessa).
CREATE OR REPLACE FUNCTION pg_temp.lr_mk_commessa(p_chiave text) RETURNS bigint AS $$
DECLARE r RECORD; v bigint;
BEGIN
  SELECT * INTO r FROM tmp_lr_refs;
  v := vendite.fn_get_or_create_commessa(
         p_billing_account_id     => r.billing_account_id,
         p_utility_id             => r.utility_id,
         p_tipo_commessa          => 'AUTO',
         p_policy_fatturazione    => 'DA_DOCUMENTO',
         p_fatturazione_immediata => false,
         p_priorita_operativa     => 'NORMALE',
         p_competenza_dal         => date_trunc('month', script.fn_data_operativa())::date,
         p_competenza_al          => (date_trunc('month', script.fn_data_operativa())
                                      + interval '1 month - 1 day')::date,
         p_meta                   => '{}'::jsonb,
         p_force_new              => true);
  INSERT INTO tmp_lr_fix VALUES (p_chiave, v);
  RETURN v;
END $$ LANGUAGE plpgsql;

-- L'invio in commessa come lo fa l'orchestratore: le righe del lister della
-- sorgente, scritte dalla madre delle righe. Ritorna gli id delle righe.
CREATE OR REPLACE FUNCTION pg_temp.lr_invia(p_sorgente text, p_id bigint, p_commessa bigint,
                                            p_righe bigint[] DEFAULT NULL)
RETURNS bigint[] AS $$
DECLARE v jsonb; v_ids bigint[] := ARRAY[]::bigint[]; v_id bigint;
BEGIN
  FOR v IN
    SELECT to_jsonb(x) FROM vendite.fn_list_preventivi_da_pushare(
             p_preventivo_id => p_id, p_righe_ids => p_righe) x
     WHERE p_sorgente = 'PREVENTIVO'
    UNION ALL
    SELECT to_jsonb(x) FROM vendite.fn_list_ordini_da_pushare(p_ordine_id => p_id) x
     WHERE p_sorgente = 'ORDINE'
  LOOP
    SELECT u.attivita_id INTO v_id
      FROM vendite.fn_upsert_commessa_attivita(
        p_commessa_id                   => p_commessa,
        p_segment_key                   => (v ->> 'segment_key')::varchar,
        p_articolo_id                   => (v ->> 'articolo_id')::uuid,
        p_istanza_utility_id            => (v ->> 'istanza_utility_id')::bigint,
        p_data_attivita                 => (v ->> 'data_attivita')::date,
        p_uom_id                        => (v ->> 'uom_id')::bigint,
        p_quantita                      => (v ->> 'quantita')::numeric,
        p_competenza_mese               => (v ->> 'competenza_mese')::date,
        p_competenza_dal                => (v ->> 'competenza_dal')::date,
        p_competenza_al                 => (v ->> 'competenza_al')::date,
        p_prezzo_snapshot               => (v ->> 'prezzo_snapshot')::numeric,
        p_prezzo_base_snapshot          => NULL,
        p_origine_prezzo                => NULL,
        p_tipo_variazione_applicata     => NULL,
        p_valore_variazione_applicata   => NULL,
        p_promo_id                      => NULL,
        p_contratto_id                  => NULL,
        p_categoria_cliente_id_snapshot => NULL,
        p_classe_utenza_id_snapshot     => NULL,
        p_qta_operativa                 => (v ->> 'qta_operativa')::numeric,
        p_uom_operativa_id              => (v ->> 'uom_operativa_id')::bigint,
        p_factor_to_base                => (v ->> 'factor_to_base')::numeric,
        p_tipo_doc_fiscale_id           => COALESCE((v ->> 'tipo_doc_fiscale_id')::bigint,
                                                    (SELECT tipo_doc_fiscale_id FROM tmp_lr_refs)),
        p_valuta_id                     => (v ->> 'valuta_id')::integer,
        p_prezzo_bloccato               => (v ->> 'prezzo_bloccato')::boolean,
        p_pricing_mode                  => (v ->> 'pricing_mode')::varchar,
        p_stato_approvazione            => 'BOZZA',
        p_stato_emissione               => 'NON_EMESSA',
        p_sorgente_tipo_id              => (v ->> 'sorgente_tipo_id')::bigint,
        p_sorgente_uid                  => v ->> 'sorgente_uid',
        p_tipo_movimento                => (v ->> 'tipo_movimento')::varchar,
        p_meta                          => v -> 'meta') u;
    v_ids := v_ids || v_id;
  END LOOP;
  RETURN v_ids;
END $$ LANGUAGE plpgsql;


-- Il legame dell'arco che parte dal (o arriva al) documento, dal pannello.
CREATE OR REPLACE FUNCTION pg_temp.lr_legame(p_sorgente text, p_uid text, p_direzione text, p_arco text)
RETURNS text AS $$
  SELECT string_agg(coalesce(l.is_legame_ritirato::text, 'NULL') || '/'
                    || coalesce(l.to_is_abortito::text, 'NULL'), ',' ORDER BY l.ordine)
    FROM vendite.fn_documento_lineage(
           (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = p_sorgente),
           p_uid, p_direzione) l
   WHERE l.arco = p_arco
$$ LANGUAGE sql;

CREATE OR REPLACE FUNCTION pg_temp.lr_uid_prev(p_chiave text) RETURNS text AS $$
  SELECT p.uid::text FROM vendite.preventivi p WHERE p.id = pg_temp.lr_fix(p_chiave)
$$ LANGUAGE sql;

-- ============================================================
-- B — preventivo -> commessa
-- ============================================================
SELECT pg_temp.lr_mk_preventivo('b', 0, 2);
SELECT pg_temp.lr_mk_commessa('b_cm');
INSERT INTO tmp_lr_fix
SELECT 'b_ca' || o.n, o.id
  FROM unnest(pg_temp.lr_invia('PREVENTIVO', pg_temp.lr_fix('b_prev'), pg_temp.lr_fix('b_cm')))
       WITH ORDINALITY AS o(id, n);

SELECT is(pg_temp.lr_legame('PREVENTIVO', pg_temp.lr_uid_prev('b_prev'), 'avanti', 'B'),
  'false/false',
  '3) due righe vive in commessa: legame vivo');

-- ⚠️ Una riga nata da un documento non si annulla col verbo delle righe manuali
--   (vendite.fn_annulla_commessa_attivita la rifiuta): il ritiro e' per sorgente,
--   tutte le righe insieme. Lo stato si scrive qui, come test-annullo-commessa-v1
--   scrive EMESSA: la colonna ammette righe di stati diversi, e la regola e' per riga.
UPDATE vendite.commesse_attivita SET stato_emissione = 'ANNULLATA' WHERE id = pg_temp.lr_fix('b_ca1');
SELECT is(pg_temp.lr_legame('PREVENTIVO', pg_temp.lr_uid_prev('b_prev'), 'avanti', 'B'),
  'false/false',
  '4) una riga annullata e l''altra viva: il legame e'' ancora vivo');

SELECT vendite.fn_annulla_preventivo(pg_temp.lr_fix('b_prev'), 1);
SELECT is(pg_temp.lr_legame('PREVENTIVO', pg_temp.lr_uid_prev('b_prev'), 'avanti', 'B')
          || ' | ' || pg_temp.lr_stato('preventivi', pg_temp.lr_fix('b_prev')),
  'true/false | ANNULLATO',
  '5) ⭐ preventivo annullato: legame RITIRATO, e la commessa resta viva (il caso del collaudo)');

SELECT is(pg_temp.lr_legame('COMMESSA', pg_temp.lr_fix('b_cm')::text, 'indietro', 'B'),
  'true/false',
  '6) dal nodo commessa, all''indietro, lo stesso legame: la colonna e'' dell''arco');

-- Una riga EMESSA (la forma di test-annullo-commessa-v1, test G) e l'altra annullata.
SELECT pg_temp.lr_mk_preventivo('e', 0, 2);
SELECT pg_temp.lr_mk_commessa('e_cm');
INSERT INTO tmp_lr_fix
SELECT 'e_ca' || o.n, o.id
  FROM unnest(pg_temp.lr_invia('PREVENTIVO', pg_temp.lr_fix('e_prev'), pg_temp.lr_fix('e_cm')))
       WITH ORDINALITY AS o(id, n);
UPDATE vendite.commesse_attivita SET stato_emissione = 'EMESSA' WHERE id = pg_temp.lr_fix('e_ca1');
UPDATE vendite.commesse_attivita SET stato_emissione = 'ANNULLATA' WHERE id = pg_temp.lr_fix('e_ca2');
SELECT is(pg_temp.lr_legame('PREVENTIVO', pg_temp.lr_uid_prev('e_prev'), 'avanti', 'B'),
  'false/false',
  '7) una riga EMESSA e l''altra annullata: vivo — li'' il preventivo e'' stato fatturato');

-- La commessa annullata col suo verbo.
SELECT pg_temp.lr_mk_preventivo('k', 0, 1);
SELECT pg_temp.lr_mk_commessa('k_cm');
SELECT pg_temp.lr_invia('PREVENTIVO', pg_temp.lr_fix('k_prev'), pg_temp.lr_fix('k_cm'));
SELECT vendite.fn_annulla_commessa(pg_temp.lr_fix('k_cm'), 1);
SELECT is(pg_temp.lr_legame('PREVENTIVO', pg_temp.lr_uid_prev('k_prev'), 'avanti', 'B'),
  'true/true',
  '8) commessa annullata: legame ritirato, insieme a to_is_abortito');

-- ============================================================
-- C — preventivo -> ordine
-- ============================================================
SELECT pg_temp.lr_mk_preventivo('a', 1, 0);
INSERT INTO tmp_lr_fix
SELECT 'a_ord', vendite.fn_push_preventivo_a_ordine(pg_temp.lr_fix('a_prev'));

SELECT is(pg_temp.lr_legame('PREVENTIVO', pg_temp.lr_uid_prev('a_prev'), 'avanti', 'A'),
  'false/false',
  '9) dopo il push: la riga d''ordine viene dal preventivo, legame vivo');

UPDATE vendite.ordini_righe SET attivo = false WHERE ordine_id = pg_temp.lr_fix('a_ord');
SELECT is(pg_temp.lr_legame('PREVENTIVO', pg_temp.lr_uid_prev('a_prev'), 'avanti', 'A')
          || ' | ' || pg_temp.lr_stato('ordini', pg_temp.lr_fix('a_ord')),
  'true/false | DRAFT',
  '10) l''ordine in bozza perde la riga venuta dal preventivo: ritirato, e l''ordine resta vivo');

-- ============================================================
-- D — gli archi senza ritiro con i nodi vivi, e la lettera ignota
-- ============================================================
SELECT is(
  (SELECT string_agg(g.arco || '=' || coalesce(g.is_legame_ritirato::text, 'NULL'), ',' ORDER BY g.arco)
     FROM vendite.fn_documento_lineage_legami(
            ARRAY['C','D','G','N','S','T'],
            ARRAY[0,0,0,0,0,0]::bigint[], ARRAY['0','0','0','0','0','0'],
            ARRAY[0,0,0,0,0,0]::bigint[], ARRAY['1','2','3','4','5','6']) g),
  'C=false,D=false,G=false,N=false,S=false,T=false',
  '11) legame solo di testata (C, D) o arco che nasce dalle righe di legame (G, N, S, T): false');

SELECT is(
  (SELECT coalesce(g.is_legame_ritirato::text, 'NULL')
     FROM vendite.fn_documento_lineage_legami(ARRAY['Z'], ARRAY[0::bigint], ARRAY['0'],
                                              ARRAY[0::bigint], ARRAY['0']) g),
  'NULL',
  '12) una lettera non censita risponde NULL: «non so», non «vivo»');

-- ============================================================
-- E — la colonna non cambia il resto
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.fn_documento_lineage(
            (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'PREVENTIVO'),
            pg_temp.lr_uid_prev('a_prev'), 'avanti') l),
  1,
  '13) il preventivo smistato a ordine ha un solo arco (A): la decorazione non aggiunge righe');

SELECT is(
  (SELECT count(*)::int FROM vendite.fn_documento_lineage(
            (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
            pg_temp.lr_fix('e_cm')::text, 'indietro') l
    WHERE l.is_legame_ritirato IS NULL),
  0,
  '14) all''indietro dalla commessa: nessun arco con la colonna NULL');

-- ============================================================
-- F — la sintesi
-- ============================================================
CREATE OR REPLACE FUNCTION pg_temp.lr_sintesi(p_sorgente text, p_uid text) RETURNS text AS $$
  SELECT (s.frontiera_uid IS NOT DISTINCT FROM s.uid)::text
         || '|' || s.n_discendenti_diretti || '|' || s.n_discendenti_attivi
         || '|' || s.is_transitato || '|' || s.n_sorgenti
         || '|' || coalesce(s.root_uid, 'NULL')
    FROM vendite.fn_documento_lineage_sintesi(
           ARRAY[(SELECT so.id FROM config.sorgenti so WHERE so.codice_interno = p_sorgente)],
           ARRAY[p_uid]) s
$$ LANGUAGE sql;

SELECT is(pg_temp.lr_sintesi('PREVENTIVO', pg_temp.lr_uid_prev('b_prev')),
  'true|0|0|false|0|NULL',
  '15) ⭐ preventivo ritirato: la frontiera e'' lui stesso, nessun discendente, non transitato');

SELECT is(pg_temp.lr_sintesi('COMMESSA', pg_temp.lr_fix('b_cm')::text),
  'true|0|0|false|0|NULL',
  '16) la commessa: la sorgente ritirata non conta, e non c''e'' radice');

SELECT is(pg_temp.lr_sintesi('PREVENTIVO', pg_temp.lr_uid_prev('e_prev')),
  'false|1|1|true|0|NULL',
  '17) il legame vivo (riga EMESSA) resta: frontiera la commessa, un discendente attivo');

SELECT is(split_part(pg_temp.lr_sintesi('PREVENTIVO', pg_temp.lr_uid_prev('a_prev')), '|', 4),
  'false',
  '18) il preventivo il cui ordine in bozza ha perso le sue righe non e'' transitato');

SELECT * FROM finish();
ROLLBACK;
