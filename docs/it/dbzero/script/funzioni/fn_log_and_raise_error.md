{% include-markdown "it/dbzero/script/manual/fn_log_and_raise_error.md" %}
# ⚙️ Funzione `fn_log_and_raise_error`

```sql
CREATE FUNCTION fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_msg    config.messaggi_errore.messaggio%TYPE;
    v_detail config.messaggi_errore.causa%TYPE;
    v_hint   config.messaggi_errore.soluzione%TYPE;
    -- ⚠️ `text` esplicito, e non e' una dimenticanza: v_campo NON e' il valore
    --    di una colonna, e' il NOME di una colonna — un identificatore che
    --    esce sul canale COLUMN. Non c'e' niente da ancorare.
    v_campo  text;
    v_lang   config.messaggi_errore.lingua%TYPE := coalesce(
        current_setting('myapp.user_language', true),
        'it'
    );
    -- ── Il BERSAGLIO (23-08-2026). Vedi il punto 4-ter. ──
    -- ⚠️ Tutti e quattro a tipo esplicito, per la stessa ragione di v_campo:
    --    non riflettono nessuna colonna. `v_bers_forma` e' l'esito di
    --    jsonb_typeof, `v_bersaglio` e' la forma compatta che esce nel canale
    --    dell'eccezione (una stringa costruita qui, che in nessuna tabella
    --    esiste), e gli altri due sono CONTEGGI.
    v_bers_forma text;
    v_bersaglio  text;
    v_bers_tot   integer;
    v_bers_ok    integer;
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
    --
    -- ⭐ IL RIPIEGO, 18-08-2026 — e perche' la funzione GEMELLA ce l'aveva
    --    gia'. `format()` con MENO valori dei segnaposto non degrada: alza
    --    `22023`. E lo alzava DA QUI, cioe' PRIMA del RAISE del punto 5:
    --    l'errore di dominio non veniva mai sollevato. Niente `P0001`, niente
    --    codice sul canale `CONSTRAINT`, niente campo sul canale `COLUMN`.
    --    Il guard che aveva chiamato bloccava lo stesso — il dato restava
    --    integro, ed e' il motivo per cui non se n'era accorto nessuno — ma il
    --    backend perdeva il codice su cui decide 409/404/403 e l'operatore
    --    leggeva un errore interno al posto della frase scritta per lui.
    --
    --    ⚠️ L'argomento decisivo non e' teorico: `script.fn_log_error_only`,
    --    che questa funzione chiama al punto 1 CON GLI STESSI ARGOMENTI, quel
    --    ripiego ce l'ha da sempre (`BEGIN ... EXCEPTION WHEN OTHERS THEN
    --    NULL`). Quindi davanti allo stesso disallineamento le due funzioni
    --    gemelle si comportavano in modo opposto: il log sopravviveva, l'errore
    --    no. Non era una scelta, era un'asimmetria.
    --
    --    ⚠️ CHE COSA *NON* FA. Non ripara il messaggio e non nasconde niente:
    --    degrada al caso «segnaposto non sostituito», che e' brutto da leggere
    --    ma conserva il codice. La funzione che serve a RIPORTARE un errore non
    --    puo' essere quella che lo distrugge.
    --
    --    ⚠️ E non diventa silenzioso: si scrive `W_MESSAGGIO_ARITA` nel log.
    --    E' un `W_` e resta un `W_` — si LOGGA, non si solleva mai (controllo
    --    (E) di scripts/sql/guardrail_codice_errore_strutturato.sql).
    --    Il presidio vero resta pero' quello STATICO, che vede il difetto
    --    prima che scatti: test 5 di
    --    db/pgtap/script/test-catalogo-messaggi-errore-completo.sql.
    --    Brief: docs/it/dev/work-in-progress/brief-db-segnaposti-messaggi-errore.md
    IF array_length(p_valori, 1) IS NOT NULL THEN
        BEGIN
            v_msg := format(v_msg, VARIADIC p_valori);
        EXCEPTION WHEN OTHERS THEN
            -- v_msg resta il template: l'assegnazione e' fallita, quindi non
            -- l'ha toccato. Si prosegue al punto 5 e l'eccezione di dominio
            -- parte comunque, col suo codice.
            PERFORM script.fn_log_error_only(
                p_area,
                p_function_name,
                'W_MESSAGGIO_ARITA',
                coalesce(p_context, '{}'::jsonb) || jsonb_build_object(
                    'codice_atteso',  p_error_code,
                    'valori_passati', coalesce(array_length(p_valori, 1), 0),
                    'errore_format',  SQLERRM
                ),
                p_tx_id,
                VARIADIC ARRAY[]::text[]
            );
        END;
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

    -- 4-ter) IL BERSAGLIO: su quale cosa e' successo.
    --
    --    ⭐ IL PRINCIPIO, che e' tutto il cantiere: la FRASE e' per la
    --       persona, il BERSAGLIO e' per l'interfaccia. Chi solleva scrive
    --       l'array UNA volta nel context; di li' escono due proiezioni —
    --       quella ricca resta in dbops.error_log per chi diagnostica, quella
    --       compatta viaggia nel canale per chi deve disegnare un pulsante.
    --       Non sono due verita': e' la stessa, letta da due lettori.
    --
    --    Forma attesa nel context (array SEMPRE, anche con un elemento solo):
    --       'bersaglio', jsonb_build_array(
    --            jsonb_build_object('tipo', 'FATTURA', 'id', v_id::text))
    --    Forma che esce nel canale:  FATTURA:835,FATTURA:820
    --
    --    ⚠️ SI VALIDA LA FORMA, NON IL VOCABOLARIO. Nessuna lettura di
    --       config.tipi_entita: sarebbe una query dentro il percorso
    --       d'errore, cioe' una dipendenza in piu' proprio dove non se ne
    --       vogliono. Che il tipo esista a catalogo lo dice la CI
    --       (dbops.vw_bersagli_non_dichiarati), che e' dove un errore di
    --       programmazione va scoperto.
    --
    --    ⛔ E NON PUO' FAR FALLIRE NIENTE. E' la stessa lezione del 18-08 sul
    --       ripiego della format(): la funzione che serve a RIPORTARE un
    --       errore non puo' essere quella che lo distrugge. Un bersaglio
    --       storto lascia il canale vuoto e scrive W_BERSAGLIO_MALFORMATO nel
    --       log — un W_ che si LOGGA e non si solleva mai.
    --
    --    ⚠️ Il tetto di cinque non e' un difetto e non si segnala: oltre, il
    --       frontend non disegna piu' un gesto ma un elenco, e QUANTI sono lo
    --       dice gia' la frase (i messaggi che ne hanno tanti portano il
    --       conteggio in un %s).
    v_bers_forma := jsonb_typeof(p_context -> 'bersaglio');

    IF v_bers_forma IS NOT NULL THEN
        IF v_bers_forma = 'array' THEN
            BEGIN
                SELECT count(*),
                       count(*) FILTER (WHERE x.valido),
                       string_agg(x.tipo || ':' || x.id, ',' ORDER BY x.ord)
                           FILTER (WHERE x.valido AND x.ord <= 5)
                  INTO v_bers_tot, v_bers_ok, v_bersaglio
                  FROM (SELECT e.value ->> 'tipo' AS tipo,
                               e.value ->> 'id'   AS id,
                               e.ord,
                               (    e.value ->> 'tipo' ~ '^[A-Z][A-Z0-9_]{0,30}$'
                                AND coalesce(e.value ->> 'id', '') ~ '^[0-9a-fA-F-]{1,36}$'
                               ) AS valido
                          FROM jsonb_array_elements(p_context -> 'bersaglio')
                               WITH ORDINALITY AS e(value, ord)) x;
            EXCEPTION WHEN OTHERS THEN
                -- Qualunque cosa sia andata storta leggendo il context, il
                -- bersaglio si perde e l'errore di dominio parte lo stesso.
                v_bersaglio := NULL;
                v_bers_tot  := NULL;
                v_bers_ok   := NULL;
            END;
        END IF;

        -- La chiave c'e' ma non dice niente di utilizzabile: elemento
        -- scartato per forma, oggetto nudo invece dell'array, array vuoto.
        IF v_bersaglio IS NULL OR coalesce(v_bers_ok, 0) < coalesce(v_bers_tot, 1) THEN
            PERFORM script.fn_log_error_only(
                p_area,
                p_function_name,
                'W_BERSAGLIO_MALFORMATO',
                coalesce(p_context, '{}'::jsonb) || jsonb_build_object(
                    'codice_atteso',   p_error_code,
                    'bersaglio_forma', coalesce(v_bers_forma, 'assente'),
                    'bersaglio_letti', coalesce(v_bers_tot, 0),
                    'bersaglio_validi', coalesce(v_bers_ok, 0)
                ),
                p_tx_id,
                VARIADIC ARRAY[]::text[]);
        END IF;
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
    --    DATATYPE porta il BERSAGLIO: su quali entita' l'errore
    --    si riferisce, nella forma TIPO:id[,TIPO:id]. Contratto
    --    gemello degli altri due, e terzo in tre mosse.
    --
    --    ⚠️ Questo e' l'UNICO posto autorizzato a scrivere
    --    CONSTRAINT, COLUMN e DATATYPE in un RAISE. Presidiato in CI da
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
              COLUMN     = coalesce(v_campo, ''),
              DATATYPE   = coalesce(v_bersaglio, '');
END;
$function$

COMMENT ON FUNCTION script.fn_log_and_raise_error(p_area text, p_function_name text, p_error_code text, p_context jsonb, p_tx_id uuid, VARIADIC p_valori text[])
IS 'Logga e poi solleva exception con messaggio custom. Post 23-04-2026: causa/soluzione con fallback lingua=''it'' se la lingua richiesta (myapp.user_language) non ha riga per il codice. Messaggio delegato a fn_get_messaggio (gia'' context-aware). Post 05-08-2026: il CODICE di dominio esce nel campo strutturato CONSTRAINT dell''eccezione — contratto «P0001 + CONSTRAINT valorizzato = errore di dominio». Post 08-08-2026: esce anche il NOME DEL CAMPO da correggere, nel canale COLUMN, letto da p_context->>''campo'' e, in ripiego, da p_context->>''parametro'' col prefisso p_ tolto (convenzione gia'' in uso in 225 punti su 111 funzioni: copre 217 dei 380 punti evidenziabili senza toccarne nessuno) — contratto gemello «P0001 + COLUMN valorizzato = il campo che l''operatore deve correggere». Passa dal context e NON da un parametro nuovo perche'' la firma finisce con VARIADIC: un parametro dopo di essa e'' rifiutato, uno prima si mangerebbe in silenzio il primo valore di 973 chiamate. Si legge solo ''campo'' e mai ''valore'', e solo se sembra un identificatore. Unica sede autorizzata a scrivere CONSTRAINT e COLUMN (presidio: scripts/sql/guardrail_codice_errore_strutturato.sql, controlli A ed F). Il codice NON compare nel messaggio: quello e'' per l''utente. Post 18-08-2026: la format() del punto 4 e'' avvolta in un BEGIN/EXCEPTION. Con meno valori dei segnaposto alzava 22023 DA DENTRO questa funzione, quindi il RAISE di dominio non veniva mai eseguito e il contratto P0001+CONSTRAINT saltava; ora ripiega sul messaggio non composto (il codice si conserva) e scrive W_MESSAGGIO_ARITA nel log. La funzione gemella fn_log_error_only aveva gia'' lo stesso ripiego: l''asimmetria fra le due era il difetto. Il presidio statico e'' il test 5 di db/pgtap/script/test-catalogo-messaggi-errore-completo.sql. Post 23-08-2026: esce anche il BERSAGLIO dell''errore, nel canale DATATYPE, letto da p_context->''bersaglio'' (array di {tipo,id}) e composto nella forma compatta TIPO:id[,TIPO:id] — al massimo cinque, perche'' oltre il frontend non disegna piu'' un gesto ma un elenco. Contratto gemello dei due precedenti: «P0001 + DATATYPE valorizzato = le entita'' a cui l''errore si riferisce». Terzo canale in tre mosse (CONSTRAINT 05-08, COLUMN 08-08, DATATYPE 23-08). Valida solo la FORMA e non legge config.tipi_entita: una query dentro il percorso d''errore sarebbe una dipendenza in piu'' proprio dove non si vuole, e il vocabolario lo presidia la CI (dbops.vw_bersagli_non_dichiarati). Un bersaglio malformato NON distrugge mai l''errore di dominio: canale vuoto e W_BERSAGLIO_MALFORMATO nel log, stesso ripiego del 18-08 sulla format(). Brief: brief-db-bersaglio-errore.md.';
```

</div>

---
{% include-markdown "signature-core.md" %}
