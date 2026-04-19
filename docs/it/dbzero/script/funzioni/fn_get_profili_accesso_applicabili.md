{% include-markdown "it/dbzero/script/manual/fn_get_profili_accesso_applicabili.md" %}
# ⚙️ Funzione `fn_get_profili_accesso_applicabili`

```sql
CREATE FUNCTION fn_get_profili_accesso_applicabili(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_profili_accesso_applicabili(p_auth_user_id integer)
 RETURNS TABLE(profilo_accesso_id integer, priorita smallint)
 LANGUAGE sql
 STABLE
AS $function$
    -- 1) AD_HOC: binding diretto sull'identita
    --    (override personale, priorita 1).
    SELECT DISTINCT
           pab.profilo_accesso_id,
           1::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN config.profili_accesso_bindings pab
        ON pab.identita_digitale_id = id.id
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id = p_auth_user_id
       AND id.attivo = true
       AND id.ruolo_applicativo <> 'DISABILITATO'
       AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
       AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
       AND pab.attivo = true
       AND pa.attivo = true
       AND pa.tipo = 'AD_HOC'::config.tipo_profilo_accesso

    UNION ALL

    -- 2) PORTALE: binding per ruolo_applicativo dell'identita
    --    (default per CLIENTE_PORTALE / FORNITORE_PORTALE /
    --    SHOP_CUSTOMER, priorita 2).
    SELECT DISTINCT
           pab.profilo_accesso_id,
           2::smallint AS priorita
      FROM anagrafiche.identita_digitali id
      JOIN config.profili_accesso_bindings pab
        ON pab.ruolo_applicativo = id.ruolo_applicativo
      JOIN config.profili_accesso pa
        ON pa.id = pab.profilo_accesso_id
     WHERE id.auth_user_id = p_auth_user_id
       AND id.attivo = true
       AND id.ruolo_applicativo <> 'DISABILITATO'
       AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
       AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
       AND pab.attivo = true
       AND pa.attivo = true
       AND pa.tipo = 'PORTALE'::config.tipo_profilo_accesso

    UNION ALL

    -- 3) REPARTO: binding per unita_organizzativa dell'operatore
    --    (default per OPERATORE, risolta via risorse_umane,
    --    priorita 2).
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
     WHERE id.auth_user_id = p_auth_user_id
       AND id.attivo = true
       AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
       AND (id.valido_dal IS NULL OR id.valido_dal <= CURRENT_DATE)
       AND (id.valido_al  IS NULL OR id.valido_al  >= CURRENT_DATE)
       AND ru.attivo = true
       AND pab.attivo = true
       AND pa.attivo = true
       AND pa.tipo = 'REPARTO'::config.tipo_profilo_accesso;
$function$

COMMENT ON FUNCTION script.fn_get_profili_accesso_applicabili(p_auth_user_id integer)
IS 'Risolve i profili di accesso applicabili a un utente via identita digitali + bindings (AD_HOC prio 1, PORTALE/REPARTO prio 2). Usata dai resolver generalizzati §4.8 WIP multi-face-auth.';
```

---
{% include-markdown "signature-core.md" %}
