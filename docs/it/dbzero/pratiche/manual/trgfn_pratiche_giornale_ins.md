## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_giornale_ins`

> 👀 **Vedi anche**
>
> Tabelle:
>
> * [pratiche.giornale](giornale.md)
> * [pratiche.pratiche](pratiche.md)
>
> Overview:
>
> * [Trigger business overview](trigger_business_overview.md)

---

### 🎯 Scopo Principale

Registra l'azione **PRATICA_CREATA** nel giornale. Si attiva **AFTER INSERT** su `pratiche.pratiche`.

---

### 🔧 Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_giornale_ins()
RETURNS trigger
LANGUAGE plpgsql
```

---

### ⚙️ Logica

Inserisce una riga in `pratiche.giornale` con:

| Campo | Valore |
|-------|--------|
| `pratica_id` | `NEW.id` |
| `flusso_id` | `NULL` |
| `azione` | `'PRATICA_CREATA'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `jsonb_build_object('tipo_prestazione_id', 'stato_id', 'priorita_id', 'soggetto_id', 'canale_origine_id')` |
| `tx_id` | `NEW.tx_id` |

---

### 🔗 Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_pratiche_z90_giornale_ins` | AFTER | INSERT | `pratiche.pratiche` |
