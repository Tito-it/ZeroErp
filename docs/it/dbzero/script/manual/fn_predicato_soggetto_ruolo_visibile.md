## 📘 Documentazione Concettuale – Funzione `script.fn_predicato_soggetto_ruolo_visibile`

> 👀 **Vedi anche**
>
Le due funzioni che la usano:
>
[script.fn_search_soggetti_universale](/dbzero/script/manual/fn_search_soggetti_universale) (la lista)
>
[script.fn_get_search_detail](/dbzero/script/manual/fn_get_search_detail) (il dettaglio)
>
Il catalogo che legge:
>
[config.tipi_ruoli](/dbzero/config/manual/tipi_ruoli)

---
### 🎯 Scopo Principale
(latest review 10-10-2026)

È la regola che decide **chi si vede nella ricerca universale**, scritta una volta
sola. La lista dei risultati e il dettaglio che si apre da una riga la usano
entrambi, quindi non possono dare due risposte diverse sullo stesso soggetto.

Fa due cose:

1. **controlla il tipo ruolo**: deve esistere ed essere ricercabile
   (`config.tipi_ruoli.ricerca_visibile`). Altrimenti solleva l'errore, per la lista
   e per il dettaglio allo stesso modo;
2. **rende la condizione** che un soggetto-ruolo deve soddisfare per comparire, da
   inserire nella query di chi la chiama.

---

### La regola

Un soggetto-ruolo si mostra se:

* il suo ruolo ha una tabella in `config.tipi_ruoli.entita_esistenza` → ha **almeno
  una riga di quella tabella** che chi guarda vede;
* il suo ruolo non ce l'ha → esiste.

| Ruolo | Tabella | Esempio di chi non si vede |
| --- | --- | --- |
| Cliente | `anagrafiche.clienti` | un soggetto col ruolo cliente ma nessun cliente, o con clienti tutti di un altro emittente |
| Fornitore | `anagrafiche.fornitori` | un soggetto col ruolo fornitore senza la sua scheda fornitore |
| Vettore | `anagrafiche.vettori` | un soggetto col ruolo vettore senza la sua scheda vettore |
| Banca | `anagrafiche.bank_branches` | un soggetto col ruolo banca senza filiale |
| Reseller, distributore, venditore | — | nessuno: basta il ruolo |

**Chi guarda** conta per davvero: il perimetro lo fa la RLS della tabella. Per i
clienti è quella dell'emittente, quindi un operatore che lavora per l'azienda A non
vede i clienti dell'azienda B, né nella lista né nel dettaglio. La regola non ripete
il perimetro: si limita a chiedere «ne resta almeno uno?».

**Cosa non conta**, per decisione:

* **lo stato dell'entità**: un cliente chiuso o un fornitore disattivato si
  ritrovano. Il rapporto è finito, ma può avere fatture da incassare, resi,
  contestazioni;
* **`soggetti.attivo`**: il modello non ammette un soggetto-ruolo con il soggetto
  disattivato (un soggetto che ha ruoli non si disattiva, e a un soggetto disattivato
  non si dà un ruolo), quindi la regola non lo chiede.

---

### Gli errori

| Quando | Codice |
| --- | --- |
| tipo ruolo mancante o non positivo | `E_PARAMETRO_INVALIDO` |
| tipo ruolo che non esiste | `E_TIPO_RUOLO_NON_TROVATO` |
| tipo ruolo che esiste ma non si cerca (`ricerca_visibile = false`) | `E_TIPO_RUOLO_NON_RICERCABILE` |

Il menu della ricerca offre solo i ruoli ricercabili. Gli ultimi due errori arrivano
quindi da una richiesta costruita a mano: per la ricerca universale quel ruolo
«non c'è», e il backend risponde 404.

---

### Perché rende una condizione e non un sì/no

La tabella dell'entità è un dato del catalogo, quindi va letta a runtime. Una funzione
che rispondesse sì o no per ogni soggetto-ruolo farebbe questa lettura **per ogni
riga** della lista, mentre il ruolo è uno solo per tutta la ricerca. Così invece la
regola si risolve **una volta**, e la condizione entra nella query della lista e in
quella del dettaglio.

Il chiamante passa il nome con cui, nella sua query, chiama la tabella
`anagrafiche.soggetti_ruoli` (di solito `sr`). Il nome deve essere un identificatore
semplice; la funzione lo controlla e lo quota.

---

### Com'era prima

* fino al 2026-10-08 le due funzioni della ricerca filtravano i clienti a mano, con
  una copia della regola della RLS;
* dal 2026-10-08 al 2026-10-10 la regola stava in `script.fn_check_soggetto_ruolo_visibile`,
  che nominava il ruolo cliente per nome: un cliente senza clienti spariva, un
  fornitore senza scheda compariva. Due casi che il modello tratta allo stesso modo,
  due risposte. Quella funzione è stata ritirata quando è nata questa;
* la ricercabilità del ruolo la controllava solo il backend.

Brief: `brief-db-codici-non-trovato-email-e-permessi` (R-6, decisioni di Tid del
2026-10-09 e 2026-10-10).

