{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_inventario.md" %}
# ⚙️ Funzione `fn_pgtap_crea_inventario`

```sql
CREATE FUNCTION fn_pgtap_crea_inventario(p_magazzino_id bigint, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_inventario(p_magazzino_id bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un inventario in DRAFT nel
--   magazzino p_magazzino_id, dal verbo magazzino.fn_aggiungi_inventario.
--   p_campi: i facoltativi del verbo (data, descrizione, sorgente_*).
--   Da chiamare DOPO fn_pgtap_set_contesto_operatore.
-- Uso: v_inv := dbops.fn_pgtap_crea_inventario(v_mag);
DECLARE
    v_ov jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id magazzino.inventari.id%TYPE;
BEGIN
    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'inventari');
    v_id := magazzino.fn_aggiungi_inventario(p_magazzino_id, COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_inventario(p_magazzino_id bigint, p_campi jsonb)
IS 'Fixture pgTAP: un inventario in DRAFT nel magazzino dato, dal verbo magazzino.fn_aggiungi_inventario, con l''area aperta per il tempo della chiamata (dbops.fn_pgtap_apri_area_per_nascita). p_campi porta i facoltativi del verbo (data, descrizione, sorgente_*). Da chiamare dopo fn_pgtap_set_contesto_operatore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
