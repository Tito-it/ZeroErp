{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_archi.md" %}
# 🔍 View `vw_documento_lineage_archi`

> 📝 **Descrizione**
>
> Lineage documenti vendite (Step 2): grafo archi normalizzato A-H + R e N (rami di ritorno) + S, T e U. TREDICI lettere dal 2026-08-28, e il vocabolario e' CHIUSO: il pgTAP 13 le enumera e fallisce apposta a ogni arco nuovo, per costringere chi lo aggiunge a passare di li'. Chi allarga l'elenco aggiorna ANCHE questa frase e da' all'arco nuovo un rango_origine: e' questa la riga che la doc auto-gen stampa in cima alla pagina, cioe' la prima che legge chi vuole sapere quali archi esistono. Chiave nodo polimorfa (tipo_id, uid::text). Nodo target decorato via vw_documento_lineage_nodi. security_invoker=on. Base di vw_documento_lineage e fn_documento_lineage. ⭐ rev 2026-08-25 — ARCO S: reso -&gt; nota di credito, letto da vendite.resi_righe_accrediti (la tabella nata il 2026-08-18 per registrare il FATTO dell'accredito «contro cosa»), via commessa_attivita_id -&gt; attivita_fatturabili -&gt; fatture_righe. Soft-link calcolato come G e N, nessuna tabella ponte. ⛔ S NON E' UN RAMO DI RITORNO, ed e' una scelta: «inverso» vuol dire ramo di RITORNO, un verso che il grafo forward non percorre; S invece e' l'AVANZAMENTO del reso (la merce e' tornata, adesso si accredita), come H lo e' dell'ordine. La conseguenza voluta e' che il reso smette di essere una foglia e prende la nota come FRONTIERA. ⛔ NON si aggiunge un arco «reso -&gt; fattura ORIGINALE», benche' resi_righe_accrediti.fattura_riga_rettificata_id lo renda banale: sarebbe forward, i due nodi FATTURA finirebbero allo stesso livello e con lo stesso pipeline_rank, e la frontiera del reso si deciderebbe sul confronto lessicografico fra due uid testuali. Il triangolo si chiude gia' via N. ⭐ rev 2026-08-28 — ARCO T: reso -&gt; DDT di RI-CONSEGNA, letto dal ponte vendite.resi_righe_riconsegne. Il grafo aveva R (la merce torna) e S (il valore si accredita) ma non l'arco che dice che la merce e' RIPARTITA: un reso ri-consegnato finiva come una foglia. ⛔ Nemmeno T e' un ramo di ritorno: il ritorno e' gia' avvenuto ed e' R, e da li' il reso ha due modi di andare AVANTI. Si costruisce dal ponte e non da ddt.sorgente_*, quindi copre anche le ri-consegne ORDER-BACKED. ⭐ rev 2026-08-28 — ARCO U: DDT -&gt; Commessa, la QUARTA sorgente di commessa e la gemella di B, E ed F (stessa tabella commesse_sorgenti, stesso ruolo_link, stesso perimetro). Prima le righe DDT_VENDITA di commesse_sorgenti non producevano NESSUN arco, e quelle commesse dichiaravano nel grafo di non avere origine — n_sorgenti = 0, che non e' «non lo so» ma un'affermazione falsa. ⛔ AMMESSA PERCHE' LO DICE CHI SCRIVE, non perche' ci sono righe: le scrive HandlerDdt, un handler REGISTRATO del push (uno di cinque, con PREVENTIVO, ORDINE_VENDITA, CONTRATTO e ATTIVITA_CONSUMI), e ne' il chiamante ne' vendite.fn_link_commessa_sorgente hanno una whitelist di tipi — la funzione legge target_table e key_selector da config.sorgenti per QUALUNQUE sorgente attiva. Il database non ha mai vietato che un DDT sia sorgente di commessa. ⚠️ Il quinto handler, ATTIVITA_CONSUMI, scrive nella stessa tabella ma NON e' un nodo del grafo: per quelle righe non basterebbe un arco, mancherebbe il nodo. Difetto della stessa famiglia, taglia diversa, altro cantiere. ⭐ rev 2026-08-28 — RANGO_ORIGINE: quando piu' archi forward entrano nello STESSO nodo, dichiara quale sorgente e' «l'origine». Scala per quanto e' a monte il documento SORGENTE: 10 trattativa, 20 impegno, 30 esecuzione, 40 consegna, 50 ritorno; piu' basso = piu' origine. ⛔ NON e' «ordinare sul tipo con un altro nome»: prima decideva from_tipo_id, cioe' la PK di config.sorgenti — un id di SEED, per cui la commessa vinceva sul reso solo perche' 13 &lt; 15 e una riseminatura avrebbe cambiato il root di ogni nota di credito in silenzio. Questo numero e' SCRITTO, si legge, non si sposta se il catalogo cambia, e un arco nuovo senza rango vale NULL — che il pgTAP 41 prende. Le due gare vere: FATTURA &lt;- G(30) e S(50), vince la COMMESSA; DDT &lt;- H(20) e T(50), vince l'ORDINE. I pareggi A/D ed E/F sono DELIBERATI (nel primo caso i due archi si escludono per costruzione, nel secondo il modello non ha una preferenza e ruolo_link decide prima) e il tie-break residuo e' from_uid, che e' immutabile: stabile, ma non significativo, ed e' meglio dirlo che fingere una regola che non c'e'. ⛔ REGOLA DI PERIMETRO (rev 2026-08-25): ogni ramo passa dalle TABELLE-TESTATA dei due documenti che collega, perche' sono quelle che portano la RLS. Le tabelle-ponte (commesse_sorgenti, attivita_fatturabili, resi_righe, resi_righe_accrediti, resi_righe_riconsegne, ddt_righe) hanno relrowsecurity = f e non danno perimetro: un ramo che si ferma li' produce un arco verso un documento che il chiamante non vede, e la decorazione non lo ferma perche' i join ai nodi sono LEFT. Fino al 2026-08-24 lo facevano B, E, F e G; U e' il primo ramo a rispettarla per NASCITA. ⚠️ La chiave di commesse_sorgenti.sorgente_uid e' POLIMORFA (key_selector): uid per il preventivo, id::text per ordine, contratto e DDT — i quattro join non si copiano l'uno dall'altro, e si casta l'id a text, mai il testo a uuid. ⭐ is_ramo_inverso E' CALCOLATO QUI, una volta sola: prima la lettera R era ripetuta in tre posti (due WHERE della summary e fn_documento_lineage) e il terzo dimenticato non avrebbe rotto niente di visibile. Espone anche from/to_natura_doc_codice_interno, per distinguere i due nodi FATTURA.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_archi
WITH (security_invoker=on) AS
WITH archi AS (
         SELECT s_from.id AS from_tipo_id,
            (p.uid)::text AS from_uid,
            s_to.id AS to_tipo_id,
            (o.id)::text AS to_uid,
            NULL::character varying AS ruolo,
            'A'::text AS arco
           FROM (((vendite.ordini o
             JOIN vendite.preventivi p ON ((p.id = o.documento_origine_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'PREVENTIVO'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
          WHERE ((o.documento_origine_tipo)::text = 'PREVENTIVO'::text)
        UNION ALL
         SELECT s_from.id,
            (p.uid)::text AS uid,
            s_to.id,
            (cm.id)::text AS id,
            cs.ruolo_link,
            'B'::text AS text
           FROM ((((vendite.commesse_sorgenti cs
             JOIN vendite.preventivi p ON (((p.uid)::text = cs.sorgente_uid)))
             JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
             JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'PREVENTIVO'::text))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT s_from.id,
            (oc.uid)::text AS uid,
            s_to.id,
            (c.id)::text AS id,
            NULL::character varying AS "varchar",
            'C'::text AS text
           FROM (((vendite.contratti c
             JOIN vendite.offerte_commerciali oc ON ((oc.id = c.offerta_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'CONTRATTO'::text) AND (s_to.attivo IS TRUE))))
          WHERE (c.offerta_id IS NOT NULL)
        UNION ALL
         SELECT s_from.id,
            (oc.uid)::text AS uid,
            s_to.id,
            (o.id)::text AS id,
            NULL::character varying AS "varchar",
            'D'::text AS text
           FROM (((vendite.ordini o
             JOIN vendite.offerte_commerciali oc ON ((oc.id = o.documento_origine_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'OFFERTA_COMMERCIALE'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'ORDINE_VENDITA'::text) AND (s_to.attivo IS TRUE))))
          WHERE ((o.documento_origine_tipo)::text = 'OFFERTA'::text)
        UNION ALL
         SELECT s_from.id,
            (o.id)::text AS id,
            s_to.id,
            (cm.id)::text AS id,
            cs.ruolo_link,
            'E'::text AS text
           FROM ((((vendite.commesse_sorgenti cs
             JOIN vendite.ordini o ON (((o.id)::text = cs.sorgente_uid)))
             JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
             JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT s_from.id,
            (c.id)::text AS id,
            s_to.id,
            (cm.id)::text AS id,
            cs.ruolo_link,
            'F'::text AS text
           FROM ((((vendite.commesse_sorgenti cs
             JOIN vendite.contratti c ON (((c.id)::text = cs.sorgente_uid)))
             JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
             JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'CONTRATTO'::text))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT s_from.id,
            (d.id)::text AS id,
            s_to.id,
            (cm.id)::text AS id,
            cs.ruolo_link,
            'U'::text AS text
           FROM ((((vendite.commesse_sorgenti cs
             JOIN vendite.ddt d ON (((d.id)::text = cs.sorgente_uid)))
             JOIN vendite.commesse cm ON ((cm.id = cs.commessa_id)))
             JOIN config.sorgenti s_from ON (((s_from.id = cs.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'COMMESSA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT DISTINCT s_from.id,
            (cm.id)::text AS id,
            s_to.id,
            (f.id)::text AS id,
            NULL::character varying AS "varchar",
            'G'::text AS text
           FROM (((((vendite.attivita_fatturabili af
             JOIN vendite.commesse cm ON ((cm.id = af.commessa_id)))
             JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
             JOIN vendite.fatture f ON ((f.id = fr.fattura_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'COMMESSA'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
          WHERE (af.fattura_riga_id IS NOT NULL)
        UNION ALL
         SELECT s_from.id,
            (o.id)::text AS id,
            s_to.id,
            (d.id)::text AS id,
            NULL::character varying AS "varchar",
            'H'::text AS text
           FROM (((vendite.ddt d
             JOIN config.sorgenti s_from ON (((s_from.id = d.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'ORDINE_VENDITA'::text))))
             JOIN vendite.ordini o ON ((o.uid = d.sorgente_uid)))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT s_from.id,
            (d.id)::text AS id,
            s_to.id,
            (r.id)::text AS id,
            NULL::character varying AS "varchar",
            'R'::text AS text
           FROM (((vendite.resi r
             JOIN config.sorgenti s_from ON (((s_from.id = r.sorgente_tipo_id) AND ((s_from.codice_interno)::text = 'DDT_VENDITA'::text))))
             JOIN vendite.ddt d ON ((d.uid = r.sorgente_uid)))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_to.attivo IS TRUE))))
        UNION ALL
         SELECT DISTINCT s_fat.id,
            (rr.fattura_id)::text AS fattura_id,
            s_fat.id,
            (fr.fattura_id)::text AS fattura_id,
            NULL::character varying AS "varchar",
            'N'::text AS text
           FROM ((vendite.fatture_righe fr
             JOIN vendite.fatture_righe rr ON ((rr.id = fr.riga_rettificata_id)))
             JOIN config.sorgenti s_fat ON ((((s_fat.codice_interno)::text = 'FATTURA'::text) AND (s_fat.attivo IS TRUE))))
          WHERE ((fr.riga_rettificata_id IS NOT NULL) AND (rr.fattura_id <> fr.fattura_id))
        UNION ALL
         SELECT DISTINCT s_from.id,
            (r.id)::text AS id,
            s_to.id,
            (fr.fattura_id)::text AS fattura_id,
            NULL::character varying AS "varchar",
            'S'::text AS text
           FROM ((((((vendite.resi_righe_accrediti acc
             JOIN vendite.resi_righe rr ON ((rr.id = acc.resi_riga_id)))
             JOIN vendite.resi r ON ((r.id = rr.reso_id)))
             JOIN vendite.attivita_fatturabili af ON ((af.commessa_attivita_id = acc.commessa_attivita_id)))
             JOIN vendite.fatture_righe fr ON ((fr.id = af.fattura_riga_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'FATTURA'::text) AND (s_to.attivo IS TRUE))))
          WHERE (af.fattura_riga_id IS NOT NULL)
        UNION ALL
         SELECT DISTINCT s_from.id,
            (r.id)::text AS id,
            s_to.id,
            (d.id)::text AS id,
            NULL::character varying AS "varchar",
            'T'::text AS text
           FROM ((((((vendite.resi_righe_riconsegne rrr
             JOIN vendite.resi_righe rr ON ((rr.id = rrr.resi_riga_id)))
             JOIN vendite.resi r ON ((r.id = rr.reso_id)))
             JOIN vendite.ddt_righe dr ON ((dr.id = rrr.ddt_riga_id)))
             JOIN vendite.ddt d ON ((d.id = dr.ddt_id)))
             JOIN config.sorgenti s_from ON ((((s_from.codice_interno)::text = 'RESO_VENDITA'::text) AND (s_from.attivo IS TRUE))))
             JOIN config.sorgenti s_to ON ((((s_to.codice_interno)::text = 'DDT_VENDITA'::text) AND (s_to.attivo IS TRUE))))
        )
 SELECT a.from_tipo_id,
    a.from_uid,
    nf.codice AS from_codice,
    a.to_tipo_id,
    a.to_uid,
    nt.codice AS to_codice,
    nt.stato_codice_interno AS to_stato_codice_interno,
    nt.fase AS to_fase,
    nt.is_abortito AS to_is_abortito,
    a.ruolo,
    a.arco,
    (a.arco = ANY (ARRAY['R'::text, 'N'::text])) AS is_ramo_inverso,
    nf.natura_doc_codice_interno AS from_natura_doc_codice_interno,
    nt.natura_doc_codice_interno AS to_natura_doc_codice_interno,
    (
        CASE a.arco
            WHEN 'A'::text THEN 10
            WHEN 'B'::text THEN 10
            WHEN 'C'::text THEN 10
            WHEN 'D'::text THEN 10
            WHEN 'E'::text THEN 20
            WHEN 'F'::text THEN 20
            WHEN 'H'::text THEN 20
            WHEN 'G'::text THEN 30
            WHEN 'U'::text THEN 40
            WHEN 'R'::text THEN 40
            WHEN 'S'::text THEN 50
            WHEN 'T'::text THEN 50
            WHEN 'N'::text THEN 50
            ELSE NULL::integer
        END)::smallint AS rango_origine
   FROM ((archi a
     LEFT JOIN vendite.vw_documento_lineage_nodi nf ON (((nf.tipo_id = a.from_tipo_id) AND (nf.uid = a.from_uid))))
     LEFT JOIN vendite.vw_documento_lineage_nodi nt ON (((nt.tipo_id = a.to_tipo_id) AND (nt.uid = a.to_uid))));
```


---
{% include-markdown "signature-core.md" %}
