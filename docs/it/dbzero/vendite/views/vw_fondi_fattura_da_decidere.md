{% include-markdown "it/dbzero/vendite/manual/vw_fondi_fattura_da_decidere.md" %}
# 🔍 View `vw_fondi_fattura_da_decidere`

> 📝 **Descrizione**
>
> I casi di fondo fattura che chiedono una PERSONA. Quattro motivi, vocabolario chiuso per costruzione (letterali nei rami della UNION, nessun dato li produce): PROPOSTA_SENZA_ATTO = la fattura merita un fondo e non ce l'ha; UTILITY_NON_ATTRIBUIBILE = e' nella banda ma senza utility_id, quindi irraggiungibile da qualunque giro (il filtro e' `=` e NULL non e' uguale a niente); IMPORTO_NON_CORRISPONDENTE = il residuo esiste ma non assomiglia al documento (segno diverso dal totale o piu' grande in valore assoluto) e l'automatismo tace; NON_PIU_CAPIENTE = l'atto esiste ma la sorgente non lo regge piu', e il giro lo scarta a ogni corsa. ⭐ LA VISTA PRESENTA, NON SANA: nessuna di queste righe ha un gemello automatico che la corregge da solo — sanarle significherebbe muovere denaro senza che nessuno l'abbia deciso. ⭐ Non riscrive nessuna regola: la proposta la da' fn_fondo_fattura_proponibile (la stessa che usa fn_genera_fondi_fattura_source) e la capienza fn_check_fondo_fattura_capiente (la stessa che usa fn_applica_fondi_fattura), cosi' l'elenco non puo' raccontare una cosa diversa da quello che il giro notturno fa. 🔴 CONFIGURAZIONE_INCOMPLETA, quinto motivo previsto dal piano, NON esiste: dopo il CHECK chk_emittenti_fiscali_utilities_soglie_coppia (D-0, 2026-08-15) una configurazione a meta' non e' piu' salvabile, e una riga di elenco che non puo' accadere insegna una cosa falsa. ⚠️ security_invoker=on: da ri-specificare a ogni CREATE OR REPLACE, non e' visibile in pg_get_viewdef. ⚠️ E il ramo NON_PIU_CAPIENTE parte da fatture_fondi_fattura_source, che NON ha RLS: e' protetto dal JOIN INNER con vendite.fatture, non da un filtro proprio — trasformarlo in LEFT JOIN aprirebbe l'elenco a tutti gli emittenti. ⚠️ Il pre-filtro DEFINITIVA + minimo e' un pezzo di inviluppo scritto in un secondo posto: e' obbligatorio (la vista non ha scope e la proposta e' VOLATILE) e restringe, non decide. Le etichette dei motivi le mette il frontend con labelOrCode. D-10 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_fondi_fattura_da_decidere
WITH (security_invoker=on) AS
WITH tipo AS (
         SELECT t.id AS tipo_fondo_fattura_id,
            t.codice_interno AS tipo_fondo_codice_interno
           FROM vendite.tipi_fondi_fattura t
          WHERE (((t.codice_interno)::text = 'F_F_ADD_ACC'::text) AND (t.attivo IS TRUE))
        ), candidate AS (
         SELECT f.id AS fattura_sorgente_id,
            f.anno,
            f.serie,
            f.numero,
            f.data,
            f.totale_a_pagare,
            f.billing_account_id,
            f.utility_id,
            f.tipo_doc_fiscale_id,
            f.emittente_soggetto_ruolo_id,
            f.valuta_id
           FROM (vendite.fatture f
             JOIN config.stati_doc_fiscale sd ON (((sd.id = f.stato_doc_fiscale_id) AND ((sd.codice_interno)::text = 'DEFINITIVA'::text))))
          WHERE ((f.minimo IS TRUE) AND (f.totale_a_pagare IS NOT NULL))
        ), senza_atto AS (
         SELECT c.fattura_sorgente_id,
            c.anno,
            c.serie,
            c.numero,
            c.data,
            c.totale_a_pagare,
            c.billing_account_id,
            c.utility_id,
            c.tipo_doc_fiscale_id,
            c.emittente_soggetto_ruolo_id,
            c.valuta_id,
            t.tipo_fondo_fattura_id,
            t.tipo_fondo_codice_interno
           FROM (candidate c
             CROSS JOIN tipo t)
          WHERE (NOT (EXISTS ( SELECT 1
                   FROM vendite.fatture_fondi_fattura_source s
                  WHERE ((s.fattura_sorgente_id = c.fattura_sorgente_id) AND (s.tipo_fondo_fattura_id = t.tipo_fondo_fattura_id)))))
        )
 SELECT
        CASE
            WHEN (x.proposta IS NOT NULL) THEN 'PROPOSTA_SENZA_ATTO'::text
            ELSE 'IMPORTO_NON_CORRISPONDENTE'::text
        END AS motivo,
    sa.fattura_sorgente_id,
    sa.anno,
    sa.serie,
    sa.numero,
    sa.data,
    sa.totale_a_pagare,
    sa.billing_account_id,
    sa.utility_id,
    sa.tipo_doc_fiscale_id,
    sa.emittente_soggetto_ruolo_id,
    sa.valuta_id,
    sa.tipo_fondo_fattura_id,
    sa.tipo_fondo_codice_interno,
    NULL::bigint AS fondo_source_id,
    NULL::character varying AS origine,
    NULL::character varying AS stato_atto,
    NULL::numeric AS importo_atto,
    NULL::text AS atto_motivo,
    NULL::timestamp with time zone AS atto_data,
    x.proposta AS importo_proposto,
    x.capienza AS capienza_attuale
   FROM (senza_atto sa
     CROSS JOIN LATERAL ( SELECT vendite.fn_fondo_fattura_proponibile(sa.fattura_sorgente_id, sa.tipo_fondo_fattura_id) AS proposta,
            vendite.fn_saldo_sorgente_fondo(sa.fattura_sorgente_id, NULL::bigint) AS capienza) x)
  WHERE ((sa.utility_id IS NOT NULL) AND ((x.proposta IS NOT NULL) OR (x.capienza <> (0)::numeric)))
UNION ALL
 SELECT 'NON_PIU_CAPIENTE'::text AS motivo,
    f.id AS fattura_sorgente_id,
    f.anno,
    f.serie,
    f.numero,
    f.data,
    f.totale_a_pagare,
    f.billing_account_id,
    f.utility_id,
    f.tipo_doc_fiscale_id,
    f.emittente_soggetto_ruolo_id,
    f.valuta_id,
    s.tipo_fondo_fattura_id,
    tf.codice_interno AS tipo_fondo_codice_interno,
    s.id AS fondo_source_id,
    s.origine,
    s.stato AS stato_atto,
    s.importo AS importo_atto,
    s.motivo AS atto_motivo,
    s.data_insert AS atto_data,
    NULL::numeric AS importo_proposto,
    x.capienza AS capienza_attuale
   FROM (((vendite.fatture_fondi_fattura_source s
     JOIN vendite.fatture f ON ((f.id = s.fattura_sorgente_id)))
     JOIN vendite.tipi_fondi_fattura tf ON ((tf.id = s.tipo_fondo_fattura_id)))
     CROSS JOIN LATERAL ( SELECT vendite.fn_saldo_sorgente_fondo(s.fattura_sorgente_id, s.id) AS capienza) x)
  WHERE (((s.stato)::text = 'DISPONIBILE'::text) AND (s.attivo IS TRUE) AND (NOT vendite.fn_check_fondo_fattura_capiente(x.capienza, s.importo)))
UNION ALL
 SELECT 'UTILITY_NON_ATTRIBUIBILE'::text AS motivo,
    sa.fattura_sorgente_id,
    sa.anno,
    sa.serie,
    sa.numero,
    sa.data,
    sa.totale_a_pagare,
    sa.billing_account_id,
    sa.utility_id,
    sa.tipo_doc_fiscale_id,
    sa.emittente_soggetto_ruolo_id,
    sa.valuta_id,
    sa.tipo_fondo_fattura_id,
    sa.tipo_fondo_codice_interno,
    NULL::bigint AS fondo_source_id,
    NULL::character varying AS origine,
    NULL::character varying AS stato_atto,
    NULL::numeric AS importo_atto,
    NULL::text AS atto_motivo,
    NULL::timestamp with time zone AS atto_data,
    NULL::numeric AS importo_proposto,
    x.capienza AS capienza_attuale
   FROM (senza_atto sa
     CROSS JOIN LATERAL ( SELECT vendite.fn_saldo_sorgente_fondo(sa.fattura_sorgente_id, NULL::bigint) AS capienza) x)
  WHERE ((sa.utility_id IS NULL) AND (x.capienza <> (0)::numeric));
```

</div>


---
{% include-markdown "signature-core.md" %}
