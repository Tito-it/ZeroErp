{% include-markdown "it/dbzero/magazzino/manual/fn_posta_inventario.md" %}
# ⚙️ Funzione `fn_posta_inventario`

```sql
CREATE FUNCTION fn_posta_inventario(p_inventario_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_posta_inventario(p_inventario_id bigint)
 RETURNS TABLE(movimento_id bigint, riga_id bigint, qta numeric)
 LANGUAGE plpgsql
AS $function$
-- Scopo: registrare un inventario CONFIRM — per ogni riga del piano
--   (fn_inventario_piano) scrive qta_sistema e posta il delta con la
--   causale del piano attraverso la primitiva; poi porta la testata a
--   POSTED. Una transazione: se una riga fallisce non resta niente e il
--   documento resta CONFIRM. Ritorna, riga per riga, il movimento scritto.
DECLARE
    v_magazzino_id magazzino.inventari.magazzino_id%TYPE;
    v_data         magazzino.inventari.data%TYPE;
    v_stato        magazzino.inventari.stato_mag_inventario%TYPE;
    v_n_righe      bigint;
    v_sorgente_id  config.sorgenti.id%TYPE;
    v_costo        magazzino.inventari_righe.costo_unitario%TYPE;
    v_motivi       jsonb;
    v_piano        record;
BEGIN
    -- 1. Parametro
    IF p_inventario_id IS NULL OR p_inventario_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_inventario',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'inventario obbligatorio e maggiore di zero', 'p_inventario_id', p_inventario_id),
            NULL::uuid, 'magazzino.fn_posta_inventario', 'p_inventario_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata, FOR UPDATE, sotto RLS: fuori perimetro NON C'E'.
    SELECT i.magazzino_id, i.data, i.stato_mag_inventario
      INTO v_magazzino_id, v_data, v_stato
      FROM magazzino.inventari i
     WHERE i.id = p_inventario_id
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_inventario',
            'E_MAG_DOCUMENTO_NON_TROVATO',
            jsonb_build_object('inventario_id', p_inventario_id),
            NULL::uuid, p_inventario_id::text);
    END IF;
    IF v_stato <> 'CONFIRM' THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_inventario',
            'E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA',
            jsonb_build_object('detail', 'il posting parte da CONFIRM',
                               'inventario_id', p_inventario_id, 'stato', v_stato),
            NULL::uuid, v_stato, 'POSTED');
    END IF;

    -- 3. Almeno una riga.
    SELECT count(*) INTO v_n_righe FROM magazzino.inventari_righe r WHERE r.inventario_id = p_inventario_id;
    IF v_n_righe = 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_inventario',
            'E_MAG_DOCUMENTO_SENZA_RIGHE',
            jsonb_build_object('inventario_id', p_inventario_id),
            NULL::uuid, p_inventario_id::text);
    END IF;

    SELECT s.id INTO v_sorgente_id FROM config.sorgenti s WHERE s.codice_interno = 'INVENTARIO_RIGA' AND s.attivo;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_inventario',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.sorgenti.INVENTARIO_RIGA'),
            NULL::uuid, VARIADIC ARRAY['sorgente INVENTARIO_RIGA (config.sorgenti, attiva)']);
    END IF;

    -- 4. La GUC transazionale: apre la porta POSTED e le righe in CONFIRM.
    PERFORM set_config('zeroerp.magazzino_posting_inventario', p_inventario_id::text, true);

    -- 5. Per riga, in ordine di id, DAL PIANO.
    FOR v_piano IN
        SELECT pi.riga_id, pi.articolo_id, pi.ubicazione_id, pi.lotto_id, pi.asset_id,
               pi.qta_sistema, pi.delta, pi.causale_codice_interno, pi.esito
          FROM magazzino.fn_inventario_piano(p_inventario_id) pi
         WHERE pi.riga_id IS NOT NULL
         ORDER BY pi.riga_id
    LOOP
        -- La fotografia contro cui il conteggio e' stato posto: resta sulla riga.
        UPDATE magazzino.inventari_righe r
           SET qta_sistema = v_piano.qta_sistema
         WHERE r.id = v_piano.riga_id;

        IF v_piano.esito = 'NON_POSTABILE' THEN
            -- Il primo motivo della STESSA check: il piano l'aveva gia' detto.
            v_motivi := script.fn_check_riga_magazzino(v_magazzino_id, v_piano.articolo_id,
                                                       v_piano.lotto_id, v_piano.asset_id, v_piano.ubicazione_id);
            PERFORM script.fn_raise_primo_motivo_se_presente(
                'magazzino', 'magazzino.fn_posta_inventario', v_motivi, NULL, NULL::uuid,
                jsonb_build_object('inventario_id', p_inventario_id, 'riga_id', v_piano.riga_id));
        END IF;

        CONTINUE WHEN v_piano.delta = 0;     -- INVARIATA: niente da dire

        -- Il costo della riga vale solo su un'entrata (D-L2-c): un'uscita va alla media.
        SELECT CASE WHEN v_piano.delta > 0 THEN r.costo_unitario END INTO v_costo
          FROM magazzino.inventari_righe r WHERE r.id = v_piano.riga_id;

        movimento_id := magazzino.fn_scrivi_movimento(
            p_magazzino_id     => v_magazzino_id,
            p_articolo_id      => v_piano.articolo_id,
            p_causale          => v_piano.causale_codice_interno,
            p_qta              => v_piano.delta,
            p_sorgente_tipo_id => v_sorgente_id,
            p_sorgente_riga    => v_piano.riga_id,
            p_costo_unitario   => v_costo,
            p_lotto_id         => v_piano.lotto_id,
            p_asset_id         => v_piano.asset_id,
            p_ubicazione_id    => v_piano.ubicazione_id,
            p_data_mov         => v_data::timestamptz);
        riga_id := v_piano.riga_id;
        qta     := v_piano.delta;
        RETURN NEXT;
    END LOOP;

    -- 6. La testata a POSTED: passa il guard perche' la GUC dice «sono io».
    UPDATE magazzino.inventari i
       SET stato_mag_inventario = 'POSTED'
     WHERE i.id = p_inventario_id;

    -- 7. La GUC azzerata (e' comunque transazionale).
    PERFORM set_config('zeroerp.magazzino_posting_inventario', '', true);
    RETURN;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_posta_inventario(p_inventario_id bigint)
IS 'Registra un inventario CONFIRM (D-L2-f, D-L2-n): legge il piano (fn_inventario_piano), scrive qta_sistema su ogni riga, posta le righe con delta <> 0 attraverso la primitiva (causale del piano: INV_INIZIALE se l''articolo non ha movimenti nel magazzino, altrimenti RETT_POS/RETT_NEG; sorgente INVENTARIO_RIGA:{riga}; costo della riga solo su un''entrata; data_mov = data dell''inventario), porta la testata a POSTED con la GUC transazionale zeroerp.magazzino_posting_inventario. Le NON_CONTATA restano; una NON_POSTABILE rifiuta tutto col primo motivo di fn_check_riga_magazzino. SECURITY INVOKER: la testata sotto RLS FOR UPDATE — fuori perimetro E_MAG_DOCUMENTO_NON_TROVATO (404 no-leak); non CONFIRM: E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA; senza righe: E_MAG_DOCUMENTO_SENZA_RIGHE. UNA transazione per costruzione (5b): se una riga fallisce non resta niente. Ritorna (movimento_id, riga_id, qta) per riga postata. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.5.';
```

---
{% include-markdown "signature-core.md" %}
