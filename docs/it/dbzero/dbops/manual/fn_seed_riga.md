## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_riga`

> **Ultimo aggiornamento**: 19 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.seed_righe](/dbzero/dbops/tabelle/seed_righe) — il registro che legge
>
> Approfondimento funzioni:
>
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — chiamante: il guard, all'`UPDATE` e al `DELETE`
>
> Approfondimento viste:
>
> * [config.vw_email_account_seed](/dbzero/config/views/vw_email_account_seed) e [config.vw_email_template_seed](/dbzero/config/views/vw_email_template_seed) — chiamanti: il segno «nata dal seed» per l'interfaccia
>
> Guide:
>
> * [Framework di automazione DB — 4.9 SEED_PRIMO_IMPIANTO](/guide/automazione-db#49-seed_primo_impianto-la-riga-modificata-dallinstallazione-non-si-riscrive) — la regola

---

### 🎯 Scopo Principale

Risponde alla domanda «questa riga è nata dal seed?» in una sede sola. Data una tabella e l'id di
una riga, restituisce la voce del registro [seed_righe](/dbzero/dbops/tabelle/seed_righe), oppure
nessuna riga.

---

### La regola

* **Una riga = nata dal seed.** Nessuna riga = l'ha creata l'installazione, oppure la tabella non è
  iscritta al seed di primo impianto. I due casi non si distinguono, e per chi chiede valgono lo
  stesso: nessuna colonna è del software.
* La tabella entra come `regclass`: schema e nome si leggono dal catalogo, non dal testo del
  `regclass`, che cambia col `search_path`. L'id entra come testo, la forma in cui lo tiene il
  registro.
* `personalizzata_il` dice se l'installazione ha già modificato la riga: il guard lo usa per
  decidere se il CSV la riscrive.

⭐ **Perché esiste.** La chiave del registro ha una forma sua (schema e tabella di testo, id di
testo). Prima la scriveva il guard nel suo join. Con le superfici che dicono all'interfaccia quali
campi spegnere le copie sarebbero diventate tre. Chi legge «nata dal seed» passa da qui.

---

### Test

* `db/pgtap/config/test-posta-solo-disattivazione-v1.sql` — le superfici degli account e dei
  template, e l'id `NULL` (test 14).
* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql` e
  `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql` — il guard che la chiama.

---

### Note di migrazione

* 2026-11-19 — nasce, estratta dal guard quando la stessa domanda è servita alle superfici degli
  account e dei template (`brief-db-seed-primo-impianto-non-si-riscrive` §16.14).

---

{% include-markdown "signature-core.md" %}
