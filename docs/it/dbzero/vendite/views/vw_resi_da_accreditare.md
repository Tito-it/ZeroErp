{% include-markdown "it/dbzero/vendite/manual/vw_resi_da_accreditare.md" %}
# 🔍 View `vw_resi_da_accreditare`

> 📝 **Descrizione**
>
> La CODA ACCREDITI: le righe di reso per cui il conto della merce dichiara un accredito ancora dovuto. ⭐ rev 2026-09-21 (D14, giro 2 — D3): la coda NON sta piu' qui — sta in vendite.fn_resi_da_accreditare(p_ddt_ids, p_ordine_ids), e questa vista ne e' la proiezione senza filtro, fn(NULL, NULL): UN corpo solo (D1). Chi legge PER DOCUMENTO chiama la funzione con un seme e paga la coda di quel documento, non quella di tutti: fn_accredita_riga_reso e fn_resi_riga_tetti_accredito (il DDT della riga resa), BE per documento (richiesta nel brief). Chi legge tutto — la lista configurabile della coda, vw_dash_backlog_documenti — legge la vista. Colonne proiettate per NOME coi cinque varchar ricastati (reso_numero 32, ba_codice 30, descrizione e motivo 255, ddt_numero 20): un SELECT * perderebbe i typmod in silenzio. La quota della partita si ripartisce fra le righe di reso con una greedy per resi_riga_id. rev 2026-08-18 (brief-design-note-credito-resi N9): la finestra si applica alla quantita' ANCORA ACCREDITABILE (quantita' resa meno gia' accreditato) e non alla quantita' resa. ⚠️ Con la seconda, dopo il primo accredito la riga gia' servita tornava in testa alla coda e si riprendeva il residuo della partita, mentre la riga che quel residuo lo doveva davvero usciva dalla coda: la quota diventava IRRAGGIUNGIBILE — la stessa malattia per cui il cantiere esiste, creata dal rimedio. ⭐ Ne discende che una riga esce dalla coda AL VERBO e non alla generazione della fattura: l'idempotenza smette di dipendere da una finestra temporale e diventa un numero che e' gia' sceso. Espone gia_accreditato e blocco_codice perche' il frontend gate il bottone sui dati che la riga porta gia', mai con una capability per riga di lista. ⭐ rev 2026-08-25 — annullo_blocco_codice: il motivo per cui l'ANNULLO dell'accredito e' bloccato su quella riga, NULL se ammesso, dal `reason` del primo motivo di script.fn_check_accredito_annullabile. ⛔ E' una colonna NUOVA e non un allargamento di blocco_codice: quella risponde a «perche' non posso ACCREDITARE» e il suo unico valore, GIA_ACCREDITATO, e' esattamente la condizione che ABILITA l'annullo. ⭐ La sede del predicato e' UNA: la stessa funzione che la madre interroga per sollevare, cosi' lettura e guardia non possono divergere. security_invoker=on ri-specificato (un CREATE OR REPLACE la azzera: qui significa far girare la funzione come owner, bypass della RLS).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_resi_da_accreditare
WITH (security_invoker=on) AS
SELECT resi_riga_id,
    reso_id,
    reso_uid,
    (reso_numero)::character varying(32) AS reso_numero,
    data,
    emittente_fiscale_id,
    billing_account_id,
    (ba_codice)::character varying(30) AS ba_codice,
    destinatario_soggetto_ruolo_id,
    destinatario_denominazione,
    articolo_id,
    (descrizione)::character varying(255) AS descrizione,
    quantita,
    qta_operativa,
    uom_operativa_id,
    (motivo)::character varying(255) AS motivo,
    ddt_riga_id,
    ddt_id,
    (ddt_numero)::character varying(20) AS ddt_numero,
    ordine_riga_id,
    tenuti,
    fatturati,
    accredito_dovuto,
    etichetta,
    gia_accreditato,
    blocco_codice,
    annullo_blocco_codice
   FROM vendite.fn_resi_da_accreditare(NULL::bigint[], NULL::bigint[]) q(resi_riga_id, reso_id, reso_uid, reso_numero, data, emittente_fiscale_id, billing_account_id, ba_codice, destinatario_soggetto_ruolo_id, destinatario_denominazione, articolo_id, descrizione, quantita, qta_operativa, uom_operativa_id, motivo, ddt_riga_id, ddt_id, ddt_numero, ordine_riga_id, tenuti, fatturati, accredito_dovuto, etichetta, gia_accreditato, blocco_codice, annullo_blocco_codice);
```

</div>


---
{% include-markdown "signature-core.md" %}
