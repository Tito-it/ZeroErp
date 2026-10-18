## 📘 Documentazione Concettuale – Funzione `vendite.fn_provision_registri`

> 👀 **Vedi anche**
>
> **Le due porte che la usano:**
>
> • [vendite.fn_provision_registri_emittente](/dbzero/vendite/manual/fn_provision_registri_emittente) — per un emittente
> • [vendite.fn_provision_registri_famiglia](/dbzero/vendite/manual/fn_provision_registri_famiglia) — per una famiglia
>
> **Approfondimenti tabelle:**
>
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> • [vendite.famiglie_documento](/dbzero/vendite/manual/famiglie_documento)
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — funzione nata il 2026-09-01)*

**È la sede unica di «come nasce un registro di numerazione».** Crea i registri
**mancanti** per le combinazioni (emittente, famiglia non fiscale) che i filtri
selezionano, e dice quanti ne ha creati.

I due filtri sono entrambi opzionali, e `NULL` significa *tutti*:

| Chiamata | Che cosa fa |
| --- | --- |
| solo l'emittente | dà a quell'emittente i registri che gli mancano |
| solo la famiglia | dà a quella famiglia il suo registro su ogni emittente |
| nessuno dei due | riallinea tutto |

---

### ⛔ Perché esiste: per non avere due copie della stessa regola

Fino al 2026-09-01 il provisioning esisteva **solo per emittente**, e la regola
di come nasce un registro viveva dentro quella funzione. Quando è servita la
gemella per famiglia, la strada facile era copiare la `SELECT`.

⚠️ **Copiata, la prima correzione che ne tocca una sola produce due registri
diversi per la stessa coppia** — e non si vede il giorno stesso: si vede sei mesi
dopo, su un emittente solo, quando qualcuno nota che un codice non segue la
regola degli altri.

⇒ La regola sta qui, una volta. Gli involucri sopra cambiano **il filtro**, non
la regola.

---

### Che cosa decide, esattamente

| Colonna del registro nuovo | Da dove viene |
| --- | --- |
| `codice` | le prime tre lettere della famiglia + l'id dell'emittente — deterministico, unico per costruzione, e dentro i 16 caratteri della colonna |
| `descrizione` | «Registro *famiglia* — *codice emittente*», la parte parlante |
| `prefisso`, `lunghezza_numero` | ⭐ **il default della famiglia**: prefisso e cifre sono proprietà del **tipo documento**, e il registro ne tiene l'**effettivo** |
| `reset_policy` | `ANNUALE` |
| `utility_id` | vuoto: un registro per famiglia, valido per tutte le utility |
| `meta.origine` | `C2-12` — ⚠️ dice **quale meccanismo** ha creato la riga, non chi ha chiamato: le righe nate dalle due porte sono la stessa cosa |

⛔ **Il codice non porta la sigla dell'emittente**, ed è una scelta: quella è
`varchar(32)` contro i 16 del codice, e troncarla su un vincolo di unicità
trasformerebbe due sigle simili in una collisione.

---

### ⭐ Ripetibile senza danni, e su quale chiave

Il controllo «esiste già?» guarda la **coppia (emittente, famiglia)**, non il
codice. ⇒ Un registro creato a mano con un altro codice vale lo stesso e non ne
fa nascere un secondo.

È la proprietà che permette di appoggiare le due porte a eventi ripetibili senza
doversi chiedere ogni volta *«l'ho già fatto?»*.

---

### Cosa non fa, ed è voluto

* **le famiglie spente non producono registri**: il filtro `attivo` sta qui, e le
  due porte non lo ripetono;
* **non modifica** un registro esistente. Se qualcuno ne ha cambiato la serie o
  le regole di reset, quella è una decisione: non viene riscritta.

---

### 🔄 rev 2026-10-18 — anche il registro delle fatture

Fino a oggi la FATTURA restava fuori, con un letterale: il suo registro dipende da
(tipo documento, natura), e nessun altro lo creava. Risultato: **nessun emittente
nasceva capace di fatturare**, nemmeno in un'installazione nuova (R-BE-14, il
caso dell'emittente di prova del verbo di sviluppo).

Ora (decisioni D-14a … D-14d di Tid), per ogni emittente selezionato che ha
**coppie scoperte** — le dice
[`vendite.fn_coppie_fattura_scoperte`](/dbzero/vendite/manual/fn_coppie_fattura_scoperte):

| Passo | Che cosa |
| --- | --- |
| 1 | nasce **un** registro delle fatture **standard** (codice `FAT-<emittente>`), con la stessa regola degli altri registri: **un solo `INSERT`** per tutte le famiglie, cambiano solo le condizioni |
| 2 | ogni coppia scoperta si collega a lui in `vendite.tipi_doc_fiscale_registri` |

* un emittente configurato a mano riceve lo standard **solo per le coppie che non
  ha**;
* uno standard **spento** non si rifà e non si ricollega: spegnerlo è una scelta,
  e la coppia resta scoperta;
* il numero restituito resta «quanti **registri**»: i collegamenti non si contano.

⭐ **La regola del codice esce in
`vendite.fn_codice_registro_provisionato`**: serve a far nascere i registri delle
famiglie, a far nascere lo standard e a **ritrovarlo** per collegarlo. Tre copie
dello stesso letterale nella stessa funzione: la prima che cambiasse romperebbe il
collegamento in silenzio.

Chi la chiama per la fattura: la porta per emittente (alla nascita e alla
riaccensione), la porta per famiglia con `'FATTURA'` (i trigger su
`config.tipi_doc_fiscale` e `config.nature_doc_fiscale` quando nasce o si accende
una riga, e la sistemazione degli emittenti esistenti, changeSet `20261019-11`).

---

### ⚠️ Note operative

* **`SECURITY DEFINER`, come l'originale**: scrive sui registri leggendo gli
  emittenti, e la può chiamare un trigger che gira nel contesto di chi ha creato
  l'emittente. Questo cambiamento non è la sede per rivedere quel privilegio.
* **Non è concessa all'applicazione**: si passa dagli involucri, che dichiarano
  quale delle due porte si sta usando.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.6;
`brief-db-processi-accensione-per-ambiente` §6.14 (la fattura).*
