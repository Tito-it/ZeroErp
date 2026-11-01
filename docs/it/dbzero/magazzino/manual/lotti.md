## 📘 Documentazione Concettuale – Tabella `magazzino.lotti`

> **Ultimo aggiornamento**: 1 novembre 2026
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

**La partita di merce**: i pezzi di un articolo arrivati (o prodotti) insieme, con la data da
cui si conta la rotazione e l'eventuale scadenza. È l'unità della tracciabilità — «dove è
passato questo lotto», «ritira il lotto difettoso» — e la dimensione che i movimenti e le
righe di inventario, rettifica e trasferimento nominano quando l'articolo lo richiede.

Il lotto è una riga, con una chiave: due scritture diverse dello stesso codice non diventano
due lotti.

---

### La chiave è (articolo, codice)

Lo stesso codice di lotto su due articoli diversi è legittimo: due fornitori numerano
ciascuno per conto suo, e «L2026-001» del reagente A non è «L2026-001» del reagente B. Per
questo l'unicità è sulla coppia, non sul solo codice. Il codice non è un identificativo di
sistema: nessuna logica confronta su di esso, i movimenti puntano l'id.

`data_arrivo` è la data da cui si conta (arrivo o produzione), obbligatoria e senza default:
la dice chi carica. `data_scadenza` è facoltativa e mai prima dell'arrivo.

---

### Due booleani sull'articolo, non un enum

`catalogo.articoli.requires_lotto` e `requires_serial` sono **due domande indipendenti**: un
articolo può volere il lotto e non il seriale (un reagente), il seriale e non il lotto
(un'apparecchiatura), entrambi (un dispositivo medico), nessuno. È la primitiva di scrittura
a rifiutare un movimento senza lotto quando l'articolo lo pretende.

---

### Fuori dal perimetro, per costruzione

Un lotto è una **definizione**: non ha magazzino né emittente, e la storia di una partita è
la stessa per tutti. Non ha policy RLS, e la sua storicizzazione è permanente (è
tracciabilità: «chi ha spostato la scadenza di questo lotto» è una domanda che si fa).
Spento (`attivo` falso) non si assegna a un movimento nuovo, e non si spegne finché lo
nomina un movimento, un'attesa, una riga di inventario, rettifica o trasferimento o un
prelievo — i guard li genera il framework delle automazioni.

---

### Note di migrazione

* 2026-09-15 — tabella nuova (`brief-db-magazzino-lotto-1-terreno-vuoto`, §4.3; analisi
  carico e scarico, §7-quater, M-5): prima il lotto era un testo libero sui movimenti e sulle
  righe, e due scritture diverse dello stesso codice erano due lotti.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
