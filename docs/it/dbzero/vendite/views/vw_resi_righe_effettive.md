{% include-markdown "it/dbzero/vendite/manual/vw_resi_righe_effettive.md" %}
# 🔍 View `vw_resi_righe_effettive`

> 📝 **Descrizione**
>
> Helper unico «merce tornata indietro» (brief-db-fatturazione-ddt-resi §3b, step 2): righe reso EFFETTIVE = reso in uno stato in cui la merce e' rientrata (script.vw_stati_doc_reso_merce_rientrata: oltre la bozza, non abortito) + resi_righe.attivo, tutti i tipi. Espone le due chiavi di partita (ordine_riga_id nullable / ddt_riga_id) + riapre_residuo, cosi' ogni consumatore applica il proprio filtro-tipo SOPRA. quantita = base. Fonte unica per fn_ordine_riga_qta_riconsegna, flip a RESO e contatore tenuti-fatturati. NON copre il guard over-return (trgfn_resi_righe_guard_quantita), che conta anche le bozze di proposito (prenotazione). security_invoker=on + RLS su resi. rev 2026-07-17; rev 2026-11-09 (brief-db-sorgente-documento-e-riga lotto M, D29): lo stato dal BB, non dal letterale CONFERMATO.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_righe_effettive
WITH (security_invoker=on) AS
SELECT rr.id AS resi_riga_id,
    rr.reso_id,
    rr.ddt_riga_id,
    rr.ordine_riga_id,
    rr.tipo_reso_id,
    tr.riapre_residuo,
    rr.quantita
   FROM (((vendite.resi_righe rr
     JOIN vendite.resi r ON ((r.id = rr.reso_id)))
     JOIN script.vw_stati_doc_reso_merce_rientrata sr ON ((sr.id = r.stato_doc_reso_id)))
     JOIN config.tipi_reso tr ON ((tr.id = rr.tipo_reso_id)))
  WHERE (sr.merce_rientrata AND (rr.attivo IS TRUE));
```

</div>


---
{% include-markdown "signature-core.md" %}
