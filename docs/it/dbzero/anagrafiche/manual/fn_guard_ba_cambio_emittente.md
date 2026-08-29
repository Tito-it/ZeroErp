## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_ba_cambio_emittente`

> 👀 **Vedi anche**
>
Approfondimenti funzioni:
>
[anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/manual/fn_guard_albero_ba_emittente)
>
[script.fn_check_ba_cambio_emittente](/dbzero/script/manual/fn_check_ba_cambio_emittente)
>
[vendite.trgfn_commesse_guard_emittente_ba](/dbzero/vendite/manual/trgfn_commesse_guard_emittente_ba)
>
Approfondimenti tabelle:
>
[anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)

---
### 🎯 Scopo Principale
(latest review 26-08-26)

Impedisce di spostare un cliente da un emittente a un altro **quando quel cliente
ha gia' una storia**: fatture emesse, o lavoro raccolto in commessa.

---

### Perche' conta davvero

Una fattura **non segue il cliente**: si porta dietro chi l'ha emessa, e non lo
cambia mai. Spostare il cliente su un altro emittente quindi non riscrive quei
documenti — **li lascia orfani**.

Da quel momento chi ha emesso quelle fatture continua a vedere i documenti e
smette di vedere il cliente a cui si riferiscono. Non e' un errore che compare a
video: e' un cliente che sparisce dall'elenco di chi ha lavorato per lui, e ci si
accorge molto dopo, senza sapere da dove venga.

---

### La domanda non e' «si puo'?», e' «fino a quando?»

Vietare del tutto avrebbe un costo vero. Un cliente **nasce gia' agganciato** a
un emittente — quello dell'operatore che lo sta creando — quindi se l'operatore
sta lavorando sull'emittente sbagliato il cliente nasce sbagliato. E' un errore di
inserimento ordinario, e con un legame immutabile non si correggerebbe piu': la
via d'uscita diventerebbe cancellare e rifare, che e' peggio.

⇒ La regola scelta e' quindi: **libero finche' non c'e' storia, vietato dopo**.
La finestra di correzione esiste, ed e' quella in cui l'errore si scopre di
solito: subito, prima che su quel cliente sia passato del lavoro.

---

### Che cosa conta come «storia»

Non e' un criterio di gravita': e' cio' che porta **una copia dell'emittente che
nessuno riscrivera' piu'**. Sono due cose:

* le **fatture**, che congelano l'emittente per definizione;
* le **commesse**, che ne portano una copia fissata alla nascita.

Ordini e DDT no — non per indulgenza, ma perche' il loro emittente non e' una
copia che invecchia: c'e' un controllo che lo riallinea al cliente a ogni
scrittura.

---

### Quando invece non blocca

Quando l'emittente **non cambia davvero**. Togliere l'aggancio specifico di un
cliente, quando l'emittente generale dell'installazione e' comunque lo stesso,
non sposta nessun documento — e bloccarlo sarebbe un rifiuto senza motivo.

---

### E se il cliente e' passato davvero all'altro emittente?

Allora non si sposta: **si apre presso il nuovo emittente una fornitura nuova**.
I documenti gia' emessi restano con chi li ha emessi, il cliente resta lo stesso
soggetto, e le due posizioni convivono. E' la forma pulita, anche fiscalmente.

---

### Impatto e Vantaggi

* il messaggio dice **quante** fatture e **quante** commesse bloccano: un «non si
  puo'» senza numeri manderebbe a cercare a mano cosa c'e' sotto;
* nessuna eccezione per i dati preesistenti e nessun interruttore di
  disattivazione: **un invariante con l'interruttore non e' un invariante**;
* non risale ai clienti collegati, ed e' voluto: quel caso e' gia' respinto dal
  controllo sull'albero, con un messaggio piu' preciso.

---

### ⭐ Dal 2026-08-27 il predicato non è più qui

Questa funzione **non decide più**: chiede a
[`script.fn_check_ba_cambio_emittente`](/dbzero/script/manual/fn_check_ba_cambio_emittente)
e solleva il **primo** motivo che le viene restituito.

Non è un riordino estetico. Quella stessa funzione è ciò che la lista dei
clienti di un emittente interroga per **spegnere il cestino di riga**: il
tooltip del pulsante e l'errore del rifiuto vengono dalla stessa riga di codice.

⇒ Un controllo che confrontasse le due risposte proverebbe che *oggi* coincidono.
Così si prova che **non possono** divergere — e il presidio scritto nel test non
è «gli esiti coincidono», è **«qui dentro il predicato non c'è più»**.

⚠️ Ne discende che **l'ordine dei motivi è un contratto**: si solleva il primo.
