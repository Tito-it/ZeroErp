{% include-markdown "it/dbzero/script/manual/fn_articolo_riga_contesto.md" %}
# ⚙️ Funzione `fn_articolo_riga_contesto`

```sql
CREATE FUNCTION fn_articolo_riga_contesto(p_documento text, p_documento_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_articolo_riga_contesto(p_documento text, p_documento_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto DEFAULT NULL::vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$


DECLARE
    v_contesto     jsonb;
    v_listino_id   vendite.listini.id%TYPE;
    v_versione_id  vendite.listini_versioni.id%TYPE;
    v_etichetta    text;
    v_tip_listino  vendite.listini.tipologia_id%TYPE;
    v_padre_codice catalogo.articoli.codice%TYPE;
    v_padre_iva    catalogo.articoli.iva_id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Il lato DOCUMENTO di script.fn_check_articolo_riga: cio'
    --   che i motivi leggono e che non dipende dall'articolo,
    --   letto una volta. Valida i parametri.
    -- Ritorna: il contesto (jsonb) che riceve
    --   script.fn_check_articolo_riga_su_contesto.
    -- =========================================================
    IF p_documento IS NULL
       OR p_documento NOT IN ('PREVENTIVO', 'ORDINE_VENDITA', 'DDT_VENDITA',
                              'OFFERTA_COMMERCIALE', 'CONTRATTO',
                              'LISTINO_VERSIONE', 'ARTICOLO',
                              'PROMO_ARTICOLO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'script.fn_articolo_riga_contesto',
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
            'script.fn_articolo_riga_contesto',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_tipo_eccezione', 'documento', p_documento),
            NULL::uuid,
            'p_tipo_eccezione obbligatorio per ' || p_documento);
    END IF;

    -- La distinta: la «testata» e' l'articolo padre (uuid), non un id di documento.
    IF p_articolo_padre_id IS NULL AND p_documento = 'ARTICOLO' THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo',
            'script.fn_articolo_riga_contesto',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_articolo_padre_id', 'documento', p_documento),
            NULL::uuid,
            'p_articolo_padre_id obbligatorio per ARTICOLO (la distinta)');
    END IF;

    v_contesto := jsonb_build_object(
        'documento',         p_documento,
        'documento_id',      p_documento_id,
        'tipo_eccezione',    p_tipo_eccezione,
        'articolo_padre_id', p_articolo_padre_id);

    -- Versione di listino: la tipologia del suo listino.
    IF p_documento = 'LISTINO_VERSIONE' THEN
        SELECT l.tipologia_id INTO v_tip_listino
          FROM vendite.listini_versioni lv
          JOIN vendite.listini l ON l.id = lv.listino_id
         WHERE lv.id = p_documento_id;

        RETURN v_contesto || jsonb_build_object('listino_tipologia_id', v_tip_listino);
    END IF;

    -- Distinta: il padre.
    IF p_documento = 'ARTICOLO' THEN
        SELECT a.codice, a.iva_id INTO v_padre_codice, v_padre_iva
          FROM catalogo.articoli a
         WHERE a.id = p_articolo_padre_id;

        RETURN v_contesto || jsonb_build_object(
            'padre_codice',   v_padre_codice,
            'padre_iva_id',   v_padre_iva,
            'padre_aliquota', (SELECT i.aliquota_iva::text FROM config.iva i
                                WHERE i.id = v_padre_iva));
    END IF;

    -- Offerta e contratto: il listino operativo e la sua versione
    -- ESPANSA, una volta.
    IF p_documento IN ('OFFERTA_COMMERCIALE', 'CONTRATTO') THEN
        SELECT lo.listino_id, lo.listino_versione_id
          INTO v_listino_id, v_versione_id
          FROM vendite.fn_documento_listino_operativo(p_documento, p_documento_id) lo;

        SELECT t.etichetta INTO v_etichetta
          FROM script.fn_get_stato_testata_documento(p_documento, p_documento_id) t;
        v_etichetta := COALESCE(v_etichetta, initcap(replace(lower(p_documento), '_', ' ')) || ' #' || p_documento_id::text);

        -- «Nel listino» = una riga della versione espansa: standalone
        -- E bundle (il bundle sta nel listino coi suoi componenti, non
        -- in listini_righe). La stessa base su cui il drawer applica
        -- OVERRIDE ed ESCLUSIONE (vendite.fn_documento_righe_preview).
        RETURN v_contesto || jsonb_build_object(
            'listino_id',          v_listino_id,
            'listino_versione_id', v_versione_id,
            'etichetta',           v_etichetta,
            'articoli_listino',    COALESCE(
                (SELECT jsonb_agg(DISTINCT b.articolo_id)
                   FROM vendite.fn_espandi_listino_versione(v_versione_id, NULL, NULL) b),
                jsonb_build_array()));
    END IF;

    -- Preventivo, ordine, bolla, promo: i motivi non leggono il documento.
    RETURN v_contesto;
END;
$function$

COMMENT ON FUNCTION script.fn_articolo_riga_contesto(p_documento text, p_documento_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid)
IS 'Il lato DOCUMENTO di script.fn_check_articolo_riga, letto una volta: valida i parametri (p_documento fra PREVENTIVO | ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO | LISTINO_VERSIONE | ARTICOLO | PROMO_ARTICOLO, altrimenti E_DOC_TIPO_NON_GESTITO; p_tipo_eccezione obbligatorio per offerta e contratto e p_articolo_padre_id per ARTICOLO, altrimenti E_PARAMETRO_INVALIDO) e restituisce il contesto jsonb che riceve script.fn_check_articolo_riga_su_contesto. Sempre: documento, documento_id, tipo_eccezione, articolo_padre_id. LISTINO_VERSIONE: listino_tipologia_id. ARTICOLO (la distinta): padre_codice, padre_iva_id, padre_aliquota. OFFERTA_COMMERCIALE e CONTRATTO: listino_id, listino_versione_id, etichetta, articoli_listino (gli articolo_id di vendite.fn_espandi_listino_versione, standalone e bundle; [] senza versione). documento_id non e'' obbligatorio: preventivo, ordine, bolla e promo non leggono il documento (l''obbligo di A-1 e'' del picker catalogo.fn_articoli_ammessi). Nasce per R-5: il picker valuta molti articoli sullo stesso documento, e rileggere il listino espanso per ognuno costava piu'' del giudizio. Sotto RLS (SECURITY INVOKER): un documento che l''operatore non vede da'' un contesto senza listino. Nasce il 2026-10-14, brief-db-articoli-ammessi-per-documento (Lotto 4, §9.4). ⭐ rev 2026-10-19 (20261019-31, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. Il ponte A-8 si restringe: il listino operativo riceve il codice com''e'' (OFFERTA_COMMERCIALE), e la chiave doc_listino esce dal contesto (era una copia di documento). Traduce ancora, in un punto solo, verso script.fn_get_stato_testata_documento (l''etichetta): grammatica delle testate, lotto 2. ⭐ rev 2026-10-19 (20261019-53, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. Il ponte A-8 non c''e'' piu'': nessuna traduzione fra il vocabolario delle entita'' e quello delle testate.';
```

</div>

---
{% include-markdown "signature-core.md" %}
