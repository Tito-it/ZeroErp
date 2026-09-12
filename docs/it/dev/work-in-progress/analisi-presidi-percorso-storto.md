# Analisi — Presidi sul percorso storto

> **Destinatari:** Tid, backend, frontend, team DB
>
> **Tipo:** analisi + catalogo di candidati. Non è un piano di cantiere: è
> l'inventario di una leva che il progetto usa bene su metà del suo perimetro.
>
> **Stato:** WIP — inventario misurato il 2026-08-22, **rimisurato il 2026-09-05**
> (§3-bis). Nessun candidato è stato scritto; due si sono chiusi o quasi **da
> soli**, uno è peggiorato in silenzio. Le decisioni del §6 sono tutte ancora
> aperte.
>
> **Origine:** discussione con Tid del 2026-08-22, nata da un'altra domanda
> («l'osservabilità ci fa trovare i bug più in fretta?»). La risposta ha fatto
> emergere che *trovare* e *capire* sono due mestieri diversi, e che il progetto
> ne presidia sistematicamente uno solo.
>
> **Cosa NON è.** Non è
> [analisi-osservabilita-log.md](analisi-osservabilita-log.md): quella risponde a
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
| Documento | questo | [analisi-osservabilita-log.md](analisi-osservabilita-log.md) |

**La prova che in questo repo la colonna sinistra rende di più** è di questa
settimana, e non è un'opinione:

* i difetti trovati durante il cantiere delle liste del drawer lotto li ha
  trovati il **presidio del seed** (una colonna dichiarata `ordinabile = f`
  mentre la funzione DB la sa ordinare: capacità irraggiungibile) e una
  **prova reale** — il `DELETE` mancante al ruolo worker su `vendite.note`, che
  rompeva il rollback **solo** dal canale batch e che nessun test coglieva,
  perché i mock non vedono i grant
  ([brief-db-grant-batch-cleanup-note.md](../work-done/brief-db-grant-batch-cleanup-note.md));
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
§0-bis di [analisi-osservabilita-log.md](analisi-osservabilita-log.md)).

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
[analisi-osservabilita-log.md](analisi-osservabilita-log.md) e non si duplica
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
4. **Chi decide le esenzioni.** Il registro con la ragione scritta funziona solo
   se la ragione la scrive chi conosce il dominio, non chi scrive il test.

---

## 7. Rapporto con gli altri documenti

| Documento | Rapporto |
| --- | --- |
| [analisi-osservabilita-log.md](analisi-osservabilita-log.md) | **La leva opposta** (§1). Là: capire in fretta un caso rotto. Qui: evitare che esca. Il suo «binario parallelo» sulle liste è il candidato **C3** di questo documento |
| [fatturazione-roadmap.md](../work-done/fatturazione-roadmap.md) | Da lì viene la frase del §5 punto 2 («un controllo che protegge per caso non è un presidio»). La roadmap resta il documento di dominio |
| [analisi-diagnostica-produzione-senza-accesso-db.md](analisi-diagnostica-produzione-senza-accesso-db.md) | Cita due presidi esistenti come precedenti per un check CI: stessa tecnica, altro scopo |
| [api.md](../api.md) | La convenzione dei codici errore e dell'envelope — il terreno su cui si misura **C2** |

---

*Analisi WIP — Presidi sul percorso storto (22 agosto 2026).*
