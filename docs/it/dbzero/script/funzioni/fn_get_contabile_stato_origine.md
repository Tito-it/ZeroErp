{% include-markdown "it/dbzero/script/manual/fn_get_contabile_stato_origine.md" %}
# ⚙️ Funzione `fn_get_contabile_stato_origine`

```sql
CREATE FUNCTION fn_get_contabile_stato_origine(p_contabile_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_contabile_stato_origine(p_contabile_id bigint)
 RETURNS TABLE(stato_id smallint, origine character varying)
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Lo stato e l'origine di una distinta contabile, e
    --   nient'altro, letti fuori dalla row security.
    --
    -- 🔴 Perche' SECURITY DEFINER: una riga contabile si vede
    --   anche dalla FATTURA (seconda strada della policy). Chi
    --   la vede cosi' non vede la sua distinta, e un guard
    --   SECURITY INVOKER che la legge sotto RLS non la trova e
    --   lascia passare.
    --
    -- ⚠️ Il CODICE non si risponde: chi non vede la distinta
    --   non ne legge il numero. Il chiamante lo legge sotto la
    --   RLS e, se manca, ripiega sull'id.
    --
    -- ⚠️ Dipende dalla RLS abilitata e NON forzata.
    --
    -- Zero righe: distinta inesistente (o id NULL). La FK della
    -- riga la rende un caso di chiamata, non di perimetro.
    -- =========================================================

    RETURN QUERY
    SELECT c.stato_id, c.origine
      FROM pagamenti.vendite_contabili c
     WHERE c.id = p_contabile_id;
END
$function$

COMMENT ON FUNCTION script.fn_get_contabile_stato_origine(p_contabile_id bigint)
IS 'Stato e origine di una distinta contabile, letti fuori dalla row security: un building block per i guard delle righe (pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale e la porta 2 di pagamenti.trgfn_vendite_contabili_righe_guard_contenuto). 🔴 Esiste perche'' una riga contabile si vede anche dalla FATTURA: chi la vede cosi'' non vede la sua distinta, e un guard SECURITY INVOKER che la leggesse sotto RLS non la troverebbe e lascerebbe passare. ⚠️ Non risponde il codice: chi non vede la distinta non ne legge il numero. ⚠️ Non allarga niente: dice solo se le righe di quella distinta si lavorano. ⚠️ Dipende dalla RLS abilitata e NON forzata, come script.fn_get_sistemazione_di_contabile.';
```

</div>

---
{% include-markdown "signature-core.md" %}
