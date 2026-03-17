## 📘 Documentazione Funzione – `pratiche.fn_calcola_tempo_netto_da_a`

> 👀 **Vedi anche**
>
[pratiche.calcoli_tempo](/dbzero/pratiche/manual/calcoli_tempo)
> [pratiche.sospensioni](/dbzero/pratiche/manual/sospensioni)
> [fn_valuta_tempo_esecuzione_da_a](/dbzero/pratiche/manual/fn_valuta_tempo_esecuzione_da_a)

---

### 🎯 Scopo Principale

Funzione **check** (pura, STABLE): calcola i giorni netti trascorsi tra il completamento di `flusso_da` e il completamento di `flusso_a`, sottraendo i periodi di sospensione della pratica.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_calcola_tempo_netto_da_a(
    p_pratica_id   BIGINT,
    p_flusso_da_id BIGINT,
    p_flusso_a_id  BIGINT
) RETURNS INTEGER
LANGUAGE plpgsql STABLE
```

---

### Logica

1. Recupera `data_fine` del flusso_da come punto di partenza.
2. Se flusso_a e' gia' COMPLETATO, usa `data_fine` del flusso_a; altrimenti `NOW()`.
3. Calcola giorni lordi = punto_arrivo - punto_partenza.
4. Sottrae i giorni di sospensione a livello pratica (`flusso_id IS NULL`) che ricadono nel periodo.
5. Restituisce `GREATEST(0, giorni_lordi - giorni_sospensione)`.
6. Se flusso_da non ha `data_fine`, restituisce NULL.

---

{% include-markdown "signature-core.md" %}
