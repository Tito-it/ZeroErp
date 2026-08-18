# Fase E + ricerca: tre richieste al team DB · *perimetro emittente*

> **Cos'è.** Quello che serve dal database per finire il giro **P-4** — la
> colonna emittente sulle **cinque liste** che restano — più il **residuo D-3**,
> l'emittente nella riga della ricerca universale.
>
> **Origine.** Misurato il **2026-08-18**, chiuse le fasi A→D del piano BE/FE
> ([brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md) §13-bis).
>
> **Destinatario**: team DB, branch `dev/db-tid`.
> **Autorizzazione**: Tid, 2026-08-18.
>
> ⛔ **La Fase E è ferma su queste richieste, tutta.** Non è una scelta di
> comodo: senza la riga di catalogo la colonna **non esiste** per il frontend, e
> senza la ragione sociale nella vista il backend non ha cosa selezionare. Il
> codice BE si scrive in mezz'ora quando i due pezzi ci sono; scritto prima
> sarebbe codice che seleziona una colonna inesistente.

| # | Cosa | Peso | Blocca | Stato |
| --- | --- | --- | --- | --- |
| **R-3** | **5 righe** in `lista_colonna.csv`: la colonna emittente sulle liste che restano | append al CSV | ⛔ tutta la Fase E | ✅ **fatto** |
| **R-4** | `emittente_ragione_sociale` nelle viste — ~~3~~ **5**, vedi sotto | ~~5~~ **6** `CREATE OR REPLACE VIEW` | ⛔ 4 liste su 5 | ✅ **fatto**, poi 🔴 **corretto** con `-74`: `-61` consegnava la colonna vuota su 274 righe su 274 |
| **R-5** | L'emittente nella riga della **ricerca universale** | 2 funzioni + 1 rifattorizzata | 🔵 niente — è il residuo D-3 | ✅ **fatto** |

---

## ✅ Consegnato dal team DB — 2026-08-18 · **applicato e verde**

> 🟢 **Stato finale.** ChangeSet `20260818-58`→`-67` **applicati** da Tid il
> 2026-08-18. Suite pgTAP: **nessuna regressione**; i due file nuovi (25
> asserzioni) verdi, e i tre file che presidiano la dismissione della legacy
> verdi dopo `-67`.
>
> ⛔ **Resta rossa una cosa sola, ed è voluta**: `test_liste_configurabili_seed`
> lato backend, finché non arriva **BE-E1** (sotto). È la finestra che questo
> stesso brief prevedeva.

> Le due domande aperte hanno risposta (in fondo a R-4 e a R-5). In breve:
> **R-4 → sì, per costruzione** (l'emittente è una colonna della commessa, non
> dell'attività: il `GROUP BY` è sicuro). **R-5 → A**, ma l'etichetta non può
> essere «Emittente»: su una riga-soggetto quella colonna mostra una
> **relazione**, non un attributo — *il soggetto non ha un emittente*.

### 🔴 Correzione del 2026-08-18 — `-61` consegnava una colonna VUOTA (changeSet `-74`)

> ⚠️ **Il paragrafo qui sotto sul backlog aveva ragione a metà, e la metà
> mancante è costata due liste.** Il ramo resi non era il *solo* posto in cui
> `emittente_soggetto_ruolo_id` è `NULL::bigint` scritto a mano.

Misurato contando le righe, non leggendo il codice:

| vista | righe | con il nome |
| --- | ---: | ---: |
| `vw_dash_fatturazione_documenti` (`-61`) | 274 | **0** |
| `vw_dash_aperto_documenti` (`-62`) | 156 | **0** |
| `vw_dash_backlog_documenti` (`-63`) | 95 | **95** ✅ |

**La causa.** `-61` risolve il nome da `emittente_soggetto_ruolo_id`, fidandosi
della frase che sta nel `COMMENT` della vista stessa — *«i sei resolver portano
tutti `emittente_soggetto_ruolo_id`»*. **Cinque dei sei la scrivono
`NULL::bigint`**: preventivi, ordini, offerte, contratti, DDT. L'unica che porta
il valore vero è `commesse`. `emittente_fiscale_id`, invece, è valorizzato su
274 righe su 274.

⭐ **E su «Situazione aperta» il vuoto era per sempre, non «in questa
istanza»**: quella lente filtra `area <> 'COMMESSE'`, cioè esclude proprio
l'unico ramo che avrebbe risolto. Nessun dataset diverso l'avrebbe mai
riempita.

**Il rimedio è la cura di `-63` portata a monte** — `COALESCE` sulla chiave,
`emittente_soggetto_ruolo_id` altrimenti `emittenti_fiscali.soggetto_ruolo_id`
dedotto da `emittente_fiscale_id`. Una sola catena di JOIN, un solo posto.
`-62` non va rifatta: proietta la colonna da qui e si riempie da sola
(verificato in transazione: 274/274, 156/156, backlog invariato 95/95).

> ⭐ **La lezione, e non è quella che sembra.** La verifica che questo brief
> prescriveva — *«guardare cosa legge il backend, non il grafo delle viste»* —
> è stata fatta, ed è servita: ha trovato `-62` e `-63`. Non bastava, perché
> risponde alla domanda *«la colonna arriva?»* e non a *«la colonna è piena?»*.
> **L'unica verifica che le copre entrambe è contare le righe valorizzate** —
> `count(*)` contro `count(colonna)` — e va fatta sulla vista che il backend
> legge davvero, con un contesto operatore addosso.
>
> ⛔ **E il difetto era esattamente quello che il flag `multi_emittente` esiste
> per impedire**: una lista con l'adesivo «so dire da quale emittente arriva
> ogni riga» e la colonna muta. La vista di controllo di catalogo dava — e dà —
> zero, perché è un controllo di **catalogo**: sa che la colonna è dichiarata,
> non che porta un valore. Il collaudo riga-per-riga resta a mano, ed è la
> ragione per cui il flag si accende una lista alla volta.

### 🔴 R-4 chiedeva 3 viste. Ne servivano 5, e le due mancanti erano quelle silenziose

È la scoperta più importante del giro, e vale la pena capire come è stata
possibile, perché il tranello si ripresenta.

Il brief dava le liste **«Situazione aperta»** e **«Backlog»** per *«eredita»* la
colonna da `vw_dash_fatturazione_documenti`. La frase è **vera del dato** — è lì
che nasce — e **falsa della proiezione**: sono due viste separate
(`vw_dash_aperto_documenti`, `vw_dash_backlog_documenti`) con elenco di colonne
**esplicito**, e sono **quelle** che il backend legge (`vendite_repository.py`,
righe 607 e 1737), non la union a monte.

> ⚠️ **Come sarebbe finita senza accorgersene**: migrazione verde, catalogo
> seedato, presidi verdi, e la colonna **vuota a video**. Nessun errore da
> nessuna parte a spiegare perché. È il difetto che nessuna suite trova, perché
> non c'è niente di rotto — c'è solo una colonna che non è stata elencata.
>
> ⭐ **La verifica che lo ha fatto emergere è banale, e va rifatta ogni volta**:
> guardare **cosa legge il backend**, non il grafo delle viste.

E il backlog aveva **un secondo strato**: è a sua volta una `UNION` di tre rami, e
i due rami **RESI** non hanno `emittente_soggetto_ruolo_id` (lì è `NULL`) ma
hanno `emittente_fiscale_id`. Risolvere il nome solo dal soggetto-ruolo avrebbe
lasciato muto **l'intero blocco resi** — e siccome i resi sono una minoranza
delle righe, sarebbe passato per *«qualche riga senza emittente»* invece che per
un ramo mai risolto. Si risolve con un `COALESCE` sulla **chiave**, sfruttando
l'uno-a-uno `emittenti_fiscali.soggetto_ruolo_id` (`NOT NULL` + `UNIQUE`): una
sola catena di JOIN.

### I changeSet

| # | Oggetto | Cosa |
| --- | --- | --- |
| `20260818-58` | `script.fn_get_ba_emittente_sr_id` | **nuova** — «quale emittente fattura questo billing account?» |
| `20260818-59` | `script.fn_check_ba_visible_for_emittenti` | delega la regola a due livelli alla `-58`: una definizione sola |
| `20260818-60` | `script.fn_search_soggetti_universale` | **R-5** — `emittente_ragione_sociale` in coda (DROP+CREATE: cambia il `RETURNS TABLE`) |
| `20260818-61` | `vendite.vw_dash_fatturazione_documenti` | R-4 — la JOIN scritta **una volta**, avvolgendo la union dei sei resolver |
| `20260818-62` | `vendite.vw_dash_aperto_documenti` | R-4 — 🔴 *non era nel brief* |
| `20260818-63` | `vendite.vw_dash_backlog_documenti` | R-4 — 🔴 *non era nel brief*, + i due rami resi |
| `20260818-64` | `vendite.vw_dash_competenza_errori` | R-4 |
| `20260818-65` | `vendite.vw_dash_competenza_attivita` | R-4 — alimenta il drill-down commesse |
| `20260818-66` | `script.fn_get_emittenti_scope` | **DROP** della legacy fail-open (fuori perimetro Fase E, vedi §finale) |
| `20260818-74` | `vendite.vw_dash_fatturazione_documenti` | 🔴 **correzione di `-61`** — il nome si risolveva da una colonna che cinque resolver su sei scrivono `NULL`. Ricade su `-62`, che non va rifatta |
| CSV | `80_data/sql/ui/lista_colonna.csv` | **R-3** — righe id **479→483** |

### Perché R-5 ha prodotto due funzioni e non una

Perché la regola *«quale emittente fattura questo billing account»* esisteva nel
database **solo in forma booleana**, dentro `fn_check_ba_visible_for_emittenti`
(*«è visibile per questi emittenti?»*). Ottima per filtrare, inutile per
**mostrare**.

Le strade erano due: riscriverla nel punto che deve mostrarla, o estrarla. La
prima sembra più corta, ma due copie della stessa regola non restano uguali:
alla prima modifica **il filtro e l'etichetta a video iniziano a raccontare cose
diverse sullo stesso billing account**, senza che nessuna delle due sia sbagliata
da sola. Per una regola di perimetro è il difetto peggiore, perché è silenzioso.

Quindi: estratta in `-58`, e il check delega (`-59`). L'equivalenza fra vecchia e
nuova forma è **esatta** — la garantiscono i due indici univoci
`uq_emittenti_fiscali_ba` e `uq_emittenti_fiscali_ba_default` — ed è anche
**esercitata sui dati**, perché una dimostrazione non è un presidio.

### ⭐ La colonna della ricerca è filtrata dallo scope, non solo la riga

È il punto meno ovvio di R-5, e il brief non lo poneva.

Non basta che la **riga** sia visibile: se un soggetto è cliente di A e di B, e
chi guarda ha in whitelist il solo A, la riga si vede (via A) ma la colonna deve
dire **«A»**, non «A, B». Altrimenti una colonna nata per *disambiguare*
finirebbe per **rivelare l'esistenza di un emittente fuori perimetro**.

Con scope `NULL` (super admin) il filtro non morde e si vedono tutti: è
esattamente il caso per cui la colonna è stata chiesta.

### I test

| File | Cosa presidia |
| --- | --- |
| `db/pgtap/script/test-ba-emittente-risoluzione-v1.sql` (13) | la risoluzione a due livelli, l'equivalenza col check, il **BA nullo che non cade nel default**, la colonna dichiarata nella ricerca |
| `db/pgtap/vendite/test-viste-dash-emittente-v1.sql` (12) | la colonna nelle 5 viste, ⭐ `security_invoker=on` su tutte e 5, le 6 righe di catalogo, ⭐ **la coerenza catalogo↔vista** |

> ⭐ Il test più importante del secondo file **non parla di emittenti**:
> verifica che tutte e cinque le viste abbiano ancora `security_invoker = on`.
> Quella reloption **non è visibile in `pg_get_viewdef`**: chi ricrea una vista
> partendo dalla definizione stampata la perde senza nessun avviso, e da quel
> momento la RLS smette di filtrare per chi legge. Cinque `CREATE OR REPLACE` in
> un colpo solo sono cinque occasioni di sbagliarlo.

---

## Il quadro, misurato

| Lista | Da dove nascono le righe | id emittente | ragione sociale | serve dal DB |
| --- | --- | :---: | :---: | --- |
| **Situazione aperta — documenti** (39) | `vw_dash_fatturazione_documenti` | ✅ | ❌ | vista + catalogo |
| **Backlog — documenti fermi** (40) | *la stessa vista a monte* | ✅ | ❌ | **eredita** + catalogo |
| **Competenza — errori vivi** (41) | `vw_dash_competenza_errori` | ✅ (`l.emittente_soggetto_ruolo_id`) | ❌ | vista + catalogo |
| **Competenza — drill-down commesse** (43) | `vw_dash_competenza_attivita`, **aggregata dal BE** | ✅ (`co.emittente_soggetto_ruolo_id`) | ❌ | vista + catalogo |
| **Lotti di fatturazione** (12) | SQL diretto su `vendite.fatturazione_lotti` — **nessuna vista** | ✅ (colonna `NOT NULL`) | n/a | **solo** catalogo |

⭐ **Aperto e backlog costano una JOIN sola**: sono due proiezioni della
**stessa** vista a monte (`vw_dash_fatturazione_documenti`). È il motivo per cui
Q4 le aveva messe insieme nel 2° giro.

⭐ **Lotti non chiede niente al database oltre alla riga di catalogo**: il dato
è già sulla tabella, la JOIN a `soggetti_ruoli`/`soggetti` la fa il repository.
È il motivo per cui Q4 la metteva ultima — «non insegna niente al database».

---

## R-3 · Le cinque righe di catalogo ⛔

Append a `80_data/sql/ui/lista_colonna.csv`, **copiando la riga della pilota**
(id 478, lista 42), che è già nella forma delle sei liste documento:

```text
codice          = emittente_fiscale
etichetta       = Emittente
campo_sorgente  = emittente_ragione_sociale
tipo_colonna    = informazione
tipo_dato       = string
ordine_default  = 100
filtrabile=t  ordinabile=t  esportabile=t  ricercabile_full=f  sensibile=f  attivo=t
etichetta_i18n_key = <vedi sotto>
```

⚠️ **`etichetta_i18n_key` non è la stessa per tutte**: la radice segue la
**cartella del frontend** che monta la lista, non lo schema DB
(frontend-standards §Multilingua). Per queste cinque:

| Lista | chiave |
| --- | --- |
| `vendite.dash_aperto_documenti` | `vendite.situazione_aperta.col_emittente` |
| `vendite.dash_backlog_documenti` | `vendite.dashboard_backlog.col_emittente` |
| `vendite.dash_competenza_errori` · `vendite.dash_competenza_commesse` | `vendite.dashboard_competenza.col_emittente` *(già esiste — è quella della pilota)* |
| `vendite.lotti` | `vendite.lotti.col_emittente` |

🔵 **Le chiavi mancanti le aggiunge il BE** in `it.json`/`en.json` insieme al
proprio pezzo: sono frontend. Qui servono solo **scritte giuste** nel CSV,
perché è il CSV a dire al frontend quale chiave cercare — e una chiave che non
esiste non dà errore, mostra l'etichetta italiana anche in inglese.

⚠️ **`ordinabile = t` non è gratis**: il presidio
`apps/core/tests/test_liste_configurabili_seed.py` pretende che ogni colonna
ordinabile stia nella whitelist di ordinamento del suo repository, **e nei due
versi**. È già successo con la pilota: la riga di catalogo è arrivata il
2026-08-17 e il presidio è rimasto **rosso fino al giorno dopo**, quando il BE
ha aggiunto la voce. Non è un problema — è il presidio che fa il suo mestiere —
ma conviene saperlo: **fra il seed e il codice BE la CI è rossa**, e va
attraversata in fretta o concordata.

---

## R-4 · `emittente_ragione_sociale` in tre viste ⛔

Il pattern è **già scritto sette volte** (le sei liste documento più la pilota),
e non va inventato:

```sql
LEFT JOIN anagrafiche.soggetti_ruoli sr_ef ON sr_ef.id = <…>.emittente_soggetto_ruolo_id
LEFT JOIN anagrafiche.soggetti       s_ef  ON s_ef.id  = sr_ef.soggetto_id
-- in proiezione:
s_ef.ragione_sociale_completa AS emittente_ragione_sociale
```

| Vista | Quante liste ne dipendono | Nota |
| --- | :---: | --- |
| `vendite.vw_dash_fatturazione_documenti` | **2** | è la vista a monte di aperto **e** backlog: la JOIN si scrive una volta |
| `vendite.vw_dash_competenza_errori` | 1 | l'emittente arriva dal lotto (`l.emittente_soggetto_ruolo_id`) |
| `vendite.vw_dash_competenza_attivita` | 1 | alimenta il drill-down commesse, che il BE **aggrega** (sotto) |

### ⚠️ Due vincoli di `CREATE OR REPLACE VIEW`, silenziosi se sbagliati

Sono gli stessi pagati sulla pilota (`20260818-15`), e li ripeto perché non si
vedono finché non fanno danno:

1. **`security_invoker = on` va RI-SPECIFICATA** o PostgreSQL la azzera — e su
   queste viste ci si appoggia lo scope emittente: senza, la RLS smette di
   filtrare per chi legge;
2. si possono solo **appendere** colonne in coda: la nuova è per forza l'ultima.

### ❓ Una domanda di merito sul drill-down commesse (lista 43)

Il BE non legge la vista riga per riga: **aggrega**, con

```sql
GROUP BY a.commessa_id, a.commessa_codice, a.cliente_display
```

Per portare l'emittente a video il backend deve aggiungerlo al `GROUP BY`. È
sicuro **solo se l'emittente è funzionalmente dipendente dalla commessa** —
cioè se una commessa non può avere attività di emittenti diversi. Se lo fosse,
la stessa commessa si spezzerebbe in **più righe** nel drill-down, e sarebbe una
regressione silenziosa (i totali resterebbero giusti, il conteggio delle righe
no).

> **La domanda è una sola: `vw_dash_competenza_attivita.emittente_soggetto_ruolo_id`
> è univoco per `commessa_id`?** Se sì, il BE aggiunge la colonna al `GROUP BY`
> e non serve altro. Se no, va deciso **cosa mostrare** su una commessa
> multi-emittente — e allora la colonna su quella lista è un lavoro diverso, non
> una riga di CSV.

#### ✅ Risposta del team DB (2026-08-18): **sì, e non è una misura — è strutturale**

Nella vista quella colonna è `co.emittente_soggetto_ruolo_id`, dove `co` è
**`vendite.commesse`**; e `commessa_id` è `co.id`, cioè la sua chiave primaria.

> **L'emittente è una colonna della commessa stessa.** Una commessa ha un solo
> emittente per lo stesso motivo per cui ha un solo codice: è un campo di quella
> riga. Una commessa **non può** avere attività di emittenti diversi, perché
> l'emittente non sta sull'attività.

Non è una proprietà dei dati che possa cambiare domani. **Il BE può aggiungere
la colonna al `GROUP BY` in sicurezza**: non può spezzare una commessa in più
righe.

⚠️ **La colonna nel `GROUP BY` serve comunque.** PostgreSQL sa dedurre da sé la
dipendenza funzionale quando si raggruppa per la **chiave primaria di una
tabella**, ma qui si raggruppa su una colonna di **vista**: la deduzione non
scatta. È solo innocua, non superflua.

⚠️ **La controprova sui dati non è utilizzabile, e vale la pena sapere perché.**
Interrogando la vista si ottengono **zero commesse** — ma quello zero *non è un
dato*: la vista filtra sullo scope emittente e una sessione senza utente è
fail-closed. Sulle tabelle base: **59 commesse, tutte con emittente valorizzato,
92 attività**. La prova resta comunque la struttura, non il conteggio.

---

## R-5 · L'emittente nella riga della ricerca universale 🔵 · *residuo D-3*

### Cosa manca

`script.fn_search_soggetti_universale` restituisce:

```sql
RETURNS TABLE(total_count bigint, soggetto_id uuid, soggetto_ruolo_id bigint,
              tipo_ruolo_id integer, soggetto_codice text,
              ragione_sociale_completa text, id_fiscale_univoco text,
              utility_list text)
```

**Nessun emittente.** La funzione lo *usa* per filtrare (ramo `CL`, dal
2026-08-18 risolvendoselo da sé), ma non lo *espone*.

### Perché serve, e perché l'etichetta di perimetro non basta

Il frontend ha appena messo un'etichetta sopra i risultati — *«stai cercando in
tutti gli emittenti»* (P-2c, passo D-3). È onesta e utile, ma dichiara il
**perimetro**, non risolve il caso concreto:

> Due clienti **omonimi**, di due emittenti diversi, sono a video **due righe
> identiche**. Il super admin ne sceglie una e non ha modo di sapere quale.

È esattamente la distinzione di P-2c fra le due cure: su un **numero** basta
dichiarare il perimetro, su una **riga affiancata ad altre** serve il dato.

### Cosa si chiede

Una colonna in coda al `RETURNS TABLE`:

```sql
emittente_ragione_sociale text   -- NULL quando il ruolo non ne ha uno
```

⚠️ **Sul tipo ruolo `CL` l'emittente c'è** (è quello su cui la funzione già
filtra, via `emittenti_fiscali_billing_account`). Su `FO` e sugli altri rami
**non esiste** e la colonna esce `NULL`: è la risposta giusta, non un buco —
una ricerca fornitori non ha perimetro emittente, e la funzione non deve
inventarne uno. Il frontend mostra l'etichetta solo dove il valore c'è.

❓ **Da decidere insieme**: un soggetto cliente può avere billing account sotto
**più** emittenti (è lo scenario §3.1 del brief madre, legittimo). In quel caso
la riga di ricerca è **una** e gli emittenti sono due. Le strade sono due, e la
scelta è di merito:

| | Cosa mostra | Costo |
| --- | --- | --- |
| **A** — una riga per soggetto, emittenti **aggregati** (`string_agg`) | «Tito Srl, Pippo Spa» | non cambia il numero di righe: la paginazione resta quella di oggi |
| **B** — una riga **per emittente** | due righe «Rossi SRL» distinguibili | cambia la cardinalità del risultato, e con essa `total_count` e la paginazione |

> ⭐ **Proposta: A.** La ricerca universale serve a *trovare il soggetto*, non a
> scegliere un perimetro; e B cambierebbe il significato di `total_count` — che
> oggi conta soggetti — per un caso raro. Con A la riga resta una e dichiara
> onestamente che quel cliente vive sotto due emittenti.

#### ✅ Risposta del team DB (2026-08-18): **A**, e il caso non è raro — ma l'etichetta va cambiata

**Il numero, prima di tutto.** Su **7 soggetti cliente, 1** ha già billing
account sotto più emittenti: il **14%**, non un caso di laboratorio. Il che
rafforza A — con B quel soggetto diventerebbe due righe e `total_count`
smetterebbe di contare soggetti.

##### ⚠️ Ma c'è un punto di modello che la richiesta non mette a fuoco

La riga della ricerca universale è un **soggetto**. E **un soggetto non ha un
emittente**: verificato sul catalogo, in tutta l'anagrafica l'emittente compare
in un solo posto — `emittenti_fiscali_billing_account` — e non esiste su
`soggetti`, `soggetti_ruoli`, `clienti`, `billing_account` né
`istanze_utilities`. Il legame è solo **transitivo**, via billing account.
Scritto come sezione canonica in
[soggetti-e-ruoli-anagrafici §5a-bis](/guide/soggetti-e-ruoli-anagrafici).

Ne seguono tre cose:

1. **B non è solo costosa: è concettualmente sbagliata.** Moltiplicherebbe i
   soggetti per una proprietà che non è loro;
2. **A va bene, ma l'etichetta «Emittente» no.** Su una riga-soggetto quella
   colonna mostra una **relazione**, non un attributo. Chiamarla «Emittente»
   insegnerebbe un modello falso: meglio *«Emittenti presso cui è cliente»* o
   simile. È una scelta FE, ma nasce da un vincolo di dominio;
3. **i due scenari che motivano R-5 sono diversi**, e il brief li tratta come uno:

   | Scenario | A video | La colonna cosa fa |
   | --- | --- | --- |
   | **(a)** due soggetti **diversi** omonimi, ciascuno sotto un emittente | due righe | **disambigua** — è il caso portato a motivazione |
   | **(b)** **un** soggetto sotto due emittenti | una riga | **descrive** — è il caso misurato (1 su 7) |

   Per (a) la colonna funziona perfettamente. Per (b) l'aggregato è l'unica
   risposta onesta, e non disambigua niente — perché non c'è niente da
   disambiguare: quella riga *è* una sola.

##### 🔵 Una nota sul livello 2, da tenere per il futuro

L'esclusione di `fn_get_search_detail` è motivata bene («non c'è una riga gemella
accanto»). Vale però la pena annotare che il dettaglio elenca le righe
**cliente**, e ogni riga cliente punta a **un** billing account, quindi a **un**
emittente: è l'unico posto dove il dato è per-riga e non ambiguo. Non si chiede
di aggiungerlo — si segnala dove sarà la sede, se un domani servirà *«di quale
emittente è questo rapporto»*.

⚠️ **`fn_get_search_detail` (livello 2) resta fuori da questa richiesta**: il
dettaglio si apre su **un** soggetto già scelto, quindi non c'è nessuna riga
gemella accanto da cui distinguerlo. È la stessa ragione per cui il dettaglio di
un documento non prende il cancello (P-2c, ultima riga della tabella).

---

## Cosa fa il backend — ⭐ **adesso: le tre cose ci sono tutte**

> ✅ Aggiornato il **2026-08-18**: catalogo, viste e funzione sono applicati e
> verdi. Quello che segue non è più una previsione, è la lista di lavoro.

### ⛔ BE-E1 — la whitelist di ordinamento, o la CI resta rossa

Le cinque righe di catalogo sono seedate con `ordinabile = t`, copiando la
pilota. Il presidio `apps/core/tests/test_liste_configurabili_seed.py` pretende
che **ogni colonna ordinabile stia nella whitelist di ordinamento del suo
repository, nei due versi**.

> ⚠️ Quindi **da adesso la CI è rossa** finché il BE non aggiunge le cinque voci.
> Non è un difetto: è il presidio che fa il suo mestiere, e la finestra era
> prevista nel brief («va attraversata in fretta o concordata»). Le colonne
> interessate sono `emittente_ragione_sociale` sulle liste `dash_aperto_documenti`,
> `dash_backlog_documenti`, `dash_competenza_errori`, `dash_competenza_commesse`,
> `lotti`.

### ⛔ BE-E2 — l'etichetta della ricerca NON può essere «Emittente»

Su una riga-soggetto quella colonna mostra una **relazione**, non un attributo:
il soggetto non ha un emittente, ce l'ha il suo billing account. «Emittenti
presso cui è cliente», o simile. È una scelta di frontend, ma nasce da un
vincolo di dominio — vedi
[soggetti-e-ruoli-anagrafici §5a-bis](/guide/soggetti-e-ruoli-anagrafici).

E i due scenari che motivano R-5 restano **diversi**, anche adesso che la colonna
c'è: su due soggetti omonimi la colonna *disambigua*; su un soggetto sotto due
emittenti *descrive*, e non c'è niente da disambiguare — quella riga è una sola.

### 🔵 BE-E3 — la colonna della ricerca arriva da sola nel JSON

`search_repository.py` usa `row_to_json(r)`: la chiave `emittente_ragione_sociale`
compare nell'envelope **senza toccare la query**. Resta da esporla nel serializer
e a video.

### 🔵 BE-E4 — `emittente_ragione_sociale` non è ordinabile nella ricerca

È un aggregato (`string_agg`): ordinarci sopra ordinerebbe per la stringa
concatenata, non per emittente. Non è stata messa nella whitelist di
`p_order_by`, e non va aggiunta senza deciderlo.

### Il resto, come previsto

| Lista | Lavoro BE |
| --- | --- |
| aperto · backlog · errori | colonna nel `SELECT` + riga nel mapping + voce nella whitelist di ordinamento + chiave i18n |
| drill-down commesse | idem, **più** la colonna nel `GROUP BY` (vedi la domanda in R-4) |
| lotti | JOIN a `soggetti_ruoli`/`soggetti` in `list_lotti` + colonna + mapping + whitelist + i18n |
| ricerca (R-5) | colonna nel repository + etichetta **per riga** al posto di quella di perimetro |

Il presidio `test_liste_configurabili_seed` lega catalogo e whitelist nei due
versi, e `test_perimetro_emittente_copertura` verifica che ogni lista abbia il
suo cancello: **entrambi sono già verdi e diventano rossi** se una delle due
metà arriva senza l'altra. Non serve ricordarsene.

---

## Cosa NON si chiede

- **il flag `multi_emittente` acceso**: si accende **dopo**, lista per lista,
  quando la colonna mostra un nome su dati veri — mai insieme al seed della
  colonna (§7, decisione 3);
- ~~**nessuna migrazione applicata da me**~~ → **applicata da Tid il 2026-08-18**,
  changeSet `20260818-58`→`-67`;
- **niente sulle 10 liste di amministrazione**: sono `AdminAPIView` e restano
  fuori dal cancello per decisione (§13-bis, C-2);
- **`fn_get_search_detail`** (sopra).
