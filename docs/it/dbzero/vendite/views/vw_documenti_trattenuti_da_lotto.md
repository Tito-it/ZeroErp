# 🔍 View `vw_documenti_trattenuti_da_lotto`

> 📝 **Descrizione**
>
> Sede unica della domanda «questo documento e' trattenuto da un lotto ancora in gioco?». Una riga per (documento, lotto che lo trattiene): la gruppo_key e il lotto, col suo stato e la sua competenza. Consumatori: la riga di vendite.vw_dash_competenza_gruppi (il motivo a video), il conteggio della card, vendite.fn_list_emittibili_lane e il pull, perche' un secondo giro non se lo prenda. «In gioco» si legge da vendite.vw_lotti_fase (pre_fiscale: il lotto non ha congelato i documenti), mai da un elenco di stati, da is_abortito o da chiude_lotto: un lotto DEFINITIVA non e' annullato ma e' chiuso, e non trattiene. Un documento uscito dal giro (esito ESCLUSO) non trattiene niente. Il legame di competenza non e' qui: la vista espone lotto_competenza_mese, e chi aggancia lega lotto_competenza_mese &gt;= la competenza della riga, perche' la selezione e' cumulativa (un lotto di settembre lavora anche agosto, non ottobre): non un'uguaglianza. Puo' tornare piu' di una riga per la stessa gruppo_key (lo stesso documento in due lotti in gioco): chi ne vuole una ordina. script.fn_get_stato_push_segment misura l'esito del lavoro (LIBERA, ALLOCATA, EMESSA), non il fatto che il lavoro sia in corso: e' la domanda di questa vista.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

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
  WHERE ((le.stato_esecuzione <> 'ESCLUSO'::text) AND f.pre_fiscale);
```

</div>


---
{% include-markdown "signature-core.md" %}
