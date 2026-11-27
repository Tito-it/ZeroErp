# ⚙️ Funzione `fn_iban_coerente_con_filiale`

```sql
CREATE FUNCTION fn_iban_coerente_con_filiale(p_iban text, p_bank_code text, p_branch_code text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_iban_coerente_con_filiale(p_iban text, p_bank_code text, p_branch_code text)
 RETURNS boolean
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT (NOT (EXISTS ( SELECT 1
            FROM config.stati s
           WHERE (((s.codice_iso2)::text = "left"(fn_iban_coerente_con_filiale.p_iban, 2)) AND (s.iban_pos_banca IS NOT NULL) AND ((substr(fn_iban_coerente_con_filiale.p_iban, (s.iban_pos_banca)::integer, (s.iban_len_banca)::integer) IS DISTINCT FROM fn_iban_coerente_con_filiale.p_bank_code) OR (substr(fn_iban_coerente_con_filiale.p_iban, (s.iban_pos_filiale)::integer, (s.iban_len_filiale)::integer) IS DISTINCT FROM fn_iban_coerente_con_filiale.p_branch_code))))));
END

COMMENT ON FUNCTION anagrafiche.fn_iban_coerente_con_filiale(p_iban text, p_bank_code text, p_branch_code text)
IS 'Vero se l''IBAN porta il codice della banca e quello della filiale dati, nelle posizioni che lo stato dell''IBAN dichiara (config.stati.iban_pos_banca, iban_len_banca, iban_pos_filiale, iban_len_filiale; lo stato si trova dalle prime due lettere, codice_iso2). Vero anche quando lo stato non dichiara le posizioni, o non e'' censito: il confronto non si fa. Riceve i valori gia'' nella forma di confronto (script.fn_normalizza_codice_bancario). La usano i due guard anagrafiche.trgfn_conti_bancari_guard_iban_filiale e anagrafiche.trgfn_bank_branches_guard_iban_conti.';
```

</div>

---
{% include-markdown "signature-core.md" %}
