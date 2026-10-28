{% include-markdown "it/dbzero/vendite/manual/vw_segnalazioni_con_documento_ignoto.md" %}
# 🔍 View `vw_segnalazioni_con_documento_ignoto`

> 📝 **Descrizione**
>
> PRESIDIO. Le segnalazioni VIVE che nominano un documento che il loro lotto non ha fra gli esiti. ⛔ INVARIANTE: deve restare VUOTA. Una riga qui e' un difetto vero e con una conseguenza precisa: quella segnalazione non si potra' MAI zittire togliendo il documento dal giro — non c'e' niente da togliere — quindi resta a bloccare il lotto per sempre, e nel frattempo l'operatore legge nella colonna «Documento» il nome di una cosa che nell'elenco non c'e'. Dice che CHI SCRIVE la segnalazione ha dichiarato un proprietario sbagliato (contratto §6 del brief). ⚠️ gruppo_key NULL NON entra: vuol dire «la segnalazione e' del GIRO», che e' legittimo e non ha un documento. ⚠️ Solo le vive: una ritirata non blocca e non si legge. ⭐ Oggi e' vuota per ASSENZA DI DATO (nessuno valorizza ancora gruppo_key), non per teorema — e la differenza conta, perche' diventa raggiungibile il giorno in cui il backend comincia a dichiarare il proprietario. 🔴 Sostituisce il presidio promesso nel brief («lotti fermi con tutte le critiche di documenti usciti»), che era VACUO: se tutte le critiche sono di documenti usciti il conteggio risponde zero e il lotto non e' fermo. Un presidio che non puo' accendersi e' rumore. Brief: brief-db-uscita-documento-dal-giro §5.6.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_segnalazioni_con_documento_ignoto
WITH (security_invoker=true) AS
SELECT ll.id AS segnalazione_id,
    ll.lotto_id,
    fl.codice AS lotto_codice,
    ll.gruppo_key,
    ll.status AS livello,
    ll.data_ora,
    ll.messaggio
   FROM (vendite.fatturazione_lotti_log ll
     JOIN vendite.fatturazione_lotti fl ON ((fl.id = ll.lotto_id)))
  WHERE ((ll.disabilitato IS FALSE) AND (ll.gruppo_key IS NOT NULL) AND (NOT (EXISTS ( SELECT 1
           FROM vendite.fatturazione_lotti_esiti e
          WHERE ((e.lotto_id = ll.lotto_id) AND (e.gruppo_key = ll.gruppo_key))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
