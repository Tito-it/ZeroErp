{% include-markdown "it/dbzero/vendite/manual/vw_fattura_righe_esposte.md" %}
# 🔍 View `vw_fattura_righe_esposte`

> 📝 **Descrizione**
>
> Rappresentazione del documento per OGNI uscita verso l'esterno: PDF, XML SDI, portale. ⚠️ NON e' «la vista di stampa»: se il PDF mostrasse il kit raggruppato e l'XML trasmettesse i componenti avremmo due uscite dello stesso documento con dettagli diversi. vendite.fatture_righe resta il DETTAGLIO (tutte le componenti, con articolo/quantita'/prezzo propri), questa vista produce la SINTESI — nessun secondo dato da tenere allineato. Tre regole, dal modello unificato componenti BoM del 2026-05-13: riga non-kit invariata; kit come UNA riga padre che porta il totale; componenti con esposto_in_fattura=TRUE come righe DESCRITTIVE senza importo (NULL, non zero). I componenti non esposti non compaiono: il loro valore e' gia' nel totale del padre, quindi il totale del documento non cambia mai al variare dell'esposizione. Convenzioni: quantita' del padre = MEDIA dei componenti (regge finche' coeff_qta_snapshot vale 1), riga_nr = il primo dei componenti, prezzo unitario derivato come totale/quantita'. La riga padre e' costruita per (fattura, kit, IVA, BA destinatario): un kit con aliquote diverse produce due righe padre, che e' l'esito corretto. Ordinamento: `ordinamento` + `livello` dispongono i componenti sotto il proprio padre. ⭐ rev 2026-08-31 (decisione B, brief-db-richieste-aperte-dal-backend voce 5): LA VISTA CONOSCE LA RIGA SPEZZATA DAL PLAFOND. Quando il plafond di un titolo IVA copre solo una quota dell'imponibile la riga di fattura si spezza in due — per OBBLIGO DI FORMATO, perche' una riga FatturaPA porta una sola AliquotaIVA e una sola Natura — e le due parti escono qui come DUE RIGHE SORELLE: entrambe col loro imponibile, entrambe a livello 0, stesso `ordinamento` (quello della capofila, cosi' restano attaccate anche se fra loro cade un'altra riga), e `tipo_riga` = PARTE_PLAFOND sulla parte. La colonna `riga_capofila_id` e' esposta in coda perche' chi consuma possa raggruppare senza rifare il join. ⛔ NON SI E' RIUSATA LA FORMA DEL KIT, e non e' una preferenza: quella AGGREGA, e aggregare le due parti produrrebbe UN SOLO DettaglioLinee, cioe' cancellerebbe la ragione per cui la riga si e' spezzata. ⛔ E non si e' usato `livello 1`, che in questa vista significa «riga descrittiva SENZA importo»: il codice che fa «salta il livello 1» esiste perche' e' la regola della vista, e su una fattura spezzata perderebbe la seconda parte senza nessun errore, con un totale semplicemente piu' basso. ⚠️ `riga_nr` NON cambia: e' il numero di linea del documento, quello che RiferimentoNumeroLinea indirizza. 📌 Limite dichiarato: una riga che e' insieme componente di kit E parte di plafond cade nei rami del kit, dove il raggruppamento include gia' iva_id e quindi produce due righe padre distinte (regola R13, esito corretto) — ma li' le due parti non si vedono come una sola origine. Il caso non e' stato costruito perche' oggi il backend non spezza i componenti di kit. brief-fix-importi-riga-fattura-zero §4.7-bis (D5) + brief-db-richieste-aperte-dal-backend voce 5.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_fattura_righe_esposte
WITH (security_invoker=on) AS
WITH kit AS NOT MATERIALIZED (
         SELECT r.fattura_id,
            r.kit_key,
            r.iva_id,
            r.dest_billing_account_id,
            r.kit_articolo_padre_id AS articolo_padre_id,
            r.kit_descrizione_padre AS descrizione_padre,
            min(r.riga_nr) AS riga_nr_padre,
            max(r.uom_id) AS uom_id,
            avg(r.qta) AS qta_media,
            sum(r.imponibile_riga) AS imponibile_totale,
            max((r.iva_natura)::text) AS iva_natura
           FROM vendite.fatture_righe r
          WHERE (r.kit_key IS NOT NULL)
          GROUP BY r.fattura_id, r.kit_key, r.iva_id, r.dest_billing_account_id, r.kit_articolo_padre_id, r.kit_descrizione_padre
        )
 SELECT r.fattura_id,
        CASE
            WHEN (r.riga_capofila_id IS NOT NULL) THEN 'PARTE_PLAFOND'::text
            ELSE 'NORMALE'::text
        END AS tipo_riga,
    r.riga_nr,
    COALESCE(cap.riga_nr, r.riga_nr) AS ordinamento,
    (0)::smallint AS livello,
    r.id AS fatture_righe_id,
    r.articolo_id,
    r.descrizione,
    r.uom_id,
    r.qta,
    r.prezzo_unitario,
    r.sconto_percentuale,
    r.iva_id,
    r.iva_natura,
    r.imponibile_riga AS imponibile,
    r.dest_billing_account_id,
    NULL::text AS kit_key,
    r.riga_capofila_id
   FROM (vendite.fatture_righe r
     LEFT JOIN vendite.fatture_righe cap ON ((cap.id = r.riga_capofila_id)))
  WHERE (r.kit_key IS NULL)
UNION ALL
 SELECT k.fattura_id,
    'KIT_PADRE'::text AS tipo_riga,
    k.riga_nr_padre AS riga_nr,
    k.riga_nr_padre AS ordinamento,
    (0)::smallint AS livello,
    NULL::bigint AS fatture_righe_id,
    k.articolo_padre_id AS articolo_id,
    k.descrizione_padre AS descrizione,
    k.uom_id,
    k.qta_media AS qta,
        CASE
            WHEN (COALESCE(k.qta_media, (0)::numeric) = (0)::numeric) THEN NULL::numeric
            ELSE (k.imponibile_totale / k.qta_media)
        END AS prezzo_unitario,
    NULL::numeric AS sconto_percentuale,
    k.iva_id,
    k.iva_natura,
    k.imponibile_totale AS imponibile,
    k.dest_billing_account_id,
    k.kit_key,
    NULL::bigint AS riga_capofila_id
   FROM kit k
UNION ALL
 SELECT r.fattura_id,
    'KIT_COMPONENTE'::text AS tipo_riga,
    r.riga_nr,
    k.riga_nr_padre AS ordinamento,
    (1)::smallint AS livello,
    r.id AS fatture_righe_id,
    r.articolo_id,
    r.descrizione,
    r.uom_id,
    r.qta,
    NULL::numeric AS prezzo_unitario,
    NULL::numeric AS sconto_percentuale,
    r.iva_id,
    r.iva_natura,
    NULL::numeric AS imponibile,
    r.dest_billing_account_id,
    r.kit_key,
    r.riga_capofila_id
   FROM (vendite.fatture_righe r
     JOIN kit k ON (((k.fattura_id = r.fattura_id) AND (k.kit_key = r.kit_key) AND (NOT (k.iva_id IS DISTINCT FROM r.iva_id)) AND (NOT (k.dest_billing_account_id IS DISTINCT FROM r.dest_billing_account_id)))))
  WHERE ((r.kit_key IS NOT NULL) AND (r.kit_esposto_in_fattura IS TRUE));
```


---
{% include-markdown "signature-core.md" %}
