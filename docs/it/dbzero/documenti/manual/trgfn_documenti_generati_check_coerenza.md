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
3. Chiede a `documenti.fn_template_motivo_non_coerente` se il modello va bene per il documento:
   stessa sorgente, stesso tipo di output, e la stessa azienda **oppure** un modello standard
   (lo standard vale per tutte). È la stessa domanda che `fn_risolvi_template_applicabile` fa sul
   modello indicato prima del render: la regola sta in un punto solo (rev 21-10-2026, §10.3 K-4).
4. Un'incoerenza solleva `E_DOCUMENTI_GENERATO_COERENZA`. Per la regola 1 il contesto porta il
   modello atteso e quello fornito; per le altre il **motivo** per nome (`SORGENTE`, `TIPO`,
   `EMITTENTE`) e i valori del documento. Se più regole falliscono, il motivo è il primo
   nell'ordine del BB (sorgente, tipo, azienda).

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
* [Sviluppo Documenti — Piano DB §6.5, §13.3 A6](/dev/work-done/sviluppo-documenti-db)
