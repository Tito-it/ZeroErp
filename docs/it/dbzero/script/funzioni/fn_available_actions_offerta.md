{% include-markdown "it/dbzero/script/manual/fn_available_actions_offerta.md" %}
# ⚙️ Funzione `fn_available_actions_offerta`

```sql
CREATE FUNCTION fn_available_actions_offerta(p_offerta_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_offerta(p_offerta_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo:
--   Capability dell'offerta commerciale per il detail API (pattern
--   data-driven capability layer, specchio di fn_available_actions_preventivo).
--   Calcola le transizioni manuali disponibili leggendo la matrice
--   config.stati_doc_offerte_transizioni (campo meta: action_key /
--   label_key / severity / icon / requires_confirm / requires_motivazione
--   / manuale). Aggiunge hardcoded le azioni speciali non-cambio-stato:
--     - crea_revisione (solo EMESSA): produce rev.N+1 in BOZZA.
--     - push_contratto (solo ACCETTATA senza contratto generato):
--       genera un contratto DRAFT.
--   Restituisce anche i flag can_* usati dai drawer Vue per
--   abilitare/disabilitare azioni e campi senza ricalcolare logica
--   in Python o nel frontend.
--
--   Struttura meta attesa su ogni transizione (seed CSV 20260524-22):
--     action_key:           chiave azione (es. 'emetti', 'annulla')
--     label_key:            chiave i18n per il label del bottone
--     severity:             severity PrimeVue (info/success/danger)
--     icon:                 classe PrimeIcons (es. 'pi pi-send')
--     requires_confirm:     boolean - richiede dialog di conferma
--     requires_motivazione: boolean - richiede campo motivazione
--     manuale:              boolean - false esclude dalla lista UI
--
--   Fallback sicuro: NULL se l'offerta non esiste (gestito BE come 404).
DECLARE
    v_stato_id    vendite.offerte_commerciali.stato_doc_offerta_id%TYPE;
    v_stato_cod   config.stati_doc_offerte.codice_interno%TYPE;
    v_actions     jsonb;
    v_can_edit    boolean;
    v_can_push    boolean;
    v_push_reason     text;
    v_push_reason_key text;
    v_can_rev     boolean;

    -- Campi sempre immutabili: gestiti dal trigger di transizione stato.
    -- Includono i timestamp valorizzati automaticamente e i campi identita'.
    c_sempre_non_edit CONSTANT jsonb :=
        '["codice","uid","revisione_numero","revisione_padre_id",'
        '"stato_doc_offerta_id","data_emissione","data_accettazione",'
        '"data_rifiuto","data_annullamento","motivazione_rifiuto"]'::jsonb;

    -- Campi bloccati fuori BOZZA (whitelist testata editabile solo in BOZZA).
    c_non_edit_extra CONSTANT jsonb :=
        '["emittente_fiscale_id","billing_account_id","istanza_utility_id",'
        '"utility_id","listino_id","listino_versione_id",'
        '"valore_variazione_globale","tipo_variazione_globale",'
        '"validita_dal","validita_al","meta"]'::jsonb;

    -- Azione speciale hardcoded: crea_revisione (EMESSA).
    -- Non e' una transizione di stato: produce rev.N+1 in BOZZA
    -- e marca la rev.N corrente SUPERATA via trigger z90.
    c_action_crea_revisione CONSTANT jsonb := jsonb_build_object(
        'key',                'crea_revisione',
        'target_state',       NULL,
        'label_key',          'vendite.offerte.azione_crea_revisione',
        'severity',           'info',
        'icon',               'pi pi-clone',
        'requires_confirm',   true,
        'requires_motivazione', false
    );

    -- Azione speciale hardcoded: push_contratto (ACCETTATA senza contratto).
    -- Non e' una transizione di stato: genera un contratto DRAFT
    -- tramite vendite.fn_push_offerta_a_contratto (1:1 eccezioni + utility).
    c_action_push_contratto CONSTANT jsonb := jsonb_build_object(
        'key',                'push_contratto',
        'target_state',       NULL,
        'label_key',          'vendite.offerte.azione_push_contratto',
        'severity',           'success',
        'icon',               'pi pi-arrow-right',
        'requires_confirm',   true,
        'requires_motivazione', false
    );

BEGIN
    -- Recupera stato corrente dell'offerta.
    SELECT o.stato_doc_offerta_id, sdo.codice_interno
      INTO v_stato_id, v_stato_cod
      FROM vendite.offerte_commerciali o
      JOIN config.stati_doc_offerte sdo ON sdo.id = o.stato_doc_offerta_id
     WHERE o.id = p_offerta_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Transizioni manuali disponibili per lo stato corrente.
    -- COALESCE su meta.manuale: se assente si assume manuale = true
    --   (compatibile con seed senza campo esplicito manuale=true).
    -- COALESCE su requires_confirm / requires_motivazione: default false.
    -- Filtro defense-in-depth: esclude righe con action_key o label_key
    --   mancanti (paralle con ck_transizioni_stati_prev_meta_ui dei preventivi).
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',                t.meta->>'action_key',
                'target_state',       sa.codice_interno,
                'label_key',          t.meta->>'label_key',
                'severity',           t.meta->>'severity',
                'icon',               t.meta->>'icon',
                'requires_confirm',   COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'requires_motivazione', COALESCE((t.meta->>'requires_motivazione')::boolean, false)
            )
            ORDER BY sa.ordine
        ),
        '[]'::jsonb
    )
    INTO v_actions
    FROM config.stati_doc_offerte_transizioni t
    JOIN config.stati_doc_offerte sa ON sa.id = t.stato_a_id
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, true) IS TRUE
      AND t.meta ? 'action_key'
      AND t.meta ? 'label_key';

    -- Aggiunge crea_revisione hardcoded: solo in EMESSA (addendum A2).
    -- In EMESSA il cliente non ha ancora deciso: la revisione permette
    -- di ritrattare le condizioni senza perdere la tracciabilita'.
    v_can_rev := (v_stato_cod = 'EMESSA');
    IF v_can_rev THEN
        v_actions := v_actions || jsonb_build_array(c_action_crea_revisione);
    END IF;

    -- can_push_contratto: ACCETTATA + nessun contratto gia' generato.
    -- Check cross-dominio su vendite.contratti.offerta_id (UNIQUE idempotenza
    -- pattern A). A differenza di can_push_commessa del preventivo (solo stato),
    -- qui il check cross-dominio e' in v1 perche' l'idempotenza e' strutturale
    -- e il caso "contratto gia' generato" e' atteso nel normale flusso operativo.
    IF v_stato_cod = 'ACCETTATA' THEN
        IF NOT EXISTS (
            SELECT 1 FROM vendite.contratti WHERE offerta_id = p_offerta_id
        ) THEN
            v_can_push        := true;
            v_push_reason     := NULL;
            v_push_reason_key := NULL;
            -- push_contratto appare in available_actions solo quando abilitato.
            v_actions := v_actions || jsonb_build_array(c_action_push_contratto);
        ELSE
            v_can_push        := false;
            v_push_reason     := 'OFFERTA_CONTRATTO_GIA_GENERATO';
            v_push_reason_key := 'offerte.push_reason.gia_generato';
        END IF;
    ELSE
        v_can_push        := false;
        v_push_reason     := 'OFFERTA_NON_ACCETTATA';
        v_push_reason_key := 'offerte.push_reason.non_accettata';
    END IF;

    -- Editabilita': solo in BOZZA.
    -- Testata, eccezioni e utility 1:1 sono tutti bloccati fuori BOZZA.
    v_can_edit := (v_stato_cod = 'BOZZA');

    RETURN jsonb_build_object(
        'available_actions',             v_actions,
        'can_change_state',              jsonb_array_length(v_actions) > 0,
        'can_edit_testata',              v_can_edit,
        'can_edit_eccezioni',            v_can_edit,
        'can_edit_utility',              v_can_edit,
        'can_create_revisione',          v_can_rev,
        'can_push_contratto',            v_can_push,
        'can_push_contratto_reason',     v_push_reason,
        'can_push_contratto_reason_key', v_push_reason_key,
        'non_editable_fields',           CASE WHEN v_can_edit
                                             THEN c_sempre_non_edit
                                             ELSE c_sempre_non_edit || c_non_edit_extra END,
        'stato_codice',                  v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_offerta(p_offerta_id bigint)
IS 'Capability offerta commerciale per detail API: available_actions (da matrice transizioni + azioni speciali hardcoded), can_edit_*, can_push_contratto, can_create_revisione, non_editable_fields. Pattern data-driven capability layer (specchio fn_available_actions_preventivo). rev 2026-05-26.';
```

---
{% include-markdown "signature-core.md" %}
