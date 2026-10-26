{% include-markdown "it/dbzero/vendite/manual/fn_build_gruppo_fatturabile_key.md" %}
# ⚙️ Funzione `fn_build_gruppo_fatturabile_key`

```sql
CREATE FUNCTION fn_build_gruppo_fatturabile_key(p_sorgente_tipo_id bigint, p_sorgente_uid text, p_commessa_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_build_gruppo_fatturabile_key(p_sorgente_tipo_id bigint, p_sorgente_uid text, p_commessa_id bigint)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: costruire la chiave del GRUPPO FATTURABILE di una riga di
--        commessa. Due forme, secondo la natura della riga:
--          riga con documento sorgente -> '<codice_interno>:<uid>'
--          riga sourceless (oneri)     -> 'MAN:<commessa_id>'
-- E' l'unica fonte di verita' della chiave: la usano l'elenco dei
-- gruppi (vw_dash_competenza_gruppi) e tutti i filtri di emissione
-- mirata. Se la forma cambiasse qui, cambierebbe ovunque insieme.
-- brief-db-emissione-fattura-per-documento-sorgente A1 / D-1 / D-9.
DECLARE
    v_uid             vendite.commesse_attivita.sorgente_uid%TYPE;
    v_codice_interno  config.sorgenti.codice_interno%TYPE;
BEGIN
    -- Guard parametri ID: errore esplicito, mai normalizzazione
    -- silenziosa (linee-guida-sql: "se NULL o <= 0 -> errore").
    IF p_sorgente_tipo_id IS NOT NULL AND p_sorgente_tipo_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_gruppo_fatturabile_key', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_sorgente_tipo_id', 'valore', p_sorgente_tipo_id),
            NULL::uuid, 'p_sorgente_tipo_id se fornito deve essere > 0'
        );
    END IF;

    IF p_commessa_id IS NOT NULL AND p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_gruppo_fatturabile_key', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id),
            NULL::uuid, 'p_commessa_id se fornito deve essere > 0'
        );
    END IF;

    v_uid := NULLIF(btrim(COALESCE(p_sorgente_uid, '')), '');

    -- ============================================
    -- CASO 1: riga SOURCELESS -> gruppo "oneri di commessa"
    -- ============================================
    -- Il CHECK chk_commesse_attivita_sorgente_pair impone che la
    -- coppia (sorgente_tipo_id, sorgente_uid) sia tutta NULL o
    -- tutta valorizzata: sourceless = entrambe NULL.
    IF p_sorgente_tipo_id IS NULL AND v_uid IS NULL THEN
        IF p_commessa_id IS NULL THEN
            -- Senza documento E senza commessa la riga non ha
            -- alcun contenitore: non e' un gruppo, e' un errore.
            PERFORM script.fn_log_and_raise_error(
                'vendite', 'fn_build_gruppo_fatturabile_key', 'E_PARAMETRO_INVALIDO',
                jsonb_build_object('parametro', 'p_commessa_id', 'valore', NULL),
                NULL::uuid,
                'riga sourceless: p_commessa_id obbligatorio (e'' il suo unico contenitore)'
            );
        END IF;

        -- Prefisso MAN: allineato alla convenzione della porta
        -- oneri (segment_key 'MAN:<commessa>:<n>'), ma qui la
        -- chiave si ferma alla commessa: tutti gli oneri di una
        -- commessa sono UN gruppo solo, non uno per riga.
        RETURN 'MAN:' || p_commessa_id::text;
    END IF;

    -- ============================================
    -- CASO 2: coppia incoerente -> fail-loud
    -- ============================================
    -- Non dovrebbe accadere (lo impedisce il CHECK sulla tabella),
    -- ma la funzione e' chiamabile con valori arbitrari: meglio
    -- rumore che una chiave inventata che poi non risolve.
    IF p_sorgente_tipo_id IS NULL OR v_uid IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_gruppo_fatturabile_key', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id,
                               'sorgente_uid', p_sorgente_uid),
            NULL::uuid,
            'coppia sorgente incoerente: attesi entrambi NULL (riga sourceless) o entrambi valorizzati'
        );
    END IF;

    -- ============================================
    -- CASO 3: riga con documento sorgente
    -- ============================================
    -- codice_interno (immutabile), MAI codice (etichetta
    -- modificabile) — linee-guida-sql §6c/§6d.
    -- Nessun filtro su attivo: una riga di commessa nata da una
    -- sorgente poi disattivata appartiene comunque al suo gruppo,
    -- e deve restare fatturabile.
    SELECT s.codice_interno
      INTO v_codice_interno
      FROM config.sorgenti s
     WHERE s.id = p_sorgente_tipo_id
     LIMIT 1;

    IF v_codice_interno IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_build_gruppo_fatturabile_key', 'E_CODICE',
            jsonb_build_object('sorgente_tipo_id', p_sorgente_tipo_id),
            NULL::uuid, p_sorgente_tipo_id::text, 'config.sorgenti'
        );
    END IF;

    -- v_uid e' l'UID del documento (D-9): e' la forma presente in
    -- commesse_attivita, NON la chiave canonica di
    -- commesse_sorgenti. Vedi header del changeSet.
    RETURN v_codice_interno || ':' || v_uid;
END;
$function$

COMMENT ON FUNCTION vendite.fn_build_gruppo_fatturabile_key(p_sorgente_tipo_id bigint, p_sorgente_uid text, p_commessa_id bigint)
IS 'Unica fonte di verita'' della chiave di GRUPPO FATTURABILE di una riga vendite.commesse_attivita. Due forme: riga con documento sorgente -> ''<codice_interno_sorgente>:<sorgente_uid>''; riga sourceless (oneri della porta manuale, sorgente_* NULL) -> ''MAN:<commessa_id>'' (tutti gli oneri di una commessa sono UN gruppo). Prefisso da codice_interno (immutabile), mai da codice. ⚠️ L''identificativo del documento e'' l''UID, perche'' e'' cio'' che commesse_attivita.sorgente_uid contiene per TUTTE le sorgenti, anche quelle con config.sorgenti.key_selector=''id'': NON allineare a commesse_sorgenti, che e'' normalizzata da fn_link_commessa_sorgente e per lo stesso documento contiene un valore diverso (decisione D-9; guida /guide/sorgente-polimorfa §4a). La chiave non esce mai dal perimetro di commesse_attivita: la produce vw_dash_competenza_gruppi e la consumano i filtri p_gruppi dell''emissione mirata. Non derivarla da segment_key. STABLE (lookup su config.sorgenti). Guard: ID <= 0, riga sourceless senza commessa, coppia sorgente incoerente. brief-db-emissione-fattura-per-documento-sorgente A1, rev 2026-07-27.';
```

</div>

---
{% include-markdown "signature-core.md" %}
