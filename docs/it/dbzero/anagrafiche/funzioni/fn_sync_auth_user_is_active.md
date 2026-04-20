{% include-markdown "it/dbzero/anagrafiche/manual/fn_sync_auth_user_is_active.md" %}
# ⚙️ Funzione `fn_sync_auth_user_is_active`

```sql
CREATE FUNCTION fn_sync_auth_user_is_active(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_sync_auth_user_is_active(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_should_active   boolean;
    v_current_active  boolean;
    v_rows_updated    integer := 0;
BEGIN
    -- ============================================================
    -- Funzione: anagrafiche.fn_sync_auth_user_is_active (v4 OR)
    -- Scopo:
    --   Sincronizza django.auth_user.is_active in base a OR
    --   logico sulle N identita_digitali dello stesso auth_user.
    --   Modello SSO multi-veste post 20-04-2026.
    -- Ritorna true se ha eseguito un UPDATE su auth_user,
    -- false altrimenti (incluso utente orfano o stato gia'
    -- allineato).
    -- ============================================================

    -- 1) Guard parametro.
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_sync_auth_user_is_active',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'parametro', 'p_auth_user_id',
                'valore', p_auth_user_id
            ),
            NULL::uuid,
            'p_auth_user_id deve essere NOT NULL e > 0'
        );
    END IF;

    -- 2) Calcolo OR: esiste almeno una identita utilizzabile?
    --    Una identita e' utilizzabile se:
    --      attiva AND ruolo != DISABILITATO
    --      AND finestra temporale corrente
    --      AND soggetto parent attivo
    --    DISABILITATO e' fail-closed per convenzione.
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
          JOIN anagrafiche.soggetti_ruoli    sr ON sr.id = id.soggetto_ruolo_id
          JOIN anagrafiche.soggetti          s  ON s.id  = sr.soggetto_id
         WHERE id.auth_user_id      = p_auth_user_id
           AND id.attivo            = true
           AND id.ruolo_applicativo <> 'DISABILITATO'
           AND CURRENT_DATE >= id.valido_dal
           AND (id.valido_al IS NULL OR CURRENT_DATE <= id.valido_al)
           AND s.attivo             = true
    )
    INTO v_should_active;

    -- 3) No-op in ambienti CI senza schema django.
    IF to_regclass('django.auth_user') IS NULL THEN
        RETURN false;
    END IF;

    -- 4) Stato corrente auth_user.
    EXECUTE 'SELECT is_active FROM django.auth_user WHERE id = $1'
       INTO v_current_active
      USING p_auth_user_id;

    -- Se l'auth_user non esiste (orfano): exit silente.
    IF v_current_active IS NULL THEN
        RETURN false;
    END IF;

    -- 5) UPDATE solo se lo stato cambia.
    IF v_current_active IS DISTINCT FROM v_should_active THEN
        EXECUTE 'UPDATE django.auth_user
                    SET is_active = $1
                  WHERE id = $2'
           USING v_should_active, p_auth_user_id;

        GET DIAGNOSTICS v_rows_updated = ROW_COUNT;
        RETURN (v_rows_updated > 0);
    END IF;

    RETURN false;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_sync_auth_user_is_active(p_auth_user_id integer)
IS 'Sincronizza django.auth_user.is_active via OR sulle N identita digitali dello stesso auth_user (modello SSO multi-veste post 20-04-2026). is_active=true se almeno una identita e'' utilizzabile (attiva, ruolo != DISABILITATO, finestra valida, soggetto attivo). Return true se ha modificato auth_user.';
```

---
{% include-markdown "signature-core.md" %}
