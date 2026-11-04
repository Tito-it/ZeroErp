## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_concedi_azione`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni) — l'eccezione utente sull'azione
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree) — l'eccezione utente sull'area, quando serve
> * [config.azioni_processo](/dbzero/config/tabelle/azioni_processo) — il catalogo delle azioni e il loro livello minimo d'area
>
> Approfondimento funzioni:
>
> * [script.fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione) — il guard che rende necessario concedere l'azione
> * [script.fn_area_consente_azione](/dbzero/script/funzioni/fn_area_consente_azione) — il tetto d'area
> * [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area) — il livello d'area di oggi dell'utente
> * [dbops.fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore) — l'operatore di fixture, che nasce senza azioni né aree
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — il permesso si costruisce, non si cerca

---

### 🎯 Scopo Principale

Concede a un utente di un test un'**azione di processo**, e fa in modo che valga davvero.
Restituisce l'id dell'eccezione utente sull'azione.

---

### ⭐ Il permesso si costruisce nel test

Serve ai test dei verbi che controllano un'azione con
[fn_guard_azione](/dbzero/script/funzioni/fn_guard_azione): l'operatore di
[fn_pgtap_crea_emittente_operatore](/dbzero/dbops/funzioni/fn_pgtap_crea_emittente_operatore)
è tecnico, non super admin, e non ha né azioni né aree. Il permesso quindi non si cerca nei
dati: si concede.

La fixture scrive un'eccezione utente sull'azione abilitata, valida da oggi (il giorno
operativo) e senza scadenza: la stessa forma che scrive il pannello di amministrazione. È
idempotente: se l'eccezione c'è già, la riabilita e la riapre da oggi.

---

### ⭐ L'azione vale solo se l'area arriva al suo minimo

Per il tetto d'area un'azione concessa non basta: anche l'area dell'azione deve arrivare al
livello minimo che l'azione chiede. Se il livello d'area di oggi dell'utente non ci arriva,
la fixture scrive anche un'eccezione utente sull'area, **al minimo** e non di più, valida da
oggi.

⛔ Se il test ha già scritto un'eccezione d'area valida oggi che tiene l'area sotto il
minimo, la fixture non la scavalca: è una scelta del test, e la fixture solleva dicendo che
l'azione non varrebbe.

---

### ⚠️ Scrive come l'applicazione

La fixture gira coi privilegi di chi la chiama, quindi valgono i trigger delle due tabelle:
un'azione disattivata la rifiuta il trigger che pretende il padre attivo, ed è giusto che il
test lo veda.

---

### Codici errore

Valgono quelli dei trigger delle tabelle delle eccezioni. Un'azione che non esiste, o
un'area chiusa da un'eccezione del test, sono eccezioni senza codice sollevate dalla
fixture: è la fixture a essere chiamata male.

---

### Test

Nessun pgTAP dedicato: la usano i test dei verbi con permesso, per esempio
`db/pgtap/magazzino/test-verbi-permesso-v1.sql`, e quelli del tetto d'area
(`db/pgtap/script/test-permessi-tetto-area-v1.sql`).

---

### Note di migrazione

* 2026-09-24 — nasce con i verbi di magazzino con permesso (`brief-db-magazzino-verbi-con-permesso`).
* 2026-10-04 — apre anche l'area al minimo dell'azione (`brief-db-permessi-tetto-area`).
* 2026-10-09 — «oggi» è il giorno operativo nel fuso dell'azienda.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
