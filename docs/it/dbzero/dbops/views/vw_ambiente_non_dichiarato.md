{% include-markdown "it/dbzero/dbops/manual/vw_ambiente_non_dichiarato.md" %}
# 🔍 View `vw_ambiente_non_dichiarato`

> 📝 **Descrizione**
>
> PRESIDIO: una riga se questa installazione non ha ancora dichiarato il suo ambiente (dbops.installazione vuota). DEVE restare vuota. La tabella nasce vuota di proposito (nessun default da un changeSet, R-2): l'ambiente lo scrive la fase post di scripts/sql/provision_zeroerp.sql con -v ambiente=SVILUPPO|PRODUZIONE, una volta. Finche' manca, script.fn_ambiente_installazione() da' E_CONFIG_MANCANTE: il provisioning di sviluppo non parte e le sveglie spegnibili falliscono. Questo presidio dice la causa una volta, a chi la sistema. Il panorama dei processi non ha una causa per questo: un fatto, un presidio. Legge script.fn_ambiente_dichiarato(), che non solleva. Brief: brief-db-processi-accensione-per-ambiente (R-2).

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_ambiente_non_dichiarato AS
SELECT (current_database())::text AS database_nome
  WHERE (script.fn_ambiente_dichiarato() IS NULL);
```

</div>


---
{% include-markdown "signature-core.md" %}
