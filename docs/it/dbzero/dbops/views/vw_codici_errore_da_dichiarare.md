{% include-markdown "it/dbzero/dbops/manual/vw_codici_errore_da_dichiarare.md" %}
# 🔍 View `vw_codici_errore_da_dichiarare`

> 📝 **Descrizione**
>
> Misura canonica del "terzo lato" del presidio sui codici errore: ogni codice E_* nominato da un corpo plpgsql vivo (commenti esclusi), con da_trigger = la funzione che lo nomina e' agganciata a un trigger, quindi sta sul percorso di una richiesta. ⚠️ VOLUTAMENTE LARGA: raccoglie ogni letterale, non solo quelli dentro una chiamata a fn_log_and_raise_error, perche' restringere perderebbe i codici che arrivano da espressione (gruppo C: v_motivi -&gt; 0 -&gt;&gt; 'codice') — 19 codici, 4 dei quali senza policy. Fra i due errori possibili si sceglie quello che si corregge guardando i falsi positivi, non quello che non si vede. Non vede: codici costruiti per concatenazione, e i RAISE EXCEPTION diretti che non passano dall'helper. Brief: brief-db-be-terzo-lato-presidio-codici.md.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_codici_errore_da_dichiarare
WITH (security_invoker=true) AS
SELECT m.m[1] AS codice,
    bool_or(t.agganciata) AS da_trigger,
    count(DISTINCT p.oid) AS n_funzioni,
    string_agg(DISTINCT (((n.nspname)::text || '.'::text) || (p.proname)::text), ', '::text ORDER BY (((n.nspname)::text || '.'::text) || (p.proname)::text)) AS funzioni
   FROM ((pg_proc p
     JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
     CROSS JOIN LATERAL ( SELECT (EXISTS ( SELECT 1
                   FROM pg_trigger tg
                  WHERE ((tg.tgfoid = p.oid) AND (NOT tg.tgisinternal)))) AS agganciata) t),
    LATERAL regexp_matches(regexp_replace(p.prosrc, '--[^\n]*'::text, ''::text, 'g'::text), '''(E_[A-Z0-9_]+)'''::text, 'g'::text) m(m)
  WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prolang = ( SELECT pg_language.oid
           FROM pg_language
          WHERE (pg_language.lanname = 'plpgsql'::name))))
  GROUP BY m.m[1];
```

</div>


---
{% include-markdown "signature-core.md" %}
