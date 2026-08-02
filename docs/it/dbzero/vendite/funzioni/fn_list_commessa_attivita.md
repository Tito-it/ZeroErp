{% include-markdown "it/dbzero/vendite/manual/fn_list_commessa_attivita.md" %}
# ⚙️ Funzione `fn_list_commessa_attivita`

```sql
CREATE FUNCTION fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying DEFAULT NULL::character varying, p_stato_approvazione character varying DEFAULT NULL::character varying, p_competenza_mese date DEFAULT NULL::date, p_limit integer DEFAULT 1000, p_offset integer DEFAULT 0, p_order_by text DEFAULT NULL::text, p_order_dir text DEFAULT 'asc'::text)
 RETURNS TABLE(id bigint, commessa_id bigint, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, competenza_mese date, competenza_dal date, competenza_al date, prezzo_snapshot numeric, prezzo_bloccato boolean, prezzo_da_riallineare boolean, stato_approvazione character varying, stato_emissione character varying, sorgente_tipo_id bigint, sorgente_codice character varying, meta jsonb, data_update timestamp with time zone, fatturata boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_competenza_mese vendite.commesse_attivita.competenza_mese%TYPE;
    v_order_col       text;
    v_order_dir       text;
BEGIN
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id), NULL::uuid, 'p_commessa_id obbligatorio e > 0');
    END IF;

    -- ⚠️ La whitelist si valida PRIMA di andare a cercare la
    -- commessa: un parametro sbagliato non deve costare una query
    -- per essere respinto. Stessa scelta fatta dal BE sulla coda
    -- approvazioni, dove la validazione precede la risoluzione
    -- utente/emittente.
    -- Whitelist di ordinamento: mappa CHIUSA nome -> espressione.
    -- Le chiavi sono i `campo_sorgente` che il seed manda dal FE
    -- (<ListaConfigurabile> monta le Column su campo_sorgente).
    -- NULL/vuoto = ordine storico `ca.id`: le chiamate che non
    -- chiedono niente ottengono esattamente quello di prima.
    v_order_col := CASE lower(btrim(COALESCE(p_order_by, '')))
        WHEN ''                   THEN 'ca.id'
        WHEN 'id'                 THEN 'ca.id'
        WHEN 'data_attivita'      THEN 'ca.data_attivita'
        WHEN 'competenza_mese'    THEN 'ca.competenza_mese'
        WHEN 'segment_key'        THEN 'ca.segment_key'
        WHEN 'quantita'           THEN 'ca.quantita'
        WHEN 'prezzo_snapshot'    THEN 'ca.prezzo_snapshot'
        WHEN 'stato_approvazione' THEN 'ca.stato_approvazione'
        WHEN 'stato_emissione'    THEN 'ca.stato_emissione'
        ELSE NULL
    END;

    -- Fail-loud: un nome fuori whitelist NON ripiega sul default.
    -- Un ripiego silenzioso e' la «freccia che non ordina»: a video
    -- sembra funzionare e restituisce un ordine che nessuno ha chiesto.
    IF v_order_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_order_by', 'valore', p_order_by),
            NULL::uuid, concat('p_order_by non ammesso: ', p_order_by));
    END IF;

    v_order_dir := CASE WHEN lower(btrim(COALESCE(p_order_dir, 'asc'))) = 'desc'
                        THEN 'DESC' ELSE 'ASC' END;

    IF NOT EXISTS (SELECT 1 FROM vendite.commesse c WHERE c.id = p_commessa_id) THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_VALORE_MANCANTE',
            jsonb_build_object('commessa_id', p_commessa_id), NULL::uuid, concat('commessa_id ', p_commessa_id));
    END IF;

    -- Sanitize limit/offset
    IF p_limit IS NULL OR p_limit <= 0 THEN p_limit := 1000; END IF;
    IF p_limit > 10000 THEN p_limit := 10000; END IF;
    IF p_offset IS NULL OR p_offset < 0 THEN p_offset := 0; END IF;

    v_competenza_mese := CASE WHEN p_competenza_mese IS NOT NULL
        THEN date_trunc('month', p_competenza_mese)::DATE ELSE NULL END;

    -- SQL dinamico solo per l'ORDER BY (non parametrizzabile).
    -- L'espressione viene dal CASE chiuso qui sopra, MAI dal
    -- parametro: i valori restano parametri veri (USING).
    -- Tiebreak ca.id: senza, righe con la stessa chiave possono
    -- scambiarsi fra una pagina e l'altra.
    RETURN QUERY EXECUTE format($q$
        SELECT ca.id, ca.commessa_id, ca.segment_key, ca.articolo_id, ca.istanza_utility_id,
               ca.data_attivita, ca.uom_id, ca.quantita, ca.competenza_mese, ca.competenza_dal,
               ca.competenza_al, ca.prezzo_snapshot, ca.prezzo_bloccato, ca.prezzo_da_riallineare,
               ca.stato_approvazione, ca.stato_emissione, ca.sorgente_tipo_id,
               s.codice AS sorgente_codice, ca.meta, ca.data_update,
               -- fatturata: specchio del guard BE _assert_non_fatturata.
               EXISTS (
                   SELECT 1 FROM vendite.attivita_fatturabili af
                    WHERE af.commessa_attivita_id = ca.id
                      AND af.fattura_riga_id IS NOT NULL
               ) AS fatturata
          FROM vendite.commesse_attivita ca
          LEFT JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
         WHERE ca.commessa_id = $1
           AND ($2 IS NULL OR ca.stato_emissione = $2)
           AND ($3 IS NULL OR ca.stato_approvazione = $3)
           AND ($4 IS NULL OR ca.competenza_mese = $4)
         ORDER BY %s %s, ca.id
         LIMIT $5 OFFSET $6
    $q$, v_order_col, v_order_dir)
    USING p_commessa_id, p_stato_emissione, p_stato_approvazione,
          v_competenza_mese, p_limit, p_offset;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer, p_order_by text, p_order_dir text)
IS 'Read-only: righe commesse_attivita con filtri opzionali, paginazione e ORDINAMENTO. JOIN sorgenti per codice. rev 2026-07-24: colonna fatturata BOOLEAN = EXISTS di un''attivita_fatturabili della riga con fattura_riga_id valorizzato -- specchio esatto del guard BE commesse_service._assert_non_fatturata. rev 2026-08-02 (7o lotto liste configurabili, consegna 2 del BE): p_order_by/p_order_dir con whitelist CHIUSA di 7 colonne + tiebreak ca.id; ordine e paginazione vivono qui, quindi ordinare a valle ordinerebbe la sola pagina estratta. p_order_by NULL = ordine storico ca.id: nessuna chiamata esistente cambia risultato. Un nome fuori whitelist solleva E_PARAMETRO_INVALIDO invece di ripiegare in silenzio. STABLE preservato.';
```

---
{% include-markdown "signature-core.md" %}
