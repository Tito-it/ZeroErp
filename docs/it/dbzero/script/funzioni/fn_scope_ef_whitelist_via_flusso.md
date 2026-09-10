# ⚙️ Funzione `fn_scope_ef_whitelist_via_flusso`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_flusso(p_auth_user_id integer, p_flusso_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_flusso(p_auth_user_id integer, p_flusso_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: come sopra, ma partendo da un FLUSSO — e' la chiave
    --   che portano pratiche.allegati_flussi e pratiche.note_flussi.
    -- ⭐ Delega alla sorella invece di ripetere la risalita: se un
    --   giorno cambia il modo in cui una pratica nomina il proprio
    --   emittente, si corregge in un posto solo.
    SELECT script.fn_scope_ef_whitelist_via_pratica(
        p_auth_user_id,
        (SELECT f.pratica_id
           FROM pratiche.flussi f
          WHERE f.id = p_flusso_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_flusso(p_auth_user_id integer, p_flusso_id bigint)
IS 'Come fn_scope_ef_whitelist_via_pratica ma a partire da un flusso: e'' la chiave che portano pratiche.allegati_flussi e pratiche.note_flussi. Delega alla sorella invece di ripetere la risalita alla testata.';
```

---
{% include-markdown "signature-core.md" %}
