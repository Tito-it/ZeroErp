{% include-markdown "it/dbzero/dbops/manual/vw_af_senza_giro.md" %}
# 🔍 View `vw_af_senza_giro`

> 📝 **Descrizione**
>
> Attivita' fatturabili libere e non fatturate che NESSUN GIRO ha marchiato (emit_batch_id NULL). ⭐ Deve restare vuota, ed e' la controparte obbligatoria del marchio introdotto dal 20260904-31: il rimedio a D1 trasforma un danno RUMOROSO (una fattura di troppo, che si vede) in uno MUTO (una fattura che non nasce, e nessuno se ne accorge) — questa vista e' cio' che lo rende di nuovo visibile. ⭐ Nasce PIENA: e' il registro del debito, e cala da sola perche' il pull ri-adotta le righe esistenti e ci scrive sopra il proprio giro. ⛔ Non si esclude il pregresso per farla partire verde: quelle righe sono esattamente la popolazione del difetto. ⚠️ NON elenca il lavoro mai entrato in fatturazione (una commessa che nessun giro ha pullato non ha righe qui): quella domanda ha gia' la sua superficie nella lane. Piano: brief-residuo-fatturabili-e-bandiere-esito-parziale, sezione 9.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_af_senza_giro
WITH (security_invoker=true) AS
SELECT id AS attivita_fatturabile_id,
    commessa_id,
    commessa_attivita_id,
    competenza_mese,
    data_attivita,
    billing_account_id,
    anagrafiche.fn_get_emittente_fiscale_id(billing_account_id) AS emittente_soggetto_ruolo_id,
    tipo_doc_fiscale_id,
    tipo_movimento,
    data_insert
   FROM vendite.attivita_fatturabili a
  WHERE ((emit_batch_id IS NULL) AND (fatturato IS FALSE) AND (COALESCE(lock_in_fatturazione, false) IS FALSE));
```

</div>


---
{% include-markdown "signature-core.md" %}
