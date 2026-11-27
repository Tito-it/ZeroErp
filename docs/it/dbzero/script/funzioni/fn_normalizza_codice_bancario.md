# ⚙️ Funzione `fn_normalizza_codice_bancario`

```sql
CREATE FUNCTION fn_normalizza_codice_bancario(p_valore text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_normalizza_codice_bancario(p_valore text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT NULLIF(upper(regexp_replace(p_valore, '[^A-Za-z0-9]', '', 'g')), '');
$function$

COMMENT ON FUNCTION script.fn_normalizza_codice_bancario(p_valore text)
IS 'La forma di confronto di un codice bancario (IBAN, BIC, codice della banca, codice della filiale): senza spazi, trattini, punti o altri separatori, in maiuscolo; il vuoto e'' NULL, NULL resta NULL. Gli zeri restano: sono parte del codice. La usano anagrafiche.trgfn_conti_bancari_normalize e anagrafiche.trgfn_bank_branches_normalize, in fase a01, prima di guard, lucchetti e indici: chi scrive passa il valore come lo legge, e il backend non ricopia la regola.';
```

</div>

---
{% include-markdown "signature-core.md" %}
