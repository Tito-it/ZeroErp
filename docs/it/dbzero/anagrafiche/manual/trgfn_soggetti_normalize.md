## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_normalize`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella di cui scrive `stato_id`
> * [config.stati](/dbzero/config/tabelle/stati) — gli stati, cercati per codice ISO2
>
> Approfondimento funzioni:
>
> * [script.fn_stato_proposto_id](/dbzero/script/funzioni/fn_stato_proposto_id) — lo stato proposto, letto dal parametro
> * [anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch](/dbzero/anagrafiche/funzioni/trgfn_soggetti_valida_cf_piva_dispatch) — il controllo che dallo stato sceglie il validatore

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_normalize` dà lo stato proposto a un soggetto scritto senza stato. Non fa altro: non
pulisce né normalizza nessun altro campo.

---

### Lo stato proposto è un dato

Lo stato che si propone non è scritto nel codice: è il parametro `STATO_PROPOSTO_ISO2`, letto da
`script.fn_stato_proposto_id` con la cascata degli override della sessione (utente, gruppo, azienda, sessione, funzione).
Il trigger le passa il proprio nome, così un override può valere anche solo per questa strada.

La lettura non ripiega mai: un parametro assente o vuoto, un codice che non indica nessuno stato o che ne indica
più d'uno fermano la scrittura con un errore che lo dice. Uno stato detto da chi scrive non si tocca.

Il trigger viene prima, per nome, del controllo del formato di CF e P.IVA, che dallo stato sceglie il
validatore: il controllo vede già lo stato proposto.

---

### ⚠️ Che cosa oggi non copre

* **Una modifica che toglie lo stato non è rifiutata.** Il trigger scatta anche in modifica: una scrittura che
  porta `stato_id` a NULL riceve lo stato proposto, e il soggetto cambia nazionalità (e perimetro
  dell'identificativo fiscale) senza averlo chiesto.
* **Il trigger non ha la fascia nel nome** (`trg_soggetti_normalize_ins_upd`): il suo posto fra i trigger lo
  decide l'ordine alfabetico, dopo tutti i guard della fascia `a10`.

---

### Codici errore

Il trigger non ne solleva di suoi. Dalla lettura dello stato proposto:

* `E_CONFIG_MANCANTE` — il parametro manca o è vuoto.
* `E_STATO_ISO2_AMBIGUO` — il codice indica più stati.
* `E_DEFAULT_ERRATO` — il codice non indica nessuno stato.

---

### Note di migrazione

* 2026-10-18 — lo stato proposto passa al parametro `STATO_PROPOSTO_ISO2`, che non ripiega; prima si leggeva un
  default per codice ISO3.

---

{% include-markdown "signature-core.md" %}
