{% include-markdown "it/dbzero/vendite/manual/vw_famiglie_documento_lista.md" %}
# 🔍 View `vw_famiglie_documento_lista`

> 📝 **Descrizione**
>
> Superficie di lettura del catalogo delle famiglie di documento: le colonne di catalogo, i due conteggi dei registri e i due blocchi capability presi dalle check. ⛔ ESISTE PERCHE' IL LOOKUP GENERICO NON BASTA: dbops.fn_get_lookup_codici torna id, codice, codice_interno, descrizione e attivo, e non puo' portare i default della forma ne' le colonne di natura — non e' un suo difetto, e' generico e va lasciato generico. ⭐ TRE LETTORI, UNA SEDE: la lista del CRUD delle famiglie (dove e' anche la `vista_sql` dichiarata a catalogo, cosi' il database valida ogni campo_sorgente contro le colonne vere), il suo export CSV/XLSX che legge le stesse righe con le stesse chiavi, e il drawer dei REGISTRI, che da qui prende prefisso_default e lunghezza_default per precompilare la forma alla creazione e presidia_data_documento / colonna_serie per decidere quali campi mostrare. ⛔ Quest'ultimo e' cio' che toglie i due letterali 'FATTURA' paralleli da backend e frontend: presidia_data_documento e' ammette_regole_fiscali SONO le colonne che rispondono a quelle domande — la prima al pavimento di sequenza, la seconda ai campi fiscali del registro: due domande diverse con la stessa risposta di oggi, tenute distinte apposta. ⚠️ IL NOME DELLE COLONNE E' IL CONTRATTO: &lt;ListaConfigurabile&gt; legge data[campo_sorgente] e il renderer di export fa lo stesso, quindi un rename qui rompe le celle e il file esportato insieme, e in silenzio. ⭐ I due conteggi sono DATO: n_registri e' il predicato che rende immutabile la struttura, n_registri_attivi quello che blocca lo spegnimento — mostrarli fa capire il rifiuto prima di provarlo. ⛔ DUE BLOCCHI CAPABILITY, DUE NOMI: rimozione_* risponde a «posso spegnerla?», struttura_* a «posso cambiarle le colonne?»; su una famiglia con registri sono spenti entrambi per motivi diversi, e riusare uno per l'altra domanda mostrerebbe la frase sbagliata senza che niente fallisca. ⚠️ LEFT JOIN LATERAL ... ON TRUE e non CROSS JOIN: la check risponde [] quando l'azione e' ammessa, e con un CROSS JOIN sparirebbero dalla lista proprio le famiglie senza problemi. ⚠️ security_invoker=on e' scritto nel changeSet perche' si AZZERA a ogni CREATE OR REPLACE VIEW: una revisione che non lo ripete trasforma la vista in un bypass della RLS, in silenzio. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.8 (DB-6). Rev 2026-10-20 (20261020-46, brief-db-grammatica-unica-documenti 2c, G-5): codice_interno e' il codice della sorgente; schema_tabella, nome_tabella e tabella_documento restano (il nome delle colonne e' il contratto) ma vengono dalla target_table della sorgente (config.fn_sorgente_tabella): le due colonne della tabella sono ritirate. Rev 2026-10-21 (20261021-18/-19, brief-db-grammatica-unica-documenti, G-3): tolta e rimessa identica perche' famiglie_documento.codice passa a varchar(50); la colonna `codice` della vista segue.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_famiglie_documento_lista
WITH (security_invoker=true) AS
SELECT f.id,
    f.codice_interno,
    f.descrizione,
    (t.schema_tabella)::text AS schema_tabella,
    (t.nome_tabella)::text AS nome_tabella,
    f.colonna_numero,
    f.colonna_serie,
    f.colonna_billing_account,
    (((t.schema_tabella)::text || '.'::text) || (t.nome_tabella)::text) AS tabella_documento,
    f.presidia_data_documento,
    (f.colonna_serie IS NOT NULL) AS gestisce_serie,
    f.ammette_regole_fiscali,
    f.prefisso_default,
    f.lunghezza_default,
    r.n_registri,
    r.n_registri_attivi,
    f.attivo,
    f.meta,
    f.data_insert,
    f.data_update,
    disattiva.reason AS rimozione_blocco_reason,
    disattiva.reason_key AS rimozione_blocco_reason_key,
    disattiva.dettaglio AS rimozione_blocco_dettaglio,
    (disattiva.reason IS NULL) AS can_disattivare,
    struttura.reason AS struttura_blocco_reason,
    struttura.reason_key AS struttura_blocco_reason_key,
    struttura.dettaglio AS struttura_blocco_dettaglio,
    (struttura.reason IS NULL) AS can_modificare_struttura,
    f.codice
   FROM ((((vendite.famiglie_documento f
     LEFT JOIN LATERAL config.fn_sorgente_tabella(f.codice_interno) t(schema_tabella, nome_tabella, relid) ON (true))
     LEFT JOIN LATERAL ( SELECT count(*) AS n_registri,
            count(*) FILTER (WHERE rr.attivo) AS n_registri_attivi
           FROM vendite.registri_fatturazione rr
          WHERE ((rr.famiglia_documento)::text = (f.codice_interno)::text)) r ON (true))
     LEFT JOIN LATERAL ( SELECT (m.value ->> 'reason'::text) AS reason,
            (m.value ->> 'reason_key'::text) AS reason_key,
            (m.value -> 'dettaglio'::text) AS dettaglio
           FROM jsonb_array_elements(script.fn_check_famiglia_documento_disattivabile(f.id)) WITH ORDINALITY m(value, ord)
          ORDER BY m.ord
         LIMIT 1) disattiva ON (true))
     LEFT JOIN LATERAL ( SELECT (m.value ->> 'reason'::text) AS reason,
            (m.value ->> 'reason_key'::text) AS reason_key,
            (m.value -> 'dettaglio'::text) AS dettaglio
           FROM jsonb_array_elements(script.fn_check_famiglia_documento_struttura_modificabile(f.id)) WITH ORDINALITY m(value, ord)
          ORDER BY m.ord
         LIMIT 1) struttura ON (true));
```

</div>


---
{% include-markdown "signature-core.md" %}
