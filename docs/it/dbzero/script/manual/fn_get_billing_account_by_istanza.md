# fn_get_billing_account_by_istanza

### Scopo

Resolver di **lettura** (no raise) che, data un'istanza utility, restituisce il `billing_account_id` del **cliente attivo** su quell'istanza. `NULL` se l'istanza non ha un cliente (prospect puro) o se l'input non e' valido.

Serve alla pratica per **esporre il contesto cliente** ai documenti che si aprono dal proprio flusso (preventivo / offerta / contratto): il backend proietta il campo nel dettaglio pratica senza fare alcuna derivazione di dominio, e il frontend precompila/blocca `billing_account_id` dal contesto.

Introdotta 2026-06-15 (brief contesto cliente pratica). Specchio di [`fn_get_stato_cliente_by_istanza`](/dbzero/script/funzioni/fn_get_stato_cliente_by_istanza): stesso schema, stessa forma `_by_istanza`, stessa derivazione via `anagrafiche.clienti`.

## Schema

`script` (convention progetto: funzioni di lettura riusabili cross-dominio in `script`).

## Firma

```sql
script.fn_get_billing_account_by_istanza(
    p_istanza_id  anagrafiche.istanze_utilities.id%TYPE
) RETURNS anagrafiche.clienti.billing_account_id%TYPE
LANGUAGE plpgsql STABLE
```

Tipi ancorati con `%TYPE` alle colonne sorgente: il parametro segue il tipo della PK istanza, il ritorno il tipo del BA in `clienti`.

## Logica

1. **Guard input** (resolver di lettura): `p_istanza_id` `NULL` o `<= 0` → ritorna `NULL`, **senza raise**.
2. Cerca in `anagrafiche.clienti` la riga con `istanza_utility_id = p_istanza_id` (`ORDER BY id DESC LIMIT 1`, difensivo: `clienti` ha `UNIQUE(istanza_utility_id)` → al piu' 1 riga) e ne ritorna `billing_account_id`.
3. Nessun cliente per quell'istanza → `NULL` (prospect).

### Semantica NULL (non raise) — deroga consapevole

La regola generale "parametro ID `NULL`/`<=0` → errore" vale per i **punti di mutazione**. Qui la funzione e' un **resolver di lettura** e "manca il billing account" e' una risposta **legittima** (prospect, oppure istanza assente): ritornare `NULL` e' corretto, non un bug da intercettare. Comportamento allineato al fratello `fn_get_stato_cliente_by_istanza`.

### Coerenza `(istanza, BA)` garantita strutturalmente

Il BA ritornato appartiene **per costruzione** all'istanza richiesta: la FK composta `fk_clienti_billing_account (billing_account_id, istanza_utility_id)` su `anagrafiche.clienti` lega il cliente al proprio BA sulla stessa istanza. Quindi la coppia esposta dalla pratica e' **sempre** una coppia che il documento accetterebbe — **non** serve invocare [`fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza).

## Performance

`STABLE` + singolo lookup su `clienti` per `istanza_utility_id` (UNIQUE): O(log n). Sicura da chiamare in `SELECT` di dettaglio/lista.

## Caller attuali

* Dettaglio pratica (backend): proiezione `script.fn_get_billing_account_by_istanza(p.istanza_utility_id) AS billing_account_id`.

## Caller candidati futuri

* Qualsiasi consumatore che, partendo da un'istanza utility, debba risolvere il BA del cliente attivo (preventivo/offerta/contratto aperti dal flusso pratica).

## Dipendenze

Nessuna fn esterna. Solo lookup su `anagrafiche.clienti`.

## Vedi anche

* [`script.fn_get_stato_cliente_by_istanza`](/dbzero/script/funzioni/fn_get_stato_cliente_by_istanza) — funzione gemella (stato cliente per istanza), stesso pattern.
* [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza) — coerenza coppia `(istanza, utility)` applicata dal guard preventivi.
* [`anagrafiche.clienti`](/dbzero/anagrafiche/tabelle/clienti) — fonte della derivazione (`UNIQUE(istanza_utility_id)`, FK `(billing_account_id, istanza_utility_id)`).
