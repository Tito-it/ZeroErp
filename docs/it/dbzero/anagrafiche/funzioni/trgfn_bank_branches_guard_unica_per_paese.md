# ⚙️ Funzione `trgfn_bank_branches_guard_unica_per_paese`

```sql
CREATE FUNCTION trgfn_bank_branches_guard_unica_per_paese()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_bank_branches_guard_unica_per_paese()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi    CONSTANT dbops.error_log.function_name%TYPE := 'anagrafiche.trgfn_bank_branches_guard_unica_per_paese';
    v_stato  anagrafiche.soggetti.stato_id%TYPE;
    v_altra  anagrafiche.bank_branches.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: lo sportello (codice della banca, codice della
    --   filiale) esiste una volta nel paese del soggetto della
    --   banca. Montata BEFORE INSERT OR UPDATE, fase a12: i codici
    --   nella forma della normalizzazione a01. In modifica giudica
    --   solo se cambiano i codici o il ruolo della banca.
    --   Il lock consultivo mette in fila due scritture della
    --   stessa terna: la seconda vede la prima dopo il COMMIT.
    -- =========================================================
    IF TG_OP = 'UPDATE'
       AND NEW.bank_code IS NOT DISTINCT FROM OLD.bank_code
       AND NEW.branch_code IS NOT DISTINCT FROM OLD.branch_code
       AND NEW.soggetto_ruolo_id IS NOT DISTINCT FROM OLD.soggetto_ruolo_id THEN
        RETURN NEW;
    END IF;

    SELECT s.stato_id INTO v_stato
      FROM anagrafiche.soggetti_ruoli r
      JOIN anagrafiche.soggetti s ON s.id = r.soggetto_id
     WHERE r.id = NEW.soggetto_ruolo_id;
    -- Un ruolo che non c'e' lo rifiutano la FK e il guard del ruolo.
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    PERFORM pg_catalog.pg_advisory_xact_lock(
        pg_catalog.hashtext('anagrafiche.bank_branches'),
        pg_catalog.hashtext(concat_ws('|', v_stato, NEW.bank_code, NEW.branch_code)));

    v_altra := anagrafiche.fn_filiale_stessi_codici(
                   NEW.id, NEW.bank_code, NEW.branch_code, v_stato);
    IF v_altra IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_FILIALE_DUPLICATA',
            jsonb_build_object('campo', 'branch_code',
                               'tabella', 'anagrafiche.bank_branches',
                               'bank_branch_id', NEW.id,
                               'altra_filiale_id', v_altra,
                               'stato_id', v_stato),
            NEW.tx_id,
            NEW.bank_code::text, NEW.branch_code::text);
    END IF;
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_bank_branches_guard_unica_per_paese()
IS 'BEFORE INSERT OR UPDATE su anagrafiche.bank_branches, fase a12: lo sportello (codice della banca, codice della filiale) esiste una volta nel paese del soggetto della banca (soggetti.stato_id). In modifica giudica solo un cambio dei codici o del ruolo. Due scritture della stessa terna paese-banca-filiale si mettono in fila con un lock consultivo di transazione. Rifiuto: E_FILIALE_DUPLICATA, campo branch_code. Il verso del soggetto lo tiene anagrafiche.trgfn_soggetti_guard_filiali_unica_per_paese.';
```

</div>

---
{% include-markdown "signature-core.md" %}
