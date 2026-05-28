{% include-markdown "it/dbzero/script/manual/fn_available_actions_preventivo.md" %}
# ⚙️ Funzione `fn_available_actions_preventivo`

```sql
CREATE FUNCTION fn_available_actions_preventivo(p_preventivo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_preventivo(p_preventivo_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo:
--   Capability del preventivo per il detail API (Fase 1 refactor
--   frontend vendite). Calcola le transizioni manuali disponibili
--   leggendo la matrice config.transizioni_stati_preventivi (campo
--   meta per i metadati UI). Aggiunge hardcoded le azioni speciali
--   non-cambio-stato (pattern fn_available_actions_offerta):
--     - crea_revisione (solo EMESSO): produce rev.N+1 in BOZZA.
--     - push_commessa (solo ACCETTATO): avvia commessa vendita.
--   Restituisce anche i flag can_* usati dai drawer Vue per
--   abilitare/disabilitare azioni e campi senza ricalcolare logica
--   in Python o nel frontend.
--
--   Struttura meta attesa su ogni transizione (80_data seed):
--     action_key:       chiave azione (es. 'emetti', 'annulla')
--     label_key:        chiave i18n per il label del bottone
--     severity:         severity PrimeVue (info/success/danger)
--     icon:             classe PrimeIcons (es. 'pi pi-send')
--     requires_confirm: boolean — richiede dialog di conferma
--     manuale:          boolean — false esclude dalla lista UI
--                       (transizione automatica da job/trigger)
--
--   Fallback sicuro: NULL se il preventivo non esiste.
DECLARE
    v_stato_id        vendite.preventivi.stato_doc_preventivo_id%TYPE;
    v_stato_cod       config.stati_doc_preventivi.codice_interno%TYPE;
    v_actions         jsonb;
    v_can_edit        boolean;
    v_can_push        boolean;
    v_can_rev         boolean;
    v_push_reason     text;
    v_push_reason_key text;
    -- Due famiglie di immutabilita':
    -- (a) c_sempre_non_edit: campi immutabili dal create
    --     indipendentemente dallo stato (regola di dominio).
    --     utility_id identifica il preventivo, non si cambia mai.
    -- (b) c_non_edit_extra: campi bloccati solo fuori DRAFT
    --     (whitelist aggiorna_preventivo in preventivi_service.py).
    c_sempre_non_edit CONSTANT jsonb := '["utility_id"]'::jsonb;
    c_non_edit_extra  CONSTANT jsonb := '["billing_account_id","istanza_utility_id","valuta_id","termine_pagamento_id","validita_dal","validita_al","competenza_mese","fatturazione_immediata","meta"]'::jsonb;

    -- Azione speciale hardcoded: crea_revisione (EMESSO).
    -- Non e' una transizione di stato: produce rev.N+1 in BOZZA
    -- e marca rev.N corrente SUPERATA via trigger z90.
    -- icon pi pi-clone: coerente con fn_available_actions_offerta.
    c_action_crea_revisione CONSTANT jsonb := jsonb_build_object(
        'key',                  'crea_revisione',
        'target_state',         NULL,
        'label_key',            'preventivi.azione_crea_revisione',
        'severity',             'info',
        'icon',                 'pi pi-clone',
        'requires_confirm',     true,
        'requires_motivazione', false
    );

    -- Azione speciale hardcoded: push_commessa (ACCETTATO).
    -- Non e' una transizione di stato: avvia la commessa vendita.
    -- Gate v1: solo stato ACCETTATO (no check cross-dominio in v1).
    c_action_push_commessa CONSTANT jsonb := jsonb_build_object(
        'key',                  'push_commessa',
        'target_state',         NULL,
        'label_key',            'preventivi.azione_push_commessa',
        'severity',             'info',
        'icon',                 'pi pi-arrow-right',
        'requires_confirm',     true,
        'requires_motivazione', false
    );
BEGIN
    -- Recupera stato corrente del preventivo.
    SELECT p.stato_doc_preventivo_id, sdp.codice_interno
      INTO v_stato_id, v_stato_cod
      FROM vendite.preventivi p
      JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
     WHERE p.id = p_preventivo_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Transizioni manuali disponibili per lo stato corrente.
    -- COALESCE su meta.manuale: se assente si assume manuale = true.
    -- Guard meta keys: esclude transizioni manuali con meta incompleto
    --   (defense-in-depth su ck_transizioni_stati_prev_meta_ui).
    -- COALESCE su meta.requires_confirm: se assente si assume false.
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',              t.meta->>'action_key',
                'target_state',     sa.codice_interno,
                'label_key',        t.meta->>'label_key',
                'severity',         t.meta->>'severity',
                'icon',             t.meta->>'icon',
                'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, false)
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    FROM config.transizioni_stati_preventivi t
    JOIN config.stati_doc_preventivi sa ON sa.id = t.stato_a_id
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    -- Capability derivate dallo stato corrente.
    -- can_edit: solo DRAFT (allineato a _STATI_MODIFICABILI Python).
    -- can_push_commessa: solo ACCETTATO (check cross-dominio in Fase 3).
    -- can_create_revisione: SOLO EMESSO (rev 03-05-2026: ACCETTATO
    --   chiude la negoziazione, non rivisitabile - allineato a
    --   vendite.fn_crea_revisione_preventivo).
    v_can_edit := (v_stato_cod = 'DRAFT');
    v_can_push := (v_stato_cod = 'ACCETTATO');
    v_can_rev  := (v_stato_cod = 'EMESSO');

    -- Appende crea_revisione hardcoded: solo in EMESSO.
    IF v_can_rev THEN
        v_actions := v_actions || jsonb_build_array(c_action_crea_revisione);
    END IF;

    -- Appende push_commessa hardcoded: solo in ACCETTATO.
    IF v_can_push THEN
        v_actions := v_actions || jsonb_build_array(c_action_push_commessa);
    END IF;

    -- Reason code (machine-readable) + chiave i18n associata.
    -- Coppia stabile reason/reason_key: il FE traduce via key,
    -- il BE/log usa il reason. In Fase 3 si estendera' il CASE
    -- per nuovi motivi (commesse pushate, approvazioni pendenti).
    IF v_can_push THEN
        v_push_reason     := NULL;
        v_push_reason_key := NULL;
    ELSE
        v_push_reason     := 'PREVENTIVO_NON_ACCETTATO';
        v_push_reason_key := 'preventivi.push_commessa_reason.non_accettato';
    END IF;

    RETURN jsonb_build_object(
        'available_actions',            v_actions,
        'can_edit_testata',             v_can_edit,
        'can_edit_righe',               v_can_edit,
        'can_push_commessa',            v_can_push,
        'can_push_commessa_reason',     v_push_reason,
        'can_push_commessa_reason_key', v_push_reason_key,
        'can_create_revisione',         v_can_rev,
        'non_editable_fields',          CASE WHEN v_can_edit
                                            THEN c_sempre_non_edit
                                            ELSE c_sempre_non_edit || c_non_edit_extra END,
        'stato_codice',                 v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_preventivo(p_preventivo_id bigint)
IS 'Capability preventivo per detail API: available_actions (da matrice transizioni + azioni hardcoded crea_revisione/push_commessa), can_edit_*, can_push_commessa, can_create_revisione, non_editable_fields. rev 03-05-2026: can_create_revisione solo da EMESSO. rev 11-05-2026: WHERE guard meta ?''action_key'' + ?''label_key''. rev 28-05-2026: append hardcoded crea_revisione (EMESSO) e push_commessa (ACCETTATO) in available_actions (pattern offerta).';
```

---
{% include-markdown "signature-core.md" %}
