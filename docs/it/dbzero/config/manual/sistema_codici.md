## 📘 Documentazione Concettuale – Tabella `config.sistema_codici`

> **Ultimo aggiornamento**: 13 novembre 2026

La tabella **`config.sistema_codici`** definisce le regole per la generazione automatica di codici alfanumerici (clienti, soggetti, fornitori, vettori, istanze di utility, pratiche, preventivi, contratti, offerte commerciali, lotti di fatturazione).

⛔ **Non i documenti di vendita.** Fatture, documenti di trasporto, ordini, commesse e resi si numerano sui registri, e dal 2026-08-31 non hanno più una riga qui: vedi la revisione in fondo.

---
### 🎯 Scopo Principale
(latest review 18-01-26)
* **Definizione del formato codice**
  Consente di specificare per ogni tipo di codice (`codice_interno`) un **prefisso**, un **separatore** e la **lunghezza numerica** totale, rendendo parametrica la struttura dei codici generati.
* **Configurazione del meccanismo di sequenza**
  Tramite il flag `usa_sequenza` si abilita o meno l’utilizzo di una progressione automatica basata su sequenza di database, a garanzia di unicità e ordinarietà.
* **Aggancio alla tabella target**
  Le colonne `schema_tabella`, `nome_tabella` e `nome_colonna` definiscono la destinazione del codice e permettono di derivare automaticamente il nome sequenza standard.
* **Automazione trigger**
  Le righe con `usa_sequenza = TRUE` attivano automaticamente la creazione di un trigger sulla tabella target che genera il codice quando il campo risulta nullo (o vuoto/0 secondo il tipo).

---

### Parametri di Configurazione

* **`prefisso`**
  Prefisso testuale anteposto alla parte numerica (es. `ORD-`, `CL-`).
* **`separatore`**
  Carattere o stringa utilizzata per separare il prefisso dalla parte numerica (es. `-`, `/`, `_`).
  «Nessun separatore» è la **stringa vuota**: la colonna è `NOT NULL DEFAULT ''` dal 2026-11-13
  (`90_end/20261112-53`). Il generatore compone `prefisso || separatore || numero`, e un `NULL`
  renderebbe `NULL` il codice. Una riga creata dal pannello col campo vuoto prende il default.
* **`lunghezza_numero`**
  Numero totale di cifre della parte numerica (es. `6` → da `000001` a `999999`). Se la sequenza supera lo spazio, si deve aggiornare il parametro.
* **`usa_sequenza`**
  Booleano che, se **true**, indica che il codice numerico è generato tramite una sequenza di database; se **false**, occorre gestire manualmente l’incremento.
* **`schema_tabella`**, **`nome_tabella`**, **`nome_colonna`**
  Identificano la tabella e la colonna a cui si applica la numerazione e servono per calcolare il nome sequenza automatico `<schema>.<tabella>_<colonna>_seq`.

---

### Vantaggi Operativi

* **Uniformità dei codici**
  Garantisce che tutti i codici generati rispettino lo stesso pattern configurato, migliorando la leggibilità e la coerenza aziendale.
* **Flessibilità**
  La parametrizzazione di `prefisso`, `separatore` e `lunghezza_numero` consente di adattarsi a requisiti diversi (es. prefissi stagionali, codifiche diverse per aree di business) senza modifiche al codice.
* **Affidabilità della sequenza**
  L’uso di una sequenza di database (quando `usa_sequenza` è **true**) evita collisioni e garantisce incrementi atomici, utili in contesti ad alto carico.
* **Gestione dinamica**
  Il flag `usa_sequenza` permette di sospendere la generazione di un dato tipo di codice senza rimuoverne la configurazione, utile per archiviare vecchie configurazioni o per esigenze temporanee.

---

### 🔄 rev 2026-08-31 (sera) — quando un numeratore deve **traslocare sui registri**

I motori di numerazione in Zero ERP sono **due**, e questa è la metà semplice.
L'altra è `vendite.registri_fatturazione`, che numera fatture, documenti di
trasporto, ordini, commesse e resi.

⛔ **Delle cinque famiglie che si numerano sui registri, qui non c'è più
niente.** Le righe `ddt`, `ordine`, `reso` e `commessa` sono uscite col changeSet
`20260831-53`, come la riga della fattura era uscita a febbraio: prefisso,
suffisso e lunghezza dei documenti di vendita vivono ora sul registro, e i valori
con cui un registro **nasce** stanno in `vendite.famiglie_documento`.

⚠️ **Una versione precedente di questa scheda diceva il contrario**, ed è stata
vera per mezza giornata: *«questa tabella non ha perso niente nel trasloco, cambia
solo il contatore»*. Il trasloco è avvenuto in due tempi — la mattina il
contatore, la sera la forma — ed è **spostando la forma** che si è visto perché
doveva muoversi: finché restava qui, quelle quattro righe dovevano restarci anche
loro, monche, in una tabella **editabile dal pannello di configurazione**. Un
amministratore che ne cambiava il prefisso non otteneva niente, e non aveva modo
di accorgersene.

⭐ **Ciò che resta qui, oggi, genera davvero.** Dieci voci, e per ognuna questa
tabella fa tutt'e tre le cose: formato, contatore e momento.

#### Il criterio, in una frase

> **Il periodo il generatore se lo calcola da sé; l'emittente, la serie e un
> momento diverso dall'inserimento gli arrivano dalla RIGA.**

Chi chiede una dimensione che viene dalla riga sta chiedendo i **registri**, non
un allargamento del sistema codici.

#### I tre campanelli

Se anche uno solo suona, il numeratore è nel posto sbagliato:

1. **«Ogni azienda deve avere la sua numerazione.»** Qui il trigger generato è
   **uno per tabella** e chiama il generatore senza passargli la riga: non può
   sapere di chi è il documento. E non si aggira con una riga di configurazione
   per azienda — il trigger resta uno.
2. **«Il numero deve ripartire da 1 a Capodanno.»** Il contatore di qui è una
   sequenza di database, e **una sequenza non sa cosa sia un anno**. Il reset
   periodico non è configurabile: è il substrato a non prevederlo.
3. **«Il numero non deve uscire alla creazione, ma quando il documento viene
   confermato.»** Il trigger generato scatta all'inserimento, punto. Numerare più
   tardi significa scriverne uno proprio — e a quel punto tanto vale usare il
   motore che lo fa già.

⚠️ **Un quarto campanello, più sottile: la serie.** Se lo stesso documento deve
poter girare su più serie (sezionali), la serie è una dimensione del contatore e
qui non c'è.

#### ⛔ Il segnale che dice che si sta sbagliando strada

Se per far quadrare la numerazione si sta pensando di aggiungere una colonna a
questa tabella — l'azienda, il periodo, lo stato in cui numerare — **la risposta
non è qui**. Ogni dimensione aggiunta va poi passata al trigger generato, che è
generico per costruzione: si finisce a ricostruire i registri, peggio.

⭐ **E c'è un invariante che decide da solo:** *ogni dimensione del contatore deve
comparire nella stringa del codice*. Un contatore per azienda **obbliga** la sigla
dell'azienda dentro il codice, altrimenti al primo cambio di periodo o di azienda
il vincolo di unicità salta. Se quella sigla nel codice non ci può stare, il
contatore per azienda non si può fare — e viceversa, se il codice la porta, il
contatore *deve* essere per azienda o la sigla **mente**.

#### La checklist del trasloco

Per ogni documento che passa ai registri, **in quest'ordine**:

1. la tabella guadagna `registro_id` (nullable: il documento in bozza il registro
   non ce l'ha ancora);
2. ⛔ **il vincolo di unicità guadagna `registro_id` nello STESSO passo**, e
   **prima** che esca il primo numero nuovo. È l'unico errore che non degrada ma
   **ferma**: due aziende che ripartono entrambe da 1 e una violazione di indice
   senza messaggio di dominio;
3. il generatore chiama il motore dei registri al posto della sequenza. ⚠️ Il
   **momento** resta quello di prima ed è l'unica cosa che non si centralizza;
   **formato e composizione se ne vanno con il contatore** (passo 5-bis);
4. l'anno si ri-deriva dalla **data del documento** nello stesso comando del
   numero. ⚠️ Il trigger di normalizzazione lo scrive solo se il documento nasce
   già numerato: chi numera a stato non passa mai di lì, e l'anno resterebbe vuoto;
5. la riga di qui va a `usa_sequenza = false` — il trigger generato si smonta da
   solo;
5-bis. ⛔ **e poi la riga ESCE**, dopo che prefisso, suffisso e lunghezza sono
   passati sul registro e i loro default in `vendite.famiglie_documento`.
   Fermarsi al passo 5 lascia qui una riga che non conta più niente ma che si può
   ancora modificare dal pannello: è **confusione garantita**, non un residuo
   innocuo. ⚠️ E l'ordine dei passi è portante — la rimozione va in `80_data`,
   dopo che le funzioni leggono già dal registro: invertirne uno lascia qualcuno
   senza fonte, con un difetto **muto**;
5-ter. ⚠️ **si censiscono i LETTORI della riga che si toglie**, non solo si
   verifica che la sede nuova sia piena. È l'errore costato il difetto del
   `20260831-55`: la funzione centrale continuava a leggere la lunghezza di qui,
   non trovava più niente e ripiegava su 7 cifre — giusto per caso su tre
   famiglie, sbagliato sulla commessa che ne vuole 9, e in silenzio;
6. ogni azienda deve avere il registro di quella famiglia **prima**, o il primo
   documento si ferma;
7. la famiglia va registrata in `vendite.famiglie_documento`, o il documento non
   entra nel controllo che impedisce di spostare un cliente fra due aziende.

⚠️ **Un effetto sul frontend da non dimenticare.** `usa_sequenza` è ciò che le
maschere leggono per decidere se il campo del numero è automatico: portandolo a
`false`, una maschera può iniziare a invitare l'utente a digitarlo.

---

> **"Un sistema configurabile di generazione codici, che separa prefisso, numerazione e logica di sequenza, per codifiche coerenti e facilmente modificabili."**
