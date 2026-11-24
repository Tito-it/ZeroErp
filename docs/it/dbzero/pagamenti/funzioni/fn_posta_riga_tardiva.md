{% include-markdown "it/dbzero/pagamenti/manual/fn_posta_riga_tardiva.md" %}
# ⚙️ Funzione `fn_posta_riga_tardiva`

```sql
CREATE FUNCTION fn_posta_riga_tardiva(p_riga_id bigint, p_fattura_id bigint, p_billing_account_id bigint, p_scadenza_id bigint, p_forzata boolean, p_motivo_forzatura text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_posta_riga_tardiva(p_riga_id bigint, p_fattura_id bigint, p_billing_account_id bigint, p_scadenza_id bigint DEFAULT NULL::bigint, p_forzata boolean DEFAULT false, p_motivo_forzatura text DEFAULT NULL::text)
 RETURNS TABLE(movimento_id bigint, riga_id bigint, importo numeric, esito text)
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_contabile_id         pagamenti.vendite_contabili_righe.contabile_id%TYPE;
    v_attivo               pagamenti.vendite_contabili_righe.attivo%TYPE;
    v_importo              pagamenti.vendite_contabili_righe.importo%TYPE;
    v_data_pagamento       pagamenti.vendite_contabili_righe.data_pagamento%TYPE;
    v_data_valuta          pagamenti.vendite_contabili_righe.data_valuta%TYPE;
    v_stato_riga           pagamenti.vendite_contabili_righe_stati.codice_interno%TYPE;
    v_stato_riga_label     pagamenti.vendite_contabili_righe_stati.descrizione%TYPE;
    v_codice               pagamenti.vendite_contabili.codice%TYPE;
    v_centro_id            pagamenti.vendite_contabili.centro_riscossione_id%TYPE;
    v_data_contabile       pagamenti.vendite_contabili.data_contabile%TYPE;
    v_data_conferma        pagamenti.vendite_contabili.data_conferma%TYPE;
    v_stato_distinta       pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_stato_distinta_label pagamenti.vendite_contabili_stati.descrizione%TYPE;
    v_is_final             pagamenti.vendite_contabili_stati.is_final%TYPE;
    v_stato_abbinata_id    pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_stato_postata_id     pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_movimento_id         pagamenti.vendite_movimenti.id%TYPE;
    v_utente               config.user_emittenti_fiscali.auth_user_id%TYPE;
    v_emittente_distinta   anagrafiche.emittenti_fiscali.id%TYPE;
    v_emittente_fattura    anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Registrare IN RITARDO una riga contabile rimasta SOSPESA
    --   sotto una distinta gia' registrata: la si abbina e la si
    --   registra nello stesso gesto. Movimento scritto, riga a
    --   POSTATA, distinta che resta CHIUSA e non tocca la sua
    --   conferma. E' la strada del «resto» di D3-a, che dalla
    --   chiusura automatica in poi non ne aveva (brief §1).
    --
    -- ⭐ Passa da ABBINATA, cosi' girano tutti i guard
    --    dell'abbinamento normale; alla quarta mossa del guard
    --    sulla distinta finale si presenta con la GUC
    --    transazionale app.registrazione_tardiva_riga_id.
    -- ⛔ Nessun esito NULLA_DA_POSTARE: un rifiuto e' un rifiuto.
    --
    -- ⭐ SECURITY DEFINER: il permesso e' qui, in prima riga, e
    --    chiede la stessa azione dell'endpoint, registra_distinta
    --    (script.fn_guard_azione: E_PERMESSO_NEGATO). Il verbo gira
    --    come proprietario, fuori dalla row security: il perimetro
    --    lo rimette lui, una volta, all'ingresso (passo 2-bis).
    -- Brief: brief-db-validata-e-registrazione-tardiva §2.2, §4.1;
    --   brief-db-porte-aperte-dalla-sola-guc §11.
    -- =========================================================

    -- =========================================================
    -- 0) IL PERMESSO, prima di ogni altra cosa; e la porta spenta
    --    La GUC della porta la scrive solo il verbo: quella che il
    --    chiamante avesse acceso si spegne qui.
    -- =========================================================
    v_utente := script.fn_utente_di_sessione('pagamenti.fn_posta_riga_tardiva');
    PERFORM script.fn_guard_azione(v_utente, 'registra_distinta');

    PERFORM set_config('app.registrazione_tardiva_riga_id', '', true);

    -- =========================================================
    -- 1) GUARD DI PARAMETRO
    --    Un id nullo o non positivo non esce da nessuna
    --    interfaccia: lo produce solo un chiamante rotto, e per
    --    questo il codice e' TECNICO e non DATO_ERRATO. Il
    --    cliente a NULL NON e' un guard di qui: risponde il guard
    --    sui dati entrando in ABBINATA, col campo da accendere.
    -- =========================================================
    IF p_riga_id IS NULL OR p_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_riga_id', 'valore', p_riga_id),
            NULL::uuid,
            'pagamenti.fn_posta_riga_tardiva',
            'identificativo della riga contabile non valido');
    END IF;

    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_fattura_id', 'valore', p_fattura_id),
            NULL::uuid,
            'pagamenti.fn_posta_riga_tardiva',
            'la fattura a cui registrare la riga e'' obbligatoria');
    END IF;

    IF p_billing_account_id IS NOT NULL AND p_billing_account_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_billing_account_id', 'valore', p_billing_account_id),
            NULL::uuid,
            'pagamenti.fn_posta_riga_tardiva',
            'identificativo del cliente non valido');
    END IF;

    IF p_scadenza_id IS NOT NULL AND p_scadenza_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_scadenza_id', 'valore', p_scadenza_id),
            NULL::uuid,
            'pagamenti.fn_posta_riga_tardiva',
            'identificativo della rata non valido');
    END IF;

    -- =========================================================
    -- 2) LOCK DELLA RIGA, e la sua testata con lo stato
    --    ⚠️ FOR UPDATE OF r: si blocca la sola riga, non i
    --    cataloghi ne' la testata (che non si scrive). «Non
    --    trovata» e «non e' tua» devono restare indistinguibili:
    --    stesso codice e stessa frase del mirror del movimento
    --    (404, no-leak). Il verbo legge fuori dalla row security:
    --    «non e' tua» la dice il passo 2-bis, con lo stesso codice.
    -- =========================================================
    SELECT r.contabile_id, r.attivo, r.importo, r.data_pagamento, r.data_valuta,
           st.codice_interno, st.descrizione,
           c.codice, c.centro_riscossione_id, c.data_contabile, c.data_conferma,
           s.codice_interno, s.descrizione, s.is_final
      INTO v_contabile_id, v_attivo, v_importo, v_data_pagamento, v_data_valuta,
           v_stato_riga, v_stato_riga_label,
           v_codice, v_centro_id, v_data_contabile, v_data_conferma,
           v_stato_distinta, v_stato_distinta_label, v_is_final
      FROM pagamenti.vendite_contabili_righe r
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = r.stato_id
      JOIN pagamenti.vendite_contabili c              ON c.id  = r.contabile_id
      JOIN pagamenti.vendite_contabili_stati s        ON s.id  = c.stato_id
     WHERE r.id = p_riga_id
       FOR UPDATE OF r;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_RIGA_CONTABILE_NON_TROVATA',
            jsonb_build_object('contabile_riga_id', p_riga_id),
            NULL::uuid,
            p_riga_id::text);
    END IF;

    -- =========================================================
    -- 2-bis) IL PERIMETRO, una volta, sull'oggetto padre
    --    La riga segue la sua distinta: la distinta dev'essere
    --    nel perimetro di chi agisce. E' la regola che la row
    --    security della testata faceva valere quando il verbo
    --    girava come l'app, con la stessa risposta: fuori dal
    --    perimetro la riga «non c'e'». Poi la fattura su cui la si
    --    registra: il guard di scope della riga la giudica solo
    --    quando la colonna cambia, e il movimento non deve nascere
    --    su un'azienda d'altri. La rete sotto resta
    --    (script.trgfn_guard_emittente_scope su riga e movimento).
    -- =========================================================
    v_emittente_distinta := script.fn_resolve_emittente_fiscale_id('contabile', v_contabile_id);

    IF NOT COALESCE(script.fn_check_user_emittente_scope(v_utente, v_emittente_distinta), false) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_RIGA_CONTABILE_NON_TROVATA',
            jsonb_build_object('contabile_riga_id', p_riga_id, 'fuori_perimetro', true),
            NULL::uuid,
            p_riga_id::text);
    END IF;

    v_emittente_fattura := script.fn_resolve_emittente_fiscale_id('fattura', p_fattura_id);

    -- Una fattura che non esiste la rifiuta la sua FK, col suo messaggio.
    IF v_emittente_fattura IS NOT NULL
       AND NOT COALESCE(script.fn_check_user_emittente_scope(v_utente, v_emittente_fattura), false) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_SCOPE_EMITTENTE',
            jsonb_build_object(
                'detail', 'Utente non autorizzato per emittente fiscale',
                'auth_user_id', v_utente,
                'emittente_fiscale_id', v_emittente_fattura,
                'modo', 'fattura',
                'table', 'pagamenti.vendite_contabili_righe'),
            NULL::uuid,
            format('Utente %s non autorizzato per emittente fiscale %s su %s',
                   v_utente, v_emittente_fattura, 'pagamenti.vendite_contabili_righe'));
    END IF;

    -- =========================================================
    -- 3) GUARD DI STATO DELLA RIGA: attiva e SOSPESA
    --    Da SCARTATA si passa prima da «Riprendi» (-> SOSPESA, in
    --    matrice); da DA_ABBINARE non si arriva qui (D20-a: sotto
    --    una registrata non ce ne sono); da POSTATA il movimento
    --    c'e' gia'. Una riga eliminata non e' in nessun conto.
    -- =========================================================
    IF v_attivo IS NOT TRUE OR v_stato_riga IS DISTINCT FROM 'SOSPESA' THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_RIGA_CONTABILE_TARDIVA_STATO',
            jsonb_build_object(
                'contabile_riga_id', p_riga_id,
                'contabile_id',      v_contabile_id,
                'contabile_codice',  v_codice,
                'attivo',            v_attivo,
                'stato_riga',        v_stato_riga),
            NULL::uuid,
            p_riga_id::text,
            v_codice,
            -- La descrizione del catalogo com'e' («Riga scartata
            -- definitivamente»): entra fra parentesi nella frase.
            CASE WHEN v_attivo IS NOT TRUE THEN 'eliminata'
                 ELSE v_stato_riga_label END);
    END IF;

    -- =========================================================
    -- 4) GUARD DI STATO DELLA TESTATA: REGISTRATA
    --    = finale E con data_conferma. Sotto ANNULLATA niente si
    --    registra («non e' mai successa»); una CHIUSA senza
    --    conferma non ha registrato niente; sotto BOZZA /
    --    VALIDATA c'e' il giro normale, e la frase lo dice.
    -- =========================================================
    IF v_is_final IS NOT TRUE OR v_data_conferma IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA',
            jsonb_build_object(
                'contabile_riga_id', p_riga_id,
                'contabile_id',      v_contabile_id,
                'contabile_codice',  v_codice,
                'stato_distinta',    v_stato_distinta,
                'is_final',          v_is_final,
                'data_conferma',     v_data_conferma),
            NULL::uuid,
            v_codice,
            CASE
                WHEN v_stato_distinta = 'ANNULLATA'
                    THEN 'e'' annullata'
                WHEN v_is_final IS TRUE
                    THEN 'e'' chiusa senza essere mai stata registrata'
                ELSE 'e'' ancora ' || lower(v_stato_distinta_label)
                     || ': usa il giro normale, abbina la riga e registra la distinta'
            END);
    END IF;

    -- =========================================================
    -- 5) GLI STATI DI DESTINAZIONE, per codice_interno
    --    (la chiave immutabile, mai `codice`). Nessun ripiego:
    --    uno stato mancante e' una configurazione rotta.
    -- =========================================================
    SELECT s.id INTO v_stato_abbinata_id
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.codice_interno = 'ABBINATA' AND s.attivo IS TRUE
     LIMIT 1;

    IF v_stato_abbinata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_CONTABILE_STATO_NON_CONFIGURATO',
            jsonb_build_object('codice_interno', 'ABBINATA', 'catalogo', 'vendite_contabili_righe_stati'),
            NULL::uuid,
            'ABBINATA');
    END IF;

    SELECT s.id INTO v_stato_postata_id
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.codice_interno = 'POSTATA' AND s.attivo IS TRUE
     LIMIT 1;

    IF v_stato_postata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_riga_tardiva',
            'E_CONTABILE_STATO_NON_CONFIGURATO',
            jsonb_build_object('codice_interno', 'POSTATA', 'catalogo', 'vendite_contabili_righe_stati'),
            NULL::uuid,
            'POSTATA');
    END IF;

    -- ⚠️ Le tre scritture stanno in un blocco che svuota la porta
    --    anche in errore: set_config(..., true) la legherebbe alla
    --    transazione, non alla chiamata.
    BEGIN
        -- =========================================================
        -- 6) LA PORTA: ci si presenta alla quarta mossa
        --    set_config(..., true) = transazionale. Il guard sulla
        --    distinta finale legge la GUC e lascia passare SOLO
        --    questa riga, e solo se chi scrive e' il proprietario:
        --    qui, dentro il verbo SECURITY DEFINER.
        -- =========================================================
        PERFORM set_config('app.registrazione_tardiva_riga_id', p_riga_id::text, true);

        -- =========================================================
        -- 7) PRIMO STATEMENT — la riga si ABBINA
        --    Girano i guard dell'abbinamento normale: transizione
        --    (SOSPESA -> ABBINATA), dati (fattura e cliente), rata
        --    (coerenza rifiutata, capienza col doppio tempo: senza
        --    forzata -> E_RIGA_CONTABILE_CAPIENZA_SUPERATA), scope.
        --    ⚠️ `WHERE id = p_riga_id`, non un predicato: la riga e'
        --    quella, e basta.
        -- =========================================================
        UPDATE pagamenti.vendite_contabili_righe r
           SET stato_id           = v_stato_abbinata_id,
               fattura_id         = p_fattura_id,
               billing_account_id = p_billing_account_id,
               scadenza_id        = p_scadenza_id,
               forzata            = COALESCE(p_forzata, false),
               motivo_forzatura   = p_motivo_forzatura
         WHERE r.id = p_riga_id;

        -- =========================================================
        -- 8) SECONDO STATEMENT — il MOVIMENTO
        --    Come il passo 8 della madre del posting: fattura,
        --    cliente, distinta e rata NON si passano, li deriva dalla
        --    riga il trigger di mirror. E' registrata OGGI:
        --    data_registrazione e data_contabilizzazione =
        --    current_date; la testata tiene la data della PRIMA
        --    registrazione, il movimento la sua.
        --    ℹ️ Il doppio movimento e' impossibile per costruzione
        --    (uq_vendite_movimenti_contabile_riga).
        -- =========================================================
        INSERT INTO pagamenti.vendite_movimenti (
            contabile_riga_id, data_effettiva, data_registrazione,
            data_contabile, data_valuta, data_contabilizzazione,
            importo, centro_riscossione_id, meta)
        VALUES (
            p_riga_id,
            COALESCE(v_data_pagamento, v_data_contabile),
            (SELECT script.fn_data_operativa()),
            v_data_contabile,
            v_data_valuta,
            (SELECT script.fn_data_operativa()),
            v_importo,
            v_centro_id,
            jsonb_build_object('origine', 'POSTING_TARDIVO', 'contabile_codice', v_codice))
        RETURNING id INTO v_movimento_id;

        -- =========================================================
        -- 9) TERZO STATEMENT — la riga a POSTATA
        --    🔴 Statement separato, non una CTE: con la RLS padre e
        --    figlio nella stessa snapshot non si vedono. Scatta
        --    marca_fondo_eseguito se e' una riga di fondo, come nel
        --    posting. La distinta NON si tocca: resta CHIUSA con la
        --    sua data_conferma.
        -- =========================================================
        UPDATE pagamenti.vendite_contabili_righe r
           SET stato_id = v_stato_postata_id
         WHERE r.id = p_riga_id;

        -- ⚠️ La porta si RICHIUDE qui, non al COMMIT: dopo il
        --    ritorno nessun'altra scrittura della stessa
        --    transazione deve trovarla aperta.
        PERFORM set_config('app.registrazione_tardiva_riga_id', '', true);
    EXCEPTION
        WHEN OTHERS THEN
            PERFORM set_config('app.registrazione_tardiva_riga_id', '', true);
            RAISE;
    END;

    RETURN QUERY SELECT v_movimento_id, p_riga_id, v_importo, 'POSTATA'::text;
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_posta_riga_tardiva(p_riga_id bigint, p_fattura_id bigint, p_billing_account_id bigint, p_scadenza_id bigint, p_forzata boolean, p_motivo_forzatura text)
IS 'La registrazione tardiva di una riga: una riga SOSPESA sotto una distinta registrata (finale e con data_conferma) si abbina (fattura, cliente, rata facoltativa, forzatura a due tempi) e si registra nello stesso gesto: movimento scritto, riga a POSTATA, distinta che resta CHIUSA senza toccare data_conferma e user_conferma. La quadratura del giorno non cambia: la riga era già contata. SECURITY DEFINER: in prima riga chiede l''azione registra_distinta all''utente di sessione (script.fn_guard_azione: E_PERMESSO_NEGATO), la stessa dell''endpoint. Gira fuori dalla row security, e il perimetro lo rimette all''ingresso: la distinta della riga dev''essere nel perimetro di chi agisce, altrimenti la riga non c''è (E_RIGA_CONTABILE_NON_TROVATA, la stessa risposta di una riga inesistente); la fattura su cui la si registra pure (E_SCOPE_EMITTENTE). Passa da ABBINATA, così girano tutti i guard dell''abbinamento: transizione, dati, rata (coerenza, capienza col doppio tempo: senza forzata E_RIGA_CONTABILE_CAPIENZA_SUPERATA), scope. Alla quarta mossa del guard sulla distinta finale (pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale) si presenta con la GUC transazionale app.registrazione_tardiva_riga_id uguale all''id della riga, che apre solo per quella riga e solo al proprietario; il verbo la spegne all''ingresso e la svuota prima di uscire, anche in errore. Poi il movimento (origine POSTING_TARDIVO, data_registrazione e data_contabilizzazione al giorno operativo; fattura, cliente, distinta e rata dal mirror della riga), poi POSTATA: tre istruzioni separate, ognuna sulla riga per id. Nessun esito NULLA_DA_POSTARE: una riga che non si può registrare è un rifiuto. E_RIGA_CONTABILE_TARDIVA_STATO: non attiva o non SOSPESA (da SCARTATA si passa prima da «Riprendi»). E_RIGA_CONTABILE_TARDIVA_DISTINTA_NON_REGISTRATA: annullata, chiusa senza registrazione, o ancora aperta («usa il giro normale»). E_PAGAMENTI_CHIAMATA_NON_VALIDA: riga o fattura mancanti, id non positivi; il cliente mancante lo rifiuta il guard sui dati col suo campo; una forzatura senza motivo è ammessa. La chiama l''endpoint di registrazione della riga, mai un lavoro automatico: è la decisione di chi ha identificato il denaro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
