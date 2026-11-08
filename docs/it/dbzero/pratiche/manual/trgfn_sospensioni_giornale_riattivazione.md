## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_sospensioni_giornale_riattivazione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.sospensioni](/dbzero/pratiche/tabelle/sospensioni) — la tabella su cui è montata
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — dove scrive
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_sospensioni_giornale_ins](/dbzero/pratiche/funzioni/trgfn_sospensioni_giornale_ins) — l'evento di apertura
> * [pratiche.trgfn_sospensioni_riattiva](/dbzero/pratiche/funzioni/trgfn_sospensioni_riattiva) — la riattivazione dei flussi

---

### 🎯 Scopo Principale

Chiude il paio aperto da `trgfn_sospensioni_giornale_ins`: scrive nel giornale della pratica
l'evento `SOSPENSIONE_CHIUSA` quando la sospensione viene riattivata, cioè quando
`data_fine` passa da nulla a valorizzata.

Insieme, i due eventi rendono leggibile nel giornale l'intero intervallo di fermo — inizio,
motivo, fine — senza dover interrogare la tabella delle sospensioni.

---

### Aggancio

È montata `AFTER UPDATE OF data_fine` su `pratiche.sospensioni`, riga per riga, nella fase finale
(`_z90_`), con una condizione sul trigger: scatta solo quando `data_fine` era vuota e diventa
valorizzata.

---

### Che cosa scrive

| Colonna | Valore |
|---------|--------|
| `pratica_id` / `flusso_id` | copiati dalla sospensione |
| `azione` | `'SOSPENSIONE_CHIUSA'` |
| `origine` | `'SISTEMA'` |
| `dettaglio` | `sospensione_id`, `data_inizio`, `data_fine`, `motivo`, e `livello` (`PRATICA` se la sospensione non ha flusso, altrimenti `FLUSSO`) |
| `tx_id` | quello della sospensione; se manca, un identificativo nuovo |

Il `dettaglio` riporta **entrambe** le date, non solo quella di chiusura: la riga di
giornale è così autosufficiente e la durata del fermo si legge senza risalire all'evento
di apertura.

---

### ⚠️ La condizione è nel `WHEN`, e registra solo la *prima* chiusura

Il filtro «da vuota a valorizzata» vive sulla dichiarazione del trigger, non nel corpo. La funzione, invocata, scrive **sempre**. Due conseguenze:

* **Correggere una `data_fine` già impostata non lascia traccia.** Un `UPDATE` da un valore
  a un altro non soddisfa il `WHEN`, quindi il giornale continua a mostrare la data della
  prima chiusura mentre la tabella ne ha un'altra. Per l'operatore che legge il giornale la
  correzione è invisibile.
* **Riaprire e richiudere genera un secondo evento.** Portare `data_fine` a `NULL` e poi
  rivalorizzarla soddisfa di nuovo il `WHEN`: nel giornale compaiono due
  `SOSPENSIONE_CHIUSA` per la stessa sospensione. È corretto — sono due chiusure reali — ma
  chi conta gli eventi per dedurre il numero di sospensioni sbaglia il conto.

⚠️ Chi riaggancia questa funzione a un trigger nuovo deve **riportare anche il `WHEN`**:
senza, ogni `UPDATE` di `data_fine` scrive una riga di giornale.

---

### Codici errore

Nessuno: la funzione non solleva.

---


{% include-markdown "signature-core.md" %}
