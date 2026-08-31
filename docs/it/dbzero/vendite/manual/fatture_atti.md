## 📘 Documentazione Concettuale – Tabella `vendite.fatture_atti`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)
> • [vendite.contratti](/dbzero/vendite/manual/contratti)
> • [vendite.fatture_riepiloghi_iva](/dbzero/vendite/tabelle/fatture_riepiloghi_iva)

---

### 🎯 Scopo Principale

`vendite.fatture_atti` registra **a quale atto si riferisce una fattura**: il
contratto da cui nasce, con il suo numero, la sua data e i tre codici che una
pubblica amministrazione richiede — **CIG**, **CUP** e **codice commessa**.

C'è **una riga per ogni coppia (fattura, contratto)**. Una fattura che mette
insieme lavori di due contratti diversi produce due righe; una fattura che
riguarda un contratto solo ne produce una; una fattura che non nasce da nessun
contratto non ne produce nessuna.

---

### Perché una tabella a parte, e non tre colonne sulla fattura

È la domanda naturale, e la risposta viene dal formato della **fattura
elettronica**, non da una preferenza tecnica.

Nella FatturaPA i riferimenti dell'atto stanno in un blocco che si chiama
`DatiContratto`, e quel blocco **si può ripetere**: ogni occorrenza porta i suoi
codici *e l'elenco delle righe della fattura a cui si riferisce*. È fatto
esattamente per il caso in cui un documento parla di più atti insieme.

Metterli sulla testata avrebbe funzionato solo con un contratto per fattura.
Metterli su ogni riga avrebbe costretto chi genera il file a rimettere insieme i
blocchi confrontando dei testi: due atti che condividono un codice ma non la
data si sarebbero fusi o spezzati a seconda di come si guardava, **senza che
niente segnalasse l'errore**.

⭐ Così invece **una riga di questa tabella *è* un blocco del file elettronico**,
e le righe che ci puntano sono la sua lista. Non è un'invenzione: la tabella dei
riepiloghi IVA funziona già allo stesso modo per il blocco `DatiRiepilogo`.

---

### ⛔ I valori sono una fotografia, non un collegamento

Numero, data e i tre codici sono **copiati** dal contratto nel momento in cui la
fattura si forma, e da lì non cambiano più.

È la ragione per cui quelle colonne esistono invece di leggere il contratto ogni
volta: se domani qualcuno corregge il CIG in anagrafica — perché era sbagliato,
o perché il contratto è stato rinnovato — **una fattura già emessa non deve
cambiare**. Un documento fiscale dice quello che diceva il giorno in cui è stato
emesso.

Il collegamento al contratto (`contratto_id`) c'è lo stesso, ma serve a un'altra
cosa: ricostruire da dove viene quella riga. **Chi stampa o trasmette il
documento legge sempre le colonne copiate.**

---

### Collocazione nel flusso

1. **Formazione della fattura** — il backend, mentre costruisce le righe,
   riconosce da quali contratti provengono le attività e scrive una riga qui per
   ognuno.
2. **Aggancio delle righe** — ogni riga di fattura che nasce da un contratto
   punta al proprio blocco con `fatture_righe.fattura_atto_id`. Le righe che non
   vengono da un contratto lasciano quel collegamento vuoto: è il caso ordinario.
3. **Congelamento** — appena la fattura supera la soglia oltre la quale diventa
   un documento fiscale definitivo, questa tabella **non si tocca più**: né in
   scrittura né in cancellazione. Se ne occupa un controllo automatico, lo stesso
   che protegge gli altri allegati della fattura.
4. **Uscita** — chi genera il file elettronico legge da qui i blocchi e, per
   ognuno, l'elenco delle righe che lo citano.

> ⚠️ Il generatore del file FatturaPA **non esiste ancora**. Numero e data sono
> copiati fin da adesso proprio perché, il giorno in cui arriverà, non ci sia
> niente da ricostruire.

---

### Le regole che il database garantisce da sé

Tre, e nessuna delle tre è una raccomandazione: sono vincoli, e non si possono
aggirare nemmeno per sbaglio.

| Regola | Perché conta |
| --- | --- |
| **Un blocco solo per ogni atto, su ogni fattura** | Due blocchi per lo stesso contratto significherebbero lo stesso CIG scritto due volte nello stesso documento |
| **Il contratto va sempre indicato** | Senza, la regola qui sopra si potrebbe aggirare lasciando il campo vuoto: due righe «senza contratto» non si darebbero fastidio |
| **Una riga di fattura può puntare solo a un blocco della *propria* fattura** | È il difetto che non si vedrebbe: una riga agganciata all'atto di un altro documento non produce nessun errore, semplicemente fa sparire il CIG dalla fattura in cui doveva comparire |

---

### Cosa succede quando una fattura viene cancellata

Le righe di questa tabella **muoiono con la fattura**, ed è giusto così: sono la
fotografia di *quel* documento, e senza il documento non hanno più oggetto. Se la
fattura viene rigenerata (cosa che può succedere finché è in bozza), i blocchi si
riscrivono insieme alle righe.

Per la stessa ragione qui **non si conserva lo storico delle modifiche**: questa
tabella si rifà da capo a ogni rigenerazione, quindi tenerne le versioni
intermedie riempirebbe l'archivio di copie identiche senza aggiungere niente. La
predisposizione c'è, spenta, nel caso un domani serva.

---

### Chi può vederla

Questa tabella **non ha regole di visibilità proprie**: il filtro è sulla
fattura. Chi ha diritto di vedere il documento vede anche i suoi blocchi, e chi
non lo vede non li raggiunge — semplicemente perché per arrivarci deve passare
dalla testata. È la stessa impostazione delle righe e del riepilogo IVA.

---

### 📌 Cosa non copre, oggi

* **Gli ordini attuativi degli accordi quadro** — nella pubblica amministrazione
  un contratto quadro ha un CIG «padre» e i singoli ordini ne hanno uno
  derivato. La forma di questa tabella li reggerebbe senza modifiche, ma oggi ad
  alimentarla è solo il contratto: il giorno che servisse, andrà deciso come
  indicare una sorgente di tipo diverso.
* **La generazione del file elettronico** — questa tabella prepara il dato, non
  lo stampa.

---

*Piano: `brief-db-fatture-atti-riferimenti-contratto.md` · richiesta raccolta in
`brief-db-richieste-aperte-dal-backend.md`, voce 4.*
