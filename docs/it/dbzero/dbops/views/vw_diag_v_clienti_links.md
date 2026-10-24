{% include-markdown "it/dbzero/dbops/manual/vw_diag_v_clienti_links.md" %}
# 🔍 View `vw_diag_v_clienti_links`

> 📝 **Descrizione**
>
> Diagnostica dei legami di un cliente: billing account, istanza utility, soggetto e tipo ruolo, con i tre flag ba_match_* che dicono dove il legame si rompe. security_invoker=on: legge nel perimetro di chi interroga. ⭐ rev 2026-08-29 (brief-db-be-iva-risolutore-e-regime-cliente, I0-B): fuori il blocco IVA (iva_id/iva_codice/iva_descrizione e il LEFT JOIN su config.iva). Era l'unica vista del database che leggeva anagrafiche.clienti.iva_id, colonna rimossa da 20260829-17 perché non aveva più un lavoro: l'aliquota la decide la merce, e il regime del soggetto passa da un titolo documentato. Il blocco non viene sostituito perché non rispondeva alla domanda di questa vista.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_diag_v_clienti_links
WITH (security_invoker=on) AS
SELECT c.id AS cliente_id,
    c.soggetto_ruolo_id AS cliente_soggetto_ruolo_id,
    c.istanza_utility_id AS cliente_istanza_utility_id,
    c.utility_id AS cliente_utility_id,
    c.billing_account_id AS cliente_billing_account_id,
    ba.id AS ba_id,
    ba.istanza_utility_id AS ba_istanza_utility_id,
    ba.soggetto_ruolo_id AS ba_soggetto_ruolo_id,
    ba.utility_id AS ba_utility_id,
    s.id AS soggetto_id,
    s.codice AS soggetto_codice,
    s.ragione_sociale,
    s.cognome,
    s.nome,
    iu.id AS istanza_id,
    iu.fittizia AS istanza_fittizia,
    u.id AS utility_id,
    u.codice_interno AS utility_codice_interno,
    u.descrizione AS utility_descrizione,
    tr.id AS tipo_ruolo_id,
    tr.codice_interno AS tipo_ruolo_codice_interno,
    tr.descrizione AS tipo_ruolo_descrizione,
    (ba.istanza_utility_id = c.istanza_utility_id) AS ba_match_istanza,
    (ba.soggetto_ruolo_id = c.soggetto_ruolo_id) AS ba_match_soggetto_ruolo,
    (ba.utility_id = c.utility_id) AS ba_match_utility
   FROM ((((((anagrafiche.clienti c
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = c.billing_account_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = c.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
     LEFT JOIN anagrafiche.istanze_utilities iu ON ((iu.id = c.istanza_utility_id)))
     LEFT JOIN config.utilities u ON ((u.id = c.utility_id)))
     LEFT JOIN config.tipi_ruoli tr ON ((tr.id = sr.tipo_ruolo_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
