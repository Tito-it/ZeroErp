## 📘 Documentazione Concettuale – Tabella `magazzino.lotti`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — `requires_lotto` dice se l'articolo lo pretende
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — `lotto_id` è parte della tranche
> * [magazzino.assets](/dbzero/magazzino/tabelle/assets) — l'altra dimensione: il pezzo serializzato

---

### 🎯 Scopo Principale

**La partita di merce di un'azienda**: i pezzi di un articolo arrivati (o prodotti) insieme, con la data da
cui si conta la rotazione e l'eventuale scadenza. È l'unità della tracciabilità — «dove è
passato questo lotto», «ritira il lotto difettoso» — e la dimensione che i movimenti e le
righe di inventario, rettifica e trasferimento nominano quando l'articolo lo richiede.

Il lotto è una riga, con una chiave: due scritture diverse dello stesso codice non diventano
due lotti.

---

### La chiave è (azienda, articolo, codice)

Lo stesso codice di lotto su due articoli diversi è legittimo: due fornitori numerano
ciascuno per conto suo, e «L2026-001» del reagente A non è «L2026-001» del reagente B. Ed è
legittimo su due aziende: il codice sta sul cartone del fornitore, e due aziende possono
ricevere dallo stesso fornitore partite con lo stesso codice. Per questo l'unicità è sulla
terna, non sul solo codice. Il codice non è un identificativo di sistema: nessuna logica
confronta su di esso, i movimenti puntano l'id.

`data_arrivo` è la data da cui si conta (arrivo o produzione), obbligatoria e senza default:
la dice chi carica. `data_scadenza` è facoltativa e mai prima dell'arrivo.

---

### Due booleani sull'articolo, non un enum

`catalogo.articoli.requires_lotto` e `requires_serial` sono **due domande indipendenti**: un
articolo può volere il lotto e non il seriale (un reagente), il seriale e non il lotto
(un'apparecchiatura), entrambi (un dispositivo medico), nessuno. È la primitiva di scrittura
a rifiutare un movimento senza lotto quando l'articolo lo pretende.

---

### Il perimetro è l'azienda, non il magazzino

Un lotto è di un **emittente**: l'azienda che ha ricevuto o prodotto la partita. Non è di un
magazzino, perché si sposta fra i magazzini della stessa azienda, e dove si trova lo dice il
registro. L'emittente non si sceglie: lo mette la sessione di chi crea il lotto. Un operatore
vede e modifica i lotti delle proprie aziende (policy RLS diretta, come il seriale), e una
riga di magazzino non può nominare il lotto di un'altra azienda: il controllo sta sulle sei
tabelle che citano il lotto. La storicizzazione è permanente, col perimetro dell'emittente (è
tracciabilità: «chi ha spostato la scadenza di questo lotto» è una domanda che si fa).
Spento (`attivo` falso) non si assegna a un movimento nuovo, e non si spegne finché lo
nomina un movimento, un'attesa, una riga di inventario, rettifica o trasferimento o un
prelievo — i guard li genera il framework delle automazioni.

---

### Chi scrive

L'applicazione legge questa tabella e non la scrive: ogni scrittura passa da un **verbo**, che controlla il livello dell'operatore e il perimetro prima di scrivere. Nasce con [fn_aggiungi_lotto](/dbzero/magazzino/funzioni/fn_aggiungi_lotto) e si modifica con [fn_modifica_lotto](/dbzero/magazzino/funzioni/fn_modifica_lotto). Non si elimina: si disattiva con la modifica.

---

### Note di migrazione

* 2026-09-15 — tabella nuova (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.3; analisi
  carico e scarico, §7-quater, M-5): prima il lotto era un testo libero sui movimenti e sulle
  righe, e due scritture diverse dello stesso codice erano due lotti.
* 2026-11-22 — il lotto prende l'emittente (`brief-db-magazzino-lotto-dell-azienda`): prima
  era condiviso fra tutte le aziende, e una poteva cambiare la scadenza del lotto di un'altra.
* 2026-11-22 — in sola lettura per l'applicazione: la scrivono i verbi (`brief-db-magazzino-tutte-le-scritture-dal-verbo`, Lotto 1).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
