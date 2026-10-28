{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_cliente_chiave_unica.md" %}
# ⚙️ Funzione `fn_guard_cliente_chiave_unica`

```sql
CREATE FUNCTION fn_guard_cliente_chiave_unica(p_cliente_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_cliente_chiave_unica(p_cliente_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_sr         anagrafiche.clienti.soggetto_ruolo_id%TYPE;
    v_utility_id anagrafiche.clienti.utility_id%TYPE;
    v_ef_sr      anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id%TYPE;
    v_altro_id   anagrafiche.clienti.id%TYPE;
    v_altro_ba   anagrafiche.billing_account.codice%TYPE;
BEGIN
    -- ⚠️ SECURITY DEFINER: legge clienti e billing_account,
    --   in RLS. Da INVOKER il doppione fuori perimetro di chi
    --   scrive sarebbe invisibile.
    IF p_cliente_id IS NULL THEN
        RETURN;
    END IF;

    SELECT c.soggetto_ruolo_id, c.utility_id,
           script.fn_get_ba_emittente_sr_id_installazione(c.billing_account_id)
      INTO v_sr, v_utility_id, v_ef_sr
      FROM anagrafiche.clienti c
     WHERE c.id = p_cliente_id;

    -- Cliente cancellato nella stessa transazione: niente
    -- da presidiare.
    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Un solo predicato (C-4). Se il cliente stesso non
    -- occupa la chiave (istanza non fittizia, AN, PR, AG,
    -- senza periodo) il suo periodo e' NULL e nessuno si
    -- sovrappone.
    WITH k AS (
        SELECT *
          FROM anagrafiche.fn_clienti_stessa_chiave(v_sr, v_utility_id, v_ef_sr)
    )
    SELECT a.cliente_id, a.billing_account_codice
      INTO v_altro_id, v_altro_ba
      FROM k a
     WHERE a.cliente_id <> p_cliente_id
       AND a.periodo && (SELECT s.periodo FROM k s WHERE s.cliente_id = p_cliente_id)
     ORDER BY a.data_attivazione, a.cliente_id
     LIMIT 1;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'anagrafiche',
        'fn_guard_cliente_chiave_unica',
        'E_CLIENTE_STESSA_CHIAVE',
        jsonb_build_object(
            'cliente_id',         p_cliente_id,
            'altro_cliente_id',   v_altro_id,
            'soggetto_ruolo_id',  v_sr,
            'utility_id',         v_utility_id,
            'emittente_sr',       v_ef_sr
        ),
        NULL::uuid,
        v_altro_ba::text
    );
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_cliente_chiave_unica(p_cliente_id bigint)
IS 'Guard fail-fast (C-1, C-2, C-3 di Tid del 2026-10-13): fra le istanze fittizie un cliente non si sovrappone nel periodo a un altro con lo stesso soggetto, utility e azienda emittente. Il predicato di chi occupa la chiave e'' anagrafiche.fn_clienti_stessa_chiave. Solleva E_CLIENTE_STESSA_CHIAVE col codice del billing account del cliente esistente. Cliente inesistente o fuori dalla chiave: niente da presidiare. Lo chiamano al COMMIT i constraint trigger su clienti, sul collegamento BA -> azienda e su istanze_utilities.fittizia. SECURITY DEFINER: clienti e billing_account sono in RLS. Brief: brief-db-cliente-manuale-uno-per-soggetto-e-utility.';
```

</div>

---
{% include-markdown "signature-core.md" %}
