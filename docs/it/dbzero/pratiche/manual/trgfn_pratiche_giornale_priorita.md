## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_giornale_priorita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica di cui cambia la priorità
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove si registra l'evento
> * [config.priorita_pratiche](/dbzero/config/tabelle/priorita_pratiche) — il catalogo delle priorità

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_giornale_priorita` registra nel giornale l'evento
`PRIORITA_CAMBIATA` quando la priorità di una pratica cambia davvero.

---

### La riga di giornale

* È un evento della pratica: il flusso resta vuoto.
* L'origine è `SISTEMA`.
* Il dettaglio porta la priorità precedente e quella nuova, come id del catalogo.
* Il `tx_id` è quello della pratica o, se manca, quello della sessione: l'evento resta correlato alla
  transazione che ha cambiato la priorità.

---

### Quando scatta

Dopo l'aggiornamento della priorità di una pratica, e solo se il valore è cambiato: riscrivere la stessa
priorità non produce eventi.

---

### Test

* `pratiche/test-trigger-giornale-pratiche` — gli eventi di giornale della pratica.

---

{% include-markdown "signature-core.md" %}
