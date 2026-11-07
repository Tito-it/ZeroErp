{% include-markdown "it/dbzero/dbops/manual/fn_trigger_figlie_presenti.md" %}
# ⚙️ Funzione `fn_trigger_figlie_presenti`

```sql
CREATE FUNCTION fn_trigger_figlie_presenti(p_tabella oid, p_trigger name, p_valore text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_trigger_figlie_presenti(p_tabella oid, p_trigger name, p_valore text)
 RETURNS TABLE(configurato boolean, figlia_attivo_col name, presenti boolean, dettaglio text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_chi          CONSTANT dbops.error_log.function_name%TYPE := 'dbops.fn_trigger_figlie_presenti';
    v_funzione     pg_catalog.pg_proc.proname%TYPE;
    v_schema_fn    pg_catalog.pg_namespace.nspname%TYPE;
    v_tgargs       pg_catalog.pg_trigger.tgargs%TYPE;
    v_proprietario pg_catalog.pg_class.relowner%TYPE;
    v_g            record;  -- riga di dbops.fn_trigger_attivo_argomenti
    v_figlia       pg_catalog.pg_class.oid%TYPE;
    -- il tipo della colonna FK, stampato per il cast: testo
    v_tipo_fk      text;
    v_attivo_col   pg_catalog.pg_attribute.attname%TYPE;
    v_presenti     boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Se il padre di un trigger block ha ancora righe figlie che
    --   lo usano (attive, se la figlia ha la colonna attivo),
    --   cercate fuori dalla row security.
    --
    -- Uso (dalla funzione trigger):
    --   SELECT * FROM dbops.fn_trigger_figlie_presenti(TG_RELID, TG_NAME, v_ref);
    --
    -- configurato = false (con dettaglio): il montaggio nomina una
    --   tabella figlia o una colonna FK che non c'e'.
    -- Solleva E_DBOPS_CHIAMATA_NON_VALIDA se il trigger non e' un
    --   block, se la sua tabella non e' del proprietario, o se la
    --   figlia e' sotto row security anche per il proprietario.
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
       OR v_funzione <> 'trgfn_prevent_deactivate_if_children' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_trigger',
                               'tabella', p_tabella::text, 'trigger', p_trigger),
            NULL::uuid,
            v_chi, format('%s su %s non e'' un trigger block ATTIVO', p_trigger, p_tabella));
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
        RETURN QUERY SELECT false, NULL::name, NULL::boolean, v_g.dettaglio;
        RETURN;
    END IF;

    SELECT c.oid
      INTO v_figlia
      FROM pg_catalog.pg_class c
      JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = v_g.figlia_schema
       AND c.relname = v_g.figlia_tabella
       AND c.relkind IN ('r', 'p');

    IF v_figlia IS NULL THEN
        RETURN QUERY SELECT false, NULL::name, NULL::boolean,
            format('la tabella figlia %s.%s non esiste', v_g.figlia_schema, v_g.figlia_tabella);
        RETURN;
    END IF;

    -- Dentro una DEFINER risponde per il proprietario: vero solo se
    -- la ricerca sarebbe filtrata anche per lui.
    IF pg_catalog.row_security_active(v_figlia) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_trigger', 'tabella', p_tabella::text,
                               'trigger', p_trigger, 'figlia', v_figlia::regclass::text),
            NULL::uuid,
            v_chi, format('la figlia %s e'' sotto row security anche per il proprietario: la ricerca sarebbe parziale',
                          v_figlia::regclass));
    END IF;

    SELECT a.atttypid::regtype::text
      INTO v_tipo_fk
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_figlia
       AND a.attname  = v_g.fk_col
       AND a.attnum   > 0
       AND NOT a.attisdropped;

    IF v_tipo_fk IS NULL THEN
        RETURN QUERY SELECT false, NULL::name, NULL::boolean,
            format('la colonna FK %s.%s.%s non esiste',
                   v_g.figlia_schema, v_g.figlia_tabella, v_g.fk_col);
        RETURN;
    END IF;

    SELECT a.attname
      INTO v_attivo_col
      FROM pg_catalog.pg_attribute a
     WHERE a.attrelid = v_figlia
       AND a.attname  = dbops.fn_get_override_col(v_g.figlia_schema, v_g.figlia_tabella,
                                                  'ATTIVO_COL', 'attivo')
       AND a.attnum   > 0
       AND NOT a.attisdropped;

    IF v_attivo_col IS NOT NULL THEN
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = ($1)::%s AND %I IS DISTINCT FROM false)',
                       v_g.figlia_schema, v_g.figlia_tabella, v_g.fk_col, v_tipo_fk, v_attivo_col)
           INTO v_presenti
          USING p_valore;
    ELSE
        EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I.%I WHERE %I = ($1)::%s)',
                       v_g.figlia_schema, v_g.figlia_tabella, v_g.fk_col, v_tipo_fk)
           INTO v_presenti
          USING p_valore;
    END IF;

    RETURN QUERY SELECT true, v_attivo_col, v_presenti, NULL::text;
END
$function$

COMMENT ON FUNCTION dbops.fn_trigger_figlie_presenti(p_tabella oid, p_trigger name, p_valore text)
IS 'Se il padre di un trigger block ATTIVO (dbops.trgfn_prevent_deactivate_if_children) ha ancora righe figlie che lo usano, cercate fuori dalla row security: configurato, figlia_attivo_col (la colonna attivo della figlia, con l''override di dbops.automation_overrides_cols; NULL se non ce l''ha), presenti e dettaglio. Con la colonna attivo contano le figlie attive, senza ogni riga. Riceve il trigger (tabella e nome) e il valore della colonna referenziata del padre; gli argomenti li legge dal montaggio con dbops.fn_trigger_attivo_argomenti, mai dal chiamante. configurato = false, con il motivo in dettaglio, se il montaggio nomina una tabella figlia o una colonna FK che non esiste. Solleva E_DBOPS_CHIAMATA_NON_VALIDA se il trigger non e'' un block ATTIVO, se la sua tabella non e'' del proprietario di questa funzione (gli argomenti devono averli scritti le migrazioni), o se la figlia e'' sotto row security anche per il proprietario. 🔴 Fuori dalla row security perche'' che un padre sia ancora usato non dipende da chi guarda: sotto la RLS di chi agisce un catalogo si spegneva con figlie attive di un''altra azienda. ⚠️ DEFINER del PROPRIETARIO, non di un superuser, come dbops.fn_trigger_padre_stato; lo presidia dbops/test-guard-attivo-occhi-del-proprietario-v1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
