{% include-markdown "it/dbzero/pagamenti/manual/vw_rate_fuori_capienza.md" %}
# 🔍 View `vw_rate_fuori_capienza`

> 📝 **Descrizione**
>
> Le rate il cui residuo e' uscito dalla banda: l'elenco senza il quale la forzatura sarebbe un modo di NASCONDERE denaro invece di registrarlo (brief madre §5). ⭐ DUE motivi e non uno: SOVRA_INCASSATA (il residuo ha ATTRAVERSATO lo zero — e' entrato piu' del dovuto; su una nota di credito: rimborsato piu' del credito) e MOVIMENTO_CONTRARIO (il residuo SUPERA l'importo della rata in valore assoluto — e' uscito denaro dove non era entrato; su una nota di credito: e' entrato denaro invece di uscire). Il secondo e' il caso che ha fatto cadere l'asimmetria di D1-bis, ed e' il motivo per cui la vista NON si chiama «sovra incassate». ⭐ rev 2026-09-18 (P-7, brief-db-distinta-ricerca-rate §4-bis.9): + natura_doc_codice_interno e natura_doc_descrizione in coda, JOIN interno su config.nature_doc_fiscale (NOT NULL + FK: nessuna riga in meno) — la sfumatura dei due motivi sulla nota di credito e' affidata all'etichetta del frontend, che senza la natura del documento non poteva dirla. ⭐ rev 2026-09-17 (brief-db-distinta-ricerca-rate §4-bis.6, P-5): la banda NON e' piu' [0, importo] — era la trappola del §5 del brief madre, sciolta sul guard da D14-c e non qui — ma la forma di D14-c: segno e valore assoluto, senza estremi da invertire, giusta anche sulla rata NEGATIVA della nota di credito. Sulle rate positive e' identica a prima. Il vocabolario resta a due valori: la sfumatura la dice l'etichetta. ⭐ Stessa rev: i CANDIDATI includono le rate di un documento con movimenti SENZA rata (dal 20260917-10 il nucleo dei saldi li imputa alle rate, e una rata puo' uscire dalla banda senza che nessun movimento la nomini); il saldo arriva dal nucleo pagamenti.fn_get_saldi_rate in UNA chiamata sull'insieme dei candidati e non piu' in LATERAL per rata; + numero_documento in coda dalla sede unica vendite.fn_numero_documento_fattura (la lista ui 52 mostrava il contatore nudo, ambiguo fra fattura e nota di credito). ⚠️ Il criterio guarda i FATTI: contano i movimenti registrati, non le righe ancora in lavorazione — `in_lavorazione` resta come colonna, per chi legge la riga e se lo chiede. ⚠️ Le righe forzate sono la TRACCIA della decisione, non il criterio. ⚠️ La formula del saldo NON e' ricopiata: e' il nucleo, una sede sola. ⚠️ security_invoker=on: va RI-SPECIFICATA a ogni CREATE OR REPLACE o PostgreSQL la azzera. S2-7 del cantiere incassi.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW pagamenti.vw_rate_fuori_capienza
WITH (security_invoker=on) AS
WITH candidate AS (
         SELECT s.id AS scadenza_id,
            s.fattura_id,
            s.numero_rata,
            s.data_scadenza,
            s.importo
           FROM vendite.fatture_scadenze s
          WHERE ((EXISTS ( SELECT 1
                   FROM pagamenti.vendite_movimenti m
                  WHERE ((m.scadenza_id = s.id) AND (m.attivo IS TRUE)))) OR (EXISTS ( SELECT 1
                   FROM pagamenti.vendite_contabili_righe cr
                  WHERE ((cr.scadenza_id = s.id) AND (cr.attivo IS TRUE) AND (cr.forzata IS TRUE)))) OR (EXISTS ( SELECT 1
                   FROM pagamenti.vendite_movimenti m
                  WHERE ((m.fattura_id = s.fattura_id) AND (m.scadenza_id IS NULL) AND (m.attivo IS TRUE)))))
        )
 SELECT
        CASE
            WHEN ((sign(x.saldo) <> sign(c.importo)) AND (x.saldo <> (0)::numeric)) THEN 'SOVRA_INCASSATA'::text
            ELSE 'MOVIMENTO_CONTRARIO'::text
        END AS motivo,
    c.scadenza_id,
    c.fattura_id,
    f.anno,
    f.serie,
    f.numero AS fattura_numero,
    f.billing_account_id,
    f.emittente_soggetto_ruolo_id,
    c.numero_rata,
    c.data_scadenza,
    c.importo AS importo_rata,
    (c.importo - x.saldo) AS registrato,
    x.saldo AS residuo,
    x.incassato,
    x.in_lavorazione,
    fz.righe_forzate,
    fz.motivi_forzatura,
    vendite.fn_numero_documento_fattura(f.numero, f.serie) AS numero_documento,
    nd.codice_interno AS natura_doc_codice_interno,
    nd.descrizione AS natura_doc_descrizione
   FROM ((((candidate c
     JOIN vendite.fatture f ON ((f.id = c.fattura_id)))
     JOIN config.nature_doc_fiscale nd ON ((nd.id = f.natura_doc_id)))
     JOIN pagamenti.fn_get_saldi_rate(ARRAY( SELECT cd.scadenza_id
           FROM candidate cd)) x(scadenza_id, saldo, in_lavorazione, incassato, has_movimenti) ON ((x.scadenza_id = c.scadenza_id)))
     LEFT JOIN LATERAL ( SELECT (count(*))::integer AS righe_forzate,
            string_agg(NULLIF(btrim(cr.motivo_forzatura), ''::text), ' · '::text ORDER BY cr.id) AS motivi_forzatura
           FROM pagamenti.vendite_contabili_righe cr
          WHERE ((cr.scadenza_id = c.scadenza_id) AND (cr.attivo IS TRUE) AND (cr.forzata IS TRUE))) fz ON (true))
  WHERE (((sign(x.saldo) <> sign(c.importo)) AND (x.saldo <> (0)::numeric)) OR (abs(x.saldo) > abs(c.importo)));
```

</div>


---
{% include-markdown "signature-core.md" %}
