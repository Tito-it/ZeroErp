## 📘 Documentazione Funzione – `pratiche.fn_guard_ripetibilita_flusso`

> 👀 **Vedi anche**
>
Funzioni collegate:
>
[pratiche.fn_check_ripetibilita_flusso](fn_check_ripetibilita_flusso.md)
> [pratiche.trgfn_flussi_guard_ripetibilita](trgfn_flussi_guard_ripetibilita.md)
> [pratiche.fn_guard_prerequisiti_flusso](fn_guard_prerequisiti_flusso.md)

---
### 🎯 Scopo Principale
La funzione **`pratiche.fn_guard_ripetibilita_flusso`** e' la **sentinella fail-fast** (`fn_guard_*`) della regola di ripetibilita': se la regola del template vieta una nuova istanza nella pratica, solleva `PRATICHE_FLUSSO_NON_RIPETIBILE` con contesto parlante (regola del template + stato/esito dell'ultima istanza).

Pattern simmetrico a `fn_guard_prerequisiti_flusso`: il check puro vive in `fn_check_ripetibilita_flusso`, il guard aggiunge solo il sollevamento errore.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_guard_ripetibilita_flusso(
  p_pratica_id         pratiche.flussi.pratica_id%TYPE,
  p_template_flusso_id pratiche.flussi.template_flusso_id%TYPE
)
RETURNS void
LANGUAGE plpgsql
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_pratica_id` | bigint | SI | ID della pratica in cui si vuole creare la nuova istanza |
| `p_template_flusso_id` | integer | SI | ID del template flusso da istanziare |

---

### ⚠️ Errori sollevati

| Codice errore | Condizione |
|---------------|------------|
| `PRATICHE_FLUSSO_NON_RIPETIBILE` (483) | La regola di ripetibilita' del template vieta una nuova istanza: `MAI` con istanza esistente, oppure `SE_NON_POSITIVO` con ultima istanza aperta o chiusa `POSITIVO` |

Placeholders del messaggio: codice template, regola, stato/esito dell'ultima istanza.

---

### Note operative

* Invocata dal trigger `trg_flussi_a10_guard_ripetibilita_ins` (BEFORE INSERT su `pratiche.flussi`): la regola vale per **qualunque chiamante** (BE, funzioni DB, SQL diretto).
* Se il check passa, la funzione ritorna senza effetti.
