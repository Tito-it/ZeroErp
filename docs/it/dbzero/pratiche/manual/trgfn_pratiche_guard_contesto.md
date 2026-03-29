## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_guard_contesto`

> 👀 **Vedi anche**
>
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
> [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)

---
### 🎯 Scopo Principale

Guard: valida la coerenza gerarchica del contesto anagrafico sulla pratica.
La catena soggetto → ruolo → istanza deve essere coerente:

- Non si puo' avere un'istanza senza ruolo
- Non si puo' avere un ruolo senza soggetto
- Il ruolo deve appartenere al soggetto indicato
- L'istanza deve appartenere al soggetto indicato

Tutti i campi sono opzionali: una pratica interna ha tutti NULL.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_guard_contesto()
RETURNS trigger LANGUAGE plpgsql
```

---

### Regole di validazione

| # | Regola | Condizione errore |
|---|--------|-------------------|
| 1 | Istanza richiede ruolo | `istanza_utility_id NOT NULL AND soggetto_ruolo_id IS NULL` |
| 2 | Ruolo richiede soggetto | `soggetto_ruolo_id NOT NULL AND soggetto_id IS NULL` |
| 3 | Ruolo deve appartenere al soggetto | `soggetti_ruoli.soggetto_id <> pratiche.soggetto_id` |
| 4 | Istanza deve appartenere al soggetto | `istanze_utilities.soggetto_id <> pratiche.soggetto_id` |

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_pratiche_a10_guard_contesto_ins_upd` | BEFORE | INSERT, UPDATE OF soggetto_id, soggetto_ruolo_id, istanza_utility_id | `pratiche.pratiche` |

---

### Messaggi errore

| Codice | ID | Messaggio |
|--------|----|-----------|
| `PRATICHE_ISTANZA_SENZA_RUOLO` | 304 | istanza_utility_id richiede soggetto_ruolo_id |
| `PRATICHE_RUOLO_SENZA_SOGGETTO` | 305 | soggetto_ruolo_id richiede soggetto_id |
| `PRATICHE_RUOLO_NON_COERENTE` | 306 | Il ruolo %s non appartiene al soggetto %s |
| `PRATICHE_ISTANZA_NON_COERENTE` | 307 | L'istanza %s non appartiene al soggetto %s |

---

### Note operative

* Il trigger scatta solo su INSERT o UPDATE delle colonne `soggetto_id`, `soggetto_ruolo_id`, `istanza_utility_id` (non su altri campi).
* La stessa validazione puo' essere replicata nel service Python per errori user-friendly, ma il trigger DB garantisce l'integrita' anche per accessi diretti.
* La catena di collegamento e': `pratiche.soggetto_id → soggetti_ruoli.soggetto_id` e `pratiche.soggetto_id → istanze_utilities.soggetto_id`.

---

{% include-markdown "signature-core.md" %}
