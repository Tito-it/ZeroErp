## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_guard_contesto`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la tabella che il guard presidia
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli) — il ramo del ruolo
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — il ramo dell'istanza
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il billing account della pratica
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_ruolo_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_ruolo_di_altro_soggetto) — la regola «il ruolo è del soggetto», comune a più guard
> * [anagrafiche.fn_istanza_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_istanza_di_altro_soggetto) — la regola «l'istanza è del soggetto»
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_guard_contesto` valida la coerenza del contesto
anagrafico di una pratica: soggetto, ruolo, istanza utility e billing account devono parlare dello
stesso cliente.

Tutti i campi sono facoltativi: una pratica interna li ha tutti vuoti.

---

### Il modello a due rami

Ruolo e istanza pendono entrambi dal soggetto, indipendenti fra loro:

* il ramo del **ruolo**, per le pratiche su un ruolo (cliente, fornitore…);
* il ramo dell'**istanza utility**, che appartiene al soggetto e non al ruolo.

Un'istanza può quindi stare sulla pratica anche senza ruolo. Il billing account, quando c'è, lega
invece la pratica al ruolo: l'istanza nasce col suo billing account, e il ruolo cliente con lui.

---

### Le regole

| # | Regola | Errore |
| --- | --- | --- |
| 1 | Un ruolo richiede il soggetto | `E_PRATICHE_RUOLO_SENZA_SOGGETTO` |
| 2 | Un'istanza richiede il soggetto | `E_PRATICHE_ISTANZA_SENZA_SOGGETTO` |
| 3 | Il ruolo appartiene al soggetto della pratica | `E_PRATICHE_RUOLO_NON_COERENTE` |
| 4 | L'istanza appartiene al soggetto della pratica | `E_PRATICHE_ISTANZA_NON_COERENTE` |
| 5 | Il billing account è del ruolo della pratica: un ruolo assente è incoerente quanto uno diverso | `E_PRATICHE_BA_NON_COERENTE` |

* La regola 2 sarebbe coperta anche dalla 4, ma è esplicita per dare un messaggio che dice la causa.
* Le regole 3 e 4 passano dai building block `anagrafiche.fn_ruolo_di_altro_soggetto` e
  `anagrafiche.fn_istanza_di_altro_soggetto`, gli stessi dei controlli su indirizzi, contatti e conti
  del ruolo. Un ruolo o un'istanza che non esistono non sono «non coerenti»: li rifiuta la chiave
  esterna, che dice la causa giusta.
* La regola 5 tiene il legame fra billing account e ruolo. Il legame fra billing account e istanza lo
  tiene la chiave esterna composta, e la presenza dell'istanza quando c'è un billing account il
  `CHECK` `chk_pratiche_ba_con_istanza`.

Il guard scatta all'inserimento e quando cambiano `soggetto_id`, `soggetto_ruolo_id`,
`istanza_utility_id` o `billing_account_id`, non sugli altri campi. Il backend può ripetere la
validazione per dare errori più leggibili, ma è il trigger a garantirla su ogni strada di scrittura.

---

### Codici errore

* `E_PRATICHE_RUOLO_SENZA_SOGGETTO` — regola 1.
* `E_PRATICHE_ISTANZA_SENZA_SOGGETTO` — regola 2.
* `E_PRATICHE_RUOLO_NON_COERENTE` — regola 3.
* `E_PRATICHE_ISTANZA_NON_COERENTE` — regola 4.
* `E_PRATICHE_BA_NON_COERENTE` — regola 5, sul campo `billing_account_id`.

---

### Test

* `pratiche/test-guard-contesto-pratica` — le regole del contesto sulla pratica.
* `anagrafiche/test-istanza-dello-stesso-soggetto-v1` e `anagrafiche/test-un-ba-un-cliente-v1` — i
  building block condivisi e il legame fra billing account e cliente.

---

### Note di migrazione

* 2026-06-11 — ritirata la regola «un'istanza richiede un ruolo» (`PRATICHE_ISTANZA_SENZA_RUOLO`):
  l'istanza pende dal soggetto, non dal ruolo.
* 2026-08-05 — i codici prendono il prefisso `E_`; i vecchi nomi restano a catalogo, ritirati.
* 2026-10-08 — arriva la regola 5 sul billing account, e il trigger scatta anche su
  `billing_account_id`. La pagina parlava di un «prospect puro», un'istanza agganciata senza ruolo
  perché il ruolo cliente arrivava dopo: oggi l'istanza nasce col billing account
  (brief-db-istanza-nasce-col-ba).
* 2026-10-19 — le regole 3 e 4 passano dai building block di `anagrafiche`; codici e frasi non
  cambiano (brief-db-processi-accensione-per-ambiente).

---

{% include-markdown "signature-core.md" %}
