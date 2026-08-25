{% include-markdown "it/dbzero/vendite/manual/vw_resi_da_accreditare.md" %}
# 🔍 View `vw_resi_da_accreditare`

> 📝 **Descrizione**
>
> La CODA ACCREDITI: le righe di reso per cui il conto della merce dichiara un accredito ancora dovuto. La quota della partita si ripartisce fra le righe di reso con una greedy per resi_riga_id. rev 2026-08-18 (brief-design-note-credito-resi N9): la finestra si applica alla quantita' ANCORA ACCREDITABILE (quantita' resa meno gia' accreditato) e non alla quantita' resa. ⚠️ Con la seconda, dopo il primo accredito la riga gia' servita tornava in testa alla coda e si riprendeva il residuo della partita, mentre la riga che quel residuo lo doveva davvero usciva dalla coda: la quota diventava IRRAGGIUNGIBILE — la stessa malattia per cui il cantiere esiste, creata dal rimedio. Misurato sulla partita 17163 il 2026-08-18. ⭐ Ne discende che una riga esce dalla coda AL VERBO e non alla generazione della fattura: l'idempotenza smette di dipendere da una finestra temporale e diventa un numero che e' gia' sceso. Espone gia_accreditato e blocco_codice perche' il frontend gate il bottone sui dati che la riga porta gia', mai con una capability per riga di lista. ⭐ rev 2026-08-25 — annullo_blocco_codice: il motivo per cui l'ANNULLO dell'accredito e' bloccato su quella riga, NULL se ammesso, dal `reason` del primo motivo di script.fn_check_accredito_annullabile. Richiesta del team BE: il pulsante «Annulla l'accredito» era acceso anche quando l'annullo non era piu' possibile, e l'operatore scopriva il vincolo dopo aver scritto il motivo obbligatorio e confermato. ⛔ E' una colonna NUOVA e non un allargamento di blocco_codice: quella risponde a «perche' non posso ACCREDITARE» e il suo unico valore, GIA_ACCREDITATO, e' esattamente la condizione che ABILITA l'annullo — nella stessa colonna vorrebbe dire «bottone A spento» e «bottone B acceso» insieme. ⭐ La sede del predicato e' UNA: la stessa funzione che la madre interroga per sollevare, cosi' lettura e guardia non possono divergere. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_da_accreditare
WITH (security_invoker=on) AS
WITH acc AS (
         SELECT p.ddt_riga_id,
            p.tenuti,
            p.fatturato AS fatturati,
            (- p.differenza) AS accredito_partita
           FROM vendite.vw_partite_merce p
          WHERE (p.differenza < (0)::numeric)
        ), eff AS (
         SELECT e.resi_riga_id,
            e.reso_id,
            e.ddt_riga_id,
            e.ordine_riga_id,
            e.riapre_residuo,
            e.quantita,
            vendite.fn_resi_riga_accreditato_partita(e.resi_riga_id) AS gia_accreditato
           FROM vendite.vw_resi_righe_effettive e
        ), dist AS (
         SELECT e.resi_riga_id,
            e.reso_id,
            e.ddt_riga_id,
            e.ordine_riga_id,
            e.riapre_residuo,
            e.quantita AS qta_resa,
            e.gia_accreditato,
            a.tenuti,
            a.fatturati,
            GREATEST((0)::numeric, LEAST(GREATEST((0)::numeric, (e.quantita - e.gia_accreditato)), (a.accredito_partita - COALESCE(sum(GREATEST((0)::numeric, (e.quantita - e.gia_accreditato))) OVER (PARTITION BY e.ddt_riga_id ORDER BY e.resi_riga_id ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING), (0)::numeric)))) AS accredito_dovuto
           FROM (eff e
             JOIN acc a ON ((a.ddt_riga_id = e.ddt_riga_id)))
        )
 SELECT x.resi_riga_id,
    r.id AS reso_id,
    r.uid AS reso_uid,
    r.numero AS reso_numero,
    r.data,
    r.emittente_fiscale_id,
    r.billing_account_id,
    ba.codice AS ba_codice,
    r.destinatario_soggetto_ruolo_id,
    s_dest.ragione_sociale_completa AS destinatario_denominazione,
    rr.articolo_id,
    rr.descrizione,
    rr.quantita,
    rr.qta_operativa,
    rr.uom_operativa_id,
    rr.motivo,
    x.ddt_riga_id,
    dr.ddt_id,
    d.numero AS ddt_numero,
    x.ordine_riga_id,
    x.tenuti,
    x.fatturati,
    x.accredito_dovuto,
    (
        CASE
            WHEN (x.riapre_residuo AND (vendite.fn_resi_riga_residuo_riconsegna(x.resi_riga_id) > (0)::numeric)) THEN 'FACOLTATIVA'::text
            ELSE 'DOVUTA'::text
        END)::character varying AS etichetta,
    x.gia_accreditato,
    (
        CASE
            WHEN (x.gia_accreditato > (0)::numeric) THEN 'GIA_ACCREDITATO'::text
            ELSE NULL::text
        END)::character varying AS blocco_codice,
    (((script.fn_check_accredito_annullabile(x.resi_riga_id) -> 0) ->> 'reason'::text))::character varying AS annullo_blocco_codice
   FROM (((((((dist x
     JOIN vendite.resi_righe rr ON ((rr.id = x.resi_riga_id)))
     JOIN vendite.resi r ON ((r.id = x.reso_id)))
     JOIN anagrafiche.soggetti_ruoli sr_dest ON ((sr_dest.id = r.destinatario_soggetto_ruolo_id)))
     JOIN anagrafiche.soggetti s_dest ON ((s_dest.id = sr_dest.soggetto_id)))
     LEFT JOIN anagrafiche.billing_account ba ON ((ba.id = r.billing_account_id)))
     JOIN vendite.ddt_righe dr ON ((dr.id = x.ddt_riga_id)))
     JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
  WHERE (x.accredito_dovuto > (0)::numeric);
```


---
{% include-markdown "signature-core.md" %}
