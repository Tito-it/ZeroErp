{% include-markdown "it/dbzero/dbops/manual/fn_trigger_padre_stato.md" %}
# ⚙️ Funzione `fn_trigger_padre_stato`

```sql
CREATE FUNCTION fn_trigger_padre_stato(p_tabella oid, p_trigger name, p_valore text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_padre_stato(p_tabella oid, p_trigger name, p_valore text)
 RETURNS TABLE(configurato boolean, trovato boolean, valore jsonb, dettaglio text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_chi         CONSTANT dbops.error_log.function_name%TYPE := 'dbops.fn_trigger_padre_stato';
    v_funzione    pg_catalog.pg_proc.proname%TYPE;
    v_schema_fn   pg_catalog.pg_namespace.nspname%TYPE;
    v_tgargs      pg_catalog.pg_trigger.tgargs%TYPE;
    v_proprietario pg_catalog.pg_class.relowner%TYPE;
    v_g           record;  -- riga di dbops.fn_trigger_attivo_argomenti
    v_padre       pg_catalog.pg_class.oid%TYPE;
    -- il tipo della colonna referenziata, stampato per il cast: testo
    v_tipo_ref    text;
    v_trovato     boolean;
    v_valore      jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Lo stato del padre di un trigger require (la colonna che il
    --   montaggio dichiara: attivo, oppure obsoleto_dal), e se la
    --   riga padre esiste, letti fuori dalla row security.
    --
    -- Uso (dalla funzione trigger):
    --   SELECT * FROM dbops.fn_trigger_padre_stato(TG_RELID, TG_NAME, v_fk);
    --
    -- configurato = false (con dettaglio): il montaggio nomina una
    --   tabella o una colonna che non c'e'; il trigger sceglie il codice.
    -- Solleva E_DBOPS_CHIAMATA_NON_VALIDA se il trigger non e' un
    --   require, se la sua tabella non e' del proprietario, o se il
    --   padre e' sotto row security anche per il proprietario.
    -- =========================================================

    SELECT p.proname, n.nspname, t.tgargs, c.relowner
      INTO v_funzione, v_schema_fn, v_tgargs, v_proprietario
      FROM pg_catalog.pg_trigger t
      JOIN pg_catalog.pg_proc p      ON p.oid = t.tgfoid
      JOIN pg_catalog.pg_namespace n ON n.oid = p.pronamespace
      JOIN pg_catalog.pg_class c     ON c.oid = t.tgrelid
     WHERE t.tgrelid = p_tabella
       AND t.tgname  = p_trigger;

    IF v_funzione IS NULL
       OR v_schema_fn <> 'dbops'
       OR v_funzione NOT IN ('trgfn_child_requires_active_parent',
                             'trgfn_child_requires_non_obsolete_parent') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_trigger',
                               'tabella', p_tabella::text, 'trigger', p_trigger),
            NULL::uuid,
            v_chi, format('%s su %s non e'' un trigger require ATTIVO', p_trigger, p_tabella));
    END IF;

    -- Gli argomenti li ha scritti chi possiede la tabella: solo cosi'
    -- si possono eseguire con gli occhi del proprietario.
    IF NOT pg_catalog.pg_has_role(current_user, v_proprietario, 'USAGE') THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_tabella', 'tabella', p_tabella::text,
                               'proprietario', pg_catalog.pg_get_userbyid(v_proprietario)),
            NULL::uuid,
            v_chi, format('la tabella %s non e'' del proprietario del database', p_tabella));
    END IF;

    SELECT * INTO v_g
      FROM dbops.fn_trigger_attivo_argomenti(v_funzione, dbops.fn_trigger_argomenti(v_tgargs));

    IF NOT v_g.valido THEN
        RETURN QUERY SELECT false, NULL::boolean, NULL::jsonb, v_g.dettaglio;
        RETURN;
    END IF;

    SELECT c.oid
      INTO v_padre
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = v_g.padre_schema
       AND c.relname = v_g.padre_tabella
       AND c.relkind IN ('r', 'p');

    IF v_padre IS NULL THEN
        RETURN QUERY SELECT false, NULL::boolean, NULL::jsonb,
            format('la tabella padre %s.%s non esiste', v_g.padre_schema, v_g.padre_tabella);
        RETURN;
    END IF;

    -- Dentro una DEFINER risponde per il proprietario: vero solo se
    -- la lettura sarebbe filtrata anche per lui.
    IF pg_catalog.row_security_active(v_padre) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_trigger', 'tabella', p_tabella::text,
                               'trigger', p_trigger, 'padre', v_padre::regclass::text),
            NULL::uuid,
            v_chi, format('il padre %s e'' sotto row security anche per il proprietario: la lettura sarebbe parziale',
                          v_padre::regclass));
    END IF;

    SELECT a.atttypid::regtype::text
      INTO v_tipo_ref
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_padre
       AND a.attname  = v_g.ref_col
       AND a.attnum   > 0
       AND NOT a.attisdropped;

    IF v_tipo_ref IS NULL THEN
        RETURN QUERY SELECT false, NULL::boolean, NULL::jsonb,
            format('la colonna referenziata %s.%s.%s non esiste',
                   v_g.padre_schema, v_g.padre_tabella, v_g.ref_col);
        RETURN;
    END IF;

    IF NOT EXISTS (SELECT 1
                     FROM pg_catalog.pg_attribute a
                    WHERE a.attrelid = v_padre
                      AND a.attname  = v_g.stato_col
                      AND a.attnum   > 0
                      AND NOT a.attisdropped) THEN
        RETURN QUERY SELECT false, NULL::boolean, NULL::jsonb,
            format('la colonna di stato %s.%s.%s non esiste',
                   v_g.padre_schema, v_g.padre_tabella, v_g.stato_col);
        RETURN;
    END IF;

    -- Zero righe: v_trovato resta NULL. Non FOUND: EXECUTE non lo aggiorna.
    EXECUTE format('SELECT true, to_jsonb(%I) FROM %I.%I WHERE %I = ($1)::%s',
                   v_g.stato_col, v_g.padre_schema, v_g.padre_tabella,
                   v_g.ref_col, v_tipo_ref)
       INTO v_trovato, v_valore
      USING p_valore;

    RETURN QUERY SELECT true, COALESCE(v_trovato, false), v_valore, NULL::text;
END
$function$

COMMENT ON FUNCTION dbops.fn_trigger_padre_stato(p_tabella oid, p_trigger name, p_valore text)
IS 'Lo stato del padre di un trigger require ATTIVO (dbops.trgfn_child_requires_active_parent, dbops.trgfn_child_requires_non_obsolete_parent), letto fuori dalla row security: configurato, trovato, valore (jsonb: la colonna di stato che il montaggio dichiara, attivo o obsoleto_dal) e dettaglio. Riceve il trigger (tabella e nome) e la chiave del padre come la scrive la figlia; gli argomenti li legge dal montaggio con dbops.fn_trigger_attivo_argomenti, mai dal chiamante. configurato = false, con il motivo in dettaglio, se il montaggio nomina una tabella o una colonna che non esiste: il codice lo sceglie il trigger. trovato = false se nessuna riga padre ha quella chiave (possibile solo dove il collegamento non e'' una FK). Solleva E_DBOPS_CHIAMATA_NON_VALIDA se il trigger non e'' un require ATTIVO, se la sua tabella non e'' del proprietario di questa funzione (gli argomenti devono averli scritti le migrazioni), o se il padre e'' sotto row security anche per il proprietario. 🔴 Fuori dalla row security perche'' lo stato di un padre non dipende da chi guarda, e il require differito legge al commit, col contesto di chi chiude la transazione. ⚠️ DEFINER del PROPRIETARIO, non di un superuser: attraversa la row security perche'' il proprietario delle tabelle e'' anche il suo, con la RLS abilitata e non forzata; lo presidia dbops/test-guard-attivo-occhi-del-proprietario-v1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
