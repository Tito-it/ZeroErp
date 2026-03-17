## 📘 Documentazione Funzione – `pratiche.trgfn_flussi_guard_transizione`

> 👀 **Vedi anche**
>
Tabelle:
>
[config.transizioni_stati_flussi_pratiche](/dbzero/config/manual/transizioni_stati_flussi_pratiche)
> [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---

### 🎯 Scopo Principale

Trigger function guard che **blocca transizioni di stato non ammesse** per i flussi pratica. Consulta la matrice `config.transizioni_stati_flussi_pratiche` (solo righe con `attivo = true`) e solleva eccezione se la transizione non e' configurata.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_guard_transizione()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Logica

1. Se `OLD.stato_id = NEW.stato_id` → nessuna transizione, RETURN NEW senza controllo.
2. Cerca la coppia `(OLD.stato_id, NEW.stato_id)` in `config.transizioni_stati_flussi_pratiche` con `attivo = true`.
3. Se non esiste:
   - Risolve i `codice_interno` degli stati da e a per un messaggio leggibile.
   - Solleva eccezione tramite `script.fn_log_and_raise_error('FLUSSI_TRANSIZIONE_NON_AMMESSA', ...)`.
4. Se esiste → RETURN NEW.

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_flussi_a10_guard_transizione_upd` | BEFORE | UPDATE OF stato_id | `pratiche.flussi` |

Fase `_a10_`: guard/block — esegue prima dei trigger giornale (`_z90_`).

Condizione WHEN: `OLD.stato_id IS DISTINCT FROM NEW.stato_id`.

---

### Messaggi errore

| Codice | Messaggio |
|--------|-----------|
| `FLUSSI_TRANSIZIONE_NON_AMMESSA` | Transizione flusso non ammessa: {da} -> {a} |

---

{% include-markdown "signature-core.md" %}
