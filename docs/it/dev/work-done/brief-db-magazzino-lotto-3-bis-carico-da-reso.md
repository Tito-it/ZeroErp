# Brief DB — magazzino, Lotto 3-bis: la merce rientra col reso

> **Destinatario:** team DB (`dev/db-tid`). 🔵 **Richieste a BE/FE in §6**, da
> fare nello stesso giro di PR.
>
> ✅ **Chiuso il 2026-10-14** (sessione BE, su richiesta di Tid): lato DB applicato e verde, richieste a
> BE/FE fatte (giri del [piano BE/FE](../work-in-progress/piano-be-fe-magazzino-lotto-3.md) §3). Quel che
> restava — collaudo a video, CI da zero, la corsa del pgTAP kit/seriali, i motivi della «Conferma» (R-1c, brief suo) — e' raccolto nel piano, §5, e il copione e'
> [collaudo-in-app-magazzino-bolla-e-reso](../work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md).
>
> **Origine.** [Brief del Lotto 3](brief-db-magazzino-lotto-3-scarico-da-ddt.md),
> D-L3-i (Tid, 28-09: *«B, fuori, in un 3-bis subito dopo»*), e la riga «3-bis» di
> [analisi carico e scarico §8](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md). La
> regola che lo mette **subito dopo**: *«un'asimmetria fra due versi si chiude
> subito»*. Prerequisiti **chiusi**: Lotto 3 applicato e verde (28-09).
>
> ⏩ **Lato BE/FE al 2026-10-13: R-1…R-5 fatti, da collaudare** — dettaglio e collaudo in
> [piano-be-fe-magazzino-lotto-3](../work-in-progress/piano-be-fe-magazzino-lotto-3.md) (giri A2, B2). R-1c (i motivi della
> «Conferma» senza i numeri) era un difetto DB, chiuso il 2026-10-14: [brief-db-reso-motivi-conferma-con-valori](brief-db-reso-motivi-conferma-con-valori.md).
>
> **Stato al 2026-09-29:** ✅ **LATO DB APPLICATO E VERDE.** I diciannove
> changeSet (`20260928-84 → -98`, `20260929-01 → -04`) sono `EXECUTED` su dbdev;
> la suite pgTAP col runner come app è senza regressioni (Tid). Otto decisioni
> di Tid, tutte prese. Cinque rossi del primo giro — quattro presidi
> trasversali (messaggi, stati mai scritti, mappa dello storico, codici-motivo)
> e l'elenco degli adottanti del BB — chiusi con i correttivi del 29-09 (§9).
> ⏳ **Resta, e non è del DB**:
> * le richieste a BE/FE (§6, R-1…R-5), nello stesso giro di PR: senza R-2 la
>   CI è rossa (`check_i18n_keys`, guardrail dei codici), senza R-4 il backend
>   riceve `E_PERMESSO_NEGATO` alla conferma;
> * la CI da zero (`ci_apply` + suite);
> * la corsa col runner di `magazzino/test-reso-carico-kit-seriali-v1` (kit per
>   componenti, seriale, ubicazione di rientro), scritto il 29-09: 14/14 sullo
>   scratch.
>
> **Perimetro:** il **carico** della merce che il cliente rende, il suo **storno**
> quando il reso si annulla, e il passaggio del reso al modello *«una scrittura =
> un verbo»*, che questo lotto tocca. ⛔ Fuori: la merce presso terzi, il reso a
> fornitore (Lotto 4), i prelievi proposti alla bolla di ri-consegna (§7).
>
> ⚠️ **Le decisioni già prese non si ridiscutono qui.** Ogni pezzo cita la
> decisione da cui discende: M-* di carico/scarico, D-L2-*, D-L3-*.

---

## 0. In due parole, senza tecnicismi

Col Lotto 3 la merce **esce** dal magazzino quando si emette la bolla. Quando il
cliente la **rende**, però, il magazzino non se ne accorge: il reso confermato
non la ricarica. Questo lotto chiude il giro.

Il reso deve imparare due cose:

* **in quale magazzino rientra la merce.** Di solito è quello da cui era partita,
  e sarà la proposta. Ma la merce resa può essere da controllare o rotta: chi la
  riceve può metterla in un magazzino a parte (per esempio «resi da verificare»).
  **Dove la metti dice in che stato è**: non serve un concetto nuovo;
* **che cosa rientra, esattamente.** Il reso non sceglie il lotto o il seriale:
  li **ritrova** da quello che era uscito con la bolla. Se è partito il lotto A,
  rientra il lotto A. Così la tracciabilità regge anche al richiamo di un lotto.

Alla **conferma** del reso la merce entra, al **costo al quale era uscita**. Se il
reso si annulla, la merce riesce con una riga opposta, come per la bolla.

⚠️ **Perché subito.** La bolla di **ri-consegna** di un reso (quella che rispedisce
la merce al cliente) eredita la causale dalla bolla d'origine, quindi col Lotto 3
**scarica di nuovo**. Oggi il registro vede la merce uscire due volte e rientrare
mai. Non è un buco che aspetta: è un errore che ogni ri-consegna produce.

---

## 1. Il filtro: che cosa entra qui

Entra ciò che soddisfa **tutte e tre** le condizioni:

1. è **deciso**, o è in §3 con una raccomandazione;
2. **muove merce attraverso il reso di vendita**, che esiste già
   (`vendite.resi`, `resi_righe`), o ne ripara l'effetto (lo storno);
3. **non chiede un documento nuovo** né uno stato nuovo del reso, se il modello
   non lo pretende (D-3b-c).

---

## 2. Le decisioni da cui discende ogni riga

| Decisione | Dove sta | Che cosa impone qui |
| --- | --- | --- |
| **M-1** il verso sta nella quantità | c/s §4 | il carico si scrive `+qta` |
| **M-2** primitiva + operazioni; la conferma parla | c/s §5-bis | il posting chiama `fn_scrivi_movimento` e non ricontrolla; i motivi li dice la check della conferma |
| **M-5** lotto e seriale per FK, mai testo | c/s §7-quater | il rientro porta lotto e seriale **per derivazione** dal prelievo d'origine (D-3b-b) |
| **M-6** nessuna operazione attraversa due emittenti | c/s §7-sexies | magazzino di rientro = emittente del reso (che è quello della bolla) |
| **M-8** si corregge aggiungendo | c/s §7-quinquies | l'annullo di un reso confermato **storna** con `fn_storna_movimenti_sorgente`, che esiste (Lotto 3, P-8) |
| **D-4 / §6** un record per tranche | aggancio §8-quater | la sorgente del carico è il **rientro**, non la riga di reso (D-3b-d) |
| **D-L2-c** il costo si decide dalla struttura | Lotto 2 §3 | un'entrata prende `p_costo_unitario` se passato: qui il costo **dell'uscita d'origine** (D-3b-e) |
| **D-L2-m** `usa_ubicazioni` sul magazzino | Lotto 2 §3 | l'ubicazione di rientro è obbligatoria o vietata secondo il magazzino di rientro |
| **D-L3-b / -d** prelievi in tabella figlia, sorgente = prelievo | Lotto 3 §3 | il rientro punta al prelievo d'origine: è **lui** il dettaglio fisico di ciò che era uscito |
| **D-L3-c** niente reso da bolla di trasferimento | Lotto 3 §3 | già in `trgfn_resi_guard_ddt_consegnato` |
| **D-L3-f** la regola del kit | Lotto 3 §3 | **non si riscrive**: rientra ciò che è uscito, e ciò che è uscito l'ha già deciso la regola del kit |
| **D-1 / D-2 permesso** una scrittura = un verbo; il processo chiede la sua azione | brief permesso §7 | conferma e annullo del reso diventano **verbi DEFINER** con `fn_guard_azione` (D-3b-f) |

---

## 3. Le decisioni del Lotto 3-bis

### ✅ D-3b-a — Il magazzino di rientro sta sulla TESTATA del reso — Tid, 2026-09-28: raccomandazione accolta

`vendite.resi` prende `magazzino_id` (FK a `magazzino.magazzini`, nullable).

**La ragione sul modello**: è la stessa di D-L3-a, rovesciata. Un reso è un
arrivo, e un arrivo va in un posto. Il reso ha **un** emittente sulla testata
(lo eredita dalla bolla, `trgfn_resi_normalize`): magazzino ed emittente stanno
allo stesso livello.

**Raccomandazione**, sullo stampo di D-L3-a:

* **default = il magazzino della bolla d'origine**, all'`INSERT`, sovrascrivibile
  in `DRAFT`. ⚠️ Non il predefinito dell'emittente (D-L3-h): la domanda del reso
  è *«da dove era partita?»*, e la risposta sta sulla bolla;
* nullable in `DRAFT`, **obbligatorio alla conferma** quando il reso muove merce
  (D-3b-b): un motivo della check, non un `NOT NULL`;
* **dell'emittente del reso** e **immutabile fuori da `DRAFT`** (stato vecchio).

⭐ **Regola del 2, dichiarata.** Le due regole «magazzino dell'emittente del
documento» e «immutabile fuori bozza» esistono già, scritte sul posto, in
`vendite.trgfn_ddt_guard_magazzino` (passi 1 e 3). Il reso è la **seconda
occorrenza**: si estrae un BB (per esempio `script.fn_check_magazzino_documento(
p_magazzino_ids, p_emittente_id)` per il passo 3) e il guard della bolla lo
chiama **nello stesso giro**. L'immutabilità, che legge uno stato vecchio di un
vocabolario diverso, resta scritta sul posto se l'estrazione costa più di quello
che toglie: lo si decide leggendo i due corpi, e lo si scrive qui.

### ✅ D-3b-b — Che cosa rientra: il RIENTRO punta al prelievo d'origine — Tid, 2026-09-28: raccomandazione accolta

Nuova tabella `vendite.resi_righe_rientri`: *«di questa riga di reso, questa
quantità, di quel prelievo della bolla, in questa ubicazione»*.

| Colonna | Note |
| --- | --- |
| `id` | chiave |
| `resi_riga_id` | FK `NOT NULL` alla riga del reso |
| `ddt_riga_prelievo_id` | FK `NOT NULL` a `vendite.ddt_righe_prelievi`: **che cosa** era uscito |
| `qta` | UoM base, `> 0` |
| `ubicazione_id` | ubicazione di **rientro**, obbligatoria o vietata secondo `usa_ubicazioni` del magazzino del reso (D-L2-m) |

**Articolo, lotto, seriale, componente del kit non si copiano**: si leggono dal
prelievo d'origine, che fuori bozza è immutabile (`trgfn_ddt_righe_prelievi_guard`
ammette solo `ubicazione_arrivo_id`, che qui non conta). Il derivato è completo:
una copia sarebbe una seconda sede che può divergere.

**Perché puntare al prelievo e non scegliere di nuovo il lotto**:

* la merce che rientra **è** quella che era uscita: il lotto non è una scelta,
  è un fatto già registrato. Scegliere di nuovo permetterebbe di rendere il lotto
  B di una bolla che ha spedito il lotto A;
* il **kit** si risolve da sé: se erano usciti i componenti, i prelievi sono dei
  componenti; se era uscito il padre, il prelievo è del padre. D-L3-f non si
  riscrive (regola del 2 rispettata per costruzione);
* un reso da una bolla che **non ha mosso merce** (causale senza causale di
  magazzino, articoli non gestiti) non ha prelievi a cui puntare, quindi **non
  carica**. Il simmetrico esatto dello scarico, senza una seconda regola.

**Ne discende**:

* **stessa riga d'origine**: il prelievo appartiene a `resi_righe.ddt_riga_id`
  (guard);
* **tetto per prelievo**: la somma dei rientri dei resi **non annullati** sullo
  stesso prelievo non supera la `qta` del prelievo. È un tetto su **una** unità
  (UoM base), quindi può stare in un controllo; lo si fa alla conferma, sotto il
  lock della bolla d'origine (D-3b-f), perché due resi confermati insieme sono
  due transazioni. Con un seriale il tetto è 1, e il `qta = 1` segue da sé;
* **quadratura**:
  * riga il cui articolo era uscito **lui** (prelievi senza componente): somma dei
    rientri = `resi_righe.quantita` (base) — motivo della conferma;
  * riga di kit uscita **per componenti**: ⏸️ vedi D-3b-g;
* satellite del reso: RLS sulla famiglia dei satelliti del reso
  (`fn_scope_ef_whitelist_via_reso_riga`), scrivibile **solo in `DRAFT`**
  (`trgfn_doc_righe_lock_fuori_bozza`, come le righe).

⭐ **Regola del 2 sui prelievi, dichiarata.** Il Lotto 3 aveva scritto *«alla
seconda occorrenza si decide se estrarre un satellite generico»*. Questa **non** è
la seconda occorrenza: il rientro non **sceglie** una posizione fisica, **ritrova**
quella di un altro documento. Ha un'altra domanda e un'altra forma. La seconda
occorrenza vera è la ricezione acquisti (Lotto 4), dove il lotto si **crea**:
lì si decide.

**Il rientro automatico**, sullo stampo del prelievo automatico del Lotto 3: se
la voce d'origine ha **un solo** prelievo e il magazzino di rientro **non** usa
ubicazioni, non c'è niente da scegliere, e la conferma crea da sé il rientro.
L'operatore scrive rientri solo dove c'è una scelta (più lotti, più seriali,
ubicazioni).

### ✅ D-3b-c — Quando rientra: alla CONFERMA del reso — Tid, 2026-09-28: raccomandazione accolta

La brief del Lotto 3 lo aveva lasciato aperto: *«l'unico evento è la conferma,
che è un atto amministrativo»*.

| | Forma | Conseguenza |
| --- | --- | --- |
| **A** ⭐ | la **conferma** è la presa in carico: il carico avviene lì, alla data del reso | nessuno stato nuovo; il reso è il documento di rientro, come la bolla è quello di uscita. Il costo: non si conferma un reso prima che la merce sia arrivata |
| **B** | uno stato nuovo `RICEVUTO` (o un atto «ricevi») distinto dalla conferma | separa l'autorizzazione al reso dall'arrivo della merce. Il costo: uno stato nuovo in matrice, e la domanda di che cosa si può fare fra conferma e ricezione (accredito? ri-consegna?) |

**Raccomandazione: A.** Nel modello di oggi la conferma **abilita** l'accredito
e la ri-consegna: entrambe presumono la merce già tornata (la ri-consegna la
**rispedisce**). Un reso confermato senza merce in casa è già oggi una
contraddizione, non un caso del 3-bis. Se un giorno serve un'**autorizzazione al
reso** prima dell'arrivo (un RMA), è uno stato **prima** della conferma, e il
carico resta dov'è.

⚠️ **La data del movimento** è `resi.data` (come la bolla usa `ddt.data`).

### ✅ D-3b-d — La sorgente del carico è il RIENTRO — Tid, 2026-09-28: raccomandazione accolta

Nuova riga di catalogo `RESO_VENDITA_RIENTRO` → `vendite.resi_righe_rientri`,
`key_selector = 'id'`, scope `MAGAZZINO`. È D-L3-d applicata al verso opposto:
due rientri della stessa riga di reso (due lotti) sono **due** movimenti. Con
sorgente la riga, i componenti senza lotto di un kit avrebbero la stessa
identità e il secondo carico sarebbe rifiutato come doppio.

**Ne discende la nota di coerenza di D-L3-i**: `RESO_VENDITA_RIGA` **resta**
`ROW_VALIDATOR` e non si rinomina. Resta la sorgente di ciò che è commerciale,
come `DDT_VENDITA_RIGA` accanto a `DDT_VENDITA_PRELIEVO`.

La causale è **`CARICO_RESO_VEN`** (esiste dal Lotto 1, segno +1): nessun
vocabolario nuovo.

### ✅ D-3b-e — Il costo: quello dell'uscita d'origine — Tid, 2026-09-28: raccomandazione accolta

Una semplice entrata, per la primitiva, prende `COALESCE(p_costo_unitario, media)`
(passo 12). Senza costo, la merce resa rientrerebbe **alla media di oggi**, cioè a
un valore che non ha niente a che fare con lei.

**Raccomandazione**: il posting passa `p_costo_unitario` = costo del movimento
di **uscita** del prelievo d'origine (sorgente `DDT_VENDITA_PRELIEVO`, chiave il
prelievo, non stornato). La merce rientra al valore al quale era uscita:
simmetria esatta, e la media non si sposta per un andata-e-ritorno. Se l'uscita
era senza costo (`NULL`, giacenza senza valore), si passa `NULL` e vale la media:
è la regola della primitiva, non una scelta nuova.

⛔ **Nessuna modifica alla primitiva**: il ramo «entrata con costo passato» c'è
già, ed è quello giusto. Il costo lo **cerca l'operazione**, perché è lei a sapere
da dove viene la merce.

### ✅ D-3b-f — Conferma e annullo del reso diventano VERBI, con la loro azione — Tid, 2026-09-28: raccomandazione accolta

**Il fatto (struttura)**: `vendite.fn_conferma_reso` e `vendite.fn_annulla_reso`
sono **INVOKER** e senza guard di permesso; il backend le chiama già, non
scrive lo stato del reso con un `UPDATE` (`resi_repository.py`). Il posting di
magazzino è riservato (Lotto 3, P-12): una funzione INVOKER non lo può chiamare.

**Raccomandazione**, sullo stampo di `fn_cambia_stato_ddt`:

* le due madri diventano **DEFINER** del proprietario, `search_path` bloccato,
  testata `FOR UPDATE` con il **predicato della policy** nella `WHERE`
  (`script.fn_scope_ef_whitelist_via_reso`); fuori perimetro `E_RESO_NOT_FOUND`;
* nella prima riga `script.fn_guard_azione(v_utente, 'conferma_reso')`: **un'azione
  nuova**, che copre conferma e annullo (sono i due passaggi che muovono merce),
  come `emetti_ddt` per la bolla. Non si riusa `emetti_ddt`: chi emette bolle non
  è per forza chi accetta la merce indietro;
* **la porta**: il guard di transizione del reso rifiuta `DRAFT → CONFERMATO` e
  `CONFERMATO → ANNULLATO` senza la GUC transazionale **quando il reso muove
  merce** — lo stesso perimetro affinato di D-L3-e (Regola 3 di
  `trgfn_ddt_guard_transizione`). ⛔ Non un `REVOKE` per colonna (linee-guida-sql
  §11.8);
* il **lock**: la conferma prende `FOR UPDATE` anche la **bolla d'origine**,
  perché il tetto per prelievo (D-3b-b) legge i rientri di tutti i suoi resi.

⚠️ **Da decidere con questa D: il permesso vale sempre, o solo sui resi che
muovono merce?** Raccomandazione: **sempre**, come `emetti_ddt` vale su ogni
emissione. La conferma di un reso è un atto di processo anche quando non carica
niente (apre il credito, riapre il residuo dell'ordine). Il costo: i pgTAP che
chiamano le due madri (sono 22 file, letti il 28-09) devono dare all'utente di
prova l'azione. È un costo di preparazione, non una ragione: si censiscono prima
di scrivere (§5-bis).

### ✅ D-3b-g — Il kit uscito per componenti: quanto rientra di ciascuno — Tid, 2026-09-28: raccomandazione accolta

Se la bolla ha fatto uscire i **componenti** (padre non gestito, D-L3-f), il reso
parla del **padre** (`resi_righe.quantita` del kit), e i rientri dei
componenti.

| | Forma | Conseguenza |
| --- | --- | --- |
| **A** ⭐ | **proporzionale di default, libero sotto il tetto**: il rientro automatico propone per ogni componente `quantita_componente × qta_resa / quantita_riga`; l'operatore può scendere (il kit torna incompleto). Nessuna quadratura imposta sui componenti, solo il tetto per prelievo | il registro dice il vero anche quando il cliente rende un kit senza un pezzo |
| **B** | quadratura imposta: ogni componente deve rientrare in proporzione esatta | semplice da controllare, ma **falso** quando il kit torna incompleto: obbliga a caricare un pezzo che non c'è |

**Raccomandazione: A.** Il registro scrive ciò che è **fisicamente** rientrato.
Se la proporzione non è intera (tre pezzi per kit, un kit reso su due), il
rientro automatico **non** si crea e la conferma chiede la scelta con un motivo:
non si arrotonda un pezzo.

### ✅ D-3b-h — Le righe di un reso confermato si possono ancora cambiare? — emersa scrivendo il 28-09; Tid, 2026-09-29: A

**Il fatto (struttura)**: `vendite.resi_righe` non ha un guard «solo in bozza».
Non monta `trgfn_doc_righe_lock_fuori_bozza`; `trgfn_resi_righe_guard_quantita`
guarda solo il tetto sul consegnato. Quindi dopo la conferma una riga si può
ancora disattivare, cambiare di quantità o cancellare. Un pgTAP lo fa di
proposito (`vendite/test-vw-resi-righe-effettive-v1`, test 9: «riga di reso
CONFERMATO ma disattivata»), per provare il filtro `attivo` della vista.

**Perché col 3-bis diventa una domanda**: i rientri sono congelati alla
conferma, e il carico è scritto. Se dopo la conferma la riga cambia quantità o
si spegne, il registro e il reso non dicono più la stessa cosa. L'annullo
storna comunque tutti i carichi (legge i rientri, non le righe), quindi il
registro non si rompe, ma resta una riga che dice 4 su un carico di 5.

| | Forma | Conseguenza |
| --- | --- | --- |
| **A** ⭐ | le righe del reso **solo in bozza**: il BB `trgfn_doc_righe_lock_fuori_bozza` montato su `resi_righe` (tipo `RESO`, colonna `reso_id`; il lettore lo conosce già, `20260928-86`) | un reso confermato è un fatto, come una bolla emessa: la correzione passa dall'annullo e da un reso nuovo. Il test 9 della vista va riscritto: il caso «confermato e disattivato» non esiste più |
| **B** | lasciare com'è | la vista continua a filtrare `attivo`, e il registro può divergere dal reso in silenzio |

**Raccomandazione: A** (✅ accolta). È la regola che vale già per bolle e
contratti. Verificato (struttura): il backend la applicava già da sé —
`resi_service`: *«righe editabili solo con testata DRAFT: enforcement BE»* — e
nessuna funzione DB scrive `resi_righe` dopo la conferma. Scritto in
`20260929-01`.

---

## 4. Il lavoro, pezzo per pezzo

> ⚠️ I numeri di changeSet si leggono **al momento di creare il file**: Tid
> applica mentre si scrive. Al 28-09 l'ultimo è `20260928-83`.

| # | Cartella | Che cosa | Discende da |
| --- | --- | --- | --- |
| **P-1** | `00_schema/vendite` | `resi.magazzino_id` (FK, nullable) + riga in `dbops.fk_index_policy` | D-3b-a |
| **P-2** | `00_schema/vendite` | `vendite.resi_righe_rientri` (colonne di D-3b-b, `CHECK qta > 0`, `UNIQUE (resi_riga_id, ddt_riga_prelievo_id, ubicazione_id) NULLS NOT DISTINCT`), policy della famiglia dei satelliti del reso, RLS accesa | D-3b-b |
| **P-3** | `20_code/script` | il BB estratto dal passo 3 di `trgfn_ddt_guard_magazzino` (magazzino dell'emittente del documento), e il guard della bolla che lo chiama — **stesso giro**. ✍️ *Scritto: `script.fn_magazzino_dell_emittente`, INVOKER (sotto RLS un magazzino fuori perimetro risponde come uno inesistente). L'immutabilità fuori bozza resta scritta nei due guard: legge due vocabolari diversi e solleva due codici, il pezzo comune è una riga* | D-3b-a, regola del 2 |
| **P-4** | `20_code/vendite` | `trgfn_resi_default_magazzino` (dalla bolla d'origine, all'`INSERT`) e `trgfn_resi_guard_magazzino` (emittente via BB, immutabile fuori `DRAFT`); `trgfn_resi_righe_rientri_guard` (solo in `DRAFT`, prelievo della stessa riga d'origine) | D-3b-a, -b |
| **P-5** | `20_code/vendite` | `fn_reso_merce_da_rientrare(p_reso vendite.resi)`: le voci d'origine di ogni riga (i prelievi della sua riga di bolla), la quantità attesa (D-3b-g), quella già coperta, e `automatico`. Sede unica, come `fn_ddt_merce_da_movimentare`; e `fn_reso_muove_merce(p_reso)` | D-3b-b, -g |
| **P-6** | `20_code/script` | `script.fn_check_reso_merce(p_reso)`: magazzino mancante, rientri incompleti (riga intera), proporzione non intera (kit), tetto per prelievo superato, e per ogni rientro `fn_check_riga_magazzino` (ubicazione) — con i `valori` della frase. La accoda la capability della conferma (`fn_available_actions_reso`) | M-2, D-3b-b |
| **P-7** | `20_code/magazzino` | `fn_posta_reso(p_reso_id)` — **riservata**: un `fn_scrivi_movimento` per rientro, `CARICO_RESO_VEN`, `+qta`, sorgente `RESO_VENDITA_RIENTRO`, lotto/seriale/articolo dal prelievo d'origine, costo dell'uscita d'origine (D-3b-e), data `resi.data` | D-3b-c, -d, -e |
| **P-8** | `20_code/vendite` | `fn_conferma_reso` e `fn_annulla_reso` **verbi** (DEFINER, `fn_guard_azione 'conferma_reso'`, perimetro, GUC-porta); la conferma, su un reso che muove merce: primo motivo della check, rientri automatici, lock della bolla d'origine, posting; l'annullo di un reso confermato: `fn_storna_movimenti_sorgente(RESO_VENDITA_RIENTRO, …)`. **Il corpo dalla doc auto-gen** (i rami accredito e ri-consegna restano identici) | D-3b-f, M-8 |
| **P-9** | `20_code/vendite` | `trgfn_resi_guard_transizione` impara la porta (solo i due passaggi, solo se il reso muove merce) | D-3b-f |
| **P-10** | `80_data` | `config/sorgenti.csv`: `RESO_VENDITA_RIENTRO`; `config/azioni_processo.csv`: `conferma_reso`; codici e messaggi (P-12) — **dal CSV** (§11.2) | D-3b-d, -f |
| **P-11** | `90_end` | la postura nelle tre sedi (loop `ci_apply/20260205-41`, forward, `provision_db_roles.sql`): `fn_posta_reso` in `v_fn_riservate`; `EXECUTE` all'app sulle due madri **resta** (sono il verbo) | permesso D-4 |
| **P-12** | codici | `E_RESO_MAGAZZINO_OBBLIGATORIO`, `E_RESO_MAGAZZINO_INCOERENTE`, `E_RESO_MAGAZZINO_IMMUTABILE`, `E_RESO_RIENTRI_INCOMPLETI`, `E_RESO_RIENTRO_INCOERENTE`, `E_RESO_RIENTRO_OLTRE_USCITO`, `E_RESO_STATO_SOLO_DA_VERBO` (TECNICO); `reason_key` `vendite.reso.azione_reason.{magazzino_mancante, rientri_incompleti, rientro_oltre_uscito, merce_non_ricollocabile}` — ⚠️ i nomi si confermano scrivendo, contro il registro dei codici | — |
| **P-13** | `20_code/dbops` + `presidi.csv` | presidio **reso confermato senza carico**. ⭐ Regola del 2: è la seconda occorrenza di `dbops.vw_ddt_emessi_senza_scarico` (*«un documento ha passato lo stato che muove merce, e le sue sorgenti non hanno il movimento»*). Si scrive **una** vista `dbops.vw_documenti_senza_movimento` — i rami elencano soltanto i record-sorgente attesi (documento, sorgente, chiave), il confronto col registro è **uno** — e quella della bolla si ritira nello stesso giro (riga di `presidi.csv` e pgTAP che la nominano). ✍️ *Scritto diversamente, leggendo i due corpi: **due viste**, `dbops.vw_resi_confermati_senza_carico` accanto a quella della bolla. In comune hanno solo il confronto col registro per sorgente; la domanda (quale documento, quale stato, quali sorgenti, quale verso) è di ciascun documento, come un guard lo è della sua tabella. E ritirare la vista della bolla costerebbe una `DELETE` su `dbops.presidi` fuori dal CSV (il mirror fa upsert sul nome, e il catalogo pretende che ogni vista iscritta esista)* | D-6, regola del 2 |
| **P-14** | `db/pgtap` | §5 | M-7 |

---

## 4-bis. ✅ Scritto il 2026-09-28 — che cosa c'è, file per file

> Forme precisate scrivendo, dentro le D già prese: (1) il **rientro
> automatico** vale solo se la riga di reso non ha ancora rientri — chi ne
> scrive uno si prende la riga intera, ed è così che si dice un kit reso senza
> un pezzo; (2) la conferma solleva il primo motivo **prima** di creare gli
> automatici, e la check li conta come già scritti, così capability e verbo
> dicono la stessa cosa; (3) le due madri restano `RETURNS void`: cambiano
> solo `SECURITY DEFINER` e `search_path`, senza `DROP`; (4) firme, `RETURNS
> TABLE` e `DECLARE` ancorati con `%TYPE`, i tipi nudi con il loro perché.

| ChangeSet | Che cosa |
| --- | --- |
| `00_schema/vendite/20260928-84` | `resi.magazzino_id` |
| `00_schema/vendite/20260928-85` | `vendite.resi_righe_rientri` + policy + RLS accesa |
| `20_code/script/20260928-86` | `fn_get_stato_testata_documento` impara `RESO` |
| `20_code/script/20260928-87` | BB `fn_magazzino_dell_emittente`, e il guard della bolla che lo chiama |
| `20_code/vendite/20260928-88` | `fn_reso_merce_da_rientrare`, `fn_reso_muove_merce` |
| `20_code/vendite/20260928-89` | `trgfn_resi_default_magazzino` + `trgfn_resi_guard_magazzino` (fascia z10) |
| `20_code/vendite/20260928-90` | `trgfn_resi_righe_rientri_guard` (solo in bozza, prelievo della riga d'origine) |
| `20_code/script/20260928-91` | `fn_check_reso_merce` (quattro motivi, con `valori`) |
| `20_code/script/20260928-92` | `fn_available_actions_reso`: «Conferma» spenta col motivo fisico |
| `20_code/vendite/20260928-93` | `trgfn_resi_guard_transizione`: Regola 2, la porta del registro |
| `20_code/magazzino/20260928-94` | `fn_posta_reso` (riservata) |
| `20_code/vendite/20260928-95` | **verbo** `fn_conferma_reso` |
| `20_code/vendite/20260928-96` | **verbo** `fn_annulla_reso` (storno) |
| `20_code/dbops/20260928-97` | presidio `dbops.vw_resi_confermati_senza_carico` |
| `90_end/20260928-98` | la postura, forward su dev |
| `20_code/vendite/20260929-01` | D-3b-h: il BB `trgfn_doc_righe_lock_fuori_bozza('RESO', 'reso_id')` su `resi_righe`, e il suo COMMENT con il quarto adottante |
| `20_code/script/20260929-02` | correttivo: valori vuoti del motivo 1 di `fn_check_reso_merce` come `jsonb_build_array()` |
| `80_data/changelog/20260929-03` | presidio C1: via le esenzioni `CHIUSA` / `POSTED` pagate dal Lotto 3 |
| `20_code/script/20260929-04` | correttivo: il motivo 4 di `fn_check_reso_merce` con la guardia `IF FOUND` accanto |

**E fuori dai changeSet:**
- `80_data`: `config/sorgenti.csv` (id 22 `RESO_VENDITA_RIENTRO`);
  `config/azioni_processo.csv` (39 `conferma_reso`); `codici_errore.csv` e
  `messaggi_errore.csv` (sette codici, messaggi `it` 1154-1160);
  `dbops/presidi.csv`; `dbops/fk_index_policy.csv` (quattro FK, `consentito = false`).
- Postura: loop `90_end/ci_apply/20260205-41` (`fn_posta_reso` in
  `v_fn_riservate`) e `scripts/sql/provision_db_roles.sql`.
- pgTAP **nuovi**: `magazzino/test-reso-carico-v1` (25: il 25 è D-3b-h);
  `magazzino/test-reso-carico-kit-seriali-v1` (14, 29-09: kit, seriale, ubicazione).
- pgTAP **aggiornati**: `script/test-rubinetto-primo-motivo-v1` (da 29 a 30:
  `fn_conferma_reso`); 21 file di `vendite/` che confermano o annullano un
  reso concedono `conferma_reso` all'utente in sessione (nessuno committa,
  nessun `plan` cambiato); in `vendite/test-vw-resi-righe-effettive-v1` il
  test 9 spegne la riga **in bozza** e poi conferma (il caso «spenta dopo la
  conferma» non esiste più, D-3b-h), e due commenti «le madri sono SECURITY
  INVOKER» sono corretti.

## 4-ter. ✅ La prova pre-apply — 2026-09-28, su `zeroerp_ci`, transazione annullata

> Da `zeroerp`, proprietario dello scratch (allineato al Lotto 3). L'SQL è
> **estratto** dagli YAML, mai riscritto; i seed sono simulati inserendo le
> righe nuove dei CSV. Niente applicato: ogni corsa chiude in `ROLLBACK`.

| Che cosa | Esito |
| --- | --- |
| i 15 changeSet, in ordine di NN, in una transazione | ✅ compilano |
| `plpgsql_check` sulle 14 funzioni nuove o cambiate | ✅ zero errori; un avviso «STABLE con PERFORM volatile» **già esistente** nel lettore di stato |
| una sola firma per funzione dopo l'ancoraggio `%TYPE` | ✅ |
| `magazzino/test-reso-carico-v1` | ✅ 25/25 (al primo giro 23 su 24: la frase attesa del test 8 era sbagliata, non il verbo) |
| `vendite/test-vw-resi-righe-effettive-v1`, test 9 riscritto | ⚠️ **non provato sullo scratch**: il file si ferma prima sulla fixture (utente 1), come prima della modifica. Lo prova il runner su dbdev |
| `script/test-catalogo-messaggi-errore-completo` | 🔴 non provato prima dell'apply: rosso al runner (test 7), corretto in `20260929-02` e riprovato 7/7 |
| presidi e Lotto 3: scarico 16, trasferimento 13, testata della bolla 9 (passa dal BB estratto), rubinetto 7, catalogo presidi 11, sorgenti orfane 6, seed causali e sorgenti 11, riferimenti morti 9 | ✅ tutti verdi |
| i 21 pgTAP dei resi aggiornati, confrontati con la loro versione in `HEAD` | ✅ **identici prima e dopo**. ⚠️ Ma sullo scratch 17 si fermano prima del reso, sui debiti noti della fixture (utente 1 inesistente, nessun cliente adatto) o sulle asserzioni di scope, rosse da owner per costruzione: **la loro prova vera è il runner su dbdev** |
| porta del ledger 14/18, blocco del Lotto 3 13/14 | ⚠️ rossi **solo** i 42501 attesi (privilegio, da owner non c'è): identici prima e dopo |

**Che cosa la prova NON copre**: la corsa come app con la RLS; il database da
zero (CI); il mirror dei CSV risvegliato davvero dall'apply;
`check_i18n_keys` e il guardrail dei codici del backend (R-2).
✅ **I tre casi di §5 che il primo file non fabbricava** — il **kit** uscito per
componenti (proporzione, componente oltre la sua parte, kit reso incompleto),
il **seriale** che rientra con il suo asset e il suo costo, l'**ubicazione** di
rientro in un magazzino che le usa — sono in
`magazzino/test-reso-carico-kit-seriali-v1` (29-09, 14/14 sullo scratch, da
owner: la corsa come app resta al runner). ⚠️ Resta **dichiarato e non provato**
un solo ramo: la proporzione con RESTO. Le quantità dei componenti le calcola il
trigger del kit (coefficiente × quantità della riga), e con coefficienti interi
la proporzione è sempre esatta: il caso non si costruisce senza forzare un dato
che il modello non produce.

## 5-bis. Il censimento da fare PRIMA di scrivere

> Lettura di **struttura** (chi nomina che cosa), da rifare al momento del
> changeSet: i file cambiano.

| Che cosa cambia | Chi lo nomina | Effetto atteso |
| --- | --- | --- |
| `fn_conferma_reso` / `fn_annulla_reso` chiedono `conferma_reso` | 22 pgTAP in `db/pgtap/vendite/` (letto il 28-09) | l'utente di prova deve avere l'azione, o il test prova il rifiuto: si rilegge il preambolo di ciascuno |
| le due madri diventano DEFINER con perimetro | gli stessi, più i test RLS dei resi | fuori perimetro la risposta diventa `E_RESO_NOT_FOUND` |
| i motivi nuovi nella capability del reso | i pgTAP di `fn_available_actions_reso` | scattano solo sui resi che muovono merce: chi confronta **tutti** i motivi per uguaglianza va riletto |
| `vw_ddt_emessi_senza_scarico` si ritira (P-13) | `presidi.csv`, i pgTAP che la nominano, la pagina `manual/` se c'è | si rinominano sul presidio nuovo; ⛔ il `manual/` di un oggetto ritirato si cancella |
| catalogo delle sorgenti (riga nuova) | `magazzino/test-causali-e-sorgenti-seed-v1`, `dbops/test-sorgenti-orfane-v1` | se contano le righe, la conta sale di uno |
| guard della bolla che chiama il BB estratto (P-3) | i pgTAP del Lotto 3 sulla testata | stessi codici e stessa frase: nessun effetto atteso, da confermare |

## 5. I pgTAP — i casi si fabbricano, non si cercano

⛔ Regola zero: ogni ramo si prova **costruendo** il caso.

* **carico**: bolla con due prelievi da due lotti, reso di tutta la riga ⇒ due
  movimenti `CARICO_RESO_VEN`, lotti giusti, costo = costo delle uscite; reso
  parziale sul lotto A ⇒ un movimento; articolo non gestito ⇒ nessun movimento;
  reso da bolla di causale che non muove merce ⇒ nessun movimento;
* **kit**: padre gestito ⇒ rientra il padre; per componenti ⇒ un movimento per
  componente, **senza collisione di identità**; kit reso incompleto ⇒ ammesso;
  proporzione non intera ⇒ motivo;
* **tetto**: due resi sullo stesso prelievo oltre la sua `qta` ⇒ il secondo
  rifiutato alla conferma; un reso annullato libera il tetto;
* **seriale**: un seriale uscito rientra; un secondo reso dello stesso ⇒ rifiuto;
* **magazzino**: default dalla bolla; altro emittente ⇒ rifiuto; cambiato fuori
  `DRAFT` ⇒ rifiuto; ubicazione secondo `usa_ubicazioni`;
* **annullo**: `CONFERMATO → ANNULLATO` ⇒ storno al costo del carico, giacenza
  tornata; con merce già uscita di nuovo ⇒ il rifiuto della primitiva;
* **ri-consegna**: reso per ri-consegna confermato, poi bolla di ri-consegna
  emessa ⇒ carico e scarico, giacenza netta come prima del reso;
* **porta**: `UPDATE` diretto dello stato di un reso che muove merce ⇒ rifiuto;
  il verbo senza azione ⇒ rifiuto; l'app non esegue `fn_posta_reso`;
* **i presidi trasversali**: `dbops/test-riferimenti-morti-v1`,
  `script/test-rubinetto-primo-motivo-v1`, la postura dei grant.

⚠️ Le lezioni dei lotti precedenti valgono intere (Lotto 3 §4-ter e registro):
la prova pre-apply è da owner e **non** vede i privilegi; un seed simulato non
prova il loader (celle vuote → token `NULL` e `nullValue: "NULL"`).

---

## 6. Richieste a BE/FE — nello stesso giro di PR

| # | Richiesta | Perché |
| --- | --- | --- |
| **R-1** | il drawer del reso: magazzino di rientro sulla testata (proposto dalla bolla), griglia dei rientri sotto la riga (il prelievo d'origine si **sceglie**, lotto e seriale si **mostrano**), i motivi della merce nella capability «Conferma» | D-3b-a, -b, P-6 |
| **R-2** | i codici nuovi coi ripieghi e le chiavi i18n (P-12) | la CI (`check_i18n_keys`, guardrail dei codici) |
| **R-3** | l'azione `conferma_reso` nell'editor profili | D-3b-f |
| **R-4** | il backend chiama le madri come oggi (la firma non cambia); ⚠️ verificare che imposti l'utente (`app.current_user_id`) anche su queste chiamate, come per i verbi del Lotto 3 | senza, il guard risponde `E_PERMESSO_NEGATO` |
| **R-5** | `resi_service`: il commento *«righe editabili solo con testata DRAFT: enforcement BE (il DB non ha il…)»* è superato — dal `20260929-01` il DB rifiuta con `E_RIGA_DOC_NON_BOZZA`, che il backend deve mappare come per le righe della bolla | D-3b-h |

---

## 7. Che cosa NON entra, e dove sta

| Cosa | Dove | Perché non qui |
| --- | --- | --- |
| i **prelievi proposti** alla bolla di ri-consegna dai rientri del reso | miglioria, senza lotto | la ri-consegna funziona già: l'operatore sceglie il lotto, che ora è a scaffale |
| un'**autorizzazione al reso** prima dell'arrivo (RMA) | decisione a sé, se serve | D-3b-c: sarebbe uno stato **prima** della conferma |
| la **merce presso terzi** e i suoi rientri | decisione a sé (D-L3-g) | è una domanda di proprietà |
| il **reso a fornitore** | Lotto 4 | ciclo acquisti |
| il satellite generico dei prelievi | Lotto 4 (D-3b-b) | il rientro non è la seconda occorrenza |
| l'apply, i pgTAP col runner, il commit | Tid | non sono autonomi |

---

## 8. Riferimenti

- Le decisioni: [Lotto 3](brief-db-magazzino-lotto-3-scarico-da-ddt.md) (D-L3-a,
  -b, -d, -e, -f, -i), [analisi carico e scarico](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md)
  (§6 identità, §7-quinquies storno, §8 lotti),
  [Lotto 2](brief-db-magazzino-lotto-2-motore.md) (D-L2-c costo,
  D-L2-m ubicazioni), [permesso nel verbo](brief-db-permesso-nel-verbo-di-scrittura.md).
- Le forme da copiare: il verbo → `vendite.fn_cambia_stato_ddt`; la merce da
  muovere in una sede → `vendite.fn_ddt_merce_da_movimentare`; la check che
  parla → `script.fn_check_ddt_merce`; il posting → `magazzino.fn_posta_ddt`; lo
  storno → `magazzino.fn_storna_movimenti_sorgente`; la porta → Regola 3 di
  `vendite.trgfn_ddt_guard_transizione`; il presidio →
  `dbops.vw_ddt_emessi_senza_scarico`.

---

## 9. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-28 | Prima stesura, da D-L3-i. ⚠️ Emerso leggendo `fn_genera_ddt_riconsegna`: la bolla di ri-consegna **eredita la causale** dalla bolla d'origine, quindi col Lotto 3 una ri-consegna scarica di nuovo merce che il reso non ha ricaricato — il 3-bis chiude un errore, non solo un buco. Sette decisioni aperte con una raccomandazione: magazzino sulla testata del reso con default dalla bolla (D-3b-a); il **rientro** punta al prelievo d'origine e ne eredita lotto, seriale e kit (D-3b-b); il carico alla **conferma** (D-3b-c); sorgente `RESO_VENDITA_RIENTRO`, `RESO_VENDITA_RIGA` resta `ROW_VALIDATOR` (D-3b-d); costo dell'uscita d'origine (D-3b-e); conferma e annullo **verbi** con azione `conferma_reso` e porta (D-3b-f); kit per componenti proporzionale ma libero sotto il tetto (D-3b-g). Due estrazioni per regola del 2: il controllo «magazzino dell'emittente» della bolla, e il presidio «documento senza movimento» |
| 2026-10-01 | 🧭 **Il registro di magazzino è un servizio dell'anello 2** (Tid): la dipendenza `vendite` → `magazzino` è verso l'interno; il verso inverso — `magazzino.fn_posta_reso` nello schema `magazzino`, che legge le tabelle di `vendite` — si sposta in `vendite`. [brief-db-magazzino-registro-anello-interno](brief-db-magazzino-registro-anello-interno.md) — scritto lo stesso giorno: `vendite.fn_posta_reso` (`20261001-19`), la `magazzino.fn_posta_reso` ritirata in `90_end/20261001-24`, ⏳ da applicare |
| 2026-09-29 | 📝 **Documentazione e pgTAP dei casi mancanti.** `manual/`: `vendite/resi` (magazzino di rientro, conferma che carica, annullo che storna, porta, presidio), `vendite/resi_righe` (righe solo in bozza, il dettaglio fisico nei rientri), `vendite/trgfn_resi_guard_transizione` (la porta), pagina nuova `vendite/resi_righe_rientri`; e il debito del Lotto 3: `magazzino/movimenti_attesi` (i verbi del blocco, l'app in sola lettura) e `magazzino/magazzini` (il predefinito, la regola «magazzino della sua azienda»). pgTAP nuovo `magazzino/test-reso-carico-kit-seriali-v1`: kit per componenti, seriale, ubicazione di rientro — 14/14 sullo scratch; la proporzione con resto resta dichiarata e non provata |
| 2026-09-29 | ✅ **Applicato e verde** (Tid): `20260928-84 → -98` e `20260929-01 → -04` `EXECUTED` su dbdev, suite pgTAP col runner come app senza regressioni. Il lato DB del 3-bis è consegnato; restano R-1…R-5 a BE/FE, la CI da zero e il pgTAP di kit, seriale e ubicazione. ⭐ La lezione del giro, in memoria: una tabella nuova, un nuovo scrittore di stato, un motivo nuovo e un adottante nuovo di un BB accendono ciascuno un presidio trasversale diverso — si provano PRIMA dell'apply, non si scoprono dal runner |
| 2026-09-29 | 🔴 **Runner di Tid**: `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1`, test 2 — l'elenco ESATTO degli adottanti del BB non conosceva il quarto, `vendite.resi_righe` (`20260929-01`, D-3b-h). È il presidio che fa il suo mestiere: aggiornato l'elenco atteso («i quattro adottanti»), 21/21 sullo scratch. ⚠️ Mancato al censimento di D-3b-h, che aveva cercato solo chi MODIFICA le righe dopo la conferma. Riverificato: nessun pgTAP inserisce righe in un reso già confermato (nove `INSERT` dopo una conferma, tutte su resi nuovi in bozza) |
| 2026-09-29 | 🔴 **Runner di Tid**: `dbops/test-vw-codici-errore-motivo-nominato`, test 6 — i codici-motivo invisibili al classificatore salgono da 4 a 5 (soglia che può solo calare). Il quinto è `E_RESO_RIENTRO_OLTRE_USCITO`: il motivo 4 di `fn_check_reso_merce` era un `FOR … LOOP` con il `RETURN` dentro, senza un `IF` accanto al motivo. **Corretto** in `20260929-04` con `SELECT … INTO` + `IF FOUND`, la forma del motivo 2: nessun cambio di comportamento. Sullo scratch: presidio 8/8 (7/8 senza), carico 25/25, messaggi 7/7, rubinetto 7/7, `plpgsql_check` pulito |
| 2026-09-29 | 🔴 **Runner di Tid, due presidi trasversali rossi, due registri non censiti.** (1) `dbops/test-storico-scope-policy-v1`, test 2 e 29: `vendite.resi_righe_rientri` (e `vendite.ddt_righe_prelievi` del Lotto 3) hanno lo storico da `ci_apply` ma nessuna riga in `dbops.storico_scope_policy` → righe 123-124 nel CSV, modo `PADRE` sulla riga madre (33/33 sullo scratch). (2) `dbops/test-stati-check-scrittori-v1`, test 3: `movimenti_attesi.stato = CHIUSA` e `trasferimenti.stato_trasferimento = POSTED` erano ancora ESENTE in `dbops.stati_check_dichiarazioni`, ma il Lotto 3 li scrive → tolte dal CSV e cancellate da `80_data/changelog/20260929-03` (15/15 sullo scratch). ⚠️ Nessuno dei due era nella regressione pre-apply |
| 2026-09-29 | 🔴 **Runner di Tid** su dbdev: `magazzino/test-reso-carico-v1` 24/25 — il 25 era rosso solo perché `20260929-01` non era ancora applicato. E `script/test-catalogo-messaggi-errore-completo`, test 7: *«E_RESO_MAGAZZINO_OBBLIGATORIO <- fn_check_reso_merce (emette 1, il messaggio ne chiede 0)»*. Il motivo 1 scriveva i valori vuoti come `'[]'::jsonb`, e il presidio, che conta dal `jsonb_build_array(` dopo `'valori'`, finiva su quello del motivo 2. **Corretto** in `20260929-02` con `jsonb_build_array()`: nessun cambio di comportamento. Provato su `zeroerp_ci` in transazione annullata: presidio 7/7, carico 25/25. ⚠️ Quel presidio non era nella regressione pre-apply (§4-ter): ora sì |
| 2026-09-29 | ✅ **D-3b-h, Tid: A.** Le righe del reso si toccano solo in bozza: `20260929-01` monta il BB delle righe dei documenti su `resi_righe` (tipo `RESO`, già noto al lettore dal `20260928-86`). Test 25 nel pgTAP del carico; test 9 della vista delle righe effettive riscritto sul modello (la riga si spegne in bozza). Richiesta R-5 al backend |
| 2026-09-28 (notte) | ✅ **Scritto, non applicato** (§4-bis): quindici changeSet `20260928-84 → -98`, seed, postura nelle tre sedi, un pgTAP nuovo e 22 aggiornati. Due scostamenti di metodo dichiarati: il BB estratto è la sola regola «magazzino dell'emittente» (l'immutabilità resta nei due guard), e il presidio è una **seconda vista** gemella, non una vista unica (P-3, P-13). 🔴 Rilievo di Tid: firme e `RETURNS TABLE` erano a tipi nudi, corretti con `%TYPE`. ✅ Prova pre-apply su `zeroerp_ci` (§4-ter). ⏸️ Emersa scrivendo **D-3b-h**: le righe di un reso confermato si possono ancora cambiare |
| 2026-09-28 | ✅ **Tid accoglie le sette raccomandazioni** (D-3b-a → D-3b-g), compreso il permesso `conferma_reso` richiesto **sempre** (D-3b-f). Si scrivono i changeSet |
| 2026-10-14 | ✅ **Chiuso e archiviato** (sessione BE, su richiesta di Tid). I residui (CI da zero, corsa col runner del pgTAP kit/seriali, R-1c nel suo brief) passano al §5 del [piano BE/FE](../work-in-progress/piano-be-fe-magazzino-lotto-3.md); il collaudo a video e' [collaudo-in-app-magazzino-bolla-e-reso](../work-in-progress/collaudo-in-app-magazzino-bolla-e-reso.md) |
