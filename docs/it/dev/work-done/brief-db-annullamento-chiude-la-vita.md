# Brief DB — L'annullamento chiude la vita: un lotto annullato esce dai controlli

> **Destinatari:** team DB (`dev/db-tid`). ⚠️ **Una richiesta al BE, da fare
> prima del merge** (§9.8): rigenerare `error_policies_generated.py` per il
> codice nuovo, altrimenti `test_error_policies_divergenza_db` è rosso in CI.
>
> **Tipo:** brief di cantiere, nato da una **decisione di Tid del 2026-09-22**
> (§1) presa davanti a un difetto trovato lo stesso giorno (§2).
>
> **Da leggere per primo: §9 — la decisione del 2026-09-23 e il lavoro che ne
> discende.** Il §1 resta la regola; il §4 è **superato** dal §9 (la regola non
> si scrive più come filtro nei controlli, si scrive nell'annullo). Il §8 è la
> rilettura che ha portato alla decisione.
>
> **Stato (2026-09-23 sera):** 🟢 **DB applicato e verificato** — i cinque
> changeSet `20260923-30` → `-34` sono `EXECUTED` su dbdev (15:43), pgTAP
> eseguiti da Tid **senza regressioni** (§9.9). ⛔ **Non ancora chiudibile**:
> manca un passo BE che blocca il merge — rigenerare
> `error_policies_generated.py` (oggi non contiene il codice nuovo), altrimenti
> `test_error_policies_divergenza_db` è rosso in CI. Fatto quello, il brief si
> archivia (§9.9 dice cosa passa a PROJECT_CONTEXT). ⚠️ Il §9.3 è stato
> **corretto scrivendolo**: la guardia sta su un trigger, non nella funzione.
>
> **In una riga:** un lotto annullato è **vuoto** — l'annullo chiude ogni
> attività del giro, esiti compresi, e da lì nessun controllo ha bisogno di
> escluderlo. La contraddizione «COMPLETATO con documenti in ERRORE» diventa
> **impossibile a DB** invece che segnalata, e il suo controllo va a catalogo
> come testimone.

---

## 1. La regola

> **L'annullamento chiude la vita.** Un lotto annullato non compare nei
> controlli.
> — Tid, 2026-09-22

È una regola sul **modello**, non una risposta alle righe di oggi: l'annullo è
un atto dichiarato e tracciato, non una cancellazione, e ciò che è chiuso non
è più lavoro di nessuno. Un controllo elenca **cose da fare**; un lotto
annullato non ne è una, qualunque cosa gli sia successa prima.

### 1.1 La regola ha già un nome, e non va inventato

Il modello sa già dire «questa cosa è morta»:

| Dove | Che cosa dice |
| --- | --- |
| `config.stati_doc_fiscale.is_abortito` | il flag. ⭐ **`ANNULLATA` è l'unico stato che ce l'ha acceso** — letto sul vivo il 22-09, sei stati in tabella |
| `vendite.vw_lotti_fase.is_abortito` | lo **proietta già**, accanto a `pre_fiscale` e `in_gioco` |
| 17 viste di `vendite` | lo leggono già (dashboard, lineage, preventivi, offerte, stato sorgente) |

⇒ La regola si scrive `NOT is_abortito`, in un flag che esiste, con una vista
che lo espone già. **Non serve una colonna nuova né un elenco di stati
cablato**: un `stato_codice_interno <> 'ANNULLATA'` sarebbe la stessa regola
scritta peggio, e si romperebbe il giorno che nasce un secondo stato abortito.

---

## 2. Il difetto che l'ha fatta emergere — 2026-09-22, letto su `dbdev`

⚠️ *Fatto datato. È un **controesempio**, non la ragione della regola: la
ragione sta nel §1 e regge anche a zero righe.*

`vendite.vw_lotti_chiusi_con_gruppi_in_errore` elenca una contraddizione — un
lotto chiuso `COMPLETATO` che contiene documenti in `ERRORE`. Il suo
`COMMENT` dichiara l'invariante:

> ⛔ L'INVARIANTE NON È PIÙ «VUOTO», È «NESSUNA RIGA NON DICHIARATA»
> (rev 2026-09-07). […] sono i lotti ANNULLATI PRIMA del 2026-09-07 19:09
> […] ⇒ Una riga su un lotto annullato DOPO quel momento è un allarme vero,
> e va guardata.

**Oggi le righe sono 7, e il pregresso dichiarato è 6.**

| Lotto | `stato_lotto` | Stato fiscale | Annullato il | Dichiarato? |
| --- | --- | --- | --- | --- |
| `LTF-0009900` `LTF-0009901` `LTF-0009931` `LTF-0009960` `LTF-0009961` `LTF-0009962` | `COMPLETATO` | `ANNULLATA` | 2026-09-07, fra 11:28 e 17:53 | ✅ sì (prima delle 19:09) |
| **`LTF-0010972`** (id 13337, 2 gruppi in errore, `E_PULL_COMMESSA`) | `COMPLETATO` | `ANNULLATA` | **2026-09-12 11:21** | 🔴 **no** |

⭐ Il criterio del `COMMENT` e i dati concordano perfettamente sui sei: è la
prova che il criterio è quello giusto, e che il settimo è davvero l'allarme
che quella riga descrive.

### 2.1 ⭐ Il secondo difetto, ed è quello che è costato di più

**L'allarme è suonato e non l'ha sentito nessuno: è lì dal 12-09, dieci
giorni.** La vista si chiama `PRESIDIO` nel proprio `COMMENT` e dichiara un
invariante preciso, ma **non ha una riga in `dbops.presidi`** — quindi è fuori
dal digest, dal pallino e da ogni conteggio.

* letto il 22-09: 45 presidi a catalogo di schema `dbops`, 1 di `maintenance`,
  **0 di `vendite`**;
* ⭐ e non c'è niente che lo vieti: `chk_presidi_vista_qualificata` chiede solo
  la forma `schema.nome`, e `maintenance` è già dentro. Non è una convenzione
  a tenerla fuori, è una dimenticanza; ⚠️ **smentito dal §8.3**: lo vieta il
  test 2 di `test-catalogo-presidi-v1.sql`;
* ⚠️ il pgTAP citato come verifica (`test-lotti-gruppi-esito.sql`, `plan(13)`,
  casi 11-12) prova il **meccanismo** su casi costruiti apposta — e dichiara di
  non dipendere dal pregresso. Giusto così, ma vuol dire che **nessuno guarda
  il contenuto vivo**: resterebbe verde con cento righe lì dentro.

### 2.2 Perché il conteggio può solo crescere

> ⚠️ **Smentito dal §8.1 (2026-09-23).** Dopo il `20260907-08` un giro che
> finisce con un gruppo fallito resta `ERRORE`, e l'annullo non lo tocca più:
> una riga nuova qui nasce **solo** se qualcuno ha scritto `COMPLETATO` sopra un
> gruppo in errore. Non è l'annullo a produrla.

Il changeSet `20260907-08` ha tolto una falsificazione vera: prima, annullare
un lotto **riscriveva** `stato_lotto = COMPLETATO`, cioè cancellava la memoria
di com'era andata. Ora non lo fa più — ed è giusto.

⇒ Conseguenza: ogni giro che finisce con un gruppo fallito e viene poi
annullato **aggiunge una riga qui**. Le sei dichiarate sono un insieme chiuso;
tutte le righe nuove sono vere per costruzione; e non le guarda nessuno.
`LTF-0010972` è la prima, non l'ultima.

---

## 3. Dove vale la regola — il censimento, 2026-09-22

Sweep su tutti i presidi a catalogo **più** la vista non catalogata: i
controlli che toccano i lotti sono **due**.

| Controllo | Esclude gli annullati? | Come |
| --- | --- | --- |
| `vendite.vw_lotti_chiusi_con_gruppi_in_errore` | 🔴 **no** | filtra solo `stato_esecuzione='ERRORE' AND stato_lotto='COMPLETATO'` |
| `dbops.vw_lotti_fermi_da_guardare` | ✅ sì — **ma per un'altra ragione** | `WHERE … f.pre_fiscale`, e `pre_fiscale = NOT congela_fiscale` |

⚠️ **Il secondo va guardato lo stesso, ed è il punto del §4.3.** Oggi non
mostra gli annullati perché `ANNULLATA` **congela il fiscale**, non perché sia
annullato. Sono due proprietà diverse che oggi viaggiano insieme: il giorno che
uno stato abortito non congelasse il fiscale — o che il congelamento cambiasse
perimetro — quel controllo ricomincerebbe a mostrare lotti morti, **senza che
nessuno abbia toccato la vista**. La regola del §1 lì è rispettata per
coincidenza, e una coincidenza non è un presidio.

---

## 4. La richiesta al team DB

> ⛔ **SUPERATO dal §9 (decisione di Tid, 2026-09-23).** La regola del §1 non
> si scrive come filtro dentro i controlli (§4.1, §4.3): si scrive
> **nell'annullo**, che chiude gli esiti, e da lì nessun controllo ha bisogno di
> escludere niente. Il §4.4 (catalogo) sopravvive nella forma del §9.4; il §4.5
> è sostituito dal §9.6. Il testo sotto resta per la storia della decisione.

### 4.1 La vista esclude gli annullati

`vendite.vw_lotti_chiusi_con_gruppi_in_errore`: aggiungere l'esclusione dei
lotti abortiti, letta dal flag e non da un elenco di stati. La vista oggi
`JOIN`a `vendite.fatturazione_lotti` diretta, quindi serve arrivare a
`is_abortito` — via `vendite.vw_lotti_fase` (che lo proietta già) o via
`config.stati_doc_fiscale`. ⭐ La scelta è vostra; il vincolo è che la regola
resti **una sola** e nominata, non ricopiata.

✅ Effetto atteso, verificato sui dati del 22-09: **7 righe → 0**, perché tutte
e sette sono `ANNULLATA`.

### 4.2 L'invariante torna «vuoto», e il pregresso dichiarato sparisce

⭐ **È la parte elegante, e va scritta nel `COMMENT`.** Le sei righe del
pregresso erano annullate: con la regola del §1 **escono da sole**. Quindi:

* l'invariante torna da «nessuna riga non dichiarata» a **«vuoto»**;
* il registro delle eccezioni **non serve più** — non nasce proprio;
* il blocco del `COMMENT` sul pregresso (rev 2026-09-07) va riscritto: non
  cancellato, ma raccontato come **chiuso** e col perché, che è la ragione per
  cui quel testo esiste.

⚠️ Il difetto che il pregresso descriveva (`stato_lotto` falsificato su undici
lotti) **resta un fatto storico vero** e la decisione di Tid del 07-09 di non
correggerlo non cambia: semplicemente quei lotti non sono più affari di questo
controllo. ⛔ Non è «nascondere le righe»: è che un lotto annullato non è una
cosa da fare — che è esattamente la regola, non una scorciatoia per farle
tacere.

### 4.3 La regola si scrive anche dove oggi è una coincidenza

`dbops.vw_lotti_fermi_da_guardare`: rendere **esplicita** l'esclusione degli
abortiti, accanto a `pre_fiscale` e non al posto suo. Non cambia una riga del
risultato di oggi (§3) — e questo è precisamente il motivo per cui va fatto
ora: è un guard che non costa niente e che regge il giorno in cui le due
proprietà si separano.

⛔ Argomento da rifiutare, se venisse in mente: *«oggi è ridondante»*. Zero
occorrenze non significa che il caso non esiste, e la vista aggiornata
dichiarerebbe la regola invece di ereditarla.

### 4.4 Il controllo entra a catalogo

Iscrivere `vendite.vw_lotti_chiusi_con_gruppi_in_errore` in
`dbops.presidi` (`80_data/.../dbops/presidi.csv`):

| Campo | Valore proposto | Perché |
| --- | --- | --- |
| `natura` | `ZERO` | dopo il §4.1 l'invariante è di nuovo «vuoto» |
| `cadenza` | `GIORNALIERA` | stessa ragione del gemello: una contraddizione nata ieri sera va vista stamattina |
| `perimetro` | da decidere: le tabelle sotto hanno la RLS | ⚠️ **da verificare**: il gemello è `DEFINER` perché `security_invoker` + RLS dà «zero per cecità». Va provato, non assunto |
| `registro` | `NULL` | §4.2: non nasce |
| `presidiato_da` | `NULL` | `ZERO` non lo richiede (`chk_presidi_cancello_ha_presidio` vincola solo `CANCELLO`) |

⚠️ `chk_presidi_fuori_digest_cadenza_mai` non morde: vincola `INVENTARIO` e
`CANCELLO`, non `ZERO`.

### 4.5 Il pgTAP cresce di due casi

`db/pgtap/vendite/test-lotti-gruppi-esito.sql` (oggi `plan(13)`, casi 11-12 sul
meccanismo). Due casi **costruiti**, non misurati sulla popolazione:

1. un lotto `COMPLETATO` con un gruppo in `ERRORE` **e annullato** → **non**
   viene nominato (è la regola del §1);
2. lo stesso lotto **non** annullato → viene nominato (il presidio non si è
   spento del tutto).

⭐ Il secondo è quello che conta: senza, la regola si potrebbe soddisfare
svuotando la vista, e sarebbe verde per sottrazione.

E la riga a catalogo del §4.4 va provata come le altre (natura/perimetro/
cadenza/attivo, sulla falsariga del caso 19 di `test-lotti-fermi-verdetto-a-db-v1.sql`).

---

## 5. La conseguenza, dichiarata

> ⛔ **SUPERATO dal §9.** Il prezzo descritto qui («annullare fa sparire
> l'allarme») non si paga più: la contraddizione non viene nascosta
> dall'annullo, viene **impedita** a DB (§9.3). `LTF-0010972` era un difetto
> del runner già chiuso (§9.2), non un caso che l'annullo doveva coprire.

⚠️ **Con questa regola, annullare un lotto fa sparire il suo allarme.**
`LTF-0010972` era una contraddizione vera, e dopo il §4.1 non si vedrà più.

Va detto perché è il prezzo della regola, e va detto che **è un prezzo accettato
e non un effetto collaterale scoperto dopo**. Le ragioni per cui regge:

* l'annullo non è una cancellazione: è un atto **tracciato**, con il suo stato,
  la sua data e il suo autore. La storia conserva tutto, e resta interrogabile;
* il controllo continua a prendere le contraddizioni sui lotti **vivi**, cioè
  finché servono a qualcuno;
* ⛔ e l'alternativa era peggiore: un controllo che elenca per sempre lotti
  morti smette di essere letto — e allora non presidia più nemmeno il caso per
  cui è nato. È esattamente quello che è successo qui, dieci giorni.

⇒ Se un domani servisse sapere «quante volte un giro è finito in contraddizione
ed è stato annullato», quella è una **misura sullo storico**, non un controllo:
sede diversa, e non è questo brief.

---

## 6. Cosa resta

> ⛔ **SUPERATO: l'elenco vivo è il §9.7.** Quello sotto è l'elenco del 22-09.

* 🔵 §4.1 la vista esclude gli abortiti (7 → 0);
* 🔵 §4.2 `COMMENT` riscritto: invariante «vuoto», pregresso chiuso col perché;
* 🔵 §4.3 la regola esplicita anche in `dbops.vw_lotti_fermi_da_guardare`
  (nessun cambio di risultato oggi, ed è il punto);
* 🔵 §4.4 la riga in `presidi.csv` — ⚠️ `perimetro` da **provare**, non assumere;
* 🔵 §4.5 due casi pgTAP costruiti + la riga di catalogo;
* ▶ niente da fare lato BE/FE: nessun endpoint e nessuna schermata leggono
  questa vista (verificato il 22-09 — i soli riferimenti fuori da `db/` e
  `docs/` sono commenti).

---

## 7. Come sono stati letti i numeri di questo brief

⚠️ Per chi rifarà le misure: le tabelle sotto hanno la **RLS** e le viste sono
`security_invoker`. Da una sessione senza veste rispondono **zero**, e quello
zero **non è un dato** — è cecità. Le letture del §2 e del §3 sono state fatte
con `SET app.ruolo_applicativo = 'OPERATORE'` lasciando vuoto
`app.current_user_id`, che cade nel ramo «job batch» (`p_auth_user_id IS NULL
→ true`) di `script.fn_check_user_emittente_scope`. I conteggi dei presidi
vengono invece da `dbops.fn_conta_presidio`, che è `SECURITY DEFINER`.

---

## 8. Rilettura critica — 2026-09-23

> Letto contro la doc auto-gen, i changeSet, `test-catalogo-presidi-v1.sql` e,
> in sola lettura da owner, lo storico di `LTF-0010972`. **Ordine: dal più grave.**
> La regola del §1 non è messa in discussione come regola; lo è la sua
> applicazione **a questo** controllo.

### 8.1 🔴 Il settimo lotto è un difetto della pipeline, non un lotto annullato

Storico di `LTF-0010972` (id 13337), letto il 23-09:

| Istante (09-12) | `stato_lotto` | Stato fiscale | Che cosa è successo |
| --- | --- | --- | --- |
| 11:15:14 | `IN_ESECUZIONE → ERRORE` | `DRAFT` | primo giro: esiti 1921 e 1922 scritti `ERRORE` (`E_PULL_COMMESSA`) |
| **11:19:31** | `ERRORE → IN_ESECUZIONE → COMPLETATO` | `DRAFT` | ⭐ **rilancio: chiuso `COMPLETATO` nella stessa transazione** |
| 11:21:40 | `COMPLETATO` (non toccato) | `ANNULLATA` | l'annullo, due minuti dopo |

* i due esiti **non sono stati toccati dal rilancio** (`data_update` = 11:15:14);
* il lotto ha oggi **zero** righe in `fatturazione_lotti_fatture` (da capire se
  non sono mai nate o se le ha staccate l'annullo).

⇒ `COMPLETATO` l'ha scritto **la pipeline**, con i suoi due soli gruppi in
`ERRORE`, prima che nessuno annullasse. È **esattamente** il caso per cui la
vista è nata (`COMMENT`: con tutte le commesse fallite le fatture non nascono, e
la salvezza è «INDIRETTA»). Il presidio ha preso il suo bersaglio al primo
colpo vero; il §4.1 lo spegne.

⛔ Conseguenza sul §1: *«un controllo elenca cose da fare»* **non vale per
questo controllo.** Il manuale di `dbops.presidi` definisce `ZERO` come «un
guasto **adesso**», non come una coda di lavoro. Qui il guasto è del **codice**
che ha chiuso il lotto, e un atto successivo di una persona sul **dato** non lo
ripara: lo copre. Il §5 dice *«il controllo continua a prendere le
contraddizioni sui lotti vivi»* — ma il rilancio che ha chiuso male
`LTF-0010972` si ripete identico su un lotto che poi verrà annullato, e da quel
momento nessuno lo vede.

⚠️ **Due domande prima di tutto il resto** (il §4 non ne affronta nessuna):

1. **Chi ha scritto `COMPLETATO` alle 11:19:31, e può ancora farlo?** Ipotesi da
   verificare, non conclusione: il «decimo conteggio» (esiti `ERRORE` nel
   verdetto `fermo`) è entrato in Python **il 12-09** e a DB il 19-09
   (`vw_lotti_segnalazioni_summary`). Se il rilancio delle 11:19 girava sul
   codice di prima, il difetto può essere già chiuso — ma va provato.
2. ⭐ **A DB niente lo impedisce.** `fn_set_fatturazione_lotto_stato` non guarda
   gli esiti: la transizione `IN_ESECUZIONE → COMPLETATO` con gruppi in
   `ERRORE` passa, e l'unica difesa è il verdetto letto dal runner. In un
   progetto DB-first la contraddizione si rende **impossibile** (guard sulla
   transizione che legge `fermo` dalla sede unica), e il presidio diventa il
   testimone del pregresso, non l'unica difesa.

### 8.2 🟠 `NOT is_abortito` sparisce sul lotto senza stato

`fatturazione_lotti.stato_doc_fiscale_id` è **nullable** e `vw_lotti_fase` fa
`LEFT JOIN`: su un lotto senza stato risolvibile `is_abortito` è `NULL`,
`NOT NULL` è `NULL`, e il `WHERE` **toglie il lotto dal presidio in silenzio**.
Il modello lo ammette (è il «settimo caso» del `COMMENT` di `vw_lotti_fase`).

* per un **controllo** la prudenza è mostrare: `is_abortito IS NOT TRUE`, non
  `NOT is_abortito`;
* ⭐ e con il §4.3 le sedi che scrivono la regola diventano **due** nello stesso
  giro: per la regola del 2 la regola va **estratta** come colonna derivata di
  `vw_lotti_fase` (che è già «la sede unica della domanda: in che fase è questo
  lotto?», con i derivati `COALESCE`-ati e il fail-closed dichiarato), non
  scritta due volte. La scelta «via `vw_lotti_fase` o via
  `config.stati_doc_fiscale`» del §4.1 non è libera.

⚠️ Il §1.1 dice «17 viste di `vendite` lo leggono già»: molte leggono
l'`is_abortito` di **altri cataloghi** (ordini, DDT, contratti) e in quattro
forme diverse (`IS TRUE`, `IS FALSE`, `IS NOT TRUE`, nudo). Il flag esiste; la
sua lettura sull'ignoto **non** è una sola. Non è un argomento a favore.

### 8.3 🔴 Una vista di `vendite` a catalogo accende il test 2

`test-catalogo-presidi-v1.sql`, **test 2 (verso 1)**: ogni vista di **ogni schema
che compare nella colonna `vista`** deve avere la sua riga in `dbops.presidi`. È
per questo che `maintenance` è dentro: ha **una** vista sola. `vendite` ne ha
**63** (doc auto-gen, 23-09): iscriverne una rende il test rosso sulle altre
62.

⇒ Il §2.1 (*«non c'è niente che lo vieti… è una dimenticanza»*) va corretto: lo
vieta il presidio del catalogo, e il gemello è nato in `dbops`
(`dbops.vw_lotti_fermi_da_guardare`, un **lettore** di `vendite`) con ogni
probabilità per la stessa ragione. Le strade sono due:

* **A** — un lettore `dbops.vw_lotti_chiusi_con_gruppi_in_errore` sopra la vista
  di `vendite` (stessa forma del gemello), ed è quello che va a catalogo;
* **B** — portare in catalogo tutto `vendite` (62 `INVENTARIO`): un cantiere a
  sé, non un effetto collaterale di questo.

### 8.4 🟠 Il §4.2 rovescia una decisione del 07-09 senza nominarla

Il `COMMENT` di oggi e il §25.4 di `brief-db-esito-gruppo-lotto` dicono:
*«⛔ E non si filtrano via. Nasconderle renderebbe la vista verde su una
falsificazione che c'è davvero, e toglierebbe l'unico posto in cui quei sei
lotti sono nominati.»* Il §4.2 cita la metà della decisione del 07-09 che non
cambia (non si corregge) e tace la metà che cambia (non si filtra).

⇒ Se Tid conferma, il `COMMENT` riscritto deve dire che quella clausola è
**rovesciata**, perché, e **dove** i sei (anzi gli undici) restano nominati —
lo storico, con la query o il criterio per ritrovarli.

⭐ E c'è una strada che il brief non considera: il catalogo ha già la forma per
«nessuna riga non dichiarata» — `colonna_stato` + `stato_atteso`, o `REGISTRO`.
La vista così com'è si iscrive con una colonna `DICHIARATO`/`NON_DICHIARATO`
(il criterio del `COMMENT`, «annullato prima del 2026-09-07 19:09», è già
scritto) e **l'allarme su `LTF-0010972` resta acceso**.

### 8.5 🟡 Minori

* §2 *«il criterio e i dati concordano perfettamente: è la prova che il
  criterio è quello giusto»* — regola zero: un dato può smentire un criterio,
  non provarlo. Da riscrivere come «i dati non lo smentiscono».
* §4.4: mancano `nota` (vincolata da `chk_presidi_nota_non_vuota`),
  `colonna_stato`/`stato_atteso`, `attivo`. Il `perimetro` non è davvero «da
  decidere»: il §7 del brief stesso spiega la cecità, e la risposta è `DEFINER`
  come il gemello — con il test 11 di `test-catalogo-presidi-v1` che la presidia.
* §4.5: il caso 2 proposto («lo stesso lotto non annullato viene nominato») è
  già il test 12. Il contrasto utile è **lo stesso** lotto costruito, nominato
  prima dell'annullo e non nominato dopo: così la sola differenza è l'annullo.
* §4.2: riscrivere il `COMMENT` di una vista passa da `CREATE OR REPLACE VIEW`
  (o `COMMENT ON`): nel primo caso `security_invoker=true` va ri-specificato.
* §1 *«in nessun controllo»*: il censimento del §3 guarda solo i presidi. Il
  verdetto `fermo` di `vw_lotti_segnalazioni_summary` resta vero su un lotto
  annullato, ed è giusto (una sede, una domanda) — ma il perimetro della regola
  («controllo» = riga di `dbops.presidi`) va scritto, o il prossimo lo estende
  al banner. ✅ *Assorbito dal §9: con l'annullo che chiude gli esiti anche il
  verdetto `fermo` si spegne da sé sul lotto annullato, per l'addendo esiti.*

---

## 9. ✅ La decisione — 2026-09-23: l'annullo chiude le attività

### 9.1 Che cosa ha deciso Tid

> **B**: prima si rende impossibile la contraddizione, poi il controllo va a
> catalogo come testimone. E: *«il lotto si dovrebbe annullare solo se vuoto,
> in quanto tutte le attività o vengono risolte o riportate allo stato
> precedente»*. Gli esiti di un lotto annullato sono **attività**, non storia.
> — Tid, 2026-09-23

⇒ La regola del §1 cambia **sede**. Non è più «i controlli escludono gli
annullati», ma **«un lotto annullato è vuoto»**. Lo rende vero l'annullo stesso,
nella stessa transazione, e allora nessun lettore ha bisogno di escludere
niente: niente `is_abortito` nei controlli, niente colonna derivata (§8.2
decade), niente §4.3.

⭐ Il «solo se vuoto» di Tid non diventa un guard che rifiuta: l'annullo **è**
lo svuotamento. `fn_annulla_lotto_da_draft` cancella già le fatture
(`fn_cleanup_fatture_by_ids`), riporta indietro le attività e annulla i task
run. Gli esiti sono **l'unica** cosa del giro che non tocca, ed è il buco.

### 9.2 ✅ Il difetto di `LTF-0010972` è già chiuso — verificato sul codice

Lo dice il codice, non l'assenza di righe nuove:

* il runner, a fine giro, scrive `ERRORE` o `COMPLETATO` secondo
  `evaluate_lotto_status` (`pipeline_runner.py`, ramo di chiusura; il giro vuoto
  conta anche lui dal 2026-09-08, `c74008452`);
* fino al **2026-09-12 16:15** (`72f4be589`, brief «rilancio step non rivede le
  proprie commesse») quel verdetto **non contava gli esiti in `ERRORE`**;
* il rilancio di `LTF-0010972` è delle **11:19 dello stesso giorno**: nessuna
  fattura, nessuna critica, esiti non contati ⇒ `COMPLETATO`.

⇒ I sette lotti del §2 sono **tutti pregresso**, di due difetti chiusi: l'annullo
che riscriveva `stato_lotto` (`20260907-08`) e il verdetto senza esiti
(`72f4be589`). Il §8.1 resta vero come diagnosi, ma non c'è un difetto vivo da
cercare.

⚠️ **Resta aperta una sola cosa, ed è il §9.3:** la difesa oggi è **solo nel
backend**. A DB `fn_set_fatturazione_lotto_stato` accetta `COMPLETATO` con
esiti in `ERRORE`, quindi il `72f4be589` è stato una correzione del runner, non
del modello.

### 9.3 Il lavoro 1 — `COMPLETATO` si rifiuta su un lotto fermo

> ⛔ **Corretto il 2026-09-23 scrivendolo — il testo sotto è la prima stesura.**
> La guardia **non** sta in `fn_set_fatturazione_lotto_stato`: lì sarebbe stata
> **muta**. Il runner non chiama quella funzione: `set_lotto_job_stato`
> (`pipeline_repository.py`) scrive `stato_lotto` con un `UPDATE` diretto e una
> sua copia della matrice degli stati. Nessuna funzione DB viva scrive
> `COMPLETATO`, e la funzione la chiamano solo due pgTAP.
> ⇒ **Trigger** `trg_fatturazione_lotti_a10_guard_completato_upd`,
> `BEFORE UPDATE OF stato_lotto`: l'unico punto che ogni scrittore attraversa.
> Legge `fermo` (e `fermo_motivo`, per la frase) dalla sede
> `vw_lotti_segnalazioni_summary`.
>
> ⭐ **E un secondo ramo, nato dal §9.4:** con gli esiti chiusi dall'annullo,
> `fermo` su un lotto annullato torna falso, e la domanda «è fermo?» lascerebbe
> passare un `COMPLETATO` su un annullato. È la falsificazione del 07-09 («la
> corsa è finita bene» di un giro interrotto). Il runner rifiuta già i giri su
> un ANNULLATA; ora lo dice anche il modello: `COMPLETATO` si rifiuta se lo
> stato fiscale è **abortito** (il flag `is_abortito`, non un elenco).
>
> Codice `E_LOTTO_COMPLETATO_NON_GUADAGNATO` (TECNICO); la frase dice il motivo
> in italiano («ha documenti in errore», «è annullato»), il codice del motivo
> resta nel contesto.
>
> ⚠️ **Debito trovato, non toccato:** la matrice degli stati di `stato_lotto`
> vive in **due** sedi che dissentono — `fn_set_fatturazione_lotto_stato` rifiuta
> `COMPLETATO → ERRORE`, il backend lo ammette (decisione del 24-08, lotto 6260).
> La funzione è di fatto morta. Va deciso se ritirarla o farla diventare la
> sede unica che il backend chiama: cantiere a sé, BE + DB.

In `vendite.fn_set_fatturazione_lotto_stato`: la transizione verso `COMPLETATO`
si rifiuta se il lotto è `fermo`, letto dal lettore per-lotto della sede unica
(`vendite.fn_get_lotto_segnalazioni_summary(p_lotto_id)`, colonna `fermo`). Non
si ricalcolano gli addendi: la sede è una (D-1 del 18-09).

* ⭐ il runner fa già la stessa domanda alla stessa sede prima di scrivere: in
  esercizio il guard **non scatta mai**. È un cancello contro un chiamante che
  diverge (un altro percorso, un runner regredito), cioè esattamente il caso
  del 12-09;
* codice di errore **nuovo**, `TECNICO` (nessun operatore lo provoca: è un
  chiamante rotto). Va in `codici_errore.csv` ⇒ ricaduta BE: rigenerare
  `error_policies_generated.py` (richiesta al team BE, niente di più);
* ⚠️ prima di scriverlo, grep dei pgTAP che portano un lotto a `COMPLETATO`
  (due file chiamano la funzione direttamente): una fixture che chiude un lotto
  con esiti o critiche aperte diventa rossa, e va riletta. Non va ammorbidito
  il guard.

### 9.4 Il lavoro 2 — l'annullo chiude gli esiti

In `vendite.fn_annulla_lotto_da_draft`, dopo il cleanup delle fatture: **ogni**
esito del lotto non ancora `ESCLUSO` passa a `ESCLUSO`, con
`uscita_motivo = 'Annullo del lotto <codice>'`. `uscita_quando` e `uscita_da`
li deriva già il trigger (`trgfn_fatturazione_lotti_esiti_uscita`): non si
scrivono.

⭐ **Tutti gli esiti, non solo quelli in `ERRORE`.** L'annullo cancella
**tutte** le fatture del giro, e `fn_escludi_documento_da_giro` dice già perché
un `COMPLETED` rimasto non va bene: direbbe *«è andato bene» su un documento che
non ha più nessuna fattura*. Stessa cosa per `PENDING`/`RUNNING`: il giro non
esiste più.

⭐ **`ESCLUSO` e non uno stato nuovo.** Il vocabolario (`chk_..._stato`) ha già
lo stato che vuol dire «questo documento è uscito dal giro, ecco chi, quando e
perché», con il motivo obbligatorio per `CHECK`. L'annullo è l'uscita di
tutti i documenti in un colpo solo, con un motivo solo.

⚠️ **Non si chiama `fn_escludi_documento_da_giro` in un ciclo**, e non è una
copia di quella funzione. Quella è il verbo per un documento: la sua check
ammette solo esiti in `ERRORE`, cancella le fatture di quel documento e
rimette in `PENDING` i trascinati. Nell'annullo le fatture sono già cancellate
e non c'è un giro che riparte. Quello che è in comune (`ESCLUSO` + motivo,
`uscita_*` dal trigger) sta già in un posto solo: nel `CHECK` e nel trigger.

Effetti a valle, **senza toccare i lettori**:

| Lettore | Effetto |
| --- | --- |
| `vw_lotti_chiusi_con_gruppi_in_errore` | un lotto annullato **dopo** il changeSet non ha esiti in `ERRORE` ⇒ non compare |
| `vw_lotti_segnalazioni_summary` | `esiti_stato_esecuzione_errore_count` = 0 ⇒ l'addendo esiti del `fermo` si spegne |
| `vw_documenti_trattenuti_da_lotto` | nessun cambio: esclude già `ESCLUSO`, e l'annullato non è `in_gioco` |
| `fn_log_pipeline_fase` | rifiuta già `W`/`C` su un documento uscito: dopo l'annullo nessuno ci scrive sopra un allarme |

Due scelte per chi scrive il changeSet:

* **la firma non cambia.** `fn_annulla_lotto_da_draft` restituisce `RETURNS
  TABLE` a cinque colonne, e il backend le legge **per posizione**
  (`pipeline_repository.py`). Una sesta colonna vorrebbe dire `DROP` e una
  ricaduta BE. Il conteggio degli esiti chiusi va nel **giornale**;
* **una riga di giornale** (`fn_log_pipeline_fase`, status `I`) per l'annullo,
  con il numero di documenti usciti: è quello che `fn_escludi_documento_da_giro`
  fa per il singolo documento dal 09-09, e per la stessa ragione.

### 9.5 ✅ Il pregresso — deciso da Tid il 2026-09-23: **A, si allineano**

> ✅ **Scelta A** (Tid, 2026-09-23). Un changeSet `80_data` una tantum applica
> ai lotti **già annullati** la chiusura degli esiti del §9.4. Perimetro:
> **tutti** i lotti annullati con esiti non `ESCLUSO`, qualunque sia lo stato
> dell'esito, non solo i sette del §2. `stato_lotto` **non si tocca**: la
> decisione del 07-09 resta. Da scrivere dopo il §9.4, così la correzione
> ripete esattamente ciò che fa l'annullo. Il testo sotto è la domanda com'era
> stata posta.

I sette lotti del §2 sono già annullati con esiti in `ERRORE`, e il changeSet
del §9.4 vale solo per gli annulli successivi. Due strade:

* **A — si allineano.** Un changeSet `80_data` una tantum applica ai lotti **già
  annullati** la stessa chiusura del §9.4 (`ESCLUSO`, motivo «Annullo del lotto
  — allineato il GG-MM-AAAA»). ⭐ Qui non vale l'obiezione del 07-09 contro
  l'`UPDATE`: allora l'`UPDATE` aggirava la macchina a stati di `stato_lotto`;
  questo scrive su un annullato quello che l'annullo scrive da oggi in poi, e
  `stato_lotto` falsificato **resta com'è** (la decisione del 07-09 non cambia).
  La vista torna vuota, l'invariante torna «vuoto», e il `COMMENT` racconta il
  pregresso come **chiuso**.
* **B — si dichiarano.** La vista va a catalogo con uno stato atteso
  (`colonna_stato`: `DICHIARATO` per i lotti annullati prima del changeSet del
  §9.4); il criterio del `COMMENT` si allarga dal 07-09 19:09 a quell'istante.

➡️ **Raccomandazione: A.** È l'unica in cui «un lotto annullato è vuoto» vale
per **tutti** i lotti e non «per quelli annullati dopo una certa data». B tiene
per sempre un'eccezione datata dentro un controllo `ZERO`. ⚠️ AGENTS.md chiede
comunque, per un problema di dati in sviluppo, se si fa prima a mano: A è la
versione ripetibile della stessa correzione, e vale anche per gli altri
annullati con esiti `COMPLETED`/`PENDING` che nessun controllo nomina.

### 9.6 Il lavoro 3 — il controllo a catalogo, e i pgTAP

> ✅ **Scritto** (§9.8). Il lettore si chiama
> **`dbops.vw_lotti_chiusi_con_errori_da_guardare`**, non come la sorgente: due
> viste omonime in due schemi si distinguerebbero solo per `search_path`. I casi
> 11-12 di `test-lotti-gruppi-esito.sql` **non** vanno toccati: costruiscono la
> contraddizione con un `INSERT` già `COMPLETATO` e un esito scritto dopo, cioè
> dalla porta dell'esito, che la guardia non chiude — verdi con l'SQL nuovo.
> Da rileggere è invece `test-lotti-attivita-stato-esecuzione-v2.sql`, che
> fissava come atteso un lotto `COMPLETATO` con una fattura in `ERRORE`.

**Catalogo** (§8.3): un lettore `dbops.vw_lotti_chiusi_con_gruppi_in_errore`
sopra la vista di `vendite`, stessa forma di `dbops.vw_lotti_fermi_da_guardare`.
`vendite` non entra nella colonna `vista` (test 2 di
`test-catalogo-presidi-v1.sql`).

| Campo | Valore |
| --- | --- |
| `natura` | `ZERO`: dopo l'allineamento del §9.5 la vista è vuota, e l'invariante torna «vuoto» |
| `cadenza` | `GIORNALIERA` |
| `perimetro` | `DEFINER`: le tabelle sotto hanno la RLS, e le viste sono `security_invoker` (§7). Il test 11 del catalogo presidia il proprietario |
| `registro`, `presidiato_da` | `NULL` |
| `attivo` | `t` |
| `nota` | obbligatoria (`chk_presidi_nota_non_vuota`): che cosa vuol dire una riga, e che dal §9.3 è un **testimone** — a DB la contraddizione non si può più scrivere |

**pgTAP**, tutti su casi **costruiti**:

1. *annullo, esiti chiusi* — un lotto DRAFT con un esito `ERRORE`, uno
   `COMPLETED` e uno `PENDING`; dopo l'annullo sono tutti `ESCLUSO`, con
   `uscita_motivo` valorizzato e `uscita_quando`/`uscita_da` scritti dal
   trigger. Sede naturale: accanto a `test-annulla-lotto-non-riscrive-stato-v1.sql`;
2. ⭐ *il contrasto* — lo **stesso** lotto, prima dell'annullo, è nominato da
   `vw_lotti_chiusi_con_gruppi_in_errore` (se `COMPLETATO`) e dopo no. Senza
   il «prima», il «dopo» passa anche su una vista vuota;
3. *il guard del §9.3* — `COMPLETATO` su un lotto con un esito `ERRORE`
   solleva il codice nuovo (`throws_ok` **con** SQLSTATE/codice, non a vuoto);
   e sullo stesso lotto, tolto l'errore, passa. Di nuovo la coppia: senza il
   secondo, un guard che rifiuta sempre sarebbe verde;
4. *la riga di catalogo* — `ZERO`/`DEFINER`/`GIORNALIERA`/`attivo`, sulla
   falsariga del caso 19 di `test-lotti-fermi-verdetto-a-db-v1.sql`.

⚠️ `test-lotti-gruppi-esito.sql` casi 11-12 costruiscono un lotto
`COMPLETATO` con un esito `ERRORE`: con il §9.3 **non si può più costruire
passando dalla funzione**. Va riletto come fixture (inserimento diretto sotto
la GUC di servizio, se esiste, o riformulato) — ed è un segno giusto: il caso
che quel test costruisce non è più raggiungibile dal dominio.

### 9.7 Cosa resta

* ✅ §9.3 guardia su `COMPLETATO` — **trigger**, due rami (fermo, abortito) +
  codice nuovo (`20260923-30`);
* ✅ §9.4 l'annullo chiude tutti gli esiti e scrive una riga di giornale, firma
  invariata (`20260923-31`);
* ✅ §9.5 allineamento dei lotti già annullati (`80_data 20260923-34`);
* ✅ §9.6 lettore `dbops` (`20260923-33`) + riga in `presidi.csv` + `COMMENT`
  della vista di `vendite` (`20260923-32`, solo `COMMENT ON VIEW`: la
  definizione non cambia);
* ✅ §9.6 pgTAP: `test-annullamento-chiude-la-vita-v1.sql` (nuovo, 17) e
  `test-lotti-attivita-stato-esecuzione-v2.sql` (9-12 riscritti, 14 → 15);
* ✅ manuale `fn_annulla_lotto_da_draft` riscritto: era fermo al 03-08 e diceva
  ancora `stato_lotto = COMPLETATO`;
* ✅ **Tid**: apply dei cinque changeSet e corsa pgTAP, nessuna regressione
  (2026-09-23, §9.9);
* 🔴 **BE, prima del merge**: `manage.py genera_error_policies` e commit di
  `error_policies_generated.py` (codice `E_LOTTO_COMPLETATO_NON_GUADAGNATO`).
  Senza, `test_error_policies_divergenza_db` è rosso in CI;
* ▶ **BE, da guardare**: i test Django e2e (`ZEROERP_TEST_DB_E2E=1`) che portano
  un lotto a `COMPLETATO` con errori aperti ora ricevono il rifiuto dal DB. Il
  runner non lo fa (chiede prima `fermo`), ma una fixture sì potrebbe;
* ▶ **A video**: un annullato mostra tutti i documenti `ESCLUSO` col motivo
  «Annullo del lotto …» nella lista gruppi — da guardare che si legga bene;
* ⚠️ debito dichiarato (§9.3): la matrice di `stato_lotto` in due sedi che
  dissentono, `fn_set_fatturazione_lotto_stato` morta. Cantiere a sé.

### 9.8 La consegna — 2026-09-23

| File | Che cosa |
| --- | --- |
| `20_code/vendite/20260923-30-create-trgfn-fatturazione-lotti-guard-completato` | `trgfn_fatturazione_lotti_guard_completato` + trigger `_a10_guard_completato_upd` |
| `20_code/vendite/20260923-31-update-fn-annulla-lotto-da-draft-chiude-esiti` | l'annullo chiude gli esiti (`ESCLUSO` + motivo) + riga `ANNULLO_LOTTO` nel giornale |
| `20_code/vendite/20260923-32-comment-vw-lotti-chiusi-con-gruppi-in-errore-invariante-vuoto` | `COMMENT ON VIEW`: invariante vuota, le due porte, pregresso chiuso |
| `20_code/dbops/20260923-33-create-vw-lotti-chiusi-con-errori-da-guardare` | il lettore a catalogo |
| `80_data/changelog/20260923-34-allinea-esiti-lotti-annullati` | una tantum: lotti già annullati come quelli di domani |
| `config/codici_errore.csv`, `config/messaggi_errore.csv` (id 1117), `dbops/presidi.csv` | codice nuovo, frase, riga di catalogo |
| `db/pgtap/vendite/test-annullamento-chiude-la-vita-v1.sql` | nuovo, 17 test, tutti su casi costruiti |
| `db/pgtap/vendite/test-lotti-attivita-stato-esecuzione-v2.sql` | 9-12 riscritti: il vecchio 11 fissava la contraddizione come attesa |
| `docs/it/dbzero/vendite/manual/fn_annulla_lotto_da_draft.md` | manuale riscritto |

⚠️ I numeri `-30 → -34` sono stati scelti **lontani** da quelli del cantiere
fixture, che il 23-09 avanzava in sequenza (`-01 → -10`).

**Le prove** — da owner, SQL **estratto** dagli YAML, in `BEGIN … ROLLBACK`;
fotografia degli oggetti vivi prima e dopo, identica (niente applicato).

* SQL estratto + righe CSV nuove + allineamento: compila, `plpgsql_check` a
  zero su entrambe le funzioni. Sulla macchina del 23-09 (fatto datato):
  **30 lotti annullati, 83 esiti chiusi**; la vista **7 → 0**;
  `fn_conta_presidio` del lettore = 0; `LTF-0010972` con i due esiti `ESCLUSO`
  e la sua riga di giornale; zero annullati con esiti aperti.
* `test-annullamento-chiude-la-vita-v1`: **16/17**. Il 16 (cecità senza veste)
  è **rosso da owner per costruzione** — l'owner attraversa la RLS — ed è lo
  stesso comportamento del gemello (test 18 di `test-lotti-fermi-verdetto-a-db-v1`,
  rosso da owner anche senza l'SQL nuovo). Da app deve essere verde.
* `test-lotti-attivita-stato-esecuzione-v2` adattato: **15/15**. La versione
  **originale** con l'SQL nuovo: rossi 9 e 10 — la modifica serviva.
* Con l'SQL nuovo in testa, verdi: `test-lotti-gruppi-esito` (13),
  `test-annulla-lotto-non-riscrive-stato-v1` (7), `test-annulla-lotto-vuoto-v1`
  (6), `test-annulla-lotto-task-runs-v1` (7), `test-fatture-log-trigger-sync` (8),
  `test-fn-get-or-create-lotto-emittente` (10), `test-catalogo-presidi-v1` (11),
  `test-available-actions-lotto-v1` (12), `test-fatturazione-reset-lotto-draft`
  (16); `test-lotti-fermi-verdetto-a-db-v1` 20/21, il 18 come sopra.
* Guardrail statici verdi: letterali SQL, `runOnChange`, preCondition/seed,
  DDL su trigger generati, GRANT batch, preambolo pgTAP.
* ⚠️ Non provato qui: l'upsert **completo** dei tre CSV (il mirror li rilegge
  interi, §11.2 delle linee guida) — si vede all'apply. ✅ Passato all'apply
  (§9.9).

### 9.9 ✅ Applicato — 2026-09-23

**Apply di Tid**, letto dal `databasechangelog`: `20260923-30`, `-31`, `-32`,
`-33` e `-34` tutti `EXECUTED` alle 15:43 (i tre mirror CSV riletti senza
rifiuti). **Corsa pgTAP di Tid: nessuna regressione.**

Riletto sul vivo dopo l'apply (fatto datato, 23-09):

| Che cosa | Valore |
| --- | --- |
| righe di `vendite.vw_lotti_chiusi_con_gruppi_in_errore` | **0** (erano 7) |
| `fn_conta_presidio('dbops.vw_lotti_chiusi_con_errori_da_guardare')` | **0** |
| esiti non `ESCLUSO` su lotti con stato abortito | **0** |
| `E_LOTTO_COMPLETATO_NON_GUADAGNATO` in `codici_errore` / `messaggi_errore` | 1 / 1 |
| `E_LOTTO_COMPLETATO_NON_GUADAGNATO` in `error_policies_generated.py` | ⛔ **0** — il passo BE manca |

**Per chiudere** (e solo questo):

1. 🔴 **BE**: `manage.py genera_error_policies` e commit di
   `error_policies_generated.py`, nello stesso giro del merge.

**Cosa passa a PROJECT_CONTEXT alla chiusura**, perché un debito lasciato in un
brief archiviato non lo rilegge nessuno:

* la matrice di `stato_lotto` in **due** sedi che dissentono (BE ammette
  `COMPLETATO → ERRORE`, `fn_set_fatturazione_lotto_stato` no) e la funzione di
  fatto morta — cantiere BE + DB (§9.3);
* la porta dell'esito ancora aperta (ERRORE marcato su un lotto già
  `COMPLETATO`): oggi la sorveglia il presidio a catalogo; chiuderla a DB è una
  decisione a sé.

Da guardare, ma non bloccante: a video un annullato mostra tutti i documenti
`ESCLUSO` con il motivo «Annullo del lotto …».
