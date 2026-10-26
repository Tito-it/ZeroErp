{% include-markdown "it/dbzero/script/manual/fn_check_operatore_invitabile.md" %}
# ⚙️ Funzione `fn_check_operatore_invitabile`

```sql
CREATE FUNCTION fn_check_operatore_invitabile(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_operatore_invitabile(p_auth_user_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Tipi espliciti: colonne di django.auth_user (niente %TYPE su Django).
    v_email            VARCHAR(254);
    -- Ancorata: e' il bool_or della colonna attivo delle vesti.
    v_veste_attiva     anagrafiche.identita_digitali.attivo%TYPE;
    -- Senza colonna di cui siano il riflesso: un flag «trovato», un
    -- conteggio, un predicato calcolato sulla finestra.
    v_trovato          boolean;
    v_n_vesti          integer;
    v_in_finestra      boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire se un operatore puo' ricevere l'invito che ACCENDE
    --   la sua veste OPERATORE (regola unica dell'invito,
    --   rev 20260925-43: la veste nasce spenta, la accende
    --   l'attivazione; il reinvito riapre una veste spenta).
    --
    -- Condizioni (in ordine: il primo motivo vince):
    --   1. auth_user valido ed esistente     UTENTE_NON_TROVATO
    --   2. almeno una veste OPERATORE        SENZA_VESTE_OPERATORE
    --   3. nessuna veste OPERATORE gia'
    --      attiva (D-8)                      VESTE_GIA_ATTIVA
    --   3-bis. UNA sola veste OPERATORE: con piu' vesti spente
    --      non si sa quale riaccendere
    --      (rev 20260925-53, R-9)            PIU_VESTI_SPENTE
    --   4. la veste nella sua finestra       VESTE_FUORI_FINESTRA
    --   5. auth_user ha un indirizzo email   SENZA_EMAIL
    --   ⛔ NON contano piu': last_login (D-8) e is_active
    --      (derivato dalle vesti: false per costruzione).
    --
    -- Ritorna:
    --   JSONB: {invitabile: bool, reason: text, reason_key: text,
    --           email: text}
    --   reason/reason_key NULL se invitabile.
    --   ⛔ Rev 20260927-01 (§16): il motivo e' un CODICE con la
    --   sua chiave i18n; la frase `motivo` e' ritirata — il
    --   testo vive nei locales, non nel payload.
    -- =========================================================

    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'reason', 'UTENTE_NON_TROVATO',
            'reason_key', 'amministrazione.operatori.invito_reason.utente_non_trovato',
            'email', NULL
        );
    END IF;

    -- Credenziale + le sue vesti OPERATORE, AGGREGATE: il modello
    -- ammette piu' vesti spente sulla stessa credenziale, e
    -- prenderne una a caso deciderebbe per la prima che capita.
    SELECT true,
           au.email,
           count(idg.id),
           bool_or(idg.attivo),
           bool_or(    (idg.valido_dal IS NULL OR idg.valido_dal <= (SELECT script.fn_data_operativa()))
                   AND (idg.valido_al  IS NULL OR idg.valido_al  >= (SELECT script.fn_data_operativa())))
      INTO v_trovato, v_email, v_n_vesti, v_veste_attiva, v_in_finestra
      FROM django.auth_user au
      LEFT JOIN anagrafiche.identita_digitali idg
        ON idg.auth_user_id = au.id
       AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
     WHERE au.id = p_auth_user_id
     GROUP BY au.email;

    IF v_trovato IS NULL THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'reason', 'UTENTE_NON_TROVATO',
            'reason_key', 'amministrazione.operatori.invito_reason.utente_non_trovato',
            'email', NULL
        );
    END IF;

    IF v_n_vesti = 0 THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'reason', 'SENZA_VESTE_OPERATORE',
            'reason_key', 'amministrazione.operatori.invito_reason.senza_veste_operatore',
            'email', v_email
        );
    END IF;

    -- ⛔ D-8: veste gia' attiva → rifiuto. L'accesso c'e' gia': per
    --   una password dimenticata c'e' il reset, non l'invito.
    IF v_veste_attiva THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'reason', 'VESTE_GIA_ATTIVA',
            'reason_key', 'amministrazione.operatori.invito_reason.veste_gia_attiva',
            'email', v_email
        );
    END IF;

    -- ⛔ Rev 20260925-53 (R-9): piu' vesti spente e nessuna attiva.
    --   L'invito riaccende UNA veste, e qui non c'e' una regola che dica
    --   quale: il verbo del backend lo rifiuta gia'. La capability deve
    --   dire lo stesso, o il pulsante si offre e il verbo fallisce.
    IF v_n_vesti > 1 THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'reason', 'PIU_VESTI_SPENTE',
            'reason_key', 'amministrazione.operatori.invito_reason.piu_vesti_spente',
            'email', v_email
        );
    END IF;

    IF NOT v_in_finestra THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'reason', 'VESTE_FUORI_FINESTRA',
            'reason_key', 'amministrazione.operatori.invito_reason.veste_fuori_finestra',
            'email', v_email
        );
    END IF;

    IF v_email IS NULL OR trim(v_email) = '' THEN
        RETURN jsonb_build_object(
            'invitabile', false,
            'reason', 'SENZA_EMAIL',
            'reason_key', 'amministrazione.operatori.invito_reason.senza_email',
            'email', NULL
        );
    END IF;

    RETURN jsonb_build_object(
        'invitabile', true,
        'reason', NULL,
        'reason_key', NULL,
        'email', v_email
    );
END;
$function$

COMMENT ON FUNCTION script.fn_check_operatore_invitabile(p_auth_user_id integer)
IS 'Dice se un operatore puo'' ricevere l''invito che ACCENDE la sua veste OPERATORE. ⭐ Rev 20260925-43 (brief-db-blocco-login-per-credenziale §12; R-1 del piano BE/FE, D-8): regola unica dell''invito — la veste nasce spenta (fn_crea_operatore_v2) e la accende l''attivazione; il reinvito riapre una veste spenta (D-3). Invitabile se: credenziale esistente, almeno una veste OPERATORE, NESSUNA veste OPERATORE gia'' attiva (veste attiva -> rifiuto), UNA SOLA veste OPERATORE (rev 20260925-53, R-9: con piu'' vesti spente non si sa quale riaccendere, e l''invito del backend lo rifiuta), veste nella sua finestra, email presente. Non contano piu'' last_login (D-8) ne'' is_active (derivato dalle vesti, false per costruzione con la sola veste spenta). Ritorna jsonb {invitabile, reason, reason_key, email}. ⭐ Rev 20260927-01 (§16): il motivo e'' un codice macchina con la sua chiave i18n, nell''ordine delle condizioni (il primo vince); la frase `motivo` e'' ritirata. Codici -> chiavi: UTENTE_NON_TROVATO -> amministrazione.operatori.invito_reason.utente_non_trovato; SENZA_VESTE_OPERATORE -> amministrazione.operatori.invito_reason.senza_veste_operatore; VESTE_GIA_ATTIVA -> amministrazione.operatori.invito_reason.veste_gia_attiva; PIU_VESTI_SPENTE -> amministrazione.operatori.invito_reason.piu_vesti_spente; VESTE_FUORI_FINESTRA -> amministrazione.operatori.invito_reason.veste_fuori_finestra; SENZA_EMAIL -> amministrazione.operatori.invito_reason.senza_email. reason e reason_key li inoltra fn_get_operatore_detail come invite_reason e invite_reason_key.';
```

</div>

---
{% include-markdown "signature-core.md" %}
