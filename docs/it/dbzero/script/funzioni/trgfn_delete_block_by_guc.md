{% include-markdown "it/dbzero/script/manual/trgfn_delete_block_by_guc.md" %}
# ⚙️ Funzione `trgfn_delete_block_by_guc`

```sql
CREATE FUNCTION trgfn_delete_block_by_guc()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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

    -- La porta di manutenzione: la GUC dell'argomento, aperta solo per
    -- la sessione del migratore, con la riga nel diario.
    IF script.fn_porta_manutenzione_aperta(TG_ARGV[0], TG_RELID, TG_OP, OLD.id::text) THEN
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
IS 'Blocca il DELETE delle tabelle dichiarate in dbops.automation_delete_block (BEFORE DELETE FOR EACH ROW, montato dall''automazione DELETE_BLOCK). TG_ARGV[0] e'' la GUC della porta di manutenzione: apre solo per la sessione del migratore (script.fn_porta_manutenzione_aperta), e ogni riga cancellata dalla porta lascia una riga in dbops.porte_manutenzione_passaggi; per l''applicazione il DELETE resta rifiutato anche con la GUC accesa. Errori: E_TRIGGER_ARGOMENTI_INVALIDI (argomento mancante), E_DELETE_NOT_ALLOWED (il DELETE).';
```

</div>

---
{% include-markdown "signature-core.md" %}
