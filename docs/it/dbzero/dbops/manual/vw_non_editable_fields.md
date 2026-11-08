## 📘 Documentazione Concettuale – Vista `dbops.vw_non_editable_fields`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [dbops.vw_lock_columns_vivi](/dbzero/dbops/views/vw_lock_columns_vivi) — i trigger di lock vivi, da cui la vista legge
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro da cui il runner monta i trigger
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — i blocchi che dipendono dallo stato della riga, che qui non ci sono
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) — il testo dei codici errore del blocco
>
> Approfondimento funzioni:
>
> * [dbops.fn_non_editable_fields](/dbzero/dbops/funzioni/fn_non_editable_fields) — i blocchi di una riga precisa, incondizionati e condizionali insieme
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — il confronto fra il lock vivo e il registro
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il trigger che rifiuta l'UPDATE

---

### 🎯 Scopo Principale

Le colonne **non modificabili dopo l'inserimento**, per ogni tabella: una riga per ogni colonna che
un trigger di lock vivo e abilitato blocca, con il codice errore che l'UPDATE solleverebbe e il
nome del trigger. È il punto da cui il backend legge quali campi presentare in sola lettura.

---

### ⭐ Dice ciò che il database rifiuta

La vista legge i **trigger**, non il registro. Il form deve spegnere un campo esattamente quando
il salvataggio verrebbe rifiutato, e chi lo rifiuta è il trigger su `script.trgfn_lock_columns`:
la vista legge i suoi argomenti (le coppie colonna, codice) da `dbops.vw_lock_columns_vivi`.

Ne seguono tre cose:

* `codice_interno` compare su ogni tabella dove il runner lo blocca, anche se il registro non lo
  nomina: è la colonna implicita del framework;
* una riga del registro che nessun trigger applica (spenta, di un'altra modalità che non l'ha
  ancora montata, o su una tabella fuori dall'ambito delle automazioni) **non** compare: l'UPDATE
  passerebbe;
* un trigger disabilitato non blocca niente, e le sue colonne non compaiono.

Se il lock vivo e il registro non coincidono, non è la vista a ripararlo: diventa rosso il
presidio `dbops/test-lock-columns-convergenza`, e il runner li riallinea.

---

### Che cosa elenca

* `column_name` e `error_code`: la coppia di argomenti del trigger. Il codice più comune è
  `E_CODICE_NON_MODIFICABILE`, ma molte colonne portano un codice del loro dominio, che dice quale
  identità della riga è immutabile. Il backend lo usa per il messaggio da mostrare;
* `trigger_name`: il trigger che blocca la colonna. Una colonna bloccata da due trigger compare due
  volte (è già una divergenza, che il presidio vede).

---

### ⛔ Che cosa non elenca

* **i blocchi condizionali**, che dipendono dallo stato della riga (i flag di struttura di un
  articolo padre di una distinta in vigore, i campi di un documento in uno stato chiuso): per
  quelli, data una riga, c'è `dbops.fn_non_editable_fields`. Le regole di modifica più complesse
  restano nei guard di dominio e nei service.

---

### Test

* `db/pgtap/dbops/test-non-editable-fields-dal-lock-vivo-v1.sql` — su uno schema di prova:
  `codice_interno` bloccato e assente dal registro è elencato, una riga del registro senza trigger
  no, un trigger disabilitato no, e l'UPDATE conferma la vista.

---

### Note di migrazione

* 2026-04-28 — nasce come nome semantico sopra il registro, al posto di una tabella nuova chiesta dal
  backend.
* 2026-05-22 — i blocchi condizionali prendono il loro registro e la loro funzione; questa vista
  resta per i blocchi incondizionati.
* 2026-11-08 — legge il lock vivo invece del registro (`20261109-61`, brief-db-revisione-dbops
  D25): prima mancava `codice_interno`, che il backend aggiungeva a mano, ed erano elencate righe
  del registro che nessun trigger applicava. Escono le colonne `exec_mode` e `note`, entra
  `trigger_name`.

---

{% include-markdown "signature-core.md" %}
