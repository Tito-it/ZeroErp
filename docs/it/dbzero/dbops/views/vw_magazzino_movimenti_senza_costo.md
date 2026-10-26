{% include-markdown "it/dbzero/dbops/manual/vw_magazzino_movimenti_senza_costo.md" %}
# 🔍 View `vw_magazzino_movimenti_senza_costo`

> 📝 **Descrizione**
>
> Le ENTRATE (qta &gt; 0) scritte SENZA costo unitario: il primo carico senza valore (inventario iniziale senza costo_unitario sulla riga e nessuna media), una rettifica positiva senza media. Un'entrata senza costo non e' un errore: e' un fatto dichiarato (D-L2-c) — il movimento nasce con costo NULL, il valore resta com'e' e la media si diluisce. Le uscite a NULL sono la CONSEGUENZA (nessuna media), non la causa, e non entrano. Natura LAVORAZIONE (una tendenza da guardare, non un guasto): compare nel digest invece di sparire nella media. security_invoker, perimetro DEFINER, cadenza SETTIMANALE. Brief: brief-db-magazzino-lotto-2-motore, sezione 4.4.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_magazzino_movimenti_senza_costo
WITH (security_invoker=true) AS
SELECT id,
    articolo_id,
    magazzino_id,
    data_mov,
    qta,
    causale_id,
    sorgente_tipo_id,
    sorgente_riga,
    sorgente_uid,
    lotto_id,
    asset_id,
    ubicazione_id
   FROM magazzino.movimenti m
  WHERE ((qta > (0)::numeric) AND (costo_unitario IS NULL));
```

</div>


---
{% include-markdown "signature-core.md" %}
