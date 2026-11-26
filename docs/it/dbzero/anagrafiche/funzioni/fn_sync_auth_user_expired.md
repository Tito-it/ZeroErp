{% include-markdown "it/dbzero/anagrafiche/manual/fn_sync_auth_user_expired.md" %}
# ⚙️ Funzione `fn_sync_auth_user_expired`

```sql
CREATE FUNCTION fn_sync_auth_user_expired()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_sync_auth_user_expired()
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id anagrafiche.identita_digitali.auth_user_id%TYPE;
    v_modified     boolean;        -- esito di fn_sync_auth_user_is_active: nessuna colonna dietro
    v_count        integer := 0;   -- un conteggio
BEGIN
    -- =========================================================
    -- Scopo: riallinea auth_user.is_active alla data di oggi, nei
    --   due versi, per le scritture che non arrivano: una data
    --   che passa non fa scattare trigger. Spegne la credenziale
    --   che non ha piu' nessuna veste utilizzabile (veste o
    --   rapporto scaduti, o nessuna veste), accende quella che
    --   ne ha una diventata valida oggi. La regola e' una sola,
    --   quella di fn_sync_auth_user_is_active, che fa
    --   l'aggiornamento. Ritorna le credenziali riallineate.
    -- =========================================================

    -- Senza lo schema django (CI, Liquibase prima di Django): niente da fare.
    IF to_regclass('django.auth_user') IS NULL THEN
        RETURN 0;
    END IF;

    -- I candidati: ogni credenziale il cui is_active non dice
    -- «esiste una veste utilizzabile oggi», anche quella senza vesti.
    FOR v_auth_user_id IN
        EXECUTE '
            SELECT au.id
              FROM django.auth_user au
             WHERE au.is_active IS DISTINCT FROM EXISTS (
                       SELECT 1
                         FROM anagrafiche.identita_digitali id
                        WHERE id.auth_user_id = au.id
                          AND script.fn_veste_utilizzabile(id.id))
             ORDER BY au.id
        '
    LOOP
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
IS 'Riallinea django.auth_user.is_active alla data di oggi nei due versi, perche'' una data che arriva non scrive niente e non fa scattare trigger. Spegne le credenziali che non hanno piu'' nessuna veste utilizzabile (veste o rapporto scaduti, o nessuna veste) e accende quelle che ne hanno una diventata valida oggi; la regola e'' script.fn_veste_utilizzabile, la stessa di anagrafiche.fn_sync_auth_user_is_active, che fa l''aggiornamento. La chiamano il job pgAgent sync_auth_user_expired_daily (ogni ora) e il management command Django sync_auth_user_active. Ritorna il numero di credenziali riallineate (spente o accese). Senza lo schema django ritorna 0.';
```

</div>

---
{% include-markdown "signature-core.md" %}
