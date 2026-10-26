{% include-markdown "it/dbzero/magazzino/manual/fn_posta_inventario.md" %}
# ⚙️ Funzione `fn_posta_inventario`

```sql
CREATE FUNCTION fn_posta_inventario(p_inventario_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_posta_inventario(p_inventario_id bigint)
 RETURNS TABLE(movimento_id bigint, riga_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: registrare un inventario CONFIRM — per ogni riga del piano
--   (fn_inventario_piano) scrive qta_sistema e posta il delta con la
--   causale del piano attraverso la primitiva; poi porta la testata a
--   POSTED. Una transazione: se una riga fallisce non resta niente e il
--   documento resta CONFIRM. Ritorna, riga per riga, il movimento scritto.
-- Rev 2026-09-22 (Lotto 2-bis, R-1): le condizioni di registrabilita' non
--   sono piu' scritte qui — le dice
--   script.fn_check_documento_interno_registrabile, la stessa funzione da
--   cui la capability del drawer accende o spegne «Registra». Codici e
--   valori invariati: le frasi sono quelle di prima.
-- Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso, D-4): e' un VERBO.
--   Prima riga: script.fn_guard_azione('registra_magazzino'), lo stesso
--   permesso che il backend chiede all'endpoint. SECURITY DEFINER del
--   proprietario: l'app non chiama piu' la primitiva, la chiama il verbo.
--   La RLS dei documenti qui non vale: il perimetro lo rimette il predicato
--   della policy (fn_scope_ef_whitelist_via_magazzino) nella WHERE del
--   FOR UPDATE — fuori perimetro resta NON TROVATO, e senza lock.
DECLARE
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
    v_magazzino_id magazzino.inventari.magazzino_id%TYPE;
    v_data         magazzino.inventari.data%TYPE;
    v_stato        magazzino.inventari.stato_mag_inventario%TYPE;
    v_sorgente_id  config.sorgenti.id%TYPE;
    v_costo        magazzino.inventari_righe.costo_unitario%TYPE;
    v_motivi       jsonb;
    v_piano        record;
BEGIN
    -- 0. Il permesso, prima di ogni altra cosa: lo stesso del backend.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_azione(v_utente, 'registra_magazzino');

    -- 1. Parametro
    IF p_inventario_id IS NULL OR p_inventario_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_inventario',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'inventario obbligatorio e maggiore di zero', 'p_inventario_id', p_inventario_id),
            NULL::uuid, 'magazzino.fn_posta_inventario', 'p_inventario_id (obbligatorio, maggiore di zero)');
    END IF;

    -- 2. La testata, FOR UPDATE, nel perimetro: fuori perimetro NON C'E'.
    --    Il predicato e' quello della policy (qui la RLS non vale: DEFINER).
    --    Il lock viene PRIMA di ogni domanda: e' cio' che serializza due
    --    posting dello stesso documento (la check e' STABLE e non lo prende).
    SELECT i.magazzino_id, i.data, i.stato_mag_inventario
      INTO v_magazzino_id, v_data, v_stato
      FROM magazzino.inventari i
     WHERE i.id = p_inventario_id
       AND script.fn_scope_ef_whitelist_via_magazzino(v_utente, i.magazzino_id)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_inventario',
            'E_MAG_DOCUMENTO_NON_TROVATO',
            jsonb_build_object('inventario_id', p_inventario_id),
            NULL::uuid, p_inventario_id::text);
    END IF;

    -- 3. Si puo' registrare? Lo dice la check CONDIVISA con la capability:
    --    stato non CONFIRM, nessuna riga, una riga non postabile — in
    --    quest'ordine. Il codice lo LEGGO dall'array, quindi l'helper.
    v_motivi := script.fn_check_documento_interno_registrabile('INVENTARIO', p_inventario_id);
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'magazzino', 'magazzino.fn_posta_inventario', v_motivi, NULL, NULL::uuid,
        jsonb_build_object('inventario_id', p_inventario_id));

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
            -- La RETE: la check del passo 3 l'ha gia' detto, ma se un giorno
            -- i due percorsi divergessero il ledger non deve pagarlo.
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
            p_data_mov         => script.fn_inizio_giorno_operativo(v_data));
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
IS 'VERBO (rev 2026-09-24, brief-db-magazzino-verbi-con-permesso): registra un inventario CONFIRM (D-L2-f, D-L2-n). Prima riga: script.fn_guard_azione(utente, ''registra_magazzino''), lo stesso permesso dell''endpoint (E_PERMESSO_NEGATO, anche senza utente). SECURITY DEFINER del proprietario con search_path bloccato: e'' la sola strada verso la primitiva. La RLS qui non vale: la testata si prende FOR UPDATE con il predicato della policy (script.fn_scope_ef_whitelist_via_magazzino) nella WHERE — fuori perimetro E_MAG_DOCUMENTO_NON_TROVATO (404 no-leak) e nessun lock. Poi come prima: legge il piano (fn_inventario_piano), scrive qta_sistema su ogni riga, posta le righe con delta <> 0 attraverso la primitiva (causale del piano; sorgente INVENTARIO_RIGA; costo della riga solo su un''entrata; data_mov = data dell''inventario), porta la testata a POSTED con la GUC transazionale zeroerp.magazzino_posting_inventario. Non CONFIRM: E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA; senza righe: E_MAG_DOCUMENTO_SENZA_RIGHE; una NON_POSTABILE rifiuta tutto. UNA transazione: se una riga fallisce non resta niente. Ritorna (movimento_id, riga_id, qta) per riga postata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
