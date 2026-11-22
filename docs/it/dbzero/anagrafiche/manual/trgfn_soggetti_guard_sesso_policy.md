## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_guard_sesso_policy`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella che il guard presidia
> * [config.tipi_soggetto_dettaglio](/dbzero/config/tabelle/tipi_soggetto_dettaglio) — la natura, con la sua `sesso_policy`
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_crea_soggetto_pf](/dbzero/anagrafiche/funzioni/fn_crea_soggetto_pf) — la porta che passa il sesso così com'è
> * [anagrafiche.trgfn_soggetti_guard_cambio_natura](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_cambio_natura) — il cambio di natura, che parla prima

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_guard_sesso_policy` fa rispettare al sesso di un soggetto la regola della sua natura:
obbligatorio, facoltativo o da non indicare.

---

### Il valore lo dice un vincolo, il «quando» la natura

Che il sesso sia `M`, `F`, `X` o NULL lo dice il vincolo `chk_soggetti_sesso`, sulla riga. Quando serve sta in
un'altra tabella, che un vincolo di riga non può leggere: lo dice `sesso_policy` della natura, e lo legge questo
guard.

* `REQUIRED` — il sesso c'è: NULL è rifiutato. `X` («serve, ma non si può stabilire») vale come indicato.
* `OPTIONAL` — tutto è ammesso.
* `NONE` — il sesso non si indica: un valore è rifiutato.

Il catalogo delle nature lega `NONE` alle nature che non sono persone fisiche: una società o un ente non hanno
sesso, un privato lo deve avere, una ditta individuale può.

---

### Anche il cambio di natura

Il guard scatta alla nascita e quando cambiano il sesso o la natura: una società che diventa una persona deve
portare il sesso, una persona che diventa società deve lasciarlo, nella stessa scrittura. Il sesso non lo cambia
nessuno da sé.

---

### Senza natura tace

Un soggetto senza natura non ha una regola da leggere, e il guard lo lascia passare, come quello della presenza di
CF e P.IVA. Con una natura che non esiste tace anche lui, e il rifiuto arriva da chi parla dopo (per un
soggetto italiano, con un errore tecnico del controllo del formato; altrimenti dalla chiave esterna).

---

### Codici errore

* `E_SESSO_OBBLIGATORIO` — la natura pretende il sesso e manca.
* `E_SESSO_NON_AMMESSO` — la natura non ammette il sesso e c'è.

Il campo dell'errore è `sesso`, così il form sa quale segnare; il messaggio nomina la natura.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-sesso-policy-v1.sql` — il vincolo dei valori, la colonna senza default, la
  regola per natura; la società senza sesso e con un sesso rifiutato; il privato senza sesso rifiutato, anche da
  un inserimento diretto e dalla creazione dell'operatore, e con `X` ammesso; la ditta individuale senza sesso; la
  ditta che diventa privato senza sesso rifiutata; il soggetto senza natura che passa.

---

### Note di migrazione

* 2026-10-09 — nasce quando il sesso perde il default `M` e il valore `S` («soggetto generico»): da allora
  quando serve lo dice la natura.

---

{% include-markdown "signature-core.md" %}
