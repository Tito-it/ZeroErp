## 📘 Documentazione Concettuale – Tabella `vendite.registri_fatturazione`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
>
### 🎯 Scopo Principale
(latest review 26-01-2026)
`vendite.registri_fatturazione` definisce i **sezionali di numerazione**: serie,
regole di reset, politica della data e collegamento all'emittente fiscale. Ogni
documento numerato si aggancia a un registro, che ne governa numerazione e
perimetro.

⛔ **Il nome dice meno di quello che la tabella fa, ed è un debito dichiarato:**
dal 31 agosto 2026 qui non vivono più solo le fatture. Vedi la sezione in fondo.

---

### Campi chiave (semantica)

* **Identita`**: `id`, `uid`, `codice`.
* **Emittente**: `emittente_soggetto_ruolo_id` (ruolo fiscale che emette).
* **Utility**: `utility_id` (opzionale, per registri specifici di utility).
* **Numerazione**: `serie_default`, `reset_policy` (`ANNUALE` o `NESSUNA`).
* **Forma del numero**: `prefisso`, `suffisso`, `lunghezza_numero` — vedi la
  revisione «il registro dice anche CHE FORMA ha il numero».
* **Stato**: `attivo`.
* **Governance**: `meta`, `storicizza`, `tx_id`, audit.

---

### Relazioni principali

* `vendite.fatture.registro_id` → determina la numerazione.
* `vendite.registri_fatturazione_progressivi` mantiene i contatori per anno/serie.
* `vendite.tipi_doc_fiscale_registri` associa il registro al tipo documento fiscale.

---

### Nota sulla FK emittente

La FK su `emittente_soggetto_ruolo_id` e` **coerente** con un modello multi‑emittente:
ogni registro appartiene a un emittente fiscale specifico. In presenza di piu`
aziende abilitate, la separazione dei registri evita collisioni di numerazione.

---

### 🔄 rev 2026-08-25 — il registro dice anche CHE DATA porta il documento

Brief: `brief-db-numerazione-data-documento-e-sequenza` (**DB-3**, **DB-12**).

#### Nuova colonna `politica_data_documento`

| valore | data del documento |
| --- | --- |
| `OGGI` (default) | `script.fn_data_operativa()` — fattura immediata |
| `FINE_MESE_COMPETENZA` | ultimo giorno di `fatturazione_lotti.competenza_mese` — fattura differita |

⭐ **Perché sul registro e non sul lotto.** Il registro **è** il sezionale: è lì
che vive la sequenza, e la regola della data deve stare accanto alla regola del
numero — altrimenti si può configurare un registro la cui data litiga con la sua
numerazione.

E c'è un guadagno che una colonna sul lotto non darebbe: **un lotto può contenere
documenti di registri diversi** (la natura instrada la nota di credito su un
sezionale suo). Con la regola sul registro, ogni documento prende la data giusta
**da sé**.

⚠️ Una data valorizzata su `fatturazione_lotti.data_documento` **scavalca** questa
politica, per tutti i documenti di quel lotto.

⚠️ **`FINE_MESE_COMPETENZA` e il cancello di monotonia collidono per
costruzione**, e non è un difetto: è il comportamento normale della differita in
ritardo. Un lotto di competenza arretrata lavorato oggi prende la data di fine di
quel mese, che è anteriore all'ultimo numero emesso, e viene rifiutato —
l'operatore ridichiara la data dal dialog. 📌 Misurato il 2026-08-25: 4 lotti
hanno competenza giugno e fatture datate luglio/agosto, e uno di essi porta una
fattura **già numerata**. ⭐ Per questo la `minDate` esposta al frontend
([`fn_get_data_minima_numerabile_lotto`](/dbzero/vendite/funzioni/fn_get_data_minima_numerabile_lotto))
non è un abbellimento: è ciò che rende vivibile la politica.

#### ~~`reset_policy` scende a **una voce sola**~~ → 🔴 rev 2026-09-01: `NESSUNA` è tornata, e adesso FUNZIONA

> ~~Il `CHECK` ammette ora solo `ANNUALE`. Prima accettava anche `NESSUNA` e
> `MENSILE`, che erano **dichiarate e non implementate**: la chiave del contatore
> porta `mese = 0` fisso e `uq_fatture_numero` il mese non lo contiene, quindi
> `NESSUNA` si comportava come `ANNUALE` e `MENSILE` pure.~~
>
> ⛔ **Ma la frase che segue era giusta, ed è quella che conta** — vale ancora,
> parola per parola: *«un catalogo che promette tre comportamenti e ne fa uno è
> peggio di un catalogo con una voce sola»*.

⭐ **E quella nota conteneva già l'invariante, scritta il 2026-08-25 e non ancora
riconosciuta come regola generale:**

> *«se un giorno `MENSILE` servisse davvero non basta riaprire il `CHECK`: serve
> il mese **nel contatore** (c'è già) **e in `uq_fatture_numero`** (non c'è)»*

Quella è, in un caso particolare, la regola che il 2026-09-01 è stata scritta per
esteso nella [guida alla numerazione §8-bis](/guide/numerazione-documenti-e-codici):

> **Tutto ciò che discrimina il CONTATORE deve poter discriminare anche il
> DOCUMENTO.**

**Cosa è cambiato**, e sono tre cose:

| | |
| --- | --- |
| `MENSILE` | ⛔ **non torna**. Il mese non ce l'ha *nessun* documento nel proprio vincolo: accenderlo li farebbe collidere tutti e cinque |
| la colonna `mese` del contatore | 🔴 **tolta**. Stava in chiave e in nessun documento: una dimensione dormiente in una chiave è **armata**, non inutilizzata |
| `NESSUNA` | ✅ **riammessa, e letta**. `fn_get_next_progressivo` legge la politica: sotto `NESSUNA` l'anno del secchio vale `0`, cioè un secchio solo e numerazione **continua** fra gli anni |

⭐ **Perché una sì e l'altra no**, ed è l'asimmetria della regola: `MENSILE`
farebbe discriminare il contatore su un asse che il documento **non ha**
(collisione); `NESSUNA` gli fa usare **meno** assi, non di più — e l'anno ce
l'hanno tutti i documenti. Il verso innocuo.

⚠️ **E due cose si chiamano «anno»**: quello del **secchio**
(`progressivi.anno`, che vale `0` sotto `NESSUNA`) e quello del **documento**
(`fatture.anno`, `ddt.anno`, …), sempre solare. `fn_get_anno_registro` risponde
alla seconda domanda — per questo **non** ha ricevuto il registro come parametro,
contrariamente a quanto la nota vecchia prevedeva: la politica si legge dove
serve, cioè nell'unica funzione che legge `progressivi.anno`.

⚠️ **Il `serie_default` è portante, non un'etichetta.** È da lì che
`fn_assign_numero_fattura` risolve la serie di un documento che non ne dichiara
una (`COALESCE(f.serie, r.serie_default, '')`), quindi **rinominarlo sposta il
sezionale**: le righe di `registri_fatturazione_progressivi` restano sulla serie
vecchia e vanno spostate a mano, o il contatore riparte da zero e il cancello
resta senza pavimento.

---

### 🔄 rev 2026-08-31 — il registro numera **cinque famiglie**, non solo le fatture

Brief: `brief-db-registri-di-numerazione-emittente-e-trasloco` (**C2**).

#### La colonna `famiglia_documento`

Dice **che specie di documento** questo registro numera: `FATTURA`, `DDT`,
`ORDINE`, `COMMESSA`, `RESO` — le voci sono quelle di
[`vendite.famiglie_documento`](/dbzero/vendite/manual/famiglie_documento).

⭐ **Il motore era già neutro.** Documenti di trasporto, ordini, commesse e resi
avevano ciascuno il proprio contatore, e nessuno dei tre sapeva ripartire a
Capodanno né distinguere due aziende. Portarli qui non ha richiesto un motore
nuovo: nel generatore la fattura compariva ormai solo nel ramo dell'errore.

⚠️ **Un registro appartiene a UNA azienda**, e non è una preferenza: è la chiave
del contatore. Due aziende sullo stesso registro non producono numeri doppi — il
contatore è uno solo — ma **spezzano l'attribuzione**, e nessuna delle due ha più
una progressione propria. Nessun errore lo segnala: è il motivo per cui esiste un
controllo apposta e per cui l'emittente è obbligatorio dal 30 agosto 2026.

#### ⚠️ Il cancello della data vale **solo per le fatture**

Il pavimento di sequenza — *«non numeri un documento con data anteriore
all'ultimo già numerato»* — è una regola **fiscale** e vive dove c'è il registro
fiscale.

⛔ Acceso anche altrove sarebbe un rifiuto nuovo, non un modo diverso di dare il
numero: emesso un documento di trasporto datato oggi, su quel registro **nessuno
datato prima passerebbe più** — e il documento per la spedizione di ieri, inserito
stamattina, verrebbe respinto. Lo governa il flag `presidia_data_documento` sul
catalogo delle famiglie.

⭐ **L'anno invece resta quello della data del documento** per tutti, ed è
indipendente da quel flag.

#### ⛔ Un registro spento occupa ancora il suo posto

**«Spegni e rifai» non è una strada per un registro.** Per la stessa combinazione
di famiglia, azienda e utility non se ne ritira uno per crearne un altro: si
**riattiva quello che c'è**.

Il motivo è che l'unicità dei registri non guarda l'interruttore acceso/spento:
una riga spenta continua a occupare il posto. Chi prova a inserirne una nuova
accanto riceve un errore di duplicato che parla di una riga che non vede più — ed
è il genere di messaggio che fa perdere mezz'ora.

⭐ **Ed è giusto così, non è una svista.** Se spegnere liberasse il posto,
resterebbero due registri storici della stessa famiglia per la stessa azienda, e
nessuno saprebbe più **quale ha numerato cosa**. La numerazione è una storia che
non si riapre, e il vincolo è severo per quel motivo.

#### ⛔ E un registro che ha già numerato **non si spegne affatto**

*(corretto il 2026-08-31 sera — la frase che stava qui diceva il contrario)*

Questa scheda affermava che *«spegnere resta la mossa giusta quando serve solo a
togliere un registro dalla circolazione»*. **È falso**, e non per un vincolo
aggiunto di recente: per come è fatto il modello. Tre cose lo dicono insieme:

| | |
| --- | --- |
| lo slot `UNIQUE` resta occupato anche da spento | non se ne può creare uno sostitutivo |
| il lettore del registro pretende `attivo IS TRUE` | il documento non nasce più |
| il provisioning non crea dove una riga esiste già | nessun rimedio automatico |

⇒ Spegnere il registro DDT di un'azienda significa **quell'azienda non emette più
documenti di trasporto, e non c'è modo di tornare indietro.** Non è un ritiro: è
un blocco senza uscita.

⭐ **Per questo i guard di disattivazione sono la difesa giusta, non un
impedimento.** Al 2026-09-18 sono **otto** — commesse, documenti di trasporto,
fatture, ordini, progressivi, resi, mapping dei tipi documento e, dal 17-09, la
**distinta di incasso** (`pagamenti.vendite_contabili`, la prima figlia fuori
dallo schema `vendite`) — e li monta l'automazione da sé a partire dalle chiavi
esterne, senza annunciarlo: erano sei il 31-08 e sette il 02-09. Chi prova a
spegnere un registro usato riceve un rifiuto;
`script.fn_check_registro_disattivabile` lo anticipa, così l'interfaccia spegne
il cestino **e dice perché**, invece di far scoprire il vincolo premendo.
⚠️ Che la check non resti indietro rispetto ai guard lo presidia il pgTAP
`script/test-fn-check-registro-disattivabile-v1` (test 6), che confronta i
trigger montati con i motivi coperti: è diventato rosso da solo tutte e tre le
volte, ed è la ragione per cui l'elenco qui sopra ha una data.

⚠️ **Il bisogno vero che stava dietro «ritiro e rifaccio» era cambiare la forma
del numero**, e oggi si fa senza spegnere niente: `prefisso`, `suffisso` e
`lunghezza_numero` sono colonne di questo registro e si modificano. Ciò che
cambia da lì in avanti riguarda i documenti nuovi; quelli già numerati restano
com'erano, che è esattamente il comportamento voluto.

⚠️ **Resta vero il contrario di prima:** l'unico registro che si può spegnere è
quello che non ha mai numerato niente — cioè quello che nessuno ha bisogno di
ritirare. La possibilità esiste per correggere una configurazione appena creata
per sbaglio, non per gestire un ciclo di vita.

#### ⛔ Il debito sul nome, dichiarato

La tabella si chiama `registri_fatturazione` e numera anche merce in uscita e
ordini. **Il nome non si cambia**, e non per pigrizia: rinominarla significa
rinominare la tabella dei progressivi, i trigger, le funzioni, le viste, i vincoli
e le colonne `registro_id` delle tabelle di documento che la portano — sei al
2026-09-18, in due schemi (`vendite.*` e `pagamenti.vendite_contabili`).

⭐ È un lavoro che non cambia **nessun** comportamento — cioè esattamente quello
che non va infilato dentro un cantiere che ne cambia molti, dove un errore di
rinomina si confonderebbe con un errore di trasloco.

⚠️ **Ne discende una regola di lettura:** chi trova questo nome in giro non deve
dedurne «fattura». La specie si chiede a `famiglia_documento`, e la funzione che
risolve il registro di un documento **rifiuta** proprio la famiglia `FATTURA` —
quella ha una strada sua, che passa dal tipo di documento fiscale e dalla natura
dell'operazione.

---

### 🔄 rev 2026-08-31 (sera) — il registro dice anche **che forma** ha il numero

Brief: `brief-db-prefisso-sul-registro-e-allineamento-contatori` (**P-2**, **P-9**).

Fino a quel giorno il registro diceva **quanto**: chi conta, per quale azienda e
per quale anno. La forma della stringa — il prefisso, le cifre di riempimento —
stava altrove, in `config.sistema_codici`. Oggi sta qui:

| colonna | che cos'è |
| --- | --- |
| `prefisso` | ciò che precede il numero. Vuoto è legittimo, e vuol dire «nessun prefisso» |
| `suffisso` | ciò che lo segue. Nato insieme al prefisso, per non doverlo aggiungere dopo |
| `lunghezza_numero` | quante cifre ha la parte numerica. `NOT NULL`, default 7; la commessa ne usa 9 |

#### ⭐ Default e effettivo: due sedi, un ruolo ciascuna

```
famiglie_documento     →  il DEFAULT   (com'è fatto quel TIPO di documento)
registri_fatturazione  →  l'EFFETTIVO  (com'è fatto QUESTO sezionale)
```

Tutti i documenti di trasporto hanno 7 cifre: è una proprietà del tipo documento.
Un singolo sezionale può però volere un prefisso suo — è esattamente **a cosa
serve un sezionale** — e allora vale quello scritto qui.

⚠️ **Un registro nuovo nasce copiando il default della sua famiglia**, quindi
nessuno deve ricordarsi di riempirlo. Chi ne crea uno a mano e lascia il prefisso
vuoto ottiene numeri **nudi**, in silenzio: è il motivo per cui esiste un presidio
sul provisioning.

#### ⚠️ Il separatore non è più un campo a sé

Se serve, si scrive **dentro** il prefisso (`CMM-`). Con due campi distinti un
prefisso vuoto lasciava il separatore **orfano in testa** — `-ACME-2026-000000001`
— e chi spezzava il codice sul trattino trovava un primo pezzo vuoto.

#### ⛔ La coppia prefisso+suffisso è unica dentro l'emittente

Due registri della stessa azienda non possono avere la stessa coppia: sarebbero
due sezionali **indistinguibili a valle**, che è il contrario di ciò per cui
esistono. ⚠️ Il vincolo è **parziale**: due registri entrambi senza prefisso né
suffisso convivono, perché non hanno un nome da tenere distinto.

#### ⛔ I contatori sono stati allineati al massimo già emesso

Il giorno del trasloco i contatori partivano da zero mentre il pregresso era
arrivato per esempio a `ORD0040688`: il primo ordine nuovo ha ricevuto
`ORD0000001`, **un numero già usato**, con la stessa identica forma.

⚠️ E il vincolo di unicità non se n'è accorto: le righe vecchie hanno il registro
vuoto, le nuove no, e **un campo vuoto contro un campo pieno non collide mai**.

⭐ L'allineamento porta ogni contatore almeno al massimo progressivo già emesso
dalla stessa azienda in quell'anno. Lascia dei buchi nella progressione — un
contatore non torna indietro — ed è un prezzo molto più basso di un numero doppio.

⚠️ L'anno si ricava dalla **data del documento** e non dalla colonna `anno`: sul
pregresso di documenti di trasporto e resi quella colonna è vuota.

---

{% include-markdown "signature-core.md" %}
