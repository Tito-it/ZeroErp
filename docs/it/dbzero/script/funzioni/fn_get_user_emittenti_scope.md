{% include-markdown "it/dbzero/script/manual/fn_get_user_emittenti_scope.md" %}
# ⚙️ Funzione `fn_get_user_emittenti_scope`

```sql
CREATE FUNCTION fn_get_user_emittenti_scope(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_user_emittenti_scope(p_auth_user_id integer)
 RETURNS TABLE(auth_user_id integer, scope_mode text, emittente_id bigint, emittente_descrizione text, allowed_scope_modes text[], can_change_scope boolean, change_scope_reason text)
 LANGUAGE sql
 STABLE
AS $function$
    -- =========================================================
    -- Scopo:
    --   Lo stato dell'assegnazione di un utente a un emittente, per il
    --   drawer dell'operatore. Ritorna sempre una riga.
    --
    -- scope_mode:
    --   - con la riga in config.user_emittenti_fiscali -> SINGLE,
    --     con il suo emittente;
    --   - senza riga, SUPER_ADMIN -> GLOBAL («Tutti gli emittenti»);
    --   - senza riga, chi non e' SUPER_ADMIN -> SINGLE con emittente_id
    --     NULL: lavora per un emittente, ancora da scegliere. Dal
    --     fail-closed non vede niente finche' non e' assegnato.
    --   La UNIQUE(auth_user_id) tiene al massimo una riga.
    --
    -- allowed_scope_modes:
    --   ['GLOBAL','SINGLE'] al SUPER_ADMIN, ['SINGLE'] agli altri: un
    --   operatore non e' mai «globale» (script.fn_applica_user_emittenti_scope
    --   lo rifiuta). La domanda e' script.fn_is_super_admin_account
    --   sull'utente interrogato, non sulla veste della sessione.
    --
    -- can_change_scope:
    --   NOT script.fn_check_ultimo_super_admin_attivo: l'ultimo
    --   SUPER_ADMIN attivo non si sposta.
    --
    -- Note:
    --   - la base VALUES da' la riga anche senza assegnazione;
    --   - nessun filtro sulla veste OPERATORE: il drawer interroga solo
    --     operatori, e la firma generica non da' zero righe a un utente
    --     tecnico interrogato per diagnostica;
    --   - emittente_descrizione e' la ragione sociale del soggetto.
    -- =========================================================
    WITH state AS (
        SELECT
            p_auth_user_id                                                   AS auth_user_id,
            uef.emittente_fiscale_id                                         AS emittente_id,
            s_ef.ragione_sociale_completa                                    AS emittente_descrizione,
            script.fn_check_ultimo_super_admin_attivo(p_auth_user_id)        AS is_last_sa,
            script.fn_is_super_admin_account(p_auth_user_id)                 AS is_sa
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
        CASE WHEN s.emittente_id IS NULL AND s.is_sa THEN 'GLOBAL' ELSE 'SINGLE' END,
        s.emittente_id,
        s.emittente_descrizione,
        CASE WHEN s.is_sa THEN ARRAY['GLOBAL','SINGLE'] ELSE ARRAY['SINGLE'] END::text[],
        NOT s.is_last_sa,
        CASE WHEN s.is_last_sa
             THEN 'Ultimo SUPER_ADMIN attivo: il cambio scope e'' bloccato per evitare il lockout del sistema'
             ELSE NULL
        END
      FROM state s;
$function$

COMMENT ON FUNCTION script.fn_get_user_emittenti_scope(p_auth_user_id integer)
IS 'Lo stato dell''assegnazione di un utente a un emittente, per il drawer dell''operatore; sempre una riga. scope_mode: SINGLE con l''emittente della riga di config.user_emittenti_fiscali; senza riga, GLOBAL al SUPER_ADMIN («Tutti gli emittenti») e SINGLE con emittente_id NULL a chi non lo è (un emittente da scegliere: dal fail-closed non vede niente finché non è assegnato). allowed_scope_modes: GLOBAL e SINGLE al SUPER_ADMIN, solo SINGLE agli altri, perché un operatore non è mai «globale» (lo rifiuta script.fn_applica_user_emittenti_scope); la domanda è script.fn_is_super_admin_account sull''utente interrogato. can_change_scope è falso per l''ultimo SUPER_ADMIN attivo (script.fn_check_ultimo_super_admin_attivo), con il motivo in change_scope_reason. emittente_descrizione è la ragione sociale del soggetto. LANGUAGE sql, STABLE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
