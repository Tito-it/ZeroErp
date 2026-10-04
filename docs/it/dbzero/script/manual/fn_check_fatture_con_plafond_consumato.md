## 📘 Documentazione Concettuale – Funzione `script.fn_check_fatture_con_plafond_consumato`

> 👀 **Vedi anche**
>
> • [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro che legge
> • [script.fn_check_fatture_con_rettifiche](/dbzero/script/funzioni/fn_check_fatture_con_rettifiche) — la sorella, stesso stampo
> • [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — la pulizia che la usa come guard

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-04, `20261004-07`)

Dice se delle fatture hanno già **consumato il plafond** di una dichiarazione d'intento,
cioè se nel registro dei movimenti c'è almeno una riga che le nomina.

Risponde `[]` se nessuna ha consumato; altrimenti un motivo solo:

| `codice` | `reason` | `dettaglio` |
| --- | --- | --- |
| `E_FATTURE_PLAFOND_CONSUMATO` | `PLAFOND_CONSUMATO` | **quante fatture** hanno consumato |

---

### ⭐ Perché consumato vuol dire «non si torna indietro»

Il plafond si consuma all'**emissione**, nel passaggio a definitiva, **prima** che la
fattura prenda il numero. Il movimento scritto nel registro è un fatto contabile: il
registro è **solo aggiunte**, e le sue chiavi verso la fattura e la riga sono fatte
apposta per non lasciar cancellare il documento.

Disfare la fattura vorrebbe dire cancellare quel fatto. E uno storno non basterebbe:
anche lo storno nominerebbe la fattura. Quindi una fattura che ha consumato plafond si
tratta come una fattura numerata: **il lotto va avanti**. Il passaggio a definitiva
riprende fattura per fattura, e il consumo non si ripete (è idempotente).

Decisione di Tid del 2026-10-04 (`brief-db-bom-flag-quantita-e-kit-in-fattura` §14,
strada A).

---

### Chi la usa

* le tre porte di reset, ciascuna nella sua funzione di controllo:
  [riporta a draft](/dbzero/script/funzioni/fn_check_lotto_riportabile_a_draft),
  [annulla lotto](/dbzero/script/funzioni/fn_check_lotto_annullabile),
  [elimina fattura](/dbzero/script/funzioni/fn_check_fattura_eliminabile_da_lotto) —
  e per loro tramite il pulsante si spegne col motivo;
* la pulizia, come difesa della porta che nessuno ha ancora scritto.

---

### Regole

* Conta **qualunque** movimento che nomini la fattura: è la chiave esterna a impedire la
  cancellazione, non il segno. Anche un kit che vale zero (+50 e −50) ha due movimenti, e
  blocca.
* Conta le **fatture**, non i movimenti: all'operatore serve sapere quali documenti sono
  intoccabili.
* Un insieme vuoto o `NULL` non è un errore: risponde `[]`.
* ⚠️ Legge sotto le regole di visibilità per emittente. Un chiamante fuori perimetro
  potrebbe non vedere i movimenti: in quel caso è la chiave esterna a fermare la
  cancellazione, con l'errore tecnico di prima. Nessun peggioramento, ma nemmeno la
  frase giusta.

---

{% include-markdown "signature-core.md" %}
