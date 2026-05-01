# trgfn_documenti_generati_block_delete

### Scopo

Trigger function `BEFORE DELETE` su `documenti.documenti_generati` che blocca **sempre** la cancellazione fisica di un documento generato (guard **A5** del piano Fase A documenti).

`documenti_generati` è la tabella append-only del registro di generazione persistita: ogni rigenerazione di un documento sorgente produce una nuova riga con `progressivo_sorgente` crescente (snapshot completo di template, contesto e hash). Cancellare un record significherebbe falsificare la sequenza storica delle generazioni e rendere irreproducibile l'audit del PDF prodotto.

Il ciclo di vita è gestito **esclusivamente via stato**: `GENERATO → ARCHIVIATO` (documento superato) oppure `GENERATO → ANNULLATO` (documento revocato per errore di emissione). Il record fisico resta indefinitamente e l'audit dei cambi di stato passa attraverso `data_update`/`user_update` (Fase A) e in futuro via `documenti_generati_eventi` (Fase B).

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_documenti_generati_a10_block_delete_dlt
BEFORE DELETE ON documenti.documenti_generati
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_documenti_generati_block_delete();
```

* **Fase**: `a10` (guard fail-fast).
* **Comportamento**: incondizionato — la `DELETE` non è mai un'operazione legittima sul registro di generazione.

## Logica

1. Solleva sempre `E_DOCUMENTI_GENERATO_DELETE_BLOCKED` con dettaglio `documento_generato_id`, `uid`, `stato`.
2. Il `RETURN OLD` è formale: l'eccezione interrompe la transazione.

## Codice errore

| Codice                                     | HTTP | Messaggio                                                                                          |
| ------------------------------------------ | ---- | -------------------------------------------------------------------------------------------------- |
| `E_DOCUMENTI_GENERATO_DELETE_BLOCKED`      | 409  | Documento generato non cancellabile: usare lo stato (`ARCHIVIATO`/`ANNULLATO`) per chiuderne il ciclo di vita. |

Messaggio in `config.messaggi_errore` (id 414).

## Caratteristiche

* **Append-only by design**: il delete block è la prima delle tre guard che rendono la tabella append-only e immutabile (insieme ad A6 coerenza e A7 immutabilità snapshot). Senza questa guard, la disabilitazione dello storico standard (Step B del piano Fase A) sarebbe un buco di audit.
* **No cleanup automatico**: non esiste TTL su `documenti_generati`. La storia delle generazioni si conserva quanto serve all'azienda; eventuali purge sono operazioni amministrative esplicite, fuori dal ciclo applicativo.
* **Coerenza con `documenti_generati_file`**: anche i file collegati sono protetti via A7-bis (immutabilità) e via FK `RESTRICT`: se non si può cancellare il padre, non si tenta nemmeno di cancellare i figli.

## Dipendenze

* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.documenti_generati`](/dbzero/documenti/tabelle/documenti_generati)
* [`trgfn_documenti_generati_check_coerenza`](trgfn_documenti_generati_check_coerenza.md) — guard A6 (coerenza referenziale)
* [`trgfn_documenti_generati_protect_snapshot`](trgfn_documenti_generati_protect_snapshot.md) — guard A7 (immutabilità snapshot)
* [Sviluppo Documenti — Piano DB §6.5, §13.3 A5, sezione B](/dev/work-in-progress/sviluppo-documenti-db)
