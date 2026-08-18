# Brief di design — la situazione della merce di un ordine non è leggibile da nessuna parte

> **Tipo**: brief di design · **Data**: 2026-08-17 · **Owner**: Tid ·
> **Stato**: 🟢 **FATTO E VALIDATO IN-APP** (Tid, 2026-08-18) su `ORD0018586`
> (l'ordine del §3, quello che ha generato il requisito) e su `ORD0018585`
> (confermato e mai spedito). Vedi §8.
>
> **Origine**: rilievo in-app di Tid (2026-08-17), dopo aver percorso a mano il
> giro completo ordine → DDT → fattura → reso a credito → reso per riconsegna:
> *«a video non si capisce nulla di tutto questo giro… se si vuole avere la
> situazione di un ordine non si capisce nulla di quello che è successo»*.
>
> **Requisito minimo posto da Tid**: *«quanto meno nell'ordine, da qualche parte,
> va indicata una situazione»*.
>
> ✅ **Quattro decisioni di forma prese con Tid il 2026-08-17** (§5): pannello
> **sull'ordine e sul DDT**; **riassunto in testata** con dettaglio a richiesta;
> ciò che non si può ancora chiudere **si mostra dichiarandolo**; il saldo **non
> si mostra mai come numero negativo** ma come compito («8 da accreditare»).
>
> ✅ **Anche la quinta è decisa**: la merce aggiunta a mano **rientra** nei conti,
> con la generalizzazione della partita (opzione C del §7-bis del brief NC).
>
> 🔴 **Ordine di esecuzione, e non è negoziabile**: **partita generalizzata →
> questo pannello → nota di credito**. Costruito prima della generalizzazione, il
> pannello mostrerebbe spedizioni miste con conti parziali proprio **sul DDT**,
> dove l'incoerenza si vede a occhio (§5.5).
>
>
> ## 🔢 ORDINE DEI LAVORI COLLEGATI
>
> **1.** partita generalizzata → **2.** pannello situazione merce (ordine e DDT)
> → **3.** nota di credito.  ·  *In parallelo e indipendente*: righe DDT a
> prezzo zero.
>
> Catena completa e ragioni in
> [brief-design-partita-merce-generalizzata.md](brief-design-partita-merce-generalizzata.md).
>
> **Rif.**: [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md)
> (le code che alimentano la lettura) · `brief-design-fatturazione-due-lenti.md`
> §6-quater DL-24/DL-27.

---

## 1. Il fatto: il dato c'è, l'oggetto che lo racconta c'è, non lo mostra nessuno

`vendite.vw_contatore_merce` tiene il conto della partita per **riga d'ordine**:

```text
ordine_riga_id · ordine_id · articolo_id · tenuti · fatturati · differenza
```

È l'oggetto che risponde a *«di questi pezzi, che ne è stato?»*. Cercato in tutto
il repository: **non è consumato da nessuno** — né dal backend né dal frontend.
Vive solo dentro altre viste DB (`vw_resi_da_accreditare` per calcolare
l'accredito, `fn_list_ddt_da_pushare` per escludere la merce tornata indietro).

⚠️ **Serve a far funzionare le macchine e non è mai stato mostrato a una
persona.** È la ragione precisa per cui il giro non si legge: il numero che lo
spiega non è su nessuna schermata.

✅ Nota che semplifica il lavoro: la vista porta già `ordine_id`, quindi
raccogliere la situazione di un ordine è un filtro, non una nuova aggregazione.

## 2. Cosa c'è oggi, e perché non basta

La **barra dei collegamenti** dei drawer mostra i chip dei documenti collegati —
«Ordine», «2 DDT», «Reso» — con un'intenzione dichiarata nel codice:

> *«un reso su un DDT avvisa che le quantità non significano più quello che
> leggi»*

**Avvisa**, ma non dice *cosa* significano adesso. E ha un secondo limite, anche
questo dichiarato: mostra **un solo livello**. Su `ordine → DDT → reso`, l'ordine
mostra «DDT» e **non** «Reso», perché il reso è collegato al DDT. Partendo
dall'ordine, il reso non si vede nemmeno come esistenza.

## 3. Il caso reale che ha generato il requisito

Percorso a mano il 2026-08-17 su una riga d'ordine da **21 pezzi**:

| Fatto | Dove si legge oggi |
| --- | --- |
| 21 ordinati, tutti spediti (`DDT0010839`) | drawer ordine |
| tutti fatturati (fattura 9908, lotto `LTF-0004017`) | lista lotti / drawer fattura |
| `RESO0005122`: 5 a credito → accredito **5 DOVUTA** | tab «Da accreditare» |
| `RESO0005123`: 3 per riconsegna → accredito **3 FACOLTATIVA** + 3 da riconsegnare | due tab diversi |
| **tenuti 13 · fatturati 21 · differenza −8** | **da nessuna parte** |

**Cinque schermate per ricostruire una storia, e la riga che la riassume non
esiste.** Nessuno dei numeri è sbagliato: il modello si comporta come previsto —
lo stesso reso compare in due code e l'accredito è *facoltativo* perché la merce
si può ancora riconsegnare. È la **lettura** che manca.

## 4. Cosa serve (il «cosa», non il «come»)

Nel drawer dell'ordine, una **situazione della merce** che per ciascuna riga dica:

* **ordinato** — la quantità della riga;
* **consegnato** — quanto è uscito (dal fulfillment);
* **fatturato** — `fatturati` del contatore;
* **in mano al cliente** — `tenuti`;
* **reso** — quanto è tornato, distinguendo *a credito* da *per riconsegna*;
* **da riconsegnare** — residuo aperto (`vw_resi_da_riconsegnare.qta_residua`);
* **da accreditare** — con l'etichetta **dovuto/facoltativo**
  (`vw_resi_da_accreditare.accredito_dovuto` + `etichetta`).

Le fonti esistono tutte e tre e sono già per riga d'ordine: contatore + le due
code. Nessun calcolo nuovo, nessuna nozione nuova.

## 5. Le domande da decidere prima di scrivere

**5.1 Dove sta? ✅ DECISA (Tid, 2026-08-17): sull'ordine E sul DDT.**

L'ordine è la sede naturale — il conto della merce è **per riga d'ordine** — ma
chi apre un DDT vuole sapere cosa è successo a *quella* spedizione senza dover
risalire all'ordine. Due letture della **stessa** fonte, non due fonti.

⚠️ **Sul DDT nasce una domanda che sull'ordine non esiste**: il conto è per riga
d'**ordine**, quindi un DDT che evade righe di **ordini diversi** tocca più
partite. Va deciso se il pannello mostra *«la situazione di questa spedizione»*
(quanto di ciò che è uscito con questo DDT è fatturato, reso, da accreditare) o
*«la situazione delle partite che questo DDT tocca»* — che include merce uscita
con **altri** DDT. Sono due risposte diverse: la prima risponde a «cosa ho
spedito qui», la seconda a «come sta la partita». La prima è quella che serve a
chi apre un DDT.

⚠️⚠️ **E il DDT rende urgente il §5.5**: su una spedizione mista — righe da
ordine + righe aggiunte a mano — un pannello che conta solo le prime mostrerebbe
**una spedizione parziale spacciata per intera**. Sull'ordine la merce fuori
partita è un'assenza; sul DDT è una **contraddizione visibile**, perché le righe
del documento sono lì sotto e i conti non tornano con esse.

**5.2 Riga per riga o totale d'ordine? ✅ DECISA (Tid, 2026-08-17):
riassunto in testata, dettaglio a richiesta.**

In testata una riga sola che dice **se** c'è qualcosa di aperto — es. *«Merce: 8
da accreditare · 3 da riconsegnare»* — e da lì si apre il dettaglio riga per
riga.

Perché è la scelta giusta: su un ordine **sano** non occupa spazio e non aggiunge
rumore; su uno con pendenze si nota **subito**, che è l'unico momento in cui
serve. Una tabella sempre visibile avrebbe messo sette colonne accanto alle
righe d'ordine — su un ordine da venti righe diventa una seconda tabella da
leggere, e la si smette di guardare.

⚠️ **Ne discende un requisito sul riassunto**: deve essere costruito in modo che
«tutto regolare» sia **visibilmente diverso** da «non ancora calcolato». Una
riga vuota è ambigua; serve che l'assenza di pendenze sia un'affermazione.

**5.3 Cosa si mostra di ciò che non si può chiudere? ✅ DECISA (Tid, 2026-08-17):
si mostra, dichiarando che l'azione non c'è ancora.**

Il numero si vede, con accanto la nota che **l'emissione della nota di credito
non è ancora disponibile** e che il dato è quindi informativo.

Perché non le altre due: mostrarlo **senza commento** manda l'operatore a
cercare un pulsante che non esiste, e non gli dà modo di capire se manca o se non
lo trova lui; **nasconderlo** farebbe sembrare a posto un ordine su cui c'è un
accredito dovuto al cliente — che è un'informazione che non si può tacere.

⚠️ **Questa nota è temporanea per costruzione, e va rimossa quando la NC arriva.**
Il rischio è che resti lì per sempre a dire una cosa falsa: perciò l'integrazione
fra i due cantieri è scritta **anche** nel brief NC (§10-bis), non solo qui. Chi
implementa la NC deve trovarlo dalla sua parte, senza dover conoscere questo
documento.

**5.4 Come si dice il saldo? ✅ DECISA (Tid, 2026-08-17): mai il numero
negativo — si dice cosa manca.**

Il pannello **non** mostra `−8`: mostra **«8 da accreditare»**. Il segno del
saldo diventa un'**etichetta**, cioè un compito:

```text
fatturati > tenuti   →  «N da accreditare»    (il tuo caso: 21 fatturati, 13 in mano → 8)
tenuti > fatturati   →  «N da fatturare»      (merce consegnata e non ancora fatturata)
tenuti = fatturati   →  nulla in sospeso
```

Perché: `differenza` è un saldo, e un saldo negativo si legge come un guasto
anche quando è la descrizione corretta del mondo. L'operatore deve leggere **che
cosa c'è da fare**, non fare l'algebra fra due colonne.

⚠️ **Conseguenza per chi implementa**: il verso del saldo va tradotto **una volta
sola**, in un punto condiviso. Due traduzioni indipendenti — una nel pannello
ordine, una in un eventuale pannello DDT — divergerebbero, e sarebbero due frasi
diverse per lo stesso numero. `differenza` resta il dato; l'etichetta è la sua
lettura.

**5.5 La merce fuori partita? ✅ DECISA (Tid, 2026-08-17): rientra, con
l'opzione C.**

Le righe DDT aggiunte a mano oggi non hanno `ordine_riga_id` e **non compaiono**
in nessuno di questi conti. La scelta è di **farle rientrare**: righe manuali di
prima classe, con una partita propria (§7-bis del brief NC, opzione C — scelta e
resa **prerequisito** della slice NC).

Ne discende, per questo pannello:

* **non serve un caso speciale**: quando la partita è «la riga di merce» e la
  riga d'ordine è una delle sue possibili origini, il pannello conta tutto ciò
  che è uscito, ordinato o no;
* **la contraddizione del §5.1 non si presenta**: sul DDT i conti tornano con le
  righe che si leggono sotto, comprese quelle aggiunte a mano;
* ⚠️ **ma questo pannello dipende da quel lavoro.** Costruito prima della
  generalizzazione, mostrerebbe spedizioni miste con conti parziali — e li
  mostrerebbe **sul DDT**, dove l'incoerenza è visibile a occhio. L'ordine di
  esecuzione è: **partita generalizzata → pannello → NC**.

## 6. Cosa NON serve

* **Nessun cambio ai calcoli**: contatore e code restano come sono, si leggono.
* **Niente sulle lenti** (Competenza, Backlog, Situazione aperta): quelle
  rispondono a *«cosa devo fare»*, questa a *«cos'è successo a questo ordine»*.
  Sono due domande diverse e non vanno mescolate.
* **Nessuna azione nel pannello** in questa fase: è una lettura. I verbi vivono
  dove già stanno (code resi, dashboard).

## 7. Definizione di «fatto»

* [x] aprendo l'ordine si capisce, **senza uscire dal drawer**, quanto è stato
      consegnato, fatturato, reso, e cosa resta aperto;
* [x] il caso del §3 è leggibile in **una** schermata invece di cinque;
* [x] un saldo negativo è **spiegato**, non solo esposto (§5.4) — anzi non è
      mai mostrato come numero negativo: è un compito;
* [x] ciò che non si può ancora chiudere è **dichiarato tale** (§5.3);
* [x] il pannello non contraddice le code: legge **le stesse viste**, quindi
      stessi numeri e stessa etichetta dovuto/facoltativo per costruzione.

✅ **Validato in-app da Tid il 2026-08-18** su `ORD0018586`: *«vedo 8 da
accreditare · 3 da riconsegnare · 3 da spedire, mi sembra corretto»*.

⭐ **È l'ordine del §3**, quello percorso a mano il 2026-08-17 che ha generato
il requisito: cinque schermate per ricostruirlo, e la riga che lo riassume non
esisteva. Ora è la prima cosa che si legge aprendo il drawer.

---

## 8. 📓 Come è stato realizzato (2026-08-18)

**Backend** — `GET /vendite/{ordini|ddt}/<id>/situazione-merce/`, quattro
sezioni in un round-trip, dal factory `build_situazione_merce_view`. Doc:
[api_situazione_merce.md](../../backend/vendite/manual/api_situazione_merce.md).

**Frontend** — `src/vendite/_shared/situazioneMerce/`: `SituazioneMerceBar`
(il riassunto in testata, sotto `DocumentoCollegamentiBar`) +
`SituazioneMerceDialog`/`Contenuto` (il dettaglio) + `sintesiSituazioneMerce`
(funzione pura) + `statoMerceSeverity`. Montato in `OrdiniDrawer` e
`DdtDrawer`, con `reload` agganciato alle azioni che spostano merce.

**Il caso del §3, a video**, dal payload vero:

```text
Merce:  [8 da accreditare]  [3 da riconsegnare]  [3 da spedire]
   ↓ (un clic)
righe d'ordine   riga 1 · ordinato 21 · consegnato 21 · dal cliente 13
                 · fatturato 21 · da spedire 3 · «8 da accreditare»
spedizioni       DDT0010839 · consegnato 21 · reso 8 · «8 da accreditare»
da accreditare   RESO0005122 · 5 · Dovuta      RESO0005123 · 3 · Facoltativa
da ri-consegnare RESO0005123 · resa 3 · ri-consegnata 0 · residua 3
```

⭐ **Le cinque schermate del §3 sono una riga e un clic.**

### 8.1 ✅ La soglia di impegno dell'ordine — rilievo chiuso il 2026-08-18

**Com'era**: una riga d'ordine **confermata e non ancora spedita** produceva il
chip «N da spedire». Corretto in sé, ma la review del 2026-08-18 ha misurato che
la vista **non guardava lo stato dell'ordine**: **60 righe su 107** del pannello
stavano su ordini in **BOZZA**, tutte con `da_spedire > 0`. Un ordine in bozza
presentava un'intenzione come un arretrato; un ordine **annullato** lo avrebbe
mostrato per sempre.

**Come è stato chiuso** — team DB, `20260818-06`, e il rimedio è **migliore di
quello che avevamo proposto**. Noi chiedevamo di far sparire le righe sotto
soglia; loro hanno fatto sparire il **numero**:

```text
impegnata := stato ordine >= CONFERMATO  AND NOT is_abortito

da_spedire   NULL             sotto soglia
stato        NON_IMPEGNATA    sotto soglia e senza partite   ← settimo valore
```

⭐ **Perché la loro è la scelta giusta, e la nostra no**: il pannello si legge
**per un ordine**. Togliere le righe non ripulisce un elenco da 107 — rende
**vuoto il pannello di ogni bozza**, cioè «non c'è nulla» dove la verità è «non
sto vedendo niente». È lo stesso difetto che il cancello di perimetro del
service combatte col 404, entrato da un'altra porta.

⚠️ **E la clausola di salvaguardia che avevamo chiesto era un ramo morto**:
`fn_check_ordine_annullabile` non lascia annullare un ordine con un DDT vivo, D1
esclude i DDT abortiti, e i due scrittori di `ordini_righe_fulfillment` creano
entrambi il DDT da ordine — quindi *abortito ⟹ zero partite*. La protezione
esiste comunque, come **precedenza nel `CASE`**: dove c'è merce uscita vince il
saldo, e se quel ramo un giorno si aprisse il pannello lo mostrerebbe invece di
nasconderlo.

**Verificato come applicazione** dopo l'applicazione:

```text
cardinalita' .................. 107   (invariata)
NON_IMPEGNATA .................  60   tutte con da_spedire NULL
NON_SPEDITA ...................  29   (erano 89: le bozze se ne sono andate)
arretrati dichiarati sotto soglia  0
```

#### 🔴 E il cambio ha creato un difetto nel FRONTEND, trovato provandolo

Con `da_spedire` NULL spariva **l'unica voce che su una bozza faceva
`haPendenze`** — e `tuttoRegolare` era `!haPendenze && righe.length > 0`.
Risultato: un ordine in bozza usciva `tuttoRegolare: true`, cioè **la spunta
verde «tutto regolare» su un ordine dove non è successo niente**.

⭐ **È il requisito §5.2 di sempre, sul terzo caso che allora non esisteva**:
«tutto regolare», «non ancora calcolato» e «non ancora impegnato» sono **tre**
cose, e solo la prima si può affermare. `tuttoRegolare` ora pretende almeno una
riga con un impegno vero; su un ordine interamente `NON_IMPEGNATA` la barra
**non compare** — e il Tag di stato del drawer dice già «Bozza».

✅ **Validato anche quello, da Tid il 2026-08-18**: `ORD0018585` —
**CONFERMATO**, 1 ordinato, 0 consegnato — mostra «**1 da spedire**».

⭐ **E la cosa che conta non è il chip, è ciò che NON compare accanto**:
`differenza` è `null` e `fatturato_anticipato` è 0, quindi niente «da
fatturare» e niente «da accreditare» su una riga che deve solo partire. È il
rilievo A chiuso a video, sull'unico caso in cui si vedrebbe.

Con questa, i due estremi del vocabolario sono provati in-app: l'ordine più
complicato che esista in sviluppo (`ORD0018586`: consegnato, fatturato, reso a
credito, reso per ri-consegna) e quello più semplice (`ORD0018585`: confermato
e fermo).
