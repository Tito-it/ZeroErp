# ⚙️ Funzione `fn_pgtap_crea_asset`

```sql
CREATE FUNCTION fn_pgtap_crea_asset(p_articolo_id uuid, p_seriale character varying, p_campi jsonb, p_stato_id bigint, p_ownership_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_asset(p_articolo_id uuid, p_seriale character varying, p_campi jsonb DEFAULT '{}'::jsonb, p_stato_id bigint DEFAULT NULL::bigint, p_ownership_id bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un seriale dell'articolo p_articolo_id,
--   dell'emittente dell'operatore in sessione, dal verbo
--   magazzino.fn_aggiungi_asset. Senza stato e proprieta': il primo
--   attivo dei due cataloghi. p_campi: i facoltativi del verbo.
-- Uso: v_sn := dbops.fn_pgtap_crea_asset(v_ser, 'PGT-SN1');
DECLARE
    v_stato magazzino.assets.stato_id%TYPE;
    v_own   magazzino.assets.ownership_id%TYPE;
    v_ov    jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id    magazzino.assets.id%TYPE;
BEGIN
    v_stato := COALESCE(p_stato_id,
                        (SELECT s.id FROM config.stati_assets s
                          WHERE s.attivo ORDER BY s.id LIMIT 1));
    v_own   := COALESCE(p_ownership_id,
                        (SELECT o.id FROM config.assets_ownership o
                          WHERE o.attivo ORDER BY o.id LIMIT 1));

    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'assets');
    v_id := magazzino.fn_aggiungi_asset(
                p_articolo_id, p_seriale, v_stato, v_own, COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_asset(p_articolo_id uuid, p_seriale character varying, p_campi jsonb, p_stato_id bigint, p_ownership_id bigint)
IS 'Fixture pgTAP: un seriale dell''articolo dato e dell''emittente dell''operatore in sessione, dal verbo magazzino.fn_aggiungi_asset, con l''area aperta per il tempo della nascita. Senza stato e proprieta'': il primo attivo di config.stati_assets e config.assets_ownership.';
```

</div>

---
{% include-markdown "signature-core.md" %}
