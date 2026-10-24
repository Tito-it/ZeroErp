## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage`

> 👀 **Vedi anche**
>
> Approfondimento:
>
> [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi)
> [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) (era `vw_documento_lineage`, ritirata nel giro B)
> [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi)

---

### 🎯 Scopo Principale

`vendite.fn_documento_lineage(p_tipo_id, p_uid, p_direzione)` è il **traversal ricorsivo**
del grafo di genealogia, pensato per il pannello **"Passaggi"** del dettaglio documento:
ritorna la **catena completa** degli archi attraversati, con lo stato di ogni tappa e
`livello`/`ordine` per il rendering a timeline/albero.

Sorgente unica: `vendite.vw_documento_lineage_archi` (tutti gli archi, incluso R).

---

### 📥 Input

| Parametro | Tipo | Significato |
|---|---|---|
| `p_tipo_id` | `bigint` | `config.sorgenti.id` del nodo di partenza (guard: NOT NULL, `> 0`) |
| `p_uid` | `text` | chiave nodo (secondo `key_selector`; guard: NOT NULL / non vuoto) |
| `p_direzione` | `text` | `avanti` (documento → destinazioni) o `indietro` (nodo → sorgenti); default `avanti` (guard: solo questi due valori) |

I guard sui parametri usano `script.fn_log_and_raise_error` con codice registrato
`ERRORE_PARAMETRI`.

---

### 📤 Output (`RETURNS TABLE`, una riga per arco)

* `livello` — profondità dal nodo di partenza (1 = adiacente)
* `ordine` — sequenza stabile per il rendering
* `arco`, `ruolo` — tipo di relazione (`A`..`H`/`R`) e ruolo `ROOT`/`COLLEGATO`
* `from_*`, `to_*` — estremi dell'arco + `to_stato_codice_interno`/`to_fase`/`to_is_abortito`
* `is_ramo_inverso` — `true` per l'arco **R** (DDT→Reso): il reso compare nei "Passaggi"
  come **ramo di ritorno**; il FE lo rende in modo distinto. La frontiera forward della
  summary lo esclude già.
* `is_legame_ritirato` — (rev 2026-10-13) il **legame** dell'arco, non il nodo:
  `true` quando quello che il documento ha portato dall'altra parte non c'è più,
  anche se i due documenti sono vivi. Vedi
  [`fn_documento_lineage_legami`](fn_documento_lineage_legami.md).

---

### Esempio d'uso

```sql
-- AVANTI: da un preventivo alle sue destinazioni.
SELECT livello, ordine, arco, from_codice, to_codice, to_fase, is_ramo_inverso
FROM vendite.fn_documento_lineage(
     (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO'),
     (SELECT uid::text FROM vendite.preventivi WHERE numero = 'PRV0000185'),
     'avanti')
ORDER BY ordine;

-- INDIETRO: da una commessa alle sue sorgenti (ROOT + COLLEGATO).
SELECT livello, arco, from_codice, to_codice, ruolo
FROM vendite.fn_documento_lineage(
     (SELECT id FROM config.sorgenti WHERE codice_interno = 'COMMESSA'),
     '186', 'indietro')
ORDER BY ordine;
```

---

### Note operative

* **`STABLE` · `SECURITY INVOKER`**: sola lettura; gira come il chiamante → la RLS
  emittente delle viste `security_invoker=on` resta applicata.
* **Cycle guard**: il traversal traccia i nodi visitati sul percorso e limita a
  `livello < 10` (le catene reali sono ≤ ~5 hop).
* **Direzioni**: `avanti` per le liste dei documenti, `indietro` per la lista commesse
  (genealogia inversa, G-11).
* Test: `db/pgtap/vendite/test-documento-lineage-v1.sql`.

---


### ⭐ Le due colonne nuove, e una conseguenza a video (rev 2026-08-21)

Il traversal espone anche `from_natura_doc_codice_interno` /
`to_natura_doc_codice_interno`: sono
ciò che, nel pannello «Passaggi», distingue la fattura dalla nota di credito che
la rettifica — due nodi che senza la natura hanno stesso tipo, stesso stato e
`codice` NULL finché non sono numerati.

`is_ramo_inverso` **non è più ricalcolato qui** come `arco = 'R'`: arriva da
`vw_documento_lineage_archi`, che è l'unica sede dell'elenco dei rami di ritorno.
Sull'arco N vale `true`, quindi il FE lo rende già in modo distinto senza sapere
nulla di note di credito.

⚠️ **Una conseguenza da sapere, per chi rende a video.** Camminando in avanti da
una **commessa**, la nota di credito compare **due volte**: una come figlia
diretta (arco G, dalla commessa) e una a livello 2 (arco N, dalla fattura che
rettifica). Non è un difetto — sono due relazioni diverse verso lo stesso
documento, e questa funzione ritorna **archi**, non nodi.

⛔ La revisione è un **DROP + CREATE** (la `RETURNS TABLE` cambia, e PostgreSQL
non lo consente in place). Il DROP porta via i GRANT: sono ri-concessi a
`zeroerp_app` nello stesso changeSet, altrimenti il pannello e i pgTAP
prenderebbero «permesso negato» fino alla passata serale di `ci_apply`.

---

### 🔄 rev 2026-10-10 — il grafo si legge una volta

Il pannello «Passaggi» impiegava più di mezzo secondo a ogni apertura (~0,6-0,8 s,
misurato come applicazione il 2026-10-10), anche per un documento senza
collegamenti. La vista degli archi costruisce **l'intero grafo** dei documenti,
già decorato con stato e natura di ogni nodo, e la funzione la ricostruiva più
volte: al primo passo e a ogni livello della risalita.

Da `20261010-44` la funzione legge la vista **una volta** e risale su quella
copia: ~0,18 s a chiamata, con le stesse righe di prima su tutti i casi del
grafo. Il costo che resta è quello di costruire il grafo intero; scendere ai
millisecondi vorrebbe dire costruire solo i collegamenti del documento chiesto,
ed è un lavoro a parte. Dettaglio:
`brief-db-plancache-funzioni-con-query-incorporate` §5.

---

---

### 🔄 rev 2026-10-11 — la catena si risale un livello alla volta

Changeset `20261011-93`. Il pannello non legge più l'intero grafo: parte dal
documento, chiede a [`fn_documento_lineage_archi`](fn_documento_lineage_archi.md)
i passaggi dei soli documenti raggiunti, livello per livello, e alla fine legge i
dettagli dei soli documenti toccati da
[`fn_documento_lineage_nodi`](fn_documento_lineage_nodi.md). Il risultato è lo
stesso di prima, riga per riga; il costo segue la lunghezza della catena e non il
numero dei documenti del sistema (su dbdev, 2026-10-11: ~154 → ~16 ms).

### 🔄 rev 2026-10-13 — il legame, oltre al nodo

`20261013-70`, R-17 del backend, dal collaudo. Un preventivo annullato mostrava
nel pannello la sua commessa «pronta da fatturare», come se ci fosse ancora
dentro. Lo stato del nodo diceva il vero (la commessa è viva, porta righe di
altri documenti), ma rispondeva a un'altra domanda. La colonna nuova
`is_legame_ritirato` risponde a quella giusta: *quello che questo documento ha
portato nella commessa è ancora lì?* Viene da
[`fn_documento_lineage_legami`](fn_documento_lineage_legami.md), letta una volta
alla fine come i nodi, e vale nei due versi (è dell'arco). Il link resta come
storia: si ritira il legame, non il passaggio.

{% include-markdown "signature-core.md" %}
