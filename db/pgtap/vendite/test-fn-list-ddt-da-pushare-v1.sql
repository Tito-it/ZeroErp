-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-25 (brief-db-pgtap-reso-costruito, giro D-4): le bolle da ordine dei casi A (tmp_ddt_a, tmp_ddt_conf) da dbops.fn_pgtap_crea_ddt_da_ordine (p_data, p_data_ordine, p_fatturazione_trigger), la bolla autonoma del caso B da dbops.fn_pgtap_crea_ddt_senza_ordine (8 a 45, SPEDITO); resta a mano la bolla senza BA del test 9 (il caso). La riga della bolla A perde in bozza il prezzo che la madre copia (A-2): il test 5 prova il fallback via fulfillment.
-- rev 2026-10-25 (brief-modello-documento-vendita §7, giro 5): pg_temp.spedisci porta la bolla a SPEDITO con dbops.fn_pgtap_porta_a_stato, non piu' con gli UPDATE diretti dello stato che la porta ora rifiuta.
-- rev 2026-10-24 (brief-modello-documento-vendita Q-4): il mondo (azienda, operatore, contesto, cliente con BA) si costruisce con dbops.fn_pgtap_crea_mondo_cliente; prima BA, emittente e ruolo del cliente erano «il primo BA del database con un emittente», assente su un database ricostruito da zero.
-- rev 2026-10-20 (brief-db-grammatica-unica-documenti §13.5-ter, 2e): le chiavi del push col codice della sorgente (PREVENTIVO:, DDT_VENDITA:, ORDINE_VENDITA:, CONTRATTO:, ATTIVITA_CONSUMI:), stessa forma di script.fn_segment_key carattere per carattere.
-- pgTAP test per Zero ERP
-- Test: vendite.fn_list_ddt_da_pushare (Caso A: da ordine, Caso B: autonomo)
--       + trgfn_ddt_normalize (ereditarieta` billing fields)
-- ------------------------------------------------------------
-- Indice test (1..12):
-- 1) fn_list_ddt_da_pushare presente
-- 2) Riferimenti minimi disponibili
-- 3) Caso A: DDT da ordine (trigger SPEDITO, DDT SPEDITO) restituito
-- 4) Caso A: billing_account ereditato da ordine sorgente
-- 5) Caso A: prezzo ereditato da ordine riga via fulfillment
-- 6) Caso A: DDT da ordine con trigger CONFERMATO escluso
-- 7) Caso B: DDT autonomo SPEDITO con billing_account restituito
-- 8) Caso B: prezzo da ddt_righe.prezzo_unitario
-- 9) Caso B: DDT autonomo VENDITA senza billing_account non si emette (rev 2026-10-09)
-- 10) Segment key formato corretto (DDT_VENDITA:<uid>:R:<riga_id>)
-- 11) prezzo_bloccato = TRUE se prezzo presente
-- 12) Filtro p_billing_account_id rispettato
-- ------------------------------------------------------------

BEGIN;
-- ⚠️ Vincoli DIFFERITI: senza questa riga il test smetterebbe di verificarli.
--   Un trigger DEFERRABLE INITIALLY DEFERRED scatta al COMMIT, e qui il COMMIT
--   non arriva mai (si chiude in ROLLBACK): sarebbero saltati in silenzio, e il
--   file sarebbe verde per sottrazione. IMMEDIATE li riporta a scattare a fine
--   di ogni istruzione. In testa e non in coda: in coda scatterebbero dopo il
--   cleanup, su righe ormai cancellate.
--   Brief: brief-db-pgtap-runner-rls-baseline §19.
SET CONSTRAINTS ALL IMMEDIATE;

-- Contesto applicativo: questo test gira come gira l'applicazione (ruolo
-- OPERATORE + RLS attiva), non come owner. Senza, con FORCE ROW LEVEL
-- SECURITY disattivo l'owner salta la RLS e il test non la esercita mai.
-- Brief: brief-db-pgtap-runner-rls-baseline §8.
-- ⭐ rev 2026-10-24 (Q-4): il mondo si COSTRUISCE — azienda, operatore,
--   contesto aperto su di lui e un cliente fatturabile legato a quella
--   azienda — al posto del contesto nudo e del «primo BA del database».
-- pgtap-contesto: escluso — il contesto lo apre dbops.fn_pgtap_crea_mondo_cliente
CREATE TEMP TABLE tmp_mondo AS
SELECT * FROM dbops.fn_pgtap_crea_mondo_cliente('PGTAP-LDDT');

SELECT plan(12);

-- ============================================================
-- 0) Funzione presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'vendite'
      AND p.proname = 'fn_list_ddt_da_pushare'
  ),
  'fn_list_ddt_da_pushare presente'
);

-- ============================================================
-- 0b) Riferimenti minimi
-- ============================================================
CREATE TEMP TABLE tmp_refs_ddt AS
SELECT
  -- rev 2026-10-24 (Q-4): BA, emittente e ruolo del cliente dal mondo
  --   costruito, non pescati. Il BA e' legato all'azienda di chi agisce,
  --   quindi trgfn_ordini_guard_emittente_ba trova la coppia coerente.
  m.billing_account_id AS billing_account_id,
  -- NB: fn_get_emittente_fiscale_pk (PK), non _id: e' la funzione con cui
  -- trgfn_ordini_guard_emittente_ba verifica la coerenza emittente<->BA.
  anagrafiche.fn_get_emittente_fiscale_pk(m.billing_account_id) AS emittente_fiscale_id,
  -- rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-4/D-5): il ruolo del
  --   cliente e' quello del BA: le FK composte fk_ordini_ba_cliente e
  --   fk_ddt_ba_cliente rifiutano un ruolo scollegato.
  m.cliente_soggetto_ruolo_id AS soggetto_ruolo_id,
  -- ⭐ Articolo COSTRUITO e NON gestito a magazzino (rev 2026-10-02). Prima era
  --   «l'ultimo articolo attivo del catalogo»: se quello era gestito, la bolla
  --   muoveva merce, e la porta del registro (trgfn_ddt_guard_transizione,
  --   Regola 3, 20260928-71) rifiutava il passaggio a EMESSO fatto con l'UPDATE
  --   di pg_temp.spedisci (E_DDT_STATO_SOLO_DA_VERBO). Il test misura il lister
  --   del push, non il registro di magazzino: la bolla non deve muovere merce,
  --   e non deve dipenderlo dal catalogo della macchina.
  dbops.fn_pgtap_crea_articolo('PGTAP-LDDT-ART', false) AS articolo_id,
  -- Stato ordine
  (SELECT s.id
     FROM config.stati_doc_ordini s
    WHERE s.codice = 'CONFERMATO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_ordine_confermato_id,
  -- Stati DDT
  (SELECT s.id
     FROM config.stati_doc_ddt s
    WHERE s.codice = 'SPEDITO' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_ddt_spedito_id,
  -- rev 2026-09-22: i DDT nascono in DRAFT e si SPEDISCONO nel verso vero
  -- (righe, indirizzo CON, EMESSO, SPEDITO): il BB delle righe
  -- (trgfn_doc_righe_lock_fuori_bozza) non ammette piu' una riga in un
  -- documento nato fuori bozza.
  (SELECT s.id
     FROM config.stati_doc_ddt s
    WHERE s.codice = 'DRAFT' AND s.attivo IS TRUE
    LIMIT 1
  ) AS stato_ddt_draft_id,
  (SELECT id FROM config.tipi_indirizzi WHERE codice_interno = 'CON') AS tipo_ind_con_id,
  -- Causale di trasporto: dal 2026-07-18 (step 5b, DL-28) il lister fa un INNER
  -- JOIN su config.causali_trasporto con fatturabile IS TRUE, e VENDITA e' la
  -- sola fatturabile. Senza causale il DDT non e' piu' eleggibile al push.
  (SELECT c.id
     FROM config.causali_trasporto c
    WHERE c.codice = 'VENDITA'
    LIMIT 1
  ) AS causale_vendita_id,
  -- Sorgenti
  (SELECT s.id
     FROM config.sorgenti s
    WHERE s.codice = 'DDT_VENDITA' AND s.attivo IS TRUE
    LIMIT 1
  ) AS sorgente_ddt_tipo_id
FROM tmp_mondo m;

-- Porta un DDT nato in DRAFT fino a SPEDITO nel verso vero: indirizzo CON,
-- poi le transizioni contigue (EMESSO, SPEDITO). rev 2026-09-22.
-- rev 2026-10-25 (§7, giro 5): i passi col verbo, da dbops.fn_pgtap_porta_a_stato
--   (la porta sullo stato rifiuta l'UPDATE diretto); solleva gli stessi errori
--   dei guard d'emissione, che il caso B senza BA aspetta.
CREATE OR REPLACE FUNCTION pg_temp.spedisci(p_ddt bigint)
RETURNS void AS $$
DECLARE r RECORD;
BEGIN
  SELECT * INTO r FROM tmp_refs_ddt;
  INSERT INTO vendite.ddt_indirizzi (ddt_id, tipo_indirizzo_id, snapshot)
  VALUES (p_ddt, r.tipo_ind_con_id, '{"display":"CON"}'::jsonb) ON CONFLICT DO NOTHING;
  PERFORM dbops.fn_pgtap_porta_a_stato('vendite.ddt', p_ddt, 'SPEDITO');
END $$ LANGUAGE plpgsql;

SELECT ok(
  (SELECT billing_account_id IS NOT NULL
      AND soggetto_ruolo_id IS NOT NULL
      AND articolo_id IS NOT NULL
      AND stato_ordine_confermato_id IS NOT NULL
      AND stato_ddt_spedito_id IS NOT NULL
      AND sorgente_ddt_tipo_id IS NOT NULL
   FROM tmp_refs_ddt),
  'Riferimenti minimi disponibili'
);

-- ============================================================
-- Caso A: Setup ordine + DDT + fulfillment
--   Ordine con fatturazione_trigger = SPEDITO
--   DDT con stato SPEDITO, collegato via fulfillment
-- ============================================================

-- La bolla da ordine dal builder: ordine confermato del 2026-07-01 (riga 10
-- a 30, trigger SPEDITO), bolla del 2026-07-05 generata dalla madre, in bozza.
-- Il BA la bolla lo eredita dall'ordine.
-- ⭐ Il test 5 prova il prezzo ereditato VIA FULFILLMENT: la madre copia il
--   prezzo sulla riga di bolla (A-2), quindi qui la riga in bozza lo perde e
--   il lister lo deve leggere dalla riga d'ordine. Poi SPEDITO per la matrice.
CREATE TEMP TABLE tmp_a AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_da_ordine('PGTAP-LDDT A', 'DRAFT',
         (SELECT billing_account_id FROM tmp_refs_ddt),
         p_quantita => 10, p_prezzo => 30, p_articolo_id => (SELECT articolo_id FROM tmp_refs_ddt),
         p_fatturazione_trigger => 'SPEDITO',
         p_data => DATE '2026-07-05', p_data_ordine => DATE '2026-07-01');

UPDATE vendite.ddt_righe dr SET prezzo_unitario = NULL
 WHERE dr.ddt_id = (SELECT ddt_id FROM tmp_a);

SELECT dbops.fn_pgtap_porta_a_stato('vendite.ddt', (SELECT ddt_id FROM tmp_a), 'SPEDITO');

CREATE TEMP TABLE tmp_ordine_a AS
SELECT o.id, o.uid, o.billing_account_id
  FROM vendite.ordini o
 WHERE o.id = (SELECT ordine_id FROM tmp_a);

CREATE TEMP TABLE tmp_ddt_a AS SELECT ddt_id AS id, ddt_uid AS uid FROM tmp_a;

-- ============================================================
-- Test 3: Caso A restituito
-- ============================================================
CREATE TEMP TABLE tmp_result_ddt AS
SELECT *
FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL);

SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_ddt rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_a)
  ),
  'Caso A: DDT da ordine (trigger SPEDITO, DDT SPEDITO) restituito'
);

-- ============================================================
-- Test 4: billing_account ereditato da ordine
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_ddt rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_a)
      AND rd.billing_account_id = (SELECT billing_account_id FROM tmp_ordine_a)
  ),
  'Caso A: billing_account ereditato da ordine sorgente'
);

-- ============================================================
-- Test 5: prezzo ereditato da ordine riga via fulfillment
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM tmp_result_ddt rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_a)
      AND rd.prezzo_snapshot = 30.000000
  ),
  'Caso A: prezzo ereditato da ordine riga via fulfillment'
);

-- ============================================================
-- Test 6: DDT da ordine con fatturazione_trigger=CONFERMATO escluso
--   Creo un altro ordine con trigger CONFERMATO e DDT collegato.
--   L'ordine pusha su conferma, il DDT non deve pushare.
-- ============================================================
-- Dal builder: ordine del 2026-07-01 con la riga 5 a 20 e il trigger
-- ereditato dal BA (CONFERMATO), bolla del 2026-07-10 portata a SPEDITO.
CREATE TEMP TABLE tmp_ddt_conf AS
SELECT b.ddt_id AS id, b.ddt_uid AS uid
  FROM dbops.fn_pgtap_crea_ddt_da_ordine('PGTAP-LDDT conf', 'SPEDITO',
         (SELECT billing_account_id FROM tmp_refs_ddt),
         p_quantita => 5, p_prezzo => 20, p_articolo_id => (SELECT articolo_id FROM tmp_refs_ddt),
         p_data => DATE '2026-07-10', p_data_ordine => DATE '2026-07-01') b;

SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_conf)
  ),
  'Caso A: DDT da ordine con fatturazione_trigger CONFERMATO escluso'
);

-- ============================================================
-- Caso B: DDT autonomo
-- ============================================================

-- DDT autonomo con billing_account_id e stato SPEDITO, dal builder: del
-- 2026-07-15, una riga 8 a 45 (il prezzo che il test 8 legge).
CREATE TEMP TABLE tmp_b AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_senza_ordine('PGTAP-LDDT autonomo', 'SPEDITO',
         (SELECT billing_account_id FROM tmp_refs_ddt),
         p_quantita => 8, p_prezzo => 45, p_articolo_id => (SELECT articolo_id FROM tmp_refs_ddt),
         p_data => DATE '2026-07-15');

CREATE TEMP TABLE tmp_ddt_b AS SELECT ddt_id AS id, ddt_uid AS uid FROM tmp_b;
CREATE TEMP TABLE tmp_ddt_b_riga AS SELECT ddt_riga_id AS id FROM tmp_b;

-- ============================================================
-- Test 7: Caso B restituito
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
  ),
  'Caso B: DDT autonomo SPEDITO con billing_account restituito'
);

-- ============================================================
-- Test 8: prezzo da ddt_righe.prezzo_unitario
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
      AND rd.prezzo_snapshot = 45.000000
  ),
  'Caso B: prezzo da ddt_righe.prezzo_unitario'
);

-- ============================================================
-- Test 9: DDT autonomo senza billing_account escluso
-- ============================================================
CREATE TEMP TABLE tmp_ddt_no_ba AS
WITH ins AS (
  INSERT INTO vendite.ddt (
    destinatario_soggetto_ruolo_id,
    stato_doc_ddt_id, data,
    emittente_fiscale_id, causale_trasporto_id, storicizza, meta
  )
  SELECT
    r.soggetto_ruolo_id,
    r.stato_ddt_draft_id, DATE '2026-07-20',
    -- Senza BA il default emittente non ha nulla da cui derivare (e il guard
    -- emittente<->BA salta): va passato esplicito, la colonna e' NOT NULL.
    r.emittente_fiscale_id,
    -- causale valorizzata anche qui: questo DDT resta escluso perche' non ha
    -- billing_account (caso 9), non per la causale — l'asserzione deve
    -- continuare a misurare cio' che dice di misurare
    r.causale_vendita_id,
    false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'no_ba')
  FROM tmp_refs_ddt r
  RETURNING id, uid
)
SELECT * FROM ins;

INSERT INTO vendite.ddt_righe (
  ddt_id, riga_nr, articolo_id, descrizione,
  qta_operativa, quantita, prezzo_unitario, iva_id, attivo,
  storicizza, meta
)
SELECT
  d.id, 1, r.articolo_id, 'Riga DDT senza BA',
  -- prezzo e iva: il gate di emissione vuole un prezzo risolvibile su causale
  -- fatturabile (rev 22-09). L'esclusione dal push resta per il BA assente.
  3.000000, 3.000000, 5.000000, (SELECT i.id FROM config.iva i WHERE i.attivo IS TRUE ORDER BY i.id LIMIT 1), true,
  false, jsonb_build_object('test_scope', 'pgtap_fn_list_ddt', 'case', 'no_ba')
FROM tmp_ddt_no_ba d, tmp_refs_ddt r;

-- ⭐ rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-2): una bolla VENDITA
--   manda merce a un cliente e senza billing account NON SI EMETTE (motivo
--   E_DDT_CLIENTE_OBBLIGATORIO). Lo stato che questo caso costruiva — spedita
--   senza BA, quindi esclusa dal push — il modello non lo ammette piu': il caso
--   misura ora la regola che lo impedisce. L'esclusione SENZA_BA della diagnosi
--   resta per un BA che chi legge non vede.
SELECT throws_like(
  format('SELECT pg_temp.spedisci(%s)', (SELECT id FROM tmp_ddt_no_ba)),
  '%manda la merce a un cliente%',
  'Caso B: DDT autonomo VENDITA senza billing_account non si emette (D-2)'
);

-- ============================================================
-- Test 10: Segment key formato corretto
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
      AND rd.segment_key = 'DDT_VENDITA:' || (SELECT uid FROM tmp_ddt_b)::text
                            || ':R:' || (SELECT id FROM tmp_ddt_b_riga)::text
  ),
  'Segment key formato corretto (DDT_VENDITA:<uid>:R:<riga_id>)'
);

-- ============================================================
-- Test 11: prezzo_bloccato = TRUE se prezzo presente
-- ============================================================
SELECT ok(
  EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, NULL, NULL) rd
    WHERE rd.ddt_id = (SELECT id FROM tmp_ddt_b)
      AND rd.prezzo_bloccato IS TRUE
      AND rd.prezzo_snapshot IS NOT NULL
  ),
  'prezzo_bloccato = TRUE se prezzo presente'
);

-- ============================================================
-- Test 12: Filtro p_billing_account_id rispettato
-- ============================================================
SELECT ok(
  NOT EXISTS (
    SELECT 1
    FROM vendite.fn_list_ddt_da_pushare(NULL, -999999, NULL) rd
    WHERE rd.ddt_id IN (
      (SELECT id FROM tmp_ddt_a),
      (SELECT id FROM tmp_ddt_b)
    )
  ),
  'Filtro p_billing_account_id rispettato'
);

SELECT * FROM finish();
ROLLBACK;
