{% include-markdown "it/dbzero/dbops/manual/vw_resi_confermati_senza_carico.md" %}
# 🔍 View `vw_resi_confermati_senza_carico`

> 📝 **Descrizione**
>
> Presidio, DEVE restare vuota. Una riga e' un reso in uno stato in cui la merce e' rientrata (il BB script.vw_stati_doc_reso_merce_rientrata: oltre la bozza, non abortito), con un magazzino, che fa rientrare merce (vendite.fn_reso_muove_merce), con almeno un rientro di una riga attiva senza il suo carico a registro: un movimento di magazzino.movimenti con provenienza RESO_VENDITA (il reso, la riga, il rientro come dettaglio), quantita' positiva, che non sia uno storno. La domanda e' RIENTRO PER RIENTRO, come il contratto del posting (vendite.fn_posta_reso: un carico per rientro delle righe attive): anche un carico parziale si vede, e rientri_senza_carico dice quanti rientri mancano. Una riga e' la porta del registro del reso che non ha tenuto (lo stato cambia solo dai verbi del reso, attraverso script.trgfn_doc_stato_solo_dal_verbo; la conferma e' vendite.fn_conferma_reso): merce tornata dal cliente che la giacenza non vede. Il rimedio non e' scrivere il movimento a mano: e' capire da dove e' passata la conferma. Un reso senza magazzino resta fuori: non e' questo difetto. Gemella di dbops.vw_ddt_emessi_senza_scarico, la stessa domanda sul verso opposto. security_invoker; il digest conta da proprietario (dbops.fn_conta_presidio, perimetro DEFINER).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_resi_confermati_senza_carico
WITH (security_invoker=true) AS
SELECT r.id AS reso_id,
    r.numero,
    r.data,
    r.emittente_fiscale_id,
    r.magazzino_id,
    s.codice_interno AS stato_codice_interno,
    n.rientri_senza_carico
   FROM ((vendite.resi r
     JOIN script.vw_stati_doc_reso_merce_rientrata s ON ((s.id = r.stato_doc_reso_id)))
     CROSS JOIN LATERAL ( SELECT count(*) AS rientri_senza_carico
           FROM (vendite.resi_righe rr
             JOIN vendite.resi_righe_rientri x ON ((x.resi_riga_id = rr.id)))
          WHERE ((rr.reso_id = r.id) AND rr.attivo AND (NOT (EXISTS ( SELECT 1
                   FROM (magazzino.movimenti m
                     JOIN config.sorgenti so ON (((so.id = m.sorgente_tipo_id) AND ((so.codice_interno)::text = 'RESO_VENDITA'::text))))
                  WHERE ((m.sorgente_id = r.id) AND (m.sorgente_riga = rr.id) AND (m.sorgente_dettaglio = x.id) AND (m.qta > (0)::numeric) AND (m.storno_di_movimento_id IS NULL))))))) n)
  WHERE (s.merce_rientrata AND (r.magazzino_id IS NOT NULL) AND (n.rientri_senza_carico > 0) AND vendite.fn_reso_muove_merce(r.*));
```

</div>


---
{% include-markdown "signature-core.md" %}
