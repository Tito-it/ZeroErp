## 📘 Documentazione Concettuale – Funzione `pratiche.trgfn_sospensioni_giornale_ins()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni)
> • [pratiche.giornale](/dbzero/pratiche/tabelle/giornale)
>
Approfondimento funzioni:
> • [pratiche.trgfn_sospensioni_giornale_riattivazione](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_riattivazione)
> • [pratiche.trgfn_sospensioni_propaga](/dbzero/pratiche/funzioni/trgfn_sospensioni_propaga)
> • [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Scrive nel **giornale della pratica** l'evento `SOSPENSIONE_REGISTRATA` ogni volta che nasce
una sospensione. È audit di dominio, non tecnico: `pratiche.giornale` è la cronologia
leggibile di che cosa è successo a una pratica, ed è ciò che l'operatore consulta per capire
perché i tempi si sono fermati.

L'evento è scritto **dal database**, non dall'applicazione. Vale la conseguenza abituale del
DB-first: una sospensione creata da un import, da uno script o da un `INSERT` diretto finisce
comunque nel giornale, senza che il chiamante debba ricordarsene.

---

### Aggancio

Trigger `trg_sospensioni_z90_giornale_ins` — fase `_z90_` (finale),
`AFTER INSERT` su `pratiche.sospensioni`, `FOR EACH ROW`.

---

### Che cosa scrive

Una riga in `pratiche.giornale` con:

| Colonna | Valore |
|---------|--------|
| `pratica_id` / `flusso_id` | copiati dalla sospensione |
| `azione` | `'SOSPENSIONE_REGISTRATA'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` (JSONB) | `sospensione_id`, `motivo`, `data_inizio`, `data_riattivazione_prevista`, `livello` |
| `tx_id` | `COALESCE(NEW.tx_id, gen_random_uuid())` |

Il campo `livello` è calcolato: `'PRATICA'` se `flusso_id` è nullo, `'FLUSSO'` altrimenti.
Serve a distinguere a colpo d'occhio la sospensione dell'intera pratica da quella di una
singola fase, senza dover reinterpretare il `NULL` in lettura.

---

### Il vocabolario delle azioni è un CHECK, non una tabella

`'SOSPENSIONE_REGISTRATA'` è ammesso perché compare nella whitelist di
`chk_giornale_azione`, che accetta 11 eventi di motore più qualunque codice nella forma
`DOMINIO_<NOME>`.

⚠️ Conseguenza: **il vocabolario si estende con una migration, non con una riga di dati.**
Un evento di motore nuovo che non rispetti la forma `DOMINIO_*` richiede di riscrivere il
CHECK; scriverlo e basta produce una violazione di vincolo.

---

### ⚠️ Il fallback sul `tx_id` è una rete che non dovrebbe servire

`COALESCE(NEW.tx_id, gen_random_uuid())` genera un id **nuovo** quando la sospensione non
ne ha uno. Un id inventato qui non correla niente: la riga di giornale risulterebbe di una
transazione che non esiste altrove.

In pratica non accade, perché `trg_sospensioni_gen_tx_id_ins_upd`
(`dbops.trgfn_tx_id_managed`, `BEFORE INSERT`) valorizza `tx_id` prima che questo trigger
`AFTER` parta. Il `COALESCE` è quindi ridondante — ma se un giorno quel `BEFORE` venisse
rimosso, il difetto **non si manifesterebbe come errore**: si manifesterebbe come righe di
giornale non correlabili, ed è la forma peggiore in cui possa presentarsi.

---

### Codici errore

Nessuno: la funzione non solleva. Un fallimento sarebbe una violazione di vincolo su
`pratiche.giornale`, e — trattandosi di un `AFTER` nella stessa transazione — farebbe
fallire anche l'inserimento della sospensione.

---

{% include-markdown "signature-core.md" %}
