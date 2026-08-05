{% include-markdown "it/dbzero/script/manual/fn_log_and_raise_error.md" %}
# ⚙️ Funzione `fn_log_and_raise_error`

```sql
CREATE FUNCTION fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_msg    text;
    v_detail text;
    v_hint   text;
    v_lang   text := coalesce(
        current_setting('myapp.user_language', true),
        'it'
    );
BEGIN
    -- =========================================================
    -- Scopo (post 23-04-2026, i18n incrementale):
    --   Logga l'errore nel sistema di logging e solleva
    --   RAISE EXCEPTION con messaggio, DETAIL e HINT
    --   localizzati secondo la lingua di sessione.
    --
    -- Cambiamento 23-04-2026: il recupero di causa/soluzione
    -- ora ricade su lingua='it' se la lingua richiesta non
    -- ha riga per il codice (stesso pattern di
    -- fn_get_messaggio). Il messaggio testuale era gia'
    -- context-aware perche' delegato a fn_get_messaggio.
    --
    -- Cambiamento 05-08-2026: il CODICE di dominio esce in un
    -- campo strutturato dell'eccezione (CONSTRAINT), non piu'
    -- solo dentro al testo dello statement chiamante. Vedi il
    -- blocco 5.
    -- =========================================================

    -- 1) Logging (non loc-sensitive).
    PERFORM script.fn_log_error_only(
        p_area, p_function_name, p_error_code,
        p_context, p_tx_id, VARIADIC p_valori
    );

    -- 2) Template messaggio (gia' gestisce fallback lingua
    -- internamente post 20260423-02-01).
    v_msg := script.fn_get_messaggio(
        p_error_code,
        NULL,
        v_lang
    );

    -- 3) Recupera causa e hint con fallback IT inline.
    -- Single-query: preferisci v_lang; se la riga esiste
    -- solo in 'it' vince quella per LIMIT 1.
    -- Semantica "riga intera vince": se la riga EN esiste
    -- ma ha causa/soluzione NULL, mantiene NULL (non mescola
    -- con IT -- ordering sceglie la riga della lingua
    -- richiesta come blocco atomico).
    SELECT causa, soluzione
      INTO v_detail, v_hint
      FROM config.messaggi_errore
     WHERE codice = p_error_code
       AND lingua IN (v_lang, 'it')
     ORDER BY (lingua = v_lang) DESC
     LIMIT 1;

    -- 4) Format placeholder con VARIADIC values, se presenti.
    IF array_length(p_valori, 1) IS NOT NULL THEN
        v_msg := format(v_msg, VARIADIC p_valori);
    END IF;

    -- 5) Sollevamento eccezione con DETAIL/HINT localizzati.
    --
    --    CONSTRAINT porta il CODICE di dominio: e' l'unico campo
    --    strutturato che il backend puo' leggere senza fare
    --    parsing del testo. Il codice NON compare nel messaggio,
    --    ed e' una scelta: il messaggio e' per l'utente.
    --
    --    ⚠️ CONTRATTO — «P0001 + CONSTRAINT valorizzato = errore
    --    di dominio». ERRCODE e' gia' il default: e' esplicito
    --    per dichiararlo. Il backend NON puo' fidarsi del campo
    --    fuori da P0001, perche' su una violazione di vincolo
    --    vera (classe 23xxx) `constraint_name` contiene il nome
    --    del vincolo DB (`uq_...`, `fk_...`).
    --
    --    ⚠️ Questo e' l'UNICO posto autorizzato a scrivere
    --    CONSTRAINT in un RAISE. Presidiato in CI da
    --    scripts/sql/guardrail_codice_errore_strutturato.sql: se
    --    un altro RAISE usa lo stesso canale per altro, il guard
    --    P0001 del backend si fiderebbe di un campo scritto da
    --    qualcun altro.
    --
    --    ⚠️ Se p_error_code e' NULL il campo esce come STRINGA
    --    VUOTA, non NULL (verificato). Succede nelle guard che
    --    passano `v_motivi -> 0 ->> 'codice'`: lato backend la
    --    lettura deve fare `... or None` per ricadere sulla
    --    regex invece di propagare un codice vuoto.
    RAISE EXCEPTION '%', v_msg
        USING ERRCODE    = 'P0001',
              DETAIL     = coalesce(v_detail, ''),
              HINT       = coalesce(v_hint, ''),
              CONSTRAINT = p_error_code;
END;
$function$

COMMENT ON FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
IS 'Logga e poi solleva exception con messaggio custom. Post 23-04-2026: causa/soluzione con fallback lingua=''it'' se la lingua richiesta (myapp.user_language) non ha riga per il codice. Messaggio delegato a fn_get_messaggio (gia'' context-aware). Post 05-08-2026: il CODICE di dominio esce nel campo strutturato CONSTRAINT dell''eccezione — contratto «P0001 + CONSTRAINT valorizzato = errore di dominio», unica sede autorizzata a scrivere quel campo (presidio: scripts/sql/guardrail_codice_errore_strutturato.sql). Il codice NON compare nel messaggio: quello e'' per l''utente.';
```

---
{% include-markdown "signature-core.md" %}
