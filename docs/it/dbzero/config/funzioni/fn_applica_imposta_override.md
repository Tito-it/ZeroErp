{% include-markdown "it/dbzero/config/manual/fn_applica_imposta_override.md" %}
# ⚙️ Funzione `fn_applica_imposta_override`

```sql
CREATE FUNCTION fn_applica_imposta_override(p_tabella regclass, p_auth_user_id integer, p_elenco jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_applica_imposta_override(p_tabella regclass, p_auth_user_id integer, p_elenco jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Sostituire gli override di un utente su una delle tre tabelle
--   (config.user_override_aree, _azioni, _oggetti) con l'elenco dato
--   (vuoto = nessun override). Ritorna quanti ne scrive.
--
-- Regole:
--   - nessun permesso: lo chiede il verbo che la chiama;
--   - tabella fuori elenco, utente NULL, elenco o elemento malformati:
--     E_SCRIPT_CHIAMATA_NON_VALIDA;
--   - chiave estranea in un elemento: E_CAMPO_NON_AMMESSO;
--   - chiave assente = DEFAULT, chiave null = NULL;
--   - catalogo, riservati e date: vincoli e guard della tabella.
DECLARE
    v_lista   jsonb := COALESCE(p_elenco, '[]'::jsonb);
    v_el      jsonb;
    v_n       integer := 0;  -- un conteggio: niente da ancorare
    v_verbo   text;          -- il nome del verbo, per il contesto degli errori: nessuna colonna
    v_ammesse text[];        -- le chiavi di un elemento: nomi di colonna, nessuna colonna da ancorare
BEGIN
    CASE p_tabella
        WHEN 'config.user_override_aree'::regclass THEN
            v_verbo   := 'config.fn_imposta_override_aree';
            v_ammesse := ARRAY['area_id', 'livello', 'motivo', 'valido_dal', 'valido_al'];
        WHEN 'config.user_override_azioni'::regclass THEN
            v_verbo   := 'config.fn_imposta_override_azioni';
            v_ammesse := ARRAY['azione_id', 'abilitata', 'motivo', 'valido_dal', 'valido_al'];
        WHEN 'config.user_override_oggetti'::regclass THEN
            v_verbo   := 'config.fn_imposta_override_oggetti';
            v_ammesse := ARRAY['app_label', 'model_name', 'livello', 'motivo', 'valido_dal', 'valido_al'];
        ELSE
            v_verbo   := NULL;
    END CASE;

    IF v_verbo IS NULL OR p_auth_user_id IS NULL OR jsonb_typeof(v_lista) <> 'array'
       OR EXISTS (SELECT 1 FROM jsonb_array_elements(v_lista) AS e
                   WHERE jsonb_typeof(e) <> 'object') THEN
        PERFORM script.fn_log_and_raise_error(
            'config', COALESCE(v_verbo, 'config.fn_applica_imposta_override'), 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('tabella',      p_tabella::text,
                               'auth_user_id', p_auth_user_id,
                               'tipo_elenco',  jsonb_typeof(v_lista)),
            NULL::uuid,
            COALESCE(v_verbo, 'config.fn_applica_imposta_override'),
            'tabella fuori elenco, utente mancante, o elenco degli override malformato');
    END IF;

    FOR v_el IN SELECT e FROM jsonb_array_elements(v_lista) AS e LOOP
        PERFORM script.fn_guard_campi_ammessi(
            v_el, v_ammesse,
            'config', v_verbo,
            jsonb_build_object('auth_user_id', p_auth_user_id));
    END LOOP;

    EXECUTE format('DELETE FROM %s o WHERE o.auth_user_id = $1', p_tabella)
      USING p_auth_user_id;

    FOR v_el IN SELECT e FROM jsonb_array_elements(v_lista) AS e LOOP
        PERFORM script.fn_scrivi_riga_da_jsonb(
            p_tabella,
            v_el || jsonb_build_object('auth_user_id', p_auth_user_id));
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION config.fn_applica_imposta_override(p_tabella regclass, p_auth_user_id integer, p_elenco jsonb)
IS 'Primitiva degli override di un utente: sostituisce le sue righe di una delle tre tabelle (config.user_override_aree, config.user_override_azioni, config.user_override_oggetti) con l''elenco p_elenco, anche vuoto (= nessun override); ritorna quanti ne scrive. Le chiavi ammesse di un elemento sono per tabella: aree area_id, livello, motivo, valido_dal, valido_al; azioni azione_id, abilitata, motivo, valido_dal, valido_al; oggetti app_label, model_name, livello, motivo, valido_dal, valido_al. Una chiave assente prende il DEFAULT (valido_dal = la data operativa), una chiave a null scrive NULL. Chiave estranea: E_CAMPO_NON_AMMESSO; tabella fuori elenco, utente NULL, elenco o elemento malformati: E_SCRIPT_CHIAMATA_NON_VALIDA, col nome del verbo della tabella. Catalogo, riservati e date: i vincoli e i guard della tabella. Non chiede permessi: la chiamano i verbi del SUPER_ADMIN config.fn_imposta_override_aree, config.fn_imposta_override_azioni, config.fn_imposta_override_oggetti e il provisioning di sviluppo; l''applicazione non la esegue.';
```

</div>

---
{% include-markdown "signature-core.md" %}
