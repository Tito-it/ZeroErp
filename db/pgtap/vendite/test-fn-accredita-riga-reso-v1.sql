-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito): il reso a credito dal builder dbops.fn_pgtap_crea_reso (che concede da se' conferma_reso); resta scritta a mano la commessa con la fattura, che e' il caso del test.
-- rev 2026-10-25 (brief-db-pgtap-bolla-e-reso-costruiti, giro 1): la bolla da ordine dal builder dbops.fn_pgtap_crea_ddt_da_ordine; resta scritto a mano il reso (giro 2) e la commessa con la fattura, che sono il caso del test.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13, 2e/L2c-1): le chiavi del push col codice della sorgente, composte da script.fn_segment_key dove la forma lo permette (le forme su piu' righe col prefisso lungo); corsia e codice del registro coi codici lunghi.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_accredita_riga_reso — la madre del verbo «accredita»
--       (brief-design-note-credito-resi, slice N8; changeset 20260818-39)
-- ------------------------------------------------------------
-- Indice test (1..16):
--   1) fixture: la partita nasce in coda accrediti con accredito dovuto 3
--   2) il verbo crea UNA rettifica (la partita ha una sola riga di fattura)
--   3) la rettifica porta quantita' NEGATIVA (D-NC-2: il segno sta nel numero)
--   4) ⭐ D-NC-1: il segmento e' quello della SPEDIZIONE, col suffisso #RET:1
--   5) la rettifica e' RETTIFICA + natura NOTA_CREDITO + APPROVATA/NON_EMESSA
--   6) ⭐ N-1: il prezzo e' COPIATO dalla riga di fattura, non ricalcolato
--   7) il ponte resi_righe_accrediti registra il fatto, con qta e qta_partita
--   8) ⭐ la riga esce dalla coda AL VERBO, non alla generazione della fattura
--   9) ⭐ due click non producono due accrediti (E_ACCREDITO_GIA_ESEGUITO)
--  10) ⭐ il contratto del §2: emessa la rettifica, la partita PAREGGIA e la
--      differenza torna a zero — il contatore ha visto la nota di credito
--  11) invariante D-NC-9: la rettifica nomina la riga di fattura che rettifica
--  12) guard: una riga di reso NON in coda -> E_ACCREDITO_NON_IN_CODA
--  13) guard sul parametro: id nullo -> E_PARAMETRO_INVALIDO
--  14) ⭐ tetto del DOCUMENTO: un secondo reso non puo' accreditare piu' di
--      quanto la riga di fattura abbia fatturato
--  15) ⭐ corsia ORD: fatturato sull'ordine, la rettifica nasce sulla
--      spedizione col prezzo della riga d'ordine (rev 2026-10-18)
--  16) ⭐ pin di forma: ogni lettura di commesse_attivita del verbo entra da
--      segment_base (rev 2026-10-18, 20261018-15)
--
-- Scopo:
--  - collaudare il verbo PASSANDO DALLA MADRE, non inserendo le righe a mano:
--    al 2026-08-17 le righe RETTIFICA nel database sono ZERO, quindi ogni ramo
--    scritto dal cantiere e' un ramo che nessun dato attraversa. Una fixture
--    costruita a mano potrebbe CONFERMARE UN RAMO MORTO — «un ramo si verifica
--    dal percorso che lo attraversa, non dal codice che lo dichiara».
-- ------------------------------------------------------------

BEGIN;

-- ⚠️ Vincoli DIFFERITI: nel DB ce ne sono 365 e scattano al COMMIT, che qui non
--   arriva mai (si chiude in ROLLBACK). Senza questa riga non verrebbero
--   esercitati e il file sarebbe verde per sottrazione.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: il test gira come gira l'applicazione (OPERATORE + RLS
-- attiva), non come owner. L'owner salterebbe le policy e il test non le
-- eserciterebbe mai.
-- ⛔ rev 2026-10-13: il mondo si COSTRUISCE (su un DB ricostruito anagrafiche e
--   articoli sono vuoti): azienda + operatore + cliente BA, e il builder apre
--   da se' il contesto su quell'operatore. Niente utente 1 inchiodato.
CREATE TEMP TABLE tmp_mondo_acc AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('pgTAP accredita reso');
-- Il mondo ha gia' aperto il contesto sul suo operatore: la riga lo
--   dichiara (e il guardrail del preambolo la cerca).
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore((SELECT auth_user_id FROM tmp_mondo_acc)); END $ctx$;

SELECT plan(16);

-- ============================================================
-- Riferimenti
-- ⚠️ Ogni scelta ha il suo ORDER BY: senza, quale riga esca dipende dal piano
--    del planner e il test passa a giorni alterni. E l'emittente non si pesca,
--    si DERIVA da chi agisce, o le policy ef_whitelist negano fail-closed.
-- ============================================================
CREATE TEMP TABLE tmp_refs_acc AS
SELECT
  ba.id                                                                  AS billing_account_id,
  ba.utility_id                                                          AS utility_id,
  ba.istanza_utility_id                                                  AS istanza_utility_id,
  script.fn_pgtap_emittente_sr_operatore()                               AS emittente_sr_id,
  -- ⛔ rev 2026-10-13: l'articolo si COSTRUISCE (merce non solo-componente, non
  --   gestito: il test non misura il magazzino) — da zero il catalogo ha solo ONERE_*.
  dbops.fn_pgtap_crea_articolo('PGTAP-ACC-RESO', false)                  AS articolo_id,
  (SELECT u.id FROM catalogo.unita_misura u WHERE u.attivo IS TRUE ORDER BY u.id LIMIT 1) AS uom_id,
  (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1)                                AS valuta_id,
  (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1)            AS iva_id,
  (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno='COMMESSA'    AND s.attivo ORDER BY s.id LIMIT 1)         AS sorgente_root_id,
  (SELECT t.id FROM config.tipi_doc_fiscale t WHERE t.attivo IS TRUE ORDER BY t.id LIMIT 1)                            AS tipo_doc_fiscale_id,
  (SELECT s.id FROM config.stati_doc_fiscale s WHERE s.codice_interno='DRAFT' AND s.attivo IS TRUE ORDER BY s.id LIMIT 1) AS stato_fatt_draft_id,
  script.fn_pgtap_registro_fattura()                      AS registro_id
-- ⛔ rev 2026-10-13: il BA e' quello del mondo costruito, non il primo del database.
FROM tmp_mondo_acc m
JOIN anagrafiche.billing_account ba ON ba.id = m.billing_account_id;

-- ============================================================
-- Helper di fixture
-- ⚠️ Padre e figlio in DUE istruzioni, mai in una CTE sola: le CTE che scrivono
--    condividono la stessa snapshot, e una policy che risolve il perimetro dal
--    padre non lo trova e nega fail-closed. Per questo sono funzioni plpgsql.
-- La partita di merce vera (ordine confermato -> bolla CONSEGNATA) e' del
-- builder dbops.fn_pgtap_crea_ddt_da_ordine.
-- ============================================================

-- La merce viene FATTURATA: attivita' di commessa -> emissione -> riga di
-- fattura vera, agganciata all'AF. E' la catena che la madre risale per
-- copiare il prezzo, e va costruita per intero: senza `fattura_riga_id` la
-- madre rifiuta, ed e' la condizione che rende l'accredito impossibile.
CREATE OR REPLACE FUNCTION pg_temp.acc_fattura(p_segment varchar, p_qta numeric, p_prezzo numeric)
RETURNS bigint AS $$
DECLARE r RECORD; v_af bigint; v_fatt bigint; v_riga bigint;
BEGIN
  SELECT * INTO r FROM tmp_refs_acc;

  PERFORM vendite.fn_upsert_commessa_attivita(
    p_commessa_id                   => (SELECT commessa_id FROM tmp_com_acc),
    -- La riga NORMALE ha la sua sorgente (vincolo 20261012-27).
    p_sorgente_tipo_id => (SELECT s.id FROM config.sorgenti s WHERE s.codice_interno = 'COMMESSA'),
    p_sorgente_uid => ((SELECT commessa_id FROM tmp_com_acc))::text,
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
      (SELECT commessa_id FROM tmp_com_acc), true, false);

  SELECT af.id INTO v_af
    FROM vendite.attivita_fatturabili af
    JOIN vendite.commesse_attivita ca ON ca.id = af.commessa_attivita_id
   WHERE ca.segment_key = p_segment
   ORDER BY af.id DESC LIMIT 1;

  INSERT INTO vendite.fatture (registro_id, data, tipo_doc_fiscale_id, stato_doc_fiscale_id,
      emittente_soggetto_ruolo_id, billing_account_id, utility_id, valuta_id, tasso_cambio, meta)
  VALUES (r.registro_id, DATE '2026-07-31', r.tipo_doc_fiscale_id, r.stato_fatt_draft_id,
      r.emittente_sr_id, r.billing_account_id, r.utility_id, r.valuta_id, 1,
      jsonb_build_object('test_scope','pgtap_fn_accredita'))
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

-- ============================================================
-- FIXTURE
--   Partita A: consegnati 10 a 25 euro, fatturati 10, resi 3
--              -> tenuti 7, fatturati 10 -> accredito dovuto 3
-- ============================================================
CREATE TEMP TABLE tmp_com_acc AS
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id     => (SELECT billing_account_id FROM tmp_refs_acc),
  p_utility_id             => (SELECT utility_id FROM tmp_refs_acc),
  p_tipo_commessa          => 'AUTO',
  p_policy_fatturazione    => 'DA_DOCUMENTO',
  p_fatturazione_immediata => false,
  p_priorita_operativa     => 'NORMALE',
  p_competenza_dal         => DATE '2026-07-01',
  p_competenza_al          => DATE '2026-07-31',
  p_meta                   => '{}'::jsonb,
  p_force_new              => true) AS commessa_id;

SELECT vendite.fn_link_commessa_sorgente(
  p_commessa_id      => (SELECT commessa_id FROM tmp_com_acc),
  p_sorgente_tipo_id => (SELECT sorgente_root_id FROM tmp_refs_acc),
  p_sorgente_uid     => (SELECT commessa_id FROM tmp_com_acc)::text,
  p_sorgente_riga    => 1,
  p_meta             => '{}'::jsonb);

CREATE TEMP TABLE tmp_pa AS
SELECT b.ordine_riga_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('accredita riga reso',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_acc),
           p_quantita             => 10,
           p_prezzo               => 25,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_acc),
           p_fatturazione_trigger => 'CONSEGNATO') b;

CREATE TEMP TABLE tmp_pa_fattura AS
SELECT pg_temp.acc_fattura(
    script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pa)::text, (SELECT ddt_riga_id FROM tmp_pa)),
    10, 25) AS fattura_riga_id;

-- Il reso a credito di 3, confermato.
CREATE TEMP TABLE tmp_pa_reso AS
SELECT x.resi_riga_id
  FROM dbops.fn_pgtap_crea_reso('accredita riga reso', (SELECT ddt_id FROM tmp_pa), 3,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pa)) x;

-- ============================================================
-- 1) La fixture e' arrivata dove doveva: la coda vede l'accredito.
-- ============================================================
SELECT is(
  (SELECT q.accredito_dovuto FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  3::numeric,
  '1) fixture: la partita e'' in coda accrediti con accredito dovuto 3'
);

-- ============================================================
-- IL VERBO. ⭐ Il caso si costruisce PASSANDO DA QUI, non inserendo la riga
--    di rettifica a mano: una fixture scritta a mano potrebbe confermare un
--    ramo che nessun percorso reale attraversa.
-- ============================================================
CREATE TEMP TABLE tmp_esito AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pa_reso));

SELECT is(
  (SELECT count(*)::int FROM tmp_esito), 1,
  '2) il verbo crea UNA rettifica (la partita ha una sola riga di fattura)'
);

SELECT is(
  (SELECT ca.quantita FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_esito)),
  -3::numeric,
  '3) D-NC-2: la quantita'' e'' NEGATIVA — il segno sta nel numero, non in un''etichetta'
);

SELECT is(
  (SELECT ca.segment_key FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_esito)),
  (script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pa)::text, (SELECT ddt_riga_id FROM tmp_pa)) || '#RET:1')::varchar,
  '4) D-NC-1: il segmento e'' quello della SPEDIZIONE, col suffisso #RET:1'
);

SELECT is(
  (SELECT ca.tipo_movimento || '|' || nd.codice_interno || '|' || ca.stato_approvazione || '|' || ca.stato_emissione
     FROM vendite.commesse_attivita ca
     JOIN config.nature_doc_fiscale nd ON nd.id = ca.natura_doc_id
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_esito)),
  'RETTIFICA|NOTA_CREDITO|APPROVATA|NON_EMESSA',
  '5) la rettifica e'' RETTIFICA + natura NOTA_CREDITO + gia'' approvata, da emettere'
);

SELECT is(
  (SELECT ca.prezzo_snapshot FROM vendite.commesse_attivita ca
    WHERE ca.id = (SELECT commessa_attivita_id FROM tmp_esito)),
  (SELECT fr.prezzo_unitario FROM vendite.fatture_righe fr
    WHERE fr.id = (SELECT fattura_riga_id FROM tmp_pa_fattura))::numeric(22,10),
  '6) N-1: il prezzo e'' COPIATO dalla riga di fattura, mai ricalcolato'
);

SELECT is(
  (SELECT a.qta::text || '|' || a.qta_partita::text || '|' || (a.fattura_riga_rettificata_id = (SELECT fattura_riga_id FROM tmp_pa_fattura))::text
     FROM vendite.resi_righe_accrediti a
    WHERE a.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  '3.000000|3.000000|true',
  '7) il ponte registra il fatto: quantita'' di documento, di merce e riga rettificata'
);

-- ⭐ Il presidio dell'idempotenza NON dipende da una finestra temporale: la
--    coda sottrae la quota gia' accreditata, quindi la riga esce SUBITO, prima
--    ancora che l'attivita' fatturabile esista.
SELECT is(
  (SELECT count(*)::int FROM vendite.vw_resi_da_accreditare q
    WHERE q.resi_riga_id = (SELECT resi_riga_id FROM tmp_pa_reso)),
  0,
  '8) la riga esce dalla coda AL VERBO, non alla generazione della fattura'
);

-- ⚠️ SQLSTATE esplicito: senza, throws_ok accetterebbe qualunque errore, anche
--    il crash del guard stesso. P0001 dice «errore di dominio»; per distinguere
--    QUALE, il discriminante e' la frase.
SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_accredita_riga_reso(%s) $$,
         (SELECT resi_riga_id FROM tmp_pa_reso)),
  '%accredito gia%',
  '9) due click non producono due accrediti: il secondo trova il fatto gia'' scritto'
);

-- ============================================================
-- 10) IL CONTRATTO DEL §2, che e' la ragione per cui il cantiere esiste:
--     emessa la rettifica, i «fatturati» scendono e la differenza torna a
--     zero. Se non accadesse, la coda continuerebbe a chiedere l'accredito
--     per sempre anche a nota di credito emessa.
-- ============================================================
SELECT vendite.fn_emit_attivita_fatturabili_da_commessa(
    (SELECT commessa_id FROM tmp_com_acc), true, false);

SELECT is(
  (SELECT p.differenza::text || '|' || p.stato || '|' || p.rettificato::text
     FROM vendite.vw_partite_merce p
    WHERE p.ddt_riga_id = (SELECT ddt_riga_id FROM tmp_pa)),
  '0.000000|PAREGGIATA|-3.000000',
  '10) il contratto del S2: la partita PAREGGIA e il contatore ha visto la nota di credito'
);

SELECT is(
  (SELECT af.fattura_riga_rettificata_id FROM vendite.attivita_fatturabili af
    WHERE af.commessa_attivita_id = (SELECT commessa_attivita_id FROM tmp_esito)),
  (SELECT fattura_riga_id FROM tmp_pa_fattura),
  '11) D-NC-9: la tracciabilita'' riga-a-riga arriva fino all''attivita'' fatturabile'
);

-- ============================================================
-- Guard
-- ============================================================
CREATE TEMP TABLE tmp_pb AS
SELECT b.ordine_riga_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('accredita riga reso',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_acc),
           p_quantita             => 5,
           p_prezzo               => 12,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_acc),
           p_fatturazione_trigger => 'CONSEGNATO') b;
CREATE TEMP TABLE tmp_pb_reso AS
SELECT x.resi_riga_id
  FROM dbops.fn_pgtap_crea_reso('accredita riga reso', (SELECT ddt_id FROM tmp_pb), 2,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pb)) x;

-- La partita B non e' mai stata fatturata: tenuti 3, fatturati 0 -> il conto
-- e' a credito, non a debito, e la riga non entra in coda.
SELECT throws_like(
  format($$ SELECT * FROM vendite.fn_accredita_riga_reso(%s) $$,
         (SELECT resi_riga_id FROM tmp_pb_reso)),
  '%nessun accredito dovuto in coda%',
  '12) una riga di reso NON in coda non si accredita: la coda e'' la sede del numero'
);

SELECT throws_ok(
  $$ SELECT * FROM vendite.fn_accredita_riga_reso(NULL) $$,
  'P0001', NULL,
  '13) guard sul parametro: id nullo -> errore di dominio, mai normalizzazione silenziosa'
);

-- ============================================================
-- 14) ⭐ IL TETTO DEL DOCUMENTO. Un secondo reso sulla stessa partita non puo'
--     accreditare piu' di quanto la riga di fattura abbia fatturato. E' la
--     misura che parla la lingua del DOCUMENTO invece che della merce, e prima
--     di questo cantiere non esisteva.
--     Si scrive direttamente sul ponte perche' il tetto e' del GUARD: passando
--     dalla madre lo fermerebbe prima il conto della merce, e il ramo che si
--     vuole collaudare resterebbe non attraversato.
-- ============================================================
SELECT throws_like(
  format($$ INSERT INTO vendite.resi_righe_accrediti
              (resi_riga_id, fattura_riga_rettificata_id, qta, qta_partita, gruppo, commessa_attivita_id)
            VALUES (%s, %s, 999, 999, 'DDT_VENDITA:test#RET:9', %s) $$,
         (SELECT resi_riga_id FROM tmp_pa_reso),
         (SELECT fattura_riga_id FROM tmp_pa_fattura),
         (SELECT commessa_attivita_id FROM tmp_esito)),
  '%gia'' accreditati%',
  '14) tetto del DOCUMENTO: non si accredita piu'' di quanto la riga di fattura abbia fatturato'
);

-- ============================================================
-- 15) ⭐ LA CORSIA ORD. Partita C: consegnati 8, fatturati 8 sul segmento
--     dell'ORDINE (non della spedizione), resi 2 -> accredito dovuto 2.
--     Il verbo legge il gruppo dal segmento ORD (v_seg_ord) e scrive la
--     rettifica sulla SPEDIZIONE (D-NC-1), col prezzo della riga di fattura
--     d'ordine. Rev 2026-10-18 (D-3b di brief-db-plancache-funzioni-con-query-
--     incorporate): il verbo entra in commesse_attivita da segment_base, e la
--     corsia ORD e' il ramo che nessun altro test costruiva.
-- ============================================================
CREATE TEMP TABLE tmp_pc AS
SELECT b.ordine_riga_id, b.ddt_id, b.ddt_uid, b.ddt_riga_id
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('accredita riga reso',
           p_billing_account_id   => (SELECT billing_account_id FROM tmp_refs_acc),
           p_quantita             => 8,
           p_prezzo               => 30,
           p_articolo_id          => (SELECT articolo_id FROM tmp_refs_acc),
           p_fatturazione_trigger => 'CONSEGNATO') b;

CREATE TEMP TABLE tmp_pc_fattura AS
SELECT pg_temp.acc_fattura(
    ('ORDINE_VENDITA:' || (SELECT o.uid FROM vendite.ordini_righe orr
                  JOIN vendite.ordini o ON o.id = orr.ordine_id
                 WHERE orr.id = (SELECT ordine_riga_id FROM tmp_pc))::text
     || ':R:' || (SELECT ordine_riga_id FROM tmp_pc)::text)::varchar,
    8, 30) AS fattura_riga_id;

CREATE TEMP TABLE tmp_pc_reso AS
SELECT x.resi_riga_id
  FROM dbops.fn_pgtap_crea_reso('accredita riga reso', (SELECT ddt_id FROM tmp_pc), 2,
           p_ddt_riga_id => (SELECT ddt_riga_id FROM tmp_pc)) x;

CREATE TEMP TABLE tmp_esito_c AS
SELECT * FROM vendite.fn_accredita_riga_reso((SELECT resi_riga_id FROM tmp_pc_reso));

SELECT is(
  (SELECT count(*)::text || '|' || max(ca.quantita)::text || '|' || max(ca.prezzo_snapshot)::numeric(12,2)::text
          || '|' || bool_and(e.fattura_riga_rettificata_id = (SELECT fattura_riga_id FROM tmp_pc_fattura))::text
          || '|' || max(ca.segment_key)
     FROM tmp_esito_c e
     JOIN vendite.commesse_attivita ca ON ca.id = e.commessa_attivita_id),
  '1|-2.000000|30.00|true|' || script.fn_segment_key('DDT_VENDITA', (SELECT ddt_uid FROM tmp_pc)::text, (SELECT ddt_riga_id FROM tmp_pc)) || '#RET:1',
  '15) corsia ORD: fatturato sull''ordine, la rettifica nasce sulla spedizione col prezzo della riga d''ordine'
);

-- ============================================================
-- 16) ⭐ PIN DI FORMA (D-3b, 2026-10-18): ogni lettura di commesse_attivita
--     nel verbo ENTRA da segment_base. Sotto la policy della tabella un LIKE
--     o uno split_part su segment_key non arriva all'indice (non sono
--     leakproof, linee-guida-sql §8.5-bis): la tabella si legge intera, con
--     la policy pagata riga per riga, a ogni accredito. I risultati restano
--     giusti — lo dicono i test qui sopra — e se ne accorge solo il tempo:
--     per questo il presidio e' sul testo. Commenti esclusi.
--     Se una lettura nuova di commesse_attivita entra nel verbo, deve entrare
--     anch'essa da segment_base (o da un'altra uguaglianza leakproof: allora
--     questo pin va riscritto, non spento).
-- ============================================================
SELECT is(
  (SELECT (SELECT count(*) FROM regexp_matches(s.src, 'FROM\s+vendite\.commesse_attivita\s+ca\M', 'g'))::text
          || '|' ||
          (SELECT count(*) FROM regexp_matches(s.src, 'ca\.segment_base\s*(=|IN\M)', 'g'))::text
     FROM (SELECT regexp_replace(p.prosrc, '--[^\n]*', '', 'g') AS src
             FROM pg_proc p
            WHERE p.oid = 'vendite.fn_accredita_riga_reso(bigint)'::regprocedure) s),
  '3|3',
  '16) pin di forma: le 3 letture di commesse_attivita del verbo entrano da segment_base'
);

SELECT * FROM finish();
ROLLBACK;
