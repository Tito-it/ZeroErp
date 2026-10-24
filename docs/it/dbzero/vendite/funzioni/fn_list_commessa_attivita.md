{% include-markdown "it/dbzero/vendite/manual/fn_list_commessa_attivita.md" %}
# ⚙️ Funzione `fn_list_commessa_attivita`

```sql
CREATE FUNCTION fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer, p_order_by text, p_order_dir text, p_tipo_movimento character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying DEFAULT NULL::character varying, p_stato_approvazione character varying DEFAULT NULL::character varying, p_competenza_mese date DEFAULT NULL::date, p_limit integer DEFAULT 1000, p_offset integer DEFAULT 0, p_order_by text DEFAULT NULL::text, p_order_dir text DEFAULT 'asc'::text, p_tipo_movimento character varying DEFAULT NULL::character varying)
 RETURNS TABLE(id bigint, commessa_id bigint, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, competenza_mese date, competenza_dal date, competenza_al date, prezzo_snapshot numeric, prezzo_bloccato boolean, prezzo_da_riallineare boolean, stato_approvazione character varying, stato_emissione character varying, sorgente_tipo_id bigint, sorgente_codice_interno character varying, meta jsonb, data_update timestamp with time zone, fatturata boolean, fatturata_il timestamp with time zone, fattura_id bigint, fattura_numero bigint, fattura_stato character varying, sorgente_uid text, sorgente_apribile boolean, sorgente_documento_id bigint, tipo_movimento character varying, articolo_codice character varying, articolo_descrizione character varying, sorgente_documento_numero text, gruppo_key text, sorgente_etichetta character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- rev 2026-10-20 (20261020-63, brief-db-grammatica-unica-documenti, 2d G-6):
--   sorgente_area (il plurale, ritirato) diventa sorgente_apribile: il
--   documento d'origine si apre dal codice della sorgente; firma e
--   RETURNS TABLE ancorati.
-- rev 2026-10-21 (20261021-20, brief-db-grammatica-unica-documenti, G-1):
--   sorgente_codice (config.sorgenti.codice, il nome modificabile) esce;
--   il documento d'origine si apre da sorgente_codice_interno, l'unico
--   protetto dal lock, e la lista mostra sorgente_etichetta.
DECLARE
    v_competenza_mese vendite.commesse_attivita.competenza_mese%TYPE;
    v_tipo_movimento  vendite.commesse_attivita.tipo_movimento%TYPE;
    v_order_col       text;
    v_order_dir       text;
BEGIN
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id), NULL::uuid, 'p_commessa_id obbligatorio e > 0');
    END IF;

    -- ⭐ Filtro tipo_movimento (BE, 2026-08-20 seconda mandata).
    -- Il parametro e' il NONO nella firma (in coda), ma il filtro
    -- e' il quarto: la posizione serve ai chiamanti, non alla
    -- logica.
    -- NULL/vuoto = tutti i movimenti: chi non chiede niente ottiene
    -- esattamente il risultato di prima.
    -- ⚠️ FAIL-LOUD sul vocabolario, e non filtro a vuoto: un valore
    -- sbagliato che restituisce zero righe si legge come «non c'e'
    -- niente», cioe' il difetto si traveste da dato. E' la stessa
    -- classe della «freccia che non ordina» qui sotto.
    -- ⚠️ Questi tre letterali sono una LETTURA del vocabolario: a
    -- enforcarlo e' il CHECK chk_commesse_attivita_tipo_movimento
    -- sulla tabella, che resta l'unica difesa vera. Se un giorno
    -- il vocabolario cresce, la mossa e' una tabella di catalogo
    -- con codice_interno, non una quarta copia.
    v_tipo_movimento := NULLIF(upper(btrim(COALESCE(p_tipo_movimento, ''))), '');

    IF v_tipo_movimento IS NOT NULL
       AND v_tipo_movimento NOT IN ('NORMALE', 'RETTIFICA', 'ONERE') THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_movimento', 'valore', p_tipo_movimento),
            NULL::uuid, concat('p_tipo_movimento non ammesso: ', p_tipo_movimento));
    END IF;

    -- ⚠️ La whitelist si valida PRIMA di andare a cercare la
    -- commessa: un parametro sbagliato non deve costare una query
    -- per essere respinto. Stessa scelta fatta dal BE sulla coda
    -- approvazioni, dove la validazione precede la risoluzione
    -- utente/emittente.
    -- Whitelist di ordinamento: mappa CHIUSA nome -> espressione.
    -- Le chiavi sono i `campo_sorgente` che il seed manda dal FE
    -- (<ListaConfigurabile> monta le Column su campo_sorgente).
    -- NULL/vuoto = ordine storico `ca.id`: le chiamate che non
    -- chiedono niente ottengono esattamente quello di prima.
    v_order_col := CASE lower(btrim(COALESCE(p_order_by, '')))
        WHEN ''                   THEN 'ca.id'
        WHEN 'id'                 THEN 'ca.id'
        WHEN 'data_attivita'      THEN 'ca.data_attivita'
        WHEN 'competenza_mese'    THEN 'ca.competenza_mese'
        WHEN 'segment_key'        THEN 'ca.segment_key'
        WHEN 'quantita'           THEN 'ca.quantita'
        WHEN 'prezzo_snapshot'    THEN 'ca.prezzo_snapshot'
        WHEN 'stato_approvazione' THEN 'ca.stato_approvazione'
        WHEN 'stato_emissione'    THEN 'ca.stato_emissione'
        -- Nuove dal 2026-08-16. `fatturata_il` e' quella che serve
        -- alla domanda che ha originato la richiesta: distinguere
        -- una riga fatturata ieri da una di tre mesi fa.
        WHEN 'fatturata_il'       THEN 'fatt.fatturata_il'
        WHEN 'fattura_numero'     THEN 'fatt.fattura_numero'
        -- Nuove dal 2026-08-20 (provenienza). ⚠️ Entrano QUI nello
        -- stesso giro in cui entrano a catalogo: una colonna con
        -- `ordinabile = t` su un nome che questa mappa non conosce
        -- non da' una freccia inerte, ROMPE la lista al primo
        -- click (il ramo sotto e' fail-loud, e deve restarlo).
        WHEN 'tipo_movimento'            THEN 'ca.tipo_movimento'
        WHEN 'articolo_codice'           THEN 'art.codice'
        WHEN 'articolo_descrizione'      THEN 'art.descrizione'
        -- 2026-10-21: la colonna «Tipo origine» mostra l'etichetta
        -- della sorgente, non piu' il suo codice.
        WHEN 'sorgente_etichetta'        THEN 's.etichetta'
        WHEN 'sorgente_documento_numero' THEN 'ref.documento_numero'
        WHEN 'gruppo_key'                THEN 'grp.gruppo_key'
        ELSE NULL
    END;

    -- Fail-loud: un nome fuori whitelist NON ripiega sul default.
    -- Un ripiego silenzioso e' la «freccia che non ordina»: a video
    -- sembra funzionare e restituisce un ordine che nessuno ha chiesto.
    IF v_order_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_order_by', 'valore', p_order_by),
            NULL::uuid, concat('p_order_by non ammesso: ', p_order_by));
    END IF;

    v_order_dir := CASE WHEN lower(btrim(COALESCE(p_order_dir, 'asc'))) = 'desc'
                        THEN 'DESC' ELSE 'ASC' END;

    IF NOT EXISTS (SELECT 1 FROM vendite.commesse c WHERE c.id = p_commessa_id) THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id), NULL::uuid, concat('commessa_id ', p_commessa_id));
    END IF;

    -- Sanitize limit/offset
    IF p_limit IS NULL OR p_limit <= 0 THEN p_limit := 1000; END IF;
    IF p_limit > 10000 THEN p_limit := 10000; END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN p_offset := 0; END IF;

    v_competenza_mese := CASE WHEN p_competenza_mese IS NOT NULL
        THEN date_trunc('month', p_competenza_mese)::DATE ELSE NULL END;

    -- SQL dinamico solo per l'ORDER BY (non parametrizzabile).
    -- L'espressione viene dal CASE chiuso qui sopra, MAI dal
    -- parametro: i valori restano parametri veri (USING).
    -- Tiebreak ca.id: senza, righe con la stessa chiave possono
    -- scambiarsi fra una pagina e l'altra.
    -- ⚠️ NULLS LAST ESPLICITO, e non solo sul DESC: chi ordina per
    -- una colonna vuole vedere per prime le righe che quel valore
    -- ce l'hanno. Su ASC e' gia' il default di PostgreSQL, su DESC
    -- e' l'opposto — scriverlo per entrambi i versi evita che
    -- l'ordinamento si comporti in due modi diversi a seconda
    -- della freccia.
    -- ℹ️ Il filtro nuovo e' $7, in CODA ai placeholder e non al suo
    -- posto logico: rinumerare $5/$6 per infilarlo in mezzo e'
    -- esattamente il tipo di modifica che si sbaglia in silenzio.
    RETURN QUERY EXECUTE format($q$
        SELECT ca.id, ca.commessa_id, ca.segment_key, ca.articolo_id, ca.istanza_utility_id,
               ca.data_attivita, ca.uom_id, ca.quantita, ca.competenza_mese, ca.competenza_dal,
               ca.competenza_al, ca.prezzo_snapshot, ca.prezzo_bloccato, ca.prezzo_da_riallineare,
               ca.stato_approvazione, ca.stato_emissione, ca.sorgente_tipo_id,
               s.codice_interno AS sorgente_codice_interno, ca.meta, ca.data_update,
               -- fatturata: specchio del guard BE _assert_non_fatturata.
               -- ⚠️ Resta l'EXISTS su attivita_fatturabili, che NON ha
               -- RLS, e non diventa `fatt.fattura_id IS NOT NULL`:
               -- vendite.fatture ce l'ha, e chi non vede la fattura
               -- leggerebbe «da fatturare» una riga gia' fatturata.
               EXISTS (
                   SELECT 1 FROM vendite.attivita_fatturabili af
                    WHERE af.commessa_attivita_id = ca.id
                      AND af.fattura_riga_id IS NOT NULL
               ) AS fatturata,
               -- Il momento in cui la riga e' stata PORTATA in
               -- fattura: la nascita della riga di fattura, non
               -- l'ultimo aggiornamento dell'attivita'.
               fatt.fatturata_il,
               fatt.fattura_id, fatt.fattura_numero, fatt.fattura_stato,
               ca.sorgente_uid, s.apribile AS sorgente_apribile,
               -- Id e numero del documento di origine: UNA
               -- chiamata, non due funzioni gemelle.
               ref.documento_id AS sorgente_documento_id,
               -- ===== La provenienza (BE, 2026-08-20) =====
               ca.tipo_movimento,
               art.codice      AS articolo_codice,
               art.descrizione AS articolo_descrizione,
               ref.documento_numero AS sorgente_documento_numero,
               grp.gruppo_key,
               -- ultima, come nella RETURNS TABLE (2026-10-21)
               s.etichetta AS sorgente_etichetta
          FROM vendite.commesse_attivita ca
          LEFT JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
          -- ⚠️ LEFT anche se articolo_id e' NOT NULL, e non perche'
          -- catalogo.articoli abbia la RLS (non ce l'ha): perche'
          -- una riga di lista non deve sparire per colpa di un
          -- decode. Se l'articolo non risolve, mancano il codice e
          -- la descrizione, non la riga.
          LEFT JOIN catalogo.articoli art ON art.id = ca.articolo_id
          -- Il documento di origine, id + numero in una lettura.
          -- La funzione restituisce SEMPRE una riga, quindi qui il
          -- LEFT e' cintura, non necessita'.
          LEFT JOIN LATERAL vendite.fn_get_sorgente_documento_ref(
                       ca.sorgente_tipo_id, ca.sorgente_uid) ref ON TRUE
          -- Il gruppo fatturabile dalla SUA unica fonte di verita'.
          -- ⚠️ fn_build_gruppo_fatturabile_key SOLLEVA su coppia
          -- sorgente incoerente o riga sourceless senza commessa:
          -- da qui non puo' accadere — lo impediscono il CHECK
          -- chk_commesse_attivita_sorgente_pair e il NOT NULL su
          -- commessa_id. In un LATERAL cosi' l'ORDER BY puo'
          -- nominarlo come una colonna qualunque.
          CROSS JOIN LATERAL (
              SELECT vendite.fn_build_gruppo_fatturabile_key(
                         ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id
                     ) AS gruppo_key
          ) grp
          -- ⚠️ LATERAL ordinato e non join nuda: oggi il rapporto
          -- attivita' -> riga di fattura e' 1:1, ma e' una
          -- fotografia e non un vincolo. Con una join diretta, il
          -- giorno di una fatturazione parziale la lista
          -- raddoppierebbe le righe — dati sbagliati, non un errore.
          LEFT JOIN LATERAL (
              SELECT fr.data_insert AS fatturata_il,
                     f.id           AS fattura_id,
                     f.numero       AS fattura_numero,
                     sdf.codice_interno AS fattura_stato
                FROM vendite.attivita_fatturabili af
                JOIN vendite.fatture_righe fr ON fr.id = af.fattura_riga_id
                JOIN vendite.fatture f        ON f.id  = fr.fattura_id
                LEFT JOIN config.stati_doc_fiscale sdf ON sdf.id = f.stato_doc_fiscale_id
               WHERE af.commessa_attivita_id = ca.id
               ORDER BY fr.data_insert DESC, fr.id DESC
               LIMIT 1
          ) fatt ON TRUE
         WHERE ca.commessa_id = $1
           AND ($2 IS NULL OR ca.stato_emissione = $2)
           AND ($3 IS NULL OR ca.stato_approvazione = $3)
           AND ($4 IS NULL OR ca.competenza_mese = $4)
           AND ($7 IS NULL OR ca.tipo_movimento = $7)
         ORDER BY %s %s NULLS LAST, ca.id
         LIMIT $5 OFFSET $6
    $q$, v_order_col, v_order_dir)
    USING p_commessa_id, p_stato_emissione, p_stato_approvazione,
          v_competenza_mese, p_limit, p_offset, v_tipo_movimento;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer, p_order_by text, p_order_dir text, p_tipo_movimento character varying)
IS 'Elenco paginato delle attivita'' di una commessa, con whitelist chiusa di ordinamento e fail-loud sul nome fuori whitelist. Rev 2026-08-16 (richiesta BE): porta a valle tre informazioni che si fermavano al database. (1) `fatturata_il` = vendite.fatture_righe.data_insert, cioe'' quando la riga e'' stata PORTATA in fattura — NON `data_update`, che e'' «ultimo aggiornamento» e oggi coincide solo per coincidenza: misurato il 2026-08-16, 10 righe su 37 gia'' divergono, e basta un riallineamento di prezzo dopo la fatturazione perche'' l''etichetta menta. (2) `fattura_id`, `fattura_numero`, `fattura_stato`: il documento su cui navigare, preso con un LATERAL ordinato + LIMIT 1 e non con una join nuda, perche'' il rapporto 1:1 fra attivita'' e riga di fattura e'' una fotografia e non un vincolo — con una join, una fatturazione parziale raddoppierebbe le righe della lista. (3) `sorgente_uid`, `sorgente_area` e `sorgente_documento_id` per l''azione «apri documento sorgente». ⚠️ Il booleano `fatturata` resta calcolato sull''EXISTS in vendite.attivita_fatturabili, che NON ha RLS, e non deriva dalla join: vendite.fatture ce l''ha, e chi non vede la fattura leggerebbe «da fatturare» una riga gia'' fatturata. Cosi'' invece legge fatturata = true con le colonne del documento a NULL: sa che e'' fatturata e sa di non poterci navigare. Rev 2026-08-16 (sera): ORDER BY con NULLS LAST esplicito in ENTRAMBI i versi (sul DESC PostgreSQL mette i NULL in testa, quindi le righe mai fatturate finivano prime). ⭐ Rev 2026-08-20 (richiesta BE, punto 2): la PROVENIENZA della riga arriva a valle, perche'' il documento di fattura si separa per gruppo fatturabile e «da dove viene la riga» e'' il criterio con cui la fattura nasce — a video l''unica traccia era `segment_key`, una chiave tecnica. Cinque colonne additive: `tipo_movimento`, `articolo_codice` e `articolo_descrizione`, `sorgente_documento_numero` (dal resolver unico fn_get_sorgente_documento_ref) e `gruppo_key`. 🔴 La quinta esiste per una misura: le righe RETTIFICA e ONERE sono SOURCELESS per progetto — 9 su 98 il 2026-08-20, cioe'' il 100% delle righe di nota di credito — quindi `sorgente_*` e'' vuoto esattamente sulle righe per cui la colonna e'' stata chiesta, e il loro gruppo fatturabile e'' `MAN:<commessa_id>`, non il DDT. ⭐ Rev 2026-08-20 (richiesta BE, seconda mandata): filtro `p_tipo_movimento` (NULL/vuoto = tutti i movimenti). Nasce dalla colonna: resa visibile «Movimento», il passo dopo e'' isolarla — «fammi vedere solo le rettifiche» — e su una commessa vera sono una manciata di righe dentro centinaia. Un valore fuori vocabolario SOLLEVA E_PARAMETRO_INVALIDO e non filtra a vuoto: una lista vuota si legge come «non c''e'' niente», cioe'' il difetto si traveste da dato — stessa classe della freccia che non ordina. Tollera spazi e minuscole, come p_order_by e p_order_dir. ⚠️ I tre valori qui dentro sono una LETTURA del vocabolario: a enforcarlo e'' il CHECK chk_commesse_attivita_tipo_movimento sulla tabella, e non esiste una tabella-vocabolario per tipo_movimento. ⭐ Il parametro e'' il NONO, IN CODA dopo p_order_dir e non accanto agli altri tre filtri dove starebbe meglio a leggersi: una firma piu'' ordinata non vale la ricostruzione della catena di chi chiama, e appeso in fondo con un DEFAULT ogni chiamata POSIZIONALE esistente continua a funzionare identica. La posizione serve ai chiamanti, non alla logica. ⚠️ E'' comunque un DROP + CREATE: aggiungere un parametro crea un OVERLOAD, non sostituisce, e con otto parametri opzionali le due firme renderebbero ambigua ogni chiamata. La RETURNS TABLE non cambia. Rev 2026-10-20 (20261020-63, brief-db-grammatica-unica-documenti 2d, G-6): sorgente_area diventa sorgente_apribile (config.sorgenti.apribile): il documento d''origine si apre dal codice della sorgente (sorgente_codice), non piu'' dal plurale. Firma e RETURNS TABLE con %TYPE. Rev 2026-10-21 (20261021-20, brief-db-grammatica-unica-documenti, G-1): sorgente_codice esce, perche'' era config.sorgenti.codice, il nome che l''operatore puo'' cambiare. Il documento d''origine si apre da `sorgente_codice_interno`, il nome del tipo, l''unico protetto dal lock; la lista mostra `sorgente_etichetta` (in coda alla RETURNS TABLE), che e'' anche la chiave di ordinamento della colonna «Tipo origine».';
```

</div>

---
{% include-markdown "signature-core.md" %}
