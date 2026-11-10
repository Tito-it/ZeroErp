{% include-markdown "it/dbzero/dbops/manual/vw_magazzino_movimenti_senza_costo.md" %}
# 🔍 View `vw_magazzino_movimenti_senza_costo`

> 📝 **Descrizione**
>
> Le ENTRATE (qta &gt; 0) scritte SENZA costo unitario, esclusi gli storni. Chi le scrive, tutti attraverso la primitiva magazzino.fn_scrivi_movimento: il primo carico senza valore (magazzino.fn_posta_inventario, riga senza costo_unitario e nessuna media), una rettifica positiva senza media (magazzino.fn_posta_rettifica), il carico da reso di una merce uscita senza costo e senza media al rientro (vendite.fn_posta_reso), l'entrata gemella di un trasferimento la cui uscita era senza costo (magazzino.fn_posta_trasferimento, vendite.fn_posta_ddt all'arrivo). Un'entrata senza costo non e' un errore: e' un fatto dichiarato, il movimento nasce con costo NULL, il valore resta com'e' e la media si diluisce. Le uscite a NULL sono la CONSEGUENZA (nessuna media), non la causa, e non entrano. Gli STORNI non entrano (magazzino.fn_storna_movimenti_sorgente): lo storno di un'uscita senza costo e' un'entrata senza costo che rende allo stesso magazzino la quantita' uscita a valore zero, e la media torna com'era; la causa e' gia' qui. L'entrata gemella di un trasferimento invece resta: diluisce la media del magazzino d'arrivo. Natura LAVORAZIONE (una tendenza da guardare, non un guasto): compare nel digest invece di sparire nella media. security_invoker, perimetro DEFINER, cadenza SETTIMANALE.

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
    ubicazione_id,
    sorgente_id,
    sorgente_dettaglio
   FROM magazzino.movimenti m
  WHERE ((qta > (0)::numeric) AND (costo_unitario IS NULL) AND (storno_di_movimento_id IS NULL));
```

</div>


---
{% include-markdown "signature-core.md" %}
