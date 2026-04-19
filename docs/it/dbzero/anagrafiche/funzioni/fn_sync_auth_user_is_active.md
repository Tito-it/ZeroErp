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
    v_ruolo_appl        anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
    v_id_attivo         anagrafiche.identita_digitali.attivo%TYPE;
    v_id_valido_dal     anagrafiche.identita_digitali.valido_dal%TYPE;
    v_id_valido_al      anagrafiche.identita_digitali.valido_al%TYPE;
    v_soggetto_ruolo_id anagrafiche.identita_digitali.soggetto_ruolo_id%TYPE;
    v_soggetto_attivo   anagrafiche.soggetti.attivo%TYPE;
    v_should_active     boolean;
    v_current_active    boolean;
    v_rows_updated      integer := 0;
BEGIN
    -- ------------------------------------------------------------
    -- Funzione: anagrafiche.fn_sync_auth_user_is_active (v3)
    -- Scopo:
    --   Sincronizza django.auth_user.is_active a partire da
    --   anagrafiche.identita_digitali. Post-cutover §13.3.4:
    --   nessun fallback su risorse_umane_auth_user (ora vista),
    --   nessuna doppia verifica legacy su risorse_umane.
    -- ------------------------------------------------------------

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

    -- 2) Lookup identita attiva (UNIQUE auth_user_id -> una riga).
    SELECT id.ruolo_applicativo,
           id.attivo,
           id.valido_dal,
           id.valido_al,
           id.soggetto_ruolo_id
      INTO v_ruolo_appl,
           v_id_attivo,
           v_id_valido_dal,
           v_id_valido_al,
           v_soggetto_ruolo_id
      FROM anagrafiche.identita_digitali id
     WHERE id.auth_user_id = p_auth_user_id
     ORDER BY id.id DESC
     LIMIT 1;

    -- Utente orfano (nessuna identita): exit silente.
    IF NOT FOUND THEN
        RETURN false;
    END IF;

    -- 3) Logica di calcolo su identita_digitali.
    IF v_ruolo_appl = 'DISABILITATO' THEN
        v_should_active := false;
    ELSE
        -- 3.a) Identita attiva + finestra temporale valida.
        v_should_active :=
            v_id_attivo
            AND CURRENT_DATE >= v_id_valido_dal
            AND (v_id_valido_al IS NULL
                 OR CURRENT_DATE <= v_id_valido_al);

        -- 3.b) Soggetto parent deve essere attivo.
        IF v_should_active THEN
            SELECT s.attivo
              INTO v_soggetto_attivo
              FROM anagrafiche.soggetti_ruoli sr
              JOIN anagrafiche.soggetti s
                ON s.id = sr.soggetto_id
             WHERE sr.id = v_soggetto_ruolo_id;

            v_should_active := COALESCE(v_soggetto_attivo, false);
        END IF;
    END IF;

    -- 4) No-op in ambienti CI senza schema django.
    IF to_regclass('django.auth_user') IS NULL THEN
        RETURN false;
    END IF;

    -- 5) Stato corrente auth_user.
    EXECUTE 'SELECT is_active FROM django.auth_user WHERE id = $1'
       INTO v_current_active
      USING p_auth_user_id;

    -- 6) UPDATE solo se lo stato cambia.
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
IS 'Sincronizza django.auth_user.is_active da anagrafiche.identita_digitali. Post-cutover §13.3.4: nessun fallback su RUA (ora vista), nessuna doppia verifica su risorse_umane.attivo. Return true se ha modificato auth_user.';
```

---
{% include-markdown "signature-core.md" %}
