{% include-markdown "it/dbzero/documenti/manual/fn_crea_bozza_da_versione.md" %}
# ⚙️ Funzione `fn_crea_bozza_da_versione`

```sql
CREATE FUNCTION fn_crea_bozza_da_versione(p_versione_origine_id bigint, p_template_documento_id bigint, p_derivata_da_versione_id bigint, p_titolo text, p_valido_dal date, p_valido_al date, p_attivo boolean, p_meta jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_crea_bozza_da_versione(p_versione_origine_id bigint, p_template_documento_id bigint, p_derivata_da_versione_id bigint DEFAULT NULL::bigint, p_titolo text DEFAULT NULL::text, p_valido_dal date DEFAULT NULL::date, p_valido_al date DEFAULT NULL::date, p_attivo boolean DEFAULT true, p_meta jsonb DEFAULT NULL::jsonb)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: copia la versione p_versione_origine_id in una BOZZA
--   nuova del modello p_template_documento_id, col numero
--   successivo, e ne restituisce l'id (brief-db-modelli-
--   documento-standard §10.3 K-6). Sede unica dei campi che una
--   copia riprende.
DECLARE
    v_origine   documenti.template_documenti_versioni%ROWTYPE;
    v_versione  documenti.template_documenti_versioni.versione%TYPE;
    v_id        documenti.template_documenti_versioni.id%TYPE;
BEGIN
    IF p_versione_origine_id IS NULL OR p_versione_origine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_crea_bozza_da_versione', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_versione_origine_id', 'valore', p_versione_origine_id),
            NULL::uuid, 'p_versione_origine_id obbligatorio e > 0');
    END IF;
    IF p_template_documento_id IS NULL OR p_template_documento_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_crea_bozza_da_versione', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_template_documento_id', 'valore', p_template_documento_id),
            NULL::uuid, 'p_template_documento_id obbligatorio e > 0');
    END IF;

    SELECT * INTO v_origine
      FROM documenti.template_documenti_versioni v
     WHERE v.id = p_versione_origine_id;

    IF v_origine.id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_crea_bozza_da_versione', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_versione_origine_id', 'valore', p_versione_origine_id),
            NULL::uuid, 'p_versione_origine_id: la versione non esiste');
    END IF;

    SELECT COALESCE(max(v.versione), 0) + 1 INTO v_versione
      FROM documenti.template_documenti_versioni v
     WHERE v.template_documento_id = p_template_documento_id;

    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, versione, stato, titolo,
        formato_template, html_template, css_template, markdown_template,
        render_engine_id, page_format, page_orientation,
        margin_top_mm, margin_right_mm, margin_bottom_mm, margin_left_mm,
        valido_dal, valido_al, versione_contesto, context_schema, meta,
        attivo, derivata_da_versione_id)
    VALUES (
        p_template_documento_id, v_versione, 'BOZZA',
        COALESCE(p_titolo, v_origine.titolo),
        v_origine.formato_template, v_origine.html_template,
        v_origine.css_template, v_origine.markdown_template,
        v_origine.render_engine_id, v_origine.page_format, v_origine.page_orientation,
        v_origine.margin_top_mm, v_origine.margin_right_mm,
        v_origine.margin_bottom_mm, v_origine.margin_left_mm,
        p_valido_dal, p_valido_al, v_origine.versione_contesto,
        v_origine.context_schema, COALESCE(p_meta, v_origine.meta),
        COALESCE(p_attivo, true), p_derivata_da_versione_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION documenti.fn_crea_bozza_da_versione(p_versione_origine_id bigint, p_template_documento_id bigint, p_derivata_da_versione_id bigint, p_titolo text, p_valido_dal date, p_valido_al date, p_attivo boolean, p_meta jsonb)
IS 'Copia una versione (qualunque stato) in una BOZZA nuova del modello indicato, col numero successivo di quel modello, e ne restituisce l''id (2026-10-21, brief-db-modelli-documento-standard §10.3 K-6). Copia corpo, motore, pagina, versione_contesto, context_schema e meta; non le date (si fissano alla pubblicazione) e non l''origine, che dichiara il chiamante (p_derivata_da_versione_id). Sostituzioni facoltative: titolo, date, attivo, meta. Sede unica dei campi di una copia: la usano fn_personalizza_template_standard e il clone di una versione del BE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
