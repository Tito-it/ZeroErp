## 📘 Documentazione Concettuale – Tabella `dbops.emittente_modi`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli) — la via di un bersaglio è un modo di questo registro
>
> Approfondimento funzioni:
>
> * [script.fn_resolve_emittente_fiscale_id](/dbzero/script/funzioni/fn_resolve_emittente_fiscale_id) — il risolutore generato da queste righe
> * [script.fn_resolve_emittente_sr_id](/dbzero/script/funzioni/fn_resolve_emittente_sr_id) — il gemello in convenzione soggetto-ruolo, generato dalle stesse righe
> * [dbops.fn_risolutore_emittente_corpo](/dbzero/dbops/funzioni/fn_risolutore_emittente_corpo) — scrive il corpo dei due risolutori, dopo aver controllato il registro
> * [dbops.fn_genera_risolutori_emittente](/dbzero/dbops/funzioni/fn_genera_risolutori_emittente) — riscrive i risolutori quando il registro cambia
> * [dbops.trgfn_emittente_modi_solo_migrazione](/dbzero/dbops/funzioni/trgfn_emittente_modi_solo_migrazione) — il registro lo scrive solo il migrate
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope) — il guard di scrittura, che riceve il modo come primo argomento

---

### 🎯 Scopo Principale

Dice **come una riga raggiunge il suo emittente**, una volta sola per ogni tipo di riga. Ogni riga
del registro è un **modo**: il nome che il guard di scrittura, le policy e i verbi passano al
risolutore dell'emittente per chiedergli «di chi è questa riga?».

È la sede unica dei modi e della loro strada. I due risolutori non si scrivono a mano: li genera il
migrate da queste righe.

---

### ⭐ Una strada in tre forme

Ogni modo parte da una tabella, ci cerca la riga per la sua chiave (`colonna_chiave`, quasi sempre
`id`) e trova l'emittente nella `colonna`, in uno di tre modi:

| `forma` | Che cosa contiene la colonna | Esempi |
| --- | --- | --- |
| `PK` | l'id dell'emittente fiscale | `ddt`, `ordine`, `magazzino`, `pratica` |
| `SR` | il soggetto-ruolo dell'emittente | `fattura`, `listino`, `commessa`, `lotto` |
| `SALTO` | la chiave verso la testata, che ha il suo modo (`modo_padre`) | le righe dei documenti, `listino_versione`, `movimento` |

Un salto può portare a un altro salto: `ente_incasso` va al conto bancario (`conto_bancario`), e il
conto porta il soggetto-ruolo. La catena finisce sempre su una radice (`PK` o `SR`).

Due modi sono le radici delle due convenzioni: `fiscale` (il valore è già l'id dell'emittente
fiscale, e si controlla solo che esista) e `soggetto_ruolo` (l'emittente fiscale di quel
soggetto-ruolo).

---

### Come si aggiunge un modo

Si aggiunge una riga al seed `80_data/sql/dbops/emittente_modi.csv` e si applica la migrazione. Dopo
il seed, il migrate riscrive i due risolutori. Non si scrive nessun ramo a mano: il migrate
successivo lo cancellerebbe, riportando il risolutore al registro.

⚠️ **Il registro lo scrive solo il migrate.** Da queste righe nasce la funzione che decide di chi è
ogni riga per le policy e i guard di scrittura, cioè il controllo che separa le aziende. Una
scrittura dall'applicazione riceve `E_EMITTENTE_MODI_NON_SCRIVIBILE`.

⚠️ Togliere una riga dal CSV non toglie il modo: il caricamento aggiunge e aggiorna, non cancella. Il
ritiro di un modo va fatto con una migrazione sua, dopo aver cercato i guard e le dichiarazioni che lo
nominano.

---

### Che cosa viene controllato

Prima di scrivere i risolutori, il migrate controlla il registro: la tabella esiste, ha la colonna
chiave e la colonna, e la catena dei salti arriva a una radice. Se qualcosa non torna, i risolutori
non si scrivono e il migrate si ferma con `E_EMITTENTE_MODI_INVALIDO`, che elenca tutti i problemi.

I vincoli della tabella aggiungono: un `SALTO` ha sempre il suo `modo_padre`, una radice no; il
nome del modo è fatto di minuscole, cifre e trattini bassi.

---

### Test

* `dbops/test-emittente-modi-registro-v1`: i risolutori vivi sono quelli che il registro genera; i
  salti, le due radici e le due convenzioni su tabelle costruite; il modo sconosciuto; il registro
  con una colonna che non c'è; ogni modo nominato da un guard, una funzione o una policy è nel
  registro.
* `dbops/test-emittente-modi-solo-migrazione-v1` (come applicazione): scrivere, cambiare, togliere
  e svuotare il registro sono respinti.

---

### Note di migrazione

* 2026-11-08 — perde `tx_id`, `data_update` e `user_update`, che nessun trigger scriveva: la tabella
  la scrive solo la migrazione, dal CSV (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis). Esce dal registro `dbops.marcatori_automazione_debito`.

---

{% include-markdown "signature-core.md" %}
