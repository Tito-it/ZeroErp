## 📘 Documentazione Funzione – `pratiche.trgfn_sospensioni_propaga`

> 👀 **Vedi anche**
>
[pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [config.transizioni_stati_flussi_pratiche](/dbzero/config/manual/transizioni_stati_flussi_pratiche)

---

### 🎯 Scopo Principale

Propaga la sospensione a livello pratica ai flussi attivi. AFTER INSERT su `pratiche.sospensioni`: se `flusso_id IS NULL`, tutti i flussi con stato DA_ESEGUIRE o IN_CORSO passano a SOSPESO.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_propaga()
RETURNS trigger LANGUAGE plpgsql
```

---

### Logica

1. Se `NEW.flusso_id IS NOT NULL` → nessuna propagazione (sospensione singolo flusso).
2. Recupera gli ID degli stati DA_ESEGUIRE, IN_CORSO, SOSPESO da `config.stati_flussi_pratiche`.
3. UPDATE tutti i flussi della pratica con stato in (DA_ESEGUIRE, IN_CORSO) → SOSPESO.

---

### Trigger associato

| Nome                                          | Fase  | Evento | Tabella                |
| --------------------------------------------- | ----- | ------ | ---------------------- |
| `trg_sospensioni_z90_propaga_sospensione_ins` | AFTER | INSERT | `pratiche.sospensioni` |

---

{% include-markdown "signature-core.md" %}
