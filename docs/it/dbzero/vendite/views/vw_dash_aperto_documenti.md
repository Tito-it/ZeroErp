{% include-markdown "it/dbzero/vendite/manual/vw_dash_aperto_documenti.md" %}
# 🔍 View `vw_dash_aperto_documenti`

> 📝 **Descrizione**
>
> Situazione aperta v2 (serbatoio pre-commessa): stock dei documenti APERTI E NON CONCLUSI delle 4 aree (PREVENTIVI/ORDINI/OFFERTE/CONTRATTI — no COMMESSE, coperte dalla Lente 1), SENZA asse temporale. Perimetro (DL-15): area&lt;&gt;COMMESSE AND NOT is_abortito AND is_transitato IS DISTINCT FROM true AND fase&lt;&gt;CHIUSO. Eliminato il concetto "transitato" (DL-14): via is_transitato/is_aperto(col)/valore_transitato/unita_transitate dalla proiezione. Perimetro unico per vw_dash_aperto_riepilogo e per il drill-down BE (il filtro "aperti da oltre N giorni" e' BE-side su data_riferimento). security_invoker=on (scope emittente RLS). ⭐ Rev 2026-08-18 (R-4, brief perimetro-emittente Fase E): aggiunta in coda `emittente_ragione_sociale`, che arriva gia' risolta da vw_dash_fatturazione_documenti. ⚠️ Andava ELENCATA: la proiezione e' a colonne esplicite e non eredita nulla dalla vista a monte — il brief dava questa lista per «eredita» e sarebbe uscita una colonna vuota senza nessun errore a segnalarlo. Rev 2026-10-20 (20261020-72, brief-db-grammatica-unica-documenti 2d, G-6): l'area COMMESSE diventa COMMESSA, il codice della sorgente (il plurale e' ritirato).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_aperto_documenti
WITH (security_invoker=on) AS
SELECT area,
    documento_id,
    documento_uid,
    codice,
    emittente_fiscale_id,
    emittente_soggetto_ruolo_id,
    cliente_display,
    fase,
    stato_codice_interno,
    stato_codice,
    valore_totale,
    unita_totali,
    motivo_fermo,
    data_riferimento,
    emittente_ragione_sociale
   FROM vendite.vw_dash_fatturazione_documenti d
  WHERE (((area)::text <> 'COMMESSA'::text) AND (NOT is_abortito) AND (is_transitato IS DISTINCT FROM true) AND ((fase)::text <> 'CHIUSO'::text));
```

</div>


---
{% include-markdown "signature-core.md" %}
