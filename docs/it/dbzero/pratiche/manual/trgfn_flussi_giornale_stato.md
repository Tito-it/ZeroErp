## 📘 Documentazione Funzione – `pratiche.trgfn_flussi_giornale_stato`

> 👀 **Vedi anche**
>
Tabelle:
>
[pratiche.giornale](giornale.md)
> [pratiche.flussi](flussi.md)
>
Overview:
>
[Trigger business overview](trigger_business_overview.md)

---
### 🎯 Scopo Principale
Registra l'azione **FLUSSO_STATO_CAMBIATO** nel giornale. Si attiva **AFTER UPDATE OF stato_id** su `pratiche.flussi`, solo quando il valore cambia realmente.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_giornale_stato()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Logica

Inserisce una riga in `pratiche.giornale` con:

| Campo | Valore |
|-------|--------|
| `pratica_id` | `NEW.pratica_id` |
| `flusso_id` | `NEW.id` |
| `azione` | `'FLUSSO_STATO_CAMBIATO'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('stato_precedente_id', OLD.stato_id, 'stato_nuovo_id', NEW.stato_id, 'esito', NEW.esito)` |
| `tx_id` | `NEW.tx_id` |

Il campo `esito` viene sempre incluso nel dettaglio per tracciare l'esito del flusso al momento del cambio stato (utile per la generazione cross-pratica).

---

### Trigger associato

| Nome | Fase | Evento | WHEN |
|------|------|--------|------|
| `trg_flussi_z90_giornale_stato_upd` | AFTER | UPDATE OF stato_id | `OLD.stato_id IS DISTINCT FROM NEW.stato_id` |
