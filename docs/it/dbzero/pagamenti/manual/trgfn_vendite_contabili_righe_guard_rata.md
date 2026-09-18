## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_righe_guard_rata`

### 🎯 Scopo Principale

(rev 2026-08-22)

Due domande sulla **rata** indicata da una riga contabile, con **due esiti
opposti**:

| | Domanda | Che cosa fa il database |
| --- | --- | --- |
| **Coerenza** | «questa rata appartiene davvero a questa fattura?» | 🔒 **RIFIUTA** — è un'incoerenza logica, non un fatto del mondo |
| **Capienza** | «c'è ancora spazio su questa rata?» | ⚠️ **SEGNALA** — che il cliente paghi di più, o paghi due volte, **è un fatto del mondo** |

> *«I pagamenti anche di una fattura completamente saldata devono essere
> accettati; segnaliamo che il documento risulta già saldato, ma se l'operatore
> conferma è sua la responsabilità.»*

---

### ⭐ La regola della capienza è una sola, e non nomina né fatture né note di credito

> **Un movimento normale RIDUCE ciò che manca, e NON lo supera.**
> Tutto il resto si segnala.

Due condizioni, con **R** = quanto resta da regolare sulla rata:

1. **va nel verso giusto** — riduce ciò che manca, non lo aumenta;
2. **non lo scavalca** — al massimo lo azzera.

⭐ **Non ha estremi fissi, ed è ciò che la salva.** La forma
`0 ≤ Σ ≤ importo` su un documento a credito diventa `[0, −50]`, cioè un
intervallo **vuoto**: una porta chiusa travestita da controllo. Questa guarda il
**rapporto fra il movimento e ciò che resta**, quindi coi versi già invertiti da
sé si comporta identica.

ℹ️ `R = 0` non è un caso a parte: è «nessuno spazio in nessuna direzione», cioè
il documento già saldato.

### ⭐ La forzatura: due tempi, nessun permesso

```text
1° tentativo, forzata = false → RIFIUTATO, con la ragione e i numeri
2° tentativo, forzata = true  → ACCETTATO, e resta scritto sulla riga
```

⛔ **Nessuna azione di processo, nessun permesso**, e la regola è **simmetrica**
nei due versi. L'asimmetria che il piano prevedeva è caduta su un esempio
concreto: *pagato 110, rimborso 15 invece di 10* è l'estremo inferiore, e non è
un capriccio — è un calcolo fatto su un dato vecchio, e **capita**. Vietarlo
sposterebbe il problema **fuori** dal sistema invece di registrarlo.

---

### Quando si guarda, e quando no

* la **coerenza** ogni volta che ci sono **rata e fattura**;
* la **capienza** solo quando la riga **occupa spazio davvero**: attiva e in uno
  stato `is_postabile`.

> 🔴 **Il caso che si sbaglia facile.** Se la capienza si verificasse a ogni
> cambio di stato, portare a `SCARTATA` una riga sospesa — cioè **toglierla di
> mezzo** — verrebbe rifiutata perché nel frattempo un'altra riga ha occupato lo
> spazio. Si rifiuterebbe **un gesto che libera**.
>
> ℹ️ E il posting non lo incontra: quando la riga passa a «registrata» il suo
> movimento è già scritto ed è **escluso dal conto** (si chiede lo spazio *prima
> di sé*), quindi il conto torna identico a quando era abbinata.

### ⭐ Una rata senza fattura: qui si tace

Non è **incoerente**, è **incompleta** — e a dirlo è il guard sui dati, quando
lo stato lo pretende: *«per portare la riga in abbinata servono la fattura e il
cliente»*.

⚠️ I `BEFORE ROW` girano in ordine **alfabetico**, quindi questo guard parla
*prima* di quello sui dati: **tacere qui è ciò che lascia parlare il messaggio
giusto**. Rispondere «la rata non è di quella fattura» a chi la fattura non l'ha
ancora messa sarebbe vero, e inutile.

### 🔴 Perché un guard solo e non due

Perché sono due domande sullo **stesso dato**, nello **stesso istante**, e la
seconda ha senso solo se la prima è passata: discutere di quanto spazio c'è su
una rata che non è di quella fattura non significa niente. Due trigger separati
non potrebbero garantirlo — l'ordine dei `BEFORE ROW` è quello dei **nomi**, non
quello del ragionamento.

---

### ⚠️ Le due letture non sono uguali, e la differenza è voluta

| Chi | Come legge | Perché |
| --- | --- | --- |
| **coerenza** | `script.fn_check_scadenza_di_fattura`, **fuori** dalla row security | deve poter dire «non è di questa fattura» e non «non la vedo»: sono due verità opposte che danno lo stesso `EXISTS` falso |
| **capienza** | `pagamenti.fn_get_saldo_rata`, **invoker** | lì «non la vedi» diventa `E_RATA_NON_TROVATA`, ed è corretto: chi non vede quella rata non ci deve imputare denaro |

### ⚠️ Error handling

| Codice | Classe |
| --- | --- |
| `E_RIGA_CONTABILE_RATA_INCOERENTE` | `DATO_ERRATO` (400) — il contesto porta `campo = scadenza_id`, perché l'interfaccia lo evidenzi |
| `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` | `CONFLITTO_STATO` (409) — non c'è un campo sbagliato: l'importo può essere giusto, è il documento che non ha più spazio |

> ⚠️ **Il messaggio della coerenza porta l'ID della rata, non i suoi dati.**
> Quella rata appartiene a un **altro documento**, che può non essere di questo
> operatore: la domanda si fa fuori dalla row security *proprio per non far
> uscire niente*, e raccontarne numero e scadenza nel messaggio disferebbe la
> ragione per cui è fatta così.

> ⭐ **Il messaggio della capienza scrive gli importi a due decimali** (dal
> 18-09-2026): *«Sulla rata 1 del 30/09/2026 restano 500.00 da regolare: un
> importo di 600.00 non ci rientra»*. Fino a quel giorno il residuo usciva come
> `500.000000`: la variabile è dichiarata sul tipo della colonna
> `fatture_scadenze.importo`, che è `numeric(18,6)` — la scala con cui il
> progetto conserva gli importi di documento — e il `::text` la portava in una
> frase per una persona. La scala di stoccaggio non è un dato per chi legge: i
> due numeri escono con la stessa maschera (`FM999999990.00`, quella di
> `fn_conferma_sistemazione`), col segno, mentre il `context` per il registro
> degli errori tiene i valori grezzi. Lo pinnano `test-abbinamento-rata` (5) e
> `test-nc-rata-unica-v1` (9), che guardano i numeri della frase.

### ⚠️ E senza l'elenco a valle non basta

Il guard **accetta** la registrazione fuori capienza, purché dichiarata. Senza
[vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) quella
dichiarazione sarebbe *«un modo per nascondere, non per registrare»*: è la
ragione per cui la vista sta nello stesso lotto del guard che permette la
forzatura.

{% include-markdown "signature-core.md" %}
