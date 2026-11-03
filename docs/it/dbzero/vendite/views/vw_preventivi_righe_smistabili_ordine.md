{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_righe_smistabili_ordine.md" %}
# 🔍 View `vw_preventivi_righe_smistabili_ordine`

> 📝 **Descrizione**
>
> Sorgente unica (DB-first) del predicato di smistamento: righe-merce di un preventivo ancora da portare in un ordine (natura merce secondo script.fn_natura_e_merce, attive, non ancora allocate a una ordini_righe.preventivo_riga_id; la natura NULL del pregresso resta fuori). Grana = preventivi_righe; i consumatori filtrano per preventivo_id ed eventualmente per id (smistamento parziale). Consumata da fn_preventivo_ha_residuo_ordine e fn_push_preventivo_a_ordine; predisposta per il dialog BE di selezione righe. ⭐ rev 2026-09-13 (P-6): + data_consegna_richiesta_cliente in coda — e' la proiezione da cui fn_push_preventivo_a_ordine copia la riga, e senza questa colonna la data del cliente si perdeva nel punto in cui il documento cambia natura. In ultima posizione perche' CREATE OR REPLACE VIEW puo' solo appendere. security_invoker=on. Brief: brief-db-modifiche-certe-ciclo-vendita-e-articolo, sezione 5.2. ⭐ rev 2026-10-19 (20261019-92, brief-db-grammatica-unica-documenti lotto 2b, G-3 di Tid): ricreata dopo l'allargamento della colonna; il codice di origine o di destinazione e' quello di config.sorgenti (OFFERTA -&gt; OFFERTA_COMMERCIALE, ORDINE -&gt; ORDINE_VENDITA). ⭐ rev 2026-11-03 (20261103-19, brief-db-addebito-trasporto-ordine §8.1, regola del 2): il filtro merce e' il BB script.fn_natura_e_merce al posto del JOIN con config.nature_vendita e della destinazione in linea; stesse righe.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_righe_smistabili_ordine
WITH (security_invoker=on) AS
SELECT preventivo_id,
    id,
    natura_vendita_id,
    articolo_id,
    descrizione,
    prezzo_unitario,
    sconto_percentuale,
    iva_id,
    qta_operativa,
    uom_operativa_id,
    factor_to_base,
    ordine,
    data_consegna_richiesta_cliente
   FROM vendite.preventivi_righe pr
  WHERE ((COALESCE(attivo, true) IS TRUE) AND (script.fn_natura_e_merce(natura_vendita_id) IS TRUE) AND (NOT (EXISTS ( SELECT 1
           FROM vendite.ordini_righe orr
          WHERE (orr.preventivo_riga_id = pr.id)))));
```

</div>


---
{% include-markdown "signature-core.md" %}
