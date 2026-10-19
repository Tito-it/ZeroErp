{% include-markdown "it/dbzero/documenti/manual/vw_template_personalizzati_scarto.md" %}
# 🔍 View `vw_template_personalizzati_scarto`

> 📝 **Descrizione**
>
> Per ogni modello d'emittente attivo con una versione pubblicata, che ha uno standard predefinito attivo della stessa coppia (tipo, sorgente): quanto la sua versione in uso (la PUBBLICATA piu' alta) e' rimasta indietro rispetto all'ultima versione standard pubblicata. stato: CONTESTO_SUPERATO (legge una forma dei dati piu' vecchia di quella dello standard, che i changeSet tengono al passo col builder: si rompera' alla stampa), ORIGINE_NON_DICHIARATA (nessuna versione dichiara derivata_da_versione_id), ALLINEATA, STANDARD_AVANTI. L'origine si eredita dalla versione piu' recente che la dichiara. La legge la lista Modelli documento per il badge. Brief: brief-db-modelli-documento-standard §4.1 Q-5.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

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
    s.id AS standard_template_documento_id,
    sv.id AS standard_versione_id,
    sv.versione AS standard_versione,
    sv.versione_contesto AS standard_versione_contesto,
        CASE
            WHEN (cv.versione_contesto < sv.versione_contesto) THEN 'CONTESTO_SUPERATO'::text
            WHEN (orig.derivata_da_versione_id IS NULL) THEN 'ORIGINE_NON_DICHIARATA'::text
            WHEN (orig.derivata_da_versione_id = sv.id) THEN 'ALLINEATA'::text
            ELSE 'STANDARD_AVANTI'::text
        END AS stato
   FROM (((((documenti.template_documenti c
     JOIN LATERAL ( SELECT v.id,
            v.versione,
            v.versione_contesto
           FROM documenti.template_documenti_versioni v
          WHERE ((v.template_documento_id = c.id) AND ((v.stato)::text = 'PUBBLICATA'::text))
          ORDER BY v.versione DESC
         LIMIT 1) cv ON (true))
     JOIN documenti.template_documenti s ON ((s.standard AND s.attivo AND s.is_default AND (s.tipo_documento_output_id = c.tipo_documento_output_id) AND (s.sorgente_tipo_id = c.sorgente_tipo_id))))
     JOIN LATERAL ( SELECT v.id,
            v.versione,
            v.versione_contesto
           FROM documenti.template_documenti_versioni v
          WHERE ((v.template_documento_id = s.id) AND ((v.stato)::text = 'PUBBLICATA'::text))
          ORDER BY v.versione DESC
         LIMIT 1) sv ON (true))
     LEFT JOIN LATERAL ( SELECT v.derivata_da_versione_id
           FROM documenti.template_documenti_versioni v
          WHERE ((v.template_documento_id = c.id) AND (v.versione <= cv.versione) AND (v.derivata_da_versione_id IS NOT NULL))
          ORDER BY v.versione DESC
         LIMIT 1) orig ON (true))
     LEFT JOIN documenti.template_documenti_versioni ov ON ((ov.id = orig.derivata_da_versione_id)))
  WHERE ((NOT c.standard) AND c.attivo);
```


---
{% include-markdown "signature-core.md" %}
