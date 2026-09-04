# 🔍 View `vw_processi_dominio_senza_difesa`

> 📝 **Descrizione**
>
> LIVELLO 2 del presidio sui processi: bersagli di processi DOMINIO che HANNO il percorso verso l'emittente ma non hanno la difesa che lo applica — policy RLS (lettura) e/o write-guard trgfn_guard_emittente_scope (scrittura). ⚠️ E' un registro di DEBITO, non un errore: deve CALARE, non essere vuoto domani. Dove compare una riga, il «Caso A» non vale — un filtro dimenticato su quella tabella passerebbe invece di fermarsi da solo. ⛔ I processi PGAGENT NON sono esclusi: un DOMINIO su pgAgent e' l'anomalia da sanare, e i suoi bersagli saranno raggiunti dal ruolo applicativo appena migra. Brief: brief-db-processi-automatici-identita-e-perimetro §8.

```sql
CREATE OR REPLACE VIEW dbops.vw_processi_dominio_senza_difesa AS
WITH bersagli AS (
         SELECT p.codice AS processo_codice,
            b.schema_tabella,
            b.nome_tabella,
            b.emittente_via,
            c.oid AS rel_oid
           FROM (((dbops.processi p
             JOIN dbops.processi_bersagli b ON ((b.processo_id = p.id)))
             JOIN pg_class c ON ((c.relname = b.nome_tabella)))
             JOIN pg_namespace n ON (((n.oid = c.relnamespace) AND (n.nspname = b.schema_tabella))))
          WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL) AND (b.emittente_via IS NOT NULL) AND (c.relkind = ANY (ARRAY['r'::"char", 'p'::"char"])))
        ), difese AS (
         SELECT b.processo_codice,
            b.schema_tabella,
            b.nome_tabella,
            b.emittente_via,
            b.rel_oid,
            (EXISTS ( SELECT 1
                   FROM pg_policy pol
                  WHERE (pol.polrelid = b.rel_oid))) AS ha_policy,
            (EXISTS ( SELECT 1
                   FROM (pg_trigger t
                     JOIN pg_proc pr ON ((pr.oid = t.tgfoid)))
                  WHERE ((t.tgrelid = b.rel_oid) AND (NOT t.tgisinternal) AND (pr.proname = 'trgfn_guard_emittente_scope'::name)))) AS ha_guard
           FROM bersagli b
        )
 SELECT processo_codice,
    schema_tabella,
    nome_tabella,
    emittente_via,
        CASE
            WHEN ((NOT ha_policy) AND (NOT ha_guard)) THEN 'policy RLS e write-guard'::text
            WHEN (NOT ha_policy) THEN 'policy RLS (lettura scoperta)'::text
            ELSE 'write-guard (scrittura scoperta)'::text
        END AS manca
   FROM difese
  WHERE ((NOT ha_policy) OR (NOT ha_guard));
```


---
{% include-markdown "signature-core.md" %}
