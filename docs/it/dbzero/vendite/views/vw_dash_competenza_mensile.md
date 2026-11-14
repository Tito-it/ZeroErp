{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_mensile.md" %}
# 🔍 View `vw_dash_competenza_mensile`

> 📝 **Descrizione**
>
> Lente 1 Competenza, aggregata in FORMATO LUNGO: una riga per (competenza_mese, stadio, stato fattura, tipo_movimento, motivo_non_fatturata). Il pivot alla griglia 12 mesi x 4 stadi e' del service, non della vista. security_invoker=on: lo scope emittente arriva da vw_dash_competenza_attivita (GUC fail-closed) e va RI-SPECIFICATO a ogni REPLACE, perche' la reloption non e' visibile in pg_get_viewdef e verrebbe azzerata in silenzio. ⭐ `tipo_movimento` e' nel raggruppamento perche' il valore e' una somma CON SEGNO: senza, le rettifiche (note di credito da emettere) compenserebbero le fatture da emettere, e il residuo del mese potrebbe dire «niente da fare» con documenti ancora da produrre: la compensazione NASCONDE LAVORO. Lo stesso vale per gli ONERI, che sono un'altra natura nello stesso totale. Per questo e' una DIMENSIONE e non una colonna `valore_rettifiche`, che metterebbe i valori dell'enum dentro la vista. ⭐ `motivo_non_fatturata` e' nel raggruppamento per la STESSA ragione e nella STESSA forma. Lo stadio EMESSA_NON_FATTURATA guarda solo fattura_riga_id, e dentro quel valore convivono situazioni con RIMEDI OPPOSTI: dentro un giro vivo (GIRO_IN_CORSO, nessun rimedio: si aspetta), RESIDUO (l'unica su cui «Riporta da emettere» ha effetto) e SENZA_ATTIVITA_FATTURABILE. Un numero solo per rimedi opposti dice all'operatore che c'e' qualcosa da fare quando non c'e', o nasconde il lavoro vero dentro un transito sano. ⛔ Dimensione e NON una colonna `n_residui`: quella costringerebbe l'aggregata a conoscere il valore RESIDUO, cioe' a cablare un elemento del vocabolario dentro una somma. La dimensione non conosce nessun valore: li porta. ⚠️ Le due dimensioni spezzano un bucket in una riga per (tipo_movimento, motivo_non_fatturata): i totali reggono se il consumatore accumula, un breakdown che elenca una voce per riga mostra invece lo stesso stato piu' volte. ⚠️ Il presidio di grana e' il test 22 di db/pgtap/vendite/test-fn-list-commessa-attivita-provenienza-v1.sql, che confronta le righe della mensile col GROUP BY del dettaglio: cambiando la grana va portato sulla regola nuova, mai spento.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

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
