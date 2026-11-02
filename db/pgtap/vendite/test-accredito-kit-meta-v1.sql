-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): la commessa da dbops.fn_pgtap_crea_commessa (sorgente ROOT), la fattura dei componenti da dbops.fn_pgtap_fattura_attivita (ritirato pg_temp.kit_fattura); resta a mano pg_temp.kit_mk_componente (il meta del kit e il segmento #CMP: sono il caso), con la sorgente DDT_VENDITA della bolla (E-3).
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso dal builder dbops.fn_pgtap_crea_reso (che concede da se' conferma_reso); resta scritto a mano il kit sulla commessa, che e' il caso del test.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso (giro 2) e il kit sulla commessa, che e' il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_accredita_riga_reso — lo snapshot KIT sulla rettifica
--       (P-7, changeset 20260818-75). Origine: smoke del BE del 2026-08-18.
-- ------------------------------------------------------------
-- ⛔ Prima di 20260818-75 questo file e' ROSSO sui test 3, 4, 7 e 8 — misurato
--    il 2026-08-18, ed e' il difetto che il file esiste per fissare:
--      3) componente_di   have 0, want 2
--      4) esposto_in_fattura   have 0, want 2
--      7) il cancello del generatore   have 0, want 2   <- e' lo smoke del BE,
--         riprodotto a livello DB invece che a fine pipeline
--      8) «no exception thrown»        <- ⭐ il difetto in tre parole: su un kit
--         che non potra' MAI produrre un documento, il verbo riesce lo stesso
--    Verdi anche prima: 1, 2, 5, 6 — la fixture e la misura in unita' padre
--    reggevano gia', il buco era solo nello snapshot che viaggia.
--
-- IL DIFETTO IN UNA RIGA. La parentela padre/componente di un kit non ha
--   colonne: vive in `segment_key` e in QUATTRO chiavi del meta (contratto
--   backend/apps/vendite/services/_kit_meta.py). La madre ne copiava UNA.
--   La rettifica di un componente si dichiarava componente — perche' fn_emit
--   scrive `segment_key` nel meta dell'attivita' fatturabile, e quel segmento
--   porta `#CMP:` — senza dire DI CHI, e il generatore righe la rifiutava.
--   ⚠️ Nella forma peggiore: verbo ok, riga fuori dalla coda, niente documento.
--
-- Indice test (1..8):
--   1) fixture: il kit e' misurato in unita' PADRE e la coda chiede 3
--   2) il verbo crea DUE rettifiche, una per componente
--   3) ⭐ ciascuna porta `componente_di` EREDITATO dalla riga rettificata
--   4) ⭐ e `esposizione`, il secondo tasto che mancava (fino al 2026-10-01 si
--      chiamava `esposto_in_fattura` ed era un booleano: tre modi da
--      brief-db-esposizione-componenti-kit-in-fattura)
--   5) `coeff_qta` continua ad arrivare (era l'unico che gia' passava)
--   6) il segmento e' <spedizione>#RET:1#CMP:<componente> — il `#RET:` PRIMA
--      del `#CMP:`, cosi' il kit_key della rettifica resta calcolabile
--   7) ⭐ IL CANCELLO DEL GENERATORE, riprodotto: dopo l'emissione l'attivita'
--      fatturabile si dichiara componente E dice di chi. E' la condizione
--      esatta che generate_fatture_righe verifica prima di sollevare
--      E_ATTIVITA_KIT_SENZA_PADRE
--   8) ⭐ il guard nuovo: un kit i cui componenti NON portano `componente_di`
--      viene rifiutato AL VERBO (E_ACCREDITO_KIT_SENZA_PADRE), e la riga
--      NON esce dalla coda
--   9) ⭐ la rettifica porta la SUA quantita' padre, -3, e non quella
--      ereditata dalla riga rettificata (+10): R-DB-B8 di
--      brief-db-bom-flag-quantita-e-kit-in-fattura, changeset 20261003-05.
--      ⚠️ Prima di quel changeset e' ROSSO: la fixture scrive `qta_padre`
--      come il push di oggi (R-BE-B2), e il meta ereditato la riportava
--      positiva su componenti negativi
--
-- ⚠️ I componenti si creano con fn_upsert_commessa_attivita, che e' la stessa
--    funzione che usa il push (BoMComponentExpander): il meta del kit lo
--    scrive li'. Non e' una fixture «a mano» in senso proprio — e' lo stesso
--    ingresso, chiamato senza passare da Python.
-- ------------------------------------------------------------

BEGIN;

SET CONSTRAINTS ALL IMMEDIATE;

-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo_kit AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP accredito kit');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_kit)); END $ctx$;

SELECT plan(9);

CREATE TEMP TABLE tmp_refs_kit AS
SELECT
  ba.id                                        AS billing_account_id,
  ba.istanza_utility_id                        AS istanza_utility_id,
  -- Tre articoli DISTINTI: il padre e i due componenti. Il suffisso #CMP: e'
  -- una stringa libera, ma usare articoli veri tiene la fixture vicina a
  -- quello che scrive il push.
  -- ⛔ rev 2026-10-13: si COSTRUISCONO (merce non solo-componente, non gestita:
  --   il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-ACC-KIT-PADRE', false)             AS art_padre_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-ACC-KIT-C1', false)                AS art_c1_id,
  dbops.fn_pgtap_crea_articolo('PGTAP-ACC-KIT-C2', false)                AS art_c2_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                               AS tipo_doc_fiscale_id
-- ⛔ rev 2026-10-13: il BA e' quello del mondo costruito, non il primo del database.
FROM tmp_mondo_kit m
JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id;

-- Un COMPONENTE di kit: l'attivita' con il segmento #CMP: e il meta del
-- contratto. p_padre NULL = il caso rotto del test 8. Torna l'attivita'.
-- ⭐ rev 2026-10-25 (E-3): la sorgente e' la bolla (DDT_VENDITA, la sua
--   chiave), come la scrive il push; era la commessa con la chiave della bolla.
CREATE OR REPLACE FUNCTION pg_temp.kit_mk_componente(
  p_segment varchar, p_articolo uuid, p_qta numeric, p_prezzo numeric,
  p_coeff numeric, p_padre text, p_ddt_uid uuid)
RETURNS bigint AS $$
DECLARE r RECORD; v_att bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_kit;
  SELECT u.attivita_id INTO v_att FROM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => (SELECT commessa_id FROM tmp_com_kit),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'DDT_VENDITA'),
    p_sorgente_uid => p_ddt_uid::text,
    p_segment_key                   => p_segment,
    p_articolo_id                   => p_articolo,
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
    p_tipo_movimento                => 'NORMALE',
    -- ⭐ Il contratto kit, scritto come lo scrive il push.
    --    jsonb_strip_nulls: con p_padre NULL la chiave `componente_di` NON
    --    nasce, che e' esattamente il caso rotto del test 8.
    --    Dal 2026-10-03 anche `qta_padre`, la quantita' della riga padre del
    --    documento (R-BE-B2): quantita' del componente / coefficiente.
    p_meta                          => jsonb_strip_nulls(jsonb_build_object(
                                          'coeff_qta',           p_coeff,
                                          'componente_di',       p_padre,
                                          'esposizione',         'DESCRITTIVO',
                                          'qta_padre',           p_qta / p_coeff))) u;
  RETURN v_att;
END $$ LANGUAGE plpgsql;

-- I componenti si emettono e si agganciano a una fattura vera, una riga per
-- componente, da dbops.fn_pgtap_fattura_attivita: senza `fattura_riga_id`
-- l'accredito e' impossibile per costruzione.
CREATE TEMP TABLE tmp_com_kit AS
SELECT c.commessa_id
  FROM dbops.fn_pgtap_crea_commessa('accredito kit', NULL,
           (SELECT billing_account_id FROM tmp_refs_kit), p_con_sorgente_root => true) c;

-- ============================================================
-- KIT A — sano: 10 unita' padre, due componenti a coefficiente 2 e 3
--   (quindi 20 e 30 pezzi), fatturati entrambi, resi 3 unita' padre.
--   ⚠️ La quantita' PADRE si legge come max(quantita/coeff) e pretende
--      coerenza: 20/2 = 30/3 = 10. Se non concordassero, `misurabile`
--      sarebbe falso e il conto della merce non si applicherebbe.
-- ============================================================
-- La partita: la bolla CONSEGNATA dell'articolo padre, 10 a 12.50, trigger
--   CONSEGNATO, dal cliente del mondo.
CREATE TEMP TABLE tmp_ka AS
SELECT b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('accredito kit',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_kit),
           p_quantita             => 10,
           p_prezzo               => 12.50,
           p_articolo_id          => (SELECT art_padre_id FROM tmp_refs_kit),
           p_fatturazione_trigger => 'CONSEGNATO') b;
CREATE TEMP TABLE tmp_ka_key AS
SELECT script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_ka)::text, (SELECT ddt_riga_id FROM tmp_ka)) AS kit_key;

CREATE TEMP TABLE tmp_ka_c1 AS
SELECT pg_temp.kit_mk_componente(
  ((SELECT kit_key FROM tmp_ka_key) || '#CMP:' || (SELECT art_c1_id FROM tmp_refs_kit)::text)::varchar,
  (SELECT art_c1_id FROM tmp_refs_kit), 20, 2.50, 2, (SELECT art_padre_id FROM tmp_refs_kit)::text,
  (SELECT ddt_uid FROM tmp_ka)) AS attivita_id;
CREATE TEMP TABLE tmp_ka_c2 AS
SELECT pg_temp.kit_mk_componente(
  ((SELECT kit_key FROM tmp_ka_key) || '#CMP:' || (SELECT art_c2_id FROM tmp_refs_kit)::text)::varchar,
  (SELECT art_c2_id FROM tmp_refs_kit), 30, 2.50, 3, (SELECT art_padre_id FROM tmp_refs_kit)::text,
  (SELECT ddt_uid FROM tmp_ka)) AS attivita_id;

CREATE TEMP TABLE tmp_ka_fatt AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('accredito kit',
           ARRAY[(SELECT attivita_id FROM tmp_ka_c1), (SELECT attivita_id FROM tmp_ka_c2)]);

-- Il reso a credito di 3 unita' padre, confermato.
CREATE TEMP TABLE tmp_ka_reso AS
SELECT x.resi_riga_id
  FROM dbops.fn_pgtap_crea_reso('accredito kit', (SELECT ddt_id FROM tmp_ka), 3,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_ka)) x;

SELECT is(
  (SELECT q.accredito_dovuto FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_ka_reso)),
  3::numeric,
  '1) fixture: il kit e'' misurato in unita'' PADRE (20/2 = 30/3 = 10) e la coda chiede 3'
);

CREATE TEMP TABLE tmp_acc_kit AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_ka_reso));

SELECT is(
  (SELECT count(*)::int FROM tmp_acc_kit),
  2,
  '2) il verbo crea DUE rettifiche, una per componente — ciascuna specchio della SUA riga di fattura'
);

-- ============================================================
-- 3-5) ⭐ IL CONTRATTO KIT SULLA RETTIFICA. Prima di 20260818-75 arrivava
--      solo `coeff_qta`: i test 3 e 4 sono il difetto trovato dallo smoke.
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
    WHERE ca.id IN (SELECT commessa_attivita_id FROM tmp_acc_kit)
      AND ca.meta ->> 'componente_di' = (SELECT art_padre_id FROM tmp_refs_kit)::text),
  2,
  '3) entrambe le rettifiche portano `componente_di` EREDITATO dalla riga rettificata'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
    WHERE ca.id IN (SELECT commessa_attivita_id FROM tmp_acc_kit)
      AND ca.meta ->> 'esposizione' = 'DESCRITTIVO'),
  2,
  '4) e portano `esposizione`: la nota di credito prende la forma della fattura che rettifica'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
    WHERE ca.id IN (SELECT commessa_attivita_id FROM tmp_acc_kit)
      AND (ca.meta ->> 'coeff_qta') IN ('2','3')),
  2,
  '5) `coeff_qta` continua ad arrivare: era l''unico dei quattro tasti che gia'' passava'
);

SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
    WHERE ca.id IN (SELECT commessa_attivita_id FROM tmp_acc_kit)
      AND ca.segment_key::text LIKE (SELECT kit_key FROM tmp_ka_key)::text || '#RET:1#CMP:%'),
  2,
  '6) il segmento porta `#RET:` PRIMA di `#CMP:`, cosi'' il kit_key della rettifica resta calcolabile'
);

-- ============================================================
-- 7) ⭐ IL CANCELLO DEL GENERATORE, riprodotto in SQL.
--    generate_fatture_righe legge meta->>'segment_key' (che ce lo mette
--    fn_emit) e, se contiene '#CMP:', PRETENDE meta->>'componente_di' non
--    vuoto — altrimenti solleva E_ATTIVITA_KIT_SENZA_PADRE, perche' trattare
--    la riga come normale la fatturerebbe due volte (R11).
--    Qui si verifica che l'attivita' fatturabile della rettifica soddisfi
--    quella condizione: e' il difetto dello smoke, misurato dove nasce.
-- ============================================================
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa(
    (SELECT commessa_id FROM tmp_com_kit), true, false);

SELECT is(
  (SELECT count(*)::int
     FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id IN (SELECT commessa_attivita_id FROM tmp_acc_kit)
      AND af.meta ->> 'segment_key' LIKE '%#CMP:%'
      AND NULLIF(btrim(af.meta ->> 'componente_di'), '') IS NOT NULL),
  2,
  '7) il cancello del generatore e'' soddisfatto: l''attivita'' si dichiara componente E dice di chi'
);

-- ============================================================
-- KIT B — rotto a monte: i componenti NON portano `componente_di`.
--   ⭐ Senza il guard nuovo il verbo riuscirebbe, la riga USCIREBBE dalla
--     coda e il documento non nascerebbe. Con il guard si ferma qui.
-- ============================================================
-- La partita: la bolla CONSEGNATA dell'articolo padre, 10 a 12.50, trigger
--   CONSEGNATO, dal cliente del mondo.
CREATE TEMP TABLE tmp_kb AS
SELECT b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('accredito kit',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_kit),
           p_quantita             => 10,
           p_prezzo               => 12.50,
           p_articolo_id          => (SELECT art_padre_id FROM tmp_refs_kit),
           p_fatturazione_trigger => 'CONSEGNATO') b;
CREATE TEMP TABLE tmp_kb_key AS
SELECT script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_kb)::text, (SELECT ddt_riga_id FROM tmp_kb)) AS kit_key;

CREATE TEMP TABLE tmp_kb_c1 AS
SELECT pg_temp.kit_mk_componente(
  ((SELECT kit_key FROM tmp_kb_key) || '#CMP:' || (SELECT art_c1_id FROM tmp_refs_kit)::text)::varchar,
  (SELECT art_c1_id FROM tmp_refs_kit), 20, 2.50, 2, NULL,
  (SELECT ddt_uid FROM tmp_kb)) AS attivita_id;
CREATE TEMP TABLE tmp_kb_c2 AS
SELECT pg_temp.kit_mk_componente(
  ((SELECT kit_key FROM tmp_kb_key) || '#CMP:' || (SELECT art_c2_id FROM tmp_refs_kit)::text)::varchar,
  (SELECT art_c2_id FROM tmp_refs_kit), 30, 2.50, 3, NULL,
  (SELECT ddt_uid FROM tmp_kb)) AS attivita_id;

CREATE TEMP TABLE tmp_kb_fatt AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('accredito kit',
           ARRAY[(SELECT attivita_id FROM tmp_kb_c1), (SELECT attivita_id FROM tmp_kb_c2)]);

CREATE TEMP TABLE tmp_kb_reso AS
SELECT x.resi_riga_id
  FROM dbops.fn_pgtap_crea_reso('accredito kit', (SELECT ddt_id FROM tmp_kb), 3,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_kb)) x;

SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_accredita_riga_reso(%s) $$,
         (SELECT resi_riga_id FROM tmp_kb_reso)),
  '%articolo padre%',
  '8) kit senza `componente_di`: rifiutato AL VERBO, prima che la riga esca dalla coda'
);

-- ============================================================
-- 9) ⭐ LA QUANTITA' PADRE DELLA RETTIFICA (R-DB-B8). Il meta ereditato
--    porterebbe +10, la quantita' padre della riga rettificata: il kit reso
--    e' di 3, e la nota di credito lo dice col segno del componente.
--    (::numeric e non il testo: v_quota ha la scala della sua colonna.)
-- ============================================================
SELECT is(
  (SELECT count(*)::int FROM vendite.commesse_attivita ca
    WHERE ca.id IN (SELECT commessa_attivita_id FROM tmp_acc_kit)
      AND (ca.meta ->> 'qta_padre')::numeric = -3),
  2,
  '9) entrambe le rettifiche portano qta_padre = -3 (il kit reso), non +10 ereditato dalla riga rettificata'
);

SELECT * FROM finish();
ROLLBACK;
