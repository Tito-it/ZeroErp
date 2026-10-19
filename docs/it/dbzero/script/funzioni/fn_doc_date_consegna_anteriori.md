{% include-markdown "it/dbzero/script/manual/fn_doc_date_consegna_anteriori.md" %}
# ⚙️ Funzione `fn_doc_date_consegna_anteriori`

```sql
CREATE FUNCTION fn_doc_date_consegna_anteriori(p_documento character varying, p_testata_id bigint, p_data_documento date, p_riga jsonb, p_riga_prima jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_doc_date_consegna_anteriori(p_documento character varying, p_testata_id bigint, p_data_documento date DEFAULT NULL::date, p_riga jsonb DEFAULT NULL::jsonb, p_riga_prima jsonb DEFAULT NULL::jsonb)
 RETURNS TABLE(colonna text, data_consegna date, data_documento date, posizione integer)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$

-- ⚠️ Tipi nudi DICHIARATI: p_documento e' un selettore senza
--   colonna-vocabolario; p_testata_id e le date sono POLIMORFI (due
--   testate, tre colonne di consegna su due tabelle).
DECLARE
  -- Il montaggio di ogni documento: nomi di oggetti scritti qui,
  -- mai presi da un argomento (finiscono in un EXECUTE).
  v_testata   text;
  v_righe     text;
  v_col_padre text;
  v_colonne   text[];
  v_data_doc  date := p_data_documento;
  v_prima     jsonb := p_riga_prima;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Quali date di consegna vengono prima della data del
  --   documento? Dalla riga che si scrive (p_riga) o dalle
  --   righe attive della testata (p_riga NULL), contro la data
  --   data (p_data_documento) o quella della testata.
  --   Consumatori: script.trgfn_doc_righe_guard_data_consegna,
  --   script.trgfn_doc_testata_guard_data_consegna_righe.
  -- =========================================================

  -- ⭐ L'ELENCO delle date di consegna, per documento: la sola sede.
  IF p_documento = 'ORDINE_VENDITA' THEN
    v_testata   := 'vendite.ordini';
    v_righe     := 'vendite.ordini_righe';
    v_col_padre := 'ordine_id';
    v_colonne   := ARRAY['data_consegna_richiesta_cliente',
                         'data_consegna_confermata'];
  ELSIF p_documento = 'PREVENTIVO' THEN
    v_testata   := 'vendite.preventivi';
    v_righe     := 'vendite.preventivi_righe';
    v_col_padre := 'preventivo_id';
    v_colonne   := ARRAY['data_consegna_richiesta_cliente'];
  ELSE
    PERFORM script.fn_log_and_raise_error(
      'script', 'script.fn_doc_date_consegna_anteriori',
      'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('documento',  p_documento,
                         'testata_id', p_testata_id),
      NULL::uuid,
      COALESCE(p_documento, '<null>'));
  END IF;

  -- Testata assente o id non valido: niente da dire, parla la FK
  -- (come script.fn_get_stato_testata_documento).
  IF p_testata_id IS NULL OR p_testata_id <= 0 THEN
    RETURN;
  END IF;

  IF v_data_doc IS NULL THEN
    EXECUTE format('SELECT t.data FROM %s t WHERE t.id = $1', v_testata)
       INTO v_data_doc
      USING p_testata_id;
    IF v_data_doc IS NULL THEN
      RETURN;
    END IF;
  END IF;

  -- 1. Dalla RIGA che si scrive.
  IF p_riga IS NOT NULL THEN
    -- Una riga spenta non fa parte del documento.
    IF (p_riga ->> 'attivo')::boolean IS FALSE THEN
      RETURN;
    END IF;
    -- Torna attiva, o cambia testata: si giudica tutta.
    IF (v_prima ->> 'attivo')::boolean IS FALSE
       OR (v_prima -> v_col_padre) IS DISTINCT FROM (p_riga -> v_col_padre) THEN
      v_prima := NULL;
    END IF;

    RETURN QUERY
    SELECT c.col,
           (p_riga ->> c.col)::date,
           v_data_doc,
           c.n::integer
      FROM unnest(v_colonne) WITH ORDINALITY AS c(col, n)
     WHERE (v_prima IS NULL OR (p_riga -> c.col) IS DISTINCT FROM (v_prima -> c.col))
       AND NOT script.fn_data_consegna_ammessa((p_riga ->> c.col)::date, v_data_doc)
     ORDER BY c.n;
    RETURN;
  END IF;

  -- 2. Dalla TESTATA: la prima data fuori regola di ogni colonna,
  --    fra le righe attive.
  RETURN QUERY EXECUTE format(
    'SELECT c.col, min((to_jsonb(r) ->> c.col)::date), $2, c.n::integer
       FROM %s r
      CROSS JOIN unnest($3) WITH ORDINALITY AS c(col, n)
      WHERE r.%I = $1
        AND r.attivo IS NOT FALSE
        AND NOT script.fn_data_consegna_ammessa((to_jsonb(r) ->> c.col)::date, $2)
      GROUP BY c.col, c.n
      ORDER BY c.n', v_righe, v_col_padre)
    USING p_testata_id, v_data_doc, v_colonne;
END;
$function$

COMMENT ON FUNCTION script.fn_doc_date_consegna_anteriori(p_documento character varying, p_testata_id bigint, p_data_documento date, p_riga jsonb, p_riga_prima jsonb)
IS 'Lettore SECURITY DEFINER (2026-10-13, collaudo date di consegna): le date di consegna anteriori alla data del documento. Con p_riga (la riga che si scrive, to_jsonb(NEW)): le sue date fuori regola contro la data della testata — con p_riga_prima (to_jsonb(OLD)) solo quelle cambiate, tutte se la riga torna attiva o cambia testata; una riga spenta non si giudica. Senza p_riga: per ogni colonna la prima data fuori regola fra le righe attive della testata, contro p_data_documento (la data che la testata sta per prendere). Righe: (colonna, data_consegna, data_documento, posizione); zero righe = niente da dire, anche con testata assente o id NULL/<= 0 (parla la FK). ⭐ Sede UNICA dell''elenco delle date di consegna: ORDINE data_consegna_richiesta_cliente, data_consegna_confermata; PREVENTIVO data_consegna_richiesta_cliente. Il confronto e'' script.fn_data_consegna_ammessa. Selettore ignoto: E_DOC_TIPO_NON_GESTITO (TECNICO). ⛔ SECURITY DEFINER: testate e righe hanno la RLS, e sotto quella di chi scrive il guard diventerebbe fail-open (come script.fn_get_stato_testata_documento). Consumatori: script.trgfn_doc_righe_guard_data_consegna, script.trgfn_doc_testata_guard_data_consegna_righe. ⭐ rev 2026-10-19 (20261019-44, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

---
{% include-markdown "signature-core.md" %}
