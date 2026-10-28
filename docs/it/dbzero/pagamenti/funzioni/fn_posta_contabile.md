{% include-markdown "it/dbzero/pagamenti/manual/fn_posta_contabile.md" %}
# ⚙️ Funzione `fn_posta_contabile`

```sql
CREATE FUNCTION fn_posta_contabile(p_contabile_id bigint, p_righe_attese integer, p_totale_atteso numeric)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.fn_posta_contabile(p_contabile_id bigint, p_righe_attese integer DEFAULT NULL::integer, p_totale_atteso numeric DEFAULT NULL::numeric)
 RETURNS TABLE(movimenti_creati integer, righe_postate integer, righe_saltate integer, totale_postato numeric, esito text)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_stato_id           pagamenti.vendite_contabili_stati.id%TYPE;
    v_stato              pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_stato_label        pagamenti.vendite_contabili_stati.descrizione%TYPE;
    v_registrabile       pagamenti.vendite_contabili_stati.is_registrabile%TYPE;
    v_codice             pagamenti.vendite_contabili.codice%TYPE;
    v_centro_id          pagamenti.centri_riscossione.id%TYPE;
    v_data_contabile     pagamenti.vendite_contabili.data_contabile%TYPE;
    v_data_registrazione pagamenti.vendite_contabili.data_registrazione%TYPE;
    v_importo_dichiarato pagamenti.vendite_contabili.importo_dichiarato%TYPE;
    v_stato_postata_id   pagamenti.vendite_contabili_righe_stati.id%TYPE;
    v_stato_chiusa_id    pagamenti.vendite_contabili_stati.id%TYPE;
    v_somma_righe        pagamenti.vendite_contabili_righe.importo%TYPE;
    v_righe_pronte       integer;
    v_totale_pronte      pagamenti.vendite_contabili_righe.importo%TYPE;
    v_senza_abbinamento  integer;
    -- ⚠️ `colonna%TYPE[]` non esiste in PostgreSQL: qui il tipo
    --    resta esplicito. Porta id di vendite_contabili_righe.
    v_righe_ids          bigint[];
    v_movimenti          integer := 0;
    v_postate            integer := 0;
    v_saltate            integer := 0;
    v_totale_postato     pagamenti.vendite_contabili_righe.importo%TYPE := 0;
BEGIN
    -- =========================================================
    -- 1) GUARD DI PARAMETRO
    --    Un id nullo o non positivo non esce da nessuna
    --    interfaccia: lo produce solo un chiamante rotto, e per
    --    questo il codice è TECNICO e non DATO_ERRATO.
    -- =========================================================
    IF p_contabile_id IS NULL OR p_contabile_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_contabile_id', 'valore', p_contabile_id),
            NULL::uuid,
            'pagamenti.fn_posta_contabile',
            'p_contabile_id obbligatorio e maggiore di zero');
    END IF;

    -- La dichiarazione è facoltativa, ma è UNA cosa sola: mezza
    -- dichiarazione non si può verificare, e accettarla in
    -- silenzio significherebbe registrare senza controllo
    -- credendo di averlo fatto.
    IF (p_righe_attese IS NULL) <> (p_totale_atteso IS NULL) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'p_righe_attese',  p_righe_attese,
                'p_totale_atteso', p_totale_atteso),
            NULL::uuid,
            'pagamenti.fn_posta_contabile',
            'p_righe_attese e p_totale_atteso si passano insieme, o non si passano');
    END IF;

    IF p_righe_attese IS NOT NULL AND p_righe_attese < 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_PAGAMENTI_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_righe_attese', 'valore', p_righe_attese),
            NULL::uuid,
            'pagamenti.fn_posta_contabile',
            'p_righe_attese non puo'' essere negativo');
    END IF;

    -- =========================================================
    -- 2) LOCK DELLA TESTATA
    --    Serve a non registrare due volte in parallelo. ⚠️ FOR
    --    UPDATE OF c: si blocca la sola testata, non la lookup
    --    degli stati che le sta accanto nella JOIN.
    -- =========================================================
    SELECT c.stato_id, s.codice_interno, s.descrizione, s.is_registrabile, c.codice,
           c.centro_riscossione_id, c.data_contabile, c.data_registrazione,
           c.importo_dichiarato
      INTO v_stato_id, v_stato, v_stato_label, v_registrabile, v_codice,
           v_centro_id, v_data_contabile, v_data_registrazione,
           v_importo_dichiarato
      FROM pagamenti.vendite_contabili c
      JOIN pagamenti.vendite_contabili_stati s ON s.id = c.stato_id
     WHERE c.id = p_contabile_id
       FOR UPDATE OF c;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_CONTABILE_NON_TROVATA',
            jsonb_build_object('contabile_id', p_contabile_id),
            NULL::uuid,
            p_contabile_id::text);
    END IF;

    -- =========================================================
    -- 3) GUARD DI STATO
    --    Si registra SOLO da uno stato REGISTRABILE — oggi la sola
    --    VALIDATA: è il gesto «ho finito di inserire» (D14-a-bis).
    --    Da BOZZA la distinta potrebbe cambiare mentre la si
    --    registra; da CHIUSA o ANNULLATA il lavoro è finito.
    -- ⭐ Rev 2026-09-18 (D20-d): la domanda si fa al CATALOGO
    --    (vendite_contabili_stati.is_registrabile), non al letterale
    --    'VALIDATA'. Stesso codice, stessa frase: cambia CHI lo dice.
    --    Il dettaglio della distinta porta la stessa bandiera, così
    --    «Registra» si spegne col motivo invece di finire qui in 409.
    --    Fail-closed: uno stato nuovo non classificato non si registra.
    -- =========================================================
    IF v_registrabile IS NOT TRUE THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_CONTABILE_NON_REGISTRABILE',
            jsonb_build_object(
                'contabile_id', p_contabile_id,
                'codice',       v_codice,
                'stato',        v_stato),
            NULL::uuid,
            v_codice,
            lower(v_stato_label));
    END IF;

    -- =========================================================
    -- 4) QUADRATURA DELLA DISTINTA (D12-e)
    --    «Ho letto tutto quello che è arrivato?» — tutte le
    --    righe attive, SCARTATA compresa: quel denaro è
    --    arrivato comunque.
    --    ℹ️ Lo stesso controllo lo fa il guard di validazione
    --    entrando in VALIDATA; qui si ripete perché fra i due
    --    momenti le righe possono essere cambiate.
    -- =========================================================
    SELECT COALESCE(SUM(cr.importo), 0)
      INTO v_somma_righe
      FROM pagamenti.vendite_contabili_righe cr
     WHERE cr.contabile_id = p_contabile_id
       AND cr.attivo IS TRUE;

    IF v_importo_dichiarato IS NOT NULL
       AND v_importo_dichiarato IS DISTINCT FROM v_somma_righe THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA',
            jsonb_build_object(
                'campo',              'importo_dichiarato',
                'contabile_id',       p_contabile_id,
                'codice',             v_codice,
                'importo_dichiarato', v_importo_dichiarato,
                'somma_righe',        v_somma_righe),
            NULL::uuid,
            v_codice,
            v_importo_dichiarato::text,
            v_somma_righe::text);
    END IF;

    -- =========================================================
    -- 5) LE RIGHE PRONTE, e la DICHIARAZIONE di chi conferma
    --    Pronte = stato `is_postabile`. Le SOSPESE restano dove
    --    sono: è D3-a, e non richiede nessun meccanismo nuovo.
    -- =========================================================
    SELECT COUNT(*)::integer, COALESCE(SUM(cr.importo), 0)
      INTO v_righe_pronte, v_totale_pronte
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
     WHERE cr.contabile_id = p_contabile_id
       AND cr.attivo IS TRUE
       AND st.is_postabile IS TRUE;

    -- ⚠️ Si rifiuta PRIMA di scrivere qualsiasi cosa: la
    --    registrazione non si torna indietro, e un avviso dopo
    --    non ripara niente.
    IF p_righe_attese IS NOT NULL
       AND (p_righe_attese <> v_righe_pronte
            OR p_totale_atteso IS DISTINCT FROM v_totale_pronte) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_CONTABILE_DICHIARAZIONE_NON_CORRISPONDE',
            jsonb_build_object(
                'contabile_id',   p_contabile_id,
                'codice',         v_codice,
                'righe_attese',   p_righe_attese,
                'totale_atteso',  p_totale_atteso,
                'righe_pronte',   v_righe_pronte,
                'totale_pronte',  v_totale_pronte),
            NULL::uuid,
            v_codice,
            p_righe_attese::text,
            p_totale_atteso::text,
            v_righe_pronte::text,
            v_totale_pronte::text);
    END IF;

    -- =========================================================
    -- 5-bis) IL RIFIUTO PARLANTE
    --    Da una riga non abbinata non si deriva un movimento. Lo
    --    direbbe comunque il trigger di mirror, ma più tardi e
    --    con un messaggio che parla del movimento invece che
    --    della riga.
    --    ℹ️ Il contesto NON porta la chiave `campo`, e non è una
    --    dimenticanza: non c'è UN campo da accendere, ci sono N
    --    righe — i loro id stanno nel contesto.
    -- =========================================================
    SELECT COUNT(*)::integer
      INTO v_senza_abbinamento
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
     WHERE cr.contabile_id = p_contabile_id
       AND cr.attivo IS TRUE
       AND st.is_postabile IS TRUE
       AND (cr.fattura_id IS NULL OR cr.billing_account_id IS NULL);

    IF v_senza_abbinamento > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO',
            jsonb_build_object(
                'contabile_id',  p_contabile_id,
                'codice',        v_codice,
                'quante',        v_senza_abbinamento,
                'contabile_righe_ids', (
                    SELECT jsonb_agg(cr.id ORDER BY cr.id)
                      FROM pagamenti.vendite_contabili_righe cr
                      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
                     WHERE cr.contabile_id = p_contabile_id
                       AND cr.attivo IS TRUE
                       AND st.is_postabile IS TRUE
                       AND (cr.fattura_id IS NULL OR cr.billing_account_id IS NULL))),
            NULL::uuid,
            'POSTATA',
            'la fattura e il cliente');
    END IF;

    -- =========================================================
    -- 6) NIENTE DA REGISTRARE — e non è un errore (Q-7)
    -- =========================================================
    IF v_righe_pronte = 0 THEN
        SELECT COUNT(*)::integer
          INTO v_saltate
          FROM pagamenti.vendite_contabili_righe cr
          JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
         WHERE cr.contabile_id = p_contabile_id
           AND cr.attivo IS TRUE
           AND st.is_final IS NOT TRUE;

        RETURN QUERY SELECT 0, 0, v_saltate, 0::numeric, 'NULLA_DA_POSTARE'::text;
        RETURN;
    END IF;

    -- =========================================================
    -- 7) GLI STATI DI DESTINAZIONE, letti per codice_interno
    --    (la chiave immutabile, mai `codice`).
    --    ⚠️ Nessun ripiego: uno stato mancante è una
    --    configurazione rotta, e si dice.
    -- =========================================================
    SELECT s.id INTO v_stato_postata_id
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.codice_interno = 'POSTATA' AND s.attivo IS TRUE
     LIMIT 1;

    IF v_stato_postata_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_CONTABILE_STATO_NON_CONFIGURATO',
            jsonb_build_object('codice_interno', 'POSTATA', 'catalogo', 'vendite_contabili_righe_stati'),
            NULL::uuid,
            'POSTATA');
    END IF;

    SELECT s.id INTO v_stato_chiusa_id
      FROM pagamenti.vendite_contabili_stati s
     WHERE s.codice_interno = 'CHIUSA' AND s.attivo IS TRUE
     LIMIT 1;

    IF v_stato_chiusa_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'pagamenti.fn_posta_contabile',
            'E_CONTABILE_STATO_NON_CONFIGURATO',
            jsonb_build_object('codice_interno', 'CHIUSA', 'catalogo', 'vendite_contabili_stati'),
            NULL::uuid,
            'CHIUSA');
    END IF;

    -- =========================================================
    -- 8) PRIMO STATEMENT — i MOVIMENTI
    --    ⚠️ fattura_id, billing_account_id e contabile_id NON si
    --    passano: li deriva dalla riga il trigger di mirror, che
    --    rifiuta i valori incoerenti. Passarli qui vorrebbe dire
    --    scrivere due volte la stessa verità.
    --    ⭐ `centro_riscossione_id` invece SÌ, e conta: è ciò che
    --    distingue la cassa dai centri interni (fondo fattura,
    --    compensazione), e ogni misura di «incassato» deve poterli
    --    escludere.
    --    ℹ️ Il doppio movimento è impossibile per costruzione
    --    (`uq_vendite_movimenti_contabile_riga`): se scattasse,
    --    è un'anomalia e deve farsi sentire, non essere inghiottita.
    -- =========================================================
    WITH ins AS (
        INSERT INTO pagamenti.vendite_movimenti (
            contabile_riga_id, data_effettiva, data_registrazione,
            data_contabile, data_valuta, data_contabilizzazione,
            importo, centro_riscossione_id, meta)
        SELECT cr.id,
               COALESCE(cr.data_pagamento, v_data_contabile),
               v_data_registrazione,
               v_data_contabile,
               cr.data_valuta,
               (SELECT script.fn_data_operativa()),
               cr.importo,
               v_centro_id,
               jsonb_build_object('origine', 'POSTING', 'contabile_codice', v_codice)
          FROM pagamenti.vendite_contabili_righe cr
          JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
         WHERE cr.contabile_id = p_contabile_id
           AND cr.attivo IS TRUE
           AND st.is_postabile IS TRUE
        RETURNING contabile_riga_id, importo
    )
    SELECT array_agg(ins.contabile_riga_id ORDER BY ins.contabile_riga_id),
           COUNT(*)::integer,
           COALESCE(SUM(ins.importo), 0)
      INTO v_righe_ids, v_movimenti, v_totale_postato
      FROM ins;

    -- =========================================================
    -- 9) SECONDO STATEMENT — le RIGHE a POSTATA
    --    🔴 Statement separato, non una CTE: con la RLS padre e
    --    figlio nella stessa snapshot non si vedono.
    --    ⚠️ Si aggiornano ESATTAMENTE le righe di cui si è appena
    --    scritto il movimento: ripetere il predicato porterebbe a
    --    POSTATA anche una riga aggiunta nel frattempo, che
    --    resterebbe senza movimento.
    --    ⭐ È questo UPDATE a far scattare, sulle righe che
    --    vengono da un fondo fattura, il trigger che porta l'atto
    --    a ESEGUITO.
    -- =========================================================
    WITH upd AS (
        UPDATE pagamenti.vendite_contabili_righe cr
           SET stato_id = v_stato_postata_id
         WHERE cr.id = ANY (COALESCE(v_righe_ids, '{}'::bigint[]))
        RETURNING cr.id
    )
    SELECT COUNT(*)::integer INTO v_postate FROM upd;

    -- =========================================================
    -- 10) CHE COSA RESTA INDIETRO
    --     Le righe attive in uno stato NON finale: quelle di cui
    --     nessuno ha ancora detto che cosa ne è stato.
    -- =========================================================
    SELECT COUNT(*)::integer
      INTO v_saltate
      FROM pagamenti.vendite_contabili_righe cr
      JOIN pagamenti.vendite_contabili_righe_stati st ON st.id = cr.stato_id
     WHERE cr.contabile_id = p_contabile_id
       AND cr.attivo IS TRUE
       AND st.is_final IS NOT TRUE;

    -- =========================================================
    -- 11) CONFERMA E CHIUSURA (D13 + decisione del 2026-08-22)
    --     La conferma è l'atto di REGISTRARE: il COALESCE tiene
    --     la prima volta che è successo.
    --     La chiusura è una CONSEGUENZA: dopo il posting righe
    --     pronte non ne restano, e il guard di chiusura dichiara
    --     che le altre non devono bloccare.
    -- =========================================================
    UPDATE pagamenti.vendite_contabili c
       SET data_conferma = COALESCE(c.data_conferma, now()),
           user_conferma = COALESCE(c.user_conferma, current_user),
           stato_id      = v_stato_chiusa_id
     WHERE c.id = p_contabile_id;

    RETURN QUERY SELECT v_movimenti, v_postate, v_saltate,
                        COALESCE(v_totale_postato, 0), 'POSTATA'::text;
END;
$function$

COMMENT ON FUNCTION pagamenti.fn_posta_contabile(p_contabile_id bigint, p_righe_attese integer, p_totale_atteso numeric)
IS 'LA MADRE DEL POSTING (S1-10 del cantiere incassi, 2026-08-22): trasforma in movimenti contabili le righe PRONTE di una distinta e la chiude. ⭐ E'' il punto in cui nasce il primo movimento del progetto: da qui pagamenti.fn_get_saldo_fattura smette di rispondere «residuo = totale» per costruzione. Una sola SELECT per il chiamante — atomica per costruzione, linee-guida-sql §5b — ma DUE STATEMENT dentro: prima l''INSERT dei movimenti, poi l''UPDATE delle righe a POSTATA. 🔴 Non e'' eleganza mancata: con la RLS attiva padre e figlio nella stessa snapshot non si vedono e il WITH CHECK nega fail-closed. ⚠️ E i due statement sono legati da un ARRAY DI ID, non dal ripetere il predicato: fra l''uno e l''altro un''altra sessione puo'' aggiungere una riga alla distinta, e ripetere il predicato la porterebbe a POSTATA senza il suo movimento. ⭐ FIRMA: p_righe_attese e p_totale_atteso sono la DICHIARAZIONE di chi conferma (D13) — facoltativi ma legati, o tutti e due o nessuno. Valorizzati, la funzione rifiuta se la distinta e'' cambiata, PRIMA di scrivere: la registrazione non si torna indietro. Assenti, si registra cio'' che c''e'' — la strada dei processi automatici, che non hanno un operatore che guarda. ⚠️ DUE controlli che sembrano uno: la QUADRATURA (959) confronta tutte le righe con importo_dichiarato («ho letto tutto quello che e'' arrivato?»), la DICHIARAZIONE (963) confronta le righe pronte adesso con quelle che l''operatore ha contato («sto registrando quello che mi hanno approvato?»). ⭐ NIENTE DA REGISTRARE NON E'' UN ERRORE (Q-7, opzione B): la funzione non solleva, dichiara l''esito — POSTATA oppure NULLA_DA_POSTARE. Il database scrive nel registro errori PRIMA di sollevare, quindi un pulsante premuto due volte avrebbe lasciato un errore che errore non e''; il messaggio «l''hai gia'' fatto» lo mette il frontend leggendo l''esito. ⭐ LA CHIUSURA E'' UNA CONSEGUENZA, non una scelta (decisione di Tid, 2026-08-22): registrato, la distinta va a CHIUSA. ⚠️ Ha un prezzo pagato nello stesso lotto — una riga rimasta DA_ABBINARE sotto una distinta chiusa non deve poter diventare pronta, e lo impedisce la quarta mossa di trgfn_vendite_contabili_righe_guard_distinta_finale (20260822-01). ⭐ data_conferma / user_conferma esistevano e non le scriveva nessuno (D9-c): le scrive qui, col COALESCE che tiene la prima volta — la conferma e'' l''atto di registrare. ⛔ Cio'' che NON fa: non crea, non modifica e non annulla fondi fattura (i fatti si aggiungono, i saldi si leggono, le decisioni le prende una persona) — ma il fondo se ne accorge lo stesso, perche'' portare la riga a POSTATA fa scattare il trigger che porta l''atto a ESEGUITO; non tocca le rate, che nel modello dell''abbinamento non esistono ancora (slice 2); non scrive in error_log di suo. ⭐ rev 2026-09-18 (20260918-38, D20-d): il guard 3 legge vendite_contabili_stati.is_registrabile al posto del letterale ''VALIDATA'' — stesso codice E_CONTABILE_NON_REGISTRABILE, stessa frase, cambia chi lo dice: il catalogo, che il dettaglio della distinta espone (stato_is_registrabile) per spegnere «Registra» col motivo invece di rispondere 409. Fail-closed su uno stato nuovo. Brief: brief-db-validata-e-registrazione-tardiva §2.4, §4 P-2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
