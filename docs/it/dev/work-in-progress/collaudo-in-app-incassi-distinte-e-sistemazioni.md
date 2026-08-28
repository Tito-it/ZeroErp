# Collaudo in-app · Il giro degli incassi: distinte, abbinamento, registrazione, sistemazioni

> **Cos'è.** Il copione della validazione a video: si tiene aperto accanto
> all'applicazione e si spunta. Non è il brief — il *perché* di ogni scelta sta
> in [brief-be-fe-posting-e-abbinamento-rata.md](brief-be-fe-posting-e-abbinamento-rata.md);
> qui c'è solo **cosa fare, cosa deve succedere, e cosa fare se non succede**.
>
> **Perché esiste, ed è la ragione più forte di tutto il cantiere.** Il codice è
> scritto, i presidi sono verdi (**4166 test**), l'SQL è provato con `EXPLAIN`
> sul database vero — ma ⛔ **`pagamenti` ha ZERO righe**. Nessuno ha mai aperto
> una distinta, digitato una riga, abbinato un incasso, registrato niente. Di
> questo dominio è stato provato **il percorso**, mai **l'esito**.
>
> ⭐ **E il cantiere gemello ha appena mostrato quanto costa saltarlo**: il
> collaudo di «riporta da emettere» ha trovato **quattro difetti che nessun test
> aveva visto**, e **tre su quattro erano difetti di ciò che il programma DICE**
> — un nome ambiguo, una promessa invecchiata, un'istruzione non eseguibile.
> Nessuno dei 4166 test poteva vederli: si vedono solo guardando la schermata.
>
> **Stato**: da eseguire. **Ambiente**: sviluppo (`dbdev`).
> **Utente**: un **operatore**, non il super admin — ⚠️ il perimetro emittente
> è metà di ciò che si sta provando, e il super admin lo vede tutto.

---

## ⛔ Tre cose da fare PRIMA di cominciare

| | Cosa | Perché blocca |
| --- | --- | --- |
| **P-0** | 🔴 **Assegnare l'azione `registra_distinta` a un profilo.** Misurato il 29/08: è a catalogo (`pericolosa = true`, `attivo = true`) con **zero profili abilitati** | Finché è così, **registra solo il super admin** — e col super admin non si prova il perimetro. È fail-closed, cioè il verso giusto in cui sbagliare, ma va aperto per collaudare |
| **Dato** | Nessun **canale di incasso** esiste (`enti_incasso` = 0 righe) | Non è un prerequisito: è la **prima prova** del copione, si crea da schermata |
| **Contesto** | Entrare come operatore di **un** emittente, e sapere quale | Metà delle prove chiede «e l'altro emittente cosa vede?» |

⚠️ **I dati di prova sono finti, il perimetro è vero.** I due IBAN
`IT00TESTINCASSO000000000{1,2}` sono fittizi, ma sono censiti **a livello di
ruolo** su due emittenti diversi: uno scambio non darebbe errore, darebbe liste
sbagliate. Per questo si guarda, non si assume.

**Materiale già in casa** (misurato il 2026-08-29):

| Cosa | Valore |
| --- | --- |
| Conto di incasso dell'emittente 32 | `IT00TESTINCASSO0000000001`, predefinito |
| Centri di riscossione | `BANCA`, `POSTE`, `CASSA` + ⚠️ due **interni**: `Fondi Fattura`, `Compensazione` |
| Fatture con una rata aperta | **n. 103** (400,00) · **n. 102** (400,00) · **n. 101** (497,76) |

---

## 1. Il canale di incasso

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **1.1** | Menu **Incassi → Canali di incasso** | Elenco vuoto, con la frase che lo **spiega** — non una tabella muta | Un vuoto senza spiegazione sembra un guasto |
| **1.2** | «Nuovo canale» → tipo **BANCA** | Compare il campo **Filiale**, e la frase dice che è obbligatoria solo su BANCA | — |
| **1.3** | Cambia tipo in **ALTRO** | La filiale **sparisce** | Se resta, al salvataggio il database la rifiuta parlando di un campo che non si vede più |
| **1.4** | Guarda la tendina **Conto di incasso** | ⭐ Ogni riga porta **IBAN · utility · predefinito**. Se il conto non ha utility si legge **«nessuna utility»**, non una cella vuota | Una cella vuota si legge come «dato mancante»: sono due cose diverse |
| **1.5** | Salva un canale su `IT00TESTINCASSO0000000001`, tipo `ALTRO`, centro `BANCA` | Creato, e in elenco compare con la **utility del conto** in colonna | — |
| **1.6** | 🔴 **La prova del perimetro.** Esci, entra come operatore dell'**altro** emittente, apri i canali | ⛔ **Non deve vedere il canale appena creato.** La policy RLS è nata il 28/08 apposta | Se lo vede, il perimetro non morde: è un difetto di **modello**, si ferma tutto e si segnala |

---

## 2. La distinta e le sue righe

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | **Incassi → Distinte** → «Apri distinta» | Un **form**, non un pulsante che crea al volo | — |
| **2.2** | Scegli il canale creato | ⭐ Il **centro si compila da solo** e si blocca, con la frase che dice perché | Se resta libero si può costruire la coppia incoerente che il database rifiuta |
| **2.3** | ⚠️ **Togli il canale** e guarda la tendina dei **centri** | 🔴 **Che cosa offre?** Il modello marca due centri come **interni** (`Fondi Fattura`, `Compensazione`): sono la macchina delle sistemazioni, non un posto dove digitare incassi a mano | ⛔ Se li offre è un difetto della **famiglia BE-8**, con un'aggravante: qui il database **non rifiuta**. Vedi §7 |
| **2.4** | Apri la distinta con **importo dichiarato 400,00** | Si apre il drawer. Quadratura: dichiarato 400, digitato 0, **scarto −400** | — |
| **2.5** | Ripremi «Apri distinta» con **gli stessi dati** | ⭐ Non nasce una seconda distinta: **ridà quella di prima**, e lo **dice** | Entrare in silenzio dentro il lavoro di stamattina è il modo in cui si registra due volte credendo di cominciare |
| **2.6** | Aggiungi una riga da **400,00**, data di oggi, con un riferimento | Compare in elenco, stato **DA_ABBINARE** | — |
| **2.7** | Guarda la quadratura | **Scarto 0** e il segno «quadra» | Con `importo dichiarato` vuoto deve dire «non si applica»: ⛔ **tre esiti, non due** |

---

## 3. L'abbinamento, e il doppio tempo della capienza

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | Azioni della riga → **Abbina** → cerca la fattura **103** | ⚠️ Sotto i **3 caratteri** non cerca. Le voci mostrano **numero e cliente** | — |
| **3.2** | Guarda la tendina delle **rate** | Ogni rata porta il **saldo**. E una frase dice che la rata è **facoltativa** | Un elenco di rate senza saldo non risponde alla domanda per cui lo si apre |
| **3.3** | Scegli la rata e conferma | La riga passa ad **ABBINATA** | — |
| **3.4** | 🔴 **Il doppio tempo.** Aggiungi una **seconda** riga da 400,00 e abbinala **alla stessa rata** | ⛔ **Non deve passare al primo colpo.** Deve comparire una **domanda** — non un errore rosso — col **messaggio del database e i numeri**, e un campo **motivo** | Se passa liscia, la forzatura è stata scritta senza che nessuno l'abbia chiesta: è il difetto peggiore del cantiere |
| **3.5** | Scrivi il motivo e conferma | Ora passa. ⭐ Il motivo **resta scritto** | — |
| **3.6** | **Incassi → Rate fuori capienza** | La rata compare, con **motivo** in prima colonna e il tuo testo | Se non compare, l'elenco che rende onesta la forzatura non funziona |
| **3.7** | Su un'altra riga, **annulla** invece di confermare | La domanda si chiude e **non resta appesa** alla riga successiva | — |

---

## 4. La registrazione — l'unico gesto irreversibile

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **4.1** | Sul drawer → **Registra** | ⭐ Prima **l'anteprima**: righe registrabili, totale, e **chi resta indietro e perché** | Senza l'elenco di chi resta fuori, una registrazione parziale è indistinguibile da una totale |
| **4.2** | Leggi l'avviso | Dice che **non si torna indietro**, e lo dice **prima** | — |
| **4.3** | Conferma | ⭐ Il messaggio porta i **numeri**: «registrata: N righe per X €» | ⛔ Un «fatto» senza numeri non dice se erano due righe o venti. *(Corretto il 29/08: questa prova verifica la correzione)* |
| **4.4** | Guarda il drawer | Stato **CHIUSA**, «Registra» **sparisce**, compare **«Correggi»** | ⛔ Nessun pulsante «chiudi» da nessuna parte: la chiusura è una conseguenza |
| **4.5** | Apri il **drawer della fattura 103** | ⭐ In cima il **residuo**, aggiornato. «In lavorazione» **non** deve comparire se è zero | A zero ruba spazio al numero che conta |

---

## 5. La correzione guidata

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **5.1** | Sulla distinta **CHIUSA** → **Correggi** | Un form: data e motivo, e la frase che dice che nasce una **bozza** e il denaro **non si muove** | «Correggi» che sembra sistemare tutto da sé è una promessa non mantenuta |
| **5.2** | Conferma | Il drawer **si sposta sulla distinta nuova**. Il messaggio dice **quante righe** rovesciate e **quante saltate** | — |
| **5.3** | Guarda le righe | Importi di **segno opposto**, con **fattura e rata già scritte**, stato **DA_ABBINARE** | ⭐ È la decisione **C-1**: il legame si eredita, il tasto finale lo preme una persona |
| **5.4** | Guarda la testata | ⭐ Dice **«questa distinta corregge la …»**, ed è **cliccabile** | Senza, due gemelli di segno opposto stanno in elenco senza niente che dica che uno rovescia l'altro |
| **5.5** | Torna sull'originale | Dice **«è già stata corretta dalla …»**, e «Correggi» è **spento col motivo** | — |
| **5.6** | Prova a correggere una distinta in **BOZZA** | Rifiutato, con la frase giusta: non ha prodotto movimenti | — |
| **5.7** | Abbina una riga **negativa** alla sua rata | ⭐ Deve comparire **la stessa domanda** di §3.4: su quella rata non c'è più spazio. È voluto | Se passa liscia, la capienza non guarda il segno |

---

## 6. Le eccedenze e le sistemazioni

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **6.1** | **Incassi → Eccedenze**, dopo aver forzato §3.4-3.5 e registrato | La fattura compare, con **chi è in credito** a colori e il totale **del cliente** accanto a quello del documento | ⛔ Sbagliare il verso significa rimborsare ciò che si deve incassare |
| **6.2** | Apri la riga | Drawer con gli **atti già decisi** (nessuno) e il form della decisione | «Non ha deciso nessuno» e «non l'ho letto» devono essere **due frasi diverse** |
| **6.3** | Destinazione **RIPORTO** | Compare il **documento di destinazione**, ristretto **allo stesso cliente** | — |
| **6.4** | Destinazione **RIMBORSO** | Il documento di destinazione **sparisce**: il denaro esce, non c'è un secondo documento | — |
| **6.5** | Registra un **RIMBORSO** parziale | Compare in elenco in **BOZZA**. ⚠️ L'eccedenza **resta**: una decisione non confermata non ha mosso niente | Se sparisce, l'elenco mente su denaro ancora fermo |
| **6.6** | Conferma → dialogo | ⭐ Chiede il **canale**, e lo chiede **solo** sul rimborso | — |
| **6.7** | Conferma | Il drawer **si chiude** e l'elenco si ricarica | ⭐ Voluto: i numeri in testata sono di prima del movimento |
| **6.8** | Riapri e prova a confermare l'atto già confermato | L'azione è **spenta col motivo**, non sparita | Una voce che sparisce non spiega niente |

---

## 7. 🔴 Il punto già noto, da confermare a video

⚠️ **§2.3 non è una domanda oziosa.** Misurato il 2026-08-29:
`pagamenti.centri_riscossione` marca due centri come interni
(`is_compensazione`, `is_fondo_fattura`), e quei due flag li leggono **le
funzioni delle sistemazioni e dei saldi** — cioè la macchina. Ma:

* ⛔ **nessun guard impedisce** di aprire una distinta manuale su quei centri;
* ⛔ la tendina passa dalla **lookup generica** (`pagamenti.centri_riscossione`),
  che restituisce tutti gli attivi e **non conosce quei flag**.

⇒ Oggi l'operatore può aprire una distinta di lavoro **sul centro delle
compensazioni**. Non è un errore che qualcuno noterebbe: è lavoro manuale che
finisce dentro il centro di una macchina automatica.

📮 **È della famiglia BE-8** («il database rifiuta, ma un elenco che lo propone
fa sbagliare») con un'aggravante: **qui il database non rifiuta**. La sede del
rimedio non è ovvia — un filtro sulla lookup generica, un endpoint dedicato, o i
due flag portati nel payload della lookup — e **non l'ho scelta da solo**.

---

## 8. Registro

| Data | Cosa |
| --- | --- |
| **2026-08-29** | Stesura, dopo la chiusura di **C-1** e la costruzione della base dei saldi (**A-8**). ⛔ Il cantiere non ha più niente da costruire e **non è mai stato visto**: `pagamenti` ha zero righe. I dati del copione sono **misurati**, non inventati. Un punto è già noto prima di cominciare (§7) |
