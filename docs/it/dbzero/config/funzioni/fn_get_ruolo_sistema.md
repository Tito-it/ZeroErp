{% include-markdown "it/dbzero/config/manual/fn_get_ruolo_sistema.md" %}
# ⚙️ Funzione `fn_get_ruolo_sistema`

```sql
CREATE FUNCTION fn_get_ruolo_sistema(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_get_ruolo_sistema(p_auth_user_id integer)
 RETURNS config.ruolo_sistema
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_ruolo config.ruolo_sistema;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce il ruolo_sistema di un utente dalla tabella
  --   ponte anagrafiche.risorse_umane_auth_user.
  --   NULL se l'utente non ha record ponte.
  --
  -- Blocco base riusato da tutte le funzioni di risoluzione
  -- permessi (fn_resolve_livello_area, fn_check_azione_processo,
  -- fn_check_user_emittente_scope).
  -- =========================================================

  SELECT rau.ruolo_sistema
    INTO v_ruolo
    FROM anagrafiche.risorse_umane_auth_user rau
   WHERE rau.auth_user_id = p_auth_user_id;

  RETURN v_ruolo;
END
$function$

COMMENT ON FUNCTION config.fn_get_ruolo_sistema(p_auth_user_id integer)
IS 'Restituisce il ruolo_sistema di un utente (NULL se nessun record ponte).';
```

---
{% include-markdown "signature-core.md" %}
