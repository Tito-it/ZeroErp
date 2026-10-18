{% include-markdown "it/dbzero/catalogo/manual/fn_articolo_correggi_struttura.md" %}
# ⚙️ Funzione `fn_articolo_correggi_struttura`

```sql
CREATE FUNCTION fn_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.fn_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_codice    catalogo.articoli.codice%TYPE;
    v_estranee  text;
    v_set       text;
    v_righe     integer;
    v_documenti integer;
    v_elenco    jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Correggere i flag strutturali di un articolo anche se
    --   usato. Solo SUPER_ADMIN. Ordine: permesso, parametri,
    --   articolo, scrittura con la porta aperta, righe vive.
    --   Le colonne ammesse: catalogo.fn_articolo_colonne_struttura().
    -- =========================================================
    PERFORM script.fn_guard_super_admin(
        NULLIF(current_setting('app.current_user_id', true), '')::integer);

    IF p_campi IS NULL OR jsonb_typeof(p_campi) <> 'object' OR p_campi = '{}'::jsonb THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_articolo_correggi_struttura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_campi', 'valore', p_campi),
            NULL::uuid,
            'p_campi: un oggetto con almeno una colonna');
    END IF;

    SELECT string_agg(k, ', ' ORDER BY k)
      INTO v_estranee
      FROM jsonb_object_keys(p_campi) k
     WHERE k <> ALL (catalogo.fn_articolo_colonne_struttura());
    IF p_campi IS NULL OR v_estranee IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_articolo_correggi_struttura', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_campi', 'non_ammesse', v_estranee),
            NULL::uuid,
            'p_campi: colonne non correggibili da qui: ' || v_estranee);
    END IF;

    SELECT a.codice INTO v_codice
      FROM catalogo.articoli a
     WHERE a.id = p_articolo_id
       FOR UPDATE;
    IF p_articolo_id IS NULL OR v_codice IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_articolo_correggi_struttura', 'E_ARTICOLO_NOT_FOUND',
            jsonb_build_object('articolo_id', p_articolo_id),
            NULL::uuid,
            COALESCE(p_articolo_id::text, '<null>'));
    END IF;

    -- Solo le colonne passate (gia' controllate qui sopra), ciascuna col
    -- tipo della sua colonna: jsonb_populate_record fa la conversione.
    SELECT string_agg(format('%1$I = r.%1$I', k), ', ' ORDER BY k)
      INTO v_set
      FROM jsonb_object_keys(p_campi) k;

    PERFORM set_config('zeroerp.articolo_correggi_struttura', p_articolo_id::text, true);

    EXECUTE format(
        'UPDATE catalogo.articoli a
            SET %s
           FROM jsonb_populate_record(NULL::catalogo.articoli, $1) r
          WHERE a.id = $2',
        v_set)
    USING p_campi, p_articolo_id;

    PERFORM set_config('zeroerp.articolo_correggi_struttura', '', true);

    -- Le righe VIVE (attive, documento non chiuso) che con la struttura
    -- nuova l'articolo non puo' piu' avere: il primo motivo della check
    -- dei guard di riga, con la natura e il tipo d'eccezione della riga.
    -- Le sette tabelle sono quelle di script.trgfn_righe_guard_articolo_ammesso.
    SELECT count(*)::integer,
           count(DISTINCT (g.documento, g.documento_id))::integer,
           jsonb_path_query_array(
               jsonb_agg(jsonb_build_object(
                             'documento',    g.documento,
                             'documento_id', g.documento_id,
                             'riga_id',      g.riga_id,
                             'codice',       g.motivo ->> 'codice')
                         ORDER BY g.documento, g.documento_id, g.riga_id),
               '$[0 to 49]')
      INTO v_righe, v_documenti, v_elenco
      FROM (
          SELECT v.documento, v.documento_id, v.riga_id,
                 script.fn_check_articolo_riga(
                     v.documento, v.documento_id, p_articolo_id,
                     v.natura_vendita_id, v.tipo_eccezione) -> 0 AS motivo
            FROM (
                SELECT 'PREVENTIVO'::text, r.preventivo_id, r.id, r.natura_vendita_id,
                       NULL::vendite.tipo_eccezione_contratto
                  FROM vendite.preventivi_righe r
                  JOIN vendite.preventivi t ON t.id = r.preventivo_id
                  JOIN config.stati_doc_preventivi s ON s.id = t.stato_doc_preventivo_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'ORDINE_VENDITA', r.ordine_id, r.id, r.natura_vendita_id, NULL
                  FROM vendite.ordini_righe r
                  JOIN vendite.ordini t ON t.id = r.ordine_id
                  JOIN config.stati_doc_ordini s ON s.id = t.stato_doc_ordine_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'DDT_VENDITA', r.ddt_id, r.id, r.natura_vendita_id, NULL
                  FROM vendite.ddt_righe r
                  JOIN vendite.ddt t ON t.id = r.ddt_id
                  JOIN config.stati_doc_ddt s ON s.id = t.stato_doc_ddt_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'OFFERTA_COMMERCIALE', r.offerta_id, r.id, NULL, r.tipo_eccezione
                  FROM vendite.offerte_commerciali_eccezioni r
                  JOIN vendite.offerte_commerciali t ON t.id = r.offerta_id
                  JOIN config.stati_doc_offerte s ON s.id = t.stato_doc_offerta_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'CONTRATTO', r.contratto_id, r.id, NULL, r.tipo_eccezione
                  FROM vendite.contratti_righe r
                  JOIN vendite.contratti t ON t.id = r.contratto_id
                  JOIN config.stati_doc_contratti s ON s.id = t.stato_doc_contratto_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND s.fase <> 'CHIUSO'
                UNION ALL
                SELECT 'LISTINO_VERSIONE', r.listino_versione_id, r.id, NULL, NULL
                  FROM vendite.listini_righe r
                  JOIN vendite.listini_versioni lv ON lv.id = r.listino_versione_id
                 WHERE r.articolo_id = p_articolo_id AND r.attivo AND lv.stato <> 'CHIUSA'
                UNION ALL
                SELECT 'PROMO_ARTICOLO', p.id, p.id, NULL, NULL
                  FROM vendite.promo_articoli p
                 WHERE p.articolo_id = p_articolo_id AND p.attivo
                   AND (upper_inf(p.validita)
                        OR upper(p.validita) > script.fn_data_operativa())
            ) v(documento, documento_id, riga_id, natura_vendita_id, tipo_eccezione)
      ) g
     WHERE g.motivo IS NOT NULL;

    IF v_righe > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'catalogo', 'catalogo.fn_articolo_correggi_struttura', 'E_ARTICOLO_STRUTTURA_RIGHE_APERTE',
            jsonb_build_object(
                'articolo_id', p_articolo_id,
                'campi',       p_campi,
                'righe',       v_elenco),
            NULL::uuid,
            v_codice,
            v_righe::text,
            v_documenti::text);
    END IF;
END;
$function$

COMMENT ON FUNCTION catalogo.fn_articolo_correggi_struttura(p_articolo_id uuid, p_campi jsonb)
IS 'VERBO (A-10 di brief-db-articoli-ammessi-per-documento, 2026-10-13): la porta amministratore della regola «un articolo usato non cambia i flag strutturali» (catalogo.trgfn_articoli_guard_struttura_se_usato). Solo SUPER_ADMIN (script.fn_guard_super_admin su app.current_user_id; altrimenti E_PERMESSO_NEGATO). p_campi: oggetto jsonb con le sole colonne da cambiare fra quelle di catalogo.fn_articolo_colonne_struttura() (vuoto, non oggetto o chiavi estranee -> E_PARAMETRO_INVALIDO); articolo assente -> E_ARTICOLO_NOT_FOUND. Scrive le sole colonne passate, ciascuna col tipo della sua colonna (jsonb_populate_record), con la GUC transazionale zeroerp.articolo_correggi_struttura = id dell''articolo, che il guard onora solo insieme al proprietario della tabella (questo verbo e'' SECURITY DEFINER), e la richiude. Gli altri guard dell''articolo parlano lo stesso. Poi rigiudica le righe VIVE dell''articolo (attive, documento non chiuso: fase dello stato diversa da CHIUSO per preventivo, ordine, bolla, offerta e contratto; versione di listino non CHIUSA; promo col periodo non finito) con script.fn_check_articolo_riga, la check dei guard di riga, nelle sette tabelle dove e'' montato script.trgfn_righe_guard_articolo_ammesso e in tutte le aziende: se una non e'' piu'' ammessa -> E_ARTICOLO_STRUTTURA_RIGHE_APERTE (valori: codice, righe, documenti; dettaglio.righe: le prime 50, col codice del motivo) e la correzione si annulla. Le righe gia'' scritte non si toccano. La via normale resta un articolo nuovo. search_path bloccato; EXECUTE solo all''app. Rev 2026-10-18 (R-DB-3): le colonne dalla sede leggibile. Rev 2026-10-18 (A-11 di Tid): le righe vive.';
```

---
{% include-markdown "signature-core.md" %}
