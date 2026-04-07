{% include-markdown "it/dbzero/anagrafiche/manual/fn_get_emittente_fiscale_pk.md" %}
# ⚙️ Funzione `fn_get_emittente_fiscale_pk`

```sql
CREATE FUNCTION fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_get_emittente_fiscale_pk',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'p_billing_account_id obbligatorio e > 0',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            'p_billing_account_id obbligatorio e > 0'
        );
    END IF;

    
    
    
    
    
    SELECT COALESCE(
        
        (SELECT ef.id
           FROM anagrafiche.emittenti_fiscali_billing_account efba
           JOIN anagrafiche.emittenti_fiscali ef
             ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
          WHERE efba.billing_account_id = p_billing_account_id
            AND ef.attivo = true
          LIMIT 1),
        
        (SELECT ef.id
           FROM anagrafiche.emittenti_fiscali_billing_account efba
           JOIN anagrafiche.emittenti_fiscali ef
             ON ef.soggetto_ruolo_id = efba.emittente_soggetto_ruolo_id
          WHERE efba.billing_account_id IS NULL
            AND efba.is_default = true
            AND ef.attivo = true
          LIMIT 1)
    ) INTO v_emittente_fiscale_id;

    
    IF v_emittente_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            'fn_get_emittente_fiscale_pk',
            'E_EMITTENTE_DEFAULT_MISSING',
            jsonb_build_object(
                'detail', 'Emittente fiscale di default mancante o disattivato',
                'billing_account_id', p_billing_account_id
            ),
            NULL::uuid,
            concat('Emittente fiscale di default mancante per billing_account_id ',
                   p_billing_account_id::text)
        );
    END IF;

    RETURN v_emittente_fiscale_id;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_get_emittente_fiscale_pk(p_billing_account_id bigint)
IS 'Restituisce anagrafiche.emittenti_fiscali.id (PK numerica reale) per un billing_account. Catena: 1) mapping specifico in emittenti_fiscali_billing_account, 2) fallback al gestore globale (BA NULL + is_default=true). Filtra per ef.attivo=true. Solleva E_EMITTENTE_DEFAULT_MISSING se nulla risolto. Affianca fn_get_emittente_fiscale_id che invece ritorna soggetto_ruolo_id.';
```

---
{% include-markdown "signature-core.md" %}
