## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_ddt`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — il documento
> * [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt) — lo stato nativo, la fase e `is_abortito`
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo `DDT_VENDITA` e la sua chiave
>
> Approfondimento viste:
>
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — l'unione dei resolver, da cui passano i consumatori
> * [vendite.vw_stato_sorgente_reso](/dbzero/vendite/views/vw_stato_sorgente_reso) — il ramo gemello dei resi
>
> Approfondimento funzioni:
>
> * [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) — il motore delle pratiche, che la legge sulla chiave tipizzata
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Il **resolver del dominio DDT** per la proiezione dello stato: traduce lo stato nativo della bolla di vendita nel vocabolario comune (`fase` / `esito` / `terminale`) con cui tutti i tipi di documento vengono confrontati.

È **read-time**: nessuna copia, il documento resta l'unica verità.

---

### 🔑 La chiave è `id`, non l'uid

Il tipo `DDT_VENDITA` è a chiave **`id`** in `config.sorgenti.key_selector` (solo `PREVENTIVO` e
`OFFERTA_COMMERCIALE` usano l'uid). La vista espone la chiave in due forme:

* **`sorgente_chiave_id`** — l'id della bolla, nel suo tipo (`sorgente_chiave_uuid` è vuota). È la
  chiave che il motore delle pratiche confronta con `sorgente_id` dei collegamenti, e quella da usare
  per cercare **una** bolla: sotto RLS il confronto sul testo non arriva all'indice, quello sul
  bigint sì;
* **`sorgente_uid`** — lo stesso id **in testo**, la chiave dei nodi della genealogia. ⚠️ Il nome è
  storico: vale l'id, non l'uid della bolla.

Tutti i documenti che nascono da una bolla — il reso, i carichi e gli scarichi di magazzino, le
righe di commessa — la dichiarano allo stesso modo, con l'id in `sorgente_id`. Cercare per uid **non
trova**: nessun errore, solo una proiezione vuota. Il pgTAP lo asserisce apposta.

---

### `esito` e `terminale` vengono dal vocabolario

La vista passa `esito` e `terminale` di
[`config.stati_doc_ddt`](/dbzero/config/manual/stati_doc_ddt), come le viste degli altri documenti: non
li calcola. I valori, e il perché la bolla resa è `POSITIVO`, li dice la pagina del vocabolario. Uno
stato nuovo dichiara i suoi nel seed, e la vista non cambia.

---

### 📑 Che cosa espone

* **Chiave**: `sorgente_tipo_id`, `sorgente_chiave_id`, `sorgente_chiave_uuid`, e `sorgente_uid` in testo
* **Stato nativo (logica)**: `stato_codice_interno` (immutabile)
* **Stato nativo (display)**: `stato_codice`, `stato_descrizione`
* **Proiezione normalizzata**: `fase`, `esito`, `terminale`

Alias **fedeli** alla sorgente.

---

### Note operative

* **Al più una riga per bolla** — la garantisce `ddt.id`, la chiave primaria.
* I consumatori **non interrogano questa vista direttamente**: passano da `script.vw_stato_sorgente`
  (a strati: dominio → `script` → consumatore).
* `security_invoker = on`, come tutta la famiglia `vw_stato_sorgente_*`: la vista applica le policy
  di chi la interroga.
* Test: `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql`.

---

### Note di migrazione

* 2026-07-18 — nasce, con il ramo dei resi: il traduttore copre tutti i tipi di documento registrati (brief-db-fatturazione-ddt-resi §4a).
* 2026-08-21 — la famiglia passa a `security_invoker`.
* 2026-10-05 — espone in coda la chiave nel suo tipo, `sorgente_chiave_id` / `sorgente_chiave_uuid`.
* 2026-11-06 — il reso dichiara la bolla con l'id in `sorgente_id`, come ogni altro documento: prima
  la portava come uid in `sorgente_uid`, fuori dal modello della provenienza
  (brief-db-sorgente-documento-e-riga).
* 2026-11-08 — il motore delle pratiche la legge sulla chiave tipizzata.

---

{% include-markdown "signature-core.md" %}
