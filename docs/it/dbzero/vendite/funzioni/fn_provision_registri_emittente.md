{% include-markdown "it/dbzero/vendite/manual/fn_provision_registri_emittente.md" %}
# ⚙️ Funzione `fn_provision_registri_emittente`

```sql
CREATE FUNCTION fn_provision_registri_emittente(p_emittente_soggetto_ruolo_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_provision_registri_emittente(p_emittente_soggetto_ruolo_id bigint)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dare a un emittente i registri delle famiglie non
    --   fiscali che ancora non ha, e dire quanti ne ha creati.
    --
    -- ⭐ Dal 2026-09-01 non contiene piu' la regola: chiama la
    --   primitiva vendite.fn_provision_registri. Qui resta solo
    --   il FILTRO, che e' l'unica cosa che distingue questa
    --   porta dalla gemella per famiglia.
    -- =========================================================
    IF p_emittente_soggetto_ruolo_id IS NULL THEN
        RETURN 0;
    END IF;

    RETURN vendite.fn_provision_registri(
               p_emittente_soggetto_ruolo_id => p_emittente_soggetto_ruolo_id,
               p_famiglia_documento          => NULL);
END;
$function$

COMMENT ON FUNCTION vendite.fn_provision_registri_emittente(p_emittente_soggetto_ruolo_id bigint)
IS 'Da a un emittente fiscale i registri di numerazione delle famiglie non fiscali che ancora non ha, e torna quanti ne ha creati. La chiama vendite.trgfn_emittenti_fiscali_provision_registri alla nascita (o riattivazione) di un emittente. ⭐ Dal 2026-09-01 e'' un INVOLUCRO SOTTILE: la regola di come nasce un registro vive in vendite.fn_provision_registri, e qui resta solo il filtro — l''unica cosa che distingue questa porta dalla gemella per famiglia. ⚠️ FIRMA INVARIATA di proposito: la chiama un trigger, e un parametro in piu'' sarebbe un OVERLOAD e non una modifica, cioe'' il trigger continuerebbe a chiamare la versione vecchia con la regola vecchia dentro. ⚠️ Un emittente NULL torna 0 e non solleva: il trigger la chiama su ogni riga, e una riga senza soggetto_ruolo non e'' un errore di dominio. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.6 (DB-4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
