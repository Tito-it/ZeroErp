{% include-markdown "it/dbzero/vendite/manual/fn_list_consumi_da_pushare.md" %}
# ⚙️ Funzione `fn_list_consumi_da_pushare`

```sql
CREATE FUNCTION fn_list_consumi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_consumo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_consumi_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_consumo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(consumo_id bigint, consumo_uid uuid, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint, termine_pagamento_id bigint, modalita_pagamento_id integer)
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (20261020-89, brief-db-grammatica-unica-documenti, 2e G-8):
--   la chiave e' ATTIVITA_CONSUMI:<uid>, composta da
--   script.fn_segment_key (era CONS:<uid>). Firma e RETURNS ancorati.
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
BEGIN
  -- rev 2026-06-28 (analisi-hardcoded-codice §3a): sorgente risolta
  -- per codice_interno (immutabile), non per codice (mutabile).
  -- rev 2026-07-27 (brief emissione mirata PARTE B, D-6): a differenza
  -- di ordini/contratti/DDT, qui fatturazione_immediata RESTA la
  -- costante FALSE. Non e' una dimenticanza: e' dominio. Un consumo
  -- e' una misura, la corsia la decide il contratto che lo governa.
  -- Guard: p_consumo_id, se specificato, deve essere > 0.
  IF p_consumo_id IS NOT NULL AND p_consumo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'fn_list_consumi_da_pushare',
      'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_consumo_id', 'valore', p_consumo_id),
      NULL::uuid,
      'p_consumo_id', p_consumo_id::text
    );
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'ATTIVITA_CONSUMI' AND s.attivo IS TRUE
  LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_consumi_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'ATTIVITA_CONSUMI'),
      NULL::uuid,
      'ATTIVITA_CONSUMI', 'config.sorgenti'
    );
  END IF;

  RETURN QUERY
  SELECT
    ac.id, ac.uid,
    ac.billing_account_id,
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(ac.billing_account_id),
    ac.periodo_dal, ac.periodo_al,
    -- fatturazione_immediata: costante FALSE PER SCELTA DI DOMINIO
    -- (D-6, 2026-07-27). I consumi seguono sempre la corsia
    -- differita; la corsia immediata si ottiene marcando il
    -- CONTRATTO che governa la fornitura, non la singola lettura.
    -- NON sostituire con una colonna: vedi header del changeSet.
    FALSE,
    v_sorgente_tipo_id,
    ac.uid::text,
    script.fn_segment_key('ATTIVITA_CONSUMI', ac.uid::text),
    NULL::uuid,
    ba.istanza_utility_id,
    COALESCE(ac.periodo_dal, ac.competenza_mese),
    ac.uom_id,
    ac.consumo_totale,
    ac.consumo_totale,
    ac.uom_id,
    1::numeric,
    ac.competenza_mese,
    NULL::numeric,
    -- prezzo_bloccato: FALSE per una ragione DIVERSA e non
    -- correlata alla precedente — un consumo non porta prezzo
    -- dalla sorgente (prezzo_snapshot NULL sopra), quindi non
    -- c'e' nulla da bloccare: il prezzo lo risolve il pricing.
    FALSE,
    'FIXED'::varchar,
    'NORMALE'::varchar,
    NULL::integer,
    jsonb_build_object(
      'consumo_uid',         ac.uid,
      'stato_calcolo',       ac.stato_calcolo,
      'periodo_dal',         ac.periodo_dal,
      'periodo_al',          ac.periodo_al,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    ),
    v_tipo_doc_fiscale_id,
    NULL::bigint,
    NULL::integer
  FROM vendite.attivita_consumi ac
  JOIN anagrafiche.billing_account ba ON ba.id = ac.billing_account_id
  WHERE ac.stato_calcolo = 'OK'
    AND ac.fattura_id IS NULL
    AND (p_competenza_mese IS NULL OR ac.competenza_mese = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR ac.billing_account_id = p_billing_account_id)
    -- Estensione 2026-05: NULL = lista globale; NOT NULL = singolo consumo.
    AND (p_consumo_id IS NULL OR ac.id = p_consumo_id)
    -- Esclusione "gia' inviato" (rev 2026-10-12, 20261012-10): dal
    -- classificatore unico, sul segmento che questa funzione scrive
    -- ('CONS:<uid>', sopra). Il NOT EXISTS di prima cercava
    -- 'CONS:<uid>:%', con i due punti finali che il segmento base non
    -- ha: vedeva solo le righe del fan-out per componente
    -- (':COMP:<x>', HandlerConsumi._expand_rows), che e' uno stub
    -- RIMANDATO (Tid, 2026-06-16) e non ne scrive. ⚠️ Il giorno in cui
    -- il fan-out si accende deve usare il suffisso '#CMP:' che il
    -- classificatore vede (DEC-2), non ':COMP:'. Una riga ANNULLATA
    -- non occupa (D-5).
    AND script.fn_get_stato_push_segment(
          script.fn_segment_key('ATTIVITA_CONSUMI', ac.uid::text)) = 'LIBERA'
  ORDER BY ac.competenza_mese, ac.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_consumi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_consumo_id bigint)
IS 'Lista consumi eligible al push su commessa (stato_calcolo OK, non fatturati). p_consumo_id (opzionale): NULL=lista globale batch, NOT NULL=singolo consumo. Tutti i filtri in AND. Esclude i consumi gia'' mandati in commessa (script.fn_get_stato_push_segment, dal 2026-10-12). rev 2026-06-28: sorgente per codice_interno (analisi-hardcoded-codice §3a). rev 2026-07-19: esclusione su ALLOCAZIONE (non piu'' solo emessi): il NOT EXISTS non filtra piu'' stato_emissione — brief-db-push-commessa-gia-inviato §4a. rev 2026-07-27: NESSUN cambio di comportamento — documentata come scelta di dominio (D-6) la costante FALSE su fatturazione_immediata: a differenza di ordini/contratti/DDT i consumi NON hanno il flag, perche'' un consumo e'' una misura e la corsia la decide il contratto che lo governa. Non sostituire con una colonna — brief-db-emissione-fattura-per-documento-sorgente PARTE B. Espone termine_pagamento_id e modalita_pagamento_id a NULL: i consumi non hanno un documento con condizioni di pagamento (rev 2026-08-03, T.1). rev 2026-10-12 (20261012-10, brief-db-annullo-a-valle-riapre-a-monte D-5): «gia'' mandato» dal classificatore unico script.fn_get_stato_push_segment(''CONS:<uid>'') invece del NOT EXISTS proprio, che cercava ''CONS:<uid>:%'' con due punti finali che il segmento scritto qui non ha, e quindi vedeva solo le righe del fan-out per componente '':COMP:<x>'' (stub rimandato, non ne scrive): il consumo gia'' mandato restava in lista, e all''idempotenza pensava solo l''ON CONFLICT dell''upsert nella stessa commessa. ⚠️ Quando il fan-out si accendera'' dovra'' usare il suffisso ''#CMP:'' che il classificatore vede. Una riga ANNULLATA non occupa: annullata la commessa, il consumo torna da mandare (D-7). rev 2026-10-13 (20261013-20): tipo_consumo RITIRATO in tutta la catena del push (madre, batch, cinque lister, builder pgTAP). Non aveva un lettore, e il vocabolario della madre (ACCONTO/CONGUAGLIO/STORNO) non lo produceva nessuna sorgente con un significato: preventivi, ordini e DDT scrivevano la costante CONGUAGLIO, contratti (l''erogazione della riga) e consumi (CONSUMO) un valore che la madre rifiutava, quindi il loro push falliva sempre (E_PARAMETRO_INVALIDO). L''erogazione resta dove gia'' stava, in meta.tipo_erogazione. Decisione A di Tid, 2026-10-13. Colonna tipo_consumo tolta dal RETURNS TABLE (DROP + CREATE). Rev 2026-10-20 (20261020-89, brief-db-grammatica-unica-documenti 2e, G-8): la chiave e'' ATTIVITA_CONSUMI:<uid>, composta da script.fn_segment_key (era CONS:<uid>).';
```

</div>

---
{% include-markdown "signature-core.md" %}
