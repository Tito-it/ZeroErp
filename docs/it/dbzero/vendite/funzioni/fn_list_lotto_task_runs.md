{% include-markdown "it/dbzero/vendite/manual/fn_list_lotto_task_runs.md" %}
# ⚙️ Funzione `fn_list_lotto_task_runs`

```sql
CREATE FUNCTION fn_list_lotto_task_runs(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_solo_attivi boolean, p_limit integer, p_offset integer, p_order_by text, p_order_dir text, p_solo_giro_corrente boolean, p_task_stato text[])
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_lotto_task_runs(p_lotto_id bigint, p_stato_doc_fiscale_id bigint DEFAULT NULL::bigint, p_task_code character varying DEFAULT NULL::character varying, p_solo_attivi boolean DEFAULT true, p_limit integer DEFAULT 500, p_offset integer DEFAULT 0, p_order_by text DEFAULT NULL::text, p_order_dir text DEFAULT 'desc'::text, p_solo_giro_corrente boolean DEFAULT false, p_task_stato text[] DEFAULT NULL::text[])
 RETURNS TABLE(id bigint, lotto_id bigint, pipeline_id bigint, stato_doc_fiscale_id integer, task_code character varying, fase character varying, tentativo smallint, task_stato character varying, started_at timestamp with time zone, ended_at timestamp with time zone, error_code character varying, error_message text, meta jsonb, attivo boolean, giro_corrente boolean, total_count bigint, esclusi_count bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ `text` esplicito: sono FRAMMENTI DI SQL da interpolare,
    --    non valori di colonna. Non c'e' niente da ancorare.
    v_order_col    text;
    v_order_dir    text;
    v_solo_attivi  vendite.fatturazione_lotti_task_runs.attivo%TYPE;
    -- Idem: un limite e uno scostamento non sono un dato del
    --    dominio, sono la finestra con cui lo si guarda.
    v_limit        integer;
    v_offset       integer;
    -- ⭐ L'ancora del giro corrente. ⚠️ `timestamptz` esplicito: e' una
    --    SOGLIA calcolata, non il valore di una colonna.
    v_ancora       timestamptz;
    v_solo_giro    boolean;
BEGIN
    -- Guard sul parametro obbligatorio: id nullo o non positivo e'
    -- un chiamante rotto, non un dato che una persona ha digitato.
    IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_list_lotto_task_runs', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_lotto_id', 'valore', p_lotto_id),
            NULL::uuid, 'p_lotto_id obbligatorio e > 0');
    END IF;

    -- Normalizzazioni. Il tetto di 500 e' lo stesso che il backend
    -- applica oggi: si sposta il clamp dove sta la query, non si
    -- alza. Un limite nullo vale il default, non «tutte».
    v_solo_attivi := COALESCE(p_solo_attivi, TRUE);
    v_limit       := LEAST(GREATEST(COALESCE(p_limit, 500), 1), 500);
    v_offset      := GREATEST(COALESCE(p_offset, 0), 0);
    v_solo_giro   := COALESCE(p_solo_giro_corrente, FALSE);

    -- ⭐ L'ANCORA DEL GIRO CORRENTE — la STESSA di
    --    vendite.fn_list_lotto_segnalazioni, e non e' pigrizia: le due liste
    --    stanno nello stesso drawer, e se dicessero «giro» in due modi
    --    diversi l'operatore vedrebbe due elenchi che non tornano — con la
    --    causa impossibile da attribuire.
    --
    -- ⚠️ NULL = il lotto non e' mai passato dal runner: non c'e' nessuna
    --    corsa precedente da cui distinguersi, e tutto conta come corrente.
    --
    -- ⛔ CHE COSA QUESTA ANCORA **NON** FA, e va saputo prima di fidarsene:
    --    il runner incatena piu' passate in un solo giro dell'operatore
    --    (`run_lotto_pipeline_until_done`) e ognuna scrive il proprio
    --    PIPELINE_STARTED. L'ancora e' l'ULTIMA: su una catena il filtro
    --    mostra l'ultima PASSATA, non tutto il click. Misurato sul lotto
    --    6260: 1 riga su 90, mentre il click ne aveva prodotte 10.
    --    ⭐ E' esattamente la domanda Q-7 del cantiere `event_log` («il filo
    --    identifica la passata o l'azione?»): il giorno che si chiude, questa
    --    ancora e quella delle segnalazioni cambiano INSIEME, in due posti
    --    soli. ⚠️ Finche' resta cosi', il conteggio degli esclusi non e' un
    --    di piu': e' cio' che dice all'operatore che sta guardando una fetta.
    SELECT max(e.event_time)
      INTO v_ancora
      FROM vendite.event_log e
     WHERE e.entity_type = 'LOTTO'
       AND e.entity_id   = p_lotto_id
       AND e.event_code  = 'PIPELINE_STARTED';

    -- ⭐ WHITELIST CHIUSA. I nomi sono i `campo_sorgente` delle
    --    colonne di ui.lista_colonna della lista
    --    `vendite.lotto_task_runs`: e' con quelli che il presidio
    --    dei seed confronta il flag `ordinabile`.
    --    Il ramo '' e' il default (nessun ordinamento chiesto) e non
    --    e' una colonna: il lettore del presidio lo salta apposta.
    v_order_col := CASE lower(btrim(COALESCE(p_order_by, '')))
        WHEN ''              THEN 'x.started_at'
        WHEN 'fase'          THEN 'x.fase'
        WHEN 'task_code'     THEN 'x.task_code'
        WHEN 'tentativo'     THEN 'x.tentativo'
        WHEN 'task_stato'    THEN 'x.task_stato'
        WHEN 'started_at'    THEN 'x.started_at'
        WHEN 'ended_at'      THEN 'x.ended_at'
        WHEN 'error_code'    THEN 'x.error_code'
        WHEN 'error_message' THEN 'x.error_message'
        ELSE NULL
    END;

    -- Fail-loud: un nome fuori whitelist NON ripiega sul default.
    -- Ripiegare in silenzio produce una lista ordinata in un modo
    -- che nessuno ha chiesto e che nessuno sa spiegare — lo stesso
    -- difetto della freccia che non ordina, visto dall'altro lato.
    IF v_order_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_list_lotto_task_runs', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_order_by', 'valore', p_order_by),
            NULL::uuid, concat('p_order_by non ammesso: ', p_order_by));
    END IF;

    -- ⚠️ Il default e' DESC (ordine storico della lista), non ASC.
    v_order_dir := CASE WHEN lower(btrim(COALESCE(p_order_dir, 'desc'))) = 'asc'
                        THEN 'ASC' ELSE 'DESC' END;

    -- ⚠️ NULLS LAST esplicito in ENTRAMBI i versi: quattro delle
    --    colonne ordinabili sono nullable (fase, ended_at,
    --    error_code, error_message) e sul DESC PostgreSQL mette i
    --    NULL in TESTA — i task mai finiti salirebbero per primi.
    --    Il pareggio si rompe su r.id nella stessa direzione, cosi'
    --    la pagina 2 non ripete righe della pagina 1.
    RETURN QUERY EXECUTE format($q$
        WITH filtrata AS (
            SELECT r.*,
                   ($7::timestamptz IS NULL OR r.started_at >= $7::timestamptz)
                       AS giro_corrente
              FROM vendite.fatturazione_lotti_task_runs r
             WHERE r.lotto_id = $1
               AND ($2 IS NULL OR r.stato_doc_fiscale_id = $2::INTEGER)
               AND ($3 IS NULL OR r.task_code = $3)
               AND (NOT $4 OR r.attivo IS TRUE)
        )
        SELECT x.id,
               x.lotto_id,
               x.pipeline_id,
               x.stato_doc_fiscale_id,
               x.task_code,
               x.fase,
               x.tentativo,
               x.task_stato,
               x.started_at,
               x.ended_at,
               x.error_code,
               x.error_message,
               x.meta,
               x.attivo,
               x.giro_corrente,
               count(*) OVER ()::bigint                          AS total_count,
               -- ⭐ QUANTE RIGHE I FILTRI NUOVI HANNO TOLTO. Si conta su
               --    `filtrata`, cioe' PRIMA di applicarli: e' l'unico posto
               --    da cui si vedono.
               -- ⚠️ Si chiama `esclusi_count` e non «fuori_giro»: gli esclusi
               --    sono quelli che QUALUNQUE filtro nuovo ha tolto, giro o
               --    esito. Un nome che parla del giro avrebbe costretto a
               --    inventarne un secondo il giorno dopo.
               (SELECT count(*) FROM filtrata y
                 WHERE NOT ( (NOT $8 OR y.giro_corrente)
                         AND ($9 IS NULL OR y.task_stato = ANY($9)) )
               )::bigint                                         AS esclusi_count
          FROM filtrata x
         WHERE (NOT $8 OR x.giro_corrente)
           AND ($9 IS NULL OR x.task_stato = ANY($9))
         ORDER BY %s %s NULLS LAST, x.id %s
         LIMIT $5 OFFSET $6
    $q$, v_order_col, v_order_dir, v_order_dir)
    USING p_lotto_id, p_stato_doc_fiscale_id, p_task_code,
          v_solo_attivi, v_limit, v_offset,
          v_ancora, v_solo_giro, p_task_stato;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_lotto_task_runs(p_lotto_id bigint, p_stato_doc_fiscale_id bigint, p_task_code character varying, p_solo_attivi boolean, p_limit integer, p_offset integer, p_order_by text, p_order_dir text, p_solo_giro_corrente boolean, p_task_stato text[])
IS 'Elenco PAGINATO dei task run di un lotto, con whitelist chiusa di ordinamento e fail-loud sul nome fuori whitelist. ⭐ rev 2026-08-21 (cantiere brief-db-liste-drawer-lotto, L1/P-1): nasce per riunire DUE sorgenti che dicevano cose diverse — questa funzione (started_at ASC, nessun filtro su `attivo`, chiamata da nessuno) e la query diretta del backend (DESC, `attivo IS TRUE`, LIMIT 100 fisso), che e'' quella che il drawer mostrava. ⚠️ I nomi della whitelist sono i `campo_sorgente` delle colonne di ui.lista_colonna (task_stato, started_at, ended_at), NON i loro codici logici (esito, inizio, fine): e'' con i primi che scripts/gen_seed_lista.py confronta il flag `ordinabile`, e il presidio sa leggere una whitelist da funzione DB cercando i rami WHEN ... THEN in questa definizione. ⚠️ Il default di p_order_dir e'' `desc` e non `asc` come nella sorella fn_list_commessa_attivita: l''ordine storico di questa lista e'' discendente e rovesciarlo in silenzio sarebbe una regressione travestita da riordino. ⭐ `total_count` viaggia CON le righe (count(*) OVER (), valutato prima di LIMIT/OFFSET) invece che con un secondo SELECT: cosi'' i filtri sono scritti una volta sola — il difetto opposto e'' documentato dal repository delle attivita'' di commessa, dove ogni filtro va ripetuto nella query del conteggio. ⚠️ Il prezzo e'' che una pagina vuota non riporta il totale, come in _query_paged_view del backend. Il filtro `attivo` NON e'' decorativo: vendite.fn_riporta_lotto_a_draft spegne i task run della vita precedente del lotto, e senza il filtro riportare un lotto a DRAFT farebbe ricomparire i tentativi di un giro annullato; p_solo_attivi = false serve a guardarli di proposito. ⚠️ I tre parametri storici restano identici per nome, tipo e posizione: le chiamate esistenti non cambiano. ⭐ Tipi ancorati con %TYPE in FIRMA, RETURNS TABLE e DECLARE — con una scelta da leggere: p_stato_doc_fiscale_id e'' ancorato a config.stati_doc_fiscale.id (bigint) e NON alla colonna omonima della tabella, che e'' integer. Cio'' che il parametro riceve e'' un id di quel catalogo, quindi l''ancora semantica e'' quella; ed e'' anche l''unica che non cambia il tipo del parametro, quindi nessuna chiamata esistente smette di risolvere. Il corpo continua a castare a integer dove confronta. Restano espliciti, di proposito: p_limit / p_offset / p_order_by / p_order_dir (la finestra con cui si guarda un dato non e'' un dato, e p_order_by porta il NOME di una colonna, non il suo contenuto), total_count (un conteggio) e i due v_order_* (frammenti di SQL da interpolare). ⭐ rev 2026-08-24 (richiesta del backend): due filtri e un conteggio. p_solo_giro_corrente usa la STESSA ancora di fn_list_lotto_segnalazioni — l''ultimo PIPELINE_STARTED del lotto — perche'' le due liste stanno nello stesso drawer e devono dire «giro» nello stesso modo. p_task_stato e'' un ARRAY (mostrami errori E annullati e'' una domanda legittima). esclusi_count dice quante righe i filtri hanno tolto, e si chiama cosi'' e non «fuori giro» perche'' vale per qualunque filtro: senza quel numero una lista filtrata e una lista vuota si leggono uguali. ⛔ CHE COSA L''ANCORA NON FA: il runner incatena piu'' passate in un giro solo e ognuna scrive il proprio PIPELINE_STARTED, quindi il filtro mostra l''ultima PASSATA e non tutto il click — misurato sul 6260: 1 riga su 90 contro le 10 del click. E'' la domanda Q-7 del cantiere event_log; il giorno che si chiude, questa ancora e quella delle segnalazioni cambiano insieme. ⚠️ p_stato_doc_fiscale_id resta bigint e NON e'' ancorato: la colonna e'' integer, e ancorarlo cambierebbe l''identita'' della funzione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
