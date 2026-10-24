# ⚙️ Funzione `fn_posta_trasferimento`

```sql
CREATE FUNCTION fn_posta_trasferimento(p_trasferimento_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_posta_trasferimento(p_trasferimento_id bigint)
 RETURNS TABLE(movimento_id bigint, riga_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
#variable_conflict use_column
-- Scopo: registrare un trasferimento interno CONFIRM — per ogni riga la
--   coppia TRASF_OUT / TRASF_IN attraverso la primitiva, poi POSTED.
--   Una transazione. Ritorna i due movimenti di ogni riga.
DECLARE
    v_utente      config.user_override_azioni.auth_user_id%TYPE;
    v_t           magazzino.trasferimenti%ROWTYPE;
    v_sorgente_id config.sorgenti.id%TYPE;
    v_motivi      jsonb;
    v_riga        magazzino.trasferimenti_righe%ROWTYPE;
BEGIN
    -- 0. Il permesso, prima di ogni altra cosa: lo stesso del backend.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_azione(v_utente, 'registra_magazzino');

    IF p_trasferimento_id IS NULL OR p_trasferimento_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_trasferimento',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'trasferimento obbligatorio e maggiore di zero',
                               'p_trasferimento_id', p_trasferimento_id),
            NULL::uuid, 'magazzino.fn_posta_trasferimento',
            'p_trasferimento_id (obbligatorio, maggiore di zero)');
    END IF;

    -- La testata, FOR UPDATE, nel perimetro del magazzino di partenza.
    SELECT t.* INTO v_t
      FROM magazzino.trasferimenti t
     WHERE t.id = p_trasferimento_id
       AND script.fn_scope_ef_whitelist_via_magazzino(v_utente, t.magazzino_id_from)
       FOR UPDATE;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_trasferimento',
            'E_MAG_DOCUMENTO_NON_TROVATO',
            jsonb_build_object('trasferimento_id', p_trasferimento_id),
            NULL::uuid, p_trasferimento_id::text);
    END IF;

    -- Si puo' registrare? La check condivisa con la capability.
    v_motivi := script.fn_check_documento_interno_registrabile('TRASFERIMENTO', p_trasferimento_id);
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'magazzino', 'magazzino.fn_posta_trasferimento', v_motivi, NULL, NULL::uuid,
        jsonb_build_object('trasferimento_id', p_trasferimento_id));

    SELECT s.id INTO v_sorgente_id
      FROM config.sorgenti s
     WHERE s.codice_interno = 'TRASFERIMENTO_RIGA' AND s.attivo;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_trasferimento',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.sorgenti.TRASFERIMENTO_RIGA'),
            NULL::uuid, VARIADIC ARRAY['sorgente TRASFERIMENTO_RIGA (config.sorgenti, attiva)']);
    END IF;

    PERFORM set_config('zeroerp.magazzino_posting_trasferimento', p_trasferimento_id::text, true);

    FOR v_riga IN
        SELECT r.* FROM magazzino.trasferimenti_righe r
         WHERE r.trasferimento_id = p_trasferimento_id
         ORDER BY r.id
    LOOP
        -- L'uscita dall'origine: alla media corrente (la primitiva).
        movimento_id := magazzino.fn_scrivi_movimento(
            p_magazzino_id     => v_t.magazzino_id_from,
            p_articolo_id      => v_riga.articolo_id,
            p_causale          => 'TRASF_OUT',
            p_qta              => -v_riga.qta,
            p_sorgente_tipo_id => v_sorgente_id,
            p_sorgente_riga    => v_riga.id,
            p_lotto_id         => v_riga.lotto_id,
            p_asset_id         => v_riga.asset_id,
            p_ubicazione_id    => v_riga.ubicazione_id_da,
            p_data_mov         => script.fn_inizio_giorno_operativo(v_t.data),
            p_transfer_uid     => v_t.uid);
        riga_id := v_riga.id;
        qta     := -v_riga.qta;
        RETURN NEXT;

        -- L'entrata nella destinazione: al costo dell'uscita (la gemella).
        movimento_id := magazzino.fn_scrivi_movimento(
            p_magazzino_id     => v_t.magazzino_id_to,
            p_articolo_id      => v_riga.articolo_id,
            p_causale          => 'TRASF_IN',
            p_qta              => v_riga.qta,
            p_sorgente_tipo_id => v_sorgente_id,
            p_sorgente_riga    => v_riga.id,
            p_lotto_id         => v_riga.lotto_id,
            p_asset_id         => v_riga.asset_id,
            p_ubicazione_id    => v_riga.ubicazione_id_a,
            p_data_mov         => script.fn_inizio_giorno_operativo(v_t.data),
            p_transfer_uid     => v_t.uid);
        riga_id := v_riga.id;
        qta     := v_riga.qta;
        RETURN NEXT;
    END LOOP;

    UPDATE magazzino.trasferimenti t
       SET stato_trasferimento = 'POSTED'
     WHERE t.id = p_trasferimento_id;

    PERFORM set_config('zeroerp.magazzino_posting_trasferimento', '', true);
    RETURN;
END;
$function$

COMMENT ON FUNCTION magazzino.fn_posta_trasferimento(p_trasferimento_id bigint)
IS 'VERBO del trasferimento interno (D-L2-g). Prima riga: script.fn_guard_azione(utente, ''registra_magazzino''). SECURITY DEFINER con search_path bloccato: la testata si prende FOR UPDATE col predicato della policy sul magazzino di partenza (fuori perimetro E_MAG_DOCUMENTO_NON_TROVATO). La check e'' quella della capability (script.fn_check_documento_interno_registrabile, TRASFERIMENTO): stato CONFIRM, righe, stessa posizione, partenza e arrivo postabili. Per riga, nello stesso momento: TRASF_OUT (-qta) da magazzino_id_from/ubicazione_id_da e TRASF_IN (+qta) in magazzino_id_to/ubicazione_id_a, transfer_uid = uid del trasferimento (l''entrata al costo dell''uscita), sorgente TRASFERIMENTO_RIGA. Poi POSTED con la GUC transazionale zeroerp.magazzino_posting_trasferimento. UNA transazione. Ritorna (movimento_id, riga_id, qta), due per riga. Brief: brief-db-magazzino-lotto-3-scarico-da-ddt (P-10).';
```

</div>

---
{% include-markdown "signature-core.md" %}
