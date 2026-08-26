# Brief DB — un billing account può cambiare emittente?

> **Natura di questo documento:** ⚠️ **è una riflessione di dominio, non un
> piano.** Non c'è una consegna da scrivere finché la domanda del titolo non ha
> una risposta. Chi cerca un difetto con un rimedio noto è nell'altro brief.
>
> **Destinatario:** Tid, per la decisione. Il team DB solo dopo.
>
> **Origine.** Tid, 2026-08-26, leggendo la D-3 di
> [brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md):
> *«ho il dubbio che sia corretto spostare un billing account da un emittente ad
> un altro; credo che al più in futuro si determini la duplica di un BA su altro,
> ma spostare quel BA è un problema ai fini fiscali: non può scomparire un
> cliente che ha già delle fatture con un emittente perché è andato ad un
> altro»*.
>
> **Separato apposta** dal brief sull'invariante della commessa (richiesta di
> Tid, stesso giorno): là c'è un difetto con un rimedio chiaro, qui una domanda
> di dominio con implicazioni fiscali. Mescolarli farebbe rimandare il primo in
> attesa del secondo.
>
> ⛔ **Stato: nessuna decisione, nessun file scritto.**

---

## 1. La domanda, in una riga

`anagrafiche.emittenti_fiscali_billing_account` dice a quale emittente fiscale
appartiene un billing account. Quella riga **si può aggiornare**. La domanda è se
debba potersi.

---

## 2. Cosa dice la struttura — e conferma l'intuizione di Tid

⭐ **La fattura NON segue il cliente: congela il proprio emittente.**
`vendite.fatture.emittente_soggetto_ruolo_id` è **`NOT NULL`**, ha un indice
proprio (`ix_fatture_emitt_data`), e accanto c'è persino un
`emittente_snapshot jsonb` — cioè una copia congelata dei dati dell'emittente al
momento dell'emissione. Il progetto ha già deciso, e bene, che **il documento
fiscale porta con sé chi lo ha emesso**.

⇒ **Spostare un BA non riscrive la storia: la orfana.** Le fatture restano
sull'emittente vecchio; il cliente passa al nuovo. Da quel momento l'operatore
dell'emittente che ha emesso quelle fatture continua a **vedere il documento** e
smette di **vedere il cliente**. È esattamente il difetto che Tid descrive, e non
è un'ipotesi: discende dalle colonne.

⚠️ **E il perimetro è preso sul serio dappertutto, tranne qui.**
`vendite.fatture` ha `trg_fatture_a10_guard_emittente_scope`, che impedisce di
scrivere un documento fuori dal proprio emittente. L'albero dei billing account
ha `fn_guard_albero_ba_emittente`, che vieta di mescolare due emittenti fra padre
e figli. Ma la riga che **decide** l'emittente di un BA ha solo due presidi — il
default globale unico e l'omogeneità dell'albero — e **nessuno dei due guarda la
storia già scritta**.

---

## 3. La tensione da sciogliere, ed è vera

⛔ **Vietare e basta ha un costo.** Un billing account può nascere sotto
l'emittente sbagliato: è un errore di inserimento ordinario. Se il legame è
immutabile, quell'errore non si corregge più — e la via d'uscita diventa
cancellare e rifare, che è peggio, o lasciare il dato sbagliato, che è peggio
ancora.

⇒ La domanda vera **non è** «si può cambiare?» ma **«fino a quando?»**. E la
risposta plausibile è: *finché non c'è storia fiscale*. Che è una riga sola di
condizione, ma ne apre un'altra — ▼ D-2.

---

## 4. Le tre forme possibili — ⚠️ nessuna scelta, sono da pesare

| | Forma | Regge? | Costo |
| --- | --- | --- | --- |
| **a** | **Divieto assoluto**: il legame BA→emittente è immutabile dalla nascita | ✅ nessuna storia si orfana mai | ⛔ un BA nato sbagliato non si corregge |
| **b** | **Divieto condizionato alla storia**: libero finché il BA non ha documenti fiscali, vietato dopo | ✅ protegge ciò che va protetto e lascia correggere gli errori | ⚠️ dipende tutto da cosa conta come «storia» (D-2) |
| **c** | **Si duplica, non si sposta** — l'ipotesi di Tid: il cliente nasce una seconda volta sotto l'altro emittente, e il BA vecchio resta con la sua storia | ✅ fiscalmente è la forma più pulita: nessun documento cambia padrone | ⚠️ apre «chi è il cliente» su due BA gemelli — e il problema si sposta su chi li deve riconoscere come la stessa persona |

⭐ **b e c non sono alternative**: rispondono a due bisogni diversi. La **b** serve
a correggere un errore; la **c** serve quando il cliente passa **davvero**
all'altro emittente e da lì in avanti lavora lì. Probabilmente servono entrambe.

---

## 5. ❓ Le domande aperte

### D-1 — quale forma, fra le tre del §4?

⚠️ È la decisione di dominio, e le altre dipendono da questa.

### D-2 — che cosa conta come «storia» che blocca?

Se si sceglie la **b**, la condizione va definita con precisione, e le risposte
non si equivalgono:

* solo le **fatture emesse** — il criterio strettamente fiscale;
* oppure anche **commesse, DDT, ordini** — cioè qualunque lavoro già attribuito a
  quell'emittente, anche se non ancora fatturato.

⚠️ Il secondo è più prudente ma blocca prima, e su un BA appena creato con una
commessa vuota bloccherebbe una correzione ancora legittima.

### D-3 — con la forma «duplica», chi tiene insieme i due BA?

Due billing account gemelli su due emittenti sono, per il database, due clienti.
❓ Serve un legame esplicito fra loro — e allora è una colonna e un concetto
nuovo — oppure basta che sia lo **stesso soggetto** a monte, che è già il caso?

### D-4 — la correzione della commessa deve aspettare questa decisione?

⭐ **La mia lettura è no, ed è il motivo per cui i due brief sono separati.**
L'altro cantiere mette `NOT NULL` sulla colonna e la vincola al billing account:
è giusto **qualunque** risposta si dia qui. Se poi si sceglie di consentire lo
spostamento in qualche forma, il come propagarlo alle commesse si progetta lì,
sopra un invariante già chiuso — non al posto suo.

---

## 6. Cosa NON è in questo brief

* **L'invariante dell'emittente sulla commessa** (nullable, coerenza col BA):
  [brief-db-emittente-commessa-invariante.md](brief-db-emittente-commessa-invariante.md).
* **L'omogeneità dell'albero dei BA**, che è già presidiata e non va ridiscussa
  (`fn_guard_albero_ba_emittente`).

---

## 7. Registro

### 2026-08-26 · Nascita

Estratto dalla D-3 del brief sull'invariante della commessa, su richiesta di Tid
di **separare le competenze**: là un difetto con un rimedio chiaro, qui una
domanda di dominio con implicazioni fiscali, che ha bisogno di essere pensata e
non di essere programmata.

⭐ La struttura conferma l'intuizione che l'ha fatto nascere: la fattura congela
il proprio emittente (`NOT NULL` + `emittente_snapshot`), quindi spostare il
billing account non sposta i documenti — **li orfana**, e il cliente sparisce
dalla vista di chi quelle fatture le ha emesse.

⛔ Nessuna decisione presa, nessun file scritto.
