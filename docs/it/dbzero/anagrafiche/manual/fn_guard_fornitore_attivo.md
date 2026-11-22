## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_fornitore_attivo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori) — il flag `attivo` e lo stato del fornitore
> * [config.stati_fornitore](/dbzero/config/tabelle/stati_fornitore) — il flag `blocca_ordini` e la descrizione dello stato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_fornitore_attivo](/dbzero/anagrafiche/funzioni/fn_check_fornitore_attivo) — la stessa domanda, senza rifiuto
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — il registro degli errori, da cui passa il rifiuto

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_fornitore_attivo` ferma l'operazione quando un fornitore non si può usare: non esiste, è
spento, o il suo stato blocca gli ordini. Se il fornitore si può usare non restituisce niente e non scrive niente.

---

### I motivi, nell'ordine

Il guard guarda un motivo alla volta e si ferma al primo: l'id dev'essere passato e positivo, il fornitore deve
esistere, dev'essere attivo, e il suo stato non deve bloccare gli ordini. Ogni motivo ha il suo codice, e il
chiamante sa quale.

È la metà «rifiuto» della coppia con `anagrafiche.fn_check_fornitore_attivo`, che risponde sì o no alla stessa
domanda: il guard serve dove l'operazione si deve fermare, il check dove l'esito è un dato.

---

### Chi la usa

Nessun oggetto del database la chiama: è a disposizione dei flussi che devono rifiutare un fornitore non
utilizzabile (un ordine, un documento del ciclo passivo). Gira coi permessi di chi la chiama; i fornitori non hanno
visibilità per azienda.

---

### ⚠️ Che cosa oggi non copre

* **La regola sta in due corpi.** Il guard e il check scrivono ciascuno la propria lettura di «attivo e non
  bloccato»: una condizione aggiunta a uno dei due non arriva all'altro.
* **Il messaggio del fornitore bloccato si ripete.** `E_FORNITORE_BLOCCATO` riempie il segnaposto del messaggio,
  che vuole l'id, con una frase intera (id e stato): il testo che arriva a chi legge dice due volte il fornitore.

---

### Codici errore

* `E_FORNITORE_ID_INVALIDO` — l'id non è passato, o non è positivo.
* `E_FORNITORE_NON_TROVATO` — il fornitore non esiste.
* `E_FORNITORE_NON_ATTIVO` — il fornitore è spento.
* `E_FORNITORE_BLOCCATO` — lo stato del fornitore blocca gli ordini; il contesto porta la descrizione dello stato.

---

### Test

Nessun pgTAP la prova.

---

{% include-markdown "signature-core.md" %}
