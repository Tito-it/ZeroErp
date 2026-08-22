# ⚙️ Funzione `fn_list_lotto_segnalazioni`

```sql
CREATE FUNCTION fn_list_lotto_segnalazioni(p_lotto_id bigint, p_origine text, p_livello character, p_solo_attive boolean, p_solo_job_corrente boolean, p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_lotto_segnalazioni(p_lotto_id bigint, p_origine text DEFAULT NULL::text, p_livello character DEFAULT NULL::bpchar, p_solo_attive boolean DEFAULT true, p_solo_job_corrente boolean DEFAULT false, p_limit integer DEFAULT 500, p_offset integer DEFAULT 0, p_order_by text DEFAULT NULL::text, p_order_dir text DEFAULT 'desc'::text)
 RETURNS TABLE(riga_key text, id bigint, origine text, data_ora timestamp with time zone, livello character, messaggio text, error_code text, fase text, fattura_id bigint, documento_display text, importo numeric, disabilitato boolean, job_corrente boolean, total_count bigint, fuori_job_count bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_order_col   text;
    v_order_dir   text;
    v_solo_attive boolean;
    v_solo_job    boolean;
    v_limit       integer;
    v_offset      integer;
    -- L'istante di inizio dell'ultima corsa. `timestamptz` esplicito:
    -- e' un confine, non il valore di una colonna di queste tabelle.
    v_ancora      timestamptz;
BEGIN
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_list_lotto_segnalazioni', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    -- ⚠️ Un valore fuori vocabolario SOLLEVA e non filtra a vuoto:
    --    una lista vuota si legge come «non c'e' niente», cioe' il
    --    difetto si traveste da dato. Stessa scelta di
    --    fn_list_commessa_attivita su p_tipo_movimento.
    IF p_origine IS NOT NULL
       AND upper(btrim(p_origine)) NOT IN ('FATTURA', 'LOTTO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_list_lotto_segnalazioni', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_origine', 'valore', p_origine),
            NULL::uuid, concat('p_origine non ammesso: ', p_origine));
    END IF;

    IF p_livello IS NOT NULL
       AND upper(btrim(p_livello::text)) NOT IN ('C', 'W', 'I') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_list_lotto_segnalazioni', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_livello', 'valore', p_livello),
            NULL::uuid, concat('p_livello non ammesso: ', p_livello));
    END IF;

    -- ⛔ IL PERIMETRO VIENE DAL LOTTO. `fatturazione_lotti` ha la RLS
    --    e questa funzione e' SECURITY INVOKER: un lotto fuori dal
    --    perimetro emittente si legge come «non c'e'». Qui si SOLLEVA
    --    invece di rispondere zero righe, perche' «non lo vedo» e
    --    «non ce ne sono» non devono leggersi uguali.
    PERFORM 1 FROM vendite.fatturazione_lotti l WHERE l.id = p_lotto_id;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_list_lotto_segnalazioni', 'E_VALORE_MANCANTE',
            jsonb_build_object('lotto_id', p_lotto_id),
            NULL::uuid, concat('lotto_id ', p_lotto_id));
    END IF;

    v_solo_attive := COALESCE(p_solo_attive, TRUE);
    v_solo_job    := COALESCE(p_solo_job_corrente, FALSE);
    v_limit       := LEAST(GREATEST(COALESCE(p_limit, 500), 1), 500);
    v_offset      := GREATEST(COALESCE(p_offset, 0), 0);

    -- ⭐ L'ANCORA DELL'ULTIMO JOB. Il runner scrive PIPELINE_STARTED
    --    a ogni corsa: e' l'unica cosa che distingue una corsa dalla
    --    precedente (il correlation_id e' il lock_batch_id, che due
    --    corse condividono).
    --    ⚠️ NULL = il lotto non e' mai passato dal runner: allora non
    --    c'e' nessuna corsa precedente da cui distinguersi, e tutto
    --    conta come corrente.
    SELECT max(e.event_time)
      INTO v_ancora
      FROM vendite.event_log e
     -- ⚠️ Rev 2026-08-22 (L4): via il filtro `e.domain = 'PIPELINE'`.
     --   Era RIDONDANTE — la query filtra gia' `event_code =
     --   'PIPELINE_STARTED'`, e un codice appartiene a un dominio solo —
     --   e la colonna non esiste piu': il dominio e' una proprieta' del
     --   codice e vive in config.eventi_dominio, non copiata su ogni riga
     --   dove potrebbe dissentire.
     WHERE e.entity_type = 'LOTTO'
       AND e.entity_id   = p_lotto_id
       AND e.event_code  = 'PIPELINE_STARTED';

    -- ⭐ WHITELIST CHIUSA. I nomi sono i `campo_sorgente` delle
    --    colonne del seed della lista `vendite.lotto_segnalazioni`.
    --    ⚠️ `messaggio` e `disabilitato` NON ci sono di proposito: il
    --    seed li offre `ordinabile = f`, e una voce che il seed non
    --    offre e' una capacita' irraggiungibile che il presidio
    --    segnala.
    v_order_col := CASE lower(btrim(COALESCE(p_order_by, '')))
        -- ⛔ Il default e la voce `livello` NON ordinano per il valore
        --    dello status: 'C' viene prima di 'I' in ordine alfabetico
        --    PER CASO, e 'W' finisce in fondo PER CASO. Serve un rango.
        --    ⚠️ I tre letterali sono MAIUSCOLI di necessita': il
        --    lettore della whitelist (gen_seed_lista.py) cerca
        --    `WHEN '<nome>' THEN` con [a-z_0-9]+, quindi un `WHEN 'c'`
        --    verrebbe scambiato per il nome di una colonna ordinabile.
        WHEN ''                  THEN 'CASE x.livello WHEN ''C'' THEN 3 WHEN ''W'' THEN 2 ELSE 1 END'
        WHEN 'livello'           THEN 'CASE x.livello WHEN ''C'' THEN 3 WHEN ''W'' THEN 2 ELSE 1 END'
        WHEN 'data_ora'          THEN 'x.data_ora'
        WHEN 'origine'           THEN 'x.origine'
        WHEN 'documento_display' THEN 'x.documento_display'
        WHEN 'importo'           THEN 'x.importo'
        WHEN 'error_code'        THEN 'x.error_code'
        WHEN 'fase'              THEN 'x.fase'
        WHEN 'job_corrente'      THEN 'x.job_corrente'
        ELSE NULL
    END;

    IF v_order_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_list_lotto_segnalazioni', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_order_by', 'valore', p_order_by),
            NULL::uuid, concat('p_order_by non ammesso: ', p_order_by));
    END IF;

    v_order_dir := CASE WHEN lower(btrim(COALESCE(p_order_dir, 'desc'))) = 'asc'
                        THEN 'ASC' ELSE 'DESC' END;

    -- ⚠️ NULLS LAST in ENTRAMBI i versi: meta' delle colonne e' NULL
    --    su meta' delle righe PER COSTRUZIONE (documento e importo
    --    solo su FATTURA, fase solo su LOTTO). Sul DESC PostgreSQL
    --    mette i NULL in testa, quindi «per importo, dal piu' grande»
    --    comincerebbe dagli eventi di lotto, che un importo non ce
    --    l'hanno.
    --    Il pareggio si rompe su (origine, id): la union ha due spazi
    --    di id, e la coppia e' l'unica chiave stabile.
    RETURN QUERY EXECUTE format($q$
        WITH base AS (
            SELECT 'FATTURA'::text                                  AS origine,
                   fl.id,
                   fl.data_ora,
                   fl.status                                        AS livello,
                   fl.messaggio,
                   NULLIF(btrim(fl.meta->>'error_code'), '')        AS error_code,
                   NULL::text                                       AS fase,
                   fl.fattura_id,
                   -- ⭐ L'identita' del documento si legge dallo
                   --    SNAPSHOT sulla riga fattura, non da un join ad
                   --    anagrafiche: `billing_account` ha la RLS, e il
                   --    nome sparirebbe per una ragione che col log non
                   --    c'entra. Lo snapshot lo scrive il task DRAFT
                   --    `snapshot_indirizzi_lotto`, quindi su un lotto
                   --    che ha girato c'e'; il ripiego sul codice del
                   --    billing account copre la fattura che non ci e'
                   --    ancora passata.
                   COALESCE(
                       NULLIF(btrim(f.cliente_snapshot->>'denominazione'), ''),
                       NULLIF(btrim(f.cliente_snapshot->>'ba_codice'), '')
                   )                                                AS documento_display,
                   f.totale_doc                                     AS importo,
                   fl.disabilitato,
                   ($2 IS NULL OR fl.data_ora >= $2)                AS job_corrente
              FROM vendite.fatturazione_lotti_fatture lf
              JOIN vendite.fatture_log fl ON fl.fattura_id = lf.fattura_id
              -- LEFT: il log esiste anche se la fattura non e'
              -- visibile; la riga resta, senza nome e senza importo.
              LEFT JOIN vendite.fatture f ON f.id = lf.fattura_id
             WHERE lf.lotto_id = $1

            UNION ALL

            SELECT 'LOTTO'::text,
                   ll.id,
                   ll.data_ora,
                   ll.status,
                   ll.messaggio,
                   NULLIF(btrim(ll.meta->>'error_code'), ''),
                   ll.fase,
                   NULL::bigint,
                   NULL::text,
                   NULL::numeric,
                   ll.disabilitato,
                   ($2 IS NULL OR ll.data_ora >= $2)
              FROM vendite.fatturazione_lotti_log ll
             WHERE ll.lotto_id = $1
        ), filtrata AS (
            SELECT b.*
              FROM base b
             WHERE ($3 IS NULL OR b.origine = upper(btrim($3)))
               AND ($4 IS NULL OR b.livello = upper(btrim($4)))
               AND (NOT $5 OR b.disabilitato IS FALSE)
        )
        SELECT format('%%s:%%s', x.origine, x.id)                   AS riga_key,
               x.id,
               x.origine,
               x.data_ora,
               x.livello,
               x.messaggio,
               x.error_code,
               x.fase,
               x.fattura_id,
               x.documento_display,
               x.importo,
               x.disabilitato,
               x.job_corrente,
               count(*) OVER ()::bigint                             AS total_count,
               -- ⭐ Quante righe VIVE restano fuori dalla finestra del
               --    job. Si conta su `filtrata`, cioe' PRIMA del filtro
               --    sul job: e' l'unico posto da cui si vedono.
               (SELECT count(*) FROM filtrata y
                 WHERE y.job_corrente IS FALSE)::bigint             AS fuori_job_count
          FROM filtrata x
         WHERE (NOT $6 OR x.job_corrente)
         ORDER BY %s %s NULLS LAST, x.data_ora DESC, x.origine, x.id
         LIMIT $7 OFFSET $8
    $q$, v_order_col, v_order_dir)
    USING p_lotto_id, v_ancora, p_origine, p_livello,
          v_solo_attive, v_solo_job, v_limit, v_offset;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_lotto_segnalazioni(p_lotto_id bigint, p_origine text, p_livello character, p_solo_attive boolean, p_solo_job_corrente boolean, p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
IS 'Le segnalazioni di un lotto come RIGHE, unendo vendite.fatture_log (per documento) e vendite.fatturazione_lotti_log (per lotto) con `origine` come discriminante. Nasce il 2026-08-21 (cantiere brief-db-liste-drawer-lotto, L2/P-7) perche'' il terzo tab del drawer non era una tabella: rendeva i sei conteggi di fn_get_lotto_segnalazioni_summary, e le righe non esistevano da nessuna parte. ⚠️ Le due meta'' sono COMPLEMENTARI e non simmetriche: `documento_display` e `importo` esistono solo sulle righe FATTURA, `fase` solo su quelle LOTTO — da cui il NULLS LAST esplicito in entrambi i versi su ogni ordinamento, stessa lezione di vw_dash_competenza_errori. ⛔ E i due alfabeti del livello sono diversi: chk_fatture_log_status ammette (W,C), chk_fatturazione_lotti_log_status ammette (I,W,C), quindi una segnalazione INFO e'' PER COSTRUZIONE di origine LOTTO. ⭐ `job_corrente` risponde a «vale l''ultimo job?»: l''ancora e'' l''event_time dell''ultimo PIPELINE_STARTED in vendite.event_log — NON il correlation_id (che e'' il lock_batch_id, condiviso da due corse), NON tx_id (GUC di sessione che sopravvive alla corsa), NON tentativo (conta per task). Ancora NULL (lotto mai passato dal runner) = tutto corrente: senza una corsa precedente non c''e'' niente da considerare stantio. ⭐ `fuori_job_count` conta le righe VIVE che il filtro sul job lascia fuori, e si calcola prima di quel filtro: le segnalazioni per fattura attraversano i job finche'' sono vere (il runner azzera solo le C di lotto), quindi la lista deve poter dire «+N di corse precedenti» invece di ingoiarle. ⛔ La regola dell''ultimo job vale sulla LISTA, mai sul GUARD: fn_get_lotto_segnalazioni_summary resta com''e'' perche'' alimenta blocks_next_step, e restringerla farebbe avanzare un lotto con una critica irrisolta. ⚠️ Il perimetro viene DAL LOTTO: i due log e il ponte non hanno RLS, fatturazione_lotti si'', e se il lotto non e'' visibile la funzione SOLLEVA invece di rispondere zero righe — «non lo vedo» e «non ce ne sono» non devono leggersi uguali. Regge perche'' fatturazione_lotti.emittente_soggetto_ruolo_id e'' NOT NULL: un lotto ha un emittente, quindi lista e contatori del banner contano la stessa popolazione per costruzione. ⭐ `livello` si ordina per RANGO di gravita'' e non per valore (C prima di I in ordine alfabetico e'' un caso), e i tre letterali del rango sono MAIUSCOLI di necessita'': il lettore della whitelist dei seed cerca WHEN ''<nome>'' THEN con [a-z_0-9]+, e in minuscolo li scambierebbe per nomi di colonna. `messaggio` e `disabilitato` non sono in whitelist perche'' il seed li offre non ordinabili. L''identita'' del documento viene dallo snapshot sulla riga fattura e non da un join ad anagrafiche, che ha la RLS.';
```

---
{% include-markdown "signature-core.md" %}
