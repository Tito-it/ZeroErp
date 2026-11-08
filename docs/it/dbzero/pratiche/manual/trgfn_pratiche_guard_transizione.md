## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_guard_transizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la tabella su cui è montata
> * [config.transizioni_stati_pratiche](/dbzero/config/tabelle/transizioni_stati_pratiche) — la matrice delle transizioni ammesse
> * [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche) — gli stati della pratica
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

`pratiche.trgfn_pratiche_guard_transizione` blocca i cambi di stato di una pratica che la matrice
`config.transizioni_stati_pratiche` non ammette.

---

### La regola

* Una transizione è ammessa se la coppia (stato di partenza, stato di arrivo) è una riga attiva della
  matrice. Una riga disattivata non ammette più quella transizione.
* Se lo stato non cambia non c'è niente da controllare.
* Nel messaggio d'errore gli stati compaiono col loro codice interno, così chi legge sa da dove a dove
  si voleva passare.

È montata `BEFORE UPDATE OF stato_id`, riga per riga, nella fase dei guard (`_a10_`), e scatta solo
quando lo stato cambia davvero: gira prima dei trigger di giornale, quindi una transizione rifiutata
non lascia traccia nel giornale.

---

### Codici errore

* `E_PRATICHE_TRANSIZIONE_NON_AMMESSA` — la transizione non è nella matrice, o la sua riga non è attiva.

---

{% include-markdown "signature-core.md" %}
