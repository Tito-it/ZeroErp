{% include-markdown "it/dbzero/anagrafiche/manual/vw_stiva_movimenti_dettaglio.md" %}
# 🔍 View `vw_stiva_movimenti_dettaglio`

> 📝 **Descrizione**
>
> Le RIGHE DEL REGISTRO dei movimenti di plafond di un titolo IVA, per il drawer di dettaglio: anagrafica del movimento, il tipo di titolo, il legame dell'annullo nei DUE versi (cosa annullo / chi mi annulla, con i flag is_annullo e is_annullato) e il MOTIVO DI BLOCCO dell'annullo. ⭐ Nasce il 2026-08-30 perche' per questo registro non esisteva nessuna vista, ed e' esattamente il motivo per cui il motivo di blocco non poteva arrivare da nessuna parte — stesso punto di partenza da cui nacque vendite.vw_resi_righe_dettaglio. ⭐ annullo_blocco_codice/reason_key si leggono da script.fn_check_annullo_movimento_titolo_iva, la STESSA che anagrafiche.fn_annulla_movimento_titolo_iva interroga per sollevare: cosi' il pulsante spento e il rifiuto non possono divergere. ⛔ Un verbo, una colonna: il nome dice per quale azione e' il blocco. La colonna porta il `reason` (codice macchina), non il codice errore — stessa convenzione della gemella. NULL = annullo ammesso. ⛔ PERIMETRO: passa da anagrafiche.soggetti_titoli_iva, da cui arrivano emittente e soggetto; un oggetto di database dev'essere sicuro da solo, perche' il prossimo consumatore non sa cosa faceva il primo. ⚠️ LA VISTA PROIETTA, IL CHIAMANTE FILTRA: nessun filtro incorporato e nessun ordinamento. ⚠️ Il LATERAL invoca la check una volta per riga: per le azioni DI RIGA e' il pattern dichiarato (linee-guida-sql §12.5), e qui si guarda il registro di UN titolo. security_invoker=on. Piano: brief-db-titoli-iva-movimenti-annullo, Fase D.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_stiva_movimenti_dettaglio
WITH (security_invoker=on) AS
SELECT m.id,
    m.titolo_iva_id,
    t.soggetto_id,
    t.emittente_fiscale_id,
    tt.codice_interno AS tipo_titolo_codice_interno,
    tt.descrizione AS tipo_titolo_descrizione,
    m.tipo_movimento,
    m.imponibile,
    m.data_movimento,
    m.fattura_id,
    m.fattura_riga_id,
    m.motivo,
    m.annulla_movimento_id,
    ann.id AS annullato_da_movimento_id,
    (ann.id IS NOT NULL) AS is_annullato,
    (m.annulla_movimento_id IS NOT NULL) AS is_annullo,
    blk.reason AS annullo_blocco_codice,
    blk.reason_key AS annullo_blocco_reason_key,
    m.meta,
    m.tx_id,
    m.data_insert,
    m.user_insert,
    m.data_update,
    m.user_update
   FROM ((((anagrafiche.soggetti_titoli_iva_movimenti m
     JOIN anagrafiche.soggetti_titoli_iva t ON ((t.id = m.titolo_iva_id)))
     LEFT JOIN config.tipi_titolo_iva tt ON ((tt.id = t.tipo_titolo_iva_id)))
     LEFT JOIN anagrafiche.soggetti_titoli_iva_movimenti ann ON ((ann.annulla_movimento_id = m.id)))
     CROSS JOIN LATERAL ( SELECT (((script.fn_check_annullo_movimento_titolo_iva(m.id) -> 0) ->> 'reason'::text))::character varying AS reason,
            (((script.fn_check_annullo_movimento_titolo_iva(m.id) -> 0) ->> 'reason_key'::text))::character varying AS reason_key) blk);
```

</div>


---
{% include-markdown "signature-core.md" %}
