## 📘 Documentazione Concettuale – Trigger Function `vendite.trgfn_preventivi_righe_ricalcola_totali()`

> 👀 **Vedi anche**
>
[vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.fn_ricalcola_totali_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_totali_preventivo)
> [vendite.preventivi](/dbzero/vendite/tabelle/preventivi)

---
### 🎯 Scopo Principale
(latest review 03-04-2026)
`vendite.trgfn_preventivi_righe_ricalcola_totali()` e' la trigger function **STATEMENT-level**
che mantiene i totali testata preventivo sempre coerenti con le righe. Invoca
`vendite.fn_ricalcola_totali_preventivo()` **una sola volta per ogni preventivo_id coinvolto**,
anche in caso di operazioni bulk (es. copia righe in revisione).

---

### Trigger associati

Tre trigger separati, uno per evento, con transition tables PG 18:

| Nome | Timing | Evento | Transition tables |
|------|--------|--------|-------------------|
| `trg_preventivi_righe_z90_ricalcola_totali_ins` | AFTER STATEMENT | INSERT | `NEW TABLE AS new_rows` |
| `trg_preventivi_righe_z90_ricalcola_totali_upd` | AFTER STATEMENT | UPDATE | `OLD TABLE AS old_rows`, `NEW TABLE AS new_rows` |
| `trg_preventivi_righe_z90_ricalcola_totali_dlt` | AFTER STATEMENT | DELETE | `OLD TABLE AS old_rows` |

**Fase `_z90_`**: il ricalcolo avviene dopo tutti i trigger di validazione/guard.

---

### Logica

* Usa **`EXECUTE`** per accedere alle transition tables in modo sicuro
  (evita problemi di plan caching tra eventi con transition tables diverse).
* In base a `TG_OP`:
  * **INSERT**: raccoglie `DISTINCT preventivo_id` da `new_rows`
  * **DELETE**: raccoglie `DISTINCT preventivo_id` da `old_rows`
  * **UPDATE**: `UNION` di entrambe (copre il caso di cambio `preventivo_id` su una riga)
* Per ogni `preventivo_id` distinto: `PERFORM vendite.fn_ricalcola_totali_preventivo(pid)`.

---

### Ottimizzazione rispetto a FOR EACH ROW

| Aspetto | FOR EACH ROW (precedente) | FOR EACH STATEMENT (attuale) |
|---------|---------------------------|------------------------------|
| INSERT 20 righe | 20 invocazioni ricalcolo (O(N²)) | 1 invocazione (O(N)) |
| Revisione con copia righe | N ricalcoli ridondanti | 1 ricalcolo finale |
| UPDATE singola riga | 1 invocazione | 1 invocazione |

---

{% include-markdown "signature-core.md" %}
