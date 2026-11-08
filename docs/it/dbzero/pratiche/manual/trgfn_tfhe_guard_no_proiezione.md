## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_tfhe_guard_no_proiezione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) — la tabella su cui è montata
> * [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione) — il binding con cui l'handler non coesiste
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_tfap_guard_compatibilita](/dbzero/pratiche/funzioni/trgfn_tfap_guard_compatibilita) — il guard speculare, dal lato del binding
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

`pratiche.trgfn_tfhe_guard_no_proiezione` vieta di aggiungere o attivare un handler sull'evento
`COMPLETATO` per uno step che ha già un binding attivo di avanzamento su proiezione.

È il lato simmetrico di `pratiche.trgfn_tfap_guard_compatibilita`: insieme garantiscono che uno step
avanzi o per proiezione o per handler, mai per entrambi. Altrimenti l'avanzamento dal database
completerebbe il flusso saltando l'handler del backend, e l'azione di dominio andrebbe persa in
silenzio.

---

### Quando scatta

È montata `BEFORE INSERT OR UPDATE`, riga per riga, su `pratiche.template_flussi_handler_eventi`.

* Solo per un handler attivo sull'evento `COMPLETATO`: un handler disattivato o su un altro evento non
  è in conflitto.
* Solo se lo stesso step ha un binding di avanzamento su proiezione attivo.

---

### Codici errore

* `E_TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER` — lo step ha già un binding di avanzamento attivo.

---

### Note di migrazione

* 2026-07-06 — nasce con il binding di avanzamento su proiezione (brief-db-guida-avanza-esito-proiettato).

---

{% include-markdown "signature-core.md" %}
