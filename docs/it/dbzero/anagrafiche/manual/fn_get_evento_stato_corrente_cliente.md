## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_evento_stato_corrente_cliente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.clienti](/dbzero/anagrafiche/tabelle/clienti) — le date di sospensione e riattivazione
> * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente) — lo stato, che la funzione non ripete
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_clienti_guard_stato_date](/dbzero/anagrafiche/funzioni/trgfn_clienti_guard_stato_date) — le date che ogni stato pretende

---

### 🎯 Scopo Principale

`anagrafiche.fn_get_evento_stato_corrente_cliente` dice qual è l'ultimo evento fra sospensione e riattivazione
di un cliente: la sua data e il suo tipo (`SOSPENSIONE` o `RIATTIVAZIONE`), oppure niente se il cliente non ne
ha.

---

### Solo i due eventi che si ripetono

Delle quattro date del cliente, la funzione guarda le due centrali. L'attivazione apre la vita del cliente e la
chiusura la chiude: non sono eventi da riepilogare. La sospensione e la riattivazione invece si alternano, e la
scheda del cliente mostra l'ultima.

Lo stato non è nel risultato: c'è già in `stato_cliente_id`, e una seconda etichetta direbbe la stessa cosa in
un altro modo.

---

### Come sceglie

* Nessuna delle due date: nessun evento.
* Una sola delle due: quella.
* Tutte e due: la più recente. A parità di giorno vince la riattivazione, che nel percorso normale viene dopo.

Una riattivazione senza sospensione esce come riattivazione: la funzione legge, non giudica la coerenza delle
date. `anagrafiche.trgfn_clienti_guard_stato_date` pretende la data di riattivazione quando un sospeso torna
attivo, ma non vieta una riattivazione scritta senza sospensione.

La lettura è sotto la RLS di chi chiama: un cliente fuori perimetro risponde come uno che non esiste.

---

### ⚠️ Che cosa oggi non copre

* **È dichiarata parallel safe**, ma sui due rifiuti chiama `script.fn_log_and_raise_error`, che scrive il log
  e non lo è.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — cliente non indicato, o con un identificativo non positivo.
* `E_VALORE_MANCANTE` — il cliente non esiste, o chi chiama non lo vede.

---

### Test

* `db/pgtap/anagrafiche/test-fn-get-evento-stato-corrente-cliente-v1.sql` — le cinque combinazioni delle due
  date (pareggio compreso) e i due rifiuti.

---

### Note di migrazione

* 2026-04-28 — nasce, e prende il posto del confronto fra le due date fatto nella scheda del cliente lato
  interfaccia.

---

{% include-markdown "signature-core.md" %}
