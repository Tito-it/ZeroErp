{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_cambia_stato_documento_interno.md" %}
# ⚙️ Funzione `fn_pgtap_cambia_stato_documento_interno`

```sql
CREATE FUNCTION fn_pgtap_cambia_stato_documento_interno(p_famiglia text, p_documento_id bigint, p_stato text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_cambia_stato_documento_interno(p_famiglia text, p_documento_id bigint, p_stato text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
-- Scopo: portare in una fixture pgTAP il documento interno
--   p_documento_id della famiglia p_famiglia allo stato p_stato
--   (conferma, riapri, annulla), dal verbo
--   magazzino.fn_cambia_stato_documento_interno. Ritorna lo stato.
-- Uso: PERFORM dbops.fn_pgtap_cambia_stato_documento_interno('INVENTARIO', v_inv, 'CONFIRM');
DECLARE
    v_tabella text;  -- il nome dal registro: nessuna colonna
    v_ov      jsonb; -- il ricordo di fn_pgtap_apri_area_per_nascita
    v_stato   text;  -- lo stato della famiglia: tre colonne, nessuna sola da ancorare
BEGIN
    SELECT f.tabella INTO v_tabella
      FROM magazzino.fn_documento_interno_famiglia(p_famiglia) AS f;
    IF v_tabella IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_cambia_stato_documento_interno: famiglia % sconosciuta (INVENTARIO | RETTIFICA | TRASFERIMENTO)', p_famiglia;
    END IF;

    v_ov    := dbops.fn_pgtap_apri_area_per_nascita('magazzino', v_tabella);
    v_stato := magazzino.fn_cambia_stato_documento_interno(p_famiglia, p_documento_id, p_stato);
    PERFORM dbops.fn_pgtap_richiudi_area(v_ov);
    RETURN v_stato;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_cambia_stato_documento_interno(p_famiglia text, p_documento_id bigint, p_stato text)
IS 'Fixture pgTAP: porta il documento interno dato (famiglia INVENTARIO, RETTIFICA, TRASFERIMENTO) allo stato chiesto, dal verbo magazzino.fn_cambia_stato_documento_interno, con l''area del documento aperta per il tempo della chiamata. La matrice la fa rispettare il trigger: un rifiuto risale al test col suo codice. Ritorna lo stato scritto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
