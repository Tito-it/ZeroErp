# trgfn_template_asset_block_delete

### Scopo

Trigger function `BEFORE DELETE` su `documenti.template_asset` che blocca **sempre** la cancellazione fisica di un asset (guard **A3** del piano Fase A documenti).

Gli asset (loghi, firme, immagini, PDF di rifermento, CSS) sono unità immutabili identificate dalla coppia `(emittente_fiscale_id, sha256)`: una volta caricati, partecipano a ogni `documenti_generati` che li ha usati nel render del PDF finale. Cancellarli romperebbe l'audit binario: il pdf storico non sarebbe più riproducibile partendo dagli stessi asset.

Per "ritirare" un asset si chiude la sua finestra temporale (`valido_al`); il record resta indefinitamente.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_template_asset_a10_block_delete_dlt
BEFORE DELETE ON documenti.template_asset
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_template_asset_block_delete();
```

* **Fase**: `a10` (guard fail-fast).
* **Comportamento**: incondizionato — non distingue tra asset attivi, scaduti, o referenziati. La policy è "zero delete fisico, sempre".

## Logica

1. Solleva sempre `E_DOCUMENTI_ASSET_DELETE_BLOCKED` con dettaglio `template_asset_id`, `emittente_fiscale_id`, `codice_interno`.
2. Il `RETURN OLD` è puramente formale: il `RAISE EXCEPTION` di `script.fn_log_and_raise_error` interrompe la transazione prima.

## Codice errore

| Codice                              | HTTP | Messaggio                                                                                |
| ----------------------------------- | ---- | ---------------------------------------------------------------------------------------- |
| `E_DOCUMENTI_ASSET_DELETE_BLOCKED`  | 409  | Asset documentale non cancellabile: usare `valido_al` per chiuderne la finestra di validità. |

Messaggio in `config.messaggi_errore` (id 412).

## Caratteristiche

* **Policy assoluta**: nessun parametro, nessun override. Se un asset deve davvero sparire (caso eccezionale di dato sensibile inserito per errore), serve un cleanup manuale fuori dal ciclo applicativo (es. patch SQL ad-hoc con disabling temporaneo del trigger).
* **No FK figli da consultare**: `documenti_generati_file` non ha FK diretta verso `template_asset` (gli asset partecipano via render, non via riferimento esplicito). Il trigger è quindi cheap: niente count su altre tabelle.
* **Coerenza con la decisione 48** del WIP: "il file non si sostituisce; si carica un nuovo asset". Questa decisione rende A4 (immutabilità file) condizione necessaria insieme a A3.

## Dipendenze

* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.template_asset`](/dbzero/documenti/tabelle/template_asset)
* [`trgfn_template_asset_protect_file`](trgfn_template_asset_protect_file.md) — guard A4 (immutabilità file su UPDATE)
* [Sviluppo Documenti — Piano DB §6.4, §13.3 A3](/dev/work-in-progress/sviluppo-documenti-db)
