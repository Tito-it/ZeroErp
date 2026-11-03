## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_or_create_vendite_contabile`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta che trova o crea
> * [pagamenti.vendite_contabili_lotti](/dbzero/pagamenti/tabelle/vendite_contabili_lotti) — il ponte verso il lotto di fatturazione
> * [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti) — il lotto da cui deriva l'emittente
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — l'atto che crea la propria distinta da sé
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_emittente_distinta](/dbzero/pagamenti/funzioni/fn_get_emittente_distinta) — la sede unica che dice di chi è la distinta
> * [pagamenti.trgfn_vendite_contabili_gen_codice](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_gen_codice) — chi assegna il codice alla distinta nuova
> * [vendite.fn_sync_contabili_fondo_fattura](/dbzero/vendite/funzioni/fn_sync_contabili_fondo_fattura) — il giro dei fondi, uno dei chiamanti
> * [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic) — l'audit da cui prende «chi sta lavorando»

---

### 🎯 Scopo Principale

Trova la distinta contabile in cui mettere degli incassi, o la crea: una per centro,
canale, emittente, data contabile, data di registrazione, stato e origine — e, sul ramo
manuale, per operatore. Se riceve un lotto di fatturazione, cerca fra le distinte di quel
lotto e collega la distinta al lotto.

È costruita per **condividere**: due chiamate con la stessa chiave ottengono la stessa
distinta.

---

### ⭐ La distinta manuale è per operatore

Sul ramo manuale la chiave di riuso comprende **chi sta lavorando**. Una distinta `MANUALE` è
il **lotto di lavoro di una persona**, non «tutti gli incassi di lunedì»: due operatori che
inseriscono nello stesso giorno e sullo stesso canale ottengono **due distinte diverse**.

Era stata chiesta una funzione di blocco perché non si pestassero i piedi: con questo
raggruppamento **la contesa non esiste**, e il blocco non si costruisce.

⚠️ Sulle altre due origini l'operatore non entra nella chiave: una distinta `GENERATA` non è
il lotto di lavoro di nessuno, e una `AUTOMATICA` è il file.

ℹ️ «Chi sta lavorando» si legge con la **stessa espressione** con cui il trigger di audit
valorizza `user_insert`. Non è un dettaglio: la chiave di riuso confronta proprio quella
colonna, e se le due divergessero la funzione creerebbe una distinta nuova a ogni riga
inserita, **in silenzio**.

---

### ⭐ L'emittente si sa prima di cercare

L'emittente entra nella chiave di riuso, quindi si risolve **prima** di cercare la distinta,
o la manuale non ritroverebbe mai «quella di prima». Le fonti, in ordine:

1. l'**emittente dato** dal chiamante (l'id dell'emittente fiscale, ciò che backend e
   frontend conoscono);
2. il **lotto**, se c'è: chi passa un lotto sa già di chi è la distinta. Il giro di massa di
   un amministratore su tutti gli emittenti ha lotti di più aziende e una sessione che non
   ne risolve nessuno;
3. la sede unica [fn_get_emittente_distinta](/dbzero/pagamenti/funzioni/fn_get_emittente_distinta):
   il canale, poi l'operatore in sessione, poi il rifiuto parlante.

⚠️ **Un lotto che non c'è o che non si vede non cade sulla sessione.** La funzione gira con i
privilegi di chi la chiama, e i lotti hanno la RLS: la distinta del lotto di un altro
nascerebbe di chi agisce, agganciata a un lotto altrui. È un rifiuto tecnico; dalla pipeline
non ci si arriva, ci arriva solo una chiamata a mano.

⭐ Con l'emittente nella chiave anche la distinta generata senza lotto è **una per
emittente**: non raccoglie più i fondi di tutti.

---

### Il codice non si passa

La distinta nuova riceve il numero dal registro del suo emittente, assegnato dal trigger
[trgfn_vendite_contabili_gen_codice](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_gen_codice):
la funzione non lo compone e non lo passa. Il trigger rispetta un codice fornito solo per le
fixture dei test, e un test presidia che nessuna madre lo usi.

---

### L'origine ha un default onesto

Se il chiamante non dice l'origine, la distinta è `GENERATA`: chi chiama **senza dirlo** è
uno script. ⚠️ Un chiamante che inserisca una distinta manuale dimenticando l'origine la
vedrebbe risultare «prodotta dal sistema»: è il prezzo del default, accettato perché questa
funzione è l'unica strada che il progetto ammette.

---

### ⛔ Non crea la distinta di una sistemazione

La distinta nata da un atto la crea l'atto stesso, e ne tiene l'id: chiederla qui vorrebbe
dire far nascere la testata **sapendo già di chi sarebbe stata**, il verso opposto a come
funziona il processo. L'unicità *«una distinta per atto»* vive sulla sistemazione. Questa
funzione condivide: due rimborsi nello stesso giorno riuserebbero la stessa testata.

---

### Due specie di rifiuto

* I dati che un **operatore** sceglie in un form — il centro di riscossione e la data
  contabile — hanno un codice di dominio, `E_CONTABILE_DATI_OBBLIGATORI`, e la frase non
  nomina un parametro.
* Tutto il resto difende un'**invariante della chiamata**: un id non positivo, uno stato
  vuoto, un'origine fuori vocabolario, un emittente che non è un emittente fiscale, un lotto
  invisibile. Nessuna interfaccia li produce: li produce solo un chiamante rotto, e il codice
  è tecnico.

---

### Codici errore

* `E_CONTABILE_DATI_OBBLIGATORI` — manca il centro di riscossione (o non è positivo), o
  manca la data contabile.
* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` — canale, lotto o emittente non positivi; stato vuoto;
  origine fuori vocabolario; emittente che non è un emittente fiscale; lotto inesistente o
  fuori perimetro.
* `E_CONTABILE_STATO_NON_CONFIGURATO` — lo stato chiesto non è a catalogo o è spento.
* i codici della sede unica dell'emittente (`E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE`,
  `E_CONTABILE_EMITTENTE_OBBLIGATORIO`, `E_CONFIG_MANCANTE`).

---

### Test

* `db/pgtap/pagamenti/test-contabili-origine-e-quadratura.sql` — due operatori aprono due
  distinte manuali, non una.
* `db/pgtap/pagamenti/test-distinta-numerazione-registro-v1.sql` — l'emittente per livelli, e
  il presidio che le madri non passano `codice`.

---

### Note di migrazione

* 2026-08-21 — i rifiuti generici passano ai codici registrati. Lo stesso giorno
  arriva l'origine, e la distinta manuale diventa per operatore.
* 2026-08-22 — sparisce il parametro della compensazione, e con lui il ramo
  di riuso «una testata per atto» e la mutua esclusione col lotto.
* 2026-09-15 — la distinta sa di chi è.
  Nuovo parametro in coda per l'emittente, derivazione dal lotto, emittente nella chiave di
  riuso; il codice smette di venire dal default di colonna. La funzione a otto parametri è
  stata eliminata e ricreata: una sostituzione con parametri diversi affianca un overload, e
  coi default le chiamate diventano ambigue.

---

{% include-markdown "signature-core.md" %}
