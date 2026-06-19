{% include-markdown "it/dbzero/vendite/manual/fn_list_emittibili_lane.md" %}
# ⚙️ Funzione `fn_list_emittibili_lane`

```sql
CREATE FUNCTION fn_list_emittibili_lane(p_competenza_mese date, p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_fatturazione_immediata boolean, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_emittibili_lane(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_fatturazione_immediata boolean DEFAULT NULL::boolean, p_limit integer DEFAULT 1000)
 RETURNS TABLE(emittente_soggetto_ruolo_id bigint, tipo_doc_fiscale_id bigint, utility_id integer, competenza_mese date, total_candidate bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_competenza_mese vendite.commesse_attivita.competenza_mese%TYPE;
BEGIN
  -- =========================================================
  -- Scopo: rispondere al driver batch "quali TERNE distinte
  --   (emittente, tipo_doc, utility) hanno lavoro pronto da
  --   fatturare, e fino a quale competenza creare il lotto".
  -- Criteri:
  --   1. commessa in stato emittibile (stati_commessa.emittibile=true)
  --   2. righe commesse_attivita APPROVATA + NON_EMESSA (allineato pull)
  --   3. tipo_doc_fiscale_id NOT NULL (il lotto lo richiede)
  --   4. competenza CUMULATIVA: competenza_mese <= p_competenza_mese
  --      (coerente con fn_select_attivita_fatturabili); NULL = no limite
  --   5. filtri perimetro BA/utility/emittente; corsia fatturazione_immediata
  -- Grana: (emittente, tipo_doc, utility). utility_id e' NOT NULL a monte
  --   (commesse.utility_id) -> in output mai NULL. La coerenza
  --   c.utility_id = ba.utility_id (E_CLIENTE_UTILITY_MISMATCH_BA in
  --   fn_get_or_create_commessa) garantisce che la terna scoperta qui sia
  --   esattamente quella che fn_select_attivita_fatturabili filtra a valle.
  -- Output per terna: competenza_mese = max(...), total_candidate = count(*).
  -- Regole: p_limit max 10000/default 1000; competenza normalizzata al mese;
  --   STABLE (read-only); LIMIT sulle TERNE.
  -- =========================================================
  IF p_limit IS NULL OR p_limit <= 0 THEN
    p_limit := 1000;
  END IF;
  IF p_limit > 10000 THEN
    p_limit := 10000;
  END IF;

  v_competenza_mese := CASE
    WHEN p_competenza_mese IS NOT NULL
    THEN date_trunc('month', p_competenza_mese)::date
    ELSE NULL
  END;

  RETURN QUERY
  SELECT
    c.emittente_soggetto_ruolo_id,
    ca.tipo_doc_fiscale_id,
    c.utility_id,
    max(ca.competenza_mese)        AS competenza_mese,
    count(ca.id)::bigint           AS total_candidate
  FROM vendite.commesse c
  JOIN vendite.stati_commessa sc
    ON sc.id = c.stato_commessa_id
   AND sc.emittibile = true
  INNER JOIN vendite.commesse_attivita ca
    ON ca.commessa_id = c.id
   AND ca.stato_emissione = 'NON_EMESSA'
   AND ca.stato_approvazione = 'APPROVATA'
   AND ca.tipo_doc_fiscale_id IS NOT NULL
   AND (v_competenza_mese IS NULL OR ca.competenza_mese <= v_competenza_mese)
  WHERE true
    AND (p_billing_account_id IS NULL OR c.billing_account_id = p_billing_account_id)
    AND (p_utility_id IS NULL OR c.utility_id = p_utility_id)
    AND (p_emittente_soggetto_ruolo_id IS NULL OR c.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
    AND (p_fatturazione_immediata IS NULL OR c.fatturazione_immediata = p_fatturazione_immediata)
  GROUP BY
    c.emittente_soggetto_ruolo_id,
    ca.tipo_doc_fiscale_id,
    c.utility_id
  ORDER BY
    c.emittente_soggetto_ruolo_id,
    ca.tipo_doc_fiscale_id,
    c.utility_id
  LIMIT p_limit;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_emittibili_lane(p_competenza_mese date, p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_fatturazione_immediata boolean, p_limit integer)
IS 'Read-only/STABLE: discovery delle corsie (emittente, tipo_doc_fiscale, utility, competenza_mese) pronte da fatturare per il driver batch. Grana per-utility (il lotto e'' segregato per utility: fn_create pretende utility NOT NULL, fn_select filtra ba.utility_id). utility_id mai NULL (commesse.utility_id NOT NULL); coerenza c.utility_id=ba.utility_id garantita da fn_get_or_create_commessa. Criterio APPROVATA+NON_EMESSA, tipo_doc NOT NULL, competenza cumulativa (<=) con output competenza_mese=max. Filtri perimetro + corsia fatturazione_immediata. fn_list_commesse_emittibili resta separata e invariata.';
```

---
{% include-markdown "signature-core.md" %}
