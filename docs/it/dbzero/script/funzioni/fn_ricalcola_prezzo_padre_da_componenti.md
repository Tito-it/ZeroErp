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
    -- Ricalcola prezzo_unitario del padre dai figli ATTIVI.
    --
    -- ⛔ Tre casi, e il secondo e' quello per cui esiste questa
    --   revisione (2026-08-19, slice C del brief righe DDT senza
    --   prezzo):
    --
    --     nessun figlio attivo          -> 0
    --     almeno un figlio senza prezzo -> NULL  «non si sa»
    --     tutti valorizzati             -> SUM(prezzo * coeff)
    --
    --   Prima era COALESCE(SUM(...), 0) e bastava, perche' il
    --   prezzo dei figli era NOT NULL ovunque. Da quando su
    --   vendite.ddt_righe_componenti puo' mancare (un kit che
    --   viaggia senza vendersi: conto visione, campionatura,
    --   riparazione), la SUM semplice IGNOREREBBE il figlio
    --   scoperto e restituirebbe la somma degli altri: un prezzo
    --   sbagliato al posto di un prezzo assente.
    --   ⚠️ La differenza non e' formale. Il kit a prezzo assente
    --   lo ferma il gate all'emissione; il kit a prezzo PARZIALE
    --   il gate lo passa — un prezzo c'e' — e arriva in fattura.
    --
    -- ⚠️ Il COALESCE non e' tornato per sbaglio: qui NON ci va.
    --   COALESCE(..., 0) trasformerebbe il NULL in zero, cioe'
    --   rifarebbe il difetto in un altro modo. Il caso «nessun
    --   figlio» e' gestito dal CASE, esplicitamente.
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
              )
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
IS 'Helper generica BoM CASO A: aggiorna prezzo_unitario della riga padre dai figli attivi. rev 2026-08-19: TRE casi invece di due — nessun figlio 0, almeno un figlio senza prezzo NULL, altrimenti SUM(prezzo * coeff_qta_snapshot). ⚠️ Il ramo NULL esiste perche'' su vendite.ddt_righe_componenti il prezzo puo'' mancare (kit che viaggia senza vendersi): con la SUM semplice il figlio scoperto veniva IGNORATO e il padre riceveva la somma parziale — un prezzo sbagliato, che passa il gate all''emissione, invece di un prezzo assente, che il gate ferma. Su preventivi e ordini i figli restano NOT NULL: per loro il ramo e'' irraggiungibile e il comportamento identico a prima. Parametrizzata su schema/tabella/FK, 4 sorgenti. Brief: brief-ddt-righe-senza-prezzo §9 slice C (C2).';
```

</div>

---
{% include-markdown "signature-core.md" %}
