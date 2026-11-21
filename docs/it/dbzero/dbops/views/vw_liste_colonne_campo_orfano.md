{% include-markdown "it/dbzero/dbops/manual/vw_liste_colonne_campo_orfano.md" %}
# 🔍 View `vw_liste_colonne_campo_orfano`

> 📝 **Descrizione**
>
> Presidio: le colonne di lista che leggono un campo che la loro sorgente non ha. DEVE restare a zero righe. Una riga per caso, con la causa: RELAZIONE_ASSENTE (una lista accesa dichiara una vista che nel suo schema non c'è), CAMPO_ASSENTE (una colonna VISTA, accesa o spenta, di una lista accesa ha un campo che la relazione non ha), LINEAGE_NON_DICHIARATA (una colonna LINEAGE su una lista che non dichiara legge_lineage), LINEAGE_SCONOSCIUTA (una colonna LINEAGE con un campo che la sintesi della lineage, vendite.vw_documento_lineage_sintesi_colonne, non produce). Vede ciò che i guard di ui non vedono: una vista che perde colonne con un DDL, una lista cambiata dal migrate. La relazione la chiede ui.fn_lista_relazione_ha_attributo, la regola dei guard.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_liste_colonne_campo_orfano
WITH (security_invoker=true) AS
SELECT ld.id AS lista_id,
    ld.codice AS lista_codice,
    NULL::integer AS colonna_id,
    NULL::character varying AS colonna_codice,
    NULL::character varying AS campo_sorgente,
    (((ld.schema_dati)::text || '.'::text) || (ld.vista_sql)::text) AS sorgente,
    'RELAZIONE_ASSENTE'::text AS causa
   FROM ui.lista_definizione ld
  WHERE (ld.attivo AND (ld.vista_sql IS NOT NULL) AND (NOT ui.fn_lista_relazione_ha_attributo(ld.schema_dati, ld.vista_sql, NULL::character varying)))
UNION ALL
 SELECT ld.id AS lista_id,
    ld.codice AS lista_codice,
    lc.id AS colonna_id,
    lc.codice AS colonna_codice,
    lc.campo_sorgente,
    (((ld.schema_dati)::text || '.'::text) || (ld.vista_sql)::text) AS sorgente,
    'CAMPO_ASSENTE'::text AS causa
   FROM (ui.lista_colonna lc
     JOIN ui.lista_definizione ld ON ((ld.id = lc.lista_id)))
  WHERE (ld.attivo AND (ld.vista_sql IS NOT NULL) AND (lc.origine_campo = 'VISTA'::ui.origine_campo_lista) AND (lc.campo_sorgente IS NOT NULL) AND ui.fn_lista_relazione_ha_attributo(ld.schema_dati, ld.vista_sql, NULL::character varying) AND (NOT ui.fn_lista_relazione_ha_attributo(ld.schema_dati, ld.vista_sql, lc.campo_sorgente)))
UNION ALL
 SELECT ld.id AS lista_id,
    ld.codice AS lista_codice,
    lc.id AS colonna_id,
    lc.codice AS colonna_codice,
    lc.campo_sorgente,
    'lineage'::text AS sorgente,
        CASE
            WHEN (NOT ld.legge_lineage) THEN 'LINEAGE_NON_DICHIARATA'::text
            ELSE 'LINEAGE_SCONOSCIUTA'::text
        END AS causa
   FROM (ui.lista_colonna lc
     JOIN ui.lista_definizione ld ON ((ld.id = lc.lista_id)))
  WHERE ((lc.origine_campo = 'LINEAGE'::ui.origine_campo_lista) AND ((NOT ld.legge_lineage) OR (NOT (EXISTS ( SELECT 1
           FROM vendite.vw_documento_lineage_sintesi_colonne sc
          WHERE (sc.colonna = (lc.campo_sorgente)::text))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
