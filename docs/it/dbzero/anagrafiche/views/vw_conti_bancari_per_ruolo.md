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
            r.predefinito,
            1 AS priority,
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
            s.predefinito,
            2 AS priority,
            s.valido_dal,
            s.valido_al,
            s.data_update,
            'SOGGETTO'::character varying(10) AS fonte
           FROM ((anagrafiche.soggetti_ruoli sr
             JOIN anagrafiche.soggetti_conti_bancari s ON ((s.soggetto_id = sr.soggetto_id)))
             JOIN anagrafiche.conti_bancari cb ON ((cb.id = s.conto_bancario_id)))
          WHERE (((s.valido_dal IS NULL) OR (s.valido_dal <= CURRENT_DATE)) AND ((s.valido_al IS NULL) OR (s.valido_al >= CURRENT_DATE)) AND (COALESCE(s.bloccato, false) = false) AND (cb.attivo = true))
        ), candidates AS (
         SELECT role_cand.soggetto_ruolo_id,
            role_cand.uso,
            role_cand.conto_bancario_id,
            role_cand.soggetto_ruolo_conto_id,
            role_cand.soggetto_conto_id,
            role_cand.predefinito,
            role_cand.priority,
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
            subj_cand.predefinito,
            subj_cand.priority,
            subj_cand.valido_dal,
            subj_cand.valido_al,
            subj_cand.data_update,
            subj_cand.fonte
           FROM subj_cand
        )
 SELECT DISTINCT ON (soggetto_ruolo_id, uso) soggetto_ruolo_id,
    uso,
    conto_bancario_id,
    soggetto_ruolo_conto_id,
    soggetto_conto_id,
    fonte,
    predefinito,
    valido_dal,
    valido_al,
    data_update
   FROM candidates
  ORDER BY soggetto_ruolo_id, uso, priority, predefinito DESC, data_update DESC, soggetto_ruolo_conto_id, soggetto_conto_id;
```


---
{% include-markdown "signature-core.md" %}
