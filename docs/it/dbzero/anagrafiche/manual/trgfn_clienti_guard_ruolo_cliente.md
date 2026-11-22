## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_clienti_guard_ruolo_cliente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — la tabella su cui scatta
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ruolo controllato
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il tipo di ruolo cliente
>
> Approfondimento funzioni:
>
> * [script.fn_guard_soggetto_ruolo](/dbzero/script/funzioni/fn_guard_soggetto_ruolo) — il controllo comune delle specializzazioni dei ruoli
> * [anagrafiche.trgfn_billing_account_guard_soggetto_coerenza_istanza](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_soggetto_coerenza_istanza) — lo stesso controllo sul billing account
> * [anagrafiche.trgfn_clienti_sync_utility_from_ba](/dbzero/anagrafiche/funzioni/trgfn_clienti_sync_utility_from_ba) — la copia del ruolo dal billing account

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_clienti_guard_ruolo_cliente` rifiuta un cliente il cui ruolo non esiste o non è di tipo
cliente (`CL`). Non crea ruoli e non cambia il valore: verifica soltanto.

---

### Il controllo comune dei ruoli

Il controllo è `script.fn_guard_soggetto_ruolo`, lo stesso delle altre tabelle di specializzazione dei ruoli,
chiamato col tipo cliente e senza soggetto: basta che il ruolo indicato esista e sia di quel tipo. Il ruolo, se
manca, lo crea chi fa nascere il cliente (`anagrafiche.fn_crea_cliente`), non il trigger.

Scatta prima di ogni scrittura del cliente, anche quando il ruolo non cambia.

---

### ⚠️ Il ruolo va passato

Per nome il guard viene prima di `anagrafiche.trgfn_clienti_sync_utility_from_ba`, che copia ruolo e utility
dal billing account quando chi scrive non li passa. Per la utility la copia funziona; per il ruolo no: un
cliente senza ruolo è rifiutato qui, prima che la copia arrivi.

---

### ⚠️ Che cosa oggi non copre

* **Ripete un controllo che il billing account fa già.** Il ruolo del cliente è quello del suo billing account
  (chiave esterna composta, e dopo la nascita bloccato), e il billing account vuole già un ruolo di tipo
  cliente. Il guard non rifiuta niente che non sarebbe rifiutato comunque; l'unico effetto proprio è il
  rifiuto del ruolo mancante, che impedisce la copia descritta sopra.
* **Gira a ogni modifica**, anche quando il ruolo non può cambiare.

---

### Codici errore

* `E_SOGGETTI_RUOLI` — ruolo mancante, inesistente o di un altro tipo.
* `E_COD_INT_RUOLO` — il tipo di ruolo cliente non è nel catalogo.

---

### Test

Nessun pgTAP lo prova da solo: lo attraversano tutti i test che creano clienti.

---

### Note di migrazione

* 2026-10-09 — il billing account controlla anche lui il tipo di ruolo cliente, e dal 2026-10-10 il cliente
  copia il ruolo dal billing account: da allora questo guard ripete un controllo che sta già a monte.

---

{% include-markdown "signature-core.md" %}
