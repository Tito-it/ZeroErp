{% include-markdown "it/dbzero/dbops/manual/vw_bersagli_non_dichiarati.md" %}
# 🔍 View `vw_bersagli_non_dichiarati`

> 📝 **Descrizione**
>
> Il cancello del vocabolario dei bersagli: ogni tipo scritto in un corpo vivo leggibile, plpgsql o sql (dbops.fn_corpo_leggibile), che costruisce un bersaglio (commenti esclusi) e che config.tipi_entita non dichiara (motivo ASSENTE) o dichiara come ritirato (motivo OBSOLETO: un bersaglio nuovo verso una voce ritirata manda l'operatore dove il progetto ha smesso di andare). Rende sicuro far crescere il catalogo una voce per volta, insieme al messaggio che la usa: dimenticare la voce fa fallire la BUILD, non l'operatore. Gemella di dbops.vw_codici_errore_da_dichiarare, che legge il SORGENTE, e NON di dbops.vw_eventi_non_dichiarati, che legge i dati perche' quei codici li scrive Python: qui il bersaglio lo scrive il database, quindi la fonte giusta e' pg_proc. Una vista sui dati sarebbe cieca su un ambiente senza traffico, e da una lettura cieca non si fa dipendere una build. Non vede i tipi costruiti per concatenazione o passati in una variabile: stesso limite della gemella, e la stessa scelta (fra i due errori possibili, quello che si corregge guardando i falsi positivi). Il rubinetto non si chiude con una FK: il bersaglio vive in un jsonb, e il canale d'errore non smette di funzionare perche' manca una voce di catalogo: il bersaglio storto si perde (W_BERSAGLIO_MALFORMATO) e l'errore di dominio parte lo stesso.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_bersagli_non_dichiarati
WITH (security_invoker=true) AS
SELECT m.m[1] AS tipo,
        CASE
            WHEN (te.codice IS NULL) THEN 'ASSENTE'::text
            ELSE 'OBSOLETO'::text
        END AS motivo,
    count(DISTINCT p.oid) AS n_funzioni,
    string_agg(DISTINCT (((n.nspname)::text || '.'::text) || (p.proname)::text), ', '::text ORDER BY (((n.nspname)::text || '.'::text) || (p.proname)::text)) AS funzioni
   FROM (((pg_proc p
     JOIN pg_namespace n ON ((n.oid = p.pronamespace)))
     CROSS JOIN LATERAL regexp_matches((dbops.fn_corpo_funzione(p.oid) COLLATE "C"), '''tipo''\s*,\s*''([A-Z][A-Z0-9_]{0,30})'''::text, 'g'::text) m(m))
     LEFT JOIN config.tipi_entita te ON ((te.codice = m.m[1])))
  WHERE ((n.nspname <> ALL (ARRAY['pg_catalog'::name, 'information_schema'::name])) AND dbops.fn_corpo_leggibile(p.prolang) AND ((p.prosrc ~~ '%bersaglio%'::text) OR (p.prosqlbody IS NOT NULL)) AND ((te.codice IS NULL) OR script.fn_e_obsoleto(te.obsoleto_dal)))
  GROUP BY m.m[1],
        CASE
            WHEN (te.codice IS NULL) THEN 'ASSENTE'::text
            ELSE 'OBSOLETO'::text
        END;
```

</div>


---
{% include-markdown "signature-core.md" %}
