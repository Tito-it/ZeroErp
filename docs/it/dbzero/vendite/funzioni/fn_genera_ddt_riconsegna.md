{% include-markdown "it/dbzero/vendite/manual/fn_genera_ddt_riconsegna.md" %}
# ⚙️ Funzione `fn_genera_ddt_riconsegna`

```sql
CREATE FUNCTION fn_genera_ddt_riconsegna(p_reso_id bigint, p_righe jsonb, p_data date)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_ddt_riconsegna(p_reso_id bigint, p_righe jsonb DEFAULT NULL::jsonb, p_data date DEFAULT script.fn_data_operativa())
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-20 (20261020-56, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi DDT diventa DDT_VENDITA, il codice della
--   sorgente; firma e RETURNS ancorati.
DECLARE
    v_stato          config.stati_doc_reso.codice_interno%TYPE;
    v_stato_draft_id config.stati_doc_ddt.id%TYPE;
    v_sorg_ord_id    config.sorgenti.id%TYPE;
    v_ordine_uid     vendite.ordini.uid%TYPE;
    v_sorgente_tipo_id config.sorgenti.id%TYPE;
    v_sorgente_uid   vendite.ddt.sorgente_uid%TYPE;
    v_reso_uid       vendite.resi.uid%TYPE;
    v_new_ddt_id     vendite.ddt.id%TYPE;
    v_new_riga_id    vendite.ddt_righe.id%TYPE;
    v_qta_base       vendite.ddt_righe.quantita%TYPE;
    v_orig           RECORD;
    v_riga           RECORD;
    v_ord            RECORD;
    v_residuo_ric    numeric;
    v_qta_ric        numeric;
    v_qta_op         numeric;
    v_riga_nr        vendite.ddt_righe.riga_nr%TYPE := 0;
    v_n              integer := 0;
BEGIN
    -- 1) Guard input.
    IF p_reso_id IS NULL OR p_reso_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_riconsegna','E_VALIDAZIONE',
            jsonb_build_object('p_reso_id', p_reso_id),
            NULL::uuid, 'p_reso_id deve essere > 0');
    END IF;

    -- 2) Reso CONFERMATO + testata origine (DDT sorgente).
    --    rev 2026-08-28 (Fase A): si legge anche il blocco
    --    «relazione» — le colonne che dicono CON CHI e PERCHE'
    --    la merce si muove. Sono le stesse per il viaggio di
    --    andata e per la ri-consegna, perche' e' la stessa
    --    relazione commerciale eseguita una seconda volta.
    --
    -- ⚠️ I tre LEFT JOIN di catalogo NON sono decorativi: le
    --    colonne corrispondenti su vendite.ddt hanno un trigger
    --    dbops.trgfn_child_requires_active_parent. Ereditare un
    --    elemento RITIRATO DOPO farebbe FALLIRE la generazione
    --    della ri-consegna. Filtrando su `attivo` la colonna
    --    resta NULL — cioe' lo stato di prima di questa rev — e
    --    il documento si genera lo stesso. Un'eredita' che puo'
    --    impedire di generare e' un guasto nuovo, non una
    --    comodita'.
    --
    -- ⚠️ Il LEFT JOIN sulla testata puo' non trovare niente:
    --    resi.sorgente_uid e' NOT NULL ma nulla impone che il
    --    tipo sia DDT_VENDITA. In quel caso v_orig.* resta
    --    tutto NULL e NON si solleva: e' lo stato di oggi, e i
    --    guard dell'emissione fanno gia' il loro mestiere.
    SELECT sdr.codice_interno AS stato,
           r.uid AS reso_uid,
           d.id  AS ddt_origine_id,
           d.destinatario_soggetto_ruolo_id, d.billing_account_id,
           d.utility_id, d.valuta_id, d.emittente_fiscale_id,
           ct.id AS causale_trasporto_id,
           ab.id AS aspetto_bene_id,
           ma.id AS modalita_addebito_trasporto_id,
           d.mittente_soggetto_ruolo_id,
           d.vettore_soggetto_ruolo_id,
           d.fatturazione_immediata
      INTO v_orig
      FROM vendite.resi r
      JOIN config.stati_doc_reso sdr ON sdr.id = r.stato_doc_reso_id
      LEFT JOIN vendite.ddt d ON d.uid = r.sorgente_uid
      LEFT JOIN config.causali_trasporto ct
             ON ct.id = d.causale_trasporto_id AND ct.attivo IS TRUE
      LEFT JOIN config.aspetti_beni ab
             ON ab.id = d.aspetto_bene_id AND ab.attivo IS TRUE
      LEFT JOIN config.modalita_addebito_trasporto ma
             ON ma.id = d.modalita_addebito_trasporto_id AND ma.attivo IS TRUE
     WHERE r.id = p_reso_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_riconsegna','E_RESO_NOT_FOUND',
            jsonb_build_object('reso_id', p_reso_id),
            NULL::uuid, p_reso_id::text);
    END IF;

    IF v_orig.stato IS DISTINCT FROM 'CONFERMATO' THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_riconsegna','E_RESO_NON_CONFERMATO',
            jsonb_build_object('reso_id', p_reso_id, 'stato', v_orig.stato),
            NULL::uuid, p_reso_id::text, v_orig.stato);
    END IF;

    -- 3) Order-backing: ordine di provenienza (righe ri-consegna
    --    condividono lo stesso ordine, o nessuno se standalone).
    SELECT o.uid INTO v_ordine_uid
      FROM vendite.resi_righe rr
      JOIN vendite.ordini_righe orr ON orr.id = rr.ordine_riga_id
      JOIN vendite.ordini o         ON o.id = orr.ordine_id
     WHERE rr.reso_id = p_reso_id
       AND rr.ordine_riga_id IS NOT NULL
     LIMIT 1;

    -- rev 2026-08-28 (Fase D / R6): la sorgente si dichiara SEMPRE.
    --   Order-backed -> ORDINE_VENDITA + uid dell'ordine (invariato).
    --   Standalone   -> RESO_VENDITA  + uid del reso, che prima restava
    --   NULL: il documento dichiarava di non venire da nessuna parte,
    --   mentre viene da un reso, e su Transito/Passaggi quel DDT non
    --   aveva origine.
    --
    -- config.sorgenti NON si tocca, ed e' la domanda che il brief si era
    --   posto: key_selector governa la chiave POLIMORFA TESTUALE
    --   (commesse_sorgenti, pratiche_sorgenti, le vw_stato_sorgente_*),
    --   non questa colonna, che e' un uuid tipizzato. ORDINE_VENDITA e'
    --   gia' a key_selector='id' e qui ci mette da sempre ordini.uid; e
    --   vendite.fn_get_sorgente_documento_ref — quella che accende
    --   l'azione «apri documento sorgente» — prova la via uuid PRIMA di
    --   guardare il selettore, quindi risolve resi.uid e ne legge il
    --   numero leggibile.
    IF v_ordine_uid IS NOT NULL THEN
        SELECT id INTO v_sorg_ord_id FROM config.sorgenti
         WHERE codice_interno = 'ORDINE_VENDITA' AND attivo IS TRUE;
        v_sorgente_tipo_id := v_sorg_ord_id;
        v_sorgente_uid     := v_ordine_uid;
    ELSE
        SELECT id INTO v_sorgente_tipo_id FROM config.sorgenti
         WHERE codice_interno = 'RESO_VENDITA' AND attivo IS TRUE;
        -- Se il tipo non fosse a catalogo la colonna resta NULL, che e' il
        --   comportamento di prima: un documento senza origine dichiarata.
        --   NON si solleva — la ri-consegna e' merce che deve partire, e un
        --   catalogo incompleto non e' un buon motivo per non farla partire.
        v_sorgente_uid := CASE WHEN v_sorgente_tipo_id IS NOT NULL
                               THEN v_orig.reso_uid END;
    END IF;

    SELECT id INTO v_stato_draft_id FROM config.stati_doc_ddt
     WHERE codice_interno = 'DRAFT' AND attivo IS TRUE;

    -- 4) Nuovo DDT DRAFT. Denormalizzati dal DDT origine (normalize
    --    COALESCE li preserva). Order-backed -> sorgente ORDINE_VENDITA.
    --
    -- ⭐ rev 2026-08-28 (Fase A, R1+R5): si eredita il blocco
    --    «relazione». Il gemello fn_genera_ddt_da_ordine parte
    --    da un ORDINE — che un blocco trasporto non ce l'ha
    --    proprio — e ciononostante fa cascadere gli indirizzi;
    --    qui si parte da un DDT, cioe' dall'unico documento che
    --    quel blocco ce l'ha TUTTO. Non era un caso di nicchia:
    --    era la stessa regola scritta in un posto e non
    --    nell'altro.
    --
    -- ⛔ COSA NON SI COPIA, ED E' DELIBERATO. Qui sotto NON
    --    compaiono, e nessuno le rimetta senza aver letto il
    --    perche':
    --      num_colli, peso_lordo, peso_netto, volume
    --        -> sbagliati PER COSTRUZIONE, non «stantii»: la
    --           ri-consegna porta un SOTTOINSIEME delle righe e
    --           su quelle una FRAZIONE della quantita' (il
    --           residuo di fn_resi_riga_residuo_riconsegna). Un
    --           peso copiato e' il peso di un collo che non e'
    --           quello che parte.
    --      targa, autista
    --        -> il mezzo e la persona di un viaggio GIA'
    --           AVVENUTO. Sono una misura, non una scelta.
    --      data_ora_partenza, data_ora_consegna_prev
    --        -> date di un viaggio concluso, su un documento
    --           che nasce in DRAFT.
    --      tracking_code
    --        -> il peggiore: punterebbe il cliente al COLLO
    --           PRECEDENTE. Un codice di tracciamento copiato
    --           non e' un campo vuoto, e' un'informazione
    --           sbagliata data a un terzo.
    --    Il criterio, in una riga: EREDITA CIO' CHE E' UNA
    --    SCELTA, NON CIO' CHE E' UNA MISURA.
    --
    -- ⚠️ fatturazione_immediata e' NOT NULL DEFAULT false: il
    --    COALESCE serve per il caso in cui la testata d'origine
    --    non sia stata trovata. Non e' un cancello sulla doppia
    --    fatturazione — quella e' gia' impedita a monte da
    --    vw_partite_merce/fn_list_ddt_da_pushare — e' una
    --    corsia di instradamento, cioe' un patto commerciale
    --    come le altre colonne di questo blocco.
    INSERT INTO vendite.ddt (
        data, stato_doc_ddt_id, destinatario_soggetto_ruolo_id,
        sorgente_tipo_id, sorgente_uid, billing_account_id,
        utility_id, valuta_id, emittente_fiscale_id,
        causale_trasporto_id, aspetto_bene_id,
        modalita_addebito_trasporto_id,
        mittente_soggetto_ruolo_id, vettore_soggetto_ruolo_id,
        fatturazione_immediata)
    VALUES (
        COALESCE(p_data, (SELECT script.fn_data_operativa())), v_stato_draft_id,
        v_orig.destinatario_soggetto_ruolo_id,
        v_sorgente_tipo_id, v_sorgente_uid, v_orig.billing_account_id,
        v_orig.utility_id, v_orig.valuta_id, v_orig.emittente_fiscale_id,
        v_orig.causale_trasporto_id, v_orig.aspetto_bene_id,
        v_orig.modalita_addebito_trasporto_id,
        v_orig.mittente_soggetto_ruolo_id, v_orig.vettore_soggetto_ruolo_id,
        COALESCE(v_orig.fatturazione_immediata, false))
    RETURNING id INTO v_new_ddt_id;

    -- 4-bis) Cascata indirizzi (R2): copia 1:1 gli snapshot del
    --   DDT d'origine, filtrati sui tipi ammessi in ambito DDT.
    --   origine_* propagati; idempotente (uno-per-tipo).
    --   Modellata sul passo 4-bis di fn_genera_ddt_da_ordine.
    --
    -- ⭐ E' il pezzo che oggi BLOCCA l'emissione: senza
    --   indirizzi, trgfn_ddt_guard_indirizzi_obbligatori alza
    --   E_INDIRIZZO_DOC_OBBLIGATORIO su un documento che il
    --   database ha generato da se'.
    --
    -- ⚠️ Il filtro su config.tipi_indirizzi_allowed SEMBRA
    --   ridondante — le righe di ddt_indirizzi sono gia'
    --   passate da trgfn_tipi_indirizzi_only_allowed('DDT_VENDITA') — e
    --   non lo e': un tipo RITIRATO DOPO resterebbe sulle righe
    --   vecchie e farebbe fallire questo INSERT contro lo
    --   stesso trigger. E' cio' che rende la copia tollerante
    --   al ritiro di un tipo.
    --
    -- ⚠️ Se la testata d'origine non e' stata trovata,
    --   v_orig.ddt_origine_id e' NULL e questa INSERT non
    --   inserisce niente: nessun ramo condizionale da
    --   mantenere.
    INSERT INTO vendite.ddt_indirizzi (
        ddt_id, tipo_indirizzo_id, snapshot,
        origine_indirizzo_id, origine_soggetto_ruolo_id)
    SELECT v_new_ddt_id, di.tipo_indirizzo_id, di.snapshot,
           di.origine_indirizzo_id, di.origine_soggetto_ruolo_id
      FROM vendite.ddt_indirizzi di
      JOIN config.tipi_indirizzi_allowed a
        ON a.tipo_indirizzo_id = di.tipo_indirizzo_id
       AND a.ambito = 'DDT_VENDITA'
       AND a.attivo IS TRUE
     WHERE di.ddt_id = v_orig.ddt_origine_id
    ON CONFLICT (ddt_id, tipo_indirizzo_id) DO NOTHING;

    -- 5) Righe ri-consegna con copertura residua.
    --    rev 2026-07-26: il residuo viene dall'helper UNICO
    --    fn_resi_riga_residuo_riconsegna, che sottrae anche le
    --    RINUNCE. Cosi' la quota dichiarata definitiva non e' piu'
    --    ri-spedibile: la richiesta viene troncata dal LEAST, e se
    --    tutto e' rinunciato la riga si salta (CONTINUE) fino a
    --    E_RESO_NESSUNA_RICONSEGNA_PENDENTE.
    --
    -- ⭐ rev 2026-08-28 (Fase A, R4+R4-quater): si legge anche
    --    il VALORE dalla riga di DDT d'origine.
    --    vendite.resi_righe.ddt_riga_id e' NOT NULL, quindi la
    --    sorgente c'e' sempre — a un salto solo, ed e' la
    --    stessa relazione da cui gia' arrivano articolo,
    --    descrizione e UoM.
    -- ⚠️ NON e' resi_righe la sorgente del valore: quella
    --    tabella il prezzo NON ce l'ha (articolo, descrizione,
    --    quantita', UoM, tipo, motivo — nessuna colonna di
    --    valore). Il reso e' uno snapshot di QUANTITA', non di
    --    VALORE. Chi cercasse il prezzo li' concluderebbe che
    --    «non c'e'», mentre sta sulla riga a monte.
    -- ⚠️ src_iva_id passa da un LEFT JOIN su config.iva
    --    filtrato su `attivo`, per la stessa ragione del passo
    --    2: vendite.ddt_righe ha un require_active_parent su
    --    iva_id, e un'aliquota ritirata farebbe fallire
    --    l'INSERT invece di lasciare il campo da scegliere.
    -- ⭐ rev 2026-10-13 (20261013-43, A-6): la porta della riconsegna. Il
    --    guard delle regole sull'articolo (script.trgfn_righe_guard_articolo_ammesso)
    --    esenta le righe di questo reso: si restituisce cio' che e' uscito,
    --    anche se l'articolo nel frattempo e' diventato solo componente. Si
    --    chiude subito dopo il ciclo.
    PERFORM set_config('zeroerp.ddt_riconsegna', p_reso_id::text, true);
    FOR v_riga IN
        SELECT rr.id AS resi_riga_id, rr.articolo_id, rr.descrizione,
               rr.uom_operativa_id, COALESCE(rr.factor_to_base, 1) AS factor,
               rr.quantita AS qta_resa, rr.ordine_riga_id,
               dr_src.natura_vendita_id   AS src_natura_vendita_id,
               dr_src.prezzo_unitario     AS src_prezzo_unitario,
               dr_src.sconto_percentuale  AS src_sconto_percentuale,
               iva_src.id                 AS src_iva_id,
               vendite.fn_resi_riga_residuo_riconsegna(rr.id) AS residuo_ric,
               (SELECT (e->>'qta')::numeric
                  FROM jsonb_array_elements(COALESCE(p_righe,'[]'::jsonb)) e
                 WHERE (e->>'resi_riga_id')::bigint = rr.id
                 LIMIT 1) AS qta_richiesta
          FROM vendite.resi_righe rr
          JOIN config.tipi_reso tr ON tr.id = rr.tipo_reso_id
          JOIN vendite.ddt_righe dr_src ON dr_src.id = rr.ddt_riga_id
          LEFT JOIN config.iva iva_src
                 ON iva_src.id = dr_src.iva_id AND iva_src.attivo IS TRUE
         WHERE rr.reso_id = p_reso_id
           AND rr.attivo IS TRUE
           AND tr.riapre_residuo IS TRUE
           AND (p_righe IS NULL OR rr.id IN (
                 SELECT (e->>'resi_riga_id')::bigint
                   FROM jsonb_array_elements(p_righe) e))
         ORDER BY rr.riga_nr, rr.id
    LOOP
        v_residuo_ric := v_riga.residuo_ric;   -- base, al netto di ric+rin
        IF v_residuo_ric <= 0 THEN
            CONTINUE;  -- gia' ri-consegnata o interamente rinunciata
        END IF;

        IF p_righe IS NOT NULL THEN
            v_qta_ric := LEAST(COALESCE(v_riga.qta_richiesta, 0), v_residuo_ric);
        ELSE
            v_qta_ric := v_residuo_ric;
        END IF;
        IF v_qta_ric IS NULL OR v_qta_ric <= 0 THEN
            CONTINUE;
        END IF;

        v_qta_op := v_qta_ric / v_riga.factor;
        v_riga_nr := v_riga_nr + 1;

        -- Riga DDT (qta_operativa -> quantita via qta_from_operativa).
        --
        -- ⛔ IL VALORE SI SCRIVE SOLO NELLO STANDALONE, e la
        --    lettura sopra invece si fa sempre. Nell'ORDER-BACKED
        --    il prezzo si risale a ordini_righe_fulfillment al
        --    momento della lettura — e' il COALESCE di
        --    fn_list_ddt_da_pushare, lo stesso che fa il punto 3
        --    di script.fn_check_ddt_emittibile. Copiarlo qui
        --    creerebbe una SECONDA copia di un numero che ha gia'
        --    una sorgente, e le due divergono al primo cambio di
        --    prezzo sull'ordine.
        --    ⚠️ Nello STANDALONE quel secondo termine non esiste
        --    (il passo 5 non scrive nessun fulfillment), quindi
        --    senza questa copia la riga non ha NIENTE da cui
        --    ereditare e il documento non si emette.
        --
        -- ⚠️ iva_id: la copia e' una MISURA DI ATTESA, non la
        --    sede. Con il risolutore IVA la riga prendera'
        --    l'aliquota DA LI', come ogni altra riga — il
        --    documento a monte proietta, la fattura decide —
        --    e QUESTA COPIA VA TOLTA, o saranno due meccanismi
        --    per lo stesso campo. Finche' il risolutore non
        --    c'e', copiarla e' meglio del NULL: una riga con
        --    prezzo e senza aliquota entra in
        --    vw_ddt_righe_iva_base (che filtra il prezzo e NON
        --    l'aliquota) e produce una riga di riepilogo con
        --    imponibile pieno, codice IVA vuoto e imposta zero.
        INSERT INTO vendite.ddt_righe (
            ddt_id, riga_nr, articolo_id, descrizione,
            prezzo_unitario, sconto_percentuale, iva_id,
            qta_operativa, uom_operativa_id, factor_to_base,
            natura_vendita_id)
        VALUES (
            v_new_ddt_id, v_riga_nr, v_riga.articolo_id, v_riga.descrizione,
            CASE WHEN v_riga.ordine_riga_id IS NULL
                 THEN v_riga.src_prezzo_unitario END,
            CASE WHEN v_riga.ordine_riga_id IS NULL
                 THEN v_riga.src_sconto_percentuale END,
            CASE WHEN v_riga.ordine_riga_id IS NULL
                 THEN v_riga.src_iva_id END,
            v_qta_op, v_riga.uom_operativa_id, v_riga.factor,
            -- La natura della riga di bolla d'origine (A-4, A-6): si
            -- restituisce cio' che e' uscito.
            v_riga.src_natura_vendita_id)
        RETURNING id, quantita INTO v_new_riga_id, v_qta_base;

        -- Aggancio duro: ponte reso -> riga DDT (chiude la coda).
        INSERT INTO vendite.resi_righe_riconsegne (
            resi_riga_id, ddt_riga_id, qta)
        VALUES (v_riga.resi_riga_id, v_new_riga_id, v_qta_base);

        -- Order-backed: fulfillment -> chiude il residuo ordine
        --   (guard reso-aware). Standalone -> nessun fulfillment.
        IF v_riga.ordine_riga_id IS NOT NULL THEN
            INSERT INTO vendite.ordini_righe_fulfillment (
                ordine_riga_id, ddt_riga_id, qta_evasa)
            VALUES (v_riga.ordine_riga_id, v_new_riga_id, v_qta_base);
        END IF;

        v_n := v_n + 1;
    END LOOP;
    PERFORM set_config('zeroerp.ddt_riconsegna', '', true);

    -- 6) Nessuna ri-consegna pendente -> errore (rollback testata orfana).
    IF v_n = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_riconsegna','E_RESO_NESSUNA_RICONSEGNA_PENDENTE',
            jsonb_build_object('reso_id', p_reso_id, 'righe', p_righe),
            NULL::uuid, p_reso_id::text);
    END IF;

    -- 7) Ri-proiezione stato ordine per gli ordini coinvolti: il
    --    fulfillment appena creato ha chiuso (in tutto o in parte)
    --    il residuo riaperto dal reso -> allinea lo stato ordine.
    FOR v_ord IN
        SELECT DISTINCT orr.ordine_id
          FROM vendite.resi_righe rr
          JOIN vendite.ordini_righe orr ON orr.id = rr.ordine_riga_id
         WHERE rr.reso_id = p_reso_id
           AND rr.ordine_riga_id IS NOT NULL
    LOOP
        -- ⭐ rev 2026-10-11: la proiezione e' il building block
        --    vendite.fn_ordine_proietta_stato_evasione (brief-db-ddt-righe-evase-dall-ordine).
        PERFORM vendite.fn_ordine_proietta_stato_evasione(v_ord.ordine_id);
    END LOOP;

    RETURN v_new_ddt_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_ddt_riconsegna(p_reso_id bigint, p_righe jsonb, p_data date)
IS 'Madre ri-spedizione reso: nuovo DDT DRAFT (order-backed ORDINE_VENDITA o standalone), popola il ponte resi_righe_riconsegne (aggancio duro) e, se order-backed, il fulfillment che richiude il residuo. p_righe [{resi_riga_id, qta}] NULL=copertura residua. brief S5b. rev 2026-07-13. rev 2026-07-26: la copertura residua viene dall''helper unico vendite.fn_resi_riga_residuo_riconsegna, che sottrae ANCHE le quote rinunciate -> una quota dichiarata definitiva non e'' piu'' ri-spedibile. ⭐ rev 2026-08-28 (brief-db-ddt-riconsegna-eredita-testata, Fase A): il documento non nasce piu'' nudo. EREDITA dal DDT d''origine il blocco «relazione» — causale, aspetto, modalita'' addebito, mittente, vettore, fatturazione_immediata — fa cascadere gli indirizzi di ambito DDT come il gemello fn_genera_ddt_da_ordine, e nel solo ramo STANDALONE copia prezzo, sconto e aliquota dalla riga di DDT d''origine (resi_righe.ddt_riga_id, NOT NULL). ⛔ NON eredita il blocco «viaggio»: num_colli, pesi, volume, targa, autista, data_ora_partenza, data_ora_consegna_prev, tracking_code — sono misure di un viaggio gia'' avvenuto, e la ri-consegna porta un sottoinsieme delle righe e una frazione della quantita''; il tracking copiato punterebbe il cliente al collo precedente. Criterio: eredita cio'' che e'' una SCELTA, non cio'' che e'' una MISURA. ⛔ Nell''order-backed il valore NON si copia: lo risale il COALESCE di fn_list_ddt_da_pushare via ordini_righe_fulfillment, e una copia diventerebbe una seconda sorgente che diverge. ⚠️ Ogni eredita'' di catalogo passa da un LEFT JOIN filtrato su `attivo` (causali_trasporto, aspetti_beni, modalita_addebito_trasporto, iva): le colonne corrispondenti hanno un trigger require_active_parent, e ereditare un elemento ritirato dopo farebbe FALLIRE la generazione invece di lasciare il campo vuoto. ⚠️ La copia di iva_id e'' una misura di attesa: col risolutore IVA la riga prendera'' l''aliquota da li'' e questa copia va TOLTA. rev 2026-08-28 (Fase D / R6): la sorgente si dichiara SEMPRE — order-backed ORDINE_VENDITA + uid dell''ordine (invariato), STANDALONE RESO_VENDITA + uid del reso, che prima restava NULL e faceva nascere il documento senza origine dichiarata. config.sorgenti non si tocca: key_selector governa la chiave polimorfa TESTUALE, non questa colonna uuid tipizzata (ORDINE_VENDITA e'' gia'' a ''id'' e qui ci mette ordini.uid), e fn_get_sorgente_documento_ref prova la via uuid PRIMA del selettore, quindi risolve resi.uid e ne legge il numero. ⭐ rev 2026-10-11 (brief-db-ddt-righe-evase-dall-ordine §5.2): la proiezione dello stato dell''ordine e'' il building block vendite.fn_ordine_proietta_stato_evasione; la copia scritta a mano qui si ritira (regola del 2). Comportamento invariato. ⭐ rev 2026-10-13 (20261013-13, brief-db-articoli-ammessi-per-documento A-4, A-6): la riga riconsegnata porta la natura della riga di bolla d''origine (quella resa), che script.trgfn_righe_natura_vendita in modo CHIAMANTE accetta: si restituisce cio'' che e'' uscito, anche se l''articolo nel frattempo ha cambiato natura. Firma invariata. ⭐ rev 2026-10-13 (20261013-43, brief-db-articoli-ammessi-per-documento A-6): accende la porta zeroerp.ddt_riconsegna (id del reso) mentre scrive le righe, e la richiude subito: il guard delle regole sull''articolo esenta le righe il cui articolo e'' fra quelle del reso. Firma invariata. Rev 2026-10-20 (20261020-56, brief-db-grammatica-unica-documenti 2d, G-6): l''ambito degli indirizzi DDT diventa DDT_VENDITA, il codice della sorgente.';
```

---
{% include-markdown "signature-core.md" %}
