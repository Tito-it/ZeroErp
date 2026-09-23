# fn_lista_colonne_livello

### 🎯 Scopo Principale

Calcola, per **ogni colonna attiva** di una lista, il livello con cui un utente la vede: `TUTTO`, `LETTURA` o `BLOCCATO`. È la **sede unica** di questa regola: la leggono sia `fn_resolve_lista_config` (quali colonne mostrare) sia `fn_lista_colonne_ricerca_full` (in quali colonne cercare). Due calcoli separati prima o poi darebbero due risposte diverse, e la ricerca troverebbe righe per il valore di una colonna che la lista non mostra.

## Schema

`ui`

## Firma

```sql
ui.fn_lista_colonne_livello(
  p_lista_id     ui.lista_definizione.id%TYPE,
  p_auth_user_id INTEGER,
  p_veste        config.ruolo_applicativo
) RETURNS TABLE (
  colonna_id      ui.lista_colonna.id%TYPE,
  codice          ui.lista_colonna.codice%TYPE,
  livello_accesso config.livello_accesso
)
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_lista_id` | `INTEGER` | Sì | Id della lista |
| `p_auth_user_id` | `INTEGER` | No | Utente. `NULL` = nessun profilo, restano i livelli di ripiego |
| `p_veste` | `config.ruolo_applicativo` | No | Veste sotto cui cercare i profili. `NULL` = tutte le vesti dell'utente (come restituisce [`ui.fn_veste_corrente`](/dbzero/ui/funzioni/fn_veste_corrente)) |

## La regola

1. I permessi si cercano in [`ui.lista_colonna_permesso`](/dbzero/ui/tabelle/lista_colonna_permesso), fra i profili d'accesso applicabili all'utente sotto la veste (`script.fn_get_profili_accesso_applicabili`).
2. Se più profili danno un permesso sulla stessa colonna, vince il profilo **più specifico** (AD_HOC prima di REPARTO e PORTALE); a parità, il livello **più restrittivo** (`BLOCCATO`, poi `LETTURA`, poi `TUTTO`).
3. Senza alcun permesso: `BLOCCATO` se la colonna è `sensibile`, `TUTTO` altrimenti.

⚠️ L'emittente fiscale non entra: i permessi di colonna sono per profilo d'accesso.

## Risultato

Una riga per **ogni** colonna attiva della lista, **anche** quelle `BLOCCATO`. Filtrare è compito di chi legge, perché ciascuno ne fa una cosa diversa: il risolutore toglie le `BLOCCATO` e spegne l'export sulle `LETTURA`, la ricerca toglie le `BLOCCATO`.

## Caratteristiche

- **STABLE**: non modifica dati.
- Chiama il risolutore dei profili **una volta**, qualunque sia il numero di colonne.

## Esempio

```sql
SELECT codice, livello_accesso
  FROM ui.fn_lista_colonne_livello(12, 42, ui.fn_veste_corrente());
```
