{% include-markdown "it/dbzero/anagrafiche/manual/fn_istanza_di_altro_soggetto.md" %}
# ⚙️ Funzione `fn_istanza_di_altro_soggetto`

```sql
CREATE FUNCTION fn_istanza_di_altro_soggetto(p_istanza_utility_id bigint, p_soggetto_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_istanza_di_altro_soggetto(p_istanza_utility_id bigint, p_soggetto_id uuid)
 RETURNS uuid
 LANGUAGE sql
 STABLE
AS $function$
    SELECT iu.soggetto_id
      FROM anagrafiche.istanze_utilities iu
     WHERE iu.id = p_istanza_utility_id
       AND p_soggetto_id IS NOT NULL
       AND iu.soggetto_id IS DISTINCT FROM p_soggetto_id;
$function$

COMMENT ON FUNCTION anagrafiche.fn_istanza_di_altro_soggetto(p_istanza_utility_id bigint, p_soggetto_id uuid)
IS 'BB (2026-10-19): il soggetto dell''istanza (istanze_utilities.soggetto_id) quando NON e'' p_soggetto_id; NULL quando e'' lo stesso, o quando non c''e'' niente da confrontare (istanza NULL o che non esiste, soggetto NULL: l''istanza che manca la rifiuta la FK). Un predicato: il rifiuto lo solleva il chiamante, col suo codice e il suo campo. Lettori: anagrafiche.trgfn_guard_istanza_del_ruolo (indirizzi, soggetti_ruoli_conti_bancari), anagrafiche.trgfn_contatti_guard_contesto_soggetto, anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza, pratiche.trgfn_pratiche_guard_contesto. Regola del 2: il confronto era scritto nel guard del BA e nella regola 4 delle pratiche. R-BE-15, D-17b di Tid, brief-db-processi-accensione-per-ambiente §6.17.1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
