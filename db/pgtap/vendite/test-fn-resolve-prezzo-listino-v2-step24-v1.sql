-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- rev 2026-10-26 (brief-modello-documento-vendita §11): i quattro contratti (OV, ESC, AGG, LV) si attivano
--   con dbops.fn_pgtap_porta_a_stato (il verbo del contratto), non con un UPDATE dello stato: la porta
--   lo ferma. Nessuna attesa cambiata.
-- pgTAP test per Zero ERP
--
-- Test: Step 2.4 — fn_resolve_prezzo_listino_v2 con tipo_eccezione
--       Migration: 20260515-15
--
-- Indice test (1..9):
--   Struttura:
--   1)  Funzione fn_resolve_prezzo_listino_v2 presente
--   2)  RETURNS TABLE include colonna tipo_eccezione
--
--   Eccezioni contratto (STADIO 1a):
--   3)  Contratto ATTIVO + riga OVERRIDE -> origine=CONTRATTO_OVERRIDE, tipo_eccezione=OVERRIDE
--   4)  Contratto ATTIVO + riga ESCLUSIONE -> raise E_ARTICOLO_ESCLUSO_DA_CONTRATTO (P0001)
--   5)  Contratto ATTIVO + riga AGGIUNTA -> origine=CONTRATTO_AGGIUNTA, tipo_eccezione=AGGIUNTA
--
--   Listino dal contratto (STADIO 1b):
--   6)  (COND) Contratto ATTIVO + versione fissata + no eccezione -> origine=CONTRATTO_LISTINO
--   7)  (COND) Contratto ATTIVO + versione fissata -> usa quella versione (non versione corrente)
--
--   Parametri invalidi:
--   8)  Chiamata con p_ba_id = NULL -> raise P0001
--   9)  Chiamata con p_uom_id = 0   -> raise P0001
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

-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.1.2, A-D2): il
--   listino e' COSTRUITO, con una versione valida da oggi. Prima era «il primo
--   listino attivo per id» del DB, e il fixture ci ATTIVA dei contratti: da quel
--   giorno un contratto con un listino senza versione in vigore non si attiva
--   piu', e l'esito dipendeva da cosa c'era sulla macchina.
--   I test 6-7 cercano una versione in vigore CON la riga dell'articolo 3: sul
--   listino costruito (senza righe) fanno skip, come facevano gia' sul listino
--   preso dai dati quando non aveva una versione in vigore.
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.6.5): il
--   cliente e il billing account sono COSTRUITI (dbops.fn_pgtap_crea_cliente_ba),
--   come il listino. Prima erano «il primo BA per id» del DB: su un database
--   ricostruito da zero (CI) non c'e' nessun BA e il file era nel registro dei
--   rossi di CI per questo.
CREATE TEMP TABLE tmp_v2_cli AS
SELECT billing_account_id, istanza_utility_id, utility_id
  FROM dbops.fn_pgtap_crea_cliente_ba(
    'resolve v2 step24',
    (SELECT u.id FROM config.utilities u
      WHERE NOT EXISTS (SELECT 1 FROM config.tipi_utenze tu WHERE tu.utility_id = u.id)
      ORDER BY u.id LIMIT 1));

CREATE TEMP TABLE tmp_v2_listino AS
SELECT listino_id, listino_versione_id FROM dbops.fn_pgtap_crea_listino(
    (SELECT utility_id FROM tmp_v2_cli), 'resolve v2 step24');

CREATE TEMP TABLE tmp_v2_ctx AS
SELECT
    ba.billing_account_id  AS ba_id,
    ba.istanza_utility_id,
    ba.utility_id,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'DRAFT'  LIMIT 1) AS id_draft,
    (SELECT id FROM config.stati_doc_contratti WHERE codice_interno = 'ATTIVO' LIMIT 1) AS id_attivo,
    (SELECT id FROM catalogo.unita_misura       WHERE attivo = TRUE             ORDER BY id LIMIT 1) AS uom_id,
    (SELECT listino_id FROM tmp_v2_listino) AS listino_id,
    -- emittente_soggetto_ruolo_id: qualsiasi valore > 0 (non usato in STADIO 1)
    1::bigint AS emittente_soggetto_ruolo_id
  FROM tmp_v2_cli ba;

-- 3 articoli non-composite per le eccezioni
-- ⚠️ Rev 2026-10-07 (brief-db-offerta-emissione-ed-erogazione §C.9, giro B3): le righe
--   stanno nel PERIMETRO dell'articolo, e la tipologia dell'articolo dev'essere fra quelle
--   della utility del cliente. Articoli SENZA tipologia (decide la natura) che ammettono
--   UNA_TANTUM/FISSA, chiesto alla sede unica; le righe ereditano l'erogazione (era
--   CANONE scritto a mano). Prima: i primi tre per id, che su dbdev sono PRODOTTI e la
--   utility del cliente costruito (ENE) non li prevede.
-- ⛔ rev 2026-10-13 (brief-db-articoli-ammessi-per-documento, Lotto 3b, A-5): i
--   tre articoli si COSTRUISCONO e stanno nel listino del contratto. Prima si
--   pescavano dal catalogo, fuori listino: un'OVERRIDE o un'ESCLUSIONE di un
--   articolo che il listino non ha non modifica niente (la riga non si vedeva
--   nemmeno), e dal Lotto 3b e' rifiutata. Erogazione e fonte le eredita il DB
--   dalla tipologia del listino; la quantita' c'e' se la fonte e' FISSA.
--   ⭐ Con l'articolo 3 a listino i test 6-7 (versione fissata) girano davvero:
--   prima dipendevano dal trovare una riga di listino nei dati, e si saltavano.
CREATE TEMP TABLE tmp_v2_arts AS
SELECT dbops.fn_pgtap_crea_articolo('PGT-V2S24-' || g, false) AS id, g AS rn
  FROM generate_series(1, 3) AS g;

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT listino_versione_id FROM tmp_v2_listino),
    ARRAY(SELECT id FROM tmp_v2_arts ORDER BY rn));

-- Scopo: la quantita' di una riga che eredita: 1 se la fonte di default e' FISSA.
CREATE OR REPLACE FUNCTION pg_temp.qta(p_articolo uuid)
RETURNS numeric LANGUAGE sql STABLE AS $fx$
  SELECT 1.00 FROM vendite.fn_articolo_erogazioni(p_articolo) e
   WHERE e.e_default AND e.fonte_quantita_attesa = 'FISSA' LIMIT 1;
$fx$;

-- Versione attiva del listino + riga con art[3] (per test 6-7 condizionali)
CREATE TEMP TABLE tmp_v2_lv AS
SELECT
    lv.id AS versione_id,
    lr.prezzo AS prezzo_listino
  FROM vendite.listini_versioni lv
  JOIN vendite.listini_righe lr ON lr.listino_versione_id = lv.id
 WHERE lv.listino_id = (SELECT listino_id FROM tmp_v2_ctx LIMIT 1)
   AND lv.validita @> script.fn_data_operativa()
   AND lv.attivo = TRUE
   AND lr.articolo_id = (SELECT id FROM tmp_v2_arts WHERE rn = 3)
   AND lr.uom_id = (SELECT uom_id FROM tmp_v2_ctx LIMIT 1)
   AND lr.attivo = TRUE
 LIMIT 1;

-- -------------------------------------------------------
-- Contratto per test 3 (OVERRIDE): DRAFT → riga → ATTIVO
-- Date 2070 (non overlap con altri BA tests)
-- -------------------------------------------------------
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, listino_id)
SELECT 'PGTAP_V2_OV',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2070-01-01', '2070-12-31', c.listino_id
  FROM tmp_v2_ctx c WHERE c.listino_id IS NOT NULL;

-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'OVERRIDE', 111.00, pg_temp.qta(a.id), NULL
  FROM vendite.contratti ca, tmp_v2_arts a
 WHERE ca.numero = 'PGTAP_V2_OV' AND a.rn = 1;

-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione dal verbo
--   (la porta ferma l'UPDATE diretto dello stato).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c WHERE c.numero = 'PGTAP_V2_OV';

-- -------------------------------------------------------
-- Contratto per test 4 (ESCLUSIONE): DRAFT → riga → ATTIVO
-- -------------------------------------------------------
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, listino_id)
SELECT 'PGTAP_V2_ESC',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2071-01-01', '2071-12-31', c.listino_id
  FROM tmp_v2_ctx c WHERE c.listino_id IS NOT NULL;

-- rev 2026-10-04 (brief-db-righe-esclusione-solo-non-si-vende): l'esclusione
--   nasce vuota (la qta_operativa 1 era un dato di vendita, ora rifiutato).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario)
SELECT ca.id, a.id, 'ESCLUSIONE', NULL
  FROM vendite.contratti ca, tmp_v2_arts a
 WHERE ca.numero = 'PGTAP_V2_ESC' AND a.rn = 2;

-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione dal verbo
--   (la porta ferma l'UPDATE diretto dello stato).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c WHERE c.numero = 'PGTAP_V2_ESC';

-- -------------------------------------------------------
-- Contratto per test 5 (AGGIUNTA): DRAFT, no listino → riga AGGIUNTA → ATTIVO
-- -------------------------------------------------------
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al)
SELECT 'PGTAP_V2_AGG',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2072-01-01', '2072-12-31'
  FROM tmp_v2_ctx c;

-- tipo_erogazione: obbligatoria su OVERRIDE/AGGIUNTA dal 2026-10-04 (brief-db-erogazione-obbligatoria-righe-fatturate).
INSERT INTO vendite.contratti_righe(contratto_id, articolo_id, tipo_eccezione, prezzo_unitario, qta_operativa,
       tipo_erogazione)
SELECT ca.id, a.id, 'AGGIUNTA', 222.00, pg_temp.qta(a.id), NULL
  FROM vendite.contratti ca, tmp_v2_arts a
 WHERE ca.numero = 'PGTAP_V2_AGG' AND a.rn = 1;

-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione dal verbo
--   (la porta ferma l'UPDATE diretto dello stato).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c WHERE c.numero = 'PGTAP_V2_AGG';

-- -------------------------------------------------------
-- Contratto per test 6-7 (CONTRATTO_LISTINO + versione fissata):
-- DRAFT + listino + no righe → ATTIVO (freeze setta versione se disponibile)
-- -------------------------------------------------------
INSERT INTO vendite.contratti(
    numero, billing_account_id, istanza_utility_id, utility_id,
    stato_doc_contratto_id, valido_dal, valido_al, listino_id)
SELECT 'PGTAP_V2_LV',
       c.ba_id, c.istanza_utility_id, c.utility_id,
       c.id_draft, '2073-01-01', '2073-12-31', c.listino_id
  FROM tmp_v2_ctx c
 WHERE c.listino_id IS NOT NULL
   AND (SELECT versione_id FROM tmp_v2_lv LIMIT 1) IS NOT NULL;

-- Transizione a ATTIVO (freeze setta listino_versione_id se versione trovata)
-- rev 2026-10-26 (brief-modello-documento-vendita §11): l'attivazione dal verbo
--   (la porta ferma l'UPDATE diretto dello stato).
SELECT dbops.fn_pgtap_porta_a_stato('vendite.contratti'::regclass, c.id, 'ATTIVO')
  FROM vendite.contratti c WHERE c.numero = 'PGTAP_V2_LV';

-- ============================================================
SELECT plan(9);
-- ============================================================

-- ============================================================
-- 1) Funzione fn_resolve_prezzo_listino_v2 presente
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1 FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_resolve_prezzo_listino_v2'
    ),
    '1) Funzione vendite.fn_resolve_prezzo_listino_v2 presente'
);

-- ============================================================
-- 2) RETURNS TABLE include colonna tipo_eccezione
-- ============================================================
SELECT ok(
    EXISTS (
        SELECT 1
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = 'vendite'
           AND p.proname = 'fn_resolve_prezzo_listino_v2'
           -- proretset=true + 'tipo_eccezione' in proallargtypes output columns
           AND 'tipo_eccezione' = ANY(
               SELECT unnest(p.proargnames)
           )
    ),
    '2) RETURNS TABLE contiene colonna tipo_eccezione'
);

-- ============================================================
-- 3) Contratto ATTIVO + OVERRIDE -> CONTRATTO_OVERRIDE + tipo_eccezione=OVERRIDE
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_V2_OV')
    THEN skip('Nessun listino disponibile per fixture OVERRIDE - skip', 1)
    ELSE ok(
        (SELECT r.origine = 'CONTRATTO_OVERRIDE' AND r.tipo_eccezione = 'OVERRIDE'
           FROM vendite.fn_resolve_prezzo_listino_v2(
               (SELECT id FROM tmp_v2_arts WHERE rn = 1),
               (SELECT uom_id FROM tmp_v2_ctx),
               '2070-06-01'::date,
               (SELECT ba_id FROM tmp_v2_ctx),
               (SELECT utility_id FROM tmp_v2_ctx)::integer,
               (SELECT emittente_soggetto_ruolo_id FROM tmp_v2_ctx),
               NULL::integer
           ) r),
        '3) Contratto ATTIVO + OVERRIDE -> origine=CONTRATTO_OVERRIDE, tipo_eccezione=OVERRIDE'
    )
END;

-- ============================================================
-- 4) Contratto ATTIVO + ESCLUSIONE -> raise E_ARTICOLO_ESCLUSO_DA_CONTRATTO
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_V2_ESC')
    THEN skip('Nessun listino disponibile per fixture ESCLUSIONE - skip', 1)
    ELSE throws_ok(
        format(
            $$SELECT * FROM vendite.fn_resolve_prezzo_listino_v2(
                %L::uuid, %s, '2071-06-01'::date, %s, %s::integer, %s, NULL::integer
            )$$,
            (SELECT id FROM tmp_v2_arts WHERE rn = 2),
            (SELECT uom_id FROM tmp_v2_ctx),
            (SELECT ba_id FROM tmp_v2_ctx),
            (SELECT utility_id FROM tmp_v2_ctx),
            (SELECT emittente_soggetto_ruolo_id FROM tmp_v2_ctx)
        ),
        'P0001',
        NULL,
        '4) Contratto ATTIVO + ESCLUSIONE -> raise E_ARTICOLO_ESCLUSO_DA_CONTRATTO'
    )
END;

-- ============================================================
-- 5) Contratto ATTIVO + AGGIUNTA -> CONTRATTO_AGGIUNTA + tipo_eccezione=AGGIUNTA
-- ============================================================
SELECT ok(
    (SELECT r.origine = 'CONTRATTO_AGGIUNTA' AND r.tipo_eccezione = 'AGGIUNTA'
       FROM vendite.fn_resolve_prezzo_listino_v2(
           (SELECT id FROM tmp_v2_arts WHERE rn = 1),
           (SELECT uom_id FROM tmp_v2_ctx),
           '2072-06-01'::date,
           (SELECT ba_id FROM tmp_v2_ctx),
           (SELECT utility_id FROM tmp_v2_ctx)::integer,
           (SELECT emittente_soggetto_ruolo_id FROM tmp_v2_ctx),
           NULL::integer,
           NULL::uuid
       ) r),
    '5) Contratto ATTIVO + AGGIUNTA -> origine=CONTRATTO_AGGIUNTA, tipo_eccezione=AGGIUNTA'
);

-- ============================================================
-- 6) Contratto ATTIVO + versione fissata + no eccezione -> CONTRATTO_LISTINO
--    SKIP se nessun contratto V2_LV creato o nessuna versione disponibile
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_V2_LV')
         OR (SELECT versione_id FROM tmp_v2_lv LIMIT 1) IS NULL
    THEN skip('Nessun listino/versione/riga disponibile per test CONTRATTO_LISTINO - skip', 1)
    ELSE ok(
        (SELECT r.origine = 'CONTRATTO_LISTINO'
           FROM vendite.fn_resolve_prezzo_listino_v2(
               (SELECT id FROM tmp_v2_arts WHERE rn = 3),
               (SELECT uom_id FROM tmp_v2_ctx),
               '2073-06-01'::date,
               (SELECT ba_id FROM tmp_v2_ctx),
               (SELECT utility_id FROM tmp_v2_ctx)::integer,
               (SELECT emittente_soggetto_ruolo_id FROM tmp_v2_ctx),
               NULL::integer,
               NULL::uuid
           ) r),
        '6) Contratto ATTIVO + versione fissata + no eccezione -> origine=CONTRATTO_LISTINO'
    )
END;

-- ============================================================
-- 7) Contratto ATTIVO + versione fissata -> usa quella versione (listino_versione_id output)
--    SKIP se condizioni test 6 non soddisfatte
-- ============================================================
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.contratti WHERE numero = 'PGTAP_V2_LV')
         OR (SELECT versione_id FROM tmp_v2_lv LIMIT 1) IS NULL
    THEN skip('Nessun listino/versione/riga disponibile per test versione fissata - skip', 1)
    ELSE ok(
        (SELECT r.listino_versione_id = (SELECT versione_id FROM tmp_v2_lv LIMIT 1)
           FROM vendite.fn_resolve_prezzo_listino_v2(
               (SELECT id FROM tmp_v2_arts WHERE rn = 3),
               (SELECT uom_id FROM tmp_v2_ctx),
               '2073-06-01'::date,
               (SELECT ba_id FROM tmp_v2_ctx),
               (SELECT utility_id FROM tmp_v2_ctx)::integer,
               (SELECT emittente_soggetto_ruolo_id FROM tmp_v2_ctx),
               NULL::integer,
               NULL::uuid
           ) r),
        '7) Contratto ATTIVO + versione fissata -> listino_versione_id output coincide con snapshot'
    )
END;

-- ============================================================
-- 8) p_ba_id = NULL -> raise P0001
-- ============================================================
SELECT throws_ok(
    $$SELECT * FROM vendite.fn_resolve_prezzo_listino_v2(
        gen_random_uuid(), 1, script.fn_data_operativa(), NULL, 1, 1, NULL::integer, NULL::uuid
    )$$,
    'P0001',
    NULL,
    '8) p_ba_id NULL -> raise E_PARAMETRO_INVALIDO'
);

-- ============================================================
-- 9) p_uom_id = 0 -> raise P0001
-- ============================================================
SELECT throws_ok(
    $$SELECT * FROM vendite.fn_resolve_prezzo_listino_v2(
        gen_random_uuid(), 0, script.fn_data_operativa(), 1, 1, 1, NULL::integer, NULL::uuid
    )$$,
    'P0001',
    NULL,
    '9) p_uom_id = 0 -> raise E_PARAMETRO_INVALIDO'
);

SELECT * FROM finish();
ROLLBACK;
