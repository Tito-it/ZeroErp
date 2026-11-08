{% include-markdown "it/dbzero/dbops/manual/fn_nome_oggetto_dichiarato.md" %}
# ⚙️ Funzione `fn_nome_oggetto_dichiarato`

```sql
CREATE FUNCTION fn_nome_oggetto_dichiarato(p_nome text, p_template text, p_schema text, p_table text)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_nome_oggetto_dichiarato(p_nome text, p_template text, p_schema text, p_table text)
 RETURNS text
 LANGUAGE sql
 IMMUTABLE
AS $function$
    -- Scopo: il nome di un oggetto (trigger, vincolo) che un registro delle automazioni dichiara
    --   riga per riga (dbops.automation_delete_block, dbops.automazione_guard_utility_tipo_ruolo,
    --   dbops.automazione_overlap): il nome della riga, o il template del registro. Sede unica per
    --   chi confronta e chi crea.
    -- Parametri: text e non %TYPE: serve tre registri, ognuno con la sua colonna del nome.
    -- Regole: p_nome se valorizzato e non oltre i 63 caratteri, preso com'e';
    --   altrimenti p_template (o il nome troppo lungo) passa da dbops.fn_name_from_template,
    --   che accorcia con un hash oltre i 63 caratteri, cosi' il nome scritto e il nome cercato
    --   sono lo stesso.
    --   ⚠️ Un nome gia' risolto non si ripassa dal template: l'accorciamento lascia un doppio
    --   trattino basso, e il template lo ripulirebbe in un nome diverso. Per questo un nome
    --   che sta nei 63 caratteri esce intatto: la funzione e' idempotente sul suo risultato.
    --   Un trigger si riconosce dalla funzione e dagli argomenti: il nome serve a crearlo.
    SELECT CASE
             WHEN NULLIF(btrim(p_nome), '') IS NOT NULL
              AND length(btrim(p_nome)) <= 63
               THEN btrim(p_nome)
             ELSE dbops.fn_name_from_template(
                      COALESCE(NULLIF(btrim(p_nome), ''), p_template),
                      p_schema, p_table, NULL, NULL, NULL, NULL)
           END;
$function$

COMMENT ON FUNCTION dbops.fn_nome_oggetto_dichiarato(p_nome text, p_template text, p_schema text, p_table text)
IS 'Il nome di un oggetto (trigger, vincolo) che un registro delle automazioni dichiara riga per riga (dbops.automation_delete_block, dbops.automazione_guard_utility_tipo_ruolo, dbops.automazione_overlap): p_nome se valorizzato e non oltre i 63 caratteri (com''e''), altrimenti p_template o il nome troppo lungo, risolti e accorciati con un hash da dbops.fn_name_from_template. Idempotente sul suo risultato: un nome gia'' risolto, ripassato, esce uguale. Sede unica del nome per chi confronta e per chi crea; un trigger si riconosce dalla funzione e dagli argomenti, il nome serve a crearlo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
