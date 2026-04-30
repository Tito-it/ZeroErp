{% include-markdown "it/dbzero/script/manual/fn_available_actions_contratto.md" %}
# ⚙️ Funzione `fn_available_actions_contratto`

```sql
CREATE FUNCTION fn_available_actions_contratto(p_contratto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_contratto(p_contratto_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo:
--   Capability del contratto per il detail API (Fase 1 refactor
--   frontend vendite). Legge lo stato corrente e i metadati UI
--   da stati_doc_contratti.meta (campo outgoing_action), aggiunge
--   i valori contestuali per la cessazione (default_date, min_date).
--
--   Grafo transizioni (hardcodato nel trigger DB):
--     DRAFT   -> ATTIVO  (manuale: attiva)
--     ATTIVO  -> CESSATO (manuale: cessa, richiede data)
--                        regola trigger: valido_al < CURRENT_DATE
--                        per data futura il BE fa solo PATCH valido_al
--     CESSATO -> *       terminale
--
--   Editabilita' testata allineata a _CONTRATTO_PATCH_ALLOWED_BY_STATE:
--     DRAFT:   tutto (can_edit_testata=true, non_editable_fields=[])
--     ATTIVO:  solo valido_al + meta (can_edit_testata=true,
--              non_editable_fields elenca i campi bloccati)
--     CESSATO: nulla (can_edit_testata=false)
--
--   Fallback sicuro: NULL se contratto non esiste.
DECLARE
    v_stato_id    vendite.contratti.stato_doc_contratto_id%TYPE;
    v_stato_cod   config.stati_doc_contratti.codice_interno%TYPE;
    v_stato_meta  jsonb;
    v_valido_dal  vendite.contratti.valido_dal%TYPE;
    v_action      jsonb;
    v_actions     jsonb;
    v_can_edit    boolean;
    v_can_righe   boolean;
    v_non_edit    jsonb;
    -- Campi bloccati in ATTIVO: tutto tranne valido_al e meta.
    -- Allineati a _CONTRATTO_PATCH_ALLOWED_BY_STATE (contratti_service.py).
    c_non_edit_attivo CONSTANT jsonb := '["billing_account_id","istanza_utility_id","utility_id","ambito","valido_dal","parent_contratto_id","data","listino_id","tipo_variazione_globale","valore_variazione_globale","categoria_cliente_id_snapshot"]'::jsonb;
    -- Tutti i campi testata bloccati in CESSATO.
    c_non_edit_tutti  CONSTANT jsonb := '["billing_account_id","istanza_utility_id","utility_id","ambito","valido_dal","valido_al","parent_contratto_id","data","listino_id","tipo_variazione_globale","valore_variazione_globale","categoria_cliente_id_snapshot","meta"]'::jsonb;
BEGIN
    -- Recupera stato corrente + valido_dal (per min_date cessazione)
    SELECT c.stato_doc_contratto_id, sdc.codice_interno,
           sdc.meta, c.valido_dal
      INTO v_stato_id, v_stato_cod, v_stato_meta, v_valido_dal
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti sdc ON sdc.id = c.stato_doc_contratto_id
     WHERE c.id = p_contratto_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Costruisce l'azione disponibile dallo stato corrente.
    -- Legge i metadati base da stati_doc_contratti.meta (outgoing_action).
    -- Per CESSATO aggiunge i campi contestuali (date dipendono dal contratto).
    v_action := v_stato_meta -> 'outgoing_action';

    IF v_action IS NOT NULL THEN
        IF (v_action->>'requires_date')::boolean IS TRUE THEN
            -- Cessazione: arricchisce con date contestuali.
            -- default_date = oggi (cessazione programmata per stasera via job).
            -- min_date = valido_dal del contratto (invariante di business).
            v_action := v_action
                || jsonb_build_object(
                    'default_date', CURRENT_DATE::text,
                    'min_date',     v_valido_dal::text
                );
        END IF;
        v_actions := jsonb_build_array(v_action);
    ELSE
        v_actions := '[]'::jsonb;
    END IF;

    -- Capability editabilita' per stato.
    -- can_edit_testata: false solo per CESSATO (terminale).
    -- can_edit_righe: solo DRAFT.
    -- non_editable_fields: vuoto in DRAFT, lista parziale in ATTIVO,
    --   lista completa in CESSATO.
    v_can_edit  := (v_stato_cod <> 'CESSATO');
    v_can_righe := (v_stato_cod = 'DRAFT');
    v_non_edit  := CASE v_stato_cod
                       WHEN 'DRAFT'   THEN '[]'::jsonb
                       WHEN 'ATTIVO'  THEN c_non_edit_attivo
                       ELSE                c_non_edit_tutti
                   END;

    RETURN jsonb_build_object(
        'available_actions',  v_actions,
        'can_change_state',   (v_action IS NOT NULL),
        'can_edit_testata',   v_can_edit,
        'can_edit_righe',     v_can_righe,
        'non_editable_fields', v_non_edit,
        'stato_codice',       v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_contratto(p_contratto_id bigint)
IS 'Capability contratto per detail API: available_actions (da stati_doc_contratti.meta), can_change_state, can_edit_testata/righe, non_editable_fields. Cessazione arricchita con default_date/min_date contestuali. Fase 1 refactor frontend vendite.';
```

---
{% include-markdown "signature-core.md" %}
