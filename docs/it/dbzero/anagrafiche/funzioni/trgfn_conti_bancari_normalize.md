{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_conti_bancari_normalize.md" %}
# ⚙️ Funzione `trgfn_conti_bancari_normalize`

```sql
CREATE FUNCTION trgfn_conti_bancari_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_conti_bancari_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo: la forma del conto, prima di chiunque lo giudichi
    --   (fase a01: lucchetto dell'IBAN, guard IBAN-filiale,
    --   CHECK e unicita' leggono il valore normalizzato).
    --   * IBAN e BIC: script.fn_normalizza_codice_bancario
    --     (senza separatori, maiuscolo, il vuoto NULL);
    --   * paese: sempre le prime due lettere dell'IBAN. E' un
    --     derivato: un valore scritto da fuori si sovrascrive.
    -- Non solleva: i rifiuti li danno i CHECK di formato e i guard.
    -- =========================================================
    NEW.iban      := script.fn_normalizza_codice_bancario(NEW.iban);
    NEW.bic_swift := script.fn_normalizza_codice_bancario(NEW.bic_swift);
    NEW.paese     := left(NEW.iban, 2);
    RETURN NEW;
END
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_conti_bancari_normalize()
IS 'BEFORE INSERT OR UPDATE su anagrafiche.conti_bancari, fase a01: IBAN e BIC nella forma di confronto (script.fn_normalizza_codice_bancario: senza separatori, maiuscolo, il vuoto NULL) e il paese sempre ricavato dalle prime due lettere dell''IBAN, anche se chi scrive ne manda un altro. Gira prima del lucchetto dell''IBAN, del guard IBAN-filiale, dei CHECK di formato e dell''unicita'', che leggono il valore normalizzato. Non solleva.';
```

</div>

---
{% include-markdown "signature-core.md" %}
