## 📘 Documentazione Concettuale – Vista `vendite.vw_documento_lineage`

> 👀 **Vedi anche**
>
> Approfondimento:
>
> [vendite.vw_documento_lineage_nodi](/dbzero/vendite/views/vw_documento_lineage_nodi)
> [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi)
> [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage)
> [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti)

---

### 🎯 Scopo Principale

`vendite.vw_documento_lineage` è la vista **summary** (una riga per documento) pensata per
**arricchire le liste vendite** con un solo JOIN. Risponde a due domande dalle liste:

1. a quale **pratica** è collegato il documento;
2. **dove è transitato** e qual è il **documento più prossimo in esecuzione** (la
   **frontiera**), oltre al conteggio dei discendenti.

Base: `vw_documento_lineage_nodi` (tutti i nodi, anche isolati). Grafo forward:
`vw_documento_lineage_archi` **escludendo l'arco R** (il reso è ramo inverso).

---

### 📑 Campi chiave esposti

* **Chiave nodo**: `tipo_id`, `uid`, `codice`
* **Stato/fase propri**: `stato_codice_interno`/`stato_codice`/`stato_descrizione`,
  `fase`, `is_abortito`
* **Pratica** (1:1 difensiva): `pratica_id`, `pratica_numero` (= `pratiche.codice`),
  `n_pratiche` (conteggio; `>1` = anomalia da segnalare)
* **Frontiera** (documento più a valle ancora attivo): `frontiera_tipo_id`,
  `frontiera_uid`, `frontiera_codice`, `frontiera_stato_codice_interno`, `frontiera_fase`
* **Discendenti diretti** (livello 1): `n_discendenti_diretti`, `n_discendenti_attivi`
  (segnala il fan-out F contratto→N commesse), `is_transitato` (ha discendenti)
* **Lato inverso** (per la lista commesse, G-11): `n_sorgenti` (archi entranti forward),
  `root_tipo_id`/`root_uid`/`root_codice` (la sorgente con ruolo `ROOT`)

---

### 🧭 Regola della frontiera

La **frontiera** è il documento più prossimo *in esecuzione*, calcolato con un traversal
forward (`WITH RECURSIVE` sugli archi, escluso R). Tra i candidati — il nodo stesso
(livello 0) e tutti i discendenti forward — si sceglie in quest'ordine:

1. prima gli **ATTIVI**: `fase <> 'CHIUSO' AND NOT is_abortito`;
2. poi il **più profondo** (`livello DESC`);
3. a parità di livello, il **più a valle nel flusso** (`pipeline_rank DESC`:
   fattura > commessa > ddt > ordine=contratto > preventivo=offerta);
4. tie-break finale deterministico (tipo, uid).

Se nessun candidato è attivo (catena tutta chiusa) la frontiera è il **nodo terminale più
profondo** (es. «→ Fatturato»). Un documento senza discendenti ha frontiera = sé stesso.

---

### Esempio d'uso

```sql
-- Arricchimento di una lista (es. preventivi): pratica + fase + frontiera con un JOIN.
SELECT l.*, dl.pratica_numero, dl.fase,
       dl.frontiera_codice, dl.frontiera_fase, dl.is_transitato
FROM vendite.vw_preventivi_lista l
JOIN vendite.vw_documento_lineage dl
  ON dl.tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')
 AND dl.uid = (l.uid)::text;
```

---

### Note operative

* **Pratica 1:1 (difensiva)**: il modello non forza 1:1 (`pratiche_sorgenti` ammette più
  righe); si prende la prima per id e si espone `n_pratiche` per intercettare le anomalie.
* **Reso**: escluso dalla frontiera forward; compare invece nei "Passaggi"
  (`fn_documento_lineage`). Un reso è frontiera solo di sé stesso.
* **`security_invoker=on`**: RLS emittente del chiamante (reloption da ri-specificare).
* **Prestazioni**: la frontiera espande il grafo per ogni nodo; su catene corte (≤ ~5 hop)
  è adeguata. Su volumi grandi valutare materializzazione o spostare il calcolo nella
  funzione traversal.
* Test: `db/pgtap/vendite/test-documento-lineage-v1.sql`.

---


### ⭐ Il filtro del ramo di ritorno, e la natura (rev 2026-08-21)

I due `WHERE` del grafo forward non nominano più la lettera `'R'`: leggono
`vw_documento_lineage_archi.is_ramo_inverso`, che è l'unica sede dell'elenco dei
rami di ritorno (oggi `R` e `N`).

⚠️ **L'arco `S` (reso → nota di credito, 2026-08-25) NON è stato aggiunto a
quell'elenco, ed è una decisione.** «Inverso» non vuol dire «a valle di un
ritorno»: vuol dire *ramo di ritorno*, un verso che il grafo forward non deve
percorrere. `S` è l'**avanzamento naturale del reso** — la merce è tornata,
adesso si accredita — come `H` è l'avanzamento dell'ordine. Marcarlo inverso
avrebbe lasciato il reso frontiera di sé stesso, cioè al punto di partenza.
Presidiato dal test **29**, che asserisce `is_ramo_inverso` vero *esattamente*
per `R` e `N`: diventerebbe rosso il giorno in cui qualcuno aggiungesse `S`
«per simmetria».

⛔ **Il risultato non è cambiato di una riga, ed è misurato**: applicando le
quattro modifiche in transazione e confrontando la summary prima/dopo su tutti i
nodi, le righe cambiate sono **zero**.

⚠️ **Quanto sarebbe costato sbagliare.** Se uno dei due filtri fosse rimasto
`arco <> 'R'`, la nota di credito sarebbe diventata un discendente forward della
fattura che rettifica. La regola della frontiera sceglie l'**attivo più
profondo**: la nota avrebbe vinto sulla fattura stessa, e ogni riga di lista
avrebbe cambiato la propria frontiera. Senza errori, senza log, solo un valore
diverso.

**La natura del nodo** (`natura_doc_codice_interno` / `natura_doc_descrizione`) è esposta
anche qui, così una lista di fatture smette di scrivere «Fattura» sopra una nota
di credito.

⛔ **CORREZIONE (2026-08-25) — qui c'era una frase falsa, e lo era già il giorno
in cui è stata scritta.** Diceva: *«non esiste una `frontiera_natura_doc_codice_interno`,
e non è una dimenticanza: l'arco N è escluso dal grafo forward, quindi una nota
di credito non può mai essere la frontiera di nessuno e quella colonna varrebbe
sempre NULL»*. La **premessa** è giusta, la **conclusione** no — e il paragrafo
successivo, sulla stessa pagina, diceva già il contrario.

L'arco **G** (commessa → fattura) **non** è un ramo di ritorno, quindi una nota
di credito **è** raggiungibile in avanti: misurata dal BE il 2026-08-21 come
frontiera dell'ordine 240 e della commessa 322. Dal 2026-08-25 l'arco **S**
(reso → nota di credito) la rende frontiera anche del **reso** — ed è
l'informazione per cui quel cantiere esiste.

Lo stesso testo viveva nel `COMMENT ON VIEW`, corretto dal changeSet
`20260825-20` (un `COMMENT ON VIEW` **da solo**: ricreare la vista per una
stringa avrebbe voluto dire ricopiare 150 righe di `WITH RECURSIVE` e
ri-specificare `security_invoker=on`, che se dimenticato si azzera in silenzio).

**La colonna quindi non c'è per un'altra ragione**: il consumatore la ricava per
conto suo. `get_lineage_nodo` la legge joinando `vw_documento_lineage_nodi` sulla
frontiera (`nfr.natura_doc_codice_interno`).

🔴 **E questo oggi basta per un consumatore solo.** Il join richiede
`frontiera_uid`, che la summary espone **ma le `vw_*_lista` no**: le sei liste
documento portano `frontiera_tipo_id`/`_codice`/`_stato`/`_fase` e non la chiave
del nodo, quindi la colonna «Transito» **non può** ricavare la natura e scrive
«Fattura» sopra una nota di credito. Misurato il 2026-08-25: 4 nodi hanno una NC
come frontiera (ordine, reso, commessa, e la NC stessa), e sul reso il caso è
**strutturale** — il pgTAP 35 asserisce che l'arco `S` arriva *sempre* a una
`NOTA_CREDITO`. Richiesta al team DB nel brief
`brief-db-lineage-residui-root-e-sorgente-ddt.md`, §3.

📌 **Un'invariante che vale la pena conoscere**, ed è quella che presidia la
scelta: *una fattura è sempre frontiera di sé stessa* — nel grafo forward non ha
archi uscenti. È il test 30 di `test-documento-lineage-v1`.
⚠️ **Non** «una nota di credito non è mai frontiera»: quella formulazione è
sbagliata, ed è stata il test a dirlo diventando rosso.

---

{% include-markdown "signature-core.md" %}
