{% include-markdown "it/dbzero/dbops/manual/vw_magazzino_dipendenze_inverse.md" %}
# 🔍 View `vw_magazzino_dipendenze_inverse`

> 📝 **Descrizione**
>
> CANCELLO — deve restare VUOTA. Gli oggetti dello schema magazzino che nominano uno schema di processo (vendite, acquisti, pagamenti: il perimetro e' scritto nella vista, uno schema nuovo si aggiunge qui). Il registro di magazzino e' un servizio dell'anello 2 (D-1): chi muove merce scrive il proprio posting e chiama la primitiva, e il registro non conosce i suoi consumatori. Due lenti: CATALOGO (pg_depend — FK, viste, default, policy, trigger, firme, corpi SQL standard) e CORPO (prosrc delle funzioni senza dipendenze registrate, commenti di riga tolti). Non vede gli argomenti dei trigger (i block_deact generati dal framework ATTIVO riflettono una FK che punta verso il registro: il verso giusto). Una riga fa rosso db/pgtap/magazzino/test-registro-non-nomina-i-consumatori-v1.sql, che gira in CI. security_invoker: legge solo il catalogo. Brief: brief-db-magazzino-registro-anello-interno (P-6).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_magazzino_dipendenze_inverse
WITH (security_invoker=true) AS
WITH schemi_processo AS (
         SELECT unnest(ARRAY['vendite'::name, 'acquisti'::name, 'pagamenti'::name]) AS nspname
        ), nominabili AS (
         SELECT 'pg_class'::regclass AS classid,
            c.oid,
            n.nspname
           FROM (pg_class c
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
          WHERE (n.nspname IN ( SELECT sp.nspname
                   FROM schemi_processo sp))
        UNION ALL
         SELECT 'pg_proc'::regclass AS regclass,
            p.oid,
            n.nspname
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE (n.nspname IN ( SELECT sp.nspname
                   FROM schemi_processo sp))
        UNION ALL
         SELECT 'pg_type'::regclass AS regclass,
            t.oid,
            n.nspname
           FROM (pg_type t
             JOIN pg_namespace n ON ((n.oid = t.typnamespace)))
          WHERE (n.nspname IN ( SELECT sp.nspname
                   FROM schemi_processo sp))
        ), dal_catalogo AS (
         SELECT o.identity AS oggetto,
            o.type AS tipo_oggetto,
            'CATALOGO'::text AS come,
            (x.nspname)::text AS schema_nominato,
            r.identity AS nominato
           FROM ((((((pg_depend d
             JOIN nominabili x ON ((((x.classid)::oid = d.refclassid) AND (x.oid = d.refobjid))))
             CROSS JOIN LATERAL pg_identify_object(d.classid, d.objid, d.objsubid) o(type, schema, name, identity))
             CROSS JOIN LATERAL pg_identify_object(d.refclassid, d.refobjid, d.refobjsubid) r(type, schema, name, identity))
             LEFT JOIN LATERAL ( SELECT rw.ev_class AS relid
                   FROM pg_rewrite rw
                  WHERE ((d.classid = ('pg_rewrite'::regclass)::oid) AND (rw.oid = d.objid))
                UNION ALL
                 SELECT tg.tgrelid
                   FROM pg_trigger tg
                  WHERE ((d.classid = ('pg_trigger'::regclass)::oid) AND (tg.oid = d.objid))
                UNION ALL
                 SELECT po.polrelid
                   FROM pg_policy po
                  WHERE ((d.classid = ('pg_policy'::regclass)::oid) AND (po.oid = d.objid))
                UNION ALL
                 SELECT ad.adrelid
                   FROM pg_attrdef ad
                  WHERE ((d.classid = ('pg_attrdef'::regclass)::oid) AND (ad.oid = d.objid))) portatore ON (true))
             LEFT JOIN pg_class pc ON ((pc.oid = portatore.relid)))
             LEFT JOIN pg_namespace pn ON ((pn.oid = pc.relnamespace)))
          WHERE ((d.deptype = ANY (ARRAY['n'::"char", 'a'::"char"])) AND (COALESCE(o.schema, (pn.nspname)::text) = 'magazzino'::text))
        ), sorgenti AS (
         SELECT p.oid,
            regexp_replace(p.prosrc, '--[^\n]*'::text, ''::text, 'g'::text) AS corpo
           FROM (pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname = 'magazzino'::name) AND (p.prosqlbody IS NULL))
        ), dal_corpo AS (
         SELECT (pg_identify_object(('pg_proc'::regclass)::oid, s.oid, 0)).identity AS oggetto,
            'function'::text AS tipo_oggetto,
            'CORPO'::text AS come,
            (sp.nspname)::text AS schema_nominato,
            m.nome[1] AS nominato
           FROM ((sorgenti s
             CROSS JOIN schemi_processo sp)
             CROSS JOIN LATERAL regexp_matches(s.corpo, (('\m('::text || (sp.nspname)::text) || '\.\w+)'::text), 'gi'::text) m(nome))
        )
 SELECT oggetto,
    tipo_oggetto,
    come,
    schema_nominato,
    string_agg(DISTINCT nominato, ', '::text ORDER BY nominato) AS nominati
   FROM ( SELECT dal_catalogo.oggetto,
            dal_catalogo.tipo_oggetto,
            dal_catalogo.come,
            dal_catalogo.schema_nominato,
            dal_catalogo.nominato
           FROM dal_catalogo
        UNION ALL
         SELECT dal_corpo.oggetto,
            dal_corpo.tipo_oggetto,
            dal_corpo.come,
            dal_corpo.schema_nominato,
            dal_corpo.nominato
           FROM dal_corpo) u
  GROUP BY oggetto, tipo_oggetto, come, schema_nominato
  ORDER BY oggetto, schema_nominato;
```

</div>


---
{% include-markdown "signature-core.md" %}
