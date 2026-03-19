## 📘 Documentazione Funzione – `pratiche.trgfn_allegati_pratiche_giornale`

> 👀 **Vedi anche**
>
Tabelle:
>
[pratiche.giornale](giornale.md)
> [pratiche.allegati_pratiche](allegati_pratiche.md)
>
Overview:
>
[Trigger business overview](trigger_business_overview.md)

---
### 🎯 Scopo Principale
Registra l'azione **ALLEGATO_AGGIUNTO** nel giornale a livello pratica. Si attiva **AFTER INSERT** su `pratiche.allegati_pratiche`.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_allegati_pratiche_giornale()
RETURNS trigger
LANGUAGE plpgsql
```

---

### Logica

Inserisce una riga in `pratiche.giornale` con:

| Campo | Valore |
|-------|--------|
| `pratica_id` | `NEW.pratica_id` |
| `flusso_id` | `NULL` (allegato a livello pratica) |
| `azione` | `'ALLEGATO_AGGIUNTO'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('allegato_id', NEW.id, 'tipo_allegato_id', NEW.tipo_allegato_id, 'nome_file', NEW.nome_file)` |

**Nota**: `tx_id` non e' incluso nell'INSERT perche' la tabella `allegati_pratiche` e' immutabile (solo `data_insert/user_insert`) e non ha il campo `tx_id`.

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_allegati_pratiche_z90_giornale_ins` | AFTER | INSERT | `pratiche.allegati_pratiche` |
