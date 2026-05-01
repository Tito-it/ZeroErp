# trgfn_documenti_generati_protect_snapshot

### Scopo

Trigger function `BEFORE UPDATE` su `documenti.documenti_generati` che blocca la modifica di **tutti i campi snapshot** del record di generazione (guard **A7** del piano Fase A documenti).

`documenti_generati` rappresenta un'**istantanea immutabile** del momento in cui un PDF (o output equivalente) è stato prodotto: `context_json`, `*_hash`, riferimenti template, sorgente, emittente, autore, timestamp, identificatori pubblici. Modificare uno qualsiasi di questi campi corromperebbe l'istantanea, rendendo l'audit della generazione non più riproducibile.

Solo `stato` e `meta` restano modificabili: lo `stato` per gestire il ciclo di vita (`GENERATO → ARCHIVIATO/ANNULLATO`), `meta` come canale per annotazioni applicative future (es. tag operativi).

Questa guard è il **prerequisito non negoziabile** della disabilitazione dello storico standard sulla tabella (Step B): senza A7 lo "spegnimento storico" sarebbe un buco di audit.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_documenti_generati_a10_protect_snapshot_upd
BEFORE UPDATE ON documenti.documenti_generati
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_documenti_generati_protect_snapshot();
```

* **Fase**: `a10` (guard fail-fast).
* **Trigger non `UPDATE OF`**: il check è espresso come `OR` di confronti diretti `NEW != OLD`. Questo trade-off vs `UPDATE OF` è scelto per:
  * coprire correttamente i campi nullable (`sorgente_riga`, `generato_da_user_id`) con `IS DISTINCT FROM`;
  * evitare la doppia manutenzione tra clausola `UPDATE OF` e logica interna;
  * semplificare l'evoluzione (aggiungere un campo allo snapshot è una sola riga di codice).

## Logica

1. Verifica una `OR` di confronti su tutti i campi snapshot: identificatori (`uid`, `*_id`), sorgente (`sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga`, `progressivo_sorgente`), generazione (`generato_at`, `generato_da_user_id`), payload (`context_json`, `context_hash`, `template_hash`, `pdf_hash`), denominazioni (`titolo`, `nome_file`).
2. Se almeno uno è cambiato, solleva `E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE` con dettaglio `documento_generato_id`, `uid`.
3. Altrimenti l'`UPDATE` passa: rimangono modificabili `stato`, `meta`, audit fields (`data_update`, `user_update`, `tx_id`).

## Codice errore

| Codice                                            | HTTP | Messaggio                                                                                          |
| ------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------- |
| `E_DOCUMENTI_GENERATO_SNAPSHOT_IMMUTABILE`        | 409  | Documento generato: snapshot di generazione immutabile. Solo `stato` e `meta` sono modificabili.    |

Messaggio in `config.messaggi_errore` (id 416).

## Caratteristiche

* **Tre guard insieme**: A5 (delete block), A6 (coerenza referenziale), A7 (immutabilità snapshot). Insieme rendono la tabella veramente append-only e auto-coerente.
* **Sostituisce lo storico standard**: con A7 attiva, lo storico standard di `documenti_generati` produrrebbe solo righe duplicate dei campi `stato`/`meta` (gli unici a cambiare): costo elevato, beneficio nullo. Per questo lo Step B disabilita storico provisioning + trigger su questa tabella.
* **`IS DISTINCT FROM` per nullable**: `sorgente_riga` e `generato_da_user_id` sono i due campi `NULL`-ammessi nello snapshot; usare `!=` lì avrebbe lasciato passare in modo silenzioso il pattern `NULL → valore` o `valore → NULL`.

## Dipendenze

* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.documenti_generati`](/dbzero/documenti/tabelle/documenti_generati)
* [`trgfn_documenti_generati_block_delete`](trgfn_documenti_generati_block_delete.md) — guard A5
* [`trgfn_documenti_generati_check_coerenza`](trgfn_documenti_generati_check_coerenza.md) — guard A6
* [`trgfn_documenti_generati_file_protect_file`](trgfn_documenti_generati_file_protect_file.md) — guard A7-bis (controparte sul file)
* [Sviluppo Documenti — Piano DB §13.3 A7, sezione B](/dev/work-in-progress/sviluppo-documenti-db)
