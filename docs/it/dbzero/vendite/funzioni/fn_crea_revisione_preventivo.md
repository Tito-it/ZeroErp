{% include-markdown "it/dbzero/vendite/manual/fn_crea_revisione_preventivo.md" %}
# ⚙️ Funzione `fn_crea_revisione_preventivo`

```sql
CREATE FUNCTION fn_crea_revisione_preventivo(p_preventivo_id bigint, p_user text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_crea_revisione_preventivo(p_preventivo_id bigint, p_user text)
 RETURNS TABLE(nuovo_preventivo_id bigint, numero character varying, nuova_rev integer)
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-31 (20261031-65, brief-db-scadenza-preventivi E-3 (ii)):
--   la revisione si crea dallo stato di emissione e da quello di
--   scadenza, che il vocabolario dichiara (colonne emissione e
--   scadenza della riga dello stato), non dal letterale 'EMESSO'.
--   Lo stato della rev N non cambia, come gia' da EMESSO.
-- rev 2026-10-24 (20261024-21, brief-modello-documento-vendita N-1/P-2):
--   lo stato iniziale non si scrive piu' qui: lo mette il trigger della
--   nascita (script.trgfn_doc_stato_iniziale), letto dal vocabolario.
DECLARE
  v_stato_corrente_cod  config.stati_doc_preventivi.codice_interno%TYPE;
  -- Lo stato di oggi e' l'emissione? la scadenza? Dal vocabolario
  -- (rev 2026-10-31).
  v_emissione           config.stati_doc_preventivi.emissione%TYPE;
  v_scadenza            config.stati_doc_preventivi.scadenza%TYPE;
  v_numero              vendite.preventivi.numero%TYPE;
  v_max_rev             vendite.preventivi.rev%TYPE;
  v_new_id              vendite.preventivi.id%TYPE;
  -- La data della testata nuova, letta dal RETURNING (rev 2026-10-13):
  -- e' il riferimento delle date di consegna copiate.
  v_new_data            vendite.preventivi.data%TYPE;
  v_new_rev             vendite.preventivi.rev%TYPE;
  v_has_draft           boolean;
  v_riga                vendite.preventivi_righe%ROWTYPE;
  v_new_riga_id         vendite.preventivi_righe.id%TYPE;
BEGIN
  -- ==========================================================
  -- Scopo:
  --   Creare una nuova revisione in DRAFT a partire da un
  --   preventivo in stato EMESSO. Copia testata, righe attive,
  --   indirizzi e componenti BoM (con FK remap). Non gestisce
  --   is_revision_attiva: l'attivazione e' derivata in
  --   vendite.vw_preventivi tramite is_abortito degli stati.
  --
  -- Regole (rev 2026-05-15):
  --   - stato corrente DEVE essere quello di emissione (EMESSO) o, dal
  --     2026-10-31, quello di scadenza (SCADUTO): dal vocabolario
  --   - non deve esistere gia' una revisione DRAFT per lo stesso numero
  --   - la nuova revisione ha rev = max(rev)+1, stato DRAFT
  --   - righe copiate: solo attive con quantita > 0, ORDER BY ordine, id
  --   - componenti BoM delle righe copiate: TUTTI, anche gli opzionali
  --     spenti, rimappati sulla riga nuova per identita' (rev 2026-10-08)
  --   - indirizzi: tutti copiati
  --
  -- Parametri:
  --   p_preventivo_id : ID del preventivo da revisionare
  --   p_user          : utente che esegue l'operazione
  --
  -- NOTE codice_interno (rev 2026-06-28, analisi-hardcoded-codice §3a #2):
  --   stato corrente e risoluzione DRAFT per codice_interno (immutabile),
  --   non per codice (mutabile). Literali EMESSO/DRAFT sono codice_interno.
  --
  -- NOTE data di consegna (rev 2026-09-14, 20260914-13):
  --   le righe copiate portano data_consegna_richiesta_cliente. La data
  --   e' del CLIENTE, non una promessa nostra: una revisione rinegozia
  --   prezzi e quantita', non cio' che il cliente ha chiesto. Le righe si
  --   copiano con un elenco ESPLICITO di colonne, quindi una colonna non
  --   nominata non passa — e' lo stesso punto in cui si perdeva al push
  --   (20260913-20). Brief: brief-db-modifiche-certe-ciclo-vendita-e-articolo.
  --   ⚠️ rev 2026-10-13 (collaudo date di consegna, decisione di Tid): una
  --   data ANTERIORE alla data della rev N+1 (che nasce con la data di oggi)
  --   si copia NULL, per la regola script.fn_data_consegna_ammessa — quella
  --   del guard di riga, che altrimenti rifiuterebbe l'INSERT. Non si
  --   rifiuta la revisione (la rev N e' fuori bozza: la data li' non si
  --   correggerebbe) e non si porta alla data della revisione (sarebbe una
  --   richiesta mai fatta dal cliente). La rev N la conserva.
  --
  -- NOTE marche di approvazione prezzo (rev 2026-09-14, 20260914-14, D di Tid):
  --   stato_approvazione_prezzo e pratica_approvazione_prezzo_id si copiano
  --   1:1 sulla riga, come gia' sui componenti qui sotto e come
  --   fn_crea_revisione_offerta (20260601-05). Ragione: i gate L3 scattano
  --   sull'edit, non alla revisione; lo stato e' l'unico marcatore
  --   persistente che un prezzo fuori policy e' autorizzato o in attesa.
  --   Azzerarlo faceva nascere la rev N+1 con lo stesso prezzo e senza
  --   marca (com'era dal 2026-04-22 al 20260914-13). Una riga PENDING
  --   copiata resta protetta da trgfn_righe_guard_pending. ⚠️ Caveat, lo
  --   stesso dell'offerta: la pratica resta agganciata per id a ENTRAMBE
  --   le righe e il suo meta nomina la riga della rev N — il ciclo di vita
  --   della pratica su una rev superata e' del dominio approvazioni (BE),
  --   refactor-prezzi.md 4.7. Non si decide qui.
  --
  -- NOTE l'ancora si copia (rev 2026-09-15, 20260915-41, D3 di Tid):
  --   la testata della rev N+1 porta emittente_fiscale_id della rev N.
  --   Prima NON era nella lista colonne e lo riempiva il trigger di default
  --   di sessione (la copia per documento di allora, oggi il BB
  --   script.trgfn_default_emittente_fiscale): per un operatore della
  --   stessa azienda lo stesso valore; per un super admin con emittente
  --   attivo B che revisiona un preventivo di A, la rev N+1 prendeva B e
  --   trgfn_preventivi_guard_emittente_ba la rifiutava — un difetto
  --   mascherato da un guard. La revisione e' LO STESSO documento: copia
  --   l'ancora, come fn_crea_revisione_offerta. Trovato censendo chi si
  --   appoggiava al default senza dirlo (brief-db-emittente-di-default-un-bb-solo, 7.1).
  --
  --   ⚠️ Colonne che NON si copiano di proposito: natura_vendita_id (la
  --   deriva e la congela il trigger BEFORE INSERT dall'articolo), tx_id
  --   (framework), id/data_insert/data_update (identity e audit). Il
  --   presidio che pretende l'elenco COMPLETO o la dichiarazione e'
  --   db/pgtap/vendite/test-fn-crea-revisione-preventivo-riga-completa-v1.
  --
  -- NOTE i componenti (rev 2026-10-08, 20261008-35, D-1 di Tid):
  --   brief-db-righe-e-componenti-le-altre-famiglie §2.1, la forma di
  --   fn_crea_revisione_offerta (20261005-19). Due cambi:
  --   * si copiano TUTTI i componenti delle righe copiate, anche gli
  --     opzionali spenti. Spegnere un opzionale e' una scelta del
  --     preventivo, e la revisione e' lo stesso documento: non portarlo la
  --     cancellava, e nella rev N+1 non si poteva piu' riaccendere. Non
  --     cambia cosa si vende: il push a ordine porta solo gli attivi;
  --   * la riga nuova si lega alla vecchia per IDENTITA': una riga alla
  --     volta, col suo RETURNING, e i componenti sull'id restituito. Prima
  --     un ROW_NUMBER su (ordine, id) dei due insiemi, che regge solo finche'
  --     gli id nuovi nascono nell'ordine della SELECT — una proprieta'
  --     dell'esecuzione, non un contratto di SQL.
  --   I trigger del componente lavorano come alla nascita: m50 ricalcola la
  --   quantita' dalla riga; z90 il prezzo della riga dai componenti ATTIVI,
  --   cioe' lo stesso della rev N. La revisione e' in DRAFT: il lock «fuori
  --   bozza» dei componenti (20261008-34) la lascia passare.
  --   ⚠️ I totali: il trigger STATEMENT su preventivi_righe ora scatta una
  --   volta per riga invece che una volta sola. L'ultimo passaggio vede
  --   tutte le righe: il risultato e' lo stesso.
  -- ==========================================================

  -- Guard: parametro obbligatorio
  IF p_preventivo_id IS NULL OR p_preventivo_id <= 0 THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'E_PARAMETRO_INVALIDO',
      jsonb_build_object('param', 'p_preventivo_id', 'value', p_preventivo_id),
      NULL::uuid,
      'p_preventivo_id = ' || COALESCE(p_preventivo_id::text, 'NULL')
    );
  END IF;

  -- Recupera stato corrente e numero
  SELECT sdp.codice_interno, sdp.emissione, sdp.scadenza, p.numero
    INTO v_stato_corrente_cod, v_emissione, v_scadenza, v_numero
    FROM vendite.preventivi p
    JOIN config.stati_doc_preventivi sdp ON sdp.id = p.stato_doc_preventivo_id
   WHERE p.id = p_preventivo_id;

  IF v_stato_corrente_cod IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'E_PREV_STATO_CORRENTE_NON_TROVATO',
      jsonb_build_object('preventivo_id', p_preventivo_id),
      NULL::uuid,
      p_preventivo_id::text
    );
  END IF;

  -- Guard: revisione ammessa SOLO dallo stato di emissione e da quello
  -- di scadenza (rev 2026-10-31, E-3 (ii) di Tid): un preventivo scaduto
  -- si ripropone con una revisione, che nasce in bozza e lascia
  -- riscrivere la validita'. Gli altri stati chiusi (ACCETTATO,
  -- RIFIUTATO, EVASO, ANNULLATO) restano esclusi. Le colonne della riga
  -- del vocabolario che la SELECT ha gia': nessun letterale di stato.
  IF NOT (v_emissione OR v_scadenza) THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'E_PREV_REVISIONE_STATO_NON_AMMESSO',
      jsonb_build_object(
        'preventivo_id', p_preventivo_id,
        'stato_corrente', v_stato_corrente_cod
      ),
      NULL::uuid,
      p_preventivo_id::text, v_stato_corrente_cod
    );
  END IF;

  -- Guard: non deve esistere gia' una revisione DRAFT
  SELECT EXISTS(
    SELECT 1
      FROM vendite.preventivi p2
      JOIN config.stati_doc_preventivi sdp2 ON sdp2.id = p2.stato_doc_preventivo_id
     WHERE p2.numero = v_numero
       AND sdp2.codice_interno = 'DRAFT'
  ) INTO v_has_draft;

  IF v_has_draft THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite', 'fn_crea_revisione_preventivo',
      'E_PREV_REVISIONE_BOZZA_ESISTENTE',
      jsonb_build_object('numero', v_numero),
      NULL::uuid,
      v_numero
    );
  END IF;

  -- Guard (rev 2026-09-24): nessuna revisione con un prezzo IN ATTESA.
  --   La revisione ricopia stato e pratica di approvazione 1:1 (sotto): una
  --   riga in attesa ricopiata resterebbe legata alla pratica della rev N,
  --   l'esito arriverebbe li' e sulla rev N+1 l'attesa non finirebbe piu' —
  --   bloccata dal guard per riga e, dal 20260924-21, anche all'emissione.
  --   Decisione di Tid del 2026-09-24: prima l'esito, poi la revisione.
  -- ⭐ Il predicato e' script.fn_check_prezzi_in_attesa, lo STESSO con cui
  --   fn_available_actions_preventivo spegne «Crea revisione»: qui si
  --   solleva soltanto. Approvato e rifiutato NON bloccano: si ricopiano.
  PERFORM script.fn_raise_primo_motivo_se_presente(
    'vendite', 'fn_crea_revisione_preventivo',
    script.fn_check_prezzi_in_attesa('vendite.preventivi'::regclass, p_preventivo_id),
    NULL,
    NULL::uuid,
    jsonb_build_object('preventivo_id', p_preventivo_id, 'numero', v_numero));

  -- Calcola nuova revisione
  SELECT COALESCE(MAX(p.rev), 0) + 1
    INTO v_new_rev
    FROM vendite.preventivi p
   WHERE p.numero = v_numero;

  -- Crea nuova testata (copia campi dal preventivo originale).
  -- Totali a 0: il trigger STATEMENT su preventivi_righe li ricalcola
  -- dopo ogni INSERT delle righe copiate (una riga alla volta dal
  -- 2026-10-08: l'ultimo passaggio vede tutte le righe).
  INSERT INTO vendite.preventivi (
    numero, rev, emittente_fiscale_id,
    billing_account_id, istanza_utility_id, utility_id,
    validita_dal, validita_al,
    totale_imponibile, totale_iva, totale_documento,
    valuta_id, competenza_mese, fatturazione_immediata,
    data, termine_pagamento_id,
    storicizza, meta,
    user_insert, user_update
  )
  SELECT
    p.numero, v_new_rev, p.emittente_fiscale_id,
    p.billing_account_id, p.istanza_utility_id, p.utility_id,
    p.validita_dal, p.validita_al,
    0, 0, 0,
    p.valuta_id, p.competenza_mese, p.fatturazione_immediata,
    (SELECT script.fn_data_operativa()), p.termine_pagamento_id,
    p.storicizza, p.meta,
    COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
  FROM vendite.preventivi p
  WHERE p.id = p_preventivo_id
  RETURNING id, data INTO v_new_id, v_new_data;

  -- Copia righe attive, e per ciascuna i suoi componenti BoM.
  -- Una riga alla volta, con RETURNING (rev 2026-10-08): la
  -- corrispondenza vecchia -> nuova e' quella dell'INSERT, non un ordine
  -- di assegnazione degli id dato per scontato.
  FOR v_riga IN
      SELECT pr.*
        FROM vendite.preventivi_righe pr
       WHERE pr.preventivo_id = p_preventivo_id
         AND pr.attivo IS TRUE
         AND pr.quantita > 0
       ORDER BY pr.ordine, pr.id
  LOOP
    INSERT INTO vendite.preventivi_righe (
      preventivo_id, articolo_id, descrizione,
      quantita, prezzo_unitario, sconto_percentuale,
      iva_id, ordine, attivo,
      qta_operativa, uom_operativa_id, factor_to_base,
      data_consegna_richiesta_cliente,
      stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
      meta,
      user_insert, user_update
    )
    VALUES (
      v_new_id, v_riga.articolo_id, v_riga.descrizione,
      v_riga.quantita, v_riga.prezzo_unitario, v_riga.sconto_percentuale,
      v_riga.iva_id, v_riga.ordine, v_riga.attivo,
      v_riga.qta_operativa, v_riga.uom_operativa_id, v_riga.factor_to_base,
      -- rev 2026-10-13 (collaudo date di consegna, decisione di Tid): una
      -- richiesta ANTERIORE alla data della rev N+1 arriva NULL — la regola
      -- del guard di riga, script.fn_data_consegna_ammessa. La rev N, fuori
      -- bozza, conserva la sua; la rev N+1 e' DRAFT e l'operatore la riscrive.
      CASE WHEN script.fn_data_consegna_ammessa(v_riga.data_consegna_richiesta_cliente, v_new_data)
           THEN v_riga.data_consegna_richiesta_cliente END,
      v_riga.stato_approvazione_prezzo, v_riga.pratica_approvazione_prezzo_id,
      v_riga.meta,
      COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
    )
    RETURNING id INTO v_new_riga_id;

    -- I componenti si copiano TUTTI, attivi e no (D-1 di Tid, 2026-10-08).
    -- Il trigger trgfn_componenti_calcola_quantita (BEFORE INSERT)
    -- ricalcola quantita/qta_operativa da coeff_qta_snapshot: i valori
    -- copiati vengono sovrascritti correttamente.
    -- Un componente SPENTO in attesa si copia SENZA marca e senza pratica
    -- (D-3 di Tid, 2026-10-08, brief-db-righe-e-componenti-debiti-residui
    -- §3): la pratica e' della rev N, e sulla rev N+1 non si esiterebbe
    -- mai. Un attivo in attesa qui non arriva (guard di testa). Approvato e
    -- rifiutato si copiano 1:1. ⚠️ La richiesta nuova alla riaccensione e'
    -- dell'L3 dei componenti, che non esiste ancora: debito dichiarato.
    INSERT INTO vendite.preventivi_righe_componenti (
        riga_preventivo_id, articolo_componente_id, componente_id,
        coeff_qta_snapshot, quantita, prezzo_unitario, iva_id,
        origine_prezzo, prezzo_resolver_context,
        stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
        uom_operativa_id, factor_to_base, qta_operativa,
        ordine, attivo, meta,
        user_insert, user_update
    )
    SELECT
        v_new_riga_id,
        prc.articolo_componente_id, prc.componente_id,
        prc.coeff_qta_snapshot, prc.quantita, prc.prezzo_unitario, prc.iva_id,
        prc.origine_prezzo, prc.prezzo_resolver_context,
        CASE WHEN prc.attivo IS NOT TRUE AND prc.stato_approvazione_prezzo = 'PENDING'
             THEN NULL ELSE prc.stato_approvazione_prezzo END,
        CASE WHEN prc.attivo IS NOT TRUE AND prc.stato_approvazione_prezzo = 'PENDING'
             THEN NULL ELSE prc.pratica_approvazione_prezzo_id END,
        prc.uom_operativa_id, prc.factor_to_base, prc.qta_operativa,
        prc.ordine, prc.attivo, prc.meta,
        COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
      FROM vendite.preventivi_righe_componenti prc
     WHERE prc.riga_preventivo_id = v_riga.id
     ORDER BY prc.ordine, prc.id;
  END LOOP;

  -- Copia indirizzi
  INSERT INTO vendite.preventivi_indirizzi (
    preventivo_id, tipo_indirizzo_id, snapshot,
    origine_indirizzo_id, origine_soggetto_ruolo_id,
    user_insert, user_update
  )
  SELECT
    v_new_id, pi.tipo_indirizzo_id, pi.snapshot,
    pi.origine_indirizzo_id, pi.origine_soggetto_ruolo_id,
    COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
  FROM vendite.preventivi_indirizzi pi
  WHERE pi.preventivo_id = p_preventivo_id;

  -- Ritorna risultato
  RETURN QUERY
  SELECT v_new_id, v_numero, v_new_rev;
END
$function$

COMMENT ON FUNCTION vendite.fn_crea_revisione_preventivo(p_preventivo_id bigint, p_user text)
IS 'Crea revisione DRAFT da preventivo EMESSO o SCADUTO (gli stati di emissione e di scadenza del vocabolario, dal 2026-10-31): copia testata, righe attive, componenti BoM (tutti, anche gli spenti, rimappati per identita'') e indirizzi. Stato corrente e risoluzione DRAFT per codice_interno (immutabile). rev 2026-06-28: analisi-hardcoded-codice §3a #2. rev 2026-08-05 (20260805-25): codici rinominati con prefisso E_ — E_PREV_REVISIONE_STATO_NON_AMMESSO (850), E_PREV_REVISIONE_BOZZA_ESISTENTE (851), E_PREV_STATO_CORRENTE_NON_TROVATO (852); i vecchi nomi restano a catalogo ritirati con obsoleto_dal. rev 2026-09-14 (20260914-13): le righe copiate portano data_consegna_richiesta_cliente — la data chiesta dal cliente sopravvive alla revisione come sopravvive al push (20260913-20); firma e RETURNS TABLE di nuovo ancorati con %TYPE, SECURITY INVOKER esplicito. Brief: brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezione 6-quinquies. rev 2026-09-14 (20260914-14, D di Tid): le righe copiate portano anche le marche di approvazione prezzo — stato_approvazione_prezzo + pratica_approvazione_prezzo_id 1:1, come i componenti e come fn_crea_revisione_offerta (invariante: prezzo fuori policy sempre marcato; ciclo di vita della pratica su rev superata: dominio approvazioni, refactor-prezzi 4.7). Presidio: test-fn-crea-revisione-preventivo-riga-completa-v1. rev 2026-09-15 (20260915-41, D3 di Tid): la TESTATA copia emittente_fiscale_id dalla rev N — prima lo riempiva il default di sessione, e per un super admin su un altro emittente attivo la rev N+1 nasceva incoerente col BA (rifiutata dal guard). Brief: brief-db-emittente-di-default-un-bb-solo, sezione 7.1. rev 2026-09-24 (20260924-34, decisione di Tid): nessuna revisione con un prezzo IN ATTESA — guard sul primo motivo di script.fn_check_prezzi_in_attesa (righe e componenti attivi PENDING), lo stesso con cui la capability spegne «Crea revisione». Una riga in attesa ricopiata restava legata alla pratica della rev N e sulla rev N+1 non si esitava piu''''. Approvato e rifiutato continuano a ricopiarsi (azzerarli farebbe passare un prezzo rifiutato). Brief: brief-db-preventivi-congelamento-pricing §10. rev 2026-10-08 (20261008-35, brief-db-righe-e-componenti-le-altre-famiglie §2.1, D-1 di Tid): i componenti delle righe copiate si copiano TUTTI, anche gli opzionali spenti (la revisione e'' lo stesso documento: non portarli li cancellava, e nella rev N+1 non si potevano piu'' riaccendere), e si rimappano per identita'', una riga alla volta col suo RETURNING, invece che con un ROW_NUMBER sui due insiemi. Forma di fn_crea_revisione_offerta (20261005-19). rev 2026-10-08 (20261008-87, brief-db-righe-e-componenti-debiti-residui §3, D-3 di Tid): un componente SPENTO in PENDING si copia con stato_approvazione_prezzo e pratica_approvazione_prezzo_id a NULL. La pratica e'' della rev N e sulla rev N+1 non si esiterebbe mai; un attivo in attesa continua a fermare la revisione, approvato e rifiutato si copiano 1:1. La richiesta nuova alla riaccensione e'' dell''L3 dei componenti, che non esiste ancora (debito dichiarato). Gemella: fn_crea_revisione_offerta (20261008-88). ⭐ rev 2026-10-13 (20261013-68, collaudo date di consegna, decisione di Tid): una data_consegna_richiesta_cliente ANTERIORE alla data della rev N+1 (letta dal RETURNING della testata nuova) si copia NULL — script.fn_data_consegna_ammessa, la regola del guard di riga script.trgfn_doc_righe_guard_data_consegna, che altrimenti rifiuterebbe l''INSERT. Non si rifiuta la revisione (la rev N e'' fuori bozza e la data li'' non si correggerebbe) e non si porta alla data della revisione (sarebbe una richiesta mai fatta dal cliente): la rev N la conserva, la rev N+1 e'' DRAFT. Firma invariata. ⭐ rev 2026-10-31 (20261031-65, brief-db-scadenza-preventivi §8.1, E-3 (ii) di Tid): la revisione si crea dallo stato di emissione e da quello di scadenza, letti dalle colonne emissione e scadenza della riga del vocabolario (non piu'' il letterale ''EMESSO''): un preventivo SCADUTO si ripropone con una revisione, che nasce in bozza con la validita'' della rev N, da riscrivere. Lo stato della rev N non cambia. Gli altri stati restano esclusi (E_PREV_REVISIONE_STATO_NON_AMMESSO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
