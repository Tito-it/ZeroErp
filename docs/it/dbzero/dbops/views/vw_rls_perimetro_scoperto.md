{% include-markdown "it/dbzero/dbops/manual/vw_rls_perimetro_scoperto.md" %}
# 🔍 View `vw_rls_perimetro_scoperto`

> 📝 **Descrizione**
>
> Le tabelle che dovrebbero filtrare e non filtrano, per due criteri indipendenti letti dal catalogo di PostgreSQL: FIGLIA_DI_TABELLA_PROTETTA (ha una FK verso una tabella con la row level security accesa) e POLICY_INERTE (porta una policy e la row level security spenta). ⛔ L'invariante NON e' «la vista e' vuota»: e' «nessuna riga fuori da DEBITO_DICHIARATO» — un debito dichiarato in dbops.rls_perimetro_debito e' una riga attesa, un NON_DICHIARATO e' un allarme, un DEBITO_ESTINTO e' una riga di registro da togliere. ⚠️ FORCE ROW LEVEL SECURITY non entra nel criterio: in questo database nessuna tabella lo usa, e l'applicazione non e' owner. Presidio: db/pgtap/rls/test-rls-perimetro-scoperto.sql. Brief: brief-db-perimetro-emittente-righe-documento §8.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_rls_perimetro_scoperto AS
WITH stato_rel AS (
         SELECT c.oid,
            (n.nspname)::text AS schema_tabella,
            (c.relname)::text AS nome_tabella,
            c.relrowsecurity AS rls_attiva,
            (EXISTS ( SELECT 1
                   FROM pg_policy pol
                  WHERE (pol.polrelid = c.oid))) AS ha_policy
           FROM (pg_class c
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
          WHERE ((c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])) AND (n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])))
        ), figlie AS (
         SELECT k.conrelid AS oid,
            string_agg(DISTINCT (((pn.nspname)::text || '.'::text) || (p.relname)::text), ', '::text) AS padri_in_rls
           FROM ((pg_constraint k
             JOIN pg_class p ON (((p.oid = k.confrelid) AND p.relrowsecurity)))
             JOIN pg_namespace pn ON ((pn.oid = p.relnamespace)))
          WHERE (k.contype = 'f'::"char")
          GROUP BY k.conrelid
        ), perimetro AS (
         SELECT 'FIGLIA_DI_TABELLA_PROTETTA'::text AS criterio,
            s.schema_tabella,
            s.nome_tabella,
            f.padri_in_rls,
                CASE
                    WHEN ((NOT s.ha_policy) AND (NOT s.rls_attiva)) THEN 'la policy e l''accensione: la tabella non filtra in nessun modo'::text
                    WHEN (s.ha_policy AND (NOT s.rls_attiva)) THEN 'l''accensione: la policy c''e'' ma la row level security e'' spenta, quindi non filtra niente'::text
                    ELSE 'la policy: la row level security e'' accesa e nessuna policy la accompagna (deny-all)'::text
                END AS manca
           FROM (figlie f
             JOIN stato_rel s ON ((s.oid = f.oid)))
          WHERE (NOT (s.rls_attiva AND s.ha_policy))
        UNION ALL
         SELECT 'POLICY_INERTE'::text AS text,
            s.schema_tabella,
            s.nome_tabella,
            NULL::text AS text,
            'l''accensione: la policy e'' scritta e la row level security e'' spenta, quindi non viene applicata'::text AS text
           FROM stato_rel s
          WHERE (s.ha_policy AND (NOT s.rls_attiva))
        )
 SELECT p.criterio,
    p.schema_tabella,
    p.nome_tabella,
    p.padri_in_rls,
    p.manca,
        CASE
            WHEN (d.id IS NULL) THEN 'NON_DICHIARATO'::text
            ELSE 'DEBITO_DICHIARATO'::text
        END AS stato,
    d.ragione,
    d.data_registrazione
   FROM (perimetro p
     LEFT JOIN dbops.rls_perimetro_debito d ON (((d.criterio = p.criterio) AND (d.schema_tabella = p.schema_tabella) AND (d.nome_tabella = p.nome_tabella))))
UNION ALL
 SELECT d.criterio,
    d.schema_tabella,
    d.nome_tabella,
    NULL::text AS padri_in_rls,
    'niente: la tabella non e'' piu'' scoperta per questo criterio, o non esiste piu''. La riga va tolta dal CSV del registro'::text AS manca,
    'DEBITO_ESTINTO'::text AS stato,
    d.ragione,
    d.data_registrazione
   FROM dbops.rls_perimetro_debito d
  WHERE (NOT (EXISTS ( SELECT 1
           FROM perimetro p
          WHERE ((p.criterio = d.criterio) AND (p.schema_tabella = d.schema_tabella) AND (p.nome_tabella = d.nome_tabella)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
