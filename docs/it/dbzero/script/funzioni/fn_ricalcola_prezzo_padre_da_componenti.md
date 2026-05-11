{% include-markdown "it/dbzero/script/manual/fn_ricalcola_prezzo_padre_da_componenti.md" %}
# ⚙️ Funzione `fn_ricalcola_prezzo_padre_da_componenti`

```sql
CREATE FUNCTION fn_ricalcola_prezzo_padre_da_componenti(p_schema text, p_tab_padre text, p_tab_figli text, p_col_fk_padre text, p_riga_padre_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_ricalcola_prezzo_padre_da_componenti(p_schema text, p_tab_padre text, p_tab_figli text, p_col_fk_padre text, p_riga_padre_id bigint)
 RETURNS void
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_sql text;
BEGIN
    -- Ricalcola prezzo_unitario del padre come somma pesata
    -- dei figli attivi: SUM(prezzo_unitario * coeff_qta_snapshot).
    -- Se nessun figlio attivo, imposta 0 (COALESCE).
    v_sql := format(
        $q$UPDATE %1$I.%2$I
              SET prezzo_unitario = COALESCE((
                  SELECT SUM(c.prezzo_unitario * c.coeff_qta_snapshot)
                    FROM %1$I.%3$I c
                   WHERE c.%4$I = $1
                     AND c.attivo = TRUE
              ), 0)
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
IS 'Helper generica BoM CASO A: aggiorna prezzo_unitario della riga padre come SUM(figli.prezzo_unitario * coeff_qta_snapshot) WHERE attivo=TRUE. Parametrizzata su schema/tabella/FK per riuso su 5 sorgenti. Chiamata da trgfn_componenti_ricalcola_padre.';
```

---
{% include-markdown "signature-core.md" %}
