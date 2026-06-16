## 📘 Documentazione Trigger Function – `pratiche.trgfn_pratiche_sorgenti_guard_coerenza_flusso`

> 👀 **Vedi anche**
>
Funzioni / oggetti collegati:
>
> [pratiche.pratiche_sorgenti](pratiche_sorgenti.md)
> [pratiche.flussi](flussi.md)
> [pratiche.trgfn_sospensioni_guard_coerenza_flusso](trgfn_sospensioni_guard_coerenza_flusso.md)

---
### 🎯 Scopo Principale

In `pratiche.pratiche_sorgenti` la colonna `flusso_id` **àncora il link ROOT al flusso
d'origine** del documento (preventivo aperto da un'attività UI di flusso), non a tutta
la pratica — vedi *brief-db-aggancio-documento-flusso*. Il flusso indicato deve
appartenere alla **stessa pratica** del link.

La FK `fk_pratiche_sorgenti_flusso` garantisce solo che `flusso_id` punti a un flusso
**esistente**, non che sia un flusso *di quella* pratica. Un `CHECK` non può fare
subquery cross-tabella: serve un guard fail-fast che impedisca l'incoerenza
`pratiche_sorgenti.pratica_id ≠ flussi.pratica_id` (denormalizzazione divergente
introdotta da una scrittura buggy).

---

### Trigger associato

| Trigger | Timing | Evento | Tabella |
|---|---|---|---|
| `trg_pratiche_sorgenti_a10_guard_coerenza_flusso_ins_upd` | BEFORE | INSERT · UPDATE OF `flusso_id`, `pratica_id` | `pratiche.pratiche_sorgenti` |

Fase `_a10_` (guard).

---

### Regole

1. Scatta **solo se `flusso_id IS NOT NULL`**: i link `COLLEGATO` a valle
   (commessa/ordine dai push handler) nascono con `flusso_id` NULL e **non** sono
   toccati.
2. Se il flusso indicato **non esiste**, `RETURN NEW`: si lascia sollevare la FK
   `fk_pratiche_sorgenti_flusso` (errore corretto, non mascherato dal guard).
3. Se `flussi.pratica_id` del flusso indicato **differisce** da `pratiche_sorgenti.pratica_id`
   del link → errore parlante.

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `PRATICHE_SORGENTI_FLUSSO_PRATICA_INCOERENTE` (493) | Link con `flusso_id` valorizzato che punta a un flusso di un'**altra** pratica |

---

### Note operative

* Lavora in coppia con l'indice unico parziale `uq_pratiche_sorgenti_flusso_root`
  (`WHERE ruolo_link='ROOT' AND flusso_id IS NOT NULL`), che impone **max 1 ROOT per
  flusso**: l'indice garantisce l'unicità, questo guard la **coerenza** del flusso
  con la pratica.
* Per i link `COLLEGATO` a valle lasciare `flusso_id` NULL: non vincolati né
  dall'indice né da questo guard.
* Test: `db/pgtap/pratiche/test-pratiche-sorgenti-flusso.sql`.

---
{% include-markdown "signature-core.md" %}
