## 📘 Documentazione Funzione – `pratiche.trgfn_flussi_calcolo_tempo_completamento`

> 👀 **Vedi anche**
>
> * [pratiche.calcoli_tempo](/dbzero/pratiche/manual/calcoli_tempo)
> * [pratiche.formule_tempo](/dbzero/pratiche/manual/formule_tempo)
> * [fn_calcola_tempo_netto_da_a](/dbzero/pratiche/manual/fn_calcola_tempo_netto_da_a)

---

### 🎯 Scopo Principale

Trigger function unica che gestisce il ciclo di vita dei calcoli tempo nel modello da/a. AFTER UPDATE OF `stato_id` su `pratiche.flussi`, scatta quando un flusso va COMPLETATO. Il flusso completato puo' essere referenziato come partenza (`flusso_da`) e/o come arrivo (`flusso_a`) in formule diverse.

---

### 🔧 Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.trgfn_flussi_calcolo_tempo_completamento()
RETURNS trigger LANGUAGE plpgsql
```

---

### ⚙️ Logica (due fasi)

**Fase 1 — Il flusso completato e' un flusso_da (avvio conteggio):**

1. Cerca in `formule_tempo` le formule con `template_flusso_da_id` = template del flusso completato.
2. Per ogni formula: cerca il flusso partner (`flusso_a`) nella stessa pratica.
3. Se il flusso_a esiste: INSERT in `calcoli_tempo` con snapshot di `giorni_formula`.
4. **Ordine invertito**: se il flusso_a e' gia' COMPLETATO, chiude immediatamente la riga calcolando i tempi.

**Fase 2 — Il flusso completato e' un flusso_a (chiusura conteggio):**

1. Cerca righe aperte in `calcoli_tempo` con `flusso_a_id = NEW.id` e `data_fine_calcolo IS NULL`.
2. Per ogni riga: calcola giorni lordi, sospensione, netti e imposta `sforato`.

---

### 🔗 Trigger associato

| Nome                                                  | Fase  | Evento              | Tabella           |
| ----------------------------------------------------- | ----- | ------------------- | ----------------- |
| `trg_flussi_z90_calcolo_tempo_completamento_upd`      | AFTER | UPDATE OF stato_id  | `pratiche.flussi` |

WHEN: `OLD.stato_id IS DISTINCT FROM NEW.stato_id`.

Il trigger scatta per ogni cambio stato, ma la function verifica internamente che il nuovo stato sia COMPLETATO.

---

{% include-markdown "signature-core.md" %}
