{% include-markdown "it/dbzero/vendite/manual/fn_list_commessa_attivita.md" %}
# ⚙️ Funzione `fn_list_commessa_attivita`

```sql
CREATE FUNCTION fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying DEFAULT NULL::character varying, p_stato_approvazione character varying DEFAULT NULL::character varying, p_competenza_mese date DEFAULT NULL::date, p_limit integer DEFAULT 1000, p_offset integer DEFAULT 0)
 RETURNS TABLE(id bigint, commessa_id bigint, segment_key character varying, articolo_id uuid, istanza_utility_id bigint, data_attivita date, uom_id bigint, quantita numeric, competenza_mese date, competenza_dal date, competenza_al date, prezzo_snapshot numeric, prezzo_bloccato boolean, prezzo_da_riallineare boolean, stato_approvazione character varying, stato_emissione character varying, sorgente_tipo_id bigint, sorgente_codice character varying, meta jsonb, data_update timestamp with time zone, fatturata boolean)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_competenza_mese vendite.commesse_attivita.competenza_mese%TYPE;
BEGIN
    IF p_commessa_id IS NULL OR p_commessa_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_list_commessa_attivita', 'E_PARAMETRO_INVALIDO',
            jsonb_build_object('parametro', 'p_commessa_id', 'valore', p_commessa_id), NULL::uuid, 'p_commessa_id obbligatorio e > 0');
    END IF;

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

    RETURN QUERY
    SELECT ca.id, ca.commessa_id, ca.segment_key, ca.articolo_id, ca.istanza_utility_id,
           ca.data_attivita, ca.uom_id, ca.quantita, ca.competenza_mese, ca.competenza_dal,
           ca.competenza_al, ca.prezzo_snapshot, ca.prezzo_bloccato, ca.prezzo_da_riallineare,
           ca.stato_approvazione, ca.stato_emissione, ca.sorgente_tipo_id,
           s.codice AS sorgente_codice, ca.meta, ca.data_update,
           -- fatturata: specchio del guard BE _assert_non_fatturata.
           -- true = esiste (0/1, per la UNIQUE 1:1) un'AF della riga
           -- con fattura_riga_id valorizzato -> il BE rifiutera' ogni
           -- azione prezzo. Coperto da ix_attivita_fatturabili_commessa_attivita_id.
           EXISTS (
               SELECT 1 FROM vendite.attivita_fatturabili af
                WHERE af.commessa_attivita_id = ca.id
                  AND af.fattura_riga_id IS NOT NULL
           ) AS fatturata
      FROM vendite.commesse_attivita ca
      LEFT JOIN config.sorgenti s ON s.id = ca.sorgente_tipo_id
     WHERE ca.commessa_id = p_commessa_id
       AND (p_stato_emissione IS NULL OR ca.stato_emissione = p_stato_emissione)
       AND (p_stato_approvazione IS NULL OR ca.stato_approvazione = p_stato_approvazione)
       AND (v_competenza_mese IS NULL OR ca.competenza_mese = v_competenza_mese)
     ORDER BY ca.id LIMIT p_limit OFFSET p_offset;
END;
$function$

COMMENT ON FUNCTION vendite.fn_list_commessa_attivita(p_commessa_id bigint, p_stato_emissione character varying, p_stato_approvazione character varying, p_competenza_mese date, p_limit integer, p_offset integer)
IS 'Read-only: righe commesse_attivita con filtri opzionali e paginazione. JOIN sorgenti per codice. rev 2026-07-24 (brief-db-flag-fatturata-lista-attivita): + colonna fatturata BOOLEAN = EXISTS di un''attivita_fatturabili della riga con fattura_riga_id valorizzato -- specchio esatto del guard BE commesse_service._assert_non_fatturata, per il gate UI delle azioni prezzo. NON usa la colonna denormalizzata attivita_fatturabili.fatturato: specchia la FK che il guard legge. CA<->AF e'' 1:1 (uq_attivita_fatturabili_commessa_attivita). STABLE preservato.';
```

---
{% include-markdown "signature-core.md" %}
