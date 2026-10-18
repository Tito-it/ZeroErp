{% include-markdown "it/dbzero/config/manual/fn_lega_profilo_identita.md" %}
# ⚙️ Funzione `fn_lega_profilo_identita`

```sql
CREATE FUNCTION fn_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id config.profili_accesso_bindings.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Legare un'identita' digitale a un profilo di accesso.
    --   Ritorna l'id del binding.
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

COMMENT ON FUNCTION config.fn_lega_profilo_identita(p_profilo_accesso_id integer, p_identita_digitale_id bigint)
IS 'BB (2026-10-18): lega un''identita'' digitale a un profilo di accesso (la riga di config.profili_accesso_bindings con identita_digitale_id). Un''identita'' ha un binding solo (uq_profili_accesso_bindings_identita): lo stesso profilo gia'' legato ritorna quel binding (idempotente), un altro profilo gia'' legato lo rifiuta il vincolo col suo nome (il BB non sostituisce in silenzio). Argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Coerenza e notifica dei permessi: i trigger della tabella. Non controlla il permesso (backend). INVOKER. Ritorna l''id del binding. Regola del 2: sede unica dell''INSERT che era in anagrafiche.fn_crea_risorsa_umana_v2 (binding SUPER_ADMIN), script.fn_crea_utente_tecnico (profilo chiesto) e AmmSoftwareRepository._set_super_admin_binding (2b-2). Brief: brief-db-processi-accensione-per-ambiente (2b-1, lotto 8).';
```

---
{% include-markdown "signature-core.md" %}
