{% include-markdown "it/dbzero/script/manual/fn_capability_promo_articolo.md" %}
# ⚙️ Funzione `fn_capability_promo_articolo`

```sql
CREATE FUNCTION fn_capability_promo_articolo(p_promo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_capability_promo_articolo(p_promo_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo:
--   Capability della promo articolo per il detail API (Fase 1
--   refactor frontend vendite). Calcola lo stato temporale da
--   CURRENT_DATE vs valido_dal/valido_al e restituisce i vincoli
--   di editing allineati al trigger guard DB.
--
--   Dispatch stati (specchio di trgfn_promo_articoli_guard_data_driven):
--     FUTURA   = CURRENT_DATE < valido_dal
--     INIZIATA = valido_dal <= CURRENT_DATE <= valido_al
--     SCADUTA  = CURRENT_DATE > valido_al
--
--   Whitelist editabilita' per stato (da trigger guard):
--     FUTURA:   tutto (date solo verso futuro — vincoli min_valido_*)
--     INIZIATA: descrizione, valido_al (>= oggi), meta
--     SCADUTA:  nulla (immutabile)
--
--   Fallback sicuro: NULL se la promo non esiste.
DECLARE
    v_dal    vendite.promo_articoli.valido_dal%TYPE;
    v_al     vendite.promo_articoli.valido_al%TYPE;
    v_today  CONSTANT date := script.fn_data_operativa();
    v_stato  text;
    v_can    boolean;
    v_reason text;
    v_nedit  jsonb;
    v_mindag text;
    v_minal  text;
    -- Campi immutabili in INIZIATA.
    -- Editabili: descrizione, valido_al, meta.
    c_nedit_iniziata CONSTANT jsonb :=
        '["codice","articolo_id","uom_id","tipo_variazione","valore_variazione","valido_dal","attivo"]'::jsonb;
    -- Tutti i campi dominio immutabili in SCADUTA.
    c_nedit_scaduta CONSTANT jsonb :=
        '["codice","descrizione","articolo_id","uom_id","tipo_variazione","valore_variazione","valido_dal","valido_al","attivo","meta"]'::jsonb;
BEGIN
    SELECT pa.valido_dal, pa.valido_al
      INTO v_dal, v_al
      FROM vendite.promo_articoli pa
     WHERE pa.id = p_promo_id;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- Dispatch: FUTURA -> INIZIATA -> SCADUTA.
    -- Le condizioni sono mutuamente esclusive; equivalente al
    -- dispatch SCADUTA->INIZIATA->FUTURA del trigger guard.
    IF v_today < v_dal THEN
        -- FUTURA: tutto editabile, ma date devono restare nel futuro.
        -- min_valido_dal = domani (trigger blocca valido_dal <= today).
        -- min_valido_al  = oggi   (trigger blocca valido_al < today).
        v_stato  := 'FUTURA';
        v_can    := true;
        v_reason := NULL;
        v_nedit  := '[]'::jsonb;
        v_mindag := (v_today + 1)::text;
        v_minal  := v_today::text;
    ELSIF v_today <= v_al THEN
        -- INIZIATA: whitelist ristretta. valido_dal immutabile.
        -- min_valido_al = oggi (trigger blocca valido_al < today).
        v_stato  := 'INIZIATA';
        v_can    := true;
        v_reason := NULL;
        v_nedit  := c_nedit_iniziata;
        v_mindag := NULL;
        v_minal  := v_today::text;
    ELSE
        -- SCADUTA: nulla e' modificabile per trigger guard.
        v_stato  := 'SCADUTA';
        v_can    := false;
        v_reason := 'PROMO_SCADUTA_IMMUTABILE';
        v_nedit  := c_nedit_scaduta;
        v_mindag := NULL;
        v_minal  := NULL;
    END IF;

    RETURN jsonb_build_object(
        'stato_temporale',     v_stato,
        'can_update',          v_can,
        'can_update_reason',   v_reason,
        'non_editable_fields', v_nedit,
        'min_valido_dal',      v_mindag,
        'min_valido_al',       v_minal
    );
END;
$function$

COMMENT ON FUNCTION script.fn_capability_promo_articolo(p_promo_id bigint)
IS 'Capability promo articolo per detail API: stato_temporale (FUTURA/INIZIATA/SCADUTA), can_update, non_editable_fields, min_valido_dal/al. Specchio del trigger guard data-driven. Fase 1 refactor frontend vendite.';
```

</div>

---
{% include-markdown "signature-core.md" %}
