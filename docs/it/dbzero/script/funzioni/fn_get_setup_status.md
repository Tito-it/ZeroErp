{% include-markdown "it/dbzero/script/manual/fn_get_setup_status.md" %}
# ⚙️ Funzione `fn_get_setup_status`

```sql
CREATE FUNCTION fn_get_setup_status()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_setup_status()
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_result jsonb;  -- oggetto composto qui: nessuna colonna dietro
BEGIN
    -- =========================================================
    -- Scopo:
    --   Stato di setup operatore-emittente per il banner di
    --   amministrazione (pattern advise, don't enforce).
    --
    -- Refactor §4.6.B.10:
    --   Source of truth operatori = identita_digitali
    --   (ruolo_applicativo=OPERATORE, utilizzabile oggi:
    --   script.fn_veste_utilizzabile, rev 2026-10-07).
    --   Admin = fn_is_super_admin anziche' ruolo_sistema='ADMIN'.
    -- =========================================================

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
                  AND script.fn_is_super_admin(id.auth_user_id)
            )::bigint AS operatori_admin_globali
          FROM anagrafiche.identita_digitali id
          JOIN django.auth_user au
            ON au.id = id.auth_user_id
          LEFT JOIN config.user_emittenti_fiscali uef
            ON uef.auth_user_id = id.auth_user_id
         WHERE id.ruolo_applicativo = 'OPERATORE'
           AND script.fn_veste_utilizzabile(id.id)
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
      INTO v_result
      FROM sub_emittenti, sub_op;

    RETURN v_result;
END
$function$

COMMENT ON FUNCTION script.fn_get_setup_status()
IS 'Stato di setup operatore-emittente in un singolo jsonb. Refactor §4.6.B.10: source of truth operatori = identita_digitali (OPERATORE attiva); admin = fn_is_super_admin. Rev 2026-10-07 (brief-db-veste-utilizzabile): un operatore conta se la sua veste e'' utilizzabile oggi (script.fn_veste_utilizzabile), non piu'' attivo + finestra ricopiati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
