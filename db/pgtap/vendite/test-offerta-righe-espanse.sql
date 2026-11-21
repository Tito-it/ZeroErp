-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
--   Core, la riga di listino del prezzo (brief-db-provenienza-prezzo-segue-il-prezzo §8.16):
--  10) la riga semplice cita la sua riga di listino
--
-- rev 2026-11-21 (giro 5 della provenienza del prezzo): la fixture si costruisce il
--   suo mondo. Prendeva «il primo listino attivo» e «il primo articolo» del
--   database: sullo scratch vuoto non c'erano, e 6-8 erano rossi (NULL) per i dati,
--   non per il codice che provano. Ora listino, versione e articolo li fanno le
--   fixture comuni (dbops.fn_pgtap_crea_listino in bozza, fn_pgtap_crea_articolo).
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
CREATE TEMP TABLE tmp_ole_lis AS
SELECT * FROM dbops.fn_pgtap_crea_listino(
    (SELECT min(u.id) FROM config.utilities u
      WHERE EXISTS (SELECT 1 FROM config.listini_tipologie_utilities ltu
                     WHERE ltu.utility_id = u.id AND ltu.attivo)),
    'offerta righe espanse', p_in_bozza => true);

CREATE TEMP TABLE tmp_ole_ver AS
SELECT listino_versione_id AS id FROM tmp_ole_lis;

CREATE TEMP TABLE tmp_ole_art AS
SELECT dbops.fn_pgtap_crea_articolo(
           ('PGT-OLE-' || substr(md5(clock_timestamp()::text), 1, 10))::varchar, false,
           p_listino_tipologia_id => (SELECT tipologia_id FROM tmp_ole_lis)) AS id;

SELECT dbops.fn_pgtap_listino_aggiungi_articoli(
    (SELECT id FROM tmp_ole_ver), ARRAY[(SELECT id FROM tmp_ole_art)], 100);

SELECT dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni', v.id, 'ATTIVA')
  FROM tmp_ole_ver v;

-- ============================================================
SELECT plan(10);
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

-- 10) la riga semplice cita la sua riga di listino
SELECT is(
    (SELECT e.listino_riga_id
       FROM vendite.fn_espandi_listino_versione((SELECT id FROM tmp_ole_ver), NULL, 0) e
      WHERE e.articolo_id = (SELECT id FROM tmp_ole_art)),
    (SELECT lr.id FROM vendite.listini_righe lr
      WHERE lr.listino_versione_id = (SELECT id FROM tmp_ole_ver)
        AND lr.articolo_id = (SELECT id FROM tmp_ole_art)),
    '10) core: la riga semplice cita la sua riga di listino (listino_riga_id)'
);

SELECT * FROM finish();
ROLLBACK;
