## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_tfap_guard_compatibilita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi_avanzamento_proiezione](/dbzero/pratiche/tabelle/template_flussi_avanzamento_proiezione) — il binding che il guard protegge
> * [pratiche.template_flussi_handler_eventi](/dbzero/pratiche/tabelle/template_flussi_handler_eventi) — gli handler con cui il binding non coesiste
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — la modalità di esito dello step
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_tfhe_guard_no_proiezione](/dbzero/pratiche/funzioni/trgfn_tfhe_guard_no_proiezione) — il guard speculare, dal lato degli handler
> * [pratiche.trgfn_flussi_guard_esito_classe](/dbzero/pratiche/funzioni/trgfn_flussi_guard_esito_classe) — il controllo a runtime che uno step `DOMINIO` farebbe scattare
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

`pratiche.trgfn_tfap_guard_compatibilita` è il guard di configurazione del binding di avanzamento su
proiezione: lo ammette solo su uno step che accetta verdetti, e non lo lascia coesistere con un handler
che completa lo stesso step.

È montata `BEFORE INSERT OR UPDATE`, riga per riga, su `pratiche.template_flussi_avanzamento_proiezione`.

---

### ⛔ Solo su uno step non `DOMINIO`

La proiezione produce **verdetti**. Uno step con `modalita_esito = 'DOMINIO'` vuole esiti di ramo, e li
rifiuterebbe a runtime con `pratiche.trgfn_flussi_guard_esito_classe`: ma l'avanzamento su proiezione
è best-effort, e il rifiuto resterebbe silenzioso. Il milestone non avanzerebbe mai, senza che nessuno
lo sappia. Per questo il guard lo blocca alla configurazione.

---

### ⛔ O proiezione o handler, mai entrambi

Uno step avanza o per proiezione o per l'handler sull'evento `COMPLETATO`, mai per entrambi: altrimenti
l'avanzamento dal database completerebbe il flusso saltando l'handler del backend, e l'azione di
dominio andrebbe persa in silenzio.

Il conflitto si valuta fra binding entrambi attivi. Un handler disattivato non fa niente, quindi il
passaggio da handler a proiezione si fa senza cancellare: si disattiva l'handler, poi si inserisce il
binding. Il lato opposto (un handler aggiunto a uno step che ha già il binding) lo presidia
`pratiche.trgfn_tfhe_guard_no_proiezione`.

---

### Codici errore

* `E_TEMPLATE_FLUSSO_PROIEZIONE_STEP_DOMINIO` — il binding punta a uno step `DOMINIO`.
* `E_TEMPLATE_FLUSSO_PROIEZIONE_CONFLITTO_HANDLER` — sullo stesso step c'è già un handler attivo
  sull'evento `COMPLETATO`.

---

### Note di migrazione

* 2026-07-06 — nasce con il binding di avanzamento su proiezione (brief-db-guida-avanza-esito-proiettato).

---

{% include-markdown "signature-core.md" %}
