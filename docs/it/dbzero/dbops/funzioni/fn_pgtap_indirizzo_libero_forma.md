{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_indirizzo_libero_forma.md" %}
# ⚙️ Funzione `fn_pgtap_indirizzo_libero_forma`

```sql
CREATE FUNCTION fn_pgtap_indirizzo_libero_forma(p_stato_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_indirizzo_libero_forma(p_stato_id integer)
 RETURNS TABLE(comune_id integer, codice_postale_id integer, locality character varying, postal_code character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_catalogo config.stati.catalogo_comuni_completo%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I campi della forma dell'indirizzo libero per questo
    --   stato, come li pretende il guard: comune e CAP del
    --   catalogo, oppure localita' e codice postale.
    -- =========================================================
    SELECT s.catalogo_comuni_completo
      INTO v_catalogo
      FROM config.stati s
     WHERE s.id = p_stato_id;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_indirizzo_libero_forma', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('stato_id', p_stato_id),
            NULL::uuid,
            'dbops.fn_pgtap_indirizzo_libero_forma',
            'lo stato non esiste');
    END IF;

    IF NOT v_catalogo THEN
        RETURN QUERY SELECT NULL::integer, NULL::integer,
                            'Localita pgTAP'::varchar, '00000'::varchar;
        RETURN;
    END IF;

    RETURN QUERY
    SELECT c.id, cp.id, NULL::varchar, NULL::varchar
      FROM config.comuni c
      JOIN config.province p        ON p.id = c.provincia_id
      JOIN config.regioni r         ON r.id = p.regione_id
      JOIN config.codici_postali cp ON cp.comune_id = c.id
     WHERE r.stato_id = p_stato_id
     ORDER BY c.id, cp.id
     LIMIT 1;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'dbops', 'dbops.fn_pgtap_indirizzo_libero_forma', 'E_SCRIPT_CHIAMATA_NON_VALIDA',
            jsonb_build_object('stato_id', p_stato_id),
            NULL::uuid,
            'dbops.fn_pgtap_indirizzo_libero_forma',
            'lo stato ha il catalogo dei comuni acceso ma nessun comune con un CAP');
    END IF;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_indirizzo_libero_forma(p_stato_id integer)
IS 'Helper di fixture pgTAP (2026-10-18): una riga con comune_id, codice_postale_id, locality, postal_code nella forma che anagrafiche.trgfn_indirizzi_guard_forma_libera pretende per lo stato. Stato col catalogo completo (config.stati.catalogo_comuni_completo): il primo comune dello stato con un CAP, e quel CAP (ordine per id, deterministico). Altrimenti locality ''Localita pgTAP'' e postal_code ''00000''. La regola si legge dal flag, come il guard: le fixture non se la inventano. Lo usano dbops.fn_pgtap_crea_soggetto_ruolo, fn_pgtap_crea_soggetto_pg e le fixture dei pgTAP. D-2 di Tid, richiesta BE in brief-db-processi-accensione-per-ambiente §6.11.';
```

---
{% include-markdown "signature-core.md" %}
