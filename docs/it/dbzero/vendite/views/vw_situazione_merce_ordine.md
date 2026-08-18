{% include-markdown "it/dbzero/vendite/manual/vw_situazione_merce_ordine.md" %}
# 🔍 View `vw_situazione_merce_ordine`

> 📝 **Descrizione**
>
> Aggregato PARLANTE per riga d'ordine, per il pannello situazione merce richiesta BE/FE del 2026-08-17; ragioni di disegno nelle intestazioni dei changeSet 20260817-15 e 20260818-06 e in dbzero/vendite/manual/vw_situazione_merce_ordine.md. Una riga per riga d'ordine ATTIVA, comprese quelle mai spedite — che vw_contatore_merce non contiene, ed erano 89 su 107. ⚠️ NON sostituisce vw_contatore_merce, che resta il contatore grezzo e dosa la fatturazione: questa gli sta accanto. `differenza` = Σ dei saldi delle PARTITE, con propagazione dei NULL (nessuna partita, o nessuna con un conto che si applica -&gt; NULL, MAI zero: e' la differenza fra «non si applica» e «non c'e' nulla da fare»). Il fatturato in anticipo resta FUORI dal saldo, in `fatturato_anticipato`: ne discende che una riga fatturata alla conferma e spedita a meta' esce PAREGGIATA e non «da accreditare», che sul contatore non era ottenibile senza rompere la parita'. ⚠️ `da_spedire` viene dalla formula del residuo GIA' esistente (ordinato − Σ qta_evasa + fn_ordine_riga_qta_riconsegna), NON da ordinato − consegnato: le due divergono, perche' il consegnato delle partite include le ri-consegne. Le righe di RI-CONSEGNA sono escluse (conterebbero due volte). origine MULTIPLA -&gt; misurabile false: si dichiara, non si ripartisce. rev 2026-08-18 (20260818-06) — LA SOGLIA DELL'IMPEGNO, gemella della decisione D1 sul DDT: impegnata := stato dell'ordine &gt;= soglia(CONFERMATO, per codice_interno) AND NOT is_abortito. Sotto soglia `da_spedire` e' NULL e non un numero (su una bozza l'impegno non c'e' ancora, su un ordine abortito non c'e' piu': «quanto resta da spedire» non si applica — erano 60 righe su 107 a dichiarare un arretrato che era un'intenzione) e `stato` e' NON_IMPEGNATA. ⚠️ La riga NON sparisce: il pannello e' per ordine e farla sparire renderebbe VUOTO il pannello di ogni bozza, cioe' «non ho il permesso di saperlo» presentato come «non c'e' nulla da fare». ⚠️ Le PARTITE hanno la precedenza: dove c'e' merce uscita vince il verso del saldo anche su ordine annullato. ⚠️ Servono ENTRAMBE le clausole: ANNULLATO ha ordine 60 &gt; 20, e su stati_doc_ordini la colonna `ordine` e' un ordinamento di presentazione (EVASO 25 prima di ALLOCATO 30), non un ciclo di vita — assunzione inchiodata dal pgTAP. `stato` ha SETTE valori: NON_IMPEGNATA | NON_SPEDITA | NON_MISURABILE | NON_FATTURABILE | DA_FATTURARE | DA_ACCREDITARE | PAREGGIATA — i consumatori NON devono ri-tradurre il segno. security_invoker=on.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_situazione_merce_ordine
WITH (security_invoker=on) AS
WITH soglia AS (
         SELECT s.ordine AS ordine_confermato
           FROM config.stati_doc_ordini s
          WHERE ((s.codice_interno)::text = 'CONFERMATO'::text)
        ), pm AS (
         SELECT p.ordine_riga_id,
            (count(*))::integer AS partite_merce,
            sum(p.consegnato) AS consegnato,
            sum(p.reso) AS reso,
            sum(p.in_riconsegna) AS in_riconsegna,
            sum(p.tenuti) AS tenuti,
            sum(p.fatturato_merce) AS fatturato_merce,
            sum(p.fatturato_da_ordine) AS fatturato_da_ordine,
            sum(p.differenza) AS differenza,
            bool_and(p.misurabile) AS misurabile,
            bool_or(((p.origine)::text = 'MULTIPLA'::text)) AS ha_origine_multipla,
            (count(*) FILTER (WHERE (p.differenza IS NOT NULL)))::integer AS partite_con_conto
           FROM vendite.vw_partite_merce p
          WHERE ((p.ordine_riga_id IS NOT NULL) AND (NOT p.e_riconsegna))
          GROUP BY p.ordine_riga_id
        ), ord AS (
         SELECT f_1.riga_id AS ordine_riga_id,
            f_1.quantita,
            f_1.misurabile
           FROM vendite.vw_af_merce_per_riga f_1
          WHERE (((f_1.corsia)::text = 'ORD'::text) AND ((f_1.tipo_movimento)::text = 'NORMALE'::text))
        ), ful AS (
         SELECT f_1.ordine_riga_id,
            sum(f_1.qta_evasa) AS evaso
           FROM vendite.ordini_righe_fulfillment f_1
          GROUP BY f_1.ordine_riga_id
        )
 SELECT orr.id AS ordine_riga_id,
    orr.ordine_id,
    orr.riga_nr,
    orr.articolo_id,
    orr.quantita AS ordinato,
    COALESCE(pm.consegnato, (0)::numeric) AS consegnato,
    COALESCE(pm.reso, (0)::numeric) AS reso,
    COALESCE(pm.in_riconsegna, (0)::numeric) AS in_riconsegna,
    COALESCE(pm.tenuti, (0)::numeric) AS tenuti,
    COALESCE(pm.fatturato_merce, (0)::numeric) AS fatturato_merce,
    COALESCE(pm.fatturato_da_ordine, (0)::numeric) AS fatturato_da_ordine,
    (COALESCE(pm.fatturato_merce, (0)::numeric) + COALESCE(pm.fatturato_da_ordine, (0)::numeric)) AS fatturato,
    GREATEST((0)::numeric, (COALESCE(o.quantita, (0)::numeric) - COALESCE(pm.fatturato_da_ordine, (0)::numeric))) AS fatturato_anticipato,
        CASE
            WHEN imp.impegnata THEN GREATEST((0)::numeric, ((orr.quantita - COALESCE(f.evaso, (0)::numeric)) + vendite.fn_ordine_riga_qta_riconsegna(orr.id)))
            ELSE NULL::numeric
        END AS da_spedire,
    COALESCE(pm.partite_merce, 0) AS partite_merce,
    v.misurabile,
        CASE
            WHEN v.misurabile THEN pm.differenza
            ELSE NULL::numeric
        END AS differenza,
    (
        CASE
            WHEN ((COALESCE(pm.partite_merce, 0) = 0) AND (NOT imp.impegnata)) THEN 'NON_IMPEGNATA'::text
            WHEN (COALESCE(pm.partite_merce, 0) = 0) THEN 'NON_SPEDITA'::text
            WHEN (NOT v.misurabile) THEN 'NON_MISURABILE'::text
            WHEN (pm.differenza IS NULL) THEN 'NON_FATTURABILE'::text
            WHEN (pm.differenza > (0)::numeric) THEN 'DA_FATTURARE'::text
            WHEN (pm.differenza < (0)::numeric) THEN 'DA_ACCREDITARE'::text
            ELSE 'PAREGGIATA'::text
        END)::character varying AS stato
   FROM ((((((((vendite.ordini_righe orr
     JOIN vendite.ordini o_rls ON ((o_rls.id = orr.ordine_id)))
     JOIN config.stati_doc_ordini sdo ON ((sdo.id = o_rls.stato_doc_ordine_id)))
     CROSS JOIN soglia sg)
     LEFT JOIN pm ON ((pm.ordine_riga_id = orr.id)))
     LEFT JOIN ord o ON ((o.ordine_riga_id = orr.id)))
     LEFT JOIN ful f ON ((f.ordine_riga_id = orr.id)))
     CROSS JOIN LATERAL ( SELECT (COALESCE(pm.misurabile, true) AND COALESCE(o.misurabile, true) AND (NOT COALESCE(pm.ha_origine_multipla, false))) AS misurabile) v)
     CROSS JOIN LATERAL ( SELECT ((COALESCE((sdo.ordine)::integer, '-1'::integer) >= sg.ordine_confermato) AND (NOT sdo.is_abortito)) AS impegnata) imp)
  WHERE (orr.attivo IS TRUE);
```


---
{% include-markdown "signature-core.md" %}
