## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_giornale`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la tabella sorvegliata
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove finiscono gli eventi
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_giornale_ins](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins) — l'apertura di una sospensione
> * [pratiche.trgfn_sospensioni_giornale_riattivazione](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_riattivazione) — la sua chiusura

---

### 🎯 Scopo Principale

Le due trigger function che registrano nel giornale della pratica l'apertura e la chiusura di una
sospensione.

⚠️ Nel database non esiste una funzione `trgfn_sospensioni_giornale`: il nome di questa pagina è il
prefisso della famiglia delle due funzioni reali, `_ins` e `_riattivazione`, documentate insieme perché
sono i due lati dello stesso fatto. Ognuna ha la sua scheda.

---

### Le due funzioni

* `pratiche.trgfn_sospensioni_giornale_ins` — dopo l'inserimento di una sospensione scrive
  `SOSPENSIONE_REGISTRATA`, con motivo, data di inizio, riattivazione prevista e livello.
* `pratiche.trgfn_sospensioni_giornale_riattivazione` — quando la data di fine passa da vuota a
  valorizzata scrive `SOSPENSIONE_CHIUSA`, con le due date, il motivo e il livello. Una data di fine che
  cambia dopo essere stata scritta non produce un secondo evento.

Entrambe scattano `AFTER`, riga per riga, su `pratiche.sospensioni`, nella fase finale.

---

### Le regole comuni

* Il livello è `PRATICA` quando la sospensione non indica un flusso, `FLUSSO` altrimenti; la riga di
  giornale porta la pratica e, se c'è, il flusso.
* L'origine dell'evento è `SISTEMA`.
* La riga di giornale porta il `tx_id` della sospensione, che il trigger `tx_id` di
  `pratiche.sospensioni` valorizza sempre prima dell'inserimento; il ripiego su un identificativo nuovo
  è solo difensivo.

---

### Test

* `pratiche/test-sospensioni-tempi` — gli eventi di sospensione e riattivazione nel ciclo dei tempi.

---

{% include-markdown "signature-core.md" %}
