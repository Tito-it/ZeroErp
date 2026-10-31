{% include-markdown "it/dbzero/vendite/manual/fn_list_preventivi_da_pushare.md" %}
# ⚙️ Funzione `fn_list_preventivi_da_pushare`

```sql
CREATE FUNCTION fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_preventivo_id bigint, p_righe_ids bigint[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date DEFAULT NULL::date, p_billing_account_id bigint DEFAULT NULL::bigint, p_limit integer DEFAULT NULL::integer, p_preventivo_id bigint DEFAULT NULL::bigint, p_righe_ids bigint[] DEFAULT NULL::bigint[])
 RETURNS TABLE(preventivo_id bigint, preventivo_uid uuid, riga_id bigint, billing_account_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, competenza_dal date, competenza_al date, fatturazione_immediata boolean, sorgente_tipo_id bigint, sorgente_uid text, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, factor_to_base numeric, competenza_mese date, prezzo_snapshot numeric, prezzo_bloccato boolean, pricing_mode character varying, tipo_movimento character varying, valuta_id integer, meta jsonb, tipo_doc_fiscale_id bigint, termine_pagamento_id bigint, modalita_pagamento_id integer)
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-31 (20261031-15, brief-modello-documento-vendita §17):
--   lo stato di accettazione dal vocabolario, non 'ACCETTATO'.
-- rev 2026-10-20 (20261020-93, brief-db-grammatica-unica-documenti, 2e G-8):
--   la chiave e' PREVENTIVO:<uid>:R:<riga>, composta da
--   script.fn_segment_key (era PREV:...). Firma e RETURNS ancorati.
DECLARE
  v_sorgente_tipo_id    config.sorgenti.id%TYPE;
  v_tipo_doc_fiscale_id config.sorgenti.tipo_doc_fiscale_id%TYPE;
  v_stato_accettato_id  config.stati_doc_preventivi.id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Restituire le righe preventivo pronte per il push su
  --   commessa, con tutti i campi necessari agli handler.
  --
  -- Regole:
  --   - stato documento ACCETTATO
  --   - predicato di riga dalla vista unica
  --     vw_preventivi_righe_smistabili_commessa (rev 12-06-2026):
  --     riga attiva, quantita > 0, prezzo >= 0, natura NULL
  --     (pregresso) o destinazione_tipo='COMMESSA', non gia'
  --     EMESSA in commessa. La merce (ORDINE) va su
  --     fn_push_preventivo_a_ordine, non qui.
  --   - prezzo_bloccato = fatturazione_immediata
  --   - tipo_commessa target: REALE, policy: DA_DOCUMENTO
  --
  -- rev 2026-10-10: via il filtro di «testata completa»
  --   (billing_account_id, utility_id NOT NULL): le due colonne
  --   sono NOT NULL dal 2026-10-08, il filtro non toglieva
  --   niente. Brief: brief-db-istanza-nasce-col-ba-residui (R-3).
  --   Lo stato ACCETTATO assente dal catalogo solleva E_CODICE,
  --   come la sorgente, invece di far cadere il filtro (D-2).
  --
  -- NOTE codice_interno (rev 2026-06-28, analisi-hardcoded-codice §3a):
  --   sorgente/stato risolti per codice_interno (immutabile), non per
  --   codice (mutabile). Difesa dai rename utente.
  --
  -- Competenza (rev 10-06-2026, brief competenza):
  --   - competenza_dal/al NON nulli (commesse_attivita NOT NULL):
  --     fallback validita -> competenza_mese -> data. GREATEST su
  --     competenza_al garantisce dal<=al anche con validita_dal
  --     NULL + validita_al valorizzato.
  --   - competenza_mese: policy p.competenza_mese autorevole, con
  --     fallback al derivato validita/data per il pregresso.
  --   - competenza_dal/al = periodo attivita'; competenza_mese =
  --     mese di fatturazione (policy). Indipendenti per costruzione.
  --
  -- Estensione 2026-05: p_preventivo_id (opzionale):
  --   NULL = lista globale batch; NOT NULL = singolo preventivo UI-driven.
  -- Estensione 2026-06-12: p_righe_ids (opzionale, brief smistamento):
  --   sottoinsieme righe del pannello; richiede p_preventivo_id.
  --   Righe non eleggibili nel sottoinsieme: skip silenzioso (D5).
  --
  -- NOTE:
  --   - uom_id: UoM canonica da catalogo.articoli (JOIN su pr.articolo_id).
  --     La colonna preventivi_righe.uom_id e` droppata (non usare).
  --   - uom_operativa_id: UoM di inserimento operatore (dalla riga).
  -- =========================================================

  IF p_preventivo_id IS NOT NULL AND p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_preventivi_da_pushare', 'E_PUSH_SORGENTE_ID_INVALIDO',
      jsonb_build_object('parametro', 'p_preventivo_id', 'valore', p_preventivo_id),
      NULL::uuid,
      'p_preventivo_id', p_preventivo_id::text
    );
  END IF;

  -- Sottoinsieme righe: ha senso solo sul push singolo UI-driven.
  IF p_righe_ids IS NOT NULL AND p_preventivo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_preventivi_da_pushare', 'E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO',
      jsonb_build_object('parametro', 'p_righe_ids', 'valore', p_righe_ids),
      NULL::uuid,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  SELECT s.id, s.tipo_doc_fiscale_id
    INTO v_sorgente_tipo_id, v_tipo_doc_fiscale_id
  FROM config.sorgenti s
  WHERE s.codice_interno = 'PREVENTIVO' AND s.attivo IS TRUE LIMIT 1;

  IF v_sorgente_tipo_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_preventivi_da_pushare', 'E_CODICE',
      jsonb_build_object('codice', 'PREVENTIVO'),
      NULL::uuid, 'PREVENTIVO', 'config.sorgenti'
    );
  END IF;

  v_stato_accettato_id := script.fn_stato_accettazione_id('vendite.preventivi'::regclass);

  -- Senza lo stato il filtro non ha un valore: si ferma, come
  -- per la sorgente (rev 2026-10-10, D-2). Prima il filtro era
  -- `IS NULL OR` e cadeva: preventivi in qualunque stato.
  IF v_stato_accettato_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_list_preventivi_da_pushare', 'E_CONFIG_MANCANTE',
      jsonb_build_object('config', 'config.stati_doc_preventivi.accettazione'),
      NULL::uuid, 'stato di accettazione (config.stati_doc_preventivi.accettazione)'
    );
  END IF;

  RETURN QUERY
  SELECT
    p.id                                                          AS preventivo_id,
    p.uid                                                         AS preventivo_uid,
    pr.id                                                         AS riga_id,
    p.billing_account_id,
    p.utility_id,
    anagrafiche.fn_get_emittente_fiscale_id(p.billing_account_id) AS emittente_soggetto_ruolo_id,
    -- competenza_dal/al NOT NULL-safe (brief competenza 10-06-2026)
    COALESCE(p.validita_dal, p.competenza_mese, p.data)           AS competenza_dal,
    GREATEST(
      COALESCE(p.validita_dal, p.competenza_mese, p.data),
      COALESCE(p.validita_al, p.validita_dal, p.competenza_mese, p.data)
    )                                                             AS competenza_al,
    p.fatturazione_immediata,
    v_sorgente_tipo_id                                            AS sorgente_tipo_id,
    p.uid::text                                                   AS sorgente_uid,
    script.fn_segment_key('PREVENTIVO', p.uid::text, pr.id) AS segment_key,
    pr.articolo_id,
    p.istanza_utility_id,
    COALESCE(p.validita_dal, p.data)                              AS data_attivita,
    -- uom_id canonica da catalogo.articoli (fix bug proiezione NULL)
    a.uom_id,
    pr.quantita,
    pr.qta_operativa,
    pr.uom_operativa_id,
    COALESCE(pr.factor_to_base, 1::numeric)                       AS factor_to_base,
    -- competenza_mese: policy autorevole, fallback al derivato (pregresso)
    COALESCE(
      p.competenza_mese,
      date_trunc('month', COALESCE(p.validita_dal, p.data))::date
    )                                                             AS competenza_mese,
    pr.prezzo_unitario                                            AS prezzo_snapshot,
    COALESCE(p.fatturazione_immediata, false)                     AS prezzo_bloccato,
    'FIXED'::varchar                                              AS pricing_mode,
    'NORMALE'::varchar                                            AS tipo_movimento,
    p.valuta_id,
    jsonb_build_object(
      'preventivo_numero',   p.numero,
      'preventivo_rev',      p.rev,
      'tipo_commessa',       'REALE',
      'policy_fatturazione', 'DA_DOCUMENTO'
    )                                                             AS meta,
    v_tipo_doc_fiscale_id                                         AS tipo_doc_fiscale_id,
    p.termine_pagamento_id,
    NULL::integer
  FROM vendite.preventivi p
  -- Predicato di riga dalla vista unica (eleggibilita' condivisa
  -- con capability e pannello smistamento).
  JOIN vendite.vw_preventivi_righe_smistabili_commessa v
    ON v.preventivo_id = p.id
  JOIN vendite.preventivi_righe pr ON pr.id = v.id
  JOIN catalogo.articoli a ON a.id = pr.articolo_id
  WHERE p.stato_doc_preventivo_id = v_stato_accettato_id
    -- Filtro allineato alla stessa espressione del SELECT competenza_mese.
    AND (p_competenza_mese IS NULL
         OR COALESCE(
              p.competenza_mese,
              date_trunc('month', COALESCE(p.validita_dal, p.data))::date
            ) = p_competenza_mese)
    AND (p_billing_account_id IS NULL OR p.billing_account_id = p_billing_account_id)
    AND (p_preventivo_id IS NULL OR p.id = p_preventivo_id)
    -- Sottoinsieme righe del pannello (skip silenzioso delle non
    -- eleggibili: gia' escluse dalla vista).
    AND (p_righe_ids IS NULL OR pr.id = ANY(p_righe_ids))
  ORDER BY p.id, pr.id
  LIMIT p_limit;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_preventivi_da_pushare(p_competenza_mese date, p_billing_account_id bigint, p_limit integer, p_preventivo_id bigint, p_righe_ids bigint[])
IS 'Righe preventivo pronte per il push su commessa (stato di accettazione, script.fn_stato_accettazione_id dal 2026-10-31, §17, oggi ACCETTATO; predicato di riga dalla vista unica vw_preventivi_righe_smistabili_commessa). p_preventivo_id: push singolo UI-driven. p_righe_ids (rev 12-06-2026, brief smistamento): sottoinsieme righe del pannello, richiede p_preventivo_id (E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO), righe non eleggibili skippate in silenzio (D5). NULL = batch invariato. rev 2026-06-28: sorgente/stato per codice_interno (analisi-hardcoded-codice §3a). Espone termine_pagamento_id del preventivo; modalita_pagamento_id e'' NULL perche'' i preventivi non la portano (rev 2026-08-03, T.1). rev 2026-10-10 (20261010-52): via il filtro di testata completa (billing_account_id, utility_id NOT NULL), che non toglieva niente: le due colonne sono NOT NULL dal 2026-10-08. Lo stato ACCETTATO assente dal catalogo solleva E_CODICE (config.stati_doc_preventivi) invece di far cadere il filtro di stato (prima `IS NULL OR`: preventivi in qualunque stato). Brief: brief-db-istanza-nasce-col-ba-residui (R-3, D-2). rev 2026-10-13 (20261013-23): tipo_consumo RITIRATO in tutta la catena del push (madre, batch, cinque lister, builder pgTAP). Non aveva un lettore, e il vocabolario della madre (ACCONTO/CONGUAGLIO/STORNO) non lo produceva nessuna sorgente con un significato: preventivi, ordini e DDT scrivevano la costante CONGUAGLIO, contratti (l''erogazione della riga) e consumi (CONSUMO) un valore che la madre rifiutava, quindi il loro push falliva sempre (E_PARAMETRO_INVALIDO). L''erogazione resta dove gia'' stava, in meta.tipo_erogazione. Decisione A di Tid, 2026-10-13. Colonna tipo_consumo tolta dal RETURNS TABLE (DROP + CREATE). Rev 2026-10-20 (20261020-93, brief-db-grammatica-unica-documenti 2e, G-8): la chiave e'' PREVENTIVO:<uid>:R:<riga>, composta da script.fn_segment_key (era PREV:...).';
```

</div>

---
{% include-markdown "signature-core.md" %}
