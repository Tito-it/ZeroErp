{% include-markdown "it/dbzero/script/manual/fn_get_operatore_detail.md" %}
# ⚙️ Funzione `fn_get_operatore_detail`

```sql
CREATE FUNCTION fn_get_operatore_detail(p_auth_user_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_operatore_detail(p_auth_user_id integer)
 RETURNS TABLE(auth_user_id integer, username character varying, email character varying, first_name character varying, last_name character varying, soggetto_cognome text, soggetto_nome text, soggetto_id uuid, ragione_sociale_completa text, codice_fiscale text, ruolo_sistema text, is_super_admin boolean, ruolo_applicativo text, is_active boolean, unita_organizzativa_id integer, unita_organizzativa_nome text, risorsa_umana_id bigint, attivo boolean, valido_dal text, valido_al text, override_aree_count bigint, override_azioni_count bigint, emittenti_count bigint, emittenti_descrizione text, last_login timestamp with time zone, invito_inviato_at timestamp with time zone, deve_cambiare_password boolean, can_invite boolean, invite_reason text, can_disable boolean, disable_reason text, can_demote_super_admin boolean, demote_reason text)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Riga di dettaglio operatore + capability per il drawer
    --   admin (P1 2026-04-29). Single row per p_auth_user_id.
    --   LEFT JOIN su identita OPERATORE: la riga puo' mancare
    --   per utenti tecnici / non ancora identitizzati. La
    --   capability viene comunque calcolata sull'auth_user.
    --
    -- LANGUAGE plpgsql obbligatorio per riferimenti django.*
    -- (deferred parsing): vedi memoria
    -- feedback_django_refs_in_liquibase + fix
    -- 20260329-17-fix-fn-check-operatore-invitabile-no-django-type.
    --
    -- Capability (single source of truth):
    --   - can_invite/invite_reason via fn_check_operatore_invitabile
    --     (riusa la stessa logica del bottone Invita).
    --   - can_disable: false sse l'utente e' l'unico SUPER_ADMIN
    --     attivo (allineato a guard 384). Reason in it-IT,
    --     NULL se l'azione e' consentita.
    --   - can_demote_super_admin: NULL se l'utente non e' SA
    --     (azione non applicabile -> il frontend nasconde
    --     l'azione). Se SA: false sse e' l'ultimo, true
    --     altrimenti.
    --
    -- Note:
    --   - p_auth_user_id non valido: 0 righe (semantica
    --     "lookup by id mancante", coerente col Python).
    --   - fn_is_super_admin e' GUC-aware: in contesti non
    --     OPERATORE (portale/shop) ritorna false fail-closed.
    --     Il drawer e' admin-only -> contesto OPERATORE -> ok.
    --   - Ottimizzazione: ef_agg LATERAL combina count e
    --     descrizione in singola scansione user_emittenti_fiscali.
    -- =========================================================
    RETURN QUERY
    WITH ctx AS (
        SELECT
            script.fn_check_operatore_invitabile(p_auth_user_id)         AS inv_jsonb,
            script.fn_is_super_admin(p_auth_user_id)                      AS is_sa,
            script.fn_check_ultimo_super_admin_attivo(p_auth_user_id)     AS is_last_sa
    )
    SELECT
        au.id                                                  AS auth_user_id,
        au.username,
        au.email,
        au.first_name,
        au.last_name,
        COALESCE(s.cognome, au.last_name)                      AS soggetto_cognome,
        COALESCE(s.nome,    au.first_name)                     AS soggetto_nome,
        s.id                                                   AS soggetto_id,
        s.ragione_sociale_completa,
        s.codice_fiscale,
        script.fn_get_ruolo_sistema(au.id)::text               AS ruolo_sistema,
        ctx.is_sa                                              AS is_super_admin,
        id.ruolo_applicativo::text                             AS ruolo_applicativo,
        au.is_active,
        ru.unita_organizzativa_id,
        uo.descrizione                                         AS unita_organizzativa_nome,
        ru.id                                                  AS risorsa_umana_id,
        ru.attivo,
        ru.valido_dal::text                                    AS valido_dal,
        ru.valido_al::text                                     AS valido_al,
        COALESCE((SELECT COUNT(*) FROM config.user_override_aree uoa
                   WHERE uoa.auth_user_id = au.id), 0)         AS override_aree_count,
        COALESCE((SELECT COUNT(*) FROM config.user_override_azioni uoz
                   WHERE uoz.auth_user_id = au.id), 0)         AS override_azioni_count,
        COALESCE(ef_agg.cnt, 0)                                AS emittenti_count,
        ef_agg.descrizione                                     AS emittenti_descrizione,
        au.last_login,
        id.invito_inviato_at,
        id.deve_cambiare_password,
        -- Capability: invito (delegata a fn_check_operatore_invitabile)
        (ctx.inv_jsonb ->> 'invitabile')::boolean              AS can_invite,
        ctx.inv_jsonb ->> 'motivo'                             AS invite_reason,
        -- Capability: disabilitazione - bloccata sse ultimo SA attivo
        NOT ctx.is_last_sa                                     AS can_disable,
        CASE WHEN ctx.is_last_sa
             THEN 'Ultimo SUPER_ADMIN attivo: disabilitarlo causerebbe il lockout del sistema'
             ELSE NULL
        END                                                    AS disable_reason,
        -- Capability: demote SA. NULL se l'utente non e' SA.
        CASE WHEN ctx.is_sa
             THEN NOT ctx.is_last_sa
             ELSE NULL
        END                                                    AS can_demote_super_admin,
        CASE
             WHEN NOT ctx.is_sa  THEN NULL
             WHEN ctx.is_last_sa THEN 'Ultimo SUPER_ADMIN attivo: la rimozione del binding causerebbe il lockout del sistema'
             ELSE NULL
        END                                                    AS demote_reason
      FROM django.auth_user au
      LEFT JOIN anagrafiche.identita_digitali id
        ON id.auth_user_id      = au.id
       AND id.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
      LEFT JOIN anagrafiche.soggetti_ruoli sr
        ON sr.id = id.soggetto_ruolo_id
      LEFT JOIN anagrafiche.risorse_umane ru
        ON ru.soggetto_ruolo_id = sr.id
      LEFT JOIN anagrafiche.soggetti s
        ON s.id = sr.soggetto_id
      LEFT JOIN config.unita_organizzative uo
        ON uo.id = ru.unita_organizzativa_id
      -- Aggregazione emittenti in singola scansione (count + descrizione)
      LEFT JOIN LATERAL (
          SELECT
              COUNT(*) AS cnt,
              string_agg(
                  COALESCE(s_ef.ragione_sociale_completa, ef.descrizione),
                  ', '
                  ORDER BY COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)
              ) AS descrizione
            FROM config.user_emittenti_fiscali uef
            JOIN anagrafiche.emittenti_fiscali ef
              ON ef.id = uef.emittente_fiscale_id
            LEFT JOIN anagrafiche.soggetti_ruoli sr_ef
              ON sr_ef.id = ef.soggetto_ruolo_id
            LEFT JOIN anagrafiche.soggetti s_ef
              ON s_ef.id = sr_ef.soggetto_id
           WHERE uef.auth_user_id = au.id
      ) ef_agg ON true
      CROSS JOIN ctx
     WHERE au.id = p_auth_user_id;
END;
$function$

COMMENT ON FUNCTION script.fn_get_operatore_detail(p_auth_user_id integer)
IS 'Riga di dettaglio operatore + 6 capability per il drawer admin (P1 2026-04-29). Migra in DB la query inline da Python (apps.amm_software.db.amm_software_repository.get_operatore_detail) e calcola capability via funzioni esistenti come single source of truth: fn_check_operatore_invitabile (invito), fn_is_super_admin (status SA), fn_check_ultimo_super_admin_attivo (lockout-guard). LEFT JOIN su identita OPERATORE; per utenti senza identita i campi anagrafici sono NULL ma le capability vengono comunque calcolate. LANGUAGE plpgsql STABLE (deferred parsing per riferimenti django.*); colonne django.* nel RETURNS TABLE con tipi espliciti (no %TYPE), altre colonne con %TYPE.';
```

---
{% include-markdown "signature-core.md" %}
