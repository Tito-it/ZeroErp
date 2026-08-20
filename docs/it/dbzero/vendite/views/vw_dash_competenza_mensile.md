{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_mensile.md" %}
# 🔍 View `vw_dash_competenza_mensile`

> 📝 **Descrizione**
>
> Lente 1 Competenza, aggregata in FORMATO LUNGO: una riga per (competenza_mese, stadio, stato fattura, tipo_movimento). Il pivot alla griglia 12 mesi x 4 stadi e' del service, non della vista. security_invoker=on: lo scope emittente arriva da vw_dash_competenza_attivita (GUC fail-closed) e va RI-SPECIFICATO a ogni REPLACE, perche' la reloption non e' visibile in pg_get_viewdef e verrebbe azzerata in silenzio. ⭐ Rev 2026-08-20 (richiesta BE, punto 3): `tipo_movimento` entra nel raggruppamento. Prima si perdeva qui, e il residuo del mese — che e' una somma CON SEGNO — compensava le rettifiche con le fatture da emettere: agosto 2026 segnava 101% di copertura perche' il residuo era −29,50, cioe' due note di credito da emettere. Con una sola fattura da 29,50 in sospeso il residuo sarebbe andato a zero e la dashboard avrebbe detto «100%, niente da fare» con tre documenti da produrre: la compensazione NASCONDE LAVORO. ⭐ E non riguarda le sole rettifiche — a luglio 2026 ci sono 5.000 EUR di ONERI nello stesso totale: la somma mescolava tre cose di natura diversa, ed e' il motivo per cui si aggiunge la DIMENSIONE e non una colonna `valore_rettifiche`, che avrebbe messo i valori dell'enum dentro la vista. 🔴 Cambia la CARDINALITA': 7 righe -&gt; 8 sul dato del 2026-08-20, unico bucket spezzato 2026-07 FATTURATA/EMESSA (NORMALE + ONERE). I totali del consumatore reggono perche' il pivot accumula, ma il breakdown per stato documento fiscale elenca una voce per riga: senza adeguamento BE mostra EMESSA due volte. brief-design-note-credito-resi §40.2.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_mensile
WITH (security_invoker=on) AS
SELECT competenza_mese,
    stadio,
    stato_fattura_codice_interno,
    (count(*))::integer AS n_attivita,
    COALESCE(sum(valore), (0)::numeric) AS valore_tot,
    COALESCE(sum(valore_fatturato), (0)::numeric) AS valore_fatturato_tot,
    (count(*) FILTER (WHERE emessa_in_ritardo))::integer AS n_in_ritardo,
    COALESCE(sum(valore) FILTER (WHERE emessa_in_ritardo), (0)::numeric) AS valore_in_ritardo,
    tipo_movimento
   FROM vendite.vw_dash_competenza_attivita
  GROUP BY competenza_mese, stadio, stato_fattura_codice_interno, tipo_movimento;
```


---
{% include-markdown "signature-core.md" %}
