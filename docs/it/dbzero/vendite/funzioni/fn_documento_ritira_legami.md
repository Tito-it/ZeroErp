# ⚙️ Funzione `fn_documento_ritira_legami`

```sql
CREATE FUNCTION fn_documento_ritira_legami(p_documento text, p_id bigint, p_legami_confermati integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_ritira_legami(p_documento text, p_id bigint, p_legami_confermati integer)
 RETURNS integer
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: la conferma e il ritiro dei consumi di un documento
--   che si sta annullando. Lascia APERTA la porta del ritiro:
--   la chiude il verbo dopo il cambio di stato. Vedi
--   l'intestazione del changeSet.
-- Parametri: documento e testata polimorfi (tipi nudi);
--   p_legami_confermati e' un CONTEGGIO.
-- Ritorna: i legami confermati (0 se non ce n'erano).
-- =========================================================
DECLARE
    -- CONTEGGIO dei legami: nessuna colonna da ancorare.
    v_legami        integer;
    v_etichetta     text;
    v_riga_id       vendite.ddt_righe.id%TYPE;
    v_preventivo_id vendite.preventivi.id%TYPE;
    -- I preventivi toccati: array, %TYPE[] non esiste.
    v_preventivi    bigint[];
    v_evaso_id      config.stati_doc_preventivi.id%TYPE;
    v_accettato_id  config.stati_doc_preventivi.id%TYPE;
    v_sorgente      record;
BEGIN
    -- 1. Parametri.
    IF p_id IS NULL OR p_id <= 0
       OR p_documento IS NULL
       OR p_documento NOT IN ('DDT', 'ORDINE', 'PREVENTIVO', 'CONTRATTO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_documento_ritira_legami',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_documento', p_documento, 'p_id', p_id),
            NULL::uuid, 'vendite.fn_documento_ritira_legami',
            'documento (DDT, ORDINE, PREVENTIVO, CONTRATTO) e id maggiore di zero');
    END IF;

    -- 2. La conferma: dichiara quanti legami si sono visti.
    SELECT count(*)::integer INTO v_legami
      FROM vendite.fn_documento_legami(p_documento, p_id) AS l;

    IF v_legami = 0 THEN
        RETURN 0;
    END IF;

    IF p_legami_confermati IS DISTINCT FROM v_legami THEN
        SELECT t.etichetta INTO v_etichetta
          FROM script.fn_get_stato_testata_documento(p_documento, p_id) AS t;

        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_documento_ritira_legami',
            'E_DOC_ANNULLO_CON_LEGAMI',
            jsonb_build_object('documento',  p_documento,
                               'id',         p_id,
                               'legami',     v_legami,
                               'confermati', p_legami_confermati),
            NULL::uuid,
            COALESCE(v_etichetta, p_documento || ' #' || p_id::text),
            v_legami::text);
    END IF;

    -- 3. La porta del ritiro, per QUESTO documento. Resta aperta.
    PERFORM set_config('zeroerp.doc_ritira_legami',
                       p_documento || ':' || p_id::text, true);

    -- 4a. Bolla: i legami con ordini e resi, riga per riga.
    FOR v_riga_id IN
        SELECT DISTINCT l.riga_id
          FROM vendite.fn_documento_legami(p_documento, p_id) AS l
         WHERE l.origine IN ('ORDINE', 'RESO')
         ORDER BY l.riga_id
    LOOP
        PERFORM vendite.fn_ddt_riga_ritira_legami(v_riga_id);
    END LOOP;

    -- 4b. Ordine: le righe si staccano dal preventivo; il
    --     preventivo EVASO con un residuo torna ACCETTATO.
    IF p_documento = 'ORDINE' THEN
        SELECT s.id INTO v_evaso_id
          FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'EVASO';
        SELECT s.id INTO v_accettato_id
          FROM config.stati_doc_preventivi s WHERE s.codice_interno = 'ACCETTATO';

        -- Una CTE che scrive non sta dentro il cursore di un FOR:
        -- i preventivi toccati si raccolgono prima.
        WITH staccate AS (
            UPDATE vendite.ordini_righe orr
               SET preventivo_riga_id = NULL
              FROM vendite.preventivi_righe pr
             WHERE orr.ordine_id = p_id
               AND pr.id = orr.preventivo_riga_id
            RETURNING pr.preventivo_id)
        SELECT array_agg(DISTINCT st.preventivo_id ORDER BY st.preventivo_id)
          INTO v_preventivi
          FROM staccate st;

        FOREACH v_preventivo_id IN ARRAY COALESCE(v_preventivi, ARRAY[]::bigint[])
        LOOP
            UPDATE vendite.preventivi p
               SET stato_doc_preventivo_id = v_accettato_id
             WHERE p.id = v_preventivo_id
               AND p.stato_doc_preventivo_id = v_evaso_id
               AND (vendite.fn_preventivo_ha_residuo_ordine(p.id)
                    OR vendite.fn_preventivo_ha_residuo_commessa(p.id));
        END LOOP;
    END IF;

    -- 4c. Commessa: le righe NON_EMESSA, per sorgente, dalla
    --     primitiva col registro.
    FOR v_sorgente IN
        SELECT DISTINCT ca.sorgente_tipo_id, ca.sorgente_uid
          FROM vendite.fn_documento_legami(p_documento, p_id) AS l
          JOIN vendite.commesse_attivita ca ON ca.id = l.origine_riga_id
         WHERE l.origine = 'COMMESSA'
    LOOP
        PERFORM vendite.fn_ritira_commessa_attivita_da_sorgente(
            v_sorgente.sorgente_tipo_id,
            v_sorgente.sorgente_uid,
            format('Ritiro all''annullo confermato del documento di origine (%s %s)',
                   p_documento, p_id));
    END LOOP;

    RETURN v_legami;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_ritira_legami(p_documento text, p_id bigint, p_legami_confermati integer)
IS 'BB (2026-10-11, brief-db-annullo-documento-con-legami D-1/D-2/D-4/D-5): la conferma e il ritiro dei consumi di un documento che si annulla. Chi conferma DICHIARA quanti legami ha visto (vendite.fn_documento_legami); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI, lo stesso avviso del guard (stampo di E_CREDENZIALE_DA_CONFERMARE). Poi apre la porta del ritiro (GUC transazionale zeroerp.doc_ritira_legami = ''<DOCUMENTO>:<id>'', letta da vendite.fn_doc_porta_ritiro_ammette) e la LASCIA APERTA: la chiude il verbo dopo il cambio di stato, perche'' il guard dell''annullo la legge per i legami di provenienza. Ritira: legami della bolla con ordini e resi (vendite.fn_ddt_riga_ritira_legami); righe dell''ordine staccate dal preventivo (preventivo_riga_id a NULL), col preventivo EVASO che torna ACCETTATO se ha di nuovo un residuo; righe di commessa NON_EMESSA della sorgente (vendite.fn_ritira_commessa_attivita_da_sorgente, col registro). La provenienza (offerta) non si ritira. Ritorna i legami confermati, 0 se non ce n''erano. SECURITY INVOKER, EXECUTE a nessuno: lo chiamano i verbi DEFINER vendite.fn_annulla_ddt, fn_annulla_ordine, fn_annulla_preventivo, fn_annulla_contratto, che bloccano la testata prima.';
```

---
{% include-markdown "signature-core.md" %}
