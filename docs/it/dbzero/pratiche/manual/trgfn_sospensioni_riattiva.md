## 📘 Documentazione Funzione – `pratiche.trgfn_sospensioni_riattiva`

> 👀 **Vedi anche**
>
[pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni)
> [pratiche.giornale](/dbzero/pratiche/manual/giornale)

---
### 🎯 Scopo Principale
Ripristina gli stati precedenti alla riattivazione. AFTER UPDATE OF `data_fine` su `pratiche.sospensioni`: quando la sospensione viene chiusa (data_fine passa da NULL a valorizzata), ripristina lo stato precedente dei flussi (dal giornale) e riporta la pratica ad APERTA.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_sospensioni_riattiva()
RETURNS trigger LANGUAGE plpgsql
```

---

### Logica

1. Si attiva solo quando `OLD.data_fine IS NULL AND NEW.data_fine IS NOT NULL`.
2. Solo per sospensioni a livello pratica (`flusso_id IS NULL`).
3. Riporta la pratica allo stato APERTA.
4. Per ogni flusso in stato SOSPESO: cerca nel giornale l'ultimo `FLUSSO_STATO_CAMBIATO` con `stato_nuovo = 'SOSPESO'` e recupera `stato_precedente_id`. Ripristina quel stato.

---

### Trigger associato

| Nome                                               | Fase  | Evento              | Tabella                |
| -------------------------------------------------- | ----- | ------------------- | ---------------------- |
| `trg_sospensioni_z90_propaga_riattivazione_upd`    | AFTER | UPDATE OF data_fine | `pratiche.sospensioni` |

WHEN: `OLD.data_fine IS NULL AND NEW.data_fine IS NOT NULL`.

---

{% include-markdown "signature-core.md" %}
