{% include-markdown "it/dbzero/config/manual/fn_imposta_emittente_attivo.md" %}
# ⚙️ Funzione `fn_imposta_emittente_attivo`

```sql
CREATE FUNCTION fn_imposta_emittente_attivo(p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_imposta_emittente_attivo(p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id config.user_emittente_attivo.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impostare l'emittente attivo di un utente: crearne la
    --   preferenza o aggiornarla. Ritorna l'id della riga.
    --
    -- Regole:
    --   - argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA;
    --   - l'UPDATE tocca la riga anche a valore invariato
    --     (la storia registra ogni conferma);
    --   - emittente attivo: il trigger della tabella.
    -- =========================================================
    IF p_auth_user_id IS NULL OR p_emittente_fiscale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_imposta_emittente_attivo', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('auth_user_id',         p_auth_user_id,
                               'emittente_fiscale_id', p_emittente_fiscale_id),
            NULL::uuid,
            'config.fn_imposta_emittente_attivo',
            'utente o emittente mancanti');
    END IF;

    INSERT INTO config.user_emittente_attivo AS uea (auth_user_id, emittente_fiscale_id)
    VALUES (p_auth_user_id, p_emittente_fiscale_id)
    ON CONFLICT (auth_user_id) DO UPDATE
       SET emittente_fiscale_id = EXCLUDED.emittente_fiscale_id
    RETURNING uea.id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION config.fn_imposta_emittente_attivo(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'BB (2026-10-18): imposta l''emittente attivo di un utente (config.user_emittente_attivo): UPSERT sull''utente (uq_user_emittente_attivo_auth_user); l''UPDATE tocca la riga anche a valore invariato, cosi'' la storia registra ogni conferma esplicita della scelta (come il backend). Argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Emittente attivo: il trigger require_attivo della tabella. Non controlla lo SCOPE dell''utente sull''emittente (pre-check del backend sulla canonica script.fn_check_user_emittente_scope; regola senza guard sulla tabella, debito dichiarato) ne'' il permesso. INVOKER. Ritorna l''id. Prende il posto di EmittenteAttivoRepository.set_preferenza (2b-2) ed e'' la sede del verbo dei dati di sviluppo (2b-3). Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 9).';
```

</div>

---
{% include-markdown "signature-core.md" %}
