# trgfn_preventivi_guard_utility_istanza_coerenza

### Scopo

Trigger function `BEFORE INSERT OR UPDATE OF (istanza_utility_id, utility_id)` su `vendite.preventivi` che valida la coerenza della coppia `(istanza_utility_id, utility_id)` delegando il check a [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza).

Solleva `E_PREV_UTILITY_ISTANZA_INCOERENTE` se la coppia non e' dichiarata da nessuna fonte satellite (BA, IDP, clienti).

Aggiunto nel refactor preventivi 2026-05-01: prima non c'era nessun trigger/CHECK che impedisse il salvataggio di un preventivo con `utility_id` non coerente con `istanza_utility_id`.

## Schema

`vendite`

## Trigger associato

```sql
CREATE TRIGGER trg_preventivi_a10_guard_utility_istanza_coerenza_ins_upd
  BEFORE INSERT OR UPDATE OF istanza_utility_id, utility_id
  ON vendite.preventivi
  FOR EACH ROW
  EXECUTE FUNCTION vendite.trgfn_preventivi_guard_utility_istanza_coerenza();
```

* **Fase**: `a10_guard_*` (ordina alfabeticamente DOPO `a10_default_*` → fires dopo `trgfn_preventivi_default_emittente`)
* **Eventi**:
    * `INSERT`: sempre validato
    * `UPDATE`: solo se cambiano `istanza_utility_id` o `utility_id` (clausola `UPDATE OF`)
* Le UPDATE su altri campi (es. totali, validita, stato) non scattano il trigger.

## Logica

1. Skip se `NEW.istanza_utility_id IS NULL` (safety net pre-rollout NOT NULL).
2. Chiama `script.fn_check_utility_istanza_coerenza(NEW.istanza_utility_id, NEW.utility_id)`.
3. Se ritorna `false` → solleva `E_PREV_UTILITY_ISTANZA_INCOERENTE` con context diagnostico.
4. Se ritorna `true` → `RETURN NEW`.

## Codice errore

| Codice                              | HTTP | Messaggio (CSV)                                              |
| ----------------------------------- | ---- | ------------------------------------------------------------ |
| `E_PREV_UTILITY_ISTANZA_INCOERENTE` | 409  | Utility non coerente con l'istanza selezionata. %s           |

L'`%s` finale contiene il context: `'istanza_utility_id=<id>, utility_id=<id>'`.

## Coerenza = una di queste 3 fonti dichiara la coppia

* `anagrafiche.billing_account` (UNIQUE su istanza+utility)
* `anagrafiche.istanze_dati_precontrattuali` (UNIQUE su istanza+utility)
* `anagrafiche.clienti` (1:1 cliente↔istanza, con colonna utility_id)

La verifica e' delegata a [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza), che e' allineata al constraint trigger su `istanze_utilities` ([`trgfn_istanze_utilities_require_utility_dichiarata`](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata)).

## Casi tipici

| Scenario                                                       | Esito          |
| -------------------------------------------------------------- | -------------- |
| Preventivo prospect (no BA), istanza ha IDP con utility=GAS, payload utility=GAS | OK             |
| Preventivo con BA gia' creato, BA dichiara coppia (istanza, GAS), payload utility=GAS | OK             |
| Preventivo prospect, istanza ha IDP utility=GAS, payload utility=ELETTRICITA | RAISE          |
| Preventivo cliente non-utility (commercio), istanza ha cliente.utility_id=GENERICO, payload utility=GENERICO | OK             |

## Caratteristiche

* **Trigger thin**: solo wrapping del pure check `fn_check_utility_istanza_coerenza`. La logica di coerenza vera e' centralizzata in `script`.
* **UPDATE OF specifico**: zero overhead se cambiano altri campi del preventivo.
* **Idempotente**: `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER` con `runOnChange: true`.

## Dipendenze

* [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza)
* `script.fn_log_and_raise_error`
* Codice CSV `messaggi_errore.E_PREV_UTILITY_ISTANZA_INCOERENTE`

## Edge case noto

Se viene cancellato l'unica fonte satellite di una coppia gia' usata in un preventivo (es. DELETE del BA che la dichiarava), il preventivo esistente non e' rivalutato. Tracciato come issue futura nel brief sessione 2026-05-01 (§4.2 risposta DB).

## Vedi anche

* [`vendite.trgfn_preventivi_default_emittente`](/dbzero/vendite/funzioni/trgfn_preventivi_default_emittente) — trigger fase `a10_default` che fires PRIMA di questo
* [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza) — pure check usato qui
* [`anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata`](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata) — constraint trigger gemello (stesse 3 fonti)
* [Tabella vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — sezione "Modello istanza/BA/emittente"
