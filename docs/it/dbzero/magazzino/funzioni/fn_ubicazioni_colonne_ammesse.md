# ⚙️ Funzione `fn_ubicazioni_colonne_ammesse`

```sql
CREATE FUNCTION fn_ubicazioni_colonne_ammesse(p_gesto text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_ubicazioni_colonne_ammesse(p_gesto text)
 RETURNS text[]
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- Scopo: le colonne di magazzino.ubicazioni che una persona
    --   compila nel gesto (crea | modifica), in ordine di tabella.
    --   magazzino_id e' l'identita' della nascita: non e' in lista.
    CASE p_gesto
        WHEN 'crea' THEN
            RETURN ARRAY['codice', 'descrizione', 'tipo_id', 'parent_id', 'area',
                         'corsia', 'scaffale', 'piano', 'posizione', 'meta'];
        WHEN 'modifica' THEN
            RETURN ARRAY['codice', 'descrizione', 'tipo_id', 'parent_id', 'area',
                         'corsia', 'scaffale', 'piano', 'posizione', 'attivo', 'meta'];
        ELSE
            PERFORM script.fn_log_and_raise_error(
                'magazzino', 'magazzino.fn_ubicazioni_colonne_ammesse',
                'E_SCRIPT_CHIAMATA_NON_VALIDA',
                jsonb_build_object('gesto', p_gesto),
                NULL::uuid,
                'magazzino.fn_ubicazioni_colonne_ammesse',
                'il gesto non e'' crea o modifica');
    END CASE;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_ubicazioni_colonne_ammesse(p_gesto text)
IS 'Le colonne di magazzino.ubicazioni che una persona compila nel gesto p_gesto (crea o modifica), nell''ordine della tabella. crea: codice, descrizione, tipo_id, parent_id, area, corsia, scaffale, piano, posizione, meta; modifica: le stesse piu'' attivo. magazzino_id e'' l''identita'' della nascita, argomento del BB, e non e'' in lista. Sede unica della lista: la leggono il BB di nascita, il verbo di modifica e il backend. Un gesto diverso: E_SCRIPT_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
