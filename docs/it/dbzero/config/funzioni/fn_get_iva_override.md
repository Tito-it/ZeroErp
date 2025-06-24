{% include-markdown "it/dbzero/config/manual/fn_get_iva_override.md" %}
# ⚙️ Funzione `fn_get_iva_override`

```sql
CREATE FUNCTION fn_get_iva_override(p_codice_iva text, p_stato_id integer)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_get_iva_override(p_codice_iva text, p_stato_id integer)
 RETURNS TABLE(id_iva integer, codice_iva character, desc_iva character varying, desc_breve_iva character varying, aliquota_base numeric, assoggettamento_base character, aliquota numeric, assoggettamento character, id_natura_iva integer, conto_iva_acquisti_id integer, conto_iva_vendita_id integer, stato_id integer, stato_sigla character varying, data_insert timestamp without time zone, user_insert text, data_update timestamp without time zone, user_update text)
 LANGUAGE sql
 STABLE
AS $function$
  SELECT
    i.id,
    i.codice_iva,
    i.desc_iva,
    i.desc_breve_iva,
    i.aliquota_iva      AS aliquota_base,
    i.assoggettamento_iva AS assoggettamento_base,
    COALESCE(s.aliquota_override, i.aliquota_iva)         AS aliquota,
    COALESCE(s.assoggettamento_override, i.assoggettamento_iva) AS assoggettamento,
    i.natura_iva_id,
    i.conto_iva_acquisti_id,
    i.conto_iva_vendita_id,
    st.id                    AS stato_id,
    st.sigla_stato           AS stato_sigla,
    i.data_insert,
    i.user_insert,
    i.data_update,
    i.user_update
  FROM config.iva i
  JOIN config.stati st
    ON st.id = p_stato_id
  LEFT JOIN config.iva_stati s
    ON s.iva_id   = i.id
   AND s.stato_id = p_stato_id
  WHERE i.codice_iva = p_codice_iva;
$function$
```