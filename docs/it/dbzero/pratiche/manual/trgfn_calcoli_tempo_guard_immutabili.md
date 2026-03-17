## 📘 Documentazione Funzione – `pratiche.trgfn_calcoli_tempo_guard_immutabili`

> 👀 **Vedi anche**
>
[pratiche.calcoli_tempo](/dbzero/pratiche/manual/calcoli_tempo)

---

### 🎯 Scopo Principale

Guard: blocca UPDATE sui campi di riferimento immutabili della tabella `pratiche.calcoli_tempo`.

Campi protetti: `pratica_id`, `flusso_da_id`, `flusso_a_id`, `formula_tempo_id`, `giorni_formula`, `data_inizio_calcolo`.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_calcoli_tempo_guard_immutabili()
RETURNS trigger LANGUAGE plpgsql
```

---

### Trigger associato

| Nome                                            | Fase   | Evento                                                                                    | Tabella                 |
| ----------------------------------------------- | ------ | ----------------------------------------------------------------------------------------- | ----------------------- |
| `trg_calcoli_tempo_a10_guard_immutabili_upd`    | BEFORE | UPDATE OF pratica_id, flusso_da_id, flusso_a_id, formula_tempo_id, giorni_formula, data_inizio_calcolo | `pratiche.calcoli_tempo` |

---

### Messaggi errore

| Codice                      | Messaggio                  |
| --------------------------- | -------------------------- |
| `E_COLONNA_NON_MODIFICABILE` | Colonna non modificabile: {nome} |

---

{% include-markdown "signature-core.md" %}
