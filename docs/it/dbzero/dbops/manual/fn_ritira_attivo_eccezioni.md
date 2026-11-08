## 📘 Documentazione Concettuale – Funzione `dbops.fn_ritira_attivo_eccezioni`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automazione_attivo_eccezioni](/dbzero/dbops/tabelle/automazione_attivo_eccezioni) — le FK dichiarate eccezione, che la funzione legge
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il motore che la chiama in testa a ogni giro
> * [dbops.fn_ritira_attivo_orfani](/dbzero/dbops/funzioni/fn_ritira_attivo_orfani) — il ritiro gemello, per i trigger che nominano oggetti spariti
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — legge gli argomenti dei trigger
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — il require sul figlio
> * [dbops.trgfn_prevent_deactivate_if_children](/dbzero/dbops/funzioni/trgfn_prevent_deactivate_if_children) — il block sul padre
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, le eccezioni della regola ATTIVO

---

### 🎯 Scopo Principale

Toglie i trigger ATTIVO **già generati** per le FK dichiarate in
`dbops.automazione_attivo_eccezioni`, e restituisce quanti ne ha tolti.

Esiste perché una FK può diventare eccezione dopo che il motore l'ha già legata: dichiararla non
basta, i trigger che ci sono vanno tolti. Chi genera i trigger li ritira.

---

### ⛔ Li riconosce per funzione e argomenti, non per nome

I nomi generati oltre i 63 caratteri sono troncati con un hash, quindi il nome non è una chiave.
La funzione guarda i trigger non interni delle due funzioni del framework ATTIVO, ne legge gli
argomenti con `dbops.fn_trigger_argomenti`, li interpreta per nome con
`dbops.fn_trigger_attivo_argomenti` (la grammatica delle funzioni trigger) e li confronta con la
riga del registro:

| Trigger | Funzione | Dove sta la FK della riga |
| --- | --- | --- |
| require, sul **figlio** | `dbops.trgfn_child_requires_active_parent` | la tabella del trigger è la figlia, con la sua colonna FK |
| block, sul **padre** | `dbops.trgfn_prevent_deactivate_if_children` | gli argomenti nominano schema, tabella e colonna FK della figlia |

Una riga del registro che nomina una tabella che non esiste non trova trigger e non produce
errori. Un trigger montato fuori grammatica non si riconosce: non è un'eccezione, è un errore di
scrittura, e lo riporta `dbops.fn_trigger_attivo_orfani`.

---

### Chi la chiama

* `dbops.fn_run_automations_attivo`, in testa a ogni giro e solo fuori dal dry run;
* un changeSet di `90_end`, una volta, per i database su cui i trigger c'erano già quando il
  registro è nato.

È un `DROP TRIGGER IF EXISTS` per trigger trovato: rilanciarla è innocuo, e su un database appena
costruito, prima della passata `ci_apply`, restituisce zero. Per ogni trigger tolto emette un
avviso col nome e la tabella.

È `SECURITY INVOKER`: la chiamano il migratore o il job delle automazioni, che sono proprietari
delle tabelle.

---

### Test

* `db/pgtap/dbops/test-automazione-attivo-eccezioni-v1.sql` — sulla FK dichiarata non resta né
  il require né il block, e le altre FK della stessa figlia sono ancora legate.

---

### Note di migrazione

* 2026-09-25 — nasce con il registro delle eccezioni (`brief-db-blocco-login-per-credenziale`
  §12.3).
* 2026-09-26 — gli argomenti si leggono da `dbops.fn_trigger_argomenti` invece che con una
  decodifica locale di `tgargs`.
* 2026-11-07 — gli argomenti si interpretano per nome con `dbops.fn_trigger_attivo_argomenti`,
  non più per posizione.

---

{% include-markdown "signature-core.md" %}
