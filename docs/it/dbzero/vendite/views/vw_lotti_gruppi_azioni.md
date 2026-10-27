{% include-markdown "it/dbzero/vendite/manual/vw_lotti_gruppi_azioni.md" %}
# 🔍 View `vw_lotti_gruppi_azioni`

> 📝 **Descrizione**
>
> Le AZIONI DI RIGA dei documenti di un lotto di fatturazione (Q-F5): una riga per (lotto_id, gruppo_key), sui documenti del lotto = perimetro dichiarato (fatturazione_lotti_gruppi) UNITO agli esiti (fatturazione_lotti_esiti). uscita_blocco_reason / uscita_blocco_reason_key: il PRIMO motivo di script.fn_check_documento_escludibile_da_giro (la stessa fn_check che vendite.fn_escludi_documento_da_giro chiama per rifiutare; NULL = si puo' togliere). n_trascinati: quanti documenti vengono via insieme (script.fn_gruppi_trascinati_da_uscita), solo dove l'azione e' viva. E' la superficie dell'azione ESCLUDI_DOCUMENTO_DA_GIRO nel registro config.azioni_riga. security_invoker: i soli lotti del proprio perimetro. Si filtra per lotto_id. Prima la composizione stava nel repository del backend. Brief: brief-modello-documento-vendita §15.10 (Q-F5 = vista DB, Tid 2026-10-27).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_lotti_gruppi_azioni
WITH (security_invoker=true) AS
WITH documenti AS (
         SELECT lg.lotto_id,
            lg.gruppo_key
           FROM vendite.fatturazione_lotti_gruppi lg
        UNION
         SELECT le.lotto_id,
            le.gruppo_key
           FROM vendite.fatturazione_lotti_esiti le
        )
 SELECT d.lotto_id,
    d.gruppo_key,
    ((chk.motivi -> 0) ->> 'reason'::text) AS uscita_blocco_reason,
    ((chk.motivi -> 0) ->> 'reason_key'::text) AS uscita_blocco_reason_key,
        CASE
            WHEN (jsonb_array_length(chk.motivi) = 0) THEN jsonb_array_length(script.fn_gruppi_trascinati_da_uscita(d.lotto_id, d.gruppo_key))
            ELSE NULL::integer
        END AS n_trascinati
   FROM (documenti d
     CROSS JOIN LATERAL ( SELECT script.fn_check_documento_escludibile_da_giro(d.lotto_id, d.gruppo_key) AS motivi) chk);
```

</div>


---
{% include-markdown "signature-core.md" %}
