## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_or_create_session_tx_id`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids) — il registro in cui nasce l'id
> * [dbops.sec_functions_owner](/dbzero/dbops/tabelle/sec_functions_owner) — dove è dichiarato il suo proprietario
>
> Approfondimento funzioni:
>
> * [dbops.fn_generate_tx_id](/dbzero/dbops/funzioni/fn_generate_tx_id) — genera e registra l'id, sulla connessione di log
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed) — il trigger che la chiama e verifica l'id pubblicato
> * [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa) — la regola unica: se il canale è acceso, e con quale stringa
> * [script.fn_ensure_logconn](/dbzero/script/funzioni/fn_ensure_logconn) — apre o ritrova la connessione di log
> * [script.uuid_nil](/dbzero/script/funzioni/uuid_nil) — la sentinella dei ripieghi
> * [script.fn_log_error_only](/dbzero/script/funzioni/fn_log_error_only) — un altro chiamante: dà un `tx_id` a ogni errore registrato
> * [dbops.fn_sync_functions_owner](/dbzero/dbops/funzioni/fn_sync_functions_owner) — il passaggio obbligato per modificarla
>
> Guide:
>
> * [Transaction ID](/guide/tx_id_implementation_guide) — come nasce e come si propaga il `tx_id`

---

### 🎯 Scopo Principale

Restituisce il **transaction id della transazione corrente**: quello già pubblicato nel GUC
`dbops.tx_id`, se c'è, altrimenti uno nuovo generato e registrato in `dbops.transaction_ids` su
una connessione separata, che poi pubblica. Con il canale di log spento, non configurato o
irraggiungibile restituisce la sentinella nulla e non pubblica niente.

Così tutte le scritture della stessa transazione portano lo stesso `tx_id`.

---

### ⚖️ La regola che regge tutto: mai pubblicare un id non registrato

Il trigger `dbops.trgfn_tx_id_managed` verifica l'id della sessione nel registro. Questa funzione
pubblica quindi **solo** id che vengono da `dbops.transaction_ids`; in ogni ripiego restituisce
`script.uuid_nil()` **senza** impostare il GUC. L'invariante che il trigger verifica è vero per
costruzione, e il ramo «id non registrato» resta irraggiungibile se nessuno imposta il GUC a mano.

⛔ Il ripiego non è un id inventato in locale: sarebbe un id non registrato, che il trigger
rifiuterebbe, e registrarlo nella transazione di lavoro inquinerebbe in modo permanente un
registro immutabile. L'autonomia — una registrazione che sopravvive all'annullamento — chiede una
seconda connessione, non un'altra macchina: il canale punta allo stesso database.

---

### Un id per transazione, non per connessione

Il GUC si pubblica con ambito **locale**: vale fino alla fine della transazione, e la transazione
successiva ne riceve uno suo. Un identificativo di transazione non sopravvive alla transazione.
Dove il canale è acceso, il registro cresce quindi di una riga per transazione che scrive su una
tabella tracciata.

---

### Come nasce un id nuovo

1. **Il GUC.** Se `dbops.tx_id` contiene un UUID, la funzione lo restituisce e non fa altro.
2. **Il canale.** Se è acceso, e con quale stringa, lo dice
   [script.fn_canale_log_stringa](/dbzero/script/funzioni/fn_canale_log_stringa), **prima** di
   aprire qualunque connessione. Spento (`myapp.log_with_dblink = off`) o non configurato (nessuna
   stringa): ripiego, avviso e sentinella.
3. **La connessione di log.** `script.fn_ensure_logconn` apre o ritrova `logconn`. Non solleva mai:
   un canale irraggiungibile è un avviso, e il passo successivo ripiega sulla stringa.
4. **La generazione.** `dbops.fn_generate_tx_id` gira sulla connessione persistente `logconn`. Se
   `logconn` non c'è, o cade durante la chiamata, la funzione la chiude e riprova **una** volta con
   una connessione nuova, aperta dalla stringa del canale.
5. **La pubblicazione.** Solo un id restituito dal registro si pubblica. Un `NULL` dal canale, o un
   errore, sono ripieghi: avviso nel log del server e sentinella, senza pubblicare.

La funzione **non blocca mai il chiamante**: un problema del canale, all'apertura di `logconn` come
durante la generazione, diventa un avviso, e la scrittura del chiamante prosegue con la sentinella.

⚠️ **Con l'interruttore a `off` il `tx_id` è la sentinella.** Le migrazioni, il makefile e la CI
spengono il canale così: in quelle sessioni le scritture sulle tabelle tracciate portano
`script.uuid_nil()`. È voluto — spento vuol dire spento anche per il `tx_id` — e innocuo: il
trigger del `tx_id` accetta la sentinella, e nessuna chiave esterna punta a `dbops.transaction_ids`.

---

### Senza canale, nessuna correlazione

Senza canale (spento, non configurato o irraggiungibile) tutte le righe portano la sentinella nulla, e le transazioni non si distinguono dal
`tx_id`. È il prezzo del disegno, ed è voluto: l'alternativa sarebbe un id non registrato, o
registrato nella transazione di lavoro.

---

### ⚠️ Gira come `postgres`

È `SECURITY DEFINER` con proprietario `postgres`, dichiarato nel registro dei proprietari delle
funzioni, e il percorso di ricerca è fissato nella definizione (`public` serve, perché `dblink`
vive lì): un rifacimento che lo dimentica lo azzera.

Un `CREATE OR REPLACE` dal ruolo di migrazione fallisce, perché la funzione non è sua. Per
modificarla, nello stesso changeSet: si dichiara per un momento nel registro il ruolo corrente, si
riallinea il proprietario con `dbops.fn_sync_functions_owner`, si sostituisce la funzione, si
ripristina il registro e si riallinea di nuovo.

---

### Test

* `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql` — senza canale la funzione restituisce
  la sentinella e non pubblica il GUC, e una scrittura su una tabella tracciata riesce con la
  sentinella; con il canale attivo (prova condizionale) l'id restituito è registrato.
* `db/pgtap/script/test-canale-log-v1.sql` — test 8-10: con un canale irraggiungibile la funzione
  non solleva, restituisce la sentinella e non pubblica il GUC, e una scrittura su una tabella
  tracciata riesce. Test 13: con `myapp.log_with_dblink = off` e un canale che funziona il `tx_id` è
  la sentinella (si salta dove il canale non c'è). Test 16: non legge da sé i parametri del canale
  (presidio sul testo).
* `db/pgtap/dbops/test-security-definer-search-path-v1.sql` — il percorso di ricerca è esattamente
  `pg_catalog`, `public`, `pg_temp`.

---

### Note di migrazione

* 2025-11-22 — una riscrittura perde la disciplina originale: nei ripieghi genera un id **non
  registrato**, lo pubblica, e con ambito di sessione. Il trigger lo rifiutava, e la prima
  scrittura tracciata bloccava l'intera migrazione dove il canale non c'era.
* 2026-07-22 — torna la disciplina originale: la connessione di log in testa, la sentinella non
  pubblicata, il GUC con ambito di transazione (`brief-db-coerenza-tx-id-non-registrato`).
* 2026-09-12 — il percorso di ricerca è fissato nella definizione.
* 2026-10-18 — la generazione passa dalla connessione persistente `logconn` invece di aprirne una a
  ogni transazione; la stringa di connessione resta il ripiego
  (`brief-db-plancache-funzioni-con-query-incorporate`).
* 2026-11-04 — il canale lo dice `script.fn_canale_log_stringa`, prima di aprire qualunque
  connessione (D26 di `brief-db-revisione-dbops`): prima la funzione aggirava l'interruttore, e con
  `off` e la stringa impostata generava e registrava l'id lo stesso. Con `fn_ensure_logconn` che non
  solleva più (D1), un canale irraggiungibile non blocca più le scritture tracciate.

---

{% include-markdown "signature-core.md" %}
