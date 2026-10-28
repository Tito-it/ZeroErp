{% include-markdown "it/dbzero/script/manual/fn_check_articolo_riga_su_contesto.md" %}
# ⚙️ Funzione `fn_check_articolo_riga_su_contesto`

```sql
CREATE FUNCTION fn_check_articolo_riga_su_contesto(p_contesto jsonb, p_articolo_id uuid, p_natura_vendita_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_articolo_riga_su_contesto(p_contesto jsonb, p_articolo_id uuid, p_natura_vendita_id bigint DEFAULT NULL::bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

DECLARE
    v_motivi       jsonb := '[]'::jsonb;
    v_documento    config.tipi_entita.codice%TYPE := p_contesto ->> 'documento';
    v_documento_id bigint := (p_contesto ->> 'documento_id')::bigint;
    v_tipo_ecc     vendite.tipo_eccezione_contratto
                       := (p_contesto ->> 'tipo_eccezione')::vendite.tipo_eccezione_contratto;
    v_padre_id     catalogo.articoli.id%TYPE := (p_contesto ->> 'articolo_padre_id')::uuid;
    v_codice       catalogo.articoli.codice%TYPE;
    v_solo_comp    catalogo.articoli.is_solo_componente%TYPE;
    v_natura_id    config.nature_vendita.id%TYPE;
    v_destinazione config.nature_vendita.destinazione_tipo%TYPE;
    v_natura_descr config.nature_vendita.descrizione%TYPE;
    v_listino_id   vendite.listini.id%TYPE := (p_contesto ->> 'listino_id')::bigint;
    v_versione_id  vendite.listini_versioni.id%TYPE := (p_contesto ->> 'listino_versione_id')::bigint;
    v_etichetta    text := p_contesto ->> 'etichetta';
    v_in_listino   boolean;
    v_composito    catalogo.articoli.is_composito%TYPE;
    v_tipologia    catalogo.articoli.listino_tipologia_id%TYPE;
    v_iva          catalogo.articoli.iva_id%TYPE;
    v_tip_listino  vendite.listini.tipologia_id%TYPE := (p_contesto ->> 'listino_tipologia_id')::bigint;
    v_padre_codice catalogo.articoli.codice%TYPE := p_contesto ->> 'padre_codice';
    v_padre_iva    catalogo.articoli.iva_id%TYPE := (p_contesto ->> 'padre_iva_id')::bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui l'articolo NON puo' stare in una riga del
    --   documento del contesto. '[]' = ammesso. Non solleva: lo fa
    --   il guard di tabella (§12.5.2).
    -- Ritorna: array ORDINATO di
    --   {codice, reason, reason_key, dettaglio, valori}.
    -- =========================================================
    IF v_documento IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'script.fn_check_articolo_riga_su_contesto',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_contesto'),
            NULL::uuid,
            'p_contesto senza documento: va costruito da script.fn_articolo_riga_contesto');
    END IF;

    IF p_articolo_id IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT a.codice, a.is_solo_componente,
           COALESCE(p_natura_vendita_id, a.natura_vendita_id),
           a.is_composito, a.listino_tipologia_id, a.iva_id
      INTO v_codice, v_solo_comp, v_natura_id, v_composito, v_tipologia, v_iva
      FROM catalogo.articoli a
     WHERE a.id = p_articolo_id;
    IF NOT FOUND THEN
        RETURN v_motivi;
    END IF;

    -- =========================== PROMO ============================
    -- Una promo si crea solo se il calcolo del prezzo la puo'
    -- applicare (D-6). Il composito la riceve (prezzo da
    -- un'eccezione di contratto): non e' un motivo.
    IF v_documento = 'PROMO_ARTICOLO' THEN
        -- 1. Solo componente: nessun prezzo a se', e in contesto
        --    bundle il resolver salta la promo.
        IF v_solo_comp IS TRUE THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_PROMO_ARTICOLO_SOLO_COMPONENTE',
                'reason',     'SOLO_COMPONENTE',
                'reason_key', 'vendite.promo_articoli.articolo_reason.solo_componente',
                'dettaglio',  jsonb_build_object(
                                  'campo',       'articolo_id',
                                  'documento',   v_documento,
                                  'articolo_id', p_articolo_id),
                'valori',     jsonb_build_array(v_codice));
        END IF;

        RETURN v_motivi;
    END IF;

    -- ===================== VERSIONE DI LISTINO =====================
    -- La riga standalone (vendite.listini_righe). Il composito sta nella
    -- versione per un'altra strada, coi suoi componenti: qui e' un motivo.
    IF v_documento = 'LISTINO_VERSIONE' THEN
        -- 1. Solo componente (D-3).
        IF v_solo_comp IS TRUE THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_ARTICOLO_SOLO_COMPONENTE',
                'reason',     'SOLO_COMPONENTE',
                'reason_key', 'vendite.righe.articolo_reason.solo_componente',
                'dettaglio',  jsonb_build_object(
                                  'campo',       'articolo_id',
                                  'documento',   v_documento,
                                  'articolo_id', p_articolo_id),
                'valori',     jsonb_build_array());
        END IF;

        -- 2. Composito: il suo prezzo e' la somma dei componenti.
        IF v_composito IS TRUE THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_LISTINO_RIGA_COMPOSITO_VIETATO',
                'reason',     'COMPOSITO_COME_BUNDLE',
                'reason_key', 'vendite.righe.articolo_reason.composito_come_bundle',
                'dettaglio',  jsonb_build_object(
                                  'campo',       'articolo_id',
                                  'documento',   v_documento,
                                  'articolo_id', p_articolo_id),
                'valori',     jsonb_build_array(v_codice));
        END IF;

        -- 3. La tipologia: mancante, o diversa da quella del listino.
        IF v_tipologia IS NULL THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_ARTICOLO_TIPOLOGIA_MANCANTE',
                'reason',     'TIPOLOGIA_MANCANTE',
                'reason_key', 'vendite.righe.articolo_reason.tipologia_mancante',
                'dettaglio',  jsonb_build_object(
                                  'campo',               'articolo_id',
                                  'documento',           v_documento,
                                  'articolo_id',         p_articolo_id,
                                  'listino_versione_id', v_documento_id,
                                  'listino_tipologia_id', v_tip_listino),
                'valori',     jsonb_build_array(v_codice, v_documento_id::text));
        ELSIF v_tipologia IS DISTINCT FROM v_tip_listino THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE',
                'reason',     'TIPOLOGIA_INCOMPATIBILE',
                'reason_key', 'vendite.righe.articolo_reason.tipologia_incompatibile',
                'dettaglio',  jsonb_build_object(
                                  'campo',                 'articolo_id',
                                  'documento',             v_documento,
                                  'articolo_id',           p_articolo_id,
                                  'articolo_tipologia_id', v_tipologia,
                                  'listino_versione_id',   v_documento_id,
                                  'listino_tipologia_id',  v_tip_listino),
                'valori',     jsonb_build_array(v_codice, v_tipologia::text,
                                                v_tip_listino::text, v_documento_id::text));
        END IF;

        RETURN v_motivi;
    END IF;

    -- ========================== DISTINTA ==========================
    -- Il componente di v_padre_id (catalogo.articoli_componenti).
    -- Il solo componente qui e' il caso normale: non e' un motivo.
    IF v_documento = 'ARTICOLO' THEN
        -- 1. Un articolo non e' componente di se stesso.
        IF p_articolo_id = v_padre_id THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_BOM_COMPONENTE_PADRE',
                'reason',     'COMPONENTE_PADRE',
                'reason_key', 'catalogo.distinta.componente_reason.componente_padre',
                'dettaglio',  jsonb_build_object(
                                  'campo',         'componente_id',
                                  'documento',     v_documento,
                                  'prodotto_id',   v_padre_id,
                                  'componente_id', p_articolo_id),
                'valori',     jsonb_build_array(v_codice));
        END IF;

        -- 2. La distinta ha un livello solo (D-4).
        IF v_composito IS TRUE THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_BOM_COMPONENTE_COMPOSITO',
                'reason',     'COMPONENTE_COMPOSITO',
                'reason_key', 'catalogo.distinta.componente_reason.componente_composito',
                'dettaglio',  jsonb_build_object(
                                  'campo',         'componente_id',
                                  'documento',     v_documento,
                                  'prodotto_id',   v_padre_id,
                                  'componente_id', p_articolo_id),
                'valori',     jsonb_build_array(v_codice, COALESCE(v_padre_codice, v_padre_id::text)));
        END IF;

        -- 3. L'IVA del componente e' quella del padre.
        IF v_iva IS DISTINCT FROM v_padre_iva THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_BOM_IVA_DISCORDANTE',
                'reason',     'IVA_DISCORDANTE',
                'reason_key', 'catalogo.distinta.componente_reason.iva_discordante',
                'dettaglio',  jsonb_build_object(
                                  'campo',         'componente_id',
                                  'documento',     v_documento,
                                  'prodotto_id',   v_padre_id,
                                  'componente_id', p_articolo_id,
                                  'iva_padre_id',  v_padre_iva,
                                  'iva_figlio_id', v_iva),
                'valori',     jsonb_build_array(
                                  COALESCE(v_padre_codice, v_padre_id::text),
                                  COALESCE(p_contesto ->> 'padre_aliquota', '—'),
                                  v_codice,
                                  COALESCE((SELECT i.aliquota_iva::text FROM config.iva i WHERE i.id = v_iva), '—')));
        END IF;

        RETURN v_motivi;
    END IF;

    -- ======================= OFFERTA, CONTRATTO =======================
    IF v_documento IN ('OFFERTA_COMMERCIALE', 'CONTRATTO') THEN
        -- «Nel listino» = una riga della versione espansa (il contesto).
        v_in_listino := v_versione_id IS NOT NULL
                        AND (p_contesto -> 'articoli_listino') @> to_jsonb(p_articolo_id);

        IF v_tipo_ecc = 'ESCLUSIONE'::vendite.tipo_eccezione_contratto THEN
            -- 1. Figlio di bundle: si esclude il bundle, non il componente.
            v_motivi := v_motivi || script.fn_check_esclusione_articolo_documento(
                v_documento, v_documento_id, p_articolo_id);
        ELSE
            -- 1. Solo componente (D-3).
            IF v_solo_comp IS TRUE THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_ARTICOLO_SOLO_COMPONENTE',
                    'reason',     'SOLO_COMPONENTE',
                    'reason_key', 'vendite.righe.articolo_reason.solo_componente',
                    'dettaglio',  jsonb_build_object(
                                      'campo',       'articolo_id',
                                      'documento',   v_documento,
                                      'articolo_id', p_articolo_id),
                    'valori',     jsonb_build_array());
            END IF;

            -- 2. Un kit senza nessun componente attivo non si vende (D-7):
            --    l'init dei componenti lo rifiuterebbe sempre. Il caso «componenti
            --    ma non validi alla data» resta all'init (E_DOC_COMPOSITO_BOM_VUOTA).
            IF v_composito IS TRUE AND NOT EXISTS (
                   SELECT 1 FROM catalogo.articoli_componenti ac
                    WHERE ac.prodotto_id = p_articolo_id
                      AND COALESCE(ac.attivo, TRUE)) THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_ARTICOLO_KIT_SENZA_COMPONENTI',
                    'reason',     'KIT_SENZA_COMPONENTI',
                    'reason_key', 'vendite.righe.articolo_reason.kit_senza_componenti',
                    'dettaglio',  jsonb_build_object(
                                      'campo',       'articolo_id',
                                      'documento',   v_documento,
                                      'articolo_id', p_articolo_id),
                    'valori',     jsonb_build_array(v_codice));
            END IF;

            -- 3. Tipologia fuori utility: la stessa domanda del form
            --    delle erogazioni, composta (erogazione e fonte NULL).
            v_motivi := v_motivi || script.fn_check_riga_erogazione(
                v_documento, v_documento_id, p_articolo_id,
                v_tipo_ecc, NULL, NULL);

            -- 4. Nessuna erogazione ammessa (§8.1).
            IF NOT EXISTS (SELECT 1 FROM vendite.fn_articolo_erogazioni(p_articolo_id)) THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_ARTICOLO_SENZA_EROGAZIONE',
                    'reason',     'SENZA_EROGAZIONE',
                    'reason_key', 'vendite.righe.articolo_reason.senza_erogazione',
                    'dettaglio',  jsonb_build_object(
                                      'campo',       'articolo_id',
                                      'documento',   v_documento,
                                      'articolo_id', p_articolo_id),
                    'valori',     jsonb_build_array(v_codice));
            END IF;

            -- 5a. AGGIUNTA di un articolo gia' nel listino.
            IF v_tipo_ecc = 'AGGIUNTA'::vendite.tipo_eccezione_contratto
               AND v_in_listino THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO',
                    'reason',     'AGGIUNTA_GIA_IN_LISTINO',
                    'reason_key', 'vendite.righe.articolo_reason.aggiunta_gia_in_listino',
                    'dettaglio',  jsonb_build_object(
                                      'campo',               'articolo_id',
                                      'documento',           v_documento,
                                      'articolo_id',         p_articolo_id,
                                      'listino_id',          v_listino_id,
                                      'listino_versione_id', v_versione_id),
                    'valori',     jsonb_build_array(v_codice, v_etichetta));
            END IF;
        END IF;

        -- 5b. OVERRIDE ed ESCLUSIONE vivono sul listino (A-5).
        IF v_tipo_ecc <> 'AGGIUNTA'::vendite.tipo_eccezione_contratto THEN
            IF v_versione_id IS NULL THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_RIGA_ECCEZIONE_SENZA_LISTINO',
                    'reason',     'ECCEZIONE_SENZA_LISTINO',
                    'reason_key', 'vendite.righe.articolo_reason.eccezione_senza_listino',
                    'dettaglio',  jsonb_build_object(
                                      'campo',          'articolo_id',
                                      'documento',      v_documento,
                                      'articolo_id',    p_articolo_id,
                                      'tipo_eccezione', v_tipo_ecc,
                                      'listino_id',     v_listino_id),
                    'valori',     jsonb_build_array(v_etichetta));
            ELSIF NOT v_in_listino THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_RIGA_ECCEZIONE_FUORI_LISTINO',
                    'reason',     'ECCEZIONE_FUORI_LISTINO',
                    'reason_key', 'vendite.righe.articolo_reason.eccezione_fuori_listino',
                    'dettaglio',  jsonb_build_object(
                                      'campo',               'articolo_id',
                                      'documento',           v_documento,
                                      'articolo_id',         p_articolo_id,
                                      'tipo_eccezione',      v_tipo_ecc,
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
                              'documento',   v_documento,
                              'articolo_id', p_articolo_id),
            -- Frase chiusa: niente da infilare nei segnaposto.
            'valori',     jsonb_build_array());
    END IF;

    -- 2. Un kit senza nessun componente attivo non si vende (D-7):
    --    l'init dei componenti lo rifiuterebbe sempre. Il caso «componenti
    --    ma non validi alla data» resta all'init (E_DOC_COMPOSITO_BOM_VUOTA).
    IF v_composito IS TRUE AND NOT EXISTS (
           SELECT 1 FROM catalogo.articoli_componenti ac
            WHERE ac.prodotto_id = p_articolo_id
              AND COALESCE(ac.attivo, TRUE)) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_ARTICOLO_KIT_SENZA_COMPONENTI',
            'reason',     'KIT_SENZA_COMPONENTI',
            'reason_key', 'vendite.righe.articolo_reason.kit_senza_componenti',
            'dettaglio',  jsonb_build_object(
                              'campo',       'articolo_id',
                              'documento',   v_documento,
                              'articolo_id', p_articolo_id),
            'valori',     jsonb_build_array(v_codice));
    END IF;

    -- 3. La natura, secondo la destinazione. rev 2026-10-19
    --    (20261019-99, lotto 2b): la destinazione e' il codice della
    --    sorgente, come il documento (ORDINE_VENDITA, era ORDINE).
    IF v_documento = 'PREVENTIVO' AND v_destinazione = 'CONTRATTO' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA',
            'reason',     'RICORRENTE_USA_OFFERTA',
            'reason_key', 'vendite.righe.articolo_reason.ricorrente_usa_offerta',
            'dettaglio',  jsonb_build_object(
                              'campo',             'articolo_id',
                              'documento',         v_documento,
                              'articolo_id',       p_articolo_id,
                              'articolo_codice',   v_codice,
                              'natura_vendita_id', v_natura_id,
                              'destinazione_tipo', v_destinazione),
            'valori',     jsonb_build_array(COALESCE(v_codice, p_articolo_id::text)));
    ELSIF v_documento IN ('ORDINE_VENDITA', 'DDT_VENDITA')
          AND v_destinazione IS DISTINCT FROM 'ORDINE_VENDITA' THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_RIGA_NATURA_NON_AMMESSA',
            'reason',     'NATURA_NON_MERCE',
            'reason_key', 'vendite.righe.articolo_reason.natura_non_merce',
            'dettaglio',  jsonb_build_object(
                              'campo',             'articolo_id',
                              'documento',         v_documento,
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

COMMENT ON FUNCTION script.fn_check_articolo_riga_su_contesto(p_contesto jsonb, p_articolo_id uuid, p_natura_vendita_id bigint)
IS 'Check pura (fn_check_*): i motivi, in ordine DICHIARATO, per cui l''articolo p_articolo_id non puo'' stare in una riga del documento descritto da p_contesto (costruito da script.fn_articolo_riga_contesto: mai a mano; senza documento E_PARAMETRO_INVALIDO). ''[]'' = ammesso; altrimenti {codice, reason, reason_key, dettaglio, valori}. Le regole, per documento, sono quelle scritte nel COMMENT di script.fn_check_articolo_riga, che e'' questa funzione sul contesto letto da quella firma; rev 2026-10-14 (20261014-06, D-7): KIT_SENZA_COMPONENTI (E_ARTICOLO_KIT_SENZA_COMPONENTI), un composito senza nessun legame attivo in catalogo.articoli_componenti, motivo 2 di preventivo, ordine, bolla e di AGGIUNTA e OVERRIDE di offerta e contratto (dopo il solo componente); il caso date-dipendente resta all''init dei componenti (E_DOC_COMPOSITO_BOM_VUOTA). In piu'' PROMO_ARTICOLO (D-6, 2026-10-14): 1. solo componente (E_PROMO_ARTICOLO_SOLO_COMPONENTE: nessun prezzo a se'', e il resolver salta la promo in contesto bundle); il composito non e'' un motivo (riceve la promo quando il contratto gli da'' un prezzo con un''eccezione). p_natura_vendita_id: la natura congelata della riga, se c''e''; altrimenti quella dell''articolo. Due chiamanti, una regola (A-2): la firma di sempre script.fn_check_articolo_riga (i guard di tabella) e il picker catalogo.fn_articoli_ammessi, che legge il contesto una volta e giudica ogni articolo trovato (R-5). Nasce il 2026-10-14 dal corpo di 20261013-59, brief-db-articoli-ammessi-per-documento (Lotto 4, §9.4). ⭐ rev 2026-10-19 (20261019-32, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. Le due check del listino (fn_check_esclusione_articolo_documento, fn_check_riga_erogazione) ricevono il documento del contesto com''e'': la chiave doc_listino non c''e'' piu'' (20261019-31). ⭐ rev 2026-10-19 (20261019-99, brief-db-grammatica-unica-documenti lotto 2b): la destinazione della natura e'' il codice della sorgente (ORDINE_VENDITA, era ORDINE): il motivo NATURA_NON_MERCE di ordine e bolla confronta due codici dello stesso vocabolario.';
```

</div>

---
{% include-markdown "signature-core.md" %}
