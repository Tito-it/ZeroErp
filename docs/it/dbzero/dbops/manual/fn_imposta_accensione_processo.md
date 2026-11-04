## 📘 Documentazione Concettuale – Funzione `dbops.fn_imposta_accensione_processo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi_accensione](/dbzero/dbops/tabelle/processi_accensione) — la riga che il verbo scrive
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il default per ambiente a cui si torna
> * [storico.processi_accensione](/dbzero/storico/tabelle/processi_accensione) — la storia dei gesti
>
> Approfondimento funzioni:
>
> * [dbops.trgfn_processi_accensione_guard](/dbzero/dbops/funzioni/trgfn_processi_accensione_guard) — i limiti, che il verbo non ripete
> * [dbops.fn_processo_acceso_dichiarato](/dbzero/dbops/funzioni/fn_processo_acceso_dichiarato) — lo stato effettivo che il verbo restituisce
>
> Guide:
>
> * [Framework di Automazione DB](/guide/automazione-db) — i processi automatici visti dall'interfaccia

---

### 🎯 Scopo Principale

Il verbo della scelta a mano: accende, spegne o rimette al default per ambiente la sveglia di un
processo su questa installazione, col motivo, e restituisce lo stato effettivo dopo il gesto.

---

### Tre gesti, una riga

| `p_acceso` | Effetto |
| --- | --- |
| vero | la sveglia è accesa qui, qualunque cosa dica il default (in produzione, non su un processo non accendibile) |
| falso | la sveglia è spenta qui (non su un processo non spegnibile) |
| vuoto | la sveglia torna al default per ambiente |

Tutti e tre scrivono la riga del processo in `dbops.processi_accensione` (la creano o la
riscrivono), e tutti e tre vogliono un motivo, anche il ritorno al default: chi viene dopo deve
capire perché. La riga è l'ultimo gesto; la storia sta in `storico.processi_accensione`.

Lo stato restituito è quello della regola: un non spegnibile risulta acceso qualunque sia il gesto;
il risultato è vuoto solo se si è tornati al default con l'ambiente non dichiarato.

---

### ⛔ Che cosa il verbo non fa

* **Non ripete i limiti.** Processo senza sveglia, non spegnibile, non accendibile in produzione,
  motivo vuoto: li dice il guard della tabella, perché la regola è del dato e vale per chiunque
  scriva la riga.
* **Non scrive chi e quando.** Li scrive l'audit automatico, che legge l'utente collegato al
  backend: così la riga e la storia dicono la persona, non il ruolo del database.
* **Non decide chi può.** È `SECURITY INVOKER`: il permesso è del backend, come per «Esegui ora».

---

### Codici errore

* `E_PROCESSO_NON_TROVATO` — il codice del processo non è a catalogo.
* Dal guard della tabella: `E_PROCESSO_SENZA_SVEGLIA`, `E_PROCESSO_NON_SPEGNIBILE`,
  `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE`, `E_CONFIG_MANCANTE` (accensione di un non accendibile
  con l'ambiente non dichiarato), `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO`.

---

### Test

* `db/pgtap/dbops/test-processi-accensione-v1.sql` — è `SECURITY INVOKER`; spegne, riaccende e
  rimette al default con lo stato restituito, la sveglia e il panorama che seguono; i rifiuti; la
  riga che resta col default; l'audit e lo storico di ogni gesto.
* `db/pgtap/dbops/test-processi-accensione-produzione-v1.sql` — in una produzione costruita:
  l'accensione di un non accendibile rifiutata, lo spegnimento e il default ammessi, un
  accendibile spento di default che si accende.
* `db/pgtap/dbops/test-installazione-ambiente-v1.sql` — la scelta a mano con l'ambiente non
  dichiarato.

---

### Note di migrazione

* 2026-10-16 — nasce col default di accensione per ambiente (`brief-db-processi-accensione-per-ambiente`).
* 2026-10-17 — il ritorno al default smette di cancellare la riga e vuole il motivo; il verbo
  smette di scrivere chi e quando.

---

{% include-markdown "signature-core.md" %}
