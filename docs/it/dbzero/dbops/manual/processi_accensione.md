## 📘 Documentazione Concettuale – Tabella `dbops.processi_accensione`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il default per ambiente che la riga scavalca
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — l'ambiente di questa installazione
> * [storico.processi_accensione](/dbzero/storico/tabelle/processi_accensione) — la storia dei gesti
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — mostra un processo spento come `SPENTO`
>
> Approfondimento funzioni:
>
> * [dbops.fn_imposta_accensione_processo](/dbzero/dbops/funzioni/fn_imposta_accensione_processo) — il verbo che scrive la riga
> * [dbops.trgfn_processi_accensione_guard](/dbzero/dbops/funzioni/trgfn_processi_accensione_guard) — i limiti della scelta a mano
> * [dbops.fn_processo_acceso_su_valori](/dbzero/dbops/funzioni/fn_processo_acceso_su_valori) — la regola che decide se la riga conta
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello che le sveglie chiedono prima di partire
>
> Guide:
>
> * [Framework di Automazione DB](/guide/automazione-db) — i processi automatici visti dall'interfaccia

---

### 🎯 Scopo Principale

La scelta a mano di questa installazione sulla sveglia di un processo automatico: «qui lo spengo»,
«qui lo accendo» o «qui torna al default», col motivo. Scavalca il default per ambiente che il
catalogo [dbops.processi](/dbzero/dbops/tabelle/processi) dichiara.

---

### La riga dice l'ultimo gesto

| La riga | Che cosa vale |
| --- | --- |
| `acceso` vero o falso | acceso o spento a mano, al posto del default |
| `acceso` vuoto | qualcuno l'ha **rimesso al default**: vale il default, e la riga dice chi, quando e perché |
| nessuna riga | nessuno l'ha mai toccato: vale il default |

Tornare al default **non cancella** la riga: la riscrive con `acceso` vuoto e il motivo, come gli
altri due gesti. C'è una riga al più per processo.

È dato di **macchina**, come `processi_identita`: nessun seed, la scrive l'operatore dal drawer
dei processi attraverso il verbo
[fn_imposta_accensione_processo](/dbzero/dbops/funzioni/fn_imposta_accensione_processo).

---

### I limiti della scelta a mano

Li dice il guard [trgfn_processi_accensione_guard](/dbzero/dbops/funzioni/trgfn_processi_accensione_guard),
su ogni inserimento e modifica, nell'ordine in cui l'operatore li legge:

| Cosa si chiede | Risposta |
| --- | --- |
| una scelta su un processo senza sveglia (canale `CODA`, o ritirato con `obsoleto_dal`) | rifiutata |
| spegnere un processo **non spegnibile** | rifiutato; confermarlo acceso, o rimetterlo al default, è ammesso |
| accendere, in produzione, un processo **non accendibile in produzione** | rifiutato |
| la stessa accensione con l'ambiente non dichiarato | rifiutata: il divieto non sa decidere |
| una scelta senza motivo | rifiutata, anche per tornare al default |

⚠️ **Il catalogo può cambiare dopo la riga.** Se un processo diventa non spegnibile dopo che una
riga l'ha spento, o una riga accesa precede il divieto di produzione, la regola dello stato
effettivo **ignora** la riga: vale il default. Una riga così non si riscrive accesa (nemmeno
ritoccando il solo motivo); si può spegnere o rimettere al default.

---

### La storia dei gesti, e chi li ha fatti

Ogni modifica e ogni cancellazione lascia una versione nella gemella
`storico.processi_accensione`: la tabella è nell'ambito delle automazioni del database e nel
registro dello storico.

**Chi** è la persona, non il ruolo del database: `user_insert` e `user_update` li scrive l'audit
automatico, che legge l'utente collegato al backend.

⚠️ I trigger dell'audit e dello storico nascono dalle automazioni: alla migrazione in CI e a ogni
installazione, e su un database di sviluppo dal giro dei job `automations_*`. Fra la migrazione e
quel giro la tabella non ha storia.

La riga segue il processo: cancellato il processo, la sua scelta a mano se ne va con lui.

---

### Codici errore

* `E_PROCESSO_SENZA_SVEGLIA` — il processo è `CODA` o ritirato.
* `E_PROCESSO_NON_SPEGNIBILE` — si spegne un processo non spegnibile.
* `E_PROCESSO_NON_ACCENDIBILE_IN_PRODUZIONE` — si accende in produzione un processo non accendibile.
* `E_CONFIG_MANCANTE` — la stessa accensione con l'ambiente non dichiarato.
* `E_PROCESSO_ACCENSIONE_MOTIVO_OBBLIGATORIO` — il motivo è vuoto; `chk_processi_accensione_motivo`
  resta come vincolo del dato.

---

### Test

* `db/pgtap/dbops/test-processi-accensione-v1.sql` — il verbo e ciò che ne segue: spegnere,
  riaccendere, tornare al default con la riga che resta, i rifiuti, l'audit con l'utente del
  backend e la versione di storico per ogni gesto.
* `db/pgtap/dbops/test-processi-accensione-produzione-v1.sql` — in una produzione costruita, la
  riga accesa scritta prima non accende, e non si riscrive accesa.
* `db/pgtap/dbops/test-installazione-ambiente-v1.sql` — con l'ambiente non dichiarato la scelta a
  mano basta a decidere.

---

### Note di migrazione

* 2026-10-16 — nasce col default di accensione per ambiente (`brief-db-processi-accensione-per-ambiente`).
* 2026-10-17 — `acceso` diventa nullable e «torna al default» smette di cancellare la riga; la
  tabella entra nello storico, e chi e quando li scrive l'audit invece del verbo. Prima il verbo
  scriveva l'utente, e dal backend risultava sempre il ruolo applicativo.
* 2026-10-18 — nasce il divieto di accensione in produzione.

---

{% include-markdown "signature-core.md" %}
