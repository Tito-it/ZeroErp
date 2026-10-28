{% include-markdown "it/dbzero/vendite/manual/fn_assign_numero_fattura.md" %}
# ⚙️ Funzione `fn_assign_numero_fattura`

```sql
CREATE FUNCTION fn_assign_numero_fattura(p_fattura_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_assign_numero_fattura(p_fattura_id bigint)
 RETURNS TABLE(registro_id bigint, anno smallint, serie character varying, numero bigint)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_registro_id vendite.fatture.registro_id%TYPE;
    v_data        vendite.fatture.data%TYPE;
    v_serie       vendite.fatture.serie%TYPE;
    -- ⭐ rev 2026-08-26: la competenza del DOCUMENTO, che il
    --    cancello usa per il limite di emissione.
    v_competenza  vendite.fatture.competenza_mese%TYPE;
    v_anno        vendite.fatture.anno%TYPE;
    v_numero      vendite.fatture.numero%TYPE;
    -- D-K: stato dei satelliti, letto una volta sola.
    v_tot_pagare  vendite.fatture.totale_a_pagare%TYPE;
    v_tot_doc     vendite.fatture.totale_doc%TYPE;
    v_impo_tot    vendite.fatture.imponibile_tot%TYPE;
    v_imps_tot    vendite.fatture.imposta_tot%TYPE;
    v_n_iva       INTEGER;
    v_sum_impo    NUMERIC;
    v_sum_imps    NUMERIC;
    v_n_rate      INTEGER;
    v_sum_rate    NUMERIC;
    v_fondi       NUMERIC;
    v_arr_prec    vendite.fatture.arrotondamento_precedente%TYPE;
    v_arr_att     vendite.fatture.arrotondamento_attuale%TYPE;
    v_motivi      TEXT[] := ARRAY[]::TEXT[];
    -- D-K condizione 7: la natura del documento, per chiave naturale.
    v_natura_cod  config.nature_doc_fiscale.codice_interno%TYPE;
BEGIN
    -- ⭐ rev 2026-08-25 (cantiere numerazione-data-documento):
    --    1) si passa p_fattura_id a fn_get_next_progressivo, che
    --       ne ha bisogno per il BERSAGLIO del cancello;
    --    2) `mese` esce dal RETURNS TABLE, e con lui reset_policy.
    -- ⭐ rev 2026-08-26 (cantiere limite-emissione, DB-14):
    --    si legge f.competenza_mese e la si passa al cancello, che
    --    la usa per il LIMITE DI EMISSIONE. Costa una colonna in
    --    una SELECT che c'e' gia'.

    -- Guard: parametro obbligatorio.
    -- ⭐ rev 2026-08-26: era E_PARAMETRO_INVALIDO con dentro
    --    `p_fattura_id obbligatorio e > 0` — un nome di variabile
    --    PL/pgSQL nella frase che legge una persona.
    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_assign_numero_fattura',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'fattura_id obbligatorio e maggiore di zero',
                'p_fattura_id', p_fattura_id),
            NULL::uuid,
            'vendite.fn_assign_numero_fattura',
            'p_fattura_id (obbligatorio, maggiore di zero)');
    END IF;

    -- Recupera dati fattura + registro con lock (solo la riga fattura, alias f)
    -- ⛔ Il JOIN sul registro RESTA: porta serie_default, cioe' il
    --    punto in cui la SERIE di un documento si risolve davvero.
    --    E' la stessa risoluzione che usano
    --    fn_get_pavimento_sequenza e il backfill di ultima_data:
    --    se una delle tre diverge, cerca una riga di contatore che
    --    non esiste e risponde «nessun vincolo».
    -- ⭐ rev 2026-08-26: `competenza_mese` entra QUI, non in una
    --    query sua. E la RLS lavora nel verso giusto: se questa
    --    riga non e' visibile non si numera affatto.
    SELECT f.registro_id,
           f.data,
           COALESCE(f.serie, r.serie_default, ''),
           f.competenza_mese
      INTO v_registro_id, v_data, v_serie, v_competenza
      FROM vendite.fatture f
      JOIN vendite.registri_fatturazione r ON r.id = f.registro_id
     WHERE f.id = p_fattura_id
       FOR UPDATE OF f;

    IF v_registro_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_assign_numero_fattura', 'E_VALORE_MANCANTE',
            jsonb_build_object('fattura_id', p_fattura_id),
            NULL::uuid, concat('fattura_id ', p_fattura_id)
        );
    END IF;

    -- ----------------------------------------------------
    -- Guard D3: un documento senza righe non si numera.
    -- ⚠️ RETTIFICA 2026-08-02: la motivazione originale diceva
    --    «nextval non fa rollback». Non e' vero qui —
    --    fn_get_next_progressivo e' table-based e transazionale.
    --    Il guard resta PRIMA, ma perche' non si scrive prima di
    --    aver validato e per non entrare in contesa sull'advisory
    --    lock del registro con un documento gia' rotto.
    -- brief-fix-importi-riga-fattura-zero §4.5.
    -- ----------------------------------------------------
    PERFORM 1
       FROM vendite.fatture_righe r
      WHERE r.fattura_id = p_fattura_id
      LIMIT 1;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_assign_numero_fattura', 'E_FATTURA_SENZA_RIGHE',
            jsonb_build_object('fattura_id', p_fattura_id,
                               'registro_id', v_registro_id,
                               -- ⭐ Il bersaglio: questa funzione gira DENTRO il
                               --    giro di lotto, su molte fatture. La frase
                               --    dice quale ha rifiutato, il bersaglio la fa
                               --    aprire. La fattura e' gia' stata letta.
                               'bersaglio', jsonb_build_array(
                                   jsonb_build_object('tipo', 'FATTURA',
                                                      'id', p_fattura_id::text))),
            NULL::uuid, p_fattura_id::text
        );
    END IF;

    -- ----------------------------------------------------
    -- Guard D-K (Fase 4b): coerenza del documento, sempre
    -- PRIMA di consumare il progressivo.
    -- Si guarda il RISULTATO, non chi avrebbe dovuto scriverlo:
    -- cosi' il presidio copre anche il caso piu' probabile, cioe'
    -- un task dello step EMESSA che non ha girato affatto.
    -- Da qui in poi sappiamo gia' che le righe esistono.
    -- ----------------------------------------------------
    SELECT f.totale_a_pagare, f.totale_doc, f.imponibile_tot, f.imposta_tot,
           (SELECT count(*)::int             FROM vendite.fatture_riepiloghi_iva i WHERE i.fattura_id = p_fattura_id),
           (SELECT COALESCE(sum(i.imponibile), 0) FROM vendite.fatture_riepiloghi_iva i WHERE i.fattura_id = p_fattura_id),
           (SELECT COALESCE(sum(i.imposta), 0)    FROM vendite.fatture_riepiloghi_iva i WHERE i.fattura_id = p_fattura_id),
           (SELECT count(*)::int             FROM vendite.fatture_scadenze s WHERE s.fattura_id = p_fattura_id),
           (SELECT COALESCE(sum(s.importo), 0)    FROM vendite.fatture_scadenze s WHERE s.fattura_id = p_fattura_id),
           COALESCE(vendite.fn_get_totale_fondi_fattura(p_fattura_id), 0),
           f.arrotondamento_precedente, f.arrotondamento_attuale,
           nd.codice_interno
      INTO v_tot_pagare, v_tot_doc, v_impo_tot, v_imps_tot,
           v_n_iva, v_sum_impo, v_sum_imps, v_n_rate, v_sum_rate,
           v_fondi, v_arr_prec, v_arr_att, v_natura_cod
      FROM vendite.fatture f
      JOIN config.nature_doc_fiscale nd ON nd.id = f.natura_doc_id
     WHERE f.id = p_fattura_id;

    -- ⚠️ `array_append` e non `|| 'testo'`: con un letterale non
    --    tipizzato PostgreSQL prova a leggerlo come letterale di
    --    ARRAY e solleva «l'array deve iniziare con {». I rami che
    --    usano format() non lo mostrano — format() restituisce gia'
    --    un text — quindi il difetto si nasconde nei soli casi a
    --    testo fisso. Qui la forma e' una sola per tutti e cinque.

    -- 1) I totali non sono mai stati calcolati.
    IF v_tot_pagare IS NULL THEN
        v_motivi := array_append(v_motivi, 'totali non calcolati (totale_a_pagare assente)');
    END IF;

    -- 2) Righe presenti (verificato sopra) ma nessun riepilogo IVA.
    IF v_n_iva = 0 THEN
        v_motivi := array_append(v_motivi, 'riepilogo IVA assente');
    END IF;

    -- 3) Documento da REGOLARE (totale diverso da zero, col segno): il
    --    piano rate deve esserci e quadrare. ⭐ rev 2026-09-17 (P-5): vale
    --    anche sulla nota di credito, che ha UNA rata negativa uguale al
    --    totale — «> 0» e' diventato «<> 0», e la somma col segno e'
    --    ANCHE il presidio di coerenza di segno che prima faceva il CHECK
    --    sull'importo (tolto nel 20260917-11): una rata di segno sbagliato
    --    rompe l'uguaglianza. L'uguaglianza e' esatta perche' il generatore
    --    quadra per costruzione e i tipi sono NUMERIC, non floating point.
    IF v_tot_pagare <> 0 AND v_n_rate = 0 THEN
        v_motivi := array_append(v_motivi, 'piano rate assente');
    ELSIF v_tot_pagare <> 0 AND v_sum_rate <> v_tot_pagare THEN
        v_motivi := array_append(v_motivi, format(
            'somma delle rate (%s) diversa dal totale a pagare (%s)',
            v_sum_rate, v_tot_pagare));
    END IF;

    -- 4) D-D allo specchio: un documento a totale ZERO non si rateizza.
    --    ⭐ rev 2026-09-17 (P-5): era «non positivo»; il negativo ora ha
    --    il suo piano come il positivo, e D-D resta vera nel merito —
    --    zero e negativo sono documenti legittimi, solo che il negativo
    --    da regolare ha una rata.
    IF v_tot_pagare IS NOT NULL AND v_tot_pagare = 0 AND v_n_rate > 0 THEN
        v_motivi := array_append(v_motivi, format(
            'presenti %s rate su un totale a pagare zero (%s)',
            v_n_rate, v_tot_pagare));
    END IF;

    -- 5) I riepiloghi IVA devono quadrare con i totali di testata.
    --    Si controlla la catena intera e non il solo estremo: due
    --    scostamenti che si compensano darebbero un totale giusto
    --    con dentro numeri sbagliati.
    IF COALESCE(v_sum_impo, 0) <> COALESCE(v_impo_tot, 0)
       OR COALESCE(v_sum_imps, 0) <> COALESCE(v_imps_tot, 0)
       OR COALESCE(v_impo_tot, 0) + COALESCE(v_imps_tot, 0) <> COALESCE(v_tot_doc, 0) THEN
        v_motivi := array_append(v_motivi, format(
            'riepilogo IVA non coerente con i totali di testata (imponibile %s vs %s, imposta %s vs %s, totale_doc %s)',
            v_sum_impo, v_impo_tot, v_sum_imps, v_imps_tot, v_tot_doc));
    END IF;

    -- 6) L'ultimo anello: `totale_a_pagare` deve DERIVARE da
    --    `totale_doc`. Senza questo controllo la catena resta
    --    aperta nel mezzo — la 5 lega i riepiloghi a totale_doc e
    --    la 3 lega le rate a totale_a_pagare, ma nulla legherebbe
    --    i due totali fra loro, e un fondo aggiunto dopo il
    --    ricalcolo passerebbe indisturbato: rate che quadrano con
    --    un totale che non tiene conto dell'acconto.
    --    L'identita' e' quella di fn_ricalcola_totali_fattura:
    --      totale_a_pagare = totale_doc + fondi
    --                        + arrotondamento_precedente
    --                        + arrotondamento_attuale
    --    Non si ricalcola nulla: si verifica che il valore scritto
    --    sia ancora quello che i suoi addendi producono.
    --    Saltata se il totale e' NULL: l'ha gia' detto la 1, e
    --    ripeterlo qui come «0 non corrisponde» sarebbe rumore.
    IF v_tot_pagare IS NOT NULL
       AND v_tot_pagare <> COALESCE(v_tot_doc, 0) + COALESCE(v_fondi, 0)
                           + COALESCE(v_arr_prec, 0) + COALESCE(v_arr_att, 0) THEN
        v_motivi := array_append(v_motivi, format(
            'totale a pagare (%s) non corrisponde alla somma dei suoi addendi: totale_doc %s + fondi %s + arrotondamenti %s/%s',
            v_tot_pagare, v_tot_doc, v_fondi, v_arr_prec, v_arr_att));
    END IF;

    -- 7) IL SEGNO PORTA IL SIGNIFICATO, e qui smette di essere una
    --    convenzione (brief nota di credito, S12.4-bis.6):
    --      natura = NOTA_CREDITO  <=>  totale_a_pagare <= 0
    --    Controllato PRIMA che il progressivo venga consumato, cioe'
    --    prima del punto in cui l'errore diventa irreparabile: «un
    --    numero fiscale valido su un documento invalido si ripara
    --    solo con una nota di variazione».
    --    ⚠️ Lo ZERO e' ammesso da entrambe le parti: un documento a
    --    saldo nullo e' strano ma non incoerente, e vietarlo qui
    --    sarebbe una regola inventata da questo guard invece che
    --    decisa. Si presidia il SEGNO, non l'importo.
    --    ⚠️ La seconda meta' e' scritta come «diverso da NOTA_CREDITO»
    --    e non come «uguale a FATTURA»: copre anche NOTA_DEBITO senza
    --    doverla nominare, ed e' il verso <= dell'equivalenza.
    IF v_tot_pagare IS NOT NULL AND v_natura_cod = 'NOTA_CREDITO' AND v_tot_pagare > 0 THEN
        v_motivi := array_append(v_motivi, format(
            'natura NOTA_CREDITO con totale a pagare positivo (%s)', v_tot_pagare));
    ELSIF v_tot_pagare IS NOT NULL AND v_natura_cod <> 'NOTA_CREDITO' AND v_tot_pagare < 0 THEN
        v_motivi := array_append(v_motivi, format(
            'natura %s con totale a pagare negativo (%s)', v_natura_cod, v_tot_pagare));
    END IF;

    -- Un errore solo, con TUTTI i motivi: chi lo riceve vede in una
    -- volta cosa manca al documento invece di scoprirlo un giro
    -- alla volta.
    IF array_length(v_motivi, 1) > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_assign_numero_fattura', 'E_FATTURA_NON_NUMERABILE_INCOERENTE',
            jsonb_build_object(
                'fattura_id',      p_fattura_id,
                'registro_id',     v_registro_id,
                'natura',          v_natura_cod,
                'motivi',          to_jsonb(v_motivi),
                'totale_a_pagare', v_tot_pagare,
                'totale_doc',      v_tot_doc,
                'riepiloghi_iva',  v_n_iva,
                'rate',            v_n_rate,
                'somma_rate',      v_sum_rate,
                'fondi',           v_fondi,
                'arrotondamento_precedente', v_arr_prec,
                'arrotondamento_attuale',    v_arr_att),
            NULL::uuid,
            p_fattura_id::text,
            array_to_string(v_motivi, '; ')
        );
    END IF;

    -- Calcolo progressivo
    -- ⭐ rev 2026-08-25: si passa p_fattura_id, che serve SOLO al
    --    bersaglio del cancello. Senza, dentro un giro di lotto
    --    l'errore direbbe da quale data ripartire ma non su quale
    --    documento e' successo.
    -- ⭐ rev 2026-08-26: si passa anche la COMPETENZA, che serve al
    --    limite di emissione. NULL e' ammesso e significa «non la
    --    so»: il cancello ripiega sul mese della data.
    v_anno := vendite.fn_get_anno_registro(v_data);
    v_numero := vendite.fn_get_next_progressivo(
                    v_registro_id, v_data, v_competenza, v_serie, p_fattura_id);

    -- Aggiorna testata fattura
    UPDATE vendite.fatture
       SET anno = v_anno,
           serie = NULLIF(v_serie, ''),
           numero = v_numero,
           data_update = now(),
           user_update = current_user
     WHERE id = p_fattura_id;

    RETURN QUERY SELECT v_registro_id, v_anno, NULLIF(v_serie, '')::VARCHAR, v_numero;
END;
$function$

COMMENT ON FUNCTION vendite.fn_assign_numero_fattura(p_fattura_id bigint)
IS 'Assegna anno, serie e numero a una fattura, dopo il guard D-K di coerenza del documento. Il guard gira SEMPRE prima di consumare il progressivo, perche'' un numero fiscale valido su un documento invalido si ripara solo con una nota di variazione. rev 2026-08-18 (brief-design-note-credito-resi N11): SETTIMA condizione — natura = NOTA_CREDITO <=> totale_a_pagare <= 0. ⭐ Trasforma la scelta «il segno vive nel numero, non in un''etichetta» da convenzione a invariante VERIFICATO, e chiude il cerchio con la FatturaPA dove lo stesso invariante si legge TipoDocumento = TD04 <=> totale_doc < 0. ⚠️ Lo zero e'' ammesso da entrambe le parti: si presidia il SEGNO, non l''importo. ⚠️ La seconda meta'' dice «diverso da NOTA_CREDITO» e non «uguale a FATTURA»: copre anche NOTA_DEBITO senza nominarla. ⭐ rev 2026-08-25: E_FATTURA_SENZA_RIGHE porta il BERSAGLIO sulla fattura; si passa p_fattura_id a fn_get_next_progressivo, che ne ha bisogno per il bersaglio del cancello; `mese` esce dal RETURNS TABLE, e con lui l''ultima lettura di reset_policy. ⭐ rev 2026-08-26 (cantiere limite-emissione, DB-14): si legge f.competenza_mese e la si passa al cancello, che la usa per il LIMITE DI EMISSIONE. ⭐ Costa UNA COLONNA IN UNA SELECT CHE C''E'' GIA'' — quella con FOR UPDATE OF f — e la RLS lavora nel verso giusto: se questa riga non e'' visibile non si numera affatto, quindi nessun fail-open. ⛔ E'' il motivo per cui la competenza sta sulla FATTURA e non si va a prendere dal lotto: vendite.fatturazione_lotti ha la RLS, e leggerlo da dentro una SECURITY INVOKER renderebbe fail-open l''unico presidio non aggirabile. ℹ️ NULL e'' ammesso (fatture nate prima del 2026-08-26) e significa «non la so»: il cancello ripiega sul mese della data. ⭐ Il guard di parametro passa da E_PARAMETRO_INVALIDO — che portava `p_fattura_id obbligatorio e > 0` nella frase letta da una persona — a E_VENDITE_CHIAMATA_NON_VALIDA (TECNICO). ℹ️ Firma e tipo di ritorno NON cambiano: i %TYPE risolvono agli stessi tipi di prima, quindi CREATE OR REPLACE basta — a cambiare firma e'' la funzione chiamata. ⛔ Il JOIN su registri_fatturazione RESTA: porta serie_default, cioe'' il punto in cui la SERIE di un documento si risolve davvero — ed e'' la stessa risoluzione, COALESCE(f.serie, r.serie_default, ''''), che devono usare fn_get_pavimento_sequenza e il backfill di ultima_data; se una delle tre diverge, cerca una riga di contatore che non esiste e risponde «nessun vincolo». ℹ️ Prima del numero ci sono DUE cose: il D-K (il documento merita un numero?) e il cancello dentro fn_get_next_progressivo (la data puo'' stare in fondo alla sequenza, ed e'' ancora emettibile?). Il secondo e'' sotto l''advisory lock, il primo no — e va bene: il D-K guarda la fattura, non la sequenza. Brief: brief-db-limite-emissione-e-data-verificata §11 DB-14. ⭐ rev 2026-09-17 (brief-db-distinta-ricerca-rate §4-bis.6, P-5 / D19-e): le condizioni 3 e 4 del guard D-K sono riscritte col segno — «documento da regolare» e'''' totale_a_pagare <> 0 (il piano rate deve esserci e quadrare, anche sulla nota di credito, che ha UNA rata negativa uguale al totale) e «non si rateizza» e'''' totale = 0. Prima erano > 0 e <= 0, e una nota di credito con la sua rata non si numerava. La somma col segno e'''' anche il presidio di coerenza di segno che faceva chk_fatture_scadenze_importo_pos, tolto nello stesso giro (20260917-11). La settima condizione (natura NOTA_CREDITO <=> totale <= 0) non cambia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
