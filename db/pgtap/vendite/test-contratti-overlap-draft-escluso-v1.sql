-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Overlap contratti — i DRAFT sono ESCLUSI dal vincolo (esclusivita' solo
--       all'attivazione). Brief "Overlap contratti: escludere i DRAFT".
--       Migrations 20260602-17..22.
--
-- Indice test (1..8):
--   Struttura:
--   1) partecipa_overlap_snapshot e' colonna GENERATED
--   2) ex_contratti_no_overlap referenzia partecipa_overlap_snapshot
--   3) fn_contratto_sovrapposto referenzia partecipa_overlap_snapshot
--   Comportamento:
--   4) due DRAFT sovrapposti (stessa quadrupla) -> ammessi
--   5) DRAFT sovrapposto a un ATTIVO -> ammesso (prepara successione)
--   6) attivazione di un contratto sovrapposto a un ATTIVO -> bloccata (P0001: dal
--      2026-10-20 la ferma il guard di transizione, col codice; la difesa dura
--      dell'EXCLUDE e' provata in test-contratto-attiva-spento-se-sovrapposto-v1)
--   7) fn_contratto_sovrapposto: NULL se l'unico "conflitto" e' un DRAFT
--   8) fn_contratto_sovrapposto: ritorna l'incumbent quando e' ATTIVO
--
-- La fixture deriva quadrupla + emittente_fiscale_id da un contratto esistente
-- (coerenza con i guard operatore/emittente); usa periodi 2080+ -> nessun overlap
-- con i dati reali. Self-clean via ROLLBACK.
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
DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

CREATE TEMP TABLE tmp_ovl_ctx AS
SELECT c.billing_account_id  AS ba_id,
       c.istanza_utility_id,
       c.utility_id,
       c.ambito,
       c.emittente_fiscale_id,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
       (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO' LIMIT 1) AS id_attivo,
       (SELECT a.id FROM catalogo.articoli a
         WHERE a.attivo = TRUE AND a.is_composito = FALSE
         -- rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): l'articolo
   --   sta nel PERIMETRO delle righe: senza tipologia (decide la natura, la utility del
   --   cliente non conta) e con UNA_TANTUM/FISSA ammessa, chiesto alla sede unica.
   AND a.listino_tipologia_id IS NULL
   AND EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(a.id) e
                WHERE e.tipo_erogazione = 'UNA_TANTUM' AND e.fonte_quantita_attesa = 'FISSA')
         ORDER BY a.id LIMIT 1) AS articolo_id
  FROM vendite.contratti c
 WHERE c.emittente_fiscale_id IS NOT NULL
   AND c.ambito IS NOT NULL
 ORDER BY c.id
 LIMIT 1;

SELECT plan(8);

-- 1) partecipa_overlap_snapshot GENERATED
SELECT is(
    (SELECT a.attgenerated FROM pg_attribute a
       JOIN pg_class c ON c.oid = a.attrelid
       JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname='vendite' AND c.relname='contratti'
        AND a.attname='partecipa_overlap_snapshot'),
    's'::"char",
    '1) partecipa_overlap_snapshot e'' una colonna GENERATED STORED'
);

-- 2) EXCLUDE referenzia partecipa_overlap_snapshot
SELECT ok(
    (SELECT pg_get_constraintdef(con.oid)
       FROM pg_constraint con
      WHERE con.conname='ex_contratti_no_overlap' AND con.contype='x')
    ILIKE '%partecipa_overlap_snapshot%',
    '2) ex_contratti_no_overlap usa il predicato partecipa_overlap_snapshot'
);

-- 3) fn_contratto_sovrapposto referenzia partecipa_overlap_snapshot
SELECT ok(
    (SELECT pg_get_functiondef(p.oid)
       FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
      WHERE n.nspname='vendite' AND p.proname='fn_contratto_sovrapposto')
    ILIKE '%partecipa_overlap_snapshot%',
    '3) fn_contratto_sovrapposto usa partecipa_overlap_snapshot'
);

-- 4) Due DRAFT sovrapposti (stessa quadrupla, finestra W1) -> ammessi
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
       utility_id, ambito, emittente_fiscale_id, stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_OVL_D1', ba_id, istanza_utility_id, utility_id, ambito, emittente_fiscale_id, id_draft,
       '2080-01-01'::date, '2080-12-31'::date FROM tmp_ovl_ctx;

SELECT lives_ok(
    $$INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
         utility_id, ambito, emittente_fiscale_id, stato_doc_contratto_id, valido_dal, valido_al)
      SELECT 'PGTAP_OVL_D2', ba_id, istanza_utility_id, utility_id, ambito, emittente_fiscale_id, id_draft,
             '2080-06-01'::date, '2081-05-31'::date FROM tmp_ovl_ctx$$,
    '4) Due DRAFT sovrapposti sulla stessa quadrupla: ammessi'
);

-- 5) ATTIVO + DRAFT sovrapposto (finestra W2) -> draft ammesso
--    L'ATTIVO ha bisogno di una riga AGGIUNTA con prezzo per poter essere attivato.
INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
       utility_id, ambito, emittente_fiscale_id, stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_OVL_A2', ba_id, istanza_utility_id, utility_id, ambito, emittente_fiscale_id, id_draft,
       '2082-01-01'::date, '2082-12-31'::date FROM tmp_ovl_ctx;
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT c.id, ctx.articolo_id, 'AGGIUNTA', 100.00, 1.00, 'UNA_TANTUM'
  FROM vendite.contratti c, tmp_ovl_ctx ctx WHERE c.numero='PGTAP_OVL_A2';
UPDATE vendite.contratti SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ovl_ctx)
 WHERE numero = 'PGTAP_OVL_A2';

SELECT lives_ok(
    $$INSERT INTO vendite.contratti(numero, billing_account_id, istanza_utility_id,
         utility_id, ambito, emittente_fiscale_id, stato_doc_contratto_id, valido_dal, valido_al)
      SELECT 'PGTAP_OVL_B2', ba_id, istanza_utility_id, utility_id, ambito, emittente_fiscale_id, id_draft,
             '2082-06-01'::date, '2083-05-31'::date FROM tmp_ovl_ctx$$,
    '5) DRAFT sovrapposto a un ATTIVO: ammesso (preparazione successione)'
);

-- Riga AGGIUNTA anche su B2, cosi' l'attivazione supera il guard "no listino/righe"
-- e arriva al check di overlap (altrimenti fallirebbe per il motivo sbagliato).
-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT c.id, ctx.articolo_id, 'AGGIUNTA', 100.00, 1.00, 'UNA_TANTUM'
  FROM vendite.contratti c, tmp_ovl_ctx ctx WHERE c.numero='PGTAP_OVL_B2';

-- 6) Attivazione del DRAFT sovrapposto all'ATTIVO -> bloccata.
--    ⚠️ Rev 2026-10-20 (20261020-21): prima la fermava l'EXCLUDE (23P01). Ora il
--    guard di transizione, che scatta prima, solleva E_CONTRATTO_OVERLAP_ESISTENTE
--    (P0001) col numero del contratto in conflitto: il codice e il motivo di
--    «Attiva» sono provati in test-contratto-attiva-spento-se-sovrapposto-v1.
SELECT throws_ok(
    $$UPDATE vendite.contratti
         SET stato_doc_contratto_id = (SELECT id_attivo FROM tmp_ovl_ctx)
       WHERE numero = 'PGTAP_OVL_B2'$$,
    'P0001',
    NULL,
    '6) Attivazione di un contratto sovrapposto a un ATTIVO: bloccata dal guard di transizione'
);

-- 7) fn_contratto_sovrapposto: NULL se il solo "conflitto" e' un DRAFT (W1)
SELECT ok(
    (SELECT vendite.fn_contratto_sovrapposto(
        ctx.ba_id, ctx.istanza_utility_id, ctx.utility_id, ctx.ambito,
        '2080-03-01'::date, '2080-09-30'::date) IS NULL
      FROM tmp_ovl_ctx ctx),
    '7) fn_contratto_sovrapposto ignora i DRAFT: ritorna NULL'
);

-- 8) fn_contratto_sovrapposto: ritorna l'incumbent ATTIVO (W2)
SELECT is(
    (SELECT vendite.fn_contratto_sovrapposto(
        ctx.ba_id, ctx.istanza_utility_id, ctx.utility_id, ctx.ambito,
        '2082-03-01'::date, '2082-09-30'::date)
      FROM tmp_ovl_ctx ctx),
    (SELECT id FROM vendite.contratti WHERE numero='PGTAP_OVL_A2'),
    '8) fn_contratto_sovrapposto ritorna l''incumbent ATTIVO sovrapposto'
);

SELECT * FROM finish();
ROLLBACK;
