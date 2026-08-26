# ⚙️ Funzione `fn_lookup_registro_id`

```sql
CREATE FUNCTION fn_lookup_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_lookup_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(natura_doc_id bigint, registro_id bigint, serie character varying, politica_data_documento character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_natura_doc_id config.nature_doc_fiscale.id%TYPE;
    v_registro_id   vendite.registri_fatturazione.id%TYPE;
    v_serie         vendite.tipi_doc_fiscale_registri.serie%TYPE;
    v_politica      vendite.registri_fatturazione.politica_data_documento%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   CERCARE il registro di numerazione e la serie, e basta.
    --   Chi non trova risponde NULL: qui non si solleva mai.
    --
    -- ⛔ Il guard di parametro e il raise NON stanno qui: sono
    --   in vendite.fn_get_registro_id, che e' l'involucro per
    --   chi SCRIVE. Questa funzione serve anche chi LEGGE — le
    --   viste della dashboard di competenza — dove un tipo
    --   documento nullo e' uno stato ammesso dal CHECK, non un
    --   guasto.
    -- =========================================================

    -- Default della natura risolto per chiave naturale, mai un
    -- id cablato: l'id e' dettaglio implementativo, il
    -- codice_interno e' il contratto (linee-guida-sql §6b).
    -- ⚠️ Esce nel risultato: e' cosi' che l'involucro distingue
    --    «natura non risolta» da «registro non trovato» senza
    --    rifare questo COALESCE per conto proprio.
    v_natura_doc_id := COALESCE(
        p_natura_doc_id,
        config.fn_get_natura_doc_fiscale_id('FATTURA'));

    -- Ricerca con fallback: tipo_doc+utility+emittente →
    -- tipo_doc+utility → tipo_doc+emittente → tipo_doc.
    -- ⚠️ Il fallback e' la gerarchia di specificita' del
    --    REGISTRO (utility/emittente). La NATURA invece e' un
    --    filtro ESATTO: non esiste un «registro della natura
    --    piu' vicina», e ripiegare sulla fattura emetterebbe una
    --    nota di credito nel registro sbagliato, in silenzio.
    -- ℹ️ Con p_tipo_doc_fiscale_id o v_natura_doc_id a NULL il
    --    predicato non corrisponde a nulla e v_registro_id resta
    --    NULL: e' il comportamento voluto, non un caso da
    --    intercettare.
    -- ⭐ `politica_data_documento` esce da QUI e non da una
    --    seconda lettura del chiamante: il JOIN su
    --    registri_fatturazione c'e' gia', quindi restituirla non
    --    e' lavoro in piu' — e' restituire cio' che si e' gia'
    --    letto. Una seconda SELECT per PK sulla stessa riga
    --    sarebbe la lettura duplicata che il progetto evita.
    SELECT r.id, m.serie, r.politica_data_documento
      INTO v_registro_id, v_serie, v_politica
      FROM vendite.tipi_doc_fiscale_registri m
      JOIN vendite.registri_fatturazione r ON r.id = m.registro_id
     WHERE m.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id
       AND m.natura_doc_id = v_natura_doc_id
       AND (r.utility_id IS NULL OR r.utility_id = p_utility_id)
       AND (r.emittente_soggetto_ruolo_id IS NULL OR r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
     ORDER BY
         CASE
             WHEN r.utility_id = p_utility_id AND r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id THEN 1
             WHEN r.utility_id = p_utility_id AND r.emittente_soggetto_ruolo_id IS NULL THEN 2
             WHEN r.utility_id IS NULL AND r.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id THEN 3
             WHEN r.utility_id IS NULL AND r.emittente_soggetto_ruolo_id IS NULL THEN 4
             ELSE 9
         END, r.id
     LIMIT 1;

    -- ⚠️ `serie` esce GREZZA (l'override del mapping), non
    --    COALESCE-ata sul serie_default del registro: scrivere
    --    il default dentro vendite.fatture.serie cambierebbe il
    --    valore di una colonna su documenti gia' emessi, dove
    --    oggi c'e' NULL. NULL qui continua a voler dire «vale il
    --    default del registro», che fn_assign_numero_fattura
    --    risolve gia' da se'.
    -- ⭐ UNA riga sempre, anche tutta a NULL.
    RETURN QUERY SELECT v_natura_doc_id, v_registro_id, v_serie, v_politica;
END;
$function$

COMMENT ON FUNCTION vendite.fn_lookup_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
IS 'CERCA il registro di numerazione e la serie per (tipo documento, natura), con utility ed emittente a raffinare — e NON solleva mai. E'' il lettore puro di cui vendite.fn_get_registro_id e'' l''involucro: stessa coppia, e stessa ragione, di script.fn_get_ba_emittente_sr_id (lettore) e anagrafiche.fn_get_emittente_fiscale_id (involucro che solleva). ⛔ Esiste perche'' le viste della dashboard di competenza mostrano una PREVISIONE del sezionale, e una previsione non puo'' far morire la lista che decora: chk_commesse_attivita_tipo_doc_emittibile pretende il tipo documento SOLO su una riga APPROVATA e NON_EMESSA, quindi su uno stadio DA_APPROVARE il NULL e'' ammesso — e li'' l''involucro solleverebbe, con l''intera lista che risponde 500 e una riga in error_log a ogni tentativo. ⭐ Torna anche la POLITICA DELLA DATA del registro, e non e'' lavoro in piu'': il JOIN su registri_fatturazione c''e'' gia'', quindi e'' restituire cio'' che si e'' gia'' letto invece di far rifare al chiamante una SELECT per PK sulla stessa riga. ⭐ Torna SEMPRE una riga, anche tutta a NULL, e porta con se'' la NATURA risolta: e'' cosi'' che l''involucro distingue «natura non risolta» da «registro non trovato» senza rifare il COALESCE per conto proprio, cioe'' senza riaprire la duplicazione da un''altra parte. ⛔ Nessun guard di parametro: un tipo documento nullo non trova e basta. La gerarchia di specificita'' a quattro livelli (utility+emittente, utility, emittente, nessuno) e il filtro ESATTO sulla natura sono copiati invariati da fn_get_registro_id; la serie esce GREZZA (NULL = vale il serie_default del registro). ℹ️ STABLE, e onestamente: legge tre tabelle e config.fn_get_natura_doc_fiscale_id, STABLE a sua volta. Serve perche'' la funzione finisce nel target list di vw_dash_competenza_attivita, base di altre quattro viste: da VOLATILE il planner non potrebbe potarla dai consumatori che le colonne nuove non le guardano. Piano: brief-db-registro-e-data-prevista-in-competenza, DB-0.';
```

---
{% include-markdown "signature-core.md" %}
