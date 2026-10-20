{% include-markdown "it/dbzero/script/manual/fn_guard_soggetto_pf_pura.md" %}
# ⚙️ Funzione `fn_guard_soggetto_pf_pura`

```sql
CREATE FUNCTION fn_guard_soggetto_pf_pura(p_soggetto_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_guard_soggetto_pf_pura(p_soggetto_id uuid)
 RETURNS uuid
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Variabili locali tipizzate sulle colonne sorgente (policy %TYPE)
    v_partita_iva    anagrafiche.soggetti.partita_iva%TYPE;
    v_codice_fiscale anagrafiche.soggetti.codice_fiscale%TYPE;
BEGIN
    -- ------------------------------------------------------------
    -- Funzione: script.fn_guard_soggetto_pf_pura
    --
    -- Scopo:
    --   Guard fail-fast che verifica che un soggetto sia persona
    --   fisica "pura" (idoneo a essere collegato a un auth_user
    --   nella veste OPERATORE).
    --
    -- Regole di dominio:
    --   1. codice_fiscale deve essere valorizzato (identificazione)
    --   2. partita_iva deve essere NULL (no professionisti/ditte
    --      individuali: appartengono ad altre vesti)
    --
    -- Parametri:
    --   p_soggetto_id -> id del soggetto da verificare
    --
    -- Ritorna:
    --   p_soggetto_id (se valido); altrimenti solleva eccezione
    --   via script.fn_log_and_raise_error.
    -- ------------------------------------------------------------

    -- 1) Validazione parametro: rifiuta NULL (non si puo' guardare
    --    un soggetto inesistente).
    IF p_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_guard_soggetto_pf_pura',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_soggetto_id'),
            NULL::uuid,
            'NULL'
        );
    END IF;

    -- 2) Recupero dati fiscali del soggetto in un unico round-trip.
    --    Uso la variabile built-in FOUND di PL/pgSQL (pattern idiomatico)
    --    per distinguere "soggetto non trovato" da "colonne NULL".
    SELECT s.partita_iva, s.codice_fiscale
      INTO v_partita_iva, v_codice_fiscale
      FROM anagrafiche.soggetti s
     WHERE s.id = p_soggetto_id;

    IF NOT FOUND THEN
        -- Soggetto inesistente: violazione di integrita' (il chiamante
        -- avrebbe gia' dovuto garantire la FK). Fail-fast.
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_guard_soggetto_pf_pura',
            'E_SOGGETTO_NOT_FOUND',
            jsonb_build_object('soggetto_id', p_soggetto_id),
            NULL::uuid,
            p_soggetto_id::text
        );
    END IF;

    -- 3) Guard PF pura: catena IF/ELSIF (fail-fast al primo problema).
    --    Ordine voluto: prima no-PIVA (regola piu' specifica del dominio
    --    aziendale), poi CF obbligatorio (vincolo identificativo).
    IF v_partita_iva IS NOT NULL THEN
        -- Soggetto con P.IVA: professionista o ditta individuale,
        -- non ammissibile come OPERATORE (accede in altra veste,
        -- es. FORNITORE_PORTALE).
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_guard_soggetto_pf_pura',
            'E_AUTH_USER_SOGGETTO_CON_PIVA',
            jsonb_build_object(
                'campo', 'soggetto_id',
                'soggetto_id', p_soggetto_id,
                'nota', 'Solo persone fisiche pure (senza P.IVA) possono essere collegate ad auth_user come OPERATORE'
            ),
            NULL::uuid,
            p_soggetto_id::text
        );
    ELSIF v_codice_fiscale IS NULL THEN
        -- CF obbligatorio: serve per identificare la persona fisica
        -- in modo univoco (obblighi anagrafici / normativi).
        PERFORM script.fn_log_and_raise_error(
            'database',
            'fn_guard_soggetto_pf_pura',
            'E_AUTH_USER_SOGGETTO_SENZA_CF',
            jsonb_build_object(
                'soggetto_id', p_soggetto_id,
                'nota', 'Il soggetto deve avere un codice fiscale per essere identificato come persona fisica'
            ),
            NULL::uuid,
            p_soggetto_id::text
        );
    END IF;

    -- 4) Tutti i guard superati: restituisco l'id (pattern "pass-through"
    --    che consente chain come: SELECT script.fn_guard_soggetto_pf_pura(:id)).
    RETURN p_soggetto_id;
END;
$function$

COMMENT ON FUNCTION script.fn_guard_soggetto_pf_pura(p_soggetto_id uuid)
IS 'Guard fail-fast: verifica che il soggetto sia persona fisica pura (CF valorizzato, P.IVA NULL). Usato dal trigger sul ponte utente identita_digitali (ruolo_applicativo=OPERATORE). Solleva errore via fn_log_and_raise_error.';
```

</div>

---
{% include-markdown "signature-core.md" %}
