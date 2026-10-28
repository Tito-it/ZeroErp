{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_istanza_ha_ba.md" %}
# ⚙️ Funzione `fn_guard_istanza_ha_ba`

```sql
CREATE FUNCTION fn_guard_istanza_ha_ba(p_istanza_utility_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_istanza_ha_ba(p_istanza_utility_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_codice anagrafiche.istanze_utilities.codice%TYPE;
BEGIN
    -- ⚠️ SECURITY DEFINER: legge anagrafiche.billing_account,
    --   che ha la RLS. Da SECURITY INVOKER un BA fuori dal
    --   perimetro di chi scrive sarebbe invisibile, e il guard
    --   rifiuterebbe un'istanza che il suo BA ce l'ha.
    IF p_istanza_utility_id IS NULL THEN
        RETURN;
    END IF;

    SELECT iu.codice
      INTO v_codice
      FROM anagrafiche.istanze_utilities iu
     WHERE iu.id = p_istanza_utility_id;

    -- Istanza cancellata nella stessa transazione (insieme ai
    -- suoi BA): non c'e' piu' niente da presidiare.
    IF NOT FOUND THEN
        RETURN;
    END IF;

    IF EXISTS (
        SELECT 1
          FROM anagrafiche.billing_account ba
         WHERE ba.istanza_utility_id = p_istanza_utility_id
    ) THEN
        RETURN;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'anagrafiche',
        'fn_guard_istanza_ha_ba',
        'E_ISTANZA_SENZA_BA',
        jsonb_build_object(
            'istanza_utility_id', p_istanza_utility_id
        ),
        NULL::uuid,
        v_codice::text
    );
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_istanza_ha_ba(p_istanza_utility_id bigint)
IS 'Guard fail-fast: un''istanza utility che esiste deve avere almeno un billing account (regola di Tid del 2026-10-08: istanza e BA nascono insieme, sempre). Solleva E_ISTANZA_SENZA_BA col codice dell''istanza. Istanza inesistente o parametro NULL: niente da presidiare. Lo chiamano al COMMIT due constraint trigger: trg_istanze_utilities_z90_require_utility_dichiarata_ins (nascita dell''istanza) e trg_billing_account_z90_require_istanza_ha_ba_dlt (cancellazione del BA); lo spostamento del BA lo chiude il lock di colonna E_BA_ISTANZA_IMMUTABILE. SECURITY DEFINER perche'' legge billing_account, che ha la RLS: da INVOKER un BA fuori perimetro sarebbe invisibile e il guard rifiuterebbe un''operazione legittima. Brief: brief-db-istanza-nasce-col-ba (R-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
