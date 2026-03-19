## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_guard_transizione`

> 👀 **Vedi anche**
>
Tabelle:
>
[config.transizioni_stati_pratiche](/dbzero/config/manual/transizioni_stati_pratiche)
> [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche)
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)

---
### 🎯 Scopo Principale
Trigger function guard che **blocca transizioni di stato non ammesse** per le pratiche. Consulta la matrice `config.transizioni_stati_pratiche` (solo righe con `attivo = true`) e solleva eccezione se la transizione non e' configurata.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_transizione()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Logica

1. Se `OLD.stato_id = NEW.stato_id` → nessuna transizione, RETURN NEW senza controllo.
2. Cerca la coppia `(OLD.stato_id, NEW.stato_id)` in `config.transizioni_stati_pratiche` con `attivo = true`.
3. Se non esiste:
   - Risolve i `codice_interno` degli stati da e a per un messaggio leggibile.
   - Solleva eccezione tramite `script.fn_log_and_raise_error('PRATICHE_TRANSIZIONE_NON_AMMESSA', ...)`.
4. Se esiste → RETURN NEW.

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_pratiche_a10_guard_transizione_upd` | BEFORE | UPDATE OF stato_id | `pratiche.pratiche` |

Fase `_a10_`: guard/block — esegue prima dei trigger giornale (`_z90_`).

Condizione WHEN: `OLD.stato_id IS DISTINCT FROM NEW.stato_id`.

---

### Messaggi errore

| Codice | Messaggio |
|--------|-----------|
| `PRATICHE_TRANSIZIONE_NON_AMMESSA` | Transizione pratica non ammessa: {da} -> {a} |

---

{% include-markdown "signature-core.md" %}
