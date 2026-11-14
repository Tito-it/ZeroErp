# trgfn_template_documenti_versioni_protect_pubblicata

### Scopo

(latest review 14-11-2026 — anche le `OBSOLETA`, e lo stato non torna indietro: `20261114-04`)

Trigger function `BEFORE UPDATE OF ...` su `documenti.template_documenti_versioni` che impone
l'**immutabilità delle versioni fuori bozza**, `PUBBLICATA` e `OBSOLETA` (guard **A1** del piano
Fase A documenti).

Una versione fuori bozza è il contenuto renderizzabile autoritativo del template: se cambiasse
silenziosamente, tutti i `documenti_generati` che la referenziano (via `template_versione_id`)
avrebbero un `template_hash` non più verificabile contro il template attuale, e l'audit della
generazione perderebbe valore. Vale anche per una versione **superata**: una `OBSOLETA` stampa
fino all'ultimo giorno della sua validità
([vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili)), e la
ristampa fedele dei documenti già generati la rilegge.

Per modificare una versione si crea sempre una **nuova `BOZZA`** e la si pubblica a sua volta.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_template_documenti_versioni_a10_protect_pubblicata_upd
BEFORE UPDATE OF
    html_template, css_template, markdown_template, render_engine_id,
    formato_template, page_format, page_orientation,
    margin_top_mm, margin_right_mm, margin_bottom_mm, margin_left_mm,
    valido_dal, valido_al, context_schema, versione_contesto,
    template_documento_id, versione, stato
ON documenti.template_documenti_versioni
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_template_documenti_versioni_protect_pubblicata();
```

* **`versione_contesto`** è nell'elenco dal 30-09-2026: la forma dei dati che la versione legge fa
  parte del patto controllato alla pubblicazione, e dopo non si cambia.
* **`stato`** è nell'elenco dal 14-11-2026: fuori bozza lo stato non torna indietro. Prima un
  `UPDATE` del solo stato riportava una versione pubblicata in `BOZZA`, e da lì si modificava tutto.
* **Fase**: `a10` (guard fail-fast, prima dei trigger di automazione `z90` storico/audit).
* **Fuori dall'elenco**: `titolo`, `meta`, `attivo`, `derivata_da_versione_id` (ha il suo guard),
  `data_update`, `user_update`, `tx_id`. Spegnere una versione (`attivo = false`) resta possibile.

## Logica

1. Se `OLD.stato` è `BOZZA`, l'`UPDATE` passa.
2. Se `OLD.stato` è `PUBBLICATA` o `OBSOLETA`, l'`UPDATE` è bloccato con
   `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` (dettaglio `template_documento_id`, `versione`,
   `stato`, `stato_nuovo`), **salvo un caso solo**: la chiusura che fa
   [`fn_pubblica_template_documento_versione`](/dbzero/documenti/funzioni/fn_pubblica_template_documento_versione)
   quando pubblica la versione successiva. Passa se tutte queste condizioni valgono insieme:
   * la porta `zeroerp.allow_template_versione_chiusura_override` è `'on'`;
   * lo stato va da `PUBBLICATA` a `OBSOLETA`;
   * `valido_al` diventa una data, uguale o precedente a quella di prima (la validità si accorcia);
   * ogni altra colonna protetta resta com'era.

## La porta della chiusura

La funzione di pubblicazione apre la porta (`set_config(…, 'on', true)`, cioè `SET LOCAL`) dopo
aver scelto le versioni da chiudere, le chiude con **una scrittura sola** (stato e data insieme), e
la richiude subito. Nessun'altra scrittura della transazione la trova aperta, e anche aperta la
porta ammette solo la forma della chiusura: un `UPDATE` che a porta aperta cambia anche l'HTML è
rifiutato. La porta protegge da un backend che sbaglia, non da uno manomesso: chi apre la porta a
mano può chiudere una versione, ma non modificarla.

## Codice errore

| Codice | HTTP | Messaggio |
| --- | --- | --- |
| `E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE` | 409 | Una versione pubblicata di un template documentale non può essere modificata, nemmeno quando è superata da una versione successiva. |

Il messaggio è centralizzato in `config.messaggi_errore` (id 410, CSV `messaggi_errore.csv`).

## Caratteristiche

* **Single-purpose**: si occupa solo dell'immutabilità della versione fuori bozza. Non gestisce
  delete (vedi **A2**
  [`trgfn_template_documenti_versioni_block_delete`](trgfn_template_documenti_versioni_block_delete.md))
  né anti-overlap (vincolo `EXCLUDE USING gist` sulla tabella).
* **`UPDATE OF` mirato**: scatta anche a valore uguale (`SET colonna = <stesso valore>`), quindi un
  salvataggio che riscrive tutta la riga di una versione fuori bozza è rifiutato. Nessun altro
  trigger `BEFORE` della tabella scrive le colonne dell'elenco: `OF` è la forma giusta (linee guida
  trigger, «`UPDATE` o `UPDATE OF colonna`»).
* **Coerenza con storico standard**: questa tabella ha storico standard attivo (`storicizza`),
  quindi ogni transizione di `stato` è comunque tracciata.

## Verifica

`db/pgtap/documenti/test-fn-pubblica-template-documento-versione-v1.sql`, test 18-23: una
`OBSOLETA` non si modifica e non torna in bozza, una `PUBBLICATA` non torna in bozza, la porta è
richiusa dopo la pubblicazione, senza porta una `PUBBLICATA` non si chiude a mano, a porta aperta
passa solo la chiusura. I test 4-7 e 14 provano che la pubblicazione chiude come prima.
`db/pgtap/documenti/test-documenti-template-versioni.sql` copre il caso `PUBBLICATA` di origine.

## Dipendenze

* `script.fn_log_and_raise_error` — sollevamento errore localizzato con DETAIL/HINT.
* `config.messaggi_errore` — messaggio i18n del codice errore.

## Vedi anche

* [`documenti.template_documenti_versioni`](/dbzero/documenti/tabelle/template_documenti_versioni) — tabella protetta
* [`trgfn_template_documenti_versioni_block_delete`](trgfn_template_documenti_versioni_block_delete.md) — guard A2 (delete block correlato)
* [Sviluppo Documenti — Piano DB §6.3, §13.3 A1](/dev/work-done/sviluppo-documenti-db)
