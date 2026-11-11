{% include-markdown "it/dbzero/catalogo/manual/vw_unita_misura_conversioni_dettaglio.md" %}
# 🔍 View `vw_unita_misura_conversioni_dettaglio`

> 📝 **Descrizione**
>
> Le conversioni generali fra unita' di misura (catalogo.unita_misura_conversioni) per la lista e il drawer: le colonne della tabella, codice e descrizione delle due unita' e la capability di riga, che dice che cosa il database lascia fare oggi. La da' catalogo.fn_uom_conversione_capability, lo stesso giudizio di catalogo.trgfn_uom_guard_storia: puo_eliminarsi e puo_cambiare_attivo (spegnere o riaccendere) solo su una conversione senza giorni passati (motivo_non_eliminabile UOM_STORIA_IN_VIGORE); puo_chiudersi se la fine e' vuota o non ancora passata (motivo_non_chiudibile UOM_STORIA_CHIUSA), con data_min_chiusura (la piu' tarda fra inizio e ieri) e data_default_chiusura (la piu' tarda fra inizio e oggi). Le colonne che non si cambiano mai (le due unita', il fattore, l'inizio) il form le legge da dbops.vw_non_editable_fields. Sorgente della lista configurabile catalogo.conversioni_uom. Tutte le righe, anche le spente e le chiuse: filtro e ordine li mette chi legge. Gemella di catalogo.vw_articoli_uom_operativa_dettaglio. Nessuna security_invoker: le tabelle lette non hanno RLS.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_unita_misura_conversioni_dettaglio AS
SELECT c.id,
    c.uom_from_id,
    c.uom_to_id,
    c.fattore,
    c.valido_dal,
    c.valido_al,
    c.validita,
    c.attivo,
    c.meta,
    c.data_insert,
    c.user_insert,
    c.data_update,
    c.user_update,
    uf.codice AS uom_from_codice,
    uf.descrizione AS uom_from_descrizione,
    ut.codice AS uom_to_codice,
    ut.descrizione AS uom_to_descrizione,
    cap.puo_eliminarsi,
    cap.motivo_non_eliminabile,
    cap.puo_cambiare_attivo,
    cap.puo_chiudersi,
    cap.data_min_chiusura,
    cap.data_default_chiusura,
    cap.motivo_non_chiudibile
   FROM (((catalogo.unita_misura_conversioni c
     JOIN catalogo.unita_misura uf ON ((uf.id = c.uom_from_id)))
     JOIN catalogo.unita_misura ut ON ((ut.id = c.uom_to_id)))
     CROSS JOIN LATERAL catalogo.fn_uom_conversione_capability(c.valido_dal, c.valido_al) cap(puo_eliminarsi, puo_cambiare_attivo, puo_chiudersi, data_min_chiusura, data_default_chiusura, motivo_non_eliminabile, motivo_non_chiudibile));
```

</div>


---
{% include-markdown "signature-core.md" %}
