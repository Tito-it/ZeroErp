# 🔍 View `vw_preventivi_stato_fatturazione_righe`

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_stato_fatturazione_righe AS
SELECT p.id AS preventivo_id,
    p.uid AS preventivo_uid,
    p.numero AS preventivo_numero,
    pr.id AS riga_id,
    pr.articolo_id,
    pr.descrizione AS riga_descrizione,
    (ca.id IS NOT NULL) AS in_commessa,
    ca.stato_approvazione,
    ca.stato_emissione,
    (af.id IS NOT NULL) AS emessa_af,
    (af.fattura_riga_id IS NOT NULL) AS fatturata,
    af.fattura_riga_id
   FROM (((vendite.preventivi p
     JOIN vendite.preventivi_righe pr ON (((pr.preventivo_id = p.id) AND (pr.attivo IS TRUE))))
     LEFT JOIN vendite.commesse_attivita ca ON (((ca.segment_key)::text = ((('PREV:'::text || (p.uid)::text) || ':R:'::text) || (pr.id)::text))))
     LEFT JOIN vendite.attivita_fatturabili af ON (((af.sorgente_uid = p.uid) AND (af.sorgente_riga = pr.id))));
```


---
{% include-markdown "signature-core.md" %}
