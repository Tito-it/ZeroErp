{% include-markdown "it/dbzero/script/manual/fn_get_stato_testata_documento.md" %}
# ⚙️ Funzione `fn_get_stato_testata_documento`

```sql
CREATE FUNCTION fn_get_stato_testata_documento(p_documento text, p_testata_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_get_stato_testata_documento(p_documento text, p_testata_id bigint)
 RETURNS TABLE(stato text, etichetta text)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
BEGIN
  -- =========================================================
  -- Scopo:
  --   Rispondere a «la testata esiste ancora, e in che stato e'?»
  --   SENZA passare dalla RLS delle testate.
  --
  -- Contratto:
  --   - zero righe  -> la testata NON esiste (cancellata, o mai
  --     esistita). Il chiamante deve trattarlo come CASCADE.
  --   - una riga    -> stato = codice_interno, etichetta = frase
  --     per l'operatore.
  --
  -- ⚠️ Lo stato e' NOT NULL su entrambe le testate e la FK verso
  --    config.stati_doc_* garantisce la riga di stato: se la
  --    testata c'e', `stato` non e' mai NULL. Il chiamante puo'
  --    quindi usare l'assenza di riga come segnale, e non deve
  --    distinguere un NULL da un vuoto.
  -- =========================================================
  IF p_testata_id IS NULL OR p_testata_id <= 0 THEN
    RETURN;   -- nessuna riga: il chiamante lo legge come «assente»
  END IF;

  IF p_documento = 'DDT' THEN
    RETURN QUERY
    SELECT s.codice_interno::text,
           concat('DDT ', COALESCE(d.numero, '#' || d.id::text))
      FROM vendite.ddt d
      JOIN config.stati_doc_ddt s ON s.id = d.stato_doc_ddt_id
     WHERE d.id = p_testata_id;

  ELSIF p_documento = 'ORDINE' THEN
    RETURN QUERY
    SELECT s.codice_interno::text,
           concat('Ordine ', COALESCE(o.numero, '#' || o.id::text))
      FROM vendite.ordini o
      JOIN config.stati_doc_ordini s ON s.id = o.stato_doc_ordine_id
     WHERE o.id = p_testata_id;

  ELSE
    -- Errore di CHIAMANTE, non di dato: nessuna persona sceglie
    -- questo valore. Classe TECNICO, messaggio che nomina il
    -- valore ricevuto (fratello di E_RUOLO_APPLICATIVO_NON_GESTITO).
    PERFORM script.fn_log_and_raise_error(
      'script',
      'fn_get_stato_testata_documento',
      'E_DOC_TIPO_NON_GESTITO',
      jsonb_build_object('documento', p_documento,
                         'testata_id', p_testata_id),
      NULL::uuid,
      COALESCE(p_documento, '<null>'));
  END IF;

  RETURN;
END;
$function$

COMMENT ON FUNCTION script.fn_get_stato_testata_documento(p_documento text, p_testata_id bigint)
IS 'Lettore SECURITY DEFINER dello stato e dell''etichetta di una testata DDT/ordine. Nasce il 2026-08-26 per vendite.trgfn_dlt_block_ordrig_ddtrig, che deve distinguere «la testata non c''e'' piu''» (CASCADE partito dalla testata) da «la testata non la vedo» (RLS). ⛔ SECURITY DEFINER perche'' quella distinzione e'' il perno della decisione: misurato sul catalogo, vendite.ddt e vendite.ordini hanno RLS attiva e vendite.ddt_righe / vendite.ordini_righe NO — un chiamante fuori perimetro raggiunge la riga e non vede la testata, e un guard che leggesse sotto RLS diventerebbe fail-open proprio per lui. ⭐ CONTRATTO: zero righe = testata assente; una riga = stato (codice_interno) piu'' etichetta per l''operatore. Lo stato e'' NOT NULL su entrambe le testate e la FK garantisce la riga di stato, quindi l''assenza di riga e'' un segnale non ambiguo. ⚠️ L''etichetta ripiega sull''id quando `numero` e'' NULL, che sui documenti in bozza e'' il caso normale, non un residuo. PERIMETRO: legge due colonne, non scrive, non espone dati riservati. Tipo documento ammesso: DDT | ORDINE; qualunque altro valore e'' un errore di chiamante (E_DOC_TIPO_NON_GESTITO, TECNICO).';
```

---
{% include-markdown "signature-core.md" %}
