{% include-markdown "it/dbzero/vendite/manual/vw_contatore_merce.md" %}
# 🔍 View `vw_contatore_merce`

> 📝 **Descrizione**
>
> Il contatore, come AGGREGATO per riga d'ordine delle partite di merce (brief-design-partita-merce-generalizzata S3, rev 2026-08-17). Non calcola piu': somma vw_partite_merce (grana = riga di DDT) e ci aggiunge il fatturato nato sulla corsia ORD. ⚠️ Le righe di RI-CONSEGNA sono ESCLUSE (e_riconsegna): i loro pezzi sono gia' nel consegnato della partita d'origine, e senza il filtro verrebbero contati due volte — hanno una riga d'ordine, perche' fn_genera_ddt_riconsegna crea un fulfillment. Le sei colonne storiche sono INVARIATE nella semantica: parita' 18/18 contro la fotografia S0 post-decisione D1. Sparisce WHERE NOT is_composito: i kit entrano, contati in unita' del PADRE (S1). Colonne in coda: consegnato, reso, in_riconsegna, fatturato_su_merce, fatturato_su_ordine, fatturato_anticipato (fatturato di merce NON ancora uscita — non e' un accredito dovuto), partite_merce, misurabile. ⚠️ Qui `differenza` NON e' mai NULL, a differenza di vw_partite_merce: fn_list_ddt_da_pushare fa COALESCE(differenza,0) e un NULL smetterebbe di fatturare una riga in silenzio. Questa resta il contatore GREZZO che dosa le macchine; chi vuole la semantica parlante (stato, NULL = «non si applica») legge vw_partite_merce. security_invoker=on + RLS.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_contatore_merce
WITH (security_invoker=on) AS
WITH pm AS (
         SELECT p.ordine_riga_id,
            sum(p.consegnato) AS consegnato,
            sum(p.reso) AS reso,
            sum(p.in_riconsegna) AS in_riconsegna,
            sum(p.tenuti) AS tenuti,
            sum(p.fatturato_merce) AS fatturato_su_merce,
            sum(p.fatturato_da_ordine) AS allocato,
            (count(*))::integer AS partite_merce,
            bool_and(p.misurabile) AS misurabile
           FROM vendite.vw_partite_merce p
          WHERE ((p.ordine_riga_id IS NOT NULL) AND (NOT p.e_riconsegna))
          GROUP BY p.ordine_riga_id
        ), ord AS (
         SELECT f.riga_id AS ordine_riga_id,
            f.quantita,
            f.misurabile
           FROM vendite.vw_af_merce_per_riga f
          WHERE (((f.corsia)::text = 'ORD'::text) AND ((f.tipo_movimento)::text = 'NORMALE'::text))
        )
 SELECT orr.id AS ordine_riga_id,
    orr.ordine_id,
    orr.articolo_id,
    pm.tenuti,
    (COALESCE(pm.fatturato_su_merce, (0)::numeric) + COALESCE(o.quantita, (0)::numeric)) AS fatturati,
    (pm.tenuti - (COALESCE(pm.fatturato_su_merce, (0)::numeric) + COALESCE(o.quantita, (0)::numeric))) AS differenza,
    pm.consegnato,
    pm.reso,
    pm.in_riconsegna,
    COALESCE(pm.fatturato_su_merce, (0)::numeric) AS fatturato_su_merce,
    COALESCE(o.quantita, (0)::numeric) AS fatturato_su_ordine,
    GREATEST((0)::numeric, (COALESCE(o.quantita, (0)::numeric) - COALESCE(pm.allocato, (0)::numeric))) AS fatturato_anticipato,
    pm.partite_merce,
    (pm.misurabile AND COALESCE(o.misurabile, true)) AS misurabile
   FROM ((pm
     JOIN vendite.ordini_righe orr ON ((orr.id = pm.ordine_riga_id)))
     LEFT JOIN ord o ON ((o.ordine_riga_id = pm.ordine_riga_id)));
```


---
{% include-markdown "signature-core.md" %}
