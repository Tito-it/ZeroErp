# Analisi DB — magazzino: come si scrive un carico e uno scarico

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Richiesta di Tid, 2026-09-02: *«raccoglierei tutto quello che è
> scritto nei documenti e lo trasformerei in un solo documento di analisi carico e
> scarico magazzino; nei precedenti sostituiamo le parti relative con il link»*.
> ⭐ La ragione per cui è stato chiesto è la stessa che lo rende utile: il
> ragionamento su carico e scarico **esisteva già per intero, sparso su tre
> analisi**, e non si ritrovava. Nessuna delle tre lo aveva come argomento: una
> guardava la sorgente polimorfa, una la simmetria degli acquisti, una la
> produzione.
>
> **Stato al 2026-09-26:** 🟡 **analisi COMPLETA (M-1 → M-9 chiuse) e in gran
> parte COSTRUITA; restano i lotti 3 → 5.** Costruiti:
> [Lotto 1](../work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md) (DDL, RLS,
> 15-09), [Lotto 1-bis](../work-done/brief-db-emittente-di-default-un-bb-solo.md)
> (17-09), [Lotto 2](../work-done/brief-db-magazzino-lotto-2-motore.md) (primitiva,
> inventario, rettifica, disponibilità, orfani, prontezza — DB 18-09, archiviato
> 24-09), [2-bis BE/FE](../work-done/brief-db-magazzino-lotto-2-bis-be-fe.md) (23-09)
> e i [verbi con permesso](../work-done/brief-db-magazzino-verbi-con-permesso.md)
> (24/25-09). ⏳ Il **collaudo a video** di inventario e rettifica è di Tid
> ([collaudo](collaudo-in-app-magazzino-inventario-e-rettifica.md)).
> ⚠️ **Le §0 → §7 raccontano la struttura del 02-09 al presente**: il
> ragionamento è la sede delle decisioni e resta valido, ma dove dicono «oggi» si
> legge «il 02-09». Lo stato vero, voce per voce, è la colonna «Realizzato» di
> **§9**; la sequenza dei lotti è in **§8**.
>
> *Stato fino al 17-09, per la storia:* 🔵 APERTO — ANALISI INCOMPLETA; le §2 → §8
> erano il consolidamento, la §9 elencava ciò che mancava; nessun changeSet.
>
> ✅ **2026-09-14 — le decisioni che questo documento PRESUPPONE sono prese**
> (D-1, D-4, D-6, D-7, D-8 dell'[analisi aggancio
> §8-quater](analisi-db-magazzino-aggancio-documento-e-produzione.md), Tid).
> ⚠️ **La D-6 rovescia una riga di §6** — *«resta tutto nullable»* — ed è
> corretta lì, con la ragione. Il primo pezzo eseguibile è
> [brief-db-magazzino-lotto-1-terreno-vuoto.md](../work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md):
> tutto il DDL che M-1 → M-9 e le D hanno deciso, sul terreno vuoto, più il
> perimetro RLS di M-6 — che atterra **con** l'ancora, non dopo (§7-sexies,
> riquadro del 14-09).
>
> ⭐ **Da qui in avanti questa è la sede unica dell'argomento.** Gli altri tre
> documenti rimandano qui invece di ripetere; ciò che resta a loro, e perché, sta
> in §10.
>
> ⚠️ **Perimetro:** il **movimento** — il vocabolario che lo classifica, il verso
> della quantità, chi lo scrive, come non scriverlo due volte, e come si rilegge.
> ⛔ **Non** è qui la scelta di *come un movimento dichiara la propria origine*:
> quella è la D-1 dell'[analisi
> aggancio](analisi-db-magazzino-aggancio-documento-e-produzione.md), e questo
> documento la **presuppone** senza deciderla.

---

## 0. In due parole, senza tecnicismi

> ⚠️ **Fotografia del 2026-09-02.** Oggi il registro **ha** chi ci scrive (la
> primitiva `magazzino.fn_scrivi_movimento`, raggiunta solo dai verbi di
> inventario e rettifica), il verso è presidiato da un guard e le causali che
> mancavano ci sono (16 in tutto). Vedi §9.

Un magazzino fa due cose: **fa entrare** merce e **la fa uscire**. Ogni volta
scrive una riga in un registro — quanto, di che articolo, quando, e per quale
motivo.

Oggi in ZeroErp quel registro **esiste come mobile e non come meccanismo**: le
tabelle ci sono, i motivi (le «causali») pure, ma:

* **nessun programma ci scrive dentro.** Non è che scrive male: non scrive
  affatto;
* **non è deciso in che verso si scrive una quantità.** Il motivo dice «questo è
  un'uscita», ma niente obbliga la quantità a essere negativa — e chi legge la
  giacenza somma senza guardare il motivo. Due modi di dire la stessa cosa che non
  si parlano;
* **manca il motivo per un paio di casi normali**: caricare ciò che si è
  prodotto, e restituire merce a un fornitore;
* ⭐ **e non c'è una sola riga da correggere**, perché il magazzino non è mai
  partito. È il momento in cui tutto questo costa zero.

---

## 1. Che cosa è stato letto, e di che natura è

Consolidato il **2026-09-02** da tre analisi del 01-09, più letture nuove fatte
lo stesso giorno **sul database vivo** (`magazzino.causali` per intero, i CHECK di
`causali` e di `movimenti`).

⚠️ Sono **letture di struttura**: colonne, vincoli, righe di catalogo, corpo delle
funzioni, chi legge e chi scrive. ⛔ Dove compare «zero» non è un argomento: è la
constatazione che non c'è una bonifica da fare.

---

## 2. Il vocabolario: le dieci causali, per intero

⭐ **Nessuno dei tre documenti di origine le aveva tutte** — ognuno ne mostrava la
fetta che gli serviva, ed è una delle ragioni per cui i buchi non si vedevano.

| Causale | Segno | Valorizza | Ambito | Note |
| --- | --- | --- | --- | --- |
| `CARICO_ACQ` | **+1** | `cmp` | ⛔ NULL | carico da DDT acquisto |
| `SCARICO_VEN` | **−1** | `cmp` | ⛔ NULL | scarico per DDT vendita · `abilita_billing` |
| `TRASF_OUT` | **−1** | `none` | ⛔ NULL | richiede magazzino di destinazione |
| `TRASF_IN` | **+1** | `none` | ⛔ NULL | la gemella in entrata |
| `RETT_POS` | **+1** | `cmp` | ⛔ NULL | `is_rettifica` |
| `RETT_NEG` | **−1** | `cmp` | ⛔ NULL | `is_rettifica` |
| `ODL_USCITA_MAT` | **−1** | `cmp` | ⛔ NULL | `richiede_odl` · `abilita_billing` |
| `ODL_ENTRATA_MAT` | **+1** | `cmp` | ⛔ NULL | `richiede_odl` |
| `ASSET_INSTALL` | **−1** | `cmp` | ⛔ NULL | richiede seriale · `abilita_billing` |
| `ASSET_RIENTRO` | **+1** | `cmp` | ⛔ NULL | richiede seriale |

I due CHECK che governano la tabella: `segno ∈ {−1, 0, 1}` e
`impatto_valorizzazione ∈ {cmp, fifo, none}`.

⭐ **Due cose che si vedono solo mettendole in fila:**

* **il trasferimento non valorizza** (`none` su entrambe le gemelle), e ha ragione:
  la merce cambia scaffale, non valore. È l'unica coppia che lo dichiara, ed è un
  pezzo di disegno **corretto** che nessuno aveva ancora scritto;
* ⛔ **l'ambito è `NULL` su tutte e dieci.** Il vocabolario dei sei ambiti
  (`VENDITE`, `ACQUISTI`, `ODL`, `TRASF`, `INVENTARIO`, `GENERICO`) esiste, è
  popolato, e **non è collegato a niente**.

---

## 3. Quello che al vocabolario manca

| Manca | Perché è un caso normale, non un caso raro |
| --- | --- |
| ⛔ **il versamento del prodotto finito** (+1) | ci sono *uscita materiali* e *rientro materiali* per l'ODL: con queste dieci causali si possono **consumare i componenti e non caricare ciò che si è prodotto** |
| ⛔ **lo scarico per reso a fornitore** (−1) | c'è `SCARICO_VEN` per il DDT di vendita, non c'è l'equivalente per la merce che torna indietro al fornitore |
| 🔴 ⛔ **il carico da reso CLIENTE** (+1) | *(aggiunto il 2026-09-04)* `vendite.resi` è **in esercizio**: la merce che il cliente restituisce deve rientrare, e fra le dieci non c'è. ⚠️ `ASSET_RIENTRO` copre i **soli serializzati** |
| 🔴 ⛔ **l'inventario iniziale** | *(aggiunto il 2026-09-04)* la §8 lo mette come **passo 2**, cioè il primo carico in assoluto — e non ha una causale propria: userebbe `RETT_POS`, che è marcata `is_rettifica` e **dice un'altra cosa**. ⚠️ E l'ambito `INVENTARIO` continuerebbe a non avere righe |

E **tre** colonne che **esistono e non le legge nessuno** — verificato sul codice
(`20_code/`, `backend/apps/`, `frontend/src/`):

* `causali.richiede_odl`, seminato a `true` su due causali;
* `causali.contabilizza_cdc`, che punta a un **centro di costo che non esiste** in
  nessuno dei 21 schemi;
* 🔴 `causali.abilita_billing` — *(verificato il 2026-09-04 su rilievo esterno: la
  prima stesura lo mostrava nella tabella del §2 su tre causali e non lo nominava
  mai)*. **Zero funzioni, zero viste, zero codice** lo leggono: è della stessa
  specie, e restava un quarto flag di cui nessuno sapeva se fosse armato.

⚠️ Sono la stessa specie dell'ambito vuoto: *strutture che sembrano funzioni*. Chi
legge il DDL conta tre presidi, e i presidi sono zero.

✅ **DECISO (Tid, 2026-09-14 — D-8 dell'analisi aggancio): l'ambito si ritira,
con i tre flag.** `ambito_causale_id`, la tabella `ambito_causale`,
`richiede_odl`, `contabilizza_cdc` e `abilita_billing` **escono** nel Lotto 1
(✅ **uscite**: `20260915-02`, `-03`; oggi le causali sono **16** — le dieci del §2,
`CARICO_RESO_VEN`, `SCARICO_RESO_ACQ`, `ODL_VERSAMENTO_PF`, `INV_INIZIALE`,
`STORNO_POS`, `STORNO_NEG`).
La ragione è in §5-bis: la primitiva è guidata da due cataloghi e nessuna di
queste colonne è fra i suoi controlli. Le **quattro causali mancanti** entrano
nello stesso lotto come righe di seed, più le **due dello storno** (§7-quinquies,
riquadro del 14-09).

---

## 4. ✅ Il verso della quantità — DECISO

⭐ **È il buco che finora non aveva una sede**, ed è il motivo principale per cui
questo documento esiste. Nelle tre analisi era citato come «materia dell'analisi
successiva» — e contemporaneamente come **passo 1**, cioè la prima cosa da chiudere.
Una voce che sta insieme «fuori perimetro» e «prima di tutto» non la prende in
mano nessuno.

**I fatti, verificati il 2026-09-02:**

* `magazzino.causali.segno` vale `−1`, `0` o `+1` e dichiara la **direzione** del
  movimento;
* su `magazzino.movimenti` l'unico vincolo sulla quantità è
  `chk_mag_movimenti_qta_non_zero`: `qta` deve essere diversa da zero. **E basta**;
* ⛔ **niente lega il segno di `qta` al `segno` della causale.** Si può scrivere
  `qta = −10` con `CARICO_ACQ` (+1), o `qta = +10` con `SCARICO_VEN` (−1), e il
  database accetta entrambi senza fiatare;
* `magazzino.vw_giacenza` è `sum(qta) GROUP BY articolo, magazzino`: **somma la
  quantità e non guarda mai la causale**.

**Le due letture possibili, e sono incompatibili:**

| | Chi porta il verso | Conseguenza |
| --- | --- | --- |
| **A** | la **quantità**: un'uscita si scrive `−10` | `causali.segno` diventa una **ridondanza dichiarativa**, utile a leggere ma non a calcolare. `vw_giacenza` è già corretta |
| **B** | la **causale**: `qta` è sempre positiva e il segno lo mette il motivo | ⛔ `vw_giacenza` è **sbagliata oggi** e va riscritta con il join; e `qta` positiva rende impossibile un movimento che «annulla» senza cambiare causale |

⛔ **Oggi il modello ammette entrambe, quindi non ne garantisce nessuna.** Ed è la
peggiore delle tre situazioni: due scrittori diversi possono scegliere convenzioni
opposte, la giacenza somma tutto insieme, e **il numero sbagliato non ha nessun
sintomo** — non c'è errore, non c'è vincolo violato, c'è solo una quantità che non
torna, mesi dopo, quando nessuno sa più da dove viene.

⇒ **Andava deciso prima della prima riga**, ed era la vera prima voce del piano.
✅ **Deciso il 2026-09-02.**

---

### ✅ DECISIONE (Tid, 2026-09-02): **A — il verso sta nella quantità**

> Un'uscita si scrive `−10`. `causali.segno` resta la **dichiarazione** di che
> cosa quella causale deve fare, e diventa il **validatore**: non l'operatore del
> calcolo.

⛔ **La ragione NON è che `vw_giacenza` è già scritta così.** Quella è una
coincidenza comoda, non un argomento — e se fosse stata l'unica, la decisione
sarebbe stata presa da una vista invece che dal modello. Le ragioni sono due.

**1. Quale dei due errori è silenzioso.**

| | Chi può sbagliare | Che cosa succede |
| --- | --- | --- |
| **A** | chi **scrive** con il verso opposto alla causale | ⭐ lo ferma un guard: **un posto solo, errore rumoroso** |
| **B** | chi **legge** dimenticando il join alle causali | ⛔ numero sbagliato, **nessun errore, mai** — e i lettori saranno molti: giacenza, disponibilità, valorizzazione, movimenti per periodo, export |

⛔ **E non è un rischio teorico: è già successo.** `vw_giacenza` **è** quel lettore
distratto — somma `qta` senza guardare la causale — ed è lì da mesi senza che
niente lo segnalasse. B chiede a ogni lettore futuro di non ripetere l'errore che
il primo lettore ha già fatto.

**2. ⭐⭐ Sotto B la giacenza dipende da una riga MODIFICABILE di un catalogo.**
`magazzino.causali` è editabile: se qualcuno porta `SCARICO_VEN.segno` da `−1` a
`+1`, **tutte le uscite passate diventano entrate**. La storia si riscrive
all'indietro, senza migrazione, senza traccia e senza errore.

Sotto A no: il movimento **porta il proprio verso**, ed è un fatto immutabile. ⭐ È
la stessa ragione per cui la fatturazione porta `prezzo_snapshot` invece di
ricalcolare dal listino: **il passato non si ricava da una lookup**. Per un ledger,
che *è* storia, vale a maggior ragione.

### Come si presidia — e c'è un vincolo tecnico

⛔ **Un `CHECK` non può guardare un'altra tabella**, quindi `sign(qta) =
causali.segno` **non è esprimibile come CHECK**. Serve un **trigger guard** in fase
`_a10_` su `movimenti` e su `movimenti_attesi`.

⚠️ **Sconsigliata la scorciatoia di copiare `segno` sulla riga del movimento**:
avremmo il verso in **tre sedi** — nella quantità, nella colonna copiata e nella
causale. Sotto A il verso *è* la quantità: sulla riga non serve altro.

⭐ E il guard non sostituisce la funzione madre (§5): la madre dà il messaggio
comprensibile, il trigger è **la rete**.

### Le conseguenze, tutte

| Dove | Che cosa cambia |
| --- | --- |
| `magazzino.vw_giacenza` | ✅ **resta com'è** — `sum(qta)` è corretta sotto A. ⚠️ Va però messo nel suo `COMMENT` *perché* è corretta, o il prossimo lettore la crederà incompleta e ci aggiungerà un join che raddoppierebbe il segno |
| `movimenti_attesi` | ⛔ **cade `chk_mag_res_qta_pos`** (`qta > 0`): anche gli attesi sono firmati. 🔴 *(La «formula unica» che stava qui — `sum(movimenti) + sum(movimenti_attesi)` — è stata **ritirata il 2026-09-04**: era vera quando la tabella teneva tutte le aspettative, ma dopo la §7-bis ne tiene solo i **blocchi manuali**, quindi quella somma non dà la giacenza prevista — dà la giacenza meno i blocchi. La formula corretta è in §7-bis, «La formula di disponibile».)* |
| la vista di §7-bis | «impegnata» e «in arrivo» si separano **filtrando sul segno**; il valore assoluto mostrato all'utente è **presentazione**, non modello |
| il guard | nuovo trigger `_a10_` su entrambe le tabelle |

### ⚠️ Il residuo di questa decisione: la causale con `segno = 0`

Il CHECK di `causali.segno` ammette **`0`**, e nessuna delle dieci causali lo usa.
⛔ Ma sotto A una causale a segno zero **non è scrivibile**: dovrebbe produrre
`qta = 0`, che `chk_mag_movimenti_qta_non_zero` vieta.

E non è un caso di scuola: `movimenti` ha `ubicazione_id_from` e `ubicazione_id_to`,
cioè **lo spostamento fra ubicazioni dentro lo stesso magazzino** — che la giacenza
per magazzino non la cambia.

✅ **DECISO (Tid, 2026-09-02): lo `0` esce dal CHECK.** `causali.segno` ammette
solo `−1` e `+1`.

⇒ Ne discende che **lo spostamento fra ubicazioni si modella come coppia OUT/IN**,
esattamente come il trasferimento fra magazzini: due movimenti firmati, tenuti
insieme dallo stesso `transfer_uid`. Non serve niente di nuovo — è la forma che il
trasferimento usa già.

> ⚠️ *Corretto il 2026-09-26*: «non serve niente di nuovo» vale per il **ledger**,
> non per il documento. Lo spostamento fra ubicazioni ha bisogno di un documento
> (sotto D-6 ogni movimento ne ha uno): per D-L2-g è `magazzino.trasferimenti`
> come trasferimento **interno**, che deve prendere `ubicazione_id_da`/`_a` sulle
> righe e allargare `chk_mag_trasferimenti_da_a_distinti` a «magazzini **o**
> ubicazioni diversi» — Lotto 3. E vale solo sui magazzini con
> `usa_ubicazioni = true` (D-L2-m).

⭐ **E toglie dal catalogo un valore che nessuno usava e che il modello non sapeva
scrivere**, cioè una terza istanza della classe «esiste e non è armata» che questi
documenti inseguono da due giorni. ⚠️ Un valore ammesso da un CHECK e inesprimibile
nel modello è peggio di un valore assente: chi legge il CHECK crede che il caso sia
previsto.

📌 **M-1 è chiusa per intero.**

---

## 5. Chi scrive un movimento: nessuno

> ⚠️ **Fotografia del 2026-09-02.** Dal 18-09 scrive **una** funzione,
> `magazzino.fn_scrivi_movimento` (DEFINER del proprietario, con `REVOKE` di
> scrittura all'app su `movimenti` e `valore_giacenza`); dal 24-09 l'app non la
> esegue più nemmeno e passa dai verbi `fn_posta_inventario` /
> `fn_posta_rettifica`, che nella prima riga chiamano `script.fn_guard_azione`
> su `registra_magazzino`. Il perimetro RLS di `magazzino` esiste dal 15-09
> (`20260915-16`). La sezione resta come il **perché** di §5-bis.

⚠️ **`magazzino.movimenti` non è scritto da nessuna parte.** Verificato: lo schema
ha **due** funzioni in tutto — `fn_get_magazzino_note` e `trgfn_magazzini_normalize`
— nessuna delle due tocca il ledger, e `backend/apps/magazzino/` è uno scheletro
(`apps.py` e poco altro).

⇒ Il registro è **una struttura senza alimentatore**. E la domanda che ne discende
non è «quando lo scriviamo», è **«chi ha il diritto di scriverlo»**:

* ⭐ se la scrittura passa da **una funzione madre sola**, il verso della quantità
  (§4), la coerenza col motivo e l'identità del movimento (§6) si presidiano **in
  un posto solo**, e il resto del sistema non ha bisogno di sapere niente;
* ⛔ se invece scrivono in tanti, ognuna di quelle regole va ripetuta ovunque — ed
  è la forma di duplicazione che questo progetto paga più cara.

⚠️ **E c'è un corollario sui permessi, non sui vincoli** (vedi §6): un vincolo di
unicità non ferma chi scrive fuori dalla porta, perché chi scrive fuori dalla porta
non compila nemmeno i campi su cui il vincolo poggia. *La porta si chiude con i
`GRANT`, non con gli indici.* Il perimetro RLS/permessi di `magazzino` **oggi non
esiste**.

---

## 5-bis. ✅ La forma di chi scrive — DECISO (M-2)

> **Decisa con Tid il 2026-09-02**, in quattro passaggi: la forma a due livelli,
> la primitiva guidata dalle causali, il blocco su magazzino+articolo, e — su
> osservazione di Tid — lo **spostamento del controllo merce prima della
> scrittura**, che ha semplificato la primitiva invece di complicarla.

### I due livelli

⛔ **«Una funzione sola» si rompe su un caso normale**: il trasferimento non scrive
un movimento, ne scrive **due** — l'uscita da un magazzino e l'entrata nell'altro —
e devono essere scritti insieme, o la merce sparisce nel mezzo. Lo stesso vale per
lo spostamento fra ubicazioni (§4) e per la produzione, che consuma componenti e
versa un prodotto.

| Livello | Che cosa fa |
| --- | --- |
| **la primitiva** — scrive **un** movimento | tutti i controlli duri, in un posto solo |
| **le operazioni** — carico, scarico, trasferimento, versamento… | ⛔ non ricontrollano niente: chiamano la primitiva una o più volte, dentro **una transazione sola** |

⭐ **E la regola di sicurezza della §5 diventa esprimibile**: su `magazzino.movimenti`
scrive **solo la primitiva**. È un `GRANT`, non un vincolo — ed è l'unica forma che
ferma davvero chi non passa dalla porta.

### ⭐ La primitiva è guidata dalle causali, e non è una scelta di stile

I controlli da fare a ogni scrittura sono già **descritti a catalogo**: non serve
una funzione per tipo di movimento, serve **una funzione che legge la causale**.

🔴 **Tabella riscritta il 2026-09-04**: la prima versione elencava **sette** colonne
tutte di `causali`, e le decisioni successive ne hanno tolte quattro — `richiede_lotto`
e `richiede_seriale` ritirate da §7-quater, `richiede_magazzino_dest` resa ridondante
dal modello a coppie, `impatto_valorizzazione` svuotata da §7-ter. ⛔ Lasciandola,
il prossimo lettore avrebbe implementato controlli su colonne che nel frattempo
abbiamo tolto.

| Controllo | Da quale colonna è guidato |
| --- | --- |
| il verso della quantità | `causali.segno` (§4) |
| giacenza che può andare sotto zero | `causali.consente_stock_negativo` |
| valorizza o no | `causali` (§7-ter) |
| l'articolo movimenta giacenza? | `catalogo.articoli.gestito_a_magazzino` |
| lotto obbligatorio | `catalogo.articoli.requires_lotto` (§7-quater) |
| seriale obbligatorio | `catalogo.articoli.requires_serial` (§7-quater) |

⭐ **L'argomento regge, ma va detto meglio**: la primitiva non è guidata *dalle
causali*, è guidata **dal catalogo** — e i cataloghi sono **due**. La causale dice
che cosa fa **questo movimento**; l'articolo dice com'è fatta **questa merce**.
⇒ Resta vero il guadagno: la causale del versamento di produzione, che oggi manca,
costerà **una riga di seed e non una di codice**.

⭐ **Il guadagno si misura su un caso che abbiamo già**: la causale del **versamento
di produzione**, che oggi manca (§3), non richiederà **una riga di codice**. È una
riga di catalogo. Stessa forma di `famiglie_documento`, che governa la numerazione
di cinque documenti con una funzione sola.

### Il blocco contro la giacenza negativa

| Aspetto | Decisione |
| --- | --- |
| **granularità** | `(magazzino_id, articolo_id)` — ⭐ perché **coincide con la regola protetta**: il vincolo è «questo articolo in questo magazzino non va sotto zero», ed è la stessa coppia su cui `vw_giacenza` raggruppa |
| **quando** | ⛔ **solo in uscita**, e solo se la causale non ammette la giacenza negativa |
| **momento** | **prima** di leggere la giacenza: leggere e poi bloccare significa aver letto un numero già vecchio |
| **durata** | transazionale — si libera da sé al commit, come già fa la numerazione |

⭐⭐ **Il «solo in uscita» non è un'ottimizzazione: elimina una classe di errori.**
Un'entrata non può violare l'invariante, quindi non ha niente da proteggere. Se
prendessimo il blocco anche in entrata, un trasferimento A→B e uno B→A dello stesso
articolo, simultanei, **si impianterebbero a vicenda** — il primo tiene A e aspetta
B, il secondo il contrario. In esercizio si manifesta come *«ogni tanto il sistema
si pianta e nessuno capisce perché»*.

⚠️ **La chiave del blocco va costruita**: il meccanismo lavora con numeri interi e
`articolo_id` è un **UUID**. Serve un valore ricavato dalla coppia. ⭐ Due coppie
diverse possono, raramente, produrre lo stesso valore: **non è un problema di
correttezza** — nel caso peggiore due scarichi che non c'entrano si mettono
brevemente in fila. Va scritto, perché è il dettaglio su cui qualcuno si allarma sei
mesi dopo.

### ⛔ Che cosa la primitiva NON fa: domande

> **Osservazione di Tid, 2026-09-02, ed è quella che ha cambiato il disegno:**
> *«il messaggio di conferma dovrebbe comparire prima, quando l'operatore conferma
> il DDT o l'ordine; quindi la scrittura di movimento va liscia»*.

La prima stesura prevedeva un rifiuto-poi-conferma **dentro la scrittura**: la
primitiva si rifiutava con un avviso, il frontend chiedeva, e una seconda chiamata
portava un flag «lo so, procedi». ⛔ **Era sbagliato per due ragioni.**

1. **Non si fa una domanda a una persona mentre si tiene un blocco.** O la
   transazione resta aperta ad aspettare un click — e quell'articolo è fermo per
   tutti — oppure aborta dopo che l'operatore ha già fatto tutto il lavoro.
2. **Chiedeva nel momento sbagliato.** Alla scrittura la decisione è già presa: la
   conferma diventa un timbro.

⇒ **I due controlli si separano, e hanno natura diversa:**

| | Che cosa protegge | Dove sta | Se scatta |
| --- | --- | --- | --- |
| **giacenza disponibile ≥ 0** | un **vincolo vero** | nella primitiva, dentro il blocco | è un **errore**, senza domande |
| **impegno derivato** | ⛔ **niente**: è un calcolo, e contiene la riga che il documento stesso serve | — | ⛔ non scatta mai |
| **blocco esplicito di un altro** | ⭐ **la decisione di una persona** | nella primitiva **e** alla conferma del documento, tramite la **stessa funzione di controllo** | ⛔ **ferma**, finché qualcuno non lo libera |

🔴 **Correzione del 2026-09-02 (seconda revisione).** La prima stesura di M-2 diceva
che la primitiva guarda **solo il fisico** e che l'impegno è sempre un semplice
avviso. ⛔ **È stato corretto in §7-bis**: un blocco esplicito che si può scavalcare
**mente**, perché resta a riservare merce che non c'è più. ⇒ La primitiva guarda
**il fisico meno i blocchi espliciti che non appartengono a questo documento** —
i propri si escludono attraverso l'identità della sorgente (§6).

⭐ **E il controllo è una funzione separata che non scrive mai**, chiamata sia dalla
UI alla conferma del documento sia dalla primitiva prima di scrivere. ⛔ **Non un
flag sulla primitiva**: con un flag, chi può controllare può anche scrivere — e i
permessi sono l'unica cosa che ferma davvero chi non passa dalla porta (§5).

⭐ **E anticipare non elimina il controllo duro: lo rende MUTO nel caso normale.**
Resta alla scrittura perché fra la conferma e il movimento passa del tempo, e in
quel tempo un altro operatore può aver preso la stessa merce. Ma smette di essere il
luogo della conversazione: parla solo su una **corsa vera**, e allora ha ragione.

⚠️ *«La scrittura va liscia»* è quindi il **risultato atteso**, non una garanzia
costruita: toglierlo darebbe giacenza negativa in silenzio.

### I due momenti della conferma, che sono due domande diverse

| Momento | La domanda | Che cosa deve vedere |
| --- | --- | --- |
| **conferma dell'ORDINE** | «posso **prometterla**?» | disponibile + **in arrivo** + le date |
| **conferma del DDT** | «posso **spedirla adesso**?» | ciò che c'è fisicamente, e a chi è promesso |

⭐⭐ **E la prima è dove si decide la data di consegna confermata**: l'operatore vede
*«ne chiedono 10: 3 ci sono, 7 arrivano il 20»* e conferma il 22, non il 15.

⇒ È il **terzo cantiere indipendente** che chiede
`acquisti.ordini_righe.data_consegna_confermata` — dopo la produzione e la merce in
arrivo. ⭐ Quando tre cose che non si parlano chiedono lo stesso dato, quel dato non
è un'opinione.

⭐ **E non serve costruire niente per mostrarlo**: entrambe le domande leggono la
**stessa vista** della §7-bis — effettiva, impegnata, in arrivo, per articolo, con
il dettaglio dei documenti. Cambia quale colonna si guarda, non il meccanismo.

### La traccia della decisione

🔴 **Ridimensionata il 2026-09-02.** Questa parte nasceva dall'idea che confermare
un documento su merce impegnata fosse una decisione da tracciare. ⛔ **Per
l'impegno derivato non lo è** — vedi §7-bis, «quando NON si fa»: non c'è nessuna
promessa da scavalcare, e l'impegnato contiene la riga che il documento stesso sta
servendo.

⇒ **Resta vero solo per il blocco manuale**, dove la conferma scavalca l'atto di una
persona. Lì la traccia va **sul documento** — sul DDT o nel suo giornale — e vale la
divisione generale: **il ledger registra i fatti, il documento registra le
decisioni.**

⚠️ **Non si limita invece CHI può confermare**: sarebbe un permesso nuovo per un
caso di cui non sappiamo la frequenza. Si registra, non si ingabbia.

### 📌 Che cosa resta aperto, e non è di questo documento

Il meccanismo delle azioni sui documenti è oggi **binario**: permessa, oppure
disabilitata con il motivo — e il flag si ricava dal motivo (*motivo assente =
permessa*). ⛔ Non esiste lo stato «permessa, ma con un avviso».

🔴 **Ma il perimetro si è ristretto molto il 2026-09-02** (§7-bis): per l'impegno
**derivato** l'avviso non si fa affatto, quindi **non c'è niente da esprimere** e
quel pattern **non va toccato**. Il terzo stato serve solo per il **blocco manuale**
— raro, deliberato, e con una persona dietro.

⚠️ ⭐ **Vale la pena che sia scritto**: senza questa riga, fra sei mesi qualcuno
aggiunge un quarto campo a un meccanismo che ne ha già tre con tre nomi diversi,
credendo di completarlo.

---

## 6. L'identità di un movimento: la regola anti-doppio

> **Origine:** appunti di revisione portati da Tid il 2026-09-01 (*«quell'indice va
> tolto, non riparato: è una chiave di idempotenza travestita da vincolo
> semantico»*) e la domanda che ne è seguita — *«la stessa colonna potrebbe
> impedire anche il doppio carico, quando riceveremo gli acquisti?»*. Sì, e la
> risposta completa è questa sezione.
>
> ⚠️ **È una proposta, non una decisione presa.** La **D-4** resta di Tid ed è registrata
> nell'[analisi aggancio §8](analisi-db-magazzino-aggancio-documento-e-produzione.md): qui c'è la terza delle sue tre forme, scritta per intero perché sia scegliibile.

### Il difetto non è che l'indice sia sbagliato: è che risponde a un'altra domanda

`uq_mag_movimenti_docref` guarda il **documento**. Ma il documento è il
*contesto* di un movimento, non la sua *identità*: da una riga di documento
possono nascere legittimamente N movimenti, e già oggi ne nascono due (il
trasferimento). ⛔ Vincolare sul documento significa scrivere «una riga di
documento, un movimento», che è una frase **falsa adesso**, non fra due cantieri.

⭐ E c'è una protezione buona nascosta là dentro che nessuno aveva dichiarato: di
rimbalzo, quell'indice impedisce anche il **doppio scarico** della stessa riga di
bolla. Togliendolo si porta via anche quella. ⚠️ **Per questo la sostituzione va
decisa insieme alla rimozione, non a valle**: toglierlo e basta lascia scoperto un
caso che capita davvero.

### Il precedente è già in esercizio, e non è una tabella

Lo stesso identico problema — *un batch rilanciato non deve spingere due volte la
stessa riga* — è già risolto nella pipeline di fatturazione, ed è risolto con una
**colonna**: `vendite.commesse_attivita.segment_key`, con
`uq_commesse_attivita_commessa_segment` su `(commessa_id, segment_key)`. Le chiavi
sono composte a mano e ricalcolabili — verificato il 2026-09-01, i prefissi in uso
sono `ORD`, `DDT`, `PREV`, `MAN` (es. `ORD:{uid}:R:{riga}`).

⛔ **Una tabella dedicata «registro degli scarichi» è la versione debole**, e va
scartata per una ragione di modello: esisterebbe **solo per reggere un vincolo**,
non risponde a nessuna domanda che qualcuno farebbe, e crea **due sedi dello
stesso fatto** — il ledger dice «questa riga ha scaricato», il registro pure. Chi
scrive un movimento senza passare di lì le separa in silenzio.

⭐ **Quando invece una tabella è giusta**: quando la relazione *è* un dato che
qualcuno legge. È il caso di `vendite.ordini_righe_fulfillment`, che esiste perché
«quanto manca da evadere?» è una domanda vera — e l'unicità gli viene in regalo.
Per lo scarico quella domanda non c'è: **il movimento stesso è la risposta**.

### La proposta

🔴 **Riscritta il 2026-09-02 dopo un rilievo di Tid**, e il rilievo cambia la
forma. La prima stesura proponeva una **chiave testuale composta a mano**
(`operazione_key`). ⛔ Se la D-1 atterra sul catalogo, il movimento porta **già**
`sorgente_tipo_id` più la chiave del record: una stringa che ripete quelle
informazioni è una **seconda sede dello stesso fatto** — precisamente ciò che
questo documento contesta al §2 e che l'analisi acquisto contesta a
`ddt.ordine_id`. *Non si può denunciare un doppio e poi introdurne uno.*

⭐ **La forma giusta è derivata, non parallela**: l'identità di un movimento è
**la sua sorgente più il verbo dell'operazione**.

| Cosa | Come |
| --- | --- |
| Identità del movimento | `(sorgente_tipo_id, chiave della sorgente, verbo, **discriminante fisico**)` |
| Colonna nuova | solo il **verbo**: `operazione_verbo` (`SCARICO`, `CARICO`, `OUT`, `IN`, `PRELIEVO`, `VERSAMENTO`, `STORNO`, …) |
| Discriminante fisico | `asset_id`, `lotto_id`, `ubicazione_id` — **colonne che ci sono già** (§7-quater) |
| Il vincolo | `UNIQUE` **parziale**, attivo dove la sorgente è valorizzata |

#### 🔴 Perché il discriminante fisico — correzione del 2026-09-04

La prima stesura fermava l'identità a **(sorgente, chiave, verbo)**. ⛔ **Non regge**,
e la contraddizione nasce con la §7-quater scritta lo stesso giorno:

* §7-quater impone `|qta| = 1` con un seriale, e che **decida l'articolo**. ⇒ scaricare
  una riga di DDT da **30 pezzi serializzati** significa scrivere **30 movimenti** con
  la stessa sorgente (`DDT_VENDITA_RIGA:47`) e lo stesso verbo (`SCARICO`): il vincolo
  li **respinge tutti tranne il primo**;
* stessa cosa, senza seriali, per una riga servita da **due lotti**, e per una riga
  prelevata da **due ubicazioni** — casi che §7-quater rende normali, tanto che la
  vista fine per ubicazione esiste apposta.

⚠️ E le due eccezioni previste dalla prima stesura non coprono nulla di tutto questo:
il **trasferimento** se la cava con un verbo diverso, il **ricevimento parziale** con
una sorgente propria — ma qui **non c'è nessun record di operazione** da usare come
sorgente, a meno di inventare un «prelievo» per singolo pezzo, che è irrealistico.

⇒ **Il discriminante entra nella chiave**, e non è una colonna in più: `asset_id`,
`lotto_id` e `ubicazione_id` sono **già** sulla riga per decisione della §7-quater.
⭐ Ed è corretto anche concettualmente: due movimenti dalla stessa riga di documento
**sono movimenti diversi** se riguardano pezzi, lotti o scaffali diversi.

⚠️ **Resta un caso scoperto, e va dichiarato**: stessa sorgente, stesso verbo, stesso
lotto, stessa ubicazione, nessun seriale — cioè lo **stesso prelievo fatto in due
riprese** senza niente che le distingua. Se quel caso è reale serve un **progressivo
di occorrenza** nella chiave; se non lo è, il discriminante fisico basta. ⛔ Va deciso
**prima del passo 3 di §8**, che è esattamente dove nasce.
✅ **DECISO (Tid, 2026-09-14 — D-4): niente progressivo.** Il caso non esiste se
vale la condizione 1 qui sotto: *la chiave la compone l'operazione* ⇒ un'operazione
parziale è **un record per tranche**, e due riprese sono due record. Va nel
`COMMENT` del vincolo. ⚠️ E con D-6 (sorgente `NOT NULL`) il vincolo è **pieno**,
non parziale — e va scritto `NULLS NOT DISTINCT`, perché `asset_id`, `lotto_id` e
`ubicazione_id` restano nullable e due NULL in un indice unico sono **distinti**:
senza quella clausola l'anti-doppio non scatterebbe proprio sui movimenti senza
lotto né seriale, cioè i più comuni (è la trappola dell'[analisi aggancio §5](analisi-db-magazzino-aggancio-documento-e-produzione.md)).
✅ **Affinamento confermato da Tid il 2026-09-15 (D-L1-c)** — e da allora la
riga «Colonna nuova: `operazione_verbo`» della tabella sopra **non vale più**: il «verbo» è
**la causale stessa** — `TRASF_OUT`/`TRASF_IN` distinguono già le due righe
del trasferimento, e uno storno ha una causale sua — senza una colonna
`operazione_verbo`, che sarebbe un vocabolario parallelo alle causali. Il vincolo
costruito è `uq_mag_movimenti_identita` su `(sorgente_tipo_id, sorgente_riga,
sorgente_uid, causale_id, asset_id, lotto_id, ubicazione_id)` `NULLS NOT DISTINCT`
(`20260915-05`), col `COMMENT` sull'operazione-per-tranche.
| `uq_mag_movimenti_docref` | ⛔ si **toglie** |
| `transfer_uid` | resta, e fa il lavoro **opposto**: raggruppa i due movimenti di un trasferimento (il suo indice è **non** unico, apposta). Una dice «questi vanno insieme», l'altra «questo esiste una volta sola» |

⭐ **Dove l'operazione è essa stessa un record, la sorgente È l'operazione** — e
allora non c'è più niente da comporre: il ricevimento, il prelievo, la riga
d'inventario hanno un id, e quello è la chiave. ⚠️ Ne discende che il catalogo
deve conoscere anche le **operazioni**, non solo i documenti commerciali: è
l'allargamento che la **D-7** già richiede — e in parte la **D-1** — non un costo
nuovo. 🔴 *(Corretto il 2026-09-04: la prima stesura citava la D-6, che riguarda
invece se un movimento **senza documento** sia ammesso.)*
⭐ E il precedente c'è: `config.sorgenti` porta già **cinque sorgenti di riga** —
`DDT_VENDITA_RIGA`, `ORDINE_VENDITA_RIGA`, `FATTURA_RIGA`, `CONTRATTO_RIGA`,
`PREVENTIVO_RIGA`, tutte con `key_selector = 'id'`.
🔴 **Corretto il 2026-09-14: le porta il DB di SVILUPPO, non il progetto.** Il
CSV `80_data/sql/config/sorgenti.csv` ha **10 righe**; le cinque `*_RIGA`
(id 3, 5, 7, 9, 11) esistono solo su dbdev — lo dice l'intestazione di
`20260820-03`, e nessuno l'ha sanato. Su un database ricostruito da zero
`DDT_VENDITA_RIGA` **non c'è**: lo scarico del passo 3 sarebbe verde su dev e
rosso in CI. ⇒ Entrano nel CSV col Lotto 1 (D-7). *È la regola zero applicata a
me stesso: una riga letta dalla macchina non è struttura finché non sta nel seed.*

~~⚠️ **Perché resta tutto nullable, e non è pigrizia.** Ci saranno movimenti senza
un'operazione a monte (una correzione a mano, un caso nuovo). Con le colonne
obbligatorie, chi non ha una sorgente **se la inventa** — ed è esattamente il modo
in cui il riferimento libero senza catalogo si sporca il primo giorno ([analisi aggancio §2](analisi-db-magazzino-aggancio-documento-e-produzione.md)). Chi ha una sorgente
è protetto; chi non ce l'ha passa, e **si vede** che non ce l'ha.~~

🔴 **ROVESCIATO il 2026-09-14 — D-6 (Tid): la sorgente sul ledger è `NOT NULL`.**
La riga sopra resta barrata perché il suo argomento era giusto **contro il testo
libero** e non regge più sotto D-1: con FK a catalogo, guard tipizzato e vista
degli orfani, una sorgente **non si inventa**. E la domanda che decide è
un'altra: *chi scriverebbe davvero senza sorgente?* **Nessuno** — ogni modo di
muovere merce è un'operazione, e ogni operazione è già un record: inventario →
`inventari_righe`, ⭐ **correzione a mano → `rettifiche_righe`** (esiste apposta,
con `qta_delta`, `motivo` e stato `DRAFT → POSTED`), trasferimento →
`trasferimenti_righe`, asset → `eventi_assets`, bolla/reso → le loro righe,
ricevimento e ODL → i loro record, storno → eredita quella del movimento che
corregge. La libertà del «senza documento» vive un livello più su e resta:
`rettifiche.sorgente_tipo_id` è nullable, perché *da dove nasce la rettifica* può
essere niente. Obbligatoria è la provenienza del **movimento**.
⇒ Il `UNIQUE` di questa sezione diventa **pieno**, non parziale; il doppio
storno è impedito ovunque (§7-quinquies); e la riga «correzione a mano, sorgente
vuota» della tabella qui sotto **non esiste più**: è una rettifica.
⚠️ Su **`movimenti_attesi`** la sorgente resta nullable: il blocco manuale non ha
un documento per definizione (§7-bis). Verbale completo: [analisi aggancio
§8-quater](analisi-db-magazzino-aggancio-documento-e-produzione.md).

#### ⛔ E la stringa leggibile? Non può essere una colonna generata

La tentazione successiva è tenere anche una stringa parlante — `DDT:47:SCARICO` —
come colonna **generata**, così non può contraddire le altre. ⛔ **Non è
possibile, ed è verificato il 2026-09-02**: una `GENERATED ALWAYS AS … STORED` non
ammette sottoquery (*«non è possibile utilizzare la sottoquery nell'espressione di
generazione di colonne»*), e il prefisso vive in `config.sorgenti` — cioè
richiede un join.

⇒ Delle due l'una, e vanno tenute distinte:

| | Dove sta l'identità | Il prefisso | Il rischio |
| --- | --- | --- | --- |
| **A — consigliata** | sulle **colonne** `(sorgente, chiave, verbo)` | non serve: nessuna stringa da comporre | ⭐ la contraddizione è **impossibile**, non «rilevabile» |
| **B** | su una stringa scritta dalla funzione madre | dal `codice_interno` del catalogo | ⚠️ la stringa può **divergere** dalle colonne, e serve un presidio che lo scopra |

⭐ **Si può avere anche la leggibilità, senza pagarla**: la stringa parlante la
compone una **vista** (che il join lo può fare), non una colonna. Nessun dato
duplicato, nessuna divergenza possibile, e chi legge il ledger vede
`DDT_VENDITA_RIGA:47:SCARICO` lo stesso.

### ⛔ Le due condizioni senza cui non funziona

**1. La chiave la compone l'OPERAZIONE, non il documento.**
Sul ricevimento di acquisto la stessa riga di bolla del fornitore può caricare
**più volte, legittimamente**: arrivano 100 pezzi, se ne accettano 60 oggi e 40
dopo il controllo. E c'è la **ri-consegna**, dove la stessa riga d'ordine riceve
merce una seconda volta. ⛔ Una chiave `BOLLA-ACQ:{riga}:CARICO` respingerebbe il
secondo carico legittimo — cioè riprodurrebbe il difetto di partenza con un nome
più bello. **Il documento entra nella chiave come contesto; l'identità è
l'operazione** («il ricevimento numero 3 della riga 47», non «la riga 47»).

**2. La chiave è RICALCOLABILE, non estratta a caso.**
Un identificativo casuale generato a ogni chiamata produrrebbe una chiave **nuova**
a ogni tentativo ripetuto: nessuna collisione, doppio movimento, e una protezione
che *sembra* esserci. Deve valere *dagli stessi fatti esce sempre la stessa
chiave* — è precisamente la proprietà per cui `segment_key` funziona.
⇒ Ne discende **chi la compone**: la funzione madre che scrive il movimento, in
modo deterministico. ⚠️ Non un valore che arriva dal backend a ogni chiamata.

### Che cosa copre, senza aggiungere niente per ogni caso nuovo

> ⚠️ La colonna di mezzo mostra la **forma leggibile** (quella che compone la
> vista). L'identità vera è la terna `(sorgente, chiave, verbo)`: sotto ogni riga
> di questa tabella c'è quella, non una stringa memorizzata.

| Operazione | Come si legge | Nota |
| --- | --- | --- |
| Scarico da riga di bolla di vendita | `DDT_VENDITA_RIGA:{riga}:SCARICO` | ⭐ la sorgente **esiste già** a catalogo |
| Carico da bolla del fornitore, anche **parziale e ripetuto** | sorgente = il **ricevimento**, non la riga di bolla | ⭐ è il caso che smaschera l'identità sbagliata |
| Reso al fornitore | sorgente = il reso | |
| Ri-consegna sullo stesso ordine | sorgente = la ri-consegna | non collide col primo carico |
| Trasferimento | stessa sorgente, verbo `OUT` e verbo `IN` | ⭐ due righe distinte: **il caso che l'indice di oggi sbaglia** |
| Prelievi e versamenti di produzione | sorgente = il prelievo / il versamento | N legittimi, nessuno blocca l'altro |
| Inventario, rettifica | sorgente = la propria riga | ⭐ *dal 14-09 (D-6)* la **correzione a mano È una rettifica**: `RETTIFICA_RIGA:{riga}`, e la riga qui sotto è ritirata |
| ~~Correzione a mano, senza operazione~~ | ~~sorgente vuota~~ | ~~⚠️ il vincolo parziale non si applica: passa, e **si vede** che è così~~ — 🔴 **ritirata il 2026-09-14**: sotto D-6 non esiste un movimento senza sorgente |

⭐ **È il vero argomento per togliere l'indice**: non «era sbagliato», ma
*rispondeva alla domanda sbagliata*. Spostata la domanda sull'operazione, il
trasferimento smette di essere un'eccezione, il ricevimento parziale funziona, e
la produzione non ha bisogno di niente di nuovo.

### Che cosa questa colonna NON fa

* ⛔ **Non dice chi può scrivere un movimento**, né se il documento citato esiste:
  quelle sono la **D-1** e i due presidi dell'[analisi aggancio §8-bis](analisi-db-magazzino-aggancio-documento-e-produzione.md).
* ⛔ **Non sostituisce il controllo dentro la funzione**, che resta e serve a
  un'altra cosa: dare un messaggio comprensibile («questa riga ha già scaricato
  il …»).
* 🔴 **E NON è «la rete per chi non passa dalla funzione».** *(Frase della prima
  stesura, corretta il 2026-09-02 su rilievo di Tid: era sbagliata.)* Chi scrive
  in `movimenti` scavalcando la funzione madre **non compone nemmeno la
  sorgente**: lascia i campi vuoti, e con il vincolo parziale passa liscio.
  ⇒ Il `UNIQUE` protegge dalla **funzione chiamata due volte** — batch rilanciato,
  retry, doppio click — che è protezione vera e sufficiente per il caso che
  capita. Ma è **un'altra cosa**, e crederla più larga di così vuol dire sentirsi
  coperti su uno scenario che resta scoperto.
  ⭐ **Lo scrittore estraneo non si ferma con un vincolo: si ferma con i
  permessi.** «In `magazzino.movimenti` non scrive nessuno se non attraverso la
  funzione» è una regola di `GRANT` e di `SECURITY DEFINER`, e va nel perimetro
  RLS/permessi di `magazzino`, che **non esiste** (§5) — *esiste dal 15-09, e la
  porta di scrittura dal 18-09 (vedi la nota in testa a §5)*.
* ⛔ **Non è un sostituto della macchina a stati**: che un DDT vada in `EMESSO`
  una volta sola resta compito del guard di transizione.

### Quel che resta da fissare, ed è piccolo

> ✅ *Fissato nel Lotto 1*: il verbo è la causale (D-L1-c), e lo scope è globale
> con la ragione nel `COMMENT`.

* ~~il **nome** e il vocabolario del verbo (`operazione_verbo`): CHECK a valori
  chiusi, oppure lookup — la seconda se i verbi dovranno portare attributi;~~
  superato da D-L1-c;
* lo **scope dell'unicità**: **globale**, e va scritto come **dipendenza, non
  come preferenza**. ⭐ È globale *perché la terna contiene già la sorgente*,
  quindi il magazzino non aggiunge identità. ⚠️ Il giorno in cui una chiave non
  contenesse più la sorgente, l'unicità globale diventerebbe **sbagliata in
  silenzio** — quindi la ragione va nel `COMMENT`, non lasciata al lettore;
* ⭐ **la grammatica dei prefissi non è più un problema aperto**, ed è il
  guadagno della forma A: se l'identità sta sulle colonne, non c'è nessuna
  stringa da comporre e **nessun quinto vocabolario parallelo** da tenere
  allineato. ⚠️ Nella forma B invece il prefisso deve venire dal
  `codice_interno` di `config.sorgenti` — mai da un elenco scritto a mano
  accanto: è la trappola in cui il gemello acquisto è appena caduto con gli
  «ambiti», quattro assi diversi con lo stesso nome.

---

## 7. La lettura: giacenza e disponibilità

> ⚠️ **Fotografia del 2026-09-02.** Oggi le viste sono sette — `vw_giacenza`,
> `vw_giacenza_ubicazione`, `vw_giacenza_valorizzata`, `vw_costo_medio`,
> `vw_costo_medio_globale`, `vw_disponibilita`, `vw_disponibilita_articolo` — e
> `costo_medio` si chiama `valore_giacenza` e la aggiorna la primitiva.

Scrivere è metà del lavoro; l'altra metà è **rileggere**, e lì i difetti di §4 si
manifestano.

Oggi lo schema espone quattro viste — `vw_giacenza`, `vw_giacenza_valorizzata`,
`vw_costo_medio`, `vw_costo_medio_globale` — e la prima è **tre righe**:

```sql
CREATE OR REPLACE VIEW magazzino.vw_giacenza AS
SELECT articolo_id, magazzino_id, sum(qta) AS qta
  FROM magazzino.movimenti
 GROUP BY articolo_id, magazzino_id;
```

⛔ **Due cose che quella somma non fa, e sono entrambe strutturali:**

1. **non guarda `causali.segno`** — ✅ e con la decisione A della §4 **è
   corretta**. ⚠️ Ma corretta *per una ragione che la vista non dichiara*: il
   prossimo lettore la vedrà incompleta e sarà tentato di aggiungerci il join alle
   causali, che **raddoppierebbe il segno** e invertirebbe ogni uscita. ⇒ La
   ragione va scritta nel suo `COMMENT`, e vale come presidio quanto un vincolo;
2. **non sottrae le `reservations`.** ⭐ *(La tabella dal 2026-09-02 è decisa come
   `magazzino.movimenti_attesi` — §7-bis. Qui resta il nome di oggi perché si sta
   descrivendo ciò che esiste.)* La tabella delle prenotazioni esiste, con
   `stato_reservation` e `data_prevista`, ed è descritta *«per ordini e ODL»*.
   ⇒ **Oggi non esiste una «disponibilità»**: c'è quanto c'è, non quanto se ne può
   ancora impegnare. Senza quel numero non c'è niente su cui un fabbisogno — di
   vendita, di acquisto o di produzione — possa decidere.

⚠️ **E c'è un terzo asse, la valorizzazione, che è dichiarato e non alimentato**:
`causali.impatto_valorizzazione` dice `cmp` / `fifo` / `none` per ogni causale, e
`magazzino.costo_medio` tiene lo stato corrente per articolo × magazzino. ⛔ Ma
nessuna funzione lo aggiorna, perché nessuna funzione scrive movimenti (§5). È
l'ennesima struttura completa e ferma.

---

## 7-bis. La giacenza che serve davvero: effettiva, impegnata, in arrivo

> **Origine:** richiesta di Tid, 2026-09-02: *«mi piacerebbe che della giacenza si
> potesse mostrare, oltre a quella effettiva, anche la “prenotata in uscita” e la
> “merce in arrivo”, per articolo. E cliccando sulla prenotata vedere preventivo X,
> ordine Y, DDT Z con la data prevista di uscita che stiamo aggiungendo»*.
>
> ⭐ **La richiesta è più fondata di quanto sembri**: non chiede un abbellimento,
> chiede il numero su cui si decide. «Quanto ce n'è» non serve a nessuno da solo —
> serve **quanto se ne può ancora promettere**.

### ⭐ Metà del meccanismo esiste già, e non lo legge nessuno

`magazzino.reservations` **è** la prenotazione in uscita, ed è già completa di
tutto ciò che la richiesta domanda:

| Colonna | A che cosa serve nella richiesta |
| --- | --- |
| `articolo_id`, `magazzino_id`, `qta` | il numero da mostrare, per articolo |
| `data_prevista` | la data nella riga di dettaglio |
| `doc_schema` · `doc_table` · `doc_id` · `doc_riga_id` | ⭐ **è esattamente il drill-down**: quale preventivo, quale ordine, quale DDT |
| `stato_reservation` | ciclo a quattro stati: `planned` → `picked` → `fulfilled` → `cancelled` |

⛔ **E non la legge nessuno**: zero funzioni, zero viste — verificato il
2026-09-02 su `pg_proc` e `pg_views`. È la quarta struttura di questo documento
che esiste, è costruita bene, e non è collegata a niente.

### ⛔ Ma «in arrivo» quella tabella non lo sa dire

`chk_mag_res_qta_pos` impone `qta > 0`, e **non c'è nessuna colonna di
direzione**. La tabella sa dire *«di questo articolo, tanti pezzi sono promessi a
qualcuno»* e non sa dire *«tanti stanno arrivando»*. ⇒ O `reservations` cambia
forma, o «in arrivo» è un'altra cosa.

⚠️ **E porta lo stesso difetto dell'indice della §6**:
`uq_mag_reservations_docref` è `UNIQUE (doc_schema, doc_table, doc_id,
doc_riga_id)` — **una prenotazione per riga di documento**. ⛔ È sbagliato per la
stessa ragione: una riga d'ordine può essere impegnata su **due magazzini**, o in
**due tranche con date diverse**. *(Trovato controllando per rispondere a questa
richiesta: è la stessa specie, nella tabella accanto.)*

### La domanda che decide la forma: si materializza o si deriva?

⭐ **C'è una definizione che rende il problema semplice, e si aggancia alla §6:**

> **Impegnato e in arrivo sono il complemento dei movimenti**: sono le righe di
> documento che portano un impegno e il cui **movimento non è ancora stato
> scritto**.

«Prenotato» significa: *esiste la riga impegnata, e la merce non è ancora uscita*.
Si **deriva**, e non c'è niente da tenere allineato.

🔴 ⚠️ **Ma la derivazione è a DUE salti, non uno — precisazione del 2026-09-04.**
L'identità del movimento di scarico è la **riga di DDT**, non la riga d'**ordine**:
per sapere se l'impegno di una riga d'ordine è stato consumato non basta cercare il
movimento, serve passare dal **ponte di evasione** (`ordini_righe_fulfillment`, e la
lettura già fatta di `vw_situazione_merce_ordine`).

⇒ **La derivazione non è «gratis»**: il salto centrale è **un'altra struttura**, che
per fortuna **esiste già ed è in esercizio** — ma va nominata, o chi la implementa
cerca un legame diretto che non c'è.

| | Come | Cosa costa |
| --- | --- | --- |
| **Derivare** (consigliata) | una vista che confronta le righe impegnate con i movimenti già scritti | ⭐ nessuna seconda verità, **il drill-down è gratis** (la riga di documento *è* il dettaglio), e la data è quella del documento. ⚠️ Costo di calcolo, da misurare |
| **Materializzare** in `reservations` | una riga scritta quando l'ordine si conferma, aggiornata quando parte la merce | ⛔ è una **seconda sede** del residuo d'ordine: due numeri che dicono la stessa cosa e divergono al primo aggiornamento mancato |

⇒ **`reservations` non sparisce, ma cambia mestiere** (e nome — vedi la decisione qui sotto): resta per ciò che *non* si
può derivare — la prenotazione **senza documento** («tieni da parte 10 pezzi per
il cliente X»), e quella che ha bisogno di uno stato proprio (`picked`: la merce è
già stata presa dallo scaffale ma non è ancora uscita). ⛔ Non il doppione del
residuo d'ordine.

### ⛔ Il preventivo NON è una prenotazione — e il progetto l'ha già deciso

La richiesta nomina *«preventivo X, ordine Y, DDT Z»*. ⚠️ Sui primi due non è la
stessa cosa, e la differenza è già codificata altrove:
`vendite.vw_situazione_merce_ordine` ha la **soglia dell'impegno** — sotto lo stato
`CONFERMATO`, `da_spedire` è **NULL** e la riga è `NON_IMPEGNATA`, *«perché su una
bozza l'impegno non c'è ancora»*. È una decisione presa, presidiata da pgTAP.

⛔ Mettere i preventivi dentro «prenotata in uscita» la contraddirebbe, e il danno
sarebbe concreto: **merce che risulta non disponibile per una promessa che nessuno
ha fatto** — un venditore si sente dire «non c'è» per un preventivo che il cliente
non ha mai accettato.

⇒ **Non è un no: sono colonne diverse**, e servono tutte.

🔴 **Corretta il 2026-09-02 (sera).** La prima stesura diceva che l'impegnata *«toglie
disponibilità»*. ⛔ **Non è più vero** dopo le due decisioni successive: l'impegno
**derivato** non ferma niente (e contiene la riga che il documento stesso sta
servendo), mentre l'unico che sottrae davvero è il **blocco esplicito**.

| Colonna | Che cosa contiene | Sottrae? |
| --- | --- | --- |
| **giacenza** | quello che c'è fisicamente | — |
| **bloccata** | i **blocchi espliciti** messi da una persona | ✅ **sì**: è il vincolo vero, ferma lo scarico (§7-bis, «l'esplicito ferma») |
| **impegnata** | ordini **confermati**, DDT non ancora spediti, prelievi di produzione | ❌ **no**: si mostra accanto, non dentro |
| **potenziale** | preventivi e offerte, cioè merce **sperata** | ❌ no |
| **in arrivo** | ordini d'acquisto con residuo, DDT fornitore non caricati | — (si somma, non si sottrae) |

⛔ **E «disponibile» come numero unico va definito, non dato per ovvio**: cambia con
la domanda. *«Posso spedire adesso?»* è `giacenza − blocchi espliciti altrui`;
*«posso prometterla?»* aggiunge l'**in arrivo** e guarda le date. ⇒ Se una sola
casella si chiamasse «disponibile» senza dire quale delle due, mentirebbe a metà
degli utenti — e mostrare `0` a chi poi riesce a spedire è esattamente il difetto che
questo documento insegue.

⭐ **E la soglia non va inventata**: è già **dato**, non codice — viene da
`config.stati_doc_*.codice_interno`. La stessa vista può esporre le due colonne
leggendo il catalogo, senza una regola nuova da mantenere.

> 🔴 **⚠️ Dipendenza dichiarata il 2026-09-02 (D-17 dell'[analisi
> acquisti](analisi-simmetria-ordini-acquisto.md)).** `config.stati_doc_ordini` è
> **condivisa** fra vendite e acquisti e **non ha un discriminante di ciclo**. Le
> righe non si mescolano — le distingue la tabella di provenienza — ma **la soglia
> sì**: «da quale stato un ordine di vendita impegna merce» e «da quale stato un
> ordine di acquisto conta come in arrivo» sono **due domande diverse**, e oggi
> `CONFERMATO` è **una riga sola** che risponde a entrambe.
> ⇒ La vista che realizza M-3 **presuppone il satellite** (`stati_doc_ordini_ambiti`,
> §7 dell'analisi acquisti, decisione **D-3** ancora da confermare nella forma): è lì
> che la colonna `ordine` sul paio permette due soglie. ⛔ Non blocca la decisione
> M-3, che è presa: blocca **la vista che la implementa**.

### «Merce in arrivo»: si deriva dagli acquisti, e le manca una data

Le fonti, nell'ordine in cui esisteranno:

1. **righe di ordine di acquisto** con residuo — ordinato meno ricevuto, via
   `acquisti.ordini_righe_fulfillment`, che **esiste già**;
2. **DDT fornitore ricevuti e non ancora caricati** — la merce è in casa ma non è
   entrata in giacenza (§8 dell'[analisi
   acquisti](analisi-simmetria-ordini-acquisto.md));
3. **versamenti attesi da ODL**, il giorno in cui la produzione esiste.

⭐⭐ **E qui le due cose che stiamo facendo si incontrano**: «in arrivo» senza una
data attesa è un numero che non serve a decidere niente — *«ne arrivano 40»* non
risponde a *«faccio in tempo a promettere la consegna di giovedì?»*. La data
attesa sull'ordine di acquisto è **`acquisti.ordini_righe.data_consegna_confermata_fornitore`**,
cioè una delle colonne del [brief delle modifiche
certe](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md).

✅ **Il nome è `acquisti.ordini_righe.data_consegna_confermata_fornitore`** — D-16,
decisa il 2026-09-02. L'omonima non marcata esiste su `vendite.ordini_righe`, dove la
promessa è **nostra**. ⭐ **È questa vista il posto per cui la distinzione è stata
fatta**: qui le due si incontrano e il nome della tabella sparisce, quindi il suffisso
è l'unica cosa che dice di chi è la promessa.

⇒ Quella colonna smette di essere «utile» e diventa **necessaria**: senza, questa
richiesta si può realizzare a metà.

### ✅ DECISIONE (Tid, 2026-09-02): `reservations` diventa `magazzino.movimenti_attesi`

> Una tabella sola per **entrambi i versi**, gemella del ledger: `movimenti` è ciò
> che è successo, **`movimenti_attesi`** è ciò che ci si aspetta.

⭐ **La ragione non è «servono due direzioni»: è che una direzione sola è già falsa
oggi.** Il **trasferimento** è simultaneamente una partenza dal magazzino A e un
arrivo nel magazzino B — la stessa riga di documento, due movimenti. Una tabella
che sa dire solo «in uscita» non lo sa rappresentare, e il trasferimento non è
ipotetico: è già nelle causali.

⛔ **Ed è la ragione per cui il nome NON enumera i casi.** «Arrivi e partenze»
descriverebbe il trasferimento **due volte**, e un nome che elenca smette di essere
vero al terzo caso. `movimenti_attesi` nomina invece la **relazione** con ciò che
completa, regge la produzione senza rinominare (un versamento atteso da un ODL è un
movimento atteso, non un «arrivo»), ed è italiano come le altre 24 tabelle dello
schema — `reservations` e `assets` sono gli unici due nomi inglesi.

#### ⭐⭐ Il guadagno vero: la direzione non è una colonna nuova

Un movimento atteso porta **`causale_id`**, esattamente come il movimento vero. Da
lì eredita **gratis**:

| Eredita | Da |
| --- | --- |
| il **verso** | `causali.segno` |
| la valorizzazione attesa | `causali.impatto_valorizzazione` |
| l'obbligo di lotto e seriale | `richiede_lotto`, `richiede_seriale` |
| l'ambito | `ambito_causale_id` (quando sarà valorizzato — §3) |

⛔ **Così non nasce un vocabolario di direzione nostro**, che sarebbe il **quinto
asse parallelo**: è la trappola in cui l'analisi acquisto è appena caduta con gli
«ambiti» — quattro cose diverse chiamate allo stesso modo.

⚠️ **E ne discende una semplificazione**: la **§4 diventa una decisione sola per due
tabelle.** Se il verso lo porta la quantità oppure la causale, la risposta vale per
gli attesi e per gli scritti insieme. Erano due domande, è una.

#### ⛔ Che cosa ci va dentro, e che cosa no

Resta la divisione della sezione: **la vista mostra tutto, la tabella tiene solo ciò
che non si deriva.**

| Caso | Riga in `movimenti_attesi`? |
| --- | --- |
| riga d'ordine confermata, residuo da spedire | ❌ **no** — si deriva dal documento |
| riga di ordine d'acquisto in attesa di arrivo | ❌ **no** — idem |
| blocco manuale («tieni da parte 10 pezzi per il cliente X») | ✅ sì: non c'è nessun documento da cui leggerlo |
| merce già prelevata dallo scaffale, non ancora uscita | ✅ sì: è uno **stato** che il documento non ha |

⛔ Se la tabella si riempie anche di ciò che è derivabile, ci sono **due numeri per
lo stesso fatto**, e il primo aggiornamento mancato li separa in silenzio. È il
difetto che questi documenti contestano tre volte: il doppio modello del §2,
`ddt.ordine_id`, e la chiave parallela alle colonne di sorgente della §6.

#### Che cosa va rifatto insieme al nome

| # | Cosa | Perché non si può rimandare |
| --- | --- | --- |
| 1 | **il ciclo degli stati**, oggi `planned → picked → fulfilled → cancelled` | ⛔ **`picked` è un concetto di sola uscita** (preso dallo scaffale). In entrata l'equivalente è «arrivato, non ancora caricato» — il `RICEVUTO → VERIFICATO → CARICATO` che l'[analisi acquisto](analisi-simmetria-ordini-acquisto.md) ha già nominato. È il primo punto in cui il generico perde pezzi |
| 2 | **`uq_mag_reservations_docref`** | stessa specie dell'indice della §6: dice *una riga per riga di documento*, ed è falso con due magazzini, due tranche o due date |
| 3 | **`chk_mag_res_qta_pos`** (`qta > 0`) | ✅ **cade**: con la decisione A della §4 anche gli attesi sono firmati, e un CHECK che impone il positivo impedirebbe il verso di entrata. ~~⭐ Ne discende la formula unica `sum(movimenti.qta) + sum(movimenti_attesi.qta)`~~ — *ritirata il 04-09 (vedi §4): la formula è in «La formula di disponibile»* |
| 4 | **`data_prevista`** | resta, ma solo per le righe **senza documento**: dove c'è un documento la data è la sua, o le due divergono |

⚠️ **E «rinominare la tabella» vuol dire rinominare TUTTO**, non solo la tabella:
indici (`pk_mag_reservations`, `ix_mag_res_stato`, `uq_mag_reservations_docref`),
vincoli (`chk_mag_res_qta_pos`, `chk_mag_res_stato`), le FK e i trigger generati.
È una lezione già registrata nel progetto, e il momento in cui costa poco è
**adesso** — non perché sia poco lavoro, ma perché nessuno di quegli oggetti è
ancora nominato da qualcos'altro.

⭐ **E il rename costa zero, adesso.** Zero righe, **zero funzioni e zero viste** che
la leggono (verificato il 2026-09-02 su `pg_proc` e `pg_views`). ⚠️ Il precedente
opposto è sotto gli occhi: `vendite.registri_fatturazione` numera anche i DDT e **si
tiene il nome sbagliato**, perché rinominarlo avrebbe toccato trigger, viste e
vincoli — con il debito dichiarato in quattro sedi. Qui non c'è niente da toccare, e
fra sei mesi non sarà più vero.

### ⛔ L'impegno allo scarico: il derivato non conta, l'esplicito ferma

> **Osservazione di Tid, 2026-09-02**, che ha chiuso un ramo di progetto invece di
> aprirlo: *«l'impegno del magazzino al momento non ha una promessa vincolata, non
> esiste; esiste solo un impegnato teorico di cui questo ordine stesso fa parte —
> quindi è un finto problema»*. **Ed è verificabile, non è un'impressione.**

#### Perché sull'impegno DERIVATO l'avviso non si fa

**1. Avviserebbe l'operatore contro sé stesso.** Con la definizione scelta —
*impegnato = riga con impegno il cui movimento non è ancora scritto* — la riga
d'ordine che **questo DDT sta servendo** è ancora dentro il conteggio: il suo
movimento si scrive a `EMESSO`, cioè **dopo** la conferma. ⇒ «10 impegnati» sono,
in tutto o in parte, i suoi.

**2. E soprattutto: non c'è nessuna allocazione.** L'impegnato è un **aggregato
calcolato**, non una prenotazione che leghi pezzi a un ordine, e **non esiste una
regola di priorità**. ⛔ Un avviso senza una regola dietro non dice all'operatore
che cosa fare: «ci sono altri impegni» — e quindi?

⚠️ **E un dialogo su cui non si può agire insegna a cliccare via i dialoghi.** Dopo
due settimane non lo legge più nessuno, compreso il giorno in cui avrebbe avuto
ragione. È la stessa forma del presidio che boccia a caso e che qualcuno finisce per
spegnere.

⇒ Non è che l'avviso sia inutile: è **prematuro**. Presuppone una **regola di
allocazione** che non esiste, e costruire il dialogo lasciando fuori la regola
significa costruire la metà che non serve.

#### ⭐⭐ Ma il blocco ESPLICITO non è un avviso: è un vincolo

🔴 **Riscritto il 2026-09-02, seconda revisione della stessa giornata**, e la
ragione è un'obiezione di Tid che ha rovesciato la conclusione precedente:

> *«fatto come dici tu il blocco mente. Il programma di scarico non può bypassare
> il vincolo, altrimenti mentirebbe.»*

⛔ **Aveva ragione, e il difetto era mio.** Avevo proposto: si avvisa, l'operatore
conferma, la merce parte. Ma se parte e il blocco resta, **quel blocco continua a
riservare merce che non esiste più** — e da quel momento la disponibilità che
mostriamo è falsa. È la piaga già registrata altrove: *una coda che non si svuota si
riempie di roba vecchia, finché nessuno la guarda più.*

⇒ **Un blocco esplicito è un vincolo, non un consiglio.** La distinzione decisiva
resta quella fra i due impegni, ma la conseguenza cambia:

| | Che cos'è | Che cosa fa allo scarico |
| --- | --- | --- |
| **impegno derivato** | un **calcolo** su ordini confermati: nessuno ha allocato niente | ⛔ **niente**: non c'è nessuna promessa da violare, e contiene la riga che il documento stesso sta servendo |
| **blocco esplicito** | ⭐ **l'atto di una persona**: qualcuno ha scritto «questi sono per il cliente X» | ⛔ **ferma lo scarico**, finché una persona non lo libera |

#### ⭐ E si libera esplicitamente, non si consuma da sé

La prima stesura diceva *«la conferma consuma il blocco»*. ⛔ **Ritirata**: sarebbe
mangiare in silenzio la decisione di un collega.

> *«Se l'operatore vuole spedire perché è urgente, libera le quantità bloccate e poi
> riconferma»* (Tid).

⭐ Così l'aggiramento ha **un atto, un autore e un momento** — invece di essere un
effetto collaterale di un click su «conferma». Un blocco messo da una persona lo
toglie una persona.

⚠️ **Ma il rilascio si offre nello stesso dialogo**, non mandando l'operatore a
cercare dov'era il blocco: resta un atto esplicito, non diventa una caccia al
tesoro.

#### ⭐⭐ Lo stesso controllo nei due momenti — ma è una funzione, non un flag

Il controllo che parla alla conferma del documento e quello che rifiuta allo scarico
**devono essere lo stesso**, o divergono. È il pattern che il progetto già impone
per le azioni sui documenti: *«il motivo lo produce la stessa funzione che il
database usa per rifiutare, chiamata sia dalla madre sia dalla query di lista»*.

⚠️ **La forma però non è un parametro sulla funzione che scrive.**

| | Come | Il problema |
| --- | --- | --- |
| flag `comunica_con_interfaccia` sulla primitiva | una funzione che a volte scrive e a volte no | ⛔ **chi può controllare può anche scrivere**: è la stessa funzione, non si può concedere l'una senza l'altra. ⚠️ E lega il database a un consumatore: il DB non deve sapere che esiste un'interfaccia |
| ⭐ **una funzione di controllo separata**, che non scrive mai | la chiamano **entrambi**: la UI per mostrare, la primitiva per rifiutare | ✅ il controllo si concede a chiunque, la scrittura resta alla sola primitiva. È il principio della §5: **la porta si chiude con i permessi** |

⭐ E la coppia *verifica / esecuzione* è già di casa nel progetto — `..._preview`
accanto a `..._init` sui componenti d'ordine.

#### ⚠️ I due momenti NON chiedono la stessa cosa

| Momento | Giacenza insufficiente | Blocco esplicito di un altro |
| --- | --- | --- |
| **conferma dell'ordine** | ⚠️ **informazione**: *«3 ci sono, 7 arrivano il 20»* — serve a decidere la data promessa | informazione |
| **conferma / spedizione del DDT** | ⛔ **blocca** | ⛔ **blocca** finché non è liberato |

⛔ **Se bloccassimo anche alla conferma dell'ordine non si potrebbe più prendere un
ordine su merce da acquistare** — cioè quasi tutti. Alla conferma dell'ordine la
merce che non c'è è normale: è il motivo per cui esistono «in arrivo» e la data
confermata.

#### ✅ Per chi è il blocco: `soggetto_ruolo_id` + nota, DECISO

Un blocco esplicito, per poter fermare qualcuno, deve dire **per chi** è. Senza, il
rifiuto è *«merce bloccata»* e basta — vero e **inutilizzabile**: chi lo riceve non
sa se liberarla o no.

⛔ **E oggi non c'è dove scriverlo**: `user_insert` dice **chi l'ha messo** (Mario),
non **per chi è** (Rossi) — sono due persone diverse, e serve la seconda. ⭐ Le
colonne che lo direbbero sono quelle del **documento**, e sono vuote *per
definizione* proprio nelle righe che ne hanno bisogno: questa tabella conserva
**solo** i blocchi senza documento.

**✅ Decisione di Tid, 2026-09-02:**

| Colonna | Come |
| --- | --- |
| `soggetto_ruolo_id` | **nullable**, FK verso `anagrafiche.soggetti_ruoli` |
| `nota` | testo, **obbligatoria solo quando il soggetto manca** |
| il vincolo | un `CHECK` solo: `soggetto_ruolo_id IS NOT NULL OR coalesce(btrim(nota), '') <> ''` |

🔴 **Una versione intermedia proponeva una scala a tre gradini** — `billing_account_id`,
poi il soggetto, poi la nota — **ed è stata scartata da Tid.** La ragione la smonta:

> **Tutto ciò che il BA sa dire, il `soggetto_ruolo` lo sa dire. Il contrario no.**

* da un BA si risale **sempre** al soggetto: `anagrafiche.billing_account.soggetto_ruolo_id`
  è `NOT NULL`;
* ⛔ ma da un soggetto non si risale a un BA — e un **fornitore** un BA non ce l'ha
  affatto (`billing_account_id` esiste su **19 tabelle di `vendite`/`anagrafiche` e
  zero in `acquisti`).

⇒ Una colonna che copre tutti i casi dell'altra **più altri** rende l'altra inutile.
E il BA costava in più un vincolo di **esclusività** — cioè un controllo per impedire
una duplicazione che esisteva *solo perché* si era aggiunta la seconda colonna.

⭐ **E c'è una ragione di sostanza, non solo di semplicità.** Un blocco è un fatto
**fisico** — *«questi pezzi sono per Rossi»*. Il BA aggiunge la precisione di
**fatturazione** (quale utility, quale istanza), che a chi decide se spedire non
serve: era una dimensione contabile messa a rispondere a una domanda logistica.

⭐ **È il `soggetto_ruolo` e non il soggetto**: la stessa persona può essere cliente
e fornitore, e il ruolo li tiene distinti.

🔴 **E il `coalesce` non è ornamentale — provato il 2026-09-04.** Scritto
`… OR btrim(nota) <> ''`, con soggetto **e** nota entrambi `NULL` l'espressione vale
`FALSE OR NULL` = **NULL**, e ⛔ **un CHECK passa sul NULL**: la riga muta che il
vincolo doveva impedire **entra lo stesso**. Verificato inserendola davvero: passa con
la forma senza `coalesce`, viene respinta con quella corretta.

⚠️ E la nota va difesa anche dal **vuoto**, non solo dal NULL — idioma già consolidato
nello schema (quattro vincoli scritti così): senza, passa una nota fatta di uno
spazio.

⭐ **Ed è un `CHECK` vero, non un trigger**: guarda solo la riga — a differenza del
guard sul verso (§4), che deve leggere un'altra tabella.

⚠️ **Se un giorno servisse distinguere due BA dello stesso cliente**, la nota lo
copre; e a quel punto la colonna si aggiungerebbe sapendo **perché**, invece di
averla messa per scrupolo.

#### Che cosa ne discende, e che cosa NON ne discende

* 🔴 **La primitiva cambia, e M-2 va corretta**: non guarda più «solo il fisico», ma
  **il fisico meno i blocchi espliciti che non appartengono a questo documento**.
  ⭐ L'esclusione dei propri è essenziale — senza, il documento inciamperebbe nel
  blocco messo per sé stesso — e l'informazione per distinguerli c'è già: è
  l'identità della sorgente (§6);
* ⭐⭐ **Il «terzo stato» delle capability non serve più, in nessuno dei due casi.**
  Sul derivato non c'è niente da dire; sull'esplicito l'azione è **davvero
  bloccata**, quindi il pattern binario di oggi — flag spento + motivo + chiave —
  la esprime esattamente. ⛔ **Nessun campo nuovo, nessuna delle tre famiglie di
  nomi toccata**;
* ⚠️ **Il dettaglio «quale ordine» non viaggia nella capability**: quel pattern
  porta un codice macchina e una chiave i18n, non parametri. Il *chi* e il *quanto*
  arrivano dalla vista della situazione merce — la capability dice **che** è
  bloccata, la vista dice **da chi**;
* 📌 **La regola di allocazione** (M-9) resta il prerequisito del solo impegno
  **derivato**: sull'esplicito non serve, perché la priorità l'ha già decisa la
  persona che ha messo il blocco.

### ⚠️ Le due date, e come non farle divergere

`reservations.data_prevista` esiste **già**, e la data che stiamo aggiungendo vive
sulla **riga di documento**. ⛔ Se la prenotazione porta una data propria e la riga
d'ordine ne porta un'altra, al primo spostamento di consegna divergono — e la
giacenza prevista mostra un futuro che non è più vero.

⇒ Ne discende, coerentemente con la scelta «derivare»: **la data è una sola, quella
del documento**. `reservations.data_prevista` resta la data delle sole prenotazioni
**senza** documento, dove non c'è una riga da cui leggerla.


### ✅ La formula di «disponibile» — DECISO (M-3)

> **Decisa con Tid il 2026-09-02.** Tre risposte: la formula, la proiezione, e chi
> governa il conteggio.

#### ⭐ La regola che decide, ed è una sola

> **Il numero mostrato deve prevedere quello che il sistema farà.**

Se la scheda dice `7` e poi il sistema ne fa spedire 10, quel numero non serve a
niente. Se dice `7` e il sistema si ferma a 5, è **peggio**: l'operatore ha promesso
al cliente sulla base di una bugia.

⇒ **`disponibile` = quello che c'è, meno ciò che è bloccato per altri** — cioè
**esattamente ciò che la primitiva controlla** prima di scrivere (§5-bis). Stessa
formula nei due posti, quindi mai una sorpresa.

🔴 **E va scritta in termini di colonne, non a parole** *(correzione del 2026-09-04)*.
Sotto la decisione A **anche gli attesi sono firmati**: un blocco in uscita è `−10`.
⛔ Quindi *«giacenza **meno** blocchi»* applicato alle colonne darebbe
`giacenza − (−10) = giacenza + 10`, cioè il contrario. La forma giusta è una
**somma**:

```
disponibile = sum(movimenti.qta) + sum(movimenti_attesi.qta dei blocchi altrui)
```

⚠️ È un dettaglio solo in apparenza: questo stesso documento ha stabilito che il
valore assoluto è **presentazione e non modello**, e questa formula va implementata in
**due posti** — la primitiva e la vista. Scritta a parole, i due posti la
interpretano diversamente.

⛔ **E l'impegno derivato NON si sottrae**, coerentemente con tutto il resto: non
ferma niente, quindi non deve far scendere il numero. Si mostra **accanto**, come
informazione.

#### ⚠️ L'auto-conteggio, e si esclude con la stessa regola della primitiva

Guardando la scheda **da dentro un documento**, i blocchi di *quel* documento non
vanno sottratti — o il documento inciampa in sé stesso, difetto già incontrato due
volte in questa sezione.

⭐ La regola è **la stessa** che usa la primitiva: *escludi ciò che appartiene al
documento che stai servendo*, attraverso l'identità della sorgente (§6). ⇒ **Una
regola sola in due posti**, non due regole che possono divergere — è la stessa
proprietà per cui il controllo che parla e quello che rifiuta sono la stessa
funzione.

#### «Posso prometterla?» non è un numero: è una proiezione

Quella domanda **non ha una risposta singola**, perché dipende da *quando*: oggi ce
ne sono 3, il 20 ne arrivano 7, il 25 altri 5.

⇒ Non è una casella, è una **piccola proiezione nel tempo**. ⛔ Schiacciarla in un
numero solo butterebbe via **la data**, che è proprio l'informazione che serve a
rispondere.

⭐ Ed è il motivo per cui i due momenti guardano cose diverse (§7-bis): la conferma
dell'**ordine** ha bisogno del calendario, quella del **DDT** no.

#### ⭐⭐ Il conteggio è guidato dal catalogo, non da query scritte a mano

Per calcolare impegnato e in arrivo servono, **per ogni tipo di documento**, due
informazioni:

1. **da quale stato in poi conta** come impegno (la *soglia*, che per l'ordine di
   vendita è già `CONFERMATO` ed è **dato**: sta in `config.stati_doc_*`);
2. **come si capisce se il suo movimento è già stato scritto** — che è l'identità
   della §6.

⛔ **Se quelle due cose si scrivessero a mano** — un pezzo di query per gli ordini,
uno per i DDT, uno per gli acquisti — il giorno che arriva la produzione qualcuno
**deve ricordarsi di aggiungerla**. E chi se ne dimentica non rompe niente: il numero
smette di contare un pezzo, **in silenzio**.

⇒ Il conteggio si guida da **`config.sorgenti`**, come la numerazione si guida da
`vendite.famiglie_documento`. ⭐ Così un tipo nuovo entra nel calcolo **il giorno che
lo si registra**, e non esiste nessun elenco parallelo da tenere allineato.

⚠️ Ne discende un requisito sul catalogo: ogni sorgente che partecipa deve poter
dichiarare la propria soglia e la propria chiave. È **la stessa estensione** che la
**D-7** già richiede per far entrare magazzino e acquisti fra le sorgenti — non un costo
nuovo.

#### Il costo del calcolo

Si **deriva**. ⚠️ E se un giorno dovesse pesare davvero, si tiene in una tabella di
appoggio **la cui definizione resta la derivazione** — mai un secondo numero scritto
per conto proprio. ⭐ La differenza: una copia sbagliata si **ricostruisce**, una
seconda verità no.

⛔ **Oggi non c'è niente da misurare** (zero righe), e qui non si progetta su una
misura: si sceglie la forma giusta e la si verifica quando ci sarà qualcosa da
verificare.

---

## 7-ter. ✅ La valorizzazione — DECISO (M-4)

> **Decisa con Tid il 2026-09-02**, in quattro punti più una pulizia di nome.
> ⭐ Guardandola sono usciti **quattro difetti**, non solo l'assenza
> dell'alimentatore: il pezzo c'era quasi tutto, ed era quasi tutto sbagliato in un
> modo che non produce errori.

### Che cosa esisteva già

| Cosa | Stato |
| --- | --- |
| `magazzino.costo_medio` — quantità **e** valore accumulati per articolo × magazzino | ✅ c'era |
| `vw_costo_medio` (`valore / qta`) e `vw_costo_medio_globale` | ✅ c'erano |
| `vw_giacenza_valorizzata` — giacenza × costo medio | ✅ c'era — 🔴 ma vedi sotto: **dopo queste decisioni diventa tautologica** |
| `causali.impatto_valorizzazione` (`cmp` / `fifo` / `none`), compilato su tutte e dieci | ✅ c'era |
| `movimenti.costo_unitario` | ✅ c'era |
| **chi aggiorna l'accumulatore** | ⛔ **nessuno** |

### ✅ 1. Il trasferimento muove il valore

Le due causali di trasferimento erano marcate `none` — *«la merce cambia scaffale,
non valore»*, che in astratto è giusto.

⛔ **Ma l'accumulatore è per magazzino**, quindi spostare 10 pezzi da A a B senza
muovere il valore lascia in **A** il valore di prima su una quantità che se n'è
andata (media **gonfiata**) e porta in **B** quantità senza valore (media **diluita
verso zero**).

⇒ **Il trasferimento esce da A alla media di A ed entra in B con quello stesso
valore.** Così nessuna delle due medie si sposta per un movimento che non è né un
acquisto né una vendita — che era l'intenzione originaria del `none`, ottenuta però
al contrario.

### ✅ 2. CMP unico metodo, e il metodo esce dalla causale

⭐ **La colonna mescolava due domande diverse:**

| Domanda | Di chi è la risposta |
| --- | --- |
| «questo movimento tocca il valore?» | ✅ della **causale** — un trasferimento no, una vendita sì |
| «con che metodo si valorizza?» | ⛔ **dell'azienda**, non del movimento |

Con la colonna com'era si potevano seminare una causale `fifo` e una `cmp` sullo
**stesso articolo**, ottenendo due valorizzazioni incoerenti sullo stesso magazzino,
e nessun vincolo lo impediva.

⇒ **La causale dice solo *se* valorizza.** Il metodo è **CMP** e basta, e `fifo`
esce dai valori ammessi — era un valore che nessuna causale usava e che **non è
nemmeno implementabile** con questa struttura: FIFO vuole gli **strati** (ogni
carico con la sua quantità residua e il suo costo), non un accumulatore.

#### ⭐⭐ E scegliere CMP oggi non chiude la porta a FIFO

Il registro conserva, per ogni **entrata**, il suo **costo unitario** e la sua
**data**. ⇒ Contiene già tutto ciò che servirebbe a ricostruire gli strati
ripercorrendolo.

⭐ Il metodo diventa quindi una **decisione di lettura**, non di scrittura: oggi si
legge a media, e se un domani servisse FIFO si legge diversamente **lo stesso
registro**. L'unica cosa che non si deve perdere è il costo di ogni entrata.

#### 🔴 E allora `none` non ha più consumatori — rilievo del 2026-09-04

Mettendo insieme le due decisioni: il **trasferimento valorizza** (decisione 1) ⇒ le
uniche due causali `none` diventano valorizzanti; e il **metodo esce dalla colonna**
(decisione 2) ⇒ la colonna risponde alla sola domanda *«valorizza?»*.

⛔ **Risultato: tutte e dieci le causali valorizzano, e `none` è un valore ammesso dal
CHECK che nessuno usa e che il modello non sa più scrivere.** È **esattamente** la
classe che la §4 ha appena chiuso togliendo lo `0` da `causali.segno`, e che questo
documento insegue da tre giorni.

⚠️ Cercando un caso che resti `none`: lo spostamento fra **ubicazioni dello stesso
magazzino** sembra il candidato — ma sotto il modello a coppie esce e rientra nello
**stesso** magazzino, quindi il valore si compensa da sé e `none` sarebbe
un'ottimizzazione, non una necessità.

### ✅ DECISO (Tid, 2026-09-04): `impatto_valorizzazione` **si ritira**

Tutte e dieci le causali valorizzano ⇒ la colonna ha **una risposta sola**. Una
colonna con una risposta sola non è una colonna: è una frase.

⚠️ **Un caso futuro va nominato, perché prima o poi arriva**: la **merce di terzi**
— conto lavoro, conto deposito, merce in visione. Quella si muove e **non è nostra**,
quindi non deve entrare nel nostro valore di magazzino.

⭐ **Ma nemmeno lì la colonna sarebbe la risposta giusta**: *«di chi è questa
merce»* è una domanda di **proprietà**, non di valorizzazione. Il giorno che arriva
si modella la proprietà, e la valorizzazione **ne discende**. Tenere oggi un flag
«non valorizzare» sarebbe rispondere in anticipo alla domanda sbagliata — ed è
esattamente il difetto che questa sezione ha appena corretto sulla stessa colonna,
che teneva insieme *se* e *con che metodo*.

⚠️ **E una distinzione che vale la pena scritta**, perché è la fonte di un equivoco
comune: *«in magazzino facciamo FIFO»* in Italia si dice quasi sempre della
**rotazione fisica** — si spedisce prima ciò che è arrivato prima, per non far
invecchiare la merce. ⛔ **È un'altra domanda**, e in questo modello vive nei
**lotti** (M-5), non qui. Si può prelevare fisicamente FIFO e valorizzare a costo
medio: è quello che fa la maggioranza.

### ✅ 3. L'accumulatore tiene SOLO il valore — e cambia nome

⚠️ **La quantità era tenuta in due posti**: `costo_medio.qta` e la somma dei
movimenti. E `vw_giacenza_valorizzata` **le mescolava** — quantità dal registro,
media dall'accumulatore. ⛔ Se divergevano, il valore mostrato era sbagliato e non se
ne accorgeva nessuno.

| Dato | Dove vive, da adesso |
| --- | --- |
| **quantità** | ⭐ **solo nel registro** (`vw_giacenza`) — una casa sola |
| **valore** | nell'accumulatore, che è una **copia ricostruibile** |
| **media** | una divisione: valore ÷ quantità |

⇒ **I due numeri non possono più litigare**, perché non ci sono più due numeri.

**✅ Rinomina (Tid, 2026-09-02, «per pulizia»): `magazzino.costo_medio` →
`magazzino.valore_giacenza`.** ⭐ Il nome vecchio era diventato falso: la tabella
**non contiene** il costo medio, contiene il valore da cui il costo medio si
*ricava*. E il nome nuovo si accoppia bene con ciò che esiste — `vw_giacenza` tiene
la quantità, `valore_giacenza` il valore, `vw_giacenza_valorizzata` li unisce.
⭐ Le due viste `vw_costo_medio*` **tengono il loro nome**: quelle il costo medio lo
producono davvero.

⚠️ **E rinominare la tabella è rinominare TUTTO**: `pk_mag_costo_medio`,
`uq_mag_costo_medio_art_mag`, `ix_magazzino_costo_medio_magazzino_id`,
`fk_mag_costo_medio_magazzino`, i due trigger e le due viste che la leggono. Costa
zero **adesso** — zero righe, nessuna funzione che la scrive — e non costerà zero fra
sei mesi.

### ✅ 4. La media è ricalcolabile — e questo decide l'architettura

> **La verità è il registro dei movimenti. L'accumulatore è una copia veloce.**

Due cose che si ottengono in regalo:

1. ⭐ **La retrodatazione smette di essere un problema.** La media mobile dipende
   dall'ordine dei movimenti, e `data_mov` è scrivibile: un movimento inserito con
   data vecchia darebbe una media diversa da quella «vera». Con il ricalcolo si
   ricostruisce e torna giusta — senza, resterebbe sbagliata **per sempre**;
2. ⭐⭐ **Si può presidiare.** Una vista che confronta il valore in copia con quello
   ricalcolato dal registro, e che **deve restare vuota**: se compare una riga, la
   copia si è staccata. È lo stesso stampo delle otto viste di controllo che il
   progetto ha già in `dbops`.

⚠️ «Ricalcolabile» **non significa ricalcolare a ogni lettura**: significa che esiste
una funzione che ricostruisce, e che la copia è sempre riparabile.

#### 🔴 «Ricalcolare» è RI-SOMMARE, non ri-eseguire — precisazione del 2026-09-04

Il rilievo che la impone: il ricalcolo ripara l'accumulatore, ma **i movimenti di
uscita già scritti portano il costo del momento in cui furono scritti**. Se il
ricalcolo *ri-eseguisse* la media in ordine di data, dopo una retrodatazione quei
valori risulterebbero sbagliati — e riscriverli ⛔ **contraddirebbe M-8** (si corregge
aggiungendo, non modificando) **e** la regola dello storno al costo originale.

⇒ **Il ricalcolo è una ri-somma, non una ri-esecuzione**: l'accumulatore è la somma
dei **valori che i movimenti portano scritti addosso**, non il risultato di
ripercorrere la media. ⭐ Così la copia coincide col registro **per costruzione**, un
movimento retrodatato **aggiunge** senza riscrivere niente, e la media cambia **solo
in avanti** — che è anche la lettura contabilmente giusta: quello **è** il costo a cui
la merce è realmente uscita.

### Che cosa ne discende per la primitiva (§5-bis)

Alla scrittura di un movimento, se la causale valorizza, la primitiva aggiorna il
**valore**:

* **entrata da documento** → il costo arriva **dal documento** (`costo_unitario` è un
  *input*);
* **uscita** → il costo è la **media corrente**, che si legge (`costo_unitario`
  diventa un *output*: che cosa è uscito, a quanto);
* 🔴 **entrata di trasferimento** *(terzo caso, aggiunto il 2026-09-04)* → il costo
  arriva **dall'uscita gemella**, non da un documento e non dalla media di
  destinazione. ⭐ È il caso creato dalla decisione 1 di questa stessa sezione, e la
  prima stesura lo aveva dimenticato.

⚠️ **`costo_unitario` ha quindi TRE significati**, e vanno dichiarati tutti nel
`COMMENT`: senza, qualcuno lo compilerà a mano anche in uscita e la
media smetterà di essere una media.

### 🔴 `vw_giacenza_valorizzata` diventa tautologica — rilievo del 2026-09-04

Con la quantità **solo nel registro** e la media definita come *valore ÷ quantità*,
il conto della vista — `giacenza × media` — si semplifica in
`giacenza × (valore / giacenza)` = **`valore`**. ⇒ La vista restituisce esattamente il
contenuto di `valore_giacenza`, cioè **non aggiunge niente**.

⚠️ Oggi la sua definizione sopravvive solo perché **nessuno l'ha ricalcolata dopo la
decisione**: va **rifatta** (se serve mostrare quantità e valore insieme, è un join
banale con `vw_giacenza`) **o ritirata**.

### ⚠️ Residui minori, da fare nello stesso giro

> ✅ *Fatti nel Lotto 1*: `fk_mag_valore_giacenza_articolo`, il `COMMENT` su
> `movimenti.costo_unitario`, e `vw_giacenza_valorizzata` rifatta come join.

* `costo_medio` ha il vincolo verso il magazzino ma **non verso l'articolo**: può
  puntare a un articolo che non esiste. La FK va aggiunta con la rinomina (e con la
  sua riga in `dbops.fk_index_policy`).

---

## 7-quater. ✅ Lotti, seriali, ubicazioni — DECISO (M-5)

> **Deciso con Tid il 2026-09-02.** Fin qui il documento ha parlato di **quanti**
> pezzi; qui si parla di **quali**. ⭐ E scrivendolo è uscita una conseguenza della
> §4 che non avevamo tracciato — vedi in fondo, «Il modello a coppie rende
> ridondanti tre colonne».

### ✅ 1. Il lotto diventa una tabella

⛔ **Oggi `movimenti.lotto` è testo libero e non esiste nessuna tabella dei lotti**
(cercata il 2026-09-02: in `magazzino` non c'è). Ne discende che un errore di
battitura **crea un lotto nuovo in silenzio**, e che il lotto non ha dove portare la
propria **data di arrivo** né la **scadenza**.

⭐ È la stessa forma che il §2 condanna per il riferimento al documento: un dato
importante scritto come su un foglietto, senza niente che lo verifichi.

⚠️ **E senza data di arrivo il FIFO fisico non è calcolabile** — quella «rotazione
dello scaffale» che in Italia si chiama FIFO e che M-4 ha distinto dal metodo di
valorizzazione. Oggi non è supportata perché **manca il dato**, non perché manchi il
programma.

| Cosa | Come |
| --- | --- |
| `magazzino.lotti` | articolo, codice, **data di arrivo/produzione**, **scadenza**, attivo, audit |
| unicità | per **articolo + codice**: lo stesso codice su articoli diversi è legittimo |
| `movimenti.lotto_id` | FK **nullable** — non tutti gli articoli sono a lotti |

⭐ **E il FIFO fisico che ne discende è un SUGGERIMENTO, non un vincolo**: al
prelievo si propone il lotto più vecchio. ⛔ Non si rifiuta una spedizione perché
l'operatore ha preso la scatola sbagliata — non c'è nessun invariante da proteggere,
e questo documento mette i vincoli solo dove un invariante c'è.

### ✅ 2. Per i seriali la verità è il registro; la posizione dell'asset si deriva

⛔ **Oggi ci sono due modelli che non si parlano**: `movimenti.seriale` (una
stringa) e `magazzino.assets` (un'entità vera — articolo, seriale, magazzino,
ubicazione, **stato**, proprietario, contratto). Nessun legame fra i due.

⚠️ E l'asset porta una **posizione propria** (`magazzino_id`, `ubicazione_id`), che è
una seconda risposta alla domanda «dov'è questo pezzo» — la **terza** sede doppia
incontrata in questo documento, dopo la quantità dell'accumulatore (§7-ter) e il
doppio riferimento al documento (§2).

| Cosa | Come |
| --- | --- |
| `movimenti.seriale` (testo) | ⛔ sostituito da **`movimenti.asset_id`**, FK verso `magazzino.assets` |
| dov'è il pezzo | ⭐ **si deriva dal registro** — stesso pattern del valore in §7-ter: la verità è il ledger, la posizione è una lettura |
| `assets.stato_id` | ✅ **resta**: guasto, installato, rientrato sono stati che il registro non conosce |
| `assets.ubicazione` (varchar) | ⛔ **si toglie**: dentro la stessa tabella convivono un testo e un `ubicazione_id` vero |

⭐ **L'asset resta l'anagrafica del pezzo** — che cos'è, di chi è, in che stato — e
smette di essere il suo GPS.

### ✅ 3. Decide l'articolo, e le due colonne sulla causale si ritirano

Due colonne dicevano la stessa cosa da due lati: `catalogo.articoli.requires_serial`
(«io sono un pezzo identificato») e `magazzino.causali.richiede_seriale` («questo
movimento deve registrarlo»). ⛔ **L'incastro non era scritto**, e niente impediva di
marcare una causale «richiede seriale» e usarla su un articolo che seriali non ne ha.

⇒ **Decide l'articolo.** Se il pezzo è identificato, **ogni** suo movimento porta il
seriale — e una causale non può inventarne uno per un articolo che non ce l'ha.
⇒ `causali.richiede_seriale` e `causali.richiede_lotto` **si ritirano**: sono
sempre-vere o sempre-false a seconda dell'articolo, quindi non decidono niente.

⚠️ **E ne discende una colonna che manca**: se l'articolo decide per i seriali, deve
decidere anche per i lotti — ma **`catalogo.articoli` non ha un `requires_lotto`**.
Va aggiunta insieme alla tabella dei lotti, o la decisione 1 non ha chi la governa.

⭐ Due **booleani distinti**, non un'unica colonna «tracciabilità»: un pezzo
identificato può benissimo provenire da un lotto, quindi i due casi convivono.

⚠️ **E oggi il magazzino `requires_serial` non lo legge affatto**: lo leggono un
guard delle distinte e la vista dell'articolo. Con questa decisione diventa un
ingresso della primitiva (§5-bis).

### ✅ 4. Un seriale è UN pezzo

Se un movimento porta un `asset_id`, la quantità dev'essere `1` o `−1`. ⛔ Oggi si
può scrivere un seriale con quantità 30 e passa.

È un vincolo piccolo e facile — ma non messo adesso, il giorno che capita produce
una giacenza che non torna e una caccia lunga.

### ✅ 5. La giacenza per ubicazione entra nel perimetro

⛔ Oggi `vw_giacenza` raggruppa **solo** per articolo e magazzino: l'ubicazione si
scrive su ogni movimento e **non entra in nessun conteggio**. Non si può sapere che
cosa c'è su uno scaffale, benché `magazzino.ubicazioni` sia una tabella fatta bene —
gerarchica, con area, corsia, scaffale, piano, posizione.

⇒ Nasce una vista **più fine**, per articolo × magazzino × ubicazione. ⭐ `vw_giacenza`
**resta com'è**, per articolo × magazzino: è la grana su cui poggiano la formula di
`disponibile` (M-3) e il blocco della primitiva (§5-bis), e non va spostata.

⭐⭐ **E questo salva una decisione che avevamo già preso.** In §4 avevamo stabilito
che lo spostamento fra ubicazioni dello stesso magazzino si modella come **coppia
OUT/IN**. ⚠️ Senza una giacenza per ubicazione quei due movimenti si annullano a
vicenda e **non significano niente**: il magazzino ha la stessa quantità di prima e
nessuno sa che la merce si è spostata. Con la vista fine, la coppia dice esattamente
ciò che deve.

### ⭐⭐ Conseguenza della §4 che non avevamo tracciato: tre colonne diventano ridondanti

Il **modello a coppie** — deciso in §4 per le ubicazioni, e già in uso per i
trasferimenti fra magazzini — dice che ogni movimento ha **una** posizione, non due:
l'uscita ha la sua, l'entrata ha la sua, e le due righe stanno insieme grazie a
`transfer_uid`.

⇒ Ne discende che sul singolo movimento sono ridondanti:

| Colonna | Perché |
| --- | --- |
| `movimenti.magazzino_id_dest` | il magazzino di destinazione è quello **della riga di entrata**, non un secondo campo su quella di uscita |
| `movimenti.ubicazione_id_from` / `_to` | ⇒ **una sola** `ubicazione_id` per riga |
| `causali.richiede_magazzino_dest` | governa un campo che non serve più |

⚠️ E ne discendono anche i due CHECK che le presuppongono
(`chk_mag_movimenti_da_destinazione_distinti`, `chk_mag_movimenti_ubi_from_to_diff`):
descrivono un modello a **un movimento con due estremi**, che non è più il nostro.

⛔ **Non è una pulizia estetica**: due modelli che convivono sono la cosa che questo
documento contesta da tre giorni. Se restano entrambi, il primo che scrive un
trasferimento sceglierà quello sbagliato — e nessun vincolo glielo dirà.

---

## 7-quinquies. ✅ Lo storno: si corregge aggiungendo — DECISO (M-8)

> **Deciso con Tid il 2026-09-02.** Qualcuno registra uno scarico di 100 pezzi
> invece di 10: come si aggiusta?

### ⛔ Il modo che sembrava esserci non funziona

`movimenti.attivo` esiste. Ma `vw_giacenza` è `sum(qta)` **senza nessun filtro**: un
movimento marcato non valido **continua a contare**. ⇒ Oggi si può «annullare» un
movimento e la giacenza non cambia di un pezzo. È l'ennesima struttura che esiste e
non è collegata a niente.

### ✅ Si corregge con una riga opposta, non annullando

| | Che cosa dice la storia |
| --- | --- |
| ⭐ **riga opposta** | *«ho sbagliato, ed ecco la correzione»* — si vedono entrambe |
| ⛔ **annullo** | *«non è mai successo»* |

**E la ragione non è la tradizione contabile: sono le decisioni già prese.**

* **M-4** dice che il valore si **ricalcola dal registro**. ⛔ Se le righe si possono
  disattivare a posteriori, il ricalcolo di ieri e quello di oggi danno numeri
  diversi **sugli stessi fatti**;
* **M-1** ha messo il verso nella quantità ⇒ la correzione ha già la sua forma
  naturale: stessa quantità, segno opposto;
* e la giacenza di un mese fa deve restare quella che era. Con l'annullo **cambia**,
  e nessuno può più ricostruire il perché.

⚠️ L'annullo, per giunta, non lascia scritto **perché**: si vede un flag spento e la
data in cui qualcuno l'ha spento.

### ⭐ La utility che genera lo specchio (idea di Tid)

> *«Sarebbe proprio il caso di fare una utility dalla quale si richiede quale sia la
> riga da rettificare.»*

⭐ **Non è una comodità: è ciò che rende lo storno impossibile da sbagliare.** Se il
movimento contrario si scrive a mano, prima o poi qualcuno sbaglia il costo o il
segno — e la correzione **non corregge**: torna giusta in pezzi e resta storta in
euro.

⇒ Una funzione che **legge la riga originale e ne genera lo specchio**: quantità,
costo, lotto, seriale, ubicazione arrivano da lì, e non c'è niente da ridigitare.

E si incastra da sola con il resto:

* è un'**operazione** nel modello a due livelli di §5-bis: non ricontrolla niente,
  chiama la primitiva;
* ⭐ **lo storno doppio è impedito**: l'identità di §6 comprende il **verbo**, quindi
  un secondo `STORNO` sulla stessa riga collide con il primo. Nessun controllo da
  scrivere.
  🔴 ⚠️ **Ma non sempre — precisazione del 2026-09-04.** Il vincolo di §6 è
  **parziale**: vale dove la sorgente è valorizzata. ⛔ Una **correzione a mano**,
  che è proprio il caso che genera più storni, ha **sorgente vuota** ⇒ il secondo
  storno **passa liscio**. È la stessa avvertenza che §6 fa su sé stessa
  (*«non è la rete per chi non passa dalla funzione»*), e che la prima stesura di
  questa sezione non riportava. ⇒ Sui movimenti senza sorgente, il doppio storno lo
  impedisce **solo la funzione**, non il vincolo.
  ✅ **Chiusa il 2026-09-14 da D-6**: la correzione a mano **è una rettifica**
  (`RETTIFICA_RIGA:{riga}`), la sorgente è `NOT NULL` e il vincolo è pieno ⇒ il
  doppio storno è impedito dal vincolo **ovunque**. Il caveat resta scritto perché
  è la ragione per cui D-6 è andata così.
* ⚠️ **Lo storno ha bisogno di causali sue** — *emerso il 2026-09-14 scrivendo il
  brief*. Sotto il guard di §4 il movimento contrario non può portare la causale
  dell'originale: `SCARICO_VEN` ha segno −1 e lo specchio è +1. ⇒ Due causali
  generiche, `STORNO_POS` (+1) e `STORNO_NEG` (−1), sullo stampo di `RETT_POS`/
  `RETT_NEG`; il *che cosa* è stornato lo dice il legame alla riga originale, non
  la causale. ✅ Confermata (D-L1-d) e seminata il 15-09; la primitiva impone
  che lo storno erediti la sorgente e il costo dell'originale
  (`E_MAG_STORNO_INCOERENTE`, `20260918-18`). ⏳ La **utility** che genera lo
  specchio non esiste ancora: Lotto 3.

### ✅ Al costo ORIGINALE, non alla media di oggi

È il dettaglio che si sbaglia. Lo storno deve usare il **costo del movimento
stornato**, non la media corrente: altrimenti annulla la quantità e **non** il
valore, e il magazzino torna giusto in pezzi restando sbagliato in euro.

⭐ Ed è possibile **solo perché** ogni movimento porta il proprio `costo_unitario` —
la stessa colonna che in §7-ter tiene aperta la porta al FIFO.

### ✅ E `movimenti.attivo` si ritira

Oggi **non fa niente**; domani sarebbe **il secondo modo** di dire «questo non
conta», accanto allo storno. ⛔ Due modelli che convivono sono la cosa che questo
documento contesta da tre giorni — e sarebbe il quinto caso.

⭐ Resta il **legame**: il movimento di storno punta a quello che corregge, così chi
guarda vede due facce dello stesso errore e non due fatti distinti.

---

## 7-sexies. ✅ Il perimetro: a chi appartiene la merce, e chi la vede — DECISO (M-6)

> **Deciso con Tid il 2026-09-02**, partendo da una sua osservazione: *«un magazzino
> potrebbe essere condiviso, e al momento nemmeno l'articolo è legato
> all'emittente»*.

### ⛔ Il problema: le policy non hanno dove agganciarsi

In `vendite` il perimetro discrimina sull'**emittente fiscale**. In `magazzino` non
c'è niente a cui agganciarlo: né `movimenti` né `magazzini` hanno un
`emittente_fiscale_id`, né un legame indiretto.

⚠️ È **lo stesso difetto** che l'analisi acquisti segnala come suo punto ①: *«non è
una colonna in meno, è l'assenza dell'ancora su cui tutto il perimetro poggia»*.
⇒ Senza, le policy non si possono nemmeno **scrivere**.

### ✅ L'emittente sta sul MAGAZZINO

E se il capannone è fisicamente lo stesso, si creano **due magazzini logici**.

⭐ **Non è un ripiego, è la modellazione corretta**: la merce di due soggetti
giuridici diversi **è merce diversa** anche se sta sullo stesso scaffale. Sommarle
sarebbe sbagliato prima ancora che scomodo.

### ⭐⭐ E il perimetro si eredita, non si copia

Con `emittente_fiscale_id` su `magazzini`, tutto il resto ce l'ha già:

* la giacenza è per articolo × **magazzino** ⇒ il perimetro c'è;
* i movimenti hanno `magazzino_id` ⇒ **non serve** aggiungere l'emittente su
  `movimenti`;
* e nessun dato è copiato in due posti, quindi non può divergere.

⛔ **La tentazione sarà duplicare l'emittente sui movimenti «per fare prima nelle
policy».** Va rifiutata: è un dato copiato che si stacca, e `magazzini` è una tabella
minuscola — il join non è il problema.

### ⚠️ Ne discende che il magazzino diventa obbligatorio dove il perimetro deve valere

Verificato il 2026-09-02: `magazzino_id` è **nullable** su `movimenti_attesi` e su
`assets`.

⛔ Un blocco o un asset **senza magazzino sfuggirebbe al perimetro**: non c'è la
strada per arrivare all'emittente, quindi nessuna policy lo intercetta — **e niente
lo segnala**.

⇒ Su **`movimenti_attesi`** il magazzino diventa **obbligatorio**: un'attesa è sempre
attesa *in un posto*.

#### 🔴 Ma su `assets` NO — correzione del 2026-09-04

La prima stesura rendeva `magazzino_id` obbligatorio **anche sugli asset**. ⛔ È
sbagliato due volte:

1. **contraddice la §7-quater**, che poche righe più su toglie `assets.ubicazione` e
   stabilisce che *«la posizione si deriva dal registro»* e che l'asset **non è il suo
   GPS**. Rendere obbligatoria la posizione sarebbe **reintrodurre** la colonna appena
   dichiarata ridondante, e per giunta non omettibile;
2. **costringe a mentire**: `ASSET_INSTALL` porta l'asset **fuori da ogni magazzino**
   (è a casa del cliente). Un `magazzino_id` NOT NULL obbligherebbe a lasciare quello
   di provenienza, oppure a inventare un magazzino fittizio.

⇒ **L'asset prende un `emittente_fiscale_id` proprio.** ⭐ Ed è coerente con la
regola già scritta qui sotto: *l'articolo è una definizione e non prende l'emittente;
la merce ha un proprietario e lo prende*. Un asset **è** un pezzo di merce
specifico — quindi ha un proprietario, e ce l'ha **anche quando non è in nessun
magazzino**, che è precisamente il caso che rompeva l'altra soluzione.

### ⛔ L'articolo NON prende l'emittente

L'articolo **non appartiene a nessuno**: è una **definizione**, non un possesso. In
`vendite` il perimetro sta sui documenti perché un documento *è* di un emittente; un
articolo no.

⇒ Legandolo si spaccherebbe in due il **catalogo**, e con lui le distinte, i
listini, le conversioni di unità di misura e ogni cosa che ci punta.

⭐ **La proprietà della merce la dice il magazzino; l'articolo dice solo che cos'è
quella merce.** La domanda «di chi sono questi pezzi» ha già risposta.

### ✅ Le policy — DECISO (Tid, 2026-09-02)

#### 1. Che cosa entra nel perimetro

⭐ Il criterio è **tutto ciò che porta merce o il suo valore**: `movimenti`,
`movimenti_attesi`, `valore_giacenza`, `magazzini`, `ubicazioni`, `assets`,
`inventari`, `rettifiche`, `trasferimenti` e le loro righe.

🔴 **`lotti` esce dall'elenco** *(corretto il 2026-09-04: la prima stesura lo
includeva)*. Un lotto è **per articolo, non per magazzino** — non ha `magazzino_id`,
quindi il perimetro «ereditato» non lo raggiunge: sarebbe una tabella dichiarata
protetta **e senza ancora**. ⭐ E la risposta giusta non è dargliene una: **un lotto è
una definizione** — *«questa partita di questo articolo»* — esattamente come
l'articolo. Chi possiede la merce di quel lotto lo dice il **registro**, che è
protetto.

⛔ **Fuori i vocabolari** (`causali`, `ambito_causale`): sono uguali per tutti, non
c'è niente da nascondere. ⛔ E fuori **l'articolo**, coerentemente con la decisione
qui sopra: non appartiene a nessuno.

#### 2. Chi vede: solo l'operatore

Il perimetro dell'**emittente** è il recinto esterno e vale per chiunque. ⚠️ Ma
dentro quel recinto, **operatore e cliente non sono la stessa cosa** — e non per
l'emittente: **per che cosa contiene il magazzino**.

Aprendolo a una controparte, quella vedrebbe:

* il **costo medio** degli articoli, cioè quanto li abbiamo pagati ⇒ **il nostro
  margine**;
* **quanti pezzi ci sono** ⇒ *«ne hanno solo 3, tratto sul prezzo»*;
* ⛔ **i blocchi degli altri clienti**, con nome e cognome, visto che portano
  `soggetto_ruolo_id`.

⇒ **Solo `OPERATORE`.** ⭐ E con la forma già in uso in `vendite` questo viene
gratis: la condizione è *«se sei operatore, e…»*, quindi ogni altra veste è esclusa
senza scrivere una seconda regola.

#### ⭐ 3. Ma il portale non resta al buio — DECISO

*«Compreso il fatto di quello che può vedere un cliente da web e la possibilità di
vedere disponibile per consegna immediata»* (Tid).

⚠️ **«Non vede il magazzino» non vuol dire «non sa niente della sua merce».** Un
cliente vede già i **suoi documenti**, governati dalle regole che esistono in
`vendite`: *«la tua merce è pronta / è partita»* è un fatto del **suo documento**.

⇒ E dove serve dirgli qualcosa sulla merce — **«disponibile per consegna
immediata»** — glielo dice una **vista dedicata** che espone **quel solo dato**, non
un accesso al registro.

⭐ È la differenza fra **rispondere a una domanda** e **aprire un archivio**. E la
vista può nascere quando servirà: il perimetro deciso qui non la impedisce, la
richiede.

#### ⚠️ 4. Accendere davvero, e anche per il proprietario

Una policy **scritta e non accesa non protegge niente e sembra proteggerlo**. ⛔ Non
è teorico: in `acquisti` ce ne sono **due, ferme da mesi** — l'analisi acquisto le
chiama *«la forma di difetto peggiore, quella che nessun test rende rosso»*.

⇒ Serve l'`ENABLE`, e serve che valga **anche per il proprietario della tabella**:
senza, chi ha i privilegi alti la scavalca **senza saperlo**.

🔴 **Precisato il 2026-09-14, contro il DB vivo**: la seconda metà di questa frase
è la postura di **nessuna** tabella del progetto. `dbops.vw_rls_perimetro_scoperto`
lo dichiara nel proprio `COMMENT`: *«FORCE ROW LEVEL SECURITY non entra nel
criterio: in questo database nessuna tabella lo usa, e l'applicazione non è
owner»*. Le nove famiglie di `vendite` sono `ENABLE` senza `FORCE`, a parità. ⇒
`magazzino` nasce **come loro**: `ENABLE`, non `FORCE`. Chi vuole cambiare la
postura la cambia per tutti, in un cantiere suo — non qui.

> ### ⭐ Il perimetro atterra CON l'ancora, non dopo — riquadro del 2026-09-14
>
> Scrivendo il brief è emerso un vincolo di sequenza che questa sezione non
> diceva. Il presidio `dbops.vw_rls_perimetro_scoperto` (in servizio dall'11-09)
> marca `NON_DICHIARATO` **ogni tabella con una FK verso una tabella protetta** che
> non abbia policy + `ENABLE`, e il suo pgTAP va rosso. Dare `emittente_fiscale_id`
> a `magazzini` con una FK verso `anagrafiche.emittenti_fiscali` (protetta) e
> **non** armarla nello stesso giro farebbe rosso il presidio; armarla e non armare
> le figlie (`movimenti`, `ubicazioni`, `inventari`, le note…) lo farebbe rosso
> lo stesso, sulle figlie.
> ⇒ **Tutto M-6 sta nel Lotto 1**, con il DDL: l'ancora, la variante
> `via_magazzino`, le policy su tutte le tabelle del perimetro, l'`ENABLE`, e la
> cancellazione della riga **65** di `dbops.rls_perimetro_debito` (`magazzino.assets`,
> «quale delle due chiavi porta il perimetro» — la risposta è la terza,
> `emittente_fiscale_id` proprio, e un debito estinto che resta a registro fa
> rosso anche lui). *Il perimetro si chiude quando nasce l'ancora, non quando
> arriva il primo scrittore.*

#### ⚠️ 5. Le viste, o si apre una porta di servizio

Ogni vista del dominio deve leggere **con i diritti di chi la interroga**, non del
suo creatore — altrimenti scavalca il perimetro restando a norma di GRANT.

⛔ **E quella marcatura si azzera da sola a ogni riscrittura della vista**: è una
trappola già registrata nel progetto, e qui le viste sono la superficie principale
(giacenza, valorizzata, costo medio, disponibilità).

#### ⭐⭐ 6. L'aggregato non è mai parziale — merito dell'ancora

Questo dominio è fatto quasi solo di **somme**. Con la RLS attiva, una somma conta
**solo le righe visibili** — e una persona con visibilità parziale leggerebbe *«40
pezzi»* dove ce ne sono 100, **senza nessun errore né avvertimento**.

⭐ **Nel nostro modello non può succedere, ed è merito della scelta dell'ancora**:
l'emittente sta sul **magazzino**, non sul movimento. Un magazzino appartiene a **un
solo** emittente ⇒ chi lo vede ne vede **tutti** i movimenti, o nessuno. **Non
esiste il mezzo.**

⚠️ Sarebbe esistito con l'emittente sul singolo movimento: un magazzino avrebbe
potuto contenere righe di due emittenti, e la somma sarebbe stata monca. ⇒ È una
conferma che quella scelta risolve anche un problema che non stavamo guardando.

🔴 **Il rilievo del 2026-09-04 diceva che vale solo alla grana del magazzino, e che
la vista per articolo — sommata su tutti i magazzini — sarebbe parziale. ✅ Verificato
il meccanismo, NON è così**, e la ragione è più solida della convenzione che stavo per
proporre.

⭐⭐ **Esiste un emittente ATTIVO di sessione.** Il corpo di
`script.fn_check_user_emittente_scope` lo dichiara nella sua seconda regola:
*«emittente attivo diverso da quello richiesto → false — restringe **CHIUNQUE**, anche
il super admin»*.

⇒ **Qualunque query, di chiunque, vede un emittente solo.** La *whitelist* può
contenerne più d'uno — un operatore può **cambiare** emittente — ma in una sessione ne
è attivo uno: non può abbracciarne due insieme.

⭐⭐ **Ed è una regola generale del progetto, non una peculiarità del magazzino**
(Tid, 2026-09-04): *«tutte le attività legate all'emittente obbligano alla scelta di
un emittente — anche il super admin, e lo facciamo già in altre attività»*. Il
meccanismo del DB e la prassi applicativa dicono quindi la stessa cosa, e la seconda
regola della funzione — *«restringe chiunque, anche il super admin»* — non è una
difesa teorica: è come si lavora.

⇒ Ne discende una semplificazione che vale per tutto questo documento: **nessuna
operazione di magazzino attraversa mai due emittenti** — né una lettura, né la
primitiva, né la utility di storno.

⇒ Ne discende che la giacenza **per articolo**, sommata su tutti i magazzini, è
**completa**: sono tutti i magazzini dell'emittente attivo, cioè **tutto ciò che c'è
per chi sta guardando**. ⭐ E lo stesso vale per `vw_costo_medio_globale`: dentro un
emittente, «globale» vuol dire davvero *tutti i miei magazzini*.

⛔ **E raggruppare per emittente sarebbe inutile**: darebbe sempre una riga sola.

### ⚠️ Ma resta un caso, ed è la PRIMA regola della stessa funzione

*«`p_auth_user_id` NULL → true (job batch)»*: un **processo automatico** non ha un
utente, quindi **vede tutto, attraverso gli emittenti**.

⇒ Per le letture non cambia niente. ⛔ Ma `valore_giacenza` è una **copia ricostruita
da una funzione** (§7-ter): se quel ricalcolo girasse come job, calcolerebbe
**attraversando gli emittenti**.

⭐ **Due rimedi, e sono entrambi già nel modello:**

1. la copia è per **articolo × magazzino**, e il magazzino porta l'emittente ⇒ finché
   il ricalcolo scrive a quella grana **non mescola nulla**;
2. ⭐ e, coerentemente con la regola generale qui sopra, **anche un processo
   automatico legato all'emittente sceglie l'emittente**: un ricalcolo che serve N
   emittenti li **itera**, non li somma.

⚠️ **Va scritto lo stesso**: la tentazione di fare un aggregato «per articolo» dentro
un batch — dove nessuna sessione lo restringe — è precisamente quella che romperebbe
il confine **senza che nessuno se ne accorga**. Sotto RLS diventa *«la media dei magazzini che
posso vedere»* — corretto, ma il nome «globale» promette un'altra cosa: va chiarito
nel `COMMENT` o rinominato.

#### ⭐ 7. E non serve un meccanismo nuovo

Le policy di `vendite` hanno tutte la stessa forma — `rls_<tabella>_ef_whitelist`,
su `ALL`, con la condizione *«ruolo = OPERATORE **e** emittente nella tua
whitelist»* — e la funzione di appoggio **esiste già in più varianti**, a seconda di
come si raggiunge l'emittente: direttamente, tramite il soggetto, tramite la
commessa.

⇒ La nostra è *«tramite il magazzino»*: **una variante in più di una famiglia che
c'è**, non un'invenzione.

📌 **Resta da scrivere il codice** — le policy, la variante della funzione, i
`GRANT` — ma nessuna decisione aperta.

---

## 7-septies. ✅ La regola di allocazione — CHIUSA come non necessaria (M-9)

> **Chiusa con Tid il 2026-09-02**, e chiusa **invece che rinviata**: una voce che
> nessuno può chiudere, perché non ha nulla che la inneschi, resta lì per anni e fa
> sembrare incompiuto un lavoro finito. ⛔ È debito che assomiglia a lavoro.

### Perché era stata aperta, e perché non serve più

Nasceva come **prerequisito dell'avviso sull'impegno derivato**: se il sistema
avvisa *«ci sono altri impegni»*, l'operatore deve sapere **chi ha la precedenza**, o
l'avviso non gli dice che cosa fare.

Nel frattempo, però, abbiamo deciso — una decisione dopo l'altra:

* l'impegno **derivato** non ferma niente, e **l'avviso non si fa** (§7-bis);
* il blocco **esplicito** ferma, ma è **l'atto di una persona**, con nome, data e
  intestatario;
* e si **libera a mano**, deliberatamente.

⇒ ⭐ **La precedenza non serve calcolarla: l'ha già decisa qualcuno.** Se due blocchi
contendono la stessa merce, chi deve spedire li vede entrambi con nome e cognome e
sceglie — o chiama. Non c'è nessuna decisione automatica da prendere, quindi non c'è
nessuna regola da scrivere.

⭐⭐ **M-9 non ha più un consumatore**: era il prerequisito di una cosa che abbiamo
scelto di non fare.

### ⭐ Che cosa esiste già, se un giorno servisse

*(Censito il 2026-09-02: è più di quanto sembrava, ma non la cosa che servirebbe di
più.)*

| Dato | Dove | Note |
| --- | --- | --- |
| **data dell'ordine** | `vendite.ordini.data` | ✅ c'è |
| **data di consegna** richiesta/confermata | — | ✅ **a DB dal 13-09** (P-3 del [brief modifiche certe](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md), chiuso il 14-09): `vendite.ordini_righe.data_consegna_confermata` e `acquisti.ordini_righe.data_consegna_confermata_fornitore` esistono; ⭐ era il **quarto** cantiere indipendente che le chiedeva. ⚠️ Quelle di `acquisti` non hanno ancora un consumatore: le prende il cantiere acquisti |
| **priorità** `ALTA`/`NORMALE`/`BASSA` | `vendite.commesse.priorita_operativa` | ⭐ esiste già — ⚠️ ma sta sulla **commessa**, non sul cliente |
| **categoria cliente** | `anagrafiche.billing_account.categoria_cliente_id` | ⚠️ sta sul **BA**, ed è nata per i **listini** |
| **priorità del cliente** | — | ⛔ **non esiste** |

*(E `pratiche.pratiche.priorita_id` ha già un vocabolario di priorità: se servisse un
elenco, c'è un precedente da guardare invece di inventarne uno.)*

### Che cosa potrebbe alimentarla

| Criterio | A che cosa serve | Il dato |
| --- | --- | --- |
| data di consegna **promessa** | chi è stato impegnato per primo | in arrivo |
| data dell'**ordine** | equità: primo arrivato, primo servito | c'è |
| **priorità del cliente** | scelta commerciale | ⛔ manca |
| **valore** della riga o dell'ordine | non lasciare a piedi l'ordine grosso | c'è |
| **penale contrattuale** | il contratto che costa se si sfora | ⚠️ non modellata |
| ⭐ **non frammentare** | meglio completare un ordine che lasciarne due a metà | **derivabile** |
| ⭐ **completare una fornitura iniziata** | non lasciare il cliente con mezza consegna | **derivabile** dal ponte di evasione |

⭐ Gli ultimi due sono i più interessanti: **non chiedono nessun dato nuovo**, e sono
esattamente quelli che un magazziniere applica da sé senza che nessuno glielo dica.

### ⭐ Che forma avrà, quando tornerà — e che forma NON avrà

L'idea di Tid è *«un algoritmo che ogni emittente stabilisce, con i parametri che
sceglie»*. **La forma è giusta; il momento no.**

⚠️ E il precedente da citare è di casa: `pratiche` è un motore generico, costruito
bene, rimasto **senza consumatori** — al punto che la mappa concentrica dice che le
sue decisioni di design *«sono ipotesi del progettista, non risposte a esigenze
osservate»*. ⛔ Qui sarebbe peggio: un algoritmo di priorità calcolerebbe una
classifica che **nessuno consuma**.

⭐ **E nella grande maggioranza dei casi reali la priorità non è un algoritmo: è un
elenco ordinato di criteri.**

> *«Prima la data promessa; a parità, la priorità del cliente; a parità, la data
> dell'ordine.»*

Una riga di configurazione per criterio, **per emittente**, applicata come
ordinamento. Nessun motore, e il caso nuovo si copre spostando una riga invece di
scrivere codice.

⇒ E se un giorno servisse un **calcolo vero**, il progetto ha già dove agganciarlo:
il registro delle implementazioni (`dbops.pipeline_task_registry_impl`), dove il nome
della funzione sta **a catalogo** e non in un campo di testo libero.

### 📌 La condizione che la fa tornare

> **Il giorno in cui si volesse un avviso — o un blocco — basato sull'impegno
> DERIVATO.**

Fino ad allora non serve. ⚠️ E prima di allora servirebbe comunque il dato che oggi
manca: una **priorità sul cliente**, perché il criterio più naturale — la data
promessa — arriva col brief, e senza di essa una priorità girerebbe su ciò che resta:
la data dell'ordine e una categoria nata per i listini.

---

## 8. L'ordine in cui conviene costruire

> Dalla nota di revisione del 2026-09-01. ⚠️ I riferimenti a **D-4**, **D-6** e
> **D-7** sono decisioni dell'[analisi aggancio §8](analisi-db-magazzino-aggancio-documento-e-produzione.md): questo documento
> le presuppone, non le prende.

| # | Passo | Perché in questo punto |
| --- | --- | --- |
| 1 | ✅ **Il verso è deciso** (§4: sta nella quantità) ✅ **e costruito** nel Lotto 1: guard `trgfn_movimenti_guard_verso` su `movimenti` e `movimenti_attesi`, `segno IN (-1, 1)` | è la cosa che, sbagliata, falsa ogni numero a valle — e correggerla dopo vuol dire ricalcolare tutto. ⛔ Il guard va **prima** della prima riga, non dopo: senza, la prima convenzione che entra diventa quella vera |
| 2 | ✅ **Inventario iniziale** come primo carico — costruito nel Lotto 2 (`INV_INIZIALE` dedotta dallo stato del registro), con la rettifica; ⏳ collaudo a video | è la sorgente più semplice: **non ha un documento a monte**, quindi collauda il registro senza dipendere da nessuna catena |
| 3 | ⏳ **Scarico da bolla di vendita** come primo consumo — Lotto 3, senza brief | il primo caso con un documento vero dietro, su una catena che esiste già ed è collaudata |
| 4 | **Acquisti** come seconda sorgente | entra su un registro già provato, e porta con sé la sua decisione (D-7) |
| 5 | **Produzione** come terza | ⭐ se i punti sopra sono stati decisi bene, è *una sorgente in più e un set di causali*, non una riscrittura |

> ⭐ **Ereditato il 2026-09-14 dal brief delle modifiche certe, alla sua
> chiusura (decisione di Tid)**: il **presidio di prontezza su
> `catalogo.articoli.gestito_a_magazzino`**. La colonna è nata `NOT NULL
> DEFAULT false` (fail-safe), quindi al rilascio *nessun* articolo movimenta
> giacenza e nessun rosso lo dice — è la stessa forma di `ambito_causale_id`
> (§3). La forma è già fissata nel brief (§7): una vista `dbops` a **una riga**,
> `stato = 'MARCATI'` se esiste almeno un articolo con `gestito_a_magazzino =
> true`, altrimenti `'NESSUNO_MARCATO'`; iscritta in `presidi.csv` con natura
> `ZERO`, `colonna_stato = stato`, `stato_atteso = 'MARCATI'` — lo zero
> suona, il pieno tace; ⛔ non una natura nuova per un caso solo. ⭐ **Va
> scritto col passo 2** (✅ *scritto nel Lotto 2*: `dbops.vw_articoli_a_magazzino_prontezza`,
> in `presidi.csv` con cadenza settimanale, D-L2-k) (inventario iniziale): è il momento in cui i primi
> articoli vengono marcati e la primitiva M-2 comincia a leggere la colonna —
> prima, sarebbe un allarme che suona per mesi senza che nessuno possa agire,
> e un presidio così viene spento. Il brief lo teneva per sé *«perché non si
> può delegare a un cantiere che forse non parte»*: dall'11-09 questo cantiere
> **parte**, e la premessa è caduta.

⚠️ **Il passo 3 è il primo che ha bisogno della §6**: è lì che nasce il
doppio scarico, e la chiave dell'operazione va decisa prima di scriverlo — non
dopo aver tolto l'indice.

⚠️ **Ma il passo 2 è già la prova della D-6, e va saputo prima di farlo.**
L'inventario iniziale è proprio il caso del **movimento senza documento
commerciale** — mentre oggi le tre caselle del riferimento sono **obbligatorie**.
Quindi la primissima riga che si scriverà in magazzino è esattamente quella che
mette alla prova la decisione che nessuno ha ancora preso. È un ottimo collaudo
e una pessima sorpresa: **la D-6 va decisa prima del passo 2**, non durante.
✅ **Decisa il 2026-09-14** (analisi aggancio §8-quater): senza documento
*commerciale* sì, senza **sorgente** no — l'inventario iniziale ha la propria
riga (`INVENTARIO_RIGA`), e quella è la sorgente. Il passo 2 non mette più alla
prova niente: la prova l'ha fatta la decisione.

> ⭐ **Come si spacca in lotti (2026-09-14)** — la sequenza sopra resta la
> sequenza dei **consumatori**; il lavoro si organizza così:
>
> | Lotto | Cosa | Brief |
> | --- | --- | --- |
> | **1 — DB, terreno vuoto** ✅ *chiuso 15-09, PR #1593* | tutto il DDL deciso da M-1 → M-9 e da D-1/D-4/D-6/D-7/D-8, **più il perimetro RLS di M-6** (riquadro di §7-sexies) e i pgTAP strutturali | [brief-db-magazzino-lotto-1-terreno-vuoto](../work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md) |
> | **1-bis — DB, prerequisito del 2** (15-09) ✅ *chiuso 17-09, PR #1598* | l'**emittente di default** come building block unico (`script.trgfn_default_emittente_fiscale`), montato su `magazzini`/`assets` **e** al posto delle quattro copie di vendite, che si ritirano nello stesso giro (decisione di Tid: *«che aspettiamo, la produzione, per fare questi refactor?»*). Senza, il primo magazzino creato dal pannello muore con `23502` | [brief-db-emittente-di-default-un-bb-solo](../work-done/brief-db-emittente-di-default-un-bb-solo.md) |
> | **2 — DB, motore** | la primitiva (M-2), la `fn_check` di disponibilità separata, l'operazione **inventario iniziale** (passo 2) **e la rettifica** (la seconda operazione senza documento commerciale, D-6), la vista di disponibilità (M-3, senza le colonne che aspettano il satellite D-17), la vista degli orfani (D-9), il presidio di prontezza su `gestito_a_magazzino`, i pgTAP di comportamento (M-7), **la porta** (`zeroerp_app` in sola lettura sul ledger, primitiva DEFINER del proprietario). ⚠️ Con `requires_lotto` esposto in vista/BE/drawer **senza** il lock BoM di `requires_serial` (Lotto 1 §4.3) | [brief-db-magazzino-lotto-2-motore](../work-done/brief-db-magazzino-lotto-2-motore.md) — ✅ **quattordici D-L2 decise il 17-09**, DB applicato il 18-09 (22 changeSet, PR #1605), consegnato il 22-09, archiviato il 24-09. Seguito da [2-bis BE/FE](../work-done/brief-db-magazzino-lotto-2-bis-be-fe.md) (23-09) e dai [verbi con permesso](../work-done/brief-db-magazzino-verbi-con-permesso.md) (24/25-09). ⏳ Collaudo a video di Tid |
> | **3** | scarico da DDT di vendita (passo 3): aggancio a `EMESSO`, con **`magazzino_id` sul DDT** (D di disegno da prendere), filtro degli articoli non gestiti e conversione UoM; utility di storno (M-8); posting del **trasferimento** — ✅ la D è presa (D-L2-g, 17-09): `magazzino.trasferimenti` è il trasferimento **interno** (prende `ubicazione_id_da`/`_a` sulle righe e il CHECK allargato), quello con trasporto è il DDT con causale `TRASFERIMENTO`; apertura/rilascio del **blocco manuale**, come verbi con `fn_guard_azione` | [brief-db-magazzino-lotto-3-scarico-da-ddt](../work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md) — ✅ **lato DB applicato e verde** (28-09): undici D di Tid, changeSet `20260928-60 → -83`, pgTAP verdi col runner; restano le richieste a BE/FE (brief §6) e la CI da zero. ⚠️ Il **carico da reso cliente** esce in un **3-bis** subito dopo (D-L3-i) |
> | **3-bis** | carico da **reso cliente** (`CARICO_RESO_VEN`, sorgente `RESO_VENDITA_RIGA`): il reso impara il magazzino di rientro e i suoi prelievi — seconda occorrenza del satellite dei prelievi, regola del 2 (D-L3-i) | [brief-db-magazzino-lotto-3-bis-carico-da-reso](../work-done/brief-db-magazzino-lotto-3-bis-carico-da-reso.md) — ✅ **lato DB applicato e verde** (29-09): otto D di Tid, changeSet `20260928-84 → -98` e `20260929-01 → -04`; il rientro **punta al prelievo d'origine** (non è la seconda occorrenza dei prelievi, che resta il Lotto 4); restano le richieste a BE/FE e la CI da zero |
> | **eventi asset** | `ASSET_INSTALL`/`ASSET_RIENTRO`, `is_installazione_asset`, `assets.stato_id`: il pezzo lascia il magazzino e cambia stato — un documento in più (D-L2-l) | — |
> | **4** | ricezione acquisti = Lotto 3 dell'[analisi acquisti §10](analisi-simmetria-ordini-acquisto.md) | — |
> | **5** | produzione (passo 5) — serve **D-5** e la §7 dell'analisi commessa | — |

⚠️ **E una nota sul passo 5**, per non lasciare in piedi una rassicurazione
sbagliata: *«la produzione sarà una sorgente in più, non una riscrittura»* è vero
**solo se D-4 e D-6 vengono decise adesso** (✅ *decise il 14-09 e costruite nel Lotto 1: `uq_mag_movimenti_docref` non esiste più*). Se il vincolo di §5 resta com'è, la
produzione — che preleva e versa **in più riprese**, quindi molti movimenti per
una sola riga di ordine — quel vincolo lo riscrive. E il «nuovo set di causali»
in buona parte **c'è già** (§6): quello che manca è l'ordine di lavoro, non le
causali.

---

## 9. ⚠️ Che cosa manca ANCORA a questa analisi

> ⭐ Questo documento **consolida**, non completa. Ciò che segue è il secondo giro,
> concordato con Tid il 2026-09-02: *«poi completeremo l'analisi con quello che
> manca»*. È elencato qui perché un'analisi incompleta che non dichiara i propri
> buchi si legge come completa.

| # | Che cosa manca | Perché non si può dedurre da ciò che c'è |
| --- | --- | --- |
| **M-1** | ✅ **CHIUSA il 2026-09-02 — A: il verso sta nella quantità** (§4). ⚠️ Restano due cose **da fare**, non da decidere: il **trigger guard** `sign(qta) = causali.segno` su entrambe le tabelle (un `CHECK` non può: non guarda altre tabelle), e il `COMMENT` su `vw_giacenza` che dice *perché* è corretta senza join. ✅ E il residuo dello `0` è **chiuso il 2026-09-02**: esce dal CHECK, lo spostamento fra ubicazioni diventa coppia OUT/IN come il trasferimento | — |
| **M-2** | ✅ **CHIUSA il 2026-09-02 — §5-bis**, con una **correzione in giornata**: due livelli (primitiva + operazioni), primitiva **guidata dalle causali**, blocco su `(magazzino, articolo)` **solo in uscita**, ⛔ nessuna domanda nella scrittura. 🔴 Corretto che la primitiva guarda **fisico meno blocchi espliciti altrui**, non «solo il fisico», e che il controllo è una **funzione separata** chiamata dai due momenti. ⚠️ Resta legata alla **D-1** solo per la firma dell'origine | — |
| **M-3** | ✅ **CHIUSA il 2026-09-02 — §7-bis, «La formula di disponibile»**: `disponibile = giacenza − blocchi espliciti`, la **stessa** formula che la primitiva controlla; «posso prometterla» è una **proiezione con le date**, non un numero; il conteggio è **guidato da `config.sorgenti`**, non da query scritte a mano | — |
| **M-4** | ✅ **CHIUSA il 2026-09-02 — §7-ter**: il trasferimento **muove il valore**; **CMP** unico metodo e `fifo` fuori dal vincolo (il metodo non è della causale); l'accumulatore tiene **solo il valore** e si chiamerà **`valore_giacenza`**; media **ricalcolabile** con vista di presidio. ⚠️ Restano da fare: la FK mancante su `articolo_id` e il `COMMENT` su `costo_unitario`, che significa due cose opposte nei due versi | — |
| **M-5** | ✅ **CHIUSA il 2026-09-02 — §7-quater**: il **lotto diventa una tabella** (con data d'arrivo, che rende calcolabile il FIFO fisico); per i seriali la verità è il **registro** e `movimenti.seriale` diventa `asset_id`; **decide l'articolo** e le due colonne sulle causali si ritirano (⚠️ manca `articoli.requires_lotto`); `abs(qta) = 1` con un seriale; **giacenza per ubicazione** in perimetro. ⭐⭐ Emerso che il modello a coppie rende ridondanti `magazzino_id_dest`, `ubicazione_id_from/_to` e `richiede_magazzino_dest` | ⚠️ *14-09*: **va propagata alle righe delle testate** — `inventari_righe`, `rettifiche_righe`, `trasferimenti_righe` portano `lotto`/`seriale` come testo, e sotto D-6 il movimento nasce da quelle righe: senza `lotto_id`/`asset_id` lì, l'operazione non ha niente da passare alla primitiva (Lotto 1) |
| **M-6** | ✅ **CHIUSA il 2026-09-02 — §7-sexies**: `emittente_fiscale_id` sta sul **magazzino**, e il perimetro **si eredita** via `magazzino_id` (⛔ niente colonna copiata sui movimenti; ⛔ l'articolo non prende l'emittente). ⚠️ `magazzino_id` deve diventare **obbligatorio** su `movimenti_attesi` ~~e `assets`~~ (*su `assets` no: corretto il 04-09 in §7-sexies, l'asset prende un emittente proprio*), oggi nullable. **Solo `OPERATORE`**; il portale è servito da una **vista dedicata** («disponibile per consegna immediata»), non dal registro. ⭐⭐ E l'aggregato **non è mai parziale**, merito dell'ancora sul magazzino. 📌 Resta il **codice**, nessuna decisione. ⚠️ *14-09*: il codice va nel **Lotto 1**, con l'ancora — il presidio `vw_rls_perimetro_scoperto` non ammette una FK verso una tabella protetta senza policy (§7-sexies, riquadro); e `ENABLE` senza `FORCE`, come tutto il progetto | — |
| **M-7** | **La copertura pgTAP**: il dominio ha **un solo file** (`test-movimenti-vincoli-v1.sql`, 21-08) | ⚠️ **Dipende da M-6**: in questo progetto i test girano **come l'applicazione, con RLS attiva** — scriverli prima che il perimetro esista significa scriverli due volte |
| **M-8** | ✅ **CHIUSA il 2026-09-02 — §7-quinquies**: si corregge con una **riga opposta**, generata da una **utility** che legge l'originale (⭐ così lo storno non può divergere dal movimento che corregge), al **costo originale** e non alla media di oggi; `movimenti.attivo` **si ritira**. ⭐⭐ Lo storno doppio è impedito **gratis** dall'identità di §6 | — |
| **M-9** | ✅ **CHIUSA il 2026-09-02 — §7-septies, come «non necessaria»**: era il prerequisito dell'avviso sull'impegno derivato, e quell'avviso abbiamo deciso di non farlo ⇒ **non ha più un consumatore**. 📌 Scritto che cosa la fa **tornare**, che **forma** avrà (elenco ordinato di criteri per emittente, ⛔ non un motore) e il dato che **mancherebbe** (una priorità sul cliente) | — |

### ✅ Realizzato — stato al 2026-09-26

> Verificato sulla doc auto-generata (`docs/it/dbzero/magazzino/`, `dbzero/dbops/`),
> sui CSV di `80_data` e sui brief chiusi. La tabella sopra resta com'era scritta:
> le righe «restano da fare» sono storia, lo stato è qui.

| # | Che cosa esiste oggi | Che cosa resta, e dove |
| --- | --- | --- |
| **M-1** | guard `magazzino.trgfn_movimenti_guard_verso` (`trg_movimenti_a10_…`, `trg_movimenti_attesi_a10_…`, `E_MAG_MOVIMENTO_VERSO_INCOERENTE`); `chk_magazzino_causali_segno` = `segno IN (-1, 1)`; `COMMENT` su `vw_giacenza`; su `movimenti_attesi` `chk_mag_movimenti_attesi_qta_non_zero` al posto di `qta > 0` (`20260915-02`, `-13`, `-17`) | — |
| **M-2** | primitiva `magazzino.fn_scrivi_movimento` (DEFINER del proprietario); controlli `script.fn_check_disponibilita_uscita` (pura, INVOKER) e `script.fn_check_riga_magazzino`; lock advisory a due argomenti su (magazzino, articolo) solo in uscita; porta = `REVOKE` di scrittura all'app su `movimenti`/`valore_giacenza` + guard BB `trgfn_guard_emittente_scope` (D-L2-b). ➕ Non previsti qui: `qta` in UoM base (D-L1-a), esonero dei blocchi per `is_rettifica` (D-L2-d), `magazzini.usa_ubicazioni` (D-L2-m). Dal 24-09 l'app esegue solo `fn_posta_inventario`/`fn_posta_rettifica` (DEFINER, `fn_guard_azione(…, 'registra_magazzino')`) | il controllo **alla conferma del DDT** (Lotto 3). ⚠️ La riga «valorizza o no ← `causali`» di §5-bis è superata: valorizzano tutte, e il costo si decide dalla **struttura** del movimento (D-L2-c) |
| **M-3** | `vw_disponibilita` (articolo × magazzino) e `vw_disponibilita_articolo`: `giacenza`, `bloccata` (firmata), `disponibile = giacenza + bloccata`, `n_blocchi` (D-L2-j, `20260918-24`); `movimenti_attesi` con `soggetto_ruolo_id` + `nota`, stati `APERTA`/`CHIUSA` (D-L1-b) | impegnata / potenziale / in arrivo e la proiezione con le date aspettano il satellite **D-17** di acquisti e il Lotto 3; i verbi per aprire e liberare un blocco manuale sono del Lotto 3 |
| **M-4** | `valore_giacenza` (solo valore, `20260915-08`) con FK all'articolo; `COMMENT` su `costo_unitario`; `fn_ricalcola_valore_giacenza` (ri-somma); presidi `dbops.vw_magazzino_valore_giacenza_divergente` e `vw_magazzino_movimenti_senza_costo`; ➕ `costo_unitario` su righe di inventario e rettifica (D-L2-c) | — |
| **M-5** | `magazzino.lotti` (`data_arrivo NOT NULL`); `articoli.requires_lotto`; `movimenti.asset_id`/`lotto_id` con `abs(qta) = 1` sul seriale; una sola `ubicazione_id`; ritirate `magazzino_id_dest`, `ubicazione_id_from/_to`, `richiede_lotto`/`_seriale`/`_magazzino_dest`; propagata alle righe delle testate; `vw_giacenza_ubicazione` | — |
| **M-6** | RLS su 23 tabelle via `script.fn_scope_ef_whitelist_via_magazzino` (`ENABLE` senza `FORCE`, `20260915-16`); `magazzini.emittente_fiscale_id NOT NULL`, `assets.emittente_fiscale_id` proprio; `movimenti_attesi.magazzino_id NOT NULL`; default dell'emittente dal BB `script.trgfn_default_emittente_fiscale` (Lotto 1-bis) | la vista per il **portale** («disponibile per consegna immediata»): nessun lotto assegnato |
| **M-7** | una ventina di file pgTAP: 17 in `db/pgtap/magazzino/` (il v1 dei vincoli è diventato `test-movimenti-vincoli-v2.sql`), più `rls/test-rls-magazzino-perimetro-v1`, `dbops/test-sorgenti-orfane-v1`, `dbops/test-articoli-a-magazzino-prontezza-v1` | cresce coi lotti |
| **M-8** | `STORNO_POS`/`STORNO_NEG`; `storno_di_movimento_id` con `uq_mag_movimenti_storno_di`; `movimenti.attivo` ritirato; ramo storno nella primitiva (sorgente e costo dell'originale, `E_MAG_STORNO_INCOERENTE`) | la **utility** che genera lo specchio: Lotto 3 |
| **M-9** | chiusa come non necessaria | — |

---

## 10. Che cosa resta negli altri documenti, e perché

⭐ **Non tutto ciò che nomina un carico o uno scarico appartiene qui.** Il criterio
usato per dividere: *questo documento tiene il MOVIMENTO; gli altri tengono il
DOCUMENTO che lo causa e le decisioni di dominio.*

| Documento | Che cosa gli resta | Perché non è di qui |
| --- | --- | --- |
| [analisi aggancio documento e produzione](analisi-db-magazzino-aggancio-documento-e-produzione.md) | **D-1 → D-9**: come un movimento dichiara la propria origine, il guard della sorgente polimorfa, l'ODL sorgente-o-anello | è la scelta su *come si nomina l'origine*, che questo documento **presuppone**. ⚠️ La D-4 in particolare vive lì e la sua risposta sta qui in §6: le due si leggono insieme |
| [analisi simmetria ordini acquisto](analisi-simmetria-ordini-acquisto.md) | la **ricezione come documento**: le quattro destinazioni di una riga ricevuta, i resi al fornitore, le code, la rinuncia, la porta del ramo credito (D-14) | è il ciclo di un **documento di acquisto**. Il carico è il suo effetto sul magazzino, e l'effetto è di qui |
| [analisi commessa e produzione](analisi-db-commessa-e-produzione-predisposizione.md) | l'ODL come oggetto, la distinta, il consuntivo, le dimensioni del ciclo di vendita | i prelievi e i versamenti di produzione sono **movimenti**, e stanno qui; l'ordine di lavoro che li ordina sta lì |
| [brief modifiche certe](../work-done/brief-db-modifiche-certe-ciclo-vendita-e-articolo.md) — ✅ chiuso il 14-09 | `articoli.gestito_a_magazzino` (a DB dal 13-09). ⚠️ Il suo **registro di prontezza** invece **è passato QUI** il 14-09 (§8, riquadro): il brief lo aveva dichiarato e non scritto | è una colonna di `catalogo`, e serve a decidere **se** un articolo movimenta, non **come**. Il presidio che dice «qualcuno l'ha marcata» vive dove nasce chi la legge |

---

## 11. Riferimenti

* Doc auto-generata dello schema: [`docs/it/dbzero/magazzino/`](/dbzero/magazzino/)
* Convenzione della sorgente polimorfa: [sorgente-polimorfa.md](../../guide/sorgente-polimorfa.md)
* Stato del dominio nella mappa: [mappa-concentrica.md](../../mappa-concentrica.md) § Anello 3
* Dove le decisioni sono diventate codice:
  [Lotto 1](../work-done/brief-db-magazzino-lotto-1-terreno-vuoto.md),
  [Lotto 1-bis](../work-done/brief-db-emittente-di-default-un-bb-solo.md),
  [Lotto 2](../work-done/brief-db-magazzino-lotto-2-motore.md),
  [2-bis BE/FE](../work-done/brief-db-magazzino-lotto-2-bis-be-fe.md),
  [anagrafiche, guard ubicazioni e codici](../work-done/brief-db-magazzino-anagrafiche-guard-ubicazioni-e-codici.md),
  [verbi con permesso](../work-done/brief-db-magazzino-verbi-con-permesso.md),
  [piano BE/FE del Lotto 2](../work-done/piano-be-fe-magazzino-lotto-2-motore.md),
  e il [collaudo a video](collaudo-in-app-magazzino-inventario-e-rettifica.md)
* Il precedente dell'idempotenza per chiave ricalcolabile:
  `vendite.commesse_attivita.segment_key` e `uq_commesse_attivita_commessa_segment`

---

## 12. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-09-02 | **Nascita per consolidamento** (richiesta di Tid). Raccolte da tre analisi del 01-09 le parti su carico e scarico: la regola anti-doppio (§6, era §8-quater dell'analisi aggancio), l'ordine di costruzione (§8, era §8-ter), il vocabolario delle causali, il verso della quantità, chi scrive, la lettura. ⭐ Aggiunte in questa sede e **non presenti in nessuno dei tre**: la tabella completa delle dieci causali (§2), il fatto che `movimenti` non abbia **nessun** vincolo che leghi `qta` al segno della causale (§4), la valorizzazione dichiarata e non alimentata (§7), e l'elenco di ciò che manca ancora (§9) |
| 2026-09-02 | ⭐ **§7-bis, richiesta di Tid**: la giacenza deve mostrare **impegnata in uscita** e **merce in arrivo**, per articolo, con il dettaglio dei documenti. Verificando: `magazzino.reservations` **è già** la prenotazione in uscita — data prevista e riferimento al documento compresi — e **non la legge nessuno**; non sa però dire «in arrivo» (`qta > 0`, nessuna direzione) e porta lo **stesso difetto d'indice** della §6. Proposta la forma **derivata** (impegnato = riga impegnata senza il suo movimento), la separazione fra **impegnato** e **potenziale** (⛔ il preventivo non è una prenotazione: contraddirebbe la soglia dell'impegno già presidiata), e la data **unica** sul documento. ⇒ **M-3 non è più un buco generico**, ed è emerso che `acquisti.ordini_righe.data_consegna_confermata` passa da utile a **necessaria** |
| 2026-09-02 | ✅ **Decisione di Tid**: `magazzino.reservations` diventa **`magazzino.movimenti_attesi`**, generica sui due versi, gemella del ledger. ⭐ La direzione **non è una colonna nuova**: viene da `causale_id`, che porta con sé verso, valorizzazione e obblighi di lotto/seriale — così non nasce un quinto vocabolario parallelo. ⚠️ Ne discende che la **§4 è una decisione sola per due tabelle**. Da rifare insieme al nome: il ciclo degli stati (`picked` è di sola uscita), l'indice `docref`, il CHECK `qta > 0` e il ruolo di `data_prevista` |
| 2026-09-02 | ✅ **M-1 chiusa — decisione A: il verso sta nella quantità.** ⭐ Decisa su due argomenti, e nessuno dei due è «`vw_giacenza` è già scritta così»: (1) sotto B l'errore è del **lettore** ed è **silenzioso** — ed è già successo, `vw_giacenza` è quel lettore; (2) sotto B la giacenza dipende da una **riga modificabile di catalogo**, e cambiare `SCARICO_VEN.segno` riscriverebbe la storia all'indietro. Conseguenze applicate: cade `qta > 0` su `movimenti_attesi`, nasce la formula unica della giacenza prevista, serve un **trigger** (il CHECK non può guardare un'altra tabella), e `vw_giacenza` resta com'è ma con la ragione nel `COMMENT`. 📌 Residuo aperto: la causale con `segno = 0`, oggi inesprimibile sotto A |
| 2026-09-02 | ✅ **Residuo di M-1 chiuso**: lo `0` esce dal CHECK di `causali.segno`, che ammette solo `−1` e `+1`. Lo spostamento fra ubicazioni dentro lo stesso magazzino si modella come **coppia OUT/IN** con `transfer_uid` condiviso — la forma che il trasferimento fra magazzini usa già. ⭐ Sparisce un valore ammesso dal CHECK e inesprimibile nel modello: terza istanza della classe «esiste e non è armata» |
| 2026-09-02 | ✅ **M-2 chiusa — §5-bis.** Due livelli: una **primitiva** che scrive un movimento con tutti i controlli duri, e le **operazioni** che la compongono in transazione (il trasferimento scrive due movimenti, non uno). ⭐ La primitiva è **guidata dalle causali** — le colonne del catalogo *sono* l'elenco dei controlli — quindi la causale mancante del versamento di produzione costerà una riga di seed, non di codice. Blocco su `(magazzino, articolo)` **solo in uscita**, che elimina la classe degli stalli incrociati. ⭐⭐ **Osservazione di Tid che ha cambiato il disegno**: il controllo sulla merce impegnata va **prima**, alla conferma del documento — così la primitiva perde il flag di conferma, e il controllo duro resta ma diventa **muto nel caso normale**. Ne è uscita anche la distinzione fra i due momenti (conferma ordine = «posso prometterla», conferma DDT = «posso spedirla»), e il **terzo cantiere** che chiede `data_consegna_confermata`. 📌 Resta aperto il **terzo stato** delle capability (permessa ma con avviso), che è di quel pattern e non di qui |
| 2026-09-02 | 🔴 **Ramo chiuso invece che aperto, su osservazione di Tid.** L'avviso «merce impegnata» alla conferma del documento **non si fa** per l'impegno derivato: (1) l'impegnato contiene la riga che il documento stesso sta servendo — l'avviso avviserebbe l'operatore contro sé stesso; (2) non esiste nessuna **allocazione** né regola di priorità, quindi il messaggio non direbbe cosa fare. ⭐ **Ma si fa contro il blocco manuale**, che è l'atto di una persona e non un calcolo — ed è esattamente ciò che `movimenti_attesi` conserva. ⚠️ Emerso che al blocco manuale **manca la colonna del beneficiario**: senza «per chi», l'avviso non è scrivibile. ⭐⭐ Conseguenze: la primitiva resta invariata, il pattern delle **capability non si tocca** (per il derivato non c'è niente da esprimere), e nasce **M-9**, la regola di allocazione, come prerequisito dichiarato |
| 2026-09-02 | 🔴 **Seconda revisione della giornata, e rovescia la precedente.** Obiezione di Tid: *«fatto come dici tu il blocco mente — il programma di scarico non può bypassare il vincolo»*. ⛔ Aveva ragione: un blocco scavalcabile resta a riservare merce che non esiste più, e la disponibilità diventa falsa. ⇒ **Il blocco esplicito è un vincolo, non un avviso**: ferma lo scarico finché **una persona non lo libera** — esplicitamente, con atto, autore e momento (⛔ ritirato il «la conferma lo consuma», che mangiava in silenzio la decisione di un collega). ⭐ Lo stesso **controllo** parla alla conferma del documento e rifiuta allo scarico, ma come **funzione separata che non scrive** e non come flag sulla primitiva: con un flag chi può controllare può anche scrivere. ⚠️ Corretta M-2 di conseguenza. ⭐⭐ E il **terzo stato delle capability muore del tutto**: sull'esplicito l'azione è davvero bloccata, quindi il pattern binario di oggi la esprime già — nessun campo nuovo. ⚠️ Alla **conferma dell'ordine** però la giacenza insufficiente resta **informazione**, o non si potrebbe più vendere merce da acquistare |
| 2026-09-02 | ✅ **Chiuso il buco del «per chi»** (Tid): il blocco esplicito prende `billing_account_id` **nullable** + una `nota` **obbligatoria quando il BA manca**, con un `CHECK` sulla riga (⭐ non serve un trigger: guarda solo sé stessa) e la difesa dal vuoto con l'idioma `btrim(...) <> ''` già in uso. ⚠️ Dichiarata la conseguenza: il BA è una dimensione **di sola vendita** — 19 tabelle in `vendite`/`anagrafiche`, **zero in `acquisti`** — quindi su un blocco **in entrata** sarà sempre la nota a parlare |
| 2026-09-02 | ⭐ **Affinato il «per chi» in una scala a tre gradini** (Tid): `billing_account_id` → `soggetto_ruolo_id` → `nota`. ⭐⭐ Il fatto che la regge, verificato: `billing_account.soggetto_ruolo_id` è **NOT NULL**, quindi il primo gradino **contiene** il secondo. ⇒ I due sono **esclusivi**, non cumulativi: tenerli entrambi sarebbe conservare un derivato accanto alla sua fonte. ⭐ E il secondo gradino toglie la conseguenza dichiarata un'ora prima — un blocco **in entrata** ora nomina il **fornitore** invece di essere costretto alla nota |
| 2026-09-02 | 🔴 **Semplificata la decisione precedente, su rilievo di Tid**: non una scala `billing_account` → soggetto → nota, ma **`soggetto_ruolo_id` + nota** e basta. ⭐ L'argomento: *tutto ciò che il BA sa dire, il soggetto_ruolo lo sa dire — il contrario no* (da un BA si risale sempre al soggetto, da un soggetto non si risale a un BA, e un fornitore un BA non ce l'ha). ⇒ Sparisce anche il vincolo di esclusività, che serviva a impedire una duplicazione creata dalla colonna in più. ⭐ E la ragione di sostanza: il BA è una dimensione **contabile** messa a rispondere a una domanda **logistica** |
| 2026-09-02 | 🔴 **Coerenza rimessa a posto**: la tabella delle colonne diceva ancora che l'impegnata «toglie disponibilità», scritto **prima** che si decidesse che l'impegno derivato non ferma niente. ⇒ Corretto: sottrae **solo** il blocco esplicito; impegnata e potenziale si mostrano **accanto**, non dentro. ⭐ E aggiunto che **«disponibile» come numero unico va definito**: *«posso spedire adesso»* e *«posso prometterla»* danno due numeri diversi, e una casella sola che non dice quale mente a metà degli utenti |
| 2026-09-02 | ✅ **M-3 chiusa — §7-bis.** ⭐ La regola che decide: *il numero mostrato deve prevedere quello che il sistema farà* ⇒ **`disponibile = giacenza − blocchi espliciti`**, identica a ciò che la primitiva controlla, e l'impegno derivato **non si sottrae** (si mostra accanto). L'auto-conteggio si esclude con **la stessa regola** della primitiva — una regola in due posti, non due che divergono. ⭐ *«Posso prometterla?»* **non è un numero**: è una proiezione nel tempo, e schiacciarla in una casella butterebbe via la data, che è l'informazione utile. ⭐⭐ E il conteggio è **guidato da `config.sorgenti`** invece che da query per tipo di documento: così la produzione entra nel calcolo il giorno che si registra, invece di dipendere da chi si ricorda di aggiungerla — e il numero che smette di contare un pezzo lo fa **in silenzio** |
| 2026-09-02 | ✅ **M-4 chiusa — §7-ter**, e sono usciti **quattro difetti**, non la sola assenza dell'alimentatore. (1) Il **trasferimento a `none` era sbagliato**: con l'accumulatore per magazzino, spostare senza valore gonfia la media di A e diluisce quella di B ⇒ esce alla media di A ed entra in B con lo stesso valore. (2) `impatto_valorizzazione` **mescolava due domande** — *se* valorizzare (della causale) e *con che metodo* (dell'azienda) ⇒ **CMP** unico, `fifo` fuori dal vincolo perché nessuno lo usava e con un accumulatore **non è implementabile**. ⭐⭐ Ma scegliere CMP **non chiude FIFO**: il registro conserva costo e data di ogni entrata, quindi il metodo diventa una decisione di **lettura**. ⚠️ Scritta anche la distinzione fra il FIFO **contabile** e il FIFO **fisico** (la rotazione dello scaffale), che è di M-5 e non di qui. (3) La **quantità era in due posti** e `vw_giacenza_valorizzata` le mescolava ⇒ l'accumulatore tiene **solo il valore**, la quantità sta nel registro, e la tabella si rinomina **`valore_giacenza`** (il nome vecchio era falso: non contiene il costo medio, contiene ciò da cui si ricava). (4) Media **ricalcolabile** ⇒ la verità è il registro, l'accumulatore è una copia riparabile: risolve la **retrodatazione** e si presidia con una vista che deve restare vuota. ⚠️ Residui: manca la **FK su `articolo_id`**, e `costo_unitario` è un *input* in entrata e un *output* in uscita — va nel `COMMENT` |
| 2026-09-02 | ✅ **M-5 chiusa — §7-quater.** (1) Il **lotto diventa una tabella** con data d'arrivo e scadenza: oggi è testo libero senza catalogo — stessa forma del riferimento libero del §2 — e ⚠️ **senza data d'arrivo il FIFO fisico non è calcolabile**, cioè manca il dato, non il programma. Il FIFO al prelievo resta un **suggerimento**, non un vincolo. (2) Per i **seriali** convivevano due modelli (`movimenti.seriale` testo e l'entità `assets`, con una **posizione propria**: terza sede doppia del documento) ⇒ `asset_id` come FK, la posizione **si deriva dal registro** come il valore in §7-ter, e l'asset resta l'anagrafica del pezzo, non il suo GPS. (3) **Decide l'articolo**: `causali.richiede_lotto`/`richiede_seriale` si ritirano, ⚠️ e ne discende che **manca `catalogo.articoli.requires_lotto`**. (4) `abs(qta) = 1` con un seriale. (5) **Giacenza per ubicazione** in perimetro, con una vista fine accanto a `vw_giacenza` che resta alla sua grana — ⭐ senza, la coppia OUT/IN decisa in §4 non significherebbe niente. ⭐⭐ **Conseguenza della §4 non tracciata prima**: il modello a coppie rende ridondanti `magazzino_id_dest`, `ubicazione_id_from/_to`, `causali.richiede_magazzino_dest` e i due CHECK che li presuppongono |
| 2026-09-02 | ✅ **M-8 chiusa — §7-quinquies**: si corregge **aggiungendo**, non annullando. ⛔ Scoperto che `movimenti.attivo` **non fa niente**: `vw_giacenza` non lo filtra, quindi oggi «annullare» un movimento lascia la giacenza identica. ⭐ Idea di Tid accolta: una **utility che genera lo specchio** dalla riga originale — non è comodità, è ciò che impedisce a un costo o a un segno sbagliato di trasformare la correzione in un secondo errore. Storno al **costo originale** (o torna giusto in pezzi e resta storto in euro), `attivo` **si ritira**, ⭐⭐ e lo **storno doppio è impedito gratis** dall'identità di §6 |
| 2026-09-02 | ⭐ **M-6: decisa l'ancora — §7-sexies.** Osservazione di Tid: un magazzino può essere condiviso, e nemmeno l'articolo è legato all'emittente. ⇒ `emittente_fiscale_id` sta sul **magazzino**, e un capannone condiviso diventa **due magazzini logici** — ⭐ non un ripiego: la merce di due soggetti giuridici è merce diversa anche sullo stesso scaffale. ⭐⭐ Il perimetro **si eredita** via `magazzino_id`: niente colonna copiata sui movimenti. ⚠️ Ne discende che `magazzino_id`, oggi **nullable** su `movimenti_attesi` e `assets`, deve diventare obbligatorio — o quelle due tabelle sfuggono al perimetro in silenzio. ⛔ E **l'articolo non prende l'emittente**: è una definizione, non un possesso, e legarlo spaccherebbe catalogo, distinte, listini e UoM |
| 2026-09-02 | ✅ **M-6 chiusa — §7-sexies, parte policy.** Perimetro su **tutto ciò che porta merce o valore** (fuori i vocabolari e l'articolo); **solo `OPERATORE`** — ⚠️ perché aprire il magazzino a una controparte le mostrerebbe **il costo medio (cioè il margine)**, le quantità e **i blocchi degli altri clienti col loro nome**: non è una questione di emittente, è che il magazzino contiene informazione interna. ⭐ Ma il portale **non resta al buio**: *«disponibile per consegna immediata»* glielo dice una **vista dedicata** — la differenza fra rispondere a una domanda e aprire un archivio (decisione di Tid). ⚠️ Accensione vera, anche per il proprietario (il precedente di `acquisti`: due policy ferme da mesi), e viste che leggono coi diritti di chi interroga, ⛔ ricordando che quella marcatura **si azzera a ogni riscrittura**. ⭐⭐ E chiarito che **l'aggregato non è mai parziale**: l'ancora sul **magazzino** rende il perimetro tutto-o-niente, mentre con l'emittente sul movimento la somma sarebbe stata monca — la scelta di ieri risolve un problema che non stavamo guardando. ⚠️ Residuo: `vw_costo_medio_globale` è «globale» solo dentro il perimetro |
| 2026-09-02 | ✅ **M-9 chiusa — §7-septies, e chiusa *invece che rinviata***. Era il prerequisito dell'avviso sull'impegno derivato: avendo deciso di non farlo, **non ha più un consumatore** — ⭐ la precedenza non serve calcolarla, perché un blocco esplicito l'ha già decisa una persona. ⭐ Censito che cosa esiste (data ordine ✅, `commesse.priorita_operativa` ALTA/NORMALE/BASSA ⭐ ma sulla **commessa**, `categoria_cliente_id` sul **BA** e nata per i listini) e che cosa **manca**: una **priorità sul cliente**. ⚠️ Sulla proposta di Tid di un algoritmo per emittente: **forma giusta, momento sbagliato** — precedente `pratiche`, motore generico rimasto senza consumatori — e nella maggior parte dei casi reali la priorità **non è un algoritmo ma un elenco ordinato di criteri**, una riga di configurazione per criterio. ⛔ Chiusa e non lasciata aperta: una voce senza innesco resta anni e fa sembrare incompiuto un lavoro finito |
| 2026-09-04 | 🔴 **REVISIONE ESTERNA — 18 rilievi, tutti accolti.** Due **bloccanti**, nati fra sezioni scritte lo stesso giorno che non si erano guardate: (1) l'identità *(sorgente, chiave, verbo)* **non regge** 30 pezzi serializzati dalla stessa riga di DDT, né una riga servita da due lotti o prelevata da due ubicazioni ⇒ **il discriminante fisico entra nella chiave** (`asset_id`/`lotto_id`/`ubicazione_id`, colonne che §7-quater mette già lì), e resta dichiarato il caso scoperto (stesso prelievo in due riprese senza discriminante ⇒ servirebbe un progressivo); (2) `assets.magazzino_id` NOT NULL **contraddiceva** §7-quater («l'asset non è il suo GPS») e costringeva a mentire su `ASSET_INSTALL` ⇒ l'asset prende un **`emittente_fiscale_id` proprio**. **Sezioni rese stale**: la tabella «guidata dalle causali» era smentita per metà ⇒ riscritta come «guidata da **due** cataloghi»; `impatto_valorizzazione = none` **non ha più consumatori** dopo M-4 ⇒ da ridurre a booleano o togliere; la «formula unica» della giacenza prevista **ritirata**; la formula di `disponibile` riscritta **in colonne**, perché con le quantità firmate la sottrazione dava il segno rovesciato. **Puntuali**: ⛔ il `CHECK` del «per chi» **non teneva** (`FALSE OR NULL` = NULL, e un CHECK passa sul NULL — **provato**) ⇒ `coalesce`; `costo_unitario` ha **tre** significati (l'entrata di trasferimento prende il valore dall'uscita gemella); «ricalcolare» è **ri-sommare**, non ri-eseguire, o si contraddice M-8; l'aggregato non-parziale vale **solo alla grana del magazzino**, non per la vista **per articolo** che è quella principale; `lotti` **esce** dal perimetro RLS (è una definizione, e non ha l'ancora); lo storno doppio è impedito **solo dove la sorgente è valorizzata**; l'impegno derivato si calcola a **due salti**, via il ponte di evasione; **D-6 → D-7/D-1** (riferimento sbagliato, due volte); mancano **due causali in più** (carico da reso cliente, inventario iniziale); `abilita_billing` **verificato morto** (quarto flag); `vw_giacenza_valorizzata` è diventata **tautologica**; §9 riordinata |
| 2026-09-04 | ✅ **`impatto_valorizzazione` ritirata** (Tid): dopo M-4 tutte le causali valorizzano ⇒ una colonna con una risposta sola. ⚠️ Nominato il caso futuro della **merce di terzi**, con la ragione per cui nemmeno lì la colonna sarebbe la risposta: è una domanda di **proprietà**, non di valorizzazione. ⭐⭐ **E chiuso il residuo dell'aggregato parziale, ma NON come stavo per proporre**: verificato nel corpo di `fn_check_user_emittente_scope` che esiste un **emittente ATTIVO di sessione** che *«restringe chiunque, anche il super admin»* ⇒ ogni query vede **un emittente solo**, la giacenza per articolo è **completa** e raggruppare sarebbe inutile (una riga sola). ⚠️ Resta però la **prima** regola della stessa funzione — *utente NULL → vede tutto* — quindi un **ricalcolo eseguito come job attraversa gli emittenti**: finché scrive alla grana articolo × magazzino non mescola, ma va scritto, perché un aggregato «per articolo» dentro un batch romperebbe il confine in silenzio |
| 2026-09-04 | ⭐⭐ **Precisazione di Tid che vale oltre questo documento**: *«tutte le attività legate all'emittente obbligano alla scelta di un emittente — anche il super admin, e lo facciamo già in altre attività»*. ⇒ Il meccanismo del DB (la seconda regola di `fn_check_user_emittente_scope`) e la **prassi applicativa** dicono la stessa cosa, quindi **nessuna operazione di magazzino attraversa mai due emittenti** — né una lettura, né la primitiva, né lo storno. ⇒ E il caso del **job** si chiude allo stesso modo: un ricalcolo che serve più emittenti li **itera**, non li somma |
| 2026-09-14 | ✅ **Le decisioni presupposte sono prese** (Tid; verbale in [analisi aggancio §8-quater](analisi-db-magazzino-aggancio-documento-e-produzione.md)): D-1 catalogo, D-4 la terza forma senza progressivo, **D-6 sorgente `NOT NULL` sul ledger** — 🔴 rovescia il paragrafo «resta tutto nullable» di §6, barrato con la ragione: ogni scrittore è un'operazione con un record e la **correzione a mano è una rettifica**; il `UNIQUE` diventa pieno e `NULLS NOT DISTINCT`, il caveat dello storno doppio (§7-quinquies) cade, la riga «sorgente vuota» della tabella di §6 è ritirata — D-7 il catalogo registra le operazioni, D-8 ambito e tre flag ritirati. 🔴 **Corretta una falsa struttura in §6**: le cinque `*_RIGA` «già a catalogo» esistono **solo sul DB di sviluppo** (CSV a 10 righe, DB a 15) — verde su dev, rosso in CI. ⭐ Emerso scrivendo il brief: M-5 va **propagata alle righe delle testate**; lo storno ha bisogno di **causali sue** (`STORNO_POS`/`STORNO_NEG`, proposta); il perimetro RLS di M-6 atterra **nel Lotto 1 con l'ancora**, o il presidio del perimetro fa rosso; `FORCE` non è la postura del progetto. Aggiunto in §8 lo **spacchettamento in cinque lotti**; il primo è `brief-db-magazzino-lotto-1-terreno-vuoto.md` |
| 2026-09-15 | ✅ **Lotto 1 chiuso e mergiato** (PR #1593; brief con la fotografia in §12). Aggiunto in §8 il **Lotto 1-bis**, prerequisito del 2: l'emittente di default come BB unico con ritiro delle copie di vendite (decisione Tid, brief suo). ⚠️ Corretto un punto di §7-quater p.3 nel modo in cui era stato letto: `requires_lotto` **non eredita** il lock BoM di `requires_serial` — quello è un flag di **struttura** (congelato su un padre di distinta attiva, in `lock_columns_conditional`), questo no per decisione; e la frase «ricreare `vw_articoli_dettaglio` azzererebbe `security_invoker`» del Lotto 1 era falsa (la vista non ce l'ha e non deve averlo) |
| 2026-09-17 (sera) | 🔵 **Nato il brief del Lotto 2** ([brief-db-magazzino-lotto-2-motore](../work-done/brief-db-magazzino-lotto-2-motore.md)), con Lotto 1 e 1-bis chiusi. Scrivendolo sono usciti **tre fatti che questo documento non aveva**: (1) **l'inventario iniziale non ha un costo** — `inventari_righe` porta solo le quantità, quindi il primo carico in assoluto entrerebbe senza valore e la media resterebbe `NULL` fino al primo acquisto ⇒ `costo_unitario` sulle righe di inventario e rettifica (D-L2-c), e il costo di un movimento si decide dalla sua **struttura** (storno → originale, gemella → OUT, uscita → media, entrata → documento con ripiego sulla media), non da una colonna su `causali`; (2) **lo spostamento fra ubicazioni dello stesso magazzino non ha un documento** — §4 lo modella come coppia OUT/IN, ma `trasferimenti` vieta `from = to` e le sue righe non hanno ubicazione: sotto D-6 non si può scrivere. È una D nuova per Tid, e il posting del trasferimento esce dal Lotto 2 (D-L2-g); (3) **`causali.is_rettifica` trova il primo consumatore**: una rettifica registra un **fatto** sulla merce e non si ferma su un **blocco** (una promessa), che semmai diventa insoddisfacibile e si vede in `vw_disponibilita` — il fisico resta (D-L2-d). ⭐ E la porta di §5-bis prende la sua forma: DEFINER del proprietario + `REVOKE` nel loop dei grant, col perimetro rimesso **dal guard di scrittura BB** (`trgfn_guard_emittente_scope`, modo `magazzino`) e non da un controllo scritto a mano (D-L2-b). ⚠️ La «vista situazione merce» di M-3 si chiama `vw_disponibilita`: il nome era già preso da vendite per un'altra domanda (D-L2-j) |
| 2026-09-26 | 🟡 **Riallineamento allo stato di sviluppo** (verifica su doc auto-generata, CSV e brief chiusi). Intestazione riscritta (analisi completa, Lotti 1, 1-bis, 2, 2-bis e verbi costruiti); note di **fotografia del 02-09** su §0, §5, §7; aggiunta in §9 la tabella **«Realizzato»**, voce per voce con i changeSet; §8 aggiornata (passi 1-2 fatti, presidio di prontezza scritto, Lotto 2 consegnato, **D-L2-g presa** nel Lotto 3 con `magazzino_id` sul DDT, riga nuova per gli **eventi asset** D-L2-l). Corretti: D-L1-c e D-L1-d **confermate** (§6, §7-quinquies); «non serve niente di nuovo» per lo spostamento fra ubicazioni (serve il documento, Lotto 3); `assets` nella riga M-6; formula unica residua in §7-bis; righe M-5 e M-8 della tabella di §9 con il numero sbagliato di celle; riga del 14-09 del registro rimessa in ordine. ⚠️ Il commit `f2e724b47` (24-09) aveva corretto due link senza lasciare una riga qui |
| 2026-09-26 (sera) | 🔵 **Nato il brief del Lotto 3** ([brief-db-magazzino-lotto-3-scarico-da-ddt](../work-done/brief-db-magazzino-lotto-3-scarico-da-ddt.md)). Tid ha deciso: il magazzino sta sulla **testata** della bolla, il dettaglio fisico in una **tabella figlia dei prelievi**, e la bolla di trasferimento carica l'arrivo al **`CONSEGNATO`**. ⚠️ Emerso scrivendolo, e aggiunge un fatto a §6: l'identità del movimento **non contiene l'articolo**, quindi con sorgente = riga di bolla i componenti senza lotto di un kit collidono. Il brief propone come sorgente il **prelievo**, che è la condizione 1 di §6 presa alla lettera (D-L3-d) |
