{% include-markdown "it/dbzero/vendite/manual/fn_get_sorgente_documento_ref.md" %}
# ⚙️ Funzione `fn_get_sorgente_documento_ref`

```sql
CREATE FUNCTION fn_get_sorgente_documento_ref(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_sorgente_documento_ref(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS TABLE(documento_id bigint, documento_numero text)
 LANGUAGE plpgsql
 STABLE ROWS 1
AS $function$
DECLARE
    -- ⭐ rev 2026-10-05 (20261005-26): la chiave si riconosce con i building
    --   block script.fn_sorgente_chiave_uuid / _id, la stessa regola con cui la
    --   salvano il guard e il rubinetto e la cercano fn_stato_sorgente e
    --   vw_pratica_doc_sorgente. Qui c'era una copia della regex (il commento
    --   diceva gia' «una sola definizione»: ora lo e' davvero), piu' larga —
    --   maiuscole, zeri davanti — e un cast '^[0-9]+$'::bigint che su un numero
    --   fuori range sollevava 22003 dentro una lista, la cosa che questa
    --   funzione ha promesso di non fare.
    v_chiave_uuid script.vw_stato_sorgente.sorgente_chiave_uuid%TYPE;
    v_chiave_id   script.vw_stato_sorgente.sorgente_chiave_id%TYPE;

    v_target   config.sorgenti.target_table%TYPE;
    v_selector config.sorgenti.key_selector%TYPE;
    v_label    config.sorgenti.label_selector%TYPE;
    v_uid      text := btrim(COALESCE(p_sorgente_uid, ''));
    v_id       bigint;
    v_numero   text;
    -- Frammento di SELECT per l'etichetta: `t.<col>::text` se la
    -- sorgente dichiara la colonna, altrimenti la costante NULL.
    -- Costruito con %I, quindi un nome bizzarro resta un
    -- identificatore quotato e non diventa sintassi.
    v_label_expr text;
BEGIN
    -- Una riga SEMPRE, anche quando non si risolve niente: i due
    -- OUT partono a NULL e si valorizzano solo se c'e' qualcosa.
    documento_id     := NULL;
    documento_numero := NULL;

    -- ⚠️ Nessun guard che solleva: i parametri mancanti sono il
    --    caso NORMALE di questa funzione — una voce manuale, un
    --    onere o una rettifica non hanno documento a monte. Un
    --    errore qui trasformerebbe una riga legittima in una
    --    lista rotta.
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 OR v_uid = '' THEN
        RETURN NEXT;
        RETURN;
    END IF;

    SELECT s.target_table, s.key_selector, s.label_selector
      INTO v_target, v_selector, v_label
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id;

    IF NOT FOUND OR v_target IS NULL OR v_selector IS NULL THEN
        RETURN NEXT;
        RETURN;
    END IF;

    -- `label_selector` NULL = la sorgente non ha un numero
    -- leggibile (ATTIVITA, ATTIVITA_CONSUMI, le *_RIGA). NON e'
    -- un errore e NON spegne l'id: si continua, l'etichetta resta
    -- NULL.
    v_label_expr := CASE
        WHEN v_label IS NULL THEN 'NULL::text'
        ELSE format('t.%I::text', v_label)
    END;

    -- ===== Il caso REALE: un uuid, qualunque sia il selector ====
    -- 🔴 Misurato il 2026-08-16 su vendite.commesse_attivita: 88
    --    righe su 88 hanno un UUID in `sorgente_uid`, comprese le
    --    44 da ORDINE_VENDITA e quella da DDT, che sono tipi a
    --    chiave `id`. La normalizzazione a id::text che fa
    --    fn_link_commessa_sorgente vale per commesse_sorgenti, non
    --    per questa colonna: qui il documento e' identificato dal
    --    suo uid e basta. Quindi si prova SEMPRE la traduzione.
    -- ⭐ Id ed etichetta nella STESSA lettura: e' la ragione per
    --    cui questa funzione ha sostituito la coppia.
    -- ⚠️ Sul valore RICEVUTO, non sulla copia ripulita: una chiave con spazi
    --   attorno non e' canonica, e altrove (stato, lineage) non si ritrova.
    v_chiave_uuid := script.fn_sorgente_chiave_uuid(p_sorgente_uid);
    IF v_chiave_uuid IS NOT NULL THEN
        -- La tabella arriva dal CATALOGO (regclass), non da un
        -- parametro: non c'e' testo di chiamante dentro il format.
        BEGIN
            EXECUTE format('SELECT t.id, %s FROM %s t WHERE t.uid = $1',
                           v_label_expr, v_target::text)
              INTO v_id, v_numero
              USING v_chiave_uuid;
        EXCEPTION WHEN undefined_column OR undefined_table THEN
            -- Una destinazione senza colonna uid — o un
            -- `label_selector` che nomina una colonna che non
            -- c'e' — e' un difetto di CATALOGO, non della riga
            -- che stiamo elencando. Il cancello che lo rende
            -- rumoroso e' nel pgTAP.
            -- ⚠️ E CADE TUTTO, id compreso, non solo l'etichetta:
            --    e' deliberato. Un ripiego che salva l'id e perde
            --    il solo numero renderebbe il refuso di catalogo
            --    ancora piu' difficile da vedere — una colonna
            --    vuota fra molte piene. Cosi' invece sparisce
            --    anche l'azione «apri», e qualcuno lo nota.
            RETURN NEXT;
            RETURN;
        END;

        documento_id     := v_id;
        documento_numero := v_numero;
        RETURN NEXT;
        RETURN;
    END IF;

    -- ===== Chiave gia' numerica =====
    -- Oggi non succede su commesse_attivita, ma la forma canonica
    -- di `config.sorgenti` la ammette (ed e' quella che vive in
    -- commesse_sorgenti): un id in forma testuale su un tipo a
    -- chiave `id` e' se stesso. L'id non costa una lettura;
    -- l'etichetta si', e solo se e' stata dichiarata.
    v_chiave_id := script.fn_sorgente_chiave_id(p_sorgente_uid);
    IF v_selector = 'id' AND v_chiave_id IS NOT NULL THEN
        v_id := v_chiave_id;

        IF v_label IS NOT NULL THEN
            BEGIN
                EXECUTE format('SELECT %s FROM %s t WHERE t.id = $1',
                               v_label_expr, v_target::text)
                  INTO v_numero
                  USING v_id;
            EXCEPTION WHEN undefined_column OR undefined_table THEN
                v_numero := NULL;
            END;
        END IF;

        documento_id     := v_id;
        documento_numero := v_numero;
        RETURN NEXT;
        RETURN;
    END IF;

    -- Tutto il resto e' un dato incoerente — un numero su un tipo
    -- a chiave uuid, o una stringa che non e' ne' l'uno ne'
    -- l'altro. Non si indovina: l'azione «apri» sparisce e
    -- l'etichetta resta vuota.
    RETURN NEXT;
    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_sorgente_documento_ref(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'Il documento di origine di una riga a sorgente polimorfa, in DUE informazioni e UNA lettura: `documento_id` (l''id numerico, per l''azione «apri documento sorgente») e `documento_numero` (il numero che l''operatore legge — DDT0010839, ORD0000227, RESO0005122). Sostituisce vendite.fn_get_sorgente_documento_id, che faceva la sola prima meta'': una gemella per l''etichetta avrebbe voluto DUE EXECUTE per riga di lista e DUE copie della stessa regola di risoluzione. 🔴 La traduzione non e'' banale perche'' la chiave e'' polimorfa per costruzione: con config.sorgenti.key_selector = ''id'' il campo sorgente_uid contiene gia'' l''id in forma testuale, con ''uid'' contiene un UUID e l''id va LETTO sulla target_table — e nel dato reale (misurato 2026-08-16) 88 righe su 88 di commesse_attivita portano un UUID, ordini e DDT compresi. ⭐ L''ETICHETTA SI DICHIARA, NON SI INDOVINA: la colonna arriva da config.sorgenti.label_selector, gemella di key_selector — `numero` su preventivi, contratti, ordini, ddt, resi e fatture, `codice` su offerte commerciali e commesse. Un COALESCE(numero, codice) funzionerebbe oggi e diventerebbe una colonna vuota in silenzio alla terza convenzione. label_selector NULL (ATTIVITA, ATTIVITA_CONSUMI, le cinque *_RIGA) = nessun numero leggibile: `documento_numero` resta NULL e NON spegne `documento_id`. ⭐ RESTITUISCE SEMPRE UNA RIGA, anche tutta a NULL: una RETURNS TABLE che a volte torna zero righe funziona con LEFT JOIN LATERAL e CANCELLA la riga chiamante se un domani qualcuno scrive CROSS JOIN LATERAL per distrazione. ⚠️ NON SOLLEVA, ed e'' la differenza con vendite.fn_link_commessa_sorgente: quella scrive un legame e davanti a una chiave irrisolvibile alza E_SORG_NORM_NON_RISOLTA, perche'' un legame sbagliato e'' peggio di nessun legame; questa risponde a una lista, dove una sorgente non risolta deve solo far sparire l''azione — come per le voci manuali, gli oneri e le rettifiche, che un documento a monte non ce l''hanno per progetto. ⚠️ SECURITY INVOKER: le tabelle di destinazione hanno la RLS operatori, quindi NULL significa «non risolvibile O non visibile a chi chiede», non «non esiste». Richiesta BE del 2026-08-20 (punto 2), brief-design-note-credito-resi §40.1.4. ⭐ rev 2026-10-05 (20261005-26): la chiave si riconosce con i building block script.fn_sorgente_chiave_uuid / _id (forma CANONICA, mai un errore), la stessa regola del guard della sorgente polimorfa, del rubinetto fn_link_commessa_sorgente e dei lettori fn_stato_sorgente / vw_pratica_doc_sorgente. Prima una copia della regex, piu'' larga (maiuscole, zeri davanti), e un cast che su un id fuori range sollevava 22003 dentro una lista: ora quella chiave e'' semplicemente non risolta. Una chiave non canonica resta non risolta qui come altrove.';
```

</div>

---
{% include-markdown "signature-core.md" %}
