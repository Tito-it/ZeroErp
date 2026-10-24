{% include-markdown "it/dbzero/config/manual/fn_lega_profilo_reparto.md" %}
# ⚙️ Funzione `fn_lega_profilo_reparto`

```sql
CREATE FUNCTION fn_lega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION config.fn_lega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_id config.profili_accesso_bindings.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Legare un reparto (unita' organizzativa) a un profilo
    --   di accesso. Ritorna l'id del binding.
    --
    -- Regole:
    --   - lo stesso profilo gia' legato: ritorna quel binding;
    --   - un altro profilo gia' legato: lo dice il vincolo
    --     uq_profili_accesso_bindings_uo;
    --   - argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA.
    -- =========================================================
    IF p_profilo_accesso_id IS NULL OR p_unita_organizzativa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'config', 'config.fn_lega_profilo_reparto', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('profilo_accesso_id',     p_profilo_accesso_id,
                               'unita_organizzativa_id', p_unita_organizzativa_id),
            NULL::uuid,
            'config.fn_lega_profilo_reparto',
            'profilo o reparto mancanti');
    END IF;

    SELECT pab.id
      INTO v_id
      FROM config.profili_accesso_bindings pab
     WHERE pab.unita_organizzativa_id = p_unita_organizzativa_id
       AND pab.profilo_accesso_id     = p_profilo_accesso_id;

    IF v_id IS NOT NULL THEN
        RETURN v_id;
    END IF;

    INSERT INTO config.profili_accesso_bindings (profilo_accesso_id, unita_organizzativa_id)
    VALUES (p_profilo_accesso_id, p_unita_organizzativa_id)
    RETURNING id INTO v_id;

    RETURN v_id;
END;
$function$

COMMENT ON FUNCTION config.fn_lega_profilo_reparto(p_profilo_accesso_id integer, p_unita_organizzativa_id integer)
IS 'MADRE (2026-10-19): lega un reparto (unita'' organizzativa) a un profilo di accesso, la riga di config.profili_accesso_bindings con unita_organizzativa_id. Gemella di config.fn_lega_profilo_identita. Un reparto ha un binding solo (uq_profili_accesso_bindings_uo): lo stesso profilo gia'' legato ritorna quel binding (idempotente), un altro profilo gia'' legato lo rifiuta il vincolo col suo nome (non sostituisce in silenzio: il backend con ON CONFLICT DO UPDATE sostituiva, ma il profilo di un reparto ha sempre lo stesso codice e quindi lo stesso id). Argomenti NULL: E_SCRIPT_CHIAMATA_NON_VALIDA. Coerenza e notifica dei permessi: i trigger della tabella. Non controlla il permesso (backend). INVOKER. Il contrario: config.fn_slega_profilo_reparto. Sede unica dell''UPSERT di AmmSoftwareRepository.put_profilo_reparto. R-BE-7, D-16b di Tid, brief-db-processi-accensione-per-ambiente §6.16.';
```

</div>

---
{% include-markdown "signature-core.md" %}
