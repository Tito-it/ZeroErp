{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_istanza_ba_gestore_globale.md" %}
# ⚙️ Funzione `fn_guard_istanza_ba_gestore_globale`

```sql
CREATE FUNCTION fn_guard_istanza_ba_gestore_globale()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_istanza_ba_gestore_globale()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    r record;
BEGIN
    -- ⚠️ RAGGIO N: cambiare il gestore globale sposta in blocco
    --   l'emittente di TUTTI i BA senza collegamento specifico.
    --   Si guardano solo quelli che hanno un fratello di istanza:
    --   la condizione che conta e' la coppia MISTA (uno collegato,
    --   uno no), e la trova fn_guard_istanza_ba_emittente.
    FOR r IN
        SELECT ba.id
          FROM anagrafiche.billing_account ba
         WHERE NOT EXISTS (
                   SELECT 1
                     FROM anagrafiche.emittenti_fiscali_billing_account e
                    WHERE e.billing_account_id = ba.id)
           AND EXISTS (
                   SELECT 1
                     FROM anagrafiche.billing_account f
                    WHERE f.istanza_utility_id = ba.istanza_utility_id
                      AND f.id <> ba.id)
         ORDER BY ba.id
    LOOP
        PERFORM anagrafiche.fn_guard_istanza_ba_emittente(r.id);
    END LOOP;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_istanza_ba_gestore_globale()
IS 'Guard fail-fast per lo spostamento del gestore globale (is_default), che cambia in blocco l''emittente di tutti i BA senza collegamento specifico: verifica che nessuna istanza finisca su due emittenti. Guarda i soli BA non collegati che hanno un fratello di istanza (la condizione e'' la coppia MISTA) e delega a fn_guard_istanza_ba_emittente (E_ISTANZA_EMITTENTI_DIVERSI). Gemello di fn_guard_albero_ba_gestore_globale; lo stesso movimento ha anche il cancello fn_guard_ba_gestore_globale_storia, e i due si sommano. SECURITY DEFINER: legge billing_account, che ha la RLS. Brief: brief-db-istanza-nasce-col-ba (R-7).';
```

---
{% include-markdown "signature-core.md" %}
