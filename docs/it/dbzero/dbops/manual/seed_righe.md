## 📘 Documentazione Concettuale – Tabella `dbops.seed_righe`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) — le tabelle iscritte, e la loro forma
>
> Approfondimento funzioni:
>
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — scrive il registro, e lo legge a ogni scrittura
> * [dbops.fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto) — iscrive le righe di seed già presenti
>
> Guide:
>
> * [Linee guida SQL — 11.7 Le tre specie di seed](/linee-guida-sql#117-in-80_data-convivono-tre-specie-di-seed-catalogo-primo-impianto-e-macchina) — la specie di primo impianto
> * [Framework di automazione DB — 4.9 SEED_PRIMO_IMPIANTO](/guide/automazione-db#49-seed_primo_impianto-la-riga-modificata-dallinstallazione-non-si-riscrive) — la regola

---

### 🎯 Scopo Principale

Il registro delle righe **nate dal seed** sulle tabelle del seed di primo impianto. Una riga di
quelle tabelle che qui c'è l'ha creata il software, dal CSV; una che qui non c'è l'ha creata
l'installazione, e il CSV non la tocca mai.

⭐ **Il segno sta qui, e non in una colonna della riga.** Una colonna della riga (per esempio
`user_insert`) la può scrivere chiunque possa scrivere la riga: l'app che la cambiasse renderebbe
cancellabile una riga di seed, o intoccabile una sua. Il registro lo scrivono solo il trigger e il
runner, e l'applicazione lo legge soltanto.

---

### Una riga per riga di seed

* `schema_name`, `table_name`, `riga_id` — la riga di seed. La chiave è unica
  (`uq_seed_righe_tabella_riga`); `riga_id` è l'`id` della riga reso a testo, e segue la riga se il
  software ne cambia l'`id`.
* `segnata_da` — come è entrata: `INSERT`, quando il software l'ha inserita col trigger montato;
  `ISCRIZIONE`, quando la riga c'era già e il runner l'ha riconosciuta all'iscrizione della tabella.
* `personalizzata_il`, `personalizzata_da` — quando l'installazione ha cambiato una sua colonna, e
  chi. Vuote, la riga è **intatta** e segue il CSV; piene, è **personalizzata** e il CSV non le
  riscrive più le colonne dell'installazione. `meta`, le colonne d'audit e `tx_id` non contano.
* `scartati`, `scartati_il` — gli ultimi valori del CSV che il trigger non ha scritto su una riga
  personalizzata, colonna per colonna. Servono a vedere che cosa il software avrebbe portato.

---

### Chi la scrive

* [trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto): inserisce la riga
  all'`INSERT` del software, la marca personalizzata all'`UPDATE` dell'installazione, scrive i
  valori scartati, la toglie quando una riga di seed si cancella dalla porta di manutenzione.
* [fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto):
  all'iscrizione di una tabella, segna le righe già presenti scritte dal seed (`user_insert` uguale a
  `SEED` o a un ruolo del migratore).

⛔ Una riga personalizzata torna a seguire il CSV solo togliendo il segno a mano, dal migratore.
Un'azione «ripristina il valore di fabbrica» dall'interfaccia non c'è.

⚠️ In **solo inserimento** il registro dice solo «nata dal seed»: il CSV non aggiorna più quelle
righe, toccate o no, e i valori scartati non si scrivono.

---

### Test

* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql` — l'`INSERT` e l'iscrizione, i valori
  scartati, la riga di seed cancellata dalla porta.
* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql` — l'installazione personalizza la
  riga.
* `db/pgtap/dbops/test-seed-primo-impianto-postura-v1.sql` — all'applicazione solo `SELECT`.

---

### Note di migrazione

* 2026-11-17 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive`). Alla prima corsa del runner
  ha iscritto su dbdev 1 riga di `config.email_account` e 9 di `config.email_template`.

---

{% include-markdown "signature-core.md" %}
