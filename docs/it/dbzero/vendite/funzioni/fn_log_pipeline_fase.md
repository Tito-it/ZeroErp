{% include-markdown "it/dbzero/vendite/manual/fn_log_pipeline_fase.md" %}
# ⚙️ Funzione `fn_log_pipeline_fase`

```sql
CREATE FUNCTION fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character, p_messaggio text, p_meta jsonb, p_error_code text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character DEFAULT 'I'::bpchar, p_messaggio text DEFAULT NULL::text, p_meta jsonb DEFAULT '{}'::jsonb, p_error_code text DEFAULT NULL::text)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_tipo_lotto      vendite.fatturazione_lotti.tipo_lotto%TYPE;
    v_stato_operativo vendite.fatturazione_lotti.stato_operativo%TYPE;
    v_error_code      config.codici_errore.codice%TYPE;
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

    INSERT INTO vendite.fatturazione_lotti_log (
        lotto_id, data_ora, messaggio, status, disabilitato, fase,
        stato_doc_fiscale_id, tipo_lotto, stato_operativo, meta,
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
        v_meta, now(), current_user, now(), current_user
    );
END;
$function$

COMMENT ON FUNCTION vendite.fn_log_pipeline_fase(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_fase text, p_status character, p_messaggio text, p_meta jsonb, p_error_code text)
IS 'Scrive una riga di log di FASE su vendite.fatturazione_lotti_log, arricchendola col tipo lotto e lo stato operativo letti dalla testata. ⭐ rev 2026-08-21 (cantiere brief-db-liste-drawer-lotto, L1/P-2): accetta p_error_code e lo scrive in meta->>''error_code''. Nasce da una misura: NESSUNA funzione del database cattura CONSTRAINT_NAME, quindi il codice di dominio — quello registrato a catalogo, su cui il backend mappa status HTTP e ui_action — non veniva conservato da nessuna parte, e i log tenevano solo RETURNED_SQLSTATE, che per un errore di dominio e'' SEMPRE P0001 e non distingue niente. ⭐ Il codice sta in `meta` e non in una colonna: e'' un dato locale al log, non un asse di ricerca, e le righe gia'' scritte non lo avranno mai — non e'' ricostruibile dal testo del messaggio — quindi una colonna NOT NULL mentirebbe sullo storico e una nullable non aggiungerebbe niente al jsonb. ⚠️ Un parametro dichiarato e non «lo mette il chiamante in p_meta»: cinque chiamanti sceglierebbero cinque nomi, e la lista che lo legge deve conoscerne uno. ⛔ NESSUNA validazione contro config.codici_errore, di proposito: questa funzione scrive un log, e un log non deve poter fallire per un refuso nel codice che registra — fallirebbe dentro il ramo EXCEPTION di qualcun altro, sostituendo il guasto vero con il proprio. Il presidio dei codici non dichiarati vive in dbops.vw_codici_errore_da_dichiarare, che guarda e non blocca. Il valore vuoto o di soli spazi e'' assenza e non entra in meta. Il parametro e'' il SETTIMO, in coda: le tre funzioni DB chiamanti e la chiamata posizionale a sei argomenti del backend continuano a funzionare identiche. ⚠️ E'' comunque un DROP + CREATE — un parametro nuovo crea un overload, e con la vecchia firma viva ogni chiamata a sei argomenti sarebbe ambigua.';
```

---
{% include-markdown "signature-core.md" %}
