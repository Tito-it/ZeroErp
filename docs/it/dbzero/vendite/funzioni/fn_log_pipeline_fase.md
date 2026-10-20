{% include-markdown "it/dbzero/vendite/manual/fn_log_pipeline_fase.md" %}
# ⚙️ Funzione `fn_log_pipeline_fase`

```sql
CREATE FUNCTION fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character, p_messaggio text, p_meta jsonb, p_error_code text, p_gruppo_key text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character DEFAULT 'I'::bpchar, p_messaggio text DEFAULT NULL::text, p_meta jsonb DEFAULT '{}'::jsonb, p_error_code text DEFAULT NULL::text, p_gruppo_key text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_lotto      vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_stato_operativo vendite.fatturazione_lotti.stato_operativo%TYPE;
    v_error_code      config.codici_errore.codice%TYPE;
    v_gruppo_key      vendite.fatturazione_lotti_log.gruppo_key%TYPE;
    v_meta            vendite.fatturazione_lotti_log.meta%TYPE;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_pipeline_fase', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id), NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    IF p_status IS NULL OR p_status NOT IN ('I', 'W', 'C') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_pipeline_fase', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_status', 'valore', p_status), NULL::uuid, concat('p_status=', coalesce(p_status::text, 'NULL'), ' (ammessi: I, W, C)'));
    END IF;

    SELECT l.tipo_lotto, l.stato_operativo INTO v_tipo_lotto, v_stato_operativo
      FROM vendite.fatturazione_lotti l WHERE l.id = p_lotto_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_log_pipeline_fase', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id), NULL::uuid, concat('lotto_id ', p_lotto_id));
    END IF;

    -- ⭐ IL CODICE ERRORE ENTRA IN META.
    --    Normalizzato: una stringa di soli spazi e' assenza, non un
    --    codice — e in JSON diventerebbe una chiave presente e vuota,
    --    cioe' peggio che assente (la lista mostrerebbe una cella
    --    bianca dove «non lo so» e «non c'e'» si leggono uguali).
    --    ⚠️ NESSUNA verifica contro config.codici_errore: questa
    --    funzione scrive un LOG, e un log non deve poter fallire per
    --    un refuso nel codice che sta registrando. Fallirebbe dentro
    --    il ramo EXCEPTION di qualcun altro, sostituendo il guasto
    --    vero con il proprio.
    v_error_code := NULLIF(btrim(COALESCE(p_error_code, '')), '');
    v_meta       := COALESCE(p_meta, '{}'::jsonb);

    IF v_error_code IS NOT NULL THEN
        -- Il parametro VINCE su una chiave omonima gia' presente in
        -- p_meta: e' quello dichiarato in firma, ed e' l'unico che
        -- un lettore sa di dover cercare.
        v_meta := v_meta || jsonb_build_object('error_code', v_error_code);
    END IF;

    -- ⭐ IL PROPRIETARIO DELLA SEGNALAZIONE ENTRA IN UNA COLONNA.
    --    NULL = «e' del GIRO», ed e' un valore dichiarato, non
    --    un'assenza di informazione: una segnalazione del giro deve
    --    fermare il giro e non ha nessun documento da togliere.
    --    ⚠️ Una stringa vuota o di soli spazi diventa NULL: la
    --    colonna ha DUE stati, e un terzo che nessun lettore conosce
    --    passerebbe per «nomina un documento» — con la conseguenza
    --    che quella riga bloccherebbe il lotto per sempre senza che
    --    nessuno possa toglierla.
    --    ⛔ Non si solleva (un log non fallisce), ma il caso si
    --    DICHIARA: e' l'unica traccia che qualcuno ha provato a dire
    --    di chi era la segnalazione senza riuscirci.
    v_gruppo_key := NULLIF(btrim(COALESCE(p_gruppo_key, '')), '');

    IF p_gruppo_key IS NOT NULL AND v_gruppo_key IS NULL THEN
        RAISE WARNING
            'fn_log_pipeline_fase: gruppo_key vuota sul lotto %: la segnalazione viene scritta come «del giro», e nessuno potra'' toglierla.',
            p_lotto_id;
    END IF;

    -- ⛔ SU UN DOCUMENTO USCITO DAL GIRO NON SI SCRIVE UNA SEGNALAZIONE.
    --   La regola del dominio e' «un documento fuori dal giro non si marca, non
    --   si conta, non blocca», e non aveva ragione di fermarsi prima di «non si
    --   racconta»: al rilancio il pull di quella commessa fallisce ancora e il
    --   backend riscriveva una critica per OGNI suo documento, compreso quello
    --   uscito. Non bloccava — il conteggio le scarta gia' — ma se ne
    --   accumulava una a ogni giro su un documento che non e' piu' in gioco.
    --
    --   ⭐ SI FERMANO `W` e `C`, NON LE `I`, e la distinzione e' portante:
    --     · `W`/`C` dicono «qualcosa non va su questo documento» — su uno che
    --       e' uscito e' rumore, e qui si smette proprio di scriverlo;
    --     · `I` e' un FATTO del giornale, e l'uscita stessa e' un fatto: la
    --       riga che la racconta (fn_escludi_documento_da_giro) e' una `I`.
    --   ⛔ Fermare tutto avrebbe funzionato solo scrivendo quella riga PRIMA di
    --   passare a ESCLUSO, cioe' appendendo la traccia dell'uscita all'ORDINE
    --   di due istruzioni: il giorno che qualcuno le riordina, la traccia
    --   sparisce in silenzio. Questa regola non ha quel punto fragile.
    --
    --   ⚠️ Chiude il RUBINETTO, non ripulisce il pregresso: le critiche gia'
    --   scritte su documenti usciti restano dove sono. Cancellare righe di
    --   giornale e' un'altra decisione.
    --   ⚠️ `ESCLUSO` letterale: e' il sesto punto del database che lo scrive a
    --   mano. Vale la nota di fn_segna_esito_gruppo_lotto — l'asse gemello ha
    --   un flag, questo no, e farne un catalogo e' un cantiere suo.
    --   Brief: brief-db-il-marcatore-scrive-su-un-documento-uscito.md §4.2
    IF v_gruppo_key IS NOT NULL
       AND p_status IN ('W', 'C')
       AND EXISTS (SELECT 1
                     FROM vendite.fatturazione_lotti_esiti e
                    WHERE e.lotto_id   = p_lotto_id
                      AND e.gruppo_key = v_gruppo_key
                      AND e.stato_esecuzione = 'ESCLUSO') THEN
        RAISE NOTICE
            'fn_log_pipeline_fase: segnalazione % sul documento % del lotto % non scritta: quel documento ha gia'' lasciato il giro.',
            p_status, v_gruppo_key, p_lotto_id;
        RETURN;
    END IF;

    INSERT INTO vendite.fatturazione_lotti_log (
        lotto_id, data_ora, messaggio, status, disabilitato, fase,
        stato_doc_fiscale_id, tipo_lotto, stato_operativo, meta,
        gruppo_key,
        data_insert, user_insert, data_update, user_update
    )
    VALUES (
        -- ⭐ R-1 (24-08-2026): clock_timestamp() e non now(). Con
        --    now() ogni riga scritta dentro la stessa transazione
        --    usciva con lo stesso identico orario, e la storia di un
        --    lotto — che unisce TRE registri i cui contatori di riga
        --    non sono confrontabili fra loro — non era ordinabile.
        --    ⚠️ Gli ultimi quattro `now()` restano: quelli sono i
        --    campi di AUDIT, dove l'orario di transazione e' la
        --    convenzione della casa e non c'entra con l'ordinamento.
        p_lotto_id, clock_timestamp(), COALESCE(p_messaggio, p_fase, 'pipeline'), p_status,
        FALSE, p_fase, p_stato_doc_fiscale_id, v_tipo_lotto, v_stato_operativo,
        v_meta, v_gruppo_key,
        now(), current_user, now(), current_user
    );
END;
$function$

COMMENT ON FUNCTION vendite.fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character, p_messaggio text, p_meta jsonb, p_error_code text, p_gruppo_key text)
IS 'Scrive una riga di log di FASE su vendite.fatturazione_lotti_log, arricchendola col tipo lotto e lo stato operativo letti dalla testata. ⭐ rev 2026-09-08 (brief-db-uscita-documento-dal-giro §6.1, richiesta BE §3.1): accetta p_gruppo_key e lo scrive nella COLONNA omonima. E'' l''unico canale con cui il backend scrive quel registro, quindi senza il parametro la colonna nata col 20260908-02 resta vuota — e il verbo «togli questo documento dal giro» non sblocca niente sulla corsia del pull, perche'' l''unica segnalazione che blocca nasce a NULL, cioe'' «e'' del giro». ⭐ In una COLONNA e non in meta, all''opposto di error_code: la gruppo_key e'' un ASSE DI JOIN — la leggono il conteggio di fn_get_lotto_segnalazioni_summary e il presidio vw_segnalazioni_con_documento_ignoto — e un dato su cui si fa EXISTS non vive in un jsonb. ⚠️ NULL significa «la segnalazione e'' del GIRO» e blocca: e'' un valore dichiarato, non un''assenza. Una stringa vuota o di soli spazi viene normalizzata a NULL e il caso viene DICHIARATO con un WARNING — la colonna ha due stati, e un terzo passerebbe per «nomina un documento» lasciando una riga che blocca il lotto per sempre e che nessuno puo'' togliere. ⛔ NESSUNA verifica che il documento esista, di proposito: un log non deve poter fallire per un riferimento sbagliato in cio'' che registra — fallirebbe dentro il ramo EXCEPTION di qualcun altro. Il presidio e'' vw_segnalazioni_con_documento_ignoto, che guarda e non blocca. Il parametro e'' l''OTTAVO, in coda: le quattro funzioni DB chiamanti e la chiamata posizionale a sei argomenti del backend continuano a funzionare identiche. ⭐ rev 2026-08-21 (cantiere brief-db-liste-drawer-lotto, L1/P-2): accetta p_error_code e lo scrive in meta->>''error_code''. Nasce da una misura: NESSUNA funzione del database cattura CONSTRAINT_NAME, quindi il codice di dominio non veniva conservato da nessuna parte, e i log tenevano solo RETURNED_SQLSTATE, che per un errore di dominio e'' SEMPRE P0001 e non distingue niente. ⛔ NESSUNA validazione contro config.codici_errore, per la stessa ragione: il presidio dei codici non dichiarati vive in dbops.vw_codici_errore_da_dichiarare. ⚠️ E'' comunque un DROP + CREATE — un parametro nuovo crea un overload, e con la vecchia firma viva ogni chiamata a sei o sette argomenti sarebbe ambigua.';
```

</div>

---
{% include-markdown "signature-core.md" %}
