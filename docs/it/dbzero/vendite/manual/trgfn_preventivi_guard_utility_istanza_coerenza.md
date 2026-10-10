# trgfn_preventivi_guard_utility_istanza_coerenza

### Scopo

Trigger function `BEFORE INSERT OR UPDATE OF (istanza_utility_id, utility_id)` su `vendite.preventivi` che valida la coerenza della coppia `(istanza_utility_id, utility_id)` delegando il check a [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza).

Solleva `E_PREV_UTILITY_ISTANZA_INCOERENTE` se la coppia non ha il suo billing account.

Dal 2026-10-08 il preventivo ha anche la FK composta `fk_preventivi_ba_coppia` (`billing_account_id`, `istanza_utility_id`, `utility_id`): questo guard resta perche' e' `BEFORE ROW` e parla **prima** della FK con un codice leggibile, sul campo `utility_id`. La FK copre il caso che il guard non vede: la coppia ha un BA, ma il preventivo ne nomina un altro.

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

* **Fase**: `a10_guard_*` (ordina alfabeticamente DOPO `a10_default_*` → fires dopo `trg_preventivi_a10_default_emittente_ins`, che dal 2026-09-15 esegue `script.trgfn_default_emittente_fiscale`)
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

## Coerenza = la coppia ha il suo billing account

La verifica e' delegata a [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/manual/fn_check_utility_istanza_coerenza). Fino al 2026-10-08 le fonti erano tre (billing account, dati precontrattuali, cliente); dalla regola «istanza e billing account nascono insieme, per coppia» le altre due implicano il BA, e la fonte e' una.

## Casi tipici

| Scenario                                                       | Esito          |
| -------------------------------------------------------------- | -------------- |
| L'istanza ha il BA della coppia (istanza, GAS), payload utility=GAS | OK             |
| L'istanza ha il BA della coppia (istanza, GAS), payload utility=ELETTRICITA, nessun BA per quella coppia | RAISE          |
| Payload col BA di un'altra coppia | passa il guard, lo rifiuta la FK `fk_preventivi_ba_coppia` |

## Caratteristiche

* **Trigger thin**: solo wrapping del pure check `fn_check_utility_istanza_coerenza`. La logica di coerenza vera e' centralizzata in `script`.
* **UPDATE OF specifico**: zero overhead se cambiano altri campi del preventivo.
* **Idempotente**: `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER` con `runOnChange: true`.

## Dipendenze

* [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza)
* `script.fn_log_and_raise_error`
* Codice CSV `messaggi_errore.E_PREV_UTILITY_ISTANZA_INCOERENTE`

## Edge case chiuso

Fino al 2026-10-08: se si cancellava l'unica fonte di una coppia gia' usata in un preventivo, il preventivo non veniva rivalutato. Ora la fonte e' il billing account, e il preventivo lo nomina con la FK composta: un BA usato da un preventivo non si cancella.

## Vedi anche

* [`script.trgfn_default_emittente_fiscale`](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) — trigger fase `a10_default` che fires PRIMA di questo (fino al 2026-09-15: la copia `trgfn_preventivi_default_emittente`)
* [`script.fn_check_utility_istanza_coerenza`](/dbzero/script/funzioni/fn_check_utility_istanza_coerenza) — pure check usato qui
* [`anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata`](/dbzero/anagrafiche/manual/trgfn_istanze_utilities_require_utility_dichiarata) — l'istanza nasce col suo billing account
* [Tabella vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — sezione "Modello istanza/BA/emittente"
