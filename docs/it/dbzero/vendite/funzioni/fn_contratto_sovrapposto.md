{% include-markdown "it/dbzero/vendite/manual/fn_contratto_sovrapposto.md" %}
# ⚙️ Funzione `fn_contratto_sovrapposto`

```sql
CREATE FUNCTION fn_contratto_sovrapposto(p_billing_account_id bigint, p_istanza_utility_id bigint, p_utility_id integer, p_ambito character varying, p_valido_dal date, p_valido_al date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratto_sovrapposto(p_billing_account_id bigint, p_istanza_utility_id bigint, p_utility_id integer, p_ambito character varying, p_valido_dal date, p_valido_al date)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo:
--   Rilevamento read-only del contratto VINCOLANTE (partecipante
--   all'overlap: non abortito e non in bozza) la cui finestra
--   temporale si sovrappone alla quintupla del nuovo contratto.
--   Cuore del meccanismo generico di successione (brief §3.2.1).
--   NON solleva errori: ritorna id o NULL.
--
-- Parametri: i 5 attributi della chiave dell'EXCLUDE
--   ex_contratti_no_overlap (billing_account, istanza_utility,
--   utility, ambito) + finestra (valido_dal/valido_al).
--
-- Ritorno:
--   id del contratto "incumbent" sovrapposto, oppure NULL.
--   I contratti in BOZZA non contano (coerente con l'EXCLUDE che li
--   esclude via partecipa_overlap_snapshot).
--
-- Daterange: COALESCE simmetrico identico alla colonna GENERATED
--   contratti.validita (linee-guida-sql §7b) per garantire che &&
--   confronti rappresentazioni interne identiche con valido_al NULL.
DECLARE
    v_finestra daterange;
    v_id       vendite.contratti.id%TYPE;
BEGIN
    v_finestra := daterange(
        COALESCE(p_valido_dal, '-infinity'::date),
        COALESCE(p_valido_al,  'infinity'::date),
        '[]'
    );

    SELECT c.id
      INTO v_id
      FROM vendite.contratti c
     WHERE c.billing_account_id = p_billing_account_id
       AND c.istanza_utility_id = p_istanza_utility_id
       AND c.utility_id         = p_utility_id
       AND c.ambito             = p_ambito
       AND c.partecipa_overlap_snapshot
       AND c.validita && v_finestra
     ORDER BY
         -- "incumbent": prima il contratto che contiene la data
         -- di decorrenza del nuovo, poi il piu' recente.
         (c.validita @> COALESCE(p_valido_dal, '-infinity'::date)) DESC,
         c.valido_dal DESC
     LIMIT 1;

    RETURN v_id;  -- NULL se nessun overlap
END;
$function$

COMMENT ON FUNCTION vendite.fn_contratto_sovrapposto(p_billing_account_id bigint, p_istanza_utility_id bigint, p_utility_id integer, p_ambito character varying, p_valido_dal date, p_valido_al date)
IS 'Rilevamento read-only (STABLE) del contratto VINCOLANTE (partecipa_overlap_snapshot: non abortito e non in bozza) sovrapposto alla quintupla (billing_account, istanza_utility, utility, ambito, periodo). Ritorna l''id dell''incumbent o NULL. I DRAFT non contano. Meccanismo generico di successione. Daterange con COALESCE simmetrico identico a contratti.validita. rev 2026-06-02.';
```

</div>

---
{% include-markdown "signature-core.md" %}
