## 📘 Documentazione Concettuale – Funzione `pratiche.fn_guard_ripetibilita_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — la regola `ripetibilita` del template
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_ripetibilita_flusso](/dbzero/pratiche/funzioni/fn_check_ripetibilita_flusso) — il controllo puro, dove sta la regola
> * [pratiche.trgfn_flussi_guard_ripetibilita](/dbzero/pratiche/funzioni/trgfn_flussi_guard_ripetibilita) — il trigger che la chiama
> * [pratiche.fn_guard_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_guard_prerequisiti_flusso) — la sentinella simmetrica dei prerequisiti
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

`pratiche.fn_guard_ripetibilita_flusso` è la sentinella della regola di ripetibilità: se la regola del
template vieta una nuova istanza nella pratica, solleva `E_PRATICHE_FLUSSO_NON_RIPETIBILE`; altrimenti
ritorna senza effetti.

La regola non è scritta qui: la sentinella chiede a `pratiche.fn_check_ripetibilita_flusso` e aggiunge
solo l'errore, come `pratiche.fn_guard_prerequisiti_flusso` fa per i prerequisiti.

---

### Dove si applica

La chiama il trigger `pratiche.trgfn_flussi_guard_ripetibilita` prima di ogni inserimento in
`pratiche.flussi`: ogni flusso nasce da un template (`template_flusso_id` è obbligatorio), e la
regola vale per qualunque chiamante (backend, funzioni del database, SQL diretto).

---

### Codici errore

* `E_PRATICHE_FLUSSO_NON_RIPETIBILE` — la regola del template vieta una nuova istanza: `MAI` con
  un'istanza già presente, oppure `SE_NON_POSITIVO` con l'ultima istanza ancora aperta o chiusa
  `POSITIVO`. La frase nomina il template, la regola e lo stato (con l'esito) dell'ultima istanza
  non annullata; gli stessi fatti stanno nel contesto dell'errore.

---

### Test

* `pratiche/test-ripetibilita-flussi` — il rifiuto sull'inserimento e i casi ammessi.

---

{% include-markdown "signature-core.md" %}
