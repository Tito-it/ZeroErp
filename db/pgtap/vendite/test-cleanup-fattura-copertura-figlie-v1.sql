-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgTAP test per Zero ERP
-- Test: la pulizia della fattura copre TUTTE le sue tabelle figlie
--       (piano-db-ritorno-lotto-a-draft.md §5.5 — invariante di catalogo)
-- ------------------------------------------------------------
-- A cosa serve, in una frase
--   Quando nascera' una tabella nuova collegata a vendite.fatture, questo
--   file diventa ROSSO e ne fa il nome. Senza, il difetto si scopre in
--   uno dei due modi peggiori possibili — e nessuno dei due e' «continua
--   a funzionare»:
--
--     * figlia in ON DELETE CASCADE  -> viene cancellata IN SILENZIO,
--       anche se doveva sopravvivere. Nessuno se ne accorge mai;
--     * figlia in NO ACTION          -> la DELETE ESPLODE con una
--       violazione di FK grezza, a runtime, davanti all'operatore.
--
-- Perche' un INVARIANTE e non un elenco
--   La tentazione sarebbe una tabella-registro dei «satelliti della
--   fattura». Sarebbe una cosa in piu' da ricordarsi di aggiornare, e se
--   te ne dimentichi non se ne accorge nessuno. Le FK sono GIA' il
--   registro: dichiarano la verita' e sono aggiornate per costruzione.
--   Questo file non costruisce una lista: legge il catalogo e tiene la
--   pulizia responsabile di cio' che il catalogo dichiara.
--
-- ⚠️ COME SI REAGISCE A UN ROSSO
--   Non si aggiunge la tabella all'inventario per far tornare il verde.
--   Si DECIDE a quale categoria appartiene, e la si scrive con la
--   motivazione. Il rosso non e' il problema: e' la domanda.
--
-- Le quattro categorie
--   GESTITA        la pulizia la nomina e la tratta esplicitamente
--   CASCADE_DB     ci pensa la FK; la riga muore con la fattura, ed e' giusto
--   BLOCCO_VOLUTO  NO ACTION di proposito: quel documento NON si deve poter
--                  disfare (un incasso, un invio allo SDI). Il blocco e' la
--                  funzionalita', non il difetto
--   SCOPERTA_NOTA  tabella non ancora in uso: l'eccezione vale FINCHE' resta
--                  vuota, e il test 5 la sorveglia
--
-- ⚠️ Se aggiungi una voce SCOPERTA_NOTA, aggiungi anche la sua verifica di
--    vuotezza al test 5: li' l'elenco e' esplicito di proposito, perche' una
--    stima di righe (reltuples) non e' un dato su cui fondare un presidio.
-- ------------------------------------------------------------
-- Indice test
-- 1) Ogni figlia di vendite.fatture e classificata (una nuova -> rosso col nome)
-- 2) Nessuna voce dell inventario e sparita dal catalogo
-- 3) Le GESTITA sono davvero nominate nel corpo della pulizia
-- 4) Le BLOCCO_VOLUTO hanno ancora NO ACTION (nessuno le ha degradate a CASCADE)
-- 5) Le SCOPERTA_NOTA sono ancora vuote (l eccezione e scaduta se si popolano)
-- ------------------------------------------------------------

BEGIN;

SELECT plan(5);

-- ============================================================
-- L'inventario: la classificazione, con la motivazione
-- ============================================================
CREATE TEMP TABLE tmp_inventario(tab text PRIMARY KEY, categoria text, perche text);

INSERT INTO tmp_inventario(tab, categoria, perche) VALUES
  -- ── GESTITA: la pulizia le nomina e le tratta ──────────────────────
  ('vendite.fatture_riepiloghi_iva',       'GESTITA',       'DELETE nel cleanup'),
  ('vendite.fatture_righe',                'GESTITA',       'DELETE nel cleanup, con conteggio'),
  ('vendite.fatture_log',                  'GESTITA',       'DELETE nel cleanup'),
  ('vendite.fatturazione_lotti_fatture',   'GESTITA',       'DELETE nel cleanup: e il collegamento al lotto'),
  ('vendite.fatture_fondi_fattura',        'GESTITA',       'DELETE via fn_reset_fondi_fattura'),
  ('vendite.fatture_fondi_fattura_source', 'GESTITA',       'UPDATE via fn_reset_fondi_fattura: azzera fattura_figlia_id e rimette il fondo DISPONIBILE. NON si cancella, ed e giusto: e un credito che deve sopravvivere alla fattura che lo consumava'),
  ('pagamenti.vendite_contabili_righe',    'GESTITA',       'DELETE via fn_reset_fondi_fattura'),

  -- ── CASCADE_DB: ci pensa la FK, e va bene cosi ─────────────────────
  ('vendite.fatture_indirizzi',            'CASCADE_DB',    'snapshot indirizzi: muore col documento e si rigenera al rilancio'),
  ('vendite.fatture_rettifiche',           'CASCADE_DB',    'rettifiche del documento: senza il documento non hanno oggetto'),
  ('vendite.fatture_scadenze',             'CASCADE_DB',    'piano rate: si rigenera dal termine al rilancio'),
  ('vendite.fatture_stampa_coda',          'CASCADE_DB',    'outbox di stampa: una stampa di un documento che non esiste piu non ha senso'),
  ('vendite.note_fatture',                 'CASCADE_DB',    'partizione di vendite.note; il cleanup cancella comunque dal padre partizionato'),

  -- ── BLOCCO_VOLUTO: il rifiuto E la funzionalita ────────────────────
  ('pagamenti.vendite_movimenti',          'BLOCCO_VOLUTO', 'una fattura con un incasso registrato NON si deve poter disfare'),
  ('vendite.fatture_sdi',                  'BLOCCO_VOLUTO', 'una fattura gia trasmessa allo SDI NON si deve poter disfare'),

  -- ── SCOPERTA_NOTA: eccezione a tempo ───────────────────────────────
  ('vendite.attivita_consumi',             'SCOPERTA_NOTA', 'flusso consumi non ancora acceso: 0 righe e nessuno scrittore (solo fn_list_consumi_da_pushare, che legge). fattura_id e NULLABLE apposta, quindi il giorno che si accende il ripristino dovra azzerarlo, non cancellare il consumo');

-- Le figlie vere, lette dal catalogo
CREATE TEMP TABLE tmp_figlie AS
SELECT DISTINCT c.conrelid::regclass::text AS tab
  FROM pg_constraint c
 WHERE c.contype = 'f' AND c.confrelid = 'vendite.fatture'::regclass;

-- Il corpo della pulizia: la primitiva PIU la funzione dei fondi, che la
-- primitiva chiama. Sono due oggetti ma una catena sola.
CREATE TEMP TABLE tmp_corpo AS
SELECT string_agg(pg_get_functiondef(p.oid), E'\n') AS src
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'vendite'
   AND p.proname IN ('fn_cleanup_fatture_by_ids', 'fn_reset_fondi_fattura');

-- ============================================================
-- 1) La domanda che questo file esiste per porre
-- ============================================================
-- Si asserisce la COPERTURA (quante classificate su quante esistono) e non
-- un confronto fra due elenchi: un confronto passerebbe anche se una figlia
-- sparisse dal catalogo, uscendo dal paragone invece di violarlo.
SELECT is(
  (SELECT count(*) FROM tmp_figlie f WHERE NOT EXISTS (SELECT 1 FROM tmp_inventario i WHERE i.tab = f.tab)),
  0::bigint,
  '1) Ogni figlia di vendite.fatture e classificata nell inventario: '
  || COALESCE((SELECT string_agg(f.tab, ', ') FROM tmp_figlie f
                WHERE NOT EXISTS (SELECT 1 FROM tmp_inventario i WHERE i.tab = f.tab)),
              'nessuna scoperta')
);

-- ============================================================
-- 2) L'inventario non deve invecchiare nell'altro verso
-- ============================================================
-- Una voce rimasta dopo che la tabella e' stata tolta e' rumore che si
-- accumula, e col tempo rende l'inventario poco credibile.
SELECT is(
  (SELECT count(*) FROM tmp_inventario i WHERE NOT EXISTS (SELECT 1 FROM tmp_figlie f WHERE f.tab = i.tab)),
  0::bigint,
  '2) Nessuna voce dell inventario e sparita dal catalogo: '
  || COALESCE((SELECT string_agg(i.tab, ', ') FROM tmp_inventario i
                WHERE NOT EXISTS (SELECT 1 FROM tmp_figlie f WHERE f.tab = i.tab)),
              'nessun fantasma')
);

-- ============================================================
-- 3) «Gestita» deve voler dire qualcosa
-- ============================================================
-- Senza questo, bastava scrivere GESTITA nell'inventario per avere il verde.
SELECT is(
  (SELECT count(*) FROM tmp_inventario i, tmp_corpo c
    WHERE i.categoria = 'GESTITA'
      AND c.src NOT ILIKE '%' || split_part(i.tab, '.', 2) || '%'),
  0::bigint,
  '3) Le GESTITA sono davvero nominate nel corpo della pulizia: '
  || COALESCE((SELECT string_agg(i.tab, ', ') FROM tmp_inventario i, tmp_corpo c
                WHERE i.categoria = 'GESTITA'
                  AND c.src NOT ILIKE '%' || split_part(i.tab, '.', 2) || '%'),
              'tutte nominate')
);

-- ============================================================
-- 4) Un blocco voluto si perde in silenzio
-- ============================================================
-- ⚠️ Se qualcuno mettesse pagamenti.vendite_movimenti in CASCADE, gli incassi
-- verrebbero cancellati insieme alla fattura senza che niente protesti. E' il
-- modo peggiore di perdere una difesa: sembra una semplificazione.
SELECT is(
  (SELECT count(*) FROM tmp_inventario i
     JOIN pg_constraint c ON c.conrelid = i.tab::regclass
    WHERE i.categoria = 'BLOCCO_VOLUTO'
      AND c.contype = 'f' AND c.confrelid = 'vendite.fatture'::regclass
      AND c.confdeltype = 'c'),
  0::bigint,
  '4) I BLOCCO_VOLUTO hanno ancora NO ACTION: nessuno li ha degradati a CASCADE'
);

-- ============================================================
-- 5) L'eccezione a tempo, e la sua scadenza
-- ============================================================
-- attivita_consumi e' fuori copertura perche' NESSUNO la popola. Il giorno
-- che il flusso consumi si accende, questo test diventa rosso — che e'
-- esattamente quando serve saperlo, non mesi dopo su una DELETE esplosa.
SELECT is(
  (SELECT count(*) FROM vendite.attivita_consumi),
  0::bigint,
  '5) attivita_consumi e ancora vuota: l eccezione SCOPERTA_NOTA e ancora valida'
);

SELECT * FROM finish();

ROLLBACK;
