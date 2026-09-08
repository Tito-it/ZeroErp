# Brief — Il residuo che scavalca il rifiuto, e le bandiere che restano alzate

> **Tipo**: brief di difetti emersi in collaudo (DB + BE + FE) · **Data**: 2026-09-04 ·
> **Owner**: Tid · **Branch**: `dev/backend-tid`
>
> **Stato**: 🟢 **CHIUSO e archiviato il 2026-09-08** (decisione di Tid).
> D1+D2, D3, D4 e il §7 erano già chiusi la sera del 2026-09-04 — otto changeSet
> applicati, dettaglio in §10-bis. L'unica voce rimasta, **D5**, era una verifica
> a video: guardata il 2026-09-08 **nel codice e sul database**, e la sua ipotesi
> non regge (§6).
>
> | Difetto | Stato |
> | --- | --- |
> | **D1+D2** | ✅ **chiuso lato DB e lato BE**: il pull firma, la select filtra (-50, `EXECUTED` il 2026-09-04 22:45:58), c'è il presidio, e il backend consegna `context.lock_batch_id` al pull. ⚠️ La finestra in cui il -50 era applicato **senza** il BE — fatturazione a zero fatture e nessun errore — è durata dalle 22:45 alla release BE della stessa sera |
> | **D3** | ✅ **chiuso lato DB** (changeSet -47, -48, -49): il pannello porta l'elenco delle commesse respinte, e ognuna ha la sua riga con il suo motivo |
> | **D4** | ✅ **chiuso**: l'annullo chiude i task run con l'esito `ANNULLATO`. ⚠️ *«disattiva»* era il verbo sbagliato — corretto in §5 e §9.4 |
> | **D5** | ✅ **chiuso il 2026-09-08 — l'ipotesi è DISPROVATA**, e il difetto non c'è dove il §6 lo cercava: badge ed elenco leggono la stessa vista e coincidono, e il frontend **rifà** la fetch quando il badge è acceso. Dettaglio in §6 |
> | **§7** | ✅ chiuso: era la mirata, non un terzo difetto |
>
> ✅ **Le decisioni sono prese (Tid, 2026-09-04)**: il perimetro si consegna a
> monte; l'annullo abbassa la bandiera per esito; e il **badge del calendario
> resta sugli eventi**, con le commesse respinte nel dettaglio.
>
> 🔎 **Il brief è stato riletto contro il database vivo** (§11): D1, D2 e D3
> reggevano, **§7 si è chiuso**, e ⭐ la ri-adozione dei residui — che §9 dava
> per scontata — è stata verificata e regge **anche sulle righe sourceless**.
>
> **Da dove viene.** Eseguendo
> [collaudo-in-app-esito-parziale-pull-commessa.md](../work-in-progress/collaudo-in-app-esito-parziale-pull-commessa.md)
> — la voce **V1** del cantiere fan-out
> ([brief-be-fan-out-isolato-e-esito-parziale.md](../work-in-progress/brief-be-fan-out-isolato-e-esito-parziale.md)
> §13.1) — la **prova 1 è passata** e la **prova 2 è uscita rossa**, ma per una
> ragione che il copione non prevedeva: il lavoro della commessa **respinta** è
> finito in fattura lo stesso.
>
> ⭐ **La prova 2 non ha quindi misurato ciò che doveva misurare.** Il savepoint
> per-commessa non è stato né confermato né smentito: la materia era contaminata
> da righe residue di un giro precedente. Resta da rifare su materia pulita —
> **dopo** i difetti D1 e D2, altrimenti misura di nuovo il residuo.

---

## 0 · In una riga

Il pull sa rifiutare una commessa e lo scrive in tre posti, ma **il rifiuto non
decide niente**: il perimetro di ciò che verrà fatturato non è quello che il
pull consegna — è tutto ciò che si trova libero in `attivita_fatturabili` per
quella competenza. Una riga liberata da un giro disfatto è indistinguibile da
una appena prodotta, quindi la commessa respinta viene fatturata lo stesso. In
più, chi guarda il cruscotto **non può sapere quale** commessa è stata
rifiutata, e la segnalazione del mese **resta accesa** anche dopo che il lotto
è stato annullato.

---

## 1 · I fatti datati

Materia costruita apposta il 2026-09-04, competenza `2026-09`, tre commesse da
tre clienti diversi, tutte nate da push (quindi con la loro riga `ROOT`):

| Commessa | Ordine sorgente | Attività | Ruolo nel collaudo |
| --- | --- | --- | --- |
| 34136 | `ORD0036003` (ROOT) + `ORD0036006` (COLLEGATO) | 3 | sana, multi-sorgente |
| **34137** | `ORD0036005` | 1 | ⭐ **guastata** (ROOT → COLLEGATO, riga 17005) |
| 34138 | `ORD0036004` | 1 | sana |

Due giri, in quest'ordine:

| Ora | Lotto | Cosa è successo |
| --- | --- | --- |
| 17:18:08 | **10140** `LTF-0009180` | giro **senza guasto** (il guasto era finito per errore su 4277, una commessa di agosto fuori perimetro). Tre fatture, tutto `COMPLETATO`. Nascono le righe `attivita_fatturabili` **26828 · 26829 · 26830** |
| ~17:2x | — | il lotto 10140 viene **riportato in lavorazione**: le attività tornano `NON_EMESSA`, ⚠️ **le tre righe `attivita_fatturabili` restano** |
| 17:32:37 | **10141** `LTF-0009181` | giro **con il guasto su 34137**. Il pull rifiuta 34137 — e la fattura di 34137 nasce lo stesso |
| dopo | — | il lotto 10141 viene **annullato**: fatture cancellate, attività di nuovo `NON_EMESSA`, ⚠️ **le tre righe `attivita_fatturabili` restano ancora** |

---

## 2 · D1 🔴 · Il rifiuto per-commessa non arriva alla fattura

**Il fatto.** Sul lotto 10141 il pull ha rifiutato 34137 e lo ha scritto per
esteso:

```
task_run 2836 · pull_attivita_da_commessa · ERRORE · tentativo 1
error_code    E_PULL_COMMESSA
error_message Pull attivita' completato con 1 commesse su 3 in errore
meta          { totale: 3, ok: 2, falliti: 1, commesse_fallite: [34137] }

log di lotto 6613 · status 'C' (critica) · «Errore emissione commessa 34137»
```

E nello stesso lotto è nata la fattura **28785** (BA 173, Azienda ConTutto) con
la riga **14925** da 15,00 — cioè **il lavoro di 34137**. Insieme a questo,
`commesse_attivita 64556` è rimasta `NON_EMESSA`: lo stesso lavoro risultava
**fatturato e ancora da emettere**, che al giro successivo è un doppione.

**Perché succede.** Lo step `select_attivita` è un involucro sottile su
`vendite.fn_select_attivita_fatturabili`, che sceglie le righe di
`attivita_fatturabili` per **competenza, tipo documento, emittente, billing
account, utility** — cioè per *coordinate*, non per *provenienza*. Non chiede a
nessuno se il pull di quella commessa, in **questo** giro, sia andato a buon
fine. Le righe 26828/26829/26830 erano lì dal giro delle 17:18, libere e in
competenza: per lo step a valle erano lavoro legittimo come qualunque altro.

**Perché è un difetto di modello, non un caso di nicchia.** La pipeline
**dichiara** un esito parziale per commessa: `commesse_fallite` è una promessa,
e una promessa che non regge fino al documento non è una promessa. Il rollback
del savepoint protegge il pezzo che il pull ha scritto in **questo** giro — ma
il perimetro di ciò che verrà fatturato non è definito dal pull, è definito da
ciò che sta in tabella. Finché le due cose non coincidono, «commessa rifiutata»
e «commessa non fatturata» sono due affermazioni diverse.

⚠️ **E non dà nessun errore.** Il lotto è in ERRORE per il task del pull, ma la
fattura di troppo è una fattura normale: nessun codice, nessuna criticità sua.

---

## 3 · D2 🔴 · Una riga liberata è indistinguibile da una appena prodotta

⚠️ **Attenzione a non leggerlo come «il cleanup dimentica di cancellare».** Non
è così, e la prima stesura di questo brief lo diceva male. `fn_annulla_lotto_da_draft`
e `fn_riporta_lotto_a_draft` passano entrambe per `fn_cleanup_fatture_by_ids`,
che chiama `vendite.fn_libera_attivita_fatturabili`: le righe si **liberano**,
non si cancellano, ed è **giusto** — quel lavoro non è perso, è lavoro ancora da
fatturare, e cancellarlo sarebbe il difetto vero.

**Il fatto.** Le righe 26828 · 26829 · 26830 hanno `data_insert = 17:18:08`,
cioè il giro del lotto 10140. Sono sopravvissute a una **riapertura** e poi a un
**annullo**, e a oggi sono lì, correttamente liberate:

```
26828 | commessa 34136 | fattura_riga_id NULL | lock_in_fatturazione f
26829 | commessa 34137 | fattura_riga_id NULL | lock_in_fatturazione f
26830 | commessa 34138 | fattura_riga_id NULL | lock_in_fatturazione f
```

**Dov'è allora il difetto.** Nel fatto che una riga liberata **non porta nessuna
memoria di quale giro l'abbia prodotta**, e nessuno gliela chiede. Da lì in poi
è indistinguibile da una riga appena consegnata dal pull, e
`fn_select_attivita_fatturabili` la raccoglie per coordinate. Quindi:

⭐ **il perimetro di un giro oggi è «tutto ciò che è libero e in competenza»,
non «ciò che il pull ha consegnato»** — e finché è così, l'esito parziale del
pull è una scrittura sul registro senza effetto su ciò che viene fatturato.

D1 e D2 sono quindi **la stessa crepa vista da due lati**: il pull calcola un
perimetro (`ok` / `commesse_fallite`) e poi non lo consegna a nessuno; lo step a
valle ne ricostruisce uno suo, per coordinate, e i due divergono senza che
niente dia errore.

---

## 4 · D3 ✅ · Il cruscotto non diceva **quale** commessa è fallita

> ✅ **Chiuso lato DB il 2026-09-04** (changeSet -47, -48, -49). Il difetto resta
> descritto qui com'era; la forma con cui è stato chiuso — e perché non è quella
> prevista — sta in §10-bis.

**Il fatto.** Il dato esiste, in due posti (`task_run.meta.commesse_fallite` e
il log di lotto con `status = 'C'`), e **nessuna delle due superfici del
cruscotto lo pubblica**:

- `vendite.vw_dash_competenza_gruppi` — le righe del drill-down — ha 30 colonne
  e **nessuna** che porti l'esito di un giro. Il frontend non può disegnare quel
  che non riceve;
- `vendite.vw_dash_competenza_errori` — il pannello «errori vivi» — espone
  `lotto_id`, `lotto_codice`, `stato_lotto`, `task_code`, `error_code`,
  `messaggio` ed emittente. **Nessun `commessa_id`.** Il messaggio stesso lo
  ammette e rimanda altrove: *«dettaglio sui log di lotto»*.

**Perché è un difetto.** L'operatore legge «una su tre è fallita» e non ha modo
di sapere su quale riga agire senza aprire il lotto e leggersi il log. È un
difetto di **trasporto**, non di calcolo: la pipeline sa chi ha rifiutato, e lo
perde per strada verso la schermata da cui si lavora.

⚠️ **Sommato a D1 è peggio**: la riga di 34137 mostrava lavoro `DA_EMETTERE`
del tutto ordinario, mentre quel lavoro era già dentro una fattura DRAFT. Sulla
riga non c'era **nessun** indizio — né dell'errore, né della fattura.

---

## 5 · D4 ✅ · L'errore di un lotto annullato restava «vivo»

> ✅ **Chiuso il 2026-09-04** (changeSet -33). Il difetto resta descritto qui
> com'era: sotto, il verbo giusto e la ragione per cui non è `attivo = false`.

**Il fatto.** Dopo l'annullo del lotto 10141 la segnalazione sul calendario di
settembre è rimasta accesa. È **fedele al dato**: la CTE `task_err` di
`vw_dash_competenza_errori` prende i `task_run` in `ERRORE` con `attivo IS TRUE`
che non abbiano un tentativo successivo `COMPLETATO` dello stesso task — e
**non guarda lo stato del lotto**. Il run 2836 è ancora `ERRORE` e ancora
`attivo`, quindi l'evento resta:

```
TASK_ERRORE · lotto 10141 · LTF-0009181 · stato_lotto COMPLETATO
             · pull_attivita_da_commessa · E_PULL_COMMESSA
```

**Perché è un difetto.** La lista si chiama **errori vivi**. Un lotto annullato
non è più lavoro in corso: il suo errore è storia, non una cosa da rimediare.
Chi annulla deve abbassare la bandiera — disattivando il run, o chiudendolo con
un esito, o escludendo dalla vista i lotti che non sono più in lavorazione. Da
decidere quale delle tre, ma non «nessuna».

⭐ **Delle tre, la seconda: la sorella l'ha già scelta, e ha scritto perché**
(verificato il 2026-09-04). `fn_riporta_lotto_a_draft` chiude i run con
`fn_cancel_lotto_task_run` → `task_stato = 'ANNULLATO'`, e nel proprio corpo
respinge la prima:

> ⚠️ NON basta `attivo = false`: quella SELECT non filtra su `attivo`. La leva
> è l'**ESITO**, e la funzione per scriverlo esiste già.

Il dato lo conferma: gli otto run del lotto **10140**, riportato in lavorazione,
sono `task_stato = ANNULLATO` **con `attivo = t`**. E `task_err` filtra su
`task_stato = 'ERRORE'`, quindi cadono **per esito**, senza toccare la vista.
⇒ La terza strada — filtrare la vista sullo stato del lotto — resta possibile ma
non serve più, e la prima **non funzionerebbe**.

⚠️ **E `attivo` non va caricato di questa domanda.** Oggi risponde a *«questo è
il tentativo valido»*; usarlo anche per *«il lotto non è più in lavorazione»* è
un flag che risponde a due domande, e il giorno che dissentono non c'è scritto
da nessuna parte quale vince.

ℹ️ `fn_annulla_lotto_da_draft` **oggi non nomina mai i task run**: non c'è un
ramo da correggere, c'è un passo da aggiungere.

⚠️ **Come si rimisura questa vista, o si legge uno zero che non è un dato.**
`vw_dash_competenza_errori` apre con
`fn_get_emittenti_scope_sr_ids(current_setting('app.current_user_id'))`: senza
quella GUC la vista restituisce **zero righe** ed è **fail-closed**, non una
bandiera abbassata. Con il contesto impostato, al 2026-09-04 la riga del lotto
10141 **c'è ancora**.

---

## 6 · D5 ✅ · Lista vuota e calendario acceso — ipotesi DISPROVATA (2026-09-08)

**Il fatto riferito**: dopo l'annullo, il pannello degli errori si è svuotato
mentre il calendario continua a segnare l'errore.

**Cosa dice il database**: il conteggio mensile e la lista leggono **la stessa
vista** con lo stesso predicato, e a DB sono d'accordo — entrambi danno **1**
per `2026-09`. Quindi la divergenza non è nei dati: il pannello si azzera
(`erroriFetch.reset()` al cambio mese/refresh) e non rifà la fetch, restando
vuoto finché non lo si risollecita.

🩺 **Verifica**: ricarica la pagina e riseleziona settembre. Se la riga
riappare, è questo; se resta vuota con il badge acceso, allora è altro e va
guardato a parte.

### ✅ Verificato il 2026-09-08 — e l'ipotesi NON regge

⛔ **Il frontend la fetch la rifà.** Il pannello non è appeso a un `reset()`
solitario: lo governa un `watch([competenzaCorrente, mesi])` che, **ogni volta
che l'aggregata arriva** (`mesi` cambia identità a ogni `fetchMensile`), fa
`loadErrori()` se il conteggio è > 0 e `resetErrori()` solo se è **zero**.

⭐ E i due leggono **lo stesso numero**: il badge del mese e il predicato del
watch sono entrambi `nErroriMese`, cioè `meseCorrente.n_errori`. ⇒ «badge acceso
+ pannello vuoto per mancata fetch» è una combinazione che quel codice **non sa
produrre**.

⚠️ E nemmeno il database la produce. Misurato il 2026-09-08 nel contesto
operatore, confrontando l'aggregata del badge con l'elenco, mese per mese:

| Competenza | Badge | Elenco |
| --- | --- | --- |
| 2026-07 | 9 | **9** |
| 2026-09 | 1 | **1** |

Entrambi leggono `vendite.vw_dash_competenza_errori` — sono d'accordo per
costruzione, e lo sono di fatto.

⇒ **La voce si chiude come ipotesi disprovata, non come difetto risolto**: se il
sintomo si ripresenta, ⛔ non è la fetch mancante. Le strade restano due, e vanno
guardate in quest'ordine: una `loadErrori()` **fallita** (l'errore finisce in un
toast e la lista resta vuota, col badge acceso), oppure una vista **stantia** che
non ha rifatto l'aggregata al rientro. ⚠️ Il rimedio suggerito qui sopra —
ricaricare — le maschera entrambe senza distinguerle: è ciò che rende una
diagnosi sbagliata più costosa di nessuna diagnosi.

---

## 7 · ✅ CHIUSA · il gruppo ROOT di 34136 non è un difetto: era la mirata

Le attività **64553 e 64554** (ordine `ORD0036003`, sorgente **ROOT** di 34136)
non sono state pullate in **nessuno dei due giri**, pur essendo `APPROVATA` /
`NON_EMESSA` e con `tipo_doc_fiscale_id` valorizzato. Di 34136 passa solo il
gruppo del COLLEGATO (`ORD0036006`).

**La risposta sta in `vendite.fatturazione_lotti_gruppi`** (letto il
2026-09-04): i due lotti portano **esattamente tre gruppi**, e quello dell'ordine
ROOT non c'è in nessuno dei due.

```text
10140 · 17:18:08.010974   ORDINE_VENDITA:01a06ce5-…f136b8   (COLLEGATO di 34136)
                          ORDINE_VENDITA:01a06ce4-b46a-…    (34137)
                          ORDINE_VENDITA:01a06ce4-35a6-…    (34138)
10141 · 17:32:37.982875   gli stessi tre

assente in entrambi:      ORDINE_VENDITA:01a06cb9-8f47-73c4-aafb-ad0f24171e42
```

⭐ **Le righe dei gruppi nascono alla creazione del lotto** (`…08.010974`),
**prima** che il pull scriva (`…08.062578`): il perimetro era già deciso quando
il pull è partito. E sono gli stessi tre nei due giri — quindi «due volte su
due» è **una selezione ripetuta uguale**, non un difetto che si ripete.

**E non è che la lane lo nascondesse.** `fn_diagnostica_gruppi_fatturabili` su
quel gruppo risponde: commessa `PRONTA_FATTURAZIONE`, `commessa_emittibile = t`,
**2 righe, 2 pronte**, zero escluse per approvazione o competenza, e la **stessa
terna** del gruppo che è passato (`utility 5, tipo_doc 1, emittente 72`). Niente
lo escludeva: semplicemente non era nel perimetro scelto.

### ⛔ E non è un prerequisito di D1

Sembrerebbe: *«se il perimetro lo consegna il pull, un gruppo mai pullato diventa
lavoro non fatturabile in silenzio»*. **Non è così**, e la ragione è strutturale:
le attività 64553/64554 **non hanno mai prodotto una riga di
`attivita_fatturabili`** — per 34136 esiste solo la 26828, del gruppo COLLEGATO.
Non sono residui invisibili: sono lavoro che in fatturazione non è **mai
entrato**, che nemmeno oggi la select prenderebbe — legge solo `attivita_fatturabili` —
e che la lane continua a mostrare.

⇒ Il §7 si chiude scrivendo che era la mirata, e **non cambia l'ordine dei
lavori di §9**. ⚠️ Il presidio di §9 ha quindi un perimetro preciso: le **AF
esistenti e non marchiate**, non le commesse mai pullate.

---

## 8 · Cosa questo brief **non** dice

⛔ **Non dice che il savepoint per-commessa è rotto.** La prova 2 doveva
misurare *«una commessa rifiutata non si porta via il lavoro di quelle passate
prima»*, e su questo giro non l'ha misurato: le fatture nascevano da righe
preesistenti, non dal pull. La proprietà resta **asserita nei test e non
eseguita in applicazione** — che è la ragione per cui il collaudo esiste.

La prova 2 va rifatta su materia pulita, **dopo** D1 e D2.

---

## 9 · Proposta di lavoro

### La forma decisa per D1+D2 — il perimetro si consegna

**Il pull consegna, la select riceve.** Chi calcola il perimetro è lo stesso che
lo dichiara, così le due cose non possono divergere.

⛔ **Non è «cancellare le righe liberate»**: quel lavoro è ancora da fatturare, e
cancellarlo perderebbe lavoro vero.

**I tre pezzi, in forma concreta:**

1. `vendite.fn_emit_attivita_fatturabili_da_commessa` riceve **l'identità del
   giro** — oggi la sua firma è
   `(p_commessa_id, p_only_approved, p_dry_run, p_gruppi)` e **non ha nessun
   parametro di batch**: va aggiunto;
2. la funzione **marchia** con quell'identità le righe che accetta, **su
   entrambi i rami** — quello di `INSERT` e quello di `UPDATE`. Il ramo di
   update è quello che conta: è lì che passano i residui;
3. `vendite.fn_select_attivita_fatturabili` sceglie **per quel marchio**, non
   più per sole coordinate. Una commessa respinta non è marchiata, quindi non
   viene fatturata.

Il backend passa già il `lock_batch_id` del lotto a `select_attivita`
(`LottoContext`), quindi il valore da consegnare al pull ce l'ha in mano: la
modifica lato BE è il passaggio di un parametro.

✅ **L'incognita che questo brief lasciava aperta è chiusa: il pull ri-adotta i
residui.** Cerca la riga esistente per `(sorgente_tipo_id, sorgente_uid)` — dove
`sorgente_uid` è l'UUID deterministico ricavato da `segment_key` — e se la trova
la **aggiorna** invece di inserirne una nuova. Quindi marchiare sul ramo di
update è sufficiente: un residuo di un giro disfatto viene ripreso e rimarchiato
dal primo giro in cui quella commessa passa, e **niente lavoro va perso**.

⭐ **Verificato il 2026-09-04, ed è il punto dove il disegno poteva rompersi in
silenzio.** Sull'AF la sorgente è **sempre la commessa**: la ricerca è
`sorgente_tipo_id = COMMESSA AND sorgente_uid = md5(segment_key)`, mentre il
documento d'origine viaggia a parte in `sorgente_origine_tipo_id`. È l'unica
ragione per cui la ri-adozione tiene anche su **RETTIFICA e ONERE**, che sono
sourceless per progetto (`chk_commesse_attivita_sorgente_pair`: la coppia è
tutta-NULL o tutta-piena) — con una chiave costruita sul documento d'origine
quelle righe non si sarebbero mai ritrovate, e ogni giro avrebbe inserito un
doppione di nota di credito **senza un errore**.

### ✅ Tre cose da decidere prima di scrivere il codice — decise

> **Esito, 2026-09-04.** ① Colonna **nuova** (`emit_batch_id`), non
> `lock_batch_id` — fatto. ② Il canale `p_gruppi`: **scartato** a favore del
> marchio, che è per riga e non fa ricomporre una chiave al backend; qui sotto
> il confronto per intero. ③ Il presidio: **fatto**
> (`dbops.vw_af_senza_giro`). Il ragionamento resta perché è la ragione per cui
> quelle scelte sono quelle, non per rifarle.

**1 · La colonna del marchio va NOMINATA, e quella ovvia è già occupata.**
`attivita_fatturabili.lock_batch_id` **esiste già**: porta il batch del lotto, la
scrive `fn_select_attivita_fatturabili` e la **azzera**
`fn_libera_attivita_fatturabili`. La frase qui sopra — *«il backend il
`lock_batch_id` ce l'ha in mano»* — letta in fretta autorizza a riusare quella
colonna. Sarebbe lo stesso valore per **due domande con cicli di vita opposti**:
*chi ti ha consegnato* deve sopravvivere alla liberazione, *chi ti ha
lucchettato* deve morire con essa. ⇒ **Colonna nuova**, e scritto qui perché non
lo decida chi implementa.

**2 · Il canale del perimetro forse esiste già, e va detto perché non basta.**
`p_gruppi text[]` è parametro di **entrambe** le funzioni, e la select lo applica
già via `fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid,
ca.commessa_id)`. Se il pull restituisse i gruppi delle commesse **accettate** e
il BE li passasse alla select, D1 si chiuderebbe **senza toccare lo schema**: il
gruppo di 34137 non entrerebbe nell'elenco e il suo residuo non verrebbe
fatturato. Il marchio resta più fine — è per riga, e non fa ricomporre una chiave
al backend — ma una proposta che aggiunge una colonna e cambia due funzioni deve
**dire perché** il canale già in servizio non basta.

**3 · Manca il presidio, e il rimedio cambia il RUMORE del danno.** Oggi una riga
libera di troppo produce una fattura in più: **si vede**. Domani una riga che
nessun giro ri-marchia non viene fatturata, per sempre, **senza errore** — è lo
stesso «FATTO, 0 elaborate» che nessuno nota. ⇒ Serve una vista che deve restare
vuota: *attività fatturabili libere, in competenza, che nessun giro ha
marchiato*. Perimetro: le **AF esistenti** e non marchiate — non le commesse mai
pullate, che hanno già la lane (§7).

### ⚠️ Un punto minore, sulla stessa crepa

Il pull scrive `ok` / `totale` / `falliti` / `commesse_fallite` **solo quando
qualcosa fallisce**: il run in `ERRORE` li porta, i run `COMPLETATO` portano solo
`{"rollback": false}`. Quindi di un giro **riuscito** non si sa quante commesse
siano state accettate — lo si deduce dai gruppi del lotto, che sono il perimetro
**chiesto**, non quello **consegnato**. Con D1 che fa del perimetro consegnato la
cosa portante, quei contatori servono anche in caso di successo, o la promessa
resta verificabile **solo quando si rompe**.

⛔ **Non è una sovrascrittura, ed è stato controllato**:
`fn_set_runtime_task_run_esito` fa già `meta = COALESCE(meta,'{}') || v_meta`, e
infatti il `rollback` del pull riuscito è **sopravvissuto** all'annullo sul run
2828. Il payload non viene cancellato: non viene mai scritto.

### Il resto, in ordine

1. **D1+D2** nella forma qui sopra — è tutto dentro due funzioni SQL; il backend
   le avvolge e basta;
2. **rifare la prova 2** del collaudo: è l'unica che dice se il savepoint
   per-commessa regge;
3. **D3** — `commessa_id` (e codice) su `vw_dash_competenza_errori`; una colonna
   d'esito sulle righe del drill-down, così la riga rifiutata si riconosce a
   video. A cascata: riga BE, catalogo lista, colonna FE;
4. **D4 · simmetria** — `fn_annulla_lotto_da_draft` chiude i task run del lotto
   **con l'esito `ANNULLATO`**, per la via che la sorella usa già
   (`fn_cancel_lotto_task_run`, che infatti fa restituire a
   `fn_riporta_lotto_a_draft` il contatore `annullati_task_run`). Due sorelle non
   possono comportarsi diversamente sulla stessa cosa. La vista `task_err` non si
   tocca — e non serve toccarla, perché filtra su `task_stato`.
   ⛔ **Non `attivo = false`**: la sorella lo respinge nel proprio corpo, e non
   basterebbe (§5). Oggi `fn_annulla_lotto_da_draft` non nomina mai i task run:
   è un passo da aggiungere, non un ramo da correggere;
5. **D5** — verificare a video, e riclassificare. Il **§7 è chiuso** (era la
   mirata) e non richiede più niente.

ℹ️ Le tre righe 26828/26829/26830 **non vanno cancellate**: sono lavoro
legittimo da fatturare. Vanno però tenute presenti nel rifare il collaudo, o
riprodurranno D1 finché D1 non è chiuso.

---

## 10 · Come riprodurre

1. tre commesse su un mese, da tre clienti diversi, nate da push (§La materia
   del copione);
2. lancia un giro **senza guasto**: nascono le righe `attivita_fatturabili`;
3. **riporta il lotto in lavorazione** (o annullalo): le attività tornano
   `NON_EMESSA`, le righe `attivita_fatturabili` **restano**;
4. guasta una commessa (ROOT → COLLEGATO) e rilancia;
5. il task del pull chiude in `ERRORE` con quella commessa fra le
   `commesse_fallite` — **e la sua fattura c'è lo stesso**.

---

## 10-bis · Stato DB — costruito il 2026-09-04

> 🟡 **D4 è CHIUSO lato DB. D1+D2 è costruito a metà, e la metà che manca è
> volutamente ferma: aspetta il backend.**

| # | changeSet | Che cosa fa | Stato |
| --- | --- | --- | --- |
| 31 | `00_schema/vendite` · `alter-attivita-fatturabili-emit-batch` | la colonna `emit_batch_id`: il giro che ha **consegnato** la riga | ✅ applicato |
| 32 | `20_code/vendite` · `update-fn-emit-attivita-fatturabili-batch` | il pull prende `p_emit_batch_id` e **marchia su entrambi i rami** | ✅ applicato |
| 33 | `20_code/vendite` · `update-fn-annulla-lotto-da-draft-task-runs` | **D4**: l'annullo chiude i task run con l'esito `ANNULLATO` | ✅ applicato |
| 34 | `20_code/dbops` · `create-vw-af-senza-giro` | il presidio: lavoro libero che nessun giro rivendica | ✅ applicato |
| 35 | `90_end` · `grant-vw-af-senza-giro-app` | `SELECT` a `zeroerp_app` sul presidio | ✅ applicato |
| 47 | `20_code/vendite` · `update-vw-dash-competenza-errori-commesse` | **D3**: il pannello errori porta `commesse_fallite` e `n_commesse_fallite`, **a grana invariata** | ✅ applicato |
| 48 | `20_code/vendite` · `create-vw-dash-commesse-respinte` | **D3**: una riga per commessa respinta, con il suo motivo | ✅ applicato |
| 49 | `90_end` · `grant-vw-dash-commesse-respinte-app` | `SELECT` a `zeroerp_app` sulla vista nuova | ✅ applicato |
| 50 | `20_code/vendite` · `update-fn-select-attivita-perimetro` | **D1+D2**: la select sceglie per **marchio**, non piu' per sole coordinate | 🔴 **scritto, NON applicato** |

pgTAP: `test-af-emit-batch-marchio-v1.sql` (7/7),
`test-annulla-lotto-task-runs-v1.sql` (7/7) e
`test-vw-dash-commesse-respinte-v1.sql` (6/6), **nessuna asserzione saltata**.

### 🔴 L'ultimo passo è scritto, e va applicato CON il backend

**`fn_select_attivita_fatturabili` filtra per il marchio** (changeSet -50).
Da quel momento un giro fattura **solo** ciò che il proprio pull ha consegnato,
e il rifiuto per-commessa decide davvero.

> 🔴🔴 **Applicarlo ferma la fatturazione finché il backend non passa il
> `lock_batch_id` del lotto al pull.** Nessuna riga è marchiata ⇒ la select non
> trova niente ⇒ il giro chiude con **zero fatture, senza errore** — «zero righe
> eleggibili» è un esito legittimo.

⭐ **Decisione di Tid, 2026-09-04, presa sapendolo.** La forma con l'interruttore
(`p_solo_marchiate`, applicabile subito e inerte) è stata **scartata**: avrebbe
reso la correttezza *opt-in* e lasciato in casa un'impalcatura da togliere.
Meglio una fatturazione ferma e visibile che un perimetro facoltativo.

⭐ **E così non si può dimenticare.** Non c'è nessun parametro nuovo: chi
lucchetta è già obbligato a dichiarare il proprio giro (il guard pretende
`p_lock_batch_id` quando `p_lock`), e da adesso **dichiarare il giro significa
prendersene il perimetro** — sono lo stesso parametro, non possono divergere.

⚠️ La condizione è sulla **presenza del giro**, non su `p_lock`: così
un'anteprima che dichiara il proprio giro vede *esattamente* ciò che il giro
vero prenderà. Una chiamata senza giro resta senza filtro — non lucchetta, non
fattura, non può fare danni.

⇒ **Lo sblocco lato BE è una riga**, e il valore è già in `LottoContext`.

### ⚠️ Il registro del debito è già leggibile

`dbops.vw_af_senza_giro` al 2026-09-04 elenca **5 righe** — lavoro libero, in
competenza, che nessun giro rivendica; fra queste le tre del collaudo
(26828/26829/26830). ⭐ È un **fatto datato, non un motivo**: cala da sé quando
il pull ri-adotta quelle righe, e ciò che resta dopo qualche giro è la domanda
vera.

### ✅ D3, la metà DB — costruita, e in una forma diversa da quella prevista

Il brief prevedeva `commessa_id` su `vw_dash_competenza_errori` e una colonna
d'esito su `vw_dash_competenza_gruppi`. La prima è stata fatta; **la seconda no,
ed è stata sostituita** — la ragione è nel riquadro più sotto.

⚠️ **E dentro c'è una decisione che questo brief non scioglie.** Il difetto è
descritto come *«manca `commessa_id`»*, ma l'unità del fallimento **non è una
commessa: è un elenco**. Il pull scrive

```text
meta  { totale: 3, ok: 2, falliti: 1, commesse_fallite: [34137] }
```

e la vista ha **una riga per errore di task**. Quindi «aggiungere `commessa_id`»
si può fare in due modi, e non sono equivalenti:

| Forma | Cosa comporta |
| --- | --- |
| una colonna **array/jsonb** `commesse_fallite` | la riga resta una; il frontend deve saper mostrare N codici in una cella |
| **fan-out**: una riga per commessa fallita | si legge meglio, ⛔ ma il **conteggio** degli errori vivi smette di contare i giri e comincia a contare le commesse — e quel conteggio è il badge del calendario |

⚠️ **E il fan-out non cambia niente finché a fallire è una commessa sola.** Sul
giro del collaudo `commesse_fallite` ha **un** elemento (`falliti = 1`; il `3` è
`totale`, cioè le commesse *processate*): una riga prima, una riga dopo. Il
conteggio si sposta solo quando in **uno stesso giro** ne fallisce più d'una —
caso che il modello ammette per costruzione, `falliti` può arrivare a `totale`.

### ⛔ E «mostrare la prima» non è una scelta di visualizzazione

Sembrerebbe la via d'uscita: una riga per giro, con dentro **la prima** commessa
fallita. ⛔ Ma qui **non c'è nessuna sequenza, e nessun colpevole**. Il savepoint
per-commessa esiste apposta perché ogni commessa fallisca **da sola**: la prima
non ha causato le altre, e le altre possono essere fallite per motivi diversi.
«La prima» è solo l'`id` più basso.

⇒ Mostrarla da sola nasconde le altre **in silenzio**, ed è la stessa forma del
difetto che questo brief racconta: la superficie dice meno di quanto il dato
sappia. L'operatore ripara 34137, rilancia, e il giro fallisce di nuovo su una
commessa che nell'elenco non c'era mai stata.

### ⭐⭐ Il requisito vero (Tid, 2026-09-04) e la sorgente che già lo serve

**Decisione di Tid:** *«le commesse in errore devono vedersi tutte, e ognuna
mostrare il problema, per poter cercare di risolvere»*. (L'idea di «mostrare il
primo» valeva per **più errori sulla stessa attività** — un caso diverso, che
qui non si presenta.)

⭐ **Quel dato esiste già, per commessa, e non è il `meta` del task.** È in
`vendite.fatturazione_lotti_log`: una riga per commessa fallita, `status = 'C'`,
con il `commessa_id` in un campo **strutturato** — non solo dentro la frase:

```text
id 6613 · messaggio  «Errore emissione commessa 34137»
          status     C
          meta       { error_code: 'E_PULL_COMMESSA',
                       context: { task: 'pull_attivita_da_commessa',
                                  commessa_id: 34137 },
                       detail:  'ROOT source mancante per commessa 34137 …' }
```

⇒ **D3 si costruisce su questa sorgente**, e il dilemma array-contro-fan-out si
scioglie da sé: il log è **già** per commessa, e ogni riga porta la propria
causa. Non serve nessun cambio al `meta`.

### ⛔ E la sorgente da NON usare è proprio `commesse_fallite`

`pipeline_step_executor` scrive nel meta `[e.item for e in esito.errori][:5]`.
**Tronca a cinque**, e lo dichiara: *«il meta è una traccia per il cockpit, il
dettaglio completo sta sui log di lotto»*. Costruirci sopra la vista
significherebbe che con **sei** commesse fallite l'operatore ne vede cinque —
e la sesta sparisce senza che niente lo dica. È il difetto di questo brief in
miniatura: una superficie che dice meno di quanto il dato sappia.

### ⚠️ Il buco che resta, ed è lato BE

Il log risponde a *«quale commessa»* con un campo pulito, ma a *«quale
problema»* risponde solo dentro `meta.detail`, che oggi è un **dump tecnico**:
messaggio Python, `DETAIL`, `HINT`, `CONTEXT` e lo stack PL/pgSQL, tutto in una
stringa. Il `messaggio` della riga dice *quale* commessa, non *perché*.

⇒ Perché «ognuna mostri il problema» sia vero **a video**, il motivo di dominio
— qui *«ROOT source mancante per commessa 34137»* — deve arrivare in un campo
suo, invece di essere sepolto nel dump. È una riga in `_messaggio_pull` /
`item_failed`, ed è lavoro di backend: il database può esporre solo ciò che
riceve.

### ✅ Deciso (Tid, 2026-09-04): il badge resta sui giri, le commesse nel dettaglio

Il conteggio del calendario continua a contare **gli eventi** — «quante volte
devo aprire un lotto» — e le commesse vivono nel dettaglio, dove la domanda
«su cosa agisco» ha senso. ⚠️ La vista somma già **due** unità (`TASK_ERRORE`
per (lotto × task) e `FATTURA_CRITICA` per fattura): una terza avrebbe reso il
totale la somma di tre cose diverse, e «4» avrebbe voluto dire «2 task + 1
fattura + 1 commessa».

⇒ Per questo il **-47** aggiunge le colonne **in coda** e non tocca la grana.

### ⛔ E la colonna su `vw_dash_competenza_gruppi` è stata SOSTITUITA da una vista

La strada prevista era `respinta_il` sulle righe del drill-down. L'apply
funziona; **il rollback no**, e la prova l'ha mostrato prima che il changeSet
esistesse:

```text
ERRORE: non è possibile eliminare colonne da una vista
```

Una vista non perde colonne con `CREATE OR REPLACE`: per tornare indietro
servirebbe un `DROP`. E da `vw_dash_competenza_gruppi` **dipende**
`vw_dash_competenza_gruppi_riepilogo`, quindi il `DROP` andrebbe in `CASCADE` e
il rollback dovrebbe **ricreare anche il riepilogo da una copia congelata**.

⛔ Cioè: per potersi ritirare, il changeSet avrebbe piantato in casa una copia
della vista di qualcun altro, che invecchia in silenzio dal giorno dopo. *Un
rollback che introduce un debito è peggio di un rollback assente.*

⭐ **Sostituita da `vendite.vw_dash_commesse_respinte`** (changeSet -48): una
riga per commessa respinta, con codice, `error_code`, messaggio, dettaglio e
quando. Nessun dipendente, si ritira con un `DROP`, e nasce già nella grana che
una lista sa mostrare. ℹ️ Il drill-down mostra la bandiera con un **join** a
questa vista: una riga di backend, senza toccare una vista da 30 colonne.

⇒ Non resta nessuna decisione aperta su D3 lato DB.

### Cosa resta, e a chi tocca

#### Lato DB

- ✅ **D3** — fatto e applicato (changeSet -47, -48, -49);
- 🔴 **il filtro nella select** — scritto **e APPLICATO** (changeSet -50,
  `EXECUTED` il 2026-09-04 22:45:58). L'intenzione era di applicarlo insieme
  alla release BE; è entrato prima, quindi **la finestra è aperta adesso**: il
  pull scrive `emit_batch_id` NULL (il BE non gli passa niente), la select
  filtra su quel marchio e non trova nulla ⇒ **zero fatture e nessun errore**,
  esattamente il rumore silenzioso che il presidio `vw_af_senza_giro` esiste per
  rendere visibile. ⇒ Lato DB non resta altro: **si chiude dal BE**, e va fatto
  subito.

#### Lato BE — ✅ fatto il 2026-09-04 sera (2793 test verdi)

- ✅ **il `lock_batch_id` del lotto arriva al pull.**
  `CommesseRepository.emit_attivita_fatturabili` ha ora `emit_batch_id`, e
  `_handle_pull_attivita_da_commessa_task` gli passa `context.lock_batch_id`.
  È la riga che riapre la fatturazione dopo il -50.
  ⛔ Presidiata da un test suo (`test_pull_consegna_al_db_l_identita_del_giro`)
  e non lasciata agli esiti: una regressione qui non solleva niente — emette
  zero fatture. Nessun altro test del file guarda gli **argomenti**;
- ✅ **i contatori si scrivono anche quando il giro riesce.** Nuovo
  `TaskEsitoOk`: il task_run chiude in `COMPLETATO` come sempre, ma il `meta`
  porta `totale`/`ok`/`falliti`. Il DB fonde (`meta || v_meta`), quindi
  `rollback` resta. ⭐ Serviva proprio per il caso che il perimetro consegnato
  rende possibile: «ok: 0 su 3» si legge, invece di doverlo dedurre da un
  COMPLETATO muto;
- ✅ **il motivo di dominio è fuori dal dump.** `_PullCommesseRunLogger.item_failed`
  scrive in `detail` — cioè in ciò che `vw_dash_commesse_respinte` mostra come
  `dettaglio` — il motivo letto da `diagnostica_db` (`message_detail`, poi
  `message_primary`), con ripiego sul messaggio normalizzato del BB per gli
  errori nati in Python. Il dump non si perde: va in
  `context.dettaglio_tecnico`;
- ✅ **gli endpoint.** `list_dash_competenza_errori` porta `commesse_fallite` e
  `n_commesse_fallite` **in coda** (il mapping è per indice: in mezzo
  sposterebbe tutto in silenzio); `list_dash_competenza_gruppi` ha la LATERAL su
  `vw_dash_commesse_respinte` con `respinta_il` / `respinta_motivo`, legata al
  **mese della riga** e con `LIMIT 1` — senza, una commessa respinta due volte
  duplicherebbe la riga del gruppo e falserebbe il conteggio della lista.

⚠️ **Due presidi esistenti sono stati corretti, non aggirati**: la guardia di
larghezza della lista gruppi contava le sole colonne `g.` e sarebbe rimasta
verde-e-sbagliata con la LATERAL (ora conta anche `resp.`), e
`assertNotIn("LATERAL")` vietava la parola mentre la regola da presidiare è che
l'id del documento non torni a essere risolto una seconda volta lì — ora dice
proprio quello. Aggiunta la guardia gemella sulla lista errori, che non l'aveva.

#### 🔴 Tre difetti trovati rivedendo il codice appena scritto (2026-09-04, tarda sera)

La suite era **verde su tutti e tre**. Vale la pena leggerli perché sono, uno per
uno, un esemplare della famiglia di questo cantiere: *difetti che non danno
errore*.

**1 · La `LATERAL` costava 41 volte tanto.** La bandiera del §D3 era nata come
`LEFT JOIN LATERAL` dentro la proiezione della lista gruppi — la forma ovvia. Ma
`query_paged_view` **materializza** la CTE per contare il totale, quindi la
LATERAL si valutava su **tutto il perimetro del mese** e non sulla pagina.
Misurato su `2026-06` (48 gruppi): **27 ms senza, 1073 ms con**, e in crescita
con lo storico perché la chiave del join esce da un `jsonb`
(`meta->'context'->>'commessa_id'`) che nessun indice copre.
⇒ Sostituita da **una seconda lettura** ristretta agli id della sola pagina
(`_applica_bandiera_respinta`, `DISTINCT ON` per prendere l'ultimo rifiuto):
**0,4 ms**. Nessun test lo avrebbe mai detto — misuravano il risultato, non il
costo.

**2 · Il `jsonb` arrivava al frontend come STRINGA.** `commesse_fallite` era
mappato con `row[15] or []`: Django/psycopg 3 in questa configurazione **non
decodifica** il jsonb fuori dall'ORM, quindi l'endpoint restituiva
`"[{...}]"` invece di un array — nessun errore, una lista che non si può
ciclare. La suite era verde perché il finto consegnava già una lista.
⇒ Corretto con il BB `jsonb_out`, e **il finto ora consegna una stringa**, cioè
la forma che il driver produce davvero. ⭐ Trovato solo da uno **smoke sul
database vero**.

**3 · Il motivo di dominio veniva letto dal campo sbagliato.**
`_motivo_dominio` preferiva `message_detail`. Facendo fallire davvero il pull
sulla commessa 34137 si legge invece:

```text
message_primary → «Indicare un valore per ROOT source mancante per commessa
                   34137. Dato obbligatorio.»        ← il motivo
message_detail  → «Non è stato assegnato un valore all'informazione
                   richiesta.»                       ← il testo della POLICY
```

`fn_log_and_raise_error` compone il **messaggio** con il dettaglio di dominio;
`DETAIL` e `HINT` portano il testo generico dell'errore, identico per ogni
`E_VALORE_MANCANTE` del sistema. A video sarebbe finita la frase inutile.
⇒ Ordine invertito (`messaggio` prima di `detail`), e **il finto corretto**: la
prima stesura metteva il motivo in `DETAIL`, cioè in un posto in cui il sistema
non lo mette — la trappola che `apps/core/tests/db_error_fakes` dichiara nel
proprio docstring.

#### Due cose aggiunte nella stessa revisione

- ⛔ **un giro senza identità non parte.** Se `context.lock_batch_id` è assente,
  il pull si ferma con `E_PIPELINE_SCOPE_INCOMPLETE` (codice esistente, policy
  già a catalogo) invece di firmare NULL e far nascere un lotto vuoto senza
  errore. Fra un giro che non parte e un giro che non emette niente in silenzio,
  il primo è l'unico recuperabile;
- ♻️ **tolta una terza copia** della decodifica jsonb in
  `vendite_repository` (una funzioncina locale `_dati` che rifaceva `jsonb_out`).

🔎 **Resta da provare in applicazione**: il giro di fatturazione su `2026-09`.
Il backend di sviluppo è stato ricaricato (`kill -HUP` sul master gunicorn).

#### Documentazione API aggiornata

[api_dashboard_competenza.md](../../backend/vendite/manual/api_dashboard_competenza.md)
porta ora i due blocchi nuovi: `respinta_il` / `respinta_motivo` sulla lista
gruppi (con la ragione per cui **non** sono colonne della vista, quindi non
ordinabili né esportabili) e `commesse_fallite` / `n_commesse_fallite` sulla
lista errori, con l'esempio di payload e l'avvertenza di **non sommarle** al
badge del calendario.

#### Lato FE

- **D5** — ricaricare la pagina e riselezionare il mese, poi riclassificare: se
  la riga riappare è il `reset()` del pannello, se resta vuota col badge acceso
  è altro (§6);
- quando D3 avrà la sua forma: la colonna a video e la voce nel **catalogo
  lista**. ⚠️ Una colonna di lista con `campo_sorgente` nasce `attivo = false`
  finché il BE non la proietta: va seminata spenta e accesa dopo.

#### Collaudo

- **rifare la prova 2** su materia pulita — è l'unica che dice se il savepoint
  per-commessa regge, e va fatta **dopo** che il filtro della select è attivo, o
  misura di nuovo il residuo.

---

## 11 · Verifiche lato DB — 2026-09-04

Il brief è stato riletto contro il **database vivo** e i **corpi delle funzioni**
subito dopo il push. ⚠️ Sono letture di **struttura** (firme, predicati, corpi,
definizione di vista) più alcune **istantanee datate** sulla materia del
collaudo: le prime dicono che cosa il progetto ammette, le seconde portano
controesempi. Nessuna delle due decide la forma di §9.

### Che cosa regge, verificato

| Affermazione del brief | Esito |
| --- | --- |
| `fn_select_attivita_fatturabili` sceglie per **coordinate** | ✅ i predicati sono `approvato`, `fatturato`, `sospesa`, `lock_in_fatturazione`, `posticipa_al`, `competenza_mese`, `tipo_doc_fiscale_id` più i facoltativi. **Nessun predicato di provenienza** |
| `fn_emit_attivita_fatturabili_da_commessa` non ha parametro di batch | ✅ firma `(p_commessa_id, p_only_approved, p_dry_run, p_gruppi)` |
| le righe liberate **non si cancellano** | ✅ `fn_libera_attivita_fatturabili` azzera lucchetto, `lock_batch_id`, `fattura_riga_id`, `stato_esecuzione`, e riporta le `commesse_attivita` a `NON_EMESSA` |
| il pull **ri-adotta** i residui | ✅ e tiene anche sulle righe sourceless — §9 |
| D3: il cruscotto non porta la commessa fallita | ✅ `vw_dash_competenza_errori` ha **15 colonne** e **nessuna** che nomini la commessa; `vw_dash_competenza_gruppi` ne ha **30**, nessuna d'esito |
| le tre righe residue sono ancora lì | ✅ 26828/26829/26830, libere, `lock_batch_id` NULL, `data_insert` 17:18:08 |
| l'errore del lotto annullato è ancora vivo | ✅ run 2836 `ERRORE` + `attivo = t`, e la vista lo restituisce ancora per `2026-09` |

### Che cosa è stato corretto

| Diceva | Verificato |
| --- | --- |
| D4: *«`fn_annulla_lotto_da_draft` **disattiva** i task run, come già fa la sorella»* | la sorella **non disattiva**: scrive l'**esito** `ANNULLATO`, e nel proprio corpo respinge `attivo = false` perché quella SELECT non filtra su `attivo`. Implementare «disattiva» alla lettera produce un **terzo** comportamento (§5, §9.4) |
| §7: *«da chiarire, se non è la mirata è un terzo difetto»* | **era la mirata**: i gruppi del lotto sono tre in entrambi i giri e quello ROOT non c'è; le righe di gruppo nascono **prima** del pull. §7 chiuso |
| §7 come possibile prerequisito di D1 | **non lo è**: quelle attività non hanno mai prodotto una riga di `attivita_fatturabili`, quindi nemmeno oggi la select le prenderebbe |
| §9: *«il BE il `lock_batch_id` ce l'ha in mano»* | vero, ma quella colonna **esiste già** con un altro significato e un ciclo di vita opposto: il marchio vuole una **colonna nuova** (§9.1) |

### ⚠️ Come si rimisura, per non leggere uno zero al posto di un dato

`vw_dash_competenza_errori` apre con
`fn_get_emittenti_scope_sr_ids(current_setting('app.current_user_id'))`: senza
quella GUC restituisce **zero righe**, ed è **fail-closed**. Chi la interroga da
`psql` senza contesto conclude che la bandiera è stata abbassata. Con il contesto
impostato, al 2026-09-04 la riga c'è ancora.

⛔ **E nessuno dei numeri qui sopra è un motivo.** «Le righe residue sono tre» e
«il run è ancora attivo» sono **controesempi**: dicono che un caso esiste e non è
gestito. La forma di §9 sta in piedi anche se domani quelle righe sono zero.
