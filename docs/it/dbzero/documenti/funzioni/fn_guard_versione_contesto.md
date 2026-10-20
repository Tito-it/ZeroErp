{% include-markdown "it/dbzero/documenti/manual/fn_guard_versione_contesto.md" %}
# ⚙️ Funzione `fn_guard_versione_contesto`

```sql
CREATE FUNCTION fn_guard_versione_contesto(p_template_versione_id bigint, p_versione_contesto integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION documenti.fn_guard_versione_contesto(p_template_versione_id bigint, p_versione_contesto integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- Scopo: rifiutare la stampa (o la pubblicazione) di una versione di
--   template che legge una forma dei dati diversa da quella dei dati.
--   p_versione_contesto = la forma che i dati HANNO: _meta.context_version
--   del contesto (stampa), la costante del builder (render, pubblicazione).
DECLARE
    v_versione        documenti.template_documenti_versioni.versione%TYPE;
    v_forma_template  documenti.template_documenti_versioni.versione_contesto%TYPE;
    v_template_nome   documenti.template_documenti.descrizione%TYPE;
BEGIN
    IF p_template_versione_id IS NULL OR p_template_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_guard_versione_contesto',
            'E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE',
            jsonb_build_object('template_versione_id', p_template_versione_id,
                               'versione_contesto',    p_versione_contesto),
            NULL::uuid,
            'la versione del template');
    END IF;

    IF p_versione_contesto IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_guard_versione_contesto',
            'E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE',
            jsonb_build_object('template_versione_id', p_template_versione_id),
            NULL::uuid,
            'la forma dichiarata dai dati');
    END IF;

    SELECT v.versione, v.versione_contesto, t.descrizione
      INTO v_versione, v_forma_template, v_template_nome
      FROM documenti.template_documenti_versioni v
      JOIN documenti.template_documenti t ON t.id = v.template_documento_id
     WHERE v.id = p_template_versione_id;

    -- ⚠️ FOUND e non «v_versione IS NULL»: versione e' NOT NULL, ma la
    --    domanda e' «la riga c'e'?», e FOUND e' la risposta diretta.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_guard_versione_contesto',
            'E_DOCUMENTI_VERSIONE_NOT_FOUND',
            jsonb_build_object('template_versione_id', p_template_versione_id),
            NULL::uuid,
            p_template_versione_id::text);
    END IF;

    -- IS DISTINCT FROM: versione_contesto e' NOT NULL (20260930-16), ma un
    --   confronto nudo con un NULL passerebbe in silenzio.
    IF v_forma_template IS DISTINCT FROM p_versione_contesto THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti', 'fn_guard_versione_contesto',
            'E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA',
            jsonb_build_object('template_versione_id',        p_template_versione_id,
                               'versione_contesto_template',  v_forma_template,
                               'versione_contesto_dati',      p_versione_contesto),
            NULL::uuid,
            v_versione::text, v_template_nome,
            coalesce(v_forma_template::text, '?'), p_versione_contesto::text);
    END IF;
END;
$function$

COMMENT ON FUNCTION documenti.fn_guard_versione_contesto(p_template_versione_id bigint, p_versione_contesto integer)
IS 'Il patto fra una versione di template e la forma dei dati che legge: solleva E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA (CONFLITTO_STATO) se template_documenti_versioni.versione_contesto non e'' p_versione_contesto, cioe'' la forma che i dati hanno (_meta.context_version del contesto, o la costante del builder). E_DOCUMENTI_VERSIONE_CONTESTO_NON_VERIFICABILE (TECNICO) se il chiamante non passa la versione o la forma; E_DOCUMENTI_VERSIONE_NOT_FOUND se la versione non c''e'' (o non e'' nel perimetro di chi legge: INVOKER). La chiamano il backend prima del render, il trigger sull''INSERT di documenti.documenti_generati e documenti.fn_pubblica_template_documento_versione. Una BOZZA si controlla solo quando si pubblica o si stampa (D-C4). Brief: brief-db-documenti-versione-contesto-template.';
```

</div>

---
{% include-markdown "signature-core.md" %}
