## 📘 Documentazione Concettuale – Funzione `dbops.fn_rename_triggers_by_order`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_fix_triggers_events_noorder](/dbzero/dbops/funzioni/fn_fix_triggers_events_noorder) — la rinomina successiva, sugli eventi
> * [dbops.fn_cleanup_triggers_suffix_2](/dbzero/dbops/funzioni/fn_cleanup_triggers_suffix_2) — la pulizia dei suffissi `_2` che le rinomine lasciavano
> * [dbops.fn_fix_lock_codice_interno_triggers](/dbzero/dbops/funzioni/fn_fix_lock_codice_interno_triggers) — l'altra utility della stessa campagna
>
> Guide:
>
> * [Linee guida Trigger](/linee-guida-trigger#il-nome-del-trigger) — la regola dei nomi di oggi, diversa da quella che questa funzione applica

---

### 🎯 Scopo Principale

Utility **una tantum** della campagna di rinomina dei trigger del settembre 2025: rinomina i
trigger che cominciano con `trg_<fase>_` (per esempio `trg_a10_…`) spostando la tabella in
testa al nome. Oggi non la chiama nessun runner, job o backend: è una **candidata al ritiro**.

Esiste ancora perché il changeSet che la crea, nel primo albero (`db/changelog/migrations/50_dbops`),
gira su ogni database nuovo, e un secondo changeSet dello stesso file la **esegue** davvero sulle
fasi `a10`, `a11` e `z90`.

---

### Che cosa fa

* Prende una fase (una lettera fra `a` e `z` seguita da due cifre). Una fase scritta in un'altra
  forma, o assente, non fa niente e non dice niente.
* Cerca in tutti gli schemi, o in quello indicato, i trigger utente il cui nome comincia con
  `trg_<fase>_`.
* Compone il nome nuovo nella forma `trg_<tabella>_<fase>_<evento>`, con `_of_<colonna>` se il
  trigger è su `UPDATE OF`, `_aft` se è un `AFTER`, e in coda lo scopo ricavato dal nome vecchio.
* Se il nome nuovo è già preso aggiunge un suffisso numerico (`_2`, `_3`, …), poi tronca a 63
  caratteri.
* In anteprima (il default) restituisce le rinomine che farebbe; altrimenti le esegue e
  restituisce l'esito di ognuna, con l'errore nel campo delle note se una non riesce.

---

### ⛔ Perché non si rilancia

* **Il nome che produce non è quello di oggi.** Mette l'evento subito dopo la fase e un solo
  evento: un trigger su `INSERT OR UPDATE` diventa `ins`, e la cancellazione è `del`. Le linee
  guida di oggi vogliono gli eventi **in coda**, tutti, in `ins_upd_dlt`.
* **Rinomina anche i trigger generati.** Un trigger del framework che cambia nome non lo
  riconosce più il controllo per nome dei runner, che al giro successivo ne monta un secondo.
* **Tronca dopo il suffisso**, quindi su un nome lungo il suffisso può sparire, e due trigger
  possono finire con lo stesso nome: la seconda rinomina fallisce.
* **Rinomina anche i `CONSTRAINT TRIGGER`** con `ALTER TRIGGER`. Le
  [linee guida dei trigger](/linee-guida-trigger#trigger-differiti-constraint-trigger) avvertono
  che una rinomina così aggiorna uno solo dei due cataloghi.

---

### Note di migrazione

* 2025-09-21 — nasce nel primo albero dei changeSet, ed è eseguita sulle fasi `a10`, `a11` e
  `z90`. È la prima di tre utility della campagna di rinomina: la seguono
  `fn_fix_triggers_events_noorder`, sugli eventi, e `fn_cleanup_triggers_suffix_2`, sui
  suffissi che le collisioni avevano lasciato.

---

{% include-markdown "signature-core.md" %}
