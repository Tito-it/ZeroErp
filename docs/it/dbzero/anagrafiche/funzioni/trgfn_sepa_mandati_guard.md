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
  -- Stato ATTIVO richiede data_attivazione
  IF NEW.stato = 'ATTIVO' AND NEW.data_attivazione IS NULL THEN
    RAISE EXCEPTION 'Mandato ATTIVO senza data_attivazione' USING ERRCODE='23514';
     PERFORM anagrafiche.fn_log_and_raise_error(
                        'database',
                        'trgfn_sepa_mandati_guard',
                        'E_DATA_ATTIVAZIONE_MANDATO',
                        jsonb_build_object(
                          'tabella','pagamenti.sepa_mandati',
                          'data_attivazione',  0,
                          'error', SQLERRM
                        ) , NULL::uuid, NULL
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
END$function$
```

---
{% include-markdown "signature-core.md" %}
