{% include-markdown "it/dbzero/vendite/manual/vw_resi_righe_dettaglio.md" %}
# 🔍 View `vw_resi_righe_dettaglio`

> 📝 **Descrizione**
>
> Le RIGHE DI UN RESO per il drawer di dettaglio: anagrafica di riga, copertura della ri-consegna (qta_riconsegnata / qta_rinunciata / qta_residua / stato_riconsegna), quota gia' accreditata e motivo di blocco dell'annullo. ⭐ Nasce il 2026-08-25 perche' le righe del reso erano l'UNICO dettaglio documento servito da SQL scritto in Python (resi_repository.py::list_righe) invece che da una vista, e quello era il motivo per cui il motivo di blocco dell'annullo — chiesto dal team BE «sia sulle righe del reso sia sulla coda accrediti» — poteva arrivare su una superficie sola. ⚠️ E proprio non quella giusta: misurato lo stesso giorno, le tre righe con un accredito sono tutte USCITE dalla coda al verbo, quindi il pulsante «Annulla l'accredito» vive qui. ⚠️ LA VISTA PROIETTA, IL CHIAMANTE FILTRA: `attivo` e' una colonna e non un filtro incorporato, perche' una vista «dettaglio» che nasconde righe di nascosto darebbe un conteggio diverso da quello della tabella senza dirlo. Anche l'ordinamento resta al chiamante. ⛔ PERIMETRO: passa da vendite.resi, che ha la RLS (rls_resi_ef_whitelist), perche' vendite.resi_righe NON ce l'ha — senza quel join la vista sarebbe leggibile per qualunque reso_id, anche fuori dal perimetro emittente. Che il service autorizzi prima non basta: un oggetto di database dev'essere sicuro da solo, perche' il prossimo consumatore non sa cosa faceva il primo. Stessa classe di difetto degli archi B/E/F/G del grafo di genealogia, chiusa lo stesso giorno. ⭐ gia_accreditato e annullo_blocco_codice si leggono da funzioni del DB che sono la SEDE UNICA della loro formula: fn_resi_riga_accreditato_partita (che consuma anche vw_resi_da_accreditare — rifare la somma sul ponte darebbe una seconda verita', sbagliata sui kit) e script.fn_check_accredito_annullabile (la stessa che fn_annulla_accredito_riga_reso interroga per sollevare, cosi' lettura e guardia non possono divergere). security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_righe_dettaglio
WITH (security_invoker=on) AS
SELECT rr.id,
    rr.reso_id,
    rr.riga_nr,
    rr.attivo,
    rr.ddt_riga_id,
    rr.ordine_riga_id,
    rr.articolo_id,
    a.codice AS articolo_codice,
    a.descrizione AS articolo_descrizione,
    rr.descrizione,
    rr.quantita,
    rr.qta_operativa,
    rr.factor_to_base,
    rr.uom_operativa_id,
    um.codice AS uom_codice,
    rr.tipo_reso_id,
    tr.codice_interno AS tipo_reso_codice_interno,
    tr.descrizione AS tipo_reso_descrizione,
    tr.riapre_residuo,
    rr.motivo,
    COALESCE(ric.tot, (0)::numeric) AS qta_riconsegnata,
    COALESCE(rin.tot, (0)::numeric) AS qta_rinunciata,
    res.residuo AS qta_residua,
    (
        CASE
            WHEN (tr.riapre_residuo IS NOT TRUE) THEN NULL::text
            WHEN ((res.residuo = (0)::numeric) AND (COALESCE(rin.tot, (0)::numeric) > (0)::numeric)) THEN 'RINUNCIATA'::text
            WHEN ((COALESCE(ric.tot, (0)::numeric) = (0)::numeric) AND (COALESCE(rin.tot, (0)::numeric) = (0)::numeric)) THEN 'DA_RICONSEGNARE'::text
            WHEN (res.residuo > (0)::numeric) THEN 'PARZIALE'::text
            ELSE 'COMPLETATA'::text
        END)::character varying AS stato_riconsegna,
    acc.accreditato AS gia_accreditato,
    ann.codice AS annullo_blocco_codice,
    rr.meta,
    rr.data_insert,
    rr.data_update
   FROM (((((((((vendite.resi_righe rr
     JOIN vendite.resi r ON ((r.id = rr.reso_id)))
     LEFT JOIN catalogo.articoli a ON ((a.id = rr.articolo_id)))
     LEFT JOIN catalogo.unita_misura um ON ((um.id = rr.uom_operativa_id)))
     LEFT JOIN config.tipi_reso tr ON ((tr.id = rr.tipo_reso_id)))
     LEFT JOIN ( SELECT resi_righe_riconsegne.resi_riga_id,
            sum(resi_righe_riconsegne.qta) AS tot
           FROM vendite.resi_righe_riconsegne
          GROUP BY resi_righe_riconsegne.resi_riga_id) ric ON ((ric.resi_riga_id = rr.id)))
     LEFT JOIN ( SELECT resi_righe_rinunce.resi_riga_id,
            sum(resi_righe_rinunce.qta) AS tot
           FROM vendite.resi_righe_rinunce
          GROUP BY resi_righe_rinunce.resi_riga_id) rin ON ((rin.resi_riga_id = rr.id)))
     CROSS JOIN LATERAL ( SELECT vendite.fn_resi_riga_residuo_riconsegna(rr.id) AS residuo) res)
     CROSS JOIN LATERAL ( SELECT vendite.fn_resi_riga_accreditato_partita(rr.id) AS accreditato) acc)
     CROSS JOIN LATERAL ( SELECT (((script.fn_check_accredito_annullabile(rr.id) -> 0) ->> 'reason'::text))::character varying AS codice) ann);
```

</div>


---
{% include-markdown "signature-core.md" %}
