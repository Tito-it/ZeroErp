## 📘 Documentazione Concettuale – Funzione `script.fn_check_prezzi_in_attesa()`

> 👀 **Vedi anche**
>
> • [script.fn_check_prezzi_autorizzati](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) — il building block di cui è un filtro
> • [vendite.fn_crea_revisione_preventivo](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo) e [vendite.fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta) — chi rifiuta la revisione
> • [script.fn_available_actions_preventivo](/dbzero/script/funzioni/fn_available_actions_preventivo) e [script.fn_available_actions_offerta](/dbzero/script/funzioni/fn_available_actions_offerta) — chi spegne «Crea revisione»

---

### 🎯 Scopo Principale

(nata il 2026-09-24 — `20260924-33`)

Dice se un documento ha **prezzi in attesa di approvazione**. È la domanda che decide se se
ne può creare una **revisione**: finché un prezzo è in attesa, la revisione non si crea.

---

### ⛔ Perché: la revisione che restava in attesa per sempre

Una revisione (di preventivo o di offerta) ricopia le righe **con** il loro stato di
approvazione e la loro pratica. Se una riga era in attesa, la copia sulla revisione nuova
restava legata alla pratica della versione **vecchia**: il responsabile rispondeva, l'esito
arrivava sulla riga vecchia, e sulla nuova l'attesa non finiva più. La riga non si poteva
modificare (è in attesa) e il documento non si poteva emettere: restava solo l'annullamento.

Decisione di Tid del 2026-09-24: **prima l'esito, poi la revisione.**

---

### ⭐ Cosa conta e cosa no

* conta solo il prezzo **in attesa** (`E_DOC_PREZZO_PENDENTE`, righe e componenti attivi);
* ⚠️ il prezzo **rifiutato** non blocca la revisione, ed è voluto: si ricopia, e sulla
  revisione l'operatore lo corregge. Azzerarlo farebbe nascere la revisione con lo stesso
  prezzo senza marca, cioè un prezzo rifiutato che passa;
* anche l'**approvato** si ricopia com'era: il prezzo è lo stesso, e l'autorizzazione vale.

Restituisce `[]` o l'array con il solo motivo dell'attesa, nella forma di
`fn_check_prezzi_autorizzati`: stesso codice, stessa `reason_key`
(`common.azione_reason.prezzo_pendente`), nessuna chiave nuova per il frontend.

---

{% include-markdown "signature-core.md" %}
