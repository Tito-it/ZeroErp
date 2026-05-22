# trgfn_template_documenti_versioni_block_delete

### Scopo

Trigger function `BEFORE DELETE` su `documenti.template_documenti_versioni` che blocca la **cancellazione fisica** delle versioni template in due casi (guard **A2** del piano Fase A documenti):

1. la versione è in stato `PUBBLICATA` o `OBSOLETA` (la storia delle pubblicazioni va preservata);
2. la versione è già stata utilizzata da almeno un `documenti_generati` (integrità referenziale storica del documento prodotto).

Solo le versioni `BOZZA` non ancora referenziate possono essere cancellate fisicamente — caso tipico: bozza creata per errore, ancora non pubblicata né renderizzata.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_template_documenti_versioni_a10_block_delete_protected_dlt
BEFORE DELETE ON documenti.template_documenti_versioni
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_template_documenti_versioni_block_delete();
```

* **Fase**: `a10` (guard fail-fast).

## Logica

1. Se `OLD.stato IN ('PUBBLICATA', 'OBSOLETA')`: solleva `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED` con dettaglio `template_documento_id`, `versione`, `stato`.
2. Conta le righe in `documenti.documenti_generati` con `template_versione_id = OLD.id`.
3. Se il conteggio è > 0: solleva `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED` con dettaglio `template_documento_id`, `versione`, `documento_generati_count`.
4. Altrimenti la `DELETE` procede.

## Codice errore

| Codice                                  | HTTP | Messaggio                                                                                          |
| --------------------------------------- | ---- | -------------------------------------------------------------------------------------------------- |
| `E_DOCUMENTI_VERSIONE_DELETE_BLOCKED`   | 409  | Versione template non cancellabile: stato protetto (PUBBLICATA/OBSOLETA) o già usata da documenti. |

Messaggio in `config.messaggi_errore` (id 411).

## Caratteristiche

* **Single-purpose**: si occupa solo del delete block. L'immutabilità del contenuto pubblicato è in **A1** [`trgfn_template_documenti_versioni_protect_pubblicata`](trgfn_template_documenti_versioni_protect_pubblicata.md).
* **No `ON DELETE CASCADE`**: il delete block è semantico, non basato su FK. La FK `documenti_generati.template_versione_id → template_documenti_versioni.id` ha `ON DELETE RESTRICT`, ma il check qui è esplicito perché alcune migrazioni passate hanno mostrato che `RESTRICT` non basta a comunicare il messaggio funzionale corretto.
* **Audit naturale**: lo storico standard della tabella mantiene comunque traccia delle versioni `OBSOLETA` se mai si volesse fare archeologia post-hoc.

## Dipendenze

* `documenti.documenti_generati` — lookup `template_versione_id` per il check di utilizzo.
* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.template_documenti_versioni`](/dbzero/documenti/tabelle/template_documenti_versioni)
* [`trgfn_template_documenti_versioni_protect_pubblicata`](trgfn_template_documenti_versioni_protect_pubblicata.md) — guard A1 correlato
* [Sviluppo Documenti — Piano DB §6.3, §13.3 A2](/dev/work-done/sviluppo-documenti-db)
