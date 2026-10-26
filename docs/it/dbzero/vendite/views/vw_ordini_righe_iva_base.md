{% include-markdown "it/dbzero/vendite/manual/vw_ordini_righe_iva_base.md" %}
# 🔍 View `vw_ordini_righe_iva_base`

> 📝 **Descrizione**
>
> Vista base righe IVA ordini vendita. Espone righe ordine attive con quantita &gt; 0, imponibile lordo/sconto/imponibile netto a precisione piena e aliquota effettiva via config.fn_get_aliquota_iva (override stato emittente). Non somma direttamente i componenti BoM: il prezzo dei componenti confluisce nella riga padre tramite trigger, evitando doppio conteggio nel riepilogo IVA. Colonna sconto_percentuale (unificata 2026-06-05).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_ordini_righe_iva_base
WITH (security_invoker=on) AS
SELECT r.ordine_id,
    r.id AS riga_id,
    r.riga_nr,
    o.emittente_fiscale_id,
    s.stato_id AS stato_emittente_id,
    r.iva_id,
        CASE
            WHEN (r.iva_id IS NOT NULL) THEN config.fn_get_aliquota_iva(r.iva_id, s.stato_id)
            ELSE NULL::numeric
        END AS aliquota_effettiva,
    r.quantita,
    r.prezzo_unitario,
    r.sconto_percentuale,
    (r.quantita * r.prezzo_unitario) AS imponibile_lordo_full,
    (((r.quantita * r.prezzo_unitario) * COALESCE(r.sconto_percentuale, (0)::numeric)) / (100)::numeric) AS sconto_riga_full,
    script.fn_imponibile_riga(r.quantita, r.prezzo_unitario, r.sconto_percentuale) AS imponibile_riga_full,
    r.attivo,
    r.data_insert,
    r.data_update
   FROM ((((vendite.ordini_righe r
     JOIN vendite.ordini o ON ((o.id = r.ordine_id)))
     LEFT JOIN anagrafiche.emittenti_fiscali ef ON ((ef.id = o.emittente_fiscale_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr ON ((sr.id = ef.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s ON ((s.id = sr.soggetto_id)))
  WHERE ((r.attivo IS TRUE) AND (r.quantita > (0)::numeric));
```

</div>


---
{% include-markdown "signature-core.md" %}
