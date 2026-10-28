{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_istanza_ba_emittente.md" %}
# ⚙️ Funzione `fn_guard_istanza_ba_emittente`

```sql
CREATE FUNCTION fn_guard_istanza_ba_emittente(p_billing_account_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_istanza_ba_emittente(p_billing_account_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_istanza_id  anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_ba_codice   anagrafiche.billing_account.codice%TYPE;
    v_ist_codice  anagrafiche.istanze_utilities.codice%TYPE;
    r             record;
BEGIN
    -- ⚠️ SECURITY DEFINER: legge anagrafiche.billing_account,
    --   che ha la RLS. Da SECURITY INVOKER un fratello di un
    --   altro emittente sarebbe INVISIBILE, e il guard direbbe
    --   «a posto» proprio nel caso che deve bloccare.
    IF p_billing_account_id IS NULL THEN
        RETURN;
    END IF;

    SELECT ba.istanza_utility_id, ba.codice, iu.codice
      INTO v_istanza_id, v_ba_codice, v_ist_codice
      FROM anagrafiche.billing_account ba
      JOIN anagrafiche.istanze_utilities iu ON iu.id = ba.istanza_utility_id
     WHERE ba.id = p_billing_account_id;

    -- BA inesistente (cancellato nella stessa transazione):
    -- non e' compito di questo guard.
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- I FRATELLI di istanza: tutti gli altri BA della stessa
    -- istanza, uno per utility (uq_billing_instance_utility).
    FOR r IN
        SELECT ba.id, ba.codice
          FROM anagrafiche.billing_account ba
         WHERE ba.istanza_utility_id = v_istanza_id
           AND ba.id <> p_billing_account_id
         ORDER BY ba.id
    LOOP
        IF NOT anagrafiche.fn_check_ba_coppia_emittente_omogenea(
                 p_billing_account_id, r.id) THEN
            PERFORM script.fn_log_and_raise_error(
                'anagrafiche', 'fn_guard_istanza_ba_emittente',
                'E_ISTANZA_EMITTENTI_DIVERSI',
                jsonb_build_object(
                    'billing_account_id',       p_billing_account_id,
                    'altro_billing_account_id', r.id,
                    'istanza_utility_id',       v_istanza_id,
                    'emittente_sr',             anagrafiche.fn_get_emittente_fiscale_id(p_billing_account_id),
                    'emittente_sr_altro',       anagrafiche.fn_get_emittente_fiscale_id(r.id)
                ),
                NULL::uuid,
                v_ba_codice::text,
                r.codice::text,
                v_ist_codice::text
            );
        END IF;
    END LOOP;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_istanza_ba_emittente(p_billing_account_id bigint)
IS 'Guard fail-fast: il billing account indicato risolve allo stesso emittente fiscale di TUTTI gli altri BA della sua istanza (D-4 di Tid del 2026-10-08: un''istanza ha billing account di un solo emittente, cosi'' la regola di scope «un''istanza e'' dell''emittente del suo BA» ha una risposta sola). Solleva E_ISTANZA_EMITTENTI_DIVERSI coi codici dei due BA e dell''istanza. Gemello di anagrafiche.fn_guard_albero_ba_emittente (padre/figli), stessa check: anagrafiche.fn_check_ba_coppia_emittente_omogenea, emittente RISOLTO e fail-closed. BA inesistente: niente da presidiare. SECURITY DEFINER perche'' legge billing_account, che ha la RLS. Chiamanti: trgfn_billing_account_guard_istanza_emittente, trgfn_efba_guard_istanza_emittente, fn_guard_istanza_ba_gestore_globale. Brief: brief-db-istanza-nasce-col-ba (R-7).';
```

</div>

---
{% include-markdown "signature-core.md" %}
