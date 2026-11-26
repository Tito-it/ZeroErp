{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_riga_rettifica.md" %}
# ⚙️ Funzione `fn_pgtap_crea_riga_rettifica`

```sql
CREATE FUNCTION fn_pgtap_crea_riga_rettifica(p_rettifica_id bigint, p_articolo_id uuid, p_qta_delta numeric, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_riga_rettifica(p_rettifica_id bigint, p_articolo_id uuid, p_qta_delta numeric, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una riga della rettifica
--   p_rettifica_id (in DRAFT), dal verbo
--   magazzino.fn_aggiungi_riga_rettifica. p_campi: motivo,
--   ubicazione_id, lotto_id, asset_id, costo_unitario.
-- Uso: PERFORM dbops.fn_pgtap_crea_riga_rettifica(v_ret, v_art, -2);
DECLARE
    v_ov jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id magazzino.rettifiche_righe.id%TYPE;
BEGIN
    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'rettifiche');
    v_id := magazzino.fn_aggiungi_riga_rettifica(
                p_rettifica_id, p_articolo_id, p_qta_delta, COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_riga_rettifica(p_rettifica_id bigint, p_articolo_id uuid, p_qta_delta numeric, p_campi jsonb)
IS 'Fixture pgTAP: una riga della rettifica data, dal verbo magazzino.fn_aggiungi_riga_rettifica, con l''area del documento aperta per il tempo della chiamata. p_campi porta i facoltativi (motivo, ubicazione_id, lotto_id, asset_id, costo_unitario).';
```

</div>

---
{% include-markdown "signature-core.md" %}
