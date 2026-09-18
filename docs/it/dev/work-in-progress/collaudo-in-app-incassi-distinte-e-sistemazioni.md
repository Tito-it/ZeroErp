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
> **Stato**: primo giro eseguito il 2026-09-14 (tre rilievi → D16/D17/D18);
> 🔴 **il secondo giro è C-2** (riquadro qui sotto): il brief che ne è nato è
> **chiuso e archiviato** il 15/09 — la prova a video è l'unica cosa che ne è
> uscita, e vive qui, con le sezioni 2, 3 e 4 riscritte per farla.
> **Ambiente**: sviluppo (`dbdev`).
> **Utente**: un **operatore**, non il super admin — ⚠️ il perimetro emittente
> è metà di ciò che si sta provando, e il super admin lo vede tutto.

---

> ## 🔴 C-2 — Il secondo giro, per D16 · D17 · D18
>
> **Da dove viene.** Il primo giro (14/09) ha trovato tre cose che
> l'interfaccia diceva al contrario del modello; le decisioni e il lavoro DB,
> BE e FE sono in
> [brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md](../work-done/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md) —
> **chiuso il 15/09** con tutto mergiato e verde in CI. Il brief chiude sul
> *percorso*; **l'esito lo prova solo questo giro**, ed è per questo che C-2
> sta qui e non lì: un copione si tiene aperto accanto all'app, un brief
> chiuso no.
>
> **Che cosa deve dire il secondo giro**, punto per punto (le righe sono già
> nelle sezioni; qui l'elenco di quelle che C-2 spunta):
>
> | Punto | Prova | Decisione |
> | --- | --- | --- |
> | **§2.6 · 2.6-bis** | la riga nasce **cercando la fattura**, con l'importo **proposto** dal residuo, e compare già `ABBINATA` — nessun «Abbina» dopo | D16 |
> | **§2.6-ter** | «Non riesco ad associarlo» è un gesto: la riga nasce `DA_ABBINARE` e compare in **Da abbinare**; senza l'interruttore e senza fattura, Salva è spento | D16 |
> | **§2.8 · 2.8-bis** | **Elimina** in bozza: la riga sparisce e la quadratura **torna**; il cestino è solo su «Elimina», «Porta a SCARTATA» ha un'altra icona | D17 |
> | **§2.9 · 2.9-bis** | sotto **VALIDATA** il contenuto è fermo (niente «Nuova riga», form chiuso, cestino **spento col motivo**), abbina e «Porta a …» restano; **Porta a BOZZA** riapre tutto. ⚠️ La riga di stato della barra compare **solo dopo l'apply di P-8** (prerequisito qui sotto) | D18 · FE-9 |
> | **§3.1 – 3.3-bis** | ri-abbinamento (`ABBINATA → DA_ABBINARE → abbina`); il kebab **non** offre SCARTATA su una `ABBINATA` (le voci vengono dalla matrice); la coda recupera l'eccezione col verbo `abbina` | D16 · BE-5 |
> | **§3.4 – 3.5** | il doppio tempo della capienza vale anche **alla nascita** e in **modifica** (PATCH di `importo`, Q-H): domanda col messaggio del DB, poi «Forza» col motivo | BE-2 · Q-H |
> | **§4.0** | **Porta a VALIDATA** prima di «Registra»: con un dichiarato sbagliato si ferma **qui** (`E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA`), non alla registrazione | §3 del brief |
> | **§4.4** | dopo la registrazione il cestino di ogni riga è **spento** col motivo «chiusa» | D17, motivo 1 |
>
> **Con chi**: un operatore **dentro** il perimetro per il giro intero, e uno
> **fuori** per la lista (§1.6 vale anche qui). **Se un punto non succede**: la
> colonna «Se non succede» della sezione dice se è un difetto di modello (si
> ferma e si segnala) o di resa; il *perché* di ogni riga è nel brief
> archiviato, non va ricostruito.
>
> **Come si chiude**: una riga nel registro (§8) con la data, i punti passati
> e i rilievi — e i rilievi, se ci sono, aprono un brief nuovo, non riaprono
> quello chiuso.

---

## ⛔ Tre cose da fare PRIMA di cominciare

| | Cosa | Perché blocca |
| --- | --- | --- |
| **P-0** | 🔴 **Assegnare l'azione `registra_distinta` a un profilo.** Misurato il 29/08: è a catalogo (`pericolosa = true`, `attivo = true`) con **zero profili abilitati** | Finché è così, **registra solo il super admin** — e col super admin non si prova il perimetro. È fail-closed, cioè il verso giusto in cui sbagliare, ma va aperto per collaudare |
| **Dato** | Nessun **canale di incasso** esiste (`enti_incasso` = 0 righe) | Non è un prerequisito: è la **prima prova** del copione, si crea da schermata |
| **Contesto** | Entrare come operatore di **un** emittente, e sapere quale | Metà delle prove chiede «e l'altro emittente cosa vede?» |
| 🆕 **P-8** | `make db-migrate` con il seed `meta.nessuna_azione_key` di `vendite_contabili_stati.csv` in albero (scritto il 15/09, [brief §4 P-8](../work-done/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md)) | Non blocca il giro: senza, la **riga di stato** della barra (§2.9, §4.4) è muta e sembrerebbe un difetto del drawer. È un prerequisito di lettura, non di modello |

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
| **1.6-bis** | Sempre come operatore dell'**altro** emittente, apri **Distinte** | ⛔ **Non vedi** la distinta su CASSA aperta dal primo (fino al 17/09 la vedevi: era «di tutti») | È la prova di D3 del [brief distinta-numerata-sul-registro](../work-done/brief-db-distinta-numerata-sul-registro.md): la RLS passa dalla colonna emittente. Se la vede, si ferma tutto e si segnala |

---

## 2. La distinta e le sue righe

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2.1** | **Incassi → Distinte** → «Apri distinta» | Un **form**, non un pulsante che crea al volo | — |
| **2.2** | Scegli il canale creato | ⭐ Il **centro si compila da solo** e si blocca, con la frase che dice perché | Se resta libero si può costruire la coppia incoerente che il database rifiuta |
| **2.3** | ⚠️ **Togli il canale** e guarda la tendina dei **centri** | 🔴 **Che cosa offre?** Il modello marca due centri come **interni** (`Fondi Fattura`, `Compensazione`): sono la macchina delle sistemazioni, non un posto dove digitare incassi a mano | ⛔ Se li offre è un difetto della **famiglia BE-8**, con un'aggravante: qui il database **non rifiuta**. Vedi §7 |
| **2.4** | Apri la distinta con **importo dichiarato 400,00** | Si apre il drawer. Quadratura: dichiarato 400, digitato 0, **scarto −400** | — |
| **2.4-bis** ✅ | Guarda il **codice** della distinta appena aperta | `DIS-<sigla del tuo emittente>-2026-0000001`; la seconda della giornata (altro canale) finisce in `…0000002`. ✅ **Provato da Tid il 2026-09-17: `DIS-PGTAPEF202-2026-0000001`, il primo numero emesso** | Un `VC_…` dice che il trigger non è montato; un codice senza sigla dice che il registro non ha la forma |
| **2.4-ter** | Togli il canale e apri su **CASSA**, come **operatore** | Il campo **Emittente** compare **già compilato** col tuo, non modificabile, con la frase che dice da dove viene | Se resta vuoto e «Apri» passa, il livello 3 (`fn_get_emittente_distinta`) non ha risolto |
| **2.4-quater** | Stessa cosa come **super admin in «Tutti gli emittenti»** | Il campo mostra l'avviso *«scegline uno dalla barra in alto»* e **«Apri» è spento**; scelto l'emittente in alto, la finestra si comporta come 2.4-ter | ⛔ Non c'è una tendina nel form: l'emittente si sceglie una volta dalla topbar (decisione del 02/09, confermata il 17/09). Se «Apri» passa senza emittente, il rifiuto D4-4 non è arrivato |
| **2.5** | Ripremi «Apri distinta» con **gli stessi dati** | ⭐ Non nasce una seconda distinta: **ridà quella di prima**, e lo **dice** | Entrare in silenzio dentro il lavoro di stamattina è il modo in cui si registra due volte credendo di cominciare |
| **2.6** | «Nuova riga» → **cerca la fattura 103** (numero o ragione sociale, dai 3 caratteri) → scegli la **rata** | ⭐ Il form parte dal **documento**, non dall'importo. Scelta la rata, l'importo si **propone da solo** = residuo della rata (**400,00**); senza rata, il residuo del documento. Sotto la tendina una frase dice che la rata è **facoltativa** | Se l'importo non si propone, la riga nasce dalla memoria dell'operatore invece che dal documento (D16) |
| **2.6-bis** | Digita un riferimento e salva | Compare in elenco già **ABBINATA**, con fattura e cliente. ⛔ **Nessun passo «Abbina» dopo**: la riga è nata giusta | Se nasce `DA_ABBINARE`, il default del form ha scelto il flusso dell'import per chi ha il nome sotto gli occhi |
| **2.6-ter** | «Nuova riga» → accendi **«Non riesco ad associarlo»** → importo **50,00** → salva | La ricerca fattura e la rata **si spengono**; la riga nasce **DA_ABBINARE** e in **Incassi → Da abbinare** compare | ⭐ L'eccezione si **dichiara** con un gesto: senza l'interruttore il pulsante Salva deve restare **spento** finché non c'è una fattura |
| **2.7** | Guarda la quadratura | Dichiarato 400, digitato 450: **scarto +50** e il segno «non quadra» | Con `importo dichiarato` vuoto deve dire «non si applica»: ⛔ **tre esiti, non due** |
| 🆕 **2.8** | Azioni della riga da 50,00 → **Elimina** (il cestino) → conferma | ⭐ La riga **sparisce** e la quadratura **torna** (scarto 0, «quadra»). Il messaggio di conferma nomina importo e riferimento | ⛔ Se l'unica via è «Porta a SCARTATA»: scartare **conta nella quadratura** (D12-e) e un errore di battitura resterebbe nel totale |
| 🆕 **2.8-bis** | Guarda le icone del kebab della riga rimasta | Il **cestino** è solo su «Elimina»; «Porta a SCARTATA» ha un'altra icona (⊘) | Un'icona con due sensi è il difetto del primo giro: il cestino su «scarta» ha fatto leggere uno stato come un'eliminazione |
| 🆕 **2.9** | Barra azioni → **Porta a VALIDATA** | La barra dice in una riga **dove sei** («validata: pronta da registrare, il denaro non è ancora registrato»). Sopra le righe compare «il contenuto è fermo»; «Nuova riga» **sparisce**, il click sulla riga **non apre** il form, il cestino è **spento col motivo** («riportala in bozza…»). ⭐ **Abbina** e «Porta a …» restano accesi | ⚠️ La riga di stato compare solo dopo l'apply del seed P-8 ([brief §4](../work-done/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md), prerequisito in testa): se la barra è muta, è quello — non un difetto del drawer |
| 🆕 **2.9-bis** | **Porta a BOZZA** | Tutto si riapre: «Nuova riga», il form, il cestino | — |

---

## 2-bis. La distinta cerca le rate — il picker e le righe da rate

> Copione ereditato il **2026-09-18** dalla chiusura di
> [brief-db-distinta-ricerca-rate.md](../work-done/brief-db-distinta-ricerca-rate.md)
> (§7). Il picker **singolo** Tid l'ha esercitato lo stesso giorno (quattro
> rilievi: altezza del dialog, dieci righe, bozze fuori, doppio bordo — tutti
> chiusi): le righe 2-bis.1 → 2-bis.4 sono un ripasso. Da confermare a video
> sono la **nota di credito nel picker** (2-bis.5) e le **righe da rate** in
> modalità multipla col secondo tempo **per riga** (2-bis.6 → 2-bis.13).
> ⭐ La regola che si sta guardando: *un incasso che copre tre rate resta tre
> righe; ogni riga è un atto suo, e il foglio è in bozza.*

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **2-bis.1** | Distinta manuale in BOZZA → «Nuova riga» → la **lente** accanto al lookup fattura | Il picker si apre **vuoto** con la frase «Indica il cliente o il numero…»; **nessuna chiamata parte** | Una lista che parte piena sta guardando lo scadenzario, non registrando il pagamento di *questo* cliente |
| **2-bis.2** | Numero fattura `101` | Compare **solo** la 101 (non la 1010): colonne Documento con il Tag natura, Rata, Scadenza, Residuo, In lavorazione, Incassato — dieci righe per pagina, altezza del dialog uguale vuoto o pieno | Nel picker il numero è un confronto **esatto**; `ILIKE` è la forma del lookup |
| **2-bis.3** | Click su una rata **esaurita** (residuo = in lavorazione) | Tag «esaurita» in colonna, toast informativo, il picker **resta aperto** | — |
| **2-bis.4** | Click su una rata aperta | Il picker si chiude; fattura e rata compilate nel form; importo proposto = **spazio** (residuo − in lavorazione); la tendina delle rate mostra la stessa rata scelta | Se propone il residuo intero su una rata già dichiarata in un'altra bozza, il DB la rifiuta al Salva |
| **2-bis.5** | Stessa cosa su una **nota di credito** (dal 17-09 ha **una** rata) | Natura in Tag, residuo scritto «**da rimborsare**» (non «di troppo»), la rata **si sceglie**, importo proposto **negativo** | Una NC nascosta dall'elenco è il buco che P-5 ha chiuso: si **segnala**, non si esclude |
| **2-bis.6** | Toolbar righe → «**Righe da rate**» | Dialog con le caselle di selezione, area «Rate scelte» vuota sotto, data pagamento = oggi | L'azione c'è solo in BOZZA e con permesso di scrittura (2-bis.14) |
| **2-bis.7** | Cliente con più fatture: spunta 2 rate a pagina 1, cambia pagina, spunta 1 rata, torna indietro | Le prime due restano spuntate; l'area elenca **tre** righe con importo = spazio; il pulsante dice «Crea 3 righe» | — |
| **2-bis.8** | Svuota un importo | Il pulsante si **spegne**; ricompilalo e si riaccende | — |
| **2-bis.9** | Cestino su una riga dell'area | Sparisce dall'area **e** si stacca la casella nella lista | — |
| **2-bis.10** | Salva (tre rate buone) | Toast «3 righe create», dialog chiuso, **tre righe** nel foglio con documento e rata, contatori del drawer aggiornati | — |
| **2-bis.11** | «Righe da rate» di nuovo: una rata aperta con importo = spazio **+ 1**, più una buona | Toast di avviso «1 righe su 2 create», il dialog **resta aperto**: la buona è sparita dall'area, la fuori capienza resta con la **frase del database** (con i numeri a due decimali: «restano 0.00…») e il toggle «Forza comunque» | È l'esito **PARZIALE per riga**: una riga rifiutata non porta via le altre |
| **2-bis.12** | Accendi «Forza comunque», scrivi il motivo, Salva | Toast «1 riga creata», dialog chiuso, nel foglio la riga con `forzata` e il motivo; la lista **ricarica** (le rate scritte hanno un altro spazio) | Il secondo tempo è **per riga**: conferma e motivo nella macchina, non nel dialog |
| **2-bis.13** | Spunta una rata, poi **X** del dialog | Conferma «Rate non salvate… chiudere e perderle?»; su «Chiudi» il dialog si chiude e, riaprendo, l'area è vuota | — |
| **2-bis.14** | Distinta **non** in BOZZA (o senza permesso di scrittura) | L'azione «Righe da rate» **non c'è**; il picker dal form non c'è (il form stesso non c'è) | — |

---

## 3. L'abbinamento, e il doppio tempo della capienza

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| **3.1** | Sulla riga **ABBINATA** del §2.6: kebab → **Porta a DA_ABBINARE** | ⭐ È il **ri-abbinamento**: l'unico modo di sganciare un abbinamento sbagliato. La riga torna `DA_ABBINARE`, fattura e rata restano scritte ma non contano. ⚠️ Il kebab **non** offre «Porta a SCARTATA» su una riga ABBINATA: le voci vengono dalla **matrice**, non dal vocabolario | Se offre SCARTATA e il DB rifiuta, il vocabolario è tornato al posto della matrice (§12) |
| **3.2** | Azioni della riga → **Abbina** → cerca la fattura **103** → guarda la tendina delle **rate** | ⚠️ Sotto i **3 caratteri** non cerca; le voci mostrano **numero e cliente**. Ogni rata porta il **saldo**, e una frase dice che la rata è **facoltativa** — è la **stessa tendina** del form di creazione (`RataSelect`) | Un elenco di rate senza saldo non risponde alla domanda per cui lo si apre |
| **3.3** | Scegli la rata e conferma | La riga torna ad **ABBINATA** | — |
| **3.3-bis** | **Incassi → Da abbinare**: apri la riga da 50,00 del §2.6-ter e abbinala alla fattura 103, rata 1 | ⭐ L'**eccezione** si recupera dalla coda col verbo `abbina`, senza altre porte | — |
| **3.4** | 🔴 **Il doppio tempo.** Aggiungi una **seconda** riga da 400,00 e abbinala **alla stessa rata** | ⛔ **Non deve passare al primo colpo.** Deve comparire una **domanda** — non un errore rosso — col **messaggio del database e i numeri**, e un campo **motivo** | Se passa liscia, la forzatura è stata scritta senza che nessuno l'abbia chiesta: è il difetto peggiore del cantiere |
| **3.5** | Scrivi il motivo e conferma | Ora passa. ⭐ Il motivo **resta scritto** | — |
| **3.6** | **Incassi → Rate fuori capienza** | La rata compare, con **motivo** in prima colonna e il tuo testo | Se non compare, l'elenco che rende onesta la forzatura non funziona |
| **3.7** | Su un'altra riga, **annulla** invece di confermare | La domanda si chiude e **non resta appesa** alla riga successiva | — |

---

## 4. La registrazione — l'unico gesto irreversibile

| | Cosa fare | Cosa deve succedere | Se non succede |
| --- | --- | --- | --- |
| 🔴 **4.0** | Con la distinta in **BOZZA** e un **totale dichiarato sbagliato** (es. 400 con righe per 450): barra → **Porta a VALIDATA** | ⛔ Si ferma **QUI**, non alla registrazione: `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA`, con i due numeri. Correggi il dichiarato (o le righe) e riprova: passa a **VALIDATA** | ⚠️ Validare ≠ registrare: la validazione è «ho finito, quadra»; il denaro si registra al passo 4.3. Il primo giro saltava questo passo e 4.1 falliva per costruzione (`E_CONTABILE_NON_REGISTRABILE`) |
| **4.1** | Sul drawer (in **VALIDATA**) → **Registra** | ⭐ Prima **l'anteprima**: righe registrabili, totale, e **chi resta indietro e perché** | Senza l'elenco di chi resta fuori, una registrazione parziale è indistinguibile da una totale |
| **4.2** | Leggi l'avviso | Dice che **non si torna indietro**, e lo dice **prima** | — |
| **4.3** | Conferma | ⭐ Il messaggio porta i **numeri**: «registrata: N righe per X €» | ⛔ Un «fatto» senza numeri non dice se erano due righe o venti. *(Corretto il 29/08: questa prova verifica la correzione)* |
| **4.4** | Guarda il drawer | Stato **CHIUSA**, «Registra» **sparisce**, compare **«Correggi»**; la riga di stato dice «registrata» e il cestino di ogni riga è **spento** col motivo «chiusa» | ⛔ Nessun pulsante «chiudi» da nessuna parte: la chiusura è una conseguenza |
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
| **2026-09-18** | 📥 **§2-bis nuova, dal brief [distinta-ricerca-rate](../work-done/brief-db-distinta-ricerca-rate.md)** (chiuso oggi, §7 del brief): quattordici righe — il picker singolo (2-bis.1 → .4, esercitato da Tid il 18-09 coi quattro rilievi chiusi), la **nota di credito nel picker** (2-bis.5: una rata, «da rimborsare», importo negativo) e le **righe da rate** in modalità multipla (2-bis.6 → .13: tre rate → tre righe, esito PARZIALE per riga, «Forza» per riga, conferma sull'abbandono). Da confermare a video: 2-bis.5 e 2-bis.6 → .13 |
| **2026-09-17** | 📥 **Quattro righe dal brief [distinta-numerata-sul-registro](../work-done/brief-db-distinta-numerata-sul-registro.md)** (chiuso oggi): §2.4-bis ✅ **provata da Tid** — `DIS-PGTAPEF202-2026-0000001`, il primo numero emesso da un registro `DISTINTA`; §2.4-ter, §2.4-quater e §1.6-bis **da provare**. ⚠️ §2.4-quater è scritta sul modello in vigore (campo in sola lettura, «Apri» spento in «Tutti»), non su quello che il brief immaginava il 15/09 (una tendina) |
| **2026-09-15** | 📥 **C-2 riceve casa qui.** Il brief nato dal primo giro è **chiuso e archiviato** ([work-done](../work-done/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md)): DB `20260914-04/05/06` applicati e verdi in CI, BE/FE mergiati (PR #1589), Q-H decisa (strada A: il doppio tempo anche in modifica). L'unica cosa che ne esce è la **prova a video**, cioè questo secondo giro: riquadro «C-2» in testa con l'elenco dei punti da spuntare. Prerequisito nuovo: l'apply del seed P-8 (riga di stato della barra) |
| **2026-09-14** (sera) | ✏️ **Sezioni 2, 3 e 4 riscritte** per D16/D17/D18 (brief DB §7): §2.6 la riga nasce **cercando la fattura**, con l'importo **proposto**; §2.6-ter l'eccezione dichiarata; 🆕 §2.8 **elimina** in bozza e la quadratura che torna; 🆕 §2.9 il contenuto **fermo** sotto VALIDATA e la riga di stato; §3.1–3.3 diventano la prova del **ri-abbinamento** e del recupero dalla coda; 🆕 §4.0 **Porta a VALIDATA** prima di «Registra», con lo stop sul dichiarato sbagliato. Da rieseguire |
| **2026-09-14** | 🔴 **Primo giro eseguito da Tid (prima contabile): tre rilievi, e il copione va riscritto** — vedi [brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md](../work-done/brief-db-riga-manuale-nasce-abbinata-ed-elimina-riga.md) §7. In sintesi: **§2.6** la riga deve nascere **cercando la fattura** (D16), non `DA_ABBINARE`; **§3.1-3.3** diventano la prova del ri-abbinamento e dell'eccezione «non identificato»; manca una prova **elimina riga in bozza** (D17); e ⛔ **fra §2.7 e §4.1 manca «Porta a VALIDATA»**: `fn_posta_contabile` registra **solo da `VALIDATA`** (`E_CONTABILE_NON_REGISTRABILE`), quindi §4.1 così com'è fallisce per costruzione. La riscrittura è del piano BE/FE |
| **2026-08-29** | Stesura, dopo la chiusura di **C-1** e la costruzione della base dei saldi (**A-8**). ⛔ Il cantiere non ha più niente da costruire e **non è mai stato visto**: `pagamenti` ha zero righe. I dati del copione sono **misurati**, non inventati. Un punto è già noto prima di cominciare (§7) |
