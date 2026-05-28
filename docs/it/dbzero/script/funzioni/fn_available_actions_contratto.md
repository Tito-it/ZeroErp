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
--   Capability del contratto per il detail API. Allineato al pattern
--   data-driven di fn_available_actions_preventivo e
--   fn_available_actions_offerta: legge le transizioni manuali
--   disponibili da config.transizioni_stati_contratti (matrice
--   introdotta in 20260528-04) invece di stati_doc_contratti.meta.
--
--   Grafo transizioni (guard nel trigger):
--     DRAFT   -> ATTIVO     (attiva, manuale)
--     DRAFT   -> ANNULLATO  (annulla, manuale)
--     ATTIVO  -> CESSATO    (cessa, manuale/job, requires_date)
--     CESSATO / ANNULLATO : terminali, nessuna transizione uscente.
--
--   Arricchimento date per requires_date=true (cessa):
--     default_date = CURRENT_DATE (suggerisce cessazione stasera)
--     min_date     = contratto.valido_dal (invariante di business)
--   Il trigger ammette ATTIVO->CESSATO solo se valido_al e' valorizzato:
--     < CURRENT_DATE → job automatico; >= CURRENT_DATE → cessazione
--     programmata con PATCH valido_al + job pgAgent.
--
--   Editabilita':
--     DRAFT:     tutto (can_edit_testata=true, non_editable_fields=[])
--     ATTIVO:    solo valido_al + meta (can_edit_righe=false)
--     CESSATO / ANNULLATO: nulla (can_edit_testata=false, terminali)
--
--   Fallback sicuro: NULL se contratto non esiste.
DECLARE
    v_stato_id   vendite.contratti.stato_doc_contratto_id%TYPE;
    v_stato_cod  config.stati_doc_contratti.codice_interno%TYPE;
    v_valido_dal vendite.contratti.valido_dal%TYPE;
    v_actions    jsonb;
    v_can_edit   boolean;
    v_can_righe  boolean;
    v_non_edit   jsonb;
    -- Campi bloccati in ATTIVO: tutto tranne valido_al e meta.
    -- Allineati a _CONTRATTO_PATCH_ALLOWED_BY_STATE (contratti_service.py).
    c_non_edit_attivo CONSTANT jsonb :=
        '["billing_account_id","istanza_utility_id","utility_id","ambito",'
        '"valido_dal","parent_contratto_id","data","listino_id",'
        '"tipo_variazione_globale","valore_variazione_globale",'
        '"categoria_cliente_id_snapshot"]'::jsonb;
    -- Tutti i campi testata bloccati in CESSATO e ANNULLATO (terminali).
    c_non_edit_tutti CONSTANT jsonb :=
        '["billing_account_id","istanza_utility_id","utility_id","ambito",'
        '"valido_dal","valido_al","parent_contratto_id","data","listino_id",'
        '"tipo_variazione_globale","valore_variazione_globale",'
        '"categoria_cliente_id_snapshot","meta"]'::jsonb;
BEGIN
    -- Recupera stato corrente e valido_dal (per arricchimento date cessazione).
    SELECT c.stato_doc_contratto_id, sdc.codice_interno, c.valido_dal
      INTO v_stato_id, v_stato_cod, v_valido_dal
      FROM vendite.contratti c
      JOIN config.stati_doc_contratti sdc ON sdc.id = c.stato_doc_contratto_id
     WHERE c.id = p_contratto_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Transizioni manuali disponibili per lo stato corrente.
    -- Pattern identico a fn_available_actions_preventivo/offerta.
    -- COALESCE su meta.manuale: assente = manuale (default true).
    -- Guard meta keys: esclude transizioni con meta incompleto.
    -- Campi extra rispetto a preventivo: requires_date, outlined
    --   (usati solo da contratti; altri domini li ignorano).
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',             t.meta->>'action_key',
                'target_state',    sa.codice_interno,
                'label_key',       t.meta->>'label_key',
                'severity',        t.meta->>'severity',
                'icon',            t.meta->>'icon',
                'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'requires_date',   COALESCE((t.meta->>'requires_date')::boolean, false),
                'outlined',        COALESCE((t.meta->>'outlined')::boolean, false)
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    FROM config.transizioni_stati_contratti t
    JOIN config.stati_doc_contratti sa ON sa.id = t.stato_a_id
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    -- Arricchimento contestuale per azioni con requires_date=true (cessa).
    -- Le date dipendono dal contratto specifico, non dallo stato:
    -- default_date = oggi (cessazione programmata per stasera via job).
    -- min_date = valido_dal del contratto (invariante di business).
    -- Usa jsonb_array_elements per trovare l'azione dinamicamente:
    -- non accoppiato al nome ('cessa') per robustezza futura.
    IF jsonb_array_length(v_actions) > 0 THEN
        SELECT jsonb_agg(
            CASE WHEN (elem->>'requires_date')::boolean IS TRUE
                 THEN elem || jsonb_build_object(
                          'default_date', CURRENT_DATE::text,
                          'min_date',     v_valido_dal::text
                      )
                 ELSE elem
            END
        )
        INTO v_actions
        FROM jsonb_array_elements(v_actions) AS elem;
    END IF;

    -- Capability editabilita' per stato.
    -- can_edit_testata: false per tutti i terminali (CESSATO, ANNULLATO).
    --   Fix bug (20260528): era <>'CESSATO'; ANNULLATO introdotto in
    --   20260520 senza aggiornare questa funzione.
    -- can_edit_righe: solo DRAFT.
    -- non_editable_fields: vuoto in DRAFT, lista parziale in ATTIVO,
    --   lista completa in CESSATO e ANNULLATO.
    v_can_edit  := (v_stato_cod IN ('DRAFT', 'ATTIVO'));
    v_can_righe := (v_stato_cod = 'DRAFT');
    v_non_edit  := CASE v_stato_cod
                       WHEN 'DRAFT'  THEN '[]'::jsonb
                       WHEN 'ATTIVO' THEN c_non_edit_attivo
                       ELSE               c_non_edit_tutti
                   END;

    RETURN jsonb_build_object(
        'available_actions',  v_actions,
        'can_change_state',   jsonb_array_length(v_actions) > 0,
        'can_edit_testata',   v_can_edit,
        'can_edit_righe',     v_can_righe,
        'non_editable_fields', v_non_edit,
        'stato_codice',       v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_contratto(p_contratto_id bigint)
IS 'Capability contratto per detail API: available_actions (da config.transizioni_stati_contratti, pattern data-driven), can_change_state, can_edit_testata/righe, non_editable_fields. DRAFT espone due azioni (attiva + annulla). Arricchimento date per requires_date=true (cessa in ATTIVO). Fix can_edit_testata per ANNULLATO (terminale). rev 2026-05-28.';
```

---
{% include-markdown "signature-core.md" %}
