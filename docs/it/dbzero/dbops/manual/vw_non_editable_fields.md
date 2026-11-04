## 📘 Documentazione Concettuale – Vista `dbops.vw_non_editable_fields`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) — il registro che la vista espone
> * [dbops.lock_columns_conditional](/dbzero/dbops/tabelle/lock_columns_conditional) — i blocchi che dipendono dallo stato della riga, che qui non ci sono
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) — il testo dei codici errore del blocco
>
> Approfondimento funzioni:
>
> * [dbops.fn_non_editable_fields](/dbzero/dbops/funzioni/fn_non_editable_fields) — i blocchi di una riga precisa, incondizionati e condizionali insieme
> * [dbops.fn_run_automations_lock_columns](/dbzero/dbops/funzioni/fn_run_automations_lock_columns) — il runner che monta i trigger di lock dal registro
> * [dbops.fn_lock_columns_divergenze](/dbzero/dbops/funzioni/fn_lock_columns_divergenze) — il lock atteso, con il blocco implicito di `codice_interno`

---

### 🎯 Scopo Principale

Le colonne **non modificabili dopo l'inserimento**, per ogni tabella: le righe abilitate del
registro `dbops.automation_lock_columns`, con il codice errore che il blocco solleva, la modalità e
la nota. È il punto da cui il backend legge quali campi presentare in sola lettura.

Non ha contenuto proprio: ogni modifica (una colonna in più, un blocco disabilitato, un codice
cambiato) si fa sul registro, e la vista la riflette subito.

---

### ⭐ Perché una vista e non una tabella nuova

Il backend aveva chiesto un registro dei campi bloccati. Il registro esisteva già, con più
informazioni (codice errore, modalità, abilitazione, nota): una tabella nuova avrebbe creato due
fonti di verità sulla stessa regola. La vista dà al backend un nome che dice la cosa e lascia la
fonte dov'è.

---

### Che cosa elenca

* solo le righe con `enabled` acceso: una riga spenta è un blocco registrato e tolto di proposito, e
  non deve apparire come blocco attivo;
* tutte le modalità del registro, senza distinguere: il runner dei trigger, invece, applica una riga
  solo nelle modalità che gli competono;
* `error_code` è il codice che il trigger solleva quando qualcuno tenta la modifica: il più comune è
  `E_CODICE_NON_MODIFICABILE`, ma molte righe portano un codice del loro dominio, che dice quale
  identità della riga è immutabile. Il backend lo usa per il messaggio da mostrare.

---

### ⛔ Che cosa non elenca

* **i blocchi condizionali**, che dipendono dallo stato della riga (i flag di struttura di un
  articolo padre di una distinta attiva, i campi di un documento in uno stato chiuso): per quelli,
  data una riga, c'è `dbops.fn_non_editable_fields`. Le regole di modifica più complesse restano nei
  guard di dominio e nei service;
* **il blocco implicito di `codice_interno`.** I trigger di lock bloccano `codice_interno` su ogni
  tabella che ce l'ha, senza che il registro lo nomini. La vista legge solo il registro, quindi su
  quelle tabelle non lo elenca: il backend lo aggiunge a mano fra le colonne che dichiara mancanti
  dal registro, dove se ne ricorda.

---

### Note di migrazione

* 2026-04-28 — nasce come nome semantico sopra il registro, al posto di una tabella nuova chiesta dal
  backend.
* 2026-05-22 — i blocchi condizionali prendono il loro registro e la loro funzione; questa vista
  resta per i blocchi incondizionati.

---

{% include-markdown "signature-core.md" %}
