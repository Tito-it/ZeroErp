{% include-markdown "it/dbzero/script/manual/vw_indirizzo_completo.md" %}
# 🔍 View `vw_indirizzo_completo`

> 📝 **Descrizione**
>
> Indirizzo completo: stradario + comune + provincia + CAP + via estesa.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_indirizzo_completo AS
SELECT s.id AS id_stradario,
    c.id AS id_comune,
    c.descrizione AS comune,
    p.sigla AS provincia,
    cp.codice AS codice_postale,
    ve.indirizzo_generale,
    s.geoloc,
    s.meta,
    ve.id_via,
    ve.tipo_toponimo,
    ve.nome_strada
   FROM ((((config.stradario s
     JOIN config.comuni c ON ((s.comune_id = c.id)))
     JOIN config.province p ON ((c.provincia_id = p.id)))
     JOIN config.codici_postali cp ON ((s.codice_postale_id = cp.id)))
     JOIN script.vw_stradario_esteso ve ON ((s.stradario_generale_id = ve.id_via)));
```

</div>


---
{% include-markdown "signature-core.md" %}
