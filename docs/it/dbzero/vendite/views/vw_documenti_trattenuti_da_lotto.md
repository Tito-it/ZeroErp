# 🔍 View `vw_documenti_trattenuti_da_lotto`

> 📝 **Descrizione**
>
> SEDE UNICA della domanda «questo documento e' trattenuto da un lotto ancora in gioco?». Una riga per (documento, lotto che lo trattiene): la gruppo_key e il lotto, col suo stato e la sua competenza. Consumatori: la riga di vw_dash_competenza_gruppi (il motivo a video), il conteggio della card, vendite.fn_list_emittibili_lane e il pull (perche' un secondo giro non se lo prenda).
> ⭐ «IN GIOCO» SI LEGGE DALLA SEDE UNICA vendite.vw_lotti_fase (rev 2026-09-09), mai da un elenco di stati e mai piu' da `is_abortito`. ⛔ Fino al 20260909-23 il predicato era `NOT is_abortito`, cioe' «non annullato»: ma un lotto DEFINITIVA non e' annullato, e' CHIUSO — quindi un documento fatturato in un lotto regolarmente chiuso restava trattenuto PER SEMPRE, e il verbo «Riporta da emettere» smetteva di avere effetto senza che niente lo segnalasse.
> ⛔ E NON si deriva da `chiude_lotto`: quel flag marca la TRANSIZIONE che chiude (solo DEFINITIVA), non la proprieta' di essere chiuso — il catalogo ammette DEFINITIVA -&gt; INVIATA, e INVIATA non lo porta.
> ⭐ FAIL-CLOSED CONSERVATO: un lotto il cui stato non si risolve TRATTIENE. Sta dentro `in_gioco`, che ripiega su TRUE proprio per questa vista — il gemello `pre_fiscale` ripiega su FALSE e serve alla porta d'uscita. Stesso asse, prudenza girata: usare qui `pre_fiscale` capovolgerebbe il caso.
> ⛔ UN DOCUMENTO USCITO DAL GIRO NON TRATTIENE NIENTE: l'esito ESCLUSO e' escluso. E' la regola «un documento fuori dal giro non si marca, non si conta, non blocca», vista dal terzo lato.
> ⚠️ IL LEGAME DI COMPETENZA NON E' QUI: la vista non conosce la competenza della riga che la interroga, espone `lotto_competenza_mese` e chi aggancia deve legarlo con `lotto_competenza_mese &gt;= competenza della riga`, perche' la selezione e' CUMULATIVA (un lotto di settembre lavora anche agosto, non ottobre). ⛔ NON e' un'uguaglianza: copiarla dal LATERAL dell'esito, che invece lega =, darebbe un blocco piu' stretto della regola.
> ⚠️ PUO' TORNARE PIU' DI UNA RIGA per la stessa gruppo_key: e' esattamente il difetto che questa vista serve a chiudere (lo stesso documento in due lotti in gioco). Chi ne vuole UNO deve ordinare — un LIMIT 1 senza ORDER BY scommette.
> ⚠️ PERCHE' NON BASTAVA CIO' CHE C'ERA: script.fn_get_stato_push_segment sa dire LIBERA / ALLOCATA / EMESSA, cioe' misura l'ESITO del lavoro, non il fatto che il lavoro sia IN CORSO. Manca la terza domanda — «e' dentro un giro che non ha ancora finito?» — ed e' questa vista. Per la stessa ragione le cinque fn_list_*_da_pushare NON si toccano: la regola loro (LIBERA) c'e' gia'.
> Brief: brief-db-il-trattenuto-passa-lo-stesso.md (L2).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_documenti_trattenuti_da_lotto
WITH (security_invoker=true) AS
SELECT le.gruppo_key,
    f.lotto_id,
    f.lotto_codice,
    f.lotto_competenza_mese,
    f.stato_codice_interno AS lotto_stato,
    le.stato_esecuzione AS esito
   FROM (vendite.fatturazione_lotti_esiti le
     JOIN vendite.vw_lotti_fase f ON ((f.lotto_id = le.lotto_id)))
  WHERE ((le.stato_esecuzione <> 'ESCLUSO'::text) AND f.in_gioco);
```

</div>


---
{% include-markdown "signature-core.md" %}
