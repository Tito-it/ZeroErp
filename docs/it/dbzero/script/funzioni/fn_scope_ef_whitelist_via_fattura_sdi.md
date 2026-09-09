# ⚙️ Funzione `fn_scope_ef_whitelist_via_fattura_sdi`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_fattura_sdi(p_auth_user_id integer, p_sdi_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_fattura_sdi(p_auth_user_id integer, p_sdi_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: veste OPERATORE per gli eventi SDI, che portano la
    --   chiave della trasmissione e non quella della fattura.
    -- ⭐ Delega alla sorella di primo livello: la regola «come una
    --   fattura nomina il proprio emittente» resta in un posto solo.
    -- ⚠️ Trasmissione inesistente -> fattura NULL -> false a
    --   whitelist valorizzata: fail-closed.
    SELECT script.fn_scope_ef_whitelist_via_fattura(
        p_auth_user_id,
        (SELECT s.fattura_id
           FROM vendite.fatture_sdi s
          WHERE s.id = p_sdi_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_fattura_sdi(p_auth_user_id integer, p_sdi_id bigint)
IS 'Adattatore di scope a due livelli per vendite.fatture_sdi_eventi, veste OPERATORE: risale da fatture_sdi alla fattura e delega a script.fn_scope_ef_whitelist_via_fattura. STABLE e NON security definer, come gli altri fn_scope_*. Trasmissione inesistente -> fattura NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md';
```

---
{% include-markdown "signature-core.md" %}
