# ⚙️ Funzione `trgfn_bank_branches_normalize`

```sql
CREATE FUNCTION trgfn_bank_branches_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_bank_branches_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: la forma della filiale, prima di chiunque la giudichi
    --   (fase a01: il guard IBAN-filiale, l'unicita' della coppia
    --   per paese e il CHECK del BIC leggono il valore
    --   normalizzato). script.fn_normalizza_codice_bancario:
    --   senza separatori, maiuscolo, il vuoto NULL; gli zeri
    --   restano. Non solleva.
    -- =========================================================
    NEW.bank_code   := script.fn_normalizza_codice_bancario(NEW.bank_code);
    NEW.branch_code := script.fn_normalizza_codice_bancario(NEW.branch_code);
    NEW.bic_swift   := script.fn_normalizza_codice_bancario(NEW.bic_swift);
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_bank_branches_normalize()
IS 'BEFORE INSERT OR UPDATE su anagrafiche.bank_branches, fase a01: codice della banca, codice della filiale e BIC nella forma di confronto (script.fn_normalizza_codice_bancario: senza separatori, maiuscolo, il vuoto NULL; gli zeri restano). Gira prima del guard IBAN-filiale e dell''unicita'' della coppia per paese, che confrontano i valori normalizzati. Non solleva.';
```

</div>

---
{% include-markdown "signature-core.md" %}
