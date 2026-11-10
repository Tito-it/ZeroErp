{% include-markdown "it/dbzero/dbops/manual/vw_af_senza_giro.md" %}
# 🔍 View `vw_af_senza_giro`

> 📝 **Descrizione**
>
> Attivita' fatturabili libere (non fatturate, non in fatturazione: lock_in_fatturazione falso o NULL) che nessun giro ha marchiato (emit_batch_id NULL), con l'emittente del billing account. E' la controparte del marchio del giro: senza, un'attivita' che un giro salta diventa una fattura che non nasce, e nessuno se ne accorge; questa vista la rende visibile. Lista di lavoro (natura LAVORAZIONE in dbops.presidi, cadenza settimanale): il pregresso non si esclude, perche' quelle righe sono la popolazione del difetto, e cala da solo quando il pull ri-adotta le righe e ci scrive il proprio giro. Non elenca il lavoro mai entrato in fatturazione (una commessa che nessun giro ha pullato non ha righe qui): quella domanda ha la sua superficie nella lane. security_invoker; il digest conta da proprietario (dbops.fn_conta_presidio, perimetro DEFINER).

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
