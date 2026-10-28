-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- rev 2026-10-28 (brief-modello-documento-vendita §16, giro 12): la versione nasce in bozza (senza
--   stato), prende la riga e si attiva dal verbo (dbops.fn_pgtap_porta_a_stato).
--
-- Test: core fn_espandi_listino_versione + fn_offerta_righe_espanse
--       + regressione fn_contratto_righe_preview (rifattorizzata sul core).
--       Migrations: 20260604-02..04 (db-brief-offerta-righe-espanse).
--
-- Indice test (1..9):
--   Struttura:
--   1) fn_espandi_listino_versione presente
--   2) fn_offerta_righe_espanse presente
--   3) fn_offerta_righe_espanse: output ordine-ready include iva_id
--   4) fn_offerta_righe_espanse: output include componenti (jsonb)
--   5) fn_contratto_righe_preview ancora presente (regressione)
--   Core (fixture listino, articolo standalone, prezzo 100):
--   6) variazione PERCENTUALE 10 -> prezzo_da_listino = 110
--   7) variazione VALORE_FISSO 5 -> prezzo_da_listino = 105
--   8) nessuna variazione -> prezzo_da_listino = 100
--   Comportamentale offerta (COND, data-dependent):
--   9) fn_offerta_righe_espanse non restituisce righe ESCLUSIONE
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
-- Setup fixture: listino + versione + 1 riga standalone prezzo 100
-- ============================================================
CREATE TEMP TABLE tmp_ole_ctx AS
SELECT
    (SELECT id FROM catalogo.unita_misura WHERE attivo = TRUE ORDER BY id LIMIT 1) AS uom_id
;

CREATE TEMP TABLE tmp_ole_art AS
SELECT a.id
  FROM catalogo.articoli a
 WHERE a.attivo = TRUE AND a.is_composito = FALSE
 ORDER BY a.id
 LIMIT 1;

CREATE TEMP TABLE tmp_ole_lst AS
WITH ins AS (
    INSERT INTO vendite.listini(codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id)
    SELECT 'PGTAP_OLE_' || substr(gen_random_uuid()::text, 1, 8),
           'Test offerta righe espanse', l.utility_id, l.tipologia_id, l.emittente_soggetto_ruolo_id
      FROM vendite.listini l WHERE l.attivo = TRUE ORDER BY l.id LIMIT 1
    RETURNING id
)
SELECT id FROM ins;

CREATE TEMP TABLE tmp_ole_ver AS
WITH ins AS (
    INSERT INTO vendite.listini_versioni(listino_id, codice_versione, valido_dal)
    SELECT id, 'PGTAP-OLE-V1', script.fn_data_operativa()
      FROM tmp_ole_lst
    RETURNING id
)
SELECT id FROM ins;

INSERT INTO vendite.listini_righe(listino_versione_id, articolo_id, uom_id, prezzo)
SELECT v.id, a.id, ctx.uom_id, 100.00
  FROM tmp_ole_ver v, tmp_ole_art a, tmp_ole_ctx ctx;

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', v.id, 'ATTIVA')
  FROM tmp_ole_ver v;

-- ============================================================
SELECT plan(9);
-- ============================================================

-- 1) core presente
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'vendite' AND p.proname = 'fn_espandi_listino_versione'),
    '1) fn_espandi_listino_versione presente'
);

-- 2) fn offerta presente
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'vendite' AND p.proname = 'fn_offerta_righe_espanse'),
    '2) fn_offerta_righe_espanse presente'
);

-- 3) output ordine-ready: iva_id
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'vendite' AND p.proname = 'fn_offerta_righe_espanse'
               AND 'iva_id' = ANY(SELECT unnest(p.proargnames))),
    '3) fn_offerta_righe_espanse: output include iva_id (ordine-ready)'
);

-- 4) output include componenti
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'vendite' AND p.proname = 'fn_offerta_righe_espanse'
               AND 'componenti' = ANY(SELECT unnest(p.proargnames))),
    '4) fn_offerta_righe_espanse: output include componenti (jsonb)'
);

-- 5) regressione: preview contratti ancora presente
SELECT ok(
    EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
             WHERE n.nspname = 'vendite' AND p.proname = 'fn_contratto_righe_preview'),
    '5) fn_contratto_righe_preview ancora presente (regressione)'
);

-- 6) core PERCENTUALE 10 -> 110
SELECT is(
    (SELECT prezzo_da_listino
       FROM vendite.fn_espandi_listino_versione(
                (SELECT id FROM tmp_ole_ver), 'PERCENTUALE', 10)
      WHERE articolo_id = (SELECT id FROM tmp_ole_art)),
    110.00::numeric,
    '6) core: variazione PERCENTUALE 10% su prezzo 100 -> 110'
);

-- 7) core VALORE_FISSO 5 -> 105
SELECT is(
    (SELECT prezzo_da_listino
       FROM vendite.fn_espandi_listino_versione(
                (SELECT id FROM tmp_ole_ver), 'VALORE_FISSO', 5)
      WHERE articolo_id = (SELECT id FROM tmp_ole_art)),
    105.00::numeric,
    '7) core: variazione VALORE_FISSO +5 su prezzo 100 -> 105'
);

-- 8) core nessuna variazione -> 100
SELECT is(
    (SELECT prezzo_da_listino
       FROM vendite.fn_espandi_listino_versione(
                (SELECT id FROM tmp_ole_ver), NULL, 0)
      WHERE articolo_id = (SELECT id FROM tmp_ole_art)),
    100.00::numeric,
    '8) core: nessuna variazione -> prezzo invariato 100'
);

-- 9) COND: su un'offerta esistente, nessuna riga espansa e' ESCLUSIONE
SELECT CASE
    WHEN NOT EXISTS (SELECT 1 FROM vendite.offerte_commerciali)
    THEN skip('Nessuna offerta in tabella - skip test comportamentale', 1)
    ELSE ok(
        NOT EXISTS (
            SELECT 1
              FROM vendite.fn_offerta_righe_espanse(
                       (SELECT id FROM vendite.offerte_commerciali ORDER BY id LIMIT 1))
             WHERE origine = 'ESCLUSIONE'
        ),
        '9) fn_offerta_righe_espanse: nessuna riga ESCLUSIONE in output (rimosse)'
    )
END;

SELECT * FROM finish();
ROLLBACK;
