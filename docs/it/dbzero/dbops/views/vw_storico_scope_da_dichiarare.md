{% include-markdown "it/dbzero/dbops/manual/vw_storico_scope_da_dichiarare.md" %}
# 🔍 View `vw_storico_scope_da_dichiarare`

> 📝 **Descrizione**
>
> ZERO — deve restare VUOTA. Il debito della mappa dello scope di storico (dbops.storico_scope_policy), in tre motivi: SENZA_RIGA (una madre col trigger di storico che nessuno ha ancora guardato), PROTETTA_NESSUNO (una madre in RLS dichiarata NESSUNO: la sua storia è ancora aperta, con la ragione dichiarata), RIGA_SENZA_MADRE (una riga di mappa senza più una madre col trigger: tabella cancellata o storicizzazione tolta). Il marcatore delle madri è il trigger. La madre di una riga si cerca sul catalogo (pg_class, pg_namespace; l'alias pg_temp è lo schema temporaneo della sessione), non con to_regclass, che solleva su uno schema senza USAGE per chi legge: la vista è security_invoker e non dipende dai privilegi del lettore sugli schemi. Porta nel digest settimanale ciò che il pgTAP db/pgtap/dbops/test-storico-scope-policy-v1.sql asserisce in CI (test 2, 4, 5 — e i test 29-33 provano che questa vista dica il vero su casi costruiti). Brief: brief-db-rls-storico-scope-congelato §4.2, §4d; brief-db-revisione-dbops §22.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_storico_scope_da_dichiarare
WITH (security_invoker=true) AS
WITH madri AS (
         SELECT DISTINCT c.oid AS madre_oid,
            (n.nspname)::text AS sch,
            (c.relname)::text AS tab,
            c.relrowsecurity AS rls
           FROM (((pg_trigger t
             JOIN pg_class c ON ((c.oid = t.tgrelid)))
             JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
             JOIN pg_proc p ON ((p.oid = t.tgfoid)))
          WHERE ((p.proname = 'trgfn_storico_generic'::name) AND (NOT t.tgisinternal))
        ), righe AS (
         SELECT m.id,
            m.schema_tabella,
            m.nome_tabella,
            m.modo,
            m.ragione,
            ( SELECT c.oid
                   FROM (pg_class c
                     JOIN pg_namespace n ON ((n.oid = c.relnamespace)))
                  WHERE ((c.relname = m.nome_tabella) AND ((n.nspname = m.schema_tabella) OR ((m.schema_tabella = 'pg_temp'::text) AND (n.oid = pg_my_temp_schema()))))) AS madre_oid
           FROM dbops.storico_scope_policy m
        )
 SELECT ((md.sch || '.'::text) || md.tab) AS madre,
    ('storico.'::text || md.tab) AS shadow,
    'SENZA_RIGA'::text AS motivo,
    'Madre col trigger di storico e nessuna riga in dbops.storico_scope_policy: nessuno ha ancora detto da dove si prende l''emittente'::text AS dettaglio
   FROM madri md
  WHERE (NOT (EXISTS ( SELECT 1
           FROM righe r
          WHERE (r.madre_oid = md.madre_oid))))
UNION ALL
 SELECT ((md.sch || '.'::text) || md.tab) AS madre,
    ('storico.'::text || md.tab) AS shadow,
    'PROTETTA_NESSUNO'::text AS motivo,
    ('Madre con la row level security accesa e modo NESSUNO — la sua storia non è protetta. Ragione dichiarata: '::text || COALESCE(r.ragione, '(nessuna)'::text)) AS dettaglio
   FROM (madri md
     JOIN righe r ON ((r.madre_oid = md.madre_oid)))
  WHERE (md.rls AND (r.modo = 'NESSUNO'::text))
UNION ALL
 SELECT ((r.schema_tabella || '.'::text) || r.nome_tabella) AS madre,
    ('storico.'::text || r.nome_tabella) AS shadow,
    'RIGA_SENZA_MADRE'::text AS motivo,
    (((('Riga di mappa (id '::text || r.id) || ', modo '::text) || r.modo) || ') senza una madre col trigger di storico: tabella cancellata o storicizzazione tolta, riga rimasta'::text) AS dettaglio
   FROM righe r
  WHERE ((r.madre_oid IS NULL) OR (NOT (EXISTS ( SELECT 1
           FROM madri md
          WHERE (md.madre_oid = r.madre_oid)))))
  ORDER BY 3, 1;
```

</div>


---
{% include-markdown "signature-core.md" %}
