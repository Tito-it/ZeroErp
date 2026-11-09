{% include-markdown "it/dbzero/dbops/manual/vw_fk_da_decidere.md" %}
# 🔍 View `vw_fk_da_decidere`

> 📝 **Descrizione**
>
> Presidio della politica degli indici delle FK (dbops.fk_index_policy). caso DA_DECIDERE: una FK scoperta (dbops.vw_fk_senza_indice) senza riga o con la riga DA_DECIDERE, cioe' una FK su cui nessuno ha deciso; si decide con una riga CON_INDICE o SENZA_INDICE nel CSV della politica. caso CON_INDICE_NON_APPLICATA: una FK decisa CON_INDICE e ancora scoperta, perche' dbops.apply_fk_index_policy non e' girato o il comando non crea un indice che la copra. caso FUORI_AMBITO: una riga su uno schema che la politica non governa (dbops.fn_indici_schema_nell_ambito), che l'apply non applica. Una FK SENZA_INDICE e' decisa e non compare. decisione e' quella della riga (NULL se non c'e'), dll_command il comando proposto o scritto.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_fk_da_decidere AS
SELECT v.schema_name,
    v.table_name,
    v.constraint_name,
        CASE
            WHEN (v.decisione = 'CON_INDICE'::text) THEN 'CON_INDICE_NON_APPLICATA'::text
            ELSE 'DA_DECIDERE'::text
        END AS caso,
    v.decisione,
    v.create_index_suggestion AS dll_command
   FROM dbops.vw_fk_senza_indice v
  WHERE ((v.decisione IS NULL) OR (v.decisione = ANY (ARRAY['DA_DECIDERE'::text, 'CON_INDICE'::text])))
UNION ALL
 SELECT p.schema_name,
    p.table_name,
    p.constraint_name,
    'FUORI_AMBITO'::text AS caso,
    p.decisione,
    p.dll_command
   FROM dbops.fk_index_policy p
  WHERE (NOT dbops.fn_indici_schema_nell_ambito(p.schema_name));
```

</div>


---
{% include-markdown "signature-core.md" %}
