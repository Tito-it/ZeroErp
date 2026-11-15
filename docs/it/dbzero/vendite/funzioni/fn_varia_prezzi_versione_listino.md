{% include-markdown "it/dbzero/vendite/manual/fn_varia_prezzi_versione_listino.md" %}
# ⚙️ Funzione `fn_varia_prezzi_versione_listino`

```sql
CREATE FUNCTION fn_varia_prezzi_versione_listino(p_listino_versione_id bigint, p_variazione_pct numeric, p_decimali integer, p_filtro_articoli uuid[], p_dry_run boolean)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_varia_prezzi_versione_listino(p_listino_versione_id bigint, p_variazione_pct numeric, p_decimali integer, p_filtro_articoli uuid[] DEFAULT NULL::uuid[], p_dry_run boolean DEFAULT false)
 RETURNS TABLE(listino_riga_id bigint, articolo_id uuid, articolo_codice character varying, articolo_descrizione character varying, prezzo_precedente numeric, prezzo_nuovo numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_utente  config.user_override_azioni.auth_user_id%TYPE;
    v_tx_id   vendite.listini_versioni.tx_id%TYPE;
    -- Tipo esplicito: un conteggio di righe.
    v_n       integer;
    -- Gli intervalli: una costante sola, letta dal controllo e dal
    --   messaggio.
    c_pct_min CONSTANT numeric := -99;
    c_pct_max CONSTANT numeric := 1000;
    c_dec_min CONSTANT integer := 0;
    c_dec_max CONSTANT integer := 10;
BEGIN
    -- ==========================================================
    -- Scopo: variare in percentuale i prezzi delle righe attive di
    --   una versione di listino (tutte, o quelle degli articoli del
    --   filtro), o mostrarne l'anteprima. Si fa solo in bozza, e lo
    --   dice la versione, non le righe che il gesto prende. Vedi
    --   l'intestazione del changeSet 20261115-79.
    -- ==========================================================
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_listino_versione_id IS NULL OR p_listino_versione_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_varia_prezzi_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_listino_versione_id', p_listino_versione_id),
            NULL::uuid, 'vendite.fn_varia_prezzi_versione_listino',
            'p_listino_versione_id (obbligatorio, maggiore di zero)');
    END IF;
    IF p_variazione_pct IS NULL OR p_decimali IS NULL OR p_dry_run IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_varia_prezzi_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_listino_versione_id', p_listino_versione_id,
                               'p_variazione_pct', p_variazione_pct,
                               'p_decimali', p_decimali, 'p_dry_run', p_dry_run),
            NULL::uuid, 'vendite.fn_varia_prezzi_versione_listino',
            'p_variazione_pct, p_decimali e p_dry_run (obbligatori)');
    END IF;

    -- 2. La versione, nel perimetro. Nel gesto vero FOR UPDATE: fra la
    --    check e la scrittura la versione non cambia stato.
    IF p_dry_run THEN
        SELECT lv.tx_id INTO v_tx_id
          FROM vendite.listini_versioni lv
         WHERE lv.id = p_listino_versione_id
           AND script.fn_scope_ef_whitelist_via_listino_versione(v_utente, lv.id);
    ELSE
        SELECT lv.tx_id INTO v_tx_id
          FROM vendite.listini_versioni lv
         WHERE lv.id = p_listino_versione_id
           AND script.fn_scope_ef_whitelist_via_listino_versione(v_utente, lv.id)
           FOR UPDATE OF lv;
    END IF;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_varia_prezzi_versione_listino',
            'E_VENDITE_LISTINO_VERSIONE_NOT_FOUND',
            -- Frase chiusa: nessun segnaposto, il variadico vuoto e' esplicito.
            jsonb_build_object('id', p_listino_versione_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 3. Prima cio' che vieta: il primo motivo della check della
    --    versione, senza riga, come la superficie. Anche
    --    nell'anteprima.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_varia_prezzi_versione_listino',
        script.fn_check_listino_riga_scrivibile(p_listino_versione_id, NULL, 'UPDATE'),
        NULL,
        v_tx_id,
        jsonb_build_object('listino_versione_id', p_listino_versione_id,
                           'variazione_pct', p_variazione_pct,
                           'dry_run', p_dry_run));

    -- 4. Gli intervalli. Il campo da correggere ha il nome del
    --    parametro dell'endpoint: esce nel canale COLUMN.
    IF p_variazione_pct < c_pct_min OR p_variazione_pct > c_pct_max
       OR p_decimali < c_dec_min OR p_decimali > c_dec_max THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_varia_prezzi_versione_listino',
            'E_LISTINO_VARIAZIONE_FUORI_INTERVALLO',
            jsonb_build_object('campo', CASE WHEN p_variazione_pct BETWEEN c_pct_min AND c_pct_max
                                             THEN 'arrotondamento_decimali'
                                             ELSE 'variazione_percentuale' END,
                               'listino_versione_id', p_listino_versione_id,
                               'variazione_pct', p_variazione_pct,
                               'decimali', p_decimali),
            v_tx_id,
            c_pct_min::text, c_pct_max::text, c_dec_min::text, c_dec_max::text);
    END IF;

    -- 5. Il prezzo nuovo, calcolato in un posto solo: l'anteprima lo
    --    restituisce, il gesto lo scrive (il guard delle righe, in
    --    bozza, passa) e restituisce il prezzo salvato, alla scala
    --    della colonna. Prezzo negativo: il CHECK della tabella.
    RETURN QUERY
    WITH calc AS (
        SELECT r.id                                                   AS riga_id,
               r.articolo_id                                          AS art_id,
               a.codice                                               AS art_codice,
               a.descrizione                                          AS art_descrizione,
               r.prezzo                                               AS prima,
               round(r.prezzo * (1 + p_variazione_pct / 100), p_decimali) AS dopo
          FROM vendite.listini_righe r
          JOIN catalogo.articoli a ON a.id = r.articolo_id
         WHERE r.listino_versione_id = p_listino_versione_id
           AND r.attivo
           AND (p_filtro_articoli IS NULL OR r.articolo_id = ANY (p_filtro_articoli))
    ), scritte AS (
        UPDATE vendite.listini_righe lr
           SET prezzo = c.dopo
          FROM calc c
         WHERE lr.id = c.riga_id
           AND NOT p_dry_run
        RETURNING lr.id AS riga_id, lr.prezzo AS salvato
    )
    SELECT c.riga_id, c.art_id, c.art_codice, c.art_descrizione, c.prima,
           COALESCE(s.salvato, c.dopo)
      FROM calc c
      LEFT JOIN scritte s ON s.riga_id = c.riga_id
     ORDER BY c.art_codice, c.riga_id;
    GET DIAGNOSTICS v_n = ROW_COUNT;

    -- 6. La traccia del gesto, anche a righe zero.
    IF NOT p_dry_run THEN
        UPDATE vendite.listini_versioni lv
           SET meta = jsonb_set(
                          lv.meta, '{variazioni_percentuali}',
                          COALESCE(lv.meta -> 'variazioni_percentuali', '[]'::jsonb)
                          || jsonb_build_array(jsonb_build_object(
                                 'data',                    now(),
                                 'operatore',               v_utente,
                                 'variazione_percentuale',  p_variazione_pct::text,
                                 'arrotondamento_decimali', p_decimali,
                                 'righe_aggiornate',        v_n,
                                 'filtro_articoli',         to_jsonb(p_filtro_articoli))))
         WHERE lv.id = p_listino_versione_id;
    END IF;
END;
$function$

COMMENT ON FUNCTION vendite.fn_varia_prezzi_versione_listino(p_listino_versione_id bigint, p_variazione_pct numeric, p_decimali integer, p_filtro_articoli uuid[], p_dry_run boolean)
IS 'VERBO «Variazione %» di una versione di listino: varia in percentuale i prezzi delle righe attive della versione (tutte, o quelle degli articoli di p_filtro_articoli; un array vuoto non prende righe), arrotondati a p_decimali, o con p_dry_run ne mostra l''anteprima senza scrivere. Si fa solo in bozza, e lo dice la versione, non le righe che il gesto prende: anche a righe zero. La versione nel perimetro (script.fn_scope_ef_whitelist_via_listino_versione: DEFINER, la RLS non c''e''; FOR UPDATE nel gesto vero; non trovata o fuori perimetro E_VENDITE_LISTINO_VERSIONE_NOT_FOUND; parametri mancanti E_VENDITE_CHIAMATA_NON_VALIDA); prima cio'' che vieta, anche nell''anteprima: il primo motivo di script.fn_check_listino_riga_scrivibile della versione senza riga, lo stesso della superficie vendite.vw_listini_versioni_azioni (variazione_blocco_*): CHIUSA E_RIGA_LISTINO_VERSIONE_CHIUSA, fuori dalla bozza E_RIGA_LISTINO_VERSIONE_NON_IN_BOZZA; poi gli intervalli, la percentuale da -99 a 1000 e i decimali da 0 a 10 (E_LISTINO_VARIAZIONE_FUORI_INTERVALLO). Il prezzo nuovo e'' round(prezzo * (1 + p_variazione_pct / 100), p_decimali), calcolato in un posto solo; prezzo negativo: il CHECK chk_listini_righe_prezzo. Ritorna una riga per riga presa (riga, articolo, codice e descrizione dell''articolo, prezzo di prima, prezzo nuovo: salvato, alla scala della colonna, nel gesto vero), per codice articolo. Il gesto vero appende a meta.variazioni_percentuali[] della versione la traccia (data, operatore = app.current_user_id, variazione_percentuale, arrotondamento_decimali, righe_aggiornate, filtro_articoli), anche a righe zero. E'' il verbo dell''azione VARIA_PREZZI_LISTINO nel registro config.azioni_riga. Prende il posto dell''UPDATE e della traccia del backend (listini_service.fn_applica_variazione_percentuale, sviluppo-listini-v3 N8a). Il permesso d''area resta al backend. SECURITY DEFINER con search_path bloccato; EXECUTE solo all''applicazione.';
```

</div>

---
{% include-markdown "signature-core.md" %}
