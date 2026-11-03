## 📘 Documentazione Concettuale – Tabella `dbops.transaction_ids`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_generate_tx_id](/dbzero/dbops/funzioni/fn_generate_tx_id) — la sola funzione che ci scrive
> * [dbops.fn_get_or_create_session_tx_id](/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id) — chiede un id nuovo, fuori transazione
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed) — il trigger che verifica qui l'id della sessione
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il blocco di modifiche e cancellazioni
>
> Guide:
>
> * [Transaction ID](/guide/tx_id_implementation_guide) — come nasce e come si propaga il `tx_id`

---

### 🎯 Scopo Principale

Il **registro dei transaction id**: ogni `tx_id` che il sistema pubblica nella sessione nasce qui,
con la funzione che l'ha chiesto e un contesto. Le righe toccate nella stessa transazione portano
quell'id nella colonna `tx_id`, e si ritrovano insieme.

Un id assente da questo registro non è un id della transazione: è la regola su cui il trigger del
`tx_id` verifica la sessione.

---

### ⭐ Si scrive fuori dalla transazione, da una sola porta

Le righe le scrive solo `dbops.fn_generate_tx_id`, chiamata da
`dbops.fn_get_or_create_session_tx_id` su una **connessione separata**: la registrazione
sopravvive all'annullamento della transazione che l'ha chiesta. Così un id usato da una
transazione annullata resta registrato, e non lo riceve nessun'altra.

La chiave è un UUID v7: cresce nel tempo.

* `generating_function` è la funzione che ha chiesto l'id;
* `session_info` è il contesto della richiesta, un oggetto JSON (vuoto se non c'è niente da dire).

---

### ⛔ Il registro non si modifica e non si cancella

Un trigger `BEFORE UPDATE OR DELETE` con `script.trgfn_prevent_modification_generic` rifiuta ogni
modifica e ogni cancellazione: un id registrato resta com'è. Per lo stesso motivo `user_update` e
`data_update` restano vuote: la tabella non è nel perimetro delle automazioni di audit, e nessuno
le scrive.

⚠️ Non ha una scadenza: le righe crescono di una per transazione che scrive su una tabella
tracciata, dove il canale di log è attivo.

---

### Test

* `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql` — con il canale attivo l'id restituito è
  registrato qui; senza canale non si pubblica un id che qui non c'è.
* `db/pgtap/dbops/test-user-update-not-null-v1.sql` — la tabella è nel registro del debito delle
  colonne `user_update` che ammettono il vuoto, come registro tecnico che nessuno aggiorna.

---

{% include-markdown "signature-core.md" %}
