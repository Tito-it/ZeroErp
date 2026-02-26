{% include-markdown "it/dbzero/vendite/manual/fn_list_commessa_attivita.md" %}
# ⚙️ Funzione `fn_list_commessa_attivita`

```sql
CREATE FUNCTION fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying DEFAULT NULL::character varying, p_stato_approvazione character varying DEFAULT NULL::character varying, p_competenza_mese date DEFAULT NULL::date, p_limit integer DEFAULT 1000, p_offset integer DEFAULT 0)
 RETURNS TABLE(id bigint, commessa_id bigint, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, competenza_mese date, competenza_dal date, competenza_al date, prezzo_snapshot numeric, prezzo_bloccato boolean, prezzo_da_riallineare boolean, stato_approvazione character varying, stato_emissione character varying, sorgente_tipo_id bigint, sorgente_codice character varying, meta jsonb, data_update timestamp with time zone)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_competenza_mese vendite.commesse_attivita.competenza_mese%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Elencare le righe commesse_attivita di una commessa
  --   con filtri opzionali e paginazione.
  --   Usata dal backend per visualizzazione dettaglio
  --   commessa e pre-validazione PULL_COMMESSA.
  --
  -- Criteri:
  --   1. p_commessa_id obbligatorio
  --   2. Filtri opzionali: stato_emissione, stato_approvazione,
  --      competenza_mese
  --   3. JOIN sorgenti per sorgente_codice (evita N+1)
  --
  -- Regole:
  --   - p_limit max 10000, default 1000
  --   - p_offset >= 0, default 0
  --   - p_competenza_mese normalizzato al primo del mese
  --   - funzione STABLE (read-only)
  -- =========================================================
  IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_list_commessa_attivita','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','commessa_id obbligatorio','commessa_id',p_commessa_id)
      ),
      NULL::uuid,
      'commessa_id obbligatorio'
    );
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM vendite.commesse c WHERE c.id = p_commessa_id
  ) THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_list_commessa_attivita','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','commessa non trovata','commessa_id',p_commessa_id)
      ),
      NULL::uuid,
      concat('commessa non trovata: ', p_commessa_id::text)
    );
  END IF;

  -- Sanitize limit/offset
  IF p_limit IS NULL OR p_limit <= 0 THEN
    p_limit := 1000;
  END IF;
  IF p_limit > 10000 THEN
    p_limit := 10000;
  END IF;
  IF p_offset IS NULL OR p_offset < 0 THEN
    p_offset := 0;
  END IF;

  -- Normalizza al primo del mese
  v_competenza_mese := CASE
    WHEN p_competenza_mese IS NOT NULL
    THEN date_trunc('month', p_competenza_mese)::date
    ELSE NULL
  END;

  RETURN QUERY
  SELECT
    ca.id,
    ca.commessa_id,
    ca.segment_key,
    ca.articolo_id,
    ca.istanza_utility_id,
    ca.data_attivita,
    ca.uom_id,
    ca.quantita,
    ca.competenza_mese,
    ca.competenza_dal,
    ca.competenza_al,
    ca.prezzo_snapshot,
    ca.prezzo_bloccato,
    ca.prezzo_da_riallineare,
    ca.stato_approvazione,
    ca.stato_emissione,
    ca.sorgente_tipo_id,
    s.codice AS sorgente_codice,
    ca.meta,
    ca.data_update
  FROM vendite.commesse_attivita ca
  LEFT JOIN config.sorgenti s
    ON s.id = ca.sorgente_tipo_id
  WHERE ca.commessa_id = p_commessa_id
    AND (p_stato_emissione IS NULL OR ca.stato_emissione = p_stato_emissione)
    AND (p_stato_approvazione IS NULL OR ca.stato_approvazione = p_stato_approvazione)
    AND (v_competenza_mese IS NULL OR ca.competenza_mese = v_competenza_mese)
  ORDER BY ca.id
  LIMIT p_limit
  OFFSET p_offset;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer)
IS 'Read-only: elenca righe commesse_attivita per una commessa con filtri opzionali (stato_emissione, stato_approvazione, competenza_mese) e paginazione LIMIT/OFFSET. JOIN sorgenti per codice. Usata dal backend per dettaglio commessa e pre-validazione PULL_COMMESSA.';
```

---
{% include-markdown "signature-core.md" %}
