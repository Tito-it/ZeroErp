# ⚙️ Funzione `fn_pgtap_richiudi_area`

```sql
CREATE FUNCTION fn_pgtap_richiudi_area(p_ricordo jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_richiudi_area(p_ricordo jsonb)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: rimettere l'override d'area com'era prima di
--   dbops.fn_pgtap_apri_area_per_nascita: tolto se l'aveva scritto,
--   coi valori di prima se l'aveva alzato. NULL: niente da rimettere.
-- Uso: PERFORM dbops.fn_pgtap_richiudi_area(v_ricordo);
BEGIN
    IF p_ricordo IS NULL THEN
        RETURN;
    END IF;

    IF (p_ricordo ->> 'nuovo')::boolean THEN
        DELETE FROM config.user_override_aree uoa
         WHERE uoa.id = (p_ricordo ->> 'override_id')::bigint;
    ELSE
        UPDATE config.user_override_aree uoa
           SET livello    = (p_ricordo ->> 'livello')::config.livello_accesso,
               valido_dal = (p_ricordo ->> 'valido_dal')::date,
               valido_al  = (p_ricordo ->> 'valido_al')::date
         WHERE uoa.id = (p_ricordo ->> 'override_id')::bigint;
    END IF;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_richiudi_area(p_ricordo jsonb)
IS 'Fixture pgTAP: rimette l''override d''area com''era prima di dbops.fn_pgtap_apri_area_per_nascita (tolto se l''aveva scritto, coi valori di prima se l''aveva alzato), cosi'' il test ritrova i livelli che aveva. NULL: niente da rimettere.';
```

</div>

---
{% include-markdown "signature-core.md" %}
