{% include-markdown "it/dbzero/script/manual/fn_get_operatore_detail.md" %}
# ⚙️ Funzione `fn_get_operatore_detail`

```sql
CREATE FUNCTION fn_get_operatore_detail(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_operatore_detail(p_auth_user_id integer)
 RETURNS TABLE(auth_user_id integer, username character varying, email character varying, first_name character varying, last_name character varying, soggetto_cognome text, soggetto_nome text, soggetto_id uuid, ragione_sociale_completa text, codice_fiscale text, is_super_admin boolean, ruolo_applicativo text, is_active boolean, unita_organizzativa_id integer, unita_organizzativa_nome text, risorsa_umana_id bigint, attivo boolean, valido_dal text, valido_al text, override_aree_count bigint, override_azioni_count bigint, emittenti_count bigint, emittenti_descrizione text, last_login timestamp with time zone, invito_inviato_at timestamp with time zone, deve_cambiare_password boolean, can_invite boolean, invite_reason text, can_disable boolean, disable_reason text, can_demote_super_admin boolean, demote_reason text, veste_attiva boolean, invite_reason_key text, disable_reason_key text, demote_reason_key text, can_set_valido_al boolean, valido_al_reason text, valido_al_reason_key text)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Update Chunk A Fase 7 (2026-04-29):
    --   Rimossa chiamata interna a script.fn_get_ruolo_sistema.
    --   Il campo ruolo_sistema (output text, contratto BE
    --   invariato) viene calcolato inline con CASE WHEN su
    --   fn_has_identita_attiva + fn_is_super_admin - stessa
    --   logica del wrapper legacy ma senza dispatch
    --   intermedio (un livello di chiamata in meno).
    --
    --   Drop output column rinviato a Chunk B post BE migrato.
    --
    -- Fase 1 cantiere emittente (2026-08-02):
    --   emittenti_descrizione aggrega la SOLA
    --   ragione_sociale_completa del soggetto. Il COALESCE su
    --   ef.descrizione e' caduto sia nel valore sia nell'ORDER BY
    --   dell'aggregazione: lasciarlo nell'ORDER BY avrebbe
    --   ordinato l'elenco per un campo non piu' mostrato.
    --
    -- Rev 20260925-54 (R-9 del piano BE/FE):
    --   UNA veste OPERATORE, non un JOIN: il modello ne ammette piu'
    --   d'una spenta (l'unique vale solo WHERE attivo), e il JOIN
    --   nudo restituiva una riga per veste. Si mostra quella attiva
    --   (al piu' una, per l'unique), altrimenti la spenta piu'
    --   recente. Con piu' vesti spente l'invito non e' offerto
    --   (fn_check_operatore_invitabile, rev -53).
    --   veste_attiva: lo stato di QUELLA veste (NULL se non ce n'e'
    --   nessuna). Ne' attivo (risorsa umana) ne' is_active
    --   (credenziale, derivato da tutte le vesti) lo dicevano.
    --   ⭐ Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): la
    --   regola «l'accesa, altrimenti la spenta piu' recente» non si
    --   scrive piu' qui: e' script.fn_veste_di_riferimento, che legge
    --   anche fn_get_user_profile (regola del 2). Dopo R-DB-1 un
    --   operatore spento dall'amministratore resta OPERATORE e compare
    --   qui per intero (prima, DISABILITATO, usciva con i campi vuoti).
    --
    -- Rev 20260927-01/-02 (brief §16):
    --   I motivi sono CODICI con la loro chiave i18n, non frasi.
    --   invite_reason/_key li inoltra dalla check (sede unica);
    --   disable e demote: ULTIMO_SUPER_ADMIN, una chiave per verbo.
    --
    -- Rev 20261007-27 (brief-db-veste-utilizzabile §10):
    --   la data di fine del RAPPORTO (risorse_umane.valido_al, il campo
    --   «Valido al» del drawer) ha la sua terna. Stessa condizione di
    --   can_disable: dal -17 fn_check_ultimo_super_admin_attivo chiede
    --   l'ultimo SUPER_ADMIN SENZA SCADENZA, e il guard -20 ferma la data
    --   di fine sul rapporto con la stessa regola. Chiave propria: la
    --   frase dice QUALE gesto e' spento. Chi ha gia' una data di fine
    --   non e' «senza scadenza»: risponde true, anche per toglierla.
    -- =========================================================
    RETURN QUERY
    WITH ctx AS (
        SELECT
            script.fn_check_operatore_invitabile(p_auth_user_id) AS inv_jsonb,
            script.fn_is_super_admin(p_auth_user_id) AS is_sa,
            script.fn_check_ultimo_super_admin_attivo(p_auth_user_id) AS is_last_sa
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
        -- rev 2026-09-25 (D-7): il flag e' della CREDENZIALE.
        script.fn_get_deve_cambiare_password(au.id),
        (ctx.inv_jsonb ->> 'invitabile')::boolean              AS can_invite,
        ctx.inv_jsonb ->> 'reason'                             AS invite_reason,
        NOT ctx.is_last_sa                                     AS can_disable,
        CASE WHEN ctx.is_last_sa
             THEN 'ULTIMO_SUPER_ADMIN'
             ELSE NULL
        END                                                    AS disable_reason,
        CASE WHEN ctx.is_sa
             THEN NOT ctx.is_last_sa
             ELSE NULL
        END                                                    AS can_demote_super_admin,
        CASE
             WHEN NOT ctx.is_sa  THEN NULL
             WHEN ctx.is_last_sa THEN 'ULTIMO_SUPER_ADMIN'
             ELSE NULL
        END                                                    AS demote_reason,
        id.attivo                                              AS veste_attiva,
        ctx.inv_jsonb ->> 'reason_key'                         AS invite_reason_key,
        CASE WHEN ctx.is_last_sa
             THEN 'amministrazione.operatori.disabilita_reason.ultimo_super_admin'
             ELSE NULL
        END                                                    AS disable_reason_key,
        CASE
             WHEN NOT ctx.is_sa  THEN NULL
             WHEN ctx.is_last_sa THEN 'amministrazione.operatori.rimuovi_super_admin_reason.ultimo_super_admin'
             ELSE NULL
        END                                                    AS demote_reason_key,
        NOT ctx.is_last_sa                                     AS can_set_valido_al,
        CASE WHEN ctx.is_last_sa
             THEN 'ULTIMO_SUPER_ADMIN'
             ELSE NULL
        END                                                    AS valido_al_reason,
        CASE WHEN ctx.is_last_sa
             THEN 'amministrazione.operatori.valido_al_reason.ultimo_super_admin'
             ELSE NULL
        END                                                    AS valido_al_reason_key
      FROM django.auth_user au
      LEFT JOIN anagrafiche.identita_digitali id
        ON id.id = script.fn_veste_di_riferimento(
                       au.id, 'OPERATORE'::config.ruolo_applicativo)
      LEFT JOIN anagrafiche.soggetti_ruoli sr
        ON sr.id = id.soggetto_ruolo_id
      LEFT JOIN anagrafiche.risorse_umane ru
        ON ru.soggetto_ruolo_id = sr.id
      LEFT JOIN anagrafiche.soggetti s
        ON s.id = sr.soggetto_id
      LEFT JOIN config.unita_organizzative uo
        ON uo.id = ru.unita_organizzativa_id
      LEFT JOIN LATERAL (
          SELECT
              COUNT(*) AS cnt,
              string_agg(
                  s_ef.ragione_sociale_completa,
                  ', '
                  ORDER BY s_ef.ragione_sociale_completa
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
IS 'Riga di dettaglio operatore + capability per il drawer admin (Fase 1 P1 2026-04-29; Fase 7 cleanup 2026-04-29: rimossa call interna fn_get_ruolo_sistema E rimossa colonna ruolo_sistema dall''output - BE post-Fase 7 LANDED non la legge piu''). Migra in DB la query inline da Python e calcola capability via funzioni esistenti come single source of truth: fn_check_operatore_invitabile, fn_is_super_admin, fn_check_ultimo_super_admin_attivo. emittenti_descrizione aggrega la ragione_sociale_completa dei soggetti emittenti (Fase 1 cantiere emittente 2026-08-02: caduto il fallback su emittenti_fiscali.descrizione, valore e ORDER BY). LANGUAGE plpgsql STABLE. La colonna deve_cambiare_password e'' della CREDENZIALE (D-7, rev 2026-09-25): si legge da script.fn_get_deve_cambiare_password. Rev 20260925-54 (R-9): UNA riga anche con piu'' vesti OPERATORE — quella attiva, altrimenti la spenta piu'' recente (data_insert, poi id) — e la colonna veste_attiva, lo stato di quella veste (NULL senza veste OPERATORE). ⭐ Rev 20260927-02 (brief-db-blocco-login-per-credenziale §16): i motivi sono CODICI con la chiave i18n, non frasi. invite_reason/invite_reason_key = reason/reason_key di fn_check_operatore_invitabile (codici e chiavi nel suo COMMENT). disable_reason = ULTIMO_SUPER_ADMIN, disable_reason_key = amministrazione.operatori.disabilita_reason.ultimo_super_admin. demote_reason = ULTIMO_SUPER_ADMIN, demote_reason_key = amministrazione.operatori.rimuovi_super_admin_reason.ultimo_super_admin. Tutti NULL quando l''azione e'' ammessa (e demote anche quando non si applica). Rev 2026-10-02 (brief-db-be-fe-area-accessi R-DB-1): la veste mostrata e'' script.fn_veste_di_riferimento(credenziale, OPERATORE), la regola che prima stava scritta qui; un operatore spento resta OPERATORE e compare per intero. Rev 20261007-27 (brief-db-veste-utilizzabile §10): can_set_valido_al / valido_al_reason / valido_al_reason_key, la data di fine del RAPPORTO (risorse_umane.valido_al, il campo Valido al del drawer). Stessa condizione di can_disable (fn_check_ultimo_super_admin_attivo: l''ultimo SUPER_ADMIN senza scadenza, la regola del guard sul rapporto): valido_al_reason = ULTIMO_SUPER_ADMIN, valido_al_reason_key = amministrazione.operatori.valido_al_reason.ultimo_super_admin; NULL quando ammessa. Un amministratore che ha gia'' una data di fine risponde true, anche per toglierla.';
```

</div>

---
{% include-markdown "signature-core.md" %}
