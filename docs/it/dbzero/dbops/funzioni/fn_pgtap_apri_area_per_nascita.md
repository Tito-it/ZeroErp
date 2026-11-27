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
-- ⚠️ La voce la scrive il verbo del SUPER_ADMIN (dbops.fn_pgtap_scrivi_override):
--   il contesto dell'operatore torna com'era prima di uscire.
DECLARE
    v_utente  config.user_override_aree.auth_user_id%TYPE;
    v_area    config.aree_funzionali.schema_db%TYPE;
    v_area_id config.aree_funzionali.id%TYPE;
    v_prima   jsonb;  -- la voce d'area di prima, NULL se non c'era: nessuna colonna
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
    v_prima := dbops.fn_pgtap_scrivi_override(
        'config.user_override_aree'::regclass, v_utente,
        jsonb_build_object('area_id', v_area_id),
        jsonb_build_object('livello',    'TUTTO',
                           'motivo',     'Fixture pgTAP: nascita di ' || p_app_label || '.' || p_model_name,
                           'valido_dal', (SELECT script.fn_data_operativa()),
                           'valido_al',  NULL));

    -- Un override sull'OGGETTO resta sotto il tetto: lo si dice.
    IF script.fn_resolve_livello_oggetto(v_utente, p_app_label, p_model_name, v_area)
           IS DISTINCT FROM 'TUTTO'::config.livello_accesso THEN
        RAISE EXCEPTION 'fn_pgtap_apri_area_per_nascita: %.% non arriva a TUTTO anche con l''area aperta (override d''oggetto)',
                        p_app_label, p_model_name;
    END IF;

    RETURN jsonb_build_object(
        'utente',  v_utente,
        'area_id', v_area_id,
        'prima',   v_prima);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_apri_area_per_nascita(p_app_label character varying, p_model_name character varying)
IS 'Fixture pgTAP: apre a TUTTO l''area dell''oggetto per l''operatore in sessione, per il tempo di una nascita fatta da un builder sul verbo: scrive un override d''area, o alza quello che c''è, dal verbo del SUPER_ADMIN config.fn_imposta_override_aree (dbops.fn_pgtap_scrivi_override), e il contesto dell''operatore torna com''era. Ritorna il ricordo di ciò che c''era ({utente, area_id, prima}; NULL se il livello c''era già), da passare a dbops.fn_pgtap_richiudi_area.';
```

</div>

---
{% include-markdown "signature-core.md" %}
