## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_titoli_iva_ambiti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo di cui dice l'ambito
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — il livello articolo
> * [vendite.articoli_gruppi](/dbzero/vendite/tabelle/articoli_gruppi) — il livello gruppo di voce
> * [vendite.articoli_tipologie](/dbzero/vendite/tabelle/articoli_tipologie) — il livello tipo di voce
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — quando un ambito sta in piedi
> * [anagrafiche.trgfn_soggetti_titoli_iva_ambiti_guard](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_ambiti_guard) — il guard sulle righe
> * [anagrafiche.trgfn_soggetti_titoli_iva_guard_ambito](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_guard_ambito) — il guard sul titolo
> * [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) — il risolutore, che legge l'ambito riga per riga

---

### 🎯 Scopo Principale

`anagrafiche.soggetti_titoli_iva_ambiti` dice per che cosa vale un titolo IVA ristretto: una riga per ogni articolo
o categoria di merce coperta. Un titolo che non vale su tutto (un'agevolazione su certi prodotti, una qualifica su
certe prestazioni) copre solo le righe di documento che ricadono qui dentro.

---

### ⭐ È ciò che distingue un titolo da un «codice IVA del cliente»

Senza ambito un titolo varrebbe su tutto, cioè sarebbe un'aliquota del cliente con un altro nome. Un documento di
dieci righe con un titolo ristretto a due articoli deve dare due righe agevolate e otto ordinarie: sono queste
righe a renderlo possibile. Il risolutore le legge riga per riga, e quando più titoli coprono la stessa riga vince
il più specifico.

---

### Tre livelli, dichiarati

| `livello` | Colonna valorizzata | Punta a |
| --- | --- | --- |
| `ARTICOLO` | `articolo_id` | `catalogo.articoli` |
| `GRUPPO_VOCE` | `gruppo_voce_id` | `vendite.articoli_gruppi` |
| `TIPO_VOCE` | `tipo_voce_id` | `vendite.articoli_tipologie` |

Sono le due classificazioni che l'articolo porta già, più l'articolo stesso. Il livello è anche la specificità con
cui si arbitra fra due titoli: articolo, poi categoria di merce, poi tutto.

Il livello è dichiarato, non dedotto da quale colonna è piena: un controllo lo lega alla sua colonna e impone il
vuoto alle altre due, così una riga non può nominare due oggetti né nessuno. L'unicità sull'oggetto tratta i valori
vuoti come uguali, perché lo stesso oggetto non si dichiari due volte sullo stesso titolo.

L'oggetto nominato deve essere attivo alla conferma dell'operazione, e così il titolo (`E_ATTIVO_PADRE_NON_ATTIVO`).
Un articolo nominato da un ambito non conta come «usato» per `catalogo.fn_articolo_usato`: l'ambito è anagrafica
del titolo, non un uso dell'articolo.

---

### Le regole dell'ambito

`anagrafiche.fn_check_titolo_iva_ambito` le scrive una volta, e i due guard la chiamano:

* una riga di ambito su un titolo che vale per **tutto** è rifiutata (`E_TITOLO_IVA_AMBITO_NON_AMMESSO`);
* il **pareggio** è rifiutato: due titoli attivi dello stesso soggetto, verso lo stesso emittente, dello stesso
  tipo, in periodi che si toccano, che coprono lo stesso oggetto allo stesso livello
  (`E_TITOLO_IVA_AMBITO_SOVRAPPOSTO`). Livelli diversi non sono un pareggio.

Il guard sulle righe scatta quando si aggiunge o si cambia una voce; quello sul titolo quando cambia il titolo (si
allarga una data, si riattiva, si cambia tipo), perché in quei casi questa tabella non viene toccata.

---

### ⚠️ Non c'è una colonna `attivo`, ed è voluto

L'ambito è la definizione del titolo, non un'entità con un ciclo di vita suo: una voce si aggiunge o si toglie.

E una riga di ambito **impedisce di spegnere il titolo**: con righe di ambito la disattivazione del titolo è
rifiutata (`E_ATTIVO_BLOCK_CHILDREN_EXIST`). Per farlo uscire si chiude la sua data di fine, oppure si tolgono le
righe di ambito prima di spegnerlo.

---

### Le righe spariscono col titolo

La cancellazione del titolo cancella le sue righe di ambito, al contrario del registro dei movimenti: un ambito è
una clausola, che senza il suo titolo non significa niente; un movimento è un fatto contabile.

---

### Chi le vede

La tabella ha la RLS, e la eredita dal titolo: una sessione con ruolo applicativo `OPERATORE` vede e scrive le righe
dei titoli presentati a un emittente del suo perimetro; le sessioni degli altri ruoli applicativi non ne vedono
nessuna. Chi può scrivere un titolo ne vede quindi tutte le righe, ed è ciò che permette ai guard dell'ambito di
girare coi permessi di chi scrive.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — la riga su un titolo ristretto che si registra, quella su un
  titolo totale rifiutata, il pareggio sullo stesso articolo rifiutato, i livelli diversi che passano, il periodo
  del titolo allargato che fa scattare il guard.

---

### Note di migrazione

* 2026-08-29 — nasce col titolo.

---

{% include-markdown "signature-core.md" %}
