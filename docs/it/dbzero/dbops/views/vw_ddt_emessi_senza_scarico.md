{% include-markdown "it/dbzero/dbops/manual/vw_ddt_emessi_senza_scarico.md" %}
# 🔍 View `vw_ddt_emessi_senza_scarico`

> 📝 **Descrizione**
>
> Presidio, DEVE restare vuota. Una riga e' una bolla in uno stato in cui la merce e' partita (il BB script.vw_stati_doc_ddt_merce_partita: uscita dalla bozza e non abortita), con un magazzino, che muove merce (vendite.fn_ddt_muove_merce), con almeno un prelievo di una riga attiva senza la sua uscita a registro: un movimento di magazzino.movimenti con provenienza DDT_VENDITA (la bolla, la riga, il prelievo come dettaglio), quantita' negativa, che non sia uno storno. La domanda e' PRELIEVO PER PRELIEVO, come il contratto del posting (vendite.fn_posta_ddt: un movimento per prelievo delle righe attive): anche uno scarico parziale si vede, e prelievi_senza_scarico dice quanti prelievi mancano. Una riga e' la porta del registro che non ha tenuto (lo stato cambia solo dal verbo vendite.fn_cambia_stato_ddt, attraverso script.trgfn_doc_stato_solo_dal_verbo): una bolla uscita senza la sua merce, cioe' una giacenza che mente. Il rimedio non e' scrivere il movimento a mano: e' capire da dove e' passata l'emissione. Una bolla senza magazzino resta fuori: non e' questo difetto. Non vede l'arrivo di un trasferimento, che presidia dbops.vw_ddt_trasferimenti_consegnati_senza_arrivo. security_invoker; il digest conta da proprietario (dbops.fn_conta_presidio, perimetro DEFINER).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_ddt_emessi_senza_scarico
WITH (security_invoker=true) AS
SELECT d.id AS ddt_id,
    d.numero,
    d.data,
    d.emittente_fiscale_id,
    d.magazzino_id,
    s.codice_interno AS stato_codice_interno,
    n.prelievi_senza_scarico
   FROM ((vendite.ddt d
     JOIN script.vw_stati_doc_ddt_merce_partita s ON ((s.id = d.stato_doc_ddt_id)))
     CROSS JOIN LATERAL ( SELECT count(*) AS prelievi_senza_scarico
           FROM (vendite.ddt_righe dr
             JOIN vendite.ddt_righe_prelievi p ON ((p.ddt_riga_id = dr.id)))
          WHERE ((dr.ddt_id = d.id) AND dr.attivo AND (NOT (EXISTS ( SELECT 1
                   FROM (magazzino.movimenti m
                     JOIN config.sorgenti so ON (((so.id = m.sorgente_tipo_id) AND ((so.codice_interno)::text = 'DDT_VENDITA'::text))))
                  WHERE ((m.sorgente_id = d.id) AND (m.sorgente_riga = dr.id) AND (m.sorgente_dettaglio = p.id) AND (m.qta < (0)::numeric) AND (m.storno_di_movimento_id IS NULL))))))) n)
  WHERE (s.merce_partita AND (d.magazzino_id IS NOT NULL) AND (n.prelievi_senza_scarico > 0) AND vendite.fn_ddt_muove_merce(d.*));
```

</div>


---
{% include-markdown "signature-core.md" %}
