{% include-markdown "it/dbzero/documenti/manual/fn_risolvi_template_applicabile.md" %}
# ⚙️ Funzione `fn_risolvi_template_applicabile`

```sql
CREATE FUNCTION fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION documenti.fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(template_documento_id bigint, livello text)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il modello che stampa un documento della sorgente
--   p_sorgente_tipo_id dell'emittente p_emittente_fiscale_id.
--   Strada B (brief-db-modelli-documento-standard §4.1 Q-2): se
--   l'emittente ha modelli attivi per (tipo, sorgente) vale il suo
--   predefinito, e senza predefinito e' un errore; se non ne ha,
--   vale il predefinito standard.
DECLARE
    v_tipo         documenti.template_documenti.tipo_documento_output_id%TYPE;
    -- tipo esplicito: un conteggio, non una colonna
    v_n_tipi       integer;
    v_n_propri     integer;
    v_template_id  documenti.template_documenti.id%TYPE;
    v_tipo_nome    documenti.tipi_documento_output.descrizione%TYPE;
    v_sorgente     config.sorgenti.codice_interno%TYPE;
BEGIN
    -- 0) Argomenti: solo un chiamante rotto li manda male.
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid,
            'p_sorgente_tipo_id (obbligatorio, > 0)');
    END IF;
    IF p_emittente_fiscale_id IS NULL OR p_emittente_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
            jsonb_build_object('emittente_fiscale_id', p_emittente_fiscale_id),
            NULL::uuid,
            'p_emittente_fiscale_id (obbligatorio, > 0: l''emittente del documento)');
    END IF;
    IF p_tipo_documento_output_id IS NOT NULL AND p_tipo_documento_output_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO',
            jsonb_build_object('tipo_documento_output_id', p_tipo_documento_output_id),
            NULL::uuid,
            'p_tipo_documento_output_id (> 0 se indicato)');
    END IF;

    -- 1) Il tipo di documento. Indicato: vale quello. Non indicato:
    --    si deduce solo se e' uno fra i modelli attivi della sorgente
    --    che questo emittente puo' usare (i suoi e gli standard).
    v_tipo := p_tipo_documento_output_id;
    IF v_tipo IS NULL THEN
        SELECT count(DISTINCT t.tipo_documento_output_id)::integer,
               min(t.tipo_documento_output_id)
          INTO v_n_tipi, v_tipo
          FROM documenti.template_documenti t
         WHERE t.sorgente_tipo_id = p_sorgente_tipo_id
           AND t.attivo
           AND (t.emittente_fiscale_id = p_emittente_fiscale_id OR t.standard);

        IF v_n_tipi > 1 THEN
            SELECT s.codice_interno INTO v_sorgente
              FROM config.sorgenti s
             WHERE s.id = p_sorgente_tipo_id;
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'fn_risolvi_template_applicabile',
                'E_DOCUMENTI_TEMPLATE_AMBIGUO',
                jsonb_build_object(
                    'sorgente_tipo_id',     p_sorgente_tipo_id,
                    'emittente_fiscale_id', p_emittente_fiscale_id,
                    'tipi_candidati',       v_n_tipi),
                NULL::uuid,
                coalesce(v_sorgente::text, p_sorgente_tipo_id::text));
        END IF;
    END IF;

    IF v_tipo IS NOT NULL THEN
        SELECT o.descrizione INTO v_tipo_nome
          FROM documenti.tipi_documento_output o
         WHERE o.id = v_tipo;
    END IF;

    -- 2) Livello EMITTENTE: decide la presenza di modelli attivi
    --    suoi, non il predefinito (strada B).
    SELECT count(*)::integer
      INTO v_n_propri
      FROM documenti.template_documenti t
     WHERE t.tipo_documento_output_id = v_tipo
       AND t.sorgente_tipo_id = p_sorgente_tipo_id
       AND t.emittente_fiscale_id = p_emittente_fiscale_id
       AND t.attivo;

    IF v_n_propri > 0 THEN
        SELECT t.id INTO v_template_id
          FROM documenti.template_documenti t
         WHERE t.tipo_documento_output_id = v_tipo
           AND t.sorgente_tipo_id = p_sorgente_tipo_id
           AND t.emittente_fiscale_id = p_emittente_fiscale_id
           AND t.attivo
           AND t.is_default;
        -- uq_template_documenti_default_attivo: al massimo uno.

        IF NOT FOUND THEN
            PERFORM script.fn_log_and_raise_error(
                'documenti', 'fn_risolvi_template_applicabile',
                'E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO',
                jsonb_build_object(
                    'tipo_documento_output_id', v_tipo,
                    'sorgente_tipo_id',         p_sorgente_tipo_id,
                    'emittente_fiscale_id',     p_emittente_fiscale_id,
                    'modelli_attivi',           v_n_propri),
                NULL::uuid,
                coalesce(v_tipo_nome::text, '?'));
        END IF;

        template_documento_id := v_template_id;
        livello := 'EMITTENTE';
        RETURN NEXT;
        RETURN;
    END IF;

    -- 3) Livello STANDARD.
    SELECT t.id INTO v_template_id
      FROM documenti.template_documenti t
     WHERE t.tipo_documento_output_id = v_tipo
       AND t.sorgente_tipo_id = p_sorgente_tipo_id
       AND t.standard
       AND t.attivo
       AND t.is_default;
    -- uq_template_documenti_default_attivo (NULLS NOT DISTINCT): al massimo uno.

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_risolvi_template_applicabile',
            'E_DOCUMENTI_TEMPLATE_NON_RISOLTO',
            jsonb_build_object(
                'tipo_documento_output_id', v_tipo,
                'sorgente_tipo_id',         p_sorgente_tipo_id,
                'emittente_fiscale_id',     p_emittente_fiscale_id),
            NULL::uuid,
            coalesce(v_tipo_nome::text, '?'));
    END IF;

    template_documento_id := v_template_id;
    livello := 'STANDARD';
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION documenti.fn_risolvi_template_applicabile(p_sorgente_tipo_id bigint, p_emittente_fiscale_id bigint, p_tipo_documento_output_id bigint)
IS 'Il modello che stampa un documento (2026-10-20, brief-db-modelli-documento-standard §4.1 Q-2, strada B di Tid). Livello EMITTENTE se l''emittente del documento ha modelli attivi per (tipo, sorgente): vale il suo predefinito attivo, e senza predefinito E_DOCUMENTI_TEMPLATE_SENZA_PREDEFINITO (lo standard non entra). Livello STANDARD se non ne ha: il predefinito attivo standard, altrimenti E_DOCUMENTI_TEMPLATE_NON_RISOLTO. Tipo di output facoltativo: si deduce solo se fra i modelli attivi della sorgente utilizzabili dall''emittente ce n''e'' uno solo, altrimenti E_DOCUMENTI_TEMPLATE_AMBIGUO. Argomenti rotti: E_DOCUMENTI_RISOLVI_TEMPLATE_INPUT_INVALIDO. L''emittente e'' quello del documento, gia'' letto sotto RLS dal chiamante: niente scope qui. Restituisce una riga (template_documento_id, livello).';
```

---
{% include-markdown "signature-core.md" %}
