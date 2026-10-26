{% include-markdown "it/dbzero/vendite/manual/fn_resi_da_accreditare.md" %}
# ⚙️ Funzione `fn_resi_da_accreditare`

```sql
CREATE FUNCTION fn_resi_da_accreditare(p_ddt_ids bigint[], p_ordine_ids bigint[])
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resi_da_accreditare(p_ddt_ids bigint[] DEFAULT NULL::bigint[], p_ordine_ids bigint[] DEFAULT NULL::bigint[])
 RETURNS TABLE(resi_riga_id bigint, reso_id bigint, reso_uid uuid, reso_numero character varying, data date, emittente_fiscale_id bigint, billing_account_id bigint, ba_codice character varying, destinatario_soggetto_ruolo_id bigint, destinatario_denominazione text, articolo_id uuid, descrizione character varying, quantita numeric, qta_operativa numeric, uom_operativa_id bigint, motivo character varying, ddt_riga_id bigint, ddt_id bigint, ddt_numero character varying, ordine_riga_id bigint, tenuti numeric, fatturati numeric, accredito_dovuto numeric, etichetta character varying, gia_accreditato numeric, blocco_codice character varying, annullo_blocco_codice character varying)
 LANGUAGE sql
 STABLE
BEGIN ATOMIC
 WITH righe_in AS MATERIALIZED (
          SELECT dr_1.id AS ddt_riga_id,
             dr_1.ddt_id
            FROM vendite.ddt_righe dr_1
           WHERE (dr_1.ddt_id = ANY (fn_resi_da_accreditare.p_ddt_ids))
         UNION
          SELECT dr_1.id,
             dr_1.ddt_id
            FROM ((vendite.ordini_righe orr
              JOIN vendite.ordini_righe_fulfillment f ON ((f.ordine_riga_id = orr.id)))
              JOIN vendite.ddt_righe dr_1 ON ((dr_1.id = f.ddt_riga_id)))
           WHERE (orr.ordine_id = ANY (fn_resi_da_accreditare.p_ordine_ids))
         ), acc AS (
          SELECT p.ddt_riga_id,
             p.tenuti,
             p.fatturato AS fatturati,
             (- p.differenza) AS accredito_partita
            FROM vendite.fn_partite_merce(NULL::bigint[], NULL::bigint[]) p(ddt_riga_id, ddt_id, ddt_uid, articolo_id, is_composito, ordine_riga_id, ordine_id, origine, fatturabile, consegnato, reso, in_riconsegna, tenuti, fatturato_merce, fatturato_da_ordine, fatturato, misurabile, differenza, stato, e_riconsegna, sospetto_duplicato_ordine, rettificato, riconsegna_quota_nuova)
           WHERE ((p.differenza < (0)::numeric) AND ((fn_resi_da_accreditare.p_ddt_ids IS NULL) AND (fn_resi_da_accreditare.p_ordine_ids IS NULL)))
         UNION ALL
          SELECT p.ddt_riga_id,
             p.tenuti,
             p.fatturato,
             (- p.differenza)
            FROM vendite.fn_partite_merce(( SELECT COALESCE(array_agg(DISTINCT s.ddt_id), '{}'::bigint[]) AS "coalesce"
                    FROM righe_in s), NULL::bigint[]) p(ddt_riga_id, ddt_id, ddt_uid, articolo_id, is_composito, ordine_riga_id, ordine_id, origine, fatturabile, consegnato, reso, in_riconsegna, tenuti, fatturato_merce, fatturato_da_ordine, fatturato, misurabile, differenza, stato, e_riconsegna, sospetto_duplicato_ordine, rettificato, riconsegna_quota_nuova)
           WHERE ((p.differenza < (0)::numeric) AND (NOT ((fn_resi_da_accreditare.p_ddt_ids IS NULL) AND (fn_resi_da_accreditare.p_ordine_ids IS NULL))))
         ), eff AS (
          SELECT e.resi_riga_id,
             e.reso_id,
             e.ddt_riga_id,
             e.ordine_riga_id,
             e.riapre_residuo,
             e.quantita,
             vendite.fn_resi_riga_accreditato_partita(e.resi_riga_id) AS gia_accreditato
            FROM (vendite.vw_resi_righe_effettive e
              JOIN righe_in s ON ((s.ddt_riga_id = e.ddt_riga_id)))
           WHERE (NOT ((fn_resi_da_accreditare.p_ddt_ids IS NULL) AND (fn_resi_da_accreditare.p_ordine_ids IS NULL)))
         UNION ALL
          SELECT e.resi_riga_id,
             e.reso_id,
             e.ddt_riga_id,
             e.ordine_riga_id,
             e.riapre_residuo,
             e.quantita,
             vendite.fn_resi_riga_accreditato_partita(e.resi_riga_id) AS fn_resi_riga_accreditato_partita
            FROM vendite.vw_resi_righe_effettive e
           WHERE ((fn_resi_da_accreditare.p_ddt_ids IS NULL) AND (fn_resi_da_accreditare.p_ordine_ids IS NULL))
         ), dist AS (
          SELECT e.resi_riga_id,
             e.reso_id,
             e.ddt_riga_id,
             e.ordine_riga_id,
             e.riapre_residuo,
             e.quantita AS qta_resa,
             e.gia_accreditato,
             a.tenuti,
             a.fatturati,
             GREATEST((0)::numeric, LEAST(GREATEST((0)::numeric, (e.quantita - e.gia_accreditato)), (a.accredito_partita - COALESCE(sum(GREATEST((0)::numeric, (e.quantita - e.gia_accreditato))) OVER (PARTITION BY e.ddt_riga_id ORDER BY e.resi_riga_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), (0)::numeric)))) AS accredito_dovuto
            FROM (eff e
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
         END)::character varying AS etichetta,
     x.gia_accreditato,
     (
         CASE
             WHEN (x.gia_accreditato > (0)::numeric) THEN 'GIA_ACCREDITATO'::text
             ELSE NULL::text
         END)::character varying AS blocco_codice,
     (((script.fn_check_accredito_annullabile(x.resi_riga_id) -> 0) ->> 'reason'::text))::character varying AS annullo_blocco_codice
    FROM (((((((dist x
      JOIN vendite.resi_righe rr ON ((rr.id = x.resi_riga_id)))
      JOIN vendite.resi r ON ((r.id = x.reso_id)))
      JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
      JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
      LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = r.billing_account_id)))
      JOIN vendite.ddt_righe dr ON ((dr.id = x.ddt_riga_id)))
      JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
   WHERE (x.accredito_dovuto > (0)::numeric);
END

COMMENT ON FUNCTION vendite.fn_resi_da_accreditare(p_ddt_ids bigint[], p_ordine_ids bigint[])
IS 'LA CODA ACCREDITI, PER DOCUMENTO (D14 giro 2 — D3, 2026-09-21): la stessa coda di vendite.vw_resi_da_accreditare — che ne e'' la proiezione senza filtro, fn(NULL, NULL) — ristretta alle righe di DDT dei documenti chiesti. Semi, nello stesso ordine di fn_partite_merce: p_ddt_ids (la colonna ddt_id) e p_ordine_ids (un fulfillment della riga di DDT resa verso l''ordine): S e'' lo STESSO predicato del BB backend _coda_documento_filtro.filtro_coda_per_documento, e NON l''uscita per ordine di fn_partite_merce (ordine_id = riga minima): una riga di DDT che evade due ordini sta nella coda di entrambi. Entrambi NULL = tutta; array VUOTO = zero righe; entrambi valorizzati = unione. La chiusura: le partite da fn_partite_merce(<i DDT di S>, NULL) (soprainsieme, riportato a S dal JOIN); le righe di reso effettive con ddt_riga_id in S — TUTTE le sorelle, quindi la greedy per resi_riga_id e'' intera — e fn_resi_riga_accreditato_partita solo su quelle. BEGIN ATOMIC: dipendenze in pg_depend, catena RLS leggibile dal presidio security_invoker attraverso fn_partite_merce. Due modi in UNION ALL, mai `p IS NULL OR`; sulla partita il ramo TUTTI (due letterali) resta inlinato, identico alla vista, il ramo col seme calcolato e'' un Function Scan che regge in piano generico. INVOKER: la RLS resta di chi legge — dentro fn_resi_riga_tetti_accredito (DEFINER) gira come l''owner, sopra la RLS, com''era la vista. Chiamanti per documento: fn_accredita_riga_reso (ARRAY[ddt della riga]), fn_resi_riga_tetti_accredito (idem), BE list_situazione_merce_accrediti e ResiRepository.list_da_accreditare con ddt_id/ordine_id (richiesta BE nel brief). Brief: brief-db-partita-merce-per-documento §7 giro 2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
