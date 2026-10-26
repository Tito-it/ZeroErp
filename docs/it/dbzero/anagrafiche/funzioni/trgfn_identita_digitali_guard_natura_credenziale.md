{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_identita_digitali_guard_natura_credenziale.md" %}
# ⚙️ Funzione `trgfn_identita_digitali_guard_natura_credenziale`

```sql
CREATE FUNCTION trgfn_identita_digitali_guard_natura_credenziale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_identita_digitali_guard_natura_credenziale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_di_sistema  boolean;   -- la natura della riga che passa (calcolata)
    v_altra_id    anagrafiche.identita_digitali.id%TYPE;
    v_altra_ruolo anagrafiche.identita_digitali.ruolo_applicativo%TYPE;
    -- ⚠️ Tipo esplicito: colonna di django.auth_user. Lo schema
    --    django non esiste quando Liquibase crea la funzione, e un
    --    %TYPE si risolverebbe proprio al CREATE.
    v_username    text;
BEGIN
    -- ------------------------------------------------------------
    -- Guard: tutte le vesti di una credenziale hanno la stessa
    -- natura, persona o macchina (script.fn_veste_di_sistema).
    -- Anche le spente contano: una veste spenta e' ancora della
    -- sua credenziale, e riaccenderla non deve poter mescolare.
    -- Fase a10, BEFORE INSERT / UPDATE OF auth_user_id,
    -- ruolo_applicativo, tecnica.
    -- ------------------------------------------------------------
    v_di_sistema := script.fn_veste_di_sistema(NEW.ruolo_applicativo, NEW.tecnica);

    -- NEW.id e' gia' assegnato in INSERT (il DEFAULT precede i trigger
    -- BEFORE): la riga stessa si esclude per id, in tutti e due i casi.
    SELECT idg.id, idg.ruolo_applicativo
      INTO v_altra_id, v_altra_ruolo
      FROM anagrafiche.identita_digitali idg
     WHERE idg.auth_user_id = NEW.auth_user_id
       AND idg.id <> NEW.id
       AND script.fn_veste_di_sistema(idg.ruolo_applicativo, idg.tecnica)
           <> v_di_sistema
     ORDER BY idg.id
     LIMIT 1;

    IF FOUND THEN
        SELECT au.username::text
          INTO v_username
          FROM django.auth_user au
         WHERE au.id = NEW.auth_user_id;

        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_CREDENZIALE_PERSONA_E_SISTEMA',
            jsonb_build_object(
                'table',                  TG_TABLE_NAME,
                'auth_user_id',           NEW.auth_user_id,
                'identita_id',            NEW.id,
                'ruolo_applicativo',      NEW.ruolo_applicativo,
                'veste_di_sistema',       v_di_sistema,
                'altra_identita_id',      v_altra_id,
                'altra_ruolo_applicativo', v_altra_ruolo
            ),
            NULL::uuid,
            COALESCE(v_username, NEW.auth_user_id::text)
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_identita_digitali_guard_natura_credenziale()
IS 'Guard a10 su anagrafiche.identita_digitali (BEFORE INSERT / UPDATE OF auth_user_id, ruolo_applicativo, tecnica): tutte le vesti di una credenziale, anche spente, hanno la stessa natura, persona o macchina (script.fn_veste_di_sistema). Altrimenti E_CREDENZIALE_PERSONA_E_SISTEMA. Una credenziale e'' una password per tutte le porte, e le sue azioni (blocco, secondo fattore) sono di tutte le sue vesti: su una credenziale mista bloccare la persona fermerebbe il processo. Rende univoca la categoria script.fn_categoria_accesso. Le righe gia'' scritte, e la gara fra due transazioni concorrenti, le segnala il presidio dbops.vw_credenziali_da_sanare. Brief: brief-db-be-fe-area-accessi (R-DB-A1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
