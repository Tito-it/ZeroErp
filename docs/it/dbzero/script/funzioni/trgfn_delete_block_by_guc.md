{% include-markdown "it/dbzero/script/manual/trgfn_delete_block_by_guc.md" %}
# ⚙️ Funzione `trgfn_delete_block_by_guc`

```sql
CREATE FUNCTION trgfn_delete_block_by_guc()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_delete_block_by_guc()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- Guard: argomento trigger obbligatorio
    IF TG_NARGS < 1 THEN
        PERFORM script.fn_log_and_raise_error(
            TG_TABLE_SCHEMA,
            TG_NAME,
            'E_TRIGGER_ARGOMENTI_INVALIDI',
            jsonb_build_object(
                'detail', 'Argomenti trigger mancanti',
                'expected', 'guc_key',
                'found', TG_NARGS
            ),
            NULL::uuid,
            concat('TG_ARGV[0] (guc_key) mancante per trigger ', TG_NAME)
        );
    END IF;

    -- Se la GUC e' abilitata → consente DELETE
    IF current_setting(TG_ARGV[0], true) = 'on' THEN
        RETURN OLD;
    END IF;

    -- Delete bloccata da policy
    PERFORM script.fn_log_and_raise_error(
        TG_TABLE_SCHEMA,
        TG_NAME,
        'E_DELETE_NOT_ALLOWED',
        jsonb_build_object(
            'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
            'id', OLD.id
        ),
        NULL::uuid,
        TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        OLD.id::text
    );

    RETURN OLD;
END;
$function$

COMMENT ON FUNCTION script.trgfn_delete_block_by_guc()
IS 'Blocca DELETE se GUC non abilitata. Errori: ERRORE_PARAMETRI, E_DELETE_NOT_ALLOWED.';
```

</div>

---
{% include-markdown "signature-core.md" %}
