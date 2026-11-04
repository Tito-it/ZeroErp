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
una connessione separata, che poi pubblica. Senza canale di log restituisce la sentinella nulla e
non pubblica niente.

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
Dove il canale è attivo, il registro cresce quindi di una riga per transazione che scrive su una
tabella tracciata.

---

### Come nasce un id nuovo

1. **Il GUC.** Se `dbops.tx_id` contiene un UUID, la funzione lo restituisce e non fa altro.
2. **La connessione di log.** `script.fn_ensure_logconn` apre o ritrova `logconn`. Assorbe la
   connessione già aperta e il troppo-connessioni, non gli altri errori di connessione.
3. **Il canale.** Se `myapp.dblink_log_connection` non è impostato, ripiego: avviso e sentinella.
4. **La generazione.** `dbops.fn_generate_tx_id` gira sulla connessione persistente `logconn`. Se
   `logconn` non c'è, o cade durante la chiamata, la funzione la chiude e riprova **una** volta con
   una connessione nuova, aperta dalla stringa del canale.
5. **La pubblicazione.** Solo un id restituito dal registro si pubblica. Un `NULL` dal canale, o un
   errore, sono ripieghi: avviso nel log del server e sentinella, senza pubblicare.

Un problema del canale durante la generazione diventa un avviso, e la scrittura del chiamante
prosegue con la sentinella. ⚠️ Non così all'apertura di `logconn` (passo 2), che sta fuori dalla
protezione: se il canale è impostato ma la connessione non si apre (credenziali o servizio
sbagliati, server irraggiungibile), l'errore esce dalla funzione, e il trigger del `tx_id` lo
trasforma in `E_TXID_GENERATION`, che blocca la scrittura.

⚠️ L'interruttore `myapp.log_with_dblink` lo rispetta solo `script.fn_ensure_logconn`, che con
`off` non apre `logconn`. Se il canale è impostato, la generazione passa comunque dalla stringa di
connessione: con l'interruttore spento il `tx_id` nasce lo stesso fuori transazione, aprendo una
connessione a ogni transazione.

---

### Senza canale, nessuna correlazione

Senza canale tutte le righe portano la sentinella nulla, e le transazioni non si distinguono dal
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

---

{% include-markdown "signature-core.md" %}
