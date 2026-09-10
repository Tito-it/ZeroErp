# ⚙️ Funzione `fn_scope_ef_whitelist_via_commessa_attivita`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_commessa_attivita(p_auth_user_id integer, p_commessa_attivita_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_commessa_attivita(p_auth_user_id integer, p_commessa_attivita_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente della commessa a cui la riga appartiene.
    -- ⭐ Delega alla sorella `_via_commessa`, che e' la stessa
    --   che protegge vendite.commesse_attivita: cosi' il diario
    --   e la riga che racconta non possono rispondere in due modi.
    -- ⚠️ Riga inesistente -> commessa NULL -> la sorella risponde
    --   false quando la whitelist e' valorizzata: fail-closed,
    --   come tutta la famiglia.
    SELECT script.fn_scope_ef_whitelist_via_commessa(
        p_auth_user_id,
        (SELECT ca.commessa_id
           FROM vendite.commesse_attivita ca
          WHERE ca.id = p_commessa_attivita_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_commessa_attivita(p_auth_user_id integer, p_commessa_attivita_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.commesse_attivita (oggi: commesse_attivita_log): risale da commessa_attivita_id alla commessa e delega a script.fn_scope_ef_whitelist_via_commessa — la stessa che protegge commesse_attivita, cosi'' il diario e la riga che racconta non possono divergere. STABLE e NON security definer, come gli altri fn_scope_*. ⛔ Stessa firma di _via_commessa e chiavi entrambe bigint: scambiarle compila e gira, e nel verso negativo sembra pure funzionare — lo presidia il verso POSITIVO del pgTAP. Riga inesistente -> commessa NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md §11.15';
```

---
{% include-markdown "signature-core.md" %}
