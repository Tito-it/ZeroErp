{% include-markdown "it/dbzero/vendite/manual/vw_documento_lineage_archi.md" %}
# 🔍 View `vw_documento_lineage_archi`

> 📝 **Descrizione**
>
> ⭐ rev 2026-10-11 (brief-db-lineage-seminata-per-chiave, giro 1): la vista e' la PROIEZIONE di vendite.fn_documento_lineage_archi(NULL, NULL), un corpo solo; chi vuole una parte del grafo chiama la funzione col seme. Stesse colonne, stessi tipi. Lineage documenti vendite (Step 2): grafo archi normalizzato A-H + R e N (rami di ritorno) + S, T e U. TREDICI lettere dal 2026-08-28, e il vocabolario e' CHIUSO: il pgTAP 13 le enumera e fallisce apposta a ogni arco nuovo, per costringere chi lo aggiunge a passare di li'. Chi allarga l'elenco aggiorna ANCHE questa frase e da' all'arco nuovo un rango_origine: e' questa la riga che la doc auto-gen stampa in cima alla pagina, cioe' la prima che legge chi vuole sapere quali archi esistono. Chiave nodo polimorfa (tipo_id, uid::text). Nodo target decorato via vw_documento_lineage_nodi. security_invoker=on. Base di vw_documento_lineage e fn_documento_lineage. ⭐ rev 2026-08-25 — ARCO S: reso -&gt; nota di credito, letto da vendite.resi_righe_accrediti (la tabella nata il 2026-08-18 per registrare il FATTO dell'accredito «contro cosa»), via commessa_attivita_id -&gt; attivita_fatturabili -&gt; fatture_righe. Soft-link calcolato come G e N, nessuna tabella ponte. ⛔ S NON E' UN RAMO DI RITORNO, ed e' una scelta: «inverso» vuol dire ramo di RITORNO, un verso che il grafo forward non percorre; S invece e' l'AVANZAMENTO del reso (la merce e' tornata, adesso si accredita), come H lo e' dell'ordine. La conseguenza voluta e' che il reso smette di essere una foglia e prende la nota come FRONTIERA. ⛔ NON si aggiunge un arco «reso -&gt; fattura ORIGINALE», benche' resi_righe_accrediti.fattura_riga_rettificata_id lo renda banale: sarebbe forward, i due nodi FATTURA finirebbero allo stesso livello e con lo stesso pipeline_rank, e la frontiera del reso si deciderebbe sul confronto lessicografico fra due uid testuali. Il triangolo si chiude gia' via N. ⭐ rev 2026-08-28 — ARCO T: reso -&gt; DDT di RI-CONSEGNA, letto dal ponte vendite.resi_righe_riconsegne. Il grafo aveva R (la merce torna) e S (il valore si accredita) ma non l'arco che dice che la merce e' RIPARTITA: un reso ri-consegnato finiva come una foglia. ⛔ Nemmeno T e' un ramo di ritorno: il ritorno e' gia' avvenuto ed e' R, e da li' il reso ha due modi di andare AVANTI. Si costruisce dal ponte e non da ddt.sorgente_*, quindi copre anche le ri-consegne ORDER-BACKED. ⭐ rev 2026-08-28 — ARCO U: DDT -&gt; Commessa, la QUARTA sorgente di commessa e la gemella di B, E ed F (stessa tabella commesse_sorgenti, stesso ruolo_link, stesso perimetro). Prima le righe DDT_VENDITA di commesse_sorgenti non producevano NESSUN arco, e quelle commesse dichiaravano nel grafo di non avere origine — n_sorgenti = 0, che non e' «non lo so» ma un'affermazione falsa. ⛔ AMMESSA PERCHE' LO DICE CHI SCRIVE, non perche' ci sono righe: le scrive HandlerDdt, un handler REGISTRATO del push (uno di cinque, con PREVENTIVO, ORDINE_VENDITA, CONTRATTO e ATTIVITA_CONSUMI), e ne' il chiamante ne' vendite.fn_link_commessa_sorgente hanno una whitelist di tipi — la funzione legge target_table e key_selector da config.sorgenti per QUALUNQUE sorgente attiva. Il database non ha mai vietato che un DDT sia sorgente di commessa. ⚠️ Il quinto handler, ATTIVITA_CONSUMI, scrive nella stessa tabella ma NON e' un nodo del grafo: per quelle righe non basterebbe un arco, mancherebbe il nodo. Difetto della stessa famiglia, taglia diversa, altro cantiere. ⭐ rev 2026-08-28 — RANGO_ORIGINE: quando piu' archi forward entrano nello STESSO nodo, dichiara quale sorgente e' «l'origine». Scala per quanto e' a monte il documento SORGENTE: 10 trattativa, 20 impegno, 30 esecuzione, 40 consegna, 50 ritorno; piu' basso = piu' origine. ⛔ NON e' «ordinare sul tipo con un altro nome»: prima decideva from_tipo_id, cioe' la PK di config.sorgenti — un id di SEED, per cui la commessa vinceva sul reso solo perche' 13 &lt; 15 e una riseminatura avrebbe cambiato il root di ogni nota di credito in silenzio. Questo numero e' SCRITTO, si legge, non si sposta se il catalogo cambia, e un arco nuovo senza rango vale NULL — che il pgTAP 41 prende. Le due gare vere: FATTURA &lt;- G(30) e S(50), vince la COMMESSA; DDT &lt;- H(20) e T(50), vince l'ORDINE. I pareggi A/D ed E/F sono DELIBERATI (nel primo caso i due archi si escludono per costruzione, nel secondo il modello non ha una preferenza e ruolo_link decide prima) e il tie-break residuo e' from_uid, che e' immutabile: stabile, ma non significativo, ed e' meglio dirlo che fingere una regola che non c'e'. ⛔ REGOLA DI PERIMETRO (rev 2026-08-25): ogni ramo passa dalle TABELLE-TESTATA dei due documenti che collega, perche' sono quelle che portano la RLS. Le tabelle-ponte (commesse_sorgenti, attivita_fatturabili, resi_righe, resi_righe_accrediti, resi_righe_riconsegne, ddt_righe) hanno relrowsecurity = f e non danno perimetro: un ramo che si ferma li' produce un arco verso un documento che il chiamante non vede, e la decorazione non lo ferma perche' i join ai nodi sono LEFT. Fino al 2026-08-24 lo facevano B, E, F e G; U e' il primo ramo a rispettarla per NASCITA. ⚠️ La chiave di commesse_sorgenti.sorgente_uid e' POLIMORFA (key_selector): uid per il preventivo, id::text per ordine, contratto e DDT — i quattro join non si copiano l'uno dall'altro, e si casta l'id a text, mai il testo a uuid. ⭐ is_ramo_inverso E' CALCOLATO QUI, una volta sola: prima la lettera R era ripetuta in tre posti (due WHERE della summary e fn_documento_lineage) e il terzo dimenticato non avrebbe rotto niente di visibile. Espone anche from/to_natura_doc_codice_interno, per distinguere i due nodi FATTURA. ⭐ rev 2026-10-05 (20261005-21, brief-db-liste-documento-lineage-lenta, passo 2) — TRE LETTURE UNA VOLTA SOLA. Le chiavi testuali di preventivi (ramo B) e ordini (ramo E) e i nodi (nf, nt) si leggono una volta, in CTE MATERIALIZED: sotto RLS il planner rileggeva l'intera tabella per ogni riga di commesse_sorgenti (la chiave e' un'espressione e non usa l'indice) e calcolava i nodi due volte. La regola di perimetro resta intera: le CTE leggono le tabelle-testata sotto la loro RLS, e il cast va dall'id al testo. Misurato come zeroerp_app su dbdev il 2026-10-05: la vista intera 380 -&gt; 90 ms, gli archi di un documento 457 -&gt; 143 ms, la pagina della lista preventivi 0,45 -&gt; 0,17 s; righe identiche (EXCEPT ALL nei due versi su questa vista e su vw_documento_lineage).

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_documento_lineage_archi
WITH (security_invoker=on) AS
WITH nodi AS MATERIALIZED (
         SELECT n.tipo_id,
            n.uid,
            n.codice,
            n.stato_codice_interno,
            n.fase,
            n.is_abortito,
            n.natura_doc_codice_interno
           FROM vendite.vw_documento_lineage_nodi n
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
    a.is_ramo_inverso,
    nf.natura_doc_codice_interno AS from_natura_doc_codice_interno,
    nt.natura_doc_codice_interno AS to_natura_doc_codice_interno,
    a.rango_origine
   FROM ((vendite.fn_documento_lineage_archi(NULL::bigint[], NULL::text[]) a(from_tipo_id, from_uid, to_tipo_id, to_uid, ruolo, arco, is_ramo_inverso, rango_origine)
     LEFT JOIN nodi nf ON (((nf.tipo_id = a.from_tipo_id) AND (nf.uid = a.from_uid))))
     LEFT JOIN nodi nt ON (((nt.tipo_id = a.to_tipo_id) AND (nt.uid = a.to_uid))));
```

</div>


---
{% include-markdown "signature-core.md" %}
