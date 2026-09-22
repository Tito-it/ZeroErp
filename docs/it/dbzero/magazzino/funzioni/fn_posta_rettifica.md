{% include-markdown "it/dbzero/magazzino/manual/fn_posta_rettifica.md" %}
# ⚙️ Funzione `fn_posta_rettifica`

```sql
CREATE FUNCTION fn_posta_rettifica(p_rettifica_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_posta_rettifica(p_rettifica_id bigint)
 RETURNS TABLE(movimento_id bigint, riga_id bigint, qta numeric)
 LANGUAGE plpgsql
AS $function$
-- Scopo: registrare una rettifica CONFIRM — per ogni riga posta qta_delta
--   (dato) con RETT_POS/RETT_NEG dal segno attraverso la primitiva; poi la
--   testata a POSTED. Una transazione. Ritorna il movimento per riga.
-- Rev 2026-09-22 (Lotto 2-bis, R-1): le condizioni di registrabilita' le
--   dice script.fn_check_documento_interno_registrabile, la stessa della
--   capability. ⭐ Per la rettifica questo ANTICIPA il rifiuto di una riga
--   non postabile (prima lo dava la primitiva a meta' ciclo, stesso codice):
--   e' la simmetria con l'inventario, non una regola nuova.
DECLARE
    v_magazzino_id magazzino.rettifiche.magazzino_id%TYPE;
    v_data         magazzino.rettifiche.data%TYPE;
    v_stato        magazzino.rettifiche.stato_mag_rettifiche%TYPE;
    v_sorgente_id  config.sorgenti.id%TYPE;
    v_motivi       jsonb;
    v_riga         magazzino.rettifiche_righe%ROWTYPE;
BEGIN
    IF p_rettifica_id IS NULL OR p_rettifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_rettifica',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'rettifica obbligatoria e maggiore di zero', 'p_rettifica_id', p_rettifica_id),
            NULL::uuid, 'magazzino.fn_posta_rettifica', 'p_rettifica_id (obbligatoria, maggiore di zero)');
    END IF;

    SELECT t.magazzino_id, t.data, t.stato_mag_rettifiche
      INTO v_magazzino_id, v_data, v_stato
      FROM magazzino.rettifiche t
     WHERE t.id = p_rettifica_id
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_rettifica',
            'E_MAG_DOCUMENTO_NON_TROVATO',
            jsonb_build_object('rettifica_id', p_rettifica_id),
            NULL::uuid, p_rettifica_id::text);
    END IF;

    -- Si puo' registrare? La check condivisa con la capability.
    v_motivi := script.fn_check_documento_interno_registrabile('RETTIFICA', p_rettifica_id);
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'magazzino', 'magazzino.fn_posta_rettifica', v_motivi, NULL, NULL::uuid,
        jsonb_build_object('rettifica_id', p_rettifica_id));

    SELECT s.id INTO v_sorgente_id FROM config.sorgenti s WHERE s.codice_interno = 'RETTIFICA_RIGA' AND s.attivo;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_rettifica',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.sorgenti.RETTIFICA_RIGA'),
            NULL::uuid, VARIADIC ARRAY['sorgente RETTIFICA_RIGA (config.sorgenti, attiva)']);
    END IF;

    PERFORM set_config('zeroerp.magazzino_posting_rettifica', p_rettifica_id::text, true);

    FOR v_riga IN
        SELECT r.* FROM magazzino.rettifiche_righe r
         WHERE r.rettifica_id = p_rettifica_id
         ORDER BY r.id
    LOOP
        movimento_id := magazzino.fn_scrivi_movimento(
            p_magazzino_id     => v_magazzino_id,
            p_articolo_id      => v_riga.articolo_id,
            p_causale          => CASE WHEN v_riga.qta_delta > 0 THEN 'RETT_POS' ELSE 'RETT_NEG' END,
            p_qta              => v_riga.qta_delta,
            p_sorgente_tipo_id => v_sorgente_id,
            p_sorgente_riga    => v_riga.id,
            p_costo_unitario   => CASE WHEN v_riga.qta_delta > 0 THEN v_riga.costo_unitario END,
            p_lotto_id         => v_riga.lotto_id,
            p_asset_id         => v_riga.asset_id,
            p_ubicazione_id    => v_riga.ubicazione_id,
            p_data_mov         => v_data::timestamptz);
        riga_id := v_riga.id;
        qta     := v_riga.qta_delta;
        RETURN NEXT;
    END LOOP;

    UPDATE magazzino.rettifiche t
       SET stato_mag_rettifiche = 'POSTED'
     WHERE t.id = p_rettifica_id;

    PERFORM set_config('zeroerp.magazzino_posting_rettifica', '', true);
    RETURN;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_posta_rettifica(p_rettifica_id bigint)
IS 'Registra una rettifica CONFIRM (D-L2-g): per ogni riga posta qta_delta (dato, firmato) con RETT_POS/RETT_NEG dal segno attraverso la primitiva (sorgente RETTIFICA_RIGA:{riga}; costo della riga solo su un''entrata; is_rettifica: i blocchi non fermano, il fisico si''), porta la testata a POSTED con la GUC transazionale zeroerp.magazzino_posting_rettifica. SECURITY INVOKER: testata sotto RLS FOR UPDATE (E_MAG_DOCUMENTO_NON_TROVATO, E_MAG_DOCUMENTO_TRANSIZIONE_NON_AMMESSA, E_MAG_DOCUMENTO_SENZA_RIGHE). UNA transazione: se una riga fallisce non resta niente. Ritorna (movimento_id, riga_id, qta) per riga. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.5.';
```

---
{% include-markdown "signature-core.md" %}
