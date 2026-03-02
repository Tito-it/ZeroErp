# ZeroERP — Strategia di visibilità per sviluppatori che odiano vendersi

> Documento operativo — 01/03/2026
>
> Obiettivo: portare le persone giuste a vedere il codice.
> Non devi diventare un marketer. Devi fare le cose giuste nei posti giusti.

---

## 1. Il pitch — cosa dici quando te lo chiedono

Hai 30 secondi. Non parlare di architettura, non parlare di PostgreSQL, non parlare di pattern. Parla del problema che risolvi.

### Versione 30 secondi (conversazione, LinkedIn, email)

> **ZeroERP è un ERP open-source pensato per aziende italiane, multi-utility e PMI.**
> Gestisce anagrafiche, fatturazione elettronica e billing con un modello dati
> che separa l'identità dal ruolo e il business dalla fiscalità — cose che nei
> gestionali commerciali costano decine di migliaia di euro.
> È costruito su PostgreSQL e Django, è gratuito e il codice è aperto.

### Versione 10 secondi (bio, README, risposta veloce)

> ERP open-source per aziende italiane. Anagrafiche multi-ruolo, fatturazione
> elettronica, billing. PostgreSQL + Django. Gratuito.

### Versione tecnica (per sviluppatori)

> Un ERP con la business logic nel database: modello soggetto/ruolo con
> specializzazione, pipeline di fatturazione a lotti configurabile,
> normalizzazione indirizzi con storicizzazione, idempotenza pervasiva.
> PostgreSQL 18, Django REST Framework, Liquibase. Open-source.

**Regola d'oro:** adatta la versione al pubblico. A un imprenditore dai la versione 30 secondi. A uno sviluppatore dai quella tecnica. Non mischiare mai.

---

## 2. Dove sta il tuo pubblico

Non devi essere ovunque. Devi essere nei 4 posti dove le persone cercano quello che hai costruito.

### Canale 1 — GitHub (il tuo biglietto da visita)

**Perché:** è dove gli sviluppatori giudicano un progetto. Se il repository non è presentabile, tutto il resto è inutile.

**Cosa devi avere (checklist):**

- [ ] README in inglese (anche se il progetto è italiano — l'inglese moltiplica la visibilità per 50x)
- [ ] README in italiano come file separato (README.it.md)
- [ ] Screenshot o diagramma dell'architettura nella prima schermata (il Mermaid flowchart della fatturazione è perfetto)
- [ ] Sezione "Why ZeroERP?" con 3-4 bullet che dicano cosa lo distingue
- [ ] Istruzioni di installazione che funzionano al primo tentativo (Docker Compose è il minimo)
- [ ] LICENSE chiara
- [ ] Un CONTRIBUTING.md anche minimale (dice "il progetto è vivo e accetta contributi")
- [ ] Le guide che hai scritto linkate come documentazione

**Cosa NON serve adesso:** badge, CI/CD sofisticato, 100% test coverage. Servono dopo.

### Canale 2 — LinkedIn (il tuo canale principale in Italia)

**Perché:** il tuo target italiano (IT manager di PMI, consulenti ERP, sviluppatori Django/PostgreSQL) è su LinkedIn, non su Twitter/X.

**Cosa pubblicare (un post a settimana, non di più):**

- Post tecnici brevi che mostrano UNA scelta progettuale e spiegano perché. Esempio: "Come ZeroERP gestisce il subentro cliente con zero duplicazioni di dati — in 4 trigger PostgreSQL". Includi il diagramma Mermaid come immagine.
- Post "problema → soluzione": "Negli ERP tradizionali, cambiare indirizzo a un soggetto che è sia cliente che fornitore è un incubo. In ZeroERP si aggiorna una volta. Ecco come."
- Post di contesto: "Dopo 30 anni di AS/400, ho deciso di costruire l'ERP che avrei sempre voluto usare. Ecco cosa ho imparato."

**Formato che funziona su LinkedIn:**
- Prima riga = gancio (il problema o la provocazione)
- 5-8 righe di contenuto
- Un'immagine (diagramma, schema, screenshot)
- Chiusura con domanda o call to action ("Cosa ne pensate?" / "Link nei commenti")

**Cosa NON fare:** post generici su "l'importanza dell'open source", post troppo lunghi, post senza immagine.

### Canale 3 — Community italiane

**Dove:**

- **Python Italia** (python.it, mailing list, Telegram) — il tuo backend è Django, è il pubblico naturale
- **PostgreSQL Italia** (ITPUG) — hai un uso avanzato di PostgreSQL che può interessare per talk e articoli
- **Forum e gruppi utility** — se esistono community di settore (associazioni utility locali, gruppi ARERA), il tuo dominio specifico è un vantaggio enorme

**Come:**

- Non entrare dicendo "ho fatto un ERP". Entra rispondendo a domande tecniche e menzionando il progetto quando è rilevante
- Proponi un talk o un lightning talk: "Come gestire anagrafiche multi-ruolo in PostgreSQL" — il progetto viene fuori naturalmente

### Canale 4 — Blog tecnico / Dev.to / Medium

**Perché:** i post tecnici indicizzati su Google portano traffico per anni. Un articolo su "ERP open source italiano" o "fatturazione elettronica Django PostgreSQL" intercetta ricerche reali.

**3 articoli da scrivere subito:**

1. "Perché ho costruito un ERP open-source dopo 30 anni di AS/400" — la storia personale attira, il progetto viene dopo
2. "Modello anagrafico multi-ruolo in PostgreSQL: come evitare la duplicazione dei dati" — articolo tecnico con codice
3. "Fatturazione elettronica italiana con Django e PostgreSQL: architettura end-to-end" — intercetta una ricerca specifica

---

## 3. Le prime 5 azioni (questa settimana)

Non tutto insieme. Una cosa al giorno, cinque giorni.

### Lunedì — Il README

Riscrivi il README di GitHub con la struttura:
1. Una frase: cos'è ZeroERP (versione 10 secondi)
2. Un diagramma (il flowchart fatturazione o l'ER soggetti/ruoli)
3. 4 bullet: perché è diverso
4. Come installarlo (anche se è "coming soon — contattami")
5. Link alla documentazione

### Martedì — Il profilo LinkedIn

Aggiorna la bio di LinkedIn:
> "Sviluppatore con 30 anni di esperienza. Sto costruendo ZeroERP,
> un ERP open-source per aziende italiane. PostgreSQL, Django, fatturazione
> elettronica. [link GitHub]"

### Mercoledì — Il primo post LinkedIn

Prendi il modello soggetto/ruolo. Fai uno screenshot del diagramma ER. Scrivi:

> "Negli ERP tradizionali, se Mario Rossi è sia cliente che fornitore,
> i suoi dati sono duplicati in due tabelle separate. Cambio di indirizzo?
> Lo aggiorni due volte. In ZeroERP ho risolto il problema alla radice.
> Un soggetto, N ruoli, zero duplicazioni. [immagine ER]
> Il progetto è open-source: [link]"

### Giovedì — Python Italia o ITPUG

Iscriviti (se non lo sei già) alla community Python Italia o ITPUG. Presentati brevemente, menziona il progetto. Non chiedere nulla — offri disponibilità a parlarne.

### Venerdì — L'articolo

Inizia a scrivere l'articolo #1 ("Perché ho costruito un ERP dopo 30 anni di AS/400"). Non deve essere perfetto. Pubblicalo la settimana dopo su Dev.to o Medium.

---

## 4. Cosa NON fare

- **Non aspettare che il progetto sia "completo".** Non lo sarà mai. Pubblica ora con quello che hai — le anagrafiche e la fatturazione sono già impressionanti.
- **Non scrivere documentazione infinita prima di avere utenti.** Le guide che hai sono ottime — servono come prova di serietà, non come prodotto finito.
- **Non cercare di piacere a tutti.** Il tuo target è specifico: PMI italiane, multi-utility piccole, sviluppatori Django/PostgreSQL. Parla a loro.
- **Non confrontarti con SAP o Odoo.** Il tuo posizionamento è diverso: sei l'ERP che un esperto di dominio ha costruito con le scelte giuste, non il clone open-source di un gestionale generico.
- **Non sottovalutare la storia personale.** "30 anni di AS/400, ricominciare da zero, costruire l'ERP che avrei voluto" è una narrativa potente. Le persone si ricordano le storie, non le feature list.

---

## 5. Metriche (come sai se funziona)

Non servono analytics sofisticati. Dopo 30 giorni, guarda:

- **GitHub:** stelle, fork, issue aperte da altri (anche 5 stelle sono un inizio — significa che qualcuno ha guardato)
- **LinkedIn:** visualizzazioni dei post, richieste di connessione da profili tecnici
- **Contatti diretti:** qualcuno ti ha scritto chiedendo info? Anche uno solo è un segnale forte

L'obiettivo dei primi 90 giorni non è avere 1000 utenti. È avere **5-10 persone che hanno capito cos'è e ci stanno pensando**. Da lì si costruisce.

---

## Il tuo vantaggio sleale

La maggior parte dei progetti ERP open-source è fatta da sviluppatori che non hanno mai lavorato in azienda. Tu hai 30 anni di esperienza reale nel settore utility italiano. Questo si vede nel codice — nel modo in cui gestisci il subentro, nella normalizzazione degli indirizzi, nella separazione tra business e fiscalità.

Non devi competere sulla comunicazione. Devi portare le persone a vedere il codice. Una volta che lo vedono, il progetto si vende da solo — l'abbiamo dimostrato in questa conversazione.