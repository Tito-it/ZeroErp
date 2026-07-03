{% include-markdown "it/dbzero/vendite/manual/vw_dash_fatturazione_commesse.md" %}
# 🔍 View `vw_dash_fatturazione_commesse`

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_fatturazione_commesse AS
SELECT 'COMMESSE'::character varying AS area,
    ca.competenza_mese,
    co.id AS documento_id,
    (co.id)::text AS documento_uid,
    (co.codice)::text AS codice,
    NULL::bigint AS emittente_fiscale_id,
    co.emittente_soggetto_ruolo_id,
    sum((COALESCE(ca.prezzo_snapshot, (0)::numeric) * ca.quantita)) AS valore_totale,
    COALESCE(sum((COALESCE(ca.prezzo_snapshot, (0)::numeric) * ca.quantita)) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text)), (0)::numeric) AS valore_transitato,
    (count(*))::integer AS unita_totali,
    (count(*) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text)))::integer AS unita_transitate,
    (count(*) = count(*) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text))) AS is_transitato,
    ((sc.codice_interno)::text = 'ANNULLATA'::text) AS is_abortito,
    (
        CASE
            WHEN ((sc.codice_interno)::text = 'ANNULLATA'::text) THEN NULL::text
            WHEN (count(*) = count(*) FILTER (WHERE ((ca.stato_emissione)::text = 'EMESSA'::text))) THEN NULL::text
            WHEN (count(*) FILTER (WHERE (((ca.stato_emissione)::text <> 'EMESSA'::text) AND ((ca.stato_approvazione)::text <> 'APPROVATA'::text))) > 0) THEN 'ATTIVITA_NON_APPROVATA'::text
            ELSE 'ATTIVITA_NON_EMESSA'::text
        END)::character varying AS motivo_fermo,
    sc.codice_interno AS stato_codice_interno,
    sc.codice AS stato_codice,
    NULL::character varying AS fase
   FROM ((vendite.commesse co
     JOIN vendite.stati_commessa sc ON ((sc.id = co.stato_commessa_id)))
     JOIN vendite.commesse_attivita ca ON ((ca.commessa_id = co.id)))
  GROUP BY co.id, co.codice, co.emittente_soggetto_ruolo_id, ca.competenza_mese, sc.codice_interno, sc.codice;
```


---
{% include-markdown "signature-core.md" %}
