# ⚙️ Funzione `fn_get_sorgente_documento_id`

```sql
CREATE FUNCTION fn_get_sorgente_documento_id(p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_sorgente_documento_id(p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    -- Stessa forma usata da fn_link_commessa_sorgente: una sola
    -- definizione di «che aspetto ha un uuid» in questo dominio.
    c_uuid_re CONSTANT text :=
        '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$';

    v_target   config.sorgenti.target_table%TYPE;
    v_selector config.sorgenti.key_selector%TYPE;
    v_uid      text := btrim(COALESCE(p_sorgente_uid, ''));
    v_id       bigint;
BEGIN
    -- ⚠️ Nessun guard che solleva: i parametri mancanti sono il
    --    caso NORMALE di questa funzione — una voce manuale non ha
    --    documento a monte. Un errore qui trasformerebbe una riga
    --    legittima in una lista rotta.
    IF p_sorgente_tipo_id IS NULL OR p_sorgente_tipo_id <= 0 OR v_uid = '' THEN
        RETURN NULL;
    END IF;

    SELECT s.target_table, s.key_selector
      INTO v_target, v_selector
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id;

    IF NOT FOUND OR v_target IS NULL OR v_selector IS NULL THEN
        RETURN NULL;
    END IF;

    -- ===== Il caso REALE: un uuid, qualunque sia il selector ====
    -- 🔴 Misurato il 2026-08-16 su vendite.commesse_attivita: 88
    --    righe su 88 hanno un UUID in `sorgente_uid`, comprese le
    --    44 da ORDINE_VENDITA e quella da DDT, che sono tipi a
    --    chiave `id`. La normalizzazione a id::text che fa
    --    fn_link_commessa_sorgente vale per commesse_sorgenti, non
    --    per questa colonna: qui il documento e' identificato dal
    --    suo uid e basta. Quindi si prova SEMPRE la traduzione.
    IF v_uid ~ c_uuid_re THEN
        -- La tabella arriva dal CATALOGO (regclass), non da un
        -- parametro: non c'e' testo di chiamante dentro il format.
        BEGIN
            EXECUTE format('SELECT id FROM %s WHERE uid = $1', v_target::text)
              INTO v_id
              USING v_uid::uuid;
        EXCEPTION WHEN undefined_column OR undefined_table THEN
            -- Una destinazione senza colonna uid e' un difetto di
            -- catalogo, non della riga che stiamo elencando.
            RETURN NULL;
        END;

        RETURN v_id;
    END IF;

    -- ===== Chiave gia' numerica: nessuna lettura =====
    -- Oggi non succede su commesse_attivita, ma la forma canonica
    -- di `config.sorgenti` la ammette (ed e' quella che vive in
    -- commesse_sorgenti): un id in forma testuale su un tipo a
    -- chiave `id` e' se stesso.
    IF v_selector = 'id' AND v_uid ~ '^[0-9]+$' THEN
        RETURN v_uid::bigint;
    END IF;

    -- Tutto il resto e' un dato incoerente — un numero su un tipo
    -- a chiave uuid, o una stringa che non e' ne' l'uno ne'
    -- l'altro. Non si indovina: l'azione «apri» sparisce.
    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_sorgente_documento_id(p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'L''id NUMERICO del documento di origine di una riga con sorgente polimorfa, o NULL se non si puo'' risolvere. Serve al frontend per l''azione «apri documento sorgente», che vuole area + id. 🔴 La traduzione non e'' banale perche'' la chiave e'' polimorfa per costruzione: con config.sorgenti.key_selector = ''id'' il campo sorgente_uid contiene gia'' l''id in forma testuale, con ''uid'' contiene un UUID e l''id va LETTO sulla target_table. Non e'' un caso di bordo: misurato il 2026-08-16, su vendite.commesse_attivita 44 righe vengono da PREVENTIVO (chiave uid) contro 44 da ordini e DDT (chiave id). ⚠️ NON SOLLEVA, ed e'' la differenza con vendite.fn_link_commessa_sorgente: quella scrive un legame e davanti a una chiave irrisolvibile alza E_SORG_NORM_NON_RISOLTA, perche'' un legame sbagliato e'' peggio di nessun legame; questa risponde a una lista, dove una sorgente non risolta deve solo far sparire l''azione — come per le voci manuali, che un documento a monte non ce l''hanno. ⚠️ SECURITY INVOKER: le tabelle di destinazione hanno la RLS operatori, quindi NULL significa «non risolvibile O non visibile a chi chiede», non «non esiste». Richiesta BE del 2026-08-16, terzo dei tre campi di fn_list_commessa_attivita.';
```

---
{% include-markdown "signature-core.md" %}
