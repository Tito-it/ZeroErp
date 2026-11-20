## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_superficie`

> **Ultimo aggiornamento**: 20 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_seed_riga](/dbzero/dbops/funzioni/fn_seed_riga) — la domanda «nata dal seed», che questa funzione chiede
> * [dbops.fn_seed_colonne_del_software](/dbzero/dbops/funzioni/fn_seed_colonne_del_software) — le colonne del software della tabella, che il chiamante legge una volta e passa
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — il guard che rifiuta le stesse colonne
>
> Approfondimento viste:
>
> * [config.vw_email_account_seed](/dbzero/config/views/vw_email_account_seed) e [config.vw_email_template_seed](/dbzero/config/views/vw_email_template_seed) — chiamanti: le superfici della posta
>
> Guide:
>
> * [Framework di automazione DB — 4.9 SEED_PRIMO_IMPIANTO](/guide/automazione-db#49-seed_primo_impianto-la-riga-modificata-dallinstallazione-non-si-riscrive) — la regola

---

### 🎯 Scopo Principale

Dice all'interfaccia che cosa fare con una riga di una tabella iscritta al seed di primo impianto:
se l'ha installata il software (`nata_dal_seed`) e quali suoi campi l'installazione non può
cambiare (`campi_del_software`). Le liste e i dettagli lo usano per spegnere il cestino e i campi,
con la stessa risposta del guard che altrimenti rifiuterebbe.

---

### La regola

* **Una riga sola**, sempre, anche per un id che non esiste.
* `nata_dal_seed` è la risposta di [fn_seed_riga](/dbzero/dbops/funzioni/fn_seed_riga): vero se la
  riga ha la sua voce nel registro.
* `campi_del_software` è l'elenco ricevuto, su una riga nata dal seed; altrimenti è vuoto. Non è
  mai `NULL`, nemmeno se l'elenco ricevuto lo è.
* Una tabella che non è iscritta risponde come una riga dell'installazione: non nata dal seed,
  nessun campo spento.
* Non elenca i campi che altri meccanismi tengono fermi (il lucchetto di colonna): la superficie
  che li vuole li aggiunge da sé.

⭐ **Perché le colonne le passa il chiamante.** Le colonne del software valgono per la tabella, non
per la riga. Il chiamante le legge una volta, con
[fn_seed_colonne_del_software](/dbzero/dbops/funzioni/fn_seed_colonne_del_software) in una
sottoquery non correlata, e la funzione giudica ogni riga senza rileggerle. È la forma «lettura e
giudizio in due metà» delle linee guida SQL (§13.2).

⭐ **Perché esiste.** Le superfici della posta scrivevano ciascuna la stessa regola, e le liste
admin di `ui` ne chiedevano altre tre: la regola sta qui, e chi mostra il segno del seed passa da
qui.

---

### Test

* `db/pgtap/dbops/test-fn-seed-superficie-v1.sql` — riga di seed, riga dell'installazione,
  elenco `NULL`, tabella non iscritta, una riga sola, le due viste che la leggono.
* `db/pgtap/config/test-posta-solo-disattivazione-v1.sql` — le superfici della posta.

---

### Note di migrazione

* 2026-11-20 — nasce come seconda occorrenza delle superfici della posta, che si riscrivono sopra
  di lei (`brief-db-seed-primo-impianto-non-si-riscrive` §16.15, QU3).

---

{% include-markdown "signature-core.md" %}
