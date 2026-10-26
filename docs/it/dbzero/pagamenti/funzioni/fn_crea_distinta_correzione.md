# ⚙️ Funzione `fn_crea_distinta_correzione`

```sql
CREATE FUNCTION fn_crea_distinta_correzione(p_contabile_id bigint, p_data_contabile date, p_motivo text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_crea_distinta_correzione(p_contabile_id bigint, p_data_contabile date DEFAULT script.fn_data_operativa(), p_motivo text DEFAULT NULL::text)
 RETURNS TABLE(contabile_id bigint, righe_create integer, righe_saltate integer, esito text)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_codice     pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_centro_id        pagamenti.vendite_contabili.centro_riscossione_id%TYPE;
    v_ente_id          pagamenti.vendite_contabili.ente_incasso_id%TYPE;
    v_emittente_sr     pagamenti.vendite_contabili.emittente_soggetto_ruolo_id%TYPE;
    v_codice_origine   pagamenti.vendite_contabili.codice%TYPE;
    v_gia_corretta     pagamenti.vendite_contabili.codice%TYPE;
    v_stato_bozza_id   pagamenti.vendite_contabili_stati.id%TYPE;
    v_stato_riga_id    pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_nuova_id         pagamenti.vendite_contabili.id%TYPE;
    v_da_correggere    integer;
    v_saltate          integer;
    v_create           integer;
BEGIN
    -- =========================================================
    -- Guard di parametro: un id nullo o non positivo non esce da
    -- nessuna interfaccia — lo produce solo un chiamante rotto.
    -- =========================================================
    IF p_contabile_id IS NULL OR p_contabile_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_crea_distinta_correzione',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_contabile_id',
                               'valore', p_contabile_id),
            NULL::uuid,
            'pagamenti.fn_crea_distinta_correzione',
            'p_contabile_id obbligatorio e maggiore di zero');
    END IF;

    -- =========================================================
    -- La distinta di partenza, bloccata: fra il controllo «e'
    -- gia' stata corretta?» e la scrittura del legame non deve
    -- passare nessun altro.
    -- ⚠️ Sotto RLS «non esiste» e «non la vedi» arrivano qui allo
    --    stesso modo, ed e' la scelta di tutto lo schema.
    -- ⭐ Rev 2026-09-15: si legge anche l'EMITTENTE — la correzione
    --    nasce dello stesso emittente, quindi sullo stesso registro.
    -- =========================================================
    SELECT st.codice_interno, c.centro_riscossione_id, c.ente_incasso_id,
           c.emittente_soggetto_ruolo_id, c.codice
      INTO v_stato_codice, v_centro_id, v_ente_id, v_emittente_sr, v_codice_origine
      FROM pagamenti.vendite_contabili c
      JOIN pagamenti.vendite_contabili_stati st ON st.id = c.stato_id
     WHERE c.id = p_contabile_id
       FOR UPDATE OF c;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_crea_distinta_correzione',
            'E_CONTABILE_NON_TROVATA',
            jsonb_build_object('contabile_id', p_contabile_id),
            NULL::uuid,
            p_contabile_id::text);
    END IF;

    -- =========================================================
    -- Si corregge cio' che e' stato REGISTRATO. Una bozza non si
    -- corregge: si modifica, ed e' un altro gesto.
    -- =========================================================
    IF v_stato_codice <> 'CHIUSA' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_crea_distinta_correzione',
            'E_CONTABILE_CORREZIONE_NON_REGISTRATA',
            jsonb_build_object('campo', 'stato_id',
                               'contabile_id', p_contabile_id,
                               'stato', v_stato_codice),
            NULL::uuid,
            v_codice_origine, v_stato_codice);
    END IF;

    -- =========================================================
    -- C-4: una correzione sola per documento. ⚠️ L'unico parziale
    -- e' la rete; qui si rifiuta con un codice che NOMINA la
    -- correzione che c'e' gia', perche' un 23505 non la dice.
    -- =========================================================
    SELECT c.codice INTO v_gia_corretta
      FROM pagamenti.vendite_contabili c
     WHERE c.contabile_corretta_id = p_contabile_id
     LIMIT 1;

    IF FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_crea_distinta_correzione',
            'E_CONTABILE_GIA_CORRETTA',
            jsonb_build_object('contabile_id', p_contabile_id,
                               'correzione', v_gia_corretta),
            NULL::uuid,
            v_codice_origine, v_gia_corretta);
    END IF;

    -- =========================================================
    -- Che cosa c'e' da correggere: SOLO le righe POSTATE, cioe'
    -- quelle che hanno prodotto un movimento. Le altre si contano
    -- e si dicono (C-2).
    -- =========================================================
    SELECT count(*) FILTER (WHERE rs.codice_interno = 'POSTATA'),
           count(*) FILTER (WHERE rs.codice_interno <> 'POSTATA')
      INTO v_da_correggere, v_saltate
      FROM pagamenti.vendite_contabili_righe r
      JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
     WHERE r.contabile_id = p_contabile_id
       AND r.attivo IS TRUE;

    IF COALESCE(v_da_correggere, 0) = 0 THEN
        -- ⭐ Non e' un errore: e' un esito. Il database dice il
        --    fatto, il frontend sceglie la frase.
        RETURN QUERY SELECT NULL::bigint, 0, COALESCE(v_saltate, 0),
                            'NULLA_DA_CORREGGERE'::text;
        RETURN;
    END IF;

    SELECT s.id INTO v_stato_bozza_id
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.codice_interno = 'BOZZA' AND s.attivo IS TRUE;

    SELECT s.id INTO v_stato_riga_id
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.codice_interno = 'DA_ABBINARE' AND s.attivo IS TRUE;

    IF v_stato_bozza_id IS NULL OR v_stato_riga_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_crea_distinta_correzione',
            'E_CONTABILE_STATO_NON_CONFIGURATO',
            jsonb_build_object('detail', 'stato BOZZA o DA_ABBINARE assente',
                               'contabile_id', p_contabile_id),
            NULL::uuid,
            'BOZZA / DA_ABBINARE');
    END IF;

    -- =========================================================
    -- La distinta NUOVA: stesso centro, stesso canale, STESSO
    -- EMITTENTE, in bozza.
    -- ⛔ `codice` non si passa: lo assegna il trigger sul registro
    --    DISTINTA dell'emittente (rev 2026-09-15, D5) — stesso
    --    emittente, stesso registro, il PROSSIMO del sezionale.
    -- ⛔ E non si usa il get-or-create: la sua chiave di riuso
    --    comprende l'operatore, e queste righe finirebbero nella
    --    distinta di lavoro di oggi.
    -- =========================================================
    INSERT INTO pagamenti.vendite_contabili (
        centro_riscossione_id, ente_incasso_id, emittente_soggetto_ruolo_id,
        data_contabile, data_registrazione, stato_id, origine,
        contabile_corretta_id, meta)
    VALUES (
        v_centro_id, v_ente_id, v_emittente_sr,
        p_data_contabile, (SELECT script.fn_data_operativa()), v_stato_bozza_id, 'MANUALE',
        p_contabile_id,
        jsonb_strip_nulls(jsonb_build_object(
            'correzione_di', v_codice_origine,
            'motivo_correzione', NULLIF(btrim(COALESCE(p_motivo, '')), ''))))
    RETURNING id INTO v_nuova_id;

    -- =========================================================
    -- Le righe: segno opposto, e i FATTI dell'originale.
    -- ⭐ Fattura e rata si portano dietro (C-1): l'abbinamento
    --    non si inventa, si rispecchia. Ma lo stato e'
    --    DA_ABBINARE, non ABBINATA: cosi' la riga non occupa
    --    spazio, il guard della capienza non la esamina, e il
    --    doppio tempo resta il gesto di una persona.
    -- ⚠️ `riferimento_ente` si conserva: e' lo stesso pagamento
    --    del mondo, e cambiarlo perderebbe l'unico appiglio per
    --    ritrovarlo nell'estratto conto.
    -- =========================================================
    INSERT INTO pagamenti.vendite_contabili_righe (
        contabile_id, riferimento_ente, data_pagamento, data_valuta,
        data_operazione, importo, fattura_id, billing_account_id,
        scadenza_id, stato_id, meta)
    SELECT v_nuova_id, r.riferimento_ente, r.data_pagamento, r.data_valuta,
           r.data_operazione, -r.importo, r.fattura_id, r.billing_account_id,
           r.scadenza_id, v_stato_riga_id,
           jsonb_build_object('corregge_riga_id', r.id)
      FROM pagamenti.vendite_contabili_righe r
      JOIN pagamenti.vendite_contabili_righe_stati rs ON rs.id = r.stato_id
     WHERE r.contabile_id = p_contabile_id
       AND r.attivo IS TRUE
       AND rs.codice_interno = 'POSTATA';

    GET DIAGNOSTICS v_create = ROW_COUNT;

    RETURN QUERY SELECT v_nuova_id, v_create, COALESCE(v_saltate, 0),
                        'CREATA'::text;
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_crea_distinta_correzione(p_contabile_id bigint, p_data_contabile date, p_motivo text)
IS 'La CORREZIONE GUIDATA (Q-7): da una distinta registrata apre una distinta NUOVA, in bozza, con le righe di segno opposto gia'' dentro. ⛔ Si chiama correzione e mai «storno»: STORNATA e'' stata ritirata dal catalogo il 2026-08-21. ⛔ E non e'' una sistemazione — quella decide che fare di un''eccedenza VERA, questa rimedia a una registrazione SBAGLIATA: confonderle significherebbe registrare come credito del cliente un errore di battitura. ⭐ E'' una MADRE e non un ciclo nel backend perche'' N righe dentro una testata nuova sono un atto solo: un ciclo che si rompe a meta'' lascia una distinta a meta'', cioe'' il documento che nessuno sa piu'' leggere. 🔴 Le righe nascono con fattura e rata GIA'' COMPILATE ma in stato DA_ABBINARE, e la ragione e'' una MISURA: una riga di segno opposto su una rata saldata dal movimento che si sta correggendo viene RIFIUTATA dal guard della capienza (con residuo zero non c''e'' spazio in nessuna direzione), quindi nascere gia'' ABBINATA pretenderebbe forzata = true — cioe'' forzare al posto dell''operatore, l''opposto del doppio tempo di D14-d. In DA_ABBINARE la riga non occupa spazio e il guard non la esamina: la correzione guida tutto tranne l''ultimo clic. ⭐ Le righe NON postate si saltano e l''esito le conta (`righe_saltate`), con lo stesso vocabolario di fn_posta_contabile: un secondo verbo che risponde come il primo si impara una volta sola. ⭐ «Niente da correggere» e'' un ESITO (`NULLA_DA_CORREGGERE`) e non un errore, come NULLA_DA_POSTARE. ⛔ NON usa fn_get_or_create_vendite_contabile: la sua chiave di riuso su MANUALE comprende giornata + canale + OPERATORE, quindi le righe di correzione finirebbero nella distinta di lavoro di oggi — questa e'' un documento proprio. ⛔ E non registra niente: nasce in BOZZA e la registra una persona, guardandola. Precompilare e'' un aiuto, non una decisione. ⭐ Rev 2026-09-15 (brief distinta-numerata-sul-registro, L8): la correzione COPIA l''emittente della distinta che corregge — stesso emittente, stesso registro DISTINTA, e il codice (assegnato dal trigger a10_gen_codice, non piu'' dal DEFAULT di colonna) e'' il PROSSIMO del sezionale; meta.correzione_di continua a portare il codice dell''originale, che per il pregresso e'' un VC_… ed e'' giusto cosi''. S6-4 del cantiere incassi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
