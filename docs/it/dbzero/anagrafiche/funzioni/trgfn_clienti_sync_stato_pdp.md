{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_clienti_sync_stato_pdp.md" %}
# ⚙️ Funzione `trgfn_clienti_sync_stato_pdp`

```sql
CREATE FUNCTION trgfn_clienti_sync_stato_pdp()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_cd_stato_cliente text;
    v_stato_att_id     bigint;
    v_stato_disp_id    bigint;
BEGIN

    -- =========================================================
    -- Sincronizza lo stato tecnico del PDP (config.stati_pdp)
    -- in base al cambio di stato_cliente del cliente.
    --
    -- Regole implementate (SOLO AT e CH):
    --  - Se stato_cliente = 'AT' (Attivo)
    --      -> PDP passa a 'ATT' (Attivo) se non DISMESSO
    --
    --  - Se stato_cliente = 'CH' (Chiuso)
    --      -> se NON esistono altri clienti ATTIVI sullo stesso PDP
    --         PDP passa a 'DISP' (Disponibile)
    --
    --  Tutti gli altri casi NON modificano lo stato_pdp.
    --  Gli stati 'DTEC' e 'DISM' saranno gestiti da processi/azioni specifiche.
    -- =========================================================



    --------------------------------------------------------------------
    -- 0) Senza PDP collegato → nessuna sincronizzazione necessaria
    --------------------------------------------------------------------
    IF NEW.pdp_id IS NULL THEN
        RETURN NEW;
    END IF;

    --------------------------------------------------------------------
    -- 1) Recupero codice interno dello stato cliente
    --------------------------------------------------------------------
    SELECT sc.codice_interno
    INTO v_cd_stato_cliente
    FROM config.stati_cliente sc
    WHERE sc.id = NEW.stato_cliente_id;

    IF v_cd_stato_cliente IS NULL THEN
        RETURN NEW; -- stato non trovato → non interveniamo
    END IF;

    --------------------------------------------------------------------
    -- 2) Ci interessano solo due stati cliente:
    --      AT = Attivo → PDP deve diventare ATT
    --      CH = Chiuso → PDP deve tornare DISP
    --------------------------------------------------------------------
    IF v_cd_stato_cliente NOT IN ('AT', 'CH') THEN
        RETURN NEW;
    END IF;

    --------------------------------------------------------------------
    -- 3) Recupero ID degli stati tecnici PDP
    --------------------------------------------------------------------
    SELECT id INTO v_stato_att_id
    FROM config.stati_pdp
    WHERE codice_interno = 'ATT';

    SELECT id INTO v_stato_disp_id
    FROM config.stati_pdp
    WHERE codice_interno = 'DISP';

    IF v_stato_att_id IS NULL OR v_stato_disp_id IS NULL THEN
        
         PERFORM script.fn_log_and_raise_error(
                'database',
                'anagrafiche.trgfn_clienti_sync_stato_pdp',
                'E_CODICE',
                jsonb_build_object(
                    'config.stati_pdp: stati tecnici ATT / DISP non configurati correttamente)', 
                    'att/disp missing'  
                ),
                new.tx_id,
                'ATT/DISP',
                'config.stati_pdp'
            );

    END IF;


    --------------------------------------------------------------------
    -- 4) Logica di sincronizzazione
    --------------------------------------------------------------------

    -- Caso A → Cliente in ATTIVO → PDP = ATTIVO
    IF v_cd_stato_cliente = 'AT' THEN

        UPDATE anagrafiche.pdp p
        SET stato_pdp_id = v_stato_att_id
        WHERE p.id = NEW.pdp_id
        AND p.stato_pdp_id IS DISTINCT FROM v_stato_att_id;

        RETURN NEW;
    END IF;

    -- Caso B → Cliente CHIUSO → PDP = DISPONIBILE
    IF v_cd_stato_cliente = 'CH' THEN

        UPDATE anagrafiche.pdp p
        SET stato_pdp_id = v_stato_disp_id
        WHERE p.id = NEW.pdp_id
        AND p.stato_pdp_id IS DISTINCT FROM v_stato_disp_id;

        RETURN NEW;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_clienti_sync_stato_pdp()
IS 'Sincronizza lo stato tecnico del PDP (config.stati_pdp)
    in base al cambio di stato_cliente del cliente.
    
    Regole implementate (SOLO AT e CH):
     - Se stato_cliente = ''AT'' (Attivo)
         -> PDP passa a ''ATT'' (Attivo) se non DISMESSO
     
     - Se stato_cliente = ''CH'' (Chiuso)
         -> se NON esistono altri clienti ATTIVI sullo stesso PDP
            PDP passa a ''DISP'' (Disponibile)
     
     Tutti gli altri casi NON modificano lo stato_pdp.
     Gli stati ''DTEC'' e ''DISM'' saranno gestiti da processi/azioni specifiche.';
```

---
{% include-markdown "signature-core.md" %}
