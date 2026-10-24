{% include-markdown "it/dbzero/anagrafiche/manual/fn_notify_cambio_reparto.md" %}
# ⚙️ Funzione `fn_notify_cambio_reparto`

```sql
CREATE FUNCTION fn_notify_cambio_reparto(p_risorsa_umana_id bigint, p_old_uo_id integer, p_new_uo_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_notify_cambio_reparto(p_risorsa_umana_id bigint, p_old_uo_id integer, p_new_uo_id integer)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_payload      text;
BEGIN
-- ------------------------------------------------------------
-- Funzione: anagrafiche.fn_notify_cambio_reparto
--
-- Scopo:
--   Emette una notifica PostgreSQL sul canale 'cambio_reparto'
--   con un payload JSON contenente i dettagli del cambio
--   di unita' organizzativa. Pensata per essere intercettata
--   da un listener backend (LISTEN/NOTIFY) che invalida
--   la cache permessi dell'utente spostato.
--
-- Parametri:
--   p_risorsa_umana_id -> ID della risorsa umana (NOT NULL, > 0)
--   p_old_uo_id        -> vecchio unita_organizzativa_id (nullable)
--   p_new_uo_id        -> nuovo unita_organizzativa_id (nullable)
--
-- Ritorna: void
-- ------------------------------------------------------------

    ----------------------------------------------------------------
    -- 1) Guard: parametro non nullo e valido
    ----------------------------------------------------------------
    IF p_risorsa_umana_id IS NULL OR p_risorsa_umana_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_notify_cambio_reparto',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_risorsa_umana_id',
                'valore', p_risorsa_umana_id
            ),
            NULL::uuid,
            'p_risorsa_umana_id deve essere NOT NULL e > 0'
        );
    END IF;

    ----------------------------------------------------------------
    -- 2) Lookup auth_user_id (potrebbe non esistere): dalla madre
    --    identita_digitali, via l'helper condiviso (12-09-2026: la
    --    vista risorse_umane_auth_user e' stata ritirata).
    ----------------------------------------------------------------
    v_auth_user_id := script.fn_get_auth_user_id_for_risorsa_umana(p_risorsa_umana_id);

    ----------------------------------------------------------------
    -- 3) Costruzione payload e NOTIFY
    ----------------------------------------------------------------
    v_payload := jsonb_build_object(
        'risorsa_umana_id', p_risorsa_umana_id,
        'old_uo_id',        p_old_uo_id,
        'new_uo_id',        p_new_uo_id,
        'auth_user_id',     v_auth_user_id
    )::text;

    PERFORM pg_notify('cambio_reparto', v_payload);
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_notify_cambio_reparto(p_risorsa_umana_id bigint, p_old_uo_id integer, p_new_uo_id integer)
IS 'Emette NOTIFY cambio_reparto con payload JSON (risorsa_umana_id, old_uo_id, new_uo_id, auth_user_id). Usata dal trigger z90 su risorse_umane per invalidazione cache permessi via LISTEN/NOTIFY. L''auth_user si risolve da identita_digitali con script.fn_get_auth_user_id_for_risorsa_umana (dal 12-09-2026: la vista risorse_umane_auth_user e'' stata ritirata).';
```

</div>

---
{% include-markdown "signature-core.md" %}
