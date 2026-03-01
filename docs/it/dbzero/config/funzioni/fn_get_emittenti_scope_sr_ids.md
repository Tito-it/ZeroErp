{% include-markdown "it/dbzero/config/manual/fn_get_emittenti_scope_sr_ids.md" %}
# ⚙️ Funzione `fn_get_emittenti_scope_sr_ids`

```sql
CREATE FUNCTION fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
 RETURNS bigint[]
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_ruolo config.ruolo_sistema;
  v_ids   bigint[];
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituisce i soggetto_ruolo_id degli emittenti fiscali
  --   autorizzati per un utente. Le tabelle vendite usano
  --   emittente_soggetto_ruolo_id (FK a soggetti_ruoli),
  --   non emittente_fiscale_id, quindi serve questa mappatura.
  --
  -- Semantica:
  --   NULL             = nessuna restrizione (vede tutto)
  --   '{}'::bigint[]   = nessun accesso (0 righe match)
  --   array di ID      = limitato a quegli emittenti
  -- =========================================================

  -- 1. Ruolo sistema
  v_ruolo := config.fn_get_ruolo_sistema(p_auth_user_id);

  IF v_ruolo IS NULL OR v_ruolo = 'DISABILITATO' THEN
    RETURN '{}'::bigint[];  -- nessun accesso
  END IF;

  IF v_ruolo = 'ADMIN' THEN
    RETURN NULL;  -- nessuna restrizione
  END IF;

  -- 2. OPERATIVO: mappa whitelist a soggetto_ruolo_id
  SELECT array_agg(ef.soggetto_ruolo_id)
    INTO v_ids
    FROM config.user_emittenti_fiscali uef
    JOIN anagrafiche.emittenti_fiscali ef
      ON ef.id = uef.emittente_fiscale_id
   WHERE uef.auth_user_id = p_auth_user_id;

  -- NULL (whitelist vuota) = nessuna restrizione
  -- array = limitato
  RETURN v_ids;
END
$function$

COMMENT ON FUNCTION config.fn_get_emittenti_scope_sr_ids(p_auth_user_id integer)
IS 'Mappa emittenti autorizzati a soggetto_ruolo_id per query vendite (NULL = nessuna restrizione).';
```

---
{% include-markdown "signature-core.md" %}
