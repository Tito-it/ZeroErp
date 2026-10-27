-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Test: Bug A (BOZZA non operativa) + Bug B (fn_contratto_righe_preview)
--       Migrations: 20260516-01..04
--
-- Indice test (1..8):
--   Struttura:
--   1)  Funzione fn_contratto_righe_preview presente
--   2)  RETURNS TABLE include colonna componenti (jsonb)
--
--   Bug A — resolver:
--   3)  Contratto con listino BOZZA-only: l'attivazione e' RIFIUTATA
--       (E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO). ⚠️ Rev 2026-10-07
--       (brief-db-offerta-emissione-ed-erogazione §C.1.2, decisione A-D2 di Tid):
--       fino a quel giorno il contratto si attivava con la versione NULL e qui si
--       provava che il resolver, poi, non usasse la BOZZA. Lo stato «ATTIVO su un
--       listino senza versione in vigore» non e' piu' costruibile: il Bug A e'
--       chiuso a monte, all'attivazione.
--   4)  Contratto ATTIVO con listino BOZZA+ATTIVA → freeze snapshot ATTIVA, resolver non raise
--
--   Bug A — guard AGGIUNTA:
--   5)  BOZZA presente nel listino → AGGIUNTA su contratto DRAFT non bloccata dal guard
--
--   Bug A — freeze trigger:
--   6)  Attivazione rifiutata con solo BOZZA → il contratto resta DRAFT, versione NULL
--       (la BOZZA non e' mai congelata)
--   7)  Attivazione con BOZZA+ATTIVA → listino_versione_id = id versione ATTIVA
--
--   Bug B — preview:
--   8)  fn_contratto_righe_preview con listino → almeno 1 riga restituita (COND)
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

-- ============================================================
-- Setup fixture
-- ============================================================

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): la riga
--   AGGIUNTA del test 5 sta nel PERIMETRO dell'articolo, e la sua tipologia dev'essere fra
--   quelle della utility del cliente. L'articolo ha la tipologia del listino copiato (il
--   primo attivo: le righe di listino lo pretendono), quindi il cliente si COSTRUISCE sulla
--   prima utility che ammette QUELLA tipologia (dbops.fn_pgtap_crea_cliente_ba).
--   ⛔ Non un cliente preso dal database: la prima versione di questa rev sceglieva il
--   primo billing account con la utility giusta, che su dbdev aveva gia' un contratto
--   attivo sovrapposto alle date del fixture (ex_contratti_no_overlap all'attivazione del
--   contratto MX). Un cliente nuovo non ha contratti. Prima ancora: il primo billing
--   account in assoluto, che su dbdev e' GAS e non ammette PRODOTTI.
CREATE TEMP TABLE tmp_bozza_cli AS
SELECT * FROM dbops.fn_pgtap_crea_cliente_ba(
    'bozza non operativa',
    (SELECT ltu.utility_id FROM config.listini_tipologie_utilities ltu
      WHERE ltu.attivo
        AND ltu.tipologia_id = (SELECT l.tipologia_id FROM vendite.listini l
                                 WHERE l.attivo = TRUE ORDER BY l.id LIMIT 1)
      ORDER BY ltu.utility_id LIMIT 1));

CREATE TEMP TABLE tmp_bozza_ctx AS
SELECT
    ba.billing_account_id   AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO' LIMIT 1) AS id_attivo,
    (SELECT id FROM catalogo.unita_misura WHERE attivo = TRUE ORDER BY id LIMIT 1) AS uom_id,
    1::bigint AS emittente_soggetto_ruolo_id
  FROM tmp_bozza_cli ba;

-- Articolo standalone per le righe listino di test
CREATE TEMP TABLE tmp_bozza_art AS
SELECT a.id
  FROM catalogo.articoli a
 WHERE a.attivo = TRUE AND a.is_composito = FALSE
 ORDER BY a.id
 LIMIT 1;

-- -------------------------------------------------------
-- Listino BOZZA-only: ha solo una versione BOZZA (per test 3 e 6)
-- Nota: CREATE TEMP TABLE ... AS WITH ins AS (INSERT ... RETURNING)
--       è la forma corretta per catturare l'RETURNING in PG.
-- -------------------------------------------------------
-- 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2: il listino del
--   documento e' della sua utility e del suo emittente (guard nuovo). Le due copie
--   del primo listino prendono la utility del CLIENTE (che ne ammette la tipologia
--   per costruzione, vedi tmp_bozza_cli) e l'emittente di chi agisce, a cui il z90
--   ha legato il cliente; prima ricopiavano utility ed emittente del listino dei dati.
CREATE TEMP TABLE tmp_lst_bozza_only AS
WITH ins AS (
    INSERT INTO vendite.listini(codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_BO_' || substr(gen_random_uuid()::text, 1, 8),
           'Test BOZZA-only', (SELECT utility_id FROM tmp_bozza_ctx), l.tipologia_id,
           script.fn_pgtap_emittente_sr_operatore()
      FROM vendite.listini l WHERE l.attivo = TRUE ORDER BY l.id LIMIT 1
    RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ver_bozza_only AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, stato)
    SELECT id, 'PGTAP-BO-V1', '2070-01-01'::date, 'BOZZA'
      FROM tmp_lst_bozza_only
    RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, a.id, ctx.uom_id, 55.00
  FROM tmp_ver_bozza_only v, tmp_bozza_art a, tmp_bozza_ctx ctx;

-- -------------------------------------------------------
-- Listino BOZZA+ATTIVA: ha BOZZA + ATTIVA entrambe coprenti 2071
-- (per test 4 e 7)
-- -------------------------------------------------------
CREATE TEMP TABLE tmp_lst_mixed AS
WITH ins AS (
    INSERT INTO vendite.listini(codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_MX_' || substr(gen_random_uuid()::text, 1, 8),
           'Test BOZZA+ATTIVA', (SELECT utility_id FROM tmp_bozza_ctx), l.tipologia_id,
           script.fn_pgtap_emittente_sr_operatore()
      FROM vendite.listini l WHERE l.attivo = TRUE ORDER BY l.id LIMIT 1
    RETURNING id
)
SELECT id FROM ins;

-- BOZZA (no no-overlap con ATTIVA: il vincolo è solo su stato=ATTIVA).
-- valido_dal = script.fn_data_operativa(): il freeze trigger usa script.fn_data_operativa() per il lookup,
-- quindi entrambe le versioni devono coprire script.fn_data_operativa() per essere trovate.
CREATE TEMP TABLE tmp_ver_mixed_bozza AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, stato)
    SELECT id, 'PGTAP-MX-BOZZA', script.fn_data_operativa(), 'BOZZA'
      FROM tmp_lst_mixed
    RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, a.id, ctx.uom_id, 99.99
  FROM tmp_ver_mixed_bozza v, tmp_bozza_art a, tmp_bozza_ctx ctx;

-- ATTIVA per stesso listino (INSERT diretto: guard solo su UPDATE OF stato).
-- valido_dal = script.fn_data_operativa(): freeze trigger la troverà e farà snapshot.
CREATE TEMP TABLE tmp_ver_mixed_attiva AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal, stato)
    SELECT id, 'PGTAP-MX-ATTIVA', script.fn_data_operativa(), 'ATTIVA'
      FROM tmp_lst_mixed
    RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, a.id, ctx.uom_id, 44.00
  FROM tmp_ver_mixed_attiva v, tmp_bozza_art a, tmp_bozza_ctx ctx;

-- -------------------------------------------------------
-- Contratto PGTAP_BO_CNT: listino BOZZA-only, date 2070
-- Resta DRAFT: l'attivazione e' il test 3, che ora la deve vedere rifiutata.
-- -------------------------------------------------------
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, listino_id, valido_dal, valido_al)
SELECT 'PGTAP_BO_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, (SELECT id FROM tmp_lst_bozza_only LIMIT 1),
       '2070-01-01'::date, '2070-12-31'::date
  FROM tmp_bozza_ctx c
 -- rev 2026-10-07 (giro B3): il cliente ora si costruisce, quindi il contratto nascerebbe
 --   anche dove il listino da copiare non c'e' (CI): senza listino non e' il caso del test.
 WHERE EXISTS (SELECT 1 FROM tmp_lst_bozza_only);

-- -------------------------------------------------------
-- Contratto PGTAP_MX_CNT: listino BOZZA+ATTIVA, date 2071
-- Freeze trigger trova ATTIVA → snapshot listino_versione_id = id ATTIVA.
-- -------------------------------------------------------
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, listino_id, valido_dal, valido_al)
SELECT 'PGTAP_MX_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, (SELECT id FROM tmp_lst_mixed LIMIT 1),
       '2071-01-01'::date, '2071-12-31'::date
  FROM tmp_bozza_ctx c
 -- rev 2026-10-07 (giro B3): il cliente ora si costruisce, quindi il contratto nascerebbe
 --   anche dove il listino da copiare non c'e' (CI): senza listino non e' il caso del test.
 WHERE EXISTS (SELECT 1 FROM tmp_lst_mixed);

-- rev 2026-10-27 (brief-modello-documento-vendita §11, debito del giro 8): il contratto ha la
--   porta sulla colonna di stato; l'attivazione passa dal verbo, che la fixture chiama con
--   emetti_contratto concessa (prima un UPDATE diretto, ora fermato dalla porta).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c
 WHERE c.numero = 'PGTAP_MX_CNT';

-- -------------------------------------------------------
-- Contratto PGTAP_GA_CNT: per test 5 (guard AGGIUNTA + BOZZA)
-- DRAFT con listino BOZZA-only. Non viene attivato.
-- -------------------------------------------------------
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, listino_id, valido_dal, valido_al)
SELECT 'PGTAP_GA_CNT', c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, (SELECT id FROM tmp_lst_bozza_only LIMIT 1),
       '2072-01-01'::date, '2072-12-31'::date
  FROM tmp_bozza_ctx c
 -- rev 2026-10-07 (giro B3): il cliente ora si costruisce, quindi il contratto nascerebbe
 --   anche dove il listino da copiare non c'e' (CI): senza listino non e' il caso del test.
 WHERE EXISTS (SELECT 1 FROM tmp_lst_bozza_only);

-- ============================================================
SELECT plan(8);
-- ============================================================

-- ============================================================
-- 1) fn_contratto_righe_preview presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_contratto_righe_preview'
    ),
    '1) Funzione vendite.fn_contratto_righe_preview presente'
);

-- ============================================================
-- 2) RETURNS TABLE include colonna componenti
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_contratto_righe_preview'
           AND 'componenti' = ANY(SELECT unnest(p.proargnames))
    ),
    '2) RETURNS TABLE contiene colonna componenti'
);

-- ============================================================
-- 3) Contratto con listino BOZZA-only: l'attivazione e' rifiutata
--    (rev 2026-10-07, A-D2). Prima passava con la versione NULL.
--    rev 2026-10-27 (§11, debito del giro 8): dal verbo vendite.fn_cambia_stato_contratto,
--    con emetti_contratto concessa (senza, il rifiuto sarebbe il permesso e non il listino).
--    Stessa attesa: il rifiuto lo dà il guard di transizione, che il verbo attraversa.
-- ============================================================
SELECT dbops.fn_pgtap_concedi_azione(current_setting('app.current_user_id')::integer, 'emetti_contratto');

SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_BO_CNT')
    THEN skip('Fixture PGTAP_BO_CNT non creata - skip', 1)
    ELSE throws_like(
        format(
            $q$SELECT * FROM vendite.fn_cambia_stato_contratto(%s, 'ATTIVO')$q$,
            (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_BO_CNT')),
        '%Impossibile attivare il contratto%',
        '3) Listino BOZZA-only: attivazione rifiutata (E_CONTRATTO_ATTIVAZIONE_SENZA_VERSIONE_LISTINO)'
    )
END;

-- ============================================================
-- 4) Contratto ATTIVO con BOZZA+ATTIVA → freeze ha snapshot ATTIVA
--    listino_versione_id = id versione ATTIVA (non id versione BOZZA)
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_MX_CNT')
         OR (SELECT id FROM tmp_ver_mixed_attiva LIMIT 1) IS NULL
    THEN skip('Fixture PGTAP_MX_CNT non creata - skip', 1)
    ELSE ok(
        (SELECT c.listino_versione_id = (SELECT id FROM tmp_ver_mixed_attiva LIMIT 1)
           FROM vendite.contratti c WHERE c.numero = 'PGTAP_MX_CNT'),
        '4) Freeze BOZZA+ATTIVA: snapshot = versione ATTIVA, non BOZZA'
    )
END;

-- ============================================================
-- 5) Guard AGGIUNTA con BOZZA presente → LIVES_OK
--    La BOZZA ha l'articolo nel listino ma non è operativa: AGGIUNTA ammessa
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_GA_CNT')
    THEN skip('Fixture PGTAP_GA_CNT non creata - skip', 1)
    ELSE lives_ok(
        -- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
        format(
            $$INSERT INTO vendite.contratti_righe(
                contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
                tipo_erogazione)
              SELECT c.id, %L::uuid, 'AGGIUNTA', 111.00, 1.00, 'UNA_TANTUM'
                FROM vendite.contratti c WHERE c.numero = 'PGTAP_GA_CNT'$$,
            (SELECT id FROM tmp_bozza_art LIMIT 1)
        ),
        '5) Guard AGGIUNTA non bloccata da BOZZA (BOZZA non operativa)'
    )
END;

-- ============================================================
-- 6) Attivazione rifiutata con BOZZA-only → resta DRAFT, versione NULL
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_BO_CNT')
    THEN skip('Fixture PGTAP_BO_CNT non creata - skip', 1)
    ELSE ok(
        (SELECT c.listino_versione_id IS NULL
                AND c.stato_doc_contratto_id = (SELECT id_draft FROM tmp_bozza_ctx)
           FROM vendite.contratti c WHERE c.numero = 'PGTAP_BO_CNT'),
        '6) BOZZA-only: il contratto resta DRAFT e la BOZZA non e'' congelata'
    )
END;

-- ============================================================
-- 7) Freeze con BOZZA+ATTIVA → listino_versione_id = id ATTIVA
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_MX_CNT')
         OR (SELECT id FROM tmp_ver_mixed_attiva LIMIT 1) IS NULL
    THEN skip('Fixture PGTAP_MX_CNT non creata - skip', 1)
    ELSE ok(
        (SELECT c.listino_versione_id = (SELECT id FROM tmp_ver_mixed_attiva LIMIT 1)
           FROM vendite.contratti c WHERE c.numero = 'PGTAP_MX_CNT'),
        '7) Freeze BOZZA+ATTIVA: listino_versione_id = versione ATTIVA'
    )
END;

-- ============================================================
-- 8) fn_contratto_righe_preview → almeno 1 riga per contratto con listino
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_MX_CNT')
    THEN skip('Fixture PGTAP_MX_CNT non creata - skip', 1)
    ELSE ok(
        (SELECT COUNT(*) > 0
           FROM vendite.fn_contratto_righe_preview(
               (SELECT id FROM vendite.contratti WHERE numero = 'PGTAP_MX_CNT')
           )),
        '8) fn_contratto_righe_preview su contratto ATTIVO restituisce almeno 1 riga'
    )
END;

SELECT * FROM finish();
ROLLBACK;
