{% include-markdown "it/dbzero/anagrafiche/manual/fn_guard_albero_ba_gestore_globale.md" %}
# ⚙️ Funzione `fn_guard_albero_ba_gestore_globale`

```sql
CREATE FUNCTION fn_guard_albero_ba_gestore_globale()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_guard_albero_ba_gestore_globale()
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    r record;
BEGIN
    -- ⚠️ E' l'unica operazione del cantiere con RAGGIO N: cambiare
    --   il gestore globale sposta in blocco l'emittente di TUTTI i
    --   BA che non hanno un mapping specifico. Una riga sola puo'
    --   spaccare un numero arbitrario di alberi. (brief §11.3, Q3)
    --
    -- ⚠️ Si guardano SOLO i BA senza mapping specifico E che stanno
    --   in un albero: se entrambi i lati di una coppia sono non
    --   mappati si spostano INSIEME e l'albero resta omogeneo;
    --   se sono entrambi mappati non si sposta nessuno dei due.
    --   La condizione che conta e' la COPPIA MISTA — non
    --   «esiste un albero». (decisione Q3)
    FOR r IN
        SELECT ba.id
          FROM anagrafiche.billing_account ba
         WHERE NOT EXISTS (
                   SELECT 1
                     FROM anagrafiche.emittenti_fiscali_billing_account e
                    WHERE e.billing_account_id = ba.id)
           AND (
                 ba.parent_account_id IS NOT NULL
              OR EXISTS (SELECT 1
                           FROM anagrafiche.billing_account f
                          WHERE f.parent_account_id = ba.id)
               )
         ORDER BY ba.id
    LOOP
        PERFORM anagrafiche.fn_guard_albero_ba_emittente(r.id);
    END LOOP;
END
$function$

COMMENT ON FUNCTION anagrafiche.fn_guard_albero_ba_gestore_globale()
IS 'Guard fail-fast per lo spostamento del gestore globale (is_default), l''unica operazione del cantiere con raggio N: cambia in blocco l''emittente di tutti i BA senza mapping specifico. Verifica i soli BA non mappati che stanno in un albero — se entrambi i lati di una coppia sono non mappati si spostano insieme e l''albero resta omogeneo (decisione Q3: la condizione e'' la COPPIA MISTA). SECURITY DEFINER: legge billing_account, che ha la RLS. Brief P-1 §11.3. ⚠️ rev 2026-08-26: dal 20260826-48 quello stesso movimento ha un SECONDO cancello, anagrafiche.fn_guard_ba_gestore_globale_storia, che lo vieta se anche UN SOLO billing account non mappato ha gia'' fatture o commesse — cioe'', su un''installazione che ha gia'' fatturato, quasi sempre. Spostare il gestore globale li'' non e'' una configurazione da rivedere: e'' una riscrittura retroattiva della storia. ⭐ I due guard restano entrambi: questo chiede «l''albero puo'' diventare misto?», l''altro «c''e'' storia da proteggere?». Brief: brief-db-billing-account-cambio-emittente.';
```

---
{% include-markdown "signature-core.md" %}
