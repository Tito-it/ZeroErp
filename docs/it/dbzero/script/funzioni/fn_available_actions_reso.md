# ⚙️ Funzione `fn_available_actions_reso`

```sql
CREATE FUNCTION fn_available_actions_reso(p_reso_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_reso(p_reso_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: capability reso per il detail API (data-driven,
--   config.transizioni_stati_reso). Mirror ridotto di
--   fn_available_actions_ddt (no push_commessa, no pdf).
DECLARE
    v_stato_id   vendite.resi.stato_doc_reso_id%TYPE;
    v_stato_cod  config.stati_doc_reso.codice_interno%TYPE;
    v_actions    jsonb;
    v_can_change boolean := false;
    c_non_edit_draft CONSTANT jsonb :=
        '["numero","sorgente_tipo_id","sorgente_uid","billing_account_id","emittente_fiscale_id"]'::jsonb;
    c_non_edit_tutti CONSTANT jsonb :=
        '["numero","sorgente_tipo_id","sorgente_uid","billing_account_id","emittente_fiscale_id",'
        '"destinatario_soggetto_ruolo_id","valuta_id","utility_id","data","meta"]'::jsonb;
BEGIN
    SELECT r.stato_doc_reso_id, sdr.codice_interno
      INTO v_stato_id, v_stato_cod
      FROM vendite.resi r
      JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
     WHERE r.id = p_reso_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',              t.meta->>'action_key',
                'target_state',     sa.codice_interno,
                'label_key',        t.meta->>'label_key',
                'severity',         t.meta->>'severity',
                'icon',             t.meta->>'icon',
                'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'outlined',         COALESCE((t.meta->>'outlined')::boolean, false)
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    FROM config.transizioni_stati_reso t
    JOIN config.stati_doc_reso sa ON sa.id = t.stato_a_id
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    v_can_change := jsonb_array_length(v_actions) > 0;

    RETURN jsonb_build_object(
        'available_actions',   v_actions,
        'can_change_state',    v_can_change,
        'can_edit_testata',    (v_stato_cod = 'DRAFT'),
        'can_edit_righe',      (v_stato_cod = 'DRAFT'),
        'non_editable_fields', CASE WHEN v_stato_cod = 'DRAFT'
                                    THEN c_non_edit_draft
                                    ELSE c_non_edit_tutti END,
        'stato_codice',        v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_reso(p_reso_id bigint)
IS 'Capability reso per detail API: available_actions (matrice transizioni_stati_reso, filtro manuale) + can_change_state + can_edit_* + non_editable_fields + stato_codice. Mirror ridotto di fn_available_actions_ddt (no push/pdf). rev 2026-07-13.';
```

---
{% include-markdown "signature-core.md" %}
