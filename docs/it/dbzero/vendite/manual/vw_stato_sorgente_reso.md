## 📘 Documentazione Concettuale – Vista `vendite.vw_stato_sorgente_reso`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.resi](/dbzero/vendite/tabelle/resi) — il documento
> * [config.stati_doc_reso](/dbzero/config/tabelle/stati_doc_reso) — lo stato nativo, la fase e `is_abortito`
> * [config.transizioni_stati_reso](/dbzero/config/tabelle/transizioni_stati_reso) — la matrice, che ammette lo storno del confermato
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo `RESO_VENDITA` e la sua chiave
>
> Approfondimento viste:
>
> * [script.vw_stato_sorgente](/dbzero/script/views/vw_stato_sorgente) — l'unione dei resolver, da cui passano i consumatori
> * [vendite.vw_stato_sorgente_ddt](/dbzero/vendite/views/vw_stato_sorgente_ddt) — il ramo gemello delle bolle
>
> Approfondimento funzioni:
>
> * [pratiche.fn_stato_sorgente](/dbzero/pratiche/funzioni/fn_stato_sorgente) — il motore delle pratiche, che la legge sulla chiave tipizzata
> * [vendite.fn_annulla_reso](/dbzero/vendite/funzioni/fn_annulla_reso) — lo storno del reso confermato
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Il **resolver del dominio RESO** per la proiezione dello stato: traduce lo stato nativo del reso di vendita nel vocabolario comune (`fase` / `esito` / `terminale`) con cui tutti i tipi di documento vengono confrontati.

È **read-time**: nessuna copia, il documento resta l'unica verità.

---

### 🔑 La chiave è `id`, e non è la sorgente del reso

Il tipo `RESO_VENDITA` è a chiave **`id`** in `config.sorgenti.key_selector`. La vista espone la
chiave in due forme:

* **`sorgente_chiave_id`** — l'id del reso, nel suo tipo (`sorgente_chiave_uuid` è vuota). È la
  chiave che il motore delle pratiche confronta con `sorgente_id` dei collegamenti, e quella da usare
  per cercare **un** reso: sotto RLS il confronto sul testo non arriva all'indice, quello sul
  bigint sì;
* **`sorgente_uid`** — lo stesso id **in testo**, la chiave dei nodi della genealogia. ⚠️ Il nome è
  storico: vale l'id, non l'uid del reso.

⚠️ Le colonne `sorgente_*` **del reso** sono un'altra cosa: dicono da quale bolla nasce, e la
dichiarano con l'id della bolla in `sorgente_id`, come ogni altro documento. Con la chiave del reso
non c'entrano.

---

### `esito` e `terminale` vengono dal vocabolario

La vista passa `esito` e `terminale` di
[`config.stati_doc_reso`](/dbzero/config/manual/stati_doc_reso), come le viste degli altri documenti:
non li calcola. Il reso confermato ha esito `POSITIVO` e **non è terminale**: resta annullabile a mano
(`CONFERMATO → ANNULLATO`, lo storno). I valori stanno nella pagina del vocabolario.

---

### 📑 Che cosa espone

* **Chiave**: `sorgente_tipo_id`, `sorgente_chiave_id`, `sorgente_chiave_uuid`, e `sorgente_uid` in testo
* **Stato nativo (logica)**: `stato_codice_interno` (immutabile)
* **Stato nativo (display)**: `stato_codice`, `stato_descrizione`
* **Proiezione normalizzata**: `fase`, `esito`, `terminale`

Alias **fedeli** alla sorgente.

---

### Note operative

* **Al più una riga per reso** — la garantisce `resi.id`, la chiave primaria.
* I consumatori **non interrogano questa vista direttamente**: passano da `script.vw_stato_sorgente`
  (a strati: dominio → `script` → consumatore).
* `security_invoker = on`, come tutta la famiglia `vw_stato_sorgente_*`: la vista applica le policy
  di chi la interroga.
* Il reso è un documento di **flusso inverso** (`RESO_VENDITA` è `REVERSE_FLOW` in
  `config.sorgenti`): proietta il suo stato come tutti, ma **non entra** nel funnel pre-commessa
  della dashboard fatturazione — compare solo nel backlog.

---

### Test

* `db/pgtap/vendite/test-vw-stato-sorgente-ddt-reso-v1.sql` — i due rami, bolla e reso.

---

### Note di migrazione

* 2026-07-18 — nasce, con il ramo delle bolle (brief-db-fatturazione-ddt-resi §4a). Nello stesso
  giro il catalogo porta `CONFERMATO` da `IN_CORSO` a `CHIUSO`: prima un reso confermato risultava
  non concluso per sempre.
* 2026-08-21 — la famiglia passa a `security_invoker`.
* 2026-10-05 — espone in coda la chiave nel suo tipo, `sorgente_chiave_id` / `sorgente_chiave_uuid`.
* 2026-11-06 — il reso dichiara la bolla con l'id in `sorgente_id`, come ogni altro documento: prima
  la portava come uid in `sorgente_uid` (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
