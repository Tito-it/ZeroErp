## 📘 Documentazione Funzione – `pratiche.fn_valuta_tempo_esecuzione_da_a`

> 👀 **Vedi anche**
>
[pratiche.formule_tempo](/dbzero/pratiche/manual/formule_tempo)
> [fn_calcola_tempo_netto_da_a](/dbzero/pratiche/manual/fn_calcola_tempo_netto_da_a)

---

### 🎯 Scopo Principale

Funzione **check** (pura, STABLE): confronta il tempo netto trascorso tra due flussi con la formula tempo configurata. Restituisce lo stato temporale corrente.

---

### Firma

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_valuta_tempo_esecuzione_da_a(
    p_pratica_id   BIGINT,
    p_flusso_da_id BIGINT,
    p_flusso_a_id  BIGINT
) RETURNS TABLE(
    giorni_netti      INTEGER,
    giorni_esecuzione INTEGER,
    giorni_rimanenti  INTEGER,
    stato_tempo       TEXT
)
LANGUAGE plpgsql STABLE
```

---

### Logica

1. Recupera `tipo_prestazione_id` dalla pratica e `template_flusso_id` dai due flussi.
2. Cerca la formula matching in `formule_tempo` per la combinazione tipo + da + a.
3. Se non esiste formula o un flusso non ha template → restituisce zero righe (nessuna valutazione).
4. Chiama `fn_calcola_tempo_netto_da_a` per i giorni netti.
5. Determina `stato_tempo`:
   - `giorni_rimanenti <= 0` → **SFORATO**
   - `giorni_rimanenti <= giorni_critico` → **CRITICO**
   - `giorni_rimanenti <= giorni_warning` → **WARNING**
   - Altrimenti → **OK**

---

{% include-markdown "signature-core.md" %}
