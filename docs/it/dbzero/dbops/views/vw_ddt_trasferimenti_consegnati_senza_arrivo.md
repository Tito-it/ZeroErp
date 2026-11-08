# 🔍 View `vw_ddt_trasferimenti_consegnati_senza_arrivo`

> 📝 **Descrizione**
>
> Presidio, DEVE restare vuota. Una riga e' una bolla di TRASFERIMENTO (vendite.fn_ddt_causale_magazzino = TRASF_OUT) che muove merce (vendite.fn_ddt_muove_merce), con un magazzino, in uno stato dalla consegna in poi (ordine &gt;= quello di CONSEGNATO e non abortito, dal catalogo config.stati_doc_ddt), con almeno un prelievo di una riga attiva senza la sua ENTRATA nel magazzino d'arrivo (provenienza DDT_VENDITA: la bolla, la riga, il prelievo come dettaglio; quantita' positiva, non uno storno). Alla consegna il verbo vendite.fn_cambia_stato_ddt scrive un arrivo per prelievo (vendite.fn_posta_ddt ARRIVO, TRASF_IN): una riga qui e' merce uscita dalla partenza e mai entrata a destinazione, cioe' due giacenze che mentono. prelievi_senza_arrivo dice quanti. Il rimedio non e' scrivere il movimento a mano: e' capire da dove e' passata la consegna. Gemella di dbops.vw_ddt_emessi_senza_scarico sull'altro capo del trasferimento. security_invoker; il digest conta da proprietario (fn_conta_presidio, perimetro DEFINER). Brief: brief-db-sorgente-documento-e-riga lotto M (decisione C di Tid, 2026-11-08).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo
WITH (security_invoker=true) AS
SELECT d.id AS ddt_id,
    d.numero,
    d.data,
    d.emittente_fiscale_id,
    d.magazzino_id,
    d.magazzino_arrivo_id,
    s.codice_interno AS stato_codice_interno,
    n.prelievi_senza_arrivo
   FROM (((vendite.ddt d
     JOIN config.stati_doc_ddt s ON ((s.id = d.stato_doc_ddt_id)))
     JOIN config.stati_doc_ddt c ON (((c.codice_interno)::text = 'CONSEGNATO'::text)))
     CROSS JOIN LATERAL ( SELECT count(*) AS prelievi_senza_arrivo
           FROM (vendite.ddt_righe dr
             JOIN vendite.ddt_righe_prelievi p ON ((p.ddt_riga_id = dr.id)))
          WHERE ((dr.ddt_id = d.id) AND dr.attivo AND (NOT (EXISTS ( SELECT 1
                   FROM (magazzino.movimenti m
                     JOIN config.sorgenti so ON (((so.id = m.sorgente_tipo_id) AND ((so.codice_interno)::text = 'DDT_VENDITA'::text))))
                  WHERE ((m.sorgente_id = d.id) AND (m.sorgente_riga = dr.id) AND (m.sorgente_dettaglio = p.id) AND (m.qta > (0)::numeric) AND (m.storno_di_movimento_id IS NULL))))))) n)
  WHERE ((NOT s.is_abortito) AND (s.ordine >= c.ordine) AND (d.magazzino_id IS NOT NULL) AND (n.prelievi_senza_arrivo > 0) AND ((vendite.fn_ddt_causale_magazzino(d.*))::text = 'TRASF_OUT'::text) AND vendite.fn_ddt_muove_merce(d.*));
```

</div>


---
{% include-markdown "signature-core.md" %}
