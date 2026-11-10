{% include-markdown "it/dbzero/dbops/manual/vw_ambiente_non_dichiarato.md" %}
# 🔍 View `vw_ambiente_non_dichiarato`

> 📝 **Descrizione**
>
> PRESIDIO: una riga se questa installazione non ha ancora dichiarato il suo ambiente (dbops.installazione vuota). DEVE restare vuota. La tabella nasce vuota di proposito, senza un default da changeSet: l'ambiente lo scrive una volta la fase post di scripts/sql/provision_zeroerp.sql con -v ambiente=SVILUPPO|PRODUZIONE. Finche' manca, script.fn_ambiente_installazione() da' E_CONFIG_MANCANTE: il provisioning di sviluppo non parte e le sveglie spegnibili falliscono. Questo presidio dice la causa una volta, a chi la sistema; il panorama dei processi non ha una causa per questo (un fatto, un presidio). Legge script.fn_ambiente_dichiarato(), che non solleva.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_ambiente_non_dichiarato AS
SELECT (current_database())::text AS database_nome
  WHERE (script.fn_ambiente_dichiarato() IS NULL);
```

</div>


---
{% include-markdown "signature-core.md" %}
