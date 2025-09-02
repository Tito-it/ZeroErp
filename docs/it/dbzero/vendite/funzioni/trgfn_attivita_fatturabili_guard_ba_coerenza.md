# ⚙️ Funzione `trgfn_attivita_fatturabili_guard_ba_coerenza`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_guard_ba_coerenza()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
   DECLARE v_iu_id INTEGER;
   BEGIN
    
   
     IF NEW.billing_account_id IS NOT NULL THEN
       SELECT b.istanza_utility_id
         INTO v_iu_id
       FROM anagrafiche.billing_account b
       WHERE b.id = NEW.billing_account_id;

       IF NOT FOUND THEN
           PERFORM script.fn_log_and_raise_error(
           'database',
           'attivita_fatturabili',
           'E_PARAMETRI_TABELLA',
           jsonb_build_object(
             'context','validazione billing_account_id',
             'billing_account_id', NEW.billing_account_id     
           ),
         NULL::uuid,
         'billing_account', NEW.billing_account_id
         );
       END IF;
       IF NEW.istanza_utility_id IS DISTINCT FROM v_iu_id THEN
        
           
            PERFORM script.fn_log_and_raise_error(
           'database',
           'attivita_fatturabili',
           'E_COERENZA_ID',
           jsonb_build_object(
             'context','validazione istanza_utility_id',
             'istanza_utility_id', NEW.istanza_utility_id,
             'billing_account_id',v_iu_id
           ),
         NULL::uuid,
         'istanza_utility_id', NEW.istanza_utility_id,
         'billing_account', NEW.billing_account_id
         );

       END IF;
     END IF;
     RETURN NEW;
 END$function$
```

---
{% include-markdown "signature-core.md" %}
