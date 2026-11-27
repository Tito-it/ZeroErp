# ⚙️ Funzione `fn_pgtap_iban`

```sql
CREATE FUNCTION fn_pgtap_iban(p_bank_branch_id bigint, p_seme text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_iban(p_bank_branch_id bigint, p_seme text)
 RETURNS text
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: un IBAN italiano coerente con la filiale, per le fixture
--   pgTAP (ABI e CAB della filiale nelle posizioni 6-10 e 11-15).
-- Uso: dbops.fn_pgtap_iban(b.bank_branch_id, 'incasso unico 1')
DECLARE
    v_banca   anagrafiche.bank_branches.bank_code%TYPE;
    v_filiale anagrafiche.bank_branches.branch_code%TYPE;
BEGIN
    SELECT b.bank_code, b.branch_code INTO v_banca, v_filiale
      FROM anagrafiche.bank_branches b
     WHERE b.id = p_bank_branch_id;
    IF NOT FOUND OR length(v_banca) <> 5 OR length(v_filiale) <> 5 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'dbops.fn_pgtap_iban', 'E_DBOPS_CHIAMATA_NON_VALIDA',
            jsonb_build_object('campo', 'p_bank_branch_id',
                               'bank_branch_id', p_bank_branch_id),
            NULL::uuid,
            'dbops.fn_pgtap_iban',
            format('la filiale %s non c''e'' o non ha codici di 5 caratteri', p_bank_branch_id));
    END IF;
    RETURN 'IT00X' || v_banca || v_filiale
           || right(lpad(coalesce(script.fn_normalizza_codice_bancario(p_seme), ''), 12, '0'), 12);
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_iban(p_bank_branch_id bigint, p_seme text)
IS 'Fixture pgTAP: un IBAN italiano di 27 caratteri coerente con la filiale data (IT, cifre di controllo 00, CIN X, ABI e CAB della filiale, poi gli ultimi 12 caratteri del seme normalizzato, con zeri a sinistra). Semi diversi danno IBAN diversi. La cifra di controllo non e'' calcolata: il database non la verifica. Una filiale che non c''e'', o con codici che non sono di 5 caratteri, solleva E_DBOPS_CHIAMATA_NON_VALIDA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
