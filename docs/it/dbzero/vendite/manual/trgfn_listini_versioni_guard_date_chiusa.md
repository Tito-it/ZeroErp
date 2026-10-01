## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_listini_versioni_guard_date_chiusa`

> 👀 **Vedi anche**
>
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — la tabella (trigger `trg_listini_versioni_a10_guard_date_chiusa_upd`)
> • [vendite.fn_listino_versione_in_vigore](/dbzero/vendite/funzioni/fn_listino_versione_in_vigore) — ciò che questo guard rende univoco
> • [vendite.trgfn_listini_versioni_guard_transizione_stato](/dbzero/vendite/funzioni/trgfn_listini_versioni_guard_transizione_stato) — quando una versione si chiude
>
> **Verifica:** `db/pgtap/vendite/test-listino-versione-in-vigore-v1.sql` (test 6-7)

---

### 🎯 Scopo Principale

(funzione nata il 2026-09-28, `20260928-34`)

**Le date di validità di una versione di listino CHIUSA non si modificano più.**
Codice `E_LISTINO_VERSIONE_CHIUSA_DATE_IMMUTABILI` (`CONFLITTO_STATO`).

---

### ⭐ Perché

Una versione chiusa è la **storia dei prezzi di un periodo**. Spostarne le date
riscriverebbe quale versione valeva in quelle date — su documenti già fatti — e
allungarne la fine la farebbe tornare **valida accanto all'ATTIVA**: per quella
data le versioni in vigore diventerebbero due. Decisione di Tid del 2026-09-28:
«non si può modificare una sequenza di date di listino, sarebbe un disastro».

---

### Regole

- Trigger `BEFORE UPDATE OF valido_dal, valido_al`, `WHEN (OLD.stato = 'CHIUSA')`:
  gira solo quando serve.
- Rifiuta solo un **cambio vero** (`IS DISTINCT FROM`): un UPDATE che riscrive
  le stesse date passa.
- La **chiusura stessa** non è toccata: quando una versione passa ATTIVA →
  CHIUSA, `OLD.stato` è ancora ATTIVA. Le date si decidono finché la versione è
  attiva (per chiuderla si fissa `valido_al`).
- Per prezzi diversi in un periodo nuovo si crea una **nuova versione**.

---

{% include-markdown "signature-core.md" %}
