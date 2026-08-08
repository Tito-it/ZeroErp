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
    v_campo  text;
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
    --
    -- Cambiamento 08-08-2026: esce anche il NOME DEL CAMPO, sul
    -- canale COLUMN, letto da p_context->>'campo'. Vedi blocco 4-bis.
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

    -- 4-bis) Il NOME DEL CAMPO da correggere, se chi solleva
    --    l'ha messo nel contesto sotto la chiave 'campo'.
    --
    --    ⚠️ Passa dal context e NON da un parametro nuovo perche'
    --    la firma finisce con VARIADIC: un parametro dopo di
    --    essa PostgreSQL lo rifiuta, e uno PRIMA — anche con
    --    DEFAULT — si mangerebbe in silenzio il primo valore di
    --    973 punti di chiamata. Verificato eseguendolo.
    --
    --    ⚠️ Si legge SOLO 'campo', mai 'valore': nei context c'e'
    --    spesso anche quello che l'operatore ha scritto, e non ha
    --    motivo di tornare indietro.
    --
    --    ⚠️ E deve SEMBRARE un identificatore. I context li scrive
    --    chi solleva, ma una chiave costruita a runtime
    --    rimanderebbe al client testo altrui. E' la simmetrica
    --    della regex che il backend applica sul suo lato: le due
    --    meta' dello stesso canale vanno guardate uguale.
    --
    --    ⭐ 08-08-2026, RIPIEGO SU 'parametro'. Misurato: la chiave
    --    'campo' e' usata in 8 punti, ma **'parametro' in 225, su
    --    111 funzioni** — e porta il nome del parametro plpgsql
    --    (`jsonb_build_object('parametro','p_cognome')`). E' la
    --    convenzione vera di questa casa, gia' scritta ovunque e
    --    mai trasmessa. Derivarla qui copre **217 dei 380 punti**
    --    che il frontend potrebbe evidenziare, **senza toccarne
    --    nessuno**.
    --
    --    Il prefisso `p_` lo togliamo QUI e non lato backend: e'
    --    una convenzione di denominazione del plpgsql, non un dato
    --    del client. Farla arrivare al frontend vorrebbe dire
    --    mettere una regola del database dentro alla pagina.
    --
    --    ⚠️ Precedenza a 'campo': e' l'override esplicito per
    --    quando il campo del form NON si chiama come il parametro.
    --    Se vincesse 'parametro' l'override non servirebbe a niente.
    --
    --    ⚠️ Molti parametri sono `*_id` interni e non campi di un
    --    form: li' il client non trova l'input e non evidenzia
    --    nulla — **inerte, non sbagliato**. E' il prezzo accettato
    --    per non fare 217 giudizi a mano.
    v_campo := nullif(btrim(coalesce(p_context ->> 'campo', '')), '');
    IF v_campo IS NULL THEN
        v_campo := nullif(btrim(coalesce(p_context ->> 'parametro', '')), '');
        v_campo := nullif(regexp_replace(coalesce(v_campo, ''), '^p_', ''), '');
    END IF;
    IF v_campo IS NOT NULL AND v_campo !~ '^[a-z_][a-z0-9_]{0,63}$' THEN
        v_campo := NULL;
    END IF;

    -- 5) Sollevamento eccezione con DETAIL/HINT localizzati.
    --
    --    CONSTRAINT porta il CODICE di dominio: e' l'unico campo
    --    strutturato che il backend puo' leggere senza fare
    --    parsing del testo. Il codice NON compare nel messaggio,
    --    ed e' una scelta: il messaggio e' per l'utente.
    --
    --    COLUMN porta il NOME DEL CAMPO da correggere. Contratto
    --    gemello: «P0001 + COLUMN valorizzato = il campo che
    --    l'operatore deve correggere».
    --
    --    ⚠️ CONTRATTO — «P0001 + CONSTRAINT valorizzato = errore
    --    di dominio». ERRCODE e' gia' il default: e' esplicito
    --    per dichiararlo. Il backend NON puo' fidarsi del campo
    --    fuori da P0001, perche' su una violazione di vincolo
    --    vera (classe 23xxx) `constraint_name` contiene il nome
    --    del vincolo DB (`uq_...`, `fk_...`).
    --
    --    ⚠️ Questo e' l'UNICO posto autorizzato a scrivere
    --    CONSTRAINT e COLUMN in un RAISE. Presidiato in CI da
    --    scripts/sql/guardrail_codice_errore_strutturato.sql,
    --    controlli (A) e (F): se un altro RAISE usa gli stessi
    --    canali per altro, il backend si fiderebbe di un campo
    --    scritto da qualcun altro — e nel caso di COLUMN
    --    evidenzierebbe il campo SBAGLIATO, che e' peggio che
    --    non evidenziarne nessuno.
    --
    --    ⚠️ Se p_error_code (o il campo) e' NULL il canale esce
    --    come STRINGA VUOTA, non NULL (verificato). Succede nelle
    --    guard che passano `v_motivi -> 0 ->> 'codice'`: lato
    --    backend la lettura deve fare `... or None` per ricadere
    --    sulla regex invece di propagare un valore vuoto.
    RAISE EXCEPTION '%', v_msg
        USING ERRCODE    = 'P0001',
              DETAIL     = coalesce(v_detail, ''),
              HINT       = coalesce(v_hint, ''),
              CONSTRAINT = p_error_code,
              COLUMN     = coalesce(v_campo, '');
END;
$function$

COMMENT ON FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
IS 'Logga e poi solleva exception con messaggio custom. Post 23-04-2026: causa/soluzione con fallback lingua=''it'' se la lingua richiesta (myapp.user_language) non ha riga per il codice. Messaggio delegato a fn_get_messaggio (gia'' context-aware). Post 05-08-2026: il CODICE di dominio esce nel campo strutturato CONSTRAINT dell''eccezione — contratto «P0001 + CONSTRAINT valorizzato = errore di dominio». Post 08-08-2026: esce anche il NOME DEL CAMPO da correggere, nel canale COLUMN, letto da p_context->>''campo'' e, in ripiego, da p_context->>''parametro'' col prefisso p_ tolto (convenzione gia'' in uso in 225 punti su 111 funzioni: copre 217 dei 380 punti evidenziabili senza toccarne nessuno) — contratto gemello «P0001 + COLUMN valorizzato = il campo che l''operatore deve correggere». Passa dal context e NON da un parametro nuovo perche'' la firma finisce con VARIADIC: un parametro dopo di essa e'' rifiutato, uno prima si mangerebbe in silenzio il primo valore di 973 chiamate. Si legge solo ''campo'' e mai ''valore'', e solo se sembra un identificatore. Unica sede autorizzata a scrivere CONSTRAINT e COLUMN (presidio: scripts/sql/guardrail_codice_errore_strutturato.sql, controlli A ed F). Il codice NON compare nel messaggio: quello e'' per l''utente.';
```

---
{% include-markdown "signature-core.md" %}
