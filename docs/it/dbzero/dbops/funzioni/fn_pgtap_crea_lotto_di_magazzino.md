# ⚙️ Funzione `fn_pgtap_crea_lotto_di_magazzino`

```sql
CREATE FUNCTION fn_pgtap_crea_lotto_di_magazzino(p_articolo_id uuid, p_codice character varying, p_data_arrivo date, p_campi jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_lotto_di_magazzino(p_articolo_id uuid, p_codice character varying, p_data_arrivo date DEFAULT NULL::date, p_campi jsonb DEFAULT '{}'::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un lotto di magazzino dell'articolo
--   p_articolo_id, dal verbo magazzino.fn_aggiungi_lotto. Senza
--   p_data_arrivo: la data operativa. p_campi: i facoltativi del verbo
--   (data_scadenza, meta).
-- ⚠️ Non e' dbops.fn_pgtap_crea_lotto: quello e' il lotto di fatturazione.
-- Uso: v_lot := dbops.fn_pgtap_crea_lotto_di_magazzino(v_art, 'PGT-L1');
DECLARE
    v_ov jsonb;  -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_id magazzino.lotti.id%TYPE;
BEGIN
    v_ov := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'lotti');
    v_id := magazzino.fn_aggiungi_lotto(
                p_articolo_id, p_codice,
                COALESCE(p_data_arrivo, (SELECT script.fn_data_operativa())),
                COALESCE(p_campi, '{}'::jsonb));
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_lotto_di_magazzino(p_articolo_id uuid, p_codice character varying, p_data_arrivo date, p_campi jsonb)
IS 'Fixture pgTAP: un lotto di magazzino dell''articolo dato, dal verbo magazzino.fn_aggiungi_lotto, con l''area aperta per il tempo della nascita. Senza data di arrivo: la data operativa. Non e'' dbops.fn_pgtap_crea_lotto, che costruisce il lotto di fatturazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
