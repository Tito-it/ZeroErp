# 🔍 View `vw_documenti_trattenuti_da_lotto`

> 📝 **Descrizione**
>
> SEDE UNICA della domanda «questo documento e' trattenuto da un lotto ancora in gioco?». Una riga per (documento, lotto che lo trattiene): la gruppo_key e il lotto, col suo stato. Consumatori: la riga di vw_dash_competenza_gruppi (il motivo a video), vw_dash_competenza_gruppi_riepilogo (il conteggio della card) e vendite.fn_list_emittibili_lane (perche' un secondo giro non se lo prenda).
> ⭐ «IN GIOCO» SI LEGGE DAL FLAG `config.stati_doc_fiscale.is_abortito`, mai da un elenco di stati. ⚠️ E mai da `congela_fiscale`, che e' l'asse piu' usato in questo dominio e su ANNULLATA vale TRUE: chi cercasse li' «il lotto e' ancora vivo» prenderebbe la risposta sbagliata proprio sulla riga che conta. Sono tre assi distinti (is_abortito, congela_fiscale, chiude_lotto) e vanno chiamati per nome.
> ⭐ FAIL-CLOSED: un lotto il cui stato non si risolve (LEFT JOIN a vuoto) risulta TRATTENUTO. Non sapere in che stato e' il giro non e' un buon motivo per lasciarci mettere le mani — stessa scelta di script.fn_check_documento_escludibile_da_giro sul confine pre-fiscale.
> ⛔ UN DOCUMENTO USCITO DAL GIRO NON TRATTIENE NIENTE: l'esito ESCLUSO e' escluso. E' la regola «un documento fuori dal giro non si marca, non si conta, non blocca», vista dal terzo lato.
> ⚠️ PUO' TORNARE PIU' DI UNA RIGA per la stessa gruppo_key: e' esattamente il difetto che questa vista serve a chiudere (lo stesso documento in due lotti vivi). Chi ne vuole UNO deve ordinare — un LIMIT 1 senza ORDER BY scommette.
> ⚠️ PERCHE' NON BASTAVA CIO' CHE C'ERA: script.fn_get_stato_push_segment sa dire LIBERA / ALLOCATA / EMESSA, cioe' misura l'ESITO del lavoro, non il fatto che il lavoro sia IN CORSO. Manca la terza domanda — «e' dentro un giro che non ha ancora finito?» — ed e' questa vista. Per la stessa ragione le cinque fn_list_*_da_pushare NON si toccano: la regola loro (LIBERA) c'e' gia'.
> Brief: brief-db-documento-trattenuto-da-un-lotto-vivo.md (T-1).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_documenti_trattenuti_da_lotto
WITH (security_invoker=true) AS
SELECT le.gruppo_key,
    l.id AS lotto_id,
    l.codice AS lotto_codice,
    l.competenza_mese AS lotto_competenza_mese,
    sdf.codice_interno AS lotto_stato,
    le.stato_esecuzione AS esito
   FROM ((vendite.fatturazione_lotti_esiti le
     JOIN vendite.fatturazione_lotti l ON ((l.id = le.lotto_id)))
     LEFT JOIN config.stati_doc_fiscale sdf ON ((sdf.id = l.stato_doc_fiscale_id)))
  WHERE ((le.stato_esecuzione <> 'ESCLUSO'::text) AND (COALESCE(sdf.is_abortito, false) = false));
```


---
{% include-markdown "signature-core.md" %}
