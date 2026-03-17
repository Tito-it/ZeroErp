## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_giornale_assegnazione`

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

Registra l'azione **ASSEGNAZIONE_CAMBIATA** nel giornale. Si attiva **AFTER UPDATE OF risorsa_umana_id, unita_organizzativa_id** su `pratiche.pratiche`, solo quando almeno uno dei due valori cambia realmente.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_assegnazione()
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
| `azione` | `'ASSEGNAZIONE_CAMBIATA'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('risorsa_umana_precedente_id', 'risorsa_umana_nuova_id', 'unita_organizzativa_precedente_id', 'unita_organizzativa_nuova_id')` |
| `tx_id` | `NEW.tx_id` |

---

### Trigger associato

| Nome | Fase | Evento | WHEN |
|------|------|--------|------|
| `trg_pratiche_z90_giornale_assegnazione_upd` | AFTER | UPDATE OF risorsa_umana_id, unita_organizzativa_id | `OLD.risorsa_umana_id IS DISTINCT FROM NEW.risorsa_umana_id OR OLD.unita_organizzativa_id IS DISTINCT FROM NEW.unita_organizzativa_id` |
