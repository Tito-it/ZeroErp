## 📘 Documentazione Funzione – `pratiche.fn_check_prerequisiti_flusso`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)
> [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche)
>
Funzioni collegate:
>
[pratiche.fn_guard_prerequisiti_flusso](fn_guard_prerequisiti_flusso.md)

---
### 🎯 Scopo Principale
La funzione **`pratiche.fn_check_prerequisiti_flusso`** e' una **pure check** (`fn_check_*`): verifica se tutti i prerequisiti di un template flusso sono soddisfatti per una data pratica.

Ritorna una **riga per ogni prerequisito** con un flag `soddisfatto` (boolean). Non solleva eccezioni — il chiamante decide come gestire i prerequisiti mancanti.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_check_prerequisiti_flusso(
  p_pratica_id         pratiche.pratiche.id%TYPE,
  p_template_flusso_id pratiche.template_flussi.id%TYPE
)
RETURNS TABLE(
  prerequisito_id  pratiche.template_flussi.id%TYPE,
  codice           pratiche.template_flussi.codice%TYPE,
  descrizione      pratiche.template_flussi.descrizione%TYPE,
  soddisfatto      boolean
)
LANGUAGE plpgsql
STABLE
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_pratica_id` | bigint | SI | ID della pratica per cui verificare i prerequisiti |
| `p_template_flusso_id` | integer | SI | ID del template flusso di cui controllare i prerequisiti configurati |

---

### Colonne ritornate

| Colonna | Tipo | Descrizione |
|---------|------|-------------|
| `prerequisito_id` | integer | ID del template flusso prerequisito |
| `codice` | varchar(50) | Codice del template flusso prerequisito |
| `descrizione` | text | Descrizione del template flusso prerequisito |
| `soddisfatto` | boolean | `true` se esiste almeno un flusso COMPLETATO per la pratica con quel template |

---

### Logica di funzionamento

1. Legge i prerequisiti configurati in `pratiche.template_flussi_prerequisiti` per il template indicato.
2. Per ciascuno, verifica se nella pratica esiste un flusso con quel `template_flusso_id` in stato **COMPLETATO** (tramite `config.stati_flussi_pratiche.codice_interno`).
3. Restituisce tutte le righe con il flag calcolato — non filtra ne' solleva errori.

---

### Esempi di utilizzo

```sql
-- Verifica prerequisiti per pratica 100, template flusso 5
SELECT * FROM pratiche.fn_check_prerequisiti_flusso(100, 5);

-- Solo prerequisiti non soddisfatti
SELECT * FROM pratiche.fn_check_prerequisiti_flusso(100, 5)
WHERE NOT soddisfatto;
```

---

### Note operative

* Funzione `STABLE`: non modifica dati, sicura per uso ripetuto nella stessa transazione.
* Usata internamente da `fn_guard_prerequisiti_flusso` per la validazione fail-fast.
* Se il template non ha prerequisiti configurati, ritorna zero righe (nessun prerequisito = tutti soddisfatti).
