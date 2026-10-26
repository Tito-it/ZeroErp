{% include-markdown "it/dbzero/vendite/manual/vw_af_merce_per_riga.md" %}
# 🔍 View `vw_af_merce_per_riga`

> 📝 **Descrizione**
>
> Base del contatore merce (brief-design-partita-merce-generalizzata S1): traduce le attivita' fatturabili in quantita' PER RIGA DI DOCUMENTO SORGENTE. ⭐ rev 2026-09-21 (D14 giro 4 — D5): il conto NON sta piu' qui — sta in vendite.fn_af_merce_per_riga(p_segment_keys), e questa vista ne e' la proiezione senza filtro, fn(NULL): UN corpo solo (D1). Chi legge per documento chiama la funzione con le chiavi di segmento della propria chiusura (fn_partite_merce, fn_situazione_merce_ordine) e paga quelle righe, non la tabella intera — che cresce con le FATTURE. Colonne per nome con tipo_movimento ricastato a varchar(32): un SELECT * perderebbe il typmod in silenzio. Grana (corsia, riga_id, tipo_movimento). corsia ORD/DDT da split_part(segment_key), riga_id da substring(... ):R:([0-9]+)) — ⚠️ i due id vengono da sequenze diverse, la corsia e' obbligatoria per interpretarli. I kit (segmenti #CMP) sono normalizzati in unita' del PADRE: quantita_padre = max(quantita / meta-&gt;&gt;'coeff_qta') per istanza di kit, con pretesa di coerenza min=max — se i componenti non concordano, o il coefficiente manca o non e' numerico, misurabile=false e il valore NON va usato come zero. tipo_movimento e' ESPOSTO e NON filtrato: il filtro NORMALE resta nei consumatori. ⭐ COSA MISURA: non «quanto e' stato fatturato» ma quanto e' entrato nella CORSIA di fatturazione — e' la misura che dosa il push e impedisce di spingere due volte. Non guarda quindi ne' fatturato ne' fattura_riga_id, e NON filtra NON_EMESSA: dopo un reset di lotto l'attivita' e' NON_EMESSA ma sta ANCORA nella corsia, e la sua riga di attivita_fatturabili e' il vaso che il ri-emit riempie di nuovo (l'emit e' un UPSERT su (sorgente_tipo_id, sorgente_uid), non un INSERT — ed e' per questo che reset + ri-emit non produce due righe che si sommano). ⛔ FILTRA pero' ANNULLATA, dal 2026-08-18: un'attivita' annullata dalla corsia e' USCITA e non ci rientra. Senza quel filtro una rettifica emessa, resettata e poi annullata lasciava qui la propria attivita_fatturabili, la partita restava pareggiata e la riga di reso non tornava MAI in coda accrediti — la merce resa diventava non accreditabile da nessuno (brief note-credito §10). ⚠️ Il filtro sta nel conto e non nell'annullo perche' questo e' l'unico oggetto che somma attivita_fatturabili.quantita: correggerlo corregge il conto ovunque, e vale per OGNI percorso che porta una riga ad ANNULLATA — compreso fn_annulla_commessa_attivita, che guarisce senza essere toccata. ⛔ E non si rispecchia lo stato dentro attivita_fatturabili: quel mirror lo aggiorna solo l'emit, quindi una colonna di stato li' sarebbe stale per costruzione. security_invoker=on ri-specificato (RLS su commesse_attivita attraverso la funzione, non DEFINER). rev 2026-08-18; rev 2026-09-21.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_af_merce_per_riga
WITH (security_invoker=on) AS
SELECT corsia,
    riga_id,
    (tipo_movimento)::character varying(32) AS tipo_movimento,
    quantita,
    misurabile,
    da_componenti,
    voci
   FROM vendite.fn_af_merce_per_riga(NULL::character varying[]) f(corsia, riga_id, tipo_movimento, quantita, misurabile, da_componenti, voci);
```

</div>


---
{% include-markdown "signature-core.md" %}
