{% include-markdown "it/dbzero/vendite/manual/fn_guard_lotto_fatture_stato_coerente.md" %}
# ⚙️ Funzione `fn_guard_lotto_fatture_stato_coerente`

```sql
CREATE FUNCTION fn_guard_lotto_fatture_stato_coerente(p_lotto_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
-- rev 2026-10-24 (20261024-34, brief-modello-documento-vendita
--   R-1): l'eccezione `critical` copre la fattura rimasta
--   INDIETRO, non quella gia' congelata davanti a un lotto che
--   non lo e'. Letto dal vocabolario (congela_fiscale,
--   is_abortito), non dall'ordine degli stati. Le fatture
--   incoerenti si LEGGONO dalla sede unica
--   vendite.vw_lotti_fatture_incoerenti: il predicato non si
--   ricopia qui.
DECLARE
  v_stato_lotto vendite.fatturazione_lotti.stato_doc_fiscale_id%TYPE;
  -- CONTEGGIO delle fatture incoerenti: tipo nudo.
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

  -- Fatture disallineate, dalla sede unica (eccezione critical
  -- compresa, R-1). Conteggio completo: e' il numero riportato
  -- nel messaggio.
  SELECT count(*)
    INTO v_count
    FROM vendite.vw_lotti_fatture_incoerenti i
   WHERE i.lotto_id = p_lotto_id;

  IF v_count = 0 THEN
    RETURN;
  END IF;

  SELECT jsonb_agg(x.riga ORDER BY x.fattura_id)
    INTO v_dettaglio
    FROM (
      SELECT i.fattura_id,
             jsonb_build_object(
               'fattura_id',       i.fattura_id,
               'stato_fattura_id', i.stato_fattura_id,
               'critical',         i.fattura_critical
             ) AS riga
        FROM vendite.vw_lotti_fatture_incoerenti i
       WHERE i.lotto_id = p_lotto_id
       ORDER BY i.fattura_id
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
IS 'Guard dell''invariante lotto <-> fatture: solleva E_LOTTO_FATTURE_STATO_INCOERENTE (556) se il lotto ha fatture con stato_doc_fiscale_id diverso dal proprio. Eccezione: la fattura critical (in errore) che resta INDIETRO; ⛔ non una fattura critical gia'' congelata e non abortita (config.stati_doc_fiscale.congela_fiscale / is_abortito) davanti a un lotto non congelato: un documento definitivo non convive con uno in errore nello stesso lotto (R-1 di Tid, 2026-10-24). Pensata per essere invocata da un CONSTRAINT TRIGGER DEFERRED (valutazione al COMMIT): gli stati intermedi dentro la transazione sono leciti. No-op se il lotto non esiste piu'' o ha stato NULL. rev 2026-08-04 (D-M): via l''eccezione `esclusa`, dormiente. rev 2026-10-24 (20261024-34, brief-modello-documento-vendita R-1): l''eccezione critical solo per chi resta indietro; le fatture incoerenti si leggono dalla sede unica vendite.vw_lotti_fatture_incoerenti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
