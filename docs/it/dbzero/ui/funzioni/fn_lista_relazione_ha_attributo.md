{% include-markdown "it/dbzero/ui/manual/fn_lista_relazione_ha_attributo.md" %}
# ⚙️ Funzione `fn_lista_relazione_ha_attributo`

```sql
CREATE FUNCTION fn_lista_relazione_ha_attributo(p_schema character varying, p_relazione character varying, p_attributo character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION ui.fn_lista_relazione_ha_attributo(p_schema character varying, p_relazione character varying, p_attributo character varying)
 RETURNS boolean
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT (EXISTS ( SELECT 1
            FROM (pg_class c
              JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
           WHERE ((n.nspname = (fn_lista_relazione_ha_attributo.p_schema)::text) AND (c.relname = (fn_lista_relazione_ha_attributo.p_relazione)::text) AND (c.relkind = ANY (ARRAY['v'::"char", 'm'::"char", 'r'::"char", 'p'::"char"])) AND ((fn_lista_relazione_ha_attributo.p_attributo IS NULL) OR (EXISTS ( SELECT 1
                    FROM pg_attribute a
                   WHERE ((a.attrelid = c.oid) AND (a.attname = (fn_lista_relazione_ha_attributo.p_attributo)::text) AND (a.attnum > 0) AND (NOT a.attisdropped)))))))) AS "exists";
END

COMMENT ON FUNCTION ui.fn_lista_relazione_ha_attributo(p_schema character varying, p_relazione character varying, p_attributo character varying)
IS 'Vero se nello schema p_schema esiste la relazione p_relazione che una lista può leggere (vista, vista materializzata, tabella, tabella partizionata) e, con p_attributo valorizzato, se ha quella colonna. p_attributo NULL: si chiede solo la relazione. Schema o relazione NULL: falso. Sede unica della domanda «la relazione della lista ha il campo?»: la leggono i guard ui.trgfn_ui_lista_definizione_a10_valida_vista_sql e ui.trgfn_ui_lista_colonna_a10_valida_campo_sorgente, il presidio dbops.vw_liste_colonne_campo_orfano e il pgTAP del catalogo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
