-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- pgTAP test per Zero ERP
--
-- Passo 6 (P-4) del cantiere «perimetro emittente»: la lista PILOTA
-- «Competenza — gruppi fatturabili» dichiara da quale emittente arriva la riga.
-- Brief: brief-db-perimetro-emittente-liste-e-gerarchia-ba.md §11.4, Q4
--
-- Elenco test (plan 5):
--   1) la vista espone `emittente_ragione_sociale`
--   2) la vista espone ANCORA `emittente_soggetto_ruolo_id` (nessuna regressione)
--   3) il catalogo ha la colonna emittente per la lista pilota
--   4) * COERENZA catalogo -> vista: il `campo_sorgente` dichiarato esiste davvero
--   5) * tutte e sei le liste del perimetro dichiarano la colonna a catalogo
--        (passo 8, META' DB, completo)
--   6) * la colonna dichiarata e' PIENA, non solo esistente
--   7)   almeno una vista del perimetro ha righe (il 6 non e' vacuo)
--
-- Scopo:
--  - il 4 e' il test che conta. Il «prezzo del biglietto» di P-2b dice che una
--    lista puo' dichiararsi multi-emittente SOLO se espone l'emittente nella
--    riga. Una riga di catalogo che punta a un campo inesistente e' una colonna
--    che si spunta e resta VUOTA: sembra la garanzia, e non lo e'. Qui si
--    verifica che il campo dichiarato esista nella vista.
--
-- ⛔ ~~NON si asseriscono i DATI. `vw_dash_competenza_gruppi` in questa istanza
--   e' vuota (nessuna attivita' fatturabile aperta): un `count(emittente_...)`
--   sarebbe 0 = 0, cioe' verde per sottrazione.~~
--   🔴 **SBAGLIATO, e corretto il 2026-08-18.** Quella vista NON e' vuota: lo
--   e' solo per una sessione SENZA operatore. Il suo filtro di perimetro passa
--   da `fn_get_emittenti_scope_sr_ids`, che dopo P-2a risponde `'{}'` all'attore
--   nullo — fail-closed, cioe' il cantiere che funziona. Nel contesto in cui
--   questo file gira (operatore vero, riga 68) la vista rende **74 righe**.
--   ⚠️ La stessa frase l'ha ripetuta il backend il 2026-08-18 leggendo la vista
--   da psql: e' un errore che si fa in tre, non una svista. Da qui il test 6.
--
-- ⚠️ Il test 4 NON prova che la colonna arrivi a VIDEO: le liste hanno
--   `vista_sql = NULL`, quindi le righe le compone il repository di dominio,
--   che elenca le colonne esplicitamente. Quella meta' e' la richiesta BE-2 del
--   brief e vive nel backend. Il DB garantisce che il campo esista; che venga
--   selezionato no.
--
-- ============================================================================
-- rev 2026-08-18 — il test 5 ha fatto il suo lavoro, e va riscritto proprio
-- per questo.
--
-- Diceva: «una sola delle sei ha la colonna: la pilota», e avvertiva che se il
-- numero fosse salito senza il lavoro dietro voleva dire adesivo senza
-- collaudo. Il numero e' salito a SEI col commit di Fase E (714efd6e7), che ha
-- messo a catalogo la riga emittente per tutte e sei le liste.
--
-- ⭐ Meta' del lavoro c'e' davvero: cinque delle sei viste-sorgente espongono
-- `emittente_ragione_sociale`, e il test 4 — ora GENERALIZZATO a tutte — lo
-- verifica invece di fidarsi. Il registro di debito quindi non e' piu' «quante
-- liste hanno la riga di catalogo» (sono tutte), ma si ribasa su cio' che il
-- DB possiede: la riga c'e' E il campo dichiarato esiste alla sorgente.
--
-- 🔴 L'altra meta' NON c'e', e il DB non puo' vederla: il repository di dominio
-- SELEZIONA `emittente_ragione_sociale` solo per la PILOTA
-- (`vendite_repository.py:1293`). Per le altre cinque la colonna si spunta e
-- resta vuota — esattamente cio' che questo file chiama «peggio di una colonna
-- assente». Non e' un difetto di questo test ne' del catalogo: e' la richiesta
-- BE-2, che ora e' scritta lista per lista nel brief §13.
--
-- 🔴 E `vendite.lotti` sta peggio delle altre quattro: non ha nemmeno una
-- vista-sorgente. Il repository compone da `vendite.fatturazione_lotti`, che
-- porta `emittente_soggetto_ruolo_id` ma NON la ragione sociale — quindi li'
-- il campo dichiarato non esiste da nessuna parte nel DB, e serve una JOIN che
-- oggi nessuno fa. Per questo e' l'unica esclusa dalla mappa del test 4, con
-- il motivo dichiarato e non taciuto.
-- ============================================================================
-- ------------------------------------------------------------

BEGIN;

DO $ctx$ BEGIN PERFORM script.fn_pgtap_set_contesto_operatore(); END $ctx$;

SET CONSTRAINTS ALL IMMEDIATE;

SELECT plan(7);

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

-- ⭐ Il test che conta, ora su TUTTE le liste del perimetro e non sulla sola
--    pilota: cio' che il catalogo DICHIARA deve esistere davvero alla sorgente.
--    Una colonna che si spunta e resta vuota e' peggio di una colonna assente,
--    perche' *sembra* il collaudo che il flag multi_emittente pretendera'.
--
--    ⚠️ La mappa lista -> vista sta QUI e non nel catalogo perche' le sei liste
--    hanno `vista_sql = NULL`: la sorgente la sceglie il repository di dominio.
--    E' verificata sul codice BE, non indovinata (vendite_repository.py e
--    commesse_repository.py). `vendite.lotti` non compare: non ha una vista,
--    compone da `vendite.fatturazione_lotti` — vedi la nota 🔴 in testa.
CREATE TEMP TABLE tmp_perimetro_liste (lista_codice text, vista text);
INSERT INTO tmp_perimetro_liste VALUES
    ('vendite.dash_competenza_gruppi',   'vw_dash_competenza_gruppi'),
    ('vendite.dash_competenza_errori',   'vw_dash_competenza_errori'),
    ('vendite.dash_aperto_documenti',    'vw_dash_aperto_documenti'),
    ('vendite.dash_backlog_documenti',   'vw_dash_backlog_documenti'),
    -- il drill-down commesse aggrega vw_dash_competenza_attivita
    ('vendite.dash_competenza_commesse', 'vw_dash_competenza_attivita');

SELECT is(
    (SELECT count(*)::int
       FROM tmp_perimetro_liste m
       JOIN ui.lista_definizione ld ON ld.codice = m.lista_codice
       JOIN ui.lista_colonna lc
         ON lc.lista_id = ld.id
        AND lc.attivo
        AND lc.campo_sorgente = 'emittente_ragione_sociale'
      WHERE EXISTS (
            SELECT 1
              FROM information_schema.columns c
             WHERE c.table_schema = 'vendite'
               AND c.table_name   = m.vista
               AND c.column_name  = lc.campo_sorgente)),
    5,
    '4. * coerenza catalogo -> vista su tutte le liste mappate: il campo_sorgente dichiarato esiste davvero'
);

-- Il registro di debito, ribasato. Il passo 8 ha portato la riga di catalogo su
-- tutte e sei: questa e' la meta' DB, ed e' completa. Se il numero SCENDE
-- qualcuno ha tolto una riga; se la mappa del test 4 e questo numero divergono,
-- e' comparsa una lista nel perimetro senza che nessuno l'abbia mappata.
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
    6::bigint,
    '5. * tutte e sei le liste del perimetro dichiarano la colonna a catalogo (passo 8, meta DB)'
);

-- ============================================================
-- 6-7) ⭐ LA META' CHE MANCAVA — la colonna e' PIENA, non solo esistente
--
--   Il test 4 chiede «il campo dichiarato esiste alla sorgente?». E' una
--   domanda di STRUTTURA, e passa anche quando la risposta a video e' NULL su
--   ogni riga. Il 2026-08-18 e' successo esattamente questo:
--   `20260818-61` aveva aggiunto `emittente_ragione_sociale` a
--   `vw_dash_fatturazione_documenti` risolvendola da `emittente_soggetto_ruolo_id`
--   — che CINQUE dei sei resolver a monte scrivono `NULL::bigint` a mano.
--   Struttura perfetta, colonna muta su 274 righe su 274, e su
--   `vw_dash_aperto_documenti` muta PER SEMPRE, perche' quella lente esclude
--   l'unica area che risolveva. Il test 4 era verde per tutto il tempo.
--
--   ⭐ La domanda giusta e' «quante righe portano il valore?», e si scrive con
--   due `count`. E' il collaudo che il flag `multi_emittente` pretende, ridotto
--   a macchina per la parte che una macchina puo' vedere.
--
--   ⚠️ Le viste VUOTE in istanza non si possono giudicare, e non si fingono
--   verdi: si escludono, e il test 7 impedisce che l'esclusione diventi
--   totale — se un giorno tutte e cinque fossero vuote, il test 6 sarebbe
--   verde senza aver verificato niente.
-- ============================================================
CREATE TEMP TABLE tmp_perimetro_pieno (vista text, righe bigint, pieni bigint);

DO $misura$
DECLARE
    r       record;
    v_tot   bigint;
    v_pieni bigint;
BEGIN
    FOR r IN SELECT DISTINCT vista FROM tmp_perimetro_liste ORDER BY vista LOOP
        EXECUTE format(
            'SELECT count(*), count(emittente_ragione_sociale) FROM vendite.%I', r.vista)
          INTO v_tot, v_pieni;
        INSERT INTO tmp_perimetro_pieno VALUES (r.vista, v_tot, v_pieni);
    END LOOP;
END
$misura$;

-- Il valore atteso e' la stringa VUOTA e non uno zero: cosi' il rosso NOMINA
-- la vista e il rapporto (es. «vw_dash_aperto_documenti 0/156»), invece di
-- dire «1 <> 0» e lasciare la ricerca a chi legge.
SELECT is(
    (SELECT COALESCE(string_agg(vista || ' ' || pieni || '/' || righe, ', ' ORDER BY vista), '')
       FROM tmp_perimetro_pieno
      WHERE righe > 0
        AND pieni <> righe),
    '',
    '6. * la colonna emittente e'' PIENA su ogni riga delle viste del perimetro che hanno righe'
);

SELECT cmp_ok(
    (SELECT count(*) FROM tmp_perimetro_pieno WHERE righe > 0),
    '>=',
    1::bigint,
    '7. almeno una vista del perimetro ha righe: il test 6 non e'' verde per sottrazione'
);

-- ============================================================
-- Chiusura
-- ============================================================
SELECT * FROM finish();
ROLLBACK;
