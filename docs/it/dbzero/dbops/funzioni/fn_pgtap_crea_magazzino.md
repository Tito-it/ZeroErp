{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_magazzino.md" %}
# ⚙️ Funzione `fn_pgtap_crea_magazzino`

```sql
CREATE FUNCTION fn_pgtap_crea_magazzino(p_codice character varying, p_usa_ubicazioni boolean, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_magazzino(p_codice character varying, p_usa_ubicazioni boolean DEFAULT false, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un magazzino dell'EMITTENTE DELL'OPERATORE
--   in sessione, con un indirizzo fabbricato e usa_ubicazioni scelto dal
--   test (D-L2-m), dal verbo magazzino.fn_aggiungi_magazzino. p_campi: gli
--   altri facoltativi del verbo (predefinito, meta, ...).
--   Da chiamare DOPO fn_pgtap_set_contesto_operatore.
-- Uso: v_mag := dbops.fn_pgtap_crea_magazzino('PGT-MAG-A', true);
DECLARE
    v_ov jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id magazzino.magazzini.id%TYPE;
BEGIN
    -- L'emittente lo mette il default di sessione: qui si controlla solo
    -- che ci sia, col messaggio di chi ha dimenticato il contesto.
    IF script.fn_pgtap_emittente_operatore() IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_crea_magazzino: nessun emittente per l''operatore in sessione — chiamare prima fn_pgtap_set_contesto_operatore';
    END IF;

    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'magazzini');
    v_id := magazzino.fn_aggiungi_magazzino(
                p_codice,
                'Fixture pgTAP: ' || p_codice,
                dbops.fn_pgtap_crea_indirizzo_dettaglio(p_codice),
                jsonb_build_object('usa_ubicazioni', COALESCE(p_usa_ubicazioni, false))
                    || COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_magazzino(p_codice character varying, p_usa_ubicazioni boolean, p_campi jsonb)
IS 'Fixture pgTAP: un magazzino dell''emittente dell''operatore in sessione, con un indirizzo fabbricato (dbops.fn_pgtap_crea_indirizzo_dettaglio) e usa_ubicazioni scelto dal test; p_campi porta gli altri facoltativi. Nasce dal verbo magazzino.fn_aggiungi_magazzino, con l''area aperta per il tempo della nascita (dbops.fn_pgtap_apri_area_per_nascita). Da chiamare dopo fn_pgtap_set_contesto_operatore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
