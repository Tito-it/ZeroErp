{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage.md" %}
# 🔍 View `vw_documento_lineage`

> 📝 **Descrizione**
>
> Lineage documenti vendite (Step 3): summary per nodo per arricchire le liste. Espone pratica (1:1 difensiva + n_pratiche), fase propria, frontiera forward (piu' a valle attivo, esclude i rami di RITORNO), discendenti diretti/attivi, is_transitato, lato inverso (n_sorgenti + ROOT), natura del documento e natura del documento di frontiera. security_invoker=on. ⭐ rev 2026-08-20 — DUE COSE. (1) i due filtri del grafo forward non nominano piu' la lettera R ma leggono vw_documento_lineage_archi.is_ramo_inverso: con l'arrivo dell'arco N (fattura rettificata -&gt; nota di credito) la lettera era scritta a mano in TRE posti, e il terzo dimenticato non avrebbe dato nessun errore — solo la nota di credito come discendente forward, cioe' una FRONTIERA diversa su ogni riga di lista. (2) espone natura_doc_codice_interno/natura_doc_descrizione del nodo, cosi' una lista di fatture smette di scrivere «Fattura» sopra una nota di credito. ⭐ rev 2026-08-28 — E ADESSO ANCHE frontiera_natura_doc_codice_interno, che e' la TERZA versione di questa frase perche' le prime due erano vere a meta'. Il 20260821-03 diceva «varrebbe sempre NULL»: falso, l'arco G (commessa -&gt; fattura) non e' un ramo di ritorno e una nota di credito E' raggiungibile in avanti. Il 20260825-20 ha corretto in «il consumatore la ricava per conto suo»: vero per UNO — il pannello del drawer, che legge questa vista e ha frontiera_uid — e falso per tutti gli altri, perche' le viste di LISTA proiettano frontiera_tipo_id/codice/stato/fase e la CHIAVE del nodo di frontiera si ferma li'. Senza quella chiave non c'e' modo onesto di leggere la natura, e ogni lista chiama «Fattura» una nota di credito: sulla lista resi non e' nemmeno un caso limite, e' IL caso, perche' l'arco S arriva sempre a una nota di credito (pgTAP 35). La ragione della colonna, al positivo: la chiave del nodo di frontiera non esce dalla summary, e senza la natura ogni lista dice la parola sbagliata proprio nel punto per cui la colonna «Transito» e' stata seminata. ⭐ Costa una colonna e non un join: la CTE frontiera fa gia' LEFT JOIN su vw_documento_lineage_nodi per il pipeline_rank del tie-break. ⚠️ Sta in ULTIMA posizione e non accanto alle sorelle frontiera_* perche' CREATE OR REPLACE VIEW puo' solo appendere colonne: metterla in mezzo richiederebbe un DROP CASCADE delle viste di lista che leggono questa. ⛔ NULL non significa «non lo so» ma «la frontiera non e' un documento fiscale»: la natura e' un asse diverso dal tipo ed esiste solo per le fatture. Si espone il solo CODICE e non la descrizione: il consumatore traduce dal codice, le chiavi i18n esistono gia'. ⭐ rev 2026-08-28 — IL ROOT NON DIPENDE PIU' DA UN ID DI SEED. La CTE inc ordinava ORDER BY (ruolo='ROOT') DESC NULLS LAST, from_tipo_id, from_uid: ogni volta che nessuna sorgente portava un ruolo — cioe' per ogni nota di credito, che ha la commessa via G e il reso via S, tutti e due con ruolo NULL — a decidere restava from_tipo_id, la PK di config.sorgenti. La commessa vinceva solo perche' 13 &lt; 15, e una riseminatura del catalogo avrebbe cambiato il root di OGNI nota di credito senza un errore e senza un log. Ora il secondo criterio e' rango_origine, DICHIARATO sull'arco in vw_documento_lineage_archi — stessa sede e stessa forma di is_ramo_inverso. L'ordine dei tre criteri E' la regola: (1) ruolo='ROOT' prima di tutto, perche' una tabella ponte che ha dichiarato l'origine batte qualunque scala; (2) rango_origine, fra archi senza ruolo; (3) from_uid, tie-break residuo dove il modello non ha una preferenza — immutabile, quindi stabile, ma non significativo. ⛔ I tre array_agg devono avere sempre lo STESSO ORDER BY: sono tre pezzi della stessa riga, e uno che divergesse comporrebbe un root inesistente a pezzi, in silenzio. ⭐ rev 2026-10-05 (20261005-20, brief-db-liste-documento-lineage-lenta) — LA LINEAGE SI CALCOLA UNA VOLTA PER QUERY. Gli archi si leggono una volta (CTE archi, prima li leggevano fwd e inc ciascuno: ~360 ms l'una come applicazione), ogni CTE e il risultato finale sono MATERIALIZED. Senza recinto, le sette viste di lista che fanno LEFT JOIN su questa vista per (tipo, uid) finivano sotto RLS in un nested loop che rieseguiva il calcolo per ogni riga della lista (preventivi 168 righe: loops=168, 3,1 s il conteggio e 2,9 s la pagina). Misurato come zeroerp_app su dbdev il 2026-10-05: lista preventivi 3,1+2,9 s -&gt; 0,44+0,45 s, le altre sei liste ~1 s -&gt; ~0,44 s, la lineage di un documento 0,75 -&gt; 0,43 s; righe identiche (EXCEPT ALL nei due versi, sulla vista intera e sulle liste). ⚠️ Recintare le sole CTE intermedie non basta: la SELECT finale sui nodi diventa lei la parte rieseguita per riga (provato: 5,5 s). Il prezzo dichiarato: chi legge UN documento paga la lineage di tutti quelli che vede, come gia' oggi per le CTE ricorsive; resta piu' veloce di prima perche' gli archi si leggono una volta.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage
WITH (security_invoker=on) AS
WITH RECURSIVE archi AS MATERIALIZED (
         SELECT vw_documento_lineage_archi.from_tipo_id,
            vw_documento_lineage_archi.from_uid,
            vw_documento_lineage_archi.from_codice,
            vw_documento_lineage_archi.to_tipo_id,
            vw_documento_lineage_archi.to_uid,
            vw_documento_lineage_archi.to_codice,
            vw_documento_lineage_archi.to_stato_codice_interno,
            vw_documento_lineage_archi.to_fase,
            vw_documento_lineage_archi.to_is_abortito,
            vw_documento_lineage_archi.ruolo,
            vw_documento_lineage_archi.arco,
            vw_documento_lineage_archi.is_ramo_inverso,
            vw_documento_lineage_archi.from_natura_doc_codice_interno,
            vw_documento_lineage_archi.to_natura_doc_codice_interno,
            vw_documento_lineage_archi.rango_origine
           FROM vendite.vw_documento_lineage_archi
        ), fwd AS MATERIALIZED (
         SELECT archi.from_tipo_id,
            archi.from_uid,
            archi.to_tipo_id,
            archi.to_uid,
            archi.to_codice,
            archi.to_stato_codice_interno,
            archi.to_fase,
            archi.to_is_abortito,
            archi.ruolo
           FROM archi
          WHERE (NOT archi.is_ramo_inverso)
        ), walk AS MATERIALIZED (
         SELECT f.from_tipo_id AS o_tipo,
            f.from_uid AS o_uid,
            f.to_tipo_id AS d_tipo,
            f.to_uid AS d_uid,
            f.to_codice AS d_codice,
            f.to_stato_codice_interno AS d_stato,
            f.to_fase AS d_fase,
            f.to_is_abortito AS d_abortito,
            1 AS lvl,
            ARRAY[(((f.from_tipo_id)::text || ':'::text) || f.from_uid), (((f.to_tipo_id)::text || ':'::text) || f.to_uid)] AS visited
           FROM fwd f
        UNION ALL
         SELECT w.o_tipo,
            w.o_uid,
            f.to_tipo_id,
            f.to_uid,
            f.to_codice,
            f.to_stato_codice_interno,
            f.to_fase,
            f.to_is_abortito,
            (w.lvl + 1),
            (w.visited || (((f.to_tipo_id)::text || ':'::text) || f.to_uid))
           FROM (walk w
             JOIN fwd f ON (((f.from_tipo_id = w.d_tipo) AND (f.from_uid = w.d_uid))))
          WHERE ((w.lvl < 10) AND (NOT ((((f.to_tipo_id)::text || ':'::text) || f.to_uid) = ANY (w.visited))))
        ), cand AS MATERIALIZED (
         SELECT n.tipo_id AS o_tipo,
            n.uid AS o_uid,
            n.tipo_id AS d_tipo,
            n.uid AS d_uid,
            n.codice AS d_codice,
            n.stato_codice_interno AS d_stato,
            n.fase AS d_fase,
            n.is_abortito AS d_abortito,
            0 AS lvl
           FROM vendite.vw_documento_lineage_nodi n
        UNION ALL
         SELECT walk.o_tipo,
            walk.o_uid,
            walk.d_tipo,
            walk.d_uid,
            walk.d_codice,
            walk.d_stato,
            walk.d_fase,
            walk.d_abortito,
            walk.lvl
           FROM walk
        ), frontiera AS MATERIALIZED (
         SELECT c.o_tipo,
            c.o_uid,
            c.d_tipo,
            c.d_uid,
            c.d_codice,
            c.d_stato,
            c.d_fase,
            nd.natura_doc_codice_interno AS d_natura_doc_codice_interno,
            nd.tipo_codice_interno AS d_tipo_codice_interno,
            row_number() OVER (PARTITION BY c.o_tipo, c.o_uid ORDER BY
                CASE
                    WHEN (((c.d_fase)::text <> 'CHIUSO'::text) AND (NOT COALESCE(c.d_abortito, false))) THEN 0
                    ELSE 1
                END, c.lvl DESC, COALESCE((nd.pipeline_rank)::integer, 0) DESC, c.d_tipo, c.d_uid) AS rn
           FROM (cand c
             LEFT JOIN vendite.vw_documento_lineage_nodi nd ON (((nd.tipo_id = c.d_tipo) AND (nd.uid = c.d_uid))))
        ), disc AS MATERIALIZED (
         SELECT walk.o_tipo,
            walk.o_uid,
            count(DISTINCT (((walk.d_tipo)::text || ':'::text) || walk.d_uid)) AS n_diretti,
            count(DISTINCT (((walk.d_tipo)::text || ':'::text) || walk.d_uid)) FILTER (WHERE (((walk.d_fase)::text <> 'CHIUSO'::text) AND (NOT COALESCE(walk.d_abortito, false)))) AS n_attivi
           FROM walk
          WHERE (walk.lvl = 1)
          GROUP BY walk.o_tipo, walk.o_uid
        ), inc AS MATERIALIZED (
         SELECT archi.to_tipo_id AS tipo,
            archi.to_uid AS uid,
            count(*) AS n_sorgenti,
            (array_agg(archi.from_tipo_id ORDER BY ((archi.ruolo)::text = 'ROOT'::text) DESC NULLS LAST, archi.rango_origine, archi.from_uid))[1] AS root_tipo,
            (array_agg(archi.from_uid ORDER BY ((archi.ruolo)::text = 'ROOT'::text) DESC NULLS LAST, archi.rango_origine, archi.from_uid))[1] AS root_uid,
            (array_agg(archi.from_codice ORDER BY ((archi.ruolo)::text = 'ROOT'::text) DESC NULLS LAST, archi.rango_origine, archi.from_uid))[1] AS root_codice
           FROM archi
          WHERE (NOT archi.is_ramo_inverso)
          GROUP BY archi.to_tipo_id, archi.to_uid
        ), prat AS MATERIALIZED (
         SELECT ps.sorgente_tipo_id AS tipo,
            ps.sorgente_uid AS uid,
            count(DISTINCT ps.pratica_id) AS n_pratiche,
            (array_agg(p.id ORDER BY p.id))[1] AS pratica_id,
            (array_agg(p.codice ORDER BY p.id))[1] AS pratica_numero
           FROM (pratiche.pratiche_sorgenti ps
             JOIN pratiche.pratiche p ON ((p.id = ps.pratica_id)))
          GROUP BY ps.sorgente_tipo_id, ps.sorgente_uid
        ), lineage AS MATERIALIZED (
         SELECT n.tipo_id,
            n.uid,
            n.codice,
            n.stato_codice_interno,
            n.stato_codice,
            n.stato_descrizione,
            n.fase,
            n.is_abortito,
            pr.pratica_id,
            pr.pratica_numero,
            COALESCE(pr.n_pratiche, (0)::bigint) AS n_pratiche,
            fr.d_tipo AS frontiera_tipo_id,
            fr.d_uid AS frontiera_uid,
            fr.d_codice AS frontiera_codice,
            fr.d_stato AS frontiera_stato_codice_interno,
            fr.d_fase AS frontiera_fase,
            COALESCE(dc.n_diretti, (0)::bigint) AS n_discendenti_diretti,
            COALESCE(dc.n_attivi, (0)::bigint) AS n_discendenti_attivi,
            (COALESCE(dc.n_diretti, (0)::bigint) > 0) AS is_transitato,
            COALESCE(ic.n_sorgenti, (0)::bigint) AS n_sorgenti,
            ic.root_tipo AS root_tipo_id,
            ic.root_uid,
            ic.root_codice,
            n.natura_doc_codice_interno,
            n.natura_doc_descrizione,
            fr.d_natura_doc_codice_interno AS frontiera_natura_doc_codice_interno,
            n.tipo_codice_interno,
            fr.d_tipo_codice_interno AS frontiera_tipo_codice_interno
           FROM ((((vendite.vw_documento_lineage_nodi n
             LEFT JOIN prat pr ON (((pr.tipo = n.tipo_id) AND (pr.uid = n.uid))))
             LEFT JOIN frontiera fr ON (((fr.o_tipo = n.tipo_id) AND (fr.o_uid = n.uid) AND (fr.rn = 1))))
             LEFT JOIN disc dc ON (((dc.o_tipo = n.tipo_id) AND (dc.o_uid = n.uid))))
             LEFT JOIN inc ic ON (((ic.tipo = n.tipo_id) AND (ic.uid = n.uid))))
        )
 SELECT tipo_id,
    uid,
    codice,
    stato_codice_interno,
    stato_codice,
    stato_descrizione,
    fase,
    is_abortito,
    pratica_id,
    pratica_numero,
    n_pratiche,
    frontiera_tipo_id,
    frontiera_uid,
    frontiera_codice,
    frontiera_stato_codice_interno,
    frontiera_fase,
    n_discendenti_diretti,
    n_discendenti_attivi,
    is_transitato,
    n_sorgenti,
    root_tipo_id,
    root_uid,
    root_codice,
    natura_doc_codice_interno,
    natura_doc_descrizione,
    frontiera_natura_doc_codice_interno,
    tipo_codice_interno,
    frontiera_tipo_codice_interno
   FROM lineage;
```


---
{% include-markdown "signature-core.md" %}
