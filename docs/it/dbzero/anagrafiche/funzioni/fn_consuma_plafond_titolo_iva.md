{% include-markdown "it/dbzero/anagrafiche/manual/fn_consuma_plafond_titolo_iva.md" %}
# ⚙️ Funzione `fn_consuma_plafond_titolo_iva`

```sql
CREATE FUNCTION fn_consuma_plafond_titolo_iva(p_titolo_iva_id bigint, p_fattura_id bigint, p_imponibile numeric, p_data_movimento date, p_fattura_riga_id bigint, p_tx_id uuid)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_consuma_plafond_titolo_iva(p_titolo_iva_id bigint, p_fattura_id bigint, p_imponibile numeric, p_data_movimento date, p_fattura_riga_id bigint DEFAULT NULL::bigint, p_tx_id uuid DEFAULT NULL::uuid)
 RETURNS TABLE(quota_coperta numeric, quota_ordinaria numeric, residuo_dopo numeric, movimento_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: consumare la capienza di un titolo IVA con tetto e
--   ritornare la RIPARTIZIONE dell'imponibile fra la parte coperta
--   dal titolo e quella che torna all'aliquota ordinaria (P2).
--   Perimetro: prende il lock di riga sul titolo (D15-bis), scrive
--   UN movimento nel registro di D5 e lascia all'accumulatore il
--   compito di riportare imponibile_utilizzato alla somma.
--   Risultato atteso: quota_coperta + quota_ordinaria = p_imponibile,
--   sempre e su tutti i rami.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I7 / D15-bis.
-- ⚠️ Non e' il risolutore: quello e' STABLE e non consuma (D14).
-- ⚠️ Non fa la restituzione della nota di credito (P4): quella e'
--   un INSERT nel registro, senza capienza da calcolare.
DECLARE
    v_titolo      record;
    v_ha_plafond  config.tipi_titolo_iva.ha_plafond%TYPE;
    v_tipo_descr  config.tipi_titolo_iva.descrizione%TYPE;
    v_capienza    anagrafiche.soggetti_titoli_iva.plafond%TYPE;
    v_coperta     anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
    v_mov_id      anagrafiche.soggetti_titoli_iva_movimenti.id%TYPE;
    v_mov_esist   anagrafiche.soggetti_titoli_iva_movimenti.imponibile%TYPE;
BEGIN
    -- ── Guard di invocazione. Questi errori non li puo' produrre
    --    una persona: li produce un chiamante rotto, quindi la
    --    classe e' TECNICA e il messaggio nomina il PARAMETRO —
    --    e' il solo caso in cui nominarlo e' la cosa giusta.
    IF p_titolo_iva_id IS NULL OR p_titolo_iva_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'titolo_iva_id',
                               'valore', p_titolo_iva_id),
            p_tx_id, 'titolo_iva_id');
    END IF;

    IF p_fattura_id IS NULL OR p_fattura_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'fattura_id',
                               'valore', p_fattura_id),
            p_tx_id, 'fattura_id');
    END IF;

    IF p_imponibile IS NULL OR p_imponibile <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'imponibile',
                               'valore', p_imponibile),
            p_tx_id, 'imponibile');
    END IF;

    -- ⚠️ La data e' un PARAMETRO e non `now()`: e' lo stesso
    --    vincolo di firma di D14, e per la stessa ragione — il
    --    lotto puo' girare il giorno dopo la data documento.
    IF p_data_movimento IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'data_movimento'),
            p_tx_id, 'data_movimento');
    END IF;

    -- ══ IL LOCK (D15-bis) ═══════════════════════════════════
    -- ⭐ FOR UPDATE sulla riga del titolo: due transizioni a
    --    DEFINITIVA in parallelo si serializzano qui, e la seconda
    --    legge il residuo GIA' aggiornato dalla prima. Senza,
    --    consumerebbero la stessa capienza e il plafond andrebbe
    --    sotto zero senza che nessun errore lo dica.
    SELECT t.id, t.plafond, t.imponibile_utilizzato, t.validita,
           t.tipo_titolo_iva_id
      INTO v_titolo
      FROM anagrafiche.soggetti_titoli_iva t
     WHERE t.id = p_titolo_iva_id
       FOR UPDATE;

    -- ⚠️ SELECT INTO senza righe azzera il record: senza questa
    --    uscita si proseguirebbe su NULL e si scriverebbe un
    --    movimento orfano (che la FK poi rifiuta, con un 23503
    --    muto invece del codice giusto).
    IF v_titolo.id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva',
            'E_TITOLO_IVA_CONSUMO_NON_INVOCABILE',
            jsonb_build_object('parametro', 'titolo_iva_id',
                               'valore', p_titolo_iva_id),
            p_tx_id, 'titolo_iva_id');
    END IF;

    SELECT tt.ha_plafond, tt.descrizione
      INTO v_ha_plafond, v_tipo_descr
      FROM config.tipi_titolo_iva tt
     WHERE tt.id = v_titolo.tipo_titolo_iva_id;

    -- ── Un consumo fuori dalla validita' del titolo e' un errore
    --    di chi ha risolto, non dell'operatore: il risolutore
    --    sceglie i titoli validi ALLA DATA DEL DOCUMENTO, quindi
    --    qui non ci si arriva per una strada legittima. E' pero'
    --    esattamente il tipo di errore che nessuno vedrebbe: un
    --    plafond consumato da una fattura che quel titolo non
    --    copre piu'.
    IF NOT (v_titolo.validita @> p_data_movimento) THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche', 'fn_consuma_plafond_titolo_iva',
            'E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA',
            jsonb_build_object('titolo_iva_id', p_titolo_iva_id,
                               'data_movimento', p_data_movimento),
            p_tx_id,
            COALESCE(v_tipo_descr, ''),
            to_char(p_data_movimento, 'DD/MM/YYYY'));
    END IF;

    -- ══ TITOLO SENZA TETTO: copre tutto, non scrive niente ═══
    IF v_ha_plafond IS NOT TRUE THEN
        quota_coperta   := p_imponibile;
        -- ⚠️ `p_imponibile - quota_coperta` e non il letterale 0,
        --    ed e' una correzione fatta dal test: il letterale
        --    esce con scala ZERO, mentre gli altri rami ereditano
        --    la scala dell'importo. La stessa funzione ritornava
        --    `0` su un ramo e `0.00` sugli altri — innocuo finche'
        --    chi legge fa aritmetica, una differenza visibile
        --    appena qualcuno confronta o stampa il risultato.
        --    Scritta cosi' dice anche l'invariante: le due quote
        --    sommano SEMPRE all'imponibile passato.
        quota_ordinaria := p_imponibile - quota_coperta;
        residuo_dopo    := NULL;
        movimento_id    := NULL;
        RETURN NEXT;
        RETURN;
    END IF;

    -- ══ IDEMPOTENZA ═════════════════════════════════════════
    -- ⭐ Se questa fattura (questa riga) ha gia' consumato questo
    --    titolo, si rilegge quello che c'e' invece di scrivere un
    --    secondo movimento. La rete resta la UNIQUE parziale, ma
    --    quella parla con un 23505 muto dentro una transizione di
    --    stato: meglio non doverla incontrare.
    SELECT m.imponibile, m.id
      INTO v_mov_esist, v_mov_id
      FROM anagrafiche.soggetti_titoli_iva_movimenti m
     WHERE m.titolo_iva_id   = p_titolo_iva_id
       AND m.tipo_movimento  = 'FATTURA'
       AND m.fattura_id      = p_fattura_id
       AND m.fattura_riga_id IS NOT DISTINCT FROM p_fattura_riga_id;

    IF v_mov_id IS NOT NULL THEN
        quota_coperta   := v_mov_esist;
        quota_ordinaria := p_imponibile - v_mov_esist;
        residuo_dopo    := v_titolo.plafond - v_titolo.imponibile_utilizzato;
        movimento_id    := v_mov_id;
        RETURN NEXT;
        RETURN;
    END IF;

    -- ══ LA SPEZZATURA DI P2 ═════════════════════════════════
    -- ⚠️ GREATEST(..., 0): un titolo gia' sfondato da una forzatura
    --    ha residuo negativo, e senza questo la quota coperta
    --    diventerebbe negativa — cioe' un consumo che RESTITUISCE
    --    capienza. Sfondato vuol dire capienza zero, non capienza
    --    al contrario.
    v_capienza := GREATEST(v_titolo.plafond - v_titolo.imponibile_utilizzato, 0);
    v_coperta  := LEAST(p_imponibile, v_capienza);

    IF v_coperta > 0 THEN
        INSERT INTO anagrafiche.soggetti_titoli_iva_movimenti
            (titolo_iva_id, tipo_movimento, imponibile, data_movimento,
             fattura_id, fattura_riga_id, tx_id)
        VALUES
            (p_titolo_iva_id, 'FATTURA', v_coperta, p_data_movimento,
             p_fattura_id, p_fattura_riga_id, p_tx_id)
        RETURNING id INTO v_mov_id;
    END IF;

    quota_coperta   := v_coperta;
    quota_ordinaria := p_imponibile - v_coperta;
    residuo_dopo    := v_capienza - v_coperta;
    movimento_id    := v_mov_id;
    RETURN NEXT;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_consuma_plafond_titolo_iva(p_titolo_iva_id bigint, p_fattura_id bigint, p_imponibile numeric, p_data_movimento date, p_fattura_riga_id bigint, p_tx_id uuid)
IS 'La primitiva di consumo del plafond (D15-bis di brief-db-be-iva-risolutore-e-regime-cliente). Prende il LOCK di riga sul titolo, calcola la capienza residua, consuma fino a capienza e ritorna la RIPARTIZIONE che P2 pretende: quota coperta dal titolo + quota che torna all''aliquota ordinaria, la cui somma e'' sempre l''imponibile passato. 🔴 Il lock non e'' prudenziale: finche'' due fatture stanno in bozza entrambe PROIETTANO sullo stesso residuo, ed e'' corretto — sono anteprime; ma due transizioni a DEFINITIVA in parallelo, senza lock, consumano la stessa capienza e mandano il plafond sotto zero IN SILENZIO, su precisamente il numero che l''Agenzia delle Entrate verifica. ⚠️ Il lock non basta e la seconda meta'' e'' DICHIARATA: D15-bis chiede anche un ordine deterministico — chi arriva prima si prende la capienza, e «prima» dev''essere una regola del dominio (data documento, poi numero). Quella meta'' NON e'' realizzabile qui, perche'' un lock non puo'' sapere che esiste una fattura precedente non ancora arrivata: la sede e'' il ciclo che chiama, che deve iterare ORDER BY data documento, numero. Il DB garantisce che il conto non vada sotto, il chiamante garantisce CHI prende la capienza; il registro rende l''ordine verificabile a posteriori. ⭐ Ritorna una RIPARTIZIONE e non un numero (§2.7.3): una funzione che desse la sola quota coperta obbligherebbe il chiamante a ricostruire l''altra meta'', cioe'' farebbe uscire la regola proprio nel caso per cui il risolutore esiste. ⚠️ Su un titolo SENZA tetto copre tutto e non scrive niente: un movimento a saldo zero allungherebbe il registro senza dire nulla. ⭐ IDEMPOTENTE: se la stessa fattura (stessa riga) ha gia'' consumato quel titolo rilegge il movimento invece di scriverne un secondo — la UNIQUE parziale resta la rete, ma parla con un 23505 muto dentro una transizione di stato. ⚠️ GREATEST(residuo, 0): un titolo sfondato da una forzatura ha residuo negativo, e senza quello un consumo RESTITUIREBBE capienza. ⛔ NON e'' il risolutore, che e'' STABLE e non consuma (D14): un risolutore che consumasse non si potrebbe chiamare per un''anteprima, cioe'' per l''uso che ne fa il documento a monte. ⛔ E non fa la restituzione della nota di credito (P4): quella e'' un INSERT nel registro con importo negativo, senza capienza da calcolare — metterla qui avrebbe dato una funzione con due comportamenti opposti sotto lo stesso nome. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

---
{% include-markdown "signature-core.md" %}
