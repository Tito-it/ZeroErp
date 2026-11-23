> **Ultimo aggiornamento**: 23 novembre 2026

### 📋 I documenti interni di magazzino — la famiglia

Tre documenti cambiano la merce senza un soggetto esterno: l'**inventario** (la conta), la
**rettifica** (una correzione con il segno) e il **trasferimento** (da un magazzino o da
un'ubicazione a un'altra). Hanno la stessa forma, una testata e le sue righe, e la stessa
vita: nascono in bozza, si confermano, si riaprono o si annullano, e solo la loro
**registrazione** li porta a «registrato», scrivendo i movimenti.

Un **registro** delle tre famiglie (`magazzino.fn_documento_interno_famiglia`) dice per
ognuna la tabella della testata e delle righe, la colonna di stato, il magazzino che fa da
perimetro (per il trasferimento quello di partenza) e la variabile con cui la registrazione
apre le sue porte. I verbi comuni ricevono la famiglia come primo argomento e leggono tutto
da lì: un nome di tabella non arriva mai da chi chiama.

### Chi nasce, chi si modifica

* **La nascita** ha un verbo per famiglia, per la testata e per la riga, perché i dati
  obbligatori sono diversi: il magazzino (partenza e arrivo, per il trasferimento), e per la
  riga l'articolo e la quantità che conta in quella famiglia.
* **Modifica, eliminazione, stato, righe** hanno un verbo comune alle tre famiglie.
* **Le colonne** che ogni gesto accetta stanno in una funzione sola
  (`magazzino.fn_documento_interno_colonne_ammesse`), per famiglia, parte e gesto. La
  provenienza del documento si sceglie alla nascita e poi non cambia, come il magazzino. Lo
  stato non è mai un campo: ha il suo verbo.

### ⭐ Lo stato lo decidono i controlli della tabella

* La **matrice** degli stati: dalla bozza si va a confermato o annullato, da confermato si
  torna in bozza o si annulla; annullato e registrato non si lasciano.
* **Registrato** lo scrive solo l'operazione di registrazione: chiesto al verbo dello stato è
  rifiutato (`E_MAG_DOCUMENTO_POSTED_SOLO_DA_OPERAZIONE`).
* **Le righe** si scrivono solo con la testata in bozza (`E_MAG_DOCUMENTO_RIGHE_CONGELATE`),
  e **la testata** si modifica solo in bozza (`E_MAG_DOCUMENTO_TESTATA_CONGELATA`): la prima
  regola la dice la tabella, la seconda il verbo di modifica.
* **Si elimina** solo un documento in bozza (`E_MAG_DOCUMENTO_NON_ELIMINABILE`), e le righe
  vanno con lui.

### ⚠️ La registrazione apre le porte, nessun altro

La registrazione accende una variabile di transazione con l'id del documento, e i controlli
della tabella aprono le due porte («registrato» e le righe fuori dalla bozza) solo quando c'è
la variabile **e** scrive il proprietario delle tabelle. I verbi girano come il proprietario:
per questo ogni verbo su un documento che esiste **spegne la variabile della sua famiglia**
prima di scrivere. Accesa dall'applicazione davanti a un verbo, non apre niente.
