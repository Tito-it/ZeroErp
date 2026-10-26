{% include-markdown "it/dbzero/pagamenti/manual/vw_saldi_rate.md" %}
# 🔍 View `vw_saldi_rate`

> 📝 **Descrizione**
>
> La PORTA 2 del nucleo pagamenti.fn_get_saldi_rate: il saldo di TUTTE le rate visibili in un passaggio (saldo · in_lavorazione · incassato · has_movimenti per scadenza_id) — il nucleo chiamato con ARRAY(SELECT id FROM vendite.fatture_scadenze), sotto RLS, perche' nel nucleo l'array e' obbligatorio (niente «NULL = tutte»: la ragione sta nel COMMENT del nucleo). E' la forma dello scadenzario — «solo aperte» e' `WHERE saldo &lt;&gt; 0` su un JOIN a vendite.vw_fatture_scadenze_lista — e non e' una seconda formula: e' il nucleo su tutte le rate. ⛔ Non e' la porta del picker sulla pagina: la' si chiama il nucleo con l'array degli id della pagina, che scende negli indici; questa aggrega tutto, ed e' il costo onesto dello scadenzario. ⚠️ security_invoker=on, da RI-SPECIFICARE a ogni CREATE OR REPLACE: il nucleo legge tre tabelle con policy. Nasce il 2026-09-17 (brief-db-distinta-ricerca-rate §4-bis.4, P-3).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW pagamenti.vw_saldi_rate
WITH (security_invoker=on) AS
SELECT scadenza_id,
    saldo,
    in_lavorazione,
    incassato,
    has_movimenti
   FROM pagamenti.fn_get_saldi_rate(ARRAY( SELECT s.id
           FROM vendite.fatture_scadenze s), NULL::bigint) r(scadenza_id, saldo, in_lavorazione, incassato, has_movimenti);
```

</div>


---
{% include-markdown "signature-core.md" %}
