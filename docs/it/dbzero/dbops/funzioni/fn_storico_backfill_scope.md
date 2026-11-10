{% include-markdown "it/dbzero/dbops/manual/fn_storico_backfill_scope.md" %}
# ⚙️ Funzione `fn_storico_backfill_scope`

```sql
CREATE FUNCTION fn_storico_backfill_scope(p_schema_base text, p_table_base text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_storico_backfill_scope(p_schema_base text, p_table_base text)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: attribuire origine_schema e scope_emittente_fiscale_id alle
--   versioni gia' scritte di UNA madre. Idempotente: tocca solo le righe
--   con origine NULL.
DECLARE
    v_sto_oid    oid  := pg_catalog.to_regclass(format('storico.%I', p_table_base));
    v_full_sto   text := format('storico.%I', p_table_base);
    v_madre      text := p_schema_base || '.' || p_table_base;
    v_madre_oid  oid  := pg_catalog.to_regclass(format('%I.%I', p_schema_base, p_table_base));
    v_owner      text;
    v_condivisa  boolean;
    v_chiavi     text[];
    v_aggiornate bigint := 0;
    v_residue    bigint := 0;
    v_nullable   boolean;
    v_not_null   boolean := false;
BEGIN
    IF v_sto_oid IS NULL OR v_madre_oid IS NULL THEN
        RETURN jsonb_build_object('madre', v_madre, 'esito', 'NO_SHADOW');
    END IF;

    -- Le colonne devono esserci (le mette fn_storico_arma_scope / il
    -- provisioning). Senza, niente da fare qui: WARN e avanti.
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_attribute a
                    WHERE a.attrelid = v_sto_oid AND a.attname = 'origine_schema'
                      AND NOT a.attisdropped) THEN
        PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_storico_backfill_scope',
            p_status        => 'WARN',
            p_rule_type     => 'STORICO_SCOPE',
            p_params        => jsonb_build_object('madre', v_madre, 'shadow', v_full_sto),
            p_message       => 'Shadow senza le colonne dello scope: prima fn_storico_arma_scope (o il provisioning)');
        RETURN jsonb_build_object('madre', v_madre, 'esito', 'SENZA_COLONNE');
    END IF;

    SELECT pg_get_userbyid(c.relowner) INTO v_owner
      FROM pg_catalog.pg_class c WHERE c.oid = v_sto_oid;

    -- La shadow e' condivisa se un'altra madre omonima porta il trigger.
    SELECT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger t
          JOIN pg_catalog.pg_class     mc ON mc.oid = t.tgrelid
          JOIN pg_catalog.pg_namespace mn ON mn.oid = mc.relnamespace
          JOIN pg_catalog.pg_proc      pr ON pr.oid = t.tgfoid
         WHERE pr.proname = 'trgfn_storico_generic' AND NOT t.tgisinternal
           AND mc.relname = p_table_base AND mn.nspname <> p_schema_base)
      INTO v_condivisa;

    IF v_condivisa THEN
        -- Le chiavi ESCLUSIVE di questa madre: colonne sue che nessuna
        -- delle omonime ha. Una versione che ne porta almeno una e' sua.
        SELECT array_agg(a.attname::text) INTO v_chiavi
          FROM pg_catalog.pg_attribute a
         WHERE a.attrelid = v_madre_oid AND a.attnum > 0 AND NOT a.attisdropped
           AND NOT EXISTS (
               SELECT 1 FROM pg_catalog.pg_attribute b
                 JOIN pg_catalog.pg_class     bc ON bc.oid = b.attrelid
                 JOIN pg_catalog.pg_namespace bn ON bn.oid = bc.relnamespace
                WHERE bc.relname = p_table_base AND bn.nspname <> p_schema_base
                  AND bc.relkind IN ('r', 'p')
                  AND b.attname = a.attname AND b.attnum > 0 AND NOT b.attisdropped);
        IF v_chiavi IS NULL THEN
            -- Due madri con le STESSE colonne: nessuna versione e' attribuibile.
            PERFORM dbops.fn_audit_log_once(
                p_function_name => 'fn_storico_backfill_scope',
                p_status        => 'WARN',
                p_rule_type     => 'STORICO_SCOPE',
                p_params        => jsonb_build_object('madre', v_madre, 'shadow', v_full_sto),
                p_message       => 'Shadow condivisa senza chiavi esclusive: le versioni legacy non sono attribuibili');
            RETURN jsonb_build_object('madre', v_madre, 'esito', 'NON_ATTRIBUIBILE');
        END IF;
        EXECUTE format(
            'UPDATE %s s
                SET origine_schema             = %L,
                    scope_emittente_fiscale_id = dbops.fn_storico_risolvi_scope(%L, %L, s.snapshot)
              WHERE s.origine_schema IS NULL
                AND s.snapshot IS NOT NULL
                AND pg_catalog.jsonb_exists_any(s.snapshot, %L::text[])',
            v_full_sto, p_schema_base, p_schema_base, p_table_base, v_chiavi);
    ELSE
        EXECUTE format(
            'UPDATE %s s
                SET origine_schema             = %L,
                    scope_emittente_fiscale_id = dbops.fn_storico_risolvi_scope(%L, %L, s.snapshot)
              WHERE s.origine_schema IS NULL',
            v_full_sto, p_schema_base, p_schema_base, p_table_base);
    END IF;
    GET DIAGNOSTICS v_aggiornate = ROW_COUNT;

    -- Quante restano senza origine (nelle condivise: le non attribuibili).
    EXECUTE format('SELECT count(*) FROM %s WHERE origine_schema IS NULL', v_full_sto)
       INTO v_residue;

    -- NOT NULL quando e' vero, e solo se abbiamo i privilegi del proprietario
    -- (membership con INHERIT o superuser, non il nome).
    SELECT NOT a.attnotnull INTO v_nullable
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_sto_oid AND a.attname = 'origine_schema';
    IF v_residue = 0 AND v_nullable AND pg_has_role(current_user, v_owner, 'USAGE') THEN
        EXECUTE format('ALTER TABLE %s ALTER COLUMN origine_schema SET NOT NULL', v_full_sto);
        v_not_null := true;
    END IF;

    IF v_aggiornate > 0 OR v_not_null THEN
        PERFORM dbops.fn_audit_log_once(
            p_function_name => 'fn_storico_backfill_scope',
            p_status        => 'OK',
            p_rule_type     => 'STORICO_SCOPE',
            p_rows_affected => v_aggiornate::int,
            p_params        => jsonb_build_object('madre', v_madre, 'shadow', v_full_sto,
                                                  'condivisa', v_condivisa, 'chiavi_esclusive', to_jsonb(v_chiavi),
                                                  'aggiornate', v_aggiornate, 'residue_null', v_residue,
                                                  'set_not_null', v_not_null),
            p_message       => 'Backfill di origine_schema e scope sulle versioni gia'' scritte');
    END IF;

    RETURN jsonb_build_object('madre', v_madre, 'shadow', v_full_sto,
                              'esito', CASE WHEN v_aggiornate > 0 THEN 'AGGIORNATA' ELSE 'NIENTE_DA_FARE' END,
                              'condivisa', v_condivisa, 'aggiornate', v_aggiornate,
                              'residue_null', v_residue, 'set_not_null', v_not_null);
END;
$function$

COMMENT ON FUNCTION dbops.fn_storico_backfill_scope(p_schema_base text, p_table_base text)
IS 'Backfill dello scope congelato sulle versioni gia'' scritte della shadow storico.<tabella> di una madre: alle righe con origine_schema NULL assegna lo schema della madre e scope_emittente_fiscale_id risolto da dbops.fn_storico_risolvi_scope sullo SNAPSHOT (per il modo PADRE risale al padre com''e'' oggi: e'' il limite dichiarato del backfill). Nelle shadow condivise fra due madri omonime attribuisce la versione alla madre di cui lo snapshot porta almeno una chiave ESCLUSIVA (jsonb_exists_any); le versioni senza chiavi esclusive restano NULL, e le conta il riepilogo di dbops.fn_storico_backfill_scope_tutte. Porta origine_schema a NOT NULL quando nessuna riga resta NULL e il chiamante ha i privilegi del proprietario della shadow (pg_has_role USAGE: il proprietario, un suo membro con INHERIT, un superuser). Idempotente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
