## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_righe_guard_rata`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — la riga che indica la rata, e la sua bandiera `forzata`
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — le rate
>
> Approfondimento viste:
>
> * [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — l'elenco a valle delle forzature
>
> Approfondimento funzioni:
>
> * [script.fn_check_scadenza_di_fattura](/dbzero/script/funzioni/fn_check_scadenza_di_fattura) — la domanda di coerenza, fuori dalla row security
> * [pagamenti.fn_get_saldo_rata](/dbzero/pagamenti/funzioni/fn_get_saldo_rata) — quanto resta sulla rata, con i diritti di chi scrive
> * [pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_stato_dati) — chi parla quando la rata non ha fattura
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — il piano rate e gli incassi

---

### 🎯 Scopo Principale

Fa due domande sulla **rata** indicata da una riga contabile, con **due esiti opposti**: rifiuta
una rata che non appartiene alla fattura della riga, e segnala un importo che non ci sta.

| | Domanda | Che cosa fa il database |
| --- | --- | --- |
| **Coerenza** | «questa rata appartiene davvero a questa fattura?» | 🔒 **RIFIUTA**: è un'incoerenza logica, non un fatto del mondo |
| **Capienza** | «c'è ancora spazio su questa rata?» | ⚠️ **SEGNALA**: che il cliente paghi di più, o paghi due volte, **è un fatto del mondo** |

> *«I pagamenti anche di una fattura completamente saldata devono essere accettati; segnaliamo
> che il documento risulta già saldato, ma se l'operatore conferma è sua la responsabilità.»*

---

### ⭐ La regola della capienza è una sola, e non nomina né fatture né note di credito

> **Un movimento normale RIDUCE ciò che manca, e NON lo supera.**
> Tutto il resto si segnala.

Due condizioni, con **R** = quanto resta da regolare sulla rata:

1. **va nel verso giusto**: riduce ciò che manca, non lo aumenta;
2. **non lo scavalca**: al massimo lo azzera.

⭐ **Non ha estremi fissi, ed è ciò che la salva.** Un controllo «fra zero e l'importo della
rata», su un documento a credito, diventa un intervallo **vuoto**: una porta chiusa travestita da
controllo. Questa guarda il **rapporto fra il movimento e ciò che resta**, quindi coi versi già
invertiti da sé si comporta identica.

ℹ️ `R = 0` non è un caso a parte: è «nessuno spazio in nessuna direzione», cioè il documento già
saldato.

---

### ⭐ La forzatura: due tempi, nessun permesso

```text
1° tentativo, forzata = false → RIFIUTATO, con la ragione e i numeri
2° tentativo, forzata = true  → ACCETTATO, e resta scritto sulla riga
```

⛔ **Nessuna azione di processo, nessun permesso**, e la regola è **simmetrica** nei due versi.
Un'asimmetria non regge a un esempio concreto: *pagato 110, rimborso 15 invece di 10* è
l'estremo inferiore, e non è un capriccio: è un calcolo fatto su un dato vecchio, e **capita**.
Vietarlo sposterebbe il problema **fuori** dal sistema invece di registrarlo.

---

### Quando si guarda, e quando no

* la **coerenza** ogni volta che ci sono **rata e fattura**;
* la **capienza** solo quando la riga **occupa spazio davvero**: attiva, in uno stato
  `is_postabile`, e non forzata.

Su un aggiornamento che non tocca rata, fattura, importo, stato, `attivo` o `forzata` il guard
non guarda niente.

🔴 **Il caso che si sbaglia facile.** Se la capienza si verificasse a ogni cambio di stato,
portare a `SCARTATA` una riga sospesa (cioè **toglierla di mezzo**) verrebbe rifiutato perché nel
frattempo un'altra riga ha occupato lo spazio. Si rifiuterebbe **un gesto che libera**.

ℹ️ E il posting non lo incontra: quando la riga passa a «registrata» il suo movimento è già
scritto ed è **escluso dal conto** (si chiede lo spazio *prima di sé*), quindi il conto torna
identico a quando era abbinata.

---

### ⭐ Una rata senza fattura: qui si tace

Non è **incoerente**, è **incompleta**, e a dirlo è il guard sui dati, quando lo stato lo
pretende: *«per portare la riga in abbinata servono la fattura e il cliente»*.

⚠️ I `BEFORE ROW` girano in ordine **alfabetico**, quindi questo guard parla *prima* di quello
sui dati: **tacere qui è ciò che lascia parlare il messaggio giusto**. Rispondere «la rata non è
di quella fattura» a chi la fattura non l'ha ancora messa sarebbe vero, e inutile.

---

### 🔴 Un guard solo e non due

Sono due domande sullo **stesso dato**, nello **stesso istante**, e la seconda ha senso solo se
la prima è passata: discutere di quanto spazio c'è su una rata che non è di quella fattura non
significa niente. Due trigger separati non potrebbero garantirlo: l'ordine dei `BEFORE ROW` è
quello dei **nomi**, non quello del ragionamento.

---

### ⚠️ Le due letture non sono uguali, e la differenza è voluta

| Chi | Come legge | Perché |
| --- | --- | --- |
| **coerenza** | [script.fn_check_scadenza_di_fattura](/dbzero/script/funzioni/fn_check_scadenza_di_fattura), **fuori** dalla row security | deve poter dire «non è di questa fattura» e non «non la vedo»: sono due verità opposte che, sotto la row security, darebbero lo stesso «non esiste» |
| **capienza** | [pagamenti.fn_get_saldo_rata](/dbzero/pagamenti/funzioni/fn_get_saldo_rata), con i diritti di chi scrive | lì «non la vedi» diventa `E_RATA_NON_TROVATA`, ed è corretto: chi non vede quella rata non ci deve imputare denaro |

---

### ⚠️ Che cosa dicono i messaggi, e che cosa no

* **Il messaggio della coerenza porta l'id della rata, non i suoi dati.** Quella rata appartiene
  a un **altro documento**, che può non essere di questo operatore: la domanda si fa fuori dalla
  row security *proprio per non far uscire niente*, e raccontarne numero e scadenza nel
  messaggio disferebbe la ragione per cui è fatta così.
* ⭐ **Il messaggio della capienza scrive gli importi a due decimali, col segno**, e nomina la
  rata col suo numero e la sua data di scadenza. Gli importi di documento si conservano con sei
  decimali, ma la scala di stoccaggio non è un dato per chi legge: i due numeri escono con la
  stessa maschera di [fn_conferma_sistemazione](/dbzero/pagamenti/funzioni/fn_conferma_sistemazione),
  mentre il contesto per il registro degli errori tiene i valori grezzi.

---

### ⚠️ Senza l'elenco a valle non basta

Il guard **accetta** la registrazione fuori capienza, purché dichiarata. Senza
[vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) quella dichiarazione
sarebbe *«un modo per nascondere, non per registrare»*: è la ragione per cui la vista è nata
insieme al guard che permette la forzatura.

---

### Codici errore

* `E_RIGA_CONTABILE_RATA_INCOERENTE` — la rata non appartiene alla fattura della riga. Il
  contesto porta `campo = scadenza_id`, perché l'interfaccia lo evidenzi.
* `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` — l'importo va nel verso sbagliato o scavalca ciò che
  resta, e la riga non è forzata. Non c'è un campo sbagliato: l'importo può essere giusto, è il
  documento che non ha più spazio.
* `E_RATA_NON_TROVATA` — da `fn_get_saldo_rata`, quando chi scrive non vede la rata.

---

### Test

* `db/pgtap/pagamenti/test-abbinamento-rata.sql` — coerenza, rata senza fattura che tace,
  capienza coi numeri, forzatura che entra e resta scritta, la sospesa che non occupa spazio, la
  scartata che non viene rifiutata, la rata invisibile a chi non deve vederla.
* `db/pgtap/vendite/test-nc-rata-unica-v1.sql` — la stessa regola su una nota di credito: il
  rimborso nel verso giusto entra, «il cliente paga la NC» viene segnalato (test 9), la forzatura
  entra.
* `db/pgtap/pagamenti/test-posta-riga-tardiva-v1.sql` — capienza e coerenza anche sulla
  registrazione tardiva.

---

### Note di migrazione

* 2026-08-22 — nasce con l'abbinamento alla rata.
* 2026-09-18 — gli importi nel messaggio della capienza passano a due decimali: fino ad allora
  il residuo usciva con la scala di stoccaggio (`500.000000`). I test che guardano i numeri della
  frase sono `test-abbinamento-rata` (5) e `test-nc-rata-unica-v1` (9).

---

{% include-markdown "signature-core.md" %}
