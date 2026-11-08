## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_prerequisiti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella su cui scatta il trigger
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) — i prerequisiti dichiarati sul template
>
> Approfondimento funzioni:
>
> * [pratiche.fn_guard_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_guard_prerequisiti_flusso) — la sentinella che solleva l'errore
> * [pratiche.fn_check_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso) — il controllo puro, dove sta la regola
> * [pratiche.trgfn_flussi_guard_ripetibilita](/dbzero/pratiche/funzioni/trgfn_flussi_guard_ripetibilita) — l'involucro gemello per la ripetibilità

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_guard_prerequisiti` applica i prerequisiti del template a
ogni nuovo flusso di pratica: delega la verifica a `pratiche.fn_guard_prerequisiti_flusso`, che rifiuta
l'inserimento quando i prerequisiti non sono soddisfatti.

---

### Le regole

* Il controllo vale per ogni flusso, perché ognuno nasce da un template (`template_flusso_id` è
  obbligatorio); un template senza prerequisiti dichiarati passa.
* La regola non è scritta qui: sta in `pratiche.fn_check_prerequisiti_flusso`, e la sentinella aggiunge
  l'errore. Il trigger è solo l'aggancio, così la regola vale per ogni strada di scrittura.

Scatta prima di ogni inserimento in `pratiche.flussi`, nella fase dei guard.

---

### Codici errore

* `E_PRATICHE_PREREQUISITI_NON_SODDISFATTI` — sollevato dalla sentinella.

---

### Test

* `pratiche/test-fn-guard-prerequisiti-flusso` — la sentinella e il rifiuto sull'inserimento.
* `pratiche/test-trigger-guard-flussi` — i guard montati su `pratiche.flussi`.

---

{% include-markdown "signature-core.md" %}
