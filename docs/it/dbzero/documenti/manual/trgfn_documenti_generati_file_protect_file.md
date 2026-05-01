# trgfn_documenti_generati_file_protect_file

### Scopo

Trigger function `BEFORE UPDATE` su `documenti.documenti_generati_file` che blocca la modifica delle colonne **file-specifiche** e dell'attributo `is_principale` (guard **A7-bis** del piano Fase A documenti).

Una riga di `documenti_generati_file` registra il file fisico effettivamente persistito su storage (PDF finale, in Fase A; futuri PDF allegati, firmati, html in Fase B). Una volta scritto, il file binario non può essere sostituito senza falsificare l'identità della generazione: cambiare `storage_key` (cioè il puntamento a un binario diverso), `sha256` (l'identità del contenuto) o `file_size_bytes` significherebbe mentire sull'output del documento.

`is_principale` è bloccata anch'essa: il "file principale" è una scelta deliberata del momento di generazione (in Fase A: sempre il `PDF_FINALE`); cambiare la designazione successivamente confonderebbe il consumer applicativo che cerca "il" file principale di un documento.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_documenti_generati_file_a10_protect_file_upd
BEFORE UPDATE ON documenti.documenti_generati_file
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_documenti_generati_file_protect_file();
```

* **Fase**: `a10` (guard fail-fast).
* Stessa scelta di A7: trigger non `UPDATE OF` per coerenza con il check interno.

## Logica

1. Verifica una `OR` di confronti su: `documento_generato_id`, `file_tipo_id`, `storage_key`, `sha256`, `file_size_bytes`, `mime_type`, `file_name`, `is_principale`.
2. Se almeno uno è cambiato, solleva `E_DOCUMENTI_GENERATO_FILE_IMMUTABILE` con dettaglio `documento_generato_id`, `file_tipo_id`.
3. Altrimenti l'`UPDATE` passa: restano modificabili `meta`, `ordinamento` (in scenari Fase B), audit fields.

## Codice errore

| Codice                                       | HTTP | Messaggio                                                                                              |
| -------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------ |
| `E_DOCUMENTI_GENERATO_FILE_IMMUTABILE`       | 409  | File persistito di un documento generato: identità file e flag principale immutabili (no replace).      |

Messaggio in `config.messaggi_errore` (id 417).

## Caratteristiche

* **Controparte di A7**: A7 protegge lo snapshot funzionale del documento; A7-bis protegge il file binario che lo materializza. Insieme rendono la coppia `(documenti_generati, documenti_generati_file)` veramente append-only.
* **Pattern "no replace, only append"**: per sostituire il PDF (caso eccezionale: bug di render scoperti dopo l'emissione), si annulla il `documenti_generati` (`stato = 'ANNULLATO'`) e si rigenera il documento, ottenendo un nuovo `progressivo_sorgente` con un nuovo `documenti_generati_file`. La storia delle versioni è esplicita e tracciabile.
* **`is_principale` bloccato in UPDATE**: insieme all'indice unique parziale `uq_documenti_generati_file_principale` (un solo principale per documento) e al vincolo `uq_documenti_generati_file_doc_tipo_ord`, garantisce che la designazione del principale sia stabile e univoca.

## Dipendenze

* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.documenti_generati_file`](/dbzero/documenti/tabelle/documenti_generati_file)
* [`documenti.documenti_generati`](/dbzero/documenti/tabelle/documenti_generati)
* [`trgfn_documenti_generati_protect_snapshot`](trgfn_documenti_generati_protect_snapshot.md) — guard A7 (controparte sul documento)
* [`trgfn_documenti_generati_block_delete`](trgfn_documenti_generati_block_delete.md) — guard A5
* [Sviluppo Documenti — Piano DB §13.3 A7-bis, sezione C](/dev/work-in-progress/sviluppo-documenti-db)
