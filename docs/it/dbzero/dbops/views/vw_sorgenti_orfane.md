{% include-markdown "it/dbzero/dbops/manual/vw_sorgenti_orfane.md" %}
# 🔍 View `vw_sorgenti_orfane`

> 📝 **Descrizione**
>
> Presidio degli ORFANI di sorgente: SELECT * FROM dbops.fn_sorgenti_orfane(). DEVE RESTARE VUOTA. Una riga = un record con una provenienza che punta a un documento, una riga o un dettaglio sparito (livello), in una tabella del perimetro della provenienza. Natura ZERO, perimetro DEFINER (la funzione attraversa la RLS), cadenza SETTIMANALE. Il rimedio non e' cancellare la riga: e' capire chi ha cancellato l'origine.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_sorgenti_orfane AS
SELECT tabella,
    riga_id,
    grammatica,
    livello,
    sorgente_tipo_id,
    sorgente_codice_interno,
    sorgente_id,
    sorgente_uid,
    sorgente_riga,
    sorgente_dettaglio,
    target_table
   FROM dbops.fn_sorgenti_orfane() o(tabella, riga_id, grammatica, livello, sorgente_tipo_id, sorgente_codice_interno, sorgente_id, sorgente_uid, sorgente_riga, sorgente_dettaglio, target_table);
```

</div>


---
{% include-markdown "signature-core.md" %}
