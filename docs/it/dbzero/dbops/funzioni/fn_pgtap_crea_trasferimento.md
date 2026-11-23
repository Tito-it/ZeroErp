{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_trasferimento.md" %}
# ⚙️ Funzione `fn_pgtap_crea_trasferimento`

```sql
CREATE FUNCTION fn_pgtap_crea_trasferimento(p_magazzino_id_from bigint, p_magazzino_id_to bigint, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_trasferimento(p_magazzino_id_from bigint, p_magazzino_id_to bigint, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un trasferimento in DRAFT dal
--   magazzino p_magazzino_id_from a p_magazzino_id_to (anche lo
--   stesso: un trasferimento fra ubicazioni), dal verbo
--   magazzino.fn_aggiungi_trasferimento. p_campi: i facoltativi
--   del verbo (data, sorgente_*).
-- Uso: v_tr := dbops.fn_pgtap_crea_trasferimento(v_a, v_b);
DECLARE
    v_ov jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id magazzino.trasferimenti.id%TYPE;
BEGIN
    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'trasferimenti');
    v_id := magazzino.fn_aggiungi_trasferimento(
                p_magazzino_id_from, p_magazzino_id_to, COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_trasferimento(p_magazzino_id_from bigint, p_magazzino_id_to bigint, p_campi jsonb)
IS 'Fixture pgTAP: un trasferimento in DRAFT fra i due magazzini dati (anche lo stesso, fra ubicazioni), dal verbo magazzino.fn_aggiungi_trasferimento, con l''area aperta per il tempo della chiamata. p_campi porta i facoltativi del verbo (data, sorgente_*).';
```

</div>

---
{% include-markdown "signature-core.md" %}
