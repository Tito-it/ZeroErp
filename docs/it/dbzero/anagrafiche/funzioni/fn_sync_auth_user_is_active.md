# ⚙️ Funzione `fn_sync_auth_user_is_active`

```sql
CREATE FUNCTION fn_sync_auth_user_is_active(p_risorsa_umana_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_sync_auth_user_is_active(p_risorsa_umana_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_auth_user_id   anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE;
    v_bridge_attivo  anagrafiche.risorse_umane_auth_user.attivo%TYPE;
    v_risorsa_attivo anagrafiche.risorse_umane.attivo%TYPE;
    v_valido_dal     anagrafiche.risorse_umane.valido_dal%TYPE;
    v_valido_al      anagrafiche.risorse_umane.valido_al%TYPE;
    v_should_active  boolean;
    v_current_active django.auth_user.is_active%TYPE;
BEGIN
-- ------------------------------------------------------------
-- Funzione: anagrafiche.fn_sync_auth_user_is_active
--
-- Scopo:
--   Sincronizza django.auth_user.is_active in base allo stato
--   della risorsa umana collegata.
--   Valuta tre condizioni (AND logico):
--     1. risorse_umane.attivo = true
--     2. risorse_umane_auth_user.attivo = true
--     3. CURRENT_DATE dentro finestra [valido_dal, valido_al]
--   Se una qualsiasi condizione non e' soddisfatta -> is_active = false.
--   Aggiorna solo se il valore e' diverso (evita UPDATE inutili).
--
-- Parametri:
--   p_risorsa_umana_id -> ID della risorsa umana (NOT NULL, > 0)
--
-- Ritorna:
--   true se ha modificato auth_user, false altrimenti
-- ------------------------------------------------------------

    ----------------------------------------------------------------
    -- 1) Guard: parametro non nullo e valido
    ----------------------------------------------------------------
    IF p_risorsa_umana_id IS NULL OR p_risorsa_umana_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.fn_sync_auth_user_is_active',
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
    -- 2) Recupero dati bridge (se esiste)
    ----------------------------------------------------------------
    SELECT rau.auth_user_id, rau.attivo
      INTO v_auth_user_id, v_bridge_attivo
      FROM anagrafiche.risorse_umane_auth_user rau
     WHERE rau.risorsa_umana_id = p_risorsa_umana_id;

    -- Se la risorsa non ha un collegamento auth_user, nulla da fare
    IF v_auth_user_id IS NULL THEN
        RETURN false;
    END IF;

    ----------------------------------------------------------------
    -- 3) Recupero stato risorsa umana
    ----------------------------------------------------------------
    SELECT ru.attivo, ru.valido_dal, ru.valido_al
      INTO v_risorsa_attivo, v_valido_dal, v_valido_al
      FROM anagrafiche.risorse_umane ru
     WHERE ru.id = p_risorsa_umana_id;

    ----------------------------------------------------------------
    -- 4) Calcolo stato atteso (AND logico)
    ----------------------------------------------------------------
    v_should_active :=
        v_risorsa_attivo
        AND v_bridge_attivo
        AND CURRENT_DATE >= v_valido_dal
        AND (v_valido_al IS NULL OR CURRENT_DATE <= v_valido_al);

    ----------------------------------------------------------------
    -- 5) Recupero stato corrente auth_user
    ----------------------------------------------------------------
    SELECT au.is_active
      INTO v_current_active
      FROM django.auth_user au
     WHERE au.id = v_auth_user_id;

    ----------------------------------------------------------------
    -- 6) Aggiorna solo se diverso
    ----------------------------------------------------------------
    IF v_current_active IS DISTINCT FROM v_should_active THEN
        UPDATE django.auth_user
           SET is_active = v_should_active
         WHERE id = v_auth_user_id;
        RETURN true;
    END IF;

    RETURN false;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_sync_auth_user_is_active(p_risorsa_umana_id bigint)
IS 'Sincronizza auth_user.is_active con lo stato della risorsa umana.
Valuta: risorse_umane.attivo, finestra temporale, bridge attivo.
Aggiorna solo se il valore cambia. Ritorna true se ha modificato auth_user.';
```

---
{% include-markdown "signature-core.md" %}
