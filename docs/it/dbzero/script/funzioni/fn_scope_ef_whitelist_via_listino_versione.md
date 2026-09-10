# ⚙️ Funzione `fn_scope_ef_whitelist_via_listino_versione`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_listino_versione(p_auth_user_id integer, p_versione_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_listino_versione(p_auth_user_id integer, p_versione_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro
    --   l'emittente del listino a cui la versione appartiene.
    -- ⭐ Delega alla sorella `_via_listino`, che e' la stessa che
    --   protegge vendite.listini_versioni: cosi' la riga e la sua
    --   versione non possono rispondere in due modi.
    -- ⚠️ Versione inesistente -> listino NULL -> la sorella
    --   risponde false quando la whitelist e' valorizzata:
    --   fail-closed, come tutta la famiglia.
    SELECT script.fn_scope_ef_whitelist_via_listino(
        p_auth_user_id,
        (SELECT v.listino_id
           FROM vendite.listini_versioni v
          WHERE v.id = p_versione_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_listino_versione(p_auth_user_id integer, p_versione_id bigint)
IS 'Adattatore di scope per i satelliti di vendite.listini_versioni (listini_righe, listini_righe_componenti): risale da listino_versione_id al listino e delega a script.fn_scope_ef_whitelist_via_listino — la stessa che protegge listini_versioni, cosi'' la riga e la sua versione non possono divergere. STABLE e NON security definer, come gli altri fn_scope_*. Versione inesistente -> listino NULL -> false a whitelist valorizzata (fail-closed). Brief: brief-db-perimetro-emittente-righe-documento.md §11.11';
```

---
{% include-markdown "signature-core.md" %}
