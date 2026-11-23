{% include-markdown "it/dbzero/magazzino/manual/fn_magazzini_colonne_ammesse.md" %}
# ⚙️ Funzione `fn_magazzini_colonne_ammesse`

```sql
CREATE FUNCTION fn_magazzini_colonne_ammesse(p_gesto text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_magazzini_colonne_ammesse(p_gesto text)
 RETURNS text[]
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Scopo: le colonne di magazzino.magazzini che una persona
    --   compila nel gesto (crea | modifica), in ordine di tabella.
    CASE p_gesto
        WHEN 'crea' THEN
            RETURN ARRAY['codice', 'descrizione', 'indirizzo_dettaglio_id',
                         'predefinito', 'meta', 'usa_ubicazioni'];
        WHEN 'modifica' THEN
            RETURN ARRAY['codice', 'descrizione', 'indirizzo_dettaglio_id',
                         'attivo', 'predefinito', 'meta', 'usa_ubicazioni'];
        ELSE
            PERFORM script.fn_log_and_raise_error(
                'magazzino', 'magazzino.fn_magazzini_colonne_ammesse',
                'E_SCRIPT_CHIAMATA_NON_VALIDA',
                jsonb_build_object('gesto', p_gesto),
                NULL::uuid,
                'magazzino.fn_magazzini_colonne_ammesse',
                'il gesto non e'' crea o modifica');
    END CASE;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_magazzini_colonne_ammesse(p_gesto text)
IS 'Le colonne di magazzino.magazzini che una persona compila nel gesto p_gesto (crea o modifica), nell''ordine della tabella. crea: codice, descrizione, indirizzo_dettaglio_id, predefinito, meta, usa_ubicazioni; modifica: le stesse piu'' attivo. L''emittente non e'' una colonna del form. Sede unica della lista: la leggono magazzino.fn_crea_magazzino, il verbo di modifica del magazzino e il backend. Un gesto diverso: E_SCRIPT_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
