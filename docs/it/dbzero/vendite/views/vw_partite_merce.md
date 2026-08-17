{% include-markdown "it/dbzero/vendite/manual/vw_partite_merce.md" %}
# 🔍 View `vw_partite_merce`

> 📝 **Descrizione**
>
> La partita di merce (brief-design-partita-merce-generalizzata S2, rev 2026-08-17 correzione ri-consegna): UNA riga per riga di DDT attiva su documento non abortito e almeno EMESSO (decisione D1). La riga d'ordine e' l'ORIGINE, nullable: righe manuali e DDT standalone hanno una partita come le altre. ⚠️ Una riga di RI-CONSEGNA NON e' una partita nuova — quei pezzi sono gia' contati sulla partita da cui il reso e' venuto, e contarli due volte li farebbe FATTURARE due volte (il «bug 1a» chiuso a luglio). La ri-consegna rientra nel `consegnato` dell'ORIGINE quando il documento e' emesso, e resta `in_riconsegna` finche' e' in bozza: lo stesso fatto in due momenti. La riga di ri-consegna resta visibile con e_riconsegna=true, differenza NULL e stato RICONSEGNA, cosi' il pannello del suo DDT non e' vuoto. fatturato = corsia DDT + quota allocata della corsia ORD (greedy oldest-first, capienza = CONSEGNATO e non tenuti). ⚠️ differenza e' NULL (non zero) se la causale non e' fatturabile senza alcun fatturato, se il conto non e' misurabile, o se la riga e' una ri-consegna. `stato` traduce il verso del saldo UNA VOLTA SOLA: i consumatori NON devono ri-tradurlo. `sospetto_duplicato_ordine` (S6b): riga senza origine su una spedizione MISTA il cui articolo e' gia' nell'ordine che le altre righe evadono. E' una LETTURA, non un divieto — il caso legittimo esiste (merce extra dello stesso codice) e vietarlo costerebbe due documenti di trasporto per un solo viaggio. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_partite_merce
WITH (security_invoker=on) AS
WITH soglia AS (
         SELECT s.ordine AS ordine_emesso
           FROM config.stati_doc_ddt s
          WHERE ((s.codice_interno)::text = 'EMESSO'::text)
        ), ponte AS (
         SELECT rr.ddt_riga_id AS ddt_riga_origine,
            COALESCE(sum(rc.qta) FILTER (WHERE (sdd_n.ordine >= sg.ordine_emesso)), (0)::numeric) AS riconsegnato,
            COALESCE(sum(rc.qta) FILTER (WHERE (sdd_n.ordine < sg.ordine_emesso)), (0)::numeric) AS in_riconsegna
           FROM (((((vendite.resi_righe_riconsegne rc
             JOIN vendite.resi_righe rr ON ((rr.id = rc.resi_riga_id)))
             JOIN vendite.ddt_righe dr_new ON ((dr_new.id = rc.ddt_riga_id)))
             JOIN vendite.ddt d_new ON ((d_new.id = dr_new.ddt_id)))
             JOIN config.stati_doc_ddt sdd_n ON ((sdd_n.id = d_new.stato_doc_ddt_id)))
             CROSS JOIN soglia sg)
          GROUP BY rr.ddt_riga_id
        ), riga AS (
         SELECT dr.id AS ddt_riga_id,
            dr.ddt_id,
            d.uid AS ddt_uid,
            d.data AS ddt_data,
            dr.articolo_id,
            COALESCE(art.is_composito, false) AS is_composito,
            (EXISTS ( SELECT 1
                   FROM vendite.resi_righe_riconsegne rc
                  WHERE (rc.ddt_riga_id = dr.id))) AS e_riconsegna,
            ((dr.quantita + COALESCE(pt.riconsegnato, (0)::numeric)))::numeric(18,6) AS consegnato,
            COALESCE(pt.in_riconsegna, (0)::numeric) AS in_riconsegna,
            COALESCE(caus.fatturabile, false) AS fatturabile
           FROM ((((((vendite.ddt_righe dr
             JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
             JOIN config.stati_doc_ddt sdd ON ((sdd.id = d.stato_doc_ddt_id)))
             JOIN catalogo.articoli art ON ((art.id = dr.articolo_id)))
             LEFT JOIN config.causali_trasporto caus ON ((caus.id = d.causale_trasporto_id)))
             LEFT JOIN ponte pt ON ((pt.ddt_riga_origine = dr.id)))
             CROSS JOIN soglia sg)
          WHERE ((dr.attivo IS TRUE) AND (NOT sdd.is_abortito) AND (sdd.ordine >= sg.ordine_emesso))
        ), orig AS (
         SELECT f.ddt_riga_id,
            count(DISTINCT f.ordine_riga_id) AS n_origini,
            min(f.ordine_riga_id) AS ordine_riga_id
           FROM vendite.ordini_righe_fulfillment f
          GROUP BY f.ddt_riga_id
        ), sospetto AS (
         SELECT dr.id AS ddt_riga_id
           FROM vendite.ddt_righe dr
          WHERE ((NOT (EXISTS ( SELECT 1
                   FROM vendite.ordini_righe_fulfillment f
                  WHERE (f.ddt_riga_id = dr.id)))) AND (EXISTS ( SELECT 1
                   FROM (((vendite.ddt_righe dr2
                     JOIN vendite.ordini_righe_fulfillment f2 ON ((f2.ddt_riga_id = dr2.id)))
                     JOIN vendite.ordini_righe orr_ful ON ((orr_ful.id = f2.ordine_riga_id)))
                     JOIN vendite.ordini_righe orr_ord ON ((orr_ord.ordine_id = orr_ful.ordine_id)))
                  WHERE ((dr2.ddt_id = dr.ddt_id) AND (dr2.attivo IS TRUE) AND (orr_ord.attivo IS TRUE) AND (orr_ord.articolo_id = dr.articolo_id)))))
        ), res AS (
         SELECT e.ddt_riga_id,
            sum(e.quantita) AS reso
           FROM vendite.vw_resi_righe_effettive e
          GROUP BY e.ddt_riga_id
        ), alloc AS (
         SELECT r_1.ddt_riga_id,
            GREATEST((0)::numeric, LEAST(r_1.consegnato, (COALESCE(fo.quantita, (0)::numeric) - COALESCE(sum(r_1.consegnato) OVER (PARTITION BY o_1.ordine_riga_id ORDER BY r_1.ddt_data, r_1.ddt_riga_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), (0)::numeric)))) AS fatturato_da_ordine,
            COALESCE(fo.misurabile, true) AS ord_misurabile
           FROM ((riga r_1
             JOIN orig o_1 ON ((o_1.ddt_riga_id = r_1.ddt_riga_id)))
             LEFT JOIN vendite.vw_af_merce_per_riga fo ON ((((fo.corsia)::text = 'ORD'::text) AND (fo.riga_id = o_1.ordine_riga_id) AND ((fo.tipo_movimento)::text = 'NORMALE'::text))))
          WHERE (NOT r_1.e_riconsegna)
        )
 SELECT r.ddt_riga_id,
    r.ddt_id,
    r.ddt_uid,
    r.articolo_id,
    r.is_composito,
    o.ordine_riga_id,
    orr.ordine_id,
    (
        CASE
            WHEN (o.ddt_riga_id IS NULL) THEN 'NESSUNA'::text
            WHEN (o.n_origini > 1) THEN 'MULTIPLA'::text
            ELSE 'ORDINE'::text
        END)::character varying AS origine,
    r.fatturabile,
    r.consegnato,
    COALESCE(res.reso, (0)::numeric) AS reso,
    r.in_riconsegna,
    v.tenuti,
    COALESCE(fd.quantita, (0)::numeric) AS fatturato_merce,
    COALESCE(al.fatturato_da_ordine, (0)::numeric) AS fatturato_da_ordine,
    v.fatturato,
    v.misurabile,
        CASE
            WHEN (w.conta_fatturazione AND v.misurabile AND (NOT r.e_riconsegna)) THEN w.saldo
            ELSE NULL::numeric
        END AS differenza,
    (
        CASE
            WHEN r.e_riconsegna THEN 'RICONSEGNA'::text
            WHEN (NOT w.conta_fatturazione) THEN 'NON_FATTURABILE'::text
            WHEN (NOT v.misurabile) THEN 'NON_MISURABILE'::text
            WHEN (w.saldo > (0)::numeric) THEN 'DA_FATTURARE'::text
            WHEN (w.saldo < (0)::numeric) THEN 'DA_ACCREDITARE'::text
            ELSE 'PAREGGIATA'::text
        END)::character varying AS stato,
    r.e_riconsegna,
    (sos.ddt_riga_id IS NOT NULL) AS sospetto_duplicato_ordine
   FROM ((((((((riga r
     LEFT JOIN orig o ON ((o.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN vendite.ordini_righe orr ON ((orr.id = o.ordine_riga_id)))
     LEFT JOIN res ON ((res.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN sospetto sos ON ((sos.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN alloc al ON ((al.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN vendite.vw_af_merce_per_riga fd ON ((((fd.corsia)::text = 'DDT'::text) AND (fd.riga_id = r.ddt_riga_id) AND ((fd.tipo_movimento)::text = 'NORMALE'::text))))
     CROSS JOIN LATERAL ( SELECT (r.consegnato - COALESCE(res.reso, (0)::numeric)) AS tenuti,
            (COALESCE(fd.quantita, (0)::numeric) + COALESCE(al.fatturato_da_ordine, (0)::numeric)) AS fatturato,
            (COALESCE(fd.misurabile, true) AND COALESCE(al.ord_misurabile, true)) AS misurabile) v)
     CROSS JOIN LATERAL ( SELECT (r.fatturabile OR (v.fatturato > (0)::numeric)) AS conta_fatturazione,
            (v.tenuti - v.fatturato) AS saldo) w);
```


---
{% include-markdown "signature-core.md" %}
