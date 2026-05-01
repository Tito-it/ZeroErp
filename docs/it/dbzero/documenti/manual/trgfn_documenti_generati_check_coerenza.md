# trgfn_documenti_generati_check_coerenza

### Scopo

Trigger function `BEFORE INSERT OR UPDATE` su `documenti.documenti_generati` che valida la **coerenza referenziale** tra i campi denormalizzati del documento e i corrispondenti valori sul template referenziato (guard **A6** del piano Fase A documenti).

`documenti_generati` denormalizza per audit alcune relazioni che potrebbero in teoria essere ricostruite via join: `tipo_documento_output_id`, `sorgente_tipo_id`, `emittente_fiscale_id`. Questa denormalizzazione è giustificata dall'audit (lo snapshot deve sopravvivere anche a rinominazioni o ristrutturazioni del template), ma introduce un rischio: se i valori dell'istanza sono incoerenti con quelli del template che ha generato il documento, lo `context_json` perde di valore probatorio.

Il guard chiude questo rischio: a ogni INSERT/UPDATE le 4 relazioni devono allinearsi.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_documenti_generati_a10_check_coerenza_ins_upd
BEFORE INSERT OR UPDATE ON documenti.documenti_generati
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_documenti_generati_check_coerenza();
```

* **Fase**: `a10` (guard fail-fast).

## Logica

1. Recupera dal `template_versione_id` indicato la coppia `(template_documento_id, ...derivati...)`.
2. Verifica che `NEW.template_documento_id` coincida con il `template_documento_id` della versione (la versione deve appartenere al template indicato).
3. Verifica che `NEW.tipo_documento_output_id` coincida con il `tipo_documento_output_id` del template.
4. Verifica che `NEW.sorgente_tipo_id` coincida con il `sorgente_tipo_id` del template.
5. Verifica che `NEW.emittente_fiscale_id` coincida con l'`emittente_fiscale_id` del template.
6. La prima incoerenza solleva `E_DOCUMENTI_GENERATO_COERENZA` con il payload del campo non allineato (atteso vs fornito); le altre verifiche non sono raggiunte.

## Codice errore

| Codice                              | HTTP | Messaggio                                                                                                              |
| ----------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------- |
| `E_DOCUMENTI_GENERATO_COERENZA`     | 409  | Documento generato incoerente: tipo, sorgente, emittente o template_versione non allineati con il template referenziato. |

Messaggio in `config.messaggi_errore` (id 415).

## Caratteristiche

* **Service vs DB-first**: la coerenza è già garantita dal `pipeline_runner` lato Django, che costruisce sempre un `documenti_generati` partendo dal template. Questa guard è la rete di sicurezza DB: protegge contro bug di service, query manuali, fixture mal scritte e migrazioni future che bypassino il livello applicativo.
* **Equivalenze, non FK**: Postgres non offre constraint `CHECK` su sub-query referenziali, quindi il controllo è espresso come trigger. La conseguenza è che il check è valutato per ogni riga, ma l'overhead è trascurabile (1 SELECT con FK indicizzata).
* **Niente "auto-fix"**: il trigger non corregge i valori incoerenti — solleva eccezione. Correggere automaticamente nasconderebbe bug di service.

## Dipendenze

* `documenti.template_documenti_versioni` — sorgente del `template_documento_id` atteso.
* `documenti.template_documenti` — sorgente di `tipo_documento_output_id`, `sorgente_tipo_id`, `emittente_fiscale_id` attesi.
* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.documenti_generati`](/dbzero/documenti/tabelle/documenti_generati)
* [`documenti.template_documenti`](/dbzero/documenti/tabelle/template_documenti)
* [`documenti.template_documenti_versioni`](/dbzero/documenti/tabelle/template_documenti_versioni)
* [`trgfn_documenti_generati_block_delete`](trgfn_documenti_generati_block_delete.md) — guard A5
* [`trgfn_documenti_generati_protect_snapshot`](trgfn_documenti_generati_protect_snapshot.md) — guard A7
* [Sviluppo Documenti — Piano DB §6.5, §13.3 A6](/dev/work-in-progress/sviluppo-documenti-db)
