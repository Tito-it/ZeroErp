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
    v_count       integer := 0;
    v_risorsa_id  anagrafiche.risorse_umane.id%TYPE;
    v_modified    boolean;
BEGIN
-- ------------------------------------------------------------
-- Funzione: anagrafiche.fn_sync_auth_user_expired
--
-- Scopo:
--   Funzione batch per disattivazione utenti con finestra
--   temporale scaduta. Trova tutte le risorse umane con
--   valido_al < CURRENT_DATE che hanno ancora auth_user attivo
--   e invoca fn_sync_auth_user_is_active per ciascuna.
--   Copre il caso "scadenza overnight" non intercettabile
--   dai trigger (che reagiscono solo a UPDATE espliciti).
--
-- Parametri: nessuno
--
-- Ritorna:
--   Numero di utenti effettivamente disattivati
--
-- Uso previsto:
--   Job pgAgent giornaliero o management command Django
-- ------------------------------------------------------------

    ----------------------------------------------------------------
    -- Ciclo su risorse con finestra scaduta + auth_user ancora attivo
    ----------------------------------------------------------------
    -- In ambienti CI senza schema django, non fare nulla.
    IF to_regclass('django.auth_user') IS NULL THEN
        RETURN 0;
    END IF;

    FOR v_risorsa_id IN
        EXECUTE '
            SELECT ru.id
              FROM anagrafiche.risorse_umane ru
              JOIN anagrafiche.risorse_umane_auth_user rau
                ON rau.risorsa_umana_id = ru.id
              JOIN django.auth_user au
                ON au.id = rau.auth_user_id
             WHERE ru.valido_al IS NOT NULL
               AND ru.valido_al < CURRENT_DATE
               AND au.is_active = true
        '
    LOOP
        SELECT anagrafiche.fn_sync_auth_user_is_active(v_risorsa_id)
          INTO v_modified;

        IF v_modified THEN
            v_count := v_count + 1;
        END IF;
    END LOOP;

    RETURN v_count;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_sync_auth_user_expired()
IS 'Batch: disattiva auth_user per risorse umane con finestra temporale scaduta.
Copre il caso scadenza overnight non intercettabile dai trigger.
Ritorna il numero di utenti effettivamente disattivati.';
```

---
{% include-markdown "signature-core.md" %}
