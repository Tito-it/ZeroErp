## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage_archi(p_tipo_ids, p_uids)`

> 👀 **Vedi anche**
>
> [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi) — la stessa cosa per tutto il grafo, con i nodi decorati
> [vendite.fn_documento_lineage_nodi](/dbzero/vendite/funzioni/fn_documento_lineage_nodi) — i nodi, con lo stesso seme
> [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage) — il pannello «Passaggi»
> Brief: `docs/it/dev/work-done/brief-db-lineage-seminata-per-chiave.md` §8.2-§8.3

---
### 🎯 Scopo Principale
(rev 2026-10-11)

I **passaggi** fra documenti — preventivo → ordine → DDT → commessa → fattura,
offerta → contratto, resi, note di credito: i 13 tipi di arco — **per i soli
documenti che si chiedono**, non per tutti.

La vista [`vw_documento_lineage_archi`](vw_documento_lineage_archi.md) costruisce
il grafo **intero**: chi voleva i passaggi di un documento pagava quelli di tutti
i documenti del sistema, e quel costo cresce con la storia dell'azienda. Da qui
la funzione, di cui la vista è diventata la proiezione «senza seme».

---

### Il seme

Il seme è la **chiave del nodo**, la stessa con cui il modello identifica un
documento in ogni grafo: il tipo (`config.sorgenti.id`) e la chiave del documento
resa a testo, `uid` per preventivo e offerta, `id` per gli altri (`key_selector`).
Arriva in **due array paralleli**, perché chi chiama di solito ha in mano un
insieme di documenti di tipi diversi (la «frontiera» di una catena).

| Seme | Risultato |
| --- | --- |
| entrambi `NULL` | tutti gli archi (è la vista) |
| array vuoti | nessun arco |
| coppie di nodi | gli archi **incidenti**: uscenti da un nodo del seme ed entranti in un nodo del seme, ciascuno una volta |
| tipo ignoto, chiave inesistente, coppia monca | non seminano niente |

---

### ⭐ Perché il seme scende come elenco e non come JOIN

Ogni ramo legge per prima una tabella **limitata dalle chiavi del seme sul suo
indice** (`= ANY(…)`): così parte sempre dal documento chiesto, qualunque ordine
di lettura scelga il database. La prima versione passava il seme come JOIN: sotto
le policy di sicurezza il database partiva dal lato sbagliato e leggeva l'altro
capo per intero. Le chiavi derivate (per esempio l'`id` di un preventivo dal suo
`uid`) si leggono con la visibilità di chi chiama: un documento che non vede non
semina niente, come nella vista.

---

### ⚠️ Da sapere

* **Un arco nuovo si aggiunge qui, nei due modi** (seme e «tutti»): la vista ne
  è la proiezione e lo eredita. Il presidio
  `db/pgtap/vendite/test-documento-lineage-seminata-v1.sql` confronta i due modi.
* **Porta `SET jit = off` e `SET plan_cache_mode = force_generic_plan`**
  (changeSet `20261011-67`, anche su `fn_documento_lineage_nodi`). Il corpo
  contiene i due modi: quando il seme non è una costante il piano li tiene
  entrambi, e il JIT ne compilava le espressioni a ogni chiamata (secondi, anche
  a database vuoto). Con le due clausole la funzione non si incorpora più, si
  pianifica una volta per sessione e chi la chiama non deve dichiarare niente.
  ⚠️ Un `CREATE OR REPLACE` che non le ripete le perde: presidio
  `db/pgtap/script/test-plan-cache-mode-piano-generico-v1.sql`.
* `is_ramo_inverso` e `rango_origine` dipendono solo dalla lettera dell'arco e
  stanno qui, una volta sola.

### 🔄 rev 2026-10-11 — i passaggi verso la commessa si cercano per indice

Changeset `20261011-92`. Nei rami preventivo/ordine/contratto/DDT → commessa la
chiave del documento è scritta come testo nelle sorgenti della commessa. Il
confronto passava da una conversione di tipo, e sotto le policy di sicurezza una
conversione non può usare l'indice: per ogni sorgente il database leggeva l'intera
tabella dell'altro capo. Ora le sorgenti delle commesse del seme si leggono una
volta con la chiave già convertita, e il confronto è fra colonne dello stesso tipo
(una commessa con 32 preventivi: ~270 → ~30 ms).

{% include-markdown "signature-core.md" %}
