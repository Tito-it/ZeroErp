{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_sepa_mandati_guard.md" %}
# ⚙️ Funzione `trgfn_sepa_mandati_guard`

```sql
CREATE FUNCTION trgfn_sepa_mandati_guard()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_sepa_mandati_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN

  /*
    Guard trigger per pagamenti.sepa_mandati.

    Responsabilità
    --------------
    1) Validazione di coerenza stato/dati:
      - se NEW.stato = 'ATTIVO' allora NEW.data_attivazione deve essere valorizzata.
      - in caso contrario genera errore applicativo (vincolo logico / check-like).

    2) Normalizzazione campi testuali (pre-insert / pre-update):
      - UMR: rimuove tutti gli spazi (whitespace) per garantire confronto e univocità consistenti.
      - IBAN snapshot: rimuove whitespace e forza uppercase (standard IBAN).

    Note tecniche
    ------------
    - Trigger tipicamente da usare BEFORE INSERT OR UPDATE, così può modificare NEW.
  */


  -- Stato ATTIVO richiede data_attivazione
  IF NEW.stato = 'ATTIVO' AND NEW.data_attivazione IS NULL THEN
    PERFORM anagrafiche.fn_log_and_raise_error(
                        'database',
                        'trgfn_sepa_mandati_guard',
                        'E_DATA_ERRATA',
                        jsonb_build_object(
                          'tabella','pagamenti.sepa_mandati',
                          'data_attivazione',  0,
                          'error', SQLERRM
                        ) , NULL::uuid, 'data attivazione per stato ATTIVO'
                      ); 
  END IF;

  -- Normalizzazione UMR e IBAN snapshot
  IF NEW.umr IS NOT NULL THEN
    NEW.umr := regexp_replace(NEW.umr, '\s+', '', 'g');
  END IF;
  IF NEW.iban_snapshot IS NOT NULL THEN
    NEW.iban_snapshot := upper(regexp_replace(NEW.iban_snapshot, '\s+', '', 'g'));
  END IF;

  RETURN NEW;
END
$function$
```

---
{% include-markdown "signature-core.md" %}
