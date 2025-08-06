{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_billing_account_ins_upd_clean_fields.md" %}
# ⚙️ Funzione `trgfn_billing_account_ins_upd_clean_fields`

```sql
CREATE FUNCTION trgfn_billing_account_ins_upd_clean_fields()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_billing_account_ins_upd_clean_fields()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
 DECLARE
   cf_child text;
   cf_parent text;
 BEGIN
   
   -- ====================================================================
       -- 0) Validazioni
   -- ====================================================================
       -- 0.1) Se account_code presente, deve esserci valid_from
       IF NEW.parent_account_id IS NOT NULL THEN

        -- 0.1.1) Se parent_account_id non è null, valid_from deve esserci
         IF NEW.valid_from IS NULL THEN
           PERFORM script.fn_log_and_raise_error(
             'database',
             TG_NAME,
             'E_VALORE_MANCANTE',
             jsonb_build_object(
               'account_code', NEW.account_code,
               'column', 'valid_from'
             ),
             NULL::uuid,
              'valid_from'
           );
         END IF;
           -- --------------------------------------------------------
          -- 0.1.2) Identificativi fiscali padri e figli devono corrispondere
          -- ---------------------------------------------------------
             
          -- recupera id fiscali del figlio
           SELECT s.id_fiscale_univoco_cf_piva
             INTO cf_child
             FROM anagrafiche.istanze_utilities iu
             JOIN anagrafiche.soggetti s ON iu.soggetto_id = s.id
           WHERE iu.id = NEW.istanza_utility_id;

           -- recupera id fiscali del parent
           SELECT s2.id_fiscale_univoco_cf_piva
             INTO cf_parent
             FROM anagrafiche.billing_account ba
             JOIN anagrafiche.istanze_utilities iu2 ON ba.istanza_utility_id = iu2.id
             JOIN anagrafiche.soggetti s2 ON iu2.soggetto_id = s2.id
           WHERE ba.id = NEW.parent_account_id;

           IF cf_child IS DISTINCT FROM cf_parent THEN
             -- Log e raise error se i CF non corrispondono
             PERFORM script.fn_log_and_raise_error(
             'database',
             TG_NAME,
             'E_ID_FISCALI_DIVERSI',
             jsonb_build_object(
               'account_code', NEW.account_code,
               'parent_account_id', NEW.parent_account_id,
               'id_fiscale_univoco_cf_piva', cf_child,
               'parent_id_fiscale_univoco_cf_piva', cf_parent
             ),
             NULL::uuid,
              NEW.parent_account_id::text, cf_child, cf_parent
             );  
           END IF;

       END IF;

       -- 0.2) Se valid_to valorizzato, valid_from deve esserci e valid_to>valid_from
       IF NEW.valid_to IS NOT NULL THEN
         IF NEW.valid_from IS NULL THEN
           PERFORM script.fn_log_and_raise_error(
             'database',
             TG_NAME,
             'E_VALORE_MANCANTE',
             jsonb_build_object(
               'account_code', NEW.account_code,
               'column', 'valid_to'
             ),
             NULL::uuid,
              'valid_to'
           );
         ELSIF NEW.valid_to <= NEW.valid_from THEN
           PERFORM script.fn_log_and_raise_error(
             'database',
             TG_NAME,
             'E_DATA_FINE_NON_MAGGIORE_DI_INIZIO',
             jsonb_build_object(
               'valid_from', NEW.valid_from,
               'valid_to',  NEW.valid_to
             ),
             NULL::uuid,
               NEW.valid_to::text, NEW.valid_from::text 
           );
         END IF;
       END IF;



   ----------------------------------------------------------------
   -- 1) Generazione codice automatico
   IF NEW.account_code IS NULL THEN
     NEW.account_code := script.fn_generate_codice('billing_account');
   END IF;

   ------------------------------------------------------------------
   RETURN NEW;
 END;
 $function$
```
---
{% include-markdown "signature-core.md" %}
