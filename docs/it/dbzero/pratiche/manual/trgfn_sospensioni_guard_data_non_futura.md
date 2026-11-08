## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_guard_data_non_futura`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la tabella che il guard presidia
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_set_periodo](/dbzero/pratiche/funzioni/trgfn_sospensioni_set_periodo) — deriva il periodo dalle due date, dopo questo guard
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_sospensioni_guard_data_non_futura` vieta che una sospensione
inizi o finisca nel futuro: una sospensione registra un fatto già avvenuto, anche retroattivo, non
uno pianificato.

---

### La regola

* `data_inizio` e, se valorizzata, `data_fine` non possono superare l'istante corrente oltre una
  tolleranza di due minuti. La tolleranza assorbe lo sfasamento fra l'orologio del client e quello del
  server, senza falsi positivi su una chiusura «adesso»; una data davvero futura resta bloccata.
* Il controllo scatta all'inserimento e a ogni modifica delle due date, nella fase dei guard: prima
  che `pratiche.trgfn_sospensioni_set_periodo` ne derivi il periodo.
* `data_riattivazione_prevista` è una previsione e resta libera nel futuro: il guard non la guarda.

È una difesa in più accanto al vincolo che impedisce a due sospensioni di sovrapporsi
(`ex_sospensioni_no_overlap`) e alla validazione del backend: l'autorità resta il database.

---

### Codici errore

* `E_SOSPENSIONE_DATA_FUTURA` — `data_inizio` o `data_fine` nel futuro; il contesto dell'errore dice
  quale delle due.

---

{% include-markdown "signature-core.md" %}
