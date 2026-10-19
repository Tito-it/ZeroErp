{% include-markdown "it/dbzero/script/manual/fn_check_listino_cambiabile.md" %}
# ⚙️ Funzione `fn_check_listino_cambiabile`

```sql
CREATE FUNCTION fn_check_listino_cambiabile(p_documento character varying, p_documento_id bigint, p_listino_da bigint, p_listino_a bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_listino_cambiabile(p_documento character varying, p_documento_id bigint, p_listino_da bigint, p_listino_a bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

-- ⚠️ Tipi nudi DICHIARATI: p_documento e' un selettore (CONTRATTO |
--   OFFERTA) senza colonna di vocabolario; p_documento_id e' POLIMORFO
--   (l'id di due testate diverse). I conteggi sono calcolati.
DECLARE
    v_righe      bigint;
    v_eccezioni  bigint;
    v_etichetta  text;
    v_motivi     jsonb := jsonb_build_array();
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire perche' il listino di un documento (contratto,
    --   offerta) NON puo' passare da p_listino_da a p_listino_a.
    --   '[]' = puo'. Non solleva: lo fa il guard
    --   script.trgfn_doc_guard_listino_con_righe, che la CHIAMA
    --   (linee-guida-sql §12.5.2). Sui VALORI: la chiama un guard
    --   BEFORE ROW.
    --
    -- Motivi (il primo e' quello che il guard solleva):
    --   1. LISTINO_CON_RIGHE — un listino nuovo (messo dove non
    --      c'era, o sostituito) su un documento con righe attive:
    --      le righe sono state caricate contro il listino di prima;
    --   2. LISTINO_RIMOZIONE_CON_ECCEZIONI — il listino tolto con
    --      eccezioni OVERRIDE o ESCLUSIONE attive: senza listino
    --      non vogliono dire niente. Le AGGIUNTE valgono anche
    --      senza listino.
    --   Listino invariato: nessun motivo.
    -- Le righe del documento: contratti_righe (contratto_id) per il
    --   CONTRATTO, offerte_commerciali_eccezioni (offerta_id) per
    --   l'OFFERTA — le stesse righe, la stessa regola (D-11 di
    --   brief-db-testata-dopo-emissione).
    -- =========================================================
    IF p_documento IS NULL OR p_documento NOT IN ('CONTRATTO', 'OFFERTA_COMMERCIALE') THEN
        -- Errore di CHIAMANTE, non di dato (stesso codice dei lettori
        -- di documento, script.fn_get_stato_testata_documento).
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_listino_cambiabile', 'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('documento', p_documento,
                               'documento_id', p_documento_id),
            NULL::uuid,
            COALESCE(p_documento, '<null>'));
    END IF;

    IF p_listino_da IS NOT DISTINCT FROM p_listino_a THEN
        RETURN v_motivi;
    END IF;

    IF p_documento = 'CONTRATTO' THEN
        SELECT count(*),
               count(*) FILTER (WHERE r.tipo_eccezione IN ('OVERRIDE', 'ESCLUSIONE'))
          INTO v_righe, v_eccezioni
          FROM vendite.contratti_righe r
         WHERE r.contratto_id = p_documento_id
           AND r.attivo IS TRUE;
    ELSE
        SELECT count(*),
               count(*) FILTER (WHERE r.tipo_eccezione IN ('OVERRIDE', 'ESCLUSIONE'))
          INTO v_righe, v_eccezioni
          FROM vendite.offerte_commerciali_eccezioni r
         WHERE r.offerta_id = p_documento_id
           AND r.attivo IS TRUE;
    END IF;

    IF v_righe = 0 THEN
        RETURN v_motivi;
    END IF;

    -- L'etichetta della frase, dal lettore DEFINER delle testate.
    SELECT t.etichetta INTO v_etichetta
      FROM script.fn_get_stato_testata_documento(p_documento, p_documento_id) AS t;
    v_etichetta := COALESCE(v_etichetta, lower(p_documento) || ' #' || p_documento_id::text);

    -- 1. Un listino nuovo sotto righe gia' caricate.
    IF p_listino_a IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_DOC_LISTINO_CAMBIO_CON_RIGHE',
            'reason',     'LISTINO_CON_RIGHE',
            'dettaglio',  jsonb_build_object('campo', 'listino_id',
                                             'documento', p_documento,
                                             'documento_id', p_documento_id,
                                             'listino_da', p_listino_da,
                                             'listino_a', p_listino_a,
                                             'righe', v_righe),
            'valori',     jsonb_build_array(v_etichetta, v_righe::text)));
    -- 2. Il listino tolto sotto eccezioni che ne dipendono.
    ELSIF v_eccezioni > 0 THEN
        v_motivi := v_motivi || jsonb_build_array(jsonb_build_object(
            'codice',     'E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI',
            'reason',     'LISTINO_RIMOZIONE_CON_ECCEZIONI',
            'dettaglio',  jsonb_build_object('campo', 'listino_id',
                                             'documento', p_documento,
                                             'documento_id', p_documento_id,
                                             'listino_da', p_listino_da,
                                             'eccezioni', v_eccezioni),
            'valori',     jsonb_build_array(v_etichetta, v_eccezioni::text)));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_listino_cambiabile(p_documento character varying, p_documento_id bigint, p_listino_da bigint, p_listino_a bigint)
IS 'Check pura (2026-10-11, brief-db-testata-dopo-emissione §11, R-DB-4 e D-11 di Tid): i motivi per cui il listino di un documento (CONTRATTO: vendite.contratti_righe; OFFERTA: vendite.offerte_commerciali_eccezioni) non puo'' passare da p_listino_da a p_listino_a. ''[]'' = puo''. Motivi in ordine: 1) E_DOC_LISTINO_CAMBIO_CON_RIGHE (reason LISTINO_CON_RIGHE): un listino nuovo, messo o sostituito, su un documento con righe attive, caricate contro il listino di prima; 2) E_DOC_LISTINO_RIMOZIONE_CON_ECCEZIONI (reason LISTINO_RIMOZIONE_CON_ECCEZIONI): il listino tolto con eccezioni OVERRIDE o ESCLUSIONE attive (le AGGIUNTE valgono anche senza listino). Campo listino_id in dettaglio.campo; valori: l''etichetta del documento e il conteggio. Listino invariato: nessun motivo; p_documento fuori da CONTRATTO | OFFERTA: E_DOC_TIPO_NON_GESTITO (errore di chiamante). Le due regole vivevano solo nel backend del contratto (contratti_service.update_contratto, E_CONTRATTO_CAMPI_BLOCCATI_CON_RIGHE ed E_CONTRATTO_LISTINO_RIMOZIONE_CON_ECCEZIONI, ritirati), e l''offerta, con le stesse righe, non ne aveva nessuna. Lettore: script.trgfn_doc_guard_listino_con_righe (solleva il primo motivo). Fuori bozza il listino e'' gia'' fermo dal lock di testata: le due regole contano in bozza. ⭐ rev 2026-10-19 (20261019-45, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

---
{% include-markdown "signature-core.md" %}
