{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_richiudi_area.md" %}
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

    -- prima = NULL (voce che non c'era): la voce si toglie.
    PERFORM dbops.fn_pgtap_scrivi_override(
        'config.user_override_aree'::regclass,
        (p_ricordo ->> 'utente')::integer,
        jsonb_build_object('area_id', (p_ricordo -> 'area_id')),
        NULLIF(p_ricordo -> 'prima', 'null'::jsonb));
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_richiudi_area(p_ricordo jsonb)
IS 'Fixture pgTAP: rimette l''override d''area com''era prima di dbops.fn_pgtap_apri_area_per_nascita (tolto se l''aveva scritto, coi valori di prima se l''aveva alzato), dal verbo del SUPER_ADMIN config.fn_imposta_override_aree (dbops.fn_pgtap_scrivi_override), così il test ritrova i livelli che aveva. NULL: niente da rimettere.';
```

</div>

---
{% include-markdown "signature-core.md" %}
