# ⚙️ Funzione `fn_pgtap_crea_consumo`

```sql
CREATE FUNCTION fn_pgtap_crea_consumo(p_billing_account_id bigint, p_competenza_mese date, p_meta jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_consumo(p_billing_account_id bigint, p_competenza_mese date DEFAULT NULL::date, p_meta jsonb DEFAULT NULL::jsonb)
 RETURNS TABLE(consumo_id bigint, consumo_uid uuid, sorgente_tipo_id bigint, segment_key character varying)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un documento d'origine vero per una riga
--   di commessa, il piu' leggero che il modello ammette: un consumo
--   (vendite.attivita_consumi), che non ha righe. Lo scrive il test come
--   lo scriverebbe il calcolo dei consumi: billing account e mese (di
--   default quello corrente). Restituisce anche il tipo della provenienza
--   (ATTIVITA_CONSUMI) e la chiave del push che il push dei consumi
--   comporrebbe (script.fn_segment_key): un test che scrive piu' righe
--   dallo stesso consumo la estende col suffisso ':<etichetta>'.
-- Uso:
--   CREATE TEMP TABLE _src AS SELECT * FROM dbops.fn_pgtap_crea_consumo(<ba>);
--   ... p_sorgente_tipo_id => (SELECT sorgente_tipo_id FROM _src),
--       p_sorgente_uid     => (SELECT consumo_id::text FROM _src),
--       p_segment_key      => (SELECT segment_key FROM _src) || ':A' ...
-- ⚠️ Sotto la RLS il billing account deve stare nel perimetro di chi
--   agisce (lo stesso della commessa della fixture).
-- ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.
DECLARE
    v_id   vendite.attivita_consumi.id%TYPE;
    v_uid  vendite.attivita_consumi.uid%TYPE;
    v_tipo vendite.commesse_attivita.sorgente_tipo_id%TYPE;
BEGIN
    IF p_billing_account_id IS NULL OR p_billing_account_id <= 0 THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_consumo: serve il billing account (> 0), ricevuto %',
            p_billing_account_id;
    END IF;

    SELECT s.id INTO v_tipo
      FROM config.sorgenti s
     WHERE s.codice_interno = 'ATTIVITA_CONSUMI' AND s.attivo;

    INSERT INTO vendite.attivita_consumi (billing_account_id, competenza_mese, meta)
    VALUES (p_billing_account_id,
            date_trunc('month', COALESCE(p_competenza_mese, (SELECT script.fn_data_operativa())))::date,
            jsonb_build_object('test_scope', 'pgtap_consumo') || COALESCE(p_meta, '{}'::jsonb))
    RETURNING id, uid INTO v_id, v_uid;

    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_id, v_uid, v_tipo, script.fn_segment_key('ATTIVITA_CONSUMI', v_uid::text);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_consumo(p_billing_account_id bigint, p_competenza_mese date, p_meta jsonb)
IS 'Fixture pgTAP: un consumo (vendite.attivita_consumi) sul billing account dato, nel mese dato o in quello corrente, con meta test_scope = pgtap_consumo; restituisce anche il tipo della provenienza (ATTIVITA_CONSUMI) e la chiave del push che il push dei consumi comporrebbe (script.fn_segment_key), che un test estende col suffisso :<etichetta> (cosi'' ogni riga ha la sua base) per scrivere piu'' righe dallo stesso consumo. E'' il documento d''origine piu'' leggero che il modello ammette per una riga di commessa: non ha righe, quindi la provenienza e'' il documento intero (tipo ATTIVITA_CONSUMI, l''id in sorgente_id). Lo usa dbops.fn_pgtap_crea_commessa_attivita quando il test non dichiara una sorgente. Sotto la RLS il billing account deve stare nel perimetro di chi agisce. Un billing account mancante o <= 0 parla. Esce con i vincoli IMMEDIATE.';
```

</div>

---
{% include-markdown "signature-core.md" %}
