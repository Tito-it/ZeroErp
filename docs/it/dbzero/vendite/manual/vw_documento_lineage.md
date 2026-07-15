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

{% include-markdown "signature-core.md" %}
