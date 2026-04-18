# ⚙️ Funzione `fn_has_identita_attiva`

```sql
CREATE FUNCTION fn_has_identita_attiva(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_has_identita_attiva(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Verifica esistenza identita_digitali attiva, nella finestra
    -- temporale, con ruolo_applicativo dato. Fail-closed su NULL
    -- auth_user_id (EXISTS restituisce false).
    SELECT EXISTS (
        SELECT 1
          FROM anagrafiche.identita_digitali id
         WHERE id.auth_user_id = p_auth_user_id
           AND id.ruolo_applicativo = p_ruolo_applicativo
           AND id.attivo = true
           AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
           AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
    );
$function$

COMMENT ON FUNCTION script.fn_has_identita_attiva(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
IS 'Verifica se esiste un''identita attiva nella finestra temporale per un auth_user_id e ruolo_applicativo dati. Helper DRY per le funzioni di risoluzione permessi/scope (§4.6.B.0 WIP multi-face-auth). LANGUAGE sql STABLE: inlineable, fail-closed su NULL.';
```

---
{% include-markdown "signature-core.md" %}
