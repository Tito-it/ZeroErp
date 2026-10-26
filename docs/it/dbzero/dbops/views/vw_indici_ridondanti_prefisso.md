{% include-markdown "it/dbzero/dbops/manual/vw_indici_ridondanti_prefisso.md" %}
# 🔍 View `vw_indici_ridondanti_prefisso`

> 📝 **Descrizione**
>
> Indici btree ridondanti PER PREFISSO negli schemi in dbops.automation_scope: le colonne chiave di indice_ridondante sono la testa di quelle di coperto_da, con stessi opclass, collation, ordinamento e stesso predicato. PostgreSQL usa gia' coperto_da per ogni ricerca sulle colonne di indice_ridondante, controllo referenziale delle FK compreso. Complementare a dbops.vw_duplicate_indexes, che vede solo i duplicati esatti e per costruzione non puo' vedere questi. Esclude PK, UNIQUE, REPLICA IDENTITY e indici a supporto di un constraint: sono candidati al DROP, non si suggerisce di rimuovere cio' che impone integrita'. origine dice COME si rimuove: AUTOMAZIONE_FK = agire su dbops.fk_index_policy (un DROP secco verrebbe rifatto dal job settimanale), MANUALE = DROP in changeSet.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_indici_ridondanti_prefisso AS
WITH idx AS (
         SELECT ix.indexrelid,
            ix.indrelid,
            n.nspname AS schema_name,
            t.relname AS table_name,
            (i.relname)::text AS index_name,
            ix.indisunique,
            ix.indisprimary,
            ix.indisreplident,
            ix.indnkeyatts,
            ix.indnatts,
            pg_get_expr(ix.indpred, ix.indrelid) AS predicato,
            ( SELECT array_agg(((((((pg_get_indexdef(ix.indexrelid, k.k, false) || '|'::text) || (ix.indclass[(k.k - 1)])::text) || '|'::text) || (ix.indcollation[(k.k - 1)])::text) || '|'::text) || (ix.indoption[(k.k - 1)])::text) ORDER BY k.k) AS array_agg
                   FROM generate_series(1, (ix.indnkeyatts)::integer) k(k)) AS colsig
           FROM ((((pg_index ix
             JOIN pg_class i ON ((i.oid = ix.indexrelid)))
             JOIN pg_class t ON ((t.oid = ix.indrelid)))
             JOIN pg_namespace n ON ((n.oid = t.relnamespace)))
             JOIN pg_am am ON ((am.oid = i.relam)))
          WHERE ((i.relkind = 'i'::"char") AND (am.amname = 'btree'::name) AND ix.indisvalid AND ix.indisready AND (EXISTS ( SELECT 1
                   FROM dbops.automation_scope sc
                  WHERE (sc.schema_name = n.nspname))))
        )
 SELECT DISTINCT ON (a.indexrelid) a.schema_name,
    a.table_name,
    a.index_name AS indice_ridondante,
    b.index_name AS coperto_da,
        CASE
            WHEN (a.indnkeyatts = b.indnkeyatts) THEN 'DUPLICATO_ESATTO'::text
            ELSE 'PREFISSO'::text
        END AS motivo,
    pg_relation_size((a.indexrelid)::regclass) AS peso_byte,
    pg_size_pretty(pg_relation_size((a.indexrelid)::regclass)) AS peso,
    st.idx_scan,
        CASE
            WHEN (p.constraint_name IS NULL) THEN 'MANUALE'::text
            ELSE 'AUTOMAZIONE_FK'::text
        END AS origine,
    p.constraint_name AS policy_constraint_name,
    p.consentito AS policy_consentito
   FROM (((idx a
     JOIN idx b ON (((b.indrelid = a.indrelid) AND (b.indexrelid <> a.indexrelid) AND (b.colsig[1:array_length(a.colsig, 1)] = a.colsig) AND (NOT (a.predicato IS DISTINCT FROM b.predicato)) AND ((b.indnkeyatts > a.indnkeyatts) OR b.indisunique))))
     LEFT JOIN dbops.fk_index_policy p ON (((p.schema_name = a.schema_name) AND (p.table_name = a.table_name) AND (p.dll_command ~~* (('%'::text || a.index_name) || ' ON%'::text)))))
     LEFT JOIN pg_stat_user_indexes st ON ((st.indexrelid = a.indexrelid)))
  WHERE ((a.indisunique = false) AND (NOT a.indisprimary) AND (NOT a.indisreplident) AND (a.indnatts = a.indnkeyatts) AND (NOT (EXISTS ( SELECT 1
           FROM pg_constraint c
          WHERE (c.conindid = a.indexrelid)))))
  ORDER BY a.indexrelid, b.indisunique DESC, b.indnkeyatts, b.indexrelid;
```

</div>


---
{% include-markdown "signature-core.md" %}
