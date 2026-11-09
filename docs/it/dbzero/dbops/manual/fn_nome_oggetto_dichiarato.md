## 📘 Documentazione Concettuale – Funzione `dbops.fn_nome_oggetto_dichiarato`

> **Ultimo aggiornamento**: 9 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.automation_delete_block](/dbzero/dbops/tabelle/automation_delete_block) — il registro dei blocchi di cancellazione, con il suo `trigger_name`
> * [dbops.automazione_guard_utility_tipo_ruolo](/dbzero/dbops/tabelle/automazione_guard_utility_tipo_ruolo) — il registro dei guard utility/tipo ruolo, con il suo `trigger_name`
> * [dbops.automazione_overlap](/dbzero/dbops/tabelle/automazione_overlap) — il registro dei vincoli di non sovrapposizione, con il suo `constraint_name`
>
> Approfondimento funzioni:
>
> * [dbops.fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template) — risolve il template e accorcia con un hash oltre i 63 caratteri
> * [dbops.fn_delete_block_divergenze](/dbzero/dbops/funzioni/fn_delete_block_divergenze) — calcola con lei il nome atteso del blocco di cancellazione
> * [dbops.fn_apply_delete_block_trigger](/dbzero/dbops/funzioni/fn_apply_delete_block_trigger) — crea il trigger col nome che lei restituisce
> * [dbops.fn_guard_utility_divergenze](/dbzero/dbops/funzioni/fn_guard_utility_divergenze) — calcola con lei il nome atteso del guard utility/tipo ruolo
> * [dbops.fn_apply_automazione_overlap](/dbzero/dbops/funzioni/fn_apply_automazione_overlap) — dà con lei il nome al vincolo `EXCLUDE`
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — le automazioni che danno il nome agli oggetti generati
> * [Linee guida Trigger](/linee-guida-trigger#il-nome-del-trigger) — le regole sui nomi dei trigger

---

### 🎯 Scopo Principale

Dà il nome a un oggetto (un trigger, un vincolo) che un registro delle automazioni dichiara **riga
per riga**: il blocco delle cancellazioni, il guard utility/tipo ruolo, il vincolo di non
sovrapposizione. Ognuno di quei registri ha una colonna del nome facoltativa e un template di
ripiego.

È la **sede unica** del nome: chi confronta l'atteso col vivo e chi crea l'oggetto chiedono qui, e
ottengono lo stesso nome. Prima il nome del blocco delle cancellazioni lo componevano due funzioni
per conto loro, senza accorciarlo: oltre i 63 caratteri PostgreSQL lo troncava alla creazione, il
controllo per nome non lo ritrovava, e il giro dopo provava a crearlo di nuovo.

---

### Come esce il nome

La funzione riceve il nome della riga, il template del registro, lo schema e la tabella.

* **Il nome della riga c'è e sta nei 63 caratteri**: esce così com'è, tolti gli spazi ai bordi.
* **Altrimenti**: il template, oppure il nome della riga troppo lungo, passa da
  [fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template), che sostituisce i
  segnaposto e, se serve, accorcia aggiungendo un hash. Il nome che si scrive e quello che si cerca
  sono così lo stesso.

Un nome vuoto o fatto di soli spazi vale come assente.

---

### ⭐ È idempotente sul suo risultato

Un nome già risolto, ripassato alla funzione, esce **uguale**. Serve perché il runner calcola il
nome atteso e lo passa a chi crea l'oggetto, che lo ricalcola.

Lo è anche [fn_name_from_template](/dbzero/dbops/funzioni/fn_name_from_template), che non lascia
più un doppio trattino basso nel nome accorciato. Un nome che sta già nei 63 caratteri, comunque,
non passa dal template: esce come la riga lo scrive.

---

### Il nome serve a creare, non a riconoscere

Chi confronta un trigger vivo con l'atteso lo riconosce dalla **funzione** che esegue e dai suoi
**argomenti**, non dal nome: un trigger con il nome sbagliato è un trigger da rigenerare, non un
trigger che manca. Il nome atteso entra nel confronto solo come una delle cose che devono
coincidere.

---

### Chi la usa

| Registro | Template | Chi |
| --- | --- | --- |
| `dbops.automation_delete_block` | `trg_{table}_a10_delete_block_dlt` | `fn_delete_block_divergenze`, `fn_apply_delete_block_trigger` |
| `dbops.automazione_guard_utility_tipo_ruolo` | `trg_{table}_a10_guard_utility_tipo_ruolo_ins_upd` | `fn_guard_utility_divergenze` |
| `dbops.automazione_overlap` | `ex_{table}_no_overlap` | `fn_apply_automazione_overlap` |

---

### Test

* `db/pgtap/dbops/test-delete-block-convergenza-v1.sql` — su una tabella dal nome di 50 caratteri
  due giri di seguito lasciano un solo trigger e nessuna divergenza.

---

### Note di migrazione

* 2026-11-08 — nasce, come sede unica del nome dei tre registri (`20261109-95`,
  `brief-db-revisione-dbops`, giro 10c). Prima il blocco delle cancellazioni componeva il nome
  senza accorciarlo, e il vincolo di non sovrapposizione aveva una variante col suffisso `_c`,
  ritirata.
* 2026-11-09 — l'idempotenza non dipende più solo da questa funzione: anche
  `fn_name_from_template` lo è (`20261110-34`, brief-db-revisione-dbops, giro 10c).

---

{% include-markdown "signature-core.md" %}
