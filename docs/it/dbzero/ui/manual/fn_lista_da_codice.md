# fn_lista_da_codice

### 🎯 Scopo Principale

Restituisce **la riga di una lista configurabile a partire dal suo codice**, se la lista esiste ed è attiva; altrimenti solleva `E_UI_LISTA_NON_TROVATA`. È l'unico punto in cui una lista si cerca per codice: il risolutore della configurazione, la ricerca libera e il backend passano tutti da qui, così la regola «lista assente o spenta» è scritta una volta sola.

## Schema

`ui`

## Firma

```sql
ui.fn_lista_da_codice(
  p_lista_codice ui.lista_definizione.codice%TYPE
) RETURNS ui.lista_definizione
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_lista_codice` | `VARCHAR` | Sì | Codice lista (es. `catalogo.unita_misura`) |

## Chi la usa

| Chi | Cosa legge |
|---|---|
| [`ui.fn_resolve_lista_config`](/dbzero/ui/funzioni/fn_resolve_lista_config) | `id`, `multi_emittente`, `perimetro_emittente`, `ricerca_min_caratteri` |
| [`ui.fn_lista_colonne_ricerca_full`](/dbzero/ui/funzioni/fn_lista_colonne_ricerca_full) | `id` |
| la ricerca libera del backend | `ricerca_min_caratteri`, la soglia sotto la quale il termine non filtra |

## Casi particolari

- **Lista inesistente o spenta** (`attivo = false`): errore `E_UI_LISTA_NON_TROVATA`, con il codice nella frase.

## Caratteristiche

- **STABLE**: non modifica dati.

## Esempio

```sql
-- La soglia della ricerca libera di una lista
SELECT ricerca_min_caratteri
  FROM ui.fn_lista_da_codice('catalogo.unita_misura');
```

⚠️ Si legge con `SELECT … FROM`: `SELECT ui.fn_lista_da_codice(...)` restituisce la riga intera come un'unica tupla in un solo campo.
