# Analisi — Presidi sul percorso storto

> 🟢 **CHIUSA e archiviata il 2026-09-19** (decisione di Tid: *«fai sia C1 che
> C2 […] così chiudiamo l'analisi e abbiamo i brief su cui lavorare»*).
>
> **Che cosa ne esce, in una riga per candidato:**
>
> | | Esito | Dove continua |
> | --- | --- | --- |
> | **C1** stato previsto e mai scritto | ✅ **chiuso lato DB il 21-09** | [brief-db-presidio-stati-mai-scritti.md](brief-db-presidio-stati-mai-scritti.md) — registro `dbops.stati_check_dichiarazioni` (40 righe, col `canale`), `vw_stati_check_scrittori` + `vw_stati_check_da_sanare` (`CANCELLO`, a zero), pgTAP a 14 test; il perimetro vero è 32 colonne, non 18. 🔵 Resta la metà Python (§6 del brief), in coda a C2 |
> | **C2** promessa all'interfaccia | 🔵 **brief aperto** | [brief-be-presidio-ui-action-e-canale-campi.md](../work-in-progress/brief-be-presidio-ui-action-e-canale-campi.md) — coerenza `highlight_form_fields` ↔ canale `fields`, con la decisione di Tid del 09-09 come premessa |
> | **C3** liste che non sanno dire perché | ✅ chiuso da solo | 20 liste su 77 col motivo (§3-quater); non serve un cancello |
> | **C4** registri scritti e mai letti | ✅ chiuso | `event_log` ha i suoi lettori (§3-bis) |
> | **C5** numero a mano | ⛔ escluso | si corregge quando si tocca il file |
>
> ⭐ **La lezione, ed è il motivo per cui si chiude invece di rimisurare una
> quarta volta:** in quattro settimane e tre rimisure nessun presidio è nato da
> questo documento — C3 e C4 li ha chiusi il lavoro ordinario, C2 l'ha sbloccato
> una decisione che stava in un altro file. *I presidi del percorso storto non
> nascono da soli, e un'analisi non li sostituisce: li sostituisce un brief.*
> Il §2 resta vero e vale come premessa dei due brief.
>
> **Destinatari:** Tid, backend, frontend, team DB
>
> **Tipo:** analisi + catalogo di candidati. Non è un piano di cantiere: è
> l'inventario di una leva che il progetto usa bene su metà del suo perimetro.
>
> **Stato:** WIP — inventario misurato il 2026-08-22, **rimisurato il 2026-09-05**
> (§3-bis), **il 2026-09-15** (§3-ter) **e il 2026-09-19** (§3-quater, da
> leggere per primo). Nessun candidato è stato scritto; due si sono chiusi o
> quasi **da soli**, uno è peggiorato in silenzio.
> ⏱️ *15-09*: **C2 ha il suo primo consumatore**, arrivato da fuori (28-08) —
> la decisione 3 del §6 è presa e il presidio C2 ora si può scrivere.
> ⏱️ *19-09*: ⚠️ **quella decisione non era «di fatto»: era di Tid, del
> 2026-09-09, ed è scritta in `api.md`** — questo documento l'aveva persa per
> dieci giorni (§3-quater). Ne discende anche la **forma** del presidio C2. Le
> altre tre decisioni del §6 restano aperte.
>
> **Origine:** discussione con Tid del 2026-08-22, nata da un'altra domanda
> («l'osservabilità ci fa trovare i bug più in fretta?»). La risposta ha fatto
> emergere che *trovare* e *capire* sono due mestieri diversi, e che il progetto
> ne presidia sistematicamente uno solo.
>
> **Cosa NON è.** Non è
> [analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md): quella risponde a
> «come capisco in fretta un caso già rotto», questa a «come evito che il caso
> rotto esca». Sono leve opposte e vanno tenute in due documenti — vedi §1.

---

## 1. La distinzione, e perché conta

Sotto la frase «trovare bug» ci stanno due mestieri con strumenti diversi:

| | Scoprire un difetto che **non sai** di avere | Capire in fretta un difetto che **sai** di avere |
| --- | --- | --- |
| Strumento | cancelli, presidi, smoke su chiamate reali | log, timeline, `correlation_id` |
| Quando agisce | mentre scrivi, prima che esca | dopo, quando il danno è visibile |
| Effetto | **meno** difetti | **meno tempo** per difetto |
| Documento | questo | [analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md) |

**La prova che in questo repo la colonna sinistra rende di più** è di questa
settimana, e non è un'opinione:

* i difetti trovati durante il cantiere delle liste del drawer lotto li ha
  trovati il **presidio del seed** (una colonna dichiarata `ordinabile = f`
  mentre la funzione DB la sa ordinare: capacità irraggiungibile) e una
  **prova reale** — il `DELETE` mancante al ruolo worker su `vendite.note`, che
  rompeva il rollback **solo** dal canale batch e che nessun test coglieva,
  perché i mock non vedono i grant
  ([brief-db-grant-batch-cleanup-note.md](brief-db-grant-batch-cleanup-note.md));
* nessuno è stato trovato leggendo un registro.

Un log si consulta quando **già sai** che qualcosa non va. Un cancello ti ferma
quando non lo sai ancora. Servono entrambi, ma solo il secondo riduce il numero.

---

## 2. I presidi che ci sono già, e cosa hanno in comune

L'inventario è reale e non piccolo. In `apps/core/tests/`:

| Presidio | Cosa impedisce |
| --- | --- |
| `test_error_codes_db_policy_guardrail` | «il cancello del terzo lato»: ogni codice `E_*` nominabile da una funzione PL/pgSQL viva deve avere una voce in `error_policies.py` |
| `test_error_codes_declared_guardrail` | AST: un codice `E_*` passato a un punto di chiamata (`code=` / `error_code=`) e non dichiarato |
| `test_error_policies_divergenza_db` | `error_policies_generated.py` che diverge dal catalogo DB |
| `test_perimetro_emittente_copertura` | una lista configurabile senza view che dichiara `lista_codice` — **o senza una ragione scritta nel registro delle esenzioni** |
| `test_system_context_usage_whitelist` | il canale di sistema `BYPASSRLS` usato dentro un percorso di richiesta web (leak cross-tenant) |
| `test_transaction_atomicity_guardrail` | AST: 2+ scritture DB composte senza `transaction.atomic()` |
| `test_liste_configurabili_seed` | il seed delle liste che diverge dalle whitelist di ordinamento — nelle tre sorgenti dove l'ordine può vivere |

Più, fuori da Python: `scripts/sql/guardrail_codice_errore_strutturato.sql`,
`plpgsql_check` sui corpi delle funzioni, i test pgTAP.

### L'osservazione che li accomuna

**Guardano tutti il percorso felice.** Che i codici siano dichiarati, che il
seed corrisponda, che le transazioni siano atomiche, che lo scope sia coperto:
sono tutte proprietà di *com'è fatto* il sistema quando funziona.

Nessuno controlla che un **fallimento** sia raccontabile: che uno stato di
errore previsto dal modello venga davvero scritto, che una lista sappia dire
perché una riga è ferma, che un registro scritto abbia un lettore, che una
promessa fatta all'interfaccia venga mantenuta.

Non è una critica al lavoro fatto: è l'ordine naturale con cui si costruisce —
prima si fa funzionare, poi si fa raccontare. Ma è un perimetro scoperto, ed è
lo stesso perimetro dove un gestionale passa molta della sua vita in esercizio.

---

## 3. I candidati, misurati

Tutti i numeri sotto sono letti da **git** — codice, seed, catalogo — non dal
database di sviluppo. Reggono indipendentemente dai dati (la ragione sta nel
§0-bis di [analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md)).

### C1 — Uno stato di fallimento previsto dal modello e mai scritto 🔴

**Il caso che ha fatto nascere questo documento.** `stato_esecuzione = 'ERRORE'`
era nel `CHECK` della tabella dal primo giorno, con un contatore dedicato nella
summary. Non è mai stato scritto da nessuno fino al **2026-08-21**: le corse
chiudevano in `COMPLETATO` anche quando un documento veniva rifiutato.

Il modello aveva il posto giusto dove dire la verità, e nessuno lo riempiva.

**Presidio candidato.** Per ogni valore ammesso da un `CHECK` di stato, esiste
almeno un punto del codice che lo scrive? La sorgente c'è già ed è quella che i
test usano di consueto: la doc auto-generata `dbzero` (i `CHECK` sono lì) più una
ricerca sui repository. Registro di esenzioni per i valori che il DB scrive da
sé.

⚠️ È il candidato più difficile dei cinque — un valore può essere scritto da una
funzione SQL e non da Python — e anche il più prezioso: è la classe di difetto
che rende un sistema *muto sui propri fallimenti*.

### C2 — Una promessa all'interfaccia che nessuno mantiene 🔴

Misurato:

| | |
| --- | --- |
| Codici errore totali | **658** |
| `ui_action` per override esplicito | **177** (⚠️ il commento in testa a `error_ui_overrides.py` dice **176**) |
| di cui `highlight_form_fields` — *«evidenzia il campo del form»* | **126** |
| L'envelope porta `ui_action`? | **sì**, da `error_responses.py` |
| Il frontend la legge? | **sì**: `useApiHandler` la mette in `azioneUi` |
| Quanti `.vue` consumano `azioneUi`? | **0** |

Il filo è staccato **all'ultimo centimetro**: c'è il catalogo, c'è la decisione
motivata codice per codice, c'è l'envelope, c'è il composable — e nessun
componente la usa.

⭐ **E c'è un secondo strato, che è la parte interessante.** I campi *vengono*
evidenziati, ma per un canale diverso: `error.fields` → `campiErrati` → **57
file `.vue`**. Quindi la promessa e il comportamento viaggiano su due binari
indipendenti, e **possono divergere in silenzio**:

* un codice che promette `highlight_form_fields` ma risponde senza `fields` non
  evidenzia niente;
* un codice che promette `show_error_banner` ma risponde con `fields` evidenzia
  comunque.

**Presidio candidato**, e qui è quasi ovvio: coerenza fra la `ui_action`
dichiarata a catalogo e il canale che la realizza. Più, separatamente, la
domanda a monte — se `ui_action` non la consuma nessuno, o le si dà un
consumatore o si smette di produrla; quello che non regge è tenerla a metà.

### C3 — Liste che non sanno dire perché una riga è ferma 🟡

Dal seed (`db/changelog/migrations_v2/80_data/sql/ui/lista_colonna.csv`):
su **47 liste** registrate, **due** hanno una colonna che parli di errore o di
stato di esecuzione — `config.email_log`, che è un log per mestiere, e
`vendite.lotto_fatture`, costruita il 2026-08-22.

**Presidio candidato.** Più debole degli altri due, e va detto: non tutte le
liste hanno righe che possono *restare ferme*. Il presidio sensato non è «ogni
lista deve avere una colonna d'errore» ma «ogni lista la cui sorgente **espone**
uno stato di fallimento deve mostrarlo, o dichiarare perché no» — di nuovo il
registro delle esenzioni motivate, l'idioma che `test_perimetro_emittente_copertura`
usa già.

### C4 — Registri scritti e mai letti ✅ *(CHIUSO il 2026-09-05: `event_log` ha i suoi lettori — §3-bis)*

`vendite.event_log` è scritto da due repository e non ha **nessun** endpoint di
lettura. Il piano per chiuderlo è in
[analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md) e non si duplica
qui; quello che riguarda **questo** documento è la classe: una tabella-registro
con scrittori e zero lettori è una condizione dichiarabile e verificabile.

⚠️ Con un'esenzione obbligatoria: alcuni registri sono di puro audit e si leggono
per forensica via SQL. Il presidio deve chiedere la **ragione**, non vietare il
caso.

### C5 — Un numero scritto a mano che invecchia ⛔ *(non fatene un presidio)*

`error_ui_overrides.py` dichiara in testa «176 override su 658»; le voci sono
**177**. Nessuna chiave duplicata, verificato: o il commento è invecchiato di una
voce, o c'è una ragione che non ho visto.

Lo elenco per onestà di metodo e per **escluderlo**: costruire un cancello che
verifica i numeri scritti nei commenti costa più del difetto che previene. Si
corregge e basta. Un presidio deve nascere da un difetto che **è costato**, non
da una categoria di difetti possibili.

---

## 3-bis. ⏱️ Rimisurato il 2026-09-05 — e il documento dimostra la propria tesi

> Quattordici giorni dopo. **Nessuno dei presidi candidati è stato scritto.** Le
> cifre sotto sono rilette dalle stesse sorgenti (git, seed, catalogo), non dal
> database.

| Candidato | 2026-08-22 | 2026-09-05 | |
| --- | --- | --- | --- |
| **C1** stato di fallimento mai scritto | 🔴 | 🔴 **invariato** | nessun presidio, nessuna esenzione |
| **C2** promessa all'interfaccia | 🔴 | 🔴 **più grande** | `.vue` che consumano `azioneUi`: **ancora 0**. Ma i codici a catalogo sono passati da 658 a **846**, gli override da 177 a **182**, `highlight_form_fields` da 126 a **131** |
| **C3** liste che non sanno dire perché | 🟡 | 🟢 **quasi chiuso, da solo** | da **2 liste su 47** a **15 su 66** (6 con la lettura stretta «errore / stato di esecuzione», 15 includendo `motivo`): `dash_competenza_errori`, `fatture_stampa_coda`, `lotto_task_runs`, `dash_aperto_documenti`… |
| **C4** registri scritti e mai letti | 🟡 | ✅ **CHIUSO** | `vendite.event_log` ha lettori: `script.vw_giornale_entita` più i due endpoint del giornale (fattura e lotto), consegnati col Passo A dell'osservabilità |
| **C5** numero a mano | ⛔ escluso | ⛔ e **invecchiato di più** | il commento dice ancora **176**, le voci sono **182**: lo scarto è passato da 1 a 6 |

### ⭐ Che cosa dice questa tabella, ed è il punto del documento

**C3 e C4 sono migliorati senza che nessuno li presidiasse** — li ha sistemati il
lavoro ordinario, perché stavano sul percorso di qualcosa che qualcuno voleva
(le dashboard, il giornale del lotto).

**C2 è l'unico che è peggiorato**, ed è l'unico che nessun lavoro attraversa: la
`ui_action` si continua a produrre — 188 codici nuovi in due settimane, override
compresi — e continua a non consumarla nessuno. ⭐ *Un filo staccato non si
riattacca da solo, e ogni settimana che passa ne aggiunge del cavo.*

E **C5 fa la sua parte**: il numero scritto a mano è invecchiato di altre cinque
voci, esattamente come previsto. ⇒ Resta escluso, e si corregge quando si tocca
il file.

### ⚠️ L'inventario del §2 è cresciuto: sette presidi, oggi **dieci**

Nuovi in `apps/core/tests/` dal 2026-08-22: `test_event_codes_declared_guardrail`,
`test_naming_codice_interno_python`, `test_ordinamento_data_desc`.
⚠️ Guardano tutti e tre il **percorso felice**, come i sette di prima:
l'osservazione del §2 regge invariata.

---

## 3-ter. ⏱️ Rimisurato il 2026-09-15 — un filo si è riattaccato, da fuori

> Dieci giorni dopo. Stesse sorgenti (git, seed, catalogo). **Nessun presidio
> candidato è stato scritto**; ma la voce che il 05-09 «peggiorava in silenzio»
> si è mossa, e l'ha mossa un cantiere che non pensava a questo documento.

| Candidato | 2026-09-05 | 2026-09-15 | |
| --- | --- | --- | --- |
| **C1** stato di fallimento mai scritto | 🔴 | 🔴 **invariato** | nessun presidio, nessuna esenzione |
| **C2** promessa all'interfaccia | 🔴 | 🟡 **mosso, da fuori** | `ui_action` ha il suo **primo consumatore**: `core/composables/useForzaturaConfermata.js` (28-08, brief incassi) dichiara a `useApiHandler` `azioniGestite: [CONFERMA_E_RIPETI]`, e il composable **spegne il toast** solo quando l'azione è gestita dal chiamante — «si dichiara la `ui_action`, mai un elenco di codici». Catalogo: **857** codici (+11), override **182** (=), `highlight_form_fields` **131** (=) |
| **C3** liste che non sanno dire perché | 🟢 | 🟢 **cresce da solo** | **67** liste (+1); **7** con colonna errore/stato di esecuzione (+1), **16** includendo `motivo` (+1). `ErroreRigaInfo.vue` ha **3** consumatori (era 1 il 22-08) |
| **C4** registri scritti e mai letti | ✅ | ✅ | — |
| **C5** numero a mano | ⛔ | ⛔ **fermo** | il commento dice ancora **176**, le voci **182**: nessuno ha toccato il file |

### ⭐ Che cosa dice, e che cosa corregge della misura del 22-08

**La misura di C2 guardava la grana sbagliata.** «Quanti `.vue` consumano
`azioneUi`» dice ancora **0** — e resta 0 anche oggi. Ma il consumatore giusto di
una `ui_action` non è un componente: è un **composable** che traduce l'azione in
un comportamento (qui: niente toast, la domanda la fa il chiamante). Contando i
`.vue` la misura non l'avrebbe mai visto. ⇒ La misura buona è «quanti punti
leggono `azioneUi` o dichiarano `azioniGestite`»: **1**, e prima era 0.

**La decisione 3 del §6 è presa di fatto: si consuma.** Non l'ha presa nessuno
in una riunione; l'ha presa il primo cantiere che aveva bisogno di
un'`ui_action` per fare la cosa giusta (chiedere conferma invece di mostrare un
errore). È esattamente il modo in cui C3 e C4 si erano chiusi: *sul percorso di
qualcosa che qualcuno voleva*.

⚠️ **Ma il presidio C2 resta da scrivere, e il secondo strato è intatto**: un
consumatore su 182 override non dice niente sulla coerenza fra la `ui_action`
dichiarata e il canale che la realizza — `highlight_form_fields` (131) viaggia
ancora sui `fields`, e i due binari possono divergere in silenzio come il 22-08.
Quello che cambia è che ora **si può** scrivere: la domanda a monte (produrla o
no) ha una risposta.

### ⚠️ L'inventario del §2: dieci, oggi **dodici**

Nuovi in `apps/core/tests/` dal 05-09: `test_skip_area_check_registro` e
`test_copertura_doc_api` (entrambi 12-09). ⚠️ Percorso felice tutti e due — il
registro delle esenzioni `skip_area_check` e la copertura della doc API.
L'osservazione del §2 regge invariata **per i presidi di CI**.

### ⭐ Fuori dal perimetro, ma sulla stessa leva: `dbops.presidi`

Dal 10-09 il progetto ha un **catalogo di presidi in esercizio** (`dbops.presidi`:
viste `ZERO` che *devono restare vuote* — code ferme, job falliti, processi
muti — contate da `fn_conta_presidio` attraverso la RLS) con un **destinatario**:
il digest email giornaliero/settimanale e il guardiano pgAgent che avvisa se il
digest stesso tace. Le prime corse vere sono del 14-09 e 15-09.

Non è questo documento — qui si parla di proprietà del **codice** verificabili
in CI, là di **dati** letti in esercizio — e non chiude C1 né C2. Ma va detto
per onestà verso il §2: l'osservazione «nessuno controlla che un fallimento sia
raccontabile» **non vale più sul lato runtime**. Là qualcuno guarda i
fallimenti, e c'è un catalogo con la ragione scritta per ogni vista — l'idioma
del registro delle esenzioni, che il §3 chiede per C1 e C3. ⇒ Quando C1 si
scriverà, la forma è già decisa dal vicino: **una riga di catalogo con la
ragione**, non un elenco nel test.

---

## 3-quater. ⏱️ Rimisurato il 2026-09-19 — il documento aveva perso una decisione

> Quattro giorni dopo. Stesse sorgenti (git, seed, catalogo). **Nessun presidio
> candidato è stato scritto.** La notizia non sta nei numeri, che si muovono
> poco: sta in una riga di `api.md` che la rimisura del 15-09 non ha letto.

| Candidato | 2026-09-15 | 2026-09-19 | |
| --- | --- | --- | --- |
| **C1** stato di fallimento mai scritto | 🔴 | 🔴 **invariato** | nessun presidio generico, nessun registro di esenzioni. I tre pgTAP che parlano di «mai scritto» presidiano **un** caso ciascuno (snapshot fattura, importi di riga, chiave a tre specchi): sono la forma per-caso, non la classe |
| **C2** promessa all'interfaccia | 🟡 | 🟡 **la decisione era già presa, e scritta** | vedi sotto. Catalogo **897** codici (+40; 92 ritirati, 805 vivi), override **182** (=), `highlight_form_fields` **129** (⚠️ non 131: vedi la correzione sotto). **Secondo lettore** di `ui_action`: `pagamenti/composables/useRigheDaRate.js` (17-09), sull'errore per-riga dell'esito PARZIALE di `righe/da-rate/` — stessa costante `CONFERMA_E_RIPETI`, stesso unico valore |
| **C3** liste che non sanno dire perché | 🟢 | 🟢 **cresce da solo** | **77** liste (+10); **9** con colonna errore/esito (+1: `magazzino.inventario_piano`), **20** includendo `motivo` (+3: `magazzino.rettifica_righe`, `pagamenti.distinta_righe`, …). `ErroreRigaInfo.vue`: **4** consumatori (+1: `PresidioChip.vue`, il pannello dei presidi). ⚠️ Criterio dichiarato, perché il 15-09 non lo era: `codice`+`campo_sorgente` di `lista_colonna.csv` che contengono `errore\|error\|stato_esecuzione\|esito` (stretto) o anche `motivo` (largo). Sul seed del 15-09 dà 8/17 contro il 7/16 scritto in §3-ter: la grana è la stessa, la soglia era di una lista |
| **C4** registri scritti e mai letti | ✅ | ✅ | — |
| **C5** numero a mano | ⛔ | ⛔ **fermo** | l'intestazione dice ancora «176» e «482 su 658»; le voci sono **182** e i codici **897** |

### ⚠️ La decisione 3 del §6 non era «di fatto»: era di Tid, del 09-09

`api.md` §«Cosa cambia davvero lo status, lato client» porta, con data:

> ⭐ **DECISIONE (Tid, 2026-09-09): le altre sei `ui_action` sono SERVITE, non
> ignorate — e la voce si chiude dichiarandolo.** Il default del client copre
> l'intero vocabolario tranne `confirm_and_retry`, che è l'unico a chiedere un
> comportamento che il default non sa produrre. […] ⚠️ E la condizione per
> accendere il settimo resta quella già scritta: le **176 righe di override**
> vanno riguardate **prima**, non dopo.

La §3-ter, scritta **sei giorni dopo**, dice che la decisione «l'ha presa il
primo cantiere che aveva bisogno di un'`ui_action`» — cioè attribuisce a un
consumatore arrivato per caso (28-08) una scelta che Tid aveva già messo per
iscritto, in un documento di lettura obbligatoria. ⛔ **È il §C5 applicato a
questo stesso documento**: una rimisura che rilegge le *proprie* sorgenti e
non quelle accanto invecchia esattamente come un numero in un commento.

**Che cosa cambia per C2, ed è più della paternità della decisione.** La
decisione dice **come** ogni `ui_action` viene servita — `highlight_form_fields`
da `campiErrati`, `redirect_login` dallo status 401, le altre quattro dal toast
— quindi il «secondo strato» del §3 (*la promessa e il comportamento viaggiano
su due binari*) non è più un'osservazione: è il **contratto**. Il presidio C2
ha allora una forma sola, e non è un presidio sul consumo:

> per ogni codice con override `highlight_form_fields`, esiste **un** punto di
> sollevamento che valorizza il canale `fields` (`context={"field": …}` in
> Python, `RAISE … USING COLUMN` in PL/pgSQL); e nessun codice con un'altra
> `ui_action` lo valorizza — con il registro delle esenzioni motivate per i
> casi in cui il campo esiste ma il banner è la resa scelta (precedente:
> `E_EMITTENTE_NON_RISOLTO`, 15-09, dichiarato in `error_ui_overrides.py`).

⭐ **Ed è esattamente la «rilettura delle 176 righe» che `api.md` mette come
condizione**: non un giro a mano una volta, ma un cancello che la rifà a ogni
PR. Le sorgenti sono tutte in git — l'override, i `context` dei `ServiceError`,
i corpi delle funzioni nella doc auto-generata — e il repertorio del §4 le
copre. ⚠️ Un presidio di **consumo** («quanti leggono `azioneUi`») invece
misurerebbe ancora la grana sbagliata: il consumatore giusto dei sei valori è
il default, e il default non si conta.

### ⚠️ Due misure di questo documento erano sbagliate, e si correggono qui

* **`highlight_form_fields` = 131 (05-09, 15-09) era un `grep -c`** che contava
  anche le righe di commento che nominano il valore. Contando i **valori**
  dell'override, il 15-09 erano già **129** — il numero che `api.md` scrive
  dallo stesso giorno. Due documenti, due numeri per lo stesso fatto: la
  lezione di `AGENTS.md` sulle versioni del frontend, in piccolo.
* **L'inventario del §2 diceva «dodici» il 15-09: erano quindici.** Mancavano
  `test_idempotency_key_contratto_fe_be` (08-09),
  `test_archiviazione_code_non_e_un_annullo` (09-09) e
  `test_coercizione_jsonb_dal_bb` (09-09). Oggi sono **sedici**:
  `test_export_lista_codice_pari` (18-09) — le coppie lista/export devono
  dichiarare lo stesso `lista_codice`. ⚠️ Percorso felice tutti e quattro:
  l'osservazione del §2 regge, e regge **meglio** con un conteggio giusto.
  (`test_logging_filters` resta fuori dal conto: è un test unitario di un
  filtro, non un presidio trasversale.)

### ⭐ Il vicino cresce: `dbops.presidi` ha un destinatario a video

Dal 18-09 il catalogo runtime (**42** viste: 21 `ZERO`, 9 `LAVORAZIONE`,
7 `INVENTARIO`, 4 `CANCELLO`, 1 `REGISTRO`) non parla più solo per posta: il
**pallino dei presidi** in topbar (`usePresidiPolling`, decisione #8 di Tid) e
il pannello «Processi automatici» rendono la stessa testata, e
`PresidioChip.vue` riusa `ErroreRigaInfo` — il quarto consumatore contato in
C3. ⚠️ Vale la stessa nota della §3-ter: è il lato **dati in esercizio**, non
chiude C1 né C2. Ma la forma «una riga di catalogo con la ragione» oggi ha
anche una superficie che la legge, e quando C1 si scriverà quella riga avrà già
un posto dove comparire.

---

## 4. La forma tecnica: perché costano poco

I candidati C1-C4 sono tutti test che **contano cose in git**, non nel database.
Girano in CI senza istanza, in secondi. Il repertorio esiste già:

| Tecnica | Precedente in casa |
| --- | --- |
| Analisi statica AST del codice Python | `test_transaction_atomicity_guardrail`, `test_error_codes_declared_guardrail` |
| Lettura dei CSV di seed | `test_liste_configurabili_seed` |
| Lettura della doc auto-generata `dbzero` come oracolo | `test_liste_configurabili_seed` (whitelist letta dalla doc della funzione) |
| Ricerca testuale sui `.vue` | il presidio del registro PrimeVue |
| Registro delle esenzioni **con ragione scritta** | `test_perimetro_emittente_copertura` |

⭐ L'ultima riga è la più importante e va imitata sempre: un presidio senza
esenzioni motivate diventa un presidio che si disattiva. Uno con le esenzioni
scritte trasforma ogni caso non coperto in **una frase che qualcuno ha dovuto
scrivere**, ed è lì che il difetto viene fuori.

---

## 5. I tre modi di sbagliarlo

Sono documentati, tutti e tre, da cose successe qui.

1. **Il presidio cieco.** Quello del registro PrimeVue era cieco su **4 liste su
   6**: la ricerca si fermava al `>` dentro un `v-if`. Diceva `ok` su un
   perimetro che non guardava. ➡️ **Ogni presidio va provato contro un caso che
   DEVE fallire**, non solo contro il verde.
2. **La protezione per caso.** Dal cantiere della nota di credito: *«il difetto
   era reale ma mascherato da un'altra precondizione — un controllo che protegge
   per caso non è un presidio»*. ➡️ Il presidio deve nominare **la** condizione,
   non ereditarne una vicina.
3. **La burocrazia.** Un presidio che non può indicare il difetto reale che ne
   ha causato la nascita è un costo fisso senza contropartita. ➡️ In testa a ogni
   presidio nuovo, come già fanno tutti quelli esistenti: `# Scopo:` e il brief
   o l'incidente da cui viene.

---

## 6. Decisioni da prendere

1. **Quali candidati**, e in che ordine. La mia proposta: **C2 primo** (il più
   circoscritto e con l'esito più netto: o si dà un consumatore a `ui_action` o
   si smette di produrla), **C1 secondo** (il più prezioso, il più difficile),
   C3 e C4 dopo. C5 è escluso per costruzione.
2. **Dove vivono.** `apps/core/tests/` accanto ai fratelli, o una cartella
   dedicata ai presidi del percorso storto?
3. **`ui_action`: consumarla o smettere di produrla?** È una decisione di
   interfaccia, non un presidio — ma il presidio C2 non si può scrivere prima di
   averla presa.
   ⏱️ *2026-09-15*: **presa di fatto — si consuma** (§3-ter:
   `useForzaturaConfermata` + `azioniGestite`). Il presidio C2 ha il suo
   prerequisito.
   ⏱️ *2026-09-19*: ⚠️ **era già presa da Tid il 2026-09-09, in `api.md`**
   (§3-quater): si continua a produrla, sei valori su sette li serve il
   default, e le righe di override vanno riguardate **prima** di un secondo
   consumatore. ⇒ Il presidio C2 non è più «consumarla o no»: è la coerenza
   `highlight_form_fields` ↔ canale `fields`, con esenzioni motivate.
4. **Chi decide le esenzioni.** Il registro con la ragione scritta funziona solo
   se la ragione la scrive chi conosce il dominio, non chi scrive il test.

---

## 7. Rapporto con gli altri documenti

| Documento | Rapporto |
| --- | --- |
| [analisi-osservabilita-log.md](../work-done/analisi-osservabilita-log.md) | **La leva opposta** (§1). Là: capire in fretta un caso rotto. Qui: evitare che esca. Il suo «binario parallelo» sulle liste è il candidato **C3** di questo documento |
| [fatturazione-roadmap.md](fatturazione-roadmap.md) | Da lì viene la frase del §5 punto 2 («un controllo che protegge per caso non è un presidio»). La roadmap resta il documento di dominio |
| [analisi-diagnostica-produzione-senza-accesso-db.md](../work-done/analisi-diagnostica-produzione-senza-accesso-db.md) | Cita due presidi esistenti come precedenti per un check CI: stessa tecnica, altro scopo |
| [api.md](../api.md) | La convenzione dei codici errore e dell'envelope — il terreno su cui si misura **C2** |

---

*Analisi WIP — Presidi sul percorso storto (22 agosto 2026; rimisure del 5, del
15 e del 19 settembre 2026 — §3-bis, §3-ter, §3-quater).*
