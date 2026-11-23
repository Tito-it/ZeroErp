{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_rettifica.md" %}
# ⚙️ Funzione `fn_pgtap_crea_rettifica`

```sql
CREATE FUNCTION fn_pgtap_crea_rettifica(p_magazzino_id bigint, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_rettifica(p_magazzino_id bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una rettifica in DRAFT nel
--   magazzino p_magazzino_id, dal verbo magazzino.fn_aggiungi_rettifica.
--   p_campi: i facoltativi del verbo (data, sorgente_*).
-- Uso: v_ret := dbops.fn_pgtap_crea_rettifica(v_mag);
DECLARE
    v_ov jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id magazzino.rettifiche.id%TYPE;
BEGIN
    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'rettifiche');
    v_id := magazzino.fn_aggiungi_rettifica(p_magazzino_id, COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_rettifica(p_magazzino_id bigint, p_campi jsonb)
IS 'Fixture pgTAP: una rettifica in DRAFT nel magazzino dato, dal verbo magazzino.fn_aggiungi_rettifica, con l''area aperta per il tempo della chiamata. p_campi porta i facoltativi del verbo (data, sorgente_*).';
```

</div>

---
{% include-markdown "signature-core.md" %}
