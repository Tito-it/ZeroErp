{% include-markdown "it/dbzero/vendite/manual/vw_af_merce_per_riga.md" %}
# 🔍 View `vw_af_merce_per_riga`

> 📝 **Descrizione**
>
> Base del contatore merce (brief-design-partita-merce-generalizzata S1): traduce le attivita' fatturabili in quantita' PER RIGA DI DOCUMENTO SORGENTE. Grana (corsia, riga_id, tipo_movimento). corsia ORD/DDT da split_part(segment_key), riga_id da substring(... ):R:([0-9]+)) — ⚠️ i due id vengono da sequenze diverse, la corsia e' obbligatoria per interpretarli. I kit (segmenti #CMP) sono normalizzati in unita' del PADRE: quantita_padre = max(quantita / meta-&gt;&gt;'coeff_qta') per istanza di kit, con pretesa di coerenza min=max — se i componenti non concordano, o il coefficiente manca o non e' numerico, misurabile=false e il valore NON va usato come zero. tipo_movimento e' ESPOSTO e NON filtrato: il filtro NORMALE resta nei consumatori. ⭐ COSA MISURA: non «quanto e' stato fatturato» ma quanto e' entrato nella CORSIA di fatturazione — e' la misura che dosa il push e impedisce di spingere due volte. Non guarda quindi ne' fatturato ne' fattura_riga_id, e NON filtra NON_EMESSA: dopo un reset di lotto l'attivita' e' NON_EMESSA ma sta ANCORA nella corsia, e la sua riga di attivita_fatturabili e' il vaso che il ri-emit riempie di nuovo (l'emit e' un UPSERT su (sorgente_tipo_id, sorgente_uid), non un INSERT — ed e' per questo che reset + ri-emit non produce due righe che si sommano). ⛔ FILTRA pero' ANNULLATA, dal 2026-08-18: un'attivita' annullata dalla corsia e' USCITA e non ci rientra. Senza quel filtro una rettifica emessa, resettata e poi annullata lasciava qui la propria attivita_fatturabili, la partita restava pareggiata e la riga di reso non tornava MAI in coda accrediti — la merce resa diventava non accreditabile da nessuno (brief note-credito §10). ⚠️ Il filtro sta QUI e non nell'annullo perche' questa vista e' l'unico oggetto che somma attivita_fatturabili.quantita: correggerla corregge il conto ovunque, e vale per OGNI percorso che porta una riga ad ANNULLATA — compreso fn_annulla_commessa_attivita, che guarisce senza essere toccata. ⛔ E non si rispecchia lo stato dentro attivita_fatturabili: quel mirror lo aggiorna solo l'emit, quindi una colonna di stato li' sarebbe stale per costruzione. security_invoker=on (RLS su commesse_attivita). rev 2026-08-18.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_af_merce_per_riga
WITH (security_invoker=on) AS
WITH base AS (
         SELECT af.quantita,
            af.tipo_movimento,
            split_part((ca.segment_key)::text, ':'::text, 1) AS corsia,
            ("substring"((ca.segment_key)::text, ':R:([0-9]+)'::text))::bigint AS riga_id,
            split_part((ca.segment_key)::text, '#CMP:'::text, 1) AS kit_key,
            ((ca.segment_key)::text ~~ '%#CMP:%'::text) AS e_componente,
                CASE
                    WHEN ((ca.meta ->> 'coeff_qta'::text) ~ '^[0-9]+(\.[0-9]+){0,1}$'::text) THEN NULLIF(((ca.meta ->> 'coeff_qta'::text))::numeric, (0)::numeric)
                    ELSE NULL::numeric
                END AS coeff_qta
           FROM (vendite.attivita_fatturabili af
             JOIN vendite.commesse_attivita ca ON ((ca.id = af.commessa_attivita_id)))
          WHERE ((split_part((ca.segment_key)::text, ':'::text, 1) = ANY (ARRAY['ORD'::text, 'DDT'::text])) AND ((ca.segment_key)::text ~ ':R:[0-9]+'::text) AND ((ca.stato_emissione)::text <> 'ANNULLATA'::text))
        ), kit AS (
         SELECT b.corsia,
            b.riga_id,
            b.tipo_movimento,
            b.kit_key,
            max((b.quantita / b.coeff_qta)) AS quantita_padre,
            (bool_and((b.coeff_qta IS NOT NULL)) AND (min((b.quantita / b.coeff_qta)) = max((b.quantita / b.coeff_qta)))) AS misurabile
           FROM base b
          WHERE b.e_componente
          GROUP BY b.corsia, b.riga_id, b.tipo_movimento, b.kit_key
        ), unita_padre AS (
         SELECT k.corsia,
            k.riga_id,
            k.tipo_movimento,
            k.quantita_padre AS quantita,
            k.misurabile,
            true AS da_componenti
           FROM kit k
        UNION ALL
         SELECT b.corsia,
            b.riga_id,
            b.tipo_movimento,
            b.quantita,
            true,
            false
           FROM base b
          WHERE (NOT b.e_componente)
        )
 SELECT (corsia)::character varying AS corsia,
    riga_id,
    tipo_movimento,
    COALESCE(sum(quantita), (0)::numeric) AS quantita,
    bool_and(misurabile) AS misurabile,
    bool_or(da_componenti) AS da_componenti,
    (count(*))::integer AS voci
   FROM unita_padre u
  GROUP BY corsia, riga_id, tipo_movimento;
```


---
{% include-markdown "signature-core.md" %}
