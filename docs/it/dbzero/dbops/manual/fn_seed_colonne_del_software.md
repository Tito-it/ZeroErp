## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_colonne_del_software`

> **Ultimo aggiornamento**: 19 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_seed_primo_impianto_argomenti](/dbzero/dbops/funzioni/fn_seed_primo_impianto_argomenti) — la grammatica degli argomenti, la stessa del guard
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — il guard che rifiuta sulle stesse colonne
> * [dbops.fn_seed_primo_impianto_divergenze](/dbzero/dbops/funzioni/fn_seed_primo_impianto_divergenze) — dice quando il montaggio e il registro della regola divergono
>
> Approfondimento viste:
>
> * [config.vw_email_account_seed](/dbzero/config/views/vw_email_account_seed) e [config.vw_email_template_seed](/dbzero/config/views/vw_email_template_seed) — chiamanti: i campi da spegnere

---

### 🎯 Scopo Principale

Dice quali colonne di una tabella iscritta sono **del software**: quelle che, su una riga nata dal
seed, l'installazione non modifica. Le superfici degli account e dei template le espongono come
`campi_del_software`, e il frontend spegne quei campi nel form.

---

### La regola

* ⭐ **Si leggono dal montaggio del trigger, non dal registro della regola.** Il guard rifiuta
  leggendo i suoi argomenti con
  [fn_seed_primo_impianto_argomenti](/dbzero/dbops/funzioni/fn_seed_primo_impianto_argomenti); qui
  si leggono gli stessi argomenti con la stessa funzione. Il campo è spento esattamente dove il
  guard rifiuterebbe, anche prima che il `ci_apply` riallinei il montaggio al registro.
* Vuoto, mai `NULL`, per: una tabella senza il trigger o col trigger spento; le forme `RIGA` e
  `SOLO_INSERIMENTO`, che non hanno colonne del software; un montaggio fuori grammatica, su cui il
  guard alza `E_TRIGGER_ARGOMENTI_INVALIDI`.
* Vale per la **tabella**. Su una riga dell'installazione nessuna colonna è del software: le
  superfici incrociano il risultato con [fn_seed_riga](/dbzero/dbops/funzioni/fn_seed_riga).
* Non elenca le colonne che altri meccanismi tengono ferme, per esempio i lucchetti di
  `script.trgfn_lock_columns`.

---

### Test

* `db/pgtap/config/test-posta-solo-disattivazione-v1.sql` — sul template di seed le colonne sono
  quelle della regola (test 8) e sono colonne vere (test 9); una tabella senza il trigger dà un
  elenco vuoto (test 13).

---

### Note di migrazione

* 2026-11-19 — nasce per le superfici degli account e dei template
  (`brief-db-seed-primo-impianto-non-si-riscrive` §16.14).

---

{% include-markdown "signature-core.md" %}
