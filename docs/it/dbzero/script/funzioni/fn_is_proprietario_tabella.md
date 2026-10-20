{% include-markdown "it/dbzero/script/manual/fn_is_proprietario_tabella.md" %}
# ⚙️ Funzione `fn_is_proprietario_tabella`

```sql
CREATE FUNCTION fn_is_proprietario_tabella(p_tabella regclass)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_is_proprietario_tabella(p_tabella regclass)
 RETURNS boolean
 LANGUAGE sql
 STABLE PARALLEL SAFE
AS $function$
    -- Scopo: dire se chi esegue e' il proprietario della tabella (o ne ha i
    --   privilegi). Il proprietario si legge da pg_class, mai scritto a mano.
    --   Nessuna riga (NULL, tabella inesistente) -> false: fail-closed.
    SELECT COALESCE(
               (SELECT pg_catalog.pg_has_role(current_user, c.relowner, 'USAGE')
                  FROM pg_catalog.pg_class c
                 WHERE c.oid = p_tabella),
               false);
$function$

COMMENT ON FUNCTION script.fn_is_proprietario_tabella(p_tabella regclass)
IS 'Check pura (non solleva): true se chi esegue l''istruzione (current_user) e'' il proprietario della tabella o ne ha i privilegi (pg_has_role USAGE: anche un superuser). Il proprietario si legge da pg_class, non si scrive a mano. E'' il modo in cui un guard riconosce di essere attraversato da un verbo SECURITY DEFINER (modello «una scrittura = un verbo», brief-db-permesso-nel-verbo-di-scrittura) e non da una scrittura diretta dell''applicazione. Tabella NULL o inesistente -> false (fail-closed). SECURITY INVOKER per costruzione: una DEFINER vedrebbe il proprio proprietario e direbbe si'' a chiunque. Un trigger passa TG_RELID. Consumatori: i due guard dei documenti interni di magazzino (porta POSTED, righe in CONFIRM) e ui.trgfn_lista_definizione_guard_multi_emittente. Brief: brief-db-magazzino-verbi-con-permesso, D-V1 / P-7.';
```

</div>

---
{% include-markdown "signature-core.md" %}
