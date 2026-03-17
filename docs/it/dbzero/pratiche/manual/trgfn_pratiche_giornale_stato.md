## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_giornale_stato`

> 👀 **Vedi anche**
>
Tabelle:
>
[pratiche.giornale](giornale.md)
> [pratiche.pratiche](pratiche.md)
>
Overview:
>
[Trigger business overview](trigger_business_overview.md)

---

### 🎯 Scopo Principale

Registra l'azione **STATO_CAMBIATO** nel giornale. Si attiva **AFTER UPDATE OF stato_id** su `pratiche.pratiche`, solo quando il valore cambia realmente (`WHEN OLD.stato_id IS DISTINCT FROM NEW.stato_id`).

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_stato()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Logica

Inserisce una riga in `pratiche.giornale` con:

| Campo | Valore |
|-------|--------|
| `pratica_id` | `NEW.id` |
| `flusso_id` | `NULL` |
| `azione` | `'STATO_CAMBIATO'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('stato_precedente_id', OLD.stato_id, 'stato_nuovo_id', NEW.stato_id)` |
| `tx_id` | `NEW.tx_id` |

---

### Trigger associato

| Nome | Fase | Evento | WHEN |
|------|------|--------|------|
| `trg_pratiche_z90_giornale_stato_upd` | AFTER | UPDATE OF stato_id | `OLD.stato_id IS DISTINCT FROM NEW.stato_id` |
