{% include-markdown "it/dbzero/vendite/manual/fn_guard_lotto_fatture_stato_coerente.md" %}
# ⚙️ Funzione `fn_guard_lotto_fatture_stato_coerente`

```sql
CREATE FUNCTION fn_guard_lotto_fatture_stato_coerente(p_lotto_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_guard_lotto_fatture_stato_coerente(p_lotto_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
-- rev 2026-08-04 (D-M): via i due predicati su lf.esclusa e il
--   campo `esclusa` dal jsonb di diagnostica. Quel campo serviva
--   a spiegare perche' una fattura NON compariva fra le
--   incoerenti: con il flag morto diceva sempre false, cioe'
--   occupava spazio nel messaggio senza informare. Resta la sola
--   eccezione `critical`, che e' viva.
DECLARE
  v_stato_lotto vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
  v_count       integer;
  v_dettaglio   jsonb;
BEGIN
  IF p_lotto_id IS NULL OR p_lotto_id <= 0 THEN
    RETURN;
  END IF;

  -- Il lotto puo' essere stato cancellato nella stessa transazione:
  -- essendo il check differito, qui la riga potrebbe non esserci piu'.
  SELECT l.stato_doc_fiscale_id
    INTO v_stato_lotto
    FROM vendite.fatturazione_lotti l
   WHERE l.id = p_lotto_id;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  -- Limite documentato: senza stato lotto il confronto non e'
  -- significativo (vedi testata del changeset).
  IF v_stato_lotto IS NULL THEN
    RETURN;
  END IF;

  -- Fatture disallineate, esclusa l'eccezione di semantica.
  -- Conteggio completo: e' il numero riportato nel messaggio.
  SELECT count(*)
    INTO v_count
    FROM vendite.fatturazione_lotti_fatture lf
    JOIN vendite.fatture f ON f.id = lf.fattura_id
   WHERE lf.lotto_id = p_lotto_id
     AND COALESCE(f.critical, FALSE) IS FALSE
     AND f.stato_doc_fiscale_id IS DISTINCT FROM v_stato_lotto;

  IF v_count = 0 THEN
    RETURN;
  END IF;

  SELECT jsonb_agg(x.riga ORDER BY x.fattura_id)
    INTO v_dettaglio
    FROM (
      SELECT f.id AS fattura_id,
             jsonb_build_object(
               'fattura_id',       f.id,
               'stato_fattura_id', f.stato_doc_fiscale_id,
               'critical',         COALESCE(f.critical, FALSE)
             ) AS riga
        FROM vendite.fatturazione_lotti_fatture lf
        JOIN vendite.fatture f ON f.id = lf.fattura_id
       WHERE lf.lotto_id = p_lotto_id
         AND COALESCE(f.critical, FALSE) IS FALSE
         AND f.stato_doc_fiscale_id IS DISTINCT FROM v_stato_lotto
       ORDER BY f.id
       LIMIT 20
    ) x;

  PERFORM script.fn_log_and_raise_error(
    'vendite',
    'fn_guard_lotto_fatture_stato_coerente',
    'E_LOTTO_FATTURE_STATO_INCOERENTE',
    jsonb_build_object(
      'detail',              'Stato fatture non allineato allo stato del lotto a fine transazione',
      'lotto_id',            p_lotto_id,
      'stato_lotto_id',      v_stato_lotto,
      'fatture_incoerenti',  COALESCE(v_dettaglio, '[]'::jsonb),
      'totale_incoerenti',   v_count,
      'rimedio',             'SELECT vendite.fn_sync_lotto_fatture_stato(' || p_lotto_id::text || ', <stato_target>)'
    ),
    NULL::uuid,
    p_lotto_id::text,
    v_count::text
  );
END;
$function$

COMMENT ON FUNCTION vendite.fn_guard_lotto_fatture_stato_coerente(p_lotto_id bigint)
IS 'Guard dell''invariante lotto <-> fatture: solleva E_LOTTO_FATTURE_STATO_INCOERENTE (556) se il lotto ha fatture non critical con stato_doc_fiscale_id diverso dal proprio. Pensata per essere invocata da un CONSTRAINT TRIGGER DEFERRED (valutazione al COMMIT): gli stati intermedi dentro la transazione sono leciti. No-op se il lotto non esiste piu'' o ha stato NULL. rev 2026-08-04 (D-M): via l''eccezione `esclusa` — il flag era dormiente — e via il campo omonimo dal jsonb di diagnostica, che diceva sempre false. Resta la sola eccezione `critical`, che e'' viva e valorizzata da fn_sync_fatture_log_critical_lotto.';
```

</div>

---
{% include-markdown "signature-core.md" %}
