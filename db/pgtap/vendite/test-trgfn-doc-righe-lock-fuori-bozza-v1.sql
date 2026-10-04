-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: le righe di un documento si aggiungono, modificano e tolgono SOLO
--   finche' il documento e' in bozza — il building block
--   vendite.trgfn_doc_righe_lock_fuori_bozza e i suoi cinque adottanti (il reso dal 2026-09-29, l'offerta dal 2026-10-04)
--   (ddt_righe, ordini_righe sul solo DELETE, contratti_righe).
--   changeSet 20260922-01 … -06.
-- ------------------------------------------------------------
-- COSA PRESIDIA, e perche' non esisteva
--   D7 di brief-db-partita-merce-per-documento (letto dal catalogo il
--   21-09): vendite.ddt_righe.attivo non aveva NESSUN guard fuori da DRAFT.
--   I soli trigger su attivo erano i block_deact delle figlie (fulfillment,
--   resi, componenti, note), e una riga standalone gia' instradata alla
--   fatturazione non ne ha: il modello ammetteva di far sparire — o
--   cambiare — una riga di merce che un'attivita' di commessa dice
--   ALLOCATA o EMESSA. La regola «righe solo in bozza» viveva nella
--   capability (can_edit_righe) e nel backend (_STATI_RIGHE_MODIFICABILI),
--   e a DB in due copie parziali: il lock delle righe di contratto (solo
--   ATTIVO) e il ramo 1 del guard di cancellazione (solo DELETE). Il BB le
--   ritira e chiude le tre porte con una sola implementazione.
--
-- ⚠️ LE FIXTURE SI COSTRUISCONO. E qui c'e' una cosa in piu' rispetto al
--   gemello test-delete-righe-documento-bozza-v1: un documento «che nasce
--   fuori bozza» NON puo' piu' ricevere righe, perche' e' esattamente la
--   scorciatoia che il BB chiude. Il DDT emesso si fabbrica quindi nel verso
--   vero — DRAFT, righe, causale, indirizzo, transizione — con la ricetta di
--   test-fn-partite-merce-chiusura-v1 (fn_genera_ddt_da_ordine + tre UPDATE
--   di stato). Il cliente lo fabbricano i builder di dbops: su un database
--   da zero anagrafiche.* e' vuoto.
--
-- ⭐ IL CASO CHE DA' IL TITOLO (test 8): una riga di DDT consegnato, con
--   un'attivita' di commessa ALLOCATA sul suo segmento, e attivo = false.
--   Prima di questo giro passava.
--
-- ⚠️ I RIFIUTI SI CATTURANO (SQLSTATE + frase), non si accettano con un
--   throws_ok a P0001 nudo: cosi' si asserisce CHI ha rifiutato e con quale
--   verbo, e un guard che parlasse per primo con il motivo sbagliato (test
--   9) sarebbe rosso.
--
-- Indice test (1..21)
--   1) Forma: il BB esiste, plpgsql, non SECURITY DEFINER
--   2) Forma: i cinque trigger sono montati in fascia _a05_ con gli argomenti giusti
--   3) Forma: la copia dei contratti (funzione e trigger) non esiste piu'
--   4) Forma: trgfn_dlt_block_ordrig_ddtrig non nomina piu' il codice ritirato
--   5) Catalogo: i due codici nuovi con la classe giusta, il vecchio ritirato
--   6) DDT in bozza: INSERT, UPDATE e DELETE di riga PASSANO
--   7) DDT emesso: INSERT di riga -> E_RIGA_DOC_NON_BOZZA, verbo «aggiungere»
--   8) 🔴 DDT consegnato, riga ALLOCATA: attivo = false -> rifiutato, verbo «modificare»
--   9) DDT emesso, riga con fulfillment: DELETE -> E_RIGA_DOC_NON_BOZZA, non E_DELETE_BLOCKED_FUL (fascia _a05_)
--  10) DDT emesso: UPDATE di quantita' -> rifiutato
--  11) DDT in bozza: la testata si elimina e le righe la seguono (il cascade non e' fermato dal BB)
--  12) Ordine in bozza: DELETE di riga PASSA
--  13) Ordine confermato: DELETE di riga -> E_RIGA_DOC_NON_BOZZA, verbo «togliere»
--  14) Ordine confermato: UPDATE di riga PASSA (porta aperta di proposito: data_consegna_confermata)
--  15) Contratto in bozza: INSERT di riga PASSA
--  16) Contratto ATTIVO: INSERT -> rifiutato con «Contratto …»
--  17) Contratto ATTIVO: UPDATE e DELETE -> rifiutati
--  18) Contratto CESSATO: UPDATE di riga -> rifiutato (il caso che la copia lasciava aperto)
--  19) Montaggio senza argomenti -> E_DOC_RIGHE_LOCK_MONTAGGIO
--  20) Montaggio con colonna FK inesistente -> E_DOC_RIGHE_LOCK_MONTAGGIO
--  21) Stato bozza con codice diverso (TG_ARGV[2]): la riga passa in quello stato e non in DRAFT
-- ------------------------------------------------------------

BEGIN;
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;
SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(21);

-- ============================================================
-- 1-5) Forma e catalogo (girano sempre)
-- ============================================================

SELECT is(
  (SELECT l.lanname || '/' || CASE WHEN p.prosecdef THEN 'definer' ELSE 'invoker' END
     FROM pg_proc p
     JOIN pg_namespace n ON n.oid = p.pronamespace
     JOIN pg_language  l ON l.oid = p.prolang
    WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_doc_righe_lock_fuori_bozza'),
  'plpgsql/invoker',
  '1) vendite.trgfn_doc_righe_lock_fuori_bozza esiste, plpgsql, non SECURITY DEFINER');

-- ⭐ 2026-09-29: il quarto adottante, vendite.resi_righe (tre porte, tipo RESO),
--   da 20260929-01 (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-h): dal
--   Lotto 3-bis la conferma del reso carica la merce, e una riga cambiata dopo
--   farebbe divergere reso e registro. Il comportamento e' provato in
--   magazzino/test-reso-carico-v1 (test 25).
-- ⚠️ La fascia e' parte del contratto: con _a10_ il nome verrebbe DOPO
--   block_ddt_dlt e i block_deact, e l'operatore leggerebbe un rimedio che
--   non e' il rimedio (test 9).
SELECT is(
  (SELECT string_agg(t.tgrelid::regclass::text || ':' || t.tgname || ':' ||
                     substring(pg_get_triggerdef(t.oid) FROM 'EXECUTE FUNCTION .*$'),
                     E'\n' ORDER BY t.tgrelid::regclass::text)
     FROM pg_trigger t JOIN pg_proc p ON p.oid = t.tgfoid
    WHERE NOT t.tgisinternal AND p.proname = 'trgfn_doc_righe_lock_fuori_bozza'),
  $atteso$vendite.contratti_righe:trg_contratti_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt:EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('CONTRATTO', 'contratto_id')
vendite.ddt_righe:trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt:EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT', 'ddt_id')
vendite.offerte_commerciali_eccezioni:trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt:EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('OFFERTA', 'offerta_id', 'BOZZA')
vendite.ordini_righe:trg_ordini_righe_a05_doc_righe_lock_fuori_bozza_dlt:EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('ORDINE', 'ordine_id')
vendite.resi_righe:trg_resi_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt:EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('RESO', 'reso_id')$atteso$,
  '2) I cinque adottanti sono montati in fascia _a05_ con gli argomenti giusti');

SELECT is(
  (SELECT count(*)::int
     FROM (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_contratti_righe_lock_post_attivazione'
           UNION ALL
           SELECT 1 FROM pg_trigger
            WHERE tgrelid = 'vendite.contratti_righe'::regclass
              AND tgname = 'trg_contratti_righe_a10_lock_post_attivazione_ins_upd_dlt') AS x),
  0,
  '3) La copia dei contratti (funzione e trigger) non esiste piu''');

-- Il sorgente senza commenti: un presidio sul testo si accende sulla prosa
-- che lo spiega, e la prosa qui lo nomina apposta.
SELECT ok(
  (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') NOT LIKE '%E_DELETE_RIGA_DOC_NON_BOZZA%'
     FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite' AND p.proname = 'trgfn_dlt_block_ordrig_ddtrig'),
  '4) trgfn_dlt_block_ordrig_ddtrig non solleva piu'' E_DELETE_RIGA_DOC_NON_BOZZA (il ramo 1 e'' nel BB)');

SELECT is(
  (SELECT string_agg(c.codice || '=' || c.classe || '/' || COALESCE(c.obsoleto_dal::text, 'vivo'), ' ' ORDER BY c.codice)
     FROM config.codici_errore c
    WHERE c.codice IN ('E_RIGA_DOC_NON_BOZZA', 'E_DOC_RIGHE_LOCK_MONTAGGIO', 'E_DELETE_RIGA_DOC_NON_BOZZA')),
  'E_DELETE_RIGA_DOC_NON_BOZZA=CONFLITTO_STATO/2026-09-22 E_DOC_RIGHE_LOCK_MONTAGGIO=TECNICO/vivo E_RIGA_DOC_NON_BOZZA=CONFLITTO_STATO/vivo',
  '5) I due codici nuovi sono a catalogo con la classe giusta, e il vecchio e'' ritirato');

-- ============================================================
-- Fixture — COSTRUITE coi builder
-- ============================================================
CREATE TEMP TABLE tmp_cli_lr AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('pgtap_lock_righe');

CREATE TEMP TABLE tmp_refs_lr AS
SELECT
  c.billing_account_id,
  c.utility_id,
  c.istanza_utility_id,
  c.soggetto_ruolo_id,
  script.fn_pgtap_emittente_operatore()    AS emittente_fiscale_id,
  -- ⚠️ NON gestito a magazzino: il ciclo DDT non tocca il ledger.
  dbops.fn_pgtap_crea_articolo('PGT-LR-ART', false)                                                  AS articolo_id,
  -- Un secondo articolo per le righe di contratto aggiunte nei test: una sola AGGIUNTA per articolo.
  dbops.fn_pgtap_crea_articolo('PGT-LR-ART2', false)                                                 AS articolo2_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1)             AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                            AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)                        AS iva_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='DRAFT'      AND s.attivo ORDER BY s.id LIMIT 1) AS stato_ord_draft_id,
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='CONFERMATO' AND s.attivo ORDER BY s.id LIMIT 1) AS stato_ord_conf_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='DRAFT'      AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_draft_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO'     AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO'    AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo ORDER BY s.id LIMIT 1)    AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno='DRAFT'   ORDER BY s.id LIMIT 1)              AS stato_con_draft_id,
  (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno='ATTIVO'  ORDER BY s.id LIMIT 1)              AS stato_con_attivo_id,
  (SELECT s.id FROM config.stati_doc_contratti s WHERE s.codice_interno='CESSATO' ORDER BY s.id LIMIT 1)              AS stato_con_cessato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA' AND s.attivo ORDER BY s.id LIMIT 1)           AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                           AS tipo_doc_fiscale_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' ORDER BY c.id LIMIT 1)                        AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')                                                   AS tipo_ind_con_id
FROM tmp_cli_lr c;

CREATE TEMP TABLE tmp_fix(chiave text PRIMARY KEY, id bigint);
CREATE TEMP TABLE tmp_esito(caso text PRIMARY KEY, sqlstate text, messaggio text, righe int);

-- Un ordine (DRAFT o CONFERMATO) con una riga.
CREATE OR REPLACE FUNCTION pg_temp.lr_mk_ordine(p_stato_id bigint, p_qta numeric)
RETURNS TABLE(ordine_id bigint, ordine_riga_id bigint) AS $$
DECLARE r RECORD; v_ord bigint; v_orr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_lr;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, p_stato_id, r.valuta_id,
          DATE '2026-08-05', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_lock_righe'))
  RETURNING id INTO v_ord;
  -- ⚠️ La riga d'ordine entra anche su un ordine confermato: il BB sugli
  --   ordini e' montato sul solo DELETE (porta aperta di proposito).
  INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
    qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
  VALUES (v_ord, 1, r.articolo_id, 'Riga lock pgTAP', p_qta, p_qta, 20, r.iva_id,
          true, false, jsonb_build_object('test_scope','pgtap_lock_righe'))
  RETURNING id INTO v_orr;
  RETURN QUERY SELECT v_ord, v_orr;
END $$ LANGUAGE plpgsql;

-- Un DDT da ordine (nasce in DRAFT con la riga e il fulfillment), portato
-- allo stato chiesto nel verso vero: causale, indirizzo, transizioni.
CREATE OR REPLACE FUNCTION pg_temp.lr_mk_ddt_da_ordine(p_ordine_id bigint, p_ordine_riga_id bigint,
                                                       p_qta numeric, p_fino_a text)
RETURNS TABLE(ddt_id bigint, ddt_uid uuid, ddt_riga_id bigint) AS $$
DECLARE r RECORD; v_ddt bigint; v_uid uuid; v_ddtr bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_lr;
  v_ddt := vendite.fn_genera_ddt_da_ordine(
      p_ordine_id,
      jsonb_build_array(jsonb_build_object('ordine_riga_id', p_ordine_riga_id, 'qta_da_evadere', p_qta)),
      DATE '2026-08-10');
  IF p_fino_a <> 'DRAFT' THEN
    INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
    VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
    UPDATE vendite.ddt SET causale_trasporto_id = r.causale_vendita_id  WHERE id = v_ddt;
    UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_emesso_id WHERE id = v_ddt;
  END IF;
  IF p_fino_a IN ('SPEDITO', 'CONSEGNATO') THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id = r.stato_ddt_spedito_id WHERE id = v_ddt;
  END IF;
  IF p_fino_a = 'CONSEGNATO' THEN
    UPDATE vendite.ddt SET stato_doc_ddt_id = r.stato_ddt_consegnato_id WHERE id = v_ddt;
  END IF;
  SELECT d.uid INTO v_uid  FROM vendite.ddt d        WHERE d.id = v_ddt;
  SELECT dr.id INTO v_ddtr FROM vendite.ddt_righe dr WHERE dr.ddt_id = v_ddt ORDER BY dr.id LIMIT 1;
  RETURN QUERY SELECT v_ddt, v_uid, v_ddtr;
END $$ LANGUAGE plpgsql;

-- Un contratto con una riga AGGIUNTA, portato allo stato chiesto (DRAFT ->
-- ATTIVO -> CESSATO): la ricetta di test-contratti-step23-v1.
CREATE OR REPLACE FUNCTION pg_temp.lr_mk_contratto(p_numero text, p_fino_a text, p_anno int)
RETURNS TABLE(contratto_id bigint, contratto_riga_id bigint) AS $$
DECLARE r RECORD; v_con bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_lr;
  INSERT INTO vendite.contratti (numero, billing_account_id, istanza_utility_id, utility_id,
                                 stato_doc_contratto_id, valido_dal, valido_al, emittente_fiscale_id)
  VALUES (p_numero, r.billing_account_id, r.istanza_utility_id, r.utility_id,
          -- ⚠️ ex_contratti_no_overlap: stesso BA, validita' disgiunte per contratto.
          r.stato_con_draft_id, make_date(p_anno, 1, 1), make_date(p_anno, 12, 31), r.emittente_fiscale_id)
  RETURNING id INTO v_con;
  -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
  INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa, tipo_erogazione)
  VALUES (v_con, r.articolo_id, 'AGGIUNTA', 99.00, 1.00, 'CANONE')
  RETURNING id INTO v_riga;
  IF p_fino_a IN ('ATTIVO', 'CESSATO') THEN
    UPDATE vendite.contratti SET stato_doc_contratto_id = r.stato_con_attivo_id WHERE id = v_con;
  END IF;
  IF p_fino_a = 'CESSATO' THEN
    UPDATE vendite.contratti SET stato_doc_contratto_id = r.stato_con_cessato_id WHERE id = v_con;
  END IF;
  RETURN QUERY SELECT v_con, v_riga;
END $$ LANGUAGE plpgsql;

-- Esegue un'istruzione e ne cattura l'esito (righe toccate, o SQLSTATE + frase).
CREATE OR REPLACE FUNCTION pg_temp.lr_prova(p_caso text, p_sql text)
RETURNS void AS $$
DECLARE v_n int;
BEGIN
  BEGIN
    EXECUTE p_sql;
    GET DIAGNOSTICS v_n = ROW_COUNT;
    INSERT INTO tmp_esito VALUES (p_caso, NULL, NULL, v_n);
  EXCEPTION WHEN OTHERS THEN
    INSERT INTO tmp_esito VALUES (p_caso, SQLSTATE, SQLERRM, NULL);
  END;
END $$ LANGUAGE plpgsql;

-- Il verdetto atteso del BB: SQLSTATE di dominio, la frase, il verbo.
CREATE OR REPLACE FUNCTION pg_temp.lr_rifiuto(p_caso text, p_verbo text)
RETURNS boolean AS $$
  SELECT e.sqlstate = 'P0001'
     AND e.messaggio LIKE '%non e'' piu'' in bozza%'
     AND e.messaggio LIKE '%le sue righe si possono ' || p_verbo || ' solo finche''%'
    FROM tmp_esito e WHERE e.caso = p_caso
$$ LANGUAGE sql;

-- ── Il mondo ────────────────────────────────────────────────────
DO $fix$
DECLARE
  r RECORD; o RECORD; d RECORD; c RECORD;
  v_id bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_lr;

  -- DDT in bozza, standalone (test 6 e 11)
  INSERT INTO vendite.ddt (data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
                           billing_account_id, utility_id, valuta_id,
                           emittente_fiscale_id, storicizza, meta)
  VALUES (CURRENT_DATE, r.stato_ddt_draft_id, r.soggetto_ruolo_id, r.billing_account_id,
          r.utility_id, r.valuta_id, r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_lock_righe'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ddt_bozza', v_id);
  INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione,
                                 qta_operativa, quantita, storicizza, meta)
  VALUES (v_id, 1, r.articolo_id, 'riga in bozza', 1, 1, false,
          jsonb_build_object('test_scope','pgtap_lock_righe'))
  RETURNING id INTO v_id;
  INSERT INTO tmp_fix VALUES ('ddt_bozza_riga', v_id);

  -- DDT EMESSO da ordine, con fulfillment (test 7, 9, 10)
  SELECT * INTO o FROM pg_temp.lr_mk_ordine(r.stato_ord_conf_id, 5);
  SELECT * INTO d FROM pg_temp.lr_mk_ddt_da_ordine(o.ordine_id, o.ordine_riga_id, 5, 'EMESSO');
  INSERT INTO tmp_fix VALUES ('ddt_emesso', d.ddt_id), ('ddt_emesso_riga', d.ddt_riga_id);

  -- DDT CONSEGNATO da ordine, per il caso ALLOCATA (test 8)
  SELECT * INTO o FROM pg_temp.lr_mk_ordine(r.stato_ord_conf_id, 3);
  SELECT * INTO d FROM pg_temp.lr_mk_ddt_da_ordine(o.ordine_id, o.ordine_riga_id, 3, 'CONSEGNATO');
  INSERT INTO tmp_fix VALUES ('ddt_cons', d.ddt_id), ('ddt_cons_riga', d.ddt_riga_id);

  -- Ordine in bozza e ordine confermato (test 12-14)
  SELECT * INTO o FROM pg_temp.lr_mk_ordine(r.stato_ord_draft_id, 1);
  INSERT INTO tmp_fix VALUES ('ord_bozza_riga', o.ordine_riga_id);
  SELECT * INTO o FROM pg_temp.lr_mk_ordine(r.stato_ord_conf_id, 1);
  INSERT INTO tmp_fix VALUES ('ord_conf_riga', o.ordine_riga_id);

  -- Contratti: bozza, attivo, cessato (test 15-18)
  SELECT * INTO c FROM pg_temp.lr_mk_contratto('PGTAP_LR_DRAFT', 'DRAFT', 2070);
  INSERT INTO tmp_fix VALUES ('con_bozza', c.contratto_id);
  SELECT * INTO c FROM pg_temp.lr_mk_contratto('PGTAP_LR_ATTIVO', 'ATTIVO', 2071);
  INSERT INTO tmp_fix VALUES ('con_attivo', c.contratto_id), ('con_attivo_riga', c.contratto_riga_id);
  SELECT * INTO c FROM pg_temp.lr_mk_contratto('PGTAP_LR_CESSATO', 'CESSATO', 2072);
  INSERT INTO tmp_fix VALUES ('con_cessato_riga', c.contratto_riga_id);
END $fix$;

-- ── L'attivita' ALLOCATA sul segmento della riga consegnata (test 8) ──
-- La commessa e la sua ROOT, poi l'attivita' NON_EMESSA sul segmento
-- 'DDT:<uid>:R:<id>': e' cio' che fn_get_stato_push_segment legge come
-- ALLOCATA, cioe' «merce instradata a fatturazione».
CREATE TEMP TABLE tmp_com_lr AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_lr),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_lr),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-08-01',
  p_competenza_al          => DATE '2026-08-31',
  p_meta                   => jsonb_build_object('test_scope','pgtap_lock_righe'),
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_lr),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_lr),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_lr)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

CREATE TEMP TABLE tmp_seg_lr AS
SELECT ('DDT:' || d.uid::text || ':R:' || dr.id::text)::varchar AS segment_key
  FROM vendite.ddt d
  JOIN vendite.ddt_righe dr ON dr.ddt_id = d.id
 WHERE d.id = (SELECT id FROM tmp_fix WHERE chiave = 'ddt_cons');

SELECT vendite.fn_upsert_commessa_attivita(
    p_commessa_id => (SELECT commessa_id FROM tmp_com_lr),
    p_segment_key => (SELECT segment_key FROM tmp_seg_lr),
    p_articolo_id => r.articolo_id,
    p_istanza_utility_id => r.istanza_utility_id, p_data_attivita => DATE '2026-08-15',
    p_uom_id => r.uom_id, p_quantita => 3,
    p_competenza_mese => DATE '2026-08-01',
    p_competenza_dal => DATE '2026-08-01', p_competenza_al => DATE '2026-08-31',
    p_prezzo_snapshot => 20, p_prezzo_base_snapshot => NULL, p_origine_prezzo => NULL,
    p_tipo_variazione_applicata => NULL, p_valore_variazione_applicata => NULL,
    p_promo_id => NULL, p_contratto_id => NULL,
    p_categoria_cliente_id_snapshot => NULL, p_classe_utenza_id_snapshot => NULL,
    p_tipo_doc_fiscale_id => r.tipo_doc_fiscale_id, p_valuta_id => r.valuta_id,
    p_stato_approvazione => 'APPROVATA', p_stato_emissione => 'NON_EMESSA',
    p_tipo_movimento => 'NORMALE')
  FROM tmp_refs_lr r
 WHERE EXISTS (SELECT 1 FROM tmp_seg_lr);

-- ============================================================
-- Le prove, con l'esito catturato
-- ============================================================
SELECT pg_temp.lr_prova('6a_ins',
  format('INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, storicizza, meta) '
         'VALUES (%s, 2, %L, ''seconda riga in bozza'', 1, 1, false, ''{"test_scope":"pgtap_lock_righe"}'')',
         (SELECT id FROM tmp_fix WHERE chiave='ddt_bozza'), (SELECT articolo_id FROM tmp_refs_lr)))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_bozza');
SELECT pg_temp.lr_prova('6b_upd',
  format('UPDATE vendite.ddt_righe SET quantita = 2, qta_operativa = 2 WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ddt_bozza_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_bozza_riga');
SELECT pg_temp.lr_prova('6c_dlt',
  format('DELETE FROM vendite.ddt_righe WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ddt_bozza_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_bozza_riga');

SELECT pg_temp.lr_prova('7_emesso_ins',
  format('INSERT INTO vendite.ddt_righe (ddt_id, riga_nr, articolo_id, descrizione, qta_operativa, quantita, storicizza, meta) '
         'VALUES (%s, 9, %L, ''riga aggiunta a emesso'', 1, 1, false, ''{"test_scope":"pgtap_lock_righe"}'')',
         (SELECT id FROM tmp_fix WHERE chiave='ddt_emesso'), (SELECT articolo_id FROM tmp_refs_lr)))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_emesso');

SELECT pg_temp.lr_prova('8_cons_attivo_false',
  format('UPDATE vendite.ddt_righe SET attivo = false WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ddt_cons_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_cons_riga');

SELECT pg_temp.lr_prova('9_emesso_dlt_ful',
  format('DELETE FROM vendite.ddt_righe WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ddt_emesso_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_emesso_riga');

SELECT pg_temp.lr_prova('10_emesso_upd',
  format('UPDATE vendite.ddt_righe SET quantita = quantita + 1, qta_operativa = qta_operativa + 1 WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ddt_emesso_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_emesso_riga');

SELECT pg_temp.lr_prova('11_bozza_testata',
  format('DELETE FROM vendite.ddt WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ddt_bozza')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_bozza');

SELECT pg_temp.lr_prova('12_ord_bozza_dlt',
  format('DELETE FROM vendite.ordini_righe WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ord_bozza_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ord_bozza_riga');
SELECT pg_temp.lr_prova('13_ord_conf_dlt',
  format('DELETE FROM vendite.ordini_righe WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ord_conf_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ord_conf_riga');
SELECT pg_temp.lr_prova('14_ord_conf_upd',
  format('UPDATE vendite.ordini_righe SET descrizione = ''promessa di consegna'' WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='ord_conf_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ord_conf_riga');

-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
SELECT pg_temp.lr_prova('15_con_bozza_ins',
  format('INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa, tipo_erogazione) VALUES (%s, %L, ''AGGIUNTA'', 10, 1, ''CANONE'')',
         (SELECT id FROM tmp_fix WHERE chiave='con_bozza'), (SELECT articolo2_id FROM tmp_refs_lr)))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='con_bozza');
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate);
--   senza, il guard nuovo potrebbe parlare al posto del lock fuori bozza che qui si prova.
SELECT pg_temp.lr_prova('16_con_attivo_ins',
  format('INSERT INTO vendite.contratti_righe (contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa, tipo_erogazione) VALUES (%s, %L, ''AGGIUNTA'', 10, 1, ''CANONE'')',
         (SELECT id FROM tmp_fix WHERE chiave='con_attivo'), (SELECT articolo2_id FROM tmp_refs_lr)))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='con_attivo');
SELECT pg_temp.lr_prova('17a_con_attivo_upd',
  format('UPDATE vendite.contratti_righe SET ordine = 99 WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='con_attivo_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='con_attivo_riga');
SELECT pg_temp.lr_prova('17b_con_attivo_dlt',
  format('DELETE FROM vendite.contratti_righe WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='con_attivo_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='con_attivo_riga');
SELECT pg_temp.lr_prova('18_con_cessato_upd',
  format('UPDATE vendite.contratti_righe SET ordine = 99 WHERE id = %s', (SELECT id FROM tmp_fix WHERE chiave='con_cessato_riga')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='con_cessato_riga');

-- ── Montaggio (test 19-21): tabelle temporanee, il BB montato a mano ──
CREATE TEMP TABLE tmp_righe_senza_argv (id serial PRIMARY KEY, ddt_id bigint);
CREATE TRIGGER trg_tmp_a05_lock BEFORE INSERT ON tmp_righe_senza_argv
  FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT');
SELECT pg_temp.lr_prova('19_montaggio_argv', 'INSERT INTO tmp_righe_senza_argv (ddt_id) VALUES (1)');

CREATE TEMP TABLE tmp_righe_col_sbagliata (id serial PRIMARY KEY, ddt_id bigint);
CREATE TRIGGER trg_tmp_a05_lock BEFORE INSERT ON tmp_righe_col_sbagliata
  FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT', 'documento_id');
SELECT pg_temp.lr_prova('20_montaggio_col', 'INSERT INTO tmp_righe_col_sbagliata (ddt_id) VALUES (1)');

-- TG_ARGV[2]: lo stato «bozza» si chiama EMESSO per questa tabella finta ->
-- la riga del DDT emesso PASSA, quella del DDT in bozza NO.
CREATE TEMP TABLE tmp_righe_bozza_diversa (id serial PRIMARY KEY, ddt_id bigint);
CREATE TRIGGER trg_tmp_a05_lock BEFORE INSERT ON tmp_righe_bozza_diversa
  FOR EACH ROW EXECUTE FUNCTION vendite.trgfn_doc_righe_lock_fuori_bozza('DDT', 'ddt_id', 'EMESSO');
SELECT pg_temp.lr_prova('21a_argv2_emesso',
  format('INSERT INTO tmp_righe_bozza_diversa (ddt_id) VALUES (%s)', (SELECT id FROM tmp_fix WHERE chiave='ddt_emesso')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_emesso');
SELECT pg_temp.lr_prova('21b_argv2_cons',
  format('INSERT INTO tmp_righe_bozza_diversa (ddt_id) VALUES (%s)', (SELECT id FROM tmp_fix WHERE chiave='ddt_cons')))
 WHERE EXISTS (SELECT 1 FROM tmp_fix WHERE chiave='ddt_cons');

-- ============================================================
-- 6) DDT in bozza: le tre porte PASSANO
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '6a_ins')
    THEN skip('fixture DDT in bozza non costruita', 1)
  ELSE is(
    (SELECT string_agg(caso || '=' || COALESCE(righe::text, sqlstate || ' ' || messaggio), ' ' ORDER BY caso)
       FROM tmp_esito WHERE caso IN ('6a_ins', '6b_upd', '6c_dlt')),
    '6a_ins=1 6b_upd=1 6c_dlt=1',
    '6) DDT in bozza: INSERT, UPDATE e DELETE di riga passano')
END;

-- ============================================================
-- 7-10) DDT fuori bozza: le tre porte RIFIUTANO, e dicono il verbo
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '7_emesso_ins')
    THEN skip('fixture DDT emesso non costruita', 1)
  ELSE ok(pg_temp.lr_rifiuto('7_emesso_ins', 'aggiungere'),
    '7) DDT emesso: INSERT di riga -> E_RIGA_DOC_NON_BOZZA, verbo «aggiungere»')
END;

-- ⭐ Il caso di D7: merce instradata (ALLOCATA) e attivo = false.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '8_cons_attivo_false')
    THEN skip('fixture DDT consegnato non costruita', 1)
  ELSE ok(
    (SELECT script.fn_get_stato_push_segment(segment_key) FROM tmp_seg_lr) = 'ALLOCATA'
    AND pg_temp.lr_rifiuto('8_cons_attivo_false', 'modificare'),
    '8) DDT consegnato con riga ALLOCATA: attivo = false -> rifiutato, verbo «modificare» (D7)')
END;

-- La fascia _a05_: sul DELETE di una riga con fulfillment parla il BB, non
-- il traduttore dei legami (E_DELETE_BLOCKED_FUL).
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '9_emesso_dlt_ful')
    THEN skip('fixture DDT emesso non costruita', 1)
  ELSE ok(
    pg_temp.lr_rifiuto('9_emesso_dlt_ful', 'togliere')
    AND (SELECT messaggio NOT LIKE '%fulfillment%' FROM tmp_esito WHERE caso = '9_emesso_dlt_ful')
    AND EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f
                 WHERE f.ddt_riga_id = (SELECT id FROM tmp_fix WHERE chiave = 'ddt_emesso_riga')),
    '9) DDT emesso, riga con fulfillment: DELETE -> E_RIGA_DOC_NON_BOZZA prima di E_DELETE_BLOCKED_FUL (fascia _a05_)')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '10_emesso_upd')
    THEN skip('fixture DDT emesso non costruita', 1)
  ELSE ok(pg_temp.lr_rifiuto('10_emesso_upd', 'modificare'),
    '10) DDT emesso: UPDATE di quantita'' -> rifiutato')
END;

-- ============================================================
-- 11) Il cascade dalla testata in bozza non e' fermato dal BB
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '11_bozza_testata')
    THEN skip('fixture DDT in bozza non costruita', 1)
  ELSE is(
    (SELECT COALESCE(righe::text, sqlstate || ' ' || messaggio) FROM tmp_esito WHERE caso = '11_bozza_testata'),
    '1',
    '11) DDT in bozza: la testata si elimina e le righe la seguono (testata assente = cascade, si passa)')
END;

-- ============================================================
-- 12-14) Ordini: solo la porta del DELETE
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '12_ord_bozza_dlt')
    THEN skip('fixture ordine in bozza non costruita', 1)
  ELSE is((SELECT COALESCE(righe::text, sqlstate || ' ' || messaggio) FROM tmp_esito WHERE caso = '12_ord_bozza_dlt'), '1',
    '12) Ordine in bozza: DELETE di riga passa')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '13_ord_conf_dlt')
    THEN skip('fixture ordine confermato non costruita', 1)
  ELSE ok(pg_temp.lr_rifiuto('13_ord_conf_dlt', 'togliere') AND
          (SELECT messaggio LIKE 'Ordine %' FROM tmp_esito WHERE caso = '13_ord_conf_dlt'),
    '13) Ordine confermato: DELETE di riga -> E_RIGA_DOC_NON_BOZZA, verbo «togliere», etichetta «Ordine …»')
END;

-- ⚠️ Pinna una porta APERTA: se un giorno si allarga il trigger degli
--   ordini a INSERT/UPDATE (quando data_consegna_confermata avra' il suo
--   verbo), questo test diventa rosso e la scelta e' deliberata.
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '14_ord_conf_upd')
    THEN skip('fixture ordine confermato non costruita', 1)
  ELSE is((SELECT COALESCE(righe::text, sqlstate || ' ' || messaggio) FROM tmp_esito WHERE caso = '14_ord_conf_upd'), '1',
    '14) Ordine confermato: UPDATE di riga PASSA — porta aperta di proposito (PROJECT_CONTEXT, promessa di consegna)')
END;

-- ============================================================
-- 15-18) Contratti: il terzo adottante, e il caso che la copia lasciava aperto
-- ============================================================
SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '15_con_bozza_ins')
    THEN skip('fixture contratto in bozza non costruita', 1)
  ELSE is((SELECT COALESCE(righe::text, sqlstate || ' ' || messaggio) FROM tmp_esito WHERE caso = '15_con_bozza_ins'), '1',
    '15) Contratto in bozza: INSERT di riga passa')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '16_con_attivo_ins')
    THEN skip('fixture contratto attivo non costruita', 1)
  ELSE ok(pg_temp.lr_rifiuto('16_con_attivo_ins', 'aggiungere') AND
          (SELECT messaggio LIKE 'Contratto PGTAP_LR_ATTIVO %' FROM tmp_esito WHERE caso = '16_con_attivo_ins'),
    '16) Contratto ATTIVO: INSERT -> E_RIGA_DOC_NON_BOZZA, etichetta «Contratto <numero>»')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '17a_con_attivo_upd')
    THEN skip('fixture contratto attivo non costruita', 1)
  ELSE ok(pg_temp.lr_rifiuto('17a_con_attivo_upd', 'modificare') AND pg_temp.lr_rifiuto('17b_con_attivo_dlt', 'togliere'),
    '17) Contratto ATTIVO: UPDATE e DELETE di riga -> rifiutati')
END;

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '18_con_cessato_upd')
    THEN skip('fixture contratto cessato non costruita', 1)
  ELSE ok(pg_temp.lr_rifiuto('18_con_cessato_upd', 'modificare') AND
          (SELECT messaggio LIKE '%(stato CESSATO)%' FROM tmp_esito WHERE caso = '18_con_cessato_upd'),
    '18) Contratto CESSATO: UPDATE di riga -> rifiutato (la copia bloccava solo ATTIVO)')
END;

-- ============================================================
-- 19-21) Il montaggio
-- ============================================================
SELECT ok(
  (SELECT sqlstate = 'P0001' AND messaggio LIKE 'Trigger trg_tmp_a05_lock montato male su %tmp_righe_senza_argv: attesi:%'
     FROM tmp_esito WHERE caso = '19_montaggio_argv'),
  '19) Montaggio senza il secondo argomento -> E_DOC_RIGHE_LOCK_MONTAGGIO');

SELECT ok(
  (SELECT sqlstate = 'P0001' AND messaggio LIKE 'Trigger trg_tmp_a05_lock montato male su %: la colonna documento_id non esiste sulla riga%'
     FROM tmp_esito WHERE caso = '20_montaggio_col'),
  '20) Montaggio con una colonna FK che la riga non ha -> E_DOC_RIGHE_LOCK_MONTAGGIO');

SELECT CASE
  WHEN NOT EXISTS (SELECT 1 FROM tmp_esito WHERE caso = '21a_argv2_emesso')
    THEN skip('fixture DDT emesso/consegnato non costruita', 1)
  ELSE is(
    (SELECT string_agg(caso || '=' || COALESCE(righe::text, sqlstate), ' ' ORDER BY caso)
       FROM tmp_esito WHERE caso IN ('21a_argv2_emesso', '21b_argv2_cons')),
    '21a_argv2_emesso=1 21b_argv2_cons=P0001',
    '21) TG_ARGV[2] = EMESSO: passa sul DDT emesso, rifiuta sul consegnato (lo stato «bozza» e'' parametrico)')
END;

SELECT * FROM finish();

ROLLBACK;
