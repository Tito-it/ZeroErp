{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_righe_smistabili_commessa.md" %}
# 🔍 View `vw_preventivi_righe_smistabili_commessa`

> 📝 **Descrizione**
>
> Righe preventivo eleggibili al push commessa (servizi una tantum): attive, qta&gt;0, prezzo&gt;=0, natura NULL/COMMESSA, non gia' mandate in commessa. Simmetrica a vw_preventivi_righe_smistabili_ordine (esclude su allocazione, non su fatturazione). Predicato di riga unico condiviso con fn_list_preventivi_da_pushare e fn_preventivo_ha_residuo_commessa; condizioni di testata a carico dei consumer. Fix gate EVASO (brief-db-gate-evaso-ramo-commessa-asimmetria.md). ⭐ rev 2026-10-12 (20261012-08/-09, brief-db-annullo-a-valle-riapre-a-monte D-5): «gia' mandata» non e' piu' un predicato proprio: e' script.fn_get_stato_push_segment('PREV:&lt;uid&gt;:R:&lt;id&gt;') = 'LIBERA', la fonte unica del «gia' inviato» (componenti #CMP e rettifiche #RET compresi). Una riga di commessa ANNULLATA non occupa: annullata la commessa, la riga torna smistabile. Prima la vista contava le righe ANNULLATA e non vedeva #RET: una terza copia della regola, gia' diversa dalle altre due. Rev 2026-10-20 (20261020-97, brief-db-grammatica-unica-documenti 2e, G-8): la chiave della riga di preventivo la compone script.fn_segment_key (PREVENTIVO:&lt;uid&gt;:R:&lt;riga&gt;, era PREV:...).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi_righe_smistabili_commessa
WITH (security_invoker=on) AS
SELECT pr.preventivo_id,
    pr.id,
    p.uid AS preventivo_uid,
    pr.natura_vendita_id,
    pr.articolo_id,
    pr.descrizione,
    pr.prezzo_unitario,
    pr.sconto_percentuale,
    pr.iva_id,
    pr.quantita,
    pr.qta_operativa,
    pr.uom_operativa_id,
    pr.factor_to_base,
    pr.ordine
   FROM ((vendite.preventivi_righe pr
     JOIN vendite.preventivi p ON ((p.id = pr.preventivo_id)))
     LEFT JOIN config.nature_vendita nv ON ((nv.id = pr.natura_vendita_id)))
  WHERE ((pr.attivo IS TRUE) AND (pr.quantita > (0)::numeric) AND (pr.prezzo_unitario >= (0)::numeric) AND ((pr.natura_vendita_id IS NULL) OR ((nv.destinazione_tipo)::text = 'COMMESSA'::text)) AND (script.fn_get_stato_push_segment(script.fn_segment_key('PREVENTIVO'::character varying, (p.uid)::text, pr.id)) = 'LIBERA'::text));
```

</div>


---
{% include-markdown "signature-core.md" %}
