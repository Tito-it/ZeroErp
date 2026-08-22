## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_conferma_sistemazione`

### 🎯 Scopo Principale

(rev 2026-08-22)

La **madre** che esegue un atto di sistemazione: sceglie la strada e ci mette
sopra il denaro.

⭐ **Non inventa nessuna macchina.** Le tre esistevano già tutte (D15-a):

| Destinazione | Che cosa produce |
| --- | --- |
| `RIPORTO` | un **fondo fattura** `origine = MANUALE`, già `ASSEGNATO` |
| `RIMBORSO` | una **distinta a importi negativi** — D3-d, *«il denaro non ha versi, ha segni»* |
| `COMPENSAZIONE` | una **distinta sul centro dedicato**, con due righe che sommano a zero |

---

### ⭐ Perché è una madre

Scrive **in più posti** — la distinta, le sue righe, l'atto — e o riescono tutte
o non ne resta nessuna. Sta nel database e non nel backend perché è tutto SQL:
nessun `transaction.atomic()` attorno a più chiamate, **l'atomicità è dentro**.

### ⭐ Il segno si ricava dal saldo, e non si scrive due volte

La riga sulla fattura di partenza vale `sign(saldo) × |importo|`:

| Il documento | Residuo | Riga generata |
| --- | --- | --- |
| fattura sovra-incassata | negativo | **negativa** — il denaro esce |
| nota di credito sovra-rimborsata | positivo | **positiva** — il denaro rientra |

⚠️ Nessun `IF` su *«è una fattura o una nota»*: la formula **non nomina né l'una
né l'altra**. Un `CASE` sul tipo di documento è il punto in cui, prima o poi, si
dimentica un caso.

⭐ Nella compensazione la seconda riga è **l'opposto esatto** della prima: due
righe che sommano a zero, che è *letteralmente* che cosa vuol dire compensare.

### 🔴 Il controllo dell'eccedenza sta qui, non alla registrazione

Fra il momento in cui una persona **decide** e quello in cui **conferma** può
arrivare un altro incasso, o un'altra sistemazione può aver consumato lo stesso
credito.

> ⚠️ Verificare alla registrazione avrebbe dato una garanzia **che scade**. È la
> stessa forma di D13 sulla distinta: si controlla al gesto **irreversibile**,
> non a quello reversibile.

### ⭐ Ogni atto ha la sua distinta

`fn_get_or_create_vendite_contabile` è costruita per **condividere**: due
rimborsi sullo stesso canale nello stesso giorno riuserebbero la stessa testata,
e il secondo atto sbatterebbe su `uq_sistemazioni_contabile` con un `23505` muto.

⭐ La distinta di una sistemazione è **il documento di quell'atto** — è ciò che
rende coerente tutto il modello girato (D15-e) — quindi si crea diretta, e il suo
codice **porta l'id dell'atto**: `SIS_<id>_<timestamp>`.

### Regole principali

* **Il canale del rimborso è un parametro**, non una colonna dell'atto: *da quale
  conto esce il bonifico* è una decisione del momento in cui si paga, non di
  quando si decide di pagare. ⛔ Obbligatorio sul `RIMBORSO`, ignorato sulle altre
  due.
* Il fondo del riporto usa il tipo `F_F_ADD_ACC`, l'unico generico a catalogo, e
  nasce **`ASSEGNATO`**: il riporto nomina già la fattura di destinazione, e un
  fondo `DISPONIBILE` sarebbe un credito che aspetta una decisione **già presa**.
* ⚠️ Il riporto pretende sul documento di partenza tre colonne che su
  `vendite.fatture` sono **nullabili** e sul fondo sono obbligatorie (servizio,
  tipo documento, valuta): il controllo è qui, con un messaggio che dice **quale
  documento** le ha vuote — un `23502` direbbe solo il nome della colonna.
* ⚠️ Distinta e righe si scrivono in **due istruzioni separate**: padre e figlio
  nella stessa CTE non passano sotto la row security.
* `FOR UPDATE` sull'atto: due conferme in parallelo creerebbero due documenti per
  la stessa decisione.

---

{% include-markdown "signature-core.md" %}
