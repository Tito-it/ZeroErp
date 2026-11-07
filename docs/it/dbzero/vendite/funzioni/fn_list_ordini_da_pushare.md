{% include-markdown "it/dbzero/vendite/manual/fn_list_ordini_da_pushare.md" %}
# ⚙️ Funzione `fn_list_ordini_da_pushare`

```sql
CREATE FUNCTION fn_list_ordini_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ordine_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_ordini_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_ordine_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ordine_id bigint, ordine_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_chiave text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint, termine_pagamento_id bigint, modalita_pagamento_id integer, causale_onere_id bigint)
 LANGUAGE plpgsql
AS $function$
-- rev 2026-11-03 (20261103-38, brief-db-addebito-trasporto-ordine §8.1, K-1):
--   la riga-onere (script.fn_natura_e_merce = false sulla natura congelata)
--   esce tipo_movimento ONERE con la causale dell'articolo, nella colonna
--   nuova causale_onere_id (DROP + CREATE). Sorgente: l'ordine, come le altre.
-- rev 2026-10-20 (20261020-92, brief-db-grammatica-unica-documenti, 2e G-8):
--   la chiave e' ORDINE_VENDITA:<uid>:R:<riga>, composta da
--   script.fn_segment_key (era ORD:...). Firma e RETURNS ancorati.
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
BEGIN
  -- rev 2026-06-28 (analisi-hardcoded-codice §3a): sorgente/stato
  -- risolti per codice_interno (immutabile), non per codice (mutabile).
  -- rev 2026-07-10 (fix orfano, piano-db-fix-orfano-push-ordine-confermato §4.1):
  -- l'eleggibilita' push NON dipende piu' dallo stato di spedizione
  -- (CONFERMATO/PARZIALMENTE_EVASO/EVASO/...): per trigger CONFERMATO
  -- si fattura l'ordine confermato, la spedizione e' ortogonale.
  -- Esclusi solo DRAFT/ANNULLATO (doc commercialmente inesistente)
  -- e FATTURATO (cintura). L'anti doppia fatturazione resta il
  -- NOT EXISTS su commesse_attivita EMESSA (verita' di billing).
  -- rev 2026-07-27 (brief emissione mirata PARTE B): fatturazione_immediata
  -- proiettata dalla COLONNA (era la costante FALSE). Il valore instrada
  -- la corsia via chiave di dedup di fn_get_or_create_commessa.
  -- rev 2026-10-10 (brief-db-istanza-nasce-col-ba-residui D-1): via il
  -- filtro billing_account_id IS NOT NULL: la colonna e' NOT NULL.
  IF p_ordine_id IS NOT NULL AND p_ordine_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ordini_da_pushare', 'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_ordine_id', 'valore', p_ordine_id),
      NULL::uuid,
      'p_ordine_id', p_ordine_id::text
    );
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'ORDINE_VENDITA' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_ordini_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'ORDINE_VENDITA'),
      NULL::uuid, 'ORDINE_VENDITA', 'config.sorgenti'
    );
  END IF;

  RETURN QUERY
  SELECT
    o.id, o.uid, or_r.id,
    o.billing_account_id,
    ba.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(o.billing_account_id),
    o.data, o.data,
    -- Corsia di instradamento: valore reale del documento.
    o.fatturazione_immediata,
    v_sorgente_tipo_id,
    o.uid::text,
    script.fn_segment_key('ORDINE_VENDITA', o.uid::text, or_r.id),
    or_r.articolo_id,
    ba.istanza_utility_id,
    o.data,
    -- uom_id canonica da catalogo.articoli (fix bug proiezione NULL)
    a.uom_id,
    or_r.quantita,
    or_r.qta_operativa,
    or_r.uom_operativa_id,
    COALESCE(or_r.factor_to_base, 1::numeric),
    date_trunc('month', o.data)::date,
    or_r.prezzo_unitario,
    -- prezzo_bloccato: costante TRUE per gli ordini, INDIPENDENTE dal
    -- flag di corsia (l'accoppiamento esiste solo sui preventivi).
    TRUE,
    'FIXED'::varchar,
    -- rev 2026-11-03 (K-1): la riga-onere va in commessa come ONERE, con la
    -- causale dell'articolo e la sorgente dell'ordine (il CHECK
    -- chk_commesse_attivita_senza_sorgente_onere_rettifica lo ammette).
    -- IS FALSE: una natura sconosciuta resta NORMALE.
    CASE WHEN script.fn_natura_e_merce(or_r.natura_vendita_id) IS FALSE
         THEN 'ONERE' ELSE 'NORMALE' END::varchar,
    o.valuta_id,
    jsonb_build_object(
      'ordine_numero',       o.numero,
      'ordine_anno',         o.anno,
      'ordine_serie',        o.serie,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    ),
    v_tipo_doc_fiscale_id,
    o.termine_pagamento_id,
    o.modalita_pagamento_id,
    -- La causale si legge dall'articolo solo qui, dove serve il valore
    -- (decisione 2 di Tid). ONERE <=> causale: lo pretende la madre
    -- vendite.fn_upsert_commessa_attivita. ⚠️ Un articolo-onere a cui fosse
    -- stata tolta la causale dopo la vendita esce ONERE senza causale, e la
    -- madre lo rifiuta (E_PARAMETRO_INVALIDO): rumoroso, non NORMALE in silenzio.
    CASE WHEN script.fn_natura_e_merce(or_r.natura_vendita_id) IS FALSE
         THEN a.causale_onere_id END
  FROM vendite.ordini o
  JOIN anagrafiche.billing_account ba ON ba.id = o.billing_account_id
  -- rev 2026-07-10: join stato solo per ESCLUDERE i non eleggibili
  -- (state-agnostic sull'asse spedizione, no whitelist fragile).
  JOIN config.stati_doc_ordini sdo
    ON sdo.id = o.stato_doc_ordine_id
   AND sdo.codice_interno NOT IN ('DRAFT', 'ANNULLATO', 'FATTURATO')
  JOIN vendite.ordini_righe or_r
    ON or_r.ordine_id = o.id
   AND or_r.attivo IS TRUE
   AND or_r.quantita > 0
   AND or_r.prezzo_unitario >= 0
  JOIN catalogo.articoli a ON a.id = or_r.articolo_id
  WHERE o.fatturazione_trigger = 'CONFERMATO'
    AND (p_competenza_mese IS NULL OR date_trunc('month', o.data)::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR o.billing_account_id = p_billing_account_id)
    AND (p_ordine_id IS NULL OR o.id = p_ordine_id)
    -- Esclusione "gia' inviato": eleggibile solo se MAI
    -- instradata (LIBERA) — classificatore condiviso coi rami
    -- reason della capability: vede anche i componenti #CMP e
    -- non dipende piu' da stato_emissione (ALLOCATA basta).
    AND script.fn_get_stato_push_segment(
          script.fn_segment_key('ORDINE_VENDITA', o.uid::text, or_r.id)) = 'LIBERA'
  ORDER BY o.id, or_r.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_ordini_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_ordine_id bigint)
IS 'Le righe degli ordini di vendita da mandare in commessa: ordini con fatturazione_trigger CONFERMATO, in qualunque stato di spedizione tranne DRAFT, ANNULLATO e FATTURATO; righe attive con quantita'' > 0 e prezzo >= 0. Una riga gia'' instradata resta fuori: e'' eleggibile solo se script.fn_get_stato_push_segment dice LIBERA, lo stesso classificatore della capability dell''ordine, che vede anche i componenti #CMP. p_ordine_id: un ordine solo (NULL = tutti; <= 0 solleva E_PUSH_SORGENTE_ID_INVALIDO); la sorgente ORDINE_VENDITA assente dal catalogo solleva E_CODICE. Filtri in AND, ordine per ordine e riga, p_limit come tetto. La chiave del documento esce in sorgente_chiave, l''uid dell''ordine in testo, come la riceve la madre vendite.fn_upsert_commessa_attivita (p_sorgente_chiave) e come la legge la chiave sorgente_chiave del batch vendite.fn_batch_upsert_commessa_attivita; la chiave del push ORDINE_VENDITA:<uid>:R:<riga> la compone script.fn_segment_key. uom_id viene dall''articolo (catalogo.articoli). fatturazione_immediata e'' quella dell''ordine; prezzo_bloccato e'' sempre TRUE, perche'' l''accoppiamento col flag di corsia esiste solo sui preventivi. Una riga-onere (script.fn_natura_e_merce falso sulla natura della riga) esce con tipo_movimento ONERE e la causale dell''articolo in causale_onere_id; la merce esce NORMALE, con causale_onere_id NULL. Espone termine_pagamento_id e modalita_pagamento_id dell''ordine. Il backend legge le colonne per nome.';
```

</div>

---
{% include-markdown "signature-core.md" %}
