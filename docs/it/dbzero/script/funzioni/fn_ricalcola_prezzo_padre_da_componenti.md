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
    -- Ricalcola prezzo_unitario del padre dai figli attivi.
    -- Se almeno 1 figlio attivo ha prezzo_unitario NULL (pending
    -- valorizzazione manuale) -> padre = NULL.
    -- Se nessun figlio attivo -> padre = 0 (COALESCE).
    -- Nota: SUM di PostgreSQL ignora NULL; il CASE e' necessario
    -- per propagare lo stato "pending" al padre.
    v_sql := format(
        $q$UPDATE %1$I.%2$I
              SET prezzo_unitario = (
                  SELECT
                      CASE
                          WHEN COUNT(*) FILTER (WHERE c.prezzo_unitario IS NULL) > 0
                              THEN NULL
                          ELSE COALESCE(SUM(c.prezzo_unitario * c.coeff_qta_snapshot), 0)
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
IS 'Helper generica BoM CASO A: aggiorna prezzo_unitario della riga padre. Se almeno 1 componente attivo ha prezzo NULL (pending), imposta NULL al padre. Se nessun componente attivo: 0. rev 12-05-2026: NULL propagation (SUM PostgreSQL ignora NULL, serve CASE esplicito).';
```

---
{% include-markdown "signature-core.md" %}
