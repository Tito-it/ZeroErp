# trgfn_template_asset_protect_file

### Scopo

Trigger function `BEFORE UPDATE` su `documenti.template_asset` che blocca la modifica delle colonne **file-specifiche** (guard **A4** del piano Fase A documenti).

Un asset è l'identità persistente di un file binario caricato per un emittente: cambiare in-place `storage_key`, `sha256`, `file_size_bytes`, `mime_type` o `file_name` significherebbe falsare l'identità del file. Tutti i `documenti_generati` che hanno renderizzato un PDF usando quell'asset perderebbero la possibilità di riprodurre lo stesso byte-stream a partire dallo stesso asset.

Pattern alternativo: per cambiare il file si crea un **nuovo asset** (con `codice_interno` distinto o nuova versione), si chiude il vecchio via `valido_al`, e si aggiornano eventualmente i template che lo referenzieranno per i prossimi render.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_template_asset_a10_protect_file_upd
BEFORE UPDATE ON documenti.template_asset
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_template_asset_protect_file();
```

* **Fase**: `a10` (guard fail-fast).
* **Trigger non `UPDATE OF`**: il check è esplicito sui campi nel corpo della funzione. Questo è scelto per chiarezza nei log di errore (il `jsonb_build_object` espone l'asset coinvolto) e per evitare la doppia manutenzione tra clausola `UPDATE OF` e check interno.

## Logica

1. Calcola la condizione `<colonna> NEW != OLD` per: `storage_key`, `sha256`, `file_size_bytes`, `mime_type`, `file_name`.
2. Se almeno una di queste è cambiata, solleva `E_DOCUMENTI_ASSET_FILE_IMMUTABILE` con dettaglio `template_asset_id`, `emittente_fiscale_id`, `codice_interno`.
3. Altrimenti l'`UPDATE` passa: rimangono modificabili `descrizione`, `attivo`, `meta`, `valido_dal`, `valido_al` (la `validita` daterange è ricalcolata da `script.trgfn_set_validita`), audit fields.

## Codice errore

| Codice                              | HTTP | Messaggio                                                                                                |
| ----------------------------------- | ---- | -------------------------------------------------------------------------------------------------------- |
| `E_DOCUMENTI_ASSET_FILE_IMMUTABILE` | 409  | Asset documentale: i campi file (storage_key, sha256, file_size_bytes, mime_type, file_name) sono immutabili. |

Messaggio in `config.messaggi_errore` (id 413).

## Caratteristiche

* **Sempre attivo, anche prima del primo uso**: la policy è "il file non si modifica mai", indipendentemente da quanti `documenti_generati` lo hanno utilizzato. Questo semplifica la regola e rispecchia la decisione 48 del WIP DB.
* **Complemento di A3**: insieme al delete block (A3), garantisce che ogni `template_asset` sia effettivamente un'**istantanea binaria stabile** — sia il record che il file sottostante.
* **Lascia liberi i campi semantici**: `descrizione`, `attivo`, `meta`, `valido_*` cambiano normalmente. Modificare `attivo = false` o impostare `valido_al` è il modo corretto di "ritirare" un asset.

## Dipendenze

* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.template_asset`](/dbzero/documenti/tabelle/template_asset)
* [`trgfn_template_asset_block_delete`](trgfn_template_asset_block_delete.md) — guard A3 (delete block)
* [Sviluppo Documenti — Piano DB §6.4, §13.3 A4, decisione 48](/dev/work-done/sviluppo-documenti-db)
