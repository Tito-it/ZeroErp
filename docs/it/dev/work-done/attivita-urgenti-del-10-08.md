# Attività urgenti — 10-08-2026

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-10.
> **A chi:** a chi riprende il lavoro, e al BE per il §2.
> **Perché esiste:** chiudendo il rilievo in-app sulle vie d'uscita per l'operatore
> sono emerse due cose che non stanno in quel perimetro. Una è **un controllo che
> non ha mai funzionato**; l'altra è **una richiesta nuova del BE** che nasce da una
> decisione di dominio già presa. Sono scritte qui perché si riparta da un documento
> e non dalla memoria.
>
> **Stato:** ✅ **tutto chiuso al 2026-08-15 — §1, §2 e §3, DB e video.** I blocchi
> in testa a ciascuna sezione dicono cosa è stato fatto e cosa è stato misurato. Il
> §3 era una slice nuova, misurata l'11-08 su conferma del BE, che non era in questo
> documento quando è nato: ora è migrata e tradotta come le altre. Resta fuori il
> solo `lotto`, **dichiarato** e non dimenticato (§4.2), e le voci del §12.6 del
> brief. Il consuntivo del §0 è la fotografia buona.
>
> 📁 **Spostato in `work-done/` il 2026-08-15.** Le due voci del §0.3 restano aperte
> ma **non sono di questo cantiere**: una è una decisione di dominio (il documento
> fiscale) e una è una slice congiunta DB+BE (la rinomina). Vivono nel
> [§12.6 del brief](brief-db-vie-uscita-operatore.md#126-cosa-resta-aperto-dichiarato),
> che è la loro sede.
>
> ⚠️ **Il nome di questo file diceva `11-08` fino a poco fa, ed era sbagliato.**
> Lo scrivo perché quella data ha già portato fuori strada una volta: il changeSet
> del §1 era stato numerato `20260811-01` e ha dovuto essere rinumerato `20260810-03`
> per rientrare nella sequenza globale del giorno giusto.

---

## 0. Consuntivo — applicato, verificato, committato

| Cosa | Stato |
| --- | --- |
| `20260810-01` / `-02` (§1 del rilievo: reason `stato_chiuso` e `annullato`) | ✅ `EXECUTED` |
| 7 celle `meta` nei tre CSV `stati_doc_*` (§2 del rilievo) | ✅ applicate (loader `RERAN`) |
| `20260810-03` (§1 di questo documento: MOTIVO 1 mai scattato) | ✅ `EXECUTED` |
| `20260810-04` / `-05` / `-06` (§2: nota sempre esposta + `stato_info_key`) | ✅ `EXECUTED` |
| `20260811-01` … `-04` (§3: i quattro domini muti) + 9 celle di seed | ✅ `EXECUTED` |
| `20260815-01` (§1: il DDT annullato non blocca l'ordine) | ✅ `EXECUTED` |
| `test-capability-motivi-e-nessuna-azione-v1.sql` | ✅ 9 → **13 test**, tutti verdi come applicazione. Test 1 esteso da 3 a **7 domini** (19 stati chiusi) |
| `test-transizioni-uscita-manuale-v1.sql` | ✅ punto cieco dichiarato (solo commenti) |
| Baseline pgTAP dopo ogni passo | ✅ `script`, `config`, `vendite` — **nessuna regressione** |
| Doc auto-gen | ✅ rigenerate: riflettono il vivo |
| Commit | ✅ `114ba076b`, `6afc20993` (§12 al BE), `2d44dcb13` (§12.5-bis), `6e427423b` (§3 misurata), `b5d501088` (la slice). ⏳ Il §1 di oggi e questi aggiornamenti sono **da committare** |

✅ **La metà a video del §1-§2 è arrivata**, ed è fuori da questa tabella perché è
lavoro FE: rinomina `nessuna_azione_key` → `stato_info_key` su 8 drawer +
`DrawerActionsBar`, **10 chiavi i18n** it/en (le 3 dei motivi + le 7 delle note di
stato), `frontend-standards.md` e `catalogo-building-block-frontend.md` aggiornati
con la **semantica** nuova e non col solo nome. Build FE verde, `check_i18n_keys.py`
verde, suite backend 3644 verdi. **Verificato in app da Tid** su `PRV0000192`
(EVASO): i due motivi non mentono più **e** la nota di stato compare accanto ai
pulsanti — le due anomalie sono chiuse nel
[documento di test](test-be-vie-uscita-operatore.md).

✅ **La seconda tornata a video è arrivata** (2026-08-15): le **9 chiavi i18n** del
§3 sono tradotte it/en, `check_i18n_keys.py` è verde, build FE verde, suite backend
3635 verdi. Lato BE **non serviva nulla**: i `call_jsonb_fn` dei sei repository
passano il blob intero, il campo viaggia opaco. Lato FE nemmeno il cablaggio: tutti
e otto i drawer leggevano già `stato_info_key`, e la trappola del
`v-if="drawerActions.length"` non c'era in nessuno dei quattro domini nuovi
(`CommessaGestioneDrawer` la aveva già estesa alla chiave).

⚠️ **Il presidio però era cieco su commessa, e per la terza volta nella stessa
forma.** `check_i18n_keys.py` ammetteva i soli CSV `transizioni_stati_*` e
`stati_doc_*`: la tabella degli stati della commessa è `vendite.stati_commessa`,
senza il segmento `doc`, quindi le sue due chiavi non comparivano fra le mancanti —
il guard segnalava **7 chiavi, non 9**, e sarebbe tornato verde lasciando due note
mute a video. Il filtro per nome file è caduto: ora si scandisce ogni CSV di
`80_data/sql` e decide il contenuto. Il guard vede **100 chiavi emesse dal DB**,
erano 98.

✅ **E il migrate di `20260811-01`…`-04` è passato**: la slice del §3 è viva. Le
nove note sono tradotte **e** la funzione le emette — la catena è chiusa da capo a
fondo su tutti e quattro i domini.

✅ **E il gemello sui DDT è chiuso** (2026-08-15, `20260815-01`, migrato e baseline
verde): un DDT figlio annullato non blocca più l'annullamento dell'ordine. Era l'unica
delle voci aperte che fosse già decisa nel merito — la regola era scritta da noi sul
preventivo — e **zero lavoro BE**: nessun codice errore nuovo, nessuna chiave nuova.
Dettaglio e presidio (test 13) nel §1.

---

### 0.1 Il dubbio sul `meta` dei contratti — chiuso, e vale la pena sapere perché

Sviluppando la parte FE il BE ha sollevato un dubbio: la doc manuale di
`config.stati_doc_contratti` diceva che il `meta` di quella tabella è gestito **solo
da UPDATE SQL dedicati** (`20260430-61`, `20260520-10`) e **non** da
`loadUpdateData`, «per evitare sovrascritture» — quindi le due note del contratto
sarebbero rimaste nel CSV senza arrivare mai al DB, invisibili al test in-app senza
che nulla diventasse rosso.

🟢 **Verificato dal DB, e la risposta è no: il mirror carica `meta`.** Misurato su
tre piani, non dedotto — perché sul solo DB di sviluppo si misura una macchina e non
la riproducibilità:

| Piano | Esito |
| --- | --- |
| Il valore **vivo** | `config.stati_doc_contratti` ha le due note in tabella: CESSATO → `vendite.contratti.stato_info.cessato`, ANNULLATO → `…annullato` |
| La **funzione** | `fn_available_actions_contratto` non legge più `outgoing_action` |
| L'**ordine in timeline** | i quattro attori, uno per uno (sotto) |

| changeSet | `runOnChange` | carica `meta` |
| --- | --- | --- |
| `20260430-61` (UPDATE SQL) | `false` | no |
| `20260520-08` (mirror originale) | `true` | **sì** |
| `20260520-10` (UPDATE SQL) | `false` | no |
| `20260806-14` (mirror ri-ancorato) | `true` | **sì** |

`20260806-14` è l'ultimo e ri-esegue a ogni migrate: **il CSV vince sia su dev sia
su un database ricostruito da zero.**

⚠️ **Il timore era fondato come classe di rischio, e non a caso: quella tabella ha
avuto esattamente quel difetto.** I due UPDATE scrivevano `meta` *dopo* il mirror,
quindi su dev vinceva il CSV (il mirror ri-esegue) e su un DB da zero vincevano loro
— due macchine su due versioni della stessa tabella. Chiuso il **2026-08-06** con
`20260806-14`, cinque giorni prima di questo cantiere, e i due SQL sono stati spenti.
Quello che tornava in vita in CI era il blocco `meta.outgoing_action` con le chiavi
i18n **vecchie** (`contratti.azione_*`): un campo morto dal 2026-05-28, ripiego di
quando i contratti non avevano una tabella di transizioni — nata quel giorno con
`20260528-04`, e la funzione è passata a leggere quella con `20260528-05`.

> **La cosa utile non è stato il dubbio, è che a farlo venire è stata la doc.**
> Era stale di due generazioni. Corretta in
> [`stati_doc_contratti.md`](../../dbzero/config/manual/stati_doc_contratti.md)
> lasciando la frase vecchia citata e **barrata** col perché: il dubbio tornerà a
> qualcun altro, e deve trovare la risposta invece della domanda.

---

### 0.2 🔴 Una correzione di METODO che riguarda tutto il documento

Il 2026-08-15 Tid ha corretto un modo di ragionare che attraversa queste pagine:
**i dati del database di sviluppo sono di TEST**, e contarli non dice niente su quanto
un difetto valga in esercizio.

Dove qui si legge «oggi non morde», «zero documenti», «parte a valore più basso», il
**giudizio è da rifare**: erano affermazioni sul contenuto di una macchina, e hanno
portato a declassare due difetti certi — il gemello DDT (chiuso oggi) e il documento
fiscale (§4.2, ora la voce più pesante). La domanda giusta è **«può succedere?»**, non
«è successo?».

⚠️ Resta invece legittimo, e va tenuto, misurare **quale forma scrive chi scrive**
(dice se un ramo è *strutturalmente* raggiungibile: è una proprietà del modello, non
del volume) e **dichiarare cosa un test non ha coperto** («questo verde non ha misurato
niente»). Quello che non si fa è dedurne una priorità. La distinzione, in tabella, è in
testa al [§12.6 del brief](brief-db-vie-uscita-operatore.md#126-cosa-resta-aperto-dichiarato).

⚠️ Le intestazioni dei changeSet `20260811-01`…`-04` portano ancora la formulazione
vecchia sul `lotto`. **Non si correggono**: sono mergiati e pushati, e riscriverle
romperebbe i checksum Liquibase. La correzione vive qui e nel brief.

---

### 0.3 Cosa resta

| Voce | Chi decide / chi fa |
| --- | --- |
| Il **documento fiscale** non ha governo dello stato: nessuna `fn_available_actions_fattura`, tre transizioni manuali dichiarate nel seed che nessuno legge, e il `lotto` muto di conseguenza | decisione di dominio, poi cantiere DB (e BE/FE a valle). §4.2 e §13.3-bis del brief |
| La rinomina di `meta.nessuna_azione_key` → `stato_info_key` | slice congiunta DB+BE: una riga di `_PROP_KEY` **nello stesso commit**, o il guard diventa verde per cecità |

✅ **Il fix del guard i18n è arrivato** (§12.5-bis del brief): il BE ha chiuso
**entrambe** le metà — la chiave presente con **valore vuoto** non passa più per
tradotta, e il messaggio non tratta più le due lingue come simmetriche («una che manca
dall'italiano non ha rete e mostra la CHIAVE GREZZA all'operatore»). Verificato
leggendo lo script, non riferito.

🟢 **Non resta nessuna attività BE aperta su questo cantiere.** Le due voci qui sopra
sono una **slice congiunta** e una **decisione di dominio**: nessuna delle due è in
attesa del BE. Anche il §1 di oggi non ne ha generate — la regola si allenta soltanto,
e `E_ORD_ANNULLA_CON_DDT` è già a catalogo e già dichiarato in
`error_policies_generated.py` (verificato).

---

## 1. ✅ FATTO — il controllo «questo preventivo ha già generato un ordine» non è mai scattato

> 🟢 **Chiuso il 2026-08-10** con `20260810-03`. Prima di scrivere una riga la
> diagnosi è stata **riverificata**, su richiesta di Tid: «ci sono stati molti
> controlli sulla sorgente polimorfa, credo che sia corretta». **Aveva ragione — la
> polimorfa è corretta**, e questo ha cambiato la forma della conclusione, non il
> fatto. Tre fonti indipendenti dicono la stessa cosa:
>
> | Fonte | Cosa dice |
> | --- | --- |
> | [guida sorgente-polimorfa](../../guide/sorgente-polimorfa.md) §6 | fra le colonne dirette elenca «`ddt.sorgente_uid`/`resi.sorgente_uid` uuid, **`ordini.documento_origine_id`**, `contratti.offerta_id`» |
> | Query 1 della guida, eseguita | il guard polimorfo è solo su `pratiche_sorgenti` e `commesse_sorgenti`: **`vendite.ordini` non è consumatrice del meccanismo** |
> | `vw_documento_lineage_archi` | lega preventivo e ordine con `p.id = o.documento_origine_id AND o.documento_origine_tipo = 'PREVENTIVO'` |
>
> Quindi il difetto **non è nel meccanismo né nelle colonne**: è che il MOTIVO 1
> applicava il pattern polimorfo a una tabella che ne è fuori. Il §4a della guida
> descrive esattamente questa trappola, e il test che la guida prescrive (la Query 1)
> l'avrebbe smascherata subito.
>
> **La diagnosi buona, che ieri sera non avevo:** il motivo era scritto **per
> simmetria col gemello** `fn_check_ordine_annullabile`, che ha la forma identica e
> **funziona** (9 ordini con DDT figlio, 9 con motivi ostativi). La simmetria si
> rompe perché `ddt.sorgente_uid` *è* il legame al padre ed *è* popolata (15/29),
> mentre `ordini.sorgente_uid` è l'origine di un import. **La stessa parola per due
> cose diverse su due tabelle vicine**: è questo che ha reso l'errore invisibile, non
> una distrazione.
>
> **Decisione di dominio (Tid, 2026-08-10).** La misura ha reso la domanda concreta:
> tutti e 20 gli ordini figli sono in **DRAFT**, cioè bozze. Deciso che *qualunque
> ordine figlio non annullato blocca, bozza compresa* — la via d'uscita esiste ed è
> nominabile (si abbandona prima la bozza dell'ordine). L'esclusione del figlio
> annullato è l'unico punto in cui la regola **non** copia il gemello, ed è voluta:
> senza, un figlio morto bloccherebbe il padre per sempre e senza uscita.
>
> **Effetto misurato prima/dopo, nella stessa transazione:**
>
> | Stato | Annullabili prima | Dopo | Bloccati dal fix | Sbloccati |
> | --- | --- | --- | --- | --- |
> | `ACCETTATO` | 23 | 10 | **13** | 0 |
> | `EVASO` | 21 | 0 | 21 *(senza effetto pratico: da EVASO l'azione non è offerta)* | 0 |
> | `DRAFT` / `EMESSO` / `ANNULLATO` / `RIFIUTATO` | invariati | | 0 | 0 |
>
> **pgTAP: nessuna regressione, misurata come applicazione (RLS attiva).**
>
> | Baseline | Rossi ora | Noti in baseline |
> | --- | --- | --- |
> | `script` | 12 su 57 | 12 |
> | `config` | 6 su 28 | 6 |
> | `vendite` | 24 su 175 | 24 |
>
> I due file che toccano l'annullamento e hanno rossi (`test-fn-cambia-stato-preventivo`,
> `test-available-actions-requires-righe-v1`) sono entrambi già in
> `baseline-rossi.tsv` come `ASSERZIONE`, con lo stesso conteggio di prima.
>
> ℹ️ Il presidio `test-capability-motivi-e-nessuna-azione-v1.sql` è rimasto verde
> **per costruzione**, e vale saperlo: i test 2 e 3 non asseriscono *quanti*
> preventivi sono annullabili, ma che la capability dica **la stessa cosa** della
> funzione pura. Quando la regola cambia, i due lati si muovono insieme e il test
> continua a presidiare ciò per cui esiste — la R2 — invece di diventare rosso su un
> numero. È la differenza fra fissare un conteggio e fissare un'invariante.
>
> ⚠️ **Il §3.3 del brief vie-d'uscita è stato corretto** — è la riga che ha causato
> l'errore, e va letta insieme al fix.
>
> 🔴 **La funzione è già viva sul DB senza essere in `databasechangelog`**: un
> `COMMIT` in una corsa diagnostica l'ha resa permanente. Nessun problema
> (`CREATE OR REPLACE` idempotente): il prossimo migrate riscrive lo stesso corpo e
> registra la riga. È lo stesso incidente del §7.2-ter di quel brief, stessa
> risoluzione.
>
> ✅ **Il gemello sui DDT è chiuso il 2026-08-15** con `20260815-01`: un DDT figlio
> **annullato** non blocca più l'annullamento dell'ordine. `is_abortito IS NOT TRUE`,
> lo stesso predicato del preventivo — una regola, due funzioni, stessa forma.
>
> ⚠️ **Ma va scritto perché era rimasto aperto, che è la parte istruttiva.** L'avevo
> classificato «asimmetria latente, oggi non morde: nessuno dei 9 DDT bloccanti è
> annullato, misurato». Quella misura è una **conta su dati di test**, e non dice
> niente sull'esercizio: annullare un DDT è ordinario — destinatario sbagliato, merce
> sbagliata, duplicato. Non era latente, era **certo**, e aspettava solo il primo
> annullamento per lasciare un ordine bloccato per sempre e senza uscita: cioè il
> difetto che questo cantiere è nato per chiudere, ricomparso sul gemello.
>
> **La domanda giusta è «può succedere?», non «è successo?».** Vale per tutto il
> documento: dove si legge «oggi non morde» o «zero documenti», il giudizio è da
> rifare. La correzione di metodo, con la distinzione fra le misure legittime e
> quelle che non lo sono, è in testa al
> [§12.6 del brief](brief-db-vie-uscita-operatore.md#126-cosa-resta-aperto-dichiarato).
>
> ℹ️ **Esclude solo l'annullato**: un DDT in stato `RESO` continua a bloccare, ed è
> corretto — la merce è rientrata ma il documento è **vissuto**, e annullare l'ordine
> cancellerebbe la storia di quel movimento. Chiusura positiva e annullamento non
> sono la stessa cosa.
>
> **Verificato dal percorso**, non da una fixture: preso un ordine il cui DDT figlio è
> in uno stato da cui la **matrice** ammette l'annullamento, e portato lì con la
> transizione vera; i DDT che bloccano scendono da 3 a 2. ⚠️ Il primo tentativo aveva
> scelto il soggetto dai dati invece che dalla matrice, e il guard di transizione l'ha
> rifiutato — correttamente. Presidiato dal test **13** di
> `test-capability-motivi-e-nessuna-azione-v1.sql`, che costruisce il soggetto allo
> stesso modo e asserisce sul **conteggio che cala**, non sulla sparizione del motivo:
> un ordine può avere più figli, e quelli vivi devono continuare a bloccare.
>
> 🟢 **Zero lavoro BE**: nessun codice errore nuovo, nessuna chiave i18n nuova. La
> regola si allenta soltanto, e `E_ORD_ANNULLA_CON_DDT` è già a catalogo e già
> dichiarato. Cambia solo la frequenza con cui l'API lo restituisce.

<!-- markdownlint-disable-next-line MD028 -->
> ℹ️ **Da qui in avanti il testo è il rilievo come fu scritto la prima volta**, prima
> della riverifica. È lasciato integro di proposito: la §1.5 propone di valutare un
> backfill di `sorgente_uid`, che la riverifica ha poi escluso — e vedere la strada
> scartata insieme alla ragione vale più di un documento ripulito.

### 1.1 Il fatto, in parole semplici

Quando si annulla un preventivo, il database deve rifiutare se da quel preventivo
è già nato un ordine: annullare il padre lasciando vivo il figlio non ha senso. La
regola sta in `script.fn_check_preventivo_annullabile`, che risponde con un elenco
di motivi ostativi. Il primo dei tre motivi è appunto «esiste già un ordine», e
solleva `E_PREV_ORDINE_GIA_GENERATO`.

**Quel motivo guarda nel posto sbagliato.** Cerca l'ordine così:

```sql
FROM vendite.ordini o
WHERE o.sorgente_uid = v_uid          -- l'uid del preventivo
  AND o.sorgente_tipo_id = (SELECT id FROM config.sorgenti WHERE codice_interno = 'PREVENTIVO')
```

Ma l'ordine nato da un preventivo **non si lega così**. Si lega con altre due
colonne, `documento_origine_tipo` e `documento_origine_id`.

Non è un'opinione: lo dice il commento della colonna nel database

> `documento_origine_tipo` — «Tipo del documento commerciale di origine (A1):
> PREVENTIVO|OFFERTA. NULL = ordine diretto (non nato da upstream)»
> `sorgente_uid` — «**Origine import** (uid)»
> `sorgente_tipo_id` — «FK → config.sorgenti.id (**tipo sorgente import**)»

e lo fa il codice che crea l'ordine, `vendite.fn_push_preventivo_a_ordine`, che ha
perfino il commento esplicito:

```sql
-- 4) Testata ordine: DRAFT, documento_origine = (PREVENTIVO, id).
INSERT INTO vendite.ordini (
    ..., documento_origine_tipo, documento_origine_id)
VALUES (
    ..., 'PREVENTIVO', p_preventivo_id)
```

`sorgente_uid` **non compare** in quella `INSERT`. Nella stessa funzione la parola
`sorgente_uid` c'è due volte, ma su un'altra tabella (`pratiche.pratiche_sorgenti`):
è la traccia sbagliata che rende la cosa difficile da vedere leggendo in fretta.

Detto in una riga: **la funzione legge la provenienza di un *import* per rispondere
a una domanda *commerciale*.**

### 1.2 Misurato, non dedotto

| Misura | Valore |
| --- | --- |
| Ordini nel database | **90** |
| Ordini con `sorgente_uid` valorizzato | **0** |
| Ordini con `documento_origine_tipo = 'PREVENTIVO'` | **64** |
| Ordini che soddisfano il predicato del Motivo 1 | **0** |

Il conteggio del Motivo 1 vale quindi sempre zero. Non «raramente»: **mai**, su
tutta la popolazione. `E_PREV_ORDINE_GIA_GENERATO` è un codice errore a catalogo
che nessun percorso vivo può produrre.

### 1.3 Perché è scomodo, e non solo sbagliato

Il §7.3 del [brief-db-vie-uscita-operatore](brief-db-vie-uscita-operatore.md)
ha consolidato le due regole di annullamento in **una** funzione, proprio per avere
una regola in una sede sola. Quel consolidamento tiene ancora — ma **uno dei tre
motivi che vivono dentro quella sede è morto**. La regola è una, e una sua terza
parte non ha mai parlato.

⚠️ **La tabella del §3.3 di quel brief è la causa dell'errore, e va corretta.**
Dice:

> | Colonne dirette — `ordini.sorgente_uid`, `ddt.sorgente_uid` | **`uuid`**, sempre |

Per `ddt.sorgente_uid` è giusto. Per `ordini.sorgente_uid` **no**: quella colonna è
l'origine di un import, non il legame al documento commerciale a monte. Chi ha
implementato il Motivo 1 ha seguito la tabella, e la tabella lo ha mandato fuori
strada. Se si corregge il predicato senza correggere anche quella riga, il prossimo
ci ricasca.

### 1.4 Il buco reale è più piccolo di quanto sembri, ma non è zero

Non tutti i preventivi con un ordine a valle passano: il **Motivo 3** (riga in
`commesse_sorgenti`) e il **Motivo 2** (righe già `EMESSA` in commessa) ne
intercettano molti per un'altra strada. Il buco sono i preventivi che hanno
generato **solo un ordine** e non sono stati mandati in commessa.

Misura dell'impatto della correzione — quanti preventivi **oggi si annullano e
domani non si annullerebbero più**:

| Stato | Con ordine generato | Di cui annullabili oggi |
| --- | --- | --- |
| `ACCETTATO` | 20 | **13** |
| `EVASO` | 44 | 21 |

⚠️ **I 21 di `EVASO` non contano nella pratica**, e va detto per non gonfiare il
numero: da `EVASO` la matrice non offre l'azione «annulla», quindi nessuno chiede
mai il verdetto da quello stato. La funzione è pura e risponde comunque, ma non c'è
un percorso che la interroghi.

**Il cambiamento vero sono quindi 13 preventivi `ACCETTATO`**: oggi il bottone
«Annulla» è acceso e l'annullamento riesce; dopo la correzione il bottone è spento
con il motivo, e il guard rifiuta.

### 1.5 La decisione, e cosa NON è

La strada è **raddrizzare il predicato**:

```sql
FROM vendite.ordini o
WHERE o.documento_origine_tipo = 'PREVENTIVO'
  AND o.documento_origine_id   = p_preventivo_id
```

⚠️ **Il backfill di `sorgente_uid` non è l'alternativa, ed è importante non
prenderlo per tale.** Verrebbe da pensare «riempiamo la colonna e il predicato
resta com'è», ma quella colonna ha un altro significato (origine import):
riempirla col preventivo la trasformerebbe in una seconda convenzione per la
stessa cosa — esattamente ciò contro cui è nata la R2 del brief. Nessuno ha mai
dovuto scriverla per questa catena, quindi non c'è nulla di rotto da sanare: c'è
un predicato che legge la colonna sbagliata.

⚠️ **È però un cambiamento RESTRITTIVO su un percorso vivo.** Prima di applicarlo
servono due cose, nell'ordine:

1. **Cercare i pgTAP che annullano un preventivo** e verificarli contro il nuovo
   predicato: 13 documenti cambiano verdetto, e una fixture che oggi annulla un
   preventivo con un ordine a valle diventa rossa **a ragione**. È lo stesso
   controllo che è mancato riattivando `CONFERMATO → ANNULLATO` sull'ordine, dove
   un test che fissava la decisione vecchia è diventato rosso a sorpresa. Quel
   rosso ha fatto il suo mestiere; questo va previsto, non subito.
2. **Chiedere a Tid se i 13 `ACCETTATO` vanno davvero bloccati.** È una decisione
   di dominio, non un dettaglio tecnico: la regola dice «un preventivo che ha già
   prodotto un ordine non si annulla», ma quei 13 esistono perché finora si
   annullavano. Se la risposta è sì, si applica; se è «no, solo se l'ordine è
   confermato», il predicato cambia forma e va scritta la ragione.

**Il BE non ha nulla da fare per questo punto**, verificato e non supposto: il
codice è a catalogo dal 2026-08-04 e la policy c'è già —
`error_policies_generated.py` lo mappa alla classe `CONFLITTO_STATO`. Cambia solo
la frequenza con cui l'API lo riceve, da mai a qualche volta.

---

## 2. ✅ FATTO lato DB — la nota di stato diventa informazione di stato

> 🟢 **Chiuso lato DB il 2026-08-10** con tre changeSet gemelli:
> `20260810-04` (preventivo), `-05` (ordine), `-06` (DDT). **Migrate eseguito lo
> stesso giorno alle 11:07** (`EXECUTED` in `databasechangelog`, vedi punto 1 in
> fondo a questo blocco e la tabella del §0).
>
> **Cosa fanno**, identico in tutte e tre: la nota non è più subordinata alla lista
> vuota (`v_nessuna_azione` e il suo `NOT EXISTS` escono come codice morto, insieme
> al commento che ne spiegava la logica) e il campo del blob si chiama ora
> **`stato_info_key`**.
>
> **Effetto misurato, per dominio:**
>
> | Dominio | Documenti con la nota | Nota |
> | --- | --- | --- |
> | `ordine` | **27 → 32** | i 5 nuovi sono gli EVASO col push ancora **acceso** — esattamente il limite dichiarato nel §9.2 del brief, che questa decisione rimuove |
> | `preventivo` | 73 → 73 | i 4 stati chiusi non hanno mai azioni vive: qui è solo rinomina + pulizia |
> | `ddt` | 12 → 12 | idem |
>
> **La questione (a) è chiusa dalla misura, non da un'opinione.** Su
> `PARZIALMENTE_EVASO` — l'unico stato **aperto** toccato dalla decisione — nel
> database non esiste un solo ordine: l'effetto oggi è zero e la scelta guarda al
> futuro. Preso «emetti sempre se seminata», perché una regola nel codice che spegne
> un dato deliberatamente seminato è la stessa classe di difetto di `20260810-01`. Se
> quella nota a video non convince, **si toglie la cella dal CSV** — non si rimette
> una regola nel codice.
>
> 🔴 **La questione (b) è stata risolta a metà, ed è una decisione, non una
> dimenticanza.** Il campo del blob è rinominato; la **proprietà nel `meta` dello
> stato resta `nessuna_azione_key`**. Il BE non l'aveva nominata, e c'è una ragione
> per cui non va toccata insieme: `scripts/check_i18n_keys.py` trova le 11 chiavi
> seminate **proprio per quel nome** (`RE_SEED_KEY` sui CSV, elenco `_PROP_KEY`).
> Rinominarla senza toccare il guard nello stesso commit lo renderebbe **verde per
> cecità** — non rosso, verde: il caso peggiore, già denunciato nel §8.3 del brief.
> L'asimmetria (`meta.nessuna_azione_key` → campo `stato_info_key`) è scritta due
> volte in ogni funzione: nel commento di revisione e accanto alla `SELECT` che legge
> la proprietà. **Rinominarla è una slice a sé**, e costa una riga di `_PROP_KEY` più
> le celle dei CSV. ⚠️ **Il preventivo è cresciuto**: quando fu scritto erano 11
> celle su 3 CSV, dopo la slice del §3 sono **20 celle su 7 CSV** (`preventivi` 4,
> `ordini` 4, `ddt` 3, `offerte` 3, `contratti` 2, `reso` 2, `stati_commessa` 2).
> Chi la prende in mano conti quelle, non queste — e noti che il settimo file **non**
> si chiama `stati_doc_*`.
>
> **pgTAP: 12/12 verde** con le funzioni nuove. Due cose sono cambiate nel presidio,
> e non in silenzio:
>
> * il **test 8 è stato ribaltato**. Asseriva «la nota non compare accanto a un
>   bottone vivo», cioè il presupposto caduto. Non è finito in baseline: la baseline
>   è un registro di **debito**, e un test che fotografa una scelta cambiata non è
>   debito. Ora presidia il verso nuovo, ed è **l'unica asserzione osservabile** del
>   cambiamento — misura i 5 ordini EVASO, e se domani qualcuno rimettesse il
>   `CASE WHEN v_nessuna_azione` sarebbe l'unica a prenderlo;
> * i test 6/7/10 **non ritagliano più niente**: la popolazione è tutta, e
>   l'asserzione è l'invariante «il valore nel blob è quello che lo stato dichiara»,
>   che copre nota-presente e nota-assente in una riga sola.
>
> ⚠️ **Il test 3 passa da 12 a 25 bloccati**, e non è un effetto di questo lavoro: è
> il §1 di stamattina, che ha fatto scattare il MOTIVO 1 su 13 preventivi in più.
>
> ✅ **Cosa mancava, e non era lavoro DB — tutto fatto il 2026-08-10:**
>
> 1. ✅ **fatto** — il migrate dei tre changeSet (11:07).
> 2. ✅ **fatto** — il **FE nello stesso rilascio**: 8 drawer + `DrawerActionsBar` passano da
>    `nessuna_azione_key` a `stato_info_key`. Fra i due deploy la nota non compare
>    (nessun errore: un campo che non arriva) — ed è **successo davvero**: fra le
>    11:07 e il rilascio FE la nota era invisibile in app. Aggiornati anche i due
>    documenti che citavano il nome vecchio, `frontend-standards.md` e
>    `catalogo-building-block-frontend.md`, con la **semantica** nuova e non solo
>    col nome;
> 3. ⚠️ **la trappola sopravvive al rinome**: il campo è **sempre presente** nel blob,
>    col valore a `null` quando non si applica. Filtrare con l'operatore di presenza
>    risponde vero per **tutti** i documenti. Va guardato il valore — vale ora per
>    `stato_info_key` come valeva prima.

<!-- markdownlint-disable-next-line MD028 -->
> ℹ️ **Da qui in avanti il testo è come fu scritto prima dell'esecuzione**, e va
> letto per quello: §2.1–2.3 riportano la richiesta del BE e la decisione, §2.4–2.5
> sono note del lato DB scritte **come cose da fare**. 🔴 In particolare il **§2.4 è
> superato**: prevedeva di ribaltare il test 8 e di aggiornare i riferimenti al nome
> del campo, e sono fatti — il blocco in testa alla sezione riporta l'esito (12/12).
> Resta utile perché dice *perché* quel test andava ribaltato e non messo in
> baseline.

### 2.1–2.3 La richiesta del BE e la decisione, come furono scritte

> Richiesta del BE del 2026-08-10, che nasce dalla **decisione §5 presa da Tid** lo
> stesso giorno. Riportata qui integralmente perché non vada persa, con in coda le
> cose che **solo il lato DB sa** e che la richiesta non poteva contenere.

### 2.1 La decisione

La domanda lasciata aperta nel §5 del documento di test — «"Evaso" è
un'informazione che serve all'operatore *anche* quando c'è ancora qualcosa da
fare, o solo quando non c'è più niente?» — è sciolta:

> **La nota spiega lo stato chiuso, e compare sempre.** Anche su un ordine evaso
> che ha ancora il pulsante vivo: l'operatore legge «è evaso, lo stato si ricalcola
> dai DDT» e ha comunque il suo bottone.

Quindi la nota **non è più la risposta a uno schermo vuoto: è l'informazione di
stato.** Il presupposto che la faceva sparire decade.

### 2.2 Il cambiamento — tre funzioni, una riga ciascuna

In `script.fn_available_actions_preventivo`, `_ordine`, `_ddt`:

```sql
-- da
'nessuna_azione_key', CASE WHEN v_nessuna_azione THEN v_nessuna_key END
-- a
'nessuna_azione_key', v_nessuna_key
```

`v_nessuna_azione` e il suo `NOT EXISTS` diventano **codice morto**: togliendoli va
via anche il commento che spiegava perché non si appoggiavano a `v_can_change` — è
la motivazione di una regola che non esiste più, e lasciarla scritta confonderebbe.

**Zero righe di frontend:** `DrawerActionsBar` rende già la nota accanto alle
azioni vive (prop `infoKey`, riga muted in coda alla barra).

### 2.3 I due effetti che la decisione non copriva — decidere qui

Il BE li ha segnalati invece di darli per scontati. Riporto la loro analisi e la
mia risposta.

**a) `ordini / PARZIALMENTE_EVASO` si accende.** Ha già la nota seminata
(«Evasione in corso: lo stato si ricalcola a ogni DDT.») ma **non è uno stato
chiuso**: `fase = IN_CORSO`. Finora non compariva mai proprio perché quegli ordini
hanno sempre azioni vive — era il caso registrato come «non provabile» nel
documento di test. Con la nuova regola comparirà su ogni ordine parzialmente
evaso.

Le due strade:

* **emettere sempre che ci sia una nota seminata** — il seed diventa l'unico
  comando: se c'è, si vede;
* **emettere solo con `fase = 'CHIUSO'`** — lettura letterale della decisione, ma
  lascia in vita un seed che non si vedrà mai.

> 🟢 **Concordo con il BE: la prima.** E aggiungo l'argomento dal lato DB, che è
> più forte della preferenza: **una regola nel codice che spegne un dato seminato è
> la stessa classe di difetto del punto ① del rilievo di ieri.** Lì il codice
> raccontava una condizione di stato che il dato non diceva; qui il codice
> deciderebbe di non mostrare un testo che qualcuno ha deliberatamente scritto nel
> seed. In entrambi i casi la sede della decisione si sdoppia. Con «se c'è, si
> vede» la sede è una: il CSV.
>
> ⚠️ Va però detto e messo a verbale che **cambia il comportamento su uno stato
> aperto**, non solo sui chiusi. Se la nota su PARZIALMENTE_EVASO non piace a
> video, la risposta è togliere quella cella dal seed — non rimettere una regola
> nel codice.

**b) Il nome del campo diventa falso.** `nessuna_azione_key` si mostrerà proprio
quando le azioni ci sono. Il vocabolario giusto esiste già dall'altra parte: le
chiavi i18n stanno sotto `vendite.<dominio>.stato_info.*`. Il BE propone la
rinomina a **`stato_info_key`**: 3 funzioni DB + 8 drawer frontend (che leggono
tutti il campo, anche i cinque domini le cui funzioni non lo emettono ancora — il
cablaggio è già lì, dormiente). Il backend non lo tocca, passa il blob invariato.
La parte frontend la fanno loro nello stesso giro.

> 🟢 **D'accordo.** È una rinomina di un campo del blob, quindi **DB e FE devono
> andare nello stesso rilascio**: nel mezzo il drawer leggerebbe un campo che non
> arriva più e la nota spariria senza errori. Da concordare il momento, non la
> sostanza.

### 2.4 ~~Quello che solo il lato DB sa, e che va fatto nello stesso commit~~ — ESEGUITO

> 🟢 **Superato: tutto quanto segue è stato fatto** nel commit `114ba076b` (test 8
> ribaltato, popolazione allargata, riferimenti al nome del campo aggiornati; suite
> **12/12**). La sezione resta perché spiega **perché** il test 8 andava ribaltato e
> non messo in baseline — un ragionamento che serve la prossima volta che una
> decisione cambia sotto un test verde. Il conto delle voci è nel blocco in testa
> alla sezione.

🔴 **Il pgTAP scritto oggi asserisce la regola VECCHIA, e con questa modifica
diventa esattamente sbagliato.** In `test-capability-motivi-e-nessuna-azione-v1.sql`:

| Test | Cosa succede |
| --- | --- |
| **8)** «non-regressione: la nota **non** compare su documenti con un'azione ancora abilitata» | 🔴 **Diventa rosso, e ha ragione il codice**: la nuova regola dice l'opposto. Va **ribaltato** («la nota compare anche accanto a un'azione viva») o ritirato. Non va messo in baseline: non è debito, è un test che fotografa una decisione cambiata |
| **6) 7) 10)** copertura della nota sui documenti muti | Restano verdi ma **misurano meno**: se la nota c'è sempre, «i muti la ricevono» è implicato. Diventa più utile asserire la copertura su **tutti** i documenti in fase CHIUSO, muti o no |
| **1)** «ogni stato in fase CHIUSO dichiara `nessuna_azione_key`» | Resta valido e diventa **più importante**: da quel momento la chiave si vede sempre, quindi una che manca è un buco visibile a ogni apertura del drawer |
| Riferimenti al nome del campo | **17 righe** citano `nessuna_azione_key` nel file, di cui **13 in codice** (le altre 4 sono commenti che spiegano la regola): cambiano tutte con la rinomina del §2.3-b |

È la stessa trappola che il brief vie-d'uscita descrive due volte: **un test che
fissa la scelta vecchia diventa rosso quando la scelta cambia**, e chi lo trova
senza saperlo dà la colpa alla modifica.

⚠️ **Il conto del seed nella richiesta del BE è vecchio di un giorno.** Loro
scrivono «la chiave è seminata solo su ordini (2) e DDT (2)». Da ieri sera è:

| Dominio | Chiavi seminate | Stati in fase CHIUSO |
| --- | --- | --- |
| `preventivi` | **4** (RIFIUTATO, SCADUTO, ANNULLATO, EVASO) | 4 |
| `ordini` | **4** (EVASO, PARZIALMENTE_EVASO, ANNULLATO, FATTURATO) | 3 (+1 su IN_CORSO) |
| `ddt` | **3** (CONSEGNATO, RESO, ANNULLATO) | 3 |

Quindi il punto ② del rilievo di ieri **è già chiuso** per questi tre domini: non
va rifatto. Restano gli altri.

🟢 **Chiuso il 2026-08-15 per quattro dei cinque — vedi §3.** Quanto segue è la
diagnosi che ha aperto la slice, tenuta com'era perché dice *perché* servivano due
cose e non una. Il `lotto` resta l'unico muto, dichiarato al §4.2.

🔴 **I cinque domini che non emettono affatto il campo.** `offerta`, `lotto`,
`reso`, `contratto`, `commessa`: le loro `fn_available_actions_*` non espongono
`nessuna_azione_key` per niente. Con la nuova regola resteranno **muti**, e per
loro servono **due** cose, non una: la riga nella funzione **e** il seed. Stati
chiusi oggi senza chiave, misurati:

| Dominio | Stati in fase CHIUSO con `meta = {}` |
| --- | --- |
| `offerta` | RIFIUTATA, SUPERATA, ANNULLATA |
| `commessa` | CHIUSA, ANNULLATA |
| `contratto` | CESSATO, ANNULLATO |
| `reso` | CONFERMATO, ANNULLATO |
| `lotto` | non misurato (tabella di stato diversa) |

⚠️ E **le chiavi i18n vanno seminate solo insieme alla riga nella funzione**: una
chiave nel `meta` che nessuna funzione legge è dato morto, e fa comunque diventare
rosso il presidio `check_i18n_keys.py` del BE finché non la traducono — cioè costa
a loro senza dare niente all'operatore. È l'errore inverso di quello di ieri, dove
il dato c'era e la funzione non lo leggeva.

### 2.5 Un dato morto già in casa, da sapere

`ordini / FATTURATO` ha da ieri la sua nota, ma **quello stato è irraggiungibile**:
nessuna transizione attiva della matrice porta a lui (le destinazioni sono solo
CONFERMATO, ANNULLATO, EVASO, PARZIALMENTE_EVASO) e il guard di matrice rifiuta un
`UPDATE` diretto. La cella è corretta e va lasciata — la pretende la regola del
test 1 — ma non aspettarsi di vederla a video, e **non cercare il difetto** quando
non compare.

---

## 3. ✅ FATTO — DB migrato e note a video (4 domini su 5) — i domini muti

> 🟢 **Deciso e scritto l'11-08, migrato e tradotto il 15-08.** Scelta di Tid: **i
> quattro domini con tabella di stato propria**, lasciando `lotto` fuori e dichiarato
> (§3.2). changeSet `20260811-01` (contratto), `-02` (reso), `-03` (offerta), `-04`
> (commessa): **migrate eseguito**. Le nove chiavi i18n sono tradotte it/en, quindi i
> quattro domini non sono più muti — la catena seed → funzione → drawer è chiusa.
>
> ⚠️ Il presidio `check_i18n_keys.py` **non vedeva** i due stati della commessa:
> ammetteva i soli CSV `transizioni_stati_*` e `stati_doc_*`, e la tabella è
> `vendite.stati_commessa`, senza il segmento `doc`. Segnalava **7 chiavi su 9** e
> sarebbe tornato verde lasciando due note mute. Il filtro per nome file è stato
> tolto: decide il contenuto, non la convenzione di battesimo (§0).
>
> | Dominio | Stati seminati | Documenti che ricevono la nota |
> | --- | --- | --- |
> | `contratto` | ANNULLATO, CESSATO | **9** |
> | `reso` | ANNULLATO, CONFERMATO | **9** |
> | `offerta` | ANNULLATA, SUPERATA, RIFIUTATA | **6** *(RIFIUTATA senza soggetti)* |
> | `commessa` | CHIUSA, ANNULLATA | **0** ⚠️ nessun soggetto vivo |
>
> **24 documenti su 24**: la slice copre tutta la popolazione misurata al §3.1.
> Zero note sugli stati aperti, verificato.
>
> ⚠️ **Su `commessa` il verde non ha misurato niente**: nessuna commessa è oggi in
> CHIUSA o ANNULLATA. Va fatto lo stesso — la regola del presidio pretende che ogni
> stato in fase CHIUSO dichiari la chiave, e il giorno in cui la prima commessa si
> chiude la nota c'è già — ma non aspettarsi di vederlo a video. Stessa cosa per
> `offerta / RIFIUTATA`.
>
> ⚠️ **`reso / CONFERMATO` è una chiusura POSITIVA** (fase CHIUSO, non abortito): il
> testo non deve suonare come un fallimento. È l'unico dei nove in cui la frase deve
> stare attenta al tono.
>
> **Le nove chiavi i18n**, dalle radici che ciascun dominio già usa nei propri seed
> (`reso` usa `vendite.reso` al singolare, non `vendite.resi`: sono entrambe nei
> locales, ma è quella che il guard già valida su quel dominio):
>
> ```text
> vendite.contratti.stato_info.cessato        vendite.contratti.stato_info.annullato
> vendite.reso.stato_info.confermato          vendite.reso.stato_info.annullato
> vendite.offerte.stato_info.rifiutata        vendite.offerte.stato_info.superata
> vendite.offerte.stato_info.annullata
> vendite.commesse.stato_info.chiusa          vendite.commesse.stato_info.annullata
> ```
>
> **pgTAP**: il test 1 del presidio è stato allargato ai domini nuovi e ora copre
> **19 stati chiusi in 7 domini** (erano 10 in 3). La lista dei domini è esplicita e
> il file dice perché deve crescere insieme alle funzioni: se non cresce, la regola
> smette di vedere il dominio nuovo **restando verde**, che è la cecità per
> costruzione già pagata due volte su quello stesso file. Suite **12/12**.

### 3.0 Il rilievo che ha aperto la slice

> Il BE ha verificato nel codice, non nel documento, e conferma: **`offerta`,
> `lotto`, `reso`, `contratto` e `commessa` non emettono affatto il campo**. Aggiunge
> un dato che dal lato DB non si vedeva: **tutti e otto i drawer leggono già
> `stato_info_key`**, quindi per cinque di loro il cablaggio è lì, pronto e inerte.
>
> E ha ragione sul fatto che la decisione §5 **peggiora** la cosa: ora che la nota
> «spiega lo stato» invece di rispondere allo schermo vuoto, quei cinque domini
> restano **gli unici in cui uno stato chiuso non dice niente** — un'incoerenza che
> prima si confondeva col comportamento generale.

---

## 4. L'analisi che ha preceduto il §3 — scansione, costo, il caso `lotto`

> ℹ️ **Questa sezione è l'istruttoria, non lavoro aperto.** È come fu scritta prima
> della decisione: misura i cinque domini muti, stima il costo e isola il `lotto`
> come caso a parte. Il §3 è l'esito, il §0 il consuntivo. Si legge qui *perché* la
> slice ha la forma che ha — in particolare perché il `lotto` è rimasto fuori.
>
> ⚠️ Fino al 2026-08-15 questa sezione non aveva un titolo: i §4.1–4.3 pendevano
> sotto il §3 e sembravano suoi. È il motivo per cui il caso `lotto` (§4.2) era
> facile da leggere come già risolto dalla slice.

### 4.1 La scansione, misurata

| Dominio | Tabella di stato | Stati CHIUSI senza chiave | Documenti oggi |
| --- | --- | --- | --- |
| `contratto` | `config.stati_doc_contratti` | ANNULLATO (7), CESSATO (2) | **9** |
| `reso` | `config.stati_doc_reso` | ANNULLATO (4), CONFERMATO (5) | **9** |
| `offerta` | `config.stati_doc_offerte` | ANNULLATA (3), SUPERATA (3), RIFIUTATA (0) | **6** |
| `commessa` | `vendite.stati_commessa` | CHIUSA (0), ANNULLATA (0) | 0 |
| `lotto` | `config.stati_doc_fiscale` | ANNULLATA (0), REGISTRATA (0) | 0 |

**11 stati, 24 documenti** che oggi mostrano una barra senza spiegazione. Tutte e
cinque le tabelle hanno già `fase` e `meta`: la forma del seed è identica a quella
appena fatta.

### 4.2 Due cose che la stima «una riga + il seed» non copriva

🟢 **La prima è a favore: la riga è davvero una riga.** Verificato: tutte e cinque
le funzioni **raggiungono già** la propria tabella di stato con un JOIN (quattro
leggono già `meta` o `pdf_mode` da lì, `lotto` fa un `LEFT JOIN` su
`config.stati_doc_fiscale`). Non serve aggiungere un JOIN a nessuna: servono una
variabile, una colonna nella `SELECT INTO` e un campo nel `jsonb_build_object` —
esattamente i tre punti toccati su preventivo/ordine/DDT.

🔴 **La seconda è un caso a parte, e va deciso prima di toccarlo. Il `lotto` non ha
una tabella di stato propria: usa `config.stati_doc_fiscale`, che è CONDIVISA con
`vendite.fatture`** (più le tabelle di log/pipeline: 8 FK in tutto). Seminare la nota
su uno stato fiscale significa scrivere un testo che deve essere vero **sia per un
lotto sia per una fattura** in quello stato — e una `fn_available_actions_fattura`
oggi **non esiste**, quindi metà dei consumatori di quel testo non è ancora scritta.
~~Nota a margine: sono anche i due stati con **zero documenti**, quindi è la parte a
valore più basso della slice.~~

> 🔴 **Quella nota a margine è RITIRATA (2026-08-15), ed è l'errore di metodo di
> tutto il documento in miniatura.** «Zero documenti» contava righe di un database di
> **test**. In esercizio una fattura raggiunge gli stati chiusi nel suo normale ciclo
> di vita, su ogni installazione, dal primo giorno: non è la parte a valore più basso,
> **è la più alta delle tre voci aperte**, e riguarda il documento più importante del
> ciclo.
>
> E verificando è emerso che il buco ha anche un'altra forma da come è raccontato qui
> sopra: `FatturaDrawer.vue` **esiste**, monta `DrawerActionsBar`, e le sue azioni sono
> **tre, hardcoded, tutte di servizio** (PDF, documenti, note). Intanto
> `config.stati_doc_fiscale_transizioni` dichiara **tre transizioni manuali con
> `action_key`** — `DRAFT → ANNULLATA`, `EMESSA → DRAFT`, `EMESSA → DEFINITIVA` — che
> nessuna funzione legge. Cioè: **il seed descrive tre bottoni che l'operatore non
> vede**, la stessa classe di ① e ②.
>
> Quindi non è «manca una nota al lotto»: manca il **governo dello stato sul documento
> fiscale**. Il quadro completo, con la domanda di dominio da sciogliere prima di
> costruire, è nel
> [§13.3-bis del brief](brief-db-vie-uscita-operatore.md).

Le tre strade, in ordine di quanto costano:

1. **Escludere il lotto** e fare i quattro domini con tabella propria — 9 stati, 24
   documenti, nessuna ambiguità. Il lotto resta dichiarato aperto;
2. includerlo con un testo scritto per essere vero su entrambi i tipi di documento
   («questo documento fiscale è annullato / registrato»), accettando che sia più
   generico degli altri;
3. rimandare tutta la slice e chiudere prima la `fn_available_actions_fattura`, che
   è il vero buco di quella famiglia — il documento **fiscale** non ha capability.

### 4.3 Costo, se si procede

* **1 changeSet per dominio** (4 o 5), stessa forma di `20260810-04/-05/-06`;
* **9 o 11 celle di seed** nei CSV degli stati — nessun changeSet, i loader sono
  mirror `runOnChange`;
* **9 o 11 chiavi i18n nuove**, testi del FE. ⚠️ Il guard `check_i18n_keys.py`
  resta **rosso** finché non le traducono: le chiavi vanno seminate **insieme** alla
  riga nella funzione, mai prima — una chiave che nessuna funzione legge è dato morto
  che costa a loro senza dare niente all'operatore, ed è l'errore inverso di quello
  del §2 del rilievo;
* **pgTAP**: il test 1 di `test-capability-motivi-e-nessuna-azione-v1.sql` presidia
  oggi i **tre** domini che espongono il campo. Va allargato ai nuovi, altrimenti la
  regola «ogni stato in fase CHIUSO dichiara la chiave» continuerebbe a non vederli —
  la stessa cecità per costruzione già pagata due volte (§2.4, §12.5 del brief).

🟢 **Consuntivo della stima (2026-08-15).** Pagata com'era scritta: 4 changeSet, 9
celle di seed, 9 chiavi i18n, test 1 allargato a **19 stati in 7 domini**. **Lato BE
e cablaggio FE il costo è stato zero** — i `call_jsonb_fn` passano il blob intero e
tutti e otto i drawer leggevano già la prop.

⚠️ **La stima mancava una voce, ed è quella che è costata.** L'ultimo punto qui
sopra prevedeva la cecità del **pgTAP** e ha fatto centro, ma nessuno ha previsto la
cecità dell'**altro** presidio: `check_i18n_keys.py` filtrava i seed per nome file
(`stati_doc_*`) e la tabella della commessa è `vendite.stati_commessa`. Due chiavi su
nove non sono mai comparse fra le mancanti. La lezione non è «allargare anche quella
lista»: è che **un presidio che seleziona per convenzione di nome è cieco per
costruzione**, e va fatto decidere dal contenuto (§0).

## 5. Cosa NON è in questo documento

Per non farne una lista di cose che sembrano mie e non lo sono.

* **I testi delle frasi** delle 11 chiavi i18n: li scrive il FE, il DB manda solo
  le chiavi. Le proposte di senso sono nella risposta al rilievo di ieri.
* **`error_policies.py`**: niente da aggiungere per nessuno dei due punti.
* **La correzione della tabella §3.3** del brief vie-d'uscita (§1.3 qui sopra): è
  una riga di documentazione, ma va fatta **con** la correzione del predicato, non
  prima e non dopo.
