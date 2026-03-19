## 📘 Documentazione Funzione – `pratiche.trgfn_flussi_giornale_ins`

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
Registra l'azione **FLUSSO_CREATO** nel giornale. Si attiva **AFTER INSERT** su `pratiche.flussi`.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_giornale_ins()
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
| `azione` | `'FLUSSO_CREATO'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('template_flusso_id', 'stato_id', 'sequenza')` |
| `tx_id` | `NEW.tx_id` |

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_flussi_z90_giornale_ins` | AFTER | INSERT | `pratiche.flussi` |
