{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_apri_area_per_nascita.md" %}
# ⚙️ Funzione `fn_pgtap_apri_area_per_nascita`

```sql
CREATE FUNCTION fn_pgtap_apri_area_per_nascita(p_app_label character varying, p_model_name character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_apri_area_per_nascita(p_app_label character varying, p_model_name character varying)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare all'operatore in sessione TUTTO sull'oggetto per il tempo
--   di una nascita fatta da un builder. Ritorna il ricordo di cio' che
--   c'era, da passare a dbops.fn_pgtap_richiudi_area; NULL se il livello
--   c'era gia'.
-- Uso: v_ricordo := dbops.fn_pgtap_apri_area_per_nascita('magazzino', 'magazzini');
--      ... il verbo ...
--      PERFORM dbops.fn_pgtap_richiudi_area(v_ricordo);
DECLARE
    v_utente  config.user_override_aree.auth_user_id%TYPE;
    v_area    config.aree_funzionali.schema_db%TYPE;
    v_area_id config.aree_funzionali.id%TYPE;
    v_prima   config.user_override_aree%ROWTYPE;
    v_ov      config.user_override_aree.id%TYPE;
BEGIN
    v_utente := script.fn_utente_di_sessione('dbops.fn_pgtap_apri_area_per_nascita');
    IF v_utente IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_apri_area_per_nascita: nessun operatore in sessione — chiamare prima fn_pgtap_set_contesto_operatore';
    END IF;

    v_area := script.fn_area_di_oggetto(p_app_label, p_model_name);
    IF script.fn_resolve_livello_oggetto(v_utente, p_app_label, p_model_name, v_area)
           IS NOT DISTINCT FROM 'TUTTO'::config.livello_accesso THEN
        RETURN NULL;
    END IF;

    SELECT af.id INTO v_area_id
      FROM config.aree_funzionali af
     WHERE af.schema_db = v_area;
    IF v_area_id IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_apri_area_per_nascita: nessuna area funzionale per %.%', p_app_label, p_model_name;
    END IF;

    -- Un override d'area che c'e' (del test, o del database) si alza per
    -- il tempo della nascita e si rimette com'era: se ne tiene il ricordo.
    SELECT * INTO v_prima
      FROM config.user_override_aree uoa
     WHERE uoa.auth_user_id = v_utente
       AND uoa.area_id      = v_area_id;

    IF v_prima.id IS NULL THEN
        INSERT INTO config.user_override_aree
               (auth_user_id, area_id, livello, motivo, valido_dal, valido_al)
        VALUES (v_utente, v_area_id, 'TUTTO',
                'Fixture pgTAP: nascita di ' || p_app_label || '.' || p_model_name,
                (SELECT script.fn_data_operativa()), NULL)
        RETURNING id INTO v_ov;
    ELSE
        UPDATE config.user_override_aree uoa
           SET livello    = 'TUTTO',
               valido_dal = (SELECT script.fn_data_operativa()),
               valido_al  = NULL
         WHERE uoa.id = v_prima.id;
        v_ov := v_prima.id;
    END IF;

    -- Un override sull'OGGETTO resta sotto il tetto: lo si dice.
    IF script.fn_resolve_livello_oggetto(v_utente, p_app_label, p_model_name, v_area)
           IS DISTINCT FROM 'TUTTO'::config.livello_accesso THEN
        RAISE EXCEPTION 'fn_pgtap_apri_area_per_nascita: %.% non arriva a TUTTO anche con l''area aperta (override d''oggetto)',
                        p_app_label, p_model_name;
    END IF;

    RETURN jsonb_build_object(
        'override_id', v_ov,
        'nuovo',       v_prima.id IS NULL,
        'livello',     v_prima.livello,
        'valido_dal',  v_prima.valido_dal,
        'valido_al',   v_prima.valido_al);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_apri_area_per_nascita(p_app_label character varying, p_model_name character varying)
IS 'Fixture pgTAP: apre a TUTTO l''area dell''oggetto per l''operatore in sessione, per il tempo di una nascita fatta da un builder sul verbo: scrive un override d''area, o alza quello che c''e''. Ritorna il ricordo di cio'' che c''era (NULL se il livello c''era gia''), da passare a dbops.fn_pgtap_richiudi_area.';
```

</div>

---
{% include-markdown "signature-core.md" %}
