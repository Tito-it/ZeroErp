{% include-markdown "it/dbzero/vendite/manual/fn_upsert_commessa_attivita.md" %}
# ⚙️ Funzione `fn_upsert_commessa_attivita`

```sql
CREATE FUNCTION fn_upsert_commessa_attivita(p_commessa_id bigint, p_segment_key character varying, p_articolo_id uuid, p_istanza_utility_id bigint, p_data_attivita date, p_uom_id bigint, p_quantita numeric, p_competenza_mese date, p_competenza_dal date, p_competenza_al date, p_prezzo_snapshot numeric, p_prezzo_base_snapshot numeric, p_origine_prezzo character varying, p_tipo_variazione_applicata character varying, p_valore_variazione_applicata numeric, p_promo_id bigint, p_contratto_id bigint, p_categoria_cliente_id_snapshot smallint, p_classe_utenza_id_snapshot integer, p_qta_operativa numeric, p_uom_operativa_id bigint, p_factor_to_base numeric, p_posticipa_al date, p_tipo_doc_fiscale_id bigint, p_valuta_id integer, p_area_geografica_id bigint, p_listino_versione_id bigint, p_prezzo_bloccato boolean, p_pricing_mode character varying, p_prezzo_da_riallineare boolean, p_stato_approvazione character varying, p_stato_emissione character varying, p_sorgente_tipo_id bigint, p_sorgente_chiave text, p_tipo_movimento character varying, p_meta jsonb, p_causale_onere_id bigint, p_natura_doc_id bigint, p_fattura_riga_rettificata_id bigint, p_listino_riga_id bigint, p_sorgente_riga bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_upsert_commessa_attivita(p_commessa_id bigint, p_segment_key character varying, p_articolo_id uuid, p_istanza_utility_id bigint, p_data_attivita date, p_uom_id bigint, p_quantita numeric, p_competenza_mese date, p_competenza_dal date, p_competenza_al date, p_prezzo_snapshot numeric, p_prezzo_base_snapshot numeric, p_origine_prezzo character varying, p_tipo_variazione_applicata character varying, p_valore_variazione_applicata numeric, p_promo_id bigint, p_contratto_id bigint, p_categoria_cliente_id_snapshot smallint, p_classe_utenza_id_snapshot integer, p_qta_operativa numeric DEFAULT NULL::numeric, p_uom_operativa_id bigint DEFAULT NULL::bigint, p_factor_to_base numeric DEFAULT NULL::numeric, p_posticipa_al date DEFAULT NULL::date, p_tipo_doc_fiscale_id bigint DEFAULT NULL::bigint, p_valuta_id integer DEFAULT NULL::integer, p_area_geografica_id bigint DEFAULT NULL::bigint, p_listino_versione_id bigint DEFAULT NULL::bigint, p_prezzo_bloccato boolean DEFAULT false, p_pricing_mode character varying DEFAULT 'FIXED'::character varying, p_prezzo_da_riallineare boolean DEFAULT false, p_stato_approvazione character varying DEFAULT 'BOZZA'::character varying, p_stato_emissione character varying DEFAULT 'NON_EMESSA'::character varying, p_sorgente_tipo_id bigint DEFAULT NULL::bigint, p_sorgente_chiave text DEFAULT NULL::text, p_tipo_movimento character varying DEFAULT 'NORMALE'::character varying, p_meta jsonb DEFAULT '{}'::jsonb, p_causale_onere_id bigint DEFAULT NULL::bigint, p_natura_doc_id bigint DEFAULT NULL::bigint, p_fattura_riga_rettificata_id bigint DEFAULT NULL::bigint, p_listino_riga_id bigint DEFAULT NULL::bigint, p_sorgente_riga bigint DEFAULT NULL::bigint)
 RETURNS TABLE(attivita_id bigint, is_new boolean)
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_attivita_id              vendite.commesse_attivita.id%TYPE;
  v_is_new                   boolean;
  v_existing_stato_emissione vendite.commesse_attivita.stato_emissione%TYPE;
  v_modificabile             vendite.stati_commessa.modificabile%TYPE;
  v_competenza_mese          vendite.commesse_attivita.competenza_mese%TYPE;
  v_tipo_doc_fiscale_id      vendite.commesse_attivita.tipo_doc_fiscale_id%TYPE;
  v_tipo_movimento           vendite.commesse_attivita.tipo_movimento%TYPE;
  v_natura_doc_id            vendite.commesse_attivita.natura_doc_id%TYPE;
  v_meta_effective           jsonb;
  v_sorgente_id              vendite.commesse_attivita.sorgente_id%TYPE;
  v_sorgente_uid             vendite.commesse_attivita.sorgente_uid%TYPE;
BEGIN
  -- =========================================================
  -- Upsert idempotente su (commessa_id, segment_key) con
  -- snapshot pricing v5 obbligatorio.
  -- Return: (attivita_id, is_new) tramite xmax=0.
  -- rev 2026-08-18 (brief nota di credito, N1b+N5): la riga
  -- porta anche la NATURA del documento che produrra'
  -- (FATTURA / NOTA_CREDITO / ...) e, per una rettifica, la
  -- riga di fattura che sta correggendo.
  -- rev 2026-10-09 (brief-db-riga-listino-propagata-dalla-commessa,
  -- R-1): la riga porta anche la RIGA DI LISTINO da cui viene il
  -- prezzo. E' il legame che vendite.trgfn_listini_righe_guard_stato
  -- guarda per dire «propagata»: senza, nessuna riga di listino
  -- usata da una commessa risultava tale, e la rettifica N6 la
  -- lasciava modificare.
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

  -- ⚠️ La quantita' puo' essere NEGATIVA (rettifica di accredito,
  --    D-NC-2): il predicato e' « = 0 », non « <= 0 ». Non e' una
  --    svista storica da correggere — e' la porta da cui la nota
  --    di credito entra senza una seconda pipeline.
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
  -- L'elenco delle origini ha una sede sola: vendite.fn_origine_prezzo_ammessa,
  -- la stessa dei CHECK (che ammette anche NULL).
  IF NOT vendite.fn_origine_prezzo_ammessa(p_origine_prezzo) THEN
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

  -- Normalizzazione tipo_movimento (COLONNA dal 2026-07-17).
  -- Dominio tipo_movimento: NORMALE (push, specchio dell'origine) |
  -- ONERE (porta voce manuale, qta=1) | RETTIFICA (accrediti e
  -- conguagli). Il CHECK chk_commesse_attivita_tipo_movimento e'
  -- la difesa finale.
  v_tipo_movimento := upper(COALESCE(NULLIF(btrim(p_tipo_movimento), ''), 'NORMALE'));
  IF v_tipo_movimento NOT IN ('NORMALE', 'RETTIFICA', 'ONERE') THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','tipo_movimento','valore',v_tipo_movimento),
      NULL::uuid, concat('tipo_movimento non valido: ', v_tipo_movimento)
    );
  END IF;

  -- Coerenza causale <-> registro (difesa fail-fast; il CHECK
  -- chk_commesse_attivita_causale_onere e' la rete finale sul DB).
  -- La causale appartiene SOLO alle righe ONERE (porta oneri): una
  -- riga ONERE deve averla, una NORMALE/RETTIFICA non puo'.
  IF (v_tipo_movimento = 'ONERE') <> (p_causale_onere_id IS NOT NULL) THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','causale_onere_id','valore',p_causale_onere_id,'tipo_movimento',v_tipo_movimento),
      NULL::uuid, 'causale_onere_id ammessa se e solo se tipo_movimento=ONERE'
    );
  END IF;

  -- NATURA del documento (rev 2026-08-18, D-NC-3). Default
  -- risolto QUI e non nella firma: un id cablato fra i DEFAULT
  -- sarebbe una fotografia del catalogo di oggi, e resterebbe
  -- valido — cioe' sbagliato in silenzio — dopo un reseed.
  v_natura_doc_id := COALESCE(
      p_natura_doc_id,
      config.fn_get_natura_doc_fiscale_id('FATTURA'));

  IF v_natura_doc_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_CONFIG_MANCANTE',
      jsonb_build_object('parametro','natura_doc_id','valore',p_natura_doc_id),
      NULL::uuid, 'natura documento non risolta (config.nature_doc_fiscale)'
    );
  END IF;

  -- Coerenza rettifica <-> riga rettificata (rev 2026-08-18,
  -- D-NC-9). IMPLICAZIONE, non equivalenza: chi porta la riga
  -- rettificata E' una rettifica, ma una rettifica puo' non
  -- nascere da una riga di fattura (conguagli). Il CHECK
  -- chk_commesse_attivita_rettificata_e_rettifica e' la rete
  -- finale; qui il messaggio dice QUALE parametro e' incoerente.
  IF p_fattura_riga_rettificata_id IS NOT NULL
     AND v_tipo_movimento <> 'RETTIFICA' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_upsert_commessa_attivita','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','fattura_riga_rettificata_id',
                         'valore',p_fattura_riga_rettificata_id,
                         'tipo_movimento',v_tipo_movimento),
      NULL::uuid, 'fattura_riga_rettificata_id ammessa solo con tipo_movimento=RETTIFICA'
    );
  END IF;

  v_competenza_mese := date_trunc('month', p_competenza_mese)::date;
  -- tipo_movimento NON entra piu' in meta: vive sulla colonna
  -- (una casa sola).
  -- ⛔ rev 2026-10-13: tipo_consumo e' RITIRATO. La chiave si TOGLIE dal
  --    meta in ingresso: il reso (fn_accredita_riga_reso) ricopia il meta
  --    della riga d'origine, e le righe scritte prima di oggi la portano
  --    ancora. Senza questa sottrazione un valore che nessuno scrive piu'
  --    continuerebbe a nascere sulle rettifiche. Le righe gia' scritte
  --    restano come sono: sono la fotografia di quell'invio.
  v_meta_effective  := COALESCE(p_meta, '{}'::jsonb) - 'tipo_consumo';

  -- Normalize tipo_doc_fiscale_id (NO derivazione di business).
  -- Se non passato esplicitamente, applica il default OPZIONALE
  -- configurato sulla sorgente (config.sorgenti.tipo_doc_fiscale_id).
  -- Single source of truth lato DB. Se la sorgente non ha default,
  -- resta NULL: l'obbligo di valorizzazione sullo stato emittibile
  -- (APPROVATA+NON_EMESSA) e' imposto dal guard
  -- trg_commesse_attivita_a10_guard_tipo_doc_emittibile, non qui.
  v_tipo_doc_fiscale_id := p_tipo_doc_fiscale_id;
  IF v_tipo_doc_fiscale_id IS NULL AND p_sorgente_tipo_id IS NOT NULL THEN
    SELECT s.tipo_doc_fiscale_id
      INTO v_tipo_doc_fiscale_id
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id;
  END IF;

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

  -- =========================================================
  -- ⭐ rev 2026-10-12 (20261012-46, brief-db-annullo-a-valle-
  --   riapre-a-monte D-13 di Tid): IL LINK DOCUMENTO -> COMMESSA
  --   NASCE CON LA RIGA. Una riga che viene da un documento
  --   (sorgente di scope PUSH_COMMESSA: preventivo, ordine,
  --   contratto, bolla, consumi) aggancia il documento alla
  --   commessa dalla porta unica, vendite.fn_link_commessa_sorgente:
  --   idempotente sulla stessa commessa, rifiutata se il documento
  --   sta gia' in un'altra commessa APERTA (D-12). Prima il link lo
  --   scriveva il backend, a parte, prima di questa funzione: la
  --   regola «una sola commessa aperta» valeva solo se chi scriveva
  --   la riga si ricordava di chiamarlo, e i pgTAP che mandano in
  --   commessa dalla madre non la attraversavano mai.
  --   Fuori: le righe senza sorgente (ONERE, RETTIFICA) e le sorgenti
  --   che non sono documenti spinti in commessa (la COMMESSA stessa,
  --   PIPELINE_MARKER, che usano le fixture e gli smoke).
  --   La sorgente si legge per scope, lo stesso vocabolario dichiarato
  --   in config.sorgenti (chk_sorgenti_scope).
  -- =========================================================
  IF p_sorgente_tipo_id IS NOT NULL
     AND EXISTS (SELECT 1
                   FROM config.sorgenti s
                  WHERE s.id = p_sorgente_tipo_id
                    AND s.scope = 'PUSH_COMMESSA') THEN
    PERFORM vendite.fn_link_commessa_sorgente(
      p_commessa_id      => p_commessa_id,
      p_sorgente_tipo_id => p_sorgente_tipo_id,
      p_sorgente_chiave     => p_sorgente_chiave);
  END IF;

  -- =========================================================
  -- La chiave del documento nel modello: una sola delle due
  -- colonne, secondo il key_selector del tipo, dalla chiave che
  -- il chiamante passa (id o uid, in testo). Il BB che scrive
  -- solleva su un documento che non esiste o non si vede. Riga e
  -- documento li verifica il guard unico all'INSERT.
  -- =========================================================
  IF p_sorgente_tipo_id IS NOT NULL THEN
    SELECT k.sorgente_id, k.sorgente_uid
      INTO v_sorgente_id, v_sorgente_uid
      FROM script.fn_sorgente_chiave(p_sorgente_tipo_id, p_sorgente_chiave) k;
  END IF;

  -- Upsert idempotente su (commessa_id, segment_key).
  INSERT INTO vendite.commesse_attivita (
    commessa_id, segment_key, articolo_id, istanza_utility_id, data_attivita,
    uom_id, quantita, qta_operativa, uom_operativa_id, factor_to_base,
    competenza_mese, competenza_dal, competenza_al, posticipa_al,
    tipo_doc_fiscale_id, valuta_id, area_geografica_id, listino_versione_id,
    listino_riga_id,
    prezzo_snapshot, prezzo_bloccato, pricing_mode, prezzo_da_riallineare,
    stato_approvazione, stato_emissione, sorgente_tipo_id, sorgente_id, sorgente_uid,
    sorgente_riga,
    tipo_movimento, causale_onere_id, meta,
    -- Natura del documento e riga di fattura rettificata (2026-08-18)
    natura_doc_id, fattura_riga_rettificata_id,
    -- Snapshot pricing v5
    prezzo_base_snapshot, origine_prezzo,
    tipo_variazione_applicata, valore_variazione_applicata,
    promo_id, contratto_id,
    categoria_cliente_id_snapshot, classe_utenza_id_snapshot
  )
  VALUES (
    p_commessa_id, btrim(p_segment_key), p_articolo_id, p_istanza_utility_id, p_data_attivita,
    p_uom_id, p_quantita, p_qta_operativa, p_uom_operativa_id, p_factor_to_base,
    v_competenza_mese, p_competenza_dal, p_competenza_al, p_posticipa_al,
    v_tipo_doc_fiscale_id, p_valuta_id, p_area_geografica_id, p_listino_versione_id,
    p_listino_riga_id,
    p_prezzo_snapshot, COALESCE(p_prezzo_bloccato, false), COALESCE(p_pricing_mode, 'FIXED'::varchar), COALESCE(p_prezzo_da_riallineare, false),
    COALESCE(p_stato_approvazione, 'BOZZA'::varchar), COALESCE(p_stato_emissione, 'NON_EMESSA'::varchar), p_sorgente_tipo_id, v_sorgente_id, v_sorgente_uid,
    p_sorgente_riga,
    v_tipo_movimento, p_causale_onere_id, v_meta_effective,
    v_natura_doc_id, p_fattura_riga_rettificata_id,
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
      -- No-regressione: un re-push con tipo_doc in arrivo NULL non
      -- azzera un valore gia' risolto (brief-db-guard-tipo-doc-attivita).
      tipo_doc_fiscale_id            = COALESCE(EXCLUDED.tipo_doc_fiscale_id, vendite.commesse_attivita.tipo_doc_fiscale_id),
      valuta_id                      = EXCLUDED.valuta_id,
      area_geografica_id             = EXCLUDED.area_geografica_id,
      listino_versione_id            = EXCLUDED.listino_versione_id,
      -- La riga di listino segue il chiamante come la versione: e'
      -- la provenienza del prezzo CORRENTE. «Propagata» vuol dire
      -- citata ADESSO (decisione D-1 del brief): un re-push che
      -- cambia prezzo libera la riga vecchia, a meno che una AF gia'
      -- emessa la citi ancora.
      listino_riga_id                = EXCLUDED.listino_riga_id,
      prezzo_snapshot                = EXCLUDED.prezzo_snapshot,
      prezzo_bloccato                = EXCLUDED.prezzo_bloccato,
      pricing_mode                   = EXCLUDED.pricing_mode,
      prezzo_da_riallineare          = EXCLUDED.prezzo_da_riallineare,
      stato_approvazione             = EXCLUDED.stato_approvazione,
      stato_emissione                = EXCLUDED.stato_emissione,
      sorgente_tipo_id               = EXCLUDED.sorgente_tipo_id,
      sorgente_id                    = EXCLUDED.sorgente_id,
      sorgente_uid                   = EXCLUDED.sorgente_uid,
      sorgente_riga                  = EXCLUDED.sorgente_riga,
      -- Il registro della riga lo dichiara il chiamante (mai NULL:
      -- normalizzato a NORMALE). I segment_key non si incrociano fra
      -- push (ORD:/DDT:) e porta manuale (MAN:), quindi un push
      -- non puo' declassare una riga ONERE.
      tipo_movimento                 = EXCLUDED.tipo_movimento,
      -- La causale segue il registro (coerente col CHECK
      -- biconditional): NULL per NORMALE, valorizzata per ONERE.
      causale_onere_id               = EXCLUDED.causale_onere_id,
      -- Natura e riga rettificata seguono il chiamante, come
      -- tipo_movimento: nessun COALESCE difensivo, perche' non
      -- esiste un percorso in cui un push atterri sul segmento di
      -- una rettifica (i suffissi #RET: non si incrociano con
      -- ORD:/DDT:/MAN:).
      natura_doc_id                  = EXCLUDED.natura_doc_id,
      fattura_riga_rettificata_id    = EXCLUDED.fattura_riga_rettificata_id,
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

COMMENT ON FUNCTION vendite.fn_upsert_commessa_attivita(p_commessa_id bigint, p_segment_key character varying, p_articolo_id uuid, p_istanza_utility_id bigint, p_data_attivita date, p_uom_id bigint, p_quantita numeric, p_competenza_mese date, p_competenza_dal date, p_competenza_al date, p_prezzo_snapshot numeric, p_prezzo_base_snapshot numeric, p_origine_prezzo character varying, p_tipo_variazione_applicata character varying, p_valore_variazione_applicata numeric, p_promo_id bigint, p_contratto_id bigint, p_categoria_cliente_id_snapshot smallint, p_classe_utenza_id_snapshot integer, p_qta_operativa numeric, p_uom_operativa_id bigint, p_factor_to_base numeric, p_posticipa_al date, p_tipo_doc_fiscale_id bigint, p_valuta_id integer, p_area_geografica_id bigint, p_listino_versione_id bigint, p_prezzo_bloccato boolean, p_pricing_mode character varying, p_prezzo_da_riallineare boolean, p_stato_approvazione character varying, p_stato_emissione character varying, p_sorgente_tipo_id bigint, p_sorgente_chiave text, p_tipo_movimento character varying, p_meta jsonb, p_causale_onere_id bigint, p_natura_doc_id bigint, p_fattura_riga_rettificata_id bigint, p_listino_riga_id bigint, p_sorgente_riga bigint)
IS 'La madre della riga di commessa: upsert idempotente su (commessa_id, segment_key) di una riga operativa, con lo snapshot di prezzo obbligatorio. Ritorna (attivita_id, is_new). La segment_key la compone chi chiama, con script.fn_segment_key. La provenienza: p_sorgente_tipo_id con la chiave del documento come la ha il chiamante (p_sorgente_chiave, l''id o l''uid in testo, per qualunque tipo) e la riga del documento (p_sorgente_riga); la chiave si scrive nella colonna del key_selector del tipo (sorgente_id o sorgente_uid), tradotta da script.fn_sorgente_chiave, che solleva su un documento che non esiste o non si vede (E_SORG_NOT_FOUND, E_SORG_FORMATO, E_SORG_NORM_NON_RISOLTA); documento e riga li verifica script.trgfn_guard_sorgente (E_SORG_RIGA_NON_DEL_DOCUMENTO), la coerenza fra chiave del push e documento trg_commesse_attivita_a10_guard_sorgente_segment_ins_upd. NULL in p_sorgente_riga vuol dire provenienza dal documento intero (consumi, quote fisse del listino di un contratto). Le righe senza documento (ONERE manuale, RETTIFICA) passano tipo e chiave NULL. Una riga con un documento di scope PUSH_COMMESSA lega il documento alla commessa dalla porta vendite.fn_link_commessa_sorgente prima di scriversi: un documento sta in una sola commessa aperta. La riga porta anche la natura del documento che produrra'' (p_natura_doc_id, default per chiave naturale), la riga di fattura che una RETTIFICA corregge (p_fattura_riga_rettificata_id) e la riga di listino che ha dato il prezzo (p_listino_riga_id, che segue il chiamante anche nell''ON CONFLICT: «propagata» vuol dire citata adesso). p_quantita ammette valori negativi (la nota di credito entra da qui). Solleva E_COMMESSA_NON_TROVATA, E_COMMESSA_NON_MODIFICABILE, E_COMMESSA_ATTIVITA_GIA_EMESSA (la riga esistente non e'' piu'' NON_EMESSA), E_PARAMETRO_INVALIDO. I chiamanti passano gli argomenti per nome: vendite.fn_batch_upsert_commessa_attivita, vendite.fn_aggiungi_onere_commessa, vendite.fn_accredita_riga_reso, il builder dbops.fn_pgtap_crea_commessa_attivita e il backend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
