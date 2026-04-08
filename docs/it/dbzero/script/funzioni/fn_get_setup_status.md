{% include-markdown "it/dbzero/script/manual/fn_get_setup_status.md" %}
# ⚙️ Funzione `fn_get_setup_status`

```sql
CREATE FUNCTION fn_get_setup_status()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_setup_status()
 RETURNS jsonb
 LANGUAGE sql
 STABLE
AS $function$
    -- Single-query con FILTER aggregations:
    -- - sub_emittenti: conta gli EF attivi
    -- - sub_op: per ogni operatore (risorsa umana attiva + auth_user
    --   attivo + ruolo non DISABILITATO) calcola in colonne booleane
    --   "ha_assoc" e "is_admin_globale"; le COUNT FILTER aggregano.
    -- Ritorno: jsonb con le 5 chiavi attese.
    WITH sub_emittenti AS (
        SELECT COUNT(*)::bigint AS emittenti_attivi
          FROM anagrafiche.emittenti_fiscali
         WHERE attivo = true
    ),
    sub_op AS (
        SELECT
            COUNT(*)::bigint AS operatori_totali,
            COUNT(*) FILTER (WHERE uef.auth_user_id IS NOT NULL)::bigint
                AS operatori_assegnati,
            COUNT(*) FILTER (
                WHERE uef.auth_user_id IS NULL
                  AND rau.ruolo_sistema = 'ADMIN'::config.ruolo_sistema
            )::bigint AS operatori_admin_globali
          FROM anagrafiche.risorse_umane_auth_user rau
          JOIN django.auth_user au
            ON au.id = rau.auth_user_id
          LEFT JOIN config.user_emittenti_fiscali uef
            ON uef.auth_user_id = rau.auth_user_id
         WHERE rau.attivo = true
           AND rau.ruolo_sistema <> 'DISABILITATO'::config.ruolo_sistema
           AND au.is_active = true
    )
    SELECT jsonb_build_object(
        'emittenti_attivi',         sub_emittenti.emittenti_attivi,
        'operatori_totali',         sub_op.operatori_totali,
        'operatori_assegnati',      sub_op.operatori_assegnati,
        'operatori_admin_globali',  sub_op.operatori_admin_globali,
        'operatori_non_assegnati',  greatest(
            sub_op.operatori_totali - sub_op.operatori_assegnati, 0
        )
    )
      FROM sub_emittenti, sub_op;
$function$

COMMENT ON FUNCTION script.fn_get_setup_status()
IS 'Stato di setup operatore-emittente in un singolo jsonb (emittenti_attivi, operatori_totali, operatori_assegnati, operatori_admin_globali, operatori_non_assegnati). Aiuto informativo per il banner di amministrazione operatori (pattern advise, don''t enforce).';
```

---
{% include-markdown "signature-core.md" %}
