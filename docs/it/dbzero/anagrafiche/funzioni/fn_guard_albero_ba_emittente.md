# ⚙️ Funzione `fn_guard_albero_ba_emittente`

```sql
CREATE FUNCTION fn_guard_albero_ba_emittente(p_billing_account_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_albero_ba_emittente(p_billing_account_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_padre_id anagrafiche.billing_account.id%TYPE;
    r          record;
BEGIN
    -- ⚠️ SECURITY DEFINER: legge anagrafiche.billing_account, che ha
    --   la RLS. Da SECURITY INVOKER un padre o un figlio di un altro
    --   emittente sarebbe INVISIBILE, e il guard direbbe «a posto»
    --   proprio nel caso che deve bloccare (brief §11.1).
    IF p_billing_account_id IS NULL THEN
        RETURN;
    END IF;

    SELECT ba.parent_account_id
      INTO v_padre_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id;

    -- BA inesistente: non e' compito di questo guard (lo dice la FK,
    -- o E_PARENT_NON_RAGGIUNGIBILE del guard di coerenza).
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- a) verso il PADRE
    IF v_padre_id IS NOT NULL
       AND NOT anagrafiche.fn_check_ba_coppia_emittente_omogenea(
                 p_billing_account_id, v_padre_id) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_guard_albero_ba_emittente',
            'E_ALBERO_EMITTENTE_MISTO',
            jsonb_build_object(
                'verso', 'padre',
                'billing_account_id', p_billing_account_id,
                'parent_account_id', v_padre_id,
                'column', 'parent_account_id',
                'emittente_sr_figlio', anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id),
                'emittente_sr_padre',  anagrafiche.fn_get_emittente_fiscale_id(v_padre_id)
            ),
            NULL::uuid,
            p_billing_account_id::text,
            v_padre_id::text,
            anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id)::text,
            anagrafiche.fn_get_emittente_fiscale_id(v_padre_id)::text
        );
    END IF;

    -- b) verso i FIGLI
    --    ⚠️ Il movimento che si dimentica sempre: cambiare
    --    l'emittente di un BA non spacca solo il legame verso
    --    l'alto, spacca anche quelli verso il basso.
    FOR r IN
        SELECT ba.id
          FROM anagrafiche.billing_account ba
         WHERE ba.parent_account_id = p_billing_account_id
         ORDER BY ba.id
    LOOP
        IF NOT anagrafiche.fn_check_ba_coppia_emittente_omogenea(
                 r.id, p_billing_account_id) THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'fn_guard_albero_ba_emittente',
                'E_ALBERO_EMITTENTE_MISTO',
                jsonb_build_object(
                    'verso', 'figlio',
                    'billing_account_id', r.id,
                    'parent_account_id', p_billing_account_id,
                    'column', 'parent_account_id',
                    'emittente_sr_figlio', anagrafiche.fn_get_emittente_fiscale_id(r.id),
                    'emittente_sr_padre',  anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id)
                ),
                NULL::uuid,
                r.id::text,
                p_billing_account_id::text,
                anagrafiche.fn_get_emittente_fiscale_id(r.id)::text,
                anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id)::text
            );
        END IF;
    END LOOP;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_albero_ba_emittente(p_billing_account_id bigint)
IS 'Guard fail-fast: verifica che il billing account indicato sia omogeneo per emittente con il PADRE e con TUTTI i FIGLI. Solleva E_ALBERO_EMITTENTE_MISTO nominando i due BA e i due emittenti. SECURITY DEFINER perche'' legge anagrafiche.billing_account, che ha la RLS: da SECURITY INVOKER un padre o un figlio di un altro emittente sarebbe invisibile e il guard direbbe «a posto» proprio nel caso da bloccare (brief §11.1). Nessuna eccezione per il pregresso e nessuna GUC di override: un invariante con l''interruttore non e'' un invariante. Brief P-1 §3.5.';
```

---
{% include-markdown "signature-core.md" %}
