## 📘 Documentazione Funzione – `pratiche.trgfn_note_flussi_giornale`

> 👀 **Vedi anche**
>
Tabelle:
>
[pratiche.giornale](giornale.md)
> [pratiche.note_flussi](note_flussi.md)
> [pratiche.flussi](flussi.md)
>
Overview:
>
[Trigger business overview](trigger_business_overview.md)

---
### 🎯 Scopo Principale
Registra l'azione **NOTA_AGGIUNTA** nel giornale a livello flusso. Si attiva **AFTER INSERT** su `pratiche.note_flussi`.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_note_flussi_giornale()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Logica

1. Recupera `pratica_id` dal flusso tramite `SELECT f.pratica_id FROM pratiche.flussi f WHERE f.id = NEW.flusso_id`.
2. Inserisce una riga in `pratiche.giornale` con:

| Campo | Valore |
|-------|--------|
| `pratica_id` | `v_pratica_id` (recuperato dal flusso) |
| `flusso_id` | `NEW.flusso_id` |
| `azione` | `'NOTA_AGGIUNTA'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('nota_id', NEW.id, 'tipo_nota_id', NEW.tipo_nota_id)` |
| `tx_id` | `NEW.tx_id` |

### DECLARE

| Variabile | Tipo | Descrizione |
|-----------|------|-------------|
| `v_pratica_id` | `pratiche.pratiche.id%TYPE` | Pratica recuperata dal flusso |

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_note_flussi_z90_giornale_ins` | AFTER | INSERT | `pratiche.note_flussi` |
