{% include-markdown "it/dbzero/magazzino/manual/fn_assets_colonne_ammesse.md" %}
# ⚙️ Funzione `fn_assets_colonne_ammesse`

```sql
CREATE FUNCTION fn_assets_colonne_ammesse(p_gesto text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_assets_colonne_ammesse(p_gesto text)
 RETURNS text[]
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Scopo: le colonne di magazzino.assets (il seriale) che una
    --   persona compila nel gesto (crea | modifica), in ordine di
    --   tabella. articolo_id ed emittente sono argomenti della
    --   nascita. Modifica: nessuna colonna, non c'e' il verbo.
    CASE p_gesto
        WHEN 'crea' THEN
            RETURN ARRAY['seriale', 'billing_account_id', 'meta',
                         'stato_id', 'ownership_id'];
        WHEN 'modifica' THEN
            RETURN ARRAY[]::text[];
        ELSE
            PERFORM script.fn_log_and_raise_error(
                'magazzino', 'magazzino.fn_assets_colonne_ammesse',
                'E_SCRIPT_CHIAMATA_NON_VALIDA',
                jsonb_build_object('gesto', p_gesto),
                NULL::uuid,
                'magazzino.fn_assets_colonne_ammesse',
                'il gesto non e'' crea o modifica');
    END CASE;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_assets_colonne_ammesse(p_gesto text)
IS 'Le colonne di magazzino.assets (il seriale) che una persona compila nel gesto p_gesto, nell''ordine della tabella. crea: seriale, billing_account_id, meta, stato_id, ownership_id; articolo_id ed emittente sono argomenti del BB di nascita. modifica: nessuna colonna, perche'' il seriale non ha un verbo di modifica. Sede unica della lista: la leggono il BB di nascita e il backend. Un gesto diverso: E_SCRIPT_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
