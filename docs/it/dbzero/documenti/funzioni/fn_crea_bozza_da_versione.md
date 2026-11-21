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
--   nuova del modello p_template_documento_id e ne restituisce
--   l'id. Sede unica dei campi che una copia riprende.
-- Regole:
--   - la destinazione e' un modello dello stesso documento
--     dell'origine: stessa sorgente, stesso tipo. La regola e'
--     quella di documenti.fn_template_motivo_non_coerente;
--   - il numero non lo sceglie la copia: lo assegna il database
--     alla nascita, il successivo all'ultimo del modello di
--     destinazione, in fila con le altre nascite dello stesso
--     modello (documenti.trgfn_template_documenti_versioni_assegna_numero).
DECLARE
    v_origine        documenti.template_documenti_versioni%ROWTYPE;
    v_orig_tipo      documenti.template_documenti.tipo_documento_output_id%TYPE;
    v_orig_sorgente  documenti.template_documenti.sorgente_tipo_id%TYPE;
    -- il motivo restituito da fn_template_motivo_non_coerente: un codice, non una colonna
    v_motivo         text;
    v_id             documenti.template_documenti_versioni.id%TYPE;
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

    SELECT t.tipo_documento_output_id, t.sorgente_tipo_id
      INTO v_orig_tipo, v_orig_sorgente
      FROM documenti.template_documenti t
     WHERE t.id = v_origine.template_documento_id;

    -- La destinazione e' dello stesso documento dell'origine. La
    -- funzione valuta i motivi in ordine (MODELLO_INESISTENTE,
    -- SORGENTE, TIPO, EMITTENTE): l'emittente non riguarda la copia,
    -- e arriva solo quando sorgente e tipo coincidono.
    v_motivo := documenti.fn_template_motivo_non_coerente(
        p_template_documento_id, v_orig_sorgente, NULL, v_orig_tipo);

    IF v_motivo = 'MODELLO_INESISTENTE' THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_crea_bozza_da_versione', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_template_documento_id', 'valore', p_template_documento_id),
            NULL::uuid, 'p_template_documento_id: il modello non esiste');
    ELSIF v_motivo IN ('SORGENTE', 'TIPO') THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_crea_bozza_da_versione', 'E_DOCUMENTI_COPIA_DOCUMENTO_DIVERSO',
            jsonb_build_object(
                'versione_origine_id',   p_versione_origine_id,
                'template_origine_id',   v_origine.template_documento_id,
                'template_documento_id', p_template_documento_id,
                'motivo',                v_motivo),
            NULL::uuid,
            v_origine.versione::text);
    END IF;

    INSERT INTO documenti.template_documenti_versioni (
        template_documento_id, stato, titolo,
        formato_template, html_template, css_template, markdown_template,
        render_engine_id, page_format, page_orientation,
        margin_top_mm, margin_right_mm, margin_bottom_mm, margin_left_mm,
        valido_dal, valido_al, versione_contesto, context_schema, meta,
        attivo, derivata_da_versione_id)
    VALUES (
        p_template_documento_id, 'BOZZA',
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
IS 'Copia una versione (qualunque stato) in una BOZZA nuova del modello indicato e ne restituisce l''id. Copia corpo, motore, pagina, versione_contesto, context_schema e meta; non le date (si fissano alla pubblicazione) e non l''origine, che dichiara il chiamante (p_derivata_da_versione_id). Sostituzioni facoltative: titolo, date, attivo, meta. La destinazione e'' un modello dello stesso documento dell''origine, stessa sorgente e stesso tipo, con la regola di documenti.fn_template_motivo_non_coerente (E_DOCUMENTI_COPIA_DOCUMENTO_DIVERSO); versione o modello che non esistono: E_PARAMETRO_INVALIDO. Il numero lo assegna il database alla nascita, il successivo all''ultimo del modello (documenti.trgfn_template_documenti_versioni_assegna_numero). Sede unica dei campi di una copia: la usano fn_personalizza_template_standard e il clone di una versione del backend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
