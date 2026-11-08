{% include-markdown "it/dbzero/vendite/manual/vw_resi_da_riconsegnare.md" %}
# 🔍 View `vw_resi_da_riconsegnare`

> 📝 **Descrizione**
>
> Elenco operativo delle righe reso ancora da ri-spedire al cliente (resi in cui la merce e' rientrata, dal BB script.vw_stati_doc_reso_merce_rientrata; tipo riapre_residuo, residuo &gt; 0). rev 2026-07-26 (brief-db-chiusura-riconsegna-reso-definitivo S4.2-bis): qta_residua viene dall'helper unico vendite.fn_resi_riga_residuo_riconsegna, che sottrae ANCHE le quote rinunciate - una riga dichiarata definitiva ha residuo 0 e sparisce da questo elenco, che era il punto del brief. Nuove: qta_rinunciata (consuntivo) e lo stato RINUNCIATA (residuo 0 con almeno una rinuncia, distinto da COMPLETATA = tutto ri-spedito). rev 2026-11-09 (brief-db-sorgente-documento-e-riga lotto M, D29): lo stato dal BB, non dal letterale CONFERMATO.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_da_riconsegnare
WITH (security_invoker=on) AS
SELECT rr.id AS resi_riga_id,
    r.id AS reso_id,
    r.uid AS reso_uid,
    r.numero AS reso_numero,
    r.data,
    r.emittente_fiscale_id,
    r.billing_account_id,
    r.destinatario_soggetto_ruolo_id,
    s_dest.ragione_sociale_completa AS destinatario_denominazione,
    rr.articolo_id,
    rr.descrizione,
    rr.uom_operativa_id,
    rr.quantita AS qta_resa,
    COALESCE(ric.tot, (0)::numeric) AS qta_riconsegnata,
    vendite.fn_resi_riga_residuo_riconsegna(rr.id) AS qta_residua,
        CASE
            WHEN ((vendite.fn_resi_riga_residuo_riconsegna(rr.id) = (0)::numeric) AND (COALESCE(rin.tot, (0)::numeric) > (0)::numeric)) THEN 'RINUNCIATA'::text
            WHEN ((COALESCE(ric.tot, (0)::numeric) = (0)::numeric) AND (COALESCE(rin.tot, (0)::numeric) = (0)::numeric)) THEN 'DA_RICONSEGNARE'::text
            WHEN (vendite.fn_resi_riga_residuo_riconsegna(rr.id) > (0)::numeric) THEN 'PARZIALE'::text
            ELSE 'COMPLETATA'::text
        END AS stato_riconsegna,
    rr.ddt_riga_id,
    dr.ddt_id,
    d.numero AS ddt_numero,
    rr.ordine_riga_id,
    COALESCE(rin.tot, (0)::numeric) AS qta_rinunciata
   FROM (((((((((vendite.resi_righe rr
     JOIN vendite.resi r ON ((r.id = rr.reso_id)))
     JOIN script.vw_stati_doc_reso_merce_rientrata sr ON ((sr.id = r.stato_doc_reso_id)))
     JOIN config.tipi_reso tr ON ((tr.id = rr.tipo_reso_id)))
     JOIN vendite.ddt_righe dr ON ((dr.id = rr.ddt_riga_id)))
     JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN ( SELECT resi_righe_riconsegne.resi_riga_id,
            sum(resi_righe_riconsegne.qta) AS tot
           FROM vendite.resi_righe_riconsegne
          GROUP BY resi_righe_riconsegne.resi_riga_id) ric ON ((ric.resi_riga_id = rr.id)))
     LEFT JOIN ( SELECT resi_righe_rinunce.resi_riga_id,
            sum(resi_righe_rinunce.qta) AS tot
           FROM vendite.resi_righe_rinunce
          GROUP BY resi_righe_rinunce.resi_riga_id) rin ON ((rin.resi_riga_id = rr.id)))
  WHERE (sr.merce_rientrata AND (tr.riapre_residuo = true) AND (rr.attivo IS TRUE) AND (vendite.fn_resi_riga_residuo_riconsegna(rr.id) > (0)::numeric));
```

</div>


---
{% include-markdown "signature-core.md" %}
