{% include-markdown "it/dbzero/documenti/manual/fn_personalizza_template_standard.md" %}
# ⚙️ Funzione `fn_personalizza_template_standard`

```sql
CREATE FUNCTION fn_personalizza_template_standard(p_template_standard_id bigint, p_emittente_fiscale_id bigint, p_codice character varying, p_codice_interno character varying, p_descrizione text, p_is_default boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_personalizza_template_standard(p_template_standard_id bigint, p_emittente_fiscale_id bigint, p_codice character varying DEFAULT NULL::character varying, p_codice_interno character varying DEFAULT NULL::character varying, p_descrizione text DEFAULT NULL::text, p_is_default boolean DEFAULT NULL::boolean)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- Scopo: crea il modello dell'emittente p_emittente_fiscale_id
--   dallo standard p_template_standard_id, con la bozza v1 copiata
--   dalla versione con cui lo standard stampa oggi e l'origine
--   dichiarata (brief-db-modelli-documento-standard §10.3 K-6).
--   Restituisce l'id del modello nuovo.
DECLARE
    v_std        documenti.template_documenti%ROWTYPE;
    v_origine_id documenti.template_documenti_versioni.id%TYPE;
    v_is_default documenti.template_documenti.is_default%TYPE;
    v_id         documenti.template_documenti.id%TYPE;
BEGIN
    IF p_template_standard_id IS NULL OR p_template_standard_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_personalizza_template_standard', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_template_standard_id', 'valore', p_template_standard_id),
            NULL::uuid, 'p_template_standard_id obbligatorio e > 0');
    END IF;
    IF p_emittente_fiscale_id IS NULL OR p_emittente_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_personalizza_template_standard', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_emittente_fiscale_id', 'valore', p_emittente_fiscale_id),
            NULL::uuid, 'p_emittente_fiscale_id obbligatorio e > 0');
    END IF;

    SELECT * INTO v_std
      FROM documenti.template_documenti t
     WHERE t.id = p_template_standard_id;

    IF v_std.id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_personalizza_template_standard', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_template_standard_id', 'valore', p_template_standard_id),
            NULL::uuid, 'p_template_standard_id: il modello non esiste');
    END IF;

    IF v_std.standard IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_personalizza_template_standard',
            'E_DOCUMENTI_PERSONALIZZA_NON_STANDARD',
            jsonb_build_object('template_documento_id', p_template_standard_id),
            NULL::uuid,
            v_std.codice::text);
    END IF;

    -- La versione di partenza: quella con cui lo standard stampa
    -- oggi, chiesta alla porta unica (D-9). Solleva lei
    -- E_DOCUMENTI_TEMPLATE_NON_STAMPABILE se non ce n'e'.
    SELECT r.template_versione_id INTO v_origine_id
      FROM documenti.fn_risolvi_template_applicabile(
             v_std.sorgente_tipo_id, p_emittente_fiscale_id,
             v_std.tipo_documento_output_id, v_std.id) r;

    -- D-6: predefinita se l'emittente non ne ha gia' uno suo.
    v_is_default := COALESCE(p_is_default, NOT EXISTS (
        SELECT 1
          FROM documenti.template_documenti t
         WHERE t.emittente_fiscale_id = p_emittente_fiscale_id
           AND t.tipo_documento_output_id = v_std.tipo_documento_output_id
           AND t.sorgente_tipo_id = v_std.sorgente_tipo_id
           AND t.is_default
           AND t.attivo));

    INSERT INTO documenti.template_documenti (
        tipo_documento_output_id, codice, codice_interno, descrizione,
        sorgente_tipo_id, context_builder_code, file_name_pattern,
        emittente_fiscale_id, is_default, attivo)
    VALUES (
        v_std.tipo_documento_output_id,
        COALESCE(p_codice, v_std.codice),
        COALESCE(p_codice_interno, v_std.codice_interno),
        COALESCE(p_descrizione, v_std.descrizione),
        v_std.sorgente_tipo_id, v_std.context_builder_code, v_std.file_name_pattern,
        p_emittente_fiscale_id, v_is_default, true)
    RETURNING id INTO v_id;

    PERFORM documenti.fn_crea_bozza_da_versione(
        p_versione_origine_id     => v_origine_id,
        p_template_documento_id   => v_id,
        p_derivata_da_versione_id => v_origine_id);

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION documenti.fn_personalizza_template_standard(p_template_standard_id bigint, p_emittente_fiscale_id bigint, p_codice character varying, p_codice_interno character varying, p_descrizione text, p_is_default boolean)
IS '«Personalizza» (2026-10-21, brief-db-modelli-documento-standard §10.3 K-6; D-2, D-6, D-9 di Tid): crea il modello di un emittente da uno standard e la sua bozza v1, copiata (fn_crea_bozza_da_versione) dalla versione con cui lo standard stampa oggi, chiesta a fn_risolvi_template_applicabile col modello indicato, con derivata_da_versione_id = quella versione. Solo da uno standard (E_DOCUMENTI_PERSONALIZZA_NON_STANDARD), che stampi oggi (E_DOCUMENTI_TEMPLATE_NON_STAMPABILE). Nasce predefinita se l''emittente non ha gia'' un suo predefinito attivo per la coppia, salvo p_is_default; codice, codice_interno e descrizione dello standard se non indicati. Funzione madre: tutto o niente. Il perimetro dell''emittente lo applica il chiamante. Restituisce l''id del modello nuovo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
