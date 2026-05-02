# trgfn_istanze_utilities_require_utility_dichiarata

### Scopo

Constraint trigger function `AFTER INSERT DEFERRABLE INITIALLY DEFERRED` su `anagrafiche.istanze_utilities` che implementa la **Strategia C** del refactor preventivi (sessione 2026-05-01):

> Ogni nuova `istanze_utilities` deve avere **almeno 1 satellite** (`billing_account`, `istanze_dati_precontrattuali`, `clienti`) che dichiari la utility associata, entro la transazione di creazione.

La validazione e' deferred: avviene al `COMMIT`, quindi e' lecito creare l'istanza prima del satellite all'interno della stessa transazione (caso d'uso normale: `INSERT istanza` + `INSERT BA` in atomic).

## Schema

`anagrafiche`

## Trigger associato

```sql
CREATE CONSTRAINT TRIGGER trg_istanze_utilities_z90_require_utility_dichiarata_ins
  AFTER INSERT ON anagrafiche.istanze_utilities
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW
  EXECUTE FUNCTION anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata();
```

* **Fase**: `z90` (final/deferrable, per convention `linee-guida-trigger.md`)
* **Solo INSERT**: si applica alle nuove istanze. Le istanze storiche orfane non sono toccate.

## Logica

1. Per ogni riga inserita (`NEW.id`), al COMMIT verifica `EXISTS` su:
   * `anagrafiche.billing_account WHERE istanza_utility_id = NEW.id`
   * `anagrafiche.istanze_dati_precontrattuali WHERE istanza_utility_id = NEW.id`
   * `anagrafiche.clienti WHERE istanza_utility_id = NEW.id`
2. Se nessuna delle 3 fonti ha riga matching → solleva `E_ISTANZA_UTILITY_SENZA_UTILITY` con `script.fn_log_and_raise_error`.
3. Se almeno una matcha → `RETURN NULL` (constraint trigger).

## Codice errore

| Codice                            | HTTP | Messaggio (CSV)                                                                                                  |
| --------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------- |
| `E_ISTANZA_UTILITY_SENZA_UTILITY` | 409  | Istanza utility senza utility dichiarata: serve almeno un riferimento (billing_account, dati precontrattuali, cliente). %s |

L'ultimo argomento del raise (`%s`) contiene il context diagnostico (`istanza_utility_id=<id>`).

## Allineamento con `script.fn_check_utility_istanza_coerenza`

La lista delle 3 fonti satellite (BA, IDP, clienti) **deve restare allineata** a `script.fn_check_utility_istanza_coerenza`. Se una delle due cambia (es. si aggiunge una nuova fonte), aggiornare anche l'altra. Vedi cross-link nelle dipendenze.

## Backfill istanze orfane storiche

Il trigger e' `AFTER INSERT`: si applica solo alle nuove istanze. Le istanze storiche con zero satelliti restano e vanno valutate manualmente. Il backfill in `migrations_v2/80_data/changelog/20260501-16-backfill-istanze-dati-precontrattuali` crea una riga `istanze_dati_precontrattuali` per le istanze che hanno gia' un BA ma nessuna IDP.

## Caratteristiche

* **Constraint trigger DEFERRABLE INITIALLY DEFERRED**: la validazione avviene al COMMIT, non a INSERT-time.
* **Idempotente nella creazione**: la migration usa `DROP TRIGGER IF EXISTS` + `CREATE CONSTRAINT TRIGGER` con `runOnChange: true`.
* **Forzabile a IMMEDIATE**: in test pgTAP si usa `SET CONSTRAINTS ALL IMMEDIATE` per forzare la valutazione anticipata (il `COMMIT` reale non e' raggiungibile dentro `BEGIN; ... ROLLBACK`).

## Dipendenze

* `script.fn_log_and_raise_error`
* Tabelle satellite: `anagrafiche.billing_account`, `anagrafiche.istanze_dati_precontrattuali`, `anagrafiche.clienti`

## Vedi anche

* [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza) — fn riusabile cross-tabella allineata alle stesse 3 fonti
* [`vendite.trgfn_preventivi_guard_utility_istanza_coerenza`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_utility_istanza_coerenza) — guard sui preventivi che usa la fn check
* [Guida: Gestione delle istanze utility — sezione "Strategia C"](/it/guide/gestione-delle-istanze-utility#strategia-c--ogni-istanza-dichiara-la-utility-tramite-un-satellite-2026-05-01)
* Brief sessione 2026-05-01: `docs/it/dev/work-in-progress/risposta-db-brief-preventivi-rev2.md`
