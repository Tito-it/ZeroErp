{% include-markdown "it/dbzero/vendite/manual/fn_genera_ddt_da_ordine.md" %}
# ⚙️ Funzione `fn_genera_ddt_da_ordine`

```sql
CREATE FUNCTION fn_genera_ddt_da_ordine(p_ordine_id bigint, p_righe jsonb, p_data date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_genera_ddt_da_ordine(p_ordine_id bigint, p_righe jsonb DEFAULT NULL::jsonb, p_data date DEFAULT script.fn_data_operativa())
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
-- rev 2026-11-03 (20261103-36, brief-db-addebito-trasporto-ordine §8.2, K-4/K-5):
--   la riga-onere dell'ordine (script.fn_natura_e_merce = false sulla
--   natura congelata) passa INTERA nella prima bolla, anche se p_righe non
--   la nomina; il legame e' il fulfillment, con la quantita' intera (la
--   regola «intero» la tiene il guard del legame). La seconda bolla la
--   salta (residuo 0). v_n_evase conta la sola merce: una bolla che
--   porterebbe solo oneri e' E_DDT_NIENTE_DA_EVADERE.
-- rev 2026-10-24 (20261024-15, brief-modello-documento-vendita N-1/P-2):
--   lo stato iniziale non si scrive piu' qui: lo mette il trigger della
--   nascita (script.trgfn_doc_stato_iniziale), letto dal vocabolario.
-- rev 2026-10-20 (20261020-55, brief-db-grammatica-unica-documenti, 2d G-6):
--   l'ambito degli indirizzi DDT diventa DDT_VENDITA, il codice della
--   sorgente; firma e RETURNS ancorati.
DECLARE
    v_stato_ord       config.stati_doc_ordini.codice_interno%TYPE;
    v_dest_ruolo_id   vendite.ordini.soggetto_ruolo_id%TYPE;
    v_ddt_id          vendite.ddt.id%TYPE;
    v_new_riga_id     vendite.ddt_righe.id%TYPE;
    v_qta_base        vendite.ddt_righe.quantita%TYPE;
    v_riga            RECORD;
    v_residuo_base    numeric;
    v_qta_op          numeric;
    v_riga_nr         vendite.ddt_righe.riga_nr%TYPE := 0;
    -- ⚠️ `integer` esplicito: un conteggio. Conta le righe di MERCE copiate
    --    (rev 2026-11-03): gli oneri viaggiano con la merce, non la sostituiscono.
    v_n_evase         integer := 0;
    -- Il BERSAGLIO dei due rifiuti di evasione. ⚠️ `jsonb` esplicito: e' un
    -- frammento del context, non il valore di una colonna.
    v_bersagli        jsonb;
    v_prov_tipo_id    vendite.ddt_righe.sorgente_tipo_id%TYPE;
    v_prov_id         vendite.ddt_righe.sorgente_id%TYPE;
    v_prov_uid        vendite.ddt_righe.sorgente_uid%TYPE;
BEGIN
    -- 1) Guard input.
    IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_da_ordine','E_VALIDAZIONE',
            jsonb_build_object('p_ordine_id', p_ordine_id),
            NULL::uuid, 'p_ordine_id deve essere > 0');
    END IF;

    -- 2) Ordine esiste + stato evadibile.
    SELECT o.soggetto_ruolo_id, sdo.codice_interno
      INTO v_dest_ruolo_id, v_stato_ord
      FROM vendite.ordini o
      JOIN config.stati_doc_ordini sdo ON sdo.id = o.stato_doc_ordine_id
     WHERE o.id = p_ordine_id;

    IF NOT FOUND THEN
        -- ⛔ QUI NESSUN BERSAGLIO, ed e' una scelta. L'ordine non esiste —
        --    oppure la RLS lo nasconde, che per chi opera e' la stessa cosa —
        --    quindi non c'e' nessun posto dove mandarlo. Un pulsante che apre
        --    il vuoto e' peggio di nessun pulsante (§4.3 del brief).
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_da_ordine','E_DDT_ORDINE_NOT_FOUND',
            jsonb_build_object('ordine_id', p_ordine_id),
            NULL::uuid, p_ordine_id::text);
    END IF;

    -- ⭐ IL BERSAGLIO, composto UNA VOLTA e riusato dai due rifiuti sotto.
    --    Qui l'ordine e' certo: la SELECT sopra l'ha letto, quindi esiste ED
    --    e' visibile a chi opera. Nessuna query in piu' — l'id ce l'abbiamo
    --    gia' — e nessun ramo condizionale da mantenere.
    --
    -- ⚠️ Perche' serve, visto che l'operatore l'ordine lo sta gia' guardando:
    --    l'evasione si lancia anche in massa, su piu' ordini in una passata, e
    --    li' la frase dice QUALE ordine ha rifiutato ma non ci porta. E' lo
    --    stesso caso del messaggio 937 dentro un giro di lotto.
    v_bersagli := jsonb_build_array(
        jsonb_build_object('tipo', 'ORDINE_VENDITA', 'id', p_ordine_id::text));

    IF v_stato_ord NOT IN ('CONFERMATO','PARZIALMENTE_EVASO') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_da_ordine','E_DDT_ORDINE_STATO_NON_EVADIBILE',
            jsonb_build_object('ordine_id', p_ordine_id, 'stato', v_stato_ord,
                               'bersaglio', v_bersagli),
            NULL::uuid, p_ordine_id::text, v_stato_ord);
    END IF;

    -- 3) La provenienza della bolla e delle sue righe: il tipo ORDINE_VENDITA e la
    --    chiave dell'ordine per il key_selector del tipo (script.fn_sorgente_provenienza).
    --    Una volta sola; la riga ci aggiunge sorgente_riga.
    SELECT p.sorgente_tipo_id, p.sorgente_id, p.sorgente_uid
      INTO v_prov_tipo_id, v_prov_id, v_prov_uid
      FROM script.fn_sorgente_provenienza('ORDINE_VENDITA', p_ordine_id::text) p;

    -- 4) Testata DDT DRAFT. Billing/utility/valuta via trgfn_ddt_normalize.
    --    Lo stato non si scrive: DRAFT lo mette trg_ddt_a05_stato_iniziale_ins.
    INSERT INTO vendite.ddt (
        data, destinatario_soggetto_ruolo_id,
        sorgente_tipo_id, sorgente_id, sorgente_uid)
    VALUES (
        COALESCE(p_data, (SELECT script.fn_data_operativa())), v_dest_ruolo_id,
        v_prov_tipo_id, v_prov_id, v_prov_uid)
    RETURNING id INTO v_ddt_id;

    -- 4-bis) Cascata indirizzi (D-1): copia 1:1 gli snapshot dell'ordine
    --   filtrati sui tipi ammessi in ambito DDT (di fatto solo CON).
    --   origine_* propagati; idempotente (uno-per-tipo).
    INSERT INTO vendite.ddt_indirizzi (
        ddt_id, tipo_indirizzo_id, snapshot,
        origine_indirizzo_id, origine_soggetto_ruolo_id)
    SELECT v_ddt_id, oi.tipo_indirizzo_id, oi.snapshot,
           oi.origine_indirizzo_id, oi.origine_soggetto_ruolo_id
      FROM vendite.ordini_indirizzi oi
      JOIN config.tipi_indirizzi_allowed a
        ON a.tipo_indirizzo_id = oi.tipo_indirizzo_id
       AND a.ambito = 'DDT_VENDITA'
       AND a.attivo IS TRUE
     WHERE oi.ordine_id = p_ordine_id
    ON CONFLICT (ddt_id, tipo_indirizzo_id) DO NOTHING;

    -- 5) Righe: copia snapshot A-2 + componenti + fulfillment.
    FOR v_riga IN
        SELECT orr.id AS ordine_riga_id, orr.articolo_id, orr.descrizione,
               orr.prezzo_unitario, orr.sconto_percentuale, orr.iva_id,
               orr.uom_operativa_id, orr.factor_to_base,
               orr.natura_vendita_id,
               -- rev 2026-11-03: la riga e' un onere (natura congelata non merce:
               -- su ordine e bolla l'ammissione lascia entrare solo merce e
               -- articoli-onere). IS FALSE: una natura sconosciuta resta merce.
               script.fn_natura_e_merce(orr.natura_vendita_id) IS FALSE AS e_onere,
               orr.qta_operativa AS qta_op_ord,
               orr.quantita AS qta_ord_base,
               COALESCE(orr.factor_to_base, 1) AS factor,
               COALESCE((
                   SELECT SUM(f.qta_evasa)
                     FROM vendite.ordini_righe_fulfillment f
                    WHERE f.ordine_riga_id = orr.id
               ), 0) AS qta_evasa_prec,
               a.is_composito,
               (SELECT (elem->>'qta_da_evadere')::numeric
                  FROM jsonb_array_elements(COALESCE(p_righe,'[]'::jsonb)) elem
                 WHERE (elem->>'ordine_riga_id')::bigint = orr.id
                 LIMIT 1) AS qta_richiesta_op
          FROM vendite.ordini_righe orr
          JOIN catalogo.articoli a ON a.id = orr.articolo_id
         WHERE orr.ordine_id = p_ordine_id
           AND orr.attivo IS TRUE
           AND (p_righe IS NULL OR orr.id IN (
                 SELECT (elem->>'ordine_riga_id')::bigint
                   FROM jsonb_array_elements(p_righe) elem)
                -- rev 2026-11-03 (K-5): l'onere entra anche se non scelto. Se
                -- e' gia' passato in una bolla il residuo e' 0 e il ciclo lo salta.
                OR script.fn_natura_e_merce(orr.natura_vendita_id) IS FALSE)
         ORDER BY orr.riga_nr, orr.id
    LOOP
        v_residuo_base := v_riga.qta_ord_base - v_riga.qta_evasa_prec;
        IF v_residuo_base <= 0 THEN
            CONTINUE;  -- riga gia' evasa
        END IF;

        -- Qta da evadere in OPERATIVA: esplicito -> richiesto,
        -- implicito -> tutto il residuo (residuo_base / factor).
        -- ⭐ rev 2026-11-03: l'onere passa INTERO, qualunque cosa dica
        --    p_righe (K-5, K-6: la sua quantita' non si sceglie). La quantita'
        --    operativa e' quella dell'ordine: la stessa derivazione ridà la
        --    stessa quantita' base, che il guard del legame pretende intera.
        IF v_riga.e_onere THEN
            v_qta_op := COALESCE(v_riga.qta_op_ord, v_residuo_base / v_riga.factor);
        ELSIF p_righe IS NOT NULL THEN
            v_qta_op := COALESCE(v_riga.qta_richiesta_op, 0);
        ELSE
            v_qta_op := v_residuo_base / v_riga.factor;
        END IF;

        IF v_qta_op IS NULL OR v_qta_op <= 0 THEN
            CONTINUE;
        END IF;
        -- NB: over-shipping (v_qta_op*factor > residuo_base) e'
        -- bloccato dal guard fulfillment (E_QTA_SUPERA_RESIDUO, C2).

        v_riga_nr := v_riga_nr + 1;

        -- Riga DDT (snapshot A-2). Padre composito: prezzo 0
        -- placeholder (ricalcolato dai componenti). qta_operativa
        -- valorizzata: il trigger qta_from_operativa deriva quantita.
        INSERT INTO vendite.ddt_righe (
            ddt_id, riga_nr, articolo_id, descrizione,
            prezzo_unitario, sconto_percentuale, iva_id,
            qta_operativa, uom_operativa_id, factor_to_base,
            natura_vendita_id,
            sorgente_tipo_id, sorgente_id, sorgente_uid, sorgente_riga)
        VALUES (
            v_ddt_id, v_riga_nr, v_riga.articolo_id, v_riga.descrizione,
            CASE WHEN v_riga.is_composito THEN 0 ELSE v_riga.prezzo_unitario END,
            v_riga.sconto_percentuale, v_riga.iva_id,
            v_qta_op, v_riga.uom_operativa_id, v_riga.factor_to_base,
            -- La natura con cui l'ordine ha venduto la riga (A-4).
            v_riga.natura_vendita_id,
            -- La provenienza: l'ordine e la riga che si evade. La quantita'
            -- evasa e' del fulfillment, qui sotto.
            v_prov_tipo_id, v_prov_id, v_prov_uid, v_riga.ordine_riga_id)
        RETURNING id, quantita INTO v_new_riga_id, v_qta_base;

        -- Componenti CASO A (A-2): copia 1:1 (no resolver). La qta
        -- del componente la scala m50_calcola_quantita (coeff*qta_padre);
        -- il prezzo padre lo ricalcola z90_ricalcola_padre.
        IF v_riga.is_composito THEN
            INSERT INTO vendite.ddt_righe_componenti (
                riga_ddt_id, articolo_componente_id, componente_id,
                coeff_qta_snapshot, uom_operativa_id, factor_to_base,
                qta_operativa, prezzo_unitario, iva_id, origine_prezzo,
                prezzo_resolver_context, stato_approvazione_prezzo,
                pratica_approvazione_prezzo_id, meta, ordine)
            SELECT
                v_new_riga_id, orc.articolo_componente_id, orc.componente_id,
                orc.coeff_qta_snapshot, orc.uom_operativa_id, orc.factor_to_base,
                orc.qta_operativa, orc.prezzo_unitario, orc.iva_id, orc.origine_prezzo,
                orc.prezzo_resolver_context, orc.stato_approvazione_prezzo,
                orc.pratica_approvazione_prezzo_id, orc.meta, orc.ordine
              FROM vendite.ordini_righe_componenti orc
             WHERE orc.riga_ordine_id = v_riga.ordine_riga_id
               AND orc.attivo;
        END IF;

        -- Fulfillment: collega DDT<->ordine. Prima questa riga diceva
        -- "e alimenta mv_ddt_ordini": quella vista materializzata e' stata
        -- ritirata il 2026-08-05 (nessuno la leggeva, nessuno la
        -- aggiornava). Il legame ordine<->DDT si ricava da qui e da
        -- dalla provenienza della testata (ddt.sorgente_*).
        -- qta_evasa = quantita base della riga DDT (derivata dal trigger).
        -- Il guard fulfillment valida articolo/uom/residuo (C2).
        -- rev 2026-11-03: anche per l'onere — e' il suo «gia' passato»
        --   (§8.2): il residuo 0 lo toglie dalla bolla successiva, e la
        --   diagnosi del push ne legge il trigger dell'ordine.
        INSERT INTO vendite.ordini_righe_fulfillment (
            ordine_riga_id, ddt_riga_id, qta_evasa)
        VALUES (
            v_riga.ordine_riga_id, v_new_riga_id, v_qta_base);

        -- rev 2026-11-03: conta la sola merce (l'onere non si evade).
        IF NOT v_riga.e_onere THEN
            v_n_evase := v_n_evase + 1;
        END IF;
    END LOOP;

    -- 6) Idempotenza/completezza: se nulla da evadere -> errore
    --    (rollback della testata orfana, atomico).
    --    rev 2026-11-03: «nulla» = nessuna riga di MERCE. Una bolla di soli
    --    oneri non si genera (K-2): un addebito senza merce si fa in commessa.
    IF v_n_evase = 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite','fn_genera_ddt_da_ordine','E_DDT_NIENTE_DA_EVADERE',
            jsonb_build_object('ordine_id', p_ordine_id, 'righe', p_righe,
                               'bersaglio', v_bersagli),
            NULL::uuid, p_ordine_id::text);
    END IF;

    -- 7) Proiezione stato ordine (C5), atomica. residuo 0 -> EVASO,
    --    altrimenti PARZIALMENTE_EVASO. La transizione passa per
    --    trgfn_ordini_guard_transizione (matrice).
    -- ⭐ rev 2026-10-11: la proiezione e' il building block
    --    vendite.fn_ordine_proietta_stato_evasione (brief-db-ddt-righe-evase-
    --    dall-ordine §5.2), condiviso con i verbi del reso, la correzione della
    --    quantita' evasa e il ritiro del legame in bozza. Qui il fulfillment
    --    c'e' sempre (step 6), quindi gli esiti restano i due di prima.
    PERFORM vendite.fn_ordine_proietta_stato_evasione(p_ordine_id);

    RETURN v_ddt_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_genera_ddt_da_ordine(p_ordine_id bigint, p_righe jsonb, p_data date)
IS 'Madre dell''evasione ordine -> bolla DRAFT. Piu'' bolle per lo stesso ordine; p_righe [{ordine_riga_id, qta_da_evadere (operativa)}], NULL = tutto il residuo. La provenienza si legge una volta con script.fn_sorgente_provenienza (ORDINE_VENDITA con la chiave dell''ordine): la testata dichiara l''ordine, ogni riga lo dichiara con in sorgente_riga la riga d''ordine. Per ogni riga copia lo snapshot di prezzi e componenti e la natura che l''ordine ha venduto, e scrive il fulfillment (vendite.ordini_righe_fulfillment, la quantita'' evasa; l''eccesso lo ferma il guard). La riga-onere (script.fn_natura_e_merce = false sulla natura congelata) passa intera nella prima bolla, anche se p_righe non la nomina; dopo, il suo residuo e'' 0. Rifiuti: E_DDT_ORDINE_NOT_FOUND, senza bersaglio (l''ordine non c''e'' o non e'' visibile); E_DDT_ORDINE_STATO_NON_EVADIBILE ed E_DDT_NIENTE_DA_EVADERE, col bersaglio sull''ordine; una bolla che porterebbe solo oneri e'' E_DDT_NIENTE_DA_EVADERE. Lo stato dell''ordine lo proietta vendite.fn_ordine_proietta_stato_evasione. Indirizzi di ambito DDT_VENDITA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
