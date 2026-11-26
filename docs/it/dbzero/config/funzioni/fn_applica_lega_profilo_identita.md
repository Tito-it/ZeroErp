{% include-markdown "it/dbzero/config/manual/fn_applica_lega_profilo_identita.md" %}
# ⚙️ Funzione `fn_applica_lega_profilo_identita`

```sql
CREATE FUNCTION fn_applica_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_applica_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id config.profili_accesso_bindings.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Primitiva: legare un'identita' digitale a un profilo di
    --   accesso. Ritorna l'id del binding. Non chiede permessi:
    --   lo chiede chi la chiama (il verbo config.fn_lega_profilo_identita,
    --   i verbi di creazione). L'app non la esegue.
    --
    -- Regole:
    --   - lo stesso profilo gia' legato: ritorna quel binding;
    --   - un altro profilo gia' legato: lo dice il vincolo
    --     uq_profili_accesso_bindings_identita;
    --   - argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    IF p_profilo_accesso_id IS NULL OR p_identita_digitale_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_lega_profilo_identita', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('profilo_accesso_id',   p_profilo_accesso_id,
                               'identita_digitale_id', p_identita_digitale_id),
            NULL::uuid,
            'config.fn_lega_profilo_identita',
            'profilo o identita'' mancanti');
    END IF;

    SELECT pab.id
      INTO v_id
      FROM config.profili_accesso_bindings pab
     WHERE pab.identita_digitale_id = p_identita_digitale_id
       AND pab.profilo_accesso_id   = p_profilo_accesso_id;

    IF v_id IS NOT NULL THEN
        RETURN v_id;
    END IF;

    INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, identita_digitale_id)
    VALUES (p_profilo_accesso_id, p_identita_digitale_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION config.fn_applica_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
IS 'Primitiva: lega un''identità digitale a un profilo di accesso (la riga di config.profili_accesso_bindings con identita_digitale_id) e ritorna l''id del legame. Lo stesso profilo già legato ritorna quel legame; un altro profilo già legato lo rifiuta il vincolo uq_profili_accesso_bindings_identita; argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Coerenza, ultimo SUPER_ADMIN e notifica dei permessi: i trigger della tabella. Non chiede permessi, e l''applicazione non la esegue: la chiamano il verbo config.fn_lega_profilo_identita e le funzioni che creano un''identità (anagrafiche.fn_crea_risorsa_umana, script.fn_applica_crea_utente_tecnico, anagrafiche.fn_provisiona_dati_di_sviluppo).';
```

</div>

---
{% include-markdown "signature-core.md" %}
