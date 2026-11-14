{% include-markdown "it/dbzero/script/manual/fn_ricalcola_prezzo_padre_da_componenti.md" %}
# ⚙️ Funzione `fn_ricalcola_prezzo_padre_da_componenti`

```sql
CREATE FUNCTION fn_ricalcola_prezzo_padre_da_componenti(p_schema text, p_tab_padre text, p_tab_figli text, p_col_fk_padre text, p_riga_padre_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_ricalcola_prezzo_padre_da_componenti(p_schema text, p_tab_padre text, p_tab_figli text, p_col_fk_padre text, p_riga_padre_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sql text;
BEGIN
    -- Ricalcola prezzo_unitario del padre dai figli ATTIVI, e
    -- dichiara la provenienza: COMPONENTI, senza listino.
    --
    -- ⛔ Tre casi per il prezzo:
    --
    --     nessun figlio attivo          -> 0
    --     almeno un figlio senza prezzo -> NULL  «non si sa»
    --     tutti valorizzati             -> SUM(prezzo * coeff)
    --
    --   Su vendite.ddt_righe_componenti il prezzo puo' mancare
    --   (un kit che viaggia senza vendersi): la SUM semplice
    --   IGNOREREBBE il figlio scoperto e restituirebbe la somma
    --   degli altri, un prezzo sbagliato al posto di un prezzo
    --   assente. Il kit a prezzo assente lo ferma il gate
    --   all'emissione; il kit a prezzo PARZIALE il gate lo passa.
    --   ⚠️ Niente COALESCE(..., 0): rifarebbe il difetto in un
    --   altro modo.
    --
    -- La provenienza: COMPONENTI, cioe' «sta su ciascun
    -- componente». Con un prezzo NULL l'origine la svuota il
    -- trigger vendite.trgfn_riga_documento_provenienza_prezzo.
    v_sql := format(
        $q$UPDATE %1$I.%2$I
              SET prezzo_unitario = (
                  SELECT CASE
                           WHEN count(*) = 0 THEN 0
                           WHEN count(*) FILTER (
                                  WHERE c.prezzo_unitario IS NULL) > 0
                             THEN NULL
                           ELSE SUM(c.prezzo_unitario * c.coeff_qta_snapshot)
                         END
                    FROM %1$I.%3$I c
                   WHERE c.%4$I = $1
                     AND c.attivo = TRUE
              ),
                  origine_prezzo          = 'COMPONENTI',
                  listino_versione_id     = NULL,
                  listino_riga_id         = NULL,
                  prezzo_resolver_context = NULL
            WHERE id = $1$q$,
        p_schema,
        p_tab_padre,
        p_tab_figli,
        p_col_fk_padre
    );
    EXECUTE v_sql USING p_riga_padre_id;
END;
$function$

COMMENT ON FUNCTION script.fn_ricalcola_prezzo_padre_da_componenti(p_schema text, p_tab_padre text, p_tab_figli text, p_col_fk_padre text, p_riga_padre_id bigint)
IS 'Ricalcola il prezzo della riga principale di un kit dai suoi componenti attivi e ne dichiara la provenienza. Prezzo: 0 senza componenti attivi; NULL se almeno un componente non ha prezzo (il kit a prezzo assente lo ferma il gate all''emissione, uno a prezzo parziale no); altrimenti la somma di prezzo per coefficiente. Provenienza: origine_prezzo COMPONENTI (la provenienza sta su ciascun componente), versione, riga di listino e contesto del resolver a NULL; con un prezzo NULL l''origine la svuota vendite.trgfn_riga_documento_provenienza_prezzo. Parametrizzata su schema, tabella della riga, tabella dei componenti e colonna FK; la chiama script.trgfn_componenti_ricalcola_padre sui componenti di preventivi, ordini, contratti, DDT e offerte.';
```

</div>

---
{% include-markdown "signature-core.md" %}
