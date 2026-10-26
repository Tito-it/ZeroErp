# ⚙️ Funzione `fn_riattiva_utente_tecnico`

```sql
CREATE FUNCTION fn_riattiva_utente_tecnico(p_processo_codice text, p_emittente_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_riattiva_utente_tecnico(p_processo_codice text, p_emittente_codice character varying)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_username     text;
    v_auth_user_id integer;   -- ⚠️ niente %TYPE su django.*
    v_processo     dbops.processi%ROWTYPE;
    v_emittente    anagrafiche.emittenti_fiscali%ROWTYPE;
    v_emit_perim   anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Riaccendere un utente tecnico che ESISTE ed e' spento.
    --   ⛔ Non crea niente: se manca un pezzo, la coppia non e'
    --   «da riattivare», e' rotta — e va guardata da una persona.
    --
    -- ⭐ Perche' esiste: lo username degli utenti tecnici e'
    --   deterministico (processo@emittente) e il suo UNIQUE non
    --   ha condizioni. Disattivare il legame — la via che il
    --   brief documenta per sostituire l'utente di un processo —
    --   non libera lo username, quindi la fabbrica non puo'
    --   rifarlo. Senza questo verbo quella strada e' chiusa.
    -- =========================================================

    -- Guard 1: il processo deve esistere. «Non c'e'» e «non e'
    -- eleggibile» sono due cose diverse (DB-8).
    SELECT * INTO v_processo
      FROM dbops.processi
     WHERE codice = p_processo_codice;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_riattiva_utente_tecnico',
            'E_PROCESSO_NON_TROVATO',
            jsonb_build_object('processo_codice', p_processo_codice),
            NULL::uuid, p_processo_codice);
    END IF;

    SELECT * INTO v_emittente
      FROM anagrafiche.emittenti_fiscali
     WHERE codice = p_emittente_codice;

    IF NOT FOUND OR NOT v_emittente.attivo THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_riattiva_utente_tecnico',
            'E_UTENTE_TECNICO_EMITTENTE_NON_VALIDO',
            jsonb_build_object('emittente_codice', p_emittente_codice),
            NULL::uuid, p_emittente_codice);
    END IF;

    -- Guard 2: c'e' qualcosa da riattivare?
    v_username := p_processo_codice || '@' || p_emittente_codice;

    SELECT au.id INTO v_auth_user_id
      FROM django.auth_user au
     WHERE au.username = v_username;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_riattiva_utente_tecnico',
            'E_UTENTE_TECNICO_NON_TROVATO',
            jsonb_build_object('processo_codice',  p_processo_codice,
                               'emittente_codice', p_emittente_codice,
                               'username',         v_username),
            NULL::uuid, p_processo_codice, p_emittente_codice);
    END IF;

    -- ⛔ Guard 3: IL PERIMETRO NON SI SPOSTA.
    --   config.user_emittenti_fiscali e' 1-a-1 e l'emittente e'
    --   immutabile. Se quell'utente aveva un'altra azienda,
    --   riaccenderlo lo farebbe lavorare per l'azienda sbagliata:
    --   il guasto silenzioso che questo cantiere esiste per
    --   impedire. Meglio fermarsi e farlo guardare.
    SELECT uef.emittente_fiscale_id INTO v_emit_perim
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = v_auth_user_id;

    IF v_emit_perim IS DISTINCT FROM v_emittente.id THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_riattiva_utente_tecnico',
            'E_UTENTE_TECNICO_NON_TROVATO',
            jsonb_build_object(
                'detail', 'utente presente ma con perimetro diverso o assente',
                'username',              v_username,
                'emittente_atteso',      v_emittente.id,
                'emittente_del_perimetro', v_emit_perim),
            NULL::uuid, p_processo_codice, p_emittente_codice);
    END IF;

    -- ⭐ I TRE LIVELLI, e si riaccendono INSIEME: spegnerne uno
    --   solo basta a fermare l'utente, quindi riaccenderne uno
    --   solo lo lascerebbe inerte in un modo che non si vede.
    UPDATE django.auth_user
       SET is_active = true
     WHERE id = v_auth_user_id
       AND is_active IS DISTINCT FROM true;

    UPDATE anagrafiche.identita_digitali
       SET attivo = true
     WHERE auth_user_id = v_auth_user_id
       AND tecnica
       AND attivo IS DISTINCT FROM true;

    UPDATE dbops.processi_identita
       SET attivo = true
     WHERE auth_user_id = v_auth_user_id
       AND processo_id = v_processo.id
       AND attivo IS DISTINCT FROM true;

    RETURN v_auth_user_id;
END
$function$

COMMENT ON FUNCTION script.fn_riattiva_utente_tecnico(p_processo_codice text, p_emittente_codice character varying)
IS 'Riaccende un utente tecnico che ESISTE ed e'' spento, per la coppia (processo, emittente): il legame in dbops.processi_identita, l''identita'' in anagrafiche.identita_digitali e l''utente in django.auth_user. Ritorna l''auth_user_id. ⭐ Esiste perche'' lo username degli utenti tecnici e'' deterministico (processo@emittente) e il suo UNIQUE non ha condizioni: disattivare il legame non libera lo username, quindi la fabbrica non puo'' rifare l''utente — e senza questo verbo la strada di sostituzione documentata resta chiusa. ⛔ NON ricostruisce niente: non crea soggetti, non tocca il perimetro, non assegna profili. Se manca un pezzo la coppia non e'' «da riattivare», e'' rotta. ⛔ E il perimetro NON si sposta: config.user_emittenti_fiscali e'' 1-a-1 con emittente immutabile, quindi se l''utente aveva un''altra azienda la funzione si ferma invece di riaccenderlo — riaccenderlo lo farebbe lavorare per l''azienda sbagliata. Compagna di script.fn_crea_utente_tecnico: quella CREA cio'' che non c''e'', questa RIACCENDE cio'' che c''e''. Brief: brief-db-processi-automatici-residui-be, DB-6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
