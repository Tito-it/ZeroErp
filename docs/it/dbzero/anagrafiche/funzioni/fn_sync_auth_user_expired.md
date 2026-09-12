{% include-markdown "it/dbzero/anagrafiche/manual/fn_sync_auth_user_expired.md" %}
# ⚙️ Funzione `fn_sync_auth_user_expired`

```sql
CREATE FUNCTION fn_sync_auth_user_expired()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_sync_auth_user_expired()
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Variabili locali tipizzate %TYPE (policy ZeroErp).
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_modified     boolean;
    v_count        integer := 0;
BEGIN
    -- ------------------------------------------------------------
    -- Funzione: anagrafiche.fn_sync_auth_user_expired (v3, 12-09-2026)
    -- Scopo:
    --   Batch di disattivazione overnight per utenti con finestra
    --   temporale scaduta: identita_digitali.valido_al < CURRENT_DATE,
    --   per tutte le vesti.
    --   ⛔ Il «ramo legacy» (risorse_umane.valido_al via la vista
    --   risorse_umane_auth_user) e' caduto: la regola vive in
    --   identita_digitali.valido_al (decisione Tid 12-09-2026), e
    --   fn_sync_auth_user_is_active decide comunque SOLO sull'identita'
    --   — quel ramo poteva proporre candidati, mai cambiare l'esito.
    --
    --   Uso: pgAgent daily job + management command Django.
    --
    -- Ritorna: numero di utenti effettivamente disattivati.
    -- ------------------------------------------------------------

    -- Short-circuit CI: se lo schema django non esiste, no-op.
    IF to_regclass('django.auth_user') IS NULL THEN
        RETURN 0;
    END IF;

    -- Loop sui candidati: auth_user ancora is_active=true con almeno
    -- un'identita' digitale attiva a finestra scaduta (operatori,
    -- portale, fornitore, shop, api client).
    FOR v_auth_user_id IN
        EXECUTE '
            SELECT DISTINCT id.auth_user_id
              FROM anagrafiche.identita_digitali id
              JOIN django.auth_user au
                ON au.id = id.auth_user_id
             WHERE id.attivo = true
               AND id.valido_al IS NOT NULL
               AND id.valido_al < CURRENT_DATE
               AND au.is_active = true
        '
    LOOP
        -- Invoca la nuova firma sync per ciascun candidato.
        -- La funzione sync applica la logica di fail-closed
        -- (fuori finestra -> false); qui contiamo solo quelli
        -- realmente modificati (v_modified = true).
        SELECT anagrafiche.fn_sync_auth_user_is_active(v_auth_user_id)
          INTO v_modified;

        IF v_modified THEN
            v_count := v_count + 1;
        END IF;
    END LOOP;

    RETURN v_count;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_sync_auth_user_expired()
IS 'Batch: disattiva auth_user per finestra temporale scaduta su identita_digitali.valido_al (tutte le vesti). Dal 12-09-2026 senza il ramo legacy via risorse_umane_auth_user: la regola vive in identita_digitali e fn_sync_auth_user_is_active decide solo li''. Invocata da pgAgent daily e management command Django. Ritorna il numero di utenti disattivati.';
```

---
{% include-markdown "signature-core.md" %}
