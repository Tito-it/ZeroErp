{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_righe_smistabili_ordine.md" %}
# 🔍 View `vw_preventivi_righe_smistabili_ordine`

> 📝 **Descrizione**
>
> Sorgente unica (DB-first) del predicato di smistamento: righe-merce di un preventivo ancora da portare in un ordine (natura destinazione_tipo=ORDINE, attive, non ancora allocate a una ordini_righe.preventivo_riga_id). Grana = preventivi_righe; i consumatori filtrano per preventivo_id ed eventualmente per id (smistamento parziale). Consumata da fn_preventivo_ha_residuo_ordine e fn_push_preventivo_a_ordine; predisposta per il dialog BE di selezione righe. ⭐ rev 2026-09-13 (P-6): + data_consegna_richiesta_cliente in coda — e' la proiezione da cui fn_push_preventivo_a_ordine copia la riga, e senza questa colonna la data del cliente si perdeva nel punto in cui il documento cambia natura. In ultima posizione perche' CREATE OR REPLACE VIEW puo' solo appendere. security_invoker=on. Brief: brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezione 5.2. ⭐ rev 2026-10-19 (20261019-92, brief-db-grammatica-unica-documenti lotto 2b, G-3 di Tid): ricreata dopo l'allargamento della colonna; il codice di origine o di destinazione e' quello di config.sorgenti (OFFERTA -&gt; OFFERTA_COMMERCIALE, ORDINE -&gt; ORDINE_VENDITA).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_righe_smistabili_ordine
WITH (security_invoker=on) AS
SELECT pr.preventivo_id,
    pr.id,
    pr.natura_vendita_id,
    pr.articolo_id,
    pr.descrizione,
    pr.prezzo_unitario,
    pr.sconto_percentuale,
    pr.iva_id,
    pr.qta_operativa,
    pr.uom_operativa_id,
    pr.factor_to_base,
    pr.ordine,
    pr.data_consegna_richiesta_cliente
   FROM (vendite.preventivi_righe pr
     JOIN config.nature_vendita nv ON ((nv.id = pr.natura_vendita_id)))
  WHERE ((COALESCE(pr.attivo, true) IS TRUE) AND ((nv.destinazione_tipo)::text = 'ORDINE_VENDITA'::text) AND (NOT (EXISTS ( SELECT 1
           FROM vendite.ordini_righe orr
          WHERE (orr.preventivo_riga_id = pr.id)))));
```


---
{% include-markdown "signature-core.md" %}
