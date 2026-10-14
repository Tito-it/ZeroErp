## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_clienti_stessa_chiave`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_cliente_chiave_unica](/dbzero/anagrafiche/manual/fn_guard_cliente_chiave_unica)
>
Guide:
>
[Un cliente manuale per soggetto, servizio e azienda](/it/guide/gestione-delle-istanze-utility#un-cliente-manuale-per-soggetto-servizio-e-azienda)

---
### 🎯 Scopo Principale
(latest review 14-10-26)

Risponde alla domanda **«chi occupa già questa fornitura?»** per i clienti senza punto di
fornitura (le istanze fittizie della creazione manuale).

Senza un punto fisico, una fornitura è fatta di tre cose: **il soggetto** che la riceve, **il
servizio** (la utility) e **l'azienda** che la fornisce. La funzione riceve queste tre cose e
restituisce i clienti che le hanno, con il codice del loro billing account, lo stato e il periodo
in cui sono stati attivi.

---

### Chi conta

Conta un cliente che **è o è stato una fornitura**: attivo, in richiesta di sospensione, sospeso,
o chiuso (in tutte le forme di chiusura). Non contano:

* l'annullato, che non è mai esistito come fornitura;
* il pre-contrattuale, che si sta ancora preparando;
* l'aggregante, che non è una fornitura.

Il periodo resta nella risposta: decide chi legge se due periodi si sovrappongono (il controllo
del doppione lo confronta con il periodo del cliente nuovo, l'avviso con la data di oggi).

---

### L'azienda

L'azienda di un billing account è quella **dell'installazione**: quella a cui il billing account
è collegato o, se non è collegato, l'azienda predefinita. Non dipende da chi sta lavorando.

---

### Chi la usa

Tre lettori, una sola regola: se fossero due, prima o poi l'avviso direbbe una cosa e il
rifiuto un'altra.

| Chi | Per cosa |
| --- | --- |
| il controllo del doppione | rifiuta un secondo cliente nello stesso periodo |
| l'avviso del pre-contrattuale (backend) | dice all'operatore che la fornitura esiste già, senza bloccare |
| la catena delle istanze | collega l'istanza di una fornitura che riparte a quella precedente |

---

### Perché è privilegiata

Clienti e billing account sono visibili per azienda. Con i permessi di chi chiama, un cliente
fuori dal suo perimetro sarebbe invisibile, e il controllo direbbe «a posto» proprio nel caso da
rifiutare. Gira quindi con i privilegi del proprietario; l'azienda è uno dei tre dati della
domanda.
