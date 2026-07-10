{% include-markdown "it/dbzero/script/manual/fn_available_actions_ddt.md" %}
# ⚙️ Funzione `fn_available_actions_ddt`

```sql
CREATE FUNCTION fn_available_actions_ddt(p_ddt_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_ddt(p_ddt_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: capability DDT per il detail API. Pattern data-driven
--   (config.transizioni_stati_ddt) allineato a
--   fn_available_actions_ordine. push_commessa appesa a mano
--   (azione applicativa, non transizione), riuso fn_list_ddt_da_pushare.
DECLARE
    v_stato_id   vendite.ddt.stato_doc_ddt_id%TYPE;
    v_stato_cod  config.stati_doc_ddt.codice_interno%TYPE;
    v_actions    jsonb;
    v_can_change boolean := false;
    v_push_ok    boolean := false;
    v_push_reason     text := NULL;
    v_push_reason_key text := NULL;
    -- Campi ereditati/sorgente immutabili anche in DRAFT.
    c_non_edit_draft CONSTANT jsonb :=
        '["numero","sorgente_tipo_id","sorgente_uid","billing_account_id"]'::jsonb;
    -- Fuori DRAFT: tutta la testata bloccata.
    c_non_edit_tutti CONSTANT jsonb :=
        '["numero","sorgente_tipo_id","sorgente_uid","billing_account_id",'
        '"destinatario_soggetto_ruolo_id","mittente_soggetto_ruolo_id",'
        '"vettore_soggetto_ruolo_id","causale_trasporto_id","aspetto_bene_id",'
        '"modalita_addebito_trasporto_id","valuta_id","utility_id","data","meta"]'::jsonb;
BEGIN
    -- Stato corrente.
    SELECT d.stato_doc_ddt_id, sdd.codice_interno
      INTO v_stato_id, v_stato_cod
      FROM vendite.ddt d
      JOIN config.stati_doc_ddt sdd ON sdd.id = d.stato_doc_ddt_id
     WHERE d.id = p_ddt_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Transizioni manuali disponibili per lo stato corrente
    -- (attive, manuale=true di default, con action_key+label_key).
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
    FROM config.transizioni_stati_ddt t
    JOIN config.stati_doc_ddt sa ON sa.id = t.stato_a_id
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    v_can_change := jsonb_array_length(v_actions) > 0;

    -- push_commessa: eleggibile se il DDT ha righe pushabili
    -- (fn_list_ddt_da_pushare: tipicamente SPEDITO/CONSEGNATO).
    IF EXISTS (SELECT 1
                 FROM vendite.fn_list_ddt_da_pushare(p_ddt_id := p_ddt_id)) THEN
        v_push_ok := true;
    ELSE
        v_push_reason     := 'DDT_NON_PUSHABILE';
        v_push_reason_key := 'vendite.ddt.push_commessa_reason.non_pushabile';
    END IF;

    IF v_push_ok THEN
        v_actions := v_actions || jsonb_build_array(
            jsonb_build_object(
                'key',              'push_commessa',
                'target_state',     NULL,
                'label_key',        'vendite.ddt.azione_push_commessa',
                'severity',         'success',
                'icon',             'pi pi-arrow-right',
                'requires_confirm', true,
                'outlined',         false
            )
        );
    END IF;

    RETURN jsonb_build_object(
        'available_actions',            v_actions,
        'can_change_state',             v_can_change,
        'can_edit_testata',             (v_stato_cod = 'DRAFT'),
        'can_edit_righe',               (v_stato_cod = 'DRAFT'),
        'can_push_commessa',            v_push_ok,
        'can_push_commessa_reason',     v_push_reason,
        'can_push_commessa_reason_key', v_push_reason_key,
        'non_editable_fields',          CASE WHEN v_stato_cod = 'DRAFT'
                                             THEN c_non_edit_draft
                                             ELSE c_non_edit_tutti END,
        'stato_codice',                 v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_ddt(p_ddt_id bigint)
IS 'Capability DDT per detail API: available_actions (da config.transizioni_stati_ddt, data-driven) + push_commessa (riuso fn_list_ddt_da_pushare) + can_change_state + can_edit_testata/righe + can_push_commessa(+reason) + non_editable_fields + stato_codice. Mirror di fn_available_actions_ordine. rev 2026-07-09.';
```

---
{% include-markdown "signature-core.md" %}
