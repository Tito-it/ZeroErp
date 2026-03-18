## 📘 Documentazione Funzione – `pratiche.fn_guard_prerequisiti_flusso`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_check_prerequisiti_flusso](fn_check_prerequisiti_flusso.md)
> `script.fn_log_and_raise_error`
>
Trigger:
>
`trg_flussi_a10_guard_prerequisiti_ins` (BEFORE INSERT su flussi)

---
### 🎯 Scopo Principale
La funzione **`pratiche.fn_guard_prerequisiti_flusso`** e' una **guard fail-fast** (`fn_guard_*`): verifica i prerequisiti e **solleva eccezione** se non sono tutti soddisfatti.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_guard_prerequisiti_flusso(
  p_pratica_id         pratiche.pratiche.id%TYPE,
  p_template_flusso_id pratiche.template_flussi.id%TYPE
)
RETURNS void
LANGUAGE plpgsql
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_pratica_id` | bigint | SI | ID della pratica |
| `p_template_flusso_id` | integer | SI | ID del template flusso di cui verificare i prerequisiti |

---

### Logica di funzionamento

1. Invoca `fn_check_prerequisiti_flusso(p_pratica_id, p_template_flusso_id)`.
2. Raccoglie i codici di tutti i prerequisiti con `soddisfatto = false` tramite `string_agg`.
3. Se almeno uno non e' soddisfatto, chiama `script.fn_log_and_raise_error` con codice errore `PRATICHE_PREREQUISITI_NON_SODDISFATTI` e l'elenco dei codici mancanti.
4. Se tutti soddisfatti, ritorna senza errori.

---

### ⚠️ Errori sollevati

| Codice errore | Condizione | Dettaglio |
|---------------|------------|-----------|
| `PRATICHE_PREREQUISITI_NON_SODDISFATTI` | Almeno un prerequisito non soddisfatto | Lista codici mancanti nel dettaglio jsonb |

---

### Esempi di utilizzo

```sql
-- Verifica fail-fast (solleva eccezione se prerequisiti mancanti)
SELECT pratiche.fn_guard_prerequisiti_flusso(100, 5);
```

---

### Note operative

* Usata come wrapper dal trigger `trgfn_flussi_guard_prerequisiti()` per bloccare l'INSERT di flussi senza prerequisiti.
* Puo' essere chiamata anche direttamente dal backend Django prima di tentare l'inserimento.
