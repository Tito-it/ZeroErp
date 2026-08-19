{% include-markdown "it/dbzero/script/manual/fn_check_ddt_emittibile.md" %}
# ⚙️ Funzione `fn_check_ddt_emittibile`

```sql
CREATE FUNCTION fn_check_ddt_emittibile(p_ddt vendite.ddt)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_ddt_emittibile(p_ddt vendite.ddt)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: elencare i motivi che impediscono l'emissione (EMESSO) di
--   un DDT. Funzione PURA (fn_check_*): non solleva, non scrive.
--   Consumatori: i 4 guard trigger di emissione (sollevano il
--   proprio codice) e script.fn_available_actions_ddt (espone
--   l'azione disabled + reason). Brief:
--   brief-db-guard-righe-avanzamento-stato §1a-bis (Rev 2).
-- Ritorna: [] se emittibile; altrimenti array ordinato di
--   {codice, reason, reason_key, dettaglio}.
DECLARE
    v_motivi      jsonb := '[]'::jsonb;
    v_fatturabile boolean;
    v_riga_senza  vendite.ddt_righe.id%TYPE;
    v_presenti    integer[];
    v_mancanti    text[];
BEGIN
    -- 1. STRUTTURA — zero righe attive = niente da trasportare (543).
    --    Il "DDT di solo trasporto" resta legittimo: quello e' righe
    --    SENZA PREZZO, non zero righe.
    IF NOT EXISTS (
        SELECT 1 FROM vendite.ddt_righe dr
         WHERE dr.ddt_id = p_ddt.id
           AND dr.attivo IS TRUE
    ) THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_DDT_EMISSIONE_SENZA_RIGHE',
            'reason',     'DOCUMENTO_SENZA_RIGHE',
            'reason_key', 'common.azione_reason.senza_righe',
            'dettaglio',  NULL);
    END IF;

    -- 2. INTENTO — la causale dichiara se la merce che viaggia e'
    --    una vendita da fatturare o solo un trasporto (544, DL-28).
    --    In bozza il NULL resta legittimo: il vincolo e' qui, non
    --    sul salvataggio.
    IF p_ddt.causale_trasporto_id IS NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_DDT_CAUSALE_OBBLIGATORIA',
            'reason',     'CAUSALE_MANCANTE',
            'reason_key', 'vendite.ddt.azione_reason.causale_mancante',
            'dettaglio',  NULL);
    ELSE
        -- 3. DATI RIGA — causale fatturabile => ogni riga attiva deve
        --    avere prezzo RISOLVIBILE: proprio o ereditato dalla riga
        --    d'ordine via fulfillment (545). Stessa COALESCE del
        --    lister. NB: vw_ddt_righe_iva_base NON e' riusabile qui
        --    (filtra prezzo_unitario IS NOT NULL, perderebbe proprio
        --    le righe da esaminare).
        SELECT ct.fatturabile INTO v_fatturabile
          FROM config.causali_trasporto ct
         WHERE ct.id = p_ddt.causale_trasporto_id;

        IF COALESCE(v_fatturabile, false) THEN
            SELECT dr.id INTO v_riga_senza
              FROM vendite.ddt_righe dr
              LEFT JOIN LATERAL (
                  SELECT or_r.prezzo_unitario
                    FROM vendite.ordini_righe_fulfillment ful
                    JOIN vendite.ordini_righe or_r ON or_r.id = ful.ordine_riga_id
                   WHERE ful.ddt_riga_id = dr.id
                   ORDER BY ful.id LIMIT 1
              ) src ON TRUE
             WHERE dr.ddt_id = p_ddt.id
               AND dr.attivo IS TRUE
               AND COALESCE(dr.prezzo_unitario, src.prezzo_unitario) IS NULL
             ORDER BY dr.id
             LIMIT 1;

            IF v_riga_senza IS NOT NULL THEN
                v_motivi := v_motivi || jsonb_build_object(
                    'codice',     'E_DDT_PREZZO_NON_RISOLVIBILE',
                    'reason',     'PREZZO_NON_RISOLVIBILE',
                    'reason_key', 'vendite.ddt.azione_reason.prezzo_non_risolvibile',
                    'dettaglio',  jsonb_build_object('riga_id', v_riga_senza));
            END IF;
        END IF;
    END IF;

    -- 4. TESTATA — indirizzi marcati obbligatori per l'ambito DDT.
    SELECT array_agg(di.tipo_indirizzo_id) INTO v_presenti
      FROM vendite.ddt_indirizzi di
     WHERE di.ddt_id = p_ddt.id;

    v_mancanti := script.fn_indirizzi_obbligatori_mancanti('DDT', v_presenti);

    IF array_length(v_mancanti, 1) IS NOT NULL THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_INDIRIZZO_DOC_OBBLIGATORIO',
            'reason',     'INDIRIZZI_MANCANTI',
            'reason_key', 'common.azione_reason.indirizzi_mancanti',
            'dettaglio',  jsonb_build_object('mancanti', to_jsonb(v_mancanti)));
    END IF;

    -- 5. COMPONENTI BoM CASO A — ma solo se il documento VENDE.
    --
    -- ⛔ La condizione e' nuova (2026-08-19, slice C del brief righe DDT senza
    --   prezzo) e senza di essa il kit in conto visione resterebbe bloccato
    --   proprio adesso che il resto della slice lo ha reso possibile:
    --   vendite.ddt_righe_componenti.prezzo_unitario e' diventato facoltativo
    --   (20260819-13), quindi il secondo controllo qui sotto — che fino a ieri
    --   era IRRAGGIUNGIBILE, perche' la colonna era NOT NULL su tutte e quattro
    --   le tabelle gemelle — da oggi scatta davvero. Se non lo si condiziona,
    --   ferma all'emissione ogni DDT con un kit non valorizzato, compresi
    --   quelli che non si fatturano.
    --
    -- ⭐ E' la stessa regola del punto 3, applicata un livello piu' sotto:
    --   padre e figli obbediscono alla stessa dichiarazione, la causale. Un
    --   prezzo in attesa di approvazione o non ancora messo non ha nulla da
    --   dire su un documento che non produce valore.
    --
    -- ⚠️ v_fatturabile e' valorizzato dal punto 2 e resta NULL quando la
    --   causale manca: in quel caso l'emissione e' gia' bloccata da
    --   E_DDT_CAUSALE_OBBLIGATORIA e questi due controlli non aggiungono nulla.
    IF COALESCE(v_fatturabile, false) THEN
        -- 5. COMPONENTI BoM CASO A — prezzo in attesa di approvazione...
        IF EXISTS (
            SELECT 1 FROM vendite.ddt_righe dr
              JOIN vendite.ddt_righe_componenti drc ON drc.riga_ddt_id = dr.id
             WHERE dr.ddt_id = p_ddt.id
               AND drc.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
        ) THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_COMPONENTE_PREZZO_PENDENTE',
                'reason',     'COMPONENTI_PREZZO_PENDENTE',
                'reason_key', 'vendite.ddt.azione_reason.componenti_prezzo_pendente',
                'dettaglio',  NULL);
        END IF;

        -- ...oppure non ancora valorizzato.
        IF EXISTS (
            SELECT 1 FROM vendite.ddt_righe dr
              JOIN vendite.ddt_righe_componenti drc ON drc.riga_ddt_id = dr.id
             WHERE dr.ddt_id = p_ddt.id
               AND drc.attivo = TRUE
               AND drc.prezzo_unitario IS NULL
        ) THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',     'E_DOC_COMPONENTI_PENDING_VALORIZZAZIONE',
                'reason',     'COMPONENTI_NON_VALORIZZATI',
                'reason_key', 'vendite.ddt.azione_reason.componenti_non_valorizzati',
                'dettaglio',  NULL);
        END IF;
    END IF;

    RETURN v_motivi;
END;

$function$

COMMENT ON FUNCTION script.fn_check_ddt_emittibile(p_ddt vendite.ddt)
IS 'Single source dei motivi che impediscono l''emissione (EMESSO) di un DDT: righe attive (543), causale (544), prezzo risolvibile se causale fatturabile (545), indirizzi obbligatori, componenti BoM CASO A pendenti/non valorizzati. Ritorna [] se emittibile, altrimenti array ORDINATO di {codice, reason, reason_key, dettaglio}. PURA: non solleva. rev 2026-08-19: i due motivi sui COMPONENTI si valutano solo se la causale e'' fatturabile, come gia'' faceva il motivo sulle righe. Prima erano incondizionati, ma il controllo «non valorizzati» era irraggiungibile (colonna NOT NULL); reso facoltativo il prezzo dei componenti DDT (20260819-13) e'' tornato vivo, e senza la condizione avrebbe bloccato all''emissione i kit sui documenti che non si fatturano — cioe'' proprio quelli che la slice rende possibili. Brief: brief-ddt-righe-senza-prezzo §9 slice C (C4).';
```

---
{% include-markdown "signature-core.md" %}
