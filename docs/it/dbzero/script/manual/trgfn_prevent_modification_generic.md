## 📘 Documentazione Concettuale – Trigger function `script.trgfn_prevent_modification_generic`

> **Ultimo aggiornamento**: 15 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.documenti_generati](/dbzero/documenti/tabelle/documenti_generati) — la stampa, che non si cancella
> * [documenti.documenti_generati_eventi](/dbzero/documenti/tabelle/documenti_generati_eventi) — la cronologia della stampa, che non si modifica e non si cancella
> * [documenti.documenti_generati_file](/dbzero/documenti/tabelle/documenti_generati_file) — il file della stampa, che non si cancella
> * [documenti.template_asset](/dbzero/documenti/tabelle/template_asset) — l'asset, che non si cancella
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro del plafond IVA, «solo aggiunte»
> * [dbops.transaction_ids](/dbzero/dbops/tabelle/transaction_ids) — il registro delle transazioni
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il rifiuto
> * [script.trgfn_delete_block_by_guc](/dbzero/script/funzioni/trgfn_delete_block_by_guc) — il blocco della cancellazione che ha una porta
>
> Guide:
>
> * [Linee guida Trigger](/linee-guida-trigger) — i nomi, le fasi, gli argomenti di un building block

---

### 🎯 Scopo Principale

Il building block «rifiuta sempre»: montato su una tabella, vieta le operazioni del suo evento a chiunque, owner
compreso. Non decide niente: la sola presenza del trigger è la regola.

Serve alle tabelle che sono storia (una stampa, la sua cronologia, il suo file, un registro «solo aggiunte»): lì una
riga scritta resta, e la correzione è una riga nuova.

---

### Il codice lo dice il montaggio

Chi monta il trigger gli passa, come argomenti, ciò che il rifiuto deve dire:

* **il primo argomento è il codice d'errore**, quello della tabella: chi legge il rifiuto sa *che cosa* non si fa
  (una stampa non si cancella, un movimento di plafond non si modifica). Senza argomenti il codice è
  `E_TABELLA_OP_NON_CONSENTITA`, con la tabella e l'operazione nella frase;
* **gli altri argomenti sono colonne della riga**, i cui valori entrano nella frase nell'ordine dei segnaposto del
  messaggio. Una data si scrive come la legge una persona (giorno, mese, anno). La riga è quella che si stava per
  modificare o cancellare, oppure quella proposta su un inserimento.

Una colonna che la tabella non ha è un montaggio sbagliato, e il trigger lo dice
(`E_TRIGGER_ARGOMENTI_INVALIDI`) invece di comporre una frase con un buco.

Il contesto del rifiuto porta la tabella, l'operazione e l'`id` della riga; il `tx_id` viene dalla riga, se la
tabella lo porta.

---

### ⛔ Nessuna porta

Il building block non ha eccezioni: niente variabile di sessione che lo apra, niente ruolo che lo scavalchi. Dove
una scrittura legittima deve passare (una manutenzione dichiarata, una riga scaduta che la pulizia ritira) la
regola è un'altra, e vuole un guard suo: `script.trgfn_delete_block_by_guc` per una cancellazione con la sua porta,
`vendite.trgfn_event_log_append_only` per un registro con la sua scadenza.

---

### Dove è montato

* `documenti.documenti_generati`, sul `DELETE` (`E_DOCUMENTI_GENERATO_DELETE_BLOCKED`);
* `documenti.documenti_generati_eventi`, sull'`UPDATE` e sul `DELETE` (`E_EVENTO_DOCUMENTO_UPDATE_VIETATA`,
  `E_EVENTO_DOCUMENTO_DELETE_VIETATA`);
* `documenti.documenti_generati_file`, sul `DELETE` (`E_FILE_DOCUMENTO_DELETE_VIETATA`);
* `documenti.template_asset`, sul `DELETE` (`E_DOCUMENTI_ASSET_DELETE_BLOCKED`);
* `anagrafiche.soggetti_titoli_iva_movimenti`, sull'`UPDATE` e sul `DELETE` (`E_TITOLO_IVA_MOVIMENTO_IMMUTABILE`,
  col tipo e la data del movimento nella frase);
* `dbops.transaction_ids`, sull'`UPDATE` e sul `DELETE`, senza argomenti.

Una tabella nuova che deve vietare sempre un'operazione monta questo building block col suo codice: non si scrive
una funzione propria che faccia la stessa cosa.

---

### Codici errore

* il codice del montaggio, oppure `E_TABELLA_OP_NON_CONSENTITA` senza argomenti;
* `E_TRIGGER_ARGOMENTI_INVALIDI` — una colonna degli argomenti non esiste nella tabella.

---

### Test

* `db/pgtap/documenti/test-documenti-stampa-e-storia-v1.sql` — il codice di riserva, i valori della riga nella
  frase con la data, la colonna che non esiste, i montaggi sulle tabelle di `documenti` e del plafond IVA, le copie
  ritirate;
* `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql` — il registro del plafond rifiuta modifica e
  cancellazione.

---

### Note di migrazione

* 2026-08-06 — il rifiuto si registra col nome del trigger che scatta, non con quello di una funzione che non
  esisteva più.
* 2026-11-15 — il building block riceve il codice e le colonne dal montaggio; le funzioni proprie di stampa,
  eventi, asset e movimenti di plafond, che facevano la stessa cosa con un codice ciascuna, sono ritirate.

---

{% include-markdown "signature-core.md" %}
