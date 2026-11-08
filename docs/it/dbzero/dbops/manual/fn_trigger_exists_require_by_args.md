## 📘 Documentazione Concettuale – Funzione `dbops.fn_trigger_exists_require_by_args`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — l'unico chiamante: riconosce così i trigger ATTIVO
> * [dbops.trgfn_child_requires_active_parent](/dbzero/dbops/funzioni/trgfn_child_requires_active_parent) — la funzione del trigger che cerca
> * [dbops.fn_trigger_exists_block_by_args](/dbzero/dbops/funzioni/fn_trigger_exists_block_by_args) — la gemella per il block sul padre
> * [dbops.fn_trigger_exists_by_name](/dbzero/dbops/funzioni/fn_trigger_exists_by_name) — il controllo per nome, che il runner usa solo per sapere se il trigger riconosciuto ha già il nome atteso
> * [dbops.fn_trigger_attivo_argomenti](/dbzero/dbops/funzioni/fn_trigger_attivo_argomenti) — la grammatica degli argomenti, la stessa che legge il trigger
> * [dbops.fn_trigger_argomenti](/dbzero/dbops/funzioni/fn_trigger_argomenti) — gli argomenti salvati di un trigger
>
> Guide:
>
> * [Framework di automazione DB](/guide/automazione-db) — §4.2, la regola ATTIVO

---

### 🎯 Scopo Principale

Dice se sulla tabella figlia c'è già un trigger *require* della regola ATTIVO
(`dbops.trgfn_child_requires_active_parent`) con **esattamente** gli argomenti attesi: schema e
tabella del padre, colonna attivo del padre, colonna FK, colonna referenziata.

È il modo in cui `dbops.fn_run_automations_attivo` riconosce un trigger ATTIVO: dagli argomenti,
cioè dalla FK che il trigger difende, qualunque nome abbia. Il nome serve al runner solo per creare
il trigger, o per rigenerarlo quando quello riconosciuto qui ha un nome diverso da quello atteso.

---

### Come riconosce un trigger

* **La funzione, per identità.** Un trigger è un require se esegue proprio
  `dbops.trgfn_child_requires_active_parent`, riconosciuta dal suo identificativo interno e non dal
  nome scritto: la risposta è la stessa con qualunque `search_path` di chi chiama. Il require del
  ritiro (`dbops.trgfn_child_requires_non_obsolete_parent`) con gli stessi argomenti non è un
  require ATTIVO.
* **Gli argomenti, per nome.** Gli argomenti salvati del trigger si leggono con la grammatica dei
  trigger ATTIVO, la stessa che il trigger usa quando scatta. Un montaggio che la grammatica rifiuta
  non è riconosciuto.
* **Confronto esatto.** Una maiuscola diversa è un altro nome, e il trattino basso è un carattere
  come gli altri.

---

### Che cosa non fa

Non guarda il nome né gli eventi del trigger, né se è acceso o differito. Non dice quanti trigger
corrispondono, solo se ce n'è almeno uno. È `STABLE` e non tocca niente.

---

### Test

`dbops/test-trigger-attivo-riconoscimento-per-funzione-v1`: un require montato come lo monta il
generatore è riconosciuto, anche col `search_path` dell'applicazione; una maiuscola diversa o la
funzione del ritiro no.

---

{% include-markdown "signature-core.md" %}
