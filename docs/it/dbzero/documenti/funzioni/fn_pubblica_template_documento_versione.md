{% include-markdown "it/dbzero/documenti/manual/fn_pubblica_template_documento_versione.md" %}
# ⚙️ Funzione `fn_pubblica_template_documento_versione`

```sql
CREATE FUNCTION fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_valido_al date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION documenti.fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_valido_al date DEFAULT NULL::date)
 RETURNS TABLE(versione_id bigint, template_documento_id bigint, versioni_obsolete integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Pubblica una versione template documento in modo atomico.
--
-- Regole:
--   - la versione target deve esistere ed essere BOZZA;
--   - p_valido_dal e' obbligatorio;
--   - p_valido_al, se valorizzato, non puo' precedere p_valido_dal;
--   - prima della pubblicazione vengono rese OBSOLETE e chiuse a
--     p_valido_dal - 1 le versioni PUBBLICATE attive dello stesso
--     template con valido_dal < p_valido_dal e intervallo sovrapposto;
--   - il vincolo EXCLUDE resta il guardrail finale contro overlap
--     residui o race concorrenti.
DECLARE
    v_template_id  documenti.template_documenti_versioni.template_documento_id%TYPE;
    v_stato        documenti.template_documenti_versioni.stato%TYPE;
    v_closed_ids   bigint[] := ARRAY[]::bigint[];
    v_closed_count integer  := 0;
BEGIN
    IF p_versione_id IS NULL OR p_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO',
            jsonb_build_object('versione_id', p_versione_id),
            NULL::uuid,
            'versione_id deve essere un intero positivo'
        );
    END IF;

    IF p_valido_dal IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO',
            jsonb_build_object('versione_id', p_versione_id),
            NULL::uuid,
            'valido_dal e'' obbligatorio'
        );
    END IF;

    IF p_valido_al IS NOT NULL AND p_valido_al < p_valido_dal THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_PUBBLICA_INPUT_INVALIDO',
            jsonb_build_object(
                'versione_id', p_versione_id,
                'valido_dal',  p_valido_dal,
                'valido_al',   p_valido_al
            ),
            NULL::uuid,
            'valido_al non puo'' precedere valido_dal'
        );
    END IF;

    SELECT v.template_documento_id, v.stato
      INTO v_template_id, v_stato
      FROM documenti.template_documenti_versioni v
     WHERE v.id = p_versione_id
     FOR UPDATE;

    IF v_template_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_NOT_FOUND',
            jsonb_build_object('versione_id', p_versione_id),
            NULL::uuid,
            p_versione_id::text
        );
    END IF;

    IF v_stato <> 'BOZZA' THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO',
            jsonb_build_object(
                'versione_id',   p_versione_id,
                'stato_corrente', v_stato
            ),
            NULL::uuid,
            p_versione_id::text, v_stato
        );
    END IF;

    -- Lock ordinato di tutte le versioni del template: evita race fra
    -- due pubblicazioni concorrenti dello stesso template.
    PERFORM 1
      FROM documenti.template_documenti_versioni v
     WHERE v.template_documento_id = v_template_id
     ORDER BY v.id
     FOR UPDATE;

    SELECT COALESCE(array_agg(c.id ORDER BY c.valido_dal, c.id), ARRAY[]::bigint[])
      INTO v_closed_ids
      FROM (
          SELECT v.id, v.valido_dal
            FROM documenti.template_documenti_versioni v
           WHERE v.template_documento_id = v_template_id
             AND v.id <> p_versione_id
             AND v.stato = 'PUBBLICATA'
             AND v.attivo IS TRUE
             AND v.valido_dal < p_valido_dal
             AND v.validita && daterange(
                     p_valido_dal,
                     COALESCE(p_valido_al, 'infinity'::date),
                     '[]'
                 )
           ORDER BY v.valido_dal, v.id
           FOR UPDATE
      ) c;

    -- Calcola subito: evita GET DIAGNOSTICS post-UPDATE.
    v_closed_count := COALESCE(array_length(v_closed_ids, 1), 0);

    IF v_closed_count > 0 THEN
        -- Il trigger A1 blocca UPDATE OF valido_al quando OLD.stato = PUBBLICATA.
        -- Step 1: porta a OBSOLETA (colonna stato non e' nell''UPDATE OF' del trigger).
        -- Step 2: aggiorna valido_al (ora OLD.stato = OBSOLETA, trigger non blocca).
        UPDATE documenti.template_documenti_versioni
           SET stato = 'OBSOLETA'
         WHERE id = ANY(v_closed_ids);

        UPDATE documenti.template_documenti_versioni
           SET valido_al = p_valido_dal - 1
         WHERE id = ANY(v_closed_ids);
    END IF;

    UPDATE documenti.template_documenti_versioni
       SET stato      = 'PUBBLICATA',
           valido_dal = p_valido_dal,
           valido_al  = p_valido_al
     WHERE id    = p_versione_id
       AND stato = 'BOZZA';

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'documenti',
            'fn_pubblica_template_documento_versione',
            'E_DOCUMENTI_VERSIONE_PUBBLICA_STATO_INVALIDO',
            jsonb_build_object(
                'versione_id',    p_versione_id,
                'stato_corrente', v_stato
            ),
            NULL::uuid,
            p_versione_id::text, v_stato
        );
    END IF;

    versione_id           := p_versione_id;
    template_documento_id := v_template_id;
    versioni_obsolete     := v_closed_count;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION documenti.fn_pubblica_template_documento_versione(p_versione_id bigint, p_valido_dal date, p_valido_al date)
IS 'Pubblica una versione template documento con auto-close atomico delle versioni PUBBLICATE precedenti sovrapposte.';
```

---
{% include-markdown "signature-core.md" %}
