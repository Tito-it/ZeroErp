{% include-markdown "it/dbzero/vendite/manual/fn_list_commesse_emittibili.md" %}
# ⚙️ Funzione `fn_list_commesse_emittibili`

```sql
CREATE FUNCTION fn_list_commesse_emittibili(p_competenza_mese date, p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_fatturazione_immediata boolean, p_limit integer, p_gruppi text[])
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_commesse_emittibili(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint, p_fatturazione_immediata boolean DEFAULT NULL::boolean, p_limit integer DEFAULT 1000, p_gruppi text[] DEFAULT NULL::text[])
 RETURNS TABLE(commessa_id bigint, codice character varying, stato_commessa_id bigint, stato_commessa character varying, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, fatturazione_immediata boolean, competenza_dal date, competenza_al date, total_non_emesse bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
  v_competenza_mese vendite.commesse_attivita.competenza_mese%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Elencare le commesse pronte per l'emissione verso AF.
  --   Usata dal backend come discovery per il batch di
  --   emissione (fn_emit_attivita_fatturabili_da_commessa).
  --
  -- Criteri:
  --   1. Stato emittibile (stati_commessa.emittibile = true)
  --   2. Esistono righe commesse_attivita NON_EMESSA
  --   3. Competenza: se p_competenza_mese fornito, filtra righe
  --      commesse_attivita il cui competenza_mese coincide
  --      (coerente con pipeline AF che opera per mese)
  --   4. Filtri opzionali per perimetro billing/utility/emittente
  --   5. Filtro opzionale corsia: p_fatturazione_immediata
  --      (true=solo immediate / false=solo differite /
  --       NULL=indifferente, comportamento storico)
  --   6. rev 2026-07-27: p_gruppi restringe alle commesse che
  --      contengono almeno una riga di un gruppo richiesto.
  --      NON sostituisce il filtro per RIGA dentro l'emit: qui si
  --      sceglie QUALI COMMESSE visitare, li' QUALI RIGHE emettere.
  --      NULL = nessuna restrizione (comportamento storico).
  --
  -- Regole:
  --   - p_limit max 10000, default 1000
  --   - p_competenza_mese normalizzato al primo del mese
  --   - funzione STABLE (read-only)
  -- =========================================================
  IF p_limit IS NULL OR p_limit <= 0 THEN
    p_limit := 1000;
  END IF;
  IF p_limit > 10000 THEN
    p_limit := 10000;
  END IF;

  -- Normalizza al primo del mese
  v_competenza_mese := CASE
    WHEN p_competenza_mese IS NOT NULL
    THEN date_trunc('month', p_competenza_mese)::date
    ELSE NULL
  END;

  RETURN QUERY
  SELECT
    c.id AS commessa_id,
    c.codice,
    c.stato_commessa_id,
    sc.codice AS stato_commessa,
    c.billing_account_id,
    c.utility_id,
    c.emittente_soggetto_ruolo_id,
    c.fatturazione_immediata,
    c.competenza_dal,
    c.competenza_al,
    count(ca.id)::bigint AS total_non_emesse
  FROM vendite.commesse c
  JOIN vendite.stati_commessa sc
    ON sc.id = c.stato_commessa_id
   AND sc.emittibile = true
  INNER JOIN vendite.commesse_attivita ca
    ON ca.commessa_id = c.id
   AND ca.stato_emissione = 'NON_EMESSA'
   AND (v_competenza_mese IS NULL OR ca.competenza_mese = v_competenza_mese)
  WHERE true
    -- Filtro perimetro billing/utility/emittente
    AND (p_billing_account_id IS NULL OR c.billing_account_id = p_billing_account_id)
    AND (p_utility_id IS NULL OR c.utility_id = p_utility_id)
    AND (p_emittente_soggetto_ruolo_id IS NULL OR c.emittente_soggetto_ruolo_id = p_emittente_soggetto_ruolo_id)
    -- Filtro corsia immediata/differita (NULL = indifferente)
    AND (p_fatturazione_immediata IS NULL OR c.fatturazione_immediata = p_fatturazione_immediata)
    -- EMISSIONE MIRATA (rev 2026-07-27): il conteggio
    -- total_non_emesse segue il filtro, cioe' riporta le righe
    -- dei soli gruppi richiesti. E' voluto: e' il numero che
    -- l'emit lavorera' davvero su quella commessa.
    AND (
         p_gruppi IS NULL
         OR vendite.fn_build_gruppo_fatturabile_key(
                ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id
            ) = ANY (p_gruppi)
        )
  GROUP BY
    c.id,
    c.codice,
    c.stato_commessa_id,
    sc.codice,
    c.billing_account_id,
    c.utility_id,
    c.emittente_soggetto_ruolo_id,
    c.fatturazione_immediata,
    c.competenza_dal,
    c.competenza_al
  ORDER BY c.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_commesse_emittibili(p_competenza_mese date, p_billing_account_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint, p_fatturazione_immediata boolean, p_limit integer, p_gruppi text[])
IS 'Read-only: elenca commesse in stato emittibile con attivita` NON_EMESSA. Filtro competenza_mese su commesse_attivita (coerente con pipeline AF). Filtri opzionali per billing_account_id, utility_id, emittente_soggetto_ruolo_id e fatturazione_immediata (corsia immediata/differita, NULL=indifferente). Espone fatturazione_immediata in output. Usata dal backend per il batch di emissione. rev 2026-07-27 (brief emissione mirata A6): p_gruppi text[] restringe alle commesse che contengono almeno una riga di un gruppo richiesto — NULL = nessuna restrizione (G1). ⚠️ NON sostituisce il filtro per RIGA dentro fn_emit_attivita_fatturabili_da_commessa: qui si sceglie QUALI COMMESSE visitare, li'' QUALI RIGHE emettere; una commessa multi-sorgente passa comunque il filtro e sara'' l''emit a prendere solo le righe richieste. Con p_gruppi valorizzato anche total_non_emesse segue il filtro: e'' il numero di righe che l''emit lavorera'' davvero.';
```

---
{% include-markdown "signature-core.md" %}
