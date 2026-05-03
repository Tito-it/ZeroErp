# trgfn_documenti_generati_eventi_block_update

### Scopo

Trigger function `BEFORE UPDATE` su `documenti.documenti_generati_eventi` che blocca **qualsiasi** modifica su qualsiasi colonna di un evento già registrato.

Una volta inserito, un evento di timeline è definitivo. Nessun campo è modificabile post `INSERT`: né `messaggio`, né `detail`, né `esito`, né `meta`. Anche i campi audit `data_update`/`user_update`, ereditati dal pattern standard del repo, restano valorizzati al solo `INSERT` ma non vengono mai aggiornati (la tabella è essa stessa il log).

Per registrare correzioni successive (es. revisione di un esito, aggiornamento informazioni diagnostiche) si inserisce **un nuovo evento** sullo stesso `documento_generato_id`, tipicamente con `esito='WARN'` e `detail` contenente riferimento all'evento corretto.

## Schema

`documenti`

## Trigger associato

```sql
CREATE TRIGGER trg_documenti_generati_eventi_a10_block_update_upd
BEFORE UPDATE ON documenti.documenti_generati_eventi
FOR EACH ROW
EXECUTE FUNCTION documenti.trgfn_documenti_generati_eventi_block_update();
```

* **Fase**: `a10` (guard fail-fast).
* **Comportamento**: incondizionato — nessuna `UPDATE` è ammessa, indipendentemente dalla colonna.
* **Niente `UPDATE OF colonna`**: la guard si applica a qualsiasi modifica, non a un sottoinsieme.

## Logica

1. Solleva sempre `E_EVENTO_DOCUMENTO_UPDATE_VIETATA` con dettaglio `evento_id`, `documento_generato_id`, `evento_tipo`, `evento_at`.
2. Il `RETURN OLD` è formale: l'eccezione interrompe la transazione.

## Codice errore

| Codice                                  | HTTP | Messaggio                                                                                |
| --------------------------------------- | ---- | ---------------------------------------------------------------------------------------- |
| `E_EVENTO_DOCUMENTO_UPDATE_VIETATA`     | 409  | Eventi documento: la modifica è vietata (timeline append-only).                          |

Messaggio in `config.messaggi_errore` (id 426).

## Caratteristiche

* **Append-only totale**: insieme al guard `block_delete`, garantisce che la sequenza degli eventi sia immutabile. Senza questa guard la "disabilitazione storico" sarebbe un buco di audit (modifiche silenziose senza traccia).
* **No `UPDATE OF`**: la scelta è deliberata. Una semantica del tipo "blocca solo `messaggio`/`detail`" lascerebbe un margine ambiguo (cosa è davvero modificabile?). La regola pulita è: *nulla*.
* **Compatibilità con automazioni `dbops`**: la regola 2 dell'automation (`audit_update`) prova a popolare `data_update`/`user_update` su UPDATE — ma la guard scatta `BEFORE UPDATE`, quindi blocca sempre. In pratica la regola 2 non si attiva mai per questa tabella, ed è il comportamento atteso (la tabella è append-only e i campi audit valgono come timestamp di INSERT).

## Dipendenze

* `script.fn_log_and_raise_error`
* `config.messaggi_errore`

## Vedi anche

* [`documenti.documenti_generati_eventi`](documenti_generati_eventi.md)
* [`trgfn_documenti_generati_eventi_block_delete`](trgfn_documenti_generati_eventi_block_delete.md) — guard append-only complementare (DELETE)
* [`trgfn_documenti_generati_protect_snapshot`](trgfn_documenti_generati_protect_snapshot.md) — guard analogo (immutabilità snapshot) sul padre `documenti_generati`
* [Sviluppo Documenti — §10-bis.5 (anticipo eventi v1)](/dev/work-in-progress/sviluppo-documenti)
