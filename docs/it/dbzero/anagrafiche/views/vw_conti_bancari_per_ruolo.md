{% include-markdown "it/dbzero/anagrafiche/manual/vw_conti_bancari_per_ruolo.md" %}
# 🔍 View `vw_conti_bancari_per_ruolo`

```sql
CREATE OR REPLACE VIEW anagrafiche.vw_conti_bancari_per_ruolo AS
WITH role_cand AS (
         SELECT sr.id AS soggetto_ruolo_id,
            r.uso,
            r.conto_bancario_id,
            r.id AS soggetto_ruolo_conto_id,
            NULL::bigint AS soggetto_conto_id,
            r.utility_id,
            r.predefinito,
            r.valido_dal,
            r.valido_al,
            r.data_update,
            'RUOLO'::character varying(10) AS fonte
           FROM ((anagrafiche.soggetti_ruoli sr
             JOIN anagrafiche.soggetti_ruoli_conti_bancari r ON ((r.soggetto_ruolo_id = sr.id)))
             JOIN anagrafiche.conti_bancari cb ON ((cb.id = r.conto_bancario_id)))
          WHERE (((r.valido_dal IS NULL) OR (r.valido_dal <= CURRENT_DATE)) AND ((r.valido_al IS NULL) OR (r.valido_al >= CURRENT_DATE)) AND (COALESCE(r.bloccato, false) = false) AND (cb.attivo = true))
        ), subj_cand AS (
         SELECT sr.id AS soggetto_ruolo_id,
            s.uso,
            s.conto_bancario_id,
            NULL::bigint AS soggetto_ruolo_conto_id,
            s.id AS soggetto_conto_id,
            NULL::integer AS utility_id,
            s.predefinito,
            s.valido_dal,
            s.valido_al,
            s.data_update,
            'SOGGETTO'::character varying(10) AS fonte
           FROM ((anagrafiche.soggetti_ruoli sr
             JOIN anagrafiche.soggetti_conti_bancari s ON ((s.soggetto_id = sr.soggetto_id)))
             JOIN anagrafiche.conti_bancari cb ON ((cb.id = s.conto_bancario_id)))
          WHERE (((s.valido_dal IS NULL) OR (s.valido_dal <= CURRENT_DATE)) AND ((s.valido_al IS NULL) OR (s.valido_al >= CURRENT_DATE)) AND (COALESCE(s.bloccato, false) = false) AND (cb.attivo = true))
        )
 SELECT c.soggetto_ruolo_id,
    c.uso,
    c.conto_bancario_id,
    c.soggetto_ruolo_conto_id,
    c.soggetto_conto_id,
    c.utility_id,
    ut.codice AS utility_codice,
    c.fonte,
    c.predefinito,
    c.valido_dal,
    c.valido_al,
    c.data_update
   FROM (( SELECT role_cand.soggetto_ruolo_id,
            role_cand.uso,
            role_cand.conto_bancario_id,
            role_cand.soggetto_ruolo_conto_id,
            role_cand.soggetto_conto_id,
            role_cand.utility_id,
            role_cand.predefinito,
            role_cand.valido_dal,
            role_cand.valido_al,
            role_cand.data_update,
            role_cand.fonte
           FROM role_cand
        UNION ALL
         SELECT subj_cand.soggetto_ruolo_id,
            subj_cand.uso,
            subj_cand.conto_bancario_id,
            subj_cand.soggetto_ruolo_conto_id,
            subj_cand.soggetto_conto_id,
            subj_cand.utility_id,
            subj_cand.predefinito,
            subj_cand.valido_dal,
            subj_cand.valido_al,
            subj_cand.data_update,
            subj_cand.fonte
           FROM subj_cand) c
     LEFT JOIN config.utilities ut ON ((ut.id = c.utility_id)))
  ORDER BY c.soggetto_ruolo_id, c.uso,
        CASE
            WHEN (((c.fonte)::text = 'RUOLO'::text) AND (c.utility_id IS NOT NULL)) THEN 1
            WHEN (((c.fonte)::text = 'RUOLO'::text) AND (c.utility_id IS NULL)) THEN 2
            WHEN ((c.fonte)::text = 'SOGGETTO'::text) THEN 3
            ELSE NULL::integer
        END, c.predefinito DESC, c.data_update DESC;
```


---
{% include-markdown "signature-core.md" %}
