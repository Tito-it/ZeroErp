{% include-markdown "it/dbzero/anagrafiche/manual/fn_sync_auth_user_is_active.md" %}
# ⚙️ Funzione `fn_sync_auth_user_is_active`

```sql
CREATE FUNCTION fn_sync_auth_user_is_active(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_sync_auth_user_is_active(p_auth_user_id integer)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_should_active   boolean;  -- esito di un EXISTS: nessuna colonna dietro
    -- ⛔ Tipo ESPLICITO e non %TYPE: e' django.auth_user.is_active, e in CI
    --    Liquibase gira prima delle migrazioni Django (al CREATE lo schema
    --    django non esiste, e un %TYPE si risolve proprio al CREATE).
    v_current_active  boolean;
    v_rows_updated    integer := 0;  -- ROW_COUNT: un conteggio
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
    --    ⭐ Rev 2026-10-07 (brief-db-veste-utilizzabile): «utilizzabile»
    --    lo decide script.fn_veste_utilizzabile (accesa, nelle sue date,
    --    soggetto attivo; per l'operatore umano anche il rapporto). Prima
    --    la regola era ricopiata qui, senza il rapporto.
    --    ⭐ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): «spenta» si
    --    legge SOLO da attivo. Il secondo controllo (ruolo <> DISABILITATO)
    --    e' caduto: DISABILITATO non e' piu' un tipo di veste, la tabella
    --    viva lo rifiuta (chk_identita_digitali_ruolo_non_ritirato).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
         WHERE id.auth_user_id = p_auth_user_id
           AND script.fn_veste_utilizzabile(id.id)
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
IS 'Sincronizza django.auth_user.is_active via OR sulle N identita digitali dello stesso auth_user (modello SSO multi-veste post 20-04-2026). is_active=true se almeno una identita e'' utilizzabile (attiva, finestra valida, soggetto attivo). Return true se ha modificato auth_user. Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): spenta si legge solo da attivo, il controllo su DISABILITATO e'' caduto con il tipo (chk_identita_digitali_ruolo_non_ritirato). Rev 2026-10-07 (brief-db-veste-utilizzabile): «utilizzabile» si legge da script.fn_veste_utilizzabile, che per l''operatore umano guarda anche il rapporto: la fine del rapporto scritta dal drawer spegne la credenziale se non resta un''altra veste utilizzabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
