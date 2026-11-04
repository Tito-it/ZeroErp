{% include-markdown "it/dbzero/dbops/manual/vw_codici_errore_da_dichiarare.md" %}
# 🔍 View `vw_codici_errore_da_dichiarare`

> 📝 **Descrizione**
>
> Misura canonica del "terzo lato" del presidio sui codici errore: ogni codice E_* nominato da un corpo plpgsql vivo (commenti esclusi) o passato da un trigger alla sua funzione negli ARGOMENTI (dbops.vw_codici_errore_argomenti_trigger, rev 20261103-03), con da_trigger = la funzione che lo nomina e' agganciata a un trigger, quindi sta sul percorso di una richiesta. ⚠️ VOLUTAMENTE LARGA: raccoglie ogni letterale, non solo quelli dentro una chiamata a fn_log_and_raise_error, perche' restringere perderebbe i codici che arrivano da espressione (gruppo C: v_motivi -&gt; 0 -&gt;&gt; 'codice') — 19 codici, 4 dei quali senza policy. Fra i due errori possibili si sceglie quello che si corregge guardando i falsi positivi, non quello che non si vede. Prima della rev 20261103-03 non vedeva i codici dei building block trigger che li ricevono da TG_ARGV (30 al 2026-11-03, D24). Non vede: codici costruiti per concatenazione, e i RAISE EXCEPTION diretti che non passano dall'helper. Brief: brief-db-be-terzo-lato-presidio-codici.md.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_codici_errore_da_dichiarare
WITH (security_invoker=true) AS
WITH sorgenti AS (
         SELECT m.m[1] AS codice,
            t.agganciata AS da_trigger,
            p.oid AS funzione_oid,
            (((n.nspname)::text || '.'::text) || (p.proname)::text) AS funzione
           FROM ((pg_proc p
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
             CROSS JOIN LATERAL ( SELECT (EXISTS ( SELECT 1
                           FROM pg_trigger tg
                          WHERE ((tg.tgfoid = p.oid) AND (NOT tg.tgisinternal)))) AS agganciata) t),
            LATERAL regexp_matches((dbops.fn_corpo_funzione(p.oid) COLLATE "C"), '''(E_[A-Z0-9_]+)'''::text, 'g'::text) m(m)
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prolang = ( SELECT pg_language.oid
                   FROM pg_language
                  WHERE (pg_language.lanname = 'plpgsql'::name))))
        UNION ALL
         SELECT a.codice,
            true,
            p.oid,
            (((n.nspname)::text || '.'::text) || (p.proname)::text)
           FROM ((dbops.vw_codici_errore_argomenti_trigger a
             JOIN pg_proc p ON ((p.oid = a.funzione_oid)))
             JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
          WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND (p.prolang = ( SELECT pg_language.oid
                   FROM pg_language
                  WHERE (pg_language.lanname = 'plpgsql'::name))))
        )
 SELECT codice,
    bool_or(da_trigger) AS da_trigger,
    count(DISTINCT funzione_oid) AS n_funzioni,
    string_agg(DISTINCT funzione, ', '::text ORDER BY funzione) AS funzioni
   FROM sorgenti s
  GROUP BY codice;
```

</div>


---
{% include-markdown "signature-core.md" %}
