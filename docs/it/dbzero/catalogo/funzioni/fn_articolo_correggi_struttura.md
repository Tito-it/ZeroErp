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
    v_prima     text[];
    v_righe     integer;
    v_documenti integer;
    v_elenco    jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Correggere i flag strutturali di un articolo anche se
    --   usato. Solo SUPER_ADMIN. Ordine: permesso, parametri,
    --   articolo, righe non ammesse prima, scrittura con la
    --   porta aperta, righe rese non ammesse.
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

    -- Le righe vive gia' non ammesse PRIMA: non sono della correzione.
    SELECT array_agg(n.documento || ':' || n.riga_id)
      INTO v_prima
      FROM catalogo.fn_articolo_righe_vive_non_ammesse(p_articolo_id) n;

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

    -- Le righe che la correzione RENDE non ammesse: non ammesse dopo,
    -- ammesse prima.
    SELECT count(*)::integer,
           count(DISTINCT (n.documento, n.documento_id))::integer,
           jsonb_path_query_array(
               jsonb_agg(jsonb_build_object(
                             'documento',    n.documento,
                             'documento_id', n.documento_id,
                             'riga_id',      n.riga_id,
                             'codice',       n.motivo ->> 'codice')
                         ORDER BY n.documento, n.documento_id, n.riga_id),
               '$[0 to 49]')
      INTO v_righe, v_documenti, v_elenco
      FROM catalogo.fn_articolo_righe_vive_non_ammesse(p_articolo_id) n
     WHERE (n.documento || ':' || n.riga_id) <> ALL (COALESCE(v_prima, '{}'::text[]));

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
IS 'VERBO (A-10 di brief-db-articoli-ammessi-per-documento, 2026-10-13): la porta amministratore della regola «un articolo usato non cambia i flag strutturali» (catalogo.trgfn_articoli_guard_struttura_se_usato). Solo SUPER_ADMIN (script.fn_guard_super_admin su app.current_user_id; altrimenti E_PERMESSO_NEGATO). p_campi: oggetto jsonb con le sole colonne da cambiare fra quelle di catalogo.fn_articolo_colonne_struttura() (vuoto, non oggetto o chiavi estranee -> E_PARAMETRO_INVALIDO); articolo assente -> E_ARTICOLO_NOT_FOUND. Scrive le sole colonne passate, ciascuna col tipo della sua colonna (jsonb_populate_record), con la GUC transazionale zeroerp.articolo_correggi_struttura = id dell''articolo, che il guard onora solo insieme al proprietario della tabella (questo verbo e'' SECURITY DEFINER), e la richiude. Gli altri guard dell''articolo parlano lo stesso. Poi confronta le righe vive non ammesse (catalogo.fn_articolo_righe_vive_non_ammesse: attive, documento non chiuso, primo motivo di script.fn_check_articolo_riga) prima e dopo la scrittura, in tutte le aziende: se la correzione RENDE non ammessa almeno una riga -> E_ARTICOLO_STRUTTURA_RIGHE_APERTE (valori: codice, righe, documenti; dettaglio.righe: le prime 50, col codice del motivo) e la correzione si annulla. Una riga gia'' non ammessa prima non blocca. Le righe gia'' scritte non si toccano. La via normale resta un articolo nuovo. search_path bloccato; EXECUTE solo all''app. Rev 2026-10-18 (R-DB-3): le colonne dalla sede leggibile. Rev 2026-10-18 (A-11 di Tid): le righe vive (20261018-72), poi solo quelle che la correzione rende non ammesse (20261018-74).';
```

---
{% include-markdown "signature-core.md" %}
