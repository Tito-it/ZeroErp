# Attività urgenti — 10-08-2026

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-10.
> **A chi:** a chi riprende il lavoro, e al BE per il §2.
> **Perché esiste:** chiudendo il rilievo in-app sulle vie d'uscita per l'operatore
> sono emerse due cose che non stanno in quel perimetro. Una è **un controllo che
> non ha mai funzionato**; l'altra è **una richiesta nuova del BE** che nasce da una
> decisione di dominio già presa. Sono scritte qui perché si riparta da un documento
> e non dalla memoria.
>
> **Stato:** **§1 e §2 chiusi, applicati e committati** — i blocchi in testa a
> ciascuna sezione dicono cosa è stato fatto e cosa è stato misurato. Resta la metà a
> video, che è del FE, e il **§3**: una slice nuova, misurata l'11-08 su conferma del
> BE, che non era in questo documento quando è nato.
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
| `test-capability-motivi-e-nessuna-azione-v1.sql` | ✅ 9 → **12 test**, 12/12 come applicazione |
| `test-transizioni-uscita-manuale-v1.sql` | ✅ punto cieco dichiarato (solo commenti) |
| Baseline pgTAP dopo ogni passo | ✅ `script`, `config`, `vendite` — **nessuna regressione** |
| Doc auto-gen | ✅ rigenerate: riflettono il vivo |
| Commit | ✅ `114ba076b` (il lavoro), `6afc20993` (§12 al BE), `2d44dcb13` (§12.5-bis) |

**Cosa resta**, e non è lavoro DB tranne il §3:

1. **la metà a video** — 10 chiavi i18n da tradurre e la prop da rinominare in 8
   drawer + `DrawerActionsBar`, nello stesso rilascio. Finché non traducono, il guard
   i18n è rosso, ed è voluto;
2. **il §3 qui sotto**: i cinque domini muti. È lavoro DB e va deciso;
3. le voci dichiarate aperte nel [§12.6 del brief](../work-done/brief-db-vie-uscita-operatore.md#126-cosa-resta-aperto-dichiarato).

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
> ⚠️ **Resta aperto, dichiarato:** il gemello sui DDT ha la lacuna speculare — un DDT
> figlio **annullato** blocca ancora l'annullamento dell'ordine. Oggi non morde
> (nessuno dei 9 DDT bloccanti è annullato, misurato) e non è stato infilato qui:
> è un'altra decisione, sulla stessa forma.

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

Il §7.3 del [brief-db-vie-uscita-operatore](../work-done/brief-db-vie-uscita-operatore.md)
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
> `20260810-04` (preventivo), `-05` (ordine), `-06` (DDT). **Scritti e provati in
> transazione, NON ancora applicati**: manca il migrate.
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
> le 11 celle dei tre CSV.
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
> 🔴 **Cosa manca, e non è lavoro DB:**
>
> 1. il **migrate** dei tre changeSet;
> 2. il **FE nello stesso rilascio** — 8 drawer + `DrawerActionsBar` passano da
>    `nessuna_azione_key` a `stato_info_key`. Fra i due deploy la nota non compare
>    (nessun errore: un campo che non arriva). Da aggiornare anche due documenti
>    frontend che citano il nome vecchio, `frontend-standards.md` e
>    `catalogo-building-block-frontend.md`;
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

## 3. ✅ FATTO lato DB (4 domini su 5) — i domini muti

> 🟢 **Deciso e scritto l'11-08.** Scelta di Tid: **i quattro domini con tabella di
> stato propria**, lasciando `lotto` fuori e dichiarato (§3.2). changeSet
> `20260811-01` (contratto), `-02` (reso), `-03` (offerta), `-04` (commessa),
> **provati in transazione, migrate da fare**.
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
Nota a margine: sono anche i due stati con **zero documenti**, quindi è la parte a
valore più basso della slice.

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

## 5. Cosa NON è in questo documento

Per non farne una lista di cose che sembrano mie e non lo sono.

* **I testi delle frasi** delle 11 chiavi i18n: li scrive il FE, il DB manda solo
  le chiavi. Le proposte di senso sono nella risposta al rilievo di ieri.
* **`error_policies.py`**: niente da aggiungere per nessuno dei due punti.
* **La correzione della tabella §3.3** del brief vie-d'uscita (§1.3 qui sopra): è
  una riga di documentazione, ma va fatta **con** la correzione del predicato, non
  prima e non dopo.
