{% include-markdown "it/dbzero/script/manual/fn_scope_ef_whitelist_via_magazzino.md" %}
# ⚙️ Funzione `fn_scope_ef_whitelist_via_magazzino`

```sql
CREATE FUNCTION fn_scope_ef_whitelist_via_magazzino(p_auth_user_id integer, p_magazzino_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_ef_whitelist_via_magazzino(p_auth_user_id integer, p_magazzino_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: dire se l'operatore ha nel proprio perimetro l'emittente
    --   del magazzino indicato. E' la risalita che tutto il dominio usa.
    -- ⚠️ Magazzino inesistente o fuori perimetro (sotto RLS non si
    --   vede) -> emittente NULL -> la canonica risponde false a
    --   whitelist valorizzata: fail-closed.
    SELECT script.fn_scope_ef_whitelist(
        p_auth_user_id,
        (SELECT m.emittente_fiscale_id
           FROM magazzino.magazzini m
          WHERE m.id = p_magazzino_id)
    );
$function$

COMMENT ON FUNCTION script.fn_scope_ef_whitelist_via_magazzino(p_auth_user_id integer, p_magazzino_id bigint)
IS 'Adattatore di scope della famiglia magazzino, L''ANCORA: risale da magazzini.id a emittente_fiscale_id e delega a script.fn_scope_ef_whitelist. STABLE e NON security definer come le sorelle via_*. Magazzino inesistente o fuori perimetro (sotto RLS non si vede) -> emittente NULL -> false a whitelist valorizzata (fail-closed). Lo usano le policy di ubicazioni, movimenti, movimenti_attesi, valore_giacenza, inventari, rettifiche, trasferimenti e, per delega, le derivate. Brief: brief-db-magazzino-lotto-1-terreno-vuoto, sezione 4.10.';
```

---
{% include-markdown "signature-core.md" %}
