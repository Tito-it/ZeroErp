## 📘 Documentazione Concettuale – Funzione `vendite.fn_documento_lineage_archi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento viste:
>
> * [vendite.vw_documento_lineage_archi](/dbzero/vendite/views/vw_documento_lineage_archi) — la stessa cosa per tutto il grafo, con i nodi decorati
>
> Approfondimento funzioni:
>
> * [vendite.fn_documento_lineage_nodi](/dbzero/vendite/funzioni/fn_documento_lineage_nodi) — i nodi, con lo stesso seme
> * [vendite.fn_documento_lineage](/dbzero/vendite/funzioni/fn_documento_lineage) — il pannello «Passaggi»
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa#grafi-tra-documenti) — l'identità di un nodo: tipo + chiave del documento

---

### 🎯 Scopo Principale

I **passaggi** fra documenti — preventivo → ordine → DDT → commessa → fattura,
offerta → contratto, resi, note di credito: i 14 tipi di arco — **per i soli
documenti che si chiedono**, non per tutti.

**La revisione dell'offerta** (arco `V`) va dalla revisione madre alla figlia. Non è
un passaggio di un documento a un altro: la mostra il pannello «Passaggi» (e da lì la finestra
dell'annullo di una revisione prende il nome di quella che torna emessa), ma non ha rango e la
scartano la [sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) e le [origini della fattura](/dbzero/vendite/funzioni/fn_fattura_origini).

La vista [`vw_documento_lineage_archi`](/dbzero/vendite/views/vw_documento_lineage_archi) costruisce
il grafo **intero**: chi vuole i passaggi di un documento pagherebbe quelli di tutti
i documenti del sistema, e quel costo cresce con la storia dell'azienda. Da qui
la funzione, di cui la vista è la proiezione «senza seme».

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
di lettura scelga il database. Passato come JOIN, sotto
le policy di sicurezza il database partirebbe dal lato sbagliato e leggerebbe l'altro
capo per intero. Le chiavi derivate (per esempio l'`id` di un preventivo dal suo
`uid`) si leggono con la visibilità di chi chiama: un documento che non vede non
semina niente, come nella vista.

---

### ⚠️ Da sapere

* **Un arco nuovo si aggiunge qui, nei due modi** (seme e «tutti»): la vista ne
  è la proiezione e lo eredita. Il presidio
  `db/pgtap/vendite/test-documento-lineage-seminata-v1.sql` confronta i due modi.
* **Porta `SET jit = off` e `SET plan_cache_mode = force_generic_plan`**
  (anche su `fn_documento_lineage_nodi`). Il corpo
  contiene i due modi: quando il seme non è una costante il piano li tiene
  entrambi, e il JIT ne compilerebbe le espressioni a ogni chiamata (secondi, anche
  a database vuoto). Con le due clausole la funzione non si incorpora, si
  pianifica una volta per sessione e chi la chiama non deve dichiarare niente.
  ⚠️ Un `CREATE OR REPLACE` che non le ripete le perde: presidio
  `db/pgtap/script/test-plan-cache-mode-piano-generico-v1.sql`.
* `is_ramo_inverso` e `rango_origine` dipendono solo dalla lettera dell'arco e
  stanno qui, una volta sola.

---

### Gli archi leggono la provenienza del modello

* **Gli archi fra testate** — A (preventivo → ordine), C (offerta → contratto), D (offerta →
  ordine), H (ordine → bolla), R (bolla → reso) — leggono la provenienza di testata del documento
  a valle con la regola d'incontro del modello: il documento a monte combacia per `id` con
  `sorgente_id` o per `uid` con `sorgente_uid`, in tutti e due i modi, sugli indici della
  provenienza (`ix_ordini_v_sorgente_uid` / `_id`, `ix_contratti_sorgente_uid` / `_id`,
  `ix_ddt_v_sorgente` / `_id`, `ix_resi_sorgente` / `_id`).
* **Gli archi verso la commessa** — B, E, F, U, dalle sorgenti della commessa — trovano la chiave
  del link nella colonna del suo tipo (`commesse_sorgenti.sorgente_uid` per il preventivo,
  `sorgente_id` per ordine, contratto e DDT): il join verso il documento confronta colonne dello
  stesso tipo, senza conversioni, e sotto le policy di sicurezza usa l'indice.

---

### Note di migrazione

* 2026-10-11 — nasce la funzione, con il seme (brief-db-lineage-seminata-per-chiave §8.2-§8.3);
  la vista ne diventa la proiezione «senza seme». Lo stesso giorno: le clausole `jit` e
  `plan_cache_mode`, e i rami verso la commessa leggono le sorgenti del seme una volta con la
  chiave già convertita (una commessa con 32 preventivi: ~270 → ~30 ms).
* 2026-10-31 — arriva l'arco `V`, la revisione dell'offerta.
* 2026-11-06 / 2026-11-07 — gli archi fra testate leggono la provenienza tipizzata del documento a
  valle, al posto delle colonne parallele `documento_origine_*` e `offerta_id` e della chiave
  testuale `sorgente_uid`; i rami verso la commessa leggono le colonne tipizzate di
  `commesse_sorgenti`, senza conversioni (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
