{% include-markdown "it/dbzero/catalogo/manual/vw_causali_onere_assegnabili.md" %}
# 🔍 View `vw_causali_onere_assegnabili`

> 📝 **Descrizione**
>
> Le causali onere (config.causali_onere) che si possono dare a un articolo nuovo: quelle non ancora legate a nessun articolo, perche' il legame articolo-causale e' 1:1 (uq_articoli_causale_onere; il guard catalogo.trgfn_articoli_guard_onere_natura rifiuta il doppione con E_ARTICOLO_CAUSALE_ONERE_GIA_USATA). Ha la forma del lookup generico (id, codice, codice_interno, descrizione, attivo) ed e' registrata in config.tabelle_gestibili con lookup = true: la tendina la legge da dbops.fn_get_lookup_codici, che filtra le attive. La causale dell'articolo aperto non c'e', perche' e' legata a lui: il drawer la legge da catalogo.vw_articoli_dettaglio. Nessuna security_invoker: config.causali_onere e catalogo.articoli non hanno RLS.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW catalogo.vw_causali_onere_assegnabili AS
SELECT id,
    codice,
    codice_interno,
    descrizione,
    attivo
   FROM config.causali_onere co
  WHERE (NOT (EXISTS ( SELECT 1
           FROM catalogo.articoli a
          WHERE (a.causale_onere_id = co.id))));
```

</div>


---
{% include-markdown "signature-core.md" %}
