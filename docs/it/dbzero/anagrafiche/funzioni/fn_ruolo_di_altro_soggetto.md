{% include-markdown "it/dbzero/anagrafiche/manual/fn_ruolo_di_altro_soggetto.md" %}
# ⚙️ Funzione `fn_ruolo_di_altro_soggetto`

```sql
CREATE FUNCTION fn_ruolo_di_altro_soggetto(p_soggetto_ruolo_id bigint, p_soggetto_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_ruolo_di_altro_soggetto(p_soggetto_ruolo_id bigint, p_soggetto_id uuid)
 RETURNS uuid
 LANGUAGE sql
 STABLE
AS $function$
    SELECT sr.soggetto_id
      FROM anagrafiche.soggetti_ruoli sr
     WHERE sr.id = p_soggetto_ruolo_id
       AND p_soggetto_id IS NOT NULL
       AND sr.soggetto_id IS DISTINCT FROM p_soggetto_id;
$function$

COMMENT ON FUNCTION anagrafiche.fn_ruolo_di_altro_soggetto(p_soggetto_ruolo_id bigint, p_soggetto_id uuid)
IS 'BB (2026-10-19): il soggetto del ruolo (soggetti_ruoli.soggetto_id) quando NON e'' p_soggetto_id; NULL quando e'' lo stesso, o quando non c''e'' niente da confrontare (ruolo NULL o che non esiste, soggetto NULL: il ruolo che manca lo rifiuta la FK). Un predicato: il rifiuto lo solleva il chiamante, col suo codice e il suo campo. Gemello di anagrafiche.fn_istanza_di_altro_soggetto. Lettori: anagrafiche.trgfn_contatti_guard_contesto_soggetto, pratiche.trgfn_pratiche_guard_contesto. Regola del 2: il confronto era scritto nella regola 3 delle pratiche. R-BE-15, D-17a e D-17b di Tid, brief-db-processi-accensione-per-ambiente §6.17.1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
