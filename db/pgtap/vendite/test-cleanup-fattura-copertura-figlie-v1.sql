-- ------------------------------------------------------------
-- SPDX-License-Identifier: AGPL-3.0-or-later
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
  -- ⭐ rev 2026-08-31 (changeSet 20260831-25): il satellite dei riferimenti
  --   dell atto. Questo file ne ha fatto il nome il giorno stesso, ed e
  --   esattamente il lavoro per cui esiste.
  --
  -- ⚠️ CASCADE_DB E UNA DECISIONE, non il modo di far tornare il verde: il
  --   blocco DatiContratto e uno snapshot di QUELLA fattura - numero, data e i
  --   tre codici congelati il giorno dell emissione - e senza il documento non
  --   ha nessun oggetto. Non e come pagamenti.vendite_movimenti, dove il
  --   rifiuto E la funzionalita: qui non c e niente da proteggere, c e una
  --   copia da buttare insieme all originale. E si rigenera al rilancio, come
  --   fatture_indirizzi qui sopra, dalla stessa scrittura che rifa le righe.
  --
  -- ⛔ E LA TABELLA HA UNA FIGLIA SUA - vendite.fatture_righe, via
  --   fk_fatture_righe_fattura_atto - che NESSUNO DEI DUE INVENTARI GUARDA:
  --   il primo elenca le figlie di vendite.fatture, il secondo quelle di
  --   vendite.fatture_righe, e le figlie di fatture_atti sono un terzo livello
  --   che non esiste. Oggi non e un buco: quell unica figlia e vendite.fatture_righe,
  --   che e gia classificata al primo livello e muore PRIMA (la pulizia la
  --   cancella esplicitamente, e in una DELETE sulla testata la NO ACTION si
  --   verifica a fine istruzione, quando entrambe le cascate sono passate -
  --   provato in test-fatture-atti-v1 caso 10).
  --   ⚠️ Ma e un DEBITO DICHIARATO, non una svista: il giorno che a fatture_atti
  --   si aggiungesse una seconda figlia, nessun presidio ne farebbe il nome.
  ('vendite.fatture_atti',                 'CASCADE_DB',    'snapshot dei riferimenti dell atto (numero, data, CIG, CUP, commessa) congelato all emissione: senza il documento non ha oggetto, e si rigenera al rilancio dalla stessa scrittura che rifa le righe. ⚠️ Ha una figlia sua - fatture_righe via fk_fatture_righe_fattura_atto - che nessuno dei due inventari guarda, perche il terzo livello non esiste: oggi non e un buco (quella figlia e gia classificata al primo livello e muore prima), ma e un debito dichiarato'),
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
  --   d intento) da parte di una fattura. E nata quel giorno, e questo file l ha
  --   nominata il giorno dopo: e esattamente il lavoro per cui esiste.
  --
  -- ⭐ rev 2026-10-04 — DA SCOPERTA_NOTA A BLOCCO_VOLUTO: la decisione I5 e
  --   presa (brief-db-bom-flag-quantita-e-kit-in-fattura §14, strada A di Tid).
  --   Il consumo si registra all EMISSIONE (task consuma_plafond_lotto, prima
  --   della numerazione), e una fattura che ha consumato NON si disfa piu: il
  --   movimento e un fatto contabile, il registro e append-only, e uno storno
  --   non basterebbe perche nominerebbe anch esso la fattura. Il lotto va
  --   avanti. Le tre porte di reset si fermano col motivo
  --   E_FATTURE_PLAFOND_CONSUMATO (script.fn_check_fatture_con_plafond_consumato)
  --   e la pulizia ha il suo guard: il test 9 lo verifica.
  -- ⚠️ La stessa decisione vale per il secondo livello (la FK verso
  --   fatture_righe): stesso fatto, visto dal lato riga.
  ('anagrafiche.soggetti_titoli_iva_movimenti', 'BLOCCO_VOLUTO', 'una fattura che ha gia CONSUMATO il plafond di un titolo IVA NON si deve poter disfare: il movimento e un fatto contabile (registro append-only, FK NO ACTION di proposito) e uno storno non basterebbe, perche nominerebbe anch esso la fattura. Il consumo avviene all emissione, PRIMA della numerazione: per questo le tre porte hanno un motivo loro (E_FATTURE_PLAFOND_CONSUMATO) oltre a quello sul numero, e la pulizia un guard (test 9). Il lotto va avanti: DEFINITIVA riprende fattura per fattura e il consumo e idempotente. Decisione I5, strada A di Tid del 2026-10-04');

-- Le figlie vere, lette dal catalogo
CREATE TEMP TABLE tmp_figlie AS
SELECT DISTINCT c.conrelid::regclass::text AS tab
  FROM pg_constraint c
 WHERE c.contype = 'f' AND c.confrelid = 'vendite.fatture'::regclass;

-- Il corpo della pulizia: la primitiva PIU la funzione dei fondi, che la
-- primitiva chiama. Sono due oggetti ma una catena sola.
-- ⚠️ L'ELENCO DELLE FUNZIONI E' IL PERIMETRO DEL PRESIDIO, e va esteso ogni
--   volta che un pezzo della pulizia si SPOSTA. Il test 3 cerca il nome di
--   ogni figlia GESTITA dentro questo testo: una tabella cancellata da una
--   funzione non elencata risulterebbe «non nominata», cioe' un rosso per il
--   motivo sbagliato — e, se un giorno la si togliesse dall'inventario per
--   farlo tacere, un verde per il motivo sbagliato.
-- ⭐ rev 2026-08-31: entra vendite.fn_cancella_fondo_fattura. Dal changeSet
--   20260831-65 fn_reset_fondi_fattura non cancella piu' inline: il criterio
--   sta in fn_check_fondo_cancellabile e i tre DELETE nell'ordine imposto dalla
--   FK stanno li'. Senza questa riga il file diventava rosso su
--   pagamenti.vendite_contabili_righe — ed e' il presidio che ha funzionato,
--   non un difetto: la pulizia era davvero cambiata di sede.
CREATE TEMP TABLE tmp_corpo AS
SELECT string_agg(pg_get_functiondef(p.oid), E'\n') AS src
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE n.nspname = 'vendite'
   AND p.proname IN ('fn_cleanup_fatture_by_ids',
                     'fn_reset_fondi_fattura',
                     'fn_cancella_fondo_fattura');

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
;
-- ⭐ rev 2026-10-04: anagrafiche.soggetti_titoli_iva_movimenti non e' piu'
--   SCOPERTA_NOTA (e' BLOCCO_VOLUTO, decisione I5): esce da qui. Con lei esce
--   l'unica ragione del marcatore `pgtap-runner: owner` in testa, che resta
--   perche' il conteggio di vendite.attivita_consumi e' comunque una misura
--   piu' affidabile da owner; e' un debito minore, dichiarato.

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
  -- ⭐ rev 2026-08-31 (changeSet 20260831-30): il secondo auto-riferimento di
  --   questa tabella. E la riga di sopra e il suo gemello per FORMA, non per
  --   comportamento - vale la pena leggerli insieme.
  --
  -- ⚠️ PERCHE BLOCCO_VOLUTO e non CASCADE_DB, che sarebbe la risposta comoda:
  --   la NO ACTION qui e VOLUTA. Cancellare una capofila lasciando vive le sue
  --   parti spezzerebbe la lettura «capofila -> parti» a meta, e chi somma gli
  --   importi partendo dall attivita fatturabile prenderebbe righe orfane che
  --   non sa piu ricondurre a niente. Il rifiuto E la risposta giusta.
  --
  -- ⭐ E SUL PERCORSO DELLA PULIZIA NON SCATTA MAI, ma non per fortuna: per
  --   COSTRUZIONE. La FK e COMPOSITA su (riga_capofila_id, fattura_id), quindi
  --   capofila e parti stanno per forza sulla STESSA fattura - e la pulizia le
  --   cancella con un DELETE solo, dove la NO ACTION e soddisfatta a fine
  --   istruzione. E la differenza con la riga sopra: li il caso «fuori
  --   dall insieme» esiste (una nota di credito di un altro lotto), qui no.
  --   Stessa posizione di pagamenti.sistemazioni al primo livello: il blocco e
  --   irraggiungibile oggi, e il giorno che il percorso cambiasse sarebbe la
  --   risposta giusta comunque.
  ('fk_fatture_righe_riga_capofila',               'vendite.fatture_righe',        'BLOCCO_VOLUTO',
   'auto-riferimento: la parte di una riga spezzata dal plafond punta alla sua capofila. NO ACTION voluta - cancellare la capofila lasciando vive le parti spezzerebbe a meta la lettura «capofila -> parti», e chi somma gli importi partendo dall attivita troverebbe righe orfane. ⭐ Sul percorso della pulizia non scatta MAI per COSTRUZIONE, non per fortuna: la FK e composita su (riga_capofila_id, fattura_id), quindi le due righe stanno sempre sulla stessa fattura e muoiono nello stesso DELETE, dove la NO ACTION e soddisfatta a fine istruzione. ⚠️ E la differenza con fk_fatture_righe_riga_rettificata, che ha la stessa forma: li il caso «la riga sta fuori dall insieme cancellato» esiste davvero (una nota di credito di un altro lotto), qui il modello non lo ammette'),

  -- ⭐ rev 2026-10-04: da SCOPERTA_NOTA a BLOCCO_VOLUTO, con il primo livello
  --   (decisione I5, strada A). E la SECONDA chiave esterna della stessa
  --   tabella: compare qui perche questo inventario e indicizzato per VINCOLO.
  ('fk_soggetti_titoli_iva_movimenti_fattura_riga', 'anagrafiche.soggetti_titoli_iva_movimenti', 'BLOCCO_VOLUTO',
   'stesso legame visto dal lato riga: il movimento di plafond punta alla singola riga che lo ha consumato. Stessa decisione del primo livello - una fattura che ha consumato plafond non si disfa, le porte la fermano con E_FATTURE_PLAFOND_CONSUMATO e la pulizia col suo guard (test 9)');

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
-- ⭐ rev 2026-10-04: i guard sono DUE, uno per famiglia di blocchi — le
--   rettifiche (secondo livello) e il plafond consumato (registro dei
--   movimenti, entrambi i livelli). Ognuno deve esistere ed essere chiamato.
SELECT ok(
  EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'script' AND p.proname = 'fn_check_fatture_con_rettifiche'
  )
  AND (SELECT c.src FROM tmp_corpo c) ILIKE '%fn_check_fatture_con_rettifiche%'
  AND EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
     WHERE n.nspname = 'script' AND p.proname = 'fn_check_fatture_con_plafond_consumato'
  )
  AND (SELECT c.src FROM tmp_corpo c) ILIKE '%fn_check_fatture_con_plafond_consumato%',
  '9) i guard fn_check_fatture_con_rettifiche e fn_check_fatture_con_plafond_consumato esistono e la pulizia li chiama'
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
