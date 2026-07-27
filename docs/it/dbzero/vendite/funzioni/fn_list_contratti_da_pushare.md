{% include-markdown "it/dbzero/vendite/manual/fn_list_contratti_da_pushare.md" %}
# ⚙️ Funzione `fn_list_contratti_da_pushare`

```sql
CREATE FUNCTION fn_list_contratti_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_contratto_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_contratti_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_contratto_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(contratto_id bigint, contratto_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, tipo_consumo character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
  v_stato_attivo_id     config.stati_doc_contratti.id%TYPE;
BEGIN
  -- rev 2026-06-28 (analisi-hardcoded-codice §3a): sorgente/stato
  -- risolti per codice_interno (immutabile), non per codice (mutabile).
  -- rev 2026-07-27 (brief emissione mirata PARTE B): fatturazione_immediata
  -- proiettata dalla COLONNA (era la costante FALSE). Il valore instrada
  -- la corsia via chiave di dedup di fn_get_or_create_commessa.
  IF p_contratto_id IS NOT NULL AND p_contratto_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_contratti_da_pushare', 'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_contratto_id', 'valore', p_contratto_id),
      NULL::uuid,
      'p_contratto_id', p_contratto_id::text
    );
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'CONTRATTO' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_contratti_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'CONTRATTO'),
      NULL::uuid, 'CONTRATTO', 'config.sorgenti'
    );
  END IF;

  SELECT s.id INTO v_stato_attivo_id
  FROM config.stati_doc_contratti s
  WHERE s.codice_interno = 'ATTIVO' AND s.attivo IS TRUE LIMIT 1;

  RETURN QUERY
  SELECT
    c.id, c.uid, cr.id,
    c.billing_account_id,
    c.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(c.billing_account_id),
    c.valido_dal, c.valido_al,
    -- Corsia di instradamento: valore reale del contratto.
    c.fatturazione_immediata,
    v_sorgente_tipo_id,
    c.uid::text,
    ('CONTR:' || c.uid::text || ':R:' || cr.id::text || ':M:' ||
     to_char(date_trunc('month', COALESCE(c.valido_dal, c.data))::date, 'YYYY-MM'))::varchar,
    cr.articolo_id,
    c.istanza_utility_id,
    COALESCE(c.valido_dal, c.data),
    -- uom_id canonica da catalogo.articoli (fix bug proiezione NULL)
    a.uom_id,
    cr.quantita,
    cr.qta_operativa,
    cr.uom_operativa_id,
    COALESCE(cr.factor_to_base, 1::numeric),
    date_trunc('month', COALESCE(c.valido_dal, c.data))::date,
    cr.prezzo_unitario,
    -- prezzo_bloccato: dipende dalla RIGA (prezzo valorizzato),
    -- INDIPENDENTE dal flag di corsia. Vedi header del changeSet.
    (cr.prezzo_unitario IS NOT NULL),
    'FIXED'::varchar,
    'NORMALE'::varchar,
    COALESCE(cr.tipo_erogazione, 'CANONE')::varchar,
    NULL::integer,
    jsonb_build_object(
      'contratto_numero',    c.numero,
      'periodicita',         cr.periodicita,
      'generazione_canone',  cr.generazione_canone,
      'competenza_canone',   cr.competenza_canone,
      'tipo_erogazione',     cr.tipo_erogazione,
      'tipo_commessa',       'AUTO',
      'policy_fatturazione', 'DA_DOCUMENTO'
    ),
    v_tipo_doc_fiscale_id
  FROM vendite.contratti c
  JOIN vendite.contratti_righe cr
    ON cr.contratto_id = c.id
   AND COALESCE(cr.attivo, TRUE) IS TRUE
  JOIN catalogo.articoli a ON a.id = cr.articolo_id
  WHERE c.billing_account_id IS NOT NULL
    AND (v_stato_attivo_id IS NULL OR c.stato_doc_contratto_id = v_stato_attivo_id)
    AND (c.valido_al IS NULL OR c.valido_al >= COALESCE(p_competenza_mese, CURRENT_DATE))
    AND (p_competenza_mese IS NULL
         OR date_trunc('month', COALESCE(c.valido_dal, c.data))::date = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR c.billing_account_id = p_billing_account_id)
    AND (p_contratto_id IS NULL OR c.id = p_contratto_id)
    -- Esclusione "gia' inviato": eleggibile solo se MAI
    -- instradata (LIBERA) — classificatore condiviso coi rami
    -- reason della capability: vede anche i componenti #CMP e
    -- non dipende piu' da stato_emissione (ALLOCATA basta).
    AND script.fn_get_stato_push_segment(
          'CONTR:' || c.uid::text || ':R:' || cr.id::text || ':M:' || to_char(date_trunc('month', COALESCE(c.valido_dal, c.data))::date, 'YYYY-MM')) = 'LIBERA'
  ORDER BY c.id, cr.id
  LIMIT p_limit;
END
$function$

COMMENT ON FUNCTION vendite.fn_list_contratti_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_contratto_id bigint)
IS 'Lista righe contratto eligible al push su commessa (stato ATTIVO). uom_id da catalogo.articoli (canonica). p_contratto_id opzionale: NULL=batch globale, NOT NULL=singolo contratto. Filtri in AND. Esclude EMESSA via NOT EXISTS. (20260511-33: cr.quantita_fissa -> cr.quantita dopo rename colonna) rev 2026-06-28: sorgente/stato per codice_interno (analisi-hardcoded-codice §3a). rev 2026-07-19: esclusione su ALLOCAZIONE del mese via script.fn_get_stato_push_segment (vede anche componenti #CMP), non piu'' solo EMESSA — brief-db-push-commessa-gia-inviato §4a. rev 2026-07-27: fatturazione_immediata proiettata dalla colonna vendite.contratti.fatturazione_immediata (era costante FALSE) — simmetria del flag di corsia, brief-db-emissione-fattura-per-documento-sorgente PARTE B. prezzo_bloccato resta legato alla riga (prezzo valorizzato): l''accoppiamento flag/prezzo esiste solo sui preventivi.';
```

---
{% include-markdown "signature-core.md" %}
