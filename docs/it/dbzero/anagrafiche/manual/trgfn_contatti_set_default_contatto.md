## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_contatti_set_default_contatto`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.contatti](/dbzero/anagrafiche/tabelle/contatti) — la tabella su cui è montata, di cui scrive `is_default` e `default_context`
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto, di cui scrive `default_contatto_id`
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_contatto](/dbzero/anagrafiche/funzioni/fn_crea_contatto) — il verbo che fa nascere i contatti
> * [anagrafiche.trgfn_contatti_guard_predefinito](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_predefinito) — il gemello che giudica il segno tolto e il predefinito cancellato
> * [script.fn_get_contatto_default](/dbzero/script/funzioni/fn_get_contatto_default) — chi legge il predefinito
>
> Guide:
>
> * [Gestione dei Contatti](/guide/gestione-dei-contatti) — il contatto predefinito nel modello dei contatti

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_contatti_set_default_contatto` mette il segno del contatto predefinito di ogni riga di contesto
(soggetto, ruolo, istanza): al primo contatto che entra in un contesto senza predefinito, o al contatto che lo
chiede. Lo toglie al predefinito di prima, scrive il livello in `default_context` e, per il contesto del soggetto,
il puntatore `anagrafiche.soggetti.default_contatto_id`.

Il segno tolto e il predefinito cancellato non li giudica lui: li giudica il gemello
[anagrafiche.trgfn_contatti_guard_predefinito](/dbzero/anagrafiche/funzioni/trgfn_contatti_guard_predefinito).

---

### Quando scatta

Prima di ogni nascita e di ogni modifica di `anagrafiche.contatti`, montato come
`trg_contatti_a20_set_default_contatto_ins_upd`. La fase `a20` lo fa girare dopo i due guard `a10` (il contesto
del soggetto e il predefinito).

---

### Che cosa fa a ogni scrittura

* **Chi chiede il segno** (`is_default` a `true` alla nascita, o passato da `false` a `true`) lo toglie al
  predefinito di prima dello stesso contesto.
* **Chi entra nel contesto** senza chiederlo (nasce, o cambia soggetto, ruolo o istanza) è predefinito se il
  contesto non ne ha uno, e senza segno se ce l'ha. Un segno portato da un altro contesto non è una richiesta.
* **Una modifica che non tocca il segno né il contesto** non sposta niente.
* `default_context` prende il livello del predefinito (`istanza`, `ruolo` o `soggetto`) ed è `NULL` sugli altri.
* Quando un contatto **diventa** il predefinito del contesto del soggetto (né ruolo né istanza), il suo id va in
  `anagrafiche.soggetti.default_contatto_id`, se il puntatore non lo ha già.

Il segno tolto agli altri è scritto prima della riga nuova: l'indice `uq_contatti_predefinito_contesto` non vede
mai due predefiniti nello stesso contesto. Quelle scritture le fa il trigger, e il guard del predefinito le lascia
passare.

---

### Il soggetto si riscrive solo quando cambia il suo predefinito

Il puntatore del soggetto si scrive solo quando un contatto diventa il predefinito del contesto del soggetto, e
solo se non punta già lì. Una modifica dei recapiti del predefinito non tocca il soggetto e non fa scattare i suoi
trigger.

---

{% include-markdown "it/dbzero/anagrafiche/_contatto-predefinito.md" %}

---

### ⚠️ Che cosa oggi non copre

* **Il puntatore del soggetto non si svuota.** Quando l'ultimo contatto del contesto del soggetto si cancella, o
  passa a un ruolo, `anagrafiche.soggetti.default_contatto_id` resta sul contatto di prima.

---

### Test

* `db/pgtap/anagrafiche/test-contatto-predefinito-per-contesto-v1.sql` — il primo contatto di ogni ruolo dello
  stesso soggetto nasce predefinito (test 3); marcare un contatto del fornitore non tocca il cliente e toglie il
  segno al predefinito di prima, con `default_context` `NULL` (4-5); la modifica di un altro contatto del contesto
  non sposta il segno (7); il predefinito che passa a un ruolo che ha già il suo entra senza segno (20).
* `db/pgtap/anagrafiche/test-contatti-soggetto-cliente.sql` — un contatto di ruolo marcato predefinito prende il
  contesto `ruolo` e non tocca il puntatore del soggetto.
* `db/pgtap/anagrafiche/test-fn-crea-contatto-v1.sql` — il primo contatto di un soggetto costruito nasce
  predefinito.

---

{% include-markdown "signature-core.md" %}
