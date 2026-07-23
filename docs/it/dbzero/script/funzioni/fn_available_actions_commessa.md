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
--   rev 2026-07-24: + enabled/reasons su chiudi/annulla, dalle funzioni
--   pure script.fn_check_commessa_chiudibile / _annullabile — le STESSE
--   che vendite.trgfn_commesse_guard_transizione usa per sollevare
--   (sorgente unica: la UI non puo' divergere dal guard).
DECLARE
    v_stato_id      vendite.commesse.stato_commessa_id%TYPE;
    v_stato_cod     vendite.stati_commessa.codice_interno%TYPE;
    v_modificabile  vendite.stati_commessa.modificabile%TYPE;
    v_emittibile    vendite.stati_commessa.emittibile%TYPE;
    v_actions       jsonb;
    v_can_change    boolean := false;
    v_mot_chiudi    jsonb;
    v_mot_annulla   jsonb;
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

    -- Motivi ostativi alle due uscite terminali, calcolati UNA VOLTA
    -- SOLA e riusati sotto per enabled e reasons. Le fn sono pure:
    -- ritornano [] quando l'uscita e' lecita.
    v_mot_chiudi  := script.fn_check_commessa_chiudibile(p_commessa_id);
    v_mot_annulla := script.fn_check_commessa_annullabile(p_commessa_id);

    -- Transizioni manuali (utente) disponibili dallo stato corrente.
    -- Filtri: attivo, manuale=true, presenza action_key/label_key.
    -- Le automatiche (manuale=false, senza action_key) sono escluse.
    -- enabled/reasons: le azioni terminali portano il verdetto delle
    -- fn_check_*; tutte le altre nascono abilitate senza motivi.
    SELECT COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'key',              t.meta->>'action_key',
                'target_state',     sa.codice_interno,
                'label_key',        t.meta->>'label_key',
                'severity',         t.meta->>'severity',
                'icon',             t.meta->>'icon',
                'requires_confirm', COALESCE((t.meta->>'requires_confirm')::boolean, false),
                'outlined',         COALESCE((t.meta->>'outlined')::boolean, false),
                'enabled',          CASE sa.codice_interno
                                      WHEN 'CHIUSA'    THEN jsonb_array_length(v_mot_chiudi)  = 0
                                      WHEN 'ANNULLATA' THEN jsonb_array_length(v_mot_annulla) = 0
                                      ELSE true
                                    END,
                'reasons',          CASE sa.codice_interno
                                      WHEN 'CHIUSA'    THEN v_mot_chiudi
                                      WHEN 'ANNULLATA' THEN v_mot_annulla
                                      ELSE '[]'::jsonb
                                    END
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

    -- can_change_state sulle sole azioni ABILITATE: con le azioni
    -- disabilitate ora presenti in lista, il vecchio
    -- jsonb_array_length(v_actions) > 0 sarebbe sempre true.
    SELECT EXISTS (
        SELECT 1
          FROM jsonb_array_elements(v_actions) AS a
         WHERE COALESCE((a->>'enabled')::boolean, true) IS TRUE
    ) INTO v_can_change;

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
IS 'Capability commessa per detail/stato API: available_actions (transizioni manuali da vendite.transizioni_stati_commessa, data-driven dal meta), can_change_state, can_edit_righe (stati_commessa.modificabile), is_emittibile (stati_commessa.emittibile), stato_codice. Mirror di fn_available_actions_ordine senza azioni applicative. Fallback NULL se commessa inesistente. rev 2026-07-24 (brief-db-guard-uscita-commessa-e-capabilities): ogni azione porta enabled + reasons; chiudi/annulla prendono il verdetto dalle funzioni pure script.fn_check_commessa_chiudibile / _annullabile, le STESSE usate dal guard di transizione (sorgente unica: la UI non puo'' divergere dal DB). ATTENZIONE CONTRATTO: la presenza di un''azione in available_actions NON significa piu'' eseguibile — i consumatori devono leggere enabled. can_change_state e'' calcolato sulle sole azioni abilitate.';
```

---
{% include-markdown "signature-core.md" %}
