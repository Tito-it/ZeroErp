# 🔍 View `vw_ddt_emessi_senza_scarico`

> 📝 **Descrizione**
>
> Presidio, DEVE restare vuota. Una riga e' una bolla in uno stato che presuppone lo scarico (EMESSO, SPEDITO, CONSEGNATO, RESO), con un magazzino, che muove merce (vendite.fn_ddt_muove_merce), senza nessuna uscita a registro da uno dei suoi prelievi (sorgente DDT_VENDITA_PRELIEVO, quantita' negativa, non uno storno). E' la porta del registro che non ha tenuto: una bolla uscita senza la sua merce, cioe' una giacenza che mente. Il rimedio non e' scrivere il movimento a mano: e' capire da dove e' passata l'emissione. Le bolle senza magazzino sono nate prima del Lotto 3 e non sono questo difetto. security_invoker; il digest conta da proprietario (fn_conta_presidio, perimetro DEFINER). Brief: brief-db-magazzino-lotto-3-scarico-da-ddt (P-13).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW dbops.vw_ddt_emessi_senza_scarico
WITH (security_invoker=true) AS
SELECT d.id AS ddt_id,
    d.numero,
    d.data,
    d.emittente_fiscale_id,
    d.magazzino_id,
    s.codice_interno AS stato_codice_interno
   FROM (vendite.ddt d
     JOIN config.stati_doc_ddt s ON ((s.id = d.stato_doc_ddt_id)))
  WHERE (((s.codice_interno)::text = ANY ((ARRAY['EMESSO'::character varying, 'SPEDITO'::character varying, 'CONSEGNATO'::character varying, 'RESO'::character varying])::text[])) AND (d.magazzino_id IS NOT NULL) AND vendite.fn_ddt_muove_merce(d.*) AND (NOT (EXISTS ( SELECT 1
           FROM (((vendite.ddt_righe dr
             JOIN vendite.ddt_righe_prelievi p ON ((p.ddt_riga_id = dr.id)))
             JOIN magazzino.movimenti m ON ((m.sorgente_riga = p.id)))
             JOIN config.sorgenti so ON (((so.id = m.sorgente_tipo_id) AND ((so.codice_interno)::text = 'DDT_VENDITA_PRELIEVO'::text))))
          WHERE ((dr.ddt_id = d.id) AND (m.qta < (0)::numeric) AND (m.storno_di_movimento_id IS NULL))))));
```


---
{% include-markdown "signature-core.md" %}
