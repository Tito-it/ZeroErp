{% include-markdown "it/dbzero/vendite/manual/vw_preventivi_smistamento_righe.md" %}
# 🔍 View `vw_preventivi_smistamento_righe`

> 📝 **Descrizione**
>
> Fonte dati del Pannello Smistamento: una riga per riga attiva del preventivo, con natura e destinazione effettiva (natura NULL = destinazione COMMESSA), i riferimenti del ramo ordine e lo stato_smistamento. Gli stati, nell'ordine in cui si decidono: FATTURATA (un'attivita' fatturabile nata dal segmento della riga e' in fattura), EMESSA_AF (l'attivita' fatturabile c'e'), IN_COMMESSA (il segmento non e' LIBERO per script.fn_get_stato_push_segment, la fonte unica del «gia' mandato»), A_ORDINE (una riga d'ordine la consuma), RESIDUA. Il segmento della riga e' script.fn_segment_key(PREVENTIVO, uid, riga); le righe di commessa del segmento sono quelle con quella segment_base, componenti e rettifiche comprese, e l'attivita' fatturabile si raggiunge per commessa_attivita_id. Una riga di commessa ANNULLATA non conta: annullata la commessa, la riga del preventivo torna RESIDUA.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

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
               FROM (vendite.commesse_attivita ca
                 JOIN vendite.attivita_fatturabili af ON ((af.commessa_attivita_id = ca.id)))
              WHERE (((ca.segment_base)::text = (script.fn_segment_key('PREVENTIVO'::character varying, (p.uid)::text, pr.id))::text) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text) AND (af.fattura_riga_id IS NOT NULL)))) THEN 'FATTURATA'::text
            WHEN (EXISTS ( SELECT 1
               FROM (vendite.commesse_attivita ca
                 JOIN vendite.attivita_fatturabili af ON ((af.commessa_attivita_id = ca.id)))
              WHERE (((ca.segment_base)::text = (script.fn_segment_key('PREVENTIVO'::character varying, (p.uid)::text, pr.id))::text) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text)))) THEN 'EMESSA_AF'::text
            WHEN (script.fn_get_stato_push_segment(script.fn_segment_key('PREVENTIVO'::character varying, (p.uid)::text, pr.id)) <> 'LIBERA'::text) THEN 'IN_COMMESSA'::text
            WHEN (orr.id IS NOT NULL) THEN 'A_ORDINE'::text
            ELSE 'RESIDUA'::text
        END AS stato_smistamento
   FROM ((((vendite.preventivi p
     JOIN vendite.preventivi_righe pr ON (((pr.preventivo_id = p.id) AND (pr.attivo IS TRUE))))
     LEFT JOIN config.nature_vendita nv ON ((nv.id = pr.natura_vendita_id)))
     LEFT JOIN vendite.ordini_righe orr ON ((orr.preventivo_riga_id = pr.id)))
     LEFT JOIN vendite.ordini o ON ((o.id = orr.ordine_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
