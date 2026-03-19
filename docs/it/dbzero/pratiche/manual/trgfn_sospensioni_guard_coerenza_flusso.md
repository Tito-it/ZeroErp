## 📘 Documentazione Funzione – `pratiche.trgfn_sospensioni_guard_coerenza_flusso`

> 👀 **Vedi anche**
>
[pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---
### 🎯 Scopo Principale
Guard: verifica che `flusso_id` appartenga alla stessa `pratica_id` della sospensione. Se `flusso_id IS NULL` (sospensione pratica intera), nessun controllo.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_guard_coerenza_flusso()
RETURNS trigger LANGUAGE plpgsql
```

---

### Trigger associato

| Nome                                               | Fase   | Evento                       | Tabella                |
| -------------------------------------------------- | ------ | ---------------------------- | ---------------------- |
| `trg_sospensioni_a10_guard_coerenza_flusso_ins_upd` | BEFORE | INSERT, UPDATE OF flusso_id | `pratiche.sospensioni` |

---

### Messaggi errore

| Codice                          | Messaggio                                       |
| ------------------------------- | ----------------------------------------------- |
| `SOSPENSIONI_FLUSSO_NON_COERENTE` | Il flusso {id} non appartiene alla pratica {id} |

---

{% include-markdown "signature-core.md" %}
