{% include-markdown "it/dbzero/script/manual/fn_area_di_oggetto.md" %}
# ⚙️ Funzione `fn_area_di_oggetto`

```sql
CREATE FUNCTION fn_area_di_oggetto(p_app_label character varying, p_model_name character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_area_di_oggetto(p_app_label character varying, p_model_name character varying)
 RETURNS character varying
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: dire a quale area appartiene un oggetto (app_label, model_name):
--   l'override di area_model_overrides se c'e', altrimenti app_label
--   (area = schema). Restituisce la chiave dell'area, schema_db.
DECLARE
    v_area config.aree_funzionali.schema_db%TYPE;
BEGIN
    SELECT af.schema_db
      INTO v_area
      FROM config.area_model_overrides amo
      JOIN config.aree_funzionali af ON af.id = amo.area_id
     WHERE amo.app_label  = p_app_label
       AND amo.model_name = p_model_name;

    RETURN COALESCE(v_area, p_app_label);
END;
$function$

COMMENT ON FUNCTION script.fn_area_di_oggetto(p_app_label character varying, p_model_name character varying)
IS 'Check pura: la chiave dell''area (schema_db) a cui appartiene un oggetto (app_label, model_name). L''override di config.area_model_overrides se c''e'', altrimenti app_label (area = schema). Un''area non a catalogo si restituisce com''e'': decide fn_resolve_livello_area, che non concede niente. E'' la sede della regola che il backend scrive in PermissionResolver.get_area_schema_db (stessa query): il backend e'' chiamato a passare da qui. La chiama script.fn_guard_livello. STABLE, INVOKER. Brief: brief-db-pannello-config-verbo-generico, sezione 3.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
