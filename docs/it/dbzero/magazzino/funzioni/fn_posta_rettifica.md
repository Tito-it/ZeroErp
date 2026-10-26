{% include-markdown "it/dbzero/magazzino/manual/fn_posta_rettifica.md" %}
# ⚙️ Funzione `fn_posta_rettifica`

```sql
CREATE FUNCTION fn_posta_rettifica(p_rettifica_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION magazzino.fn_posta_rettifica(p_rettifica_id bigint)
 RETURNS TABLE(movimento_id bigint, riga_id bigint, qta numeric)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: registrare una rettifica CONFIRM — per ogni riga posta qta_delta
--   (dato) con RETT_POS/RETT_NEG dal segno attraverso la primitiva; poi la
--   testata a POSTED. Una transazione. Ritorna il movimento per riga.
-- Rev 2026-09-22 (Lotto 2-bis, R-1): le condizioni di registrabilita' le
--   dice script.fn_check_documento_interno_registrabile, la stessa della
--   capability. ⭐ Per la rettifica questo ANTICIPA il rifiuto di una riga
--   non postabile (prima lo dava la primitiva a meta' ciclo, stesso codice):
--   e' la simmetria con l'inventario, non una regola nuova.
-- Rev 2026-09-24 (brief-db-magazzino-verbi-con-permesso, D-4): e' un VERBO.
--   Prima riga: script.fn_guard_azione('registra_magazzino'), lo stesso
--   permesso che il backend chiede all'endpoint. SECURITY DEFINER del
--   proprietario: l'app non chiama piu' la primitiva, la chiama il verbo.
--   La RLS dei documenti qui non vale: il perimetro lo rimette il predicato
--   della policy (fn_scope_ef_whitelist_via_magazzino) nella WHERE del
--   FOR UPDATE — fuori perimetro resta NON TROVATO, e senza lock.
DECLARE
    v_utente       config.user_override_azioni.auth_user_id%TYPE;
    v_magazzino_id magazzino.rettifiche.magazzino_id%TYPE;
    v_data         magazzino.rettifiche.data%TYPE;
    v_stato        magazzino.rettifiche.stato_mag_rettifiche%TYPE;
    v_sorgente_id  config.sorgenti.id%TYPE;
    v_motivi       jsonb;
    v_riga         magazzino.rettifiche_righe%ROWTYPE;
BEGIN
    -- 0. Il permesso, prima di ogni altra cosa: lo stesso del backend.
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;
    PERFORM script.fn_guard_azione(v_utente, 'registra_magazzino');

    IF p_rettifica_id IS NULL OR p_rettifica_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('magazzino', 'magazzino.fn_posta_rettifica',
            'E_MAG_CHIAMATA_NON_VALIDA',
            jsonb_build_object('detail', 'rettifica obbligatoria e maggiore di zero', 'p_rettifica_id', p_rettifica_id),
            NULL::uuid, 'magazzino.fn_posta_rettifica', 'p_rettifica_id (obbligatoria, maggiore di zero)');
    END IF;

    -- La testata, FOR UPDATE, nel perimetro (predicato della policy: DEFINER).
    SELECT t.magazzino_id, t.data, t.stato_mag_rettifiche
      INTO v_magazzino_id, v_data, v_stato
      FROM magazzino.rettifiche t
     WHERE t.id = p_rettifica_id
       AND script.fn_scope_ef_whitelist_via_magazzino(v_utente, t.magazzino_id)
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
            p_data_mov         => script.fn_inizio_giorno_operativo(v_data));
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
IS 'VERBO (rev 2026-09-24, brief-db-magazzino-verbi-con-permesso): registra una rettifica CONFIRM (D-L2-g). Prima riga: script.fn_guard_azione(utente, ''registra_magazzino''), lo stesso permesso dell''endpoint (E_PERMESSO_NEGATO, anche senza utente). SECURITY DEFINER del proprietario con search_path bloccato: e'' la sola strada verso la primitiva. La RLS qui non vale: la testata si prende FOR UPDATE con il predicato della policy (script.fn_scope_ef_whitelist_via_magazzino) nella WHERE — fuori perimetro E_MAG_DOCUMENTO_NON_TROVATO (404 no-leak) e nessun lock. Poi come prima: per ogni riga posta qta_delta con RETT_POS/RETT_NEG dal segno attraverso la primitiva (sorgente RETTIFICA_RIGA; costo della riga solo su un''entrata; is_rettifica: i blocchi non fermano, il fisico si''), porta la testata a POSTED con la GUC transazionale zeroerp.magazzino_posting_rettifica. UNA transazione. Ritorna (movimento_id, riga_id, qta) per riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
