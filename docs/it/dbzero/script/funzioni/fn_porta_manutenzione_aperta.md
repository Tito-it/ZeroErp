{% include-markdown "it/dbzero/script/manual/fn_porta_manutenzione_aperta.md" %}
# ⚙️ Funzione `fn_porta_manutenzione_aperta`

```sql
CREATE FUNCTION fn_porta_manutenzione_aperta(p_chiave text, p_tabella regclass, p_operazione text, p_riga_id text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_porta_manutenzione_aperta(p_chiave text, p_tabella regclass, p_operazione text, p_riga_id text DEFAULT NULL::text)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_schema dbops.porte_manutenzione_passaggi.schema_name%TYPE;
    v_tabella dbops.porte_manutenzione_passaggi.table_name%TYPE;
BEGIN
    -- Scopo: dire se la porta di manutenzione p_chiave e' aperta per
    --   questa sessione, e se lo e' lasciarne la traccia.
    -- Regole:
    --   - GUC spenta, assente o di valore diverso da on/true/1: chiusa;
    --   - GUC accesa ma sessione che non e' del migratore (l'app,
    --     anche dentro una DEFINER): chiusa, in silenzio — il guard
    --     decide come se la GUC non ci fosse;
    --   - GUC accesa e sessione del migratore: aperta, con una riga nel
    --     diario.
    IF p_chiave IS NULL OR p_tabella IS NULL OR p_operazione IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_porta_manutenzione_aperta', 'E_GENERICO',
            jsonb_build_object(
                'detail',     'Parametri obbligatori mancanti',
                'chiave',     p_chiave,
                'tabella',    p_tabella::text,
                'operazione', p_operazione),
            NULL::uuid,
            'Parametri obbligatori mancanti (chiave, tabella, operazione).');
    END IF;

    IF lower(btrim(COALESCE(current_setting(p_chiave, true), ''))) NOT IN ('on', 'true', '1') THEN
        RETURN false;
    END IF;

    IF NOT dbops.fn_sessione_del_migratore() THEN
        RETURN false;
    END IF;

    SELECT n.nspname, c.relname
      INTO v_schema, v_tabella
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE c.oid = p_tabella;

    INSERT INTO dbops.porte_manutenzione_passaggi
           (chiave, schema_name, table_name, riga_id, operazione, utente_sessione)
    VALUES (p_chiave, v_schema, v_tabella, p_riga_id, p_operazione, session_user);

    RETURN true;
END;
$function$

COMMENT ON FUNCTION script.fn_porta_manutenzione_aperta(p_chiave text, p_tabella regclass, p_operazione text, p_riga_id text)
IS 'La porta di manutenzione p_chiave e'' aperta per questa sessione? true solo se la GUC e'' accesa (on, true o 1, senza maiuscole) e la sessione e'' del migratore (dbops.fn_sessione_del_migratore, che legge session_user). Per l''applicazione la porta resta chiusa anche con la GUC accesa, e il guard che la chiede decide come se la GUC non ci fosse. Quando la porta si apre lascia una riga in dbops.porte_manutenzione_passaggi (chiave, tabella, id della riga, operazione, ruolo di login). Si chiama nel punto in cui il controllo rifiuterebbe, cosi'' il diario dice che cosa la porta ha forzato. La chiamano i trigger delle porte di manutenzione: script.trgfn_lock_columns, script.trgfn_delete_block_by_guc, script.trgfn_seed_primo_impianto, vendite.trgfn_event_log_append_only, vendite.trgfn_logs_guard_delete, vendite.trgfn_attivita_fatturabili_guard_commessa. Le porte che una funzione apre per se'' non passano di qui. Parametri obbligatori mancanti: E_GENERICO. SECURITY DEFINER, search_path pg_catalog.';
```

</div>

---
{% include-markdown "signature-core.md" %}
