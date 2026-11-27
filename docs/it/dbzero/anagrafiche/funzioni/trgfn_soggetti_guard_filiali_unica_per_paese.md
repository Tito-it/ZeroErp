# ⚙️ Funzione `trgfn_soggetti_guard_filiali_unica_per_paese`

```sql
CREATE FUNCTION trgfn_soggetti_guard_filiali_unica_per_paese()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_soggetti_guard_filiali_unica_per_paese()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi CONSTANT dbops.error_log.function_name%TYPE := 'anagrafiche.trgfn_soggetti_guard_filiali_unica_per_paese';
    r     record;
BEGIN
    -- =========================================================
    -- Scopo: il verso del soggetto dell'unicita' per paese delle
    --   filiali. Cambiato lo stato di un soggetto, ogni filiale
    --   dei suoi ruoli banca resta unica nel paese nuovo.
    --   Montata BEFORE UPDATE OF stato_id, fase a12.
    -- =========================================================
    IF NEW.stato_id IS NOT DISTINCT FROM OLD.stato_id THEN
        RETURN NEW;
    END IF;

    FOR r IN
        SELECT b.id, b.bank_code, b.branch_code
          FROM anagrafiche.bank_branches b
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = b.soggetto_ruolo_id
         WHERE sr.soggetto_id = NEW.id
         ORDER BY b.id
    LOOP
        PERFORM pg_catalog.pg_advisory_xact_lock(
            pg_catalog.hashtext('anagrafiche.bank_branches'),
            pg_catalog.hashtext(concat_ws('|', NEW.stato_id, r.bank_code, r.branch_code)));
        IF anagrafiche.fn_filiale_stessi_codici(
               r.id, r.bank_code, r.branch_code, NEW.stato_id) IS NOT NULL THEN
            PERFORM script.fn_log_and_raise_error(
                'database', v_chi, 'E_FILIALE_DUPLICATA',
                jsonb_build_object('campo', 'stato_id',
                                   'tabella', 'anagrafiche.soggetti',
                                   'soggetto_id', NEW.id,
                                   'bank_branch_id', r.id),
                NEW.tx_id,
                r.bank_code::text, r.branch_code::text);
        END IF;
    END LOOP;
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_soggetti_guard_filiali_unica_per_paese()
IS 'BEFORE UPDATE OF stato_id su anagrafiche.soggetti, fase a12: cambiato lo stato di un soggetto, ogni filiale dei suoi ruoli banca resta unica nel paese nuovo (codice della banca, codice della filiale). Rifiuto: E_FILIALE_DUPLICATA, campo stato_id. Il verso della filiale lo tiene anagrafiche.trgfn_bank_branches_guard_unica_per_paese.';
```

</div>

---
{% include-markdown "signature-core.md" %}
