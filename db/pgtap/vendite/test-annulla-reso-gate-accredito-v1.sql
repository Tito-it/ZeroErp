-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_annulla_reso — la guardia dell'accredito
--       (E_RESO_ANNULLO_CON_ACCREDITO, changeset 20260819-22)
-- ------------------------------------------------------------
-- ⛔ Prima di 20260819-22 questo file e' ROSSO su 4 test, ed e' il difetto che
--    misura. Corsa del 2026-08-19 senza il changeset (PGTAP_RUNNER=app):
--      1      verde  (la fixture regge: reso confermato, riga in coda)
--      2      have OK, want P0001|E_RESO_ANNULLO_CON_ACCREDITO  <- ⭐ il difetto
--             in due parole: l'annullo RIESCE
--      3      have 1|ANNULLATO, want 1|CONFERMATO  <- conseguenza del 2: il
--             reso e' gia' annullato, con il ponte ancora intero dietro. E'
--             esattamente lo stato che fa uscire una nota di credito per un
--             reso annullato
--      4      died E_RESO_STATO_NON_ANNULLABILE  <- non e' un difetto suo: il
--             reso l'ha gia' annullato il test 2
--      5,6,7  verdi
--      8      have OK, want P0001|...  <- il gemello del 2 sul reso a due righe
--    Con il changeset applicato: 8/8.
--
-- ⛔ E per i test 9..11 (capability, changeset 20260820-12) la corsa «prima» e'
--    10/11, NON 8/11 — misurata il 2026-08-20, e vale la pena scriverlo:
--      9   have true|?|?, want false|RESO_CON_ACCREDITI|...  <- ⭐ l'UNICO che
--          misura il difetto: senza il changeset il bottone e' acceso e muto
--      10  VERDE anche senza  <- l'azione era gia' nell'elenco e
--          can_change_state gia' true: e' un'INVARIANTE, non una misura
--      11  VERDE anche senza  <- senza accredito enabled e' true comunque
--    ⚠️ Non e' un difetto dei test 10 e 11: sono invarianti che devono reggere
--    PRIMA e DOPO, ed e' il loro mestiere accorgersi di una regressione futura
--    (l'azione che sparisce dall'elenco, la capability che non si riabilita).
--    Ma chi legge «tre test nuovi» deve sapere che il difetto lo misura UNO.
--
-- Indice test (1..11):
--   1) fixture A: il reso e' CONFERMATO e la sua riga e' in coda accrediti
--   2) ⭐ registrato l'accredito, fn_annulla_reso RIFIUTA: P0001 e il codice
--      E_RESO_ANNULLO_CON_ACCREDITO nel canale CONSTRAINT
--   3) e non ha cascatato: il ponte e' intero e il reso e' ancora CONFERMATO
--   4) ⭐⭐ annullato l'accredito l'annullo del reso PASSA — l'auto-riparazione
--      di C-3, che e' l'altra meta' del vincolo
--   5) e il reso e' davvero ANNULLATO (il verbo ha fatto il suo mestiere)
--   6) nessuna regressione: un reso CONFERMATO senza accredito si annulla
--   7) guardia inerte su un reso DRAFT: un accredito pretende il CONFERMATO
--   8) ⭐ basta UNA riga di ponte su UNA riga per rifiutare l'INTERO annullo
--   ⭐ 9..11 — LA CAPABILITY, aggiunte il 2026-08-20 (changeset 20260820-12).
--      La guardia da sola lasciava il bottone «annulla» acceso e muto. La regola
--      di casa e' «permesso => nascondi, STATO => disabilita col motivo»
--      (frontend-standards, e ora linee-guida-sql §12): avere un accredito e'
--      uno stato che CAMBIA, quindi il bottone resta a video e spiega.
--   9) capability: l'azione annulla c'e' ma e' DISABILITATA, col motivo giusto
--  10) e can_change_state resta true: il bottone e' grigio, non sparito
--  11) ⭐ annullato l'accredito la capability torna abilitata — l'auto-riparazione
--      del test 4, vista dal lato dell'interfaccia
--
-- ⭐ PERCHE' IL TEST 8 NON USA UN KIT. La proprieta' da verificare e' «una
--    sola riga di ponte basta a rifiutare tutto il documento». Il kit la
--    produce moltiplicando i ponti su UNA riga di reso (una rettifica per
--    componente): la EXISTS la vedrebbe comunque al primo. La forma che
--    davvero mette alla prova la guardia e' l'opposta — un reso con DUE righe
--    di cui UNA SOLA accreditata: li' la EXISTS deve attraversare tutte le
--    righe del reso, ed e' l'unico modo in cui puo' sbagliare.
--
-- ⚠️ COSA QUESTO FILE NON PUO' MISURARE, e va detto invece di sembrare
--    coperto: «la guardia sta prima di qualunque scrittura». Il test 3 rilegge
--    lo stato dopo un rifiuto, ma sia throws_ok sia il nostro helper catturano
--    l'eccezione in una sottotransazione, che annulla comunque le scritture
--    eventuali. Quel test misura quindi l'ESITO (il reso resta usabile, il
--    ponte resta intero), non l'ordine delle istruzioni. L'ordine si legge nel
--    corpo della funzione, dove la EXISTS precede la UPDATE ad ANNULLATO.
--
-- ⚠️ Il codice di dominio si legge dal canale CONSTRAINT dell'eccezione, non
--    dal testo: e' il contratto dichiarato da script.fn_log_and_raise_error
--    («P0001 + CONSTRAINT valorizzato = errore di dominio»). Un throws_like
--    sulla frase legherebbe il test alla formulazione del catalogo, che e'
--    materia dell'operatore e cambia senza che cambi la regola.
--    ⭐ E c'e' un secondo motivo, misurato: cosi' il test e' verde ANCHE prima
--    che il mirror CSV di 80_data carichi la riga del codice nuovo. Il codice
--    esce dal canale strutturato comunque; e' solo la FRASE a ripiegare finche'
--    il catalogo non ha la voce. Un test sul testo sarebbe rosso per un motivo
--    che non c'entra niente con la guardia.
--
-- ⚠️ Il tipo di reso e' RESO_PER_RICONSEGNA (riapre_residuo = true), come
--    nelle fixture gemelle: e' quello che le altre prove di questo cantiere
--    usano, e tiene il file confrontabile con test-rinuncia-gate-accredito-v1.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo_acc AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP annulla reso gate');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_acc)); END $ctx$;

SELECT plan(11);

-- Dal 2026-09-28 conferma e annullo del reso sono verbi che applicano
-- l'azione conferma_reso (brief-db-magazzino-lotto-3-bis-carico-da-reso, D-3b-f):
-- l'operatore di fixture non ha azioni, si concede qui.
DO $az$ BEGIN
    PERFORM dbops.fn_pgtap_concedi_azione(
        NULLIF(current_setting('app.current_user_id', true), '')::integer, 'conferma_reso');
END $az$;

CREATE TEMP TABLE tmp_refs_agr AS
SELECT
  ba.id                                        AS billing_account_id,
  ba.utility_id                                AS utility_id,
  ba.istanza_utility_id                        AS istanza_utility_id,
  script.fn_pgtap_emittente_operatore()        AS emittente_fiscale_id,
  script.fn_pgtap_emittente_sr_operatore()     AS emittente_sr_id,
  ba.soggetto_ruolo_id                AS soggetto_ruolo_id,  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia): il ruolo del BA, non il primo del database
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non solo-componente, non
  --   gestito: il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-ANN-RESO-GATE', false)                  AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  -- ⚠️ rev 2026-10-08 (brief-db-righe-e-componenti-debiti-residui, D-1): la testata d'ordine nasce DRAFT,
  --   prende le righe, poi passa a CONFERMATO con dbops.fn_pgtap_porta_a_stato — fuori bozza le
  --   righe non si scrivono piu' (20261008-90).
  (SELECT s.id FROM config.stati_doc_ordini s WHERE s.codice_interno='DRAFT'      AND s.attivo ORDER BY s.id LIMIT 1)     AS stato_ord_draft_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='EMESSO'     AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_ddt_emesso_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='SPEDITO'    AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_ddt_spedito_id,
  (SELECT s.id FROM config.stati_doc_ddt s WHERE s.codice_interno='CONSEGNATO' AND s.attivo ORDER BY s.id LIMIT 1)        AS stato_ddt_consegnato_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='DDT_VENDITA' AND s.attivo ORDER BY s.id LIMIT 1)            AS sorgente_ddt_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA'    AND s.attivo ORDER BY s.id LIMIT 1)            AS sorgente_root_id,
  (SELECT s.id FROM config.stati_doc_reso s WHERE s.codice_interno='DRAFT' AND s.attivo ORDER BY s.id LIMIT 1)            AS stato_reso_draft_id,
  (SELECT t.id FROM config.tipi_reso t WHERE t.codice_interno='RESO_PER_RICONSEGNA' AND t.attivo ORDER BY t.id LIMIT 1)   AS tipo_reso_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                               AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  script.fn_pgtap_registro_fattura()                         AS registro_id,
  (SELECT c.id FROM config.causali_trasporto c WHERE c.codice='VENDITA' ORDER BY c.id LIMIT 1)                            AS causale_vendita_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno='CON')                                                       AS tipo_ind_con_id
-- ⛔ rev 2026-10-13: il BA e' quello del mondo costruito, non il primo del database.
FROM tmp_mondo_acc m
JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id;

-- ============================================================
-- Helper di fixture (stessa forma di test-rinuncia-gate-accredito-v1)
-- ⚠️ Padre e figlio in DUE istruzioni, mai in una CTE sola: le CTE che
--    scrivono condividono la stessa snapshot e una policy che risolve il
--    perimetro dal padre non lo trova, negando fail-closed.
-- ============================================================

-- Una partita consegnata, con p_n_righe righe di ordine (e quindi di DDT).
CREATE OR REPLACE FUNCTION pg_temp.agr_mk_partita(p_qta numeric, p_prezzo numeric,
                                                  p_n_righe integer DEFAULT 1)
RETURNS TABLE(ordine_id bigint, ddt_id bigint, ddt_uid uuid) AS $$
DECLARE r RECORD; v_ord bigint; v_ddt bigint; v_uid uuid; i integer;
BEGIN
  SELECT * INTO r FROM tmp_refs_agr;
  INSERT INTO vendite.ordini (soggetto_ruolo_id, billing_account_id, stato_doc_ordine_id,
    valuta_id, data, fatturazione_trigger, emittente_fiscale_id, storicizza, meta)
  VALUES (r.soggetto_ruolo_id, r.billing_account_id, r.stato_ord_draft_id, r.valuta_id,
          DATE '2026-07-15', 'CONSEGNATO', r.emittente_fiscale_id, false,
          jsonb_build_object('test_scope','pgtap_annulla_reso_gate'))
  RETURNING id INTO v_ord;
  UPDATE vendite.ordini SET fatturazione_trigger = 'CONSEGNATO' WHERE id = v_ord;

  FOR i IN 1..p_n_righe LOOP
    INSERT INTO vendite.ordini_righe (ordine_id, riga_nr, articolo_id, descrizione,
      qta_operativa, quantita, prezzo_unitario, iva_id, attivo, storicizza, meta)
    VALUES (v_ord, i, r.articolo_id, 'Riga annullo reso pgTAP ' || i, p_qta, p_qta, p_prezzo,
            r.iva_id, true, false, jsonb_build_object('test_scope','pgtap_annulla_reso_gate'));
  END LOOP;
  -- ⚠️ rev 2026-10-08 (D-1): righe scritte in bozza, ora la conferma vera (20261008-90).
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ordini', v_ord, 'CONFERMATO');

  v_ddt := vendite.fn_genera_ddt_da_ordine(v_ord);
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (v_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  UPDATE vendite.ddt SET causale_trasporto_id = r.causale_vendita_id      WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_emesso_id     WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_spedito_id    WHERE id = v_ddt;
  UPDATE vendite.ddt SET stato_doc_ddt_id     = r.stato_ddt_consegnato_id WHERE id = v_ddt;

  SELECT d.uid INTO v_uid FROM vendite.ddt d WHERE d.id = v_ddt;
  RETURN QUERY SELECT v_ord, v_ddt, v_uid;
END $$ LANGUAGE plpgsql;

-- ⚠️ ORDER BY esplicito: la n-esima riga del DDT va scelta, non pescata.
CREATE OR REPLACE FUNCTION pg_temp.agr_ddt_riga(p_ddt_id bigint, p_n integer)
RETURNS bigint AS $$
  SELECT dr.id FROM vendite.ddt_righe dr
   WHERE dr.ddt_id = p_ddt_id ORDER BY dr.id OFFSET (p_n - 1) LIMIT 1;
$$ LANGUAGE sql;

-- La merce viene FATTURATA: e' la catena che fn_accredita_riga_reso risale per
-- copiare il prezzo. Senza `fattura_riga_id` l'accredito e' impossibile.
CREATE OR REPLACE FUNCTION pg_temp.agr_fattura(p_segment varchar, p_qta numeric, p_prezzo numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_af bigint; v_fatt bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_agr;

  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => (SELECT commessa_id FROM tmp_com_agr),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com_agr))::text,
    p_segment_key                   => p_segment,
    p_articolo_id                   => r.articolo_id,
    p_istanza_utility_id            => r.istanza_utility_id,
    p_data_attivita                 => DATE '2026-07-15',
    p_uom_id                        => r.uom_id,
    p_quantita                      => p_qta,
    p_competenza_mese               => DATE '2026-07-01',
    p_competenza_dal                => DATE '2026-07-01',
    p_competenza_al                 => DATE '2026-07-31',
    p_prezzo_snapshot               => p_prezzo,
    p_prezzo_base_snapshot          => NULL,
    p_origine_prezzo                => NULL,
    p_tipo_variazione_applicata     => NULL,
    p_valore_variazione_applicata   => NULL,
    p_promo_id                      => NULL,
    p_contratto_id                  => NULL,
    p_categoria_cliente_id_snapshot => NULL,
    p_classe_utenza_id_snapshot     => NULL,
    p_tipo_doc_fiscale_id           => r.tipo_doc_fiscale_id,
    p_valuta_id                     => r.valuta_id,
    p_stato_approvazione            => 'APPROVATA',
    p_stato_emissione               => 'NON_EMESSA',
    p_tipo_movimento                => 'NORMALE');

  PERFORM vendite.fn_emit_attivita_fatturabili_da_commessa(
      (SELECT commessa_id FROM tmp_com_agr), true, false);

  SELECT af.id INTO v_af
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
   WHERE ca.segment_key = p_segment
   ORDER BY af.id DESC LIMIT 1;

  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, DATE '2026-07-31', r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_annulla_reso_gate'))
  RETURNING id INTO v_fatt;

  INSERT INTO vendite.fatture_righe (fattura_id, riga_nr, articolo_id, descrizione,
      uom_id, qta, prezzo_unitario, iva_id, imponibile_riga, competenza_dal, competenza_al)
  VALUES (v_fatt, 1, r.articolo_id, 'Riga fattura pgTAP', r.uom_id, p_qta, p_prezzo,
      r.iva_id, p_qta * p_prezzo, script.fn_data_operativa(), script.fn_data_operativa())
  RETURNING id INTO v_riga;

  UPDATE vendite.attivita_fatturabili
     SET fattura_riga_id = v_riga
   WHERE id = v_af;

  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- Reso e righe separati dalla conferma: qui servono anche resi che restano
-- in DRAFT (test 7) e resi con piu' di una riga (test 8).
CREATE OR REPLACE FUNCTION pg_temp.agr_new_reso(p_ddt_uid uuid)
RETURNS bigint AS $$
DECLARE r RECORD; v_reso bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_agr;
  INSERT INTO vendite.resi (stato_doc_reso_id, sorgente_tipo_id, sorgente_uid, storicizza, meta)
  VALUES (r.stato_reso_draft_id, r.sorgente_ddt_id, p_ddt_uid, false,
          jsonb_build_object('test_scope','pgtap_annulla_reso_gate'))
  RETURNING id INTO v_reso;
  RETURN v_reso;
END $$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION pg_temp.agr_add_riga(p_reso_id bigint, p_riga_nr integer,
                                                p_ddt_riga bigint, p_qta numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_agr;
  INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, ordine_riga_id,
      articolo_id, descrizione, qta_operativa, uom_operativa_id, factor_to_base,
      tipo_reso_id, storicizza)
  SELECT p_reso_id, p_riga_nr, dr.id,
         (SELECT f.ordine_riga_id FROM vendite.ordini_righe_fulfillment f
           WHERE f.ddt_riga_id = dr.id ORDER BY f.id LIMIT 1),
         dr.articolo_id, dr.descrizione, p_qta, dr.uom_operativa_id, dr.factor_to_base,
         r.tipo_reso_id, false
    FROM vendite.ddt_righe dr WHERE dr.id = p_ddt_riga
  RETURNING id INTO v_riga;
  RETURN v_riga;
END $$ LANGUAGE plpgsql;

-- ⭐ L'esito dell'annullo come COPPIA (sqlstate, codice di dominio), letto dal
--    canale CONSTRAINT: e' il contratto di script.fn_log_and_raise_error, e non
--    lega il test alla formulazione del messaggio.
CREATE OR REPLACE FUNCTION pg_temp.agr_esito_annullo(p_reso_id bigint)
RETURNS text AS $$
DECLARE v_cod text;
BEGIN
  PERFORM vendite.fn_annulla_reso(p_reso_id);
  RETURN 'OK';
EXCEPTION WHEN OTHERS THEN
  GET STACKED DIAGNOSTICS v_cod = CONSTRAINT_NAME;
  RETURN SQLSTATE || '|' || COALESCE(NULLIF(v_cod, ''), '-');
END $$ LANGUAGE plpgsql;

-- ============================================================
-- FIXTURE: una commessa sola per tutto il file.
-- ============================================================
CREATE TEMP TABLE tmp_com_agr AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_agr),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_agr),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-07-31',
  p_meta                   => '{}'::jsonb,
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_agr),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_agr),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_agr)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

-- ── PARTITA A: consegnati 10 a 25, fatturati 10, resi 3 -> accreditabile ──
CREATE TEMP TABLE tmp_pa AS SELECT * FROM pg_temp.agr_mk_partita(10, 25);
CREATE TEMP TABLE tmp_pa_riga AS SELECT pg_temp.agr_ddt_riga((SELECT ddt_id FROM tmp_pa), 1) AS ddt_riga_id;
CREATE TEMP TABLE tmp_pa_fatt AS
SELECT pg_temp.agr_fattura(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pa)::text, (SELECT ddt_riga_id FROM tmp_pa_riga)),
    10, 25) AS fattura_riga_id;
CREATE TEMP TABLE tmp_reso_a AS SELECT pg_temp.agr_new_reso((SELECT ddt_uid FROM tmp_pa)) AS reso_id;
CREATE TEMP TABLE tmp_reso_a_riga AS
SELECT pg_temp.agr_add_riga((SELECT reso_id FROM tmp_reso_a), 1,
                            (SELECT ddt_riga_id FROM tmp_pa_riga), 3) AS resi_riga_id;
SELECT vendite.fn_conferma_reso((SELECT reso_id FROM tmp_reso_a));

SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
    WHERE r.id = (SELECT reso_id FROM tmp_reso_a))
  || '|' ||
  (SELECT count(*)::int FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_reso_a_riga))::text,
  'CONFERMATO|1',
  '1) fixture A: il reso e'' CONFERMATO e la sua riga e'' in coda accrediti'
);

-- ============================================================
-- IL VERBO, e poi l'annullo del documento
-- ============================================================
CREATE TEMP TABLE tmp_acc_a AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_reso_a_riga));

-- ⚠️ Il verbo in un'istruzione SEPARATA dall'asserzione: la snapshot di
--    statement leggerebbe PRIMA delle scritture, e il rosso accuserebbe la
--    funzione invece del test.
CREATE TEMP TABLE tmp_esito_a AS
SELECT pg_temp.agr_esito_annullo((SELECT reso_id FROM tmp_reso_a)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_a),
  'P0001|E_RESO_ANNULLO_CON_ACCREDITO',
  '2) con l''accredito registrato l''annullo del reso e'' RIFIUTATO, col codice giusto'
);

-- 3) Il rifiuto non ha disfatto niente per conto suo: e' il punto 1 della
--    segnalazione BE — «rifiutare, non cascatare». Se la funzione avesse
--    annullato l'accredito da se', il ponte sarebbe vuoto e il reso ANNULLATO.
SELECT is(
  (SELECT count(*)::int FROM vendite.resi_righe rr
     JOIN vendite.resi_righe_accrediti a ON a.resi_riga_id = rr.id
    WHERE rr.reso_id = (SELECT reso_id FROM tmp_reso_a))::text
  || '|' ||
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
    WHERE r.id = (SELECT reso_id FROM tmp_reso_a)),
  '1|CONFERMATO',
  '3) e non ha cascatato: il ponte e'' intero e il reso e'' ancora CONFERMATO'
);

-- ============================================================
-- 4-5) ⭐⭐ L'AUTO-RIPARAZIONE DI C-3.
--   La guardia non sa nulla dell'annullo dell'accredito: si spegne solo
--   perche' quello CANCELLA le righe di ponte. Se un giorno diventasse un
--   soft-delete questi due test diventerebbero rossi — ed e' il loro scopo.
-- ============================================================
SELECT vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga_id FROM tmp_reso_a_riga), 'ci ho ripensato, pgTAP');

SELECT lives_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT reso_id FROM tmp_reso_a)),
  '4) annullato l''accredito, l''annullo del reso passa: la guardia si auto-ripara'
);

SELECT is(
  (SELECT sdr.codice_interno FROM vendite.resi r
     JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
    WHERE r.id = (SELECT reso_id FROM tmp_reso_a)),
  'ANNULLATO',
  '5) e il reso e'' davvero ANNULLATO: il verbo ha fatto il suo mestiere'
);

-- ============================================================
-- 6) NESSUNA REGRESSIONE — reso CONFERMATO, mai accreditato.
--    Partita B a parte: due resi sulla stessa riga di DDT si contendono il
--    guard sull'over-return, che conta anche le bozze.
-- ============================================================
CREATE TEMP TABLE tmp_pb AS SELECT * FROM pg_temp.agr_mk_partita(10, 25);
CREATE TEMP TABLE tmp_pb_riga AS SELECT pg_temp.agr_ddt_riga((SELECT ddt_id FROM tmp_pb), 1) AS ddt_riga_id;
CREATE TEMP TABLE tmp_reso_b AS SELECT pg_temp.agr_new_reso((SELECT ddt_uid FROM tmp_pb)) AS reso_id;
CREATE TEMP TABLE tmp_reso_b_riga AS
SELECT pg_temp.agr_add_riga((SELECT reso_id FROM tmp_reso_b), 1,
                            (SELECT ddt_riga_id FROM tmp_pb_riga), 3) AS resi_riga_id;
SELECT vendite.fn_conferma_reso((SELECT reso_id FROM tmp_reso_b));

SELECT lives_ok(
  format($q$SELECT vendite.fn_annulla_reso(%s)$q$, (SELECT reso_id FROM tmp_reso_b)),
  '6) nessuna regressione: un reso CONFERMATO senza accredito si annulla come prima'
);

-- ============================================================
-- 7) GUARDIA INERTE SU UN RESO DRAFT.
--    Un accredito pretende il CONFERMATO (vw_resi_righe_effettive filtra li'),
--    quindi su una bozza la EXISTS non puo' trovare nulla — e l'annullo da
--    DRAFT, che non ha effetti da stornare, deve restare quello di sempre.
-- ============================================================
CREATE TEMP TABLE tmp_pc AS SELECT * FROM pg_temp.agr_mk_partita(10, 25);
CREATE TEMP TABLE tmp_pc_riga AS SELECT pg_temp.agr_ddt_riga((SELECT ddt_id FROM tmp_pc), 1) AS ddt_riga_id;
CREATE TEMP TABLE tmp_reso_c AS SELECT pg_temp.agr_new_reso((SELECT ddt_uid FROM tmp_pc)) AS reso_id;
CREATE TEMP TABLE tmp_reso_c_riga AS
SELECT pg_temp.agr_add_riga((SELECT reso_id FROM tmp_reso_c), 1,
                            (SELECT ddt_riga_id FROM tmp_pc_riga), 3) AS resi_riga_id;

CREATE TEMP TABLE tmp_esito_c AS
SELECT pg_temp.agr_esito_annullo((SELECT reso_id FROM tmp_reso_c)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_c),
  'OK',
  '7) guardia inerte su un reso DRAFT: l''annullo da bozza resta quello di sempre'
);

-- ============================================================
-- 8) ⭐ BASTA UNA RIGA DI PONTE PER RIFIUTARE L'INTERO ANNULLO.
--    Partita D con DUE righe: si fattura e si accredita SOLO la prima. La
--    seconda riga di reso non ha (e non puo' avere) accredito. La guardia
--    deve comunque rifiutare, perche' la sua unita' e' il DOCUMENTO.
-- ============================================================
CREATE TEMP TABLE tmp_pd AS SELECT * FROM pg_temp.agr_mk_partita(10, 25, 2);
CREATE TEMP TABLE tmp_pd_righe AS
SELECT pg_temp.agr_ddt_riga((SELECT ddt_id FROM tmp_pd), 1) AS riga1,
       pg_temp.agr_ddt_riga((SELECT ddt_id FROM tmp_pd), 2) AS riga2;
CREATE TEMP TABLE tmp_pd_fatt AS
SELECT pg_temp.agr_fattura(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pd)::text, (SELECT riga1 FROM tmp_pd_righe)),
    10, 25) AS fattura_riga_id;
CREATE TEMP TABLE tmp_reso_d AS SELECT pg_temp.agr_new_reso((SELECT ddt_uid FROM tmp_pd)) AS reso_id;
CREATE TEMP TABLE tmp_reso_d_righe AS
SELECT pg_temp.agr_add_riga((SELECT reso_id FROM tmp_reso_d), 1, (SELECT riga1 FROM tmp_pd_righe), 3) AS resi_riga1,
       pg_temp.agr_add_riga((SELECT reso_id FROM tmp_reso_d), 2, (SELECT riga2 FROM tmp_pd_righe), 3) AS resi_riga2;
SELECT vendite.fn_conferma_reso((SELECT reso_id FROM tmp_reso_d));

CREATE TEMP TABLE tmp_acc_d AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga1 FROM tmp_reso_d_righe));

CREATE TEMP TABLE tmp_esito_d AS
SELECT pg_temp.agr_esito_annullo((SELECT reso_id FROM tmp_reso_d)) AS esito;

SELECT is(
  (SELECT esito FROM tmp_esito_d),
  'P0001|E_RESO_ANNULLO_CON_ACCREDITO',
  '8) basta UNA riga accreditata su due per rifiutare l''INTERO annullo del reso'
);

-- ============================================================
-- 9..11) ⭐ LA CAPABILITY DICE LA STESSA COSA DELLA GUARDIA.
--   Se questi tre e i test 2/4 divergessero, l'operatore vedrebbe un bottone
--   acceso e prenderebbe un 409 in faccia — o, peggio, un bottone grigio su un
--   annullo che sarebbe passato. Il predicato e' lo stesso EXISTS, apposta.
-- ============================================================

CREATE TEMP TABLE tmp_cap_d AS
SELECT a->>'key' AS azione,
       (a->>'enabled')::boolean AS enabled,
       a->>'reason'     AS reason,
       a->>'reason_key' AS reason_key
  FROM jsonb_array_elements(
       script.fn_available_actions_reso((SELECT reso_id FROM tmp_reso_d)) -> 'available_actions') a
 WHERE a->>'key' = 'annulla';

SELECT is(
  (SELECT enabled::text || '|' || COALESCE(reason,'?') || '|' || COALESCE(reason_key,'?')
     FROM tmp_cap_d),
  'false|RESO_CON_ACCREDITI|vendite.reso.annulla_reason.con_accrediti',
  '9) capability: l''azione annulla e'' disabilitata col motivo dell''accredito'
);

-- ⚠️ Il punto della decisione, e la ragione per cui NON si e' tolta l'azione
--   dalle ammesse: sparire senza spiegazione e' la variante peggiore.
SELECT is(
  (SELECT count(*)::int FROM tmp_cap_d)::text || '|' ||
  (script.fn_available_actions_reso((SELECT reso_id FROM tmp_reso_d)) ->> 'can_change_state'),
  '1|true',
  '10) l''azione resta NELL''ELENCO e can_change_state resta true: grigia, non sparita'
);

-- ⭐ L'auto-riparazione del test 4, vista dall'interfaccia: la capability non sa
--   nulla dell'annullo dell'accredito, si riabilita solo perche' quello CANCELLA
--   le righe di ponte.
SELECT vendite.fn_annulla_accredito_riga_reso(
    (SELECT resi_riga1 FROM tmp_reso_d_righe), 'ci ho ripensato anche qui, pgTAP');

SELECT is(
  (SELECT (a->>'enabled')::boolean
     FROM jsonb_array_elements(
          script.fn_available_actions_reso((SELECT reso_id FROM tmp_reso_d)) -> 'available_actions') a
    WHERE a->>'key' = 'annulla'),
  true,
  '11) annullato l''accredito la capability torna abilitata (auto-riparazione lato UI)'
);

SELECT * FROM finish();
ROLLBACK;
