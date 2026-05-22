# trgfn_template_documenti_versioni_protect_pubblicata

### Scopo

Trigger function `BEFORE UPDATE OF ...` su `documenti.template_documenti_versioni` che impone l'**immutabilità delle versioni `PUBBLICATA`** (guard **A1** del piano Fase A documenti).

Una versione pubblicata è il contenuto renderizzabile autoritativo del template: se cambiasse silenziosamente, tutti i `documenti_generati` che la referenziano (via `template_versione_id`) avrebbero un `template_hash` non più verificabile contro il template attuale, e l'audit della generazione perderebbe valore.

Per modificare una versione pubblicata si crea sempre una **nuova `BOZZA`** e la si pubblica a sua volta (l'anti-overlap GIST sulle versioni `PUBBLICATA` attive gestisce la transizione).

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_template_documenti_versioni_a10_protect_pubblicata_upd
BEFORE UPDATE OF
    html_template, css_template, markdown_template,
    render_engine_id, formato_template,
    page_format, page_orientation,
    margin_top_mm, margin_right_mm, margin_bottom_mm, margin_left_mm,
    valido_dal, valido_al,
    context_schema,
    template_documento_id, versione
ON documenti.template_documenti_versioni
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_template_documenti_versioni_protect_pubblicata();
```

* **Fase**: `a10` (guard fail-fast, prima dei trigger di automazione `z90` storico/audit).
* **`UPDATE OF` mirato**: il trigger non scatta su modifiche di `stato`, `meta`, `attivo`, `data_update`, `user_update`, `tx_id` — colonne che hanno volutamente un proprio ciclo di vita anche su righe `PUBBLICATA` (es. obsolescenza, audit incrementale).

## Logica

1. Se `OLD.stato = 'PUBBLICATA'`, l'`UPDATE` è bloccato sollevando `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` con dettaglio `template_documento_id`, `versione`, `stato`.
2. Per qualsiasi altro stato (`BOZZA`, `OBSOLETA`) l'`UPDATE` passa.

## Codice errore

| Codice                                          | HTTP | Messaggio                                                                                                  |
| ----------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------- |
| `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE`    | 409  | Versione template PUBBLICATA: contenuti, finestra di validità e parametri di rendering non modificabili.    |

Il messaggio è centralizzato in `config.messaggi_errore` (id 410, vedi cliente CSV `messaggi_errore.csv`).

## Caratteristiche

* **Single-purpose**: si occupa solo dell'immutabilità contenutistica della versione pubblicata. Non gestisce delete (vedi **A2** [`trgfn_template_documenti_versioni_block_delete`](trgfn_template_documenti_versioni_block_delete.md)) né anti-overlap (vincolo `EXCLUDE USING gist` sulla tabella).
* **Granularità tramite `UPDATE OF`**: lo `stato` resta modificabile (es. `PUBBLICATA → OBSOLETA` quando arriva una nuova versione), così come `meta` e flag tecnici. Questo è il pattern preferito al `WHEN (OLD.* IS DISTINCT FROM NEW.*)` perché chiarisce direttamente nel `CREATE TRIGGER` quali colonne sono protette.
* **Coerenza con storico standard**: questa tabella ha storico standard attivo (`storicizza`), quindi ogni transizione di `stato` è comunque tracciata.

## Dipendenze

* `script.fn_log_and_raise_error` — sollevamento errore localizzato con DETAIL/HINT.
* `config.messaggi_errore` — messaggio i18n del codice errore.

## Vedi anche

* [`documenti.template_documenti_versioni`](/dbzero/documenti/tabelle/template_documenti_versioni) — tabella protetta
* [`trgfn_template_documenti_versioni_block_delete`](trgfn_template_documenti_versioni_block_delete.md) — guard A2 (delete block correlato)
* [Sviluppo Documenti — Piano DB §6.3, §13.3 A1](/dev/work-done/sviluppo-documenti-db)
