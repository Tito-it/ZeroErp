{% include-markdown "it/dbzero/vendite/manual/vw_partite_merce.md" %}
# 🔍 View `vw_partite_merce`

> 📝 **Descrizione**
>
> La PARTITA DI MERCE: una riga per riga di DDT attiva su documento EMESSO in poi, con la riga d'ordine come ORIGINE nullable. rev 2026-08-18 (N6): il `fatturato` somma anche le RETTIFICHE della corsia DDT (colonna `rettificato`, negativa o zero) — e' cio' che chiude il contratto del S2 del brief nota di credito, senza il quale una NC sarebbe invisibile al contatore e la coda continuerebbe a chiedere l'accredito per sempre. La rettifica si legge SEMPRE sulla corsia DDT anche quando a fatturare e' stata la corsia ORD (D-NC-1): nel serbatoio d'ordine la greedy la scaricherebbe sull'ULTIMA spedizione invece che su quella da cui la merce e' tornata, con il totale giusto e la ripartizione falsa. rev 2026-08-18 (N7, D-NC-4): «una ri-consegna e' merce nuova SOLO per la parte accreditata». La quota accreditata sulla partita d'origine si versa greedy oldest-first nelle spedizioni nuove (`riconsegna_quota_nuova`), che diventano partite vere con un segmento vergine — quindi LIBERA per fn_get_stato_push_segment, quindi ri-fatturabili dal giro normale, senza allentare la cintura che impedisce di ri-spingere una riga gia' fatturata. Senza nota di credito la regola e' INERTE: nessun pezzo cambia casa e ogni numero resta quello di prima. rev 2026-09-17 (D14): la CTE `sospetto` (sospetto_duplicato_ordine) non e' piu' un EXISTS correlato valutato per partita ma un insieme calcolato una volta — le coppie (DDT, articolo) coperte da un ordine collegato al DDT, `articoli_ordinati_per_ddt` — e un JOIN, entrambe AS MATERIALIZED (senza, il planner le inlina e torna al ciclo per riga). Stesse righe e stesso significato; cambia quante volte si pagano le policy RLS: la vista intera come applicazione passa da ~375 a ~88 ms (dbdev, 2026-09-17), la lettura di una riga sola sale di ~12 ms perche' l'insieme si calcola intero. Chi la legge intera e' la capability del DDT (lister + diagnosi), cioe' il drawer. security_invoker=on ri-specificato (la reloption non si vede in pg_get_viewdef e un CREATE OR REPLACE la azzera: qui significa bypass della RLS, regressione V-1).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_partite_merce
WITH (security_invoker=on) AS
WITH soglia AS (
         SELECT s.ordine AS ordine_emesso
           FROM config.stati_doc_ddt s
          WHERE ((s.codice_interno)::text = 'EMESSO'::text)
        ), ponte_riga AS (
         SELECT rr.ddt_riga_id AS ddt_riga_origine,
            rc.ddt_riga_id AS ddt_riga_nuova,
            d_new.data AS ddt_nuovo_data,
            (sdd_n.ordine >= sg.ordine_emesso) AS emesso,
            sum(rc.qta) AS qta
           FROM (((((vendite.resi_righe_riconsegne rc
             JOIN vendite.resi_righe rr ON ((rr.id = rc.resi_riga_id)))
             JOIN vendite.ddt_righe dr_new ON ((dr_new.id = rc.ddt_riga_id)))
             JOIN vendite.ddt d_new ON ((d_new.id = dr_new.ddt_id)))
             JOIN config.stati_doc_ddt sdd_n ON ((sdd_n.id = d_new.stato_doc_ddt_id)))
             CROSS JOIN soglia sg)
          GROUP BY rr.ddt_riga_id, rc.ddt_riga_id, d_new.data, (sdd_n.ordine >= sg.ordine_emesso)
        ), ponte AS (
         SELECT p.ddt_riga_origine,
            COALESCE(sum(p.qta) FILTER (WHERE p.emesso), (0)::numeric) AS riconsegnato,
            COALESCE(sum(p.qta) FILTER (WHERE (NOT p.emesso)), (0)::numeric) AS in_riconsegna
           FROM ponte_riga p
          GROUP BY p.ddt_riga_origine
        ), acc_origine AS (
         SELECT DISTINCT p.ddt_riga_origine,
            GREATEST((0)::numeric, (- COALESCE(ret.quantita, (0)::numeric))) AS accreditato
           FROM (ponte_riga p
             LEFT JOIN vendite.vw_af_merce_per_riga ret ON ((((ret.corsia)::text = 'DDT'::text) AND (ret.riga_id = p.ddt_riga_origine) AND ((ret.tipo_movimento)::text = 'RETTIFICA'::text))))
        ), migra AS (
         SELECT p.ddt_riga_nuova,
            p.ddt_riga_origine,
            GREATEST((0)::numeric, LEAST(p.qta, (a.accreditato - COALESCE(sum(p.qta) OVER (PARTITION BY p.ddt_riga_origine ORDER BY p.ddt_nuovo_data, p.ddt_riga_nuova ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), (0)::numeric)))) AS quota
           FROM (ponte_riga p
             JOIN acc_origine a ON ((a.ddt_riga_origine = p.ddt_riga_origine)))
          WHERE p.emesso
        ), migra_origine AS (
         SELECT m.ddt_riga_origine,
            sum(m.quota) AS quota_migrata
           FROM migra m
          GROUP BY m.ddt_riga_origine
        ), migra_nuova AS (
         SELECT m.ddt_riga_nuova,
            sum(m.quota) AS quota_nuova
           FROM migra m
          GROUP BY m.ddt_riga_nuova
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
            COALESCE(mn.quota_nuova, (0)::numeric) AS quota_nuova,
            (((
                CASE
                    WHEN (EXISTS ( SELECT 1
                       FROM vendite.resi_righe_riconsegne rc
                      WHERE (rc.ddt_riga_id = dr.id))) THEN COALESCE(mn.quota_nuova, (0)::numeric)
                    ELSE dr.quantita
                END + COALESCE(pt.riconsegnato, (0)::numeric)) - COALESCE(mo.quota_migrata, (0)::numeric)))::numeric(18,6) AS consegnato,
            COALESCE(pt.in_riconsegna, (0)::numeric) AS in_riconsegna,
            COALESCE(caus.fatturabile, false) AS fatturabile
           FROM ((((((((vendite.ddt_righe dr
             JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
             JOIN config.stati_doc_ddt sdd ON ((sdd.id = d.stato_doc_ddt_id)))
             JOIN catalogo.articoli art ON ((art.id = dr.articolo_id)))
             LEFT JOIN config.causali_trasporto caus ON ((caus.id = d.causale_trasporto_id)))
             LEFT JOIN ponte pt ON ((pt.ddt_riga_origine = dr.id)))
             LEFT JOIN migra_origine mo ON ((mo.ddt_riga_origine = dr.id)))
             LEFT JOIN migra_nuova mn ON ((mn.ddt_riga_nuova = dr.id)))
             CROSS JOIN soglia sg)
          WHERE ((dr.attivo IS TRUE) AND (NOT sdd.is_abortito) AND (sdd.ordine >= sg.ordine_emesso))
        ), orig AS (
         SELECT f.ddt_riga_id,
            count(DISTINCT f.ordine_riga_id) AS n_origini,
            min(f.ordine_riga_id) AS ordine_riga_id
           FROM vendite.ordini_righe_fulfillment f
          GROUP BY f.ddt_riga_id
        ), articoli_ordinati_per_ddt AS MATERIALIZED (
         SELECT DISTINCT dr2.ddt_id,
            orr_ord.articolo_id
           FROM (((vendite.ddt_righe dr2
             JOIN vendite.ordini_righe_fulfillment f2 ON ((f2.ddt_riga_id = dr2.id)))
             JOIN vendite.ordini_righe orr_ful ON ((orr_ful.id = f2.ordine_riga_id)))
             JOIN vendite.ordini_righe orr_ord ON ((orr_ord.ordine_id = orr_ful.ordine_id)))
          WHERE ((dr2.attivo IS TRUE) AND (orr_ord.attivo IS TRUE))
        ), sospetto AS MATERIALIZED (
         SELECT dr.id AS ddt_riga_id
           FROM (vendite.ddt_righe dr
             JOIN articoli_ordinati_per_ddt k ON (((k.ddt_id = dr.ddt_id) AND (k.articolo_id = dr.articolo_id))))
          WHERE (NOT (EXISTS ( SELECT 1
                   FROM vendite.ordini_righe_fulfillment f
                  WHERE (f.ddt_riga_id = dr.id))))
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
            WHEN (w.conta_fatturazione AND v.misurabile AND ((NOT r.e_riconsegna) OR (r.quota_nuova > (0)::numeric))) THEN w.saldo
            ELSE NULL::numeric
        END AS differenza,
    (
        CASE
            WHEN (r.e_riconsegna AND (r.quota_nuova <= (0)::numeric)) THEN 'RICONSEGNA'::text
            WHEN (NOT w.conta_fatturazione) THEN 'NON_FATTURABILE'::text
            WHEN (NOT v.misurabile) THEN 'NON_MISURABILE'::text
            WHEN (w.saldo > (0)::numeric) THEN 'DA_FATTURARE'::text
            WHEN (w.saldo < (0)::numeric) THEN 'DA_ACCREDITARE'::text
            ELSE 'PAREGGIATA'::text
        END)::character varying AS stato,
    r.e_riconsegna,
    (sos.ddt_riga_id IS NOT NULL) AS sospetto_duplicato_ordine,
    COALESCE(fr.quantita, (0)::numeric) AS rettificato,
    r.quota_nuova AS riconsegna_quota_nuova
   FROM (((((((((riga r
     LEFT JOIN orig o ON ((o.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN vendite.ordini_righe orr ON ((orr.id = o.ordine_riga_id)))
     LEFT JOIN res ON ((res.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN sospetto sos ON ((sos.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN alloc al ON ((al.ddt_riga_id = r.ddt_riga_id)))
     LEFT JOIN vendite.vw_af_merce_per_riga fd ON ((((fd.corsia)::text = 'DDT'::text) AND (fd.riga_id = r.ddt_riga_id) AND ((fd.tipo_movimento)::text = 'NORMALE'::text))))
     LEFT JOIN vendite.vw_af_merce_per_riga fr ON ((((fr.corsia)::text = 'DDT'::text) AND (fr.riga_id = r.ddt_riga_id) AND ((fr.tipo_movimento)::text = 'RETTIFICA'::text))))
     CROSS JOIN LATERAL ( SELECT (r.consegnato - COALESCE(res.reso, (0)::numeric)) AS tenuti,
            ((COALESCE(fd.quantita, (0)::numeric) + COALESCE(al.fatturato_da_ordine, (0)::numeric)) + COALESCE(fr.quantita, (0)::numeric)) AS fatturato,
            (COALESCE(fd.misurabile, true) AND COALESCE(al.ord_misurabile, true) AND COALESCE(fr.misurabile, true)) AS misurabile) v)
     CROSS JOIN LATERAL ( SELECT (r.fatturabile OR (v.fatturato > (0)::numeric)) AS conta_fatturazione,
            (v.tenuti - v.fatturato) AS saldo) w);
```


---
{% include-markdown "signature-core.md" %}
