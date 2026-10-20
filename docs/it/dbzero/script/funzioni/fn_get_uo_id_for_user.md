{% include-markdown "it/dbzero/script/manual/fn_get_uo_id_for_user.md" %}
# ⚙️ Funzione `fn_get_uo_id_for_user`

```sql
CREATE FUNCTION fn_get_uo_id_for_user(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_uo_id_for_user(p_auth_user_id integer)
 RETURNS integer
 LANGUAGE sql
 STABLE
AS $function$
    -- Catena di risoluzione:
    --   1) identita_digitali attiva per auth_user_id, ruolo
    --      OPERATORE (solo gli operatori hanno una RU con UO)
    --   2) risorse_umane attiva con stesso soggetto_ruolo
    --   3) ritorna ru.unita_organizzativa_id (puo' essere NULL)
    -- ORDER BY + LIMIT 1: determinismo in caso raro di piu' RU
    -- attive storicamente (prende la piu' recente per valido_dal).
    SELECT ru.unita_organizzativa_id
      FROM anagrafiche.identita_digitali id
      JOIN anagrafiche.risorse_umane     ru
        ON ru.soggetto_ruolo_id = id.soggetto_ruolo_id
     WHERE id.auth_user_id      = p_auth_user_id
       AND id.ruolo_applicativo = 'OPERATORE'
       AND id.attivo            = true
       AND ru.attivo            = true
     ORDER BY ru.valido_dal DESC
     LIMIT 1;
$function$

COMMENT ON FUNCTION script.fn_get_uo_id_for_user(p_auth_user_id integer)
IS 'Ritorna unita_organizzativa_id dell''operatore autenticato o NULL se non operatore / senza RU attiva / senza UO / inesistente. Catena: auth_user -> identita_digitali (OPERATORE) -> risorse_umane. STABLE, inlineable.';
```

</div>

---
{% include-markdown "signature-core.md" %}
