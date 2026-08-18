-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 6 (P-4) del cantiere «perimetro emittente»: la lista PILOTA
-- «Competenza — gruppi fatturabili» dichiara da quale emittente arriva la riga.
-- Brief: docs/it/dev/work-in-progress/brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §11.4, Q4
--
-- Elenco test (plan 5):
--   1) la vista espone `emittente_ragione_sociale`
--   2) la vista espone ANCORA `emittente_soggetto_ruolo_id` (nessuna regressione)
--   3) il catalogo ha la colonna emittente per la lista pilota
--   4) * COERENZA catalogo -> vista: il `campo_sorgente` dichiarato esiste davvero
--   5) * la lista pilota e' l'UNICA delle sei del perimetro ad averla (registro
--        di debito che cala: le altre cinque devono ancora guadagnarsela)
--
-- Scopo:
--  - il 4 e' il test che conta. Il «prezzo del biglietto» di P-2b dice che una
--    lista puo' dichiararsi multi-emittente SOLO se espone l'emittente nella
--    riga. Una riga di catalogo che punta a un campo inesistente e' una colonna
--    che si spunta e resta VUOTA: sembra la garanzia, e non lo e'. Qui si
--    verifica che il campo dichiarato esista nella vista.
--
-- ⚠️ NON si asseriscono i DATI. `vw_dash_competenza_gruppi` in questa istanza
--   e' vuota (nessuna attivita' fatturabile aperta): un `count(emittente_...)`
--   sarebbe 0 = 0, cioe' verde per sottrazione. Si verifica la STRUTTURA, che
--   e' quello che il passo 6 introduce, e i dati li verifica il consumo reale.
--
-- ⚠️ Il test 4 NON prova che la colonna arrivi a VIDEO: la lista ha
--   `vista_sql = NULL`, quindi le righe le compone il repository di dominio,
--   che elenca le colonne esplicitamente. Quella meta' e' la richiesta BE-2 del
--   brief e vive nel backend. Il DB garantisce che il campo esista; che venga
--   selezionato no.
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(5);

-- ============================================================
-- Asserzioni
-- ============================================================

SELECT has_column(
    'vendite', 'vw_dash_competenza_gruppi', 'emittente_ragione_sociale',
    '1. la vista espone emittente_ragione_sociale (P-4)'
);

SELECT has_column(
    'vendite', 'vw_dash_competenza_gruppi', 'emittente_soggetto_ruolo_id',
    '2. la vista espone ancora emittente_soggetto_ruolo_id (nessuna regressione)'
);

SELECT ok(
    EXISTS (
        SELECT 1
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.dash_competenza_gruppi'
           AND lc.campo_sorgente = 'emittente_ragione_sociale'
           AND lc.attivo
    ),
    '3. il catalogo ha la colonna emittente per la lista pilota'
);

-- ⭐ Il test che conta: cio' che il catalogo DICHIARA deve esistere davvero.
--    Una colonna che si spunta e resta vuota e' peggio di una colonna assente,
--    perche' *sembra* il collaudo che il flag multi_emittente pretendera'.
SELECT ok(
    NOT EXISTS (
        SELECT 1
          FROM ui.lista_colonna lc
          JOIN ui.lista_definizione ld ON ld.id = lc.lista_id
         WHERE ld.codice = 'vendite.dash_competenza_gruppi'
           AND lc.attivo
           AND lc.campo_sorgente = 'emittente_ragione_sociale'
           AND NOT EXISTS (
                   SELECT 1
                     FROM information_schema.columns c
                    WHERE c.table_schema = 'vendite'
                      AND c.table_name   = 'vw_dash_competenza_gruppi'
                      AND c.column_name  = lc.campo_sorgente)
    ),
    '4. * coerenza catalogo -> vista: il campo_sorgente dichiarato esiste davvero'
);

-- Il registro di debito: oggi UNA sola delle sei liste del perimetro ha la
-- colonna. Se un giorno questo numero sale senza che nessuno abbia fatto il
-- lavoro, vuol dire che qualcuno ha attaccato l'adesivo senza collaudare.
SELECT is(
    (SELECT count(DISTINCT ld.codice)
       FROM ui.lista_definizione ld
       JOIN ui.lista_colonna lc ON lc.lista_id = ld.id AND lc.attivo
      WHERE ld.codice IN ('vendite.lotti',
                          'vendite.dash_aperto_documenti',
                          'vendite.dash_backlog_documenti',
                          'vendite.dash_competenza_errori',
                          'vendite.dash_competenza_gruppi',
                          'vendite.dash_competenza_commesse')
        AND lc.campo_sorgente = 'emittente_ragione_sociale'),
    1::bigint,
    '5. * una sola delle sei liste del perimetro ha la colonna: la pilota'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
