{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_riga_trasferimento.md" %}
# ⚙️ Funzione `fn_pgtap_crea_riga_trasferimento`

```sql
CREATE FUNCTION fn_pgtap_crea_riga_trasferimento(p_trasferimento_id bigint, p_articolo_id uuid, p_qta numeric, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_riga_trasferimento(p_trasferimento_id bigint, p_articolo_id uuid, p_qta numeric, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP una riga del trasferimento
--   p_trasferimento_id (in DRAFT), dal verbo
--   magazzino.fn_aggiungi_riga_trasferimento. p_campi: lotto_id,
--   asset_id, ubicazione_id_da, ubicazione_id_a.
-- Uso: PERFORM dbops.fn_pgtap_crea_riga_trasferimento(v_tr, v_art, 4, jsonb_build_object('ubicazione_id_da', v_u1));
DECLARE
    v_ov jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id magazzino.trasferimenti_righe.id%TYPE;
BEGIN
    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'trasferimenti');
    v_id := magazzino.fn_aggiungi_riga_trasferimento(
                p_trasferimento_id, p_articolo_id, p_qta, COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_riga_trasferimento(p_trasferimento_id bigint, p_articolo_id uuid, p_qta numeric, p_campi jsonb)
IS 'Fixture pgTAP: una riga del trasferimento dato, dal verbo magazzino.fn_aggiungi_riga_trasferimento, con l''area del documento aperta per il tempo della chiamata. p_campi porta i facoltativi (lotto_id, asset_id, ubicazione_id_da, ubicazione_id_a).';
```

</div>

---
{% include-markdown "signature-core.md" %}
