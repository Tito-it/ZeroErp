# ⚙️ Funzione `fn_pgtap_crea_pdp`

```sql
CREATE FUNCTION fn_pgtap_crea_pdp(p_utility_codice character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_pdp(p_utility_codice character varying DEFAULT 'GAS'::character varying)
 RETURNS TABLE(pdp_id bigint, pdp_codice character varying, utility_id bigint, indirizzo_dettaglio_id bigint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un PUNTO DI PRELIEVO nuovo, su un
--   indirizzo suo, per l'utility scelta. anagrafiche.pdp e' dato di
--   MACCHINA: da zero e' vuota.
-- Uso:
--   CREATE TEMP TABLE tmp_pdp AS SELECT * FROM dbops.fn_pgtap_crea_pdp();
--   CREATE TEMP TABLE tmp_pdp AS SELECT * FROM dbops.fn_pgtap_crea_pdp('ENERGIA');
-- ⛔ Cliente e istanza sul PDP NON li scrive: sono il caso del test.
DECLARE
    v_utility anagrafiche.pdp.utility_id%TYPE;
    v_n       bigint;
    v_ind     anagrafiche.pdp.indirizzo_dettaglio_id%TYPE;
    v_codice  anagrafiche.pdp.pdp%TYPE;
    v_id      anagrafiche.pdp.id%TYPE;
BEGIN
    SELECT u.id INTO v_utility
      FROM config.utilities u
     WHERE u.codice_interno = p_utility_codice;

    IF v_utility IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_pdp: nessuna utility con codice_interno = % (config.utilities)',
            p_utility_codice;
    END IF;

    -- ⭐ UN numero libero, e da lui DUE cose nuove. Il codice e'
    --   UNIQUE globale; l'indirizzo va nuovo perche' uq_pdp_addr_utility
    --   ammette un solo PDP per (indirizzo, utility), e il builder
    --   dell'indirizzo e' idempotente sull'etichetta, troncata a 10
    --   caratteri: 'PDP' + 6 cifre ci sta intera.
    --   anagrafiche.pdp non e' in RLS: il massimo e' di tutti.
    SELECT COALESCE(max(substring(p.pdp from 9)::bigint), 0) + 1
      INTO v_n
      FROM anagrafiche.pdp p
     WHERE p.pdp ~ '^PGTAPPDP[0-9]{6}$';

    v_codice := 'PGTAPPDP' || lpad(v_n::text, 6, '0');
    v_ind    := dbops.fn_pgtap_crea_indirizzo_dettaglio(
                    'PDP' || lpad(v_n::text, 6, '0'));

    -- Lo stato lo mette trgfn_pdp_set_default_stato.
    INSERT INTO anagrafiche.pdp (pdp, utility_id, indirizzo_dettaglio_id)
    VALUES (v_codice, v_utility, v_ind)
    RETURNING id INTO v_id;

    RETURN QUERY SELECT v_id, v_codice, v_utility, v_ind;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_pdp(p_utility_codice character varying)
IS 'Fixture pgTAP: un PUNTO DI PRELIEVO nuovo (anagrafiche.pdp, dato di MACCHINA: da zero e'' vuota) per l''utility scelta per codice_interno (default GAS), su un indirizzo di dettaglio suo. ⭐ Codice e indirizzo derivano da UN numero libero sui codici PGTAPPDPnnnnnn: uq_pdp_codice e uq_pdp_addr_utility sono rispettate per costruzione. ⚠️ L''indirizzo va nuovo apposta: dbops.fn_pgtap_crea_indirizzo_dettaglio e'' idempotente sull''etichetta (troncata a 10 caratteri), e due PDP della stessa utility sullo stesso indirizzo il modello non li ammette. ⛔ Cliente e istanza sul PDP NON li scrive: sono il caso del test. Ritorna pdp_id, pdp_codice, utility_id, indirizzo_dettaglio_id. Brief: brief-db-fixture-che-costruiscono-giro-2.md';
```

</div>

---
{% include-markdown "signature-core.md" %}
