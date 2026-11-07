# ⚙️ Funzione `fn_pgtap_consumo_della_commessa`

```sql
CREATE FUNCTION fn_pgtap_consumo_della_commessa(p_commessa_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_consumo_della_commessa(p_commessa_id bigint)
 RETURNS TABLE(consumo_id bigint, consumo_uid uuid, sorgente_tipo_id bigint, segment_key character varying)
 LANGUAGE plpgsql
AS $function$
-- Scopo: il consumo di prova di una commessa, lo stesso a ogni chiamata: lo
--   trova (meta pgtap_commessa_id) o lo crea sul billing account della
--   commessa (dbops.fn_pgtap_crea_consumo). Per i test che scrivono piu'
--   righe di commessa con la madre: una provenienza sola, un link solo, e la
--   chiave del push estesa col suffisso ':<etichetta>' per ogni riga.
-- Uso:
--   p_sorgente_tipo_id => (SELECT x.sorgente_tipo_id FROM dbops.fn_pgtap_consumo_della_commessa(c) x),
--   p_sorgente_uid     => (SELECT x.consumo_id::text FROM dbops.fn_pgtap_consumo_della_commessa(c) x),
--   p_segment_key      => (SELECT x.segment_key FROM dbops.fn_pgtap_consumo_della_commessa(c) x) || ':A1'
-- ⚠️ VOLATILE: ogni istruzione interna vede il consumo scritto da una
--   chiamata precedente della stessa istruzione.
DECLARE
    v_ba vendite.commesse.billing_account_id%TYPE;
BEGIN
    RETURN QUERY
    SELECT ac.id, ac.uid, s.id, script.fn_segment_key('ATTIVITA_CONSUMI', ac.uid::text)
      FROM vendite.attivita_consumi ac
      JOIN config.sorgenti s ON s.codice_interno = 'ATTIVITA_CONSUMI'
     WHERE ac.meta @> jsonb_build_object('pgtap_commessa_id', p_commessa_id)
     ORDER BY ac.id
     LIMIT 1;
    IF FOUND THEN
        RETURN;
    END IF;

    SELECT c.billing_account_id INTO v_ba
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;
    IF v_ba IS NULL THEN
        RAISE EXCEPTION 'fn_pgtap_consumo_della_commessa: nessuna commessa con id = %', p_commessa_id;
    END IF;

    RETURN QUERY
    SELECT c.* FROM dbops.fn_pgtap_crea_consumo(
        v_ba, NULL, jsonb_build_object('pgtap_commessa_id', p_commessa_id)) c;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_consumo_della_commessa(p_commessa_id bigint)
IS 'Fixture pgTAP: il consumo di prova di una commessa, lo stesso a ogni chiamata: lo trova (meta pgtap_commessa_id) o lo crea sul billing account della commessa (dbops.fn_pgtap_crea_consumo). Restituisce id e uid del consumo, il tipo della provenienza (ATTIVITA_CONSUMI) e la chiave del push del consumo, che il test estende col suffisso :<etichetta> (cosi'' ogni riga ha la sua base) per scrivere piu'' righe di commessa dalla stessa provenienza (un link solo alla commessa). Una commessa che non esiste parla.';
```

</div>

---
{% include-markdown "signature-core.md" %}
