## 📘 Documentazione Funzione – `pratiche.trgfn_note_pratiche_giornale`

> 👀 **Vedi anche**
>
> Tabelle:
>
> * [pratiche.giornale](giornale.md)
> * [pratiche.note_pratiche](note_pratiche.md)
>
> Overview:
>
> * [Trigger business overview](trigger_business_overview.md)

---

### 🎯 Scopo Principale

Registra l'azione **NOTA_AGGIUNTA** nel giornale a livello pratica. Si attiva **AFTER INSERT** su `pratiche.note_pratiche`.

---

### 🔧 Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_note_pratiche_giornale()
RETURNS trigger
LANGUAGE plpgsql
```

---

### ⚙️ Logica

Inserisce una riga in `pratiche.giornale` con:

| Campo | Valore |
|-------|--------|
| `pratica_id` | `NEW.pratica_id` |
| `flusso_id` | `NULL` (nota a livello pratica) |
| `azione` | `'NOTA_AGGIUNTA'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('nota_id', NEW.id, 'tipo_nota_id', NEW.tipo_nota_id)` |
| `tx_id` | `NEW.tx_id` |

---

### 🔗 Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_note_pratiche_z90_giornale_ins` | AFTER | INSERT | `pratiche.note_pratiche` |
