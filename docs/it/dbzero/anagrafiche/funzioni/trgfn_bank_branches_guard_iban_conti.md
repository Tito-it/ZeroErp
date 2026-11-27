# ⚙️ Funzione `trgfn_bank_branches_guard_iban_conti`

```sql
CREATE FUNCTION trgfn_bank_branches_guard_iban_conti()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_bank_branches_guard_iban_conti()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_chi CONSTANT dbops.error_log.function_name%TYPE := 'anagrafiche.trgfn_bank_branches_guard_iban_conti';
BEGIN
    -- =========================================================
    -- Scopo: il verso della filiale della regola «l'IBAN del
    --   conto porta banca e filiale della sua filiale». Quando
    --   cambiano il codice della banca o quello della filiale,
    --   ogni conto che ci sta resta coerente.
    --   Montata BEFORE UPDATE, fase a12: i codici nella forma
    --   della normalizzazione a01.
    -- =========================================================
    IF NEW.bank_code IS NOT DISTINCT FROM OLD.bank_code
       AND NEW.branch_code IS NOT DISTINCT FROM OLD.branch_code THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
          FROM anagrafiche.conti_bancari c
         WHERE c.bank_branch_id = NEW.id
           AND NOT anagrafiche.fn_iban_coerente_con_filiale(
                       c.iban, NEW.bank_code, NEW.branch_code)) THEN
        PERFORM script.fn_log_and_raise_error(
            'database', v_chi, 'E_FILIALE_CODICI_CONTI_INCOERENTI',
            jsonb_build_object('campo', 'bank_code',
                               'tabella', 'anagrafiche.bank_branches',
                               'bank_branch_id', NEW.id),
            NEW.tx_id,
            NEW.bank_code::text, NEW.branch_code::text);
    END IF;
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_bank_branches_guard_iban_conti()
IS 'BEFORE UPDATE su anagrafiche.bank_branches, fase a12: un cambio del codice della banca o di quello della filiale lascia coerenti i conti che ci stanno (anagrafiche.fn_iban_coerente_con_filiale). Rifiuto: E_FILIALE_CODICI_CONTI_INCOERENTI, campo bank_code. Il verso del conto lo tiene anagrafiche.trgfn_conti_bancari_guard_iban_filiale.';
```

</div>

---
{% include-markdown "signature-core.md" %}
