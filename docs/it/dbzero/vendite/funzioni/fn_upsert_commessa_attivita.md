{% include-markdown "it/dbzero/vendite/manual/fn_upsert_commessa_attivita.md" %}
# ⚙️ Funzione `fn_upsert_commessa_attivita`

```sql
CREATE FUNCTION fn_upsert_commessa_attivita(p_commessa_id bigint, p_segment_key character varying, p_articolo_id uuid, p_istanza_utility_id bigint, p_data_attivita date, p_uom_id bigint, p_quantita numeric, p_competenza_mese date, p_competenza_dal date, p_competenza_al date, p_prezzo_snapshot numeric, p_prezzo_base_snapshot numeric, p_origine_prezzo character varying, p_tipo_variazione_applicata character varying, p_valore_variazione_applicata numeric, p_promo_id bigint, p_contratto_id bigint, p_categoria_cliente_id_snapshot smallint, p_classe_utenza_id_snapshot integer, p_qta_operativa numeric, p_uom_operativa_id bigint, p_factor_to_base numeric, p_posticipa_al date, p_tipo_doc_fiscale_id bigint, p_valuta_id integer, p_area_geografica_id bigint, p_listino_versione_id bigint, p_prezzo_bloccato boolean, p_pricing_mode character varying, p_prezzo_da_riallineare boolean, p_stato_approvazione character varying, p_stato_emissione character varying, p_sorgente_tipo_id bigint, p_sorgente_uid text, p_tipo_movimento character varying, p_tipo_consumo character varying, p_meta jsonb)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_upsert_commessa_attivita(p_commessa_id bigint, p_segment_key character varying, p_articolo_id uuid, p_istanza_utility_id bigint, p_data_attivita date, p_uom_id bigint, p_quantita numeric, p_competenza_mese date, p_competenza_dal date, p_competenza_al date, p_prezzo_snapshot numeric, p_prezzo_base_snapshot numeric, p_origine_prezzo character varying, p_tipo_variazione_applicata character varying, p_valore_variazione_applicata numeric, p_promo_id bigint, p_contratto_id bigint, p_categoria_cliente_id_snapshot smallint, p_classe_utenza_id_snapshot integer, p_qta_operativa numeric DEFAULT NULL::numeric, p_uom_operativa_id bigint DEFAULT NULL::bigint, p_factor_to_base numeric DEFAULT (1)::numeric, p_posticipa_al date DEFAULT NULL::date, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, p_valuta_id integer DEFAULT NULL::integer, p_area_geografica_id bigint DEFAULT NULL::bigint, p_listino_versione_id bigint DEFAULT NULL::bigint, p_prezzo_bloccato boolean DEFAULT false, p_pricing_mode character varying DEFAULT 'FIXED'::character varying, p_prezzo_da_riallineare boolean DEFAULT false, p_stato_approvazione character varying DEFAULT 'BOZZA'::character varying, p_stato_emissione character varying DEFAULT 'NON_EMESSA'::character varying, p_sorgente_tipo_id bigint DEFAULT NULL::bigint, p_sorgente_uid text DEFAULT NULL::text, p_tipo_movimento character varying DEFAULT 'NORMALE'::character varying, p_tipo_consumo character varying DEFAULT 'CONGUAGLIO'::character varying, p_meta jsonb DEFAULT '{}'::jsonb)
 RETURNS TABLE(attivita_id bigint, is_new boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_attivita_id              vendite.commesse_attivita.id%TYPE;
  v_is_new                   boolean;
  v_existing_stato_emissione vendite.commesse_attivita.stato_emissione%TYPE;
  v_modificabile             vendite.stati_commessa.modificabile%TYPE;
  v_competenza_mese          vendite.commesse_attivita.competenza_mese%TYPE;
  v_tipo_movimento           varchar(32);
  v_tipo_consumo             varchar(32);
  v_meta_effective           jsonb;
BEGIN
  -- =========================================================
  -- Upsert idempotente su (commessa_id, segment_key) con
  -- snapshot pricing v5 obbligatorio.
  -- Return: (attivita_id, is_new) tramite xmax=0.
  -- =========================================================

  -- Validazione parametri obbligatori "core".
  -- E_PARAMETRO_INVALIDO ha 1 %s (descrizione del parametro);
  -- il jsonb context conserva il dettaglio strutturato.
  IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','commessa_id','valore',p_commessa_id),
      NULL::uuid, 'commessa_id obbligatorio (>0)'
    );
  END IF;

  IF p_segment_key IS NULL OR btrim(p_segment_key) = '' OR length(btrim(p_segment_key)) > 128 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','segment_key','valore',p_segment_key),
      NULL::uuid, 'segment_key non valida (vuota o > 128 char)'
    );
  END IF;

  IF p_uom_id IS NULL OR p_uom_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','uom_id','valore',p_uom_id),
      NULL::uuid, 'uom_id obbligatorio (>0)'
    );
  END IF;

  IF p_istanza_utility_id IS NULL OR p_istanza_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','istanza_utility_id','valore',p_istanza_utility_id),
      NULL::uuid, 'istanza_utility_id obbligatoria (>0)'
    );
  END IF;

  IF p_quantita IS NULL OR p_quantita = 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','quantita','valore',p_quantita),
      NULL::uuid, 'quantita obbligatoria e diversa da 0'
    );
  END IF;

  IF p_prezzo_snapshot IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','prezzo_snapshot'),
      NULL::uuid, 'prezzo_snapshot obbligatorio'
    );
  END IF;

  -- Validazione dominio enum snapshot pricing v5: i CHECK DB
  -- (chk_commesse_attivita_origine_prezzo,
  --  chk_commesse_attivita_tipo_variazione_applicata) li
  -- garantirebbero comunque, ma qui la fail-fast e' piu'
  -- chiara come messaggio.
  IF p_origine_prezzo IS NOT NULL
     AND p_origine_prezzo NOT IN ('PROMO','CONTRATTO_OVERRIDE','CONTRATTO_LISTINO','CATEGORIA','MANUALE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','origine_prezzo','valore',p_origine_prezzo),
      NULL::uuid, concat('origine_prezzo non valida: ', p_origine_prezzo)
    );
  END IF;

  IF p_tipo_variazione_applicata IS NOT NULL
     AND p_tipo_variazione_applicata NOT IN ('PERCENTUALE','VALORE_FISSO','PREZZO_FISSO','NESSUNA') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','tipo_variazione_applicata','valore',p_tipo_variazione_applicata),
      NULL::uuid, concat('tipo_variazione_applicata non valido: ', p_tipo_variazione_applicata)
    );
  END IF;

  -- Normalizzazione tipo_movimento e tipo_consumo (salvati in meta).
  v_tipo_movimento := upper(COALESCE(NULLIF(btrim(p_tipo_movimento), ''), 'NORMALE'));
  IF v_tipo_movimento NOT IN ('NORMALE', 'RETTIFICA') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','tipo_movimento','valore',v_tipo_movimento),
      NULL::uuid, concat('tipo_movimento non valido: ', v_tipo_movimento)
    );
  END IF;

  v_tipo_consumo := upper(COALESCE(NULLIF(btrim(p_tipo_consumo), ''), 'CONGUAGLIO'));
  IF v_tipo_consumo NOT IN ('ACCONTO', 'CONGUAGLIO', 'STORNO') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','tipo_consumo','valore',v_tipo_consumo),
      NULL::uuid, concat('tipo_consumo non valido: ', v_tipo_consumo)
    );
  END IF;

  v_competenza_mese := date_trunc('month', p_competenza_mese)::date;
  v_meta_effective  := COALESCE(p_meta, '{}'::jsonb) || jsonb_build_object(
    'tipo_movimento', v_tipo_movimento,
    'tipo_consumo',   v_tipo_consumo
  );

  -- Guard: commessa esistente e in stato modificabile.
  SELECT sc.modificabile
  INTO v_modificabile
  FROM vendite.commesse c
  JOIN vendite.stati_commessa sc ON sc.id = c.stato_commessa_id
  WHERE c.id = p_commessa_id;

  IF NOT FOUND THEN
    -- E_COMMESSA_NON_TROVATA: 1 %s = commessa_id.
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_COMMESSA_NON_TROVATA',
      jsonb_build_object('commessa_id',p_commessa_id),
      NULL::uuid, p_commessa_id::text
    );
  END IF;

  IF NOT v_modificabile THEN
    -- E_COMMESSA_NON_MODIFICABILE: 1 %s = commessa_id.
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_COMMESSA_NON_MODIFICABILE',
      jsonb_build_object('commessa_id',p_commessa_id),
      NULL::uuid, p_commessa_id::text
    );
  END IF;

  -- Guard: riga esistente non gia' emessa.
  SELECT ca.stato_emissione INTO v_existing_stato_emissione
  FROM vendite.commesse_attivita ca
  WHERE ca.commessa_id = p_commessa_id
    AND ca.segment_key = btrim(p_segment_key)
  FOR UPDATE;

  IF v_existing_stato_emissione IS NOT NULL
     AND v_existing_stato_emissione <> 'NON_EMESSA' THEN
    -- E_COMMESSA_ATTIVITA_GIA_EMESSA: 3 %s = commessa, segment, stato.
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_COMMESSA_ATTIVITA_GIA_EMESSA',
      jsonb_build_object(
        'commessa_id', p_commessa_id,
        'segment_key', p_segment_key,
        'stato_emissione', v_existing_stato_emissione
      ),
      NULL::uuid,
      p_commessa_id::text,
      p_segment_key::text,
      v_existing_stato_emissione::text
    );
  END IF;

  -- Upsert idempotente su (commessa_id, segment_key).
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, qta_operativa, uom_operativa_id, factor_to_base,
    competenza_mese, competenza_dal, competenza_al, posticipa_al,
    tipo_doc_fiscale_id, valuta_id, area_geografica_id, listino_versione_id,
    prezzo_snapshot, prezzo_bloccato, pricing_mode, prezzo_da_riallineare,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_uid, meta,
    -- Snapshot pricing v5
    prezzo_base_snapshot, origine_prezzo,
    tipo_variazione_applicata, valore_variazione_applicata,
    promo_id, contratto_id,
    categoria_cliente_id_snapshot, classe_utenza_id_snapshot
  )
  VALUES (
    p_commessa_id, btrim(p_segment_key), p_articolo_id, p_istanza_utility_id, p_data_attivita,
    p_uom_id, p_quantita, p_qta_operativa, p_uom_operativa_id, COALESCE(p_factor_to_base, 1::numeric),
    v_competenza_mese, p_competenza_dal, p_competenza_al, p_posticipa_al,
    p_tipo_doc_fiscale_id, p_valuta_id, p_area_geografica_id, p_listino_versione_id,
    p_prezzo_snapshot, COALESCE(p_prezzo_bloccato, false), COALESCE(p_pricing_mode, 'FIXED'::varchar), COALESCE(p_prezzo_da_riallineare, false),
    COALESCE(p_stato_approvazione, 'BOZZA'::varchar), COALESCE(p_stato_emissione, 'NON_EMESSA'::varchar), p_sorgente_tipo_id, NULLIF(btrim(p_sorgente_uid), ''), v_meta_effective,
    p_prezzo_base_snapshot, p_origine_prezzo,
    p_tipo_variazione_applicata, p_valore_variazione_applicata,
    p_promo_id, p_contratto_id,
    p_categoria_cliente_id_snapshot, p_classe_utenza_id_snapshot
  )
  ON CONFLICT (commessa_id, segment_key) DO UPDATE
  SET articolo_id                    = EXCLUDED.articolo_id,
      istanza_utility_id             = EXCLUDED.istanza_utility_id,
      data_attivita                  = EXCLUDED.data_attivita,
      uom_id                         = EXCLUDED.uom_id,
      quantita                       = EXCLUDED.quantita,
      qta_operativa                  = EXCLUDED.qta_operativa,
      uom_operativa_id               = EXCLUDED.uom_operativa_id,
      factor_to_base                 = EXCLUDED.factor_to_base,
      competenza_mese                = EXCLUDED.competenza_mese,
      competenza_dal                 = EXCLUDED.competenza_dal,
      competenza_al                  = EXCLUDED.competenza_al,
      posticipa_al                   = EXCLUDED.posticipa_al,
      tipo_doc_fiscale_id            = EXCLUDED.tipo_doc_fiscale_id,
      valuta_id                      = EXCLUDED.valuta_id,
      area_geografica_id             = EXCLUDED.area_geografica_id,
      listino_versione_id            = EXCLUDED.listino_versione_id,
      prezzo_snapshot                = EXCLUDED.prezzo_snapshot,
      prezzo_bloccato                = EXCLUDED.prezzo_bloccato,
      pricing_mode                   = EXCLUDED.pricing_mode,
      prezzo_da_riallineare          = EXCLUDED.prezzo_da_riallineare,
      stato_approvazione             = EXCLUDED.stato_approvazione,
      stato_emissione                = EXCLUDED.stato_emissione,
      sorgente_tipo_id               = EXCLUDED.sorgente_tipo_id,
      sorgente_uid                   = EXCLUDED.sorgente_uid,
      meta                           = COALESCE(vendite.commesse_attivita.meta, '{}'::jsonb) || COALESCE(EXCLUDED.meta, '{}'::jsonb),
      -- Snapshot pricing v5: sovrascrive sempre (rappresenta
      -- lo snapshot del calcolo corrente).
      prezzo_base_snapshot           = EXCLUDED.prezzo_base_snapshot,
      origine_prezzo                 = EXCLUDED.origine_prezzo,
      tipo_variazione_applicata      = EXCLUDED.tipo_variazione_applicata,
      valore_variazione_applicata    = EXCLUDED.valore_variazione_applicata,
      promo_id                       = EXCLUDED.promo_id,
      contratto_id                   = EXCLUDED.contratto_id,
      categoria_cliente_id_snapshot  = EXCLUDED.categoria_cliente_id_snapshot,
      classe_utenza_id_snapshot      = EXCLUDED.classe_utenza_id_snapshot
  RETURNING id, (xmax = 0) INTO v_attivita_id, v_is_new;

  RETURN QUERY SELECT v_attivita_id, v_is_new;
END
$function$

COMMENT ON FUNCTION vendite.fn_upsert_commessa_attivita(p_commessa_id bigint, p_segment_key character varying, p_articolo_id uuid, p_istanza_utility_id bigint, p_data_attivita date, p_uom_id bigint, p_quantita numeric, p_competenza_mese date, p_competenza_dal date, p_competenza_al date, p_prezzo_snapshot numeric, p_prezzo_base_snapshot numeric, p_origine_prezzo character varying, p_tipo_variazione_applicata character varying, p_valore_variazione_applicata numeric, p_promo_id bigint, p_contratto_id bigint, p_categoria_cliente_id_snapshot smallint, p_classe_utenza_id_snapshot integer, p_qta_operativa numeric, p_uom_operativa_id bigint, p_factor_to_base numeric, p_posticipa_al date, p_tipo_doc_fiscale_id bigint, p_valuta_id integer, p_area_geografica_id bigint, p_listino_versione_id bigint, p_prezzo_bloccato boolean, p_pricing_mode character varying, p_prezzo_da_riallineare boolean, p_stato_approvazione character varying, p_stato_emissione character varying, p_sorgente_tipo_id bigint, p_sorgente_uid text, p_tipo_movimento character varying, p_tipo_consumo character varying, p_meta jsonb)
IS 'Upsert commesse_attivita (pricing v5). Restituisce (attivita_id, is_new). Snapshot pricing v5 obbligatorio in firma; passare NULL esplicito per dimensioni non applicabili (es. classe_utenza per utility commercio).';
```

---
{% include-markdown "signature-core.md" %}
