{% include-markdown "it/dbzero/script/manual/fn_pgtap_set_contesto_operatore.md" %}
# ⚙️ Funzione `fn_pgtap_set_contesto_operatore`

```sql
CREATE FUNCTION fn_pgtap_set_contesto_operatore(p_auth_user_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_pgtap_set_contesto_operatore(p_auth_user_id integer DEFAULT NULL::integer)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una sessione pgTAP lo stesso contesto che il
--   middleware multi-face auth da' a una richiesta applicativa,
--   cosi' i test attraversano la RLS invece di saltarla.
--   Brief: brief-db-pgtap-runner-rls-baseline §8.
-- Ritorna: l'auth_user_id usato, cosi' il test puo' stamparlo in
--   diagnostica quando qualcosa non torna.
-- Uso, in testa al file di test:
--   SELECT script.fn_pgtap_set_contesto_operatore();
-- Rev 2026-09-20: senza argomento, se il database non ha nessun
--   operatore (CI, installazione nuova) il mondo si COSTRUISCE
--   invece di lasciare il contesto vuoto.
DECLARE
    v_user_id integer;
BEGIN
    IF p_auth_user_id IS NOT NULL THEN
        -- Un test che ha bisogno di un operatore PRECISO (perche'
        -- verifica proprio il perimetro di quell'utente) lo passa.
        v_user_id := p_auth_user_id;
    ELSE
        -- ⚠️ SI SCEGLIE UN OPERATORE NORMALE, cioe' con il suo
        -- emittente assegnato — e' la regola di dominio: un
        -- operatore, un emittente; multiemittente e' solo il
        -- super admin.
        --
        -- Provata anche l'alternativa: scegliere un operatore
        -- SENZA assegnazione, che script.fn_check_user_emittente_scope
        -- tratta come «nessuna restrizione». Sembrava la mossa
        -- furba e MISURATA E' PEGGIO — 99 file rossi contro 88,
        -- 55 peggioramenti contro 51. Ed e' anche meno fedele:
        -- un operatore senza emittente non e' un operatore
        -- permissivo, e' una configurazione incompleta.
        --
        -- Si escludono i super admin: per loro la funzione esce
        -- subito con true e il percorso operatore non viene
        -- attraversato affatto, cioe' si tornerebbe a non provare
        -- la RLS come fa oggi l'owner.
        SELECT uef.auth_user_id
          INTO v_user_id
          FROM config.user_emittenti_fiscali uef
         WHERE script.fn_has_identita_attiva(
                   uef.auth_user_id, 'OPERATORE'::config.ruolo_applicativo)
           AND NOT script.fn_is_super_admin(uef.auth_user_id)
         -- Ordine stabile: un contesto che cambia da solo
         -- produrrebbe test che passano a giorni alterni.
         ORDER BY uef.auth_user_id
         LIMIT 1;

        -- ⭐ Nessun operatore: il database e' ricostruito dai
        --   changelog (CI, installazione nuova) e le anagrafiche
        --   sono a zero. Un contesto vuoto non e' un errore
        --   «parlante»: e' un file che muore venti righe dopo su
        --   «Nessun emittente fiscale attivo». Il mondo si
        --   costruisce, non si cerca — e si costruisce PRIMA di
        --   aprire il contesto (guida pgTAP, §«Il mondo si
        --   costruisce»). L'operatore e' un utente tecnico, cioe'
        --   l'unico percorso di produzione che lega un utente a
        --   un emittente: per RLS e guard e' un operatore.
        --   Sul database di sviluppo questo ramo non si percorre.
        IF v_user_id IS NULL THEN
            SELECT ceo.auth_user_id
              INTO v_user_id
              FROM dbops.fn_pgtap_crea_emittente_operatore() ceo;
        END IF;
    END IF;

    -- Le due GUC che le policy leggono davvero. Verificato sui 175
    -- test di vendite: `app.current_identita_id`, pure citata dalle
    -- policy, non serve a nessuno di essi.
    -- Terzo argomento false = vale per la SESSIONE: i file pgTAP
    -- fanno BEGIN/ROLLBACK e un contesto transazionale sparirebbe
    -- al primo rollback.
    PERFORM set_config('app.ruolo_applicativo', 'OPERATORE', false);
    PERFORM set_config('app.current_user_id', v_user_id::text, false);

    RETURN v_user_id;
END;
$function$

COMMENT ON FUNCTION script.fn_pgtap_set_contesto_operatore(p_auth_user_id integer)
IS 'Imposta nella sessione le GUC che le policy RLS leggono (app.ruolo_applicativo, app.current_user_id), scegliendo da se'' un operatore con almeno un emittente fiscale in whitelist — o quello passato come argomento. Dal 2026-09-20, se nessun operatore esiste (database ricostruito dai changelog: CI, installazione nuova) costruisce azienda+operatore con dbops.fn_pgtap_crea_emittente_operatore() e apre il contesto su quello, invece di lasciare le GUC vuote e far morire il file a valle; con argomento o dove un operatore c''e'' il comportamento e'' invariato. ⛔ VINCOLI DIFFERITI (dichiarato il 2026-09-21): QUANDO COSTRUISCE, esce con i vincoli IMMEDIATE come ogni helper pgTAP — il builder richiude la finestra della propria saga e il modo di una transazione non si puo'' ne'' leggere ne'' ripristinare; con argomento, o dove un operatore esiste, non li tocca. Un file che dopo questa riga costruisce una saga contando sulla finestra differita di DEFAULT e'' verde su dev e rosso sul database da zero (anagrafiche/create-cliente, CI 2026-09-21): chi vuole la finestra la riapre con SET CONSTRAINTS ALL DEFERRED subito dopo. Serve ai test pgTAP per girare come l''applicazione invece che come owner: con FORCE ROW LEVEL SECURITY disattivo l''owner salta la RLS, quindi una suite lanciata da lui non esercita nessuna policy. Ritorna l''auth_user_id usato. Brief: brief-db-pgtap-runner-rls-baseline §8; migliorie-generali-da-test-valutazione D7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
