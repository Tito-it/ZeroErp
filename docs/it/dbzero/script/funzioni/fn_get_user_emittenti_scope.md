{% include-markdown "it/dbzero/script/manual/fn_get_user_emittenti_scope.md" %}
# ⚙️ Funzione `fn_get_user_emittenti_scope`

```sql
CREATE FUNCTION fn_get_user_emittenti_scope(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_emittenti_scope(p_auth_user_id integer)
 RETURNS TABLE(auth_user_id integer, scope_mode text, emittente_id bigint, emittente_descrizione text, allowed_scope_modes text[], can_change_scope boolean, change_scope_reason text)
 LANGUAGE sql
 STABLE
AS $function$
    -- =========================================================
    -- Scopo:
    --   Vista dichiarativa "scope emittenti" per un auth_user.
    --   Ritorna sempre 1 riga (anche se l'utente non ha
    --   associazioni emittente: scope_mode=GLOBAL).
    --
    -- Mappatura scope_mode (Fase 2):
    --   - 0 righe in user_emittenti_fiscali  -> GLOBAL
    --   - 1 riga                              -> SINGLE
    --   - >1 righe                            -> impossibile per
    --     UNIQUE(auth_user_id) introdotto in Fase 1 refactor
    --     operatore-emittenti (20260408-11). Il vincolo DB
    --     copre il caso MULTI: la fn vede al massimo 1 riga.
    --
    -- Capability:
    --   can_change_scope = NOT fn_check_ultimo_super_admin_attivo
    --   (regola unica: se sei l'ultimo SUPER_ADMIN, lockout
    --   guard - allineato a Fase 1).
    --
    -- Note:
    --   - VALUES base garantisce 1 riga anche se l'auth_user
    --     non ha mai avuto associazioni (LEFT JOIN da base
    --     verso user_emittenti_fiscali).
    --   - Nessun filtro su esistenza identita OPERATORE: il
    --     caller (drawer admin) gia' interroga la fn solo
    --     per operatori esistenti. Mantenere la firma generica
    --     evita falsi 0-rows quando un auth_user tecnico viene
    --     comunque interrogato per diagnostica.
    --   - emittente_descrizione pre-aggregata: COALESCE
    --     ragione_sociale_completa | descrizione (stesso
    --     pattern di fn_get_operatore_detail).
    -- =========================================================
    WITH state AS (
        SELECT
            p_auth_user_id                                                   AS auth_user_id,
            uef.emittente_fiscale_id                                         AS emittente_id,
            COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)::text    AS emittente_descrizione,
            script.fn_check_ultimo_super_admin_attivo(p_auth_user_id)        AS is_last_sa
          FROM (VALUES (p_auth_user_id)) AS b(auth_user_id)
          LEFT JOIN config.user_emittenti_fiscali uef
            ON uef.auth_user_id = b.auth_user_id
          LEFT JOIN anagrafiche.emittenti_fiscali ef
            ON ef.id = uef.emittente_fiscale_id
          LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
            ON sr_ef.id = ef.soggetto_ruolo_id
          LEFT JOIN anagrafiche.soggetti s_ef
            ON s_ef.id = sr_ef.soggetto_id
    )
    SELECT
        s.auth_user_id,
        CASE WHEN s.emittente_id IS NULL THEN 'GLOBAL' ELSE 'SINGLE' END  AS scope_mode,
        s.emittente_id,
        s.emittente_descrizione,
        ARRAY['GLOBAL','SINGLE']::text[]                                     AS allowed_scope_modes,
        NOT s.is_last_sa                                                     AS can_change_scope,
        CASE WHEN s.is_last_sa
             THEN 'Ultimo SUPER_ADMIN attivo: il cambio scope e'' bloccato per evitare il lockout del sistema'
             ELSE NULL
        END                                                                  AS change_scope_reason
      FROM state s;
$function$

COMMENT ON FUNCTION script.fn_get_user_emittenti_scope(p_auth_user_id integer)
IS 'Vista dichiarativa dello scope emittenti per un auth_user (drawer Operatore Fase 2 P1 2026-04-29). Ritorna sempre 1 riga (GLOBAL se l''utente non ha associazioni). MULTI e'' impossibile per UNIQUE(auth_user_id) di Fase 1; allowed_scope_modes resta TEXT[] per non vincolare il futuro. Capability can_change_scope derivata da fn_check_ultimo_super_admin_attivo (regola unica: lockout-guard). LANGUAGE sql STABLE.';
```

---
{% include-markdown "signature-core.md" %}
