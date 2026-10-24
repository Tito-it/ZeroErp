{% include-markdown "it/dbzero/anagrafiche/manual/vw_clienti_lista.md" %}
# 🔍 View `vw_clienti_lista`

> 📝 **Descrizione**
>
> Vista flat clienti per la lista UI (anagrafiche.clienti). Espone anagrafica soggetto (incl. id_fiscale_univoco_cf_piva), codice BA, servizio, stato e date del ciclo di vita. stato_codice_interno = codice_interno (logica), stato_codice = codice (display). Sorgente dati per ui.lista_definizione codice='anagrafiche.clienti'.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_clienti_lista
WITH (security_invoker=on) AS
SELECT cl.id,
    cl.soggetto_ruolo_id,
    cl.istanza_utility_id,
    cl.billing_account_id,
    s.id AS soggetto_id,
    s.codice AS soggetto_codice,
    ba.codice AS ba_codice,
    s.ragione_sociale_completa,
    s.codice_fiscale,
    s.partita_iva,
    s.id_fiscale_univoco_cf_piva,
    u.id AS utility_id,
    u.descrizione AS utility_descrizione,
    sc.id AS stato_cliente_id,
    sc.codice_interno AS stato_codice_interno,
    sc.codice AS stato_codice,
    sc.descrizione_breve AS stato_descrizione,
    cl.data_attivazione,
    cl.data_sospensione,
    cl.data_riattivazione,
    cl.data_chiusura
   FROM (((((anagrafiche.clienti cl
     JOIN anagrafiche.istanze_utilities iu ON ((iu.id = cl.istanza_utility_id)))
     JOIN anagrafiche.soggetti s ON ((s.id = iu.soggetto_id)))
     JOIN anagrafiche.billing_account ba ON ((ba.id = cl.billing_account_id)))
     JOIN config.utilities u ON ((u.id = cl.utility_id)))
     JOIN config.stati_cliente sc ON ((sc.id = cl.stato_cliente_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
