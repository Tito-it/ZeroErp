{% include-markdown "it/dbzero/dbops/manual/trgfn_tx_id_managed.md" %}
# ⚙️ Funzione `trgfn_tx_id_managed`

```sql
CREATE FUNCTION trgfn_tx_id_managed()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.trgfn_tx_id_managed()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
AS $function$
DECLARE
    v_bypass_enabled BOOLEAN := FALSE;   
    v_session_tx_id     UUID;
    v_new_tx_id      UUID;
BEGIN

    
    
     
    
    
    
    
    BEGIN
        SELECT default_value::BOOLEAN
          INTO v_bypass_enabled
          FROM config.parameters
        WHERE code = 'tx_id_bypass_enabled';

        IF NOT FOUND THEN
            
            
            PERFORM script.fn_log_error_only(
                'database',
                'dbops.trgfn_tx_id_managed',
                'ERRORE_PARAMETRI_TABELLA',
                jsonb_build_object(
                    'codice_parametro', 'tx_id_bypass_enabled',
                    'nome_tabella',      'config.parameters',
                    'action', 'default bypass=false' 
                ),
                  NULL::uuid,
                  'tx_id_bypass_enabled',
                  'config.parameters'
              );
        END IF;

    EXCEPTION WHEN OTHERS THEN
        
        PERFORM script.fn_log_and_raise_error(
            'database',
            'dbops.trgfn_tx_id_managed',
            'E_SQL_READ_TABLE',
            jsonb_build_object(
              'parameter', 'tx_id_bypass_enabled',
              'error', SQLERRM
            ),
            NULL::uuid,
            TG_TABLE_NAME::text,
            SQLERRM::text
        );
        
        RAISE;
    END;

      
    
      
    IF NOT v_bypass_enabled THEN
        BEGIN
            v_bypass_enabled := current_setting('myapp.bypass_tx_id_check', TRUE)::BOOLEAN;
        EXCEPTION WHEN OTHERS THEN
            
            NULL;
        END;
    END IF;
      
  
      
    BEGIN
        v_session_tx_id := current_setting('dbops.tx_id', TRUE)::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_session_tx_id := NULL;
    END;
      
    
      
    IF v_bypass_enabled THEN
        
        v_new_tx_id := COALESCE(v_session_tx_id, script.uuid_nil());

    ELSE
        IF v_session_tx_id IS NOT NULL THEN
            
            
            PERFORM 1 
              FROM dbops.transaction_ids 
            WHERE id = v_session_tx_id;
            IF FOUND THEN
                v_new_tx_id := v_session_tx_id;

            ELSE
                
                
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    'dbops.trgfn_tx_id_managed',
                    'W_TXID_NOT_REGISTERED',
                    jsonb_build_object( 'tx_id', v_session_tx_id ),
                    NULL::uuid,
                    VARIADIC ARRAY[]::text[] 
                );
                v_new_tx_id := script.uuid_nil();

            END IF;

        ELSE
            
            
            
            BEGIN  
              
              v_new_tx_id := dbops.fn_get_or_create_session_tx_id();
              
            EXCEPTION WHEN OTHERS THEN

                
                PERFORM script.fn_log_and_raise_error(
                    'database',
                    'dbops.trgfn_tx_id_managed',
                    'E_TXID_GENERATION',
                    jsonb_build_object(
                      'error', SQLERRM
                    ) ,
                    NULL::uuid,
                    VARIADIC ARRAY[]::text[]
                );
                v_new_tx_id := script.uuid_nil();
            END;
        END IF;
    END IF;
  
  
  
  
  IF NEW.tx_id IS NOT NULL AND NEW.tx_id::text = '' THEN
    NEW.tx_id := NULL;
  END IF;
  
  
  IF NEW.tx_id IS NOT NULL THEN
    RETURN NEW;
  END IF;
  
  
    NEW.tx_id := COALESCE(
        NULLIF(current_setting('dbops.tx_id', true), '')::uuid,
        v_new_tx_id,
        uuidv7()
    );
  RETURN NEW;

END;
$function$

COMMENT ON FUNCTION dbops.trgfn_tx_id_managed()
IS 'Trigger function che assegna e verifica transaction ID con log centralizzato';
```

---
{% include-markdown "signature-core.md" %}
