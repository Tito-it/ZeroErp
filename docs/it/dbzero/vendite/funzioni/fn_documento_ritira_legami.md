# ⚙️ Funzione `fn_documento_ritira_legami`

```sql
CREATE FUNCTION fn_documento_ritira_legami(p_documento character varying, p_id bigint, p_legami_confermati integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_ritira_legami(p_documento character varying, p_id bigint, p_legami_confermati integer)
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
-- rev 2026-10-12 (brief-db-annullo-a-valle-riapre-a-monte):
--   + COMMESSA (D-1, D-2, D-7); prima cio' che vieta, poi la
--   conferma (D-3, per tutti i documenti); lo stato del
--   preventivo dal BB vendite.fn_preventivo_proietta_stato_
--   smistamento (D-10). Vedi l'intestazione del changeSet.
-- rev 2026-10-19 (20261019-96, brief-db-grammatica-unica-documenti
--   lotto 2b): l'origine dei legami e' il codice della sorgente
--   (ORDINE_VENDITA, RESO_VENDITA); v_sorgente_uid ancorato.
-- rev 2026-10-26 (20261026-21, brief-modello-documento-vendita
--   §13, O-4): + OFFERTA_COMMERCIALE. Prima cio' che vieta
--   (script.fn_check_offerta_annullabile), poi la conferma; il
--   legame (la revisione precedente) e' di provenienza, niente da
--   ritirare.
-- =========================================================
DECLARE
    -- CONTEGGIO dei legami: nessuna colonna da ancorare.
    v_legami        integer;
    -- L'etichetta del lettore di testata: un'uscita di funzione, nessuna
    -- colonna dietro.
    v_etichetta     text;
    v_riga_id       vendite.ddt_righe.id%TYPE;
    v_preventivo_id vendite.preventivi.id%TYPE;
    -- I preventivi toccati: array, %TYPE[] non esiste.
    v_preventivi    bigint[];
    v_sorgente      record;
    -- rev 2026-10-12. I motivi che vietano: il valore di ritorno di
    -- una fn_check_*, nessuna colonna dietro.
    v_motivi        jsonb;
    -- La chiave del documento di bolla e contratto, come la scrive la riga
    -- di commessa: id e uid, con la regola d'incontro.
    v_sorgente_id   vendite.commesse_attivita.sorgente_id%TYPE;
    v_sorgente_uid  vendite.commesse_attivita.sorgente_uid%TYPE;
    v_ca_id         vendite.commesse_attivita.id%TYPE;
    v_resi_riga_id  vendite.resi_righe.id%TYPE;
    -- Il motivo del ritiro, testo libero per i verbi che lo registrano.
    v_motivo        text;
BEGIN
    -- 1. Parametri.
    IF p_id IS NULL OR p_id <= 0
       OR p_documento IS NULL
       OR p_documento NOT IN ('DDT_VENDITA', 'ORDINE_VENDITA', 'PREVENTIVO', 'CONTRATTO', 'COMMESSA', 'OFFERTA_COMMERCIALE') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_documento_ritira_legami',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_documento', p_documento, 'p_id', p_id),
            NULL::uuid, 'vendite.fn_documento_ritira_legami',
            'documento (DDT_VENDITA, ORDINE_VENDITA, PREVENTIVO, CONTRATTO, COMMESSA, OFFERTA_COMMERCIALE) e id maggiore di zero');
    END IF;

    -- 1-bis. ⭐ Prima cio' che vieta (rev 2026-10-12, D-3): chi annulla
    --    non deve confermare un ritiro che il cambio di stato rifiuterebbe
    --    comunque. Le stesse check che i guard della testata sollevano
    --    (il primo motivo, con l'helper): preventivo e ordine dalla loro
    --    fn_check_*_annullabile, commessa dalla sua, bolla e contratto
    --    dalla chiusura della sorgente (righe di commessa EMESSA). La
    --    matrice resta ai guard.
    IF p_documento = 'PREVENTIVO' THEN
        v_motivi := script.fn_check_preventivo_annullabile(p_id);
    ELSIF p_documento = 'ORDINE_VENDITA' THEN
        v_motivi := script.fn_check_ordine_annullabile(p_id);
    ELSIF p_documento = 'COMMESSA' THEN
        v_motivi := script.fn_check_commessa_annullabile(p_id);
    ELSIF p_documento = 'OFFERTA_COMMERCIALE' THEN
        -- rev 2026-10-26 (20261026-21, O-4): un contratto o un ordine
        -- vivo nato dall'offerta, lo stesso del guard di transizione.
        v_motivi := script.fn_check_offerta_annullabile(p_id);
    ELSE  -- DDT_VENDITA, CONTRATTO
        -- ⭐ rev 2026-11-06 (20261106-43, giro 0.3): la chiave dal BB che
        --   risolve, la stessa lettura per bolla e contratto.
        SELECT d.documento_id, d.documento_uid INTO v_sorgente_id, v_sorgente_uid
          FROM config.sorgenti s
          CROSS JOIN LATERAL script.fn_sorgente_documento(s.id, p_id, NULL::uuid) d
         WHERE s.codice_interno = p_documento;
        -- Testata assente: nessun motivo, decide chi cambia lo stato.
        IF v_sorgente_id IS NOT NULL THEN
            v_motivi := script.fn_check_sorgente_chiudibile(
                (SELECT s.id FROM config.sorgenti s
                  WHERE s.codice_interno = p_documento),
                v_sorgente_id, v_sorgente_uid);
        END IF;
    END IF;

    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_documento_ritira_legami',
        COALESCE(v_motivi, '[]'::jsonb),
        NULL,
        NULL::uuid,
        jsonb_build_object('documento', p_documento, 'id', p_id));

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
    --     ⚠️ rev 2026-10-12: solo per la bolla. Anche la commessa ha
    --     legami di origine ORDINE_VENDITA e RESO_VENDITA, e i suoi riga_id sono righe
    --     di commessa, non di bolla.
    IF p_documento = 'DDT_VENDITA' THEN
        FOR v_riga_id IN
            SELECT DISTINCT l.riga_id
              FROM vendite.fn_documento_legami(p_documento, p_id) AS l
             WHERE l.origine IN ('ORDINE_VENDITA', 'RESO_VENDITA')
             ORDER BY l.riga_id
        LOOP
            PERFORM vendite.fn_ddt_riga_ritira_legami(v_riga_id);
        END LOOP;
    END IF;

    -- 4b. Ordine: le righe si staccano dal preventivo; lo stato del
    --     preventivo lo riproietta il BB (EVASO con un residuo torna
    --     ACCETTATO). rev 2026-10-12 (D-10): la regola non e' piu' qui.
    IF p_documento = 'ORDINE_VENDITA' THEN
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
            PERFORM vendite.fn_preventivo_proietta_stato_smistamento(v_preventivo_id);
        END LOOP;
    END IF;

    -- 4c. Commessa: le righe NON_EMESSA, per sorgente, dalla
    --     primitiva col registro.
    FOR v_sorgente IN
        SELECT DISTINCT ca.sorgente_tipo_id, ca.sorgente_id, ca.sorgente_uid
          FROM vendite.fn_documento_legami(p_documento, p_id) AS l
          JOIN vendite.commesse_attivita ca ON ca.id = l.origine_riga_id
         WHERE l.origine = 'COMMESSA'
    LOOP
        PERFORM vendite.fn_ritira_commessa_attivita_da_sorgente(
            v_sorgente.sorgente_tipo_id,
            v_sorgente.sorgente_id,
            v_sorgente.sorgente_uid,
            format('Ritiro all''annullo confermato del documento di origine (%s %s)',
                   p_documento, p_id));
    END LOOP;

    -- 4d. ⭐ rev 2026-10-12 (D-1, D-7): la COMMESSA. Le sue righe
    --     NON_EMESSA dal lettore, ciascuna dal verbo del suo genere:
    --     - con sorgente (documento o consumo): la primitiva col registro,
    --       limitata a QUESTA commessa (p_commessa_id, 20261012-18); lo
    --       stato del preventivo lo riproietta il trigger delle righe;
    --     - RETTIFICA: l'annullo dell'accredito (il reso torna da
    --       accreditare), per riga di reso: l'unita' e' l'accredito intero;
    --     - ONERE: l'annullo della riga manuale, col suo registro.
    --     Una riga senza sorgente e' ONERE o RETTIFICA per vincolo di
    --     tabella (20261012-27): ogni riga ha il suo verbo.
    IF p_documento = 'COMMESSA' THEN
        v_motivo := format('Ritiro all''annullo confermato della commessa %s', p_id);

        FOR v_sorgente IN
            SELECT DISTINCT ca.sorgente_tipo_id, ca.sorgente_id, ca.sorgente_uid
              FROM vendite.fn_documento_legami(p_documento, p_id) AS l
              JOIN vendite.commesse_attivita ca ON ca.id = l.riga_id
             WHERE ca.sorgente_tipo_id IS NOT NULL
        LOOP
            PERFORM vendite.fn_ritira_commessa_attivita_da_sorgente(
                v_sorgente.sorgente_tipo_id, v_sorgente.sorgente_id, v_sorgente.sorgente_uid,
                v_motivo, p_id);
        END LOOP;

        FOR v_resi_riga_id IN
            SELECT DISTINCT l.origine_riga_id
              FROM vendite.fn_documento_legami(p_documento, p_id) AS l
             WHERE l.origine = 'RESO_VENDITA'
               AND l.origine_riga_id IS NOT NULL
             ORDER BY l.origine_riga_id
        LOOP
            PERFORM vendite.fn_annulla_accredito_riga_reso(v_resi_riga_id, v_motivo);
        END LOOP;

        FOR v_ca_id IN
            SELECT l.riga_id
              FROM vendite.fn_documento_legami(p_documento, p_id) AS l
             WHERE l.origine = 'ONERE'
             ORDER BY l.riga_id
        LOOP
            PERFORM vendite.fn_annulla_commessa_attivita(v_ca_id, v_motivo);
        END LOOP;
    END IF;

    RETURN v_legami;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_ritira_legami(p_documento character varying, p_id bigint, p_legami_confermati integer)
IS 'La conferma e il ritiro dei consumi di un documento che si annulla. p_documento e'' il codice della sorgente (DDT_VENDITA, ORDINE_VENDITA, PREVENTIVO, CONTRATTO, COMMESSA, OFFERTA_COMMERCIALE). Prima solleva il primo motivo della check che il guard della testata solleverebbe (script.fn_check_preventivo_annullabile, fn_check_ordine_annullabile, fn_check_commessa_annullabile, fn_check_offerta_annullabile, fn_check_sorgente_chiudibile per bolla e contratto): chi annulla non conferma un ritiro che il cambio di stato rifiuterebbe. Poi la conferma: chi annulla dichiara quanti legami ha visto (vendite.fn_documento_legami); se non corrisponde, E_DOC_ANNULLO_CON_LEGAMI, lo stesso avviso del guard. Apre la porta del ritiro (GUC transazionale zeroerp.doc_ritira_legami = ''<codice della sorgente>:<id>'', letta da vendite.fn_doc_porta_ritiro_ammette) e la lascia aperta: la chiude il verbo dopo il cambio di stato, perche'' il guard dell''annullo la legge per i legami di provenienza. Ritira: della bolla, i legami con ordini e resi (vendite.fn_ddt_riga_ritira_legami); dell''ordine, il consumo delle righe di preventivo (preventivo_riga_id a NULL; lo stato del preventivo lo proietta vendite.fn_preventivo_proietta_stato_smistamento); le righe di commessa NON_EMESSA del documento (vendite.fn_ritira_commessa_attivita_da_sorgente, col registro); della commessa, ogni riga NON_EMESSA col verbo del suo genere (con sorgente fn_ritira_commessa_attivita_da_sorgente limitata alla commessa, RETTIFICA vendite.fn_annulla_accredito_riga_reso, ONERE vendite.fn_annulla_commessa_attivita). La chiave delle righe di commessa del documento la da'' script.fn_sorgente_documento. La provenienza (l''offerta, la revisione precedente dell''offerta) non si ritira: il rientro dell''offerta lo scrive vendite.fn_offerta_proietta_stato_revisione. Ritorna i legami confermati, 0 se non ce n''erano. SECURITY INVOKER, EXECUTE a nessuno: lo chiamano i verbi DEFINER di annullo (vendite.fn_annulla_ddt, fn_annulla_ordine, fn_annulla_preventivo, fn_annulla_contratto, fn_annulla_commessa, fn_annulla_offerta), che bloccano la testata prima.';
```

</div>

---
{% include-markdown "signature-core.md" %}
