# Guida — Termini di pagamento (quando, e in quante volte, si paga)

> **Ultima revisione**: 22 agosto 2026 — prima stesura. Nasce dalla riforma del
> 31 luglio 2026, che ha fatto del catalogo dei termini **l'unico** posto in cui
> vivono le condizioni di pagamento: prima alcune stavano sulla scheda del
> cliente, come coppia di campi liberi, e le due strade potevano dire cose
> diverse.
>
> **Destinatari**: operatori amministrazione e vendite, analisti funzionali.
>
> **Vedi anche** — scheda tecnica della tabella:
>
> * [config.termini_pagamento](/dbzero/config/tabelle/termini_pagamento) — colonne, vincoli, formula
> * [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento) — il **come** si paga
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — le rate generate
>
> **Vedi anche** — guide correlate:
>
> * [Fatturazione end-to-end](/guide/fatturazione) — dove il piano rate viene generato
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — cosa succede alle rate dopo
> * [Generazione di un cliente](/guide/generazione-cliente) — il termine sulla scheda cliente
> * [Gestione ordini](/guide/gestione-ordini) · [Gestione preventivi](/guide/gestione-preventivi)

---

## 1. Cos'è un termine di pagamento

Un termine di pagamento risponde a due domande, e solo a quelle:

* **quando** si paga — fra quanti giorni dalla data della fattura;
* **in quante volte** si paga — una rata sola, oppure più rate a distanza fissa.

Non dice **come** si paga: bonifico, RID, contanti sono la *modalità di
pagamento*, un catalogo separato. I due dati viaggiano insieme sul documento ma
sono cose diverse, e li si sceglie separatamente.

Il termine non calcola niente da solo: viene letto quando la fattura viene
preparata e trasformato nel **piano rate** del documento — l'elenco «questa
somma, entro questa data», che è la base di tutto ciò che viene dopo
(sollecito, incasso, riconciliazione).

---

## 2. Il catalogo di oggi

Nove termini disponibili. Tutti dividono il totale **in parti uguali** fra le
rate previste.

| Termine | Quando si paga | Rate |
| --- | --- | ---: |
| Unica rata **(default)** | subito, alla data della fattura | 1 |
| 30 gg data fattura | dopo 30 giorni | 1 |
| 30 gg data fattura, **fine mese** | dopo 30 giorni, spostato all'ultimo giorno di quel mese | 1 |
| 60 gg data fattura | dopo 60 giorni | 1 |
| 60 gg data fattura, **fine mese** | dopo 60 giorni, spostato a fine mese | 1 |
| 90 gg data fattura | dopo 90 giorni | 1 |
| 90 gg data fattura, **fine mese** | dopo 90 giorni, spostato a fine mese | 1 |
| Rate a 30/60 giorni | metà a 30 giorni, metà a 60 | 2 |
| Rate a 30/60 giorni, **fine mese** | come sopra, entrambe spostate a fine mese | 2 |

«**Fine mese**» significa che la data calcolata slitta all'ultimo giorno del
proprio mese: una fattura del 3 marzo con «30 gg fine mese» scade il **30
aprile**, non il 2 aprile.

---

## 3. Chi decide il termine di una fattura

Una fattura raccoglie il lavoro di più righe, che possono arrivare da documenti
diversi. Il sistema non chiede a nessuno di scegliere: scende **quattro
livelli** e si ferma al primo che risponde.

| # | Dove guarda | Nota |
| --- | --- | --- |
| 1 | Il **documento** che ha originato la riga (ordine o preventivo) | L'ordine porta termine *e* modalità, il preventivo il solo termine |
| 2 | La **commessa** | La commessa possiede le proprie condizioni: è il livello più specifico |
| 3 | Il **cliente** | Vale per tutto ciò che non ha detto altro |
| 4 | **Unica rata** | Rete di sicurezza: nessuna fattura resta senza piano rate |

Tre cose che vale la pena sapere:

* **La commessa viene prima del cliente**, ed è voluto. Cambiare le condizioni di
  un cliente non deve riscrivere quelle delle commesse già aperte: chi lavora su
  una commessa ha già concordato le sue condizioni.
* **Termine e modalità scendono separatamente** e possono fermarsi a livelli
  diversi. Solo il termine ha un valore di riserva: per la modalità non esiste
  un «predefinito», perché sceglierne uno a caso finirebbe sulla fattura
  elettronica come un dato inventato.
* **Se il cliente non ha un termine**, la fattura non si blocca: prende «unica
  rata». Non è un errore da correggere di corsa, è il comportamento previsto.

---

## 4. ⚠️ Il termine decide anche **quante fatture** nascono

È la conseguenza meno intuitiva, e la sola che cambia il lavoro di chi vende.

Le condizioni di pagamento fanno parte dei criteri con cui il lavoro si
raggruppa. Due documenti dello stesso cliente **con termini diversi non
finiscono nella stessa fattura**: aprono due commesse distinte e producono due
documenti distinti.

Non è un limite: è l'unico esito corretto. Una fattura sola non potrebbe portare
due scadenzari diversi — o si sceglie un termine sacrificando l'altro, o si
spacca il documento. Il sistema sceglie di spaccare, e lo fa **nel momento in
cui la divergenza nasce** (al push su commessa), invece di farla comparire mesi
dopo come una fattura in più che nessuno sa spiegare.

Ricaduta pratica: se ci si aspettava una fattura sola e ne arrivano due, la
prima cosa da guardare sono le condizioni di pagamento dei documenti di
partenza.

---

## 5. Come si legge un piano rate

```text
data della rata n = data fattura + giorni della prima rata + (n − 1) × intervallo
se il termine è «fine mese» → ogni data slitta all'ultimo giorno del proprio mese

importo di ogni rata = totale da pagare ÷ numero di rate, arrotondato al centesimo
importo dell'ULTIMA rata = totale da pagare − somma di tutte le precedenti
```

**La quadratura sta sull'ultima rata.** Le prime portano la quota arrotondata,
l'ultima assorbe la differenza: la somma delle rate è **esattamente** il totale
del documento, mai una sua approssimazione. Su un totale di 10,03 € in due rate
il piano è `5,02 + 5,01`, non `5,02 + 5,02`.

Il **totale da pagare** non è l'imponibile né il totale documento: è quello che
il cliente deve versare davvero, cioè il totale del documento al netto degli
acconti e dei minimi già incassati e con gli eventuali arrotondamenti. È per
questo che il piano rate viene generato **dopo** il calcolo dell'IVA e dei
totali, mai prima.

### Quando le rate non nascono affatto

| Situazione | Cosa succede |
| --- | --- |
| Il documento è **interamente coperto** da acconti (totale da pagare a zero) | Nessuna rata. È un documento normale: non c'è niente da incassare |
| Il totale è **negativo** (saldo a favore del cliente, note di credito) | Nessuna rata, e una **nota informativa** sulla fattura. A volte è corretto, a volte è un acconto configurato male: va guardata, non ignorata |
| I totali non sono ancora stati calcolati | Errore, e la lavorazione si ferma: è un passo eseguito fuori ordine, non un dato sbagliato |

---

## 6. La fattura conserva la fotografia del termine

Quando le rate vengono generate, la fattura si porta dietro una **copia dei
valori** del termine usato — quante rate, quanti giorni, fine mese sì o no.

Serve perché un documento fiscale già emesso deve continuare a spiegare le rate
che ha, anche se un domani il catalogo cambia. Un riferimento al solo nome del
termine non basterebbe: se qualcuno lo modificasse, la fattura vecchia
racconterebbe una regola che non è quella con cui è nata.

---

## 7. Serve una condizione fuori standard

Non esiste un campo libero «giorni» da riempire sul cliente: quella strada è
stata **eliminata** nel luglio 2026, proprio perché conviveva col catalogo e le
due potevano dire cose diverse. Chi ha condizioni particolari usa **un termine
dedicato a catalogo**.

Tre regole, in ordine di importanza:

1. **Un termine nuovo si aggiunge**, si chiede a chi gestisce il sistema: il
   catalogo si popola da file di configurazione, non con inserimenti a mano.
2. **Un termine già in uso non si modifica.** Cambiarlo cambierebbe il
   significato di ciò che è già stato concordato: se serve una variante, se ne
   crea una nuova.
3. **Un termine in uso non si disattiva.** Il sistema lo impedisce, ed è
   corretto: un documento non deve perdere la regola che spiega le sue rate.
   Oggi non esiste un modo per dire «non più proponibile sui nuovi, valido sui
   vecchi» — è una funzionalità che manca, non una svista.

---

## 8. Dove si vede a video

| Dove | Cosa si vede |
| --- | --- |
| Scheda **cliente** | Termine e modalità di pagamento predefiniti del cliente |
| **Preventivo** e **ordine** | Termine (e sull'ordine anche la modalità) del singolo documento |
| Drawer **fattura** | Termine e modalità applicati, e il **piano rate** con la prossima scadenza |

Sui documenti creati prima dell'agosto 2026 questi campi restano vuoti: non
sono stati riempiti a posteriori, e non lo saranno.

---

## 9. Cosa non fa ancora

Il piano rate dice **quanto** si deve e **entro quando**. Non dice ancora se è
stato pagato: il collegamento fra la singola rata e l'incasso che la salda è in
lavorazione. Fino ad allora le due metà — scadenze e incassi — si leggono
separatamente, come spiegato in
[Gestione dei pagamenti](/guide/gestione-dei-pagamenti).

---
{% include-markdown "signature-core.md" %}
