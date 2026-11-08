## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_transizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.transizioni_stati_flussi_pratiche](/dbzero/config/tabelle/transizioni_stati_flussi_pratiche) — la matrice delle transizioni ammesse
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — gli stati del flusso
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il flusso che cambia stato
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_guard_transizione` blocca i cambi di stato di un flusso che
la matrice `config.transizioni_stati_flussi_pratiche` non ammette.

---

### La regola

* Scatta a ogni modifica che cambia davvero lo stato di un flusso, nella fase dei guard: prima dei
  trigger che scrivono il giornale.
* La coppia (stato di partenza, stato di arrivo) deve comparire fra le righe attive della matrice; una
  riga spenta non ammette niente.
* La transizione è un dato, non codice: per ammetterne una nuova si aggiunge una riga alla matrice.
* L'inserimento non passa di qui: lo stato con cui un flusso nasce lo presidiano altri controlli.

---

### Codici errore

* `E_FLUSSI_TRANSIZIONE_NON_AMMESSA` — la transizione non è nella matrice; la frase nomina i due stati
  per codice interno.

---

### Test

* `pratiche/test-transizioni-stati` — transizioni ammesse e rifiutate dei flussi.

---

{% include-markdown "signature-core.md" %}
