## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_offerta`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — il documento
> * [config.stati_doc_offerte](/dbzero/config/tabelle/stati_doc_offerte) — lo stato nativo e la sua proiezione
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo `OFFERTA_COMMERCIALE` e la sua chiave
>
> Approfondimento viste:
>
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — l'unione dei resolver, da cui passano i consumatori
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

Il **resolver del dominio OFFERTA** per la proiezione dello stato: per ogni offerta commerciale dice lo stato **vivo** nel vocabolario comune — lo stato nativo e la sua proiezione `fase` / `esito` / `terminale`, dichiarata su `config.stati_doc_offerte`.

È **read-time**: nessuna copia, il documento resta l'unica verità.

---

### 🔑 La chiave: tipizzata per cercare, in testo per il grafo

La vista espone la chiave del documento in due forme:

* **`sorgente_chiave_id` / `sorgente_chiave_uuid`** — la chiave nel suo tipo, come la scrive il
  modello della provenienza: `sorgente_chiave_uuid` è l'uid dell'offerta, `sorgente_chiave_id` è vuota (il tipo `OFFERTA_COMMERCIALE` è a chiave `uid`). È la chiave che il motore delle pratiche
  ([`pratiche.fn_stato_sorgente`](/dbzero/pratiche/funzioni/fn_stato_sorgente)) confronta con
  `sorgente_id` / `sorgente_uid` di `pratiche.pratiche_sorgenti`, e quella da usare per cercare **un**
  documento: sotto RLS il confronto sul testo non arriva all'indice, quello sul tipo nativo sì;
* **`sorgente_uid`** — la stessa chiave **in testo**, nella forma canonica (l'uid in testo): è la chiave dei
  nodi della genealogia e delle unioni con il grafo. ⚠️ Il nome è storico: qui non è la colonna
  uuid del modello, e per l'offerta vale il suo uid.

Il tipo si aggancia da `config.sorgenti` per `codice_interno = 'OFFERTA_COMMERCIALE'` (attivo), mai con un
id scritto nel codice.

---

### 📑 Che cosa espone

* **Chiave**: `sorgente_tipo_id`, `sorgente_chiave_id`, `sorgente_chiave_uuid`, e `sorgente_uid` in testo
* **Stato nativo (logica)**: `stato_codice_interno` (immutabile)
* **Stato nativo (display)**: `stato_codice`, `stato_descrizione`
* **Proiezione normalizzata**: `fase`, `esito` (il verdetto, o vuoto), `terminale`

Alias **fedeli** alla sorgente. `fase` è una fra `APERTO`, `IN_CORSO`, `IN_ATTESA`, `CHIUSO`; `esito` è il verdetto (`POSITIVO`, `NEGATIVO`, …) o vuoto.

---

### Note operative

* **Al più una riga per documento** — la garantisce l'unicità di `offerte_commerciali.uid`.
* I consumatori **non interrogano questa vista direttamente**: passano da `script.vw_stato_sorgente`
  (a strati: dominio → `script` → consumatore).
* `security_invoker = on`: la vista applica le policy di chi la interroga.
* Test: `db/pgtap/pratiche/test-proiezione-stato-sorgente.sql`.

---

### Note di migrazione

* 2026-07-02 — nasce come resolver di dominio della proiezione dello stato (brief-db-proiezione-stato-dominio).
* 2026-10-05 — espone in coda la chiave nel suo tipo, `sorgente_chiave_id` / `sorgente_chiave_uuid`, accanto alla forma in testo.
* 2026-11-08 — il motore delle pratiche la legge sulla chiave tipizzata: `pratiche_sorgenti` tiene la
  chiave del documento nelle colonne del modello, non più in testo (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
