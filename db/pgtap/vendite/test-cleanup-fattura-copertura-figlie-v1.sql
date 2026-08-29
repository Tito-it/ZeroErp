-- ------------------------------------------------------------
-- SPDX-License-Identifier: GPL-3.0-or-later
-- pgtap-runner: owner
-- pgtap-runner-motivo: dieci asserzioni su undici leggono il CATALOGO
--   (pg_constraint, pg_proc), che la RLS non filtra. L undicesima, il test 5,
--   e l unica che CONTA RIGHE — ed e proprio su quello zero che si fonda
--   l eccezione SCOPERTA_NOTA. Sotto RLS uno zero non distingue «la tabella e
--   vuota» da «non la vedo»: dal 2026-08-29 l elenco comprende
--   anagrafiche.soggetti_titoli_iva_movimenti, che ha RLS ATTIVA e policy per
--   emittente, quindi da zeroerp_app quel conteggio sarebbe fail-closed e il
--   presidio si autoassolverebbe. Da owner (relforcerowsecurity = false) il
--   conteggio e una misura. Nessuna copertura RLS si perde: in questo file non
--   ce n era.
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
-- ⚠️ IL SECONDO LIVELLO, aggiunto il 2026-08-22 — e perche' mancava
--   Questo file guardava solo le figlie di vendite.fatture. Ma la pulizia
--   cancella anche vendite.fatture_RIGHE, e QUELLE figlie non le guardava
--   nessuno: sei, di cui QUATTRO in NO ACTION. Il 2026-08-22 una di loro ha
--   fatto esplodere test-riporta-lotto-a-draft-v1 con un 23503 grezzo dentro
--   fn_cleanup_fatture_by_ids — cioe' esattamente il modo di scoprire il
--   difetto che questo file esiste per evitare, applicato al livello che non
--   sorvegliava.
--
-- ⚠️ E LA CHIAVE DELL'INVENTARIO DEL PRIMO LIVELLO E' LA TABELLA, non il
--   vincolo. Non basta: vendite.attivita_fatturabili ha DUE chiavi esterne
--   verso fatture_righe, e classificata «per tabella» sarebbe risultata
--   coperta mentre una delle due non lo era. Il secondo inventario e' quindi
--   indicizzato per NOME DEL VINCOLO, che e' la cosa che porta davvero il
--   comportamento.
--   ⚠️ Il primo inventario non e' stato riscritto per non toccare un presidio
--   che funziona: e' un debito dichiarato, non una svista.
--
-- ⛔ rev 2026-08-26 — E IL MOTIVO PER CUI L'INDICE E' IL VINCOLO E' CAMBIATO
--   Fino a oggi la ragione scritta qui sopra era «le due hanno ON DELETE
--   diversi: una SET NULL, una NO ACTION». Dal changeSet 20260826-26 sono
--   ENTRAMBE NO ACTION, e quella frase — lasciata li' — avrebbe invitato il
--   prossimo lettore a verificarla, trovarla falsa e «semplificare»
--   l'inventario tornando a indicizzarlo per tabella.
--   ⭐ La ragione vera e' piu' forte, e adesso e' l'unica: **l'azione
--   referenziale e' la stessa, ed e' il TRATTAMENTO a essere opposto**. Una
--   la pulizia la sgancia di proposito prima di cancellare (GESTITA); l'altra
--   NON deve toccarla mai, ed e' il guard a rifiutare l'operazione
--   (BLOCCO_VOLUTO). Un inventario per tabella le direbbe identiche.
--
-- Indice test
-- 1) Ogni figlia di vendite.fatture e classificata (una nuova -> rosso col nome)
-- 2) Nessuna voce dell inventario e sparita dal catalogo
-- 3) Le GESTITA sono davvero nominate nel corpo della pulizia
-- 4) Le BLOCCO_VOLUTO hanno ancora NO ACTION (nessuno le ha degradate a CASCADE)
-- 5) Le SCOPERTA_NOTA sono ancora vuote (l eccezione e scaduta se si popolano)
-- 6) Ogni figlia di vendite.fatture_RIGHE e classificata, per VINCOLO
-- 7) Nessuna voce del secondo inventario e sparita dal catalogo
-- 8) I BLOCCO_VOLUTO del secondo livello non sono stati degradati a CASCADE
-- 9) Il guard che rende quei blocchi una risposta e non un incidente esiste
-- 10) 🔴 Le GESTITA del secondo livello sono nominate PRIMA del DELETE sul padre
-- 11) fk_attivita_fatturabili_fattura_riga e ancora il muro (NO ACTION)
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

SELECT plan(11);

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
  -- ⭐ rev 2026-08-21 (cantiere incassi, lotto 3 / D11): la riga qui sopra
  --   diceva «NON si cancella, ed e giusto». Dal changeSet 20260821-54 non e
  --   piu vero, e una classificazione che descrive un comportamento finito e
  --   peggio di una mancante: si legge come se fosse stata verificata.
  ('vendite.fatture_fondi_fattura_source', 'GESTITA',       'DELETE via fn_reset_fondi_fattura quando l atto NON e stato eseguito: e una PROPOSTA, non un fatto, e il giro successivo ne rifa uno letto sul residuo di adesso. Un atto ESEGUITO invece non si tocca MAI - il reset lo segnala nel diario e va avanti - e uno bloccato da una distinta CHIUSA passa ad ANNULLATO col motivo sul dato'),
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
  -- ⭐ rev 2026-08-22 (cantiere incassi, lotto 7 / D15): la tabella e nata
  --   rinominando pagamenti.compensazioni, che con vendite.fatture non aveva
  --   nessun legame — l inventario non la conosceva perche NON ERA una figlia.
  --   Adesso ne ha DUE (origine e destinazione), ed e questo file ad averlo
  --   detto: e esattamente il lavoro per cui esiste.
  ('pagamenti.sistemazioni',               'BLOCCO_VOLUTO', 'una fattura su cui e stata REGISTRATA una decisione di sistemazione NON si deve poter disfare: se l atto e CONFERMATO ha gia generato una distinta o un fondo, e cancellare il documento lascerebbe quel denaro senza origine; se e in BOZZA e comunque una decisione che qualcuno ha preso e che va ritrovata. ⚠️ Sul percorso vero il blocco non scatta mai - il cleanup lavora su fatture in DRAFT, e una sistemazione nasce da un sovra-incasso, cioe da movimenti su un documento gia emesso - ma il giorno che quel percorso cambiasse, il rifiuto e la risposta giusta'),

  -- ── SCOPERTA_NOTA: eccezione a tempo ───────────────────────────────
  ('vendite.attivita_consumi',             'SCOPERTA_NOTA', 'flusso consumi non ancora acceso: 0 righe e nessuno scrittore (solo fn_list_consumi_da_pushare, che legge). fattura_id e NULLABLE apposta, quindi il giorno che si accende il ripristino dovra azzerarlo, non cancellare il consumo'),
  -- ⭐ rev 2026-08-29 (cantiere IVA, Fase 2 / changeSet 20260829-26): la tabella
  --   registra il CONSUMO DI PLAFOND di un titolo IVA (una dichiarazione
  --   d intento) da parte di una fattura. E nata ieri, e questo file l ha
  --   nominata il giorno dopo: e esattamente il lavoro per cui esiste.
  --
  -- ⚠️ Perche SCOPERTA_NOTA e non una delle due categorie definitive: la
  --   risposta giusta DIPENDE da una decisione ancora aperta, il punto I5 del
  --   brief - DOVE si consuma il plafond.
  --     * se il consumo si registra all EMISSIONE, la pulizia (che lavora su
  --       documenti in DRAFT) non incontrera mai un movimento, e il giorno che
  --       lo incontrasse il rifiuto sarebbe la risposta giusta: BLOCCO_VOLUTO,
  --       la stessa posizione di pagamenti.sistemazioni qui sopra;
  --     * se invece si registra gia in bozza, un ripristino DEVE stornare il
  --       movimento prima di cancellare - altrimenti il plafond di un terzo
  --       resta mangiato da un documento che non esiste piu: GESTITA, e la
  --       pulizia va estesa.
  --   Scriverne una adesso significherebbe fissare la decisione da qui, che e
  --   il verso sbagliato. SCOPERTA_NOTA e la categoria ARMATA: scade da sola
  --   nel momento esatto in cui la decisione diventa reale.
  --
  -- ℹ️ Oggi il presupposto e vero e verificabile: 0 righe e NESSUNO scrittore -
  --   anagrafiche.fn_consuma_plafond_titolo_iva esiste ma non ha chiamanti.
  -- ⚠️ La stessa riga copre anche il secondo livello: la tabella ha una FK anche
  --   verso vendite.fatture_righe, e una tabella vuota e vuota per entrambe.
  ('anagrafiche.soggetti_titoli_iva_movimenti', 'SCOPERTA_NOTA', 'consumo di plafond di un titolo IVA: 0 righe e nessuno scrittore (fn_consuma_plafond_titolo_iva non ha chiamanti). Entrambe le FK verso fatture e fatture_righe sono NO ACTION e lo sono di proposito - il movimento e un fatto contabile - ma la categoria definitiva dipende da I5: consumo all EMISSIONE -> BLOCCO_VOLUTO come pagamenti.sistemazioni; consumo gia in bozza -> GESTITA, e la pulizia deve stornare il movimento prima di cancellare, altrimenti il plafond di un terzo resta mangiato da un documento che non esiste piu');

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
-- Le SCOPERTA_NOTA sono fuori copertura perche' NESSUNO le popola. Il giorno
-- che uno dei due flussi si accende, questo test diventa rosso — che e'
-- esattamente quando serve saperlo, non mesi dopo su una DELETE esplosa.
--
-- ⚠️ L'elenco resta ESPLICITO, e non diventa un giro sull'inventario: la
--   categoria e' una stringa scritta a mano, e un presidio che si costruisce
--   da sola la lista delle cose da sorvegliare si spegne nel momento in cui
--   qualcuno scrive male la categoria. Qui la lista e' seconda firma.
-- ⭐ E il messaggio NOMINA la tabella che si e' popolata, con quante righe: un
--   rosso che dice solo «una delle due» costringe a rifare il lavoro a mano.
-- ⛔ E' l'unica asserzione del file che conta righe, ed e' il motivo del
--   marcatore `pgtap-runner: owner` in testa: soggetti_titoli_iva_movimenti ha
--   RLS attiva, e sotto RLS uno zero non distingue «e' vuota» da «non la
--   vedo». Il presidio si sarebbe autoassolto.
CREATE TEMP TABLE tmp_scoperte AS
SELECT 'vendite.attivita_consumi'::text AS tab,
       (SELECT count(*) FROM vendite.attivita_consumi) AS righe
UNION ALL
SELECT 'anagrafiche.soggetti_titoli_iva_movimenti'::text,
       (SELECT count(*) FROM anagrafiche.soggetti_titoli_iva_movimenti);

SELECT is(
  (SELECT count(*) FROM tmp_scoperte WHERE righe > 0),
  0::bigint,
  '5) le SCOPERTA_NOTA sono ancora vuote, l eccezione e ancora valida: '
  || COALESCE((SELECT string_agg(tab || ' (' || righe || ' righe)', ', ' ORDER BY tab)
                 FROM tmp_scoperte WHERE righe > 0),
              'tutte vuote')
);


-- ============================================================
-- IL SECONDO LIVELLO: le figlie di vendite.fatture_righe
-- ============================================================
-- ⚠️ Indicizzato per NOME DEL VINCOLO e non per tabella: una tabella puo'
--   avere due chiavi esterne verso lo stesso padre con ON DELETE diversi, e
--   classificarla «in blocco» nasconderebbe proprio quella asimmetria.
CREATE TEMP TABLE tmp_inventario_righe(vincolo text PRIMARY KEY, tab text, categoria text, perche text);

INSERT INTO tmp_inventario_righe(vincolo, tab, categoria, perche) VALUES
  -- ── GESTITA ────────────────────────────────────────────────────────
  -- ⛔ rev 2026-08-26. La motivazione precedente diceva: «ON DELETE SET NULL, e
  --   la pulizia lo azzera COMUNQUE a mano insieme al lock: il legame muore col
  --   documento e l attivita torna in coda». Era falsa nel punto che contava:
  --   sul percorso per-fattura la pulizia NON lo azzerava mai, perche la SET
  --   NULL scattava a fine istruzione del DELETE e le UPDATE a valle non
  --   trovavano piu nulla. L attivita NON tornava in coda.
  --   ⚠️ Questo file verificava la CLASSIFICAZIONE, mai l EFFETTO: una categoria
  --   sbagliata con una motivazione convincente passa tutti i suoi test. Il
  --   test 10 e la risposta.
  --   Brief: brief-db-lavoro-che-non-torna-indietro §8.3 e §9.4.
  ('fk_attivita_fatturabili_fattura_riga', 'vendite.attivita_fatturabili', 'GESTITA',
   'ON DELETE NO ACTION dal 20260826-26, e la pulizia sgancia l attivita PRIMA di cancellare la riga (20260826-25): quando il DELETE arriva non esiste piu nessun puntatore vivo. Il vincolo e quindi la RETE, non il meccanismo - sul percorso buono non scatta mai, e scatta solo su una porta che si fosse dimenticata di riallineare. Il test 10 verifica l ORDINE, che e la cosa che si era rotta'),
  ('fk_fatture_note_riga',                 'vendite.note_fatture',         'CASCADE_DB',
   'nota agganciata alla riga: senza la riga non ha oggetto'),

  -- ── BLOCCO_VOLUTO: il rifiuto E la funzionalita ────────────────────
  -- ⭐ Le quattro qui sotto sono LA STESSA COSA vista da quattro lati: su
  --   quella riga di fattura e gia stato registrato un accredito. Il legame
  --   e il SECONDO TETTO dell accredito (20260818-27 punto 2) e il
  --   DatiFattureCollegate della TD04: azzerarlo per far passare la pulizia
  --   toglierebbe il tetto proprio mentre le quantita si ri-derivano.
  --   La via d uscita per l operatore e fn_annulla_accredito_riga_reso.
  ('fk_commesse_attivita_fattura_riga_rettificata', 'vendite.commesse_attivita', 'BLOCCO_VOLUTO',
   'la commessa_attivita di RETTIFICA punta alla riga che sta correggendo: cancellarla lascerebbe l accredito senza origine'),
  ('fk_attivita_fatturabili_fattura_riga_rettificata', 'vendite.attivita_fatturabili', 'BLOCCO_VOLUTO',
   'stesso legame sul lato attivita fatturabili. ⚠️ La stessa tabella ha anche fk_attivita_fatturabili_fattura_riga, e dal 20260826-26 le due hanno la STESSA azione referenziale (NO ACTION): e il TRATTAMENTO a essere opposto - quella la pulizia la sgancia di proposito prima di cancellare, questa non la tocca mai e il guard rifiuta l operazione. E il motivo per cui questo inventario e per VINCOLO e non per tabella, e vale piu di prima: un inventario per tabella le direbbe identiche'),
  ('fk_resi_accrediti_fattura_riga',               'vendite.resi_righe_accrediti', 'BLOCCO_VOLUTO',
   'l accredito del reso punta alla riga accreditata: e il documento che prova quanto e stato reso'),
  ('fk_fatture_righe_riga_rettificata',            'vendite.fatture_righe',        'BLOCCO_VOLUTO',
   'auto-riferimento: la riga di nota di credito punta alla riga rettificata. ⚠️ Blocca SOLO se la riga che rettifica sta FUORI dall insieme cancellato: se muoiono insieme la NO ACTION e soddisfatta a fine istruzione, ed e il caso normale della nota di credito nello stesso lotto'),

  -- ── SCOPERTA_NOTA: eccezione a tempo, la prima di questo inventario ─
  -- ⭐ rev 2026-08-29 (cantiere IVA, Fase 2): e la SECONDA chiave esterna della
  --   stessa tabella gia classificata al primo livello. Compare qui perche
  --   questo inventario e indicizzato per VINCOLO e non per tabella - e questo
  --   e il caso che mostra perche: la classificazione e la stessa, ma senza la
  --   voce il test 6 sarebbe rosso e nessuna motivazione lo spiegherebbe.
  -- ⚠️ La verifica di vuotezza NON si duplica: sta al test 5, una volta sola,
  --   perche una tabella vuota e vuota per tutte le sue chiavi esterne.
  ('fk_soggetti_titoli_iva_movimenti_fattura_riga', 'anagrafiche.soggetti_titoli_iva_movimenti', 'SCOPERTA_NOTA',
   'stesso legame visto dal lato riga: il movimento di plafond puo puntare alla singola riga che lo ha consumato. Motivazione e scadenza sono quelle del primo livello - 0 righe, nessuno scrittore, e la categoria definitiva decisa da I5. Vuotezza verificata dal test 5');

CREATE TEMP TABLE tmp_figlie_righe AS
SELECT c.conname                       AS vincolo,
       c.conrelid::regclass::text      AS tab,
       c.confdeltype                   AS on_delete
  FROM pg_constraint c
 WHERE c.contype = 'f' AND c.confrelid = 'vendite.fatture_righe'::regclass;

-- 6) La domanda, un livello piu' giu'
SELECT is(
  (SELECT count(*) FROM tmp_figlie_righe f
    WHERE NOT EXISTS (SELECT 1 FROM tmp_inventario_righe i WHERE i.vincolo = f.vincolo)),
  0::bigint,
  '6) Ogni figlia di vendite.fatture_righe e classificata: '
  || COALESCE((SELECT string_agg(f.vincolo, ', ') FROM tmp_figlie_righe f
                WHERE NOT EXISTS (SELECT 1 FROM tmp_inventario_righe i WHERE i.vincolo = f.vincolo)),
              'nessuna scoperta')
);

-- 7) E l'inventario non invecchia nell'altro verso
SELECT is(
  (SELECT count(*) FROM tmp_inventario_righe i
    WHERE NOT EXISTS (SELECT 1 FROM tmp_figlie_righe f WHERE f.vincolo = i.vincolo)),
  0::bigint,
  '7) Nessuna voce del secondo inventario e sparita dal catalogo: '
  || COALESCE((SELECT string_agg(i.vincolo, ', ') FROM tmp_inventario_righe i
                WHERE NOT EXISTS (SELECT 1 FROM tmp_figlie_righe f WHERE f.vincolo = i.vincolo)),
              'nessun fantasma')
);

-- 8) Un blocco voluto si perde in silenzio, anche qui
-- ⚠️ Se qualcuno degradasse a CASCADE uno di questi, l accredito verrebbe
--   cancellato insieme alla riga e nessuno protesterebbe: sembrerebbe una
--   semplificazione, e sarebbe la perdita del secondo tetto.
SELECT is(
  (SELECT count(*) FROM tmp_inventario_righe i
     JOIN tmp_figlie_righe f ON f.vincolo = i.vincolo
    WHERE i.categoria = 'BLOCCO_VOLUTO' AND f.on_delete = 'c'),
  0::bigint,
  '8) I BLOCCO_VOLUTO del secondo livello non sono stati degradati a CASCADE'
);

-- 9) Un blocco senza spiegazione e' un incidente; con la spiegazione e' una risposta
-- ⚠️ Questo test e' il motivo per cui i BLOCCO_VOLUTO qui sopra sono
--   accettabili: senza il guard, quelle NO ACTION producono un 23503 grezzo a
--   meta lavoro, dentro una funzione che i suoi chiamanti danno per
--   infallibile. Con il guard producono un errore di dominio che dice cosa
--   fare. Se il guard sparisce, i blocchi restano e la risposta no.
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'script' AND p.proname = 'fn_check_fatture_con_rettifiche'
  )
  AND (SELECT c.src FROM tmp_corpo c) ILIKE '%fn_check_fatture_con_rettifiche%',
  '9) il guard fn_check_fatture_con_rettifiche esiste ed e chiamato dalla pulizia'
);

-- ============================================================
-- 10) 🔴 «GESTITA» non vuol dire «nominata»: vuol dire «nominata PRIMA»
-- ============================================================
-- ⛔ E' il test che questo file non aveva, ed e' il motivo per cui il difetto
--   del cantiere «il lavoro che non torna indietro» e' sopravvissuto quattro
--   settimane. `fk_attivita_fatturabili_fattura_riga` era classificata GESTITA
--   con una motivazione convincente, e il test 3 — che sorveglia solo il primo
--   livello — avrebbe comunque risposto «si, la pulizia la nomina». La nominava
--   DOPO aver cancellato il padre, cioe' quando il legame era gia' morto.
--
-- ⭐ Il corpo si legge SENZA I COMMENTI. Con i commenti dentro, il nome della
--   tabella compare gia' nell'intestazione della funzione: la posizione
--   misurerebbe la prosa, non il codice, e il test sarebbe verde qualunque
--   cosa faccia la funzione.
-- ⚠️ E si legge il corpo della SOLA fn_cleanup_fatture_by_ids: il tmp_corpo
--   usato dal test 3 e' un string_agg di DUE funzioni senza ORDER BY, quindi
--   l'ordine dei pezzi non e' deterministico — innocuo per un ILIKE, fatale
--   per un confronto di posizioni.
SELECT is(
  (WITH corpo AS (
     SELECT regexp_replace(p.prosrc, E'--[^\n]*', '', 'g') AS src
       FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
      WHERE n.nspname = 'vendite' AND p.proname = 'fn_cleanup_fatture_by_ids')
   SELECT count(*)
     FROM tmp_inventario_righe i, corpo c
    WHERE i.categoria = 'GESTITA'
      AND NOT (position(split_part(i.tab, '.', 2) in c.src) > 0
               AND position(split_part(i.tab, '.', 2) in c.src)
                   < position('DELETE FROM vendite.fatture_righe' in c.src))),
  0::bigint,
  '10) le GESTITA del secondo livello sono nominate dalla pulizia PRIMA del DELETE sul padre'
);

-- ============================================================
-- 11) Il muro non si toglie in silenzio
-- ============================================================
-- ⚠️ Un ALTER futuro che riportasse questa FK a ON DELETE SET NULL non
--   renderebbe rosso NIENTE: la pulizia continuerebbe a funzionare (sgancia
--   prima), e si perderebbe solo la difesa contro la porta che nessuno ha
--   ancora scritto. E' la stessa forma di
--   reference_check_tabella_e_guard_funzione_dissentono: il vincolo non si
--   verifica dal nome di cio' che si crede di aver scritto.
--
-- ⛔ E si asserisce la DEFINIZIONE INTERA, non un frammento: `NO ACTION` e' il
--   default e pg_get_constraintdef NON LO STAMPA. Un test scritto come
--   «~ 'NO ACTION'» sarebbe rosso per sempre — e chi lo «aggiusta»
--   invertendolo lo rende verde per sempre. La stringa intera invece fissa
--   anche le colonne, il bersaglio, l'ON UPDATE e il non essere DEFERRABLE.
SELECT is(
  (SELECT pg_get_constraintdef(c.oid)
     FROM pg_constraint c
    WHERE c.conname = 'fk_attivita_fatturabili_fattura_riga'),
  'FOREIGN KEY (fattura_riga_id) REFERENCES vendite.fatture_righe(id) ON UPDATE CASCADE',
  '11) fk_attivita_fatturabili_fattura_riga e ancora il muro: ON DELETE NO ACTION (implicito), ON UPDATE CASCADE, non deferrable'
);

SELECT * FROM finish();

ROLLBACK;
