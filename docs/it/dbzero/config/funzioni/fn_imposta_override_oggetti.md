{% include-markdown "it/dbzero/config/manual/fn_imposta_override_oggetti.md" %}
# ⚙️ Funzione `fn_imposta_override_oggetti`

```sql
CREATE FUNCTION fn_imposta_override_oggetti(p_auth_user_id integer, p_oggetti jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_imposta_override_oggetti(p_auth_user_id integer, p_oggetti jsonb)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_lista    jsonb := COALESCE(p_oggetti, '[]'::jsonb);
    v_el       jsonb;
    v_estranea text;
    v_n        integer := 0;   -- un conteggio: niente da ancorare
    c_ammesse  CONSTANT text[] := ARRAY[
        'app_label', 'model_name', 'livello', 'motivo', 'valido_dal', 'valido_al'];
BEGIN
    -- =========================================================
    -- Scopo:
    --   Sostituire gli override di un utente sugli oggetti con
    --   l'elenco dato (vuoto = nessun override). Ritorna
    --   quanti ne scrive.
    --
    -- Regole:
    --   - utente NULL, elenco o elemento malformati:
    --     E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - chiave estranea in un elemento: E_CAMPO_NON_AMMESSO;
    --   - chiave assente = DEFAULT, chiave null = NULL;
    --   - catalogo, riservati e date: vincoli e guard.
    -- =========================================================
    IF p_auth_user_id IS NULL OR jsonb_typeof(v_lista) <> 'array'
       OR EXISTS (SELECT 1 FROM jsonb_array_elements(v_lista) AS e
                   WHERE jsonb_typeof(e) <> 'object') THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_imposta_override_oggetti', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('auth_user_id', p_auth_user_id,
                               'tipo_oggetti', jsonb_typeof(v_lista)),
            NULL::uuid,
            'config.fn_imposta_override_oggetti',
            'utente mancante, o elenco degli override malformato');
    END IF;

    FOR v_el IN SELECT e FROM jsonb_array_elements(v_lista) AS e LOOP
        v_estranea := script.fn_prima_chiave_estranea(v_el, c_ammesse);
        IF v_estranea IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'config', 'config.fn_imposta_override_oggetti', 'E_CAMPO_NON_AMMESSO',
                jsonb_build_object('campo', v_estranea, 'auth_user_id', p_auth_user_id),
                NULL::uuid,
                v_estranea);
        END IF;
    END LOOP;

    DELETE FROM config.user_override_oggetti uoo WHERE uoo.auth_user_id = p_auth_user_id;

    FOR v_el IN SELECT e FROM jsonb_array_elements(v_lista) AS e LOOP
        PERFORM script.fn_scrivi_riga_da_jsonb(
            'config.user_override_oggetti'::regclass,
            v_el || jsonb_build_object('auth_user_id', p_auth_user_id));
        v_n := v_n + 1;
    END LOOP;

    RETURN v_n;
END;
$function$

COMMENT ON FUNCTION config.fn_imposta_override_oggetti(p_auth_user_id integer, p_oggetti jsonb)
IS 'BB (2026-10-18): sostituisce gli override di un utente sugli oggetti (config.user_override_oggetti) con l''elenco p_oggetti, anche vuoto (= nessun override). Un elemento: app_label, model_name, livello (obbligatori), motivo, valido_dal, valido_al; una chiave assente prende il DEFAULT (valido_dal = la data operativa), una chiave a null scrive NULL (valido_dal NULL = senza inizio). Chiave estranea: E_CAMPO_NON_AMMESSO; utente NULL, elenco o elemento malformati: E_SCRIPT_CHIAMATA_NON_VALIDA. Oggetto fuori catalogo o riservato: fk_user_override_oggetti_catalogo; date: trgfn_guard_date_validita. Scrive con script.fn_scrivi_riga_da_jsonb. Non controlla il permesso ne'' invalida la cache dei permessi (backend). INVOKER. Ritorna quanti override scrive. Prende il posto di AmmSoftwareRepository.put_override_oggetti (2b-2) ed e'' la sede degli override del verbo dei dati di sviluppo (2b-3). Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 9).';
```

</div>

---
{% include-markdown "signature-core.md" %}
