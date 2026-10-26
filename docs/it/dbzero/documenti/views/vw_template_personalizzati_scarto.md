{% include-markdown "it/dbzero/documenti/manual/vw_template_personalizzati_scarto.md" %}
# 🔍 View `vw_template_personalizzati_scarto`

> 📝 **Descrizione**
>
> Per ogni modello d'emittente attivo che stampa oggi: quanto la versione con cui stampa e' rimasta indietro rispetto allo standard di riferimento, cioe' quello da cui la copia deriva (derivata_da_versione_id) o, senza origine dichiarata, il predefinito standard della coppia (tipo, sorgente), sulla versione con cui quello standard stampa oggi. Le versioni sono quelle di documenti.vw_template_versioni_stampabili, la stessa definizione da cui parte fn_personalizza_template_standard (rev 2026-10-21, 20261021-12, brief-db-modelli-documento-standard §10.3 K-10, D-9). stato: CONTESTO_SUPERATO (legge una forma dei dati piu' vecchia di quella dello standard, che i changeSet tengono al passo col builder: si rompera' alla stampa), ORIGINE_NON_DICHIARATA (nessuna versione dichiara derivata_da_versione_id), ALLINEATA, STANDARD_AVANTI. L'origine si eredita dalla versione piu' recente che la dichiara. La legge la lista Modelli documento. Brief: brief-db-modelli-documento-standard §4.1 Q-5.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW documenti.vw_template_personalizzati_scarto
WITH (security_invoker=true) AS
SELECT c.id AS template_documento_id,
    c.emittente_fiscale_id,
    c.tipo_documento_output_id,
    c.sorgente_tipo_id,
    c.codice,
    c.is_default,
    cv.id AS versione_id,
    cv.versione,
    cv.versione_contesto,
    orig.derivata_da_versione_id,
    ov.versione AS standard_versione_origine,
    rif.template_documento_id AS standard_template_documento_id,
    sv.id AS standard_versione_id,
    sv.versione AS standard_versione,
    sv.versione_contesto AS standard_versione_contesto,
        CASE
            WHEN (cv.versione_contesto < sv.versione_contesto) THEN 'CONTESTO_SUPERATO'::text
            WHEN (orig.derivata_da_versione_id IS NULL) THEN 'ORIGINE_NON_DICHIARATA'::text
            WHEN (orig.derivata_da_versione_id = sv.id) THEN 'ALLINEATA'::text
            ELSE 'STANDARD_AVANTI'::text
        END AS stato
   FROM ((((((documenti.template_documenti c
     JOIN documenti.vw_template_versioni_stampabili cs ON ((cs.template_documento_id = c.id)))
     JOIN documenti.template_documenti_versioni cv ON ((cv.id = cs.template_versione_id)))
     LEFT JOIN LATERAL ( SELECT v.derivata_da_versione_id
           FROM documenti.template_documenti_versioni v
          WHERE ((v.template_documento_id = c.id) AND (v.versione <= cv.versione) AND (v.derivata_da_versione_id IS NOT NULL))
          ORDER BY v.versione DESC
         LIMIT 1) orig ON (true))
     LEFT JOIN documenti.template_documenti_versioni ov ON ((ov.id = orig.derivata_da_versione_id)))
     JOIN documenti.vw_template_versioni_stampabili rif ON ((rif.standard AND (rif.template_documento_id = COALESCE(ov.template_documento_id, ( SELECT d.id
           FROM documenti.template_documenti d
          WHERE (d.standard AND d.attivo AND d.is_default AND (d.tipo_documento_output_id = c.tipo_documento_output_id) AND (d.sorgente_tipo_id = c.sorgente_tipo_id))))))))
     JOIN documenti.template_documenti_versioni sv ON ((sv.id = rif.template_versione_id)))
  WHERE ((NOT c.standard) AND c.attivo);
```

</div>


---
{% include-markdown "signature-core.md" %}
