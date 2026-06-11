## 📘 Documentazione Funzione – `pratiche.fn_check_ripetibilita_flusso`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche)
>
Funzioni collegate:
>
[pratiche.fn_guard_ripetibilita_flusso](fn_guard_ripetibilita_flusso.md)
> [pratiche.trgfn_flussi_guard_ripetibilita](trgfn_flussi_guard_ripetibilita.md)

---
### 🎯 Scopo Principale
La funzione **`pratiche.fn_check_ripetibilita_flusso`** e' una **pure check** (`fn_check_*`): verifica se una **nuova istanza** di un template flusso e' ammessa nella pratica, secondo la regola di ripetibilita' dichiarata sul template (`template_flussi.ripetibilita` — decisione D3, analisi-pratiche-workflow-v2).

Ritorna un singolo `boolean`. Non solleva eccezioni — il chiamante decide come gestire il divieto.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_ripetibilita_flusso(
  p_pratica_id         pratiche.flussi.pratica_id%TYPE,
  p_template_flusso_id pratiche.flussi.template_flusso_id%TYPE
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_pratica_id` | bigint | SI | ID della pratica in cui si vuole creare la nuova istanza |
| `p_template_flusso_id` | integer | SI | ID del template flusso da istanziare |

**Ritorna**: `boolean` — `true` se la nuova istanza e' ammessa.

---

### Logica di funzionamento

1. Legge `ripetibilita` dal template. Template inesistente o `SEMPRE` → `true` (la FK su `flussi` copre il caso inesistente).
2. Individua l'**ultima istanza** del template nella pratica: `MAX(id)` tra i flussi non `ANNULLATO` (un'istanza annullata **non consuma** la ripetibilita'; la recency e' per `id`, **non** per `sequenza`, che e' la posizione nel template).
3. Applica la regola:

| Regola | Esito del check |
|---|---|
| `SEMPRE` | sempre `true` |
| `MAI` | `true` solo se non esiste alcuna istanza non annullata |
| `SE_NON_POSITIVO` | `true` solo se l'ultima istanza e' `COMPLETATO` con esito **diverso** da `POSITIVO`. Un'istanza ancora aperta (`DA_ESEGUIRE`/`IN_CORSO`/`SOSPESO`/`ERRORE`) **blocca** (niente doppioni vivi) |

---

### Esempi di utilizzo

```sql
-- La pratica 100 puo' avere una nuova istanza del template 5?
SELECT pratiche.fn_check_ripetibilita_flusso(100, 5);
```

---

### Note operative

* Funzione `STABLE`: non modifica dati.
* Usata internamente da `fn_guard_ripetibilita_flusso` per la validazione fail-fast e dal BE per pilotare il bottone "Ripeti" nel percorso pratica (ripetibile adesso si'/no) senza duplicare logica.
* La prima istanza di un template e' **sempre** ammessa, qualunque sia la regola.
