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
    v_bypass_enabled BOOLEAN := FALSE;   -- Il bypass è abilitato di default
    v_session_tx_id     UUID;
    v_new_tx_id      UUID;
BEGIN
    -- --------------------------------------
    -- 1. Verifica stato bypass (config + sessione)
    -- --------------------------------------
    -- Legge da config.parameters
    BEGIN
        SELECT default_value::BOOLEAN
          INTO v_bypass_enabled
          FROM config.parameters
        WHERE code = 'tx_id_bypass_enabled';

        IF NOT FOUND THEN
            -- Parametro mancante: log e prosegui con bypass disabilitato
            
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
        -- Errore reale nella lettura del parametro: log e abort
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
        -- Rilascia eccezione per non proseguire
        RAISE;
    END;

      -- --------------------------------------
    -- 2.  Override da sessione se non attivo
      -- --------------------------------------
    IF NOT v_bypass_enabled THEN
        BEGIN
            v_bypass_enabled := current_setting('myapp.bypass_tx_id_check', TRUE)::BOOLEAN;
        EXCEPTION WHEN OTHERS THEN
            -- Variabile sessione non impostata: procedi senza bypass
            NULL;
        END;
    END IF;
      -- --------------------------------------
   -- 3. Lettura tx_id da variabile di sessione
      -- --------------------------------------
    BEGIN
        v_session_tx_id := current_setting('dbops.tx_id', TRUE)::UUID;
    EXCEPTION WHEN OTHERS THEN
        v_session_tx_id := NULL;
    END;
      -- --------------------------------------
    -- 4. Assegnazione tx_id in base alla modalità
      -- --------------------------------------
    IF v_bypass_enabled THEN
        -- Caso A) Bypass attivo: usa nil o valore in sessione
        v_new_tx_id := COALESCE(v_session_tx_id, script.uuid_nil());

    ELSE
        IF v_session_tx_id IS NOT NULL THEN
            -- Caso B)  Modalità normale con tx_id in sessione
            -- Verifica esistenza in transaction_ids
            PERFORM 1 
              FROM dbops.transaction_ids 
             WHERE id = v_session_tx_id;
            IF FOUND THEN
                v_new_tx_id := v_session_tx_id;

            ELSE
                 -- Caso C)
                -- ID non registrato: log warning e assegna nil
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
            -- Caso D)
            -- Nessun tx_id in sessione: generazione tramite dblink (assegna nuovo)
            --  modalita standard
            BEGIN  
              -- Invochiamo il helper che fa dblink + set_config
              v_new_tx_id := dbops.fn_get_or_create_session_tx_id();
              
            EXCEPTION WHEN OTHERS THEN

                -- Errore generazione tx_id: log e assegna nil
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
      -- --------------------------------------
    -- 5. Assegna tx_id al record
      -- --------------------------------------
    NEW.tx_id := v_new_tx_id;
    RETURN NEW;

END;
$function$
```

---
{% include-markdown "signature-core.md" %}
