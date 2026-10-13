{% include-markdown "it/dbzero/script/manual/fn_check_articolo_riga.md" %}
# ⚙️ Funzione `fn_check_articolo_riga`

```sql
CREATE FUNCTION fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint DEFAULT NULL::bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto DEFAULT NULL::vendite.tipo_eccezione_contratto)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_motivi       jsonb := '[]'::jsonb;
    v_codice       catalogo.articoli.codice%TYPE;
    v_solo_comp    catalogo.articoli.is_solo_componente%TYPE;
    v_natura_id    config.nature_vendita.id%TYPE;
    v_destinazione config.nature_vendita.destinazione_tipo%TYPE;
    v_natura_descr config.nature_vendita.descrizione%TYPE;
    -- ⚠️ v_doc_listino nudo: la grammatica OFFERTA | CONTRATTO dei
    --   lettori del listino (ponte A-8, vedi il COMMENT).
    v_doc_listino  text;
    v_listino_id   vendite.listini.id%TYPE;
    v_versione_id  vendite.listini_versioni.id%TYPE;
    v_etichetta    text;
    v_in_listino   boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui l'articolo NON puo' stare in una riga del
    --   documento p_documento. '[]' = ammesso. Non solleva: lo fa
    --   il guard di tabella, che la CHIAMA (§12.5.2).
    -- Ritorna: array ORDINATO di
    --   {codice, reason, reason_key, dettaglio, valori}.
    -- =========================================================
    IF p_documento IS NULL
       OR p_documento NOT IN ('PREVENTIVO', 'ORDINE_VENDITA', 'DDT_VENDITA',
                              'OFFERTA_COMMERCIALE', 'CONTRATTO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'script.fn_check_articolo_riga',
            'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento', p_documento),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    -- Offerta e contratto: la riga e' un'eccezione al listino, e il
    -- tipo d'eccezione decide le regole.
    IF p_tipo_eccezione IS NULL
       AND p_documento IN ('OFFERTA_COMMERCIALE', 'CONTRATTO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'script.fn_check_articolo_riga',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_eccezione', 'documento', p_documento),
            NULL::uuid,
            'p_tipo_eccezione obbligatorio per ' || p_documento);
    END IF;

    IF p_articolo_id IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT a.codice, a.is_solo_componente,
           COALESCE(p_natura_vendita_id, a.natura_vendita_id)
      INTO v_codice, v_solo_comp, v_natura_id
      FROM catalogo.articoli a
     WHERE a.id = p_articolo_id;
    IF NOT FOUND THEN
        RETURN v_motivi;
    END IF;

    -- ======================= OFFERTA, CONTRATTO =======================
    IF p_documento IN ('OFFERTA_COMMERCIALE', 'CONTRATTO') THEN
        v_doc_listino := CASE p_documento
                             WHEN 'OFFERTA_COMMERCIALE' THEN 'OFFERTA'
                             ELSE 'CONTRATTO' END;

        SELECT lo.listino_id, lo.listino_versione_id
          INTO v_listino_id, v_versione_id
          FROM vendite.fn_documento_listino_operativo(v_doc_listino, p_documento_id) lo;

        SELECT t.etichetta INTO v_etichetta
          FROM script.fn_get_stato_testata_documento(v_doc_listino, p_documento_id) t;
        v_etichetta := COALESCE(v_etichetta, initcap(v_doc_listino) || ' #' || p_documento_id::text);

        -- «Nel listino» = una riga della versione espansa: standalone
        -- E bundle (il bundle sta nel listino coi suoi componenti, non
        -- in listini_righe). La stessa base su cui il drawer applica
        -- OVERRIDE ed ESCLUSIONE (vendite.fn_documento_righe_preview).
        v_in_listino := v_versione_id IS NOT NULL AND EXISTS (
            SELECT 1 FROM vendite.fn_espandi_listino_versione(v_versione_id, NULL, NULL) b
             WHERE b.articolo_id = p_articolo_id);

        IF p_tipo_eccezione = 'ESCLUSIONE'::vendite.tipo_eccezione_contratto THEN
            -- 1. Figlio di bundle: si esclude il bundle, non il componente.
            v_motivi := v_motivi || script.fn_check_esclusione_articolo_documento(
                v_doc_listino, p_documento_id, p_articolo_id);
        ELSE
            -- 1. Solo componente (D-3).
            IF v_solo_comp IS TRUE THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_ARTICOLO_SOLO_COMPONENTE',
                    'reason',     'SOLO_COMPONENTE',
                    'reason_key', 'vendite.righe.articolo_reason.solo_componente',
                    'dettaglio',  jsonb_build_object(
                                      'campo',       'articolo_id',
                                      'documento',   p_documento,
                                      'articolo_id', p_articolo_id),
                    'valori',     jsonb_build_array());
            END IF;

            -- 2. Tipologia fuori utility: la stessa domanda del form
            --    delle erogazioni, composta (erogazione e fonte NULL).
            v_motivi := v_motivi || script.fn_check_riga_erogazione(
                v_doc_listino, p_documento_id, p_articolo_id,
                p_tipo_eccezione, NULL, NULL);

            -- 3. Nessuna erogazione ammessa (§8.1).
            IF NOT EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(p_articolo_id)) THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_ARTICOLO_SENZA_EROGAZIONE',
                    'reason',     'SENZA_EROGAZIONE',
                    'reason_key', 'vendite.righe.articolo_reason.senza_erogazione',
                    'dettaglio',  jsonb_build_object(
                                      'campo',       'articolo_id',
                                      'documento',   p_documento,
                                      'articolo_id', p_articolo_id),
                    'valori',     jsonb_build_array(v_codice));
            END IF;

            -- 4a. AGGIUNTA di un articolo gia' nel listino.
            IF p_tipo_eccezione = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
               AND v_in_listino THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO',
                    'reason',     'AGGIUNTA_GIA_IN_LISTINO',
                    'reason_key', 'vendite.righe.articolo_reason.aggiunta_gia_in_listino',
                    'dettaglio',  jsonb_build_object(
                                      'campo',               'articolo_id',
                                      'documento',           p_documento,
                                      'articolo_id',         p_articolo_id,
                                      'listino_id',          v_listino_id,
                                      'listino_versione_id', v_versione_id),
                    'valori',     jsonb_build_array(v_codice, v_etichetta));
            END IF;
        END IF;

        -- 4b. OVERRIDE ed ESCLUSIONE vivono sul listino (A-5).
        IF p_tipo_eccezione <> 'AGGIUNTA'::vendite.tipo_eccezione_contratto THEN
            IF v_versione_id IS NULL THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_RIGA_ECCEZIONE_SENZA_LISTINO',
                    'reason',     'ECCEZIONE_SENZA_LISTINO',
                    'reason_key', 'vendite.righe.articolo_reason.eccezione_senza_listino',
                    'dettaglio',  jsonb_build_object(
                                      'campo',          'articolo_id',
                                      'documento',      p_documento,
                                      'articolo_id',    p_articolo_id,
                                      'tipo_eccezione', p_tipo_eccezione,
                                      'listino_id',     v_listino_id),
                    'valori',     jsonb_build_array(v_etichetta));
            ELSIF NOT v_in_listino THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_RIGA_ECCEZIONE_FUORI_LISTINO',
                    'reason',     'ECCEZIONE_FUORI_LISTINO',
                    'reason_key', 'vendite.righe.articolo_reason.eccezione_fuori_listino',
                    'dettaglio',  jsonb_build_object(
                                      'campo',               'articolo_id',
                                      'documento',           p_documento,
                                      'articolo_id',         p_articolo_id,
                                      'tipo_eccezione',      p_tipo_eccezione,
                                      'listino_id',          v_listino_id,
                                      'listino_versione_id', v_versione_id),
                    'valori',     jsonb_build_array(v_codice, v_etichetta));
            END IF;
        END IF;

        RETURN v_motivi;
    END IF;

    -- =================== PREVENTIVO, ORDINE, BOLLA ====================
    SELECT nv.destinazione_tipo, COALESCE(nv.descrizione, nv.codice)
      INTO v_destinazione, v_natura_descr
      FROM config.nature_vendita nv
     WHERE nv.id = v_natura_id;

    -- 1. Solo componente: vive solo dentro un kit (D-3).
    IF v_solo_comp IS TRUE THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ARTICOLO_SOLO_COMPONENTE',
            'reason',     'SOLO_COMPONENTE',
            'reason_key', 'vendite.righe.articolo_reason.solo_componente',
            'dettaglio',  jsonb_build_object(
                              'campo',       'articolo_id',
                              'documento',   p_documento,
                              'articolo_id', p_articolo_id),
            -- Frase chiusa: niente da infilare nei segnaposto.
            'valori',     jsonb_build_array());
    END IF;

    -- 2. La natura, secondo la destinazione.
    IF p_documento = 'PREVENTIVO' AND v_destinazione = 'CONTRATTO' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA',
            'reason',     'RICORRENTE_USA_OFFERTA',
            'reason_key', 'vendite.righe.articolo_reason.ricorrente_usa_offerta',
            'dettaglio',  jsonb_build_object(
                              'campo',             'articolo_id',
                              'documento',         p_documento,
                              'articolo_id',       p_articolo_id,
                              'articolo_codice',   v_codice,
                              'natura_vendita_id', v_natura_id,
                              'destinazione_tipo', v_destinazione),
            'valori',     jsonb_build_array(COALESCE(v_codice, p_articolo_id::text)));
    ELSIF p_documento IN ('ORDINE_VENDITA', 'DDT_VENDITA')
          AND v_destinazione IS DISTINCT FROM 'ORDINE' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_NATURA_NON_AMMESSA',
            'reason',     'NATURA_NON_MERCE',
            'reason_key', 'vendite.righe.articolo_reason.natura_non_merce',
            'dettaglio',  jsonb_build_object(
                              'campo',             'articolo_id',
                              'documento',         p_documento,
                              'articolo_id',       p_articolo_id,
                              'natura_vendita_id', v_natura_id,
                              'destinazione_tipo', v_destinazione),
            'valori',     jsonb_build_array(
                              COALESCE(v_codice, p_articolo_id::text),
                              COALESCE(v_natura_descr, '?')));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto)
IS 'Check pura (fn_check_*): i motivi, in ordine DICHIARATO, per cui un articolo non puo'' stare in una riga del documento p_documento (codice di config.tipi_entita: PREVENTIVO | ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO, altrimenti E_DOC_TIPO_NON_GESTITO). ''[]'' = ammesso; altrimenti {codice, reason, reason_key, dettaglio, valori}. Preventivo, ordine, bolla: 1. SOLO_COMPONENTE (E_ARTICOLO_SOLO_COMPONENTE); 2. la natura secondo la destinazione (preventivo: la ricorrenza va in offerta, E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA; ordine e bolla: solo merce, E_RIGA_NATURA_NON_AMMESSA); la natura e'' quella della riga (p_natura_vendita_id, congelata) se c''e'', altrimenti quella dell''articolo. Offerta e contratto (rev 2026-10-13, 20261013-55, Lotto 3b): p_tipo_eccezione obbligatorio (E_PARAMETRO_INVALIDO). AGGIUNTA e OVERRIDE: 1. SOLO_COMPONENTE; 2. TIPOLOGIA_FUORI_UTILITY (composta da script.fn_check_riga_erogazione senza erogazione); 3. SENZA_EROGAZIONE (vendite.fn_articolo_erogazioni vuota, E_ARTICOLO_SENZA_EROGAZIONE); 4. il listino operativo (le righe di vendite.fn_espandi_listino_versione, standalone e bundle): AGGIUNTA gia'' in listino (E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO), OVERRIDE senza listino (E_RIGA_ECCEZIONE_SENZA_LISTINO) o fuori listino (E_RIGA_ECCEZIONE_FUORI_LISTINO, A-5). ESCLUSIONE: 1. FIGLIO_DI_BUNDLE (composta da script.fn_check_esclusione_articolo_documento); 2. senza listino o fuori listino (A-5). ⚠️ Ponte A-8: i lettori del listino parlano ancora OFFERTA | CONTRATTO; la traduzione da OFFERTA_COMMERCIALE sta qui e si ritira col giro BE/FE. Una sola check per tipo di riga (A-2): la chiama il guard di tabella script.trgfn_righe_guard_articolo_ammesso (solleva il primo motivo) e il picker degli articoli ammessi; l''ordine dell''array e'' il contratto. Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-2, A-5, D-1, D-2, D-3).';
```

---
{% include-markdown "signature-core.md" %}
