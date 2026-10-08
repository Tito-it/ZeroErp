# fn_get_billing_account_by_istanza

### Scopo

⚠️ **In ritiro** (2026-10-08). Resolver di **lettura** (no raise): il billing account di
un'istanza utility, **se l'istanza ne ha uno solo**. `NULL` se ne ha piu' d'uno o se l'input non
e' valido. Mai un `LIMIT 1`: con piu' BA la domanda non ha una risposta, e la funzione non ne
sceglie uno.

## Perche' e' in ritiro

Serviva al dettaglio pratica per esporre «il cliente della pratica» ai documenti aperti dal
flusso. Dal 2026-10-08 un'istanza puo' avere piu' utility, ognuna col suo BA, e un BA ha un solo
cliente: «il cliente dell'istanza» non e' piu' una domanda con una risposta. La pratica porta ora
il suo BA in una colonna (`pratiche.pratiche.billing_account_id`, D-9), e il backend deve leggere
quella. Quando nessuno la chiama piu', la funzione si cancella con questa pagina.

## Logica

1. `p_istanza_id` `NULL` o `<= 0` → `NULL`, senza errore.
2. Conta i BA dell'istanza in `anagrafiche.billing_account`: se e' **uno**, ritorna quello;
   altrimenti `NULL`.

## Note di migrazione

* **2026-06-15**: nasce. Leggeva il BA del **cliente** dell'istanza (`ORDER BY id DESC LIMIT 1`),
  contando su «un cliente per istanza»; `NULL` per il «prospect» senza cliente.
* **2026-10-08** (`20261008-71`, brief-db-istanza-nasce-col-ba R-8): legge `billing_account`,
  ritorna il BA solo se e' uno. Il prospect senza BA non esiste piu' (il BA nasce con l'istanza);
  i clienti sono uno per BA (`uq_clienti_billing_account`). La gemella
  `fn_get_stato_cliente_by_istanza` e' ritirata (D-8).

## Caller attuali

* Dettaglio pratica (backend, `pratiche_repository`): da sostituire con
  `pratiche.pratiche.billing_account_id`.
