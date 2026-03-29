## 📘 Documentazione Funzione – `pratiche.trgfn_pratiche_set_data_apertura`

> 👀 **Vedi anche**
>
> [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche)
> [config.stati_pratiche](/dbzero/config/tabelle/stati_pratiche)

---
### 🎯 Scopo Principale

Valorizza automaticamente `data_apertura` alla transizione BOZZA → APERTA.
Immutabile: una volta valorizzata, non viene sovrascritta da transizioni successive.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_pratiche_set_data_apertura()
RETURNS trigger LANGUAGE plpgsql
```

---

### Logica di funzionamento

1. Se `stato_id` non cambia → nessuna azione.
2. Se `data_apertura` e' gia' valorizzata → preserva il valore originale (immutabilita').
3. Risolve gli id degli stati BOZZA e APERTA da `config.stati_pratiche.codice_interno` (mai hardcodati).
4. Se la transizione e' BOZZA → APERTA → valorizza `data_apertura = NOW()`.
5. Per qualsiasi altra transizione → nessuna azione.

---

### Trigger associato

| Nome | Fase | Evento | Tabella |
|------|------|--------|---------|
| `trg_pratiche_m50_set_data_apertura_upd` | BEFORE | UPDATE OF stato_id | `pratiche.pratiche` |

La fase `_m50_` e' intermedia: dopo i guard `_a10_` (transizione ammessa), prima dei trigger finali `_z90_` (giornale).

---

### Note operative

* `data_apertura` e' di tipo `DATE` (non timestamp) — per dashboard e SLA conta il giorno, non l'ora. Il timestamp preciso e' nel giornale (evento STATO_CAMBIATO).
* `data_apertura` e' NULL per pratiche ancora in BOZZA o annullate senza passare per APERTA.
* Valorizzata con `CURRENT_DATE` (non `NOW()`) per coerenza col tipo `DATE`.

---

{% include-markdown "signature-core.md" %}
