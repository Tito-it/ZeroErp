{% include-markdown "it/dbzero/vendite/manual/fn_list_consumi_da_pushare.md" %}
# ⚙️ Funzione `fn_list_consumi_da_pushare`

```sql
CREATE FUNCTION fn_list_consumi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_consumi_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer)
 RETURNS TABLE(consumo_id bigint, consumo_uid uuid, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire i consumi pronti per il push su commessa AUTO,
  --   con tutti i campi necessari agli handler.
  --
  -- Regole:
  --   - stato_calcolo = 'OK' (consumi con errori o warning esclusi)
  --   - fattura_id IS NULL (non gia` fatturati sul percorso legacy)
  --   - esclude consumi con segment_key gia` EMESSA in commessa
  --   - prezzo_bloccato = FALSE (calcolato da listino al pull)
  --   - utility_id e istanza_utility_id risolti da billing_account
  --   - tipo_commessa target: AUTO, policy: DA_DOCUMENTO
  --
  -- NOTE:
  --   - articolo_id non presente su attivita_consumi: restituito NULL;
  --     l'handler deve risolverlo (es. da istanza_utility_id o config).
  --   - valuta_id non presente su attivita_consumi: restituito NULL;
  --     l'handler deve risolverlo (es. da config o billing_account).
  --   - un consumo produce N componenti nell'handler;
  --     il segment_key base e` 'CONS:<uid>', l'handler genera
  --     'CONS:<uid>:COMP:<componente>' per ogni componente fatturabile.
  --   - qta_operativa = consumo_totale, uom_operativa_id = uom_id.
  --   - codice sorgente config.sorgenti: 'ATTIVITA_CONSUMI' (id=12).
  -- =========================================================

  -- Lookup sorgente ATTIVITA_CONSUMI attiva + tipo_doc_fiscale_id (§26 B+D).
  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice = 'ATTIVITA_CONSUMI' AND s.attivo IS TRUE
  LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_list_consumi_da_pushare','E_GENERICO',
      jsonb_build_object(
        'scope','COMMESSE','severity','C','code','E_GENERICO',
        'lotto_id',NULL,'fattura_id',NULL,
        'context',jsonb_build_object('detail','sorgente ATTIVITA_CONSUMI non configurata/attiva')
      ),
      NULL::uuid,
      'sorgente ATTIVITA_CONSUMI non configurata/attiva'
    );
  END IF;

  RETURN QUERY
  SELECT
    ac.id                                                          AS consumo_id,
    ac.uid                                                         AS consumo_uid,
    ac.billing_account_id,
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(ac.billing_account_id) AS emittente_soggetto_ruolo_id,
    -- periodo_dal/al come finestra di competenza del consumo
    ac.periodo_dal                                                 AS competenza_dal,
    ac.periodo_al                                                  AS competenza_al,
    FALSE                                                          AS fatturazione_immediata,
    v_sorgente_tipo_id                                             AS sorgente_tipo_id,
    ac.uid::text                                                   AS sorgente_uid,
    -- segment_key base; l'handler espande in CONS:<uid>:COMP:<componente>
    ('CONS:' || ac.uid::text)::varchar                            AS segment_key,
    -- articolo_id non disponibile su attivita_consumi;
    -- l'handler deve risolvere (da istanza_utility_id o mapping config).
    NULL::uuid                                                     AS articolo_id,
    ba.istanza_utility_id,
    -- data_attivita: usa il primo giorno del periodo o la competenza_mese
    COALESCE(ac.periodo_dal, ac.competenza_mese)                  AS data_attivita,
    ac.uom_id,
    ac.consumo_totale                                              AS quantita,
    -- qta_operativa = consumo_totale (unica unita` di misura disponibile)
    ac.consumo_totale                                              AS qta_operativa,
    -- uom_operativa_id = uom_id (nessuna conversione a livello di sorgente)
    ac.uom_id                                                      AS uom_operativa_id,
    1::numeric                                                     AS factor_to_base,
    ac.competenza_mese,
    -- prezzo_snapshot = NULL: calcolato dal listino al momento del pull
    NULL::numeric                                                  AS prezzo_snapshot,
    -- prezzo_bloccato = FALSE: consumi sempre ricalcolabili da listino
    FALSE                                                          AS prezzo_bloccato,
    'FIXED'::varchar                                               AS pricing_mode,
    'NORMALE'::varchar                                             AS tipo_movimento,
    'CONSUMO'::varchar                                             AS tipo_consumo,
    -- valuta_id non disponibile su attivita_consumi; handler deve risolvere
    NULL::integer                                                  AS valuta_id,
    jsonb_build_object(
      'consumo_uid',         ac.uid,
      'stato_calcolo',       ac.stato_calcolo,
      'periodo_dal',         ac.periodo_dal,
      'periodo_al',          ac.periodo_al,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    )                                                              AS meta,
    v_tipo_doc_fiscale_id                                            AS tipo_doc_fiscale_id
  FROM vendite.attivita_consumi ac
  JOIN anagrafiche.billing_account ba
    ON ba.id = ac.billing_account_id
  WHERE ac.stato_calcolo = 'OK'
    -- Non fatturati sul percorso legacy (se migrazione coesiste con commessa).
    AND ac.fattura_id IS NULL
    -- Filtri opzionali.
    AND (p_competenza_mese IS NULL OR ac.competenza_mese = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR ac.billing_account_id = p_billing_account_id)
    -- Esclude consumi gia` emessi in commessa (ottimizzazione batch).
    -- Il pattern reale e` CONS:<uid>:COMP:<componente>, quindi LIKE sul prefisso.
    AND NOT EXISTS (
      SELECT 1
      FROM vendite.commesse_attivita ca
      WHERE ca.segment_key LIKE 'CONS:' || ac.uid::text || ':%'
        AND ca.stato_emissione = 'EMESSA'
    )
  ORDER BY ac.competenza_mese, ac.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_consumi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer)
IS 'Lista consumi utility eligible al push su commessa AUTO (stato_calcolo OK, non fatturati). Restituisce tutti i campi per get_or_create_commessa + upsert_commessa_attivita. utility_id/istanza_utility_id da billing_account. articolo_id e valuta_id NULL: risolti dall''handler. Prezzo non bloccato (da listino).';
```

---
{% include-markdown "signature-core.md" %}
