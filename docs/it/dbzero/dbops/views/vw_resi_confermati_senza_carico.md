# 🔍 View `vw_resi_confermati_senza_carico`

> 📝 **Descrizione**
>
> Presidio, DEVE restare vuota. Una riga e' un reso CONFERMATO, con un magazzino, che fa rientrare merce (vendite.fn_reso_muove_merce), senza nessun carico a registro da uno dei suoi rientri (sorgente RESO_VENDITA_RIENTRO, quantita' positiva, non uno storno). E' la porta del registro del reso che non ha tenuto: merce tornata dal cliente che la giacenza non vede. Il rimedio non e' scrivere il movimento a mano: e' capire da dove e' passata la conferma. I resi confermati prima del Lotto 3-bis non hanno magazzino e non sono questo difetto. Gemella di dbops.vw_ddt_emessi_senza_scarico (stessa domanda sul verso opposto: un documento ha passato lo stato che muove merce, e le sue sorgenti non hanno il movimento). security_invoker; il digest conta da proprietario (fn_conta_presidio, perimetro DEFINER). Brief: brief-db-magazzino-lotto-3-bis-carico-da-reso (P-13).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_resi_confermati_senza_carico
WITH (security_invoker=true) AS
SELECT r.id AS reso_id,
    r.numero,
    r.data,
    r.emittente_fiscale_id,
    r.magazzino_id,
    s.codice_interno AS stato_codice_interno
   FROM (vendite.resi r
     JOIN config.stati_doc_reso s ON ((s.id = r.stato_doc_reso_id)))
  WHERE (((s.codice_interno)::text = 'CONFERMATO'::text) AND (r.magazzino_id IS NOT NULL) AND vendite.fn_reso_muove_merce(r.*) AND (NOT (EXISTS ( SELECT 1
           FROM (((vendite.resi_righe rr
             JOIN vendite.resi_righe_rientri x ON ((x.resi_riga_id = rr.id)))
             JOIN magazzino.movimenti m ON ((m.sorgente_riga = x.id)))
             JOIN config.sorgenti so ON (((so.id = m.sorgente_tipo_id) AND ((so.codice_interno)::text = 'RESO_VENDITA_RIENTRO'::text))))
          WHERE ((rr.reso_id = r.id) AND (m.qta > (0)::numeric) AND (m.storno_di_movimento_id IS NULL))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
