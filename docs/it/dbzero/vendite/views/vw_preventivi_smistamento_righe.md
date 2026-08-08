{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_smistamento_righe.md" %}
# 🔍 View `vw_preventivi_smistamento_righe`

> 📝 **Descrizione**
>
> Fonte dati del Pannello Smistamento (una riga per riga attiva del preventivo): natura/destinazione effettiva (NULL = pregresso -&gt; COMMESSA), riferimenti ramo ordine, stato_smistamento autorevole (RESIDUA/A_ORDINE/IN_COMMESSA/EMESSA_AF/FATTURATA, "in commessa" = segment EMESSA). Sostituisce vw_preventivi_stato_fatturazione_righe (brief-db-smistamento-preventivi.md B).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_smistamento_righe
WITH (security_invoker=on) AS
SELECT p.id AS preventivo_id,
    p.uid AS preventivo_uid,
    p.numero AS preventivo_numero,
    pr.id AS riga_id,
    pr.ordine AS riga_ordine,
    pr.descrizione AS riga_descrizione,
    pr.articolo_id,
    pr.quantita,
    pr.qta_operativa,
    pr.uom_operativa_id,
    pr.prezzo_unitario,
    pr.natura_vendita_id,
    nv.codice AS natura_vendita_codice,
    COALESCE(nv.destinazione_tipo, 'COMMESSA'::character varying) AS destinazione_tipo,
    orr.id AS ordine_riga_id,
    o.id AS ordine_id,
    o.numero AS ordine_numero,
        CASE
            WHEN (EXISTS ( SELECT 1
               FROM vendite.attivita_fatturabili af
              WHERE ((af.sorgente_uid = p.uid) AND (af.sorgente_riga = pr.id) AND (af.fattura_riga_id IS NOT NULL)))) THEN 'FATTURATA'::text
            WHEN (EXISTS ( SELECT 1
               FROM vendite.attivita_fatturabili af
              WHERE ((af.sorgente_uid = p.uid) AND (af.sorgente_riga = pr.id)))) THEN 'EMESSA_AF'::text
            WHEN (EXISTS ( SELECT 1
               FROM vendite.commesse_attivita ca
              WHERE (((ca.segment_key)::text = ((('PREV:'::text || (p.uid)::text) || ':R:'::text) || (pr.id)::text)) AND ((ca.stato_emissione)::text = 'EMESSA'::text)))) THEN 'IN_COMMESSA'::text
            WHEN (orr.id IS NOT NULL) THEN 'A_ORDINE'::text
            ELSE 'RESIDUA'::text
        END AS stato_smistamento
   FROM ((((vendite.preventivi p
     JOIN vendite.preventivi_righe pr ON (((pr.preventivo_id = p.id) AND (pr.attivo IS TRUE))))
     LEFT JOIN config.nature_vendita nv ON ((nv.id = pr.natura_vendita_id)))
     LEFT JOIN vendite.ordini_righe orr ON ((orr.preventivo_riga_id = pr.id)))
     LEFT JOIN vendite.ordini o ON ((o.id = orr.ordine_id)));
```


---
{% include-markdown "signature-core.md" %}
