{% include-markdown "it/dbzero/vendite/manual/fn_aggiungi_onere_commessa.md" %}
# ⚙️ Funzione `fn_aggiungi_onere_commessa`

```sql
CREATE FUNCTION fn_aggiungi_onere_commessa(p_commessa_id bigint, p_istanza_utility_id bigint, p_articolo_onere_id uuid, p_importo numeric, p_tipo_doc_fiscale_id bigint, p_motivo text, p_data_attivita date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_aggiungi_onere_commessa(p_commessa_id bigint, p_istanza_utility_id bigint, p_articolo_onere_id uuid, p_importo numeric, p_tipo_doc_fiscale_id bigint, p_motivo text DEFAULT NULL::text, p_data_attivita date DEFAULT NULL::date)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_data            vendite.commesse_attivita.data_attivita%TYPE;
  v_comp_mese       vendite.commesse_attivita.competenza_mese%TYPE;
  v_uom_id          catalogo.articoli.uom_id%TYPE;
  v_causale_id      catalogo.articoli.causale_onere_id%TYPE;
  -- v_progressivo e' un contatore (MAX+1 sulla chiave), non il riflesso di una colonna.
  v_progressivo     integer;
  v_segment_key     vendite.commesse_attivita.segment_key%TYPE;
  v_attivita_id     vendite.commesse_attivita.id%TYPE;
  -- v_is_new e' l'esito di fn_upsert_commessa_attivita (RETURNS TABLE), non una colonna.
  v_is_new          boolean;
BEGIN
  -- Scopo: madre DB della "porta oneri". Crea una riga
  -- commesse_attivita di puro valore (qta=1, tipo_movimento='ONERE')
  -- gia' APPROVATA, da un ARTICOLO-ONERE (che porta causale+uom+IVA).
  -- Perimetro: una sola unita' atomica (la chiamata), riusa
  -- fn_upsert_commessa_attivita per lo specchio idempotente, e scrive
  -- l'audit su commesse_attivita_log. Risultato: id della riga creata.
  -- Il presidio permessi (carica_voce_manuale) vive sul BE, non qui:
  -- la madre e' usabile anche da un processo autorizzato.

  -- Guard parametri ID (AGENTS.md: NULL o <=0 -> errore parlante).
  IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_aggiungi_onere_commessa','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','commessa_id','valore',p_commessa_id),
      NULL::uuid, 'commessa_id obbligatorio (>0)');
  END IF;

  IF p_istanza_utility_id IS NULL OR p_istanza_utility_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_aggiungi_onere_commessa','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','istanza_utility_id','valore',p_istanza_utility_id),
      NULL::uuid, 'istanza_utility_id obbligatoria (>0)');
  END IF;

  -- La riga nasce APPROVATA+NON_EMESSA = emittibile: il guard
  -- tipo_doc_emittibile esige tipo_doc valorizzato -> obbligatorio qui.
  IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_aggiungi_onere_commessa','E_PARAMETRO_INVALIDO',
      jsonb_build_object('parametro','tipo_doc_fiscale_id','valore',p_tipo_doc_fiscale_id),
      NULL::uuid, 'tipo_doc_fiscale_id obbligatorio (>0): la riga onere nasce emittibile');
  END IF;

  -- Importo: solo positivo (la porta porta valore, qta=1). Una NC
  -- travestita (importo negativo) e' vietata per costruzione.
  IF p_importo IS NULL OR p_importo <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_aggiungi_onere_commessa','E_ONERE_IMPORTO_NON_VALIDO',
      jsonb_build_object('campo','importo','importo',p_importo),
      NULL::uuid, COALESCE(p_importo::text,'NULL'));
  END IF;

  -- Articolo-onere: deve esistere, essere attivo ed ESSERE un onere
  -- (causale_onere_id NOT NULL). Da qui derivano causale e uom (e a
  -- valle l'IVA, che e' la iva_id dell'articolo).
  SELECT a.uom_id, a.causale_onere_id
    INTO v_uom_id, v_causale_id
    FROM catalogo.articoli a
   WHERE a.id = p_articolo_onere_id
     AND a.attivo
     AND a.causale_onere_id IS NOT NULL;

  IF NOT FOUND THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_aggiungi_onere_commessa','E_ONERE_ARTICOLO_MANCANTE',
      jsonb_build_object('campo','articolo_onere_id','articolo_onere_id',p_articolo_onere_id),
      NULL::uuid, COALESCE(p_articolo_onere_id::text,'NULL'));
  END IF;

  v_data      := COALESCE(p_data_attivita, script.fn_data_operativa());
  v_comp_mese := date_trunc('month', v_data)::date;

  -- =====================================================
  -- segment_key progressivo della porta manuale per la commessa.
  -- Convenzione dedicata MAN:<commessa>:<n> (nessun prefisso manuale
  -- esisteva prima). Non si incrocia con i segment di push (ORD:/DDT:).
  --
  -- CONCORRENZA (brief-db-race-segment-key-onere, 2026-07-23):
  -- il progressivo va calcolato SOTTO LOCK. Senza, due operatori
  -- sulla stessa commessa leggono lo stesso valore, generano la
  -- stessa segment_key e la fn_upsert (ON CONFLICT su
  -- (commessa_id, segment_key)) AGGIORNA la riga del primo invece
  -- di crearne una nuova: un onere perso in silenzio, 200 OK a
  -- entrambi. La porta manuale e' il primo scrittore concorrente
  -- reale di questa fn (i push serializzano su worker singolo).
  --
  -- Advisory lock TRANSAZIONALE per commessa: serializza solo gli
  -- oneri della stessa commessa, si rilascia da solo a fine
  -- transazione, nessun oggetto nuovo. Sta QUI, dopo tutte le
  -- guard e dopo il lookup articolo: una chiamata invalida non
  -- deve serializzare gli altri operatori.
  -- Forma a 2 argomenti (namespace + chiave): lo spazio dei lock a
  -- 1 argomento e' condiviso con altre feature del progetto.
  -- =====================================================
  PERFORM pg_advisory_xact_lock(
    hashtext('vendite.fn_aggiungi_onere_commessa'),
    hashtext(p_commessa_id::text)
  );

  -- NOTA ISOLAMENTO: sotto READ COMMITTED (default PostgreSQL e
  -- Django) la SELECT qui sotto prende uno snapshot NUOVO e vede la
  -- riga committata da chi ha appena rilasciato il lock, quindi il
  -- progressivo e' corretto. Sotto REPEATABLE READ/SERIALIZABLE lo
  -- snapshot resta fisso all'inizio della transazione e il progressivo
  -- sarebbe stale: in quel caso e' il guard
  -- E_ONERE_SEGMENT_DUPLICATO a valle a impedire la perdita
  -- silenziosa (fallisce invece di sovrascrivere).
  --
  -- Progressivo dal MASSIMO, non dal count: il conteggio assume
  -- l'invariante "count = max", che nulla garantisce. Una sola
  -- DELETE di una riga MAN: e count+1 punterebbe su una chiave gia'
  -- esistente -> stessa collisione, senza nemmeno la concorrenza.
  -- I buchi nella numerazione sono ammessi e non significano nulla.
  -- Il match e' sulla forma PIENA della chiave (commessa inclusa):
  -- una chiave MAN: non auto-coerente non entra nel calcolo.
  SELECT COALESCE(MAX((split_part(ca.segment_key, ':', 3))::integer), 0) + 1
    INTO v_progressivo
    FROM vendite.commesse_attivita ca
   WHERE ca.commessa_id = p_commessa_id
     AND ca.segment_key ~ ('^MAN:' || p_commessa_id || ':[0-9]+$');

  v_segment_key := format('MAN:%s:%s', p_commessa_id, v_progressivo);

  -- Crea la riga onere. Nasce APPROVATA (nessuna approvazione a due
  -- passi); poi fa il giro normale: emissione -> AF -> fattura.
  -- SOURCELESS (sorgente NULL) + tipo_movimento='ONERE' + causale
  -- snapshottata dall'articolo.
  SELECT u.attivita_id, u.is_new
    INTO v_attivita_id, v_is_new
    FROM vendite.fn_upsert_commessa_attivita(
      p_commessa_id                 => p_commessa_id,
      p_segment_key                 => v_segment_key,
      p_articolo_id                 => p_articolo_onere_id,
      p_istanza_utility_id          => p_istanza_utility_id,
      p_data_attivita               => v_data,
      p_uom_id                      => v_uom_id,
      p_quantita                    => 1,
      p_competenza_mese             => v_comp_mese,
      p_competenza_dal              => v_data,
      p_competenza_al               => v_data,
      p_prezzo_snapshot             => p_importo,
      p_prezzo_base_snapshot        => p_importo,
      p_origine_prezzo              => 'MANUALE',
      p_tipo_variazione_applicata   => 'NESSUNA',
      p_valore_variazione_applicata => NULL,
      p_promo_id                    => NULL,
      p_contratto_id                => NULL,
      p_categoria_cliente_id_snapshot => NULL,
      p_classe_utenza_id_snapshot   => NULL,
      p_qta_operativa               => NULL,
      p_uom_operativa_id            => NULL,
      p_factor_to_base              => 1,
      p_posticipa_al                => NULL,
      p_tipo_doc_fiscale_id         => p_tipo_doc_fiscale_id,
      p_valuta_id                   => NULL,
      p_area_geografica_id          => NULL,
      p_listino_versione_id         => NULL,
      p_prezzo_bloccato             => true,
      p_pricing_mode                => 'FIXED',
      p_prezzo_da_riallineare       => false,
      p_stato_approvazione          => 'APPROVATA',
      p_stato_emissione             => 'NON_EMESSA',
      p_sorgente_tipo_id            => NULL,
      p_sorgente_chiave             => NULL,
      p_tipo_movimento              => 'ONERE',
      p_meta                        => jsonb_strip_nulls(jsonb_build_object('motivo_onere', p_motivo)),
      p_causale_onere_id            => v_causale_id
    ) AS u;

  -- Difesa in profondita' (brief-db-race-segment-key-onere §2):
  -- la porta oneri e' una CREATE, non una upsert. Riusa
  -- fn_upsert_commessa_attivita solo per non duplicarne il mapping
  -- a 38 parametri (no logica duplicata fra livelli), ma un
  -- "update" qui non e' MAI legittimo: ogni chiamata e' un onere
  -- NUOVO. Se is_new e' false siamo su una collisione di
  -- segment_key -> fallire rumorosamente invece di sovrascrivere
  -- l'onere di un altro operatore.
  -- Il guard sta QUI e non dentro fn_upsert_commessa_attivita:
  -- la' l'update e' la semantica corretta (re-push idempotente dei
  -- documenti sorgente) e spostarlo romperebbe i push.
  -- Con il lock + MAX(...)+1 sopra non deve mai scattare: se scatta
  -- e' una regressione, o una transazione fuori READ COMMITTED.
  IF NOT v_is_new THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite','fn_aggiungi_onere_commessa','E_ONERE_SEGMENT_DUPLICATO',
      jsonb_build_object(
        'commessa_id', p_commessa_id,
        'segment_key', v_segment_key,
        'attivita_id', v_attivita_id),
      NULL::uuid, v_segment_key, p_commessa_id::text);
  END IF;

  -- Audit: PRIMO evento vero di commesse_attivita_log (finora nessun
  -- writer). tx_id e audit sono gestiti dai trigger della tabella.
  -- is_new resta nel dettaglio come testimone dell'invariante: dopo
  -- il guard qui sopra puo' valere solo true.
  INSERT INTO vendite.commesse_attivita_log (commessa_attivita_id, evento, dettaglio)
  VALUES (
    v_attivita_id,
    'ONERE_AGGIUNTO',
    jsonb_build_object(
      'articolo_onere_id',  p_articolo_onere_id,
      'causale_onere_id',   v_causale_id,
      'importo',            p_importo,
      'motivo',             p_motivo,
      'istanza_utility_id', p_istanza_utility_id,
      'tipo_doc_fiscale_id',p_tipo_doc_fiscale_id,
      'segment_key',        v_segment_key,
      'is_new',             v_is_new
    )
  );

  RETURN v_attivita_id;
END
$function$

COMMENT ON FUNCTION vendite.fn_aggiungi_onere_commessa(p_commessa_id bigint, p_istanza_utility_id bigint, p_articolo_onere_id uuid, p_importo numeric, p_tipo_doc_fiscale_id bigint, p_motivo text, p_data_attivita date)
IS 'Madre DB porta oneri (brief-db-immutabilita-quantita-e-porta-oneri §4c). Da un ARTICOLO-ONERE (catalogo.articoli.causale_onere_id NOT NULL, 1:1) crea una riga commesse_attivita di puro valore (qta=1, tipo_movimento=ONERE) gia'' APPROVATA, SOURCELESS. Deriva causale+uom (e a valle IVA) dall''articolo; snapshotta la causale su commesse_attivita.causale_onere_id. Importo solo positivo. Riusa fn_upsert_commessa_attivita e scrive commesse_attivita_log (evento ONERE_AGGIUNTO). Usabile da endpoint o processo autorizzato (presidio permessi sul BE). Ritorna attivita_id. CONCORRENZA (brief-db-race-segment-key-onere, 2026-07-23): progressivo segment_key MAN:<commessa>:<n> da MAX(...)+1 sotto pg_advisory_xact_lock per commessa (serializza solo gli oneri della stessa commessa); guard E_ONERE_SEGMENT_DUPLICATO se la upsert aggiorna invece di creare (la porta e'' una CREATE, non una upsert). Buchi nella numerazione ammessi. rev 2026-07-23.';
```

</div>

---
{% include-markdown "signature-core.md" %}
