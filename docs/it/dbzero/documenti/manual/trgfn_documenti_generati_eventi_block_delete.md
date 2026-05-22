# trgfn_documenti_generati_eventi_block_delete

### Scopo

Trigger function `BEFORE DELETE` su `documenti.documenti_generati_eventi` che blocca **sempre** la cancellazione fisica di un evento dalla timeline del documento.

`documenti_generati_eventi` è la timeline append-only del ciclo vita documento (Decisioni 30/31/72): registra `GENERATO`, `SCARICATO`, `STORAGE_ORPHAN`. Cancellare un evento significherebbe falsificare l'audit: per esempio rimuovere la traccia di un download avvenuto, o cancellare il log di un file orfano da pulire. Nessun caso d'uso legittimo prevede `DELETE` su questa tabella.

Le correzioni si registrano **come nuovo evento** (tipicamente `esito='WARN'` con riferimento all'evento precedente nel campo `detail`), mai cancellando la storia.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_documenti_generati_eventi_a10_block_delete_dlt
BEFORE DELETE ON documenti.documenti_generati_eventi
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_documenti_generati_eventi_block_delete();
```

* **Fase**: `a10` (guard fail-fast).
* **Comportamento**: incondizionato — la `DELETE` non è mai un'operazione legittima sulla timeline.

## Logica

1. Solleva sempre `E_EVENTO_DOCUMENTO_DELETE_VIETATA` con dettaglio `evento_id`, `documento_generato_id`, `evento_tipo`, `evento_at`.
2. Il `RETURN OLD` è formale: l'eccezione interrompe la transazione.

## Codice errore

| Codice                                  | HTTP | Messaggio                                                                                       |
| --------------------------------------- | ---- | ----------------------------------------------------------------------------------------------- |
| `E_EVENTO_DOCUMENTO_DELETE_VIETATA`     | 409  | Eventi documento: la cancellazione fisica è vietata (timeline append-only).                     |

Messaggio in `config.messaggi_errore` (id 425).

## Caratteristiche

* **Append-only by design**: insieme al guard `block_update`, garantisce l'immutabilità totale della timeline. Equivalente DB-side della scelta architetturale di disabilitare lo storico standard sulla tabella (la colonna `storicizza` è omessa nel DDL).
* **Coerenza con `documenti_generati`**: il padre è già protetto da A5 (delete block). Il guard qui è un secondo livello: anche se per ipotesi la FK `RESTRICT` venisse aggirata (impossibile), l'evento resterebbe comunque protetto dal trigger.
* **No purge automatico**: la timeline non ha TTL. Per uso operativo gli eventi più recenti sono i più consultati (indice composito `(documento_generato_id, evento_at DESC)`); l'archivio storico resta integro per audit indefinito.

## Dipendenze

* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.documenti_generati_eventi`](documenti_generati_eventi.md)
* [`trgfn_documenti_generati_eventi_block_update`](trgfn_documenti_generati_eventi_block_update.md) — guard append-only complementare (UPDATE)
* [`trgfn_documenti_generati_block_delete`](trgfn_documenti_generati_block_delete.md) — guard A5 sul padre `documenti_generati`
* [Sviluppo Documenti — §10-bis.5 (anticipo eventi v1)](/dev/work-done/sviluppo-documenti)
