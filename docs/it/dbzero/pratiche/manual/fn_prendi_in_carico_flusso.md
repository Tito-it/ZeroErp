## 📘 Documentazione Funzione – `pratiche.fn_prendi_in_carico_flusso`

> 👀 **Vedi anche**
>
> [pratiche.competenze_flussi](/dbzero/pratiche/manual/competenze_flussi)
> [pratiche.fn_coda_lavoro_operatore](/dbzero/pratiche/manual/fn_coda_lavoro_operatore)
> [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---
### 🎯 Scopo Principale

Assegna un flusso DA_ESEGUIRE all'operatore corrente, verificando che abbia competenza attiva. Operazione atomica con lock pessimistico (`FOR UPDATE`) per evitare race condition.

---

### Firma della funzione

```sql
CREATE OR REPLACE FUNCTION pratiche.fn_prendi_in_carico_flusso(
    p_flusso_id        pratiche.flussi.id%TYPE,
    p_risorsa_umana_id anagrafiche.risorse_umane.id%TYPE
)
RETURNS BOOLEAN
LANGUAGE plpgsql
```

---

### Descrizione parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_flusso_id` | bigint | SI | ID del flusso da prendere in carico |
| `p_risorsa_umana_id` | bigint | SI | ID dell'operatore che prende in carico |

---

### Valore di ritorno

| Valore | Significato |
|--------|-------------|
| `TRUE` | Flusso assegnato con successo |
| `FALSE` | Flusso gia' assegnato allo stesso operatore (noop) |
| RAISE | Errore se il flusso non esiste, stato errato, gia' assegnato ad altro, o competenza mancante |

---

### Regole di validazione (ordine di esecuzione)

| # | Guard | Errore |
|---|-------|--------|
| 1 | Parametri obbligatori (NOT NULL, > 0) | `E_PARAMETRO_INVALIDO` |
| 2 | Il flusso deve esistere | `E_VALORE_MANCANTE` |
| 3 | Il flusso deve essere in stato DA_ESEGUIRE | `FLUSSI_PRESA_CARICO_STATO_ERRATO` (320) |
| 4 | Se gia' assegnato allo stesso operatore | Return `FALSE` (noop) |
| 5 | Se gia' assegnato ad altro operatore | `FLUSSI_GIA_ASSEGNATO` (321) |
| 6 | L'operatore deve avere competenza attiva (solo flussi template-based) | `FLUSSI_COMPETENZA_MANCANTE` (322) |

---

### Gestione concorrenza

La funzione usa `SELECT ... FOR UPDATE` sulla riga del flusso per evitare race condition:
se due operatori provano a prendere in carico lo stesso flusso contemporaneamente,
il secondo attende il rilascio del lock e poi fallira' con `FLUSSI_GIA_ASSEGNATO`.

---

### Esempi di utilizzo

```sql
-- Operatore 42 prende in carico flusso 100
SELECT pratiche.fn_prendi_in_carico_flusso(100, 42);
-- Ritorna TRUE se assegnato, FALSE se gia' suo

-- Da invocare dal service Python, non direttamente dalla UI
```

---

### Note operative

* Da invocare sempre tramite il service Python (`pratiche_service`), che gestisce l'envelope di errore per la UI.
* Per flussi manuali (senza `template_flusso_id`), la verifica competenza viene saltata.
* Dopo l'UPDATE, verifica che esattamente 1 riga sia stata aggiornata (`GET DIAGNOSTICS`).

---

{% include-markdown "signature-core.md" %}
