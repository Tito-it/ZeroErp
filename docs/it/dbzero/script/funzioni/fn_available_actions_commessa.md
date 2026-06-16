{% include-markdown "it/dbzero/script/manual/fn_available_actions_commessa.md" %}
# ⚙️ Funzione `fn_available_actions_commessa`

```sql
CREATE FUNCTION fn_available_actions_commessa(p_commessa_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_available_actions_commessa(p_commessa_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo:
--   Capability della commessa per il detail/stato API. Mirror data-driven
--   di fn_available_actions_ordine, senza azioni applicative (solo stato).
--   Le transizioni utente (meta.manuale=true + action_key/label_key) sono
--   esposte come bottoni; le automatiche (bridge push/emittibilita') no.
DECLARE
    v_stato_id      vendite.commesse.stato_commessa_id%TYPE;
    v_stato_cod     vendite.stati_commessa.codice_interno%TYPE;
    v_modificabile  vendite.stati_commessa.modificabile%TYPE;
    v_emittibile    vendite.stati_commessa.emittibile%TYPE;
    v_actions       jsonb;
    v_can_change    boolean := false;
BEGIN
    -- Stato corrente + flag governance (data-driven).
    SELECT c.stato_commessa_id, sc.codice_interno, sc.modificabile, sc.emittibile
      INTO v_stato_id, v_stato_cod, v_modificabile, v_emittibile
      FROM vendite.commesse c
      JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
     WHERE c.id = p_commessa_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Transizioni manuali (utente) disponibili dallo stato corrente.
    -- Filtri: attivo, manuale=true, presenza action_key/label_key.
    -- Le automatiche (manuale=false, senza action_key) sono escluse.
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
    FROM vendite.transizioni_stati_commessa t
    JOIN vendite.stati_commessa sa ON sa.id = t.stato_a_id
    WHERE t.stato_da_id = v_stato_id
      AND t.attivo IS TRUE
      AND COALESCE((t.meta->>'manuale')::boolean, false) IS TRUE
      AND (t.meta->>'action_key') IS NOT NULL
      AND (t.meta->>'label_key') IS NOT NULL;

    v_can_change := jsonb_array_length(v_actions) > 0;

    RETURN jsonb_build_object(
        'available_actions', v_actions,
        'can_change_state',  v_can_change,
        'can_edit_righe',    v_modificabile,
        'is_emittibile',     v_emittibile,
        'stato_codice',      v_stato_cod
    );
END;
$function$

COMMENT ON FUNCTION script.fn_available_actions_commessa(p_commessa_id bigint)
IS 'Capability commessa per detail/stato API: available_actions (transizioni manuali da vendite.transizioni_stati_commessa, data-driven dal meta), can_change_state, can_edit_righe (stati_commessa.modificabile), is_emittibile (stati_commessa.emittibile), stato_codice. Mirror di fn_available_actions_ordine senza azioni applicative. Fallback NULL se commessa inesistente. rev 2026-06-16.';
```

---
{% include-markdown "signature-core.md" %}
