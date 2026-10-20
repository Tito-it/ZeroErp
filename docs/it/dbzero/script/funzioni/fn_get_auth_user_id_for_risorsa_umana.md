{% include-markdown "it/dbzero/script/manual/fn_get_auth_user_id_for_risorsa_umana.md" %}
# ⚙️ Funzione `fn_get_auth_user_id_for_risorsa_umana`

```sql
CREATE FUNCTION fn_get_auth_user_id_for_risorsa_umana(p_risorsa_umana_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_auth_user_id_for_risorsa_umana(p_risorsa_umana_id bigint)
 RETURNS integer
 LANGUAGE sql
 STABLE
AS $function$
    -- La catena risorsa umana -> identita' OPERATORE -> auth_user, dalla madre.
    -- Nessun filtro su attivo (vedi intestazione): attiva prima, poi la piu' recente.
    SELECT id.auth_user_id
      FROM anagrafiche.identita_digitali id
      JOIN anagrafiche.risorse_umane     ru
        ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
     WHERE ru.id                = p_risorsa_umana_id
       AND id.ruolo_applicativo = 'OPERATORE'
     ORDER BY id.attivo DESC, id.id DESC
     LIMIT 1;
$function$

COMMENT ON FUNCTION script.fn_get_auth_user_id_for_risorsa_umana(p_risorsa_umana_id bigint)
IS 'auth_user_id dell''identita'' OPERATORE collegata a una risorsa umana (identita_digitali JOIN risorse_umane su soggetto_ruolo_id). Nessun filtro su attivo: attiva prima, poi la piu'' recente; NULL se non collegata. Gemella nel verso opposto di script.fn_get_uo_id_for_user. Nata il 12-09-2026 ritirando la vista risorse_umane_auth_user (regola del 2: due lettori).';
```

</div>

---
{% include-markdown "signature-core.md" %}
