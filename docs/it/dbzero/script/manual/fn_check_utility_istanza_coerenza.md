# fn_check_utility_istanza_coerenza

### Scopo

Pure check (boolean, no raise) riusabile cross-tabella per validare la coppia `(istanza_utility_id, utility_id)` come **coerente**, ovvero dichiarata da almeno una delle 3 fonti satellite riconosciute dal modello istanze utility.

Introdotta nel refactor preventivi 2026-05-01 (sessione brief preventivi rev2). Riusabile da qualsiasi tabella vendite/acquisti che abbia la coppia `(istanza, utility)`.

## Schema

`script` (la convention progetto colloca in `script` le funzioni riusabili cross-dominio).

## Firma

```sql
script.fn_check_utility_istanza_coerenza(
    p_istanza_utility_id  anagrafiche.istanze_utilities.id%TYPE,
    p_utility_id          config.utilities.id%TYPE
) RETURNS boolean
LANGUAGE plpgsql STABLE
```

## Logica

Ritorna `true` se esiste almeno una riga matching la coppia in:

1. `anagrafiche.billing_account` (UNIQUE `uq_billing_instance_utility (istanza_utility_id, utility_id)`)
2. `anagrafiche.istanze_dati_precontrattuali` (UNIQUE `uq_istanze_dati_precontrattuali_id_utility_id`)
3. `anagrafiche.clienti` (entrambe le colonne presenti, 1:1 cliente↔istanza)

Ritorna `false` se:

* `p_istanza_utility_id` o `p_utility_id` sono `NULL` (guard input)
* Nessuna delle 3 fonti ha riga matching

## Convenzione naming

* `fn_check_*` → pure check, no raise (questa)
* `fn_guard_*` → fail-fast, puo' sollevare

Per usi che richiedono raise (es. trigger guard), il caller wrappa la fn in un `IF NOT script.fn_check_...() THEN PERFORM script.fn_log_and_raise_error(...) END IF`.

## Performance

`STABLE` + 3 lookup su indici UNIQUE: O(log n) per ognuno, complessivamente O(log n) per chiamata. Sicura da chiamare in trigger BEFORE INSERT/UPDATE.

## Allineamento con `trgfn_istanze_utilities_require_utility_dichiarata`

La lista delle 3 fonti satellite **deve restare identica** al constraint trigger su `istanze_utilities`. Se cambia una delle due (es. si aggiunge una nuova fonte come `commesse_attivita`), aggiornare entrambe in coordinamento.

## Esempio d'uso (in trigger guard)

```sql
IF NOT script.fn_check_utility_istanza_coerenza(
       NEW.istanza_utility_id,
       NEW.utility_id
   ) THEN
  PERFORM script.fn_log_and_raise_error(
    'vendite', 'trgfn_<tabella>_guard_utility_istanza_coerenza',
    'E_<DOM>_UTILITY_ISTANZA_INCOERENTE',
    jsonb_build_object(
      'istanza_utility_id', NEW.istanza_utility_id,
      'utility_id',         NEW.utility_id
    ),
    NULL::uuid,
    concat('istanza_utility_id=', NEW.istanza_utility_id::text,
           ', utility_id=', NEW.utility_id::text)
  );
END IF;
```

## Caller attuali

* [`vendite.trgfn_preventivi_guard_utility_istanza_coerenza`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_utility_istanza_coerenza)

## Caller candidati futuri

* `vendite.attivita_fatturabili` (se non gia' coperto da altra coerenza)
* `vendite.commesse_attivita`
* `vendite.ddt`, `vendite.fatture` (se hanno la coppia)
* Qualsiasi nuova tabella con coppia `(istanza_utility_id, utility_id)` come perimetro

## Dipendenze

Nessuna fn esterna. Solo lookup su tabelle satellite.

## Vedi anche

* [`anagrafiche.trgfn_istanze_utilities_require_utility_dichiarata`](/dbzero/anagrafiche/funzioni/trgfn_istanze_utilities_require_utility_dichiarata) — constraint trigger gemello (stesse 3 fonti)
* [`vendite.trgfn_preventivi_guard_utility_istanza_coerenza`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_utility_istanza_coerenza) — primo caller
* [Guida: Gestione delle istanze utility — sezione "Strategia C"](/it/guide/gestione-delle-istanze-utility#strategia-c--ogni-istanza-dichiara-la-utility-tramite-un-satellite-2026-05-01)
