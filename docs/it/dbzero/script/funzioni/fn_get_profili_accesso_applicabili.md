{% include-markdown "it/dbzero/script/manual/fn_get_profili_accesso_applicabili.md" %}
# ⚙️ Funzione `fn_get_profili_accesso_applicabili`

```sql
CREATE FUNCTION fn_get_profili_accesso_applicabili(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_profili_accesso_applicabili(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo DEFAULT NULL::config.ruolo_applicativo)
 RETURNS TABLE(profilo_accesso_id integer, priorita smallint)
 LANGUAGE sql
 STABLE
AS $function$
    -- =========================================================
    -- Risolve i profili di accesso applicabili a un utente
    -- via bindings (AD_HOC prio 1, PORTALE/REPARTO prio 2).
    --
    -- Post 20-04-2026 accetta p_ruolo_applicativo opzionale:
    --   NULL -> tutti i profili applicabili all'user
    --           (comportamento legacy, backward compat)
    --   non NULL -> filtra solo le identita dell'user con
    --               quel ruolo_applicativo (veste corrente)
    --
    -- Le 3 subquery condividono il predicato
    --   AND (p_ruolo_applicativo IS NULL OR
    --        id.ruolo_applicativo = p_ruolo_applicativo)
    -- che e' idempotente quando p_ruolo_applicativo e' NULL.
    -- =========================================================

    -- 1) AD_HOC: binding diretto sull'identita
    SELECT DISTINCT
           pab.profilo_accesso_id,
           1::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN config.profili_accesso_bindings pab
        ON pab.identita_digitale_id = id.id
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id      = p_auth_user_id
       AND id.attivo            = true
       AND id.ruolo_applicativo <> 'DISABILITATO'
       AND (p_ruolo_applicativo IS NULL
            OR id.ruolo_applicativo = p_ruolo_applicativo)
       AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
       AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
       AND pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'AD_HOC'::config.tipo_profilo_accesso

    UNION ALL

    -- 2) PORTALE: binding per ruolo_applicativo dell'identita
    SELECT DISTINCT
           pab.profilo_accesso_id,
           2::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN config.profili_accesso_bindings pab
        ON pab.ruolo_applicativo = id.ruolo_applicativo
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id      = p_auth_user_id
       AND id.attivo            = true
       AND id.ruolo_applicativo <> 'DISABILITATO'
       AND (p_ruolo_applicativo IS NULL
            OR id.ruolo_applicativo = p_ruolo_applicativo)
       AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
       AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
       AND pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'PORTALE'::config.tipo_profilo_accesso

    UNION ALL

    -- 3) REPARTO: binding per UO (solo identita OPERATORE)
    SELECT DISTINCT
           pab.profilo_accesso_id,
           2::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN anagrafiche.risorse_umane ru
        ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
      JOIN config.profili_accesso_bindings pab
        ON pab.unita_organizzativa_id = ru.unita_organizzativa_id
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id      = p_auth_user_id
       AND id.attivo            = true
       AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND (p_ruolo_applicativo IS NULL
            OR p_ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo)
       AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
       AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
       AND ru.attivo  = true
       AND pab.attivo = true
       AND pa.attivo  = true
       AND pa.tipo    = 'REPARTO'::config.tipo_profilo_accesso;
$function$

COMMENT ON FUNCTION script.fn_get_profili_accesso_applicabili(p_auth_user_id integer, p_ruolo_applicativo config.ruolo_applicativo)
IS 'Profili applicabili a un auth_user (AD_HOC prio 1, PORTALE/REPARTO prio 2). Parametro p_ruolo_applicativo opzionale (post 20-04-2026): se NULL comportamento legacy (tutte le vesti), se valorizzato filtra la veste corrente. Usato dai resolver generalizzati.';
```

---
{% include-markdown "signature-core.md" %}
