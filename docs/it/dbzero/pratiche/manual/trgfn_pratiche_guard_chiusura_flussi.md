## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_guard_chiusura_flussi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la tabella sorvegliata
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — il lavoro che deve essere finito
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_chiusura_pratica](/dbzero/pratiche/funzioni/fn_check_chiusura_pratica) — gli obbligatori non completati e ancora percorribili
> * [pratiche.fn_pratica_flussi_aperti](/dbzero/pratiche/funzioni/fn_pratica_flussi_aperti) — i flussi istanziati non terminali
> * [pratiche.fn_check_pratica_chiudibile](/dbzero/pratiche/funzioni/fn_check_pratica_chiudibile) — lo stesso predicato, usato dall'auto-chiusura
> * [pratiche.trgfn_pratiche_guard_transizione](/dbzero/pratiche/funzioni/trgfn_pratiche_guard_transizione) — la legalità della transizione

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_guard_chiusura_flussi` impedisce di portare una pratica a
`CHIUSA` quando ha ancora lavoro da fare.

Le condizioni sono due, verificate in quest'ordine:

* **obbligatori mancanti** — template obbligatori non completati e ancora percorribili
  (`pratiche.fn_check_chiusura_pratica`). Il ramo morto di un bivio, il cui prerequisito non è più
  soddisfacibile, non blocca;
* **flussi aperti** — flussi istanziati in uno stato non terminale (`pratiche.fn_pratica_flussi_aperti`):
  anche uno step opzionale avviato e lasciato aperto impedisce la chiusura.

È lo stesso predicato dell'auto-chiusura: chiusura manuale e automatica non possono divergere.

---

### Le regole

* Scatta `BEFORE UPDATE OF stato_id`, riga per riga, su `pratiche.pratiche`, nella fase dei guard, e
  solo quando lo stato cambia davvero e il nuovo stato è `CHIUSA`. `ANNULLATA` resta libera: si annulla
  anche una pratica a metà.
* L'errore elenca ciò che blocca: i codici dei template obbligatori mancanti, oppure i flussi aperti
  con il loro stato.
* Questo guard valida il contenuto della pratica; `pratiche.trgfn_pratiche_guard_transizione` la
  legalità del passaggio. Nella fase dei guard scatta prima, per ordine alfabetico: l'errore di
  contenuto prevale.
* Una pratica senza obbligatori e senza flussi aperti non è toccata.

**La via d'uscita** per i flussi aperti: portarli ad `ANNULLATO`, poi ripetere la chiusura.

---

### Codici errore

* `E_PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI` — chiusura con obbligatori non completati e ancora
  percorribili.
* `E_PRATICHE_CHIUSURA_FLUSSI_APERTI` — chiusura con flussi istanziati non terminali.

---

### Test

* `pratiche/test-chiusura-nessun-lavoro-pendente` — chiusura manuale bloccata con un flusso opzionale
  aperto, sbloccata dopo averlo annullato.

---

{% include-markdown "signature-core.md" %}
