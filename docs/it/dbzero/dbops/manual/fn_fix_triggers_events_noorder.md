## 📘 Documentazione Concettuale – Funzione `dbops.fn_fix_triggers_events_noorder`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_rename_triggers_by_order](/dbzero/dbops/funzioni/fn_rename_triggers_by_order) — la rinomina precedente, per fase
> * [dbops.fn_fix_triggers_event_tokens](/dbzero/dbops/funzioni/fn_fix_triggers_event_tokens) — una variante con lo stesso scopo, rimasta solo su dbdev
> * [dbops.fn_cleanup_triggers_suffix_2](/dbzero/dbops/funzioni/fn_cleanup_triggers_suffix_2) — la pulizia dei suffissi `_2` che le rinomine lasciavano
>
> Guide:
>
> * [Linee guida Trigger](/linee-guida-trigger#il-nome-del-trigger) — la regola dei nomi di oggi, diversa da quella che questa funzione applica

---

### 🎯 Scopo Principale

Utility **una tantum** della campagna di rinomina dei trigger del settembre 2025: riscrive il
nome di ogni trigger in una forma che dice **tutti** gli eventi su cui scatta, ricavando lo
scopo dalla funzione che il trigger esegue. Oggi non la chiama nessun runner, job o backend: è
una **candidata al ritiro**.

Esiste ancora perché il changeSet che la crea, nel primo albero (`db/changelog/migrations/50_dbops`),
gira su ogni database nuovo, e un secondo changeSet dello stesso file la **esegue** davvero, su
tutti gli schemi.

---

### Che cosa fa

* Prende tutti i trigger utente il cui nome comincia con `trg_`, `ins_`, `upd_`, `del_` o `dlt_`,
  in tutti gli schemi tranne `public` e `topology`, o nel solo schema indicato.
* Legge gli eventi dalla definizione e li scrive tutti, in quest'ordine: `ins`, `upd`, `dlt`.
  Un trigger da cui non riesce a leggerli diventa `upd`.
* Conserva la fase (`a…` o `z…` con due cifre) se il nome vecchio ne aveva una, e aggiunge
  `_aft` per un trigger `AFTER`.
* Ricava lo scopo dal **nome della funzione** del trigger, togliendo i prefissi `trgfn`/`trg`/`fn`,
  il nome della tabella, la fase, gli eventi e alcune parole di servizio.
* Compone `trg_<tabella>[_<fase>]_<eventi>[_aft]_<scopo>`, aggiunge un suffisso numerico se il
  nome è preso da un altro trigger, e tronca a 63 caratteri tenendo il suffisso.
* In anteprima (il default) restituisce le rinomine che farebbe; altrimenti le esegue e
  restituisce l'esito di ognuna, con l'errore nel campo delle note se una non riesce.

---

### ⛔ Perché non si rilancia

* **Il nome che produce non è quello di oggi.** Mette gli eventi **prima** dello scopo; le linee
  guida di oggi li vogliono in coda.
* **Rinomina ogni trigger, compresi quelli generati.** Un trigger del framework che cambia nome
  non lo riconosce più il controllo per nome dei runner, che al giro successivo ne monta un
  secondo; e i nomi scritti nei documenti e nei test smettono di valere.
* **Rinomina anche i `CONSTRAINT TRIGGER`** con `ALTER TRIGGER`. Le
  [linee guida dei trigger](/linee-guida-trigger#trigger-differiti-constraint-trigger) avvertono
  che una rinomina così aggiorna uno solo dei due cataloghi.

---

### Note di migrazione

* 2025-09-22 — nasce nel primo albero dei changeSet, ed è eseguita su tutti gli schemi. Il file
  porta il nome `fn_fix_triggers_event_tokens`, ma crea questa funzione; i suoi changeSet hanno
  gli stessi id di quelli di `fn_rename_triggers_by_order`, in un altro file.

---

{% include-markdown "signature-core.md" %}
