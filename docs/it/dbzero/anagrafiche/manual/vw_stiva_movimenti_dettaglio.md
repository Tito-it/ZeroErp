## 📘 Documentazione Concettuale – Vista `anagrafiche.vw_stiva_movimenti_dettaglio`

> 👀 **Vedi anche**
>
> [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro ·
> [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo, da cui arriva il perimetro ·
> [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — chi decide il motivo di blocco ·
> [vendite.vw_resi_righe_dettaglio](/dbzero/vendite/views/vw_resi_righe_dettaglio) — la gemella, nata dallo stesso problema

---

### 🎯 Scopo Principale

(rev 2026-08-31 — vista nata il 2026-08-31)

Le **righe del registro** dei movimenti di plafond di un titolo IVA, per il drawer
di dettaglio: anagrafica del movimento, il tipo di titolo, il **legame dell'annullo
nei due versi**, e il **motivo di blocco** dell'annullo.

---

### ⭐ Perché nasce una vista

La decisione di Tid del 2026-08-30 dice che l'operatore deve trovare il pulsante
«Annulla» **già spento, col motivo**, invece di scoprirlo premendo. Perché quel
motivo arrivi a video serve una superficie che lo porti — e per questo registro
**non ne esisteva nessuna**.

⚠️ È lo stesso punto di partenza dei resi: le righe del reso erano l'unico dettaglio
documento servito da SQL scritto in Python, ed era esattamente il motivo per cui il
motivo di blocco poteva arrivare solo dove non serviva. Da lì è nata
`vw_resi_righe_dettaglio`; questa è la sua gemella.

> ⛔ **La domanda che decide la sede è: da dove si preme quel pulsante?**
> Non «quale lista parla di questa cosa». Il pulsante vive sul registro di **un**
> titolo, quindi il motivo va sulle righe di quel registro.

---

### Le colonne che non sono una semplice proiezione

| Colonna | Cosa dice |
| --- | --- |
| `annulla_movimento_id` | **cosa annullo** — valorizzata sulle sole righe di annullo |
| `annullato_da_movimento_id` | **chi mi annulla** — il verso inverso, quello che serve al frontend per barrare la riga e rimandare all'annullo |
| `is_annullo` / `is_annullato` | i due flag già pronti, per non far ricomporre la logica a chi rende |
| `annullo_blocco_codice` | il **motivo** per cui «Annulla» è spento. `NULL` = ammesso |
| `annullo_blocco_reason_key` | la chiave i18n del tooltip |

⛔ **Un verbo, una colonna.** Il nome dice **per quale azione** è il blocco: una
colonna generica «bloccato» verrebbe riusata dal prossimo verbo e direbbe due cose
insieme.

⚠️ `annullo_blocco_codice` porta il **`reason`** (codice macchina), non il codice
errore — è la stessa convenzione di `vw_resi_righe_dettaglio`, ed è il nome che il
frontend già conosce.

---

### ⭐ Il motivo viene dalla stessa funzione che rifiuta

`script.fn_check_annullo_movimento_titolo_iva` è **la sede unica** della regola: la
interrogano questa vista (per spegnere) e la madre (per rifiutare). Non «coincidono
oggi»: **non possono divergere**.

---

### ⛔ Perimetro: si passa da `soggetti_titoli_iva`

Il registro ha la RLS, ma il join al titolo **non è ridondante**: è da lì che
arrivano `soggetto_id` ed `emittente_fiscale_id`, e una vista che li leggesse
altrove sarebbe interrogabile per qualunque `titolo_iva_id`.

> ⚠️ *Un oggetto di database dev'essere sicuro **da solo**: il prossimo consumatore
> non sa cosa faceva il primo.* Che il service autorizzi prima non basta.

⛔ **`security_invoker=on` va ri-specificata** a ogni `CREATE OR REPLACE VIEW`:
PostgreSQL la **azzera** se non la si ripete, e la vista scavalcherebbe la RLS
senza dirlo.

---

### ⚠️ La vista proietta, il chiamante filtra

Nessun filtro incorporato e nessun ordinamento: una vista «dettaglio» che
nascondesse righe di nascosto darebbe un conteggio diverso da quello della tabella
**senza dirlo**.

---

### ⚠️ Una chiamata per riga, ed è la forma prevista

Il `LATERAL` invoca la check una volta per movimento. Per le **azioni di riga** è il
pattern dichiarato dalle linee guida — non l'eccezione alla regola «le capability
stanno solo sul dettaglio, mai per riga di lista»: qui si guarda il registro di
**un** titolo, non una lista globale.

---

### Test

`db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql`, asserzione **11**: sulla
forzatura annullata il motivo c'è ed è `GIA_ANNULLATO`, su quella ancora viva è
`NULL`. ⭐ Sono due metà, e servono entrambe: un motivo sempre valorizzato non
proverebbe che la vista sa distinguere.

Cantiere: `brief-db-titoli-iva-movimenti-annullo.md`, fase `D`.

---

{% include-markdown "signature-core.md" %}
