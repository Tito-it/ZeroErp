# fn_lista_colonne_ricerca_full

> **Ultimo aggiornamento**: 12 novembre 2026

### 🎯 Scopo Principale

Dice **in quali colonne di una lista l'utente che la sta guardando può fare la ricerca libera**, e per ciascuna quale campo della vista interrogare. Il backend la legge a ogni ricerca: così il flag `ricercabile_full` cambiato dal pannello di amministrazione vale subito, e una colonna che l'utente non può vedere non entra mai nella ricerca.

## Schema

`ui`

## Firma

```sql
ui.fn_lista_colonne_ricerca_full(
  p_lista_codice ui.lista_definizione.codice%TYPE
) RETURNS TABLE (
  codice         ui.lista_colonna.codice%TYPE,
  campo_sorgente ui.lista_colonna.campo_sorgente%TYPE
)
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `p_lista_codice` | `VARCHAR` | Sì | Codice lista (es. `vendite.preventivi`) |

Utente e veste **non** si passano: si leggono dalla sessione (`app.current_user_id` e [`ui.fn_veste_corrente`](/dbzero/ui/funzioni/fn_veste_corrente)), come li imposta l'autenticazione.

## Quali colonne restituisce

Tutte quelle che rispettano **insieme** quattro condizioni:

| Condizione | Perché |
|---|---|
| colonna attiva | una colonna spenta non esiste per la lista |
| `ricercabile_full = true` | è la scelta, fatta nel catalogo, di cercarci dentro |
| `campo_sorgente` valorizzato | senza, non c'è niente da interrogare. Senza sorgente vuol dire `NULL`: la stringa vuota la rifiuta un vincolo della tabella. Il filtro accetta ancora anche `''`, ed è innocuo |
| livello effettivo diverso da `BLOCCATO` | se l'utente non vede la colonna, non ci cerca. `LETTURA` entra: spegne l'export, non la vista |

Il livello effettivo viene da [`ui.fn_lista_colonne_livello`](/dbzero/ui/funzioni/fn_lista_colonne_livello), la stessa sede da cui lo legge `fn_resolve_lista_config`. Le due risposte coincidono per costruzione.

## Casi particolari

- **Nessun utente in sessione** (un comando, un job): nessun grant si applica, quindi le colonne **sensibili escono** e le altre restano.
- **L'emittente fiscale non entra**: i permessi di colonna sono per profilo d'accesso, non per azienda.
- **Lista inesistente o spenta**: errore `E_UI_LISTA_NON_TROVATA`, dal building block [`ui.fn_lista_da_codice`](/dbzero/ui/funzioni/fn_lista_da_codice), lo stesso di `fn_resolve_lista_config`.

## Caratteristiche

- **STABLE**: non modifica dati.
- Ordine dei risultati: `ordine_default` della colonna, poi `codice`.

## Dipendenze

- `ui.lista_definizione`, `ui.lista_colonna`
- [`ui.fn_lista_colonne_livello`](/dbzero/ui/funzioni/fn_lista_colonne_livello) — il livello effettivo di ogni colonna
- [`ui.fn_veste_corrente`](/dbzero/ui/funzioni/fn_veste_corrente) — la veste dalla sessione

## Esempio

```sql
SELECT codice, campo_sorgente
  FROM ui.fn_lista_colonne_ricerca_full('vendite.preventivi');
```

⚠️ Si legge con `SELECT … FROM`: `SELECT ui.fn_lista_colonne_ricerca_full(...)` restituisce ogni riga come un'unica tupla in un solo campo.
