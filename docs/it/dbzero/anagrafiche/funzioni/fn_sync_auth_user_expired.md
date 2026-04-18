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
    v_auth_user_id anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE;
    v_modified     boolean;
    v_count        integer := 0;
BEGIN
    -- ------------------------------------------------------------
    -- Funzione: anagrafiche.fn_sync_auth_user_expired (v2)
    -- Scopo:
    --   Batch di disattivazione overnight per utenti con finestra
    --   temporale scaduta. Copre:
    --     - risorse_umane.valido_al < CURRENT_DATE (legacy)
    --     - identita_digitali.valido_al < CURRENT_DATE (nuovo)
    --   Evita double-count grazie a SELECT DISTINCT sull'UNION.
    --
    --   Uso: pgAgent daily job + management command Django.
    --
    -- Ritorna: numero di utenti effettivamente disattivati.
    -- ------------------------------------------------------------

    -- Short-circuit CI: se lo schema django non esiste, no-op.
    IF to_regclass('django.auth_user') IS NULL THEN
        RETURN 0;
    END IF;

    -- Loop sui candidati (auth_user ancora is_active=true ma con
    -- finestra scaduta in almeno uno dei due modelli).
    FOR v_auth_user_id IN
        EXECUTE '
            SELECT DISTINCT t.auth_user_id
              FROM (
                  -- Ramo legacy: risorse_umane con valido_al scaduto
                  -- collegate ad auth_user via bridge RUA.
                  SELECT rau.auth_user_id
                    FROM anagrafiche.risorse_umane ru
                    JOIN anagrafiche.risorse_umane_auth_user rau
                      ON rau.risorsa_umana_id = ru.id
                   WHERE ru.valido_al IS NOT NULL
                     AND ru.valido_al < CURRENT_DATE

                  UNION

                  -- Ramo nuovo: qualsiasi identita_digitale attiva
                  -- con valido_al scaduto (operatori, portale,
                  -- fornitore, shop, api client).
                  SELECT id.auth_user_id
                    FROM anagrafiche.identita_digitali id
                   WHERE id.attivo = true
                     AND id.valido_al IS NOT NULL
                     AND id.valido_al < CURRENT_DATE
              ) t
              JOIN django.auth_user au
                ON au.id = t.auth_user_id
             WHERE au.is_active = true
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
IS 'Batch: disattiva auth_user per finestra temporale scaduta. Copre risorse_umane legacy + identita_digitali nuove (§4.5.5 WIP multi-face-auth). Invocata da pgAgent daily e management command Django. Ritorna il numero di utenti disattivati.';
```

---
{% include-markdown "signature-core.md" %}
