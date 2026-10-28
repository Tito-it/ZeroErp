{% include-markdown "it/dbzero/dbops/manual/vw_sorgenti_orfane.md" %}
# 🔍 View `vw_sorgenti_orfane`

> 📝 **Descrizione**
>
> Presidio degli ORFANI di sorgente (D-9): SELECT * FROM dbops.fn_sorgenti_orfane(). DEVE RESTARE VUOTA. Una riga = una tabella del perimetro (le sei di magazzino comprese) con una sorgente che punta a un record sparito. Natura ZERO, perimetro DEFINER (la funzione attraversa la RLS), cadenza SETTIMANALE. Il rimedio non e' cancellare la riga: e' capire chi ha cancellato il bersaglio. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.7.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_sorgenti_orfane AS
SELECT tabella,
    riga_id,
    sorgente_tipo_id,
    sorgente_codice_interno,
    sorgente_riga,
    sorgente_uid,
    target_table
   FROM dbops.fn_sorgenti_orfane() o(tabella, riga_id, sorgente_tipo_id, sorgente_codice_interno, sorgente_riga, sorgente_uid, target_table);
```

</div>


---
{% include-markdown "signature-core.md" %}
