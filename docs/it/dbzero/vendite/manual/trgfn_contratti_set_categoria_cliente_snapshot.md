## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_contratti_set_categoria_cliente_snapshot()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.contratti](/dbzero/vendite/tabelle/contratti)
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
> • [config.stati_doc_contratti](/dbzero/config/tabelle/stati_doc_contratti)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Fa **due lavori opposti sulla stessa colonna**, `categoria_cliente_id_snapshot`:

* in `INSERT` la **riempie**, copiandola dal billing account, se il chiamante non l'ha
  passata;
* in `UPDATE` la **congela**, vietandone il cambio quando il contratto non è più in `DRAFT`.

È lo schema classico dello snapshot: il valore si prende dall'anagrafica una volta sola, poi
diventa un fatto del contratto. Se il cliente viene riclassificato l'anno dopo, il contratto
già attivo continua a valere sulle condizioni con cui è stato firmato — che è esattamente
ciò che uno snapshot serve a garantire.

La finestra `DRAFT` esiste perché durante la preparazione la riclassificazione è legittima:
il contratto non è ancora un impegno.

---

### Aggancio

Trigger `trg_contratti_a10_set_categoria_cliente_snapshot_ins_upd` — fase `_a10_`,
`BEFORE INSERT OR UPDATE OF categoria_cliente_id_snapshot` su `vendite.contratti`.

---

### Regole applicate

**In `INSERT`** — se `categoria_cliente_id_snapshot IS NULL`, viene letta
`categoria_cliente_id` dal billing account del contratto e copiata. Un valore passato
esplicitamente non viene toccato.

**In `UPDATE`** — se il valore cambia (`IS DISTINCT FROM`), risolve il `codice_interno` dello
stato del contratto e blocca se **non** è `DRAFT`.

---

### ⚠️ Il congelamento vale sulla colonna, non sul contratto

L'aggancio è `UPDATE OF categoria_cliente_id_snapshot`: il guard vede solo gli `UPDATE` che
toccano quella colonna. Non è un limite — è precisamente ciò che serve — ma va letto per
quello che è: **non impedisce nient'altro** su un contratto attivo, e in particolare non
impedisce che la categoria cambi sul *billing account*.

Quest'ultimo è il comportamento voluto: il BA evolve, lo snapshot no. La conseguenza da
tenere a mente è che, dopo una riclassificazione, **BA e contratto dicono cose diverse** — e
la versione corretta per il contratto è quella del contratto.

---

### ⚠️ Se il billing account non ha categoria, lo snapshot nasce vuoto

In `INSERT` il valore viene copiato così com'è: se il BA ha `categoria_cliente_id` nulla, la
`SELECT INTO` lascia `NULL` e lo snapshot resta `NULL` — senza errori.

Da quel momento il contratto è **congelato su un vuoto**: appena esce da `DRAFT`, il guard
impedisce di correggerlo, perché anche passare da `NULL` a un valore è un cambio. La finestra
per rimediare è solo in `DRAFT`.

---

### Codici errore

| Codice | Quando |
|--------|--------|
| `E_CONTRATTO_CATEGORIA_SNAPSHOT_IMMUTABILE` | Cambio di `categoria_cliente_id_snapshot` su contratto in stato diverso da `DRAFT` |

Sollevato via `script.fn_log_and_raise_error`, area `vendite`; il context riporta
`contratto_id`, `old_categoria` e `new_categoria`.

---

{% include-markdown "signature-core.md" %}
