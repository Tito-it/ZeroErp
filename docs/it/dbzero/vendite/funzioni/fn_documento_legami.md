{% include-markdown "it/dbzero/vendite/manual/fn_documento_legami.md" %}
# ⚙️ Funzione `fn_documento_legami`

```sql
CREATE FUNCTION fn_documento_legami(p_documento character varying, p_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_legami(p_documento character varying, p_id bigint)
 RETURNS TABLE(riga_id bigint, riga_nr integer, origine character varying, natura text, origine_id bigint, origine_riga_id bigint, qta numeric)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$

#variable_conflict use_column
-- =========================================================
-- Scopo: i legami di un documento, una riga per legame: che
--   cosa si riapre se lo annullo, e dove. Vedi l'intestazione
--   del changeSet per la tabella dei legami.
-- Parametri: p_documento e' il codice della sorgente del
--   documento (DDT_VENDITA, ORDINE_VENDITA, PREVENTIVO, CONTRATTO,
--   COMMESSA), p_id la testata: polimorfa, tipo nudo.
-- Ritorna: origine e' il codice della sorgente dall'altra parte
--   del legame (config.sorgenti.codice_interno), tranne ONERE:
--   una riga di commessa senza sorgente per progetto, che non ha
--   un documento a monte. natura e' il vocabolario di questa
--   funzione (CONSUMO, PROVENIENZA, ANNULLO); riga_id, riga_nr,
--   origine_id, origine_riga_id e qta sono polimorfi (righe e
--   testate di tabelle diverse): tipi nudi.
-- rev 2026-10-12 (brief-db-annullo-a-valle-riapre-a-monte, D-2,
--   D-7): + COMMESSA, il ramo in fondo all'IF.
-- rev 2026-10-19 (20261019-95, brief-db-grammatica-unica-documenti
--   lotto 2b): origine e' il codice della sorgente (ORDINE ->
--   ORDINE_VENDITA, RESO -> RESO_VENDITA, OFFERTA ->
--   OFFERTA_COMMERCIALE, DDT -> DDT_VENDITA, CONSUMI ->
--   ATTIVITA_CONSUMI), ancorato in RETURNS TABLE; nel ramo della
--   commessa la traduzione dal codice della sorgente non c'e' piu'.
-- =========================================================
DECLARE
    -- La sorgente di commessa del documento e la sua chiave
    -- (commesse_attivita.sorgente_uid porta <testata>.uid::text).
    v_sorgente config.sorgenti.codice_interno%TYPE;
    v_uid      vendite.commesse_attivita.sorgente_uid%TYPE;
BEGIN
    IF p_id IS NULL OR p_id <= 0
       OR p_documento IS NULL
       OR p_documento NOT IN ('DDT_VENDITA', 'ORDINE_VENDITA', 'PREVENTIVO', 'CONTRATTO', 'COMMESSA') THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_documento_legami',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_documento', p_documento, 'p_id', p_id),
            NULL::uuid, 'vendite.fn_documento_legami',
            'documento (DDT_VENDITA, ORDINE_VENDITA, PREVENTIVO, CONTRATTO, COMMESSA) e id maggiore di zero');
    END IF;

    IF p_documento = 'DDT_VENDITA' THEN
        v_sorgente := 'DDT_VENDITA';
        SELECT d.uid::text INTO v_uid FROM vendite.ddt d WHERE d.id = p_id;

        RETURN QUERY
            SELECT dr.id, dr.riga_nr, 'ORDINE_VENDITA'::character varying, 'CONSUMO'::text,
                   orr.ordine_id, f.ordine_riga_id, f.qta_evasa::numeric
              FROM vendite.ddt_righe dr
              JOIN vendite.ordini_righe_fulfillment f ON f.ddt_riga_id = dr.id
              JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
             WHERE dr.ddt_id = p_id
            UNION ALL
            SELECT dr.id, dr.riga_nr, 'RESO_VENDITA'::character varying, 'CONSUMO'::text,
                   r.reso_id, rr.resi_riga_id, rr.qta::numeric
              FROM vendite.ddt_righe dr
              JOIN vendite.resi_righe_riconsegne rr ON rr.ddt_riga_id = dr.id
              JOIN vendite.resi_righe r ON r.id = rr.resi_riga_id
             WHERE dr.ddt_id = p_id;

    ELSIF p_documento = 'ORDINE_VENDITA' THEN
        v_sorgente := 'ORDINE_VENDITA';
        SELECT o.uid::text INTO v_uid FROM vendite.ordini o WHERE o.id = p_id;

        RETURN QUERY
            SELECT orr.id, orr.riga_nr, 'PREVENTIVO'::character varying, 'CONSUMO'::text,
                   pr.preventivo_id, orr.preventivo_riga_id, orr.quantita::numeric
              FROM vendite.ordini_righe orr
              JOIN vendite.preventivi_righe pr ON pr.id = orr.preventivo_riga_id
             WHERE orr.ordine_id = p_id
            UNION ALL
            SELECT NULL::bigint, NULL::integer, 'OFFERTA_COMMERCIALE'::character varying, 'PROVENIENZA'::text,
                   o.documento_origine_id, NULL::bigint, NULL::numeric
              FROM vendite.ordini o
             WHERE o.id = p_id
               AND o.documento_origine_tipo = 'OFFERTA_COMMERCIALE'
               AND o.documento_origine_id IS NOT NULL;

    ELSIF p_documento = 'PREVENTIVO' THEN
        v_sorgente := 'PREVENTIVO';
        SELECT p.uid::text INTO v_uid FROM vendite.preventivi p WHERE p.id = p_id;

    ELSIF p_documento = 'COMMESSA' THEN
        -- ⭐ rev 2026-10-12 (D-1, D-2, D-7 di Tid): la commessa e' a
        --   valle di tutto cio' che la riempie. Un legame per riga
        --   NON_EMESSA (le EMESSA non sono legami: bloccano,
        --   script.fn_check_commessa_annullabile):
        --   - con sorgente: il documento che l'ha spinta (PREVENTIVO,
        --     ORDINE_VENDITA, CONTRATTO, DDT_VENDITA) o il consumo
        --     (ATTIVITA_CONSUMI), col codice della sorgente com'e';
        --     CONSUMO, si riapre: torna da mandare in commessa;
        --   - RETTIFICA (sourceless per progetto): il RESO_VENDITA del
        --     suo accredito; CONSUMO, il reso torna da accreditare;
        --   - ONERE (sourceless): niente a monte; natura ANNULLO, la
        --     riga si annulla con la commessa e la finestra lo dice.
        --   rev 2026-10-12 (20261012-28): una riga senza sorgente e' ONERE
        --   o RETTIFICA per vincolo di tabella
        --   (chk_commesse_attivita_senza_sorgente_onere_rettifica,
        --   20261012-27): il ramo MANUALE non esiste piu'.
        -- riga_id: la riga di commessa; origine_id: il documento (o il
        --   reso) dall'altra parte, dal resolver unico della sorgente
        --   polimorfa (vendite.fn_get_sorgente_documento_ref);
        --   origine_riga_id: la riga di reso dell'accredito.
        RETURN QUERY
            SELECT ca.id,
                   NULL::integer,
                   -- rev 2026-10-19 (lotto 2b): il codice della sorgente
                   -- com'e', senza traduzione; ONERE non e' una sorgente.
                   CASE
                     WHEN ca.sorgente_tipo_id IS NOT NULL THEN s.codice_interno
                     WHEN ca.tipo_movimento = 'RETTIFICA' THEN 'RESO_VENDITA'
                     ELSE 'ONERE'
                   END::character varying,
                   CASE
                     WHEN ca.sorgente_tipo_id IS NULL AND ca.tipo_movimento = 'ONERE'
                       THEN 'ANNULLO'
                     ELSE 'CONSUMO'
                   END::text,
                   CASE
                     WHEN ca.sorgente_tipo_id IS NOT NULL THEN ref.documento_id
                     ELSE acc.reso_id
                   END,
                   acc.resi_riga_id,
                   ca.quantita::numeric
              FROM vendite.commesse_attivita ca
              LEFT JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
              LEFT JOIN LATERAL (
                     SELECT r.documento_id
                       FROM vendite.fn_get_sorgente_documento_ref(
                              ca.sorgente_tipo_id, ca.sorgente_uid) AS r
                      WHERE ca.sorgente_tipo_id IS NOT NULL
                   ) ref ON true
              LEFT JOIN LATERAL (
                     SELECT a.resi_riga_id, rr.reso_id
                       FROM vendite.resi_righe_accrediti a
                       JOIN vendite.resi_righe rr ON rr.id = a.resi_riga_id
                      WHERE a.commessa_attivita_id = ca.id
                        AND ca.tipo_movimento = 'RETTIFICA'
                      ORDER BY a.id
                      LIMIT 1
                   ) acc ON true
             WHERE ca.commessa_id = p_id
               AND ca.stato_emissione = 'NON_EMESSA'
             ORDER BY ca.id;
        RETURN;

    ELSE  -- CONTRATTO
        v_sorgente := 'CONTRATTO';
        SELECT c.uid::text INTO v_uid FROM vendite.contratti c WHERE c.id = p_id;

        RETURN QUERY
            SELECT NULL::bigint, NULL::integer, 'OFFERTA_COMMERCIALE'::character varying, 'PROVENIENZA'::text,
                   c.offerta_id, NULL::bigint, NULL::numeric
              FROM vendite.contratti c
             WHERE c.id = p_id
               AND c.offerta_id IS NOT NULL;
    END IF;

    -- Le righe di commessa che il documento ha spinto e che
    -- nessuno ha ancora emesso: le stesse che il ritiro porta ad
    -- ANNULLATA (vendite.fn_ritira_commessa_attivita_da_sorgente).
    -- Documento inesistente o invisibile: v_uid NULL, nessuna riga.
    RETURN QUERY
        SELECT NULL::bigint, NULL::integer, 'COMMESSA'::character varying, 'CONSUMO'::text,
               ca.commessa_id, ca.id, ca.quantita::numeric
          FROM vendite.commesse_attivita ca
          JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
         WHERE s.codice_interno  = v_sorgente
           AND ca.sorgente_uid   = v_uid
           AND ca.stato_emissione = 'NON_EMESSA'
         ORDER BY ca.id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_legami(p_documento character varying, p_id bigint)
IS 'I legami di un documento, una riga per legame (2026-10-11, brief-db-annullo-documento-con-legami D-4): che cosa si riapre se lo annullo, e dove. p_documento: DDT, ORDINE, PREVENTIVO, CONTRATTO, COMMESSA (codici dei lettori di testata). origine/natura: ORDINE e RESO (consumi della bolla: fulfillment e ponte di ri-consegna), PREVENTIVO (consumo dell''ordine: ordini_righe.preventivo_riga_id), OFFERTA (PROVENIENZA di ordine e contratto: resta sul documento annullato, l''offerta torna trasformabile perche'' l''unicita'' vale sui vivi), COMMESSA (righe di commessa NON_EMESSA spinte dal documento). Le righe EMESSA non sono legami: bloccano (script.fn_check_sorgente_chiudibile). riga_id/riga_nr: la riga del documento, NULL per testata e commessa; origine_id: la testata (o la commessa) dall''altra parte; origine_riga_id: la sua riga. Niente etichette: il nome lo da'' il lineage. Lettore unico di: guard vendite.trgfn_doc_guard_annullo_con_legami (avviso), BB vendite.fn_documento_ritira_legami (conferma e ritiro), finestra di conferma del backend. Generalizza e sostituisce vendite.fn_ddt_legami. Documento sconosciuto: E_VENDITE_CHIAMATA_NON_VALIDA. SECURITY DEFINER con search_path bloccato: avviso (guard, come l''app), conferma (verbo DEFINER) e finestra (backend) contano la stessa cosa anche dove la RLS dei legami ne nasconderebbe una parte. EXECUTE solo all''app. ⭐ rev 2026-10-12 (brief-db-annullo-a-valle-riapre-a-monte, D-1/D-2/D-7 di Tid): + COMMESSA, a valle di tutto cio'' che la riempie. Un legame per riga NON_EMESSA della commessa (riga_id = la riga di commessa): con sorgente, il documento che l''ha spinta (PREVENTIVO, ORDINE, CONTRATTO, DDT) o il consumo (CONSUMI), natura CONSUMO, torna da mandare; RETTIFICA (sourceless), il RESO del suo accredito (origine_riga_id = la riga di reso), natura CONSUMO, il reso torna da accreditare; ONERE (sourceless), natura ANNULLO: niente a monte, la riga si annulla con la commessa. origine_id dal resolver unico della sorgente polimorfa (vendite.fn_get_sorgente_documento_ref). Le righe EMESSA non sono legami: bloccano (script.fn_check_commessa_annullabile). rev 2026-10-12 (20261012-28): via il ramo MANUALE. Una riga senza sorgente e'' ONERE o RETTIFICA per vincolo di tabella (chk_commesse_attivita_senza_sorgente_onere_rettifica, 20261012-27, decisione di Tid): prima lo garantiva solo la disciplina di chi scrive, e una NORMALE senza sorgente rendeva la commessa non annullabile. ⭐ rev 2026-10-19 (20261019-51, brief-db-grammatica-unica-documenti lotto 2a, G-1 di Tid): la grammatica delle testate passa ai codici delle sorgenti (DDT -> DDT_VENDITA, ORDINE -> ORDINE_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE, RESO -> RESO_VENDITA, EMAIL_BOZZA -> EMAIL; PREVENTIVO, CONTRATTO, COMMESSA, FATTURA invariati); dove sopra si legge un codice corto come selettore, oggi vale il codice della sorgente. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato). La colonna origine resta nel vocabolario V7 fino al 2b. ⭐ rev 2026-10-19 (20261019-95, brief-db-grammatica-unica-documenti lotto 2b, G-1 e G-3 di Tid): origine e'' il codice della sorgente dall''altra parte del legame (ORDINE -> ORDINE_VENDITA, RESO -> RESO_VENDITA, OFFERTA -> OFFERTA_COMMERCIALE; nel ramo della commessa DDT -> DDT_VENDITA, CONSUMI -> ATTIVITA_CONSUMI), ancorato a config.sorgenti.codice_interno%TYPE nel RETURNS TABLE: il tipo passa da text a character varying (DROP + CREATE). Resta fuori dalle sorgenti solo ONERE, la riga di commessa senza sorgente per progetto. Dove sopra si legge un codice corto di origine, oggi vale il codice della sorgente.';
```

---
{% include-markdown "signature-core.md" %}
