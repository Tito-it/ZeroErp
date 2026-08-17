{% include-markdown "it/dbzero/vendite/manual/vw_resi_da_accreditare.md" %}
# 🔍 View `vw_resi_da_accreditare`

> 📝 **Descrizione**
>
> Coda degli accrediti dovuti al cliente, derivata dalla PARTITA DI MERCE (vw_partite_merce, differenza &lt; 0). rev 2026-08-17 (partita generalizzata S4): la chiave passa da ordine_riga_id (NULLABLE) a ddt_riga_id (NOT NULL) — un reso su merce senza origine ordine produce finalmente un accredito calcolabile, mentre prima usciva dal conto senza errore. La finestra che scala i resi gia' serviti partiziona per RIGA DI DDT: un reso appartiene alla spedizione da cui la merce e' tornata. ⚠️ ordine_riga_id resta esposto ma PUO' ESSERE NULL: non e' piu' la chiave. ⚠️ Il filtro differenza &lt; 0 scarta i NULL per costruzione: un conto che non si applica (causale non fatturabile, kit non misurabile) non genera accrediti. rev 2026-07-26 INVARIATA: etichetta FACOLTATIVA solo se la merce puo' ANCORA tornare al cliente; l'importo viene dal conto della merce, che le rinunce non toccano — cambia la natura della quota, non il numero. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_da_accreditare
WITH (security_invoker=on) AS
WITH acc AS (
         SELECT p.ddt_riga_id,
            p.tenuti,
            p.fatturato AS fatturati,
            (- p.differenza) AS accredito_partita
           FROM vendite.vw_partite_merce p
          WHERE (p.differenza < (0)::numeric)
        ), dist AS (
         SELECT e.resi_riga_id,
            e.reso_id,
            e.ddt_riga_id,
            e.ordine_riga_id,
            e.riapre_residuo,
            e.quantita AS qta_resa,
            a.tenuti,
            a.fatturati,
            GREATEST((0)::numeric, LEAST(e.quantita, (a.accredito_partita - COALESCE(sum(e.quantita) OVER (PARTITION BY e.ddt_riga_id ORDER BY e.resi_riga_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), (0)::numeric)))) AS accredito_dovuto
           FROM (vendite.vw_resi_righe_effettive e
             JOIN acc a ON ((a.ddt_riga_id = e.ddt_riga_id)))
        )
 SELECT x.resi_riga_id,
    r.id AS reso_id,
    r.uid AS reso_uid,
    r.numero AS reso_numero,
    r.data,
    r.emittente_fiscale_id,
    r.billing_account_id,
    ba.codice AS ba_codice,
    r.destinatario_soggetto_ruolo_id,
    s_dest.ragione_sociale_completa AS destinatario_denominazione,
    rr.articolo_id,
    rr.descrizione,
    rr.quantita,
    rr.qta_operativa,
    rr.uom_operativa_id,
    rr.motivo,
    x.ddt_riga_id,
    dr.ddt_id,
    d.numero AS ddt_numero,
    x.ordine_riga_id,
    x.tenuti,
    x.fatturati,
    x.accredito_dovuto,
    (
        CASE
            WHEN (x.riapre_residuo AND (vendite.fn_resi_riga_residuo_riconsegna(x.resi_riga_id) > (0)::numeric)) THEN 'FACOLTATIVA'::text
            ELSE 'DOVUTA'::text
        END)::character varying AS etichetta
   FROM (((((((dist x
     JOIN vendite.resi_righe rr ON ((rr.id = x.resi_riga_id)))
     JOIN vendite.resi r ON ((r.id = x.reso_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = r.billing_account_id)))
     JOIN vendite.ddt_righe dr ON ((dr.id = x.ddt_riga_id)))
     JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
  WHERE (x.accredito_dovuto > (0)::numeric);
```


---
{% include-markdown "signature-core.md" %}
