## 📘 Documentazione Concettuale – Vista `documenti.vw_template_personalizzati_scarto`

> **Ultimo aggiornamento**: 14 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [documenti.template_documenti](/dbzero/documenti/tabelle/template_documenti) — il modello dell'azienda e lo standard
> * [documenti.template_documenti_versioni](/dbzero/documenti/tabelle/template_documenti_versioni) — l'origine dichiarata di una copia e la forma dei dati che legge
>
> Approfondimento viste:
>
> * [documenti.vw_template_versioni_stampabili](/dbzero/documenti/views/vw_template_versioni_stampabili) — le due versioni confrontate
>
> Approfondimento funzioni:
>
> * [documenti.fn_personalizza_template_standard](/dbzero/documenti/funzioni/fn_personalizza_template_standard) — crea la copia, partendo dallo stesso riferimento
> * [documenti.trgfn_template_documenti_versioni_guard_derivata_da](/dbzero/documenti/funzioni/trgfn_template_documenti_versioni_guard_derivata_da) — l'origine di una copia è una versione standard della stessa coppia
>
> Guide:
>
> * [Documenti e Stampe](/guide/documenti-e-stampe) — §4.3, lo scarto

---

### 🎯 Scopo Principale

Un modello personalizzato da un'azienda non riceve più gli aggiornamenti dello standard da cui è
partito. La vista dice, per ogni modello dell'azienda che stampa oggi, quanto è rimasto indietro, così
la lista Modelli documento lo può segnalare prima che una stampa si fermi.

---

### Che cosa si confronta

Due versioni, tutte e due quelle con cui si stampa oggi:

* la versione della copia;
* la versione dello **standard di riferimento**: quello da cui la copia deriva, oppure, per una copia
  senza origine dichiarata, il predefinito standard dello stesso tipo e della stessa sorgente.

È lo stesso riferimento da cui parte «personalizza»: una copia appena nata e pubblicata è `ALLINEATA`,
e la copia di uno standard non predefinito si confronta con quello standard.

L'origine la dichiara la versione che ha ripreso lo standard; le versioni successive della stessa copia
la **ereditano** senza ripeterla: vale l'origine della versione più recente che la dichiara.

---

### Lo stato, in quest'ordine

| Stato | Significato |
| --- | --- |
| `CONTESTO_SUPERATO` | la versione in uso legge i dati in una forma più vecchia di quella dello standard: è il caso che si ferma alla stampa, e per questo viene per primo |
| `ORIGINE_NON_DICHIARATA` | nessuna versione della copia dice da dove viene: un modello scritto da zero, o nato prima dello standard |
| `ALLINEATA` | la copia parte dalla versione con cui lo standard stampa oggi |
| `STANDARD_AVANTI` | parte da una versione standard precedente: stampa, ma non ha l'aggiornamento |

⚠️ La forma dei dati che il sistema prepara per la stampa è una costante del backend, che il database
non conosce. Il riferimento è lo standard: le sue versioni le pubblicano i changeSet che accompagnano
ogni cambio di forma.

---

### Una riga solo se tutte e due stampano

Lo scarto si misura fra due cose che stampano: un modello dell'azienda spento, o senza una versione che
stampi oggi, non ha riga, e nemmeno lo standard. Il modello standard non ha mai riga: non è una copia.

---

### ⚠️ Che cosa oggi non copre

* **Lo standard di origine che non stampa più.** Se lo standard da cui la copia deriva viene spento, o
  resta senza una versione valida oggi, la copia sparisce dalla vista: non si confronta con il
  predefinito della coppia, e la lista la mostra senza stato, come se non fosse una copia. Lo stesso
  accade a una copia senza origine quando la coppia non ha un predefinito standard che stampa.

---

### Test

* `db/pgtap/documenti/test-documenti-template-standard-v1.sql` — i quattro stati, e l'origine ereditata
  dalla versione precedente.
* `db/pgtap/documenti/test-documenti-personalizza-v1.sql` — la copia appena pubblicata è `ALLINEATA`;
  la copia di uno standard non predefinito si confronta con lui; senza origine si confronta col
  predefinito.

---

### Note di migrazione

* 2026-10-20 — nasce, per segnalare le copie rimaste indietro.
* 2026-10-21 — fino a qui il riferimento era sempre lo standard predefinito della coppia, sulla sua
  pubblicata col numero più alto senza guardare `attivo` né la data: la copia di uno standard non
  predefinito si confrontava con un altro modello. Da qui le due versioni sono quelle che stampano oggi.

---

{% include-markdown "signature-core.md" %}
