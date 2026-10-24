{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_mensile.md" %}
# 🔍 View `vw_dash_competenza_mensile`

> 📝 **Descrizione**
>
> Lente 1 Competenza, aggregata in FORMATO LUNGO: una riga per (competenza_mese, stadio, stato fattura, tipo_movimento, motivo_non_fatturata). Il pivot alla griglia 12 mesi x 4 stadi e' del service, non della vista. security_invoker=on: lo scope emittente arriva da vw_dash_competenza_attivita (GUC fail-closed) e va RI-SPECIFICATO a ogni REPLACE, perche' la reloption non e' visibile in pg_get_viewdef e verrebbe azzerata in silenzio. ⭐ Rev 2026-08-20 (richiesta BE, punto 3): `tipo_movimento` entra nel raggruppamento. Prima si perdeva qui, e il residuo del mese — che e' una somma CON SEGNO — compensava le rettifiche con le fatture da emettere: agosto 2026 segnava 101% di copertura perche' il residuo era −29,50, cioe' due note di credito da emettere. Con una sola fattura da 29,50 in sospeso il residuo sarebbe andato a zero e la dashboard avrebbe detto «100%, niente da fare» con tre documenti da produrre: la compensazione NASCONDE LAVORO. ⭐ E non riguarda le sole rettifiche — a luglio 2026 ci sono 5.000 EUR di ONERI nello stesso totale: la somma mescolava tre cose di natura diversa, ed e' il motivo per cui si aggiunge la DIMENSIONE e non una colonna `valore_rettifiche`, che avrebbe messo i valori dell'enum dentro la vista. 🔴 Cambia la CARDINALITA': 7 righe -&gt; 8 sul dato del 2026-08-20, unico bucket spezzato 2026-07 FATTURATA/EMESSA (NORMALE + ONERE). I totali del consumatore reggono perche' il pivot accumula, ma il breakdown per stato documento fiscale elenca una voce per riga: senza adeguamento BE mostra EMESSA due volte. brief-design-note-credito-resi §40.2. ⭐ Rev 2026-08-26 (D-2, brief-db-residui-competenza-dimensione-e-chiave): `motivo_non_fatturata` entra nel raggruppamento, per la STESSA ragione e nella STESSA forma. Lo stadio EMESSA_NON_FATTURATA guarda solo fattura_riga_id, e dentro quel valore convivono situazioni con RIMEDI OPPOSTI: in attesa del proprio lotto (nessun rimedio, il prossimo giro la prende), dentro un giro vivo (nessun rimedio, si aspetta) e RESIDUO — l'unica su cui «Riporta da emettere» ha effetto. Un numero solo per rimedi opposti dice all'operatore che c'e' qualcosa da fare quando non c'e', o nasconde il lavoro vero dentro un transito sano. ⛔ Dimensione e NON una colonna `n_residui`: quella avrebbe costretto l'aggregata a conoscere il valore RESIDUO, cioe' a cablare un elemento del vocabolario dentro una somma. La dimensione non conosce nessun valore: li porta. 🔴 E cambia di nuovo la CARDINALITA': un bucket EMESSA_NON_FATTURATA che contiene piu' situazioni si spezza in una riga per situazione. I totali reggono, il breakdown no — l'adeguamento BE/FE va fatto nello stesso giro. ⚠️ Il presidio di grana e' il test 22 di db/pgtap/vendite/test-fn-list-commessa-attivita-provenienza-v1.sql, che confronta le righe della mensile col GROUP BY del dettaglio: cambiando la grana va portato sulla regola nuova, mai spento. Rev 2026-10-20 (20261020-81, brief-db-grammatica-unica-documenti L2c-1): ricreata identica dopo l'allargamento di registri_fatturazione.codice a varchar(80) (20261020-74).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_mensile
WITH (security_invoker=on) AS
SELECT competenza_mese,
    stadio,
    stato_fattura_codice_interno,
    (count(*) FILTER (WHERE (NOT emissione_trattenuta)))::integer AS n_attivita,
    COALESCE(sum(valore) FILTER (WHERE (NOT emissione_trattenuta)), (0)::numeric) AS valore_tot,
    COALESCE(sum(valore_fatturato), (0)::numeric) AS valore_fatturato_tot,
    (count(*) FILTER (WHERE emessa_in_ritardo))::integer AS n_in_ritardo,
    COALESCE(sum(valore) FILTER (WHERE emessa_in_ritardo), (0)::numeric) AS valore_in_ritardo,
    tipo_movimento,
    motivo_non_fatturata,
    (count(*) FILTER (WHERE emissione_trattenuta))::integer AS n_attivita_trattenute,
    COALESCE(sum(valore) FILTER (WHERE emissione_trattenuta), (0)::numeric) AS valore_trattenuto
   FROM vendite.vw_dash_competenza_attivita
  GROUP BY competenza_mese, stadio, stato_fattura_codice_interno, tipo_movimento, motivo_non_fatturata;
```

</div>


---
{% include-markdown "signature-core.md" %}
