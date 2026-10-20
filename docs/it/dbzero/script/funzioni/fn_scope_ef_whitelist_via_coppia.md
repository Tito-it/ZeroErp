{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_coppia.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_coppia`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_coppia(p_auth_user_id integer, p_istanza_utility_id bigint, p_utility_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_coppia(p_auth_user_id integer, p_istanza_utility_id bigint, p_utility_id integer)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro il BA
    --   della coppia (istanza, utility).
    -- ⭐ Delega alla scope del BA invece di ripeterla: la regola
    --   «quale BA vede l'operatore» resta scritta in un posto solo.
    -- ⚠️ BA invisibile (fuori perimetro, RLS) o coppia senza BA ->
    --   id NULL -> false: fail-closed.
    SELECT script.fn_scope_ef_whitelist_via_efba(
        p_auth_user_id,
        (SELECT ba.id
           FROM anagrafiche.billing_account ba
          WHERE ba.istanza_utility_id = p_istanza_utility_id
            AND ba.utility_id         = p_utility_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_coppia(p_auth_user_id integer, p_istanza_utility_id bigint, p_utility_id integer)
IS 'Scope RLS per le righe che nominano la coppia (istanza_utility_id, utility_id): true se l''operatore vede il billing account della coppia. Delega a script.fn_scope_ef_whitelist_via_efba (la regola resta una). BA fuori perimetro o assente: false (fail-closed). Usata dalla policy rls_istanze_dati_precontrattuali_ef_whitelist. Brief: brief-db-istanza-nasce-col-ba (§6.13).';
```

</div>

---
{% include-markdown "signature-core.md" %}
