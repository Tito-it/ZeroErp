# ⚙️ Funzione `fn_check_listino_documento`

```sql
CREATE FUNCTION fn_check_listino_documento(p_listino_id bigint, p_utility_id integer, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_listino_documento(p_listino_id bigint, p_utility_id integer, p_emittente_fiscale_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_listino_utility   vendite.listini.utility_id%TYPE;
    v_listino_emittente vendite.listini.emittente_soggetto_ruolo_id%TYPE;
    v_doc_emittente     anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
    -- Interruttore: il listino si legge (sotto RLS) o no.
    v_listino_letto     boolean;
    v_motivi            jsonb := jsonb_build_array();
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire perche' un listino NON puo' essere quello di un
    --   documento (contratto, offerta) di questa utility e di questo
    --   emittente. '[]' = puo'. Non solleva: lo fa il guard
    --   script.trgfn_doc_guard_listino_documento, che la CHIAMA, come
    --   la lettura per il form vendite.fn_listini_selezionabili.
    --   Sui VALORI: la chiama un guard BEFORE ROW.
    --
    -- Motivi (il primo e' quello che il guard solleva):
    --   1. LISTINO_UTILITY_DIVERSA — campo listino_id;
    --   2. LISTINO_EMITTENTE_DIVERSO — campo listino_id. Anche un
    --      listino che sotto RLS non si legge: il documento e' nel
    --      perimetro di chi agisce, il listino no, quindi e' di un
    --      altro emittente.
    --   Listino NULL (negoziato puro): nessun motivo.
    -- =========================================================
    IF p_listino_id IS NULL THEN
        RETURN jsonb_build_array();
    END IF;

    SELECT l.utility_id, l.emittente_soggetto_ruolo_id
      INTO v_listino_utility, v_listino_emittente
      FROM vendite.listini l
     WHERE l.id = p_listino_id;
    v_listino_letto := FOUND;

    -- La traduzione: emittente del documento (PK) -> il suo ruolo.
    SELECT ef.soggetto_ruolo_id
      INTO v_doc_emittente
      FROM anagrafiche.emittenti_fiscali ef
     WHERE ef.id = p_emittente_fiscale_id;

    -- 1. La utility del listino dev'essere quella del documento.
    IF v_listino_letto AND v_listino_utility IS DISTINCT FROM p_utility_id THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_DOC_LISTINO_UTILITY_DIVERSA',
            'reason',     'LISTINO_UTILITY_DIVERSA',
            'dettaglio',  jsonb_build_object('campo', 'listino_id',
                                             'listino_id', p_listino_id,
                                             'utility_listino', v_listino_utility,
                                             'utility_documento', p_utility_id),
            -- Frase chiusa: niente da infilare nei segnaposto.
            'valori',     jsonb_build_array()));
    END IF;

    -- 2. L'emittente del listino dev'essere quello del documento.
    IF NOT v_listino_letto
       OR v_listino_emittente IS DISTINCT FROM v_doc_emittente THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_DOC_LISTINO_EMITTENTE_DIVERSO',
            'reason',     'LISTINO_EMITTENTE_DIVERSO',
            'dettaglio',  jsonb_build_object('campo', 'listino_id',
                                             'listino_id', p_listino_id,
                                             'listino_letto', v_listino_letto,
                                             'emittente_fiscale_id', p_emittente_fiscale_id),
            'valori',     jsonb_build_array()));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_listino_documento(p_listino_id bigint, p_utility_id integer, p_emittente_fiscale_id bigint)
IS 'Check pura: i motivi per cui un listino non può essere quello di un documento (vendite.contratti, vendite.offerte_commerciali) di questa utility e di questo emittente. ''[]'' = può. Sui valori (listino, utility del documento, emittente_fiscale_id del documento): la chiamano un guard BEFORE ROW e, in creazione, la lettura per il form. Motivi in ordine: 1) E_DOC_LISTINO_UTILITY_DIVERSA (reason LISTINO_UTILITY_DIVERSA): la utility del listino non è quella del documento; 2) E_DOC_LISTINO_EMITTENTE_DIVERSO (reason LISTINO_EMITTENTE_DIVERSO): l''emittente del listino (emittente_soggetto_ruolo_id) non è quello del documento, tradotto qui da emittente_fiscale_id; anche un listino che sotto RLS non si legge (fuori dal perimetro di chi agisce, mentre il documento ci sta). Campo listino_id in dettaglio.campo, frase chiusa. Listino NULL (negoziato puro del contratto): nessun motivo. Utility o emittente NULL: diversi per costruzione. Lettori: script.trgfn_doc_guard_listino_documento (solleva il primo motivo) e vendite.fn_listini_selezionabili (propone solo i listini senza motivi). Nasce il 2026-10-08, brief-db-offerta-emissione-ed-erogazione §F.2 (decisione F-2 di Tid).';
```

</div>

---
{% include-markdown "signature-core.md" %}
