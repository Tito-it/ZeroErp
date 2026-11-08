{% include-markdown "it/dbzero/magazzino/manual/fn_scrivi_movimento.md" %}
# ⚙️ Funzione `fn_scrivi_movimento`

```sql
CREATE FUNCTION fn_scrivi_movimento(p_magazzino_id bigint, p_articolo_id uuid, p_causale character varying, p_qta numeric, p_sorgente_tipo_id bigint, p_sorgente_riga bigint, p_sorgente_uid uuid, p_costo_unitario numeric, p_lotto_id bigint, p_asset_id bigint, p_ubicazione_id bigint, p_data_mov timestamp with time zone, p_transfer_uid uuid, p_storno_di_movimento_id bigint, p_meta jsonb, p_sorgente_id bigint, p_sorgente_dettaglio bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_scrivi_movimento(p_magazzino_id bigint, p_articolo_id uuid, p_causale character varying, p_qta numeric, p_sorgente_tipo_id bigint, p_sorgente_riga bigint DEFAULT NULL::bigint, p_sorgente_uid uuid DEFAULT NULL::uuid, p_costo_unitario numeric DEFAULT NULL::numeric, p_lotto_id bigint DEFAULT NULL::bigint, p_asset_id bigint DEFAULT NULL::bigint, p_ubicazione_id bigint DEFAULT NULL::bigint, p_data_mov timestamp with time zone DEFAULT now(), p_transfer_uid uuid DEFAULT NULL::uuid, p_storno_di_movimento_id bigint DEFAULT NULL::bigint, p_meta jsonb DEFAULT '{}'::jsonb, p_sorgente_id bigint DEFAULT NULL::bigint, p_sorgente_dettaglio bigint DEFAULT NULL::bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: l'UNICA funzione che scrive su magazzino.movimenti (M-2, D-L2-b):
--   tutti i controlli duri nell'ordine del contratto, poi l'INSERT e la
--   copia del valore. Le operazioni (inventario, rettifica) non
--   ricontrollano niente e la chiamano in UNA transazione. Riceve qta
--   FIRMATA in UoM base (D-L2-a, D-L1-a: non converte) e la sorgente a
--   catalogo nella grammatica del modello: il tipo del documento, UNA chiave
--   del documento (sorgente_id | sorgente_uid), la riga e il dettaglio (la
--   foglia piu' bassa del tipo: lo pretende il guard unico, livello minimo
--   DETTAGLIO). Ritorna l'id del movimento.
-- Regole: vedi l'intestazione del changeSet e il COMMENT (i quattordici passi).
DECLARE
    v_causale_id        magazzino.causali.id%TYPE;
    v_segno             magazzino.causali.segno%TYPE;
    v_is_rettifica      magazzino.causali.is_rettifica%TYPE;
    v_stock_negativo    magazzino.causali.consente_stock_negativo%TYPE;
    v_mag_codice        magazzino.magazzini.codice%TYPE;
    v_motivi            jsonb;
    v_orig              magazzino.movimenti%ROWTYPE;
    v_storno_esistente  magazzino.movimenti.id%TYPE;
    v_seriale           magazzino.assets.seriale%TYPE;
    v_pos_qta           magazzino.movimenti.qta%TYPE;
    v_pos_mag_id        magazzino.movimenti.magazzino_id%TYPE;
    v_pos_mag_codice    magazzino.magazzini.codice%TYPE;
    v_esistente         magazzino.movimenti.id%TYPE;
    v_costo             magazzino.movimenti.costo_unitario%TYPE;
    v_media             magazzino.vw_costo_medio.costo_medio%TYPE;
    v_movimento_id      magazzino.movimenti.id%TYPE;
    v_contributo        magazzino.valore_giacenza.valore%TYPE;
    v_ctx               jsonb;
BEGIN
    -- ============================================================
    -- 1. Parametri: solo forme che nessuna interfaccia produce.
    -- ============================================================
    IF p_magazzino_id IS NULL OR p_magazzino_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'magazzino obbligatorio e maggiore di zero', 'p_magazzino_id', p_magazzino_id),
            NULL::uuid, 'magazzino.fn_scrivi_movimento', 'p_magazzino_id (obbligatorio, maggiore di zero)');
    END IF;
    IF p_articolo_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'articolo obbligatorio'),
            NULL::uuid, 'magazzino.fn_scrivi_movimento', 'p_articolo_id (obbligatorio)');
    END IF;
    IF p_causale IS NULL OR btrim(p_causale) = '' THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'causale (codice_interno) obbligatoria', 'p_causale', p_causale),
            NULL::uuid, 'magazzino.fn_scrivi_movimento', 'p_causale (obbligatoria: il codice_interno della causale)');
    END IF;
    IF p_qta IS NULL OR p_qta = 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'quantita'' firmata, diversa da zero', 'p_qta', p_qta),
            NULL::uuid, 'magazzino.fn_scrivi_movimento', 'p_qta (obbligatoria, diversa da zero: firmata, in UoM base)');
    END IF;
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'sorgente a catalogo obbligatoria (D-1)', 'p_sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid, 'magazzino.fn_scrivi_movimento', 'p_sorgente_tipo_id (obbligatorio, maggiore di zero)');
    END IF;
    IF num_nonnulls(p_sorgente_id, p_sorgente_uid) <> 1
       OR (p_sorgente_dettaglio IS NOT NULL AND p_sorgente_riga IS NULL) THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'una sola chiave del documento (id o uid); il dettaglio con la sua riga',
                               'p_sorgente_id', p_sorgente_id, 'p_sorgente_uid', p_sorgente_uid,
                               'p_sorgente_riga', p_sorgente_riga, 'p_sorgente_dettaglio', p_sorgente_dettaglio),
            NULL::uuid, 'magazzino.fn_scrivi_movimento',
            'p_sorgente_id / p_sorgente_uid (esattamente una), p_sorgente_dettaglio (solo con p_sorgente_riga)');
    END IF;
    IF (p_sorgente_id IS NOT NULL AND p_sorgente_id <= 0)
       OR (p_sorgente_riga IS NOT NULL AND p_sorgente_riga <= 0)
       OR (p_sorgente_dettaglio IS NOT NULL AND p_sorgente_dettaglio <= 0)
       OR (p_lotto_id IS NOT NULL AND p_lotto_id <= 0)
       OR (p_asset_id IS NOT NULL AND p_asset_id <= 0)
       OR (p_ubicazione_id IS NOT NULL AND p_ubicazione_id <= 0)
       OR (p_storno_di_movimento_id IS NOT NULL AND p_storno_di_movimento_id <= 0) THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'un identificativo passato vale zero o meno',
                               'p_sorgente_id', p_sorgente_id, 'p_sorgente_riga', p_sorgente_riga,
                               'p_sorgente_dettaglio', p_sorgente_dettaglio, 'p_lotto_id', p_lotto_id,
                               'p_asset_id', p_asset_id, 'p_ubicazione_id', p_ubicazione_id,
                               'p_storno_di_movimento_id', p_storno_di_movimento_id),
            NULL::uuid, 'magazzino.fn_scrivi_movimento',
            'p_sorgente_id / p_sorgente_riga / p_sorgente_dettaglio / p_lotto_id / p_asset_id / p_ubicazione_id / p_storno_di_movimento_id (se passati, maggiori di zero)');
    END IF;
    IF p_costo_unitario IS NOT NULL AND p_costo_unitario < 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'costo unitario negativo', 'p_costo_unitario', p_costo_unitario),
            NULL::uuid, 'magazzino.fn_scrivi_movimento', 'p_costo_unitario (se passato, maggiore o uguale a zero)');
    END IF;

    -- ============================================================
    -- 2. La causale, per codice_interno (mai per id), attiva.
    -- ============================================================
    SELECT c.id, c.segno, c.is_rettifica, c.consente_stock_negativo
      INTO v_causale_id, v_segno, v_is_rettifica, v_stock_negativo
      FROM magazzino.causali c
     WHERE c.codice_interno = p_causale
       AND c.attivo;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'magazzino.causali.' || p_causale, 'causale', p_causale),
            NULL::uuid,
            VARIADIC ARRAY['causale di magazzino ' || p_causale || ' (magazzino.causali, attiva)']);
    END IF;

    -- ============================================================
    -- 3. Il verso sta nella quantita' (M-1): la madre da' la frase,
    --    trgfn_movimenti_guard_verso resta la rete.
    -- ============================================================
    IF sign(p_qta) <> v_segno THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_MOVIMENTO_VERSO_INCOERENTE',
            jsonb_build_object('detail', 'sign(qta) diverso da causali.segno',
                               'causale', p_causale, 'segno', v_segno, 'qta', p_qta),
            NULL::uuid,
            p_causale, v_segno::text, trim_scale(p_qta)::text);
    END IF;

    -- ============================================================
    -- 4. Il magazzino: esiste ed e' attivo (DEFINER: «esiste», non «lo vedo»).
    -- ============================================================
    SELECT m.codice INTO v_mag_codice
      FROM magazzino.magazzini m
     WHERE m.id = p_magazzino_id
       AND m.attivo;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_MAGAZZINO_NON_VALIDO',
            jsonb_build_object('detail', 'magazzino inesistente o non attivo', 'magazzino_id', p_magazzino_id),
            NULL::uuid, p_magazzino_id::text);
    END IF;

    -- ============================================================
    -- 5-8. La riga: articolo, lotto, seriale, ubicazione — una sede
    --      (fn_check_riga_magazzino, C8); si solleva il PRIMO motivo.
    -- ============================================================
    v_ctx := jsonb_build_object('magazzino_id', p_magazzino_id, 'articolo_id', p_articolo_id,
                                'causale', p_causale, 'qta', p_qta);
    v_motivi := script.fn_check_riga_magazzino(p_magazzino_id, p_articolo_id,
                                               p_lotto_id, p_asset_id, p_ubicazione_id);
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'magazzino', 'magazzino.fn_scrivi_movimento', v_motivi, NULL, NULL::uuid, v_ctx);

    -- ============================================================
    -- 9. Lo storno: lo specchio esatto dell'originale (M-8, D-L1-d).
    -- ============================================================
    IF p_storno_di_movimento_id IS NOT NULL THEN
        SELECT * INTO v_orig
          FROM magazzino.movimenti o
         WHERE o.id = p_storno_di_movimento_id;
        IF NOT FOUND THEN
            PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                'E_MAG_STORNO_INCOERENTE',
                jsonb_build_object('detail', 'movimento originale inesistente',
                                   'storno_di_movimento_id', p_storno_di_movimento_id),
                NULL::uuid, p_storno_di_movimento_id::text, 'il movimento originale non esiste');
        END IF;
        IF v_orig.articolo_id <> p_articolo_id OR v_orig.magazzino_id <> p_magazzino_id
           OR p_qta <> -v_orig.qta
           OR p_causale NOT IN ('STORNO_POS', 'STORNO_NEG')
           OR v_orig.sorgente_tipo_id <> p_sorgente_tipo_id
           OR v_orig.sorgente_id        IS DISTINCT FROM p_sorgente_id
           OR v_orig.sorgente_uid       IS DISTINCT FROM p_sorgente_uid
           OR v_orig.sorgente_riga      IS DISTINCT FROM p_sorgente_riga
           OR v_orig.sorgente_dettaglio IS DISTINCT FROM p_sorgente_dettaglio
           OR v_orig.lotto_id      IS DISTINCT FROM p_lotto_id
           OR v_orig.asset_id      IS DISTINCT FROM p_asset_id
           OR v_orig.ubicazione_id IS DISTINCT FROM p_ubicazione_id THEN
            PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                'E_MAG_STORNO_INCOERENTE',
                jsonb_build_object('detail', 'lo storno non rispecchia l''originale',
                                   'storno_di_movimento_id', p_storno_di_movimento_id,
                                   'originale', jsonb_build_object('articolo_id', v_orig.articolo_id,
                                       'magazzino_id', v_orig.magazzino_id, 'qta', v_orig.qta,
                                       'sorgente_tipo_id', v_orig.sorgente_tipo_id,
                                       'sorgente_id', v_orig.sorgente_id, 'sorgente_uid', v_orig.sorgente_uid,
                                       'sorgente_riga', v_orig.sorgente_riga,
                                       'sorgente_dettaglio', v_orig.sorgente_dettaglio,
                                       'lotto_id', v_orig.lotto_id, 'asset_id', v_orig.asset_id,
                                       'ubicazione_id', v_orig.ubicazione_id),
                                   'ricevuto', jsonb_build_object('articolo_id', p_articolo_id,
                                       'magazzino_id', p_magazzino_id, 'qta', p_qta, 'causale', p_causale,
                                       'sorgente_tipo_id', p_sorgente_tipo_id,
                                       'sorgente_id', p_sorgente_id, 'sorgente_uid', p_sorgente_uid,
                                       'sorgente_riga', p_sorgente_riga,
                                       'sorgente_dettaglio', p_sorgente_dettaglio,
                                       'lotto_id', p_lotto_id, 'asset_id', p_asset_id,
                                       'ubicazione_id', p_ubicazione_id)),
                NULL::uuid, p_storno_di_movimento_id::text,
                'stesso articolo e magazzino, quantita'' opposta, causale STORNO_POS/STORNO_NEG, stessa sorgente e stessa posizione (lotto, seriale, ubicazione) dell''originale');
        END IF;
        SELECT s.id INTO v_storno_esistente
          FROM magazzino.movimenti s
         WHERE s.storno_di_movimento_id = p_storno_di_movimento_id;
        IF FOUND THEN
            PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                'E_MAG_STORNO_INCOERENTE',
                jsonb_build_object('detail', 'movimento gia'' stornato',
                                   'storno_di_movimento_id', p_storno_di_movimento_id,
                                   'storno_esistente_id', v_storno_esistente),
                NULL::uuid, p_storno_di_movimento_id::text,
                'e'' gia'' stato stornato dal movimento ' || v_storno_esistente::text);
        END IF;
        IF p_costo_unitario IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                'E_MAG_COSTO_NON_AMMESSO',
                jsonb_build_object('detail', 'uno storno va al costo dell''originale',
                                   'caso', 'storno', 'p_costo_unitario', p_costo_unitario),
                NULL::uuid, 'storno');
        END IF;
    END IF;

    -- ============================================================
    -- 9-bis. La posizione del seriale si DERIVA dal registro e si difende
    --        alla scrittura (D-L2-e): in entrata non e' dentro da nessuna
    --        parte (somma su tutti i magazzini, che sono dell'emittente per
    --        costruzione: il passo 7 l'ha gia' verificato); in uscita e' qui.
    -- ============================================================
    IF p_asset_id IS NOT NULL THEN
        SELECT s.seriale INTO v_seriale FROM magazzino.assets s WHERE s.id = p_asset_id;
        IF v_segno = 1 THEN
            SELECT m.magazzino_id, sum(m.qta) INTO v_pos_mag_id, v_pos_qta
              FROM magazzino.movimenti m
             WHERE m.asset_id = p_asset_id
             GROUP BY m.magazzino_id
            HAVING sum(m.qta) <> 0
             ORDER BY sum(m.qta) DESC, m.magazzino_id
             LIMIT 1;
            IF FOUND THEN
                SELECT mg.codice INTO v_pos_mag_codice FROM magazzino.magazzini mg WHERE mg.id = v_pos_mag_id;
                PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                    'E_MAG_ASSET_POSIZIONE_INCOERENTE',
                    jsonb_build_object('detail', 'entrata di un seriale che risulta gia'' dentro un magazzino',
                                       'asset_id', p_asset_id, 'magazzino_id', p_magazzino_id,
                                       'posizione_magazzino_id', v_pos_mag_id, 'posizione_qta', v_pos_qta),
                    NULL::uuid,
                    COALESCE(v_seriale, p_asset_id::text),
                    'gia'' presente nel magazzino ' || COALESCE(v_pos_mag_codice, v_pos_mag_id::text));
            END IF;
        ELSE
            SELECT COALESCE(sum(m.qta), 0) INTO v_pos_qta
              FROM magazzino.movimenti m
             WHERE m.asset_id = p_asset_id
               AND m.magazzino_id = p_magazzino_id;
            IF v_pos_qta <> 1 THEN
                PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                    'E_MAG_ASSET_POSIZIONE_INCOERENTE',
                    jsonb_build_object('detail', 'uscita di un seriale che non risulta in questo magazzino',
                                       'asset_id', p_asset_id, 'magazzino_id', p_magazzino_id,
                                       'posizione_qta', v_pos_qta),
                    NULL::uuid,
                    COALESCE(v_seriale, p_asset_id::text),
                    'assente dal magazzino ' || v_mag_codice);
            END IF;
        END IF;
    END IF;

    -- ============================================================
    -- 10. L'identita' (D-4, D-L1-c): la madre da' la frase, il UNIQUE
    --     (uq_mag_movimenti_identita, NULLS NOT DISTINCT) resta la rete.
    -- ============================================================
    SELECT m.id INTO v_esistente
      FROM magazzino.movimenti m
     WHERE (m.sorgente_tipo_id, m.sorgente_id, m.sorgente_uid, m.sorgente_riga,
            m.sorgente_dettaglio, m.causale_id, m.asset_id, m.lotto_id, m.ubicazione_id)
           IS NOT DISTINCT FROM
           (p_sorgente_tipo_id, p_sorgente_id, p_sorgente_uid, p_sorgente_riga,
            p_sorgente_dettaglio, v_causale_id, p_asset_id, p_lotto_id, p_ubicazione_id);
    IF FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
            'E_MAG_MOVIMENTO_GIA_REGISTRATO',
            v_ctx || jsonb_build_object('detail', 'stessa identita'' gia'' a registro',
                                        'movimento_id', v_esistente),
            NULL::uuid, v_esistente::text);
    END IF;

    -- ============================================================
    -- 11. SOLO in uscita: il lock (magazzino, articolo), poi la
    --     disponibilita' — la stessa funzione che la UI chiama.
    -- ============================================================
    IF v_segno = -1 THEN
        PERFORM pg_advisory_xact_lock(
            hashtext('magazzino.fn_scrivi_movimento'),
            hashtext(p_magazzino_id::text || ':' || p_articolo_id::text));

        IF NOT v_stock_negativo THEN
            v_motivi := script.fn_check_disponibilita_uscita(
                p_magazzino_id, p_articolo_id, abs(p_qta),
                p_sorgente_tipo_id, p_sorgente_riga, p_sorgente_uid,
                p_lotto_id, p_asset_id,
                v_is_rettifica,      -- il fatto vince sulla promessa (D-L2-d)
                p_sorgente_id, p_sorgente_dettaglio);
            PERFORM script.fn_raise_primo_motivo_se_presente(
                'magazzino', 'magazzino.fn_scrivi_movimento', v_motivi, NULL, NULL::uuid, v_ctx);
        END IF;
    END IF;

    -- ============================================================
    -- 12. Il costo, per STRUTTURA (D-L2-c), nell'ordine in cui i casi si
    --     escludono. La media corrente si legge DENTRO il lock (C6).
    -- ============================================================
    IF p_storno_di_movimento_id IS NOT NULL THEN
        v_costo := v_orig.costo_unitario;
    ELSIF p_transfer_uid IS NOT NULL AND v_segno = 1 THEN
        IF p_costo_unitario IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                'E_MAG_COSTO_NON_AMMESSO',
                jsonb_build_object('detail', 'l''entrata gemella va al costo della OUT',
                                   'caso', 'entrata gemella', 'p_costo_unitario', p_costo_unitario),
                NULL::uuid, 'entrata gemella di un trasferimento');
        END IF;
        SELECT o.costo_unitario INTO v_costo
          FROM magazzino.movimenti o
         WHERE o.transfer_uid = p_transfer_uid
           AND o.articolo_id  = p_articolo_id
           AND o.qta < 0
         ORDER BY o.id
         LIMIT 1;
        IF NOT FOUND THEN
            PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                'E_MAG_GEMELLA_NON_TROVATA',
                jsonb_build_object('detail', 'nessuna OUT con questo transfer_uid per l''articolo',
                                   'transfer_uid', p_transfer_uid, 'articolo_id', p_articolo_id),
                NULL::uuid, p_transfer_uid::text);
        END IF;
    ELSIF v_segno = -1 THEN
        IF p_costo_unitario IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_scrivi_movimento',
                'E_MAG_COSTO_NON_AMMESSO',
                jsonb_build_object('detail', 'un''uscita va alla media corrente',
                                   'caso', 'uscita', 'p_costo_unitario', p_costo_unitario),
                NULL::uuid, 'uscita');
        END IF;
        SELECT cm.costo_medio INTO v_media
          FROM magazzino.vw_costo_medio cm
         WHERE cm.magazzino_id = p_magazzino_id
           AND cm.articolo_id  = p_articolo_id;
        v_costo := v_media;              -- NULL se giacenza <= 0 o senza valore
    ELSE
        SELECT cm.costo_medio INTO v_media
          FROM magazzino.vw_costo_medio cm
         WHERE cm.magazzino_id = p_magazzino_id
           AND cm.articolo_id  = p_articolo_id;
        v_costo := COALESCE(p_costo_unitario, v_media);
    END IF;
    v_costo := round(v_costo, 6);        -- il costo scritto e'' quello che vale (C7)

    -- ============================================================
    -- 13. Il movimento. I trigger del Lotto 1 (scope, sorgente
    --     unico della provenienza, verso, tx_id, audit, storico) restano
    --     la rete.
    -- ============================================================
    INSERT INTO magazzino.movimenti
        (articolo_id, magazzino_id, qta, costo_unitario, data_mov, causale_id, meta,
         transfer_uid, sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga,
         sorgente_dettaglio, lotto_id, asset_id, ubicazione_id, storno_di_movimento_id)
    VALUES
        (p_articolo_id, p_magazzino_id, p_qta, v_costo, COALESCE(p_data_mov, now()), v_causale_id,
         COALESCE(p_meta, '{}'::jsonb),
         p_transfer_uid, p_sorgente_tipo_id, p_sorgente_id, p_sorgente_uid, p_sorgente_riga,
         p_sorgente_dettaglio, p_lotto_id, p_asset_id, p_ubicazione_id, p_storno_di_movimento_id)
    RETURNING id INTO v_movimento_id;

    -- ============================================================
    -- 14. La copia del valore (M-4): += round(qta * costo, 6); costo NULL
    --     contribuisce zero. La riga nasce anche a contributo zero, cosi'
    --     «giacenza con movimenti e senza riga di valore» resta la spia
    --     di una scrittura fuori porta.
    -- ============================================================
    v_contributo := round(p_qta * COALESCE(v_costo, 0), 6);
    INSERT INTO magazzino.valore_giacenza (articolo_id, magazzino_id, valore)
    VALUES (p_articolo_id, p_magazzino_id, v_contributo)
    ON CONFLICT (articolo_id, magazzino_id) DO UPDATE
       SET valore = magazzino.valore_giacenza.valore + EXCLUDED.valore;

    RETURN v_movimento_id;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_scrivi_movimento(p_magazzino_id bigint, p_articolo_id uuid, p_causale character varying, p_qta numeric, p_sorgente_tipo_id bigint, p_sorgente_riga bigint, p_sorgente_uid uuid, p_costo_unitario numeric, p_lotto_id bigint, p_asset_id bigint, p_ubicazione_id bigint, p_data_mov timestamp with time zone, p_transfer_uid uuid, p_storno_di_movimento_id bigint, p_meta jsonb, p_sorgente_id bigint, p_sorgente_dettaglio bigint)
IS 'LA PRIMITIVA (M-2): l''unica funzione che scrive su magazzino.movimenti. SECURITY DEFINER del PROPRIETARIO, non di un superuser (chi migra possiede anche le tabelle; pgTAP: proowner = relowner), pin search_path pg_catalog/public/pg_temp scelto sui chiamati. L''app non ha INSERT sul ledger e non la esegue: ci arriva solo dai verbi. Il perimetro che la DEFINER scavalca lo rimette il guard BB (trg_*_a10_guard_emittente_scope, modo magazzino), anche senza identita''. Riceve qta FIRMATA in UoM base (non converte: D-L1-a), causale per codice_interno, e la provenienza nella grammatica del modello: p_sorgente_tipo_id e'' il tipo del DOCUMENTO (DDT_VENDITA, RESO_VENDITA, INVENTARIO, RETTIFICA, TRASFERIMENTO, EVENTO_ASSET), la chiave del documento in p_sorgente_id o p_sorgente_uid (una sola), poi p_sorgente_riga e p_sorgente_dettaglio: sempre la foglia piu'' bassa che il tipo ha, la pretende il guard unico script.trgfn_guard_sorgente (livello minimo DETTAGLIO), che verifica anche la catena. p_sorgente_id e p_sorgente_dettaglio stanno in coda alla firma. I quattordici passi, nell''ordine che e'' il contratto: 1 parametri (E_MAG_CHIAMATA_NON_VALIDA: una sola chiave del documento, il dettaglio con la sua riga, identificativi maggiori di zero); 2 causale attiva (E_CONFIG_MANCANTE); 3 sign(qta) = segno (E_MAG_MOVIMENTO_VERSO_INCOERENTE); 4 magazzino attivo (E_MAG_MAGAZZINO_NON_VALIDO); 5-8 articolo gestito, lotto, seriale, ubicazione via script.fn_check_riga_magazzino (primo motivo); 9 storno = specchio esatto dell''originale — stessa provenienza intera (tipo, documento, riga, dettaglio) e stessa posizione, non gia'' stornato (E_MAG_STORNO_INCOERENTE); 9-bis posizione del seriale derivata dal registro: in entrata da nessuna parte, in uscita qui (E_MAG_ASSET_POSIZIONE_INCOERENTE); 10 identita'' prima di scrivere, sulle nove colonne di uq_mag_movimenti_identita (E_MAG_MOVIMENTO_GIA_REGISTRATO; il UNIQUE resta la rete); 11 SOLO in uscita: pg_advisory_xact_lock(magazzino, articolo) — il perimetro del lock e'' quello di tutto cio'' che si legge dentro — poi script.fn_check_disponibilita_uscita con la provenienza intera (le attese proprie per prefisso) salvo consente_stock_negativo, con p_ignora_blocchi = is_rettifica; 12 il costo per STRUTTURA: storno -> dell''originale, entrata gemella (transfer_uid, +1) -> della OUT (E_MAG_GEMELLA_NON_TROVATA), uscita -> media corrente da vw_costo_medio letta dentro il lock, entrata -> COALESCE(p_costo_unitario, media); p_costo_unitario ammesso solo sull''ultimo caso (E_MAG_COSTO_NON_AMMESSO); un''entrata senza costo scrive NULL e diluisce la media (vw_magazzino_movimenti_senza_costo); 13 INSERT; 14 valore_giacenza += round(qta * costo, 6), costo NULL vale zero — la ri-somma di fn_ricalcola_valore_giacenza usa lo stesso round. TOCTOU fra i passi 1-10 e il lock: benigno (nessuna lettura decide una scrittura non idempotente). Corsa BENIGNA dei seriali in entrata (D-L2-e): due entrate simultanee dello stesso seriale in due magazzini si fermano sul secondo solo se la prima e'' gia'' visibile (READ COMMITTED) — un''entrata non ha lock per regola. Brief: brief-db-magazzino-lotto-2-motore 4.2; brief-db-sorgente-documento-e-riga lotto M (la provenienza del modello).';
```

</div>

---
{% include-markdown "signature-core.md" %}
