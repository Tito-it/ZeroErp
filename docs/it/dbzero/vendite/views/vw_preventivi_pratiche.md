{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_pratiche.md" %}
# 🔍 View `vw_preventivi_pratiche`

> 📝 **Descrizione**
>
> Le pratiche collegate ai preventivi di vendita, una riga per link in pratiche.pratiche_sorgenti: il preventivo (id, uid, numero), il link (pratica_sorgente_id, l'id della riga di pratiche_sorgenti, con ruolo, riga e meta), la pratica con stato, tipo di prestazione e date. Il link si trova sulla chiave del modello: il preventivo ha key_selector uid, quindi pratiche_sorgenti.sorgente_uid = preventivi.uid. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_pratiche
WITH (security_invoker=on) AS
SELECT p.id AS preventivo_id,
    p.uid AS preventivo_uid,
    p.numero AS preventivo_numero,
    ps.id AS pratica_sorgente_id,
    ps.ruolo_link,
    ps.sorgente_riga,
    pr.id AS pratica_id,
    pr.codice AS pratica_codice,
    pr.descrizione AS pratica_descrizione,
    sp.codice AS stato_codice,
    sp.descrizione AS stato_descrizione,
    tp.codice AS tipo_prestazione_codice,
    tp.descrizione AS tipo_prestazione_descrizione,
    pr.data_apertura,
    pr.data_scadenza,
    ps.meta AS sorgente_meta
   FROM (((((vendite.preventivi p
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
     JOIN pratiche.pratiche_sorgenti ps ON (((ps.sorgente_tipo_id = s.id) AND (ps.sorgente_uid = p.uid))))
     JOIN pratiche.pratiche pr ON ((pr.id = ps.pratica_id)))
     LEFT JOIN config.stati_pratiche sp ON ((sp.id = pr.stato_id)))
     LEFT JOIN pratiche.tipi_prestazione tp ON ((tp.id = pr.tipo_prestazione_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
