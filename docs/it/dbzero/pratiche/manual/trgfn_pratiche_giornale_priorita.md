## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_giornale_priorita`

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

Registra l'azione **PRIORITA_CAMBIATA** nel giornale. Si attiva **AFTER UPDATE OF priorita_id** su `pratiche.pratiche`, solo quando il valore cambia realmente.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_priorita()
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
| `azione` | `'PRIORITA_CAMBIATA'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('priorita_precedente_id', OLD.priorita_id, 'priorita_nuova_id', NEW.priorita_id)` |
| `tx_id` | `NEW.tx_id` |

---

### Trigger associato

| Nome | Fase | Evento | WHEN |
|------|------|--------|------|
| `trg_pratiche_z90_giornale_priorita_upd` | AFTER | UPDATE OF priorita_id | `OLD.priorita_id IS DISTINCT FROM NEW.priorita_id` |
