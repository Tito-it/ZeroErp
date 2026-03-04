## 📘 Documentazione Funzione – `pratiche.trgfn_allegati_flussi_giornale`

> 👀 **Vedi anche**
>
> Tabelle:
>
> * [pratiche.giornale](giornale.md)
> * [pratiche.allegati_flussi](allegati_flussi.md)
> * [pratiche.flussi](flussi.md)
>
> Overview:
>
> * [Trigger business overview](trigger_business_overview.md)

---

### 🎯 Scopo Principale

Registra l'azione **ALLEGATO_AGGIUNTO** nel giornale a livello flusso. Si attiva **AFTER INSERT** su `pratiche.allegati_flussi`.

---

### 🔧 Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_allegati_flussi_giornale()
RETURNS trigger
LANGUAGE plpgsql
```

---

### ⚙️ Logica

1. Recupera `pratica_id` dal flusso tramite `SELECT f.pratica_id FROM pratiche.flussi f WHERE f.id = NEW.flusso_id`.
2. Inserisce una riga in `pratiche.giornale` con:

| Campo | Valore |
|-------|--------|
| `pratica_id` | `v_pratica_id` (recuperato dal flusso) |
| `flusso_id` | `NEW.flusso_id` |
| `azione` | `'ALLEGATO_AGGIUNTO'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('allegato_id', NEW.id, 'tipo_allegato_id', NEW.tipo_allegato_id, 'nome_file', NEW.nome_file)` |

**Nota**: `tx_id` non e' incluso perche' la tabella `allegati_flussi` e' immutabile e non ha il campo `tx_id`.

### 📋 DECLARE

| Variabile | Tipo | Descrizione |
|-----------|------|-------------|
| `v_pratica_id` | `pratiche.pratiche.id%TYPE` | Pratica recuperata dal flusso |

---

### 🔗 Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_allegati_flussi_z90_giornale_ins` | AFTER | INSERT | `pratiche.allegati_flussi` |
