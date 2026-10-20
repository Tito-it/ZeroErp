{% include-markdown "it/dbzero/vendite/manual/vw_situazione_merce_ordine.md" %}
# 🔍 View `vw_situazione_merce_ordine`

> 📝 **Descrizione**
>
> Aggregato PARLANTE per riga d'ordine, per il pannello situazione merce richiesta BE/FE del 2026-08-17; ragioni di disegno nelle intestazioni dei changeSet 20260817-15 e 20260818-06 e in dbzero/vendite/manual/vw_situazione_merce_ordine.md. ⭐ rev 2026-09-21 (D14, giro 2 — D3): l'aggregato NON sta piu' qui — sta in vendite.fn_situazione_merce_ordine(p_ddt_ids, p_ordine_ids), e questa vista ne e' la proiezione senza filtro, fn(NULL, NULL): UN corpo solo (D1). Chi legge PER DOCUMENTO chiama la funzione con un seme e paga le righe d'ordine chieste, non tutte: BE list_situazione_merce_ordine (per ordine e per DDT). Colonne proiettate per NOME con ordinato::numeric(18,6): un SELECT * perderebbe il typmod in silenzio. Una riga per riga d'ordine ATTIVA, comprese quelle mai spedite. ⭐ rev 2026-09-22 (D14 giro 6 — D6): vw_contatore_merce, il contatore GREZZO per riga d'ordine che stava accanto a questa, e' RITIRATA (20260922-08): dal giro 1 di D14 nessuna macchina la leggeva (il lister dosa dalla partita, fn_partite_merce col DDT come seme) e questa e' l'UNICA lettura per riga d'ordine — per una persona come per una macchina. `differenza` = Σ dei saldi delle PARTITE, con propagazione dei NULL (nessuna partita, o nessuna con un conto che si applica -&gt; NULL, MAI zero: e' la differenza fra «non si applica» e «non c'e' nulla da fare»). Il fatturato in anticipo resta FUORI dal saldo, in `fatturato_anticipato`: ne discende che una riga fatturata alla conferma e spedita a meta' esce PAREGGIATA e non «da accreditare». ⚠️ `da_spedire` viene dalla formula del residuo GIA' esistente (ordinato − Σ qta_evasa + fn_ordine_riga_qta_riconsegna), NON da ordinato − consegnato: le due divergono, perche' il consegnato delle partite include le ri-consegne. Le righe di RI-CONSEGNA sono escluse (conterebbero due volte). origine MULTIPLA -&gt; misurabile false: si dichiara, non si ripartisce. rev 2026-08-18 (20260818-06) — LA SOGLIA DELL'IMPEGNO: impegnata := stato dell'ordine &gt;= soglia(CONFERMATO, per codice_interno) AND NOT is_abortito. Sotto soglia `da_spedire` e' NULL e non un numero e `stato` e' NON_IMPEGNATA; la riga NON sparisce (il pannello e' per ordine). ⚠️ Le PARTITE hanno la precedenza: dove c'e' merce uscita vince il verso del saldo anche su ordine annullato. `stato` ha SETTE valori: NON_IMPEGNATA | NON_SPEDITA | NON_MISURABILE | NON_FATTURABILE | DA_FATTURARE | DA_ACCREDITARE | PAREGGIATA — i consumatori NON devono ri-tradurre il segno. rev 2026-09-13 (P-6): + data_consegna_richiesta_cliente, data_consegna_confermata e giorni_ritardo, in coda; il ritardo e' «oggi &gt; data di riferimento (la promessa, o la richiesta del cliente) E resta merce da spedire», NULL quando da_spedire e' NULL o zero o nessuna data e' dichiarata, 0 = non in ritardo. security_invoker=on ri-specificato (la reloption non si vede in pg_get_viewdef e un CREATE OR REPLACE la azzera: qui significa far girare la funzione come owner, bypass della RLS).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_situazione_merce_ordine
WITH (security_invoker=on) AS
SELECT ordine_riga_id,
    ordine_id,
    riga_nr,
    articolo_id,
    (ordinato)::numeric(18,6) AS ordinato,
    consegnato,
    reso,
    in_riconsegna,
    tenuti,
    fatturato_merce,
    fatturato_da_ordine,
    fatturato,
    fatturato_anticipato,
    da_spedire,
    partite_merce,
    misurabile,
    differenza,
    stato,
    data_consegna_richiesta_cliente,
    data_consegna_confermata,
    giorni_ritardo
   FROM vendite.fn_situazione_merce_ordine(NULL::bigint[], NULL::bigint[]) s(ordine_riga_id, ordine_id, riga_nr, articolo_id, ordinato, consegnato, reso, in_riconsegna, tenuti, fatturato_merce, fatturato_da_ordine, fatturato, fatturato_anticipato, da_spedire, partite_merce, misurabile, differenza, stato, data_consegna_richiesta_cliente, data_consegna_confermata, giorni_ritardo);
```

</div>


---
{% include-markdown "signature-core.md" %}
