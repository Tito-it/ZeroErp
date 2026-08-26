{% include-markdown "it/dbzero/vendite/manual/vw_dash_competenza_gruppi.md" %}
# 🔍 View `vw_dash_competenza_gruppi`

> 📝 **Descrizione**
>
> Lente 1 Competenza, gruppi fatturabili: l'unita' dell'emissione mirata. Una riga per (competenza_mese, gruppo_key). security_invoker=on (scope emittente). Rev 2026-08-18 (P-4, brief perimetro-emittente Q4): espone emittente_ragione_sociale, non piu' il solo emittente_soggetto_ruolo_id — un id a video non dichiara l'emittente, lo nasconde meglio. E' la lista PILOTA del giro P-4 perche' e' quella da cui parte l'emissione mirata: si spuntano i gruppi e si fattura. ⚠️ La colonna arriva a video solo con la richiesta BE-2 (la lista ha vista_sql NULL: le righe le compone il repository, che elenca le colonne esplicitamente). ⭐ Rev 2026-08-26 (L5, brief-db-registro-e-data-prevista-in-competenza): quattro colonne in coda — registri_ids, registri_n, registro_codice, data_documento_prevista. Rispondono alla domanda che ha aperto il cantiere: la schermata da cui si preme «fattura» non diceva ne' su quale sezionale sarebbe finito il documento ne' che data avrebbe portato, e sono le due cose che governano tutto cio' che viene dopo. ⛔ «UNO OPPURE N» (decisione D-2): un gruppo puo' toccare piu' sezionali per costruzione — la chiave del gruppo non contiene ne' tipo documento ne' natura, che sono colonne di RIGA — e in quel caso codice e data restano VUOTI. Mai il primo che capita: un min() o un LIMIT 1 darebbe un valore plausibile che descrive meta' di cio' che sta per succedere. I due min() qui ci sono, ma dentro un CASE che ha gia' verificato che l'insieme abbia un elemento solo. ⭐ registri_ids e' l'elemento PORTANTE e non un extra: e' cio' su cui il backend filtra per sezionale (decisione D-5), con %% = ANY(registri_ids). Filtrare su registro_codice non funzionerebbe — su un gruppo multi-sezionale e' NULL per decisione, quindi il gruppo sparirebbe da ENTRAMBI i filtri, cioe' proprio quello che ha piu' bisogno di essere visto. La domanda giusta e' «questo gruppo TOCCA quel sezionale?». ⭐ registri_n non e' una seconda verita': e' cardinality(registri_ids), la stessa espressione con due nomi, calcolata nella stessa vista. ⚠️ array_agg INCLUDE i NULL mentre count(DISTINCT) li scarta in silenzio: e' cosi' che un gruppo con una riga risolta e una NON risolvibile conta 2 e legge «piu' registri», invece di mostrare un sezionale solo. E su un gruppo interamente fatturato — dove la previsione e' azzerata a monte per la decisione D-9 — l'array e' {NULL}, cardinalita' 1, con codice e data a NULL: a video «—». ⛔ La frase «piu' registri» NON nasce qui (decisione D-4): il database dice QUANTI sono, il testo lo mette BE/FE. Una vista che restituisse quella stringa scriverebbe italiano dentro il database, e il prodotto ha it.json E en.json; il precedente giusto e' in questa stessa vista, dove tipo_gruppo restituisce un CODICE e non una frase.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_dash_competenza_gruppi
WITH (security_invoker=on) AS
WITH aggregato AS (
         SELECT a.competenza_mese,
            a.gruppo_key,
            a.sorgente_tipo_id,
            a.sorgente_uid,
            a.commessa_id,
            a.commessa_codice,
            a.emittente_soggetto_ruolo_id,
            a.cliente_display,
            a.stadio,
            a.commessa_emittibile,
            a.commessa_stato_codice_interno,
            a.commessa_stato_descrizione,
            a.billing_account_id,
            count(*) AS n_attivita,
            COALESCE(sum(a.valore), (0)::numeric) AS valore,
            min(a.data_attivita) AS data_attivita_min,
            max(a.data_attivita) AS data_attivita_max,
            bool_or(((a.tipo_movimento)::text = 'ONERE'::text)) AS ha_oneri,
            array_agg(DISTINCT a.registro_id) AS registri_ids,
            min((a.registro_codice)::text) AS registro_codice_unico,
            min(a.data_documento_prevista) AS data_prevista_unica
           FROM vendite.vw_dash_competenza_attivita a
          GROUP BY a.competenza_mese, a.gruppo_key, a.sorgente_tipo_id, a.sorgente_uid, a.commessa_id, a.commessa_codice, a.emittente_soggetto_ruolo_id, a.cliente_display, a.stadio, a.commessa_emittibile, a.commessa_stato_codice_interno, a.commessa_stato_descrizione, a.billing_account_id
        )
 SELECT g.competenza_mese,
    g.gruppo_key,
    COALESCE(s.codice_interno, 'ONERI_COMMESSA'::character varying) AS tipo_gruppo,
    s.area AS area_documento,
    COALESCE(doc.codice, g.commessa_codice, g.gruppo_key) AS riferimento,
    g.commessa_id,
    g.commessa_codice,
    g.emittente_soggetto_ruolo_id,
    g.cliente_display,
    g.stadio,
    g.n_attivita,
    g.valore,
    g.data_attivita_min,
    g.data_attivita_max,
    g.ha_oneri,
    g.sorgente_tipo_id,
    g.sorgente_uid,
    g.commessa_emittibile,
    g.commessa_stato_codice_interno,
    g.commessa_stato_descrizione,
    doc.documento_id,
    COALESCE(ba_riga.parent_account_id, ba_riga.id) AS ba_fatturazione_id,
    ba_fatt.codice AS ba_codice_fatturazione,
    sog.ragione_sociale_completa AS cliente_fatturazione_display,
    sog.id_fiscale_univoco_cf_piva AS id_fiscale,
    s_ef.ragione_sociale_completa AS emittente_ragione_sociale,
    g.registri_ids,
    (cardinality(g.registri_ids))::smallint AS registri_n,
        CASE
            WHEN (cardinality(g.registri_ids) = 1) THEN g.registro_codice_unico
            ELSE NULL::text
        END AS registro_codice,
        CASE
            WHEN (cardinality(g.registri_ids) = 1) THEN g.data_prevista_unica
            ELSE NULL::date
        END AS data_documento_prevista
   FROM ((((((((aggregato g
     LEFT JOIN config.sorgenti s ON ((s.id = g.sorgente_tipo_id)))
     LEFT JOIN LATERAL ( SELECT d.codice,
            d.documento_id
           FROM vendite.vw_dash_fatturazione_documenti d
          WHERE ((s.area IS NOT NULL) AND ((d.area)::text = (s.area)::text) AND (d.documento_uid = g.sorgente_uid))
          ORDER BY d.competenza_mese DESC NULLS LAST
         LIMIT 1) doc ON (true))
     LEFT JOIN anagrafiche.billing_account ba_riga ON ((ba_riga.id = g.billing_account_id)))
     LEFT JOIN anagrafiche.billing_account ba_fatt ON ((ba_fatt.id = COALESCE(ba_riga.parent_account_id, ba_riga.id))))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_fatt ON ((sr_fatt.id = ba_fatt.soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti sog ON ((sog.id = sr_fatt.soggetto_id)))
     LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON ((sr_ef.id = g.emittente_soggetto_ruolo_id)))
     LEFT JOIN anagrafiche.soggetti s_ef ON ((s_ef.id = sr_ef.soggetto_id)));
```


---
{% include-markdown "signature-core.md" %}
