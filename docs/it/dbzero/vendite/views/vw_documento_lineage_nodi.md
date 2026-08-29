{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_nodi.md" %}
# 🔍 View `vw_documento_lineage_nodi`

> 📝 **Descrizione**
>
> Lineage documenti vendite: dimensione nodo condivisa (una riga per documento nodo, chiave polimorfa tipo_id+uid::text per key_selector, stato/fase/is_abortito normalizzati, pipeline_rank per il tie-break frontiera). Base di vw_documento_lineage_archi, vw_documento_lineage e fn_documento_lineage. security_invoker=on. ⭐ rev 2026-08-29 — il `codice` del nodo FATTURA e' il NUMERO DOCUMENTO, non piu' il contatore nudo: lo compone la sede unica vendite.fn_numero_documento_fattura («numero - serie», senza anno). Prima usciva «1», che non e' sbagliato ma e' AMBIGUO — nello stesso anno possono esistere una fattura 1 e una nota di credito 1, e in lista erano indistinguibili. Per gli altri sei rami `numero` E' gia' il numero parlante (DDT0000031); per la fattura e' un bigint e l'identita' sta in tre colonne nullable. ⚠️ La funzione e' IMMUTABLE e prende i valori, quindi e' inlineata qui: non e' una lettura per riga. ⭐ rev 2026-08-20: il nodo porta anche natura_doc_codice_interno/natura_doc_descrizione (da config.nature_doc_fiscale.codice_interno/descrizione). Serve perche' il grafo e' nato quando FATTURA era una cosa sola: due nodi FATTURA della stessa commessa — la fattura e la nota di credito che la rettifica — erano indistinguibili, stesso tipo e stesso stato, con `codice` NULL finche' non numerati. La natura e' un ASSE DIVERSO dal tipo documento (il tipo dice da quale tabella viene il nodo, la natura che cosa e' fiscalmente) ed esiste solo per le fatture: negli altri sette rami e' NULL, ed e' corretto. LEFT JOIN sulla natura perche' natura_doc_id e' nullable: con un JOIN una fattura senza natura sparirebbe dal grafo.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_nodi
WITH (security_invoker=on) AS
SELECT s.id AS tipo_id,
    (p.uid)::text AS uid,
    p.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (1)::smallint AS pipeline_rank,
    NULL::character varying AS natura_doc_codice_interno,
    NULL::character varying AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM ((vendite.preventivi p
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_preventivi st ON ((st.id = p.stato_doc_preventivo_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (oc.uid)::text AS uid,
    oc.codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (1)::smallint AS pipeline_rank,
    NULL::character varying AS natura_doc_codice_interno,
    NULL::character varying AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM ((vendite.offerte_commerciali oc
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_offerte st ON ((st.id = oc.stato_doc_offerta_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (o.id)::text AS uid,
    o.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (2)::smallint AS pipeline_rank,
    NULL::character varying AS natura_doc_codice_interno,
    NULL::character varying AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM ((vendite.ordini o
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_ordini st ON ((st.id = o.stato_doc_ordine_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (c.id)::text AS uid,
    c.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (2)::smallint AS pipeline_rank,
    NULL::character varying AS natura_doc_codice_interno,
    NULL::character varying AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM ((vendite.contratti c
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'CONTRATTO'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_contratti st ON ((st.id = c.stato_doc_contratto_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (d.id)::text AS uid,
    d.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (3)::smallint AS pipeline_rank,
    NULL::character varying AS natura_doc_codice_interno,
    NULL::character varying AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM ((vendite.ddt d
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'DDT_VENDITA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_ddt st ON ((st.id = d.stato_doc_ddt_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (f.id)::text AS uid,
    (vendite.fn_numero_documento_fattura(f.numero, f.serie))::text AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (5)::smallint AS pipeline_rank,
    nd.codice_interno AS natura_doc_codice_interno,
    nd.descrizione AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM (((vendite.fatture f
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'FATTURA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_fiscale st ON ((st.id = f.stato_doc_fiscale_id)))
     LEFT JOIN config.nature_doc_fiscale nd ON ((nd.id = f.natura_doc_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (cm.id)::text AS uid,
    cm.codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (4)::smallint AS pipeline_rank,
    NULL::character varying AS natura_doc_codice_interno,
    NULL::character varying AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM ((vendite.commesse cm
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'COMMESSA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN vendite.stati_commessa st ON ((st.id = cm.stato_commessa_id)))
UNION ALL
 SELECT s.id AS tipo_id,
    (r.id)::text AS uid,
    r.numero AS codice,
    st.codice_interno AS stato_codice_interno,
    st.codice AS stato_codice,
    st.descrizione AS stato_descrizione,
    st.fase,
    st.is_abortito,
    (0)::smallint AS pipeline_rank,
    NULL::character varying AS natura_doc_codice_interno,
    NULL::character varying AS natura_doc_descrizione,
    s.codice_interno AS tipo_codice_interno
   FROM ((vendite.resi r
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'RESO_VENDITA'::text) AND (s.attivo IS TRUE))))
     LEFT JOIN config.stati_doc_reso st ON ((st.id = r.stato_doc_reso_id)));
```


---
{% include-markdown "signature-core.md" %}
