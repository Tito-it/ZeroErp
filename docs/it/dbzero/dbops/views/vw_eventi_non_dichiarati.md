# 🔍 View `vw_eventi_non_dichiarati`

> 📝 **Descrizione**
>
> I codici evento finiti in vendite.event_log e assenti da config.eventi_dominio. ⚠️ NON e' il gemello di dbops.vw_codici_errore_da_dichiarare, e non puo' esserlo: quella legge pg_proc perche' i codici errore li solleva il DATABASE, mentre i codici evento li scrive PYTHON — una vista su pg_proc tornerebbe vuota per sempre, cioe' direbbe sempre «tutto a posto» guardando nel posto sbagliato. Il cancello vero e' lato backend (consegna BE-9), dove i codici sono scritti. ⭐ Questa fa un lavoro complementare: la deriva GIA' AVVENUTA, che nessun controllo sul sorgente vede — un codice costruito a runtime, o scritto da qualcosa che non e' il backend. ⚠️ E' data-dependent: su un ambiente senza traffico e' cieca. E' una spia da guardare, non un semaforo che ferma. ⛔ E il rubinetto NON si chiude con una FK su event_code: sarebbe il diario che smette di scrivere per un problema di configurazione, cioe' la D-12 violata.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_eventi_non_dichiarati
WITH (security_invoker=true) AS
SELECT event_code,
    count(*) AS righe,
    min(event_time) AS primo,
    max(event_time) AS ultimo,
    count(DISTINCT entity_type) AS tipi_entita_toccati
   FROM vendite.event_log e
  WHERE (NOT (EXISTS ( SELECT 1
           FROM config.eventi_dominio ed
          WHERE (ed.codice = e.event_code))))
  GROUP BY event_code;
```

</div>


---
{% include-markdown "signature-core.md" %}
