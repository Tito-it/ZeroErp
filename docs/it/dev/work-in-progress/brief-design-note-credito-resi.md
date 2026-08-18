# Brief di design — la nota di credito: chiudere il ramo morto degli accrediti

> **Tipo**: brief di design (decisioni di dominio) + **piano DB** + **esecuzione**
> + **piano BE/FE** ·
> **Data**: 2026-08-17 · **rev**: 2026-08-18 (PARTE IV) · **Owner**: Tid ·
> **Stato**: ✅ **PERIMETRO DB CHIUSO E APPLICATO** (2026-08-18) ·
> 📋 **PIANO BE/FE SCRITTO, NIENTE ANCORA IMPLEMENTATO**.
> Ventitré changeSet (`20260818-24` → `-46`) applicati, due pgTAP nuovi (22
> asserzioni), quattro pgTAP esistenti riallineati, baseline `vendite` e
> `script` **senza regressioni**, doc concettuale aggiornata. Cronaca
> dell'esecuzione, **tre correzioni al piano** e residui nella **PARTE III
> (§20)**. Decisioni di dominio in §3; analisi critica, dieci decisioni chiuse
> (§14) e piano a dodici slice (§15) nella PARTE II. Il piano **backend e
> frontend** — otto slice BE, sei FE, i prerequisiti che restano al team DB e
> le richieste del §17 verificate una per una contro il codice vivo — è nella
> **PARTE IV (§21 → §26)**.
>
> 🔴 **Da leggere per primo, se si sta per iniziare**: il §21.1. Il seed di N11
> è già in esercizio e il Backlog dice all'operatore *«emetti la nota di credito
> dalla coda accrediti»*, mentre il pannello situazione merce dichiara ancora
> che l'emissione **non è disponibile** e la coda non ha il verbo. Sono i tre
> posti del §9-bis, e oggi ne parla uno solo: **BE/FE non è il seguito di questa
> slice, è ciò che chiude una contraddizione già in esercizio.**
>
> ⚠️ **La PARTE I va letta sapendo che il §7-bis è SUPERATO**: la
> generalizzazione della partita (opzione C) è stata fatta e applicata il
> 2026-08-17. Il §7-bis resta agli atti come il ragionamento che l'ha decisa,
> non come lavoro da fare.
>
> **Origine**: rilievo in-app di Tid (2026-08-17), subito dopo aver costruito il
> primo caso della coda accrediti: *«ho dei resi che ho deciso essere da
> accreditare, ma così come fatto rimangono bloccati, sembrano un ramo morto»*.
>
> **Ed è un ramo morto per progetto, non per dimenticanza**: la slice che ha
> costruito la coda ([brief-db-fatturazione-ddt-resi.md](../work-done/brief-db-fatturazione-ddt-resi.md)
> §7) mette l'emissione della NC **fuori perimetro** — *«qui solo la coda che la
> alimenta»* — e lascia un **contratto vincolante** per chi la disegnerà (§2).
>
> **Design-of-record a monte**: [brief-design-fatturazione-due-lenti.md](../work-done/brief-design-fatturazione-due-lenti.md)
> §6-quater, decisioni **DL-24** (dove vivono i resi) e **DL-27** (il contatore).
>
> ---
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
> ## ✅ PREREQUISITO — SODDISFATTO il 2026-08-17
>
> **La generalizzazione della «partita» (opzione C del §7-bis) è FATTA e
> APPLICATA**: nove changeSet (`20260817-06` → `-14`), perimetro DB chiuso,
> backend chiuso il 2026-08-18 (PR #1282/#1283), pannello situazione merce
> in-app. **La partita non è più `ordine_riga_id`: è `vendite.ddt_righe.id`.**
>
> ⚠️ **Ne discende che ogni riga di questo brief che dice «partita» va letta
> come «riga di DDT»**, e che le tre cose che il §2 chiedeva alla NC si
> scrivono ora sulla chiave definitiva. Il testo qui sotto è quello del
> 2026-08-17, conservato:
>
> Oggi la partita **è** `ordine_riga_id`. Se la NC nasce su quella nozione, poi
> generalizzarla obbliga a rimettere mano a tutto ciò che la NC avrà costruito
> sopra — attribuzione dell'accredito, coda accrediti, legame col contatore,
> pgTAP — **più le NC già emesse da riconciliare**. Fatta prima, la NC si scrive
> **una volta sola** e sulla chiave definitiva.
>
> ⚠️ **Non è una preferenza di ordine: è la differenza fra scriverla una volta e
> scriverla due.** E la seconda volta si riscriverebbe codice che intanto ha
> prodotto **documenti fiscali**, cioè la categoria di dato che meno si può
> rifare.

---

## 1. Il fatto, misurato oggi

La coda accrediti ha la sua **prima riga in assoluto** (2026-08-17, caso
costruito a mano validando DL-27):

```text
RESO0005122 · DDT0010839 · resa 5 · tenuti 16 · fatturati 21
accredito dovuto 5 · etichetta DOVUTA
```

Da lì **non si va da nessuna parte**: non esiste un verbo che trasformi
quell'accredito dovuto in un documento. La riga resterà in coda per sempre.

## 2. Il contratto già scritto (vincolante)

Dal §7 della slice di luglio, da rispettare qualunque forma si scelga:

> **La nota di credito deve essere attribuibile alla merce e portare una
> quantità.** Un puro legame documento↔documento **non basta**: il contatore
> chiude il cerchio solo se sa *quanti pezzi* di *quale merce* sono stati
> accreditati. **Una NC che non abbassa i «fatturati» della partita è invisibile
> al contatore → la coda accrediti continuerebbe a chiedere l'accredito per
> sempre, anche a NC emessa.**

✅ **Verificato oggi che il rischio è concreto**: `vendite.fatture_rettifiche`
esiste ed è **esattamente** la forma che il contratto dichiara insufficiente —
`(fattura_id, rettificata_id)` e nient'altro, **0 righe**, mai usata. Non va
buttata: serve come legame fra i due documenti. Ma da sola non chiude nulla.

## 3. Le decisioni di Tid (2026-08-17)

| # | Domanda | Decisione |
| --- | --- | --- |
| **N-1** | Come si valorizza l'accredito? | **Come in fattura** — stesso valore con cui la merce è stata fatturata |
| **N-2** | NC dedicata o riga in fattura? | **Sempre NC dedicata**, con il riferimento al documento rettificato |
| **N-3** | Automatica o a comando? | **Verbo dell'operatore** dalla coda accrediti |

**N-1 — perché chiude il cerchio.** Se l'accredito vale quanto è stato
fatturato, i `fatturati` scendono esattamente di quanto erano saliti e la
differenza torna a zero. Con qualunque altro prezzo resterebbe un residuo
perpetuo in coda — cioè il difetto contro cui il §2 mette in guardia.

⭐ **E porta con sé una regola che il modello applica già**: *«un reso entra in
commessa solo se fatturato; altrimenti la scelta è solo se rispedirlo, e rientra
nel giro di fatturazione successivo»*. Non è una regola nuova: è **la
popolazione della coda**. `differenza = tenuti − fatturati` diventa negativa
solo se la merce era stata fatturata; se non lo era, la differenza resta a zero
e il reso non compare. Tid ha dato un nome a ciò che il contatore fa già.

**N-2 — perché non una riga negativa in fattura.** Una quantità negativa dentro
una fattura ordinaria non **è** una nota di credito: la NC è un documento
fiscale suo, con numerazione propria e riferimento al documento rettificato —
senza il quale non regge né verso il cliente né verso la FatturaPA.

**N-3 — perché non automatica.** L'accredito è un atto commerciale: la coda
esiste **perché qualcuno decida**. Generarlo alla conferma del reso vorrebbe
dire emettere documenti fiscali senza che nessuno li abbia voluti.

## 4. La strada proposta: la rettifica rientra in commessa

Proposta di Tid, e il modello la asseconda: il reso da accreditare genera
un'**attività di commessa di rettifica** con quantità negativa, legata alla
stessa partita. Da lì entra nel serbatoio come qualunque altra riga, viene
lavorata **dallo stesso verbo di fatturazione** e produce il documento.

Il pregio: **nessuna seconda pipeline**. La NC diventa un documento come gli
altri, prodotto dalla macchina che già esiste — e il contatore si chiude da sé,
perché i `fatturati` scendono senza che nessuno debba insegnarglielo.

✅ **Il gancio è già nel modello, e non è mai stato usato.** Il vocabolario dei
movimenti ammette tre valori su **entrambe** le tabelle della catena
(`commesse_attivita` e `attivita_fatturabili`):

```text
chk_*_tipo_movimento : NORMALE | RETTIFICA | ONERE
```

Uso reale al 2026-08-17: **89 `NORMALE`, 3 `ONERE`, zero `RETTIFICA`**. È un
posto apparecchiato e mai occupato — e il nome dice per cosa.

## 5. 🔴 Il buco che cambia il perimetro: il tipo documento non esiste

Verificato oggi, ed è la scoperta che va messa davanti a tutto:

```text
config.tipi_doc_fiscale     → 1 FRONTOFFICE · 2 BACKOFFICE
vendite.registri_fatturazione → 3 Front-office · 4 Back-office
```

Quelli **non sono tipi di documento**: sono i due **canali** di fatturazione. In
tutto il modello **non esiste un tipo «nota di credito»**, né un registro
dedicato: `vendite.fatture` conosce un solo genere di documento.

⚠️ **Ne discende che N-2 non è una scelta di forma ma un pezzo di modello da
costruire**: serve un tipo documento distinto (o un discriminante equivalente) e
va deciso **come si numera** — sezionale proprio, numerazione condivisa con le
fatture, o serie dedicata. È materia fiscale e sta interamente nel perimetro DB.

## 6. Il segnale c'è già, e cambia colore da solo

DL-24 ha creato nel **Backlog fatturazione** un ramo dedicato ai resi con due
motivi. Il secondo è **`MERCE_RESA_GIA_FATTURATA`**, popolato dalla **stessa**
condizione della coda accrediti (la differenza negativa del contatore, DL-27).

Oggi è marcato 🟢, e la ragione è testuale nella decisione: *«è 🟢 perché
**nessuna azione esiste oggi** (NC assente, correzione manuale vietata
dall'immutabilità)»*.

**Appena il verbo esiste, quel motivo cambia natura**: da constatazione senza
rimedio a **arretrato con azione**, e va portato a 🟠. Non c'è un segnale da
inventare: c'è da riaccendere quello che c'è e agganciarci il verbo.

### 6.1 ⭐ Il meccanismo è già tutto lì, ed è una riga di seed

Misurato il 2026-08-17, validando le card: nel Backlog **la lista resi è vuota**
anche adesso che esiste il primo reso con accredito dovuto. Non è un difetto —
è la classificazione che fa il suo mestiere. L'ultimo filtro della vista dice:

```sql
WHERE COALESCE(mf.classe, 'ANOMALIA') <> 'FISIOLOGICO'
```

e i due motivi del ramo resi sono classificati così in `config.motivi_fermo`:

| Motivo | Classe | Azione |
| --- | --- | --- |
| `RICONSEGNA_NON_ESEGUITA` | `RECUPERABILE` | «Genera il DDT di ri-consegna» |
| `MERCE_RESA_GIA_FATTURATA` | **`FISIOLOGICO`** | **nessuna** |

Il Backlog elenca ciò che è **fermo e recuperabile**: un motivo senza rimedio
non è arretrato, è uno stato di fatto, e resta fuori. Coerente con sé stesso —
e inutile per l'operatore, che è esattamente il *«sembrano un ramo morto»* da
cui nasce questo brief.

✅ **Ne discende che il §6 costa meno di quanto sembrava**: non serve toccare la
vista né la union. Quando il verbo esiste, si porta
`MERCE_RESA_GIA_FATTURATA` da `FISIOLOGICO` a `RECUPERABILE` e gli si dà
l'`azione` — **due celle di seed** — e le righe entrano nel Backlog da sole.

⚠️ Da fare **insieme** al verbo, non prima: riclassificarlo mentre l'azione non
esiste riempirebbe il Backlog di righe che nessuno può chiudere, cioè il difetto
che la classificazione `FISIOLOGICO` sta oggi prevenendo.

⭐ **Una scelta di luglio che oggi paga.** Il motivo si chiamava `NC_DOVUTA` ed è
stato rinominato in `MERCE_RESA_GIA_FATTURATA` per *«nominare il fatto e non il
rimedio, perché le NC non sono ancora definite e il motivo non deve pre-decidere
la risposta»*. Oggi il rimedio si decide — **e il nome del fatto non si tocca**.

## 7. Dove NON va il segnale — e perché

Tid aveva proposto di segnalare i resi da accreditare **anche in Situazione
aperta**. Va contro DL-24, che esclude i resi dal serbatoio con tre argomenti:
`RESO_VENDITA` è dichiarato `REVERSE_FLOW` dal DB; sarebbe **doppio conteggio**
perché `fn_conferma_reso` riapre il residuo e l'ordine rientra da sé; e
violerebbe la semantica di DL-14.

**Concordiamo con la decisione presa**, per una ragione che è anche di lettura:
Situazione aperta misura **merce che aspetta di essere fatturata**, e un
accredito è di **segno opposto** — non è arretrato di fatturazione, è un debito
verso il cliente. Sommarli renderebbe il totale del serbatoio la somma di cose
che non si sommano.

Se servisse comunque una spia lì, va tenuta **fuori dal serbatoio**, come
contatore a sé («accrediti da emettere: N»), non come area del funnel.

## 7-bis. 🔴 La merce senza partita — emersa il 2026-08-17, tocca direttamente questa slice

Validando DL-23 è emersa una domanda che sembrava di un altro cantiere e invece
morde qui: **su un DDT nato da ordine si possono aggiungere righe a mano**, e
quelle righe **non appartengono a nessuna partita**.

### Come si aggancia (e come non si aggancia) una riga all'ordine

Su `vendite.ddt_righe` **non esiste** una colonna verso l'ordine: il legame vive
in `vendite.ordini_righe_fulfillment`, terna `(ordine_riga_id, ddt_riga_id,
qta_evasa)`. Una riga aggiunta a mano quella terna non ce l'ha, e **nessun guard
lo impedisce** — l'unico controllo su `gestisci_riga` è che il DDT sia in bozza.

### Cosa ne consegue, misurato

| | Stesso articolo dell'ordine | Articolo **non** in ordine |
| --- | --- | --- |
| Residuo dell'ordine | ❌ resta gonfiato: merce uscita, ordine che non lo sa | ✅ corretto, non c'era nulla da scalare |
| Fatturazione | ✅ avviene, via ramo **standalone** di `fn_list_ddt_da_pushare` | ✅ avviene, stesso ramo |
| Contatore merce e **accredito** | ❌ fuori partita | ❌ **fuori partita** |

Il terzo rigo è il punto: `vw_contatore_merce` è per `ordine_riga_id`, e la coda
accrediti si aggancia a quello (`JOIN acc ON a.ordine_riga_id = e.ordine_riga_id`).
`vendite.resi_righe.ordine_riga_id` è **nullable** — oggi 2 righe su 17 lo hanno
vuoto — quindi un reso su merce manuale **si registra ma non produce accredito**:
la coda non lo vede.

⚠️ **Ne discende che i due casi sono problemi diversi**: il primo è un **errore
da prevenire** (indistinguibile da una svista dell'operatore); il secondo è un
**limite del modello su un caso legittimo** — il pallet a rendere, l'omaggio, il
ricambio spedito insieme sono fatturati bene e **non accreditabili**.

### Perché riguarda proprio questa slice

Se la NC lavora **per partita**, va deciso **prima** cosa succede alla merce che
partita non ha. Deciderlo dopo significa scoprire a slice fatta che una classe
di merce fatturata non è accreditabile — e il §2 di questo brief dice già cosa
succede quando il contatore non vede un accredito: la coda lo chiede per sempre.

### ✅ DECISIONE (Tid, 2026-08-17): opzione **C**, e viene **prima** della NC

**Le righe manuali diventano di prima classe**: hanno una partita propria, il
contatore le vede, la NC le accredita. Scartate la A (risolve metà problema) e la
B (sposta il costo sul magazzino: una spedizione, due documenti di trasporto).

⚠️⚠️ **C è un PREREQUISITO di questa slice, non un seguito.** Se la NC nasce
sulla nozione di partita di oggi — che **è** `ordine_riga_id` — poi generalizzarla
significa rimettere mano a tutto ciò che la NC avrà costruito sopra:
attribuzione dell'accredito, coda accrediti, legame col contatore, pgTAP, più le
NC già emesse da riconciliare. Fatta prima, la NC si scrive **una volta sola** e
sulla chiave definitiva. È l'ordine che Tid ha indicato, e la ragione è
esattamente questa: *l'inverso richiede più lavoro*.

⭐ **L'argomento che ha spostato la scelta è arrivato da un'altra decisione**: il
pannello «situazione merce» va **anche sul DDT**
([brief dedicato](brief-design-situazione-merce-ordine.md) §5.1). Sull'ordine la
merce fuori partita è un'**assenza** — manca un numero che nessuno sa di dover
cercare. Sul DDT è una **contraddizione visibile**: le righe del documento sono
lì sotto, e il pannello sopra ne conterebbe solo alcune. Una spedizione mista
mostrerebbe conti che non tornano con ciò che si legge due centimetri più in
basso, nella stessa schermata.

**Cosa comporta C, in breve**: oggi la partita **è** la riga d'ordine. Con C la
partita diventa **la riga di merce**, e la riga d'ordine è una delle sue possibili
**origini** (l'altra è «nessuna»). Tocca il contatore, le due code e la NC —
quindi è una generalizzazione del modello, non una riga di codice. Il momento
giusto è adesso **solo perché la NC non è ancora scritta**.

### Le opzioni valutate (agli atti)

**Orientamento iniziale di Tid (2026-08-17)**: bloccare l'aggiunta manuale quando
l'articolo è già nell'ordine; e forse, più drasticamente, **vietare del tutto le
righe manuali sui DDT nati da ordine** — la merce extra va su un DDT suo.
Superato dalla decisione qui sopra.

* **A — guard sul solo articolo duplicato.** Risolve l'errore, lascia aperto il
  limite: la merce extra continua a essere non accreditabile. Minimo intervento,
  problema dimezzato.
* **B — divieto totale sui DDT order-backed** (l'ipotesi drastica). Coerente e
  semplice da spiegare: *un DDT o evade un ordine, o è un documento a sé*. Ogni
  riga ha una partita o nessuna, mai un misto, e la NC ha una regola sola.
  ⚠️ **Il costo è fisico, non informatico**: una spedizione sola viaggerebbe con
  **due documenti di trasporto**. Il DDT accompagna la merce, e chi guida ne
  porta due invece di uno. Prima di sceglierla vale la pena chiedersi quanto
  spesso capita di aggiungere merce a una spedizione già ordinata.
* ✅ **C — righe manuali di prima classe** (**SCELTA**). Ammesse, ma con una
  partita propria, così il contatore le copre e la NC le accredita. È l'unica che
  risolve entrambi i casi, ed è la più costosa: richiede di estendere la nozione
  di partita oltre `ordine_riga_id`.

La domanda che decideva fra le tre era **quanto spesso esce merce non ordinata
insieme a merce ordinata**. La risposta implicita nella scelta di C: abbastanza
spesso perché valga la pena farla funzionare, invece di vietarla (B) o di
accettarne il limite (A).

## 8. Domande aperte — tutte per il DB

1. **Tipo documento e numerazione della NC** (§5): il pezzo mancante più grosso.
2. **Chi genera la rettifica in commessa**: una funzione madre invocata dal
   verbo, sul modello dei push esistenti? E con quale idempotenza — due click
   non devono produrre due accrediti.
3. **Valorizzazione operativa di N-1**: da dove si legge «il valore con cui è
   stata fatturata» — riga di fattura, o ricalcolo? La slice di luglio indicava
   `ddt_righe.prezzo_unitario` (COALESCE con la riga ordine) come strada
   disponibile, ma N-1 sposta il riferimento **sulla fattura**, che è più
   preciso e va confermato come sorgente.
4. **Immutabilità**: la porta oneri e l'immutabilità delle quantità vietano gli
   UPDATE post-emissione — la rettifica è una **riga nuova**, e va verificato
   che la porta esista anche per questo tipo di movimento.
5. **Parzialità**: un accredito parziale di una riga già accreditata in parte
   deve poter esistere? La coda calcola già `accredito_dovuto` con una finestra
   che scala i resi precedenti, quindi il dato lo prevede.

## 9. Cosa NON è di questo cantiere

* **Movimenti di magazzino** (già fuori dalla slice di luglio).
* **La ri-consegna**: è l'altra coda, altro documento, altro giro.
* **La modifica di DL-24** sul perimetro Situazione aperta (§7).
* **Le NC facoltative**: DL-24 le dichiara *«opzione, non arretrato → fuori»* dal
  Backlog. Se il verbo le ammette, restano un'azione disponibile e non un
  arretrato da segnalare.

## 9-bis. 📌 Cosa questa slice deve andare a spegnere altrove

Il verbo che nasce qui **chiude cose che oggi vivono dichiarate come aperte** in
altri due posti. Se la slice si limita a produrre la NC, quei due posti
continueranno a raccontare il mondo di prima — ed è il tipo di incoerenza che
nessun test intercetta, perché ognuno dei due è coerente con sé stesso.

**1. La nota temporanea nel pannello «situazione merce» dell'ordine.**
[brief-design-situazione-merce-ordine.md](brief-design-situazione-merce-ordine.md)
§5.3: il pannello mostra «N da accreditare» **con la dichiarazione che
l'emissione della NC non è ancora disponibile** e che il dato è solo informativo.
Quella nota è **temporanea per costruzione**: quando la NC esiste va **rimossa**,
altrimenti resta a dire una cosa falsa. ⭐ E il posto naturale da cui invocare il
verbo diventa proprio quel pannello, dove il numero è già davanti agli occhi:
oggi la coda accrediti è raggiungibile solo da `Vendite → Resi → Da accreditare`,
cioè da un'altra parte dell'applicazione rispetto a dove il problema si vede.

**2. La classificazione `MERCE_RESA_GIA_FATTURATA` nel Backlog** (§6.1): da
`FISIOLOGICO` a `RECUPERABILE` **con** l'azione. Due celle di seed, da cambiare
**insieme** al verbo e non prima.

⚠️ **Tutte e tre le cose sono la stessa decisione vista da tre punti**: fino a
oggi «merce resa già fatturata» è un **fatto senza rimedio**, e i tre posti lo
dicono in tre modi coerenti — il Backlog la tiene fuori, il pannello la dichiara
informativa, la coda la elenca senza verbi. Nel momento in cui il rimedio esiste,
**tutti e tre** devono cambiare voce. Cambiarne uno solo produce un'applicazione
che si contraddice.

## 10. Definizione di «fatto» (bozza)

* [ ] dalla coda accrediti un verbo genera l'accredito, **a comando** (N-3);
* [ ] la NC è un documento **distinto**, numerato, con il riferimento al
      documento rettificato (N-2, §5);
* [ ] l'accredito porta **quantità e merce**, e i `fatturati` della partita
      **scendono** (§2 — il contratto);
* [ ] dopo l'emissione la riga **esce dalla coda accrediti** da sola, senza
      cancellazioni manuali: è la prova che il contatore ha visto la NC;
* [ ] `MERCE_RESA_GIA_FATTURATA` passa a `RECUPERABILE` **con** l'azione, e le
      righe compaiono nel Backlog senza toccare la vista (§6.1);
* [ ] due click non producono due accrediti;
* [ ] è deciso cosa succede alla **merce senza partita** (§7-bis): o non può
      esistere (opzione B), o è accreditabile (opzione C), o il limite è
      accettato e **scritto** (opzione A) — non lasciato implicito;
* [ ] i **tre posti** che oggi dichiarano «fatto senza rimedio» sono allineati
      (§9-bis): nota rimossa dal pannello ordine, motivo Backlog a
      `RECUPERABILE`, verbo raggiungibile da dove il numero si vede.

---

# PARTE II — ANALISI CRITICA E PIANO DB

> Scritta il **2026-08-18**, dopo la chiusura dei cantieri 1 e 2.
>
> **Metodo, e il suo limite dichiarato.** Tutto ciò che segue è letto dalle
> **definizioni vive** — documentazione auto-generata `docs/it/dbzero/` (che
> riflette l'oggetto nel DB, non lo YAML che l'ha creato), codice backend,
> seed CSV. **Nessuna misura nuova è stata eseguita sul database**: i numeri
> citati portano la data del cantiere che li ha misurati. Dove serve un conto
> fresco per decidere, sta scritto **come domanda**, non come dato.
>
> ⚠️ E vale il preambolo della PARTE II del cantiere 1: **i dati di sviluppo
> sono dati di test**. Non misurano la gravità di un difetto, misurano che il
> difetto è **raggiungibile**. Dove un caso ha zero occorrenze ma nulla lo
> impedisce, è scritto così.

## 11. Il terreno è cambiato: cosa dire prima di tutto

Fra la stesura della PARTE I (2026-08-17, sera) e oggi sono stati chiusi
**due cantieri interi**. Tre affermazioni della PARTE I non sono più vere, e
vanno lette con la correzione davanti.

| PARTE I dice… | Oggi |
| --- | --- |
| «la partita **è** `ordine_riga_id`» (§7-bis) | ❌ **superato**: la partita è `vendite.ddt_righe.id`, e la riga d'ordine è una delle sue possibili **origini** (`origine ∈ NESSUNA / ORDINE / MULTIPLA`) |
| «va deciso cosa succede alla merce senza partita» (§10) | ✅ **deciso e fatto**: righe manuali, DDT standalone e kit hanno una partita. Restano fuori solo le ri-consegne, **per progetto** |
| «il pannello dichiara che la NC non è disponibile» (§9-bis) | ✅ esiste davvero, ed è una **chiave i18n precisa** da togliere: `vendite.situazione_merce.nc_non_disponibile` |

⭐ **E c'è un guadagno che la PARTE I non poteva prevedere**: il cantiere 1 ha
lasciato in eredità **due colonne separate** sulla partita —
`fatturato_merce` (corsia DDT) e `fatturato_da_ordine` (corsia ORD) — più
`misurabile` e `stato`. Senza quella separazione il §12.3 qui sotto sarebbe un
difetto invisibile; con essa è una decisione che si può prendere.

### 11.1 Le tre cose che il cantiere 1 ha lasciato scritte per questo (§19.3), verificate

Il cantiere 1 chiude con tre avvertenze indirizzate qui. Le ho **rilette contro
il codice vivo**: due sono confermate, una va **corretta**.

| # | Avvertenza del cantiere 1 | Verifica |
| --- | --- | --- |
| **NC-1** | `uq_commesse_attivita_commessa_segment` blocca una seconda attività sullo stesso segmento → serve un suffisso, e `substring(segment_key, ':R:([0-9]+)')` continua a funzionare | ✅ **confermata, e più forte del previsto**: `vw_af_merce_per_riga` non va toccata **affatto** — vedi §12.1 |
| **NC-2** | il filtro `NORMALE` è pronto a spostarsi: «cambiare un `WHERE` in un consumatore» | ✅ **confermata**, ed è **un `LEFT JOIN` in più** in `vw_partite_merce`, non un `WHERE` cambiato — vedi §12.2 |
| **NC-3** | quando la rettifica abbassa il fatturato la differenza torna positiva e `fn_list_ddt_da_pushare` ri-spingerebbe: tiene solo `fn_get_stato_push_segment` | 🔴 **da correggere in DUE sensi opposti**: nel caso normale la differenza torna a **zero**, non positiva (quindi l'allarme è meno grave); ma nel caso ri-consegna quella cintura **impedisce ciò che deve succedere** — §12.4 |

---

## 12. I rilievi — cosa la NC smaschera

Come nel cantiere 1, la parte utile non è l'elenco delle cose da scrivere: è
**cosa cambia natura** quando il verbo esiste.

| # | Rilievo | Gravità | Dove morde |
| --- | --- | --- | --- |
| **A** | La rettifica va attaccata alla **partita** (segmento DDT), non alla corsia che ha fatturato: attaccarla alla corsia ORD sposta l'accredito sulla **spedizione sbagliata** | 🔴 | `vw_partite_merce`, CTE `alloc` |
| **B** | Il **segno**: quantità negativa in catena *oppure* `tipo_movimento` che sottrae. Le due scelte hanno raggi d'esplosione diversissimi | 🔴 | IVA, scadenze, contabilità, FatturaPA |
| **C** | Il **tipo documento** non esiste — ma il buco non è dove il §5 lo colloca: la macchina di numerazione c'è tutta, manca l'**asse** che dice «questo è un accredito» | 🔴 | `tipi_doc_fiscale`, e la sua semantica **aperta per decisione** |
| **D** | La **ri-consegna dopo la NC** non rifattura più: la correzione `20260817-11/-12` ha chiuso la porta che la riga 9 di luglio usava | 🔴 | `fn_list_ddt_da_pushare`, `vw_partite_merce` |
| **E** | L'**idempotenza** non si ottiene dal conto: fra il verbo e l'emissione c'è una finestra in cui la coda mostra ancora la riga | 🟠 | il verbo, la coda |
| **F** | N-1 «il valore con cui è stata fatturata»: la fonte **non è** la riga di fattura, ed è **più precisa** di quanto il §8.3 sperasse | 🟠 | `attivita_fatturabili.prezzo_unitario` |
| **G** | Il legame `fatture_rettifiche` **non è scrivibile dalla madre**: al momento del verbo la fattura di accredito non esiste ancora | 🟠 | pipeline, non madre |
| **H** | Il verbo si esercita **da una lista**: le capability per riga sono vietate dal progetto | 🟡 | coda accrediti |
| **I** | La riclassificazione del Backlog cambia **il conteggio di un tab** a colpo d'occhio | 🟡 | `motivi_fermo`, FE |

### 12.1 ✅ La base non si tocca — verificato riga per riga

`vw_af_merce_per_riga` (S1) estrae così:

```sql
corsia   = split_part(segment_key, ':', 1)              -- 'ORD' | 'DDT'
riga_id  = substring(segment_key, ':R:([0-9]+)')::bigint
kit_key  = split_part(segment_key, '#CMP:', 1)
WHERE corsia = ANY(ARRAY['ORD','DDT']) AND segment_key ~ ':R:[0-9]+'
GROUP BY corsia, riga_id, tipo_movimento
```

Un segmento di rettifica `DDT:<uid>:R:<id>#RET:1` attraversa tutte e cinque le
espressioni **con il risultato giusto**: corsia `DDT`, riga_id `<id>`,
`e_componente` falso, e finisce in un gruppo `tipo_movimento = 'RETTIFICA'`
già separato da quello `NORMALE`.

⭐ **Ne discende che NC-2 costa ancora meno di quanto il cantiere 1 stimasse**:
la base espone già la rettifica come **una riga a sé**, e il consumatore non
deve «cambiare un `WHERE`» — deve **aggiungere un `LEFT JOIN` e un meno**.
La frase nel commento della vista — *«il filtro NORMALE resta nei consumatori,
così la nota di credito entrerà cambiando un WHERE e non questa base»* — era
una promessa, ed è mantenuta.

### 12.2 🔴 Rilievo A — la rettifica va sulla partita, non sulla corsia

Il §4 della PARTE I dice *«un'attività di rettifica legata alla stessa
partita»*. Sembra ovvio; non lo è, perché **la merce può essere stata fatturata
da due corsie diverse**, e la partita le tiene separate apposta:

```text
vw_partite_merce.fatturato_merce      ← corsia DDT, join diretto sulla riga di DDT
vw_partite_merce.fatturato_da_ordine  ← corsia ORD, quota ALLOCATA alla riga di DDT
vw_partite_merce.fatturato            = la somma delle due
```

La seconda non è un join: è un'**allocazione greedy** dentro la CTE `alloc`:

```sql
GREATEST(0, LEAST(consegnato,
    COALESCE(fo.quantita,0)
  - sum(consegnato) OVER (PARTITION BY ordine_riga_id
                          ORDER BY ddt_data, ddt_riga_id
                          ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING)))
```

Cioè: il fatturato della **riga d'ordine** viene versato nelle spedizioni in
ordine di data, la più vecchia per prima, fino a capienza.

🔴 **Ne discende la trappola.** Se la rettifica sottraesse dal *serbatoio*
d'ordine — cioè se `fo.quantita` diventasse `NORMALE − RETTIFICA` — il serbatoio
si abbasserebbe e la greedy toglierebbe la capienza all'**ultima** spedizione,
non a quella da cui la merce è tornata.

```text
Ordine riga 100, fatturato sulla corsia ORD per 10.
  DDT₁ (1 marzo)  consegnato 6  →  fatturato_da_ordine 6
  DDT₂ (5 marzo)  consegnato 4  →  fatturato_da_ordine 4

Reso di 4 pezzi DA DDT₁ → accredito 4.

Se la rettifica abbassa il serbatoio a 6:
  DDT₁ → fatturato_da_ordine 6   (invariato, la greedy lo serve per primo)
  DDT₂ → fatturato_da_ordine 0   ← l'accredito è finito sulla spedizione SBAGLIATA
```

Il totale tornerebbe giusto e **nessun test di parità se ne accorgerebbe**: è
la ripartizione a essere falsa, ed è esattamente il difetto che il cantiere 1
aveva corretto nella direzione opposta (§17.4: *«il greedy d'ordine non sapeva
da quale spedizione la merce fosse tornata; la partita lo sa»*).

✅ **La soluzione è già implicita nel modello: la rettifica porta SEMPRE il
segmento della partita, cioè quello del DDT** — anche quando a fatturare è
stata la corsia ORD. Allora:

```text
fatturato = fatturato_merce + fatturato_da_ordine − rettificato_su_QUESTA_partita
```

Il serbatoio d'ordine resta intatto, la greedy non si muove, e l'accredito si
scarica sulla riga di merce da cui la merce è tornata. **Una sola sottrazione,
nel posto giusto.**

⚠️ **E porta con sé un vincolo sulla commessa.** `uq_commesse_attivita_commessa_segment`
è `(commessa_id, segment_key)`: la rettifica ha bisogno di **una** commessa. La
scelta naturale non è «la commessa del DDT» (che per una partita di corsia ORD
può non esistere): è **la commessa dell'attività che ha fatturato quella
merce**, raggiungibile da `attivita_fatturabili.commessa_id`. È la stessa
commessa in cui il cerchio deve chiudersi, e il §12.6 mostra che quel legame
serve comunque per altri quattro motivi.

### 12.3 🔴 Rilievo B — dove vive il segno

> 🔴 **CORREZIONE (2026-08-18), dopo l'obiezione di Tid.** La stesura originale
> di questa sezione raccomandava la **quantità positiva** contando il costo
> della quantità negativa su cinque macchine a valle. **Quel costo è già
> pagato**: la catena del denaro gestisce un documento negativo end-to-end, e lo
> dichiara nei commenti. La raccomandazione è ribaltata; la tabella dei costi
> qui sotto è stata rifatta sui fatti verificati.

Il §4 della PARTE I dice *«quantità negativa»*. È **una** delle due strade.

|  | (a) quantità **negativa** ⭐ | (b) quantità **positiva**, `tipo_movimento` che sottrae |
| --- | --- | --- |
| `vw_partite_merce` | somma e basta | un `LEFT JOIN` e un meno |
| `fatture_righe.qta` | negativa — **nessun CHECK di segno** (verificato) | positiva |
| totali di testata, riepiloghi IVA | **nessun CHECK di segno** (verificato) | invariati |
| `fn_genera_scadenze_fattura` | ✅ **ramo già scritto**: totale < 0 → *nessuna rata* + log non critico *«saldo a favore del cliente»* (D-D caso 3) | invariata |
| `fn_assign_numero_fattura` | ✅ **guard già scritti nei due versi**: `> 0` esige le rate, `<= 0` esige che NON ci siano | invariata |
| contabilità / pagamenti | il segno si propaga da sé | ⚠️ **ogni consumatore deve tradurre** `positivo + RETTIFICA` → negativo |
| FatturaPA | ⚠️ un `abs()` nel builder XML, **al confine** | ✅ già nella forma legale |

🔴 **L'obiezione di Tid, che ribalta la scelta.** *«Con l'etichetta accade lo
stesso, perché quello è un numero negativo a tutti gli effetti»* — ed è esatto:
la strada (b) **non toglie** il lavoro a valle, lo **sposta e lo moltiplica**.
Con (b) ogni consumatore che somma degli importi deve sapere che una riga
`RETTIFICA` va sottratta; chi non lo sa calcola il segno sbagliato **in
silenzio**. È la traduzione ripetuta in più sedi che il cantiere 1 vieta
esplicitamente (BE-2: *«il verso del saldo si traduce una volta sola»*). Con (a)
il segno sta nel numero e nessuno deve saperlo.

✅ **E il costo di (a) risulta già pagato, verificato riga per riga.** I due
guard di `fn_assign_numero_fattura`:

```sql
-- 3) Documento da incassare: il piano rate deve esserci e quadrare.
IF v_tot_pagare > 0 AND v_n_rate = 0 THEN … 'piano rate assente'

-- 4) D-D allo specchio: un documento NON POSITIVO non si rateizza.
IF v_tot_pagare <= 0 AND v_n_rate > 0 THEN … 'presenti N rate su un totale non positivo'
```

e il ramo di `fn_genera_scadenze_fattura`:

```sql
-- D-D caso 3: saldo a favore del cliente. Nessuna rata (il CHECK vieta
-- importi negativi) ma una nota NON critica: a volte e' corretto, a volte
-- e' un fondo configurato male, e la differenza la vede una persona.
IF v_base < 0 THEN … log 'Totale a pagare negativo: nessun piano rate generato'
```

⭐ **I predicati sono scritti `> 0` / `<= 0`, non «assumo positivo»**: il
documento a saldo negativo non è un caso che qualcuno dovrà insegnare alla
catena — è un caso che la catena **contempla già**. L'unico CHECK di segno
dell'intera catena è `chk_fatture_scadenze_importo_pos`, e **non viene mai
raggiunto**, perché su un totale negativo le rate non si generano affatto.

⭐ **E il precedente del progetto è (a), esplicito**: il brief porta oneri §3-T3
lascia i valori negativi ammessi in catena come *«predisposizione deliberata»*,
nominando **questa slice** come quella che ne deciderà il segno. Non era una
svista: era un posto tenuto.

⭐⭐ **E c'è una macchina che il negativo non lo sopporta soltanto: lo LEGGE.**
Il guard di corrispondenza di `fatture_fondi_fattura_source` impone che
l'`importo` del fondo abbia **lo stesso segno del `totale_a_pagare`** della
fattura sorgente — è così che il fondo distingue un debito riportato avanti da un
credito riportato avanti. Con la strada (b) quella macchina avrebbe letto un
totale **positivo** su una nota di credito e avrebbe portato avanti **un debito
al posto di un credito**: in silenzio, sui soldi, su un documento già numerato.
Dettaglio e prova nel §12.4-bis.7.

**Cosa resta di (b), e non si butta.** `tipo_movimento = 'RETTIFICA'` **serve
ancora**, ma non per fare il conto: serve a **dire cos'è quella riga** — audit,
lettura, e il filtro che tiene gli oneri fuori dalla merce. Il numero porta il
valore, il cartellino porta l'intento.

⚠️ **Due conseguenze di (a) da mettere agli atti** (nessuna delle due è lavoro
di questo cantiere, entrambe vanno **scritte** o diventano sorprese):

1. **FatturaPA**: TD04 si trasmette con importi **positivi** → `abs()` nel
   builder XML, che oggi non esiste. È il posto giusto — il confine in cui si
   traduce dal formato interno a quello legale — e dà un invariante
   controllabile: `TipoDocumento = TD04 ⟺ totale_doc < 0`.
2. **La NC non genera scadenze** → il credito **non compare nella
   riconciliazione incassi**. Oggi il sistema lo dichiara con un log
   («saldo a favore del cliente»), quindi non è un silenzio. Se il credito deve
   essere compensabile con una fattura, è materia del **cantiere incassi**
   ([brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md)),
   e va portata lì come richiesta, non risolta qui.

⚠️ **L'accoppiamento con il §12.4 resta, ma è più debole di quanto scritto
prima.** Con (b) una riga di rettifica finita nella fattura sbagliata si
**sommerebbe** — danno aritmetico. Con (a) si sommerebbe **col segno giusto**:
produrrebbe una fattura al netto, sbagliata **fiscalmente** ma non
aritmeticamente. La separazione del documento resta obbligatoria; il motivo
diventa fiscale invece che di calcolo.

### 12.4 🔴 Rilievo C — il tipo documento: il buco è reale, la diagnosi va spostata

Il §5 dice *«non esiste un tipo nota di credito, né un registro dedicato»*.
Vero. Ma la conclusione che ne trae — *«serve un tipo documento distinto e va
deciso come si numera»* — sottostima una cosa e ne sopravvaluta un'altra.

**Sopravvalutata: la numerazione.** La macchina c'è **tutta**, ed è già
multi-serie e multi-registro:

```text
config.tipi_doc_fiscale            →  vendite.tipi_doc_fiscale_registri  →  registri_fatturazione
vendite.fn_get_registro_id(tipo_doc, utility, emittente)   ← fallback a quattro livelli
vendite.fn_get_next_progressivo(registro, data, serie)     ← advisory lock a 2 arg, table-based
uq_fatture_numero (registro_id, anno, COALESCE(serie,''), numero)
```

E soprattutto: **`vendite.fn_build_fattura_key` contiene già
`tipo_doc_fiscale_id`**, e `fn_get_or_create_fattura_header` confronta tutti e
nove gli elementi della chiave. Ne discende che *un'attività con un tipo
documento diverso finisce automaticamente su una testata diversa, con un
registro diverso e una numerazione diversa* — **senza scrivere una riga di
codice**. Lo stesso vale a monte: `fn_select_attivita_fatturabili` filtra
`a.tipo_doc_fiscale_id = p_tipo_doc_fiscale_id`, e
`fatturazione_lotti.tipo_doc_fiscale_id` è NOT NULL. **Il lotto è già
separato per tipo documento.**

🔴 **Sottovalutata: quale asse.** Mettere `NOTA_CREDITO` dentro
`config.tipi_doc_fiscale` **collide con una decisione di dominio già presa**
(2026-06-19, registrata): la semantica di quel campo è **aperta e configurabile
per azienda** — front-office/back-office è *«solo un esempio d'uso, non una
regola vincolante da codificare»*.

Ne discende, concretamente:

```text
oggi:      tipo_doc = il CANALE          →  2 valori,  2 registri
con NC lì: tipo_doc = canale × natura    →  4 valori,  4 registri
           e un'azienda che usa il tipo_doc per altro (area, brand, mandante)
           moltiplica il SUO asse per due
```

Sono **due assi ortogonali**: il canale è una scelta dell'azienda, la natura
fiscale del documento **non lo è** — è la legge, e domani è il `TipoDocumento`
della FatturaPA (`TD01` contro `TD04`).

⚠️ **E la FatturaPA non è un domani lontano che si può ignorare**:
`fn_prepare_sdi_payload` oggi **non porta il tipo documento** (verificato: la
sua `RETURNS TABLE` non ha il campo), e il builder XML non esiste ancora. Quando
esisterà, dovrà leggere la natura **dalla fattura**. Ne discende un requisito
che vale qualunque strada si scelga: **la natura deve essere leggibile da
`vendite.fatture`**, non solo dall'attività che l'ha generata.

**Le tre strade**, con il costo vero di ciascuna → decisione **D-NC-3**.

| | Come | Costo | Rischio |
| --- | --- | --- | --- |
| **C1** | terza riga in `tipi_doc_fiscale` (`NOTA_CREDITO`) + registro + mapping | 3 righe di CSV, zero codice | 🔴 collassa i due assi: chi usa il tipo_doc per altro paga il prodotto cartesiano |
| **C2** ⭐ | asse nuovo: vocabolario `config.nature_doc_fiscale` (`FATTURA`/`NOTA_CREDITO`/…) + colonna su `fatture`, `commesse_attivita`, `attivita_fatturabili`, e l'elemento in `fn_build_fattura_key` | 1 tabella, 3 colonne, 1 fn toccata, il mapping registro da estendere | il mapping registro diventa `(tipo_doc × natura)`: va deciso se il registro è per natura o condiviso con `serie` diversa |
| **C3** | stesso registro, **`serie`** dedicata (la colonna `fatture.serie` esiste e `fn_get_next_progressivo` la usa già come dimensione) | minimo | 🔴 `serie` **non è** nella chiave di `fn_get_or_create_fattura_header`: NC e fattura finirebbero sulla **stessa testata**. E la serie è una scelta di numerazione, non una dichiarazione di natura: nessun consumatore può leggerla come tale |

**Raccomandazione: C2**, con il registro **condiviso** e la `serie` distinta —
cioè C2 che *usa* il meccanismo di C3 per la numerazione invece di duplicare i
registri. Motivo: la natura è un asse suo e va nominata come tale (è ciò che
leggerà la FatturaPA); il registro invece è una scelta **fiscale dell'azienda**
— c'è chi numera le NC in una serie a parte dentro il registro vendite e chi
tiene un sezionale separato — e quella scelta deve restare **configurabile**,
non decisa qui. ⚠️ La domanda «registro proprio o serie propria?» è di **Tid**,
ed è la sola parte di questo rilievo che il DB non può decidere da sé.

### 12.4-bis 🔬 L'asse «natura»: come si integra con registro, numerazione e fattura elettronica

> Analisi chiesta da Tid il 2026-08-18, prima di scrivere. Letta dalle
> definizioni vive, dalla [guida fatturazione](../../guide/fatturazione.md) e
> dalla documentazione concettuale di `fatture`, `registri_fatturazione`,
> `tipi_doc_fiscale_registri` e `fatture_sdi`.

#### 12.4-bis.1 ⭐ L'asse non è nuovo: era nel disegno, ed è stato occupato da altro

Prima di aggiungere una colonna vale la pena leggere cosa dice di sé la tabella.
La documentazione concettuale di `vendite.fatture` (review 24-01-2026):

> **Tipo documento**: `tipo_doc_fiscale_id` → `config.tipi_doc_fiscale`
> (es.: **fattura, nota credito, parcella**, XML tipo-doc neutrali).

e, fra le migliorie che si dava da sé:

> **Gestione annulli**: … per **note di credito** usare `tipo_doc_fiscale`
> adeguato, **con legame alla fattura originaria** (campo di riferimento in
> righe/testata).

Il seed, però, contiene `FRONTOFFICE` / `BACKOFFICE` — cioè i **canali**. E la
decisione di dominio del 2026-06-19 ha registrato **l'uso**, non l'intento:
*«front/back office è solo un esempio d'uso, ogni azienda può usarlo per scopi
diversi; non inferire mai il valore da logica cablata»*.

⭐ **Ne discende una lettura che cambia il tono della decisione**: la colonna è
**nata** come asse della natura fiscale ed è **finita** a fare l'asse del
canale. Non ci sono due verità in conflitto — c'è **una colonna sola per due
assi**, e chi ha scritto la doc di `fatture` a gennaio e chi ha deciso a giugno
stavano guardando due cose diverse con lo stesso nome.

**Aggiungere `natura` non inventa un asse: separa due assi che erano fusi dal
primo giorno**, e lascia a ciascuno ciò che davvero contiene. La riga del
manuale — *«per le note di credito usare un tipo adeguato con legame alla
fattura originaria»* — resta valida parola per parola: cambia solo **quale**
colonna è «il tipo adeguato».

⚠️ **Conseguenza operativa**: la doc concettuale di `fatture` va corretta nella
stessa slice (elenca «fattura, nota credito, parcella» sotto `tipi_doc_fiscale`,
che oggi non li contiene e non li conterrà). È doc **manuale**, quindi si edita.

#### 12.4-bis.2 La catena della numerazione, per intero

Questo è ciò che governa il numero di un documento, dall'inizio alla fine:

```text
  tipo_doc_fiscale ──┐
                     ├─► vendite.tipi_doc_fiscale_registri ──► registro
        (natura?) ───┘         UNIQUE (tipo_doc, registro)         │
                                                                   ├─ serie_default
  fn_get_registro_id(tipo_doc, utility, emittente)  ───────────────┤  reset_policy
                     ▲                                             │
                     └─ chiamata da fn_build_fattura_key           │
                                                                   ▼
  fatture.registro_id ─────────────────────────────────────────────┘
  fatture.serie       = COALESCE(f.serie, r.serie_default, '')     ← fn_assign_numero_fattura
  fn_get_next_progressivo(registro, data, serie)
        └─► registri_fatturazione_progressivi  UNIQUE (registro, anno, mese, serie)
  uq_fatture_numero  (registro_id, anno, COALESCE(serie,''), numero)  WHERE numero IS NOT NULL
```

⭐ **Due osservazioni che semplificano tutto.**

1. **`serie` è già una dimensione di numerazione a tutti gli effetti**: entra nel
   progressivo, entra nell'unicità, ed è già `COALESCE`-ata sul default del
   registro. Non va costruita: va **valorizzata**.
2. **`fatture.serie` non viene mai scritto dalla pipeline.**
   `fn_get_or_create_fattura_header` non nomina la colonna nella sua `INSERT` →
   resta `NULL` → `fn_assign_numero_fattura` cade sul `serie_default` del
   registro. ⚠️ **Ne discende che, se la NC deve avere una serie propria,
   scriverla è un lavoro da fare — non un comportamento da configurare.**

#### 12.4-bis.3 ✅ Dove far entrare la natura: nella tabella di mapping, non in una gerarchia nuova

`vendite.tipi_doc_fiscale_registri` **è già** la sede della domanda *«dato un
tipo di documento, su quale registro va?»*. La natura è la seconda metà della
stessa domanda.

```text
OGGI   (tipo_doc)          → registro
DOMANI (tipo_doc, natura)  → (registro, serie)
```

Concretamente:

* colonna `natura_doc_id` su `tipi_doc_fiscale_registri` (NOT NULL, default
  `FATTURA`) e colonna `serie` nullable (override del `serie_default` del
  registro);
* la `UNIQUE` passa da `(tipo_doc_fiscale_id, registro_id)` a
  `(tipo_doc_fiscale_id, natura_doc_id, registro_id)`;
* `fn_get_registro_id` guadagna la natura e restituisce **due** valori
  (registro **e** serie).

⭐ **E qui succede la cosa migliore di tutta questa analisi: D-NC-3b si
dissolve.** *«Registro proprio o serie dedicata?»* smette di essere una
decisione di modello e diventa **una riga di seed**:

| Se il seed dice… | Effetto |
| --- | --- |
| stesso `registro_id`, `serie = 'NC'` | le NC numerano in una serie a parte **dentro** il registro vendite |
| `registro_id` diverso | le NC hanno un **sezionale proprio**, numerazione del tutto separata |

Entrambe funzionano **senza codice diverso**, ed entrambe restano cambiabili
dopo. È esattamente la forma che il progetto usa per le scelte che appartengono
all'azienda e non allo sviluppatore — `tipi_reso.riapre_residuo`,
`causali_trasporto.fatturabile`: *«nessun IF hardcoded, si legge il flag»*.

⚠️ **Il lavoro che resta obbligatorio**, qualunque cosa dica il seed:

1. `fn_build_fattura_key` porta **la natura e la serie** (10º e 11º elemento);
2. `fn_get_or_create_fattura_header` li confronta nel `WHERE` **e li scrive
   nella `INSERT`**. Il commento vivo della funzione avverte già del pericolo:
   *«se la chiave separa e il lookup no, le due metà si annullano e le attività
   tornano nella stessa fattura»*. Con `serie` c'è la trappola gemella: se la
   chiave la calcola e la `INSERT` non la scrive, la numerazione la ignora e le
   NC finiscono nella serie delle fatture — **con numeri validi**.

#### 12.4-bis.4 🔴 Il difetto latente trovato qui: i registri per emittente sono IRRAGGIUNGIBILI

Analizzando la catena è emerso un difetto che non riguarda la NC ma che la NC
erediterebbe.

`fn_get_registro_id` accetta tre parametri e ha un fallback a quattro livelli
(tipo+utility+emittente → tipo+utility → tipo+emittente → tipo). Ma il suo
**unico chiamante** la invoca con uno solo:

```sql
-- fn_build_fattura_key
v_registro_id := vendite.fn_get_registro_id(v_tipo_doc_fiscale_id);
```

Con `p_utility_id` e `p_emittente_soggetto_ruolo_id` a `NULL`, il `WHERE` della
funzione si riduce così:

```sql
AND (r.utility_id IS NULL OR r.utility_id = p_utility_id)          -- = NULL  →  NULL, mai vero
AND (r.emittente_soggetto_ruolo_id IS NULL OR r.emittente_… = p_…) -- idem
```

🔴 **Ne discende che dalla pipeline sono raggiungibili SOLO i registri con
`utility_id` NULL **e** `emittente_soggetto_ruolo_id` NULL.** Un registro
intestato a un emittente non verrebbe scelto: verrebbe **escluso dalla
selezione**, e se fosse l'unico per quel tipo documento la funzione
solleverebbe `E_CONFIG_MANCANTE`.

⚠️ **E il modello promette il contrario.** La doc concettuale di
`registri_fatturazione`:

> La FK su `emittente_soggetto_ruolo_id` è **coerente** con un modello
> multi-emittente: ogni registro appartiene a un emittente fiscale specifico. In
> presenza di più aziende abilitate, **la separazione dei registri evita
> collisioni di numerazione**.

**Oggi non si vede** perché entrambi i registri in seed hanno utility ed
emittente a `NULL`: il livello 4 del fallback è l'unico esercitato. È la
distinzione del preambolo — zero occorrenze, e **nulla lo impedisce**.

⭐ **Perché è di questo cantiere e non di un altro.** La NC è il primo documento
che pone la domanda *«su quale registro numero?»* in modo non banale, ed è
proprio il caso in cui un'azienda multi-emittente vorrebbe registri separati.
Costruire il mapping della natura sopra una risoluzione che ignora l'emittente
significa ereditare il difetto e renderlo più difficile da togliere. **Va sanato
nella stessa slice**: `fn_build_fattura_key` conosce già emittente e utility —
li ha calcolati tre righe più su — e deve solo passarli.

⚠️ Il perimetro emittente è un cantiere **attivo** (`dev/db-tid`): questo
rilievo va portato anche lì, perché è un pezzo dello stesso quadro.

#### 12.4-bis.5 La fattura elettronica

**Il vincolo di modello viene prima di tutto.** La doc di `fatture` dichiara fra
gli obiettivi:

> Tracciare **stato e tipo fiscale** senza vincoli di specifico ordinamento
> nazionale (modello neutro, estendibile).

Ne discende che il vocabolario della natura resta **neutro** — `FATTURA`,
`NOTA_CREDITO`, `NOTA_DEBITO` — e che il codice italiano (`TD01`, `TD04`, …)
**non diventa una colonna**: è un parametro del **profilo nazionale**, e vive nel
`meta` della riga di natura (`{"sdi_tipo_documento": "TD04"}`), sul criterio già
usato per i parametri locali a un handler. Se un domani servisse un secondo
profilo fiscale, diventerà una tabella di mapping — non prima.

**Cosa va toccato lato SDI:**

| Oggetto | Cosa manca | Nota |
| --- | --- | --- |
| `fn_prepare_sdi_payload` | la `RETURNS TABLE` **non porta il tipo documento** (verificato: 11 colonne, nessuna lo dice) | ⚠️ `CREATE OR REPLACE` **non cambia** una `RETURNS TABLE`: serve `DROP` + `CREATE`, con numerazione successiva |
| `totale_a_pagare` nel payload | sarà **negativo** per la NC (D-NC-2) | il builder XML fa `abs()`, ed è il posto giusto: il confine fra formato interno e formato legale |
| `codice_documento` | è `anno ‖ serie ‖ numero` | ⭐ con la serie dedicata la NC si distingue **già** nel codice, senza aggiungere nulla |
| `vendite.fatture_sdi` | nulla | la testata dei tentativi è agnostica al tipo di documento: non va toccata |

⭐ **E ne esce un invariante controllabile**, che è ciò che rende sicura la
scelta del segno (D-NC-2):

```text
natura = NOTA_CREDITO   ⟺   totale_a_pagare <= 0   ⟺   TipoDocumento = TD04
```

#### 12.4-bis.6 ✅ Il guard che numera guadagna una settima condizione

`fn_assign_numero_fattura` ha sei condizioni di coerenza (guard **D-K**), e la
quarta è già a un passo da noi:

> *4) D-D allo specchio: un documento **non positivo** non si rateizza.*

Con la natura si può chiudere il cerchio con una settima:

```text
7)  natura = NOTA_CREDITO  e  totale_a_pagare > 0     →  incoerente
    natura = FATTURA       e  totale_a_pagare < 0     →  incoerente
```

⭐ **Costa due righe e trasforma «il segno porta il significato» da convenzione
a invariante verificato**, controllato *prima* che il progressivo venga
consumato — cioè prima del punto in cui la guida dice che l'errore diventa
irreparabile: *«un numero fiscale valido su un documento invalido… si ripara
solo con una nota di variazione»*.

#### 12.4-bis.7 ✅ Il fondo fattura non «mangia» niente — è il modo in cui l'accredito si salda

> 🔴 **CORREZIONE (Tid, 2026-08-18).** La prima stesura di questa sezione
> sosteneva che una nota di credito «di minimo» sarebbe stata **assorbita dal
> fondo invece di essere emessa**. È falso, e la documentazione del fondo lo
> dice a chiare lettere. Tid: *«il minimo non si mangia nulla, la nota di credito
> deve comunque essere emessa; solo che, se attivo, sposta la parte del rimborso
> nella fattura successiva»*.

**La prova sta nell'inviluppo della funzione.** `fn_fondo_fattura_proponibile`
non guarda nemmeno un documento che non sia già emesso:

```sql
FROM vendite.fatture f
JOIN config.stati_doc_fiscale sd ON sd.id = f.stato_doc_fiscale_id
                                AND sd.codice_interno = 'DEFINITIVA'
WHERE f.id = p_fattura_sorgente_id
  AND f.minimo IS TRUE
  AND f.utility_id IS NOT NULL
```

`DEFINITIVA` significa **numerata**: il documento è nato, ha preso il suo numero
dal registro, ed è in mano al cliente. Il fondo si crea **dopo**, e da lì in poi
non tocca il documento — sposta soltanto **dove si regola il conto**.

⭐ **Ne discende che `minimo` non è un filtro sull'emissione: è una scelta di
regolamento.** Il documento si emette sempre; l'importo, invece di essere
incassato o rimborsato, viaggia sulla fattura successiva. E la doc di
`fatture_fondi_fattura_source` lo dice per il caso che ci interessa:

> La banda **contiene lo zero**: ⭐ un `importo` **negativo** è quindi legittimo —
> è **un credito riportato avanti, non un difetto**.

#### ⭐ E questo chiude, in gran parte, il buco dichiarato al §12.3

Con D-NC-2 avevo messo agli atti che *«la NC non genera scadenze, quindi il
credito non compare nella riconciliazione»*. La correzione mostra che per una
parte dei casi **non è un buco: è il progetto**.

```text
NC dentro la banda   →  minimo = true   →  fondo NEGATIVO  →  si sottrae dal
                                                              totale_a_pagare
                                                              della fattura dopo
                                                              ✅ nessuna rata serve

NC fuori dalla banda →  minimo = false  →  nessun fondo automatico, nessuna rata
                                        →  il saldo è un RIMBORSO, e la strada
                                           esiste già: fondo `origine = MANUALE`,
                                           motivo obbligatorio, che per
                                           dichiarazione della doc «arriva dal
                                           processo rimborsi di `pagamenti`»
```

⚠️ **Il residuo, ora preciso**: una nota di credito **grande** resta senza rata e
senza fondo automatico, quindi senza un posto che dica *«questo credito va
rimborsato»*. Non è un difetto introdotto da questa slice — è il perimetro del
**processo rimborsi**, che il modello nomina e che vive in `pagamenti`. Va
portato lì come richiesta (§17), non risolto qui.

#### 🔴 E c'è un argomento che questa correzione regala a D-NC-2

Il guard di corrispondenza sulla source dice che l'`importo` del fondo deve avere
**lo stesso segno del `totale_a_pagare`** della fattura sorgente, e non superarlo
in valore assoluto.

⭐ **Quindi il fondo fattura è una macchina che legge già il segno del totale per
decidere se sta portando avanti un debito o un credito.** Con la strada (b) del
§12.3 — quantità positive e l'intento in un'etichetta — quella macchina avrebbe
letto un totale **positivo** su una nota di credito, e avrebbe riportato avanti
**un debito invece di un credito**: in silenzio, sui soldi, su un documento già
numerato.

**È la conferma più forte che (a) fosse la scelta giusta**, e non l'avevo vista:
non è solo che le macchine a valle *sopportano* il negativo — è che almeno una di
loro **lo usa come informazione**.

⚠️ **Due cose ereditate, da sapere e non da risolvere qui:**

* il fondo esige `utility_id IS NOT NULL`: una NC su un cliente senza utility
  attribuita è **irraggiungibile** dal giro dei fondi. Non è un caso nuovo — la
  doc lo dichiara ed è il motivo per cui esiste `vw_fondi_fattura_da_decidere` —
  ma la NC lo eredita;
* il cantiere **fondo fattura** ha *«piano scritto, niente applicato»*: se la
  banda cambia forma lì, questa lettura va riverificata.

#### 12.4-bis.8 Il lotto: la natura è del documento, non del lotto

`fatturazione_lotti.tipo_doc_fiscale_id` è **NOT NULL** e
`fn_select_attivita_fatturabili` filtra su quello. La domanda è se la natura
debba diventare una **seconda dimensione del lotto**.

⭐ **Raccomandazione: no.** Con la natura dentro la chiave documento, un lotto
solo produce **due documenti** — la fattura e la nota di credito — e la
separazione avviene dove deve avvenire: sulla testata. Aggiungere una dimensione
al lotto raddoppierebbe i giri senza separare nulla di più.

⚠️ **Ma va detto, perché cambia un'assunzione**: da quel momento **un lotto può
contenere documenti di natura diversa**. Il drawer del lotto, il conteggio delle
fatture e la stampa massiva non devono dare per scontato *«sono tutte
fatture»*. E il verbo «numera» del lotto numererà entrambe, ciascuna sul suo
registro/serie: è corretto, ed è bene che qualcuno lo sappia prima di vederlo.

#### 12.4-bis.9 La natura non si cambia dopo

Un documento non può cambiare natura: sarebbe trasformare una fattura in una
nota di credito a numero già assegnato. Il presidio esiste già ed è un
building-block da riusare — `script.trgfn_lock_columns`, lo stesso che protegge
`codice_interno` su `config.tipi_doc_fiscale` e su
`vendite.tipi_doc_fiscale_registri`. Stesso spirito di
`trgfn_canale_origine_immutable` su `fatture`.

#### 12.4-bis.10 Il quadro degli impatti, in una tabella

| Oggetto | Cosa cambia | Rischio se si dimentica |
| --- | --- | --- |
| `config.nature_doc_fiscale` (nuova) | vocabolario neutro + `meta.sdi_tipo_documento` | — |
| `fatture`, `commesse_attivita`, `attivita_fatturabili` | colonna `natura_doc_id` NOT NULL default `FATTURA` | — |
| `tipi_doc_fiscale_registri` | `+ natura_doc_id`, `+ serie`, UNIQUE a tre colonne | il registro/serie della NC non si risolve |
| `fn_get_registro_id` | natura in ingresso, **registro + serie** in uscita 🔴 e **emittente/utility davvero usati** | 🔴 registri per emittente irraggiungibili (§12.4-bis.4) |
| `fn_build_fattura_key` | natura e serie nella chiave; passa emittente e utility | NC e fattura sulla **stessa testata** |
| `fn_get_or_create_fattura_header` | li confronta nel `WHERE` **e scrive `serie` nell'`INSERT`** | 🔴 NC numerata nella **serie delle fatture** |
| `fn_assign_numero_fattura` | settima condizione D-K | il segno resta una convenzione non verificata |
| `fn_ricalcola_totali_fattura` | **nulla** — `minimo` vale anche per le NC ed è corretto così (§12.4-bis.7) | — |
| `fn_prepare_sdi_payload` | porta la natura — **`DROP` + `CREATE`** | il builder XML non sa emettere TD04 |
| `fn_upsert_commessa_attivita`, `fn_emit_attivita_…` | propagano la natura | la natura non arriva in fattura |
| doc concettuale `fatture` | corregge «tipi_doc_fiscale = fattura/nota credito/parcella» | la doc continua a indicare la colonna sbagliata |

⚠️ **Reperto minore, fuori perimetro ma da segnalare**: la doc concettuale di
`fatture` cita un trigger `trg_fatture_a10_upd_protect_num` *«impedisce
modifiche non consentite ai campi di numerazione»* che **nella tabella viva non
esiste**. I campi di numerazione oggi sono presidiati solo da
`trg_fatture_a11_numerata_non_annulabile` e dai guard di stato.

### 12.5 🔴 Rilievo D — la ri-consegna dopo la NC non rifattura più

È il rilievo che nessuno dei due cantieri precedenti poteva vedere, perché
richiede la NC per manifestarsi. **Ed è una promessa scritta che oggi non
regge.**

Il brief di luglio, §3d, dichiara la riga 9 della sua tabella:

> *«**se** la nota di credito abbassa i fatturati, allora la differenza torna
> positiva e la ri-consegna rifattura da sé (riga 9), la scelta umana del §5
> funziona senza codice dedicato, **zero rework**»*

E indica dove: *«i 3 pezzi in più non possono andare sull'attività esistente…
vanno sul segmento del **DDT nuovo**, che è un segmento vergine»*.

🔴 **Quel segmento vergine non esiste più.** La correzione `20260817-11/-12` —
scritta per chiudere il bug 1a, e giustamente — ha stabilito che *«una riga di
RI-CONSEGNA **non è** una partita nuova»*: la riga porta `e_riconsegna = true`,
`differenza` **NULL**, `stato = 'RICONSEGNA'`, e i suoi pezzi rientrano nel
`consegnato` della partita d'**origine**.

Facciamo il conto, sulla partita d'origine, con la vista di oggi:

```text
t0   consegnato 10 · reso 3 · tenuti 7 · fatturato 10   →  differenza −3   DA_ACCREDITARE
NC   fatturato 7                                        →  differenza  0   PAREGGIATA        ✅
ri-consegna emessa di 3:
     consegnato 13 · reso 3 · tenuti 10 · fatturato 7   →  differenza +3   DA_FATTURARE      ✅
```

⭐ **L'aritmetica è perfetta**: la partita dice esattamente ciò che deve dire,
«tre pezzi in mano al cliente e non fatturati». Il problema è l'ultimo
passaggio, in `fn_list_ddt_da_pushare`:

```sql
AND script.fn_get_stato_push_segment('DDT:' || d.uid || ':R:' || dr.id) = 'LIBERA'
```

Il segmento della partita d'origine **non è LIBERA** — è `EMESSA`, perché
quella riga è già stata fatturata una volta. Quindi i 3 pezzi **non vengono
spinti**. E la riga di ri-consegna, che sarebbe il veicolo naturale, ha
`differenza` NULL ed è esclusa dal predicato `pm.differenza IS NOT NULL`.

**Ne discende che, oggi, dopo una NC facoltativa e la ri-spedizione, la merce
resta in mano al cliente non fatturata e nessuna coda lo dice.** Non è una
regressione introdotta dal cantiere 1: è la conseguenza, mai esercitata, di due
correzioni entrambe giuste che si incontrano solo qui.

⚠️ **E la cintura non si può semplicemente allentare.** `= 'LIBERA'` è ciò che
impedisce di ri-spingere una riga già fatturata: toglierla riaprirebbe il bug
1a in forma peggiore. Il commento vivo della funzione lo dice a chiare lettere,
ed è indirizzato proprio a questo cantiere.

✅ **La formulazione che riconcilia le due cose** (proposta, → **D-NC-4**):

> **Una ri-consegna è merce nuova solo per la parte che è stata accreditata.**

Cioè la riga di ri-consegna smette di avere `differenza` incondizionatamente
NULL: porta il minimo fra la quantità ri-consegnata e la **quota accreditata e
non ancora ri-fatturata** della partita d'origine; il resto continua a
confluire nel `consegnato` dell'origine come oggi. Conseguenze:

* il segmento della riga di ri-consegna è **vergine** → la cintura `= 'LIBERA'`
  resta intatta e non va toccata;
* senza NC la riga di ri-consegna resta a `differenza` NULL → il bug 1a resta
  chiuso, e il **caso D** di `test-fn-list-ddt-da-pushare-contatore-v1` — il
  test che a agosto ha fermato tutto — resta verde;
* il cliente riceve la merce con DDT₂ e viene fatturato **per DDT₂**, che è
  anche la lettura documentalmente corretta;
* ⚠️ e la partita d'origine **non deve** contare due volte: se la quota è
  attribuita alla ri-consegna, va sottratta dal `consegnato` dell'origine —
  altrimenti si rifattura due volte, che è il difetto di partenza. **Questa è
  la parte delicata del cantiere**, e il pgTAP deve costruirla a mano perché
  sui dati non esiste (zero righe `RETTIFICA` al 2026-08-17).

⚠️ **Alternativa da valutare e scartare esplicitamente**: lasciare che la
partita d'origine venga ri-spinta con un segmento di rifatturazione
(`…#RIF:<n>`). Funziona, ma trasforma il push da «una volta per segmento» a
«n volte per partita», e rende `fn_get_stato_push_segment` — che è la **fonte
unica** del predicato *«già inviato»*, consumata anche dalle capability di
ordine e DDT — una funzione che non risponde più alla domanda per cui esiste.

### 12.5-bis ✅ D-NC-4 — la forma esatta della regola (Tid, 2026-08-18)

> Decisione: **si implementa**. Qui c'è la regola con i numeri, perché *«è merce
> nuova solo per la parte accreditata»* è una frase esatta ma non è ancora
> un'istruzione.

**Il meccanismo di oggi, in una riga.** Ogni **spedizione** (riga di DDT) ha il
suo conto. Quando si rispedisce merce resa nasce una spedizione **nuova**
(DDT₂), che oggi è marcata *«non è merce nuova»* — conto **volutamente vuoto**
(`e_riconsegna = true`, `differenza` NULL) — e i suoi pezzi rientrano nel
`consegnato` della spedizione **d'origine** (DDT₁). È la correzione
`20260817-11/-12`, ed è ciò che ha chiuso la doppia fatturazione di luglio.

#### Senza nota di credito — funziona, e non deve cambiare di una virgola

| | consegnato | reso | in mano | fatturato | esito |
| --- | --- | --- | --- | --- | --- |
| DDT₁ dopo il reso | 10 | 3 | 7 | 10 | 3 da accreditare |
| DDT₁ dopo la rispedizione | **13** | 3 | 10 | 10 | **0 — a posto** ✅ |
| DDT₂ (ri-consegna) | — | — | — | — | conto vuoto ✅ |

#### Con nota di credito — il numero è giusto, ma sta sulla riga sbagliata

| | consegnato | reso | in mano | fatturato | esito |
| --- | --- | --- | --- | --- | --- |
| DDT₁ dopo il reso | 10 | 3 | 7 | 10 | 3 da accreditare |
| DDT₁ dopo la NC | 10 | 3 | 7 | **7** | 0 — a posto ✅ |
| DDT₁ dopo la rispedizione | **13** | 3 | 10 | 7 | **3 da fatturare** — il conto è giusto |
| | | | | | 🔴 ma DDT₁ è **bloccata**: `fn_get_stato_push_segment ≠ 'LIBERA'` |
| DDT₂ | — | — | — | — | 🔴 conto vuoto: non può fatturare lei |

#### ✅ La regola

> **Quando si rispedisce, i pezzi che erano stati accreditati contano sulla
> spedizione NUOVA. Quelli non accreditati continuano a contare su quella
> vecchia.**

I pezzi accreditati **cambiano casa**:

| | consegnato | reso | in mano | fatturato | esito |
| --- | --- | --- | --- | --- | --- |
| DDT₁ *(resta ferma)* | 10 | 3 | 7 | 7 | 0 — a posto ✅ |
| DDT₂ *(prende i 3 accreditati)* | **3** | 0 | 3 | 0 | **3 da fatturare** ✅ |

DDT₂ è una spedizione **mai instradata**: `fn_get_stato_push_segment` la vede
`LIBERA` e non la blocca. Entra nel giro di fatturazione **normale**, col prezzo
della sua riga, e produce la riga in fattura. ⭐ **Nessun verbo nuovo, nessuna
seconda pipeline**: è la macchina di sempre che se ne accorge da sola.

**Le due garanzie**, entrambe per costruzione:

1. **DDT₁ non porta più quei pezzi** → non li può fatturare una seconda volta:
   il buco di luglio resta chiuso, e con esso il **caso D** di
   `test-fn-list-ddt-da-pushare-contatore-v1`;
2. **senza NC la regola è inerte** — nessun pezzo è stato accreditato, nessuno
   cambia casa, e la prima tabella resta identica a oggi.

#### Perché *«solo per la parte accreditata»* — il caso misto

Reso 5, accreditati **3**, rispediti 5:

| | consegnato | fatturato | esito |
| --- | --- | --- | --- |
| DDT₁ | 10 + **2** = 12 | 7 | i 2 **non** accreditati tornano qui → conto a 0 ✅ |
| DDT₂ | **3** | 0 | **3 da fatturare** — solo quelli accreditati ✅ |

*«Tutta la ri-consegna è merce nuova»* rifatturerebbe anche i 2 già pagati;
*«niente è merce nuova»* è il blocco di oggi. ⭐ **La quantità accreditata è
l'unica misura che divide correttamente le due parti — ed è un numero che il
sistema ha già**, perché è la somma delle rettifiche sulla partita d'origine
(§12.1: la base le espone già come riga a sé).

#### ⚠️ Cosa deve garantire l'implementazione (per il pgTAP)

* la **somma** `DDT₁.consegnato + DDT₂.consegnato` non cambia mai: i pezzi si
  spostano, non si moltiplicano — è l'invariante da asserire, prima della
  ripartizione;
* la quota che «cambia casa» è **cappata** alla quantità ri-consegnata **e** al
  già accreditato **non ancora ri-fatturato**: un secondo giro di
  reso→NC→ri-consegna non deve contare due volte lo stesso accredito;
* `stato` della riga di ri-consegna: oggi è sempre `RICONSEGNA`; con una quota
  propria diventa `DA_FATTURARE`. Il pannello del cantiere 2 lo mostra già, e la
  tavolozza FE non cambia (il valore esiste).

### 12.6 🟠 Rilievo E+F+G — l'unica colonna che risolve cinque problemi

Il §8 della PARTE I pone tre domande separate (valorizzazione, idempotenza,
legame documentale). **Hanno la stessa risposta.**

**F — da dove si legge «il valore con cui è stata fatturata».**

> 🔴 **CORREZIONE (Tid, 2026-08-18).** La prima stesura indicava come fonte
> `attivita_fatturabili.prezzo_unitario`, argomentando che è *«lo stesso
> numero»* della riga di fattura. Vero come numero, **sbagliato come regola**.
> Tid: *«deve sempre reperire i prezzi dalla fattura, non deve fare nessuna
> operazione di ricalcolo prezzo: la nota di credito non può differire da quanto
> fatturato»*.

✅ **La fonte è `vendite.fatture_righe`**, raggiunta da
`attivita_fatturabili.fattura_riga_id`:

```text
riga di reso → partita → attività fatturata → af.fattura_riga_id → fatture_righe
                                                                      │
                                          prezzo_unitario · sconto_percentuale · iva_id
```

**Perché la riga di fattura e non l'attività**, visto che il numero è lo stesso:

* **è l'invariante, non la coincidenza.** Oggi i due valori coincidono per
  costruzione — il generatore righe dichiara *«`prezzo_unitario` è unico per
  costruzione perché sta nella chiave»* — ma quella è una proprietà
  dell'implementazione corrente. *«Il prezzo è quello della fattura»* è una
  regola di dominio e regge anche se l'aggregazione cambia;
* **porta anche sconto e IVA**, che sull'attività non ci sono. Oggi
  `sconto_percentuale` non viene mai scritto dalla pipeline (verificato: la
  parola non compare nel generatore righe), quindi vale 0 — ma il giorno in cui
  ci fosse, un accredito al prezzo pieno **restituirebbe più del dovuto**;
* **è auditabile**: la rettifica può nominare la riga di fattura da cui ha preso
  il prezzo. *«Questo accredito vale 12 € perché la riga 7 della fattura
  2026/1234 valeva 12 €»* è una frase che si può verificare; *«perché
  l'attività 886 valeva 12 €»* no, non per chi guarda il documento.

⭐ **Ne discende un invariante, ed è la forma più forte che il §2 possa
prendere**:

> **Ogni riga di nota di credito ha una riga di fattura gemella: stesso
> articolo, stesso prezzo, stessa IVA, stesso sconto, quantità non superiore.**

È verificabile con una query, quindi è materia da **pgTAP** — e trasforma N-1 da
principio a cancello. ⚠️ **Nessuna operazione di ricalcolo** è ammessa lungo il
percorso: né medie, né prezzi ponderati, né riletture del listino. Se un prezzo
non si trova sulla fattura, l'accredito **non si fa** e lo dice.

#### 🔴 «Copia esatta, compresi gli sconti» — e la catena non ha dove metterlo

Precisazione di Tid (2026-08-18): *«deve essere la copia esatta, compresi gli
sconti»*. Verificato sulla catena, e c'è un buco:

```text
commesse_attivita     →  nessuna colonna sconto   (verificato: 0 occorrenze)
attivita_fatturabili  →  nessuna colonna sconto   (verificato: 0 occorrenze)
fatture_righe         →  sconto_percentuale  numeric  DEFAULT 0   ✅ c'è solo qui
```

Lo sconto **esiste solo all'arrivo**. Oggi è innocuo — la pipeline non lo scrive
mai, quindi vale 0 ovunque — ma *«copia esatta compresi gli sconti»* pretende che
un domani sia trasportabile. Due strade:

| | Come | Costo | Rischio |
| --- | --- | --- | --- |
| **α** | colonna `sconto_percentuale` su `commesse_attivita` **e** `attivita_fatturabili`, propagata dall'emit e scritta dal generatore | 2 colonne + emit + generatore, e ⚠️ **lo sconto deve entrare nella chiave di raggruppamento** del generatore, o due attività con stesso prezzo e sconti diversi finirebbero su una riga sola | tocca la catena di **tutte** le fatture per un bisogno di una sola |
| **β** ⭐ | il generatore, davanti a un'attività `RETTIFICA`, prende prezzo, sconto e IVA **dalla riga di fattura rettificata** (`af_rettificata_id → fatture_righe`) invece che dall'attività | un ramo dichiarato nel generatore, zero schema | — |

⭐ **β è anche più fedele alla richiesta**: la copia avviene **nel momento in cui
il documento si scrive, leggendo il documento che rettifica**. Con α la copia
dipende dal fatto che la catena abbia trasportato i valori senza perderli lungo
tre tabelle — cioè da una speranza, non da un vincolo.

✅ **E porta con sé una regola che semplifica tutto: le righe di rettifica NON si
aggregano.** Il generatore accorpa n attività in una riga quando condividono la
chiave; una rettifica invece **è lo specchio di UNA riga di fattura**, e
accorparne due che rettificano righe diverse produrrebbe una riga che non è
gemella di nessuna. Quindi:

> **una rettifica → una riga di nota di credito, gemella della riga di fattura
> che rettifica.**

Ne discende, come effetto e non come sforzo, che l'invariante qui sopra è vero
**per costruzione** e che una nota di credito si legge accanto alla fattura riga
per riga — compreso il caso del kit, dove le N righe della NC corrispondono alle
N righe di componente della fattura.

⚠️ **β è lavoro di BACKEND** (il generatore righe è Python): va nelle richieste
del §17, non nel piano DB.

⚠️ **E dà il guard, gratis**: un'attività con `fattura_riga_id IS NULL` non è
mai finita in una fattura, quindi **non ha un prezzo da cui accreditare**. Non è
un caso da gestire con un ripiego: è la condizione che rende l'accredito
impossibile, e va detta.

**E — l'idempotenza.** Il §10 chiede *«due click non producono due accrediti»*.
Il conto **non basta a garantirlo**, e la finestra è concreta:

```text
t0  verbo → nasce la commessa_attivita RETTIFICA, stato NON_EMESSA
    ⚠️ l'AF non esiste ancora → vw_af_merce_per_riga non la vede
    ⚠️ quindi la partita è ancora DA_ACCREDITARE e la riga è ANCORA IN CODA
t1  giro di fatturazione → emissione → nasce l'AF → il conto si chiude
```

Fra `t0` e `t1` — che è lungo quanto il batch dei lotti — un secondo click
produrrebbe **un secondo accredito**, e sarebbe perfettamente coerente col
conto. Ne discende che il guard deve essere sul **fatto** («esiste già una
rettifica per questa riga di reso»), non sul saldo.

**G — il legame `fatture_rettifiche`.** La madre **non può scriverlo**: al
momento del verbo la fattura di accredito non esiste (nascerà nel lotto), e la
fattura *rettificata* si conosce solo attraverso l'AF originale
(`attivita_fatturabili.fattura_riga_id` → `fatture_righe.fattura_id`). Quindi
il legame si scrive **a valle**, e per scriverlo serve sapere quale AF si sta
rettificando.

✅ **La risposta unica: la rettifica porta il riferimento all'AF che rettifica.**

```text
commesse_attivita  +  af_rettificata_id   (o l'equivalente in meta — forma al team)
```

Da lì discendono, tutte e cinque:

| Serve per | Come |
| --- | --- |
| **N-1** il prezzo | `af.fattura_riga_id → fatture_righe` — prezzo, sconto e IVA dalla **fattura**, mai ricalcolati |
| la **corsia** che ha fatturato | `af → ca.segment_key`: `ORD` o `DDT` |
| la **commessa** su cui creare la rettifica | `af.commessa_id` (NOT NULL) |
| il **legame documentale** | `af.fattura_riga_id → fatture_righe.fattura_id` = la fattura da rettificare |
| l'**idempotenza** | indice unico parziale su `(af_rettificata_id, riga di reso)` |

⚠️ **E dà anche il guard mancante**: non si può accreditare un'AF che non è
ancora finita in una fattura (`fattura_riga_id IS NULL`). Oggi nulla lo
impedirebbe, e la NC nascerebbe rettificando un documento che non esiste.

### 12.6-bis ✅ REQUISITO (Tid, 2026-08-18) — tracciabilità riga↔riga

> *«Dovremmo tenere traccia di quale fattura ha generato la nota di credito e la
> corrispondente riga.»*

**Cosa c'è oggi**, e non basta:

| Livello | Oggetto | Stato |
| --- | --- | --- |
| documento ↔ documento | `vendite.fatture_rettifiche (fattura_id, rettificata_id)` | esiste, **0 righe**, mai usata |
| **riga ↔ riga** | — | ⛔ **non esiste**, e `fatture_righe.sorgente_*` è NULL **per decisione** (una riga aggrega n attività: *«nessuna singola da dichiarare»*) |

⭐ **Ma per una riga di rettifica quel motivo cade**: la §12.6 stabilisce che le
righe di rettifica **non si aggregano** — una rettifica specchia **una** riga di
fattura. Quindi la sorgente singola esiste, è una sola, ed è dichiarabile.

#### La forma: una colonna che accompagna la rettifica lungo tutta la catena

```text
commesse_attivita.fattura_riga_rettificata_id   ──┐
attivita_fatturabili.fattura_riga_rettificata_id ─┤  FK → vendite.fatture_righe.id
fatture_righe.riga_rettificata_id  ───────────────┘   (auto-riferimento)
```

Il pattern è già in casa: `attivita_fatturabili.fattura_riga_id` fa esattamente
questo nel verso opposto (attività → riga di fattura). Qui si aggiunge il verso
della rettifica (riga di NC → riga rettificata).

⚠️ Va scritta **all'INSERT**: superata la soglia `DRAFT`/`EMESSA` sulle righe di
fattura non si può più fare nulla — né `UPDATE`, né `DELETE`, né `INSERT`.

#### ⭐ Cosa questa colonna regala, oltre alla tracciabilità

**1. L'invariante di N-1 diventa una query.**

```text
per ogni riga con riga_rettificata_id NOT NULL:
    articolo, prezzo_unitario, sconto_percentuale, iva_id   IDENTICI alla riga rettificata
    |qta|  ≤  qta della riga rettificata
```

È il *«copia esatta, compresi gli sconti»* trasformato da principio a **cancello
verificabile**, e va nel pgTAP.

**2. Un secondo tetto, indipendente dal conto della merce.**

```text
già accreditato su una riga di fattura  =  Σ |qta| delle righe che la rettificano
                                            ⤷ non può superare la sua qta
```

⭐ **Ne discende una cintura che non esisteva.** Oggi l'unico limite
all'accredito è il conto della merce (`fatturati − tenuti`). Con questa colonna
ce n'è un secondo, che parla la lingua del **documento** invece che della merce:
*«questa riga di fattura ha fatturato 10 pezzi, non se ne possono accreditare
11»*. Due misure indipendenti che devono concordare — e quando non concordano
c'è un difetto da guardare, invece di un numero solo di cui fidarsi.

**3. L'idempotenza smette di dipendere da una finestra.** Il §12.6-E descriveva
il buco fra il verbo e l'emissione, in cui la coda mostra ancora la riga e un
secondo click produrrebbe un secondo accredito. Con il tetto per riga di fattura
il secondo click **sbatte contro un numero**, non contro un flag da mantenere.

**4. `fatture_rettifiche` si popola da sé, e resta una proiezione.** Il legame
documento↔documento è il `DISTINCT` di quello riga↔riga:

```sql
INSERT INTO vendite.fatture_rettifiche (fattura_id, rettificata_id)
SELECT DISTINCT r.fattura_id, orig.fattura_id
  FROM vendite.fatture_righe r
  JOIN vendite.fatture_righe orig ON orig.id = r.riga_rettificata_id
 WHERE r.fattura_id = <la NC>
ON CONFLICT ON CONSTRAINT uq_fatture_rettifiche_pair DO NOTHING;
```

⭐ **Così non ci sono due verità**: le righe sono il fatto, la tabella-ponte è
l'indice. Ed è la risposta al §2 di questo brief — *«non va buttata: serve come
legame fra i due documenti, ma da sola non chiude nulla»*. Adesso non è più sola.

**5. La FatturaPA ha ciò che le serve.** Il blocco `DatiFattureCollegate` di una
TD04 vuole numero e data del documento rettificato: si leggono dal legame
documento↔documento, che ora esiste ed è popolato.

⚠️ **Conseguenza sul generatore righe** (backend): oltre a non aggregare le
rettifiche (§12.6), deve **scrivere** `riga_rettificata_id` sulla riga che
produce. È la stessa passata in cui copia prezzo, sconto e IVA dalla riga
rettificata: un solo `JOIN`, non due letture.

### 12.6-ter ✅ REQUISITO (Tid, 2026-08-18) — `vendite.resi_righe_accrediti`, il terzo lato

> *«Nel caso dobbiamo aggiungere una tabella di riferimento, anche per evitare
> che una riga possa essere fatta due volte una nota di credito.»*

⭐ **La tabella non è solo un presidio: è il posto che nel modello manca, e il
modello lo dice da solo.** Una riga di reso ha oggi **due** uscite, ciascuna con
la sua tabella-ponte, e la doc di `resi_righe_rinunce` le chiama per nome:
*«la merce torna indietro (ponte `resi_righe_riconsegne`) **oppure** si chiude
qui»*.

```text
una riga di reso ha TRE uscite:

   torna al cliente   →  vendite.resi_righe_riconsegne   (resi_riga_id, ddt_riga_id, qta)   ✅ esiste
   non torna più      →  vendite.resi_righe_rinunce      (resi_riga_id, qta)                ✅ esiste
   si accredita       →  vendite.resi_righe_accrediti    (resi_riga_id, …, qta)             ⛔ MANCA
```

**Ne discende che questa slice non aggiunge un'eccezione al modello: ne completa
una simmetria** — ed è il motivo per cui il §4 (*«nessuna seconda pipeline»*)
regge fino in fondo.

#### La forma, sul calco delle due sorelle

| Colonna | Perché |
| --- | --- |
| `resi_riga_id` | la riga di reso accreditata — come nelle due sorelle |
| `fattura_riga_rettificata_id` | **quale riga di fattura** si accredita (§12.6-bis, requisito di Tid) |
| `qta` | quanto — `CHECK > 0`, come `k_resi_riconsegne_qta_pos` e `k_resi_rinunce_qta_pos` |
| `commessa_attivita_id` | la rettifica generata: chiude il cerchio verso il documento |
| `note`, `meta`, `storicizza`, `tx_id`, audit | il corredo delle due sorelle, identico |
| `UNIQUE (resi_riga_id, fattura_riga_rettificata_id)` | il calco di `uq_resi_riconsegne_pair`: **una riga di reso non accredita due volte la stessa riga di fattura** |

⚠️ **La `UNIQUE` da sola non basta**, ed è bene dirlo subito: impedisce il
doppione esatto, non l'eccesso. Il tetto è una **somma**, e le somme non si
esprimono con un vincolo di colonna → serve il guard, sul modello di
`trgfn_resi_riconsegne_guard` che presidia già la gemella.

**I due tetti che il guard verifica**, e sono indipendenti fra loro:

```text
Σ qta per resi_riga_id                  ≤  accredito_dovuto della riga di reso   (la MERCE)
Σ qta per fattura_riga_rettificata_id   ≤  qta della riga di fattura             (il DOCUMENTO)
```

⭐ **Due misure che parlano lingue diverse e devono concordare**: una conta i
pezzi tornati, l'altra i pezzi fatturati. Quando divergono non c'è un numero di
cui fidarsi — c'è un difetto da guardare.

#### Perché la tabella risolve l'idempotenza meglio della colonna da sola

Il §12.6-E descrive la finestra fra il verbo e l'emissione: la rettifica esiste
come attività **NON_EMESSA**, l'attività fatturabile non c'è ancora, quindi il
conto della merce non è cambiato e **la riga è ancora in coda**. Un secondo
click sarebbe coerente col conto.

✅ **Con la tabella la finestra si chiude nel punto giusto**: l'accredito è
registrato **al momento del verbo**, non alla generazione della fattura. Il
secondo click sbatte contro una riga che c'è già, e l'operatore lo scopre
**quando clicca** — non a fine batch, su un documento fiscale.

#### E dà gratis le due cose che servivano altrove

* **il `gia_accreditato` della coda** (§12.7, rilievo H): un `LEFT JOIN` su
  questa tabella, non un ricalcolo. Il gating del bottone si fa su un dato che
  la riga già porta, come la regola delle liste impone;
* **l'audit**: chi, quando, quanto, su quale riga di fattura, con quale motivo.
  Oggi quella storia non esisterebbe da nessuna parte — la rettifica in commessa
  dice *cosa* è stato fatto, non *a fronte di cosa*.

⚠️ **Trappole di questa tabella**, tutte già pagate dal progetto:

* è una tabella **nuova** → gli indici FK sono **opt-in**: serve il seed
  esplicito in `dbops.fk_index_policy`, o non ne nasce nessuno;
* i trigger di audit, `tx_id` e storico girano solo in contesto `ci_apply`: su
  un migrate manuale li aggancia il job serale, non l'apply;
* `PK` `INTEGER GENERATED BY DEFAULT AS IDENTITY` (tabella tecnica), non SERIAL,
  come le due sorelle;
* il guard legge `resi_righe` e `fatture_righe` **sotto RLS**: se una delle due
  non è visibile non deve leggersi come «non c'è» — è il difetto già visto in
  `trgfn_resi_righe_guard_origine_coerente`, che si risolve leggendo la riga
  correlata da una `SECURITY DEFINER`.

### 12.6-quater ✅ D-NC-6 — l'accredito è sempre PIENO (Tid, 2026-08-18)

> 🔴 **CORREZIONE.** La prima stesura raccomandava di **ammettere** l'accredito
> parziale, con l'argomento che *«il dato lo prevede già e vietarlo costerebbe un
> guard in più»*. È sbagliato: il costo non è un guard, è un **residuo che
> nessuno può chiudere**.

**Il difetto del parziale, con i numeri.** Fatturati 10, resi 5, accreditati 3:

```text
fatturati 10 − accreditati 3 = 7        il cliente ne ha 5        →  restano −2
la coda continua a dire «2 da accreditare»
```

E quei 2 **non si chiudono in nessun modo**:

* **non esiste una rinuncia all'accredito.** `resi_righe_rinunce` riguarda la
  *ri-consegna* (*«questa merce non torna più al cliente»*) e la sua doc è
  esplicita: *«scrivere qui non muove nessun numero… l'accredito passa da
  FACOLTATIVA a DOVUTA, **con importo invariato**»*;
* **non li chiude nemmeno addebitare la trattenuta**: un onere viaggia su
  segmenti `MAN:` e **non entra nel conto della merce** (doppia cintura del
  brief porta oneri §5). Si può addebitare quel che si vuole: i −2 restano.

🔴 **Ne discende che il parziale ricrea la malattia per cui questo cantiere
esiste** — la riga che resta in coda a chiedere per sempre (§2).

#### ✅ La forma decisa, e perché non toglie nulla

Il caso commerciale dietro il parziale è reale, ma è un **addebito**, e il
sistema ha già la sua porta con le causali a catalogo (`PENALE` fra le cinque
seedate):

```text
accredito PIENO 50 €     →  il conto della merce si chiude, la coda si svuota   ✅
+ onere 20 € causale PENALE  →  con motivo e audit, leggibile dal cliente        ✅
```

Stessa cifra netta, due fatti con un nome ciascuno. È il principio del brief
oneri: *«ogni intento ha esattamente una porta, e la porta che si presta
all'abuso non esiste»*.

⭐ **E l'argomento di Tid chiude la questione a monte**: *«c'è tutta la gestione
dei resi per dire quanto trattenere e quando reinviare — non ci inventiamo
nulla»*. Le decisioni di **quantità** vivono già sul reso (quanto torna, quanto
si rinuncia, quanto si ri-consegna): l'accredito non è un posto dove si decide,
è un posto dove si **esegue** ciò che il conto ha già stabilito.

#### ⚠️ Conseguenze sulla forma della madre — semplificano il piano

1. **La madre NON ha un parametro quantità.** `fn_accredita_riga_reso(p_resi_riga_id)`
   e basta: la quantità è `vw_resi_da_accreditare.accredito_dovuto`. Sparisce
   tutta la classe di guard sull'input («≤ accredito dovuto», «> 0», «non NULL»):
   non è validazione più severa, è **input che non esiste**.
2. **Restano possibili le righe multiple**, ma per ragioni **strutturali**, non
   per scelta: se l'accredito dovuto di una riga di reso copre due righe di
   fattura a prezzi diversi (D-NC-5, LIFO), nascono due righe in
   `resi_righe_accrediti` e due rettifiche. La **somma** resta piena.
3. **Il tetto «Σ qta ≤ accredito_dovuto» del §12.6-ter smette di essere un
   limite e diventa un'uguaglianza**: dopo il verbo la somma **è** l'accredito
   dovuto. Un guard che verifica un'uguaglianza è più forte di uno che verifica
   una disuguaglianza, e costa lo stesso.
4. **Il secondo tetto — quello per riga di fattura — resta una disuguaglianza**,
   e resta necessario: più resi diversi possono accreditare la stessa riga di
   fattura in momenti diversi.

### 12.7 🟡 Rilievo H — il verbo si esercita da una lista

`vendite.resi_da_accreditare` è una **lista configurabile** (codice lista
registrato in `views_resi.py`, export incluso). E il progetto ha una regola
esplicita: **le capability `fn_available_actions_*` stanno sul DETTAGLIO, mai
per riga di lista** — le liste si gatano sui codici già presenti in riga, o con
uno scalare set-based; mai N chiamate.

Ne discende un requisito sulla **vista**, non sul verbo: la coda deve portare
in riga ciò che serve a decidere se il bottone è attivo. Almeno:

* `gia_accreditato` (o `rettifica_id`), che è anche il testimone di E;
* il motivo dell'eventuale blocco, in forma di codice (non di frase) — sul
  modello di `reason_key` già usato dalle capability.

⚠️ E se il verbo diventa **massivo** («accredita le righe selezionate»), la
madre deve accettare un array e restare **una sola unità atomica**: parziali a
metà su documenti fiscali sono la cosa peggiore di tutte. → **D-NC-7**.

### 12.7-bis ✅ D-NC-7 — massivo dal primo giorno, ma non dentro la madre (Tid, 2026-08-18)

**Decisione**: l'operatore può accreditare **più righe selezionate** fin da
subito; la funzione madre però resta **a riga singola**
(`fn_accredita_riga_reso(p_resi_riga_id)`), e il fan-out lo fa il backend.

⭐ **Perché non l'array nella madre — il building block esiste già.**
`apps/core/services/fan_out.py` (costruito il 2026-08-09, 2234 test verdi, in
catalogo BB) fa esattamente questo: riceve una lista già risolta, isola **ogni
elemento in un savepoint**, e restituisce un esito a tre valori
`COMPLETATO | PARZIALE | ERRORE`. Il chiamante decide cosa farne.

**L'argomento che decide, ed è di merito, non di comodità: il verbo NON è
l'atto fiscale.** Crea una riga di rettifica in commessa; il documento nasce
dopo, nel giro di fatturazione. Quindi un esito parziale **non lascia mai mezzo
documento** — lascia una riga non lavorata, che resta in coda e si riprova. È
precisamente il caso per cui quel BB è stato scritto.

Con l'array e il tutto-o-niente, invece, su una coda condivisa fra più operatori
basterebbe **una** riga accreditata da un collega mezz'ora prima per bloccare le
altre diciannove — e il tutto-o-niente lì non proteggerebbe nulla, perché non
c'è niente di parziale da proteggere.

⚠️ **E c'è un costo tecnico specifico dell'array**: aggiungere un parametro a
una funzione con valori di default **crea un overload** e rende ambigue le
chiamate esistenti, quindi la firma andrebbe decisa ora e cambiarla dopo
costerebbe `DROP` + rifacimento. Con la riga singola la firma è la più semplice
possibile, e il massivo resta una scelta del backend — reversibile.

⚠️ **Richiesta al backend che ne discende** (§17): il verbo massivo usa
`run_fan_out`, **non** un ciclo scritto a mano. Il BB porta con sé l'isolamento
per elemento e il protocollo di log; un ciclo lo riscriverebbe peggio, ed è
esattamente ciò che il brief del BB dichiara di voler impedire.

### 12.7-ter ✅ D-NC-8 — il pannello collega, non agisce (Tid, 2026-08-18)

**La tensione da sciogliere** era fra due decisioni prese lo stesso giorno:

| Dove | Cosa dice |
| --- | --- |
| [brief situazione merce](brief-design-situazione-merce-ordine.md) §6 | *«Nessuna azione nel pannello in questa fase: è una lettura. I verbi vivono dove già stanno»* |
| questo brief, §9-bis | *«il posto naturale da cui invocare il verbo diventa proprio quel pannello, dove il numero è già davanti agli occhi»* |

✅ **Decisione: il pannello resta una LETTURA e offre un collegamento alla coda
già filtrata** sul documento aperto. L'operatore clicca «8 da accreditare» e si
ritrova in `Vendite → Resi → Da accreditare` con davanti **solo quelle righe**,
dove il verbo c'è già.

**Le tre ragioni:**

1. **la decisione del pannello-lettura non si tocca** — e con essa il fatto che
   quel pannello non ha permessi di scrittura, conferme, gestione errori né
   ricarico dopo l'azione: sono quattro cose che dovrebbe acquisire tutte
   insieme per ospitare un verbo;
2. **il verbo resta in un posto solo.** Due superfici che chiamano lo stesso
   verbo divergono su permessi e conferme — è il tipo di divergenza che nessun
   test intercetta, perché ognuna è coerente con sé stessa;
3. **è reversibile nel verso giusto**: aggiungere domani il bottone nel pannello
   resta possibile; togliere un'azione già data è molto più difficile.

⭐ **E il percorso spezzato che aveva generato il §9-bis si chiude lo stesso**:
l'operatore non deve più *sapere* dove sta la coda — ci arriva da dove ha visto
il numero, con il filtro già messo.

⚠️ **Richiesta al frontend** (§17): il collegamento deve portare la coda
**filtrata**, non aprirla e basta. Una coda non filtrata su un'applicazione con
molte righe è un percorso spezzato uguale, solo con un click in più.

### 12.8 🟡 Rilievo I — il Backlog cambia di colpo

Il §6.1 dice giustamente che sono **due celle di seed**
(`motivi_fermo` id 14: `FISIOLOGICO` → `RECUPERABILE`, `azione` da NULL a una
frase). Verificato sul CSV: è esatto, e il loader è `runOnChange` — quindi
[si edita il CSV, non si fa un `UPDATE`](../../linee-guida-sql.md).

⚠️ **Due conseguenze che il §6.1 non nomina**:

1. **il conteggio del tab cambia a colpo d'occhio**, e il brief di luglio
   aveva già chiesto di avvisare chi lo usa prima del rilascio, *«o sembrerà una
   perdita di dati»* — qui è il contrario (righe che compaiono), ed è comunque
   un salto da annunciare;
2. l'area `RESI` del Backlog ha `valore_fermo` **NULL** per decisione (misura a
   conteggi, DL-11): il FE non deve renderlo come `0 €`. È già scritto nel
   brief di luglio §8 — ma è la prima volta che quel ramo si popola davvero,
   quindi è la prima volta che la regola viene esercitata.

---

## 13. Il modello proposto

Mettendo insieme i rilievi, la forma è questa. **Tre oggetti nuovi, due viste
toccate, un seed.**

```text
                 ┌─ coda accrediti (vw_resi_da_accreditare)
                 │     porta: resi_riga_id, ddt_riga_id, accredito_dovuto, etichetta
                 │     + NUOVO: gia_accreditato / motivo di blocco
                 │
   OPERATORE ────┴──► fn_accredita_riga_reso(resi_riga_id)   ← LA MADRE, un parametro solo
                            │
                            ├─ 1. risolve l'AF da accreditare (corsia, prezzo, commessa, fattura)
                            ├─ 2. guard: AF in fattura · in coda · non già accreditata
                            ├─ 3. advisory lock a 2 arg su (namespace, commessa)
                            ├─ 4. INSERT in resi_righe_accrediti  ← il fatto E il presidio
                            ├─ 5. fn_upsert_commessa_attivita(
                            │        segment_key = 'DDT:<uid>:R:<id>#RET:<n>',
                            │        tipo_movimento = 'RETTIFICA',
                            │        natura_doc = NOTA_CREDITO,
                            │        quantita = NEGATIVA,
                            │        prezzo = COPIATO dalla riga di FATTURA,
                            │        stato_approvazione = 'APPROVATA')
                            ├─ 6. guard is_new (la porta è una CREATE, non una upsert)
                            └─ 7. audit su commesse_attivita_log (evento ACCREDITO_RICHIESTO)
                            │
                 giro NORMALE di fatturazione (nessuna seconda pipeline)
                            │
                            ├─ emissione   → attivita_fatturabili (tipo_movimento propagato)
                            ├─ lotto       → separato per natura/tipo_doc, quindi NC a sé
                            ├─ righe       → generatore esistente, nessun ramo nuovo
                            ├─ numerazione → fn_assign_numero_fattura, serie/registro della NC
                            └─ NUOVO task  → popola vendite.fatture_rettifiche
                            │
                 vw_partite_merce:  fatturato −= rettificato   →  differenza a 0
                            │
                 la riga ESCE dalla coda da sola. ✅ (il contratto del §2)
```

⭐ **Il pregio della proposta del §4 regge tutto**: nessuna seconda pipeline. Le
uniche cose che il giro di fatturazione impara sono **due seed** (la natura, il
sezionale) e **un task** (il legame documentale). Tutto il resto è la macchina
che già gira.

⚠️ Questo schema è la **sintesi**; la forma esatta di ogni pezzo sta nel piano
del §15, che è stato riscritto dopo le decisioni.

---

## 14. ✅ Le decisioni — TUTTE CHIUSE (Tid, 2026-08-18)

Dieci decisioni, chiuse una alla volta in chat il 2026-08-18. ⚠️ **Quattro sono
andate CONTRO la raccomandazione iniziale dell'analisi**, e in tre casi la
raccomandazione era proprio sbagliata: il dettaglio è nei paragrafi indicati,
perché il *perché* di una correzione vale più della correzione.

| # | Domanda | Raccomandazione |
| --- | --- | --- |
| **D-NC-1** | La rettifica porta **sempre** il segmento della partita (DDT), anche quando a fatturare è stata la corsia ORD? | ✅ **DECISA (Tid, 2026-08-18): sempre DDT**, e il *«se non c'è, prendi il primo»* diventa un **guard fail-fast** perché non può capitare — §14.2 |
| **D-NC-2** | Il **segno**: quantità negativa in catena, o positiva con `tipo_movimento` che sottrae? | ✅ **DECISA (Tid, 2026-08-18): quantità NEGATIVA.** La raccomandazione iniziale era l'opposta ed **era sbagliata**: il costo a valle risulta già pagato — §12.3 |
| **D-NC-3** | Dove vive la **natura** del documento: terza riga in `tipi_doc_fiscale` (C1), asse nuovo (C2), o solo `serie` (C3)? | ✅ **DECISA (Tid, 2026-08-18): asse nuovo (C2).** Integrazione con registro, numerazione e fattura elettronica nel **§12.4-bis** |
| **D-NC-3b** | La NC ha un **registro proprio** o condivide quello delle fatture con una **serie** dedicata? | ✅ **DECISA (Tid, 2026-08-18): SEZIONALE PROPRIO.** Registro dedicato, progressivo e `reset_policy` indipendenti. 🔴 **Ne discende che il difetto del §12.4-bis.4 diventa BLOCCANTE**, non più latente — vedi §14.3 |
| **D-NC-4** | La **ri-consegna dopo la NC**: *«è merce nuova solo per la parte accreditata»*, oppure si accetta che non rifatturi e lo si **scrive**? | ✅ **DECISA (Tid, 2026-08-18): si implementa la regola.** Forma esatta, con i numeri, nel **§12.5-bis** |
| **D-NC-5** | Con più righe di fattura sulla stessa partita a **prezzi diversi**, quale si accredita? | ✅ **DECISA (Tid, 2026-08-18): dall'ULTIMA fatturata, a scalare.** ⚠️ Non è una regola di *calcolo* ma di **consumo**: il prezzo si **copia** dalla riga di fattura, mai si ricalcola — «in proporzione» è stata scartata perché inventerebbe un prezzo medio che in fattura non esiste. Kit: **nessuna scelta**, una rettifica per componente, specchio delle righe di fattura |
| **D-NC-6** | L'**accredito parziale** (§8.5) esiste? | ✅ **DECISA (Tid, 2026-08-18): NO — l'accredito è sempre PIENO.** La raccomandazione iniziale era l'opposta ed era sbagliata: un parziale lascia un residuo che **nessuno può chiudere**. §12.6-quater |
| **D-NC-7** | Il verbo è **per riga** o anche **massivo** sulla selezione della coda? | ✅ **DECISA (Tid, 2026-08-18): massivo DA SUBITO, ma la madre resta a RIGA SINGOLA.** Il massivo lo fa il BB `run_fan_out`, già costruito e collaudato — §12.7-bis |
| **D-NC-8** | Da **dove** si invoca: solo dalla coda, o anche dal pannello situazione merce (dove il numero si vede)? | ✅ **DECISA (Tid, 2026-08-18): dal pannello un COLLEGAMENTO alla coda già filtrata** su quel documento. Il verbo resta in un posto solo — §12.7-ter |
| **D-NC-9** | Serve la tracciabilità **riga di NC ↔ riga di fattura**, oltre al legame fra documenti? | ✅ **REQUISITO (Tid, 2026-08-18): sì.** Forma, e le cinque cose che regala, nel **§12.6-bis** |
| **D-NC-10** | Serve una **tabella** che registri l'accredito, per impedire che una riga sia accreditata due volte? | ✅ **REQUISITO (Tid, 2026-08-18): sì** — `vendite.resi_righe_accrediti`, il **terzo lato** accanto a `resi_righe_riconsegne` e `resi_righe_rinunce`. Forma e due tetti nel **§12.6-ter** |

> ⏳ **Si decidono in chat, una per volta**; man mano che una risposta arriva
> viene scritta qui. Chiuse: **D-NC-1**, **D-NC-2**, **D-NC-3**, **D-NC-4**,
> **D-NC-5**, **D-NC-6**, **D-NC-9**, **D-NC-10** (3b si dissolve in un seed,
> **D-NC-3b**, **D-NC-7**, **D-NC-8**.
> ⭐ **TUTTE E DIECI CHIUSE il 2026-08-18.** Il piano del §15 è riscritto su
> queste decisioni: non è più esplorativo.

### 14.2 ✅ D-NC-1 — sempre il segmento della spedizione (Tid, 2026-08-18)

**La domanda posta da Tid**, e vale la pena registrarla perché ha spostato la
forma della risposta: *«la fattura non dovrebbe riuscire a risalire alla
sorgente — ordine, DDT, preventivo?»*

✅ **La tracciabilità c'è, ma va nel verso opposto**, e non per caso: è una
decisione scritta nel codice del generatore righe
(`pipeline_repository.batch_insert_righe_and_mark`).

```sql
INSERT INTO vendite.fatture_righe (…, sorgente_tipo_id, sorgente_uid, sorgente_riga, …)
SELECT …
    -- La riga aggrega n attivita' con n sorgenti: nessuna
    -- singola da dichiarare. La tracciabilita' passa dal
    -- puntatore attivita_fatturabili.fattura_riga_id (D4).
    NULL, NULL, NULL,
```

I tre campi «sorgente» **esistono sulla riga di fattura e restano vuoti,
apposta**: una riga aggrega n attività (stesso articolo, stesso prezzo, stessa
IVA) che possono venire da spedizioni diverse, e dichiararne **una** sarebbe
dichiararne una falsa. Il legame vive nel verso `attività → riga di fattura`.

⭐ **Ne discende che la proposta di Tid è già dentro il piano**, e sotto un altro
nome: `af_rettificata_id` (§12.6) **è** «attaccarsi alla fattura», percorso nel
verso che il modello supporta. Da lì si arriva a prezzo, corsia, commessa,
documento da rettificare e idempotenza.

**Ma restano due domande distinte**, e questo è il punto che la decisione chiude:

```text
«quale FATTURA rettifico?»       → la fattura, via l'attività      (af_rettificata_id)
«da quale MERCE tolgo i pezzi?»  → una PARTITA: il contatore non
                                    conosce le fatture, conosce due
                                    corsie (ORD, DDT)               ← D-NC-1
```

**Decisione**: partendo dall'attività si scrive **sempre** sul segmento della
**spedizione** (`DDT:<uid>:R:<riga>#RET:<n>`), anche quando l'attività trovata
porta un segmento `ORD:`.

#### ⚠️ Il ripiego chiesto («se il DDT non c'è, prendi il primo») non può scattare

Tid l'ha posto come cintura. **Verificato: la condizione è impossibile per
costruzione**, su tre livelli indipendenti:

| Fatto | Dove |
| --- | --- |
| `vendite.resi_righe.ddt_riga_id` è **NOT NULL** | la tabella: non esiste una riga di reso senza spedizione |
| la **partita È** la riga di DDT | `vw_partite_merce`, grana `ddt_riga_id` (cantiere 1, S2) |
| la coda accrediti è **agganciata a `ddt_riga_id`** | `vw_resi_da_accreditare`: *«la chiave passa da `ordine_riga_id` (NULLABLE) a `ddt_riga_id` (NOT NULL)»* |

E c'è la ragione di merito: **la merce non può tornare indietro se non è mai
uscita**, e per uscire passa da un DDT. Un accredito senza spedizione a monte
non è un caso raro: è una contraddizione.

🔴 **Ne discende che un `COALESCE` sarebbe un ramo morto, ed è la cosa peggiore
che si possa scrivere qui.** Un ramo che nessun percorso reale attraversa
sembra coperto e non lo è; e il giorno in cui qualcosa dovesse raggiungerlo
farebbe **in silenzio** proprio la cosa che D-NC-1 vieta — scrivere su `ORD:` e
spostare l'accredito sulla spedizione sbagliata.

✅ **Forma adottata**: il ripiego diventa un **guard fail-fast** con codice
errore registrato — *«accredito senza spedizione a monte»*. Stessa disciplina
delle guard sugli ID (`NULL` o `<= 0` → errore parlante, mai normalizzazione
silenziosa). La cintura che Tid chiedeva c'è; smette solo di essere silenziosa.

⭐ **E la seconda lettura della domanda resta viva, ed è un'altra**: *quale*
attività si accredita quando ce n'è più d'una sulla stessa partita — anche su
corsie diverse. Non è D-NC-1: è **D-NC-5**.

### 14.3 🔴 Cosa cambia con il sezionale proprio (D-NC-3b)

La scelta B non è più costosa della A **in schema** — il mapping
`(tipo_doc, natura) → registro` regge entrambe — ma sposta **un difetto da
latente a bloccante**, e va detto prima di scrivere.

**Il difetto è il §12.4-bis.4**: `fn_build_fattura_key` chiama
`fn_get_registro_id` con **un argomento solo**, quindi dalla pipeline sono
raggiungibili **solo i registri con `utility_id` e `emittente_soggetto_ruolo_id`
entrambi `NULL`**.

| Con la scelta A (serie dedicata) | Con la scelta B (sezionale proprio) |
| --- | --- |
| il registro è quello delle fatture, che è già `NULL/NULL` → **il difetto resta dormiente** | il registro è **nuovo**, e il primo che lo configurerà per un emittente scoprirà che non si risolve |

🔴 **Ne discende che la correzione di `fn_get_registro_id` + `fn_build_fattura_key`
entra nel percorso critico**: non è più un rilievo collaterale da girare al
cantiere emittente, è una slice di questo piano (**N2b**). Tid: *«procederemo
con tutte le correzioni necessarie»*.

⭐ **E c'è un guadagno che la scelta A non dava**: un registro proprio può avere
**`reset_policy` propria** (le NC si azzerano con l'anno come le fatture, o no)
e può essere **disattivato** senza toccare le fatture, perché è un oggetto a sé.
Con la serie condivisa quelle proprietà sarebbero state per forza le stesse.

⚠️ **Da chiedere a chi tiene i registri IVA, in fase di seed** — non blocca la
scrittura, blocca il seed:

* `codice` e `descrizione` del registro NC;
* `serie_default` (può restare vuota: il registro è già distinto);
* `reset_policy`: `ANNUALE` come le fatture, o diversa;
* se il registro è **per emittente** (allora la correzione N2b è indispensabile
  prima del seed) o unico per tutti.

---

## 15. 🗺️ Il piano DB — dodici slice

> ⭐ **Riscritto il 2026-08-18, dopo la chiusura di tutte e dieci le decisioni.**
> Non è più un piano esplorativo: ogni slice sa cosa deve fare. Le versioni
> precedenti sono superate — dove il testo divergeva dalle decisioni, vince la
> decisione.
>
> ⚠️ **La numerazione dei changeSet NON è indicata**, e non è una dimenticanza:
> il progressivo di una data si riconta col `find` **subito prima** di scrivere
> ogni file, e di nuovo fra un file e il successivo (§16.5).

### N0 — La fotografia, prima di toccare *(nessun changeSet)*

Le misure che servono a decidere il seed e a collaudare, prese **come owner**
(le tabelle hanno RLS: uno zero letto come applicazione non è un dato, è un
fail-closed).

```text
1. righe in vw_resi_da_accreditare, per etichetta DOVUTA / FACOLTATIVA
2. per ciascuna: la partita è fatturata sulla corsia DDT, ORD, o entrambe?
   → dice se D-NC-1 è quotidiano o se il pgTAP deve costruirsi il caso
3. partite con PIÙ di una riga di fattura a prezzi diversi   → dimensiona D-NC-5
4. attività delle partite in coda con fattura_riga_id NULL   → dimensiona il guard
5. righe di ri-consegna esistenti e loro partita d'origine   → D-NC-4
6. conteggio attuale del tab Backlog area RESI               → il salto del §12.8
7. ⭐ registri con utility_id o emittente NON NULL           → misura il §12.4-bis.4
```

⚠️ **Il punto 7 è nuovo e serve a N2b**: se oggi esistono già registri
intestati, sono **già irraggiungibili** e il difetto non è teorico.

---

### N1 — L'asse «natura» *(00_schema + 20_code + 80_data)*

| Cosa | Nota |
| --- | --- |
| `config.nature_doc_fiscale` | vocabolario **neutro**: `FATTURA`, `NOTA_CREDITO`, `NOTA_DEBITO`. Mono-lingua con `descrizione`, sul modello di `causali_onere`/`tipi_reso` — **niente `label_key`** (precedente deciso nel brief porta oneri §4c.3). `meta` porta `{"sdi_tipo_documento": "TD01"/"TD04"}`: il codice italiano è un parametro di **profilo nazionale**, non una colonna, perché il modello si dichiara *«senza vincoli di specifico ordinamento nazionale»* |
| `natura_doc_id` su `fatture`, `commesse_attivita`, `attivita_fatturabili` | **NOT NULL DEFAULT `FATTURA`** → nulla di esistente cambia comportamento |
| immutabilità su `fatture` | riuso di `script.trgfn_lock_columns` — lo stesso BB che protegge `codice_interno` su `tipi_doc_fiscale`. Un documento non cambia natura |
| seed CSV | le due nature. ⚠️ **CSV, mai `INSERT`/`UPDATE` diretti** |

⚠️ `%TYPE` **non è valido** in `ALTER TABLE ADD COLUMN`: tipi espliciti.

---

### N1b — La natura viaggia lungo la catena *(20_code)*

`fn_upsert_commessa_attivita` e `fn_emit_attivita_fatturabili_da_commessa`
imparano `natura_doc_id`. È la stessa coreografia già fatta per `tipo_movimento`
(`20260717-01..04`) e per `causale_onere_id` (`20260721-04/-06`).

🔴 **`fn_upsert_commessa_attivita` ha 38 parametri con default: aggiungerne uno
CREA UN OVERLOAD** e rende ambigue le chiamate esistenti. Serve `DROP` +
`CREATE`, e il censimento dei chiamanti prima.

---

### N2 — Il registro della natura *(00_schema + 20_code + 80_data)*

* `tipi_doc_fiscale_registri` guadagna `natura_doc_id` (NOT NULL default
  `FATTURA`) e `serie` (nullable, override del `serie_default` del registro);
  la `UNIQUE` passa a `(tipo_doc_fiscale_id, natura_doc_id, registro_id)`;
* `fn_get_registro_id` guadagna la natura e restituisce **registro + serie**
  → cambia il tipo di ritorno: `DROP` + `CREATE`, non `CREATE OR REPLACE`;
* **seed del sezionale NC** (D-NC-3b) — ⚠️ i quattro valori li fornisce Tid
  (§14.3): codice, descrizione, `serie_default`, `reset_policy`.

---

### N2b — 🔴 I registri per emittente tornano raggiungibili *(20_code)*

**Correzione del §12.4-bis.4, sul percorso critico per D-NC-3b.**
`fn_build_fattura_key` passa **anche `utility_id` e `emittente_soggetto_ruolo_id`**
a `fn_get_registro_id`: li ha già calcolati tre righe più su.

⚠️ **Cambia il comportamento di documenti esistenti?** No sui dati di oggi (i
due registri in seed hanno entrambi i campi `NULL`, quindi il livello 4 del
fallback resta quello scelto), **sì** appena esisterà un registro intestato — ed
è l'intento. La parità va **misurata**, non assunta: è il punto 7 di N0.

⭐ Va segnalata anche al cantiere **perimetro emittente**, che è aperto: è un
pezzo dello stesso quadro.

---

### N3 — La chiave documento conosce la natura *(20_code)*

`fn_build_fattura_key` porta natura e serie; `fn_get_or_create_fattura_header`
li confronta nel `WHERE` **e li scrive nella `INSERT`**.

🔴 **Due trappole gemelle, entrambe silenziose:**

1. chiave che separa + lookup che non separa → *«le due metà si annullano e le
   attività tornano nella stessa fattura»* (è il commento vivo della funzione);
2. serie calcolata + `INSERT` che non la scrive → `fn_assign_numero_fattura`
   cade sul `serie_default` del registro e **la NC prende un numero valido nella
   serie sbagliata**.

⭐ Fatto questo, la separazione fisica del documento è **finita**: lotto,
testata, registro, numerazione. Senza aver scritto nulla di specifico per la NC.

---

### N4 — `vendite.resi_righe_accrediti` *(00_schema + 20_code)*

Il **terzo lato** accanto a `resi_righe_riconsegne` e `resi_righe_rinunce`
(§12.6-ter). Colonne, `UNIQUE (resi_riga_id, fattura_riga_rettificata_id)`,
`CHECK qta > 0`, corredo audit identico alle sorelle.

Più il **guard** sul modello di `trgfn_resi_riconsegne_guard`, con i due tetti:

```text
Σ qta per resi_riga_id                =  accredito_dovuto   (uguaglianza, per D-NC-6)
Σ qta per fattura_riga_rettificata_id ≤  qta della riga di fattura
```

⚠️ Il guard legge `resi_righe` e `fatture_righe` **sotto RLS**: la riga
correlata si legge da una `SECURITY DEFINER`, o «non la vedo» diventa «non
c'è». ⚠️ Tabella nuova → indici FK **opt-in**, serve il seed in
`dbops.fk_index_policy`.

---

### N5 — La tracciabilità riga↔riga *(00_schema)*

`fattura_riga_rettificata_id` su `commesse_attivita` e `attivita_fatturabili`,
`riga_rettificata_id` su `fatture_righe` (auto-riferimento) — §12.6-bis.

⚠️ Va scritta **all'INSERT**: dopo la soglia `DRAFT`/`EMESSA` sulle righe di
fattura non si può più fare nulla.

---

### N6 — `vw_partite_merce` sottrae la rettifica *(20_code)* 🔴 la slice critica

Un `LEFT JOIN` in più su `vw_af_merce_per_riga` (corsia `DDT`, `tipo_movimento
= 'RETTIFICA'`) e la somma nel `LATERAL` che calcola `fatturato`.

⭐ **Con D-NC-2 (quantità negativa) è una somma, non una sottrazione**, e con
D-NC-1 (sempre corsia DDT) la CTE `alloc` della corsia ordine **non si tocca
affatto**. Colonna nuova esposta: `rettificato`.

🔴 **Le tre cose da non sbagliare:**

1. **`security_invoker=on` va RI-SPECIFICATO**: la reloption non si vede in
   `pg_get_viewdef` e un `CREATE OR REPLACE` la azzera. Qui significa **bypass
   della RLS** (regressione V-1, già costata un rework);
2. `CREATE OR REPLACE VIEW` **non cambia il tipo di una colonna esistente**: la
   somma può allargare `numeric(18,6)` e far fallire il changeSet. Il cast è
   obbligatorio (lezione §17.5 del cantiere 1);
3. `differenza` resta **NULL** quando il conto non si applica, **mai zero**.

**Collaudo**: parità su tutte le partite — zero righe `RETTIFICA` oggi, quindi
**nessun valore deve cambiare** — più il caso costruito a mano.

---

### N7 — La ri-consegna dopo la NC *(20_code)* 🔴 D-NC-4

La regola del §12.5-bis: *«è merce nuova solo per la parte accreditata»*.

⚠️ **Changeset separato da N6**, e non è pignoleria: la parità di N6 si misura
**prima** che questa cambi i numeri.

⚠️ **Il test da tenere verde è nominato**: caso D di
`test-fn-list-ddt-da-pushare-contatore-v1` — la ri-consegna **senza** NC deve
continuare a proiettare 0. Se diventa rosso, è la regola a essere sbagliata.

---

### N8 — La madre `fn_accredita_riga_reso` *(20_code)* 🔴 il cuore

```text
fn_accredita_riga_reso(p_resi_riga_id bigint) RETURNS bigint
```

⭐ **Un parametro solo**: con D-NC-6 (sempre pieno) la quantità non è un input,
e con D-NC-7 il fan-out è del backend. Modello di riferimento:
`fn_aggiungi_onere_commessa`, la porta gemella che ha già pagato ogni pedaggio —
`SECURITY INVOKER` esplicito, `%TYPE` ovunque, guard sui parametri ID,
`pg_advisory_xact_lock` **a due argomenti** dopo le guard, progressivo del
suffisso da `MAX+1` (mai da `count`), guard `is_new`, audit su
`commesse_attivita_log`.

**Cosa fa, in ordine:**

```text
1. risolve le righe di fattura da accreditare — LIFO (D-NC-5), via
   af.fattura_riga_id → fatture_righe
2. guard: la riga è in coda · l'attività è finita in fattura · non già accreditata
3. per ciascuna riga di fattura consumata:
     - INSERT in resi_righe_accrediti  (il fatto, e il presidio)
     - fn_upsert_commessa_attivita:
         segment_key    = 'DDT:<uid>:R:<id>#RET:<n>'        ← D-NC-1
         tipo_movimento = 'RETTIFICA'
         natura_doc_id  = NOTA_CREDITO
         quantita       = NEGATIVA                           ← D-NC-2
         prezzo         = COPIATO dalla riga di fattura       ← N-1, mai ricalcolato
         stato          = APPROVATA + NON_EMESSA
     - kit: UNA rettifica per componente, suffisso '#RET:<n>#CMP:<comp>',
            con coeff_qta nel meta (specchio delle righe di fattura)
4. audit su commesse_attivita_log
```

⚠️ **Codici errore**: append al CSV, **mai un loader nuovo**. Verificare
l'unicità dell'`id` (sequenza manuale) e che i segnaposto `%s` corrispondano ai
valori: un segnaposto malformato fa crashare `format()` e **l'errore di dominio
sparisce**, sostituito da un `22023`.

⚠️ **E lascia il repository rosso** finché il backend non rigenera
`error_policies_generated.py` *e* scrive il messaggio di ripiego. Va nella lista
di consegna accanto al changeSet (lezione §22.5 del cantiere 1).

---

### N9 — La coda dice se è già accreditata *(20_code)*

`vw_resi_da_accreditare` espone `gia_accreditato` con un `LEFT JOIN` su
`resi_righe_accrediti` — è ciò che permette al frontend di disabilitare il
bottone **senza** una capability per riga di lista.

⚠️ `DROP`+`CREATE` probabile (cambia il numero di colonne) →
`security_invoker=on` ri-specificato, e **le colonne su cui il backend ordina e
cerca non si toccano** (`_CODA_META` in `resi_repository.py`).

---

### N10 — Il legame documentale *(20_code + registry task)*

`vendite.fatture_rettifiche` si popola **dal legame di riga**, come proiezione:
`SELECT DISTINCT` + `ON CONFLICT DO NOTHING` (§12.6-bis, punto 4).

⚠️ È un **task di pipeline**, non un trigger: dentro la transazione di
generazione righe appesantirebbe il punto più caldo del giro.

---

### N11 — I due presidi e il seed del Backlog *(20_code + 80_data)*

* `script.fn_get_stato_push_segment` impara il suffisso `#RET:%`. ⚠️ Non è
  cosmesi: oggi, su una partita di corsia ORD, il segmento DDT resta `LIBERA` e
  a proteggerla c'è **solo** la cintura XOR. Due cinture sono una; una è zero;
* la settima condizione del guard **D-K** in `fn_assign_numero_fattura`:
  `natura = NOTA_CREDITO ⟺ totale_a_pagare ≤ 0` (§12.4-bis.6) — due righe, e
  trasformano il segno da convenzione a invariante verificato **prima** che il
  progressivo venga consumato;
* `motivi_fermo` id 14: `FISIOLOGICO` → `RECUPERABILE` + `azione`. **Due celle
  di CSV**, e **insieme** al verbo, mai prima (§6.1).

---

### N12 — Documentazione e richieste

Doc concettuale in `docs/it/dbzero/<schema>/manual/` (**mai** gli auto-gen),
guida fatturazione, e la correzione della doc di `fatture` che oggi elenca
*«fattura, nota credito, parcella»* sotto `tipi_doc_fiscale` (§12.4-bis.1).
Più le richieste del §17, raccolte in blocco.

## 16. ⚠️ Le trappole di QUESTO cantiere

Oltre a quelle già citate slice per slice, sei che valgono per tutto il giro.

1. 🔴 **Il pgTAP deve costruire ciò che i dati non hanno.** Al 2026-08-17 le
   righe `RETTIFICA` sono **zero**: ogni ramo scritto qui è un ramo che nessun
   dato attraversa. Vale la regola imparata dal cantiere 1 — *«un ramo si
   verifica dal percorso che lo attraversa, non dal codice che lo dichiara»*:
   una fixture costruita a mano può **confermare un ramo morto**. Il caso va
   costruito **passando dalla madre**, non inserendo la riga a mano.
2. ⚠️ **`throws_ok` senza SQLSTATE accetta qualunque errore**, compreso il
   crash del guard stesso. Sempre `'P0001'` per un errore di dominio. Il
   cantiere 1 ci è cascato una volta (§20.5, punto 2) e lo ha scritto.
3. ⚠️ **Il pgTAP gira come l'APPLICAZIONE, con la RLS attiva.** Le tre righe di
   preambolo sono obbligatorie e presidiate; una fixture che scrive dove
   l'applicazione non scrive non passa. E i tre `SET CONSTRAINTS ALL IMMEDIATE`
   subito dopo `BEGIN`, o il file è verde per sottrazione.
4. ⚠️ **La baseline ha rossi preesistenti**: `scripts/pgtap-baseline.sh vendite`
   prima di attribuirsi un rosso. `test-fn-list-ddt-da-pushare-orfano-v1` è
   noto e **non è di questo cantiere**.
5. ⚠️ **`runOnChange: true` è vietato in `00_schema` e `20_code`**, e
   `validCheckSums` va **al plurale**. E la numerazione `NN` è **globale per
   data** fra tutte le cartelle. ⭐ **E il numero non si ricorda: si riconta,
   subito prima di scrivere ogni file.** Prova vissuta il 2026-08-18: nell'arco
   di un'ora la data è passata da `-19` a `-20` a `-23`, con file di **altri
   cantieri** e **non ancora committati**. Quindi `find`, non `git ls-files`:

   ```bash
   find db/changelog/migrations_v2 -name '20260818-*' | sort
   ```

   ⚠️ **Nessun numero scritto in questo brief è affidabile** quando lo leggerai:
   riconta, e riconta di nuovo fra un file e il successivo.
6. 🔴 **L'autogen mescola `00_schema` e `20_code` ordinando per numero**: chi
   ricrea una dipendenza deve avere numero più alto di chi la droppa, e mai
   `CASCADE`. Qui morde su `fn_upsert_commessa_attivita` (DROP + CREATE con
   parametro nuovo) e su `vw_partite_merce`.

---

## 17. 📌 Richieste agli altri perimetri

> Questo brief è **perimetro DB**: `backend/` e `frontend/` non si toccano. Le
> richieste si scrivono qui.

### 17.1 Backend

| # | Cosa | Perché |
| --- | --- | --- |
| **BE-1** | Endpoint del verbo, che chiama **solo** la madre | è una `SELECT fn_()`: l'atomicità è per costruzione, nessun `transaction.atomic()` che orchestri scritture |
| **BE-2** | Il verbo **massivo** usa `run_fan_out`, **non** un ciclo scritto a mano | il BB esiste, è collaudato e porta isolamento per elemento + protocollo di log. Un ciclo lo riscriverebbe peggio: è ciò che quel brief dichiara di voler impedire (D-NC-7) |
| **BE-3** | `post_permission` dedicato sul verbo | è la porta di un **documento fiscale**. Precedente: `carica_voce_manuale` sulla porta oneri. Il presidio sta **sul BE**, non nella madre, che deve restare usabile da un processo autorizzato |
| **BE-4** | 🔴 **Il generatore righe non aggrega le rettifiche**, e copia prezzo/sconto/IVA **dalla riga di fattura rettificata** | §12.6: una rettifica è lo specchio di **una** riga di fattura. Aggregarne due produrrebbe una riga gemella di nessuna, e il *«copia esatta compresi gli sconti»* cadrebbe — `commesse_attivita` non ha una colonna sconto |
| **BE-5** | Il generatore scrive `riga_rettificata_id` sulla riga che produce | §12.6-bis: è la stessa passata in cui legge la riga rettificata, un solo `JOIN` |
| **BE-6** | Rigenerare `error_policies_generated.py` **e** scrivere i messaggi di ripiego dei codici nuovi | senza, tre cancelli diventano rossi e li scopre la prima PR, non chi migra |
| **BE-7** | La coda espone `gia_accreditato`: **non** ricalcolarlo in Python | due traduzioni divergono — stessa ragione del BE-2 del cantiere 1 |
| **BE-8** | Il task di pipeline che popola `fatture_rettifiche` | N10 |
| **BE-9** | Verificare che la pipeline risolva uno **step** per la natura nuova | `fatturazione_pipeline` ha un fallback con `tipo_doc_fiscale_id IS NULL`: **probabilmente** non serve seed, ma va **verificato** invece che assunto |
| **BE-10** | ⚠️ Il drawer del lotto non deve assumere *«sono tutte fatture»* | §12.4-bis.8: con la natura sulla testata, **un lotto può contenere documenti di natura diversa**, e il verbo «numera» li numera entrambi sui rispettivi registri |

### 17.2 Frontend

| # | Cosa | Perché |
| --- | --- | --- |
| **FE-1** | 🔴 **Togliere** `vendite.situazione_merce.nc_non_disponibile` da `it.json` **e** `en.json` | è la nota temporanea del §9-bis: dal giorno del verbo **dice il falso**. Chiave precisa, non una ricerca |
| **FE-2** | Dal pannello, un **collegamento alla coda già filtrata** su quel documento | D-NC-8. ⚠️ *Filtrata*: una coda non filtrata è un percorso spezzato uguale, con un click in più |
| **FE-3** | Bottone abilitato/disabilitato su `gia_accreditato` della riga | mai una capability per riga di lista: si gate sui codici già in riga |
| **FE-4** | Selezione multipla sulla coda + esito `PARZIALE` leggibile | D-NC-7: `run_fan_out` restituisce «19 su 20, una segnalata» — va mostrato, non nascosto |
| **FE-5** | Label i18n del motivo `MERCE_RESA_GIA_FATTURATA` nel Backlog | il brief di luglio la chiedeva **già** *«da prevedere da subito»*: il ramo si popola **senza rilascio BE/FE**, quindi la chiave deve esserci **prima** |
| **FE-6** | Nell'area `RESI` del Backlog, `valore_fermo` NULL **non** si rende come `0 €` | DL-11, misura a conteggi. È la prima volta che quel ramo si popola davvero |

### 17.3 Al cantiere incassi / pagamenti

| # | Cosa | Perché |
| --- | --- | --- |
| **PG-1** | 🔴 **Il processo rimborsi non esiste**, e una NC **fuori dalla banda del minimo** non ha né rata né fondo automatico | §12.4-bis.7. Dentro la banda il fondo fattura la regola da sé; fuori, il credito resta **senza un posto che dica «va rimborsato»**. La strada è nominata dal modello (fondo `origine = MANUALE`, motivo obbligatorio, *«arriva dal processo rimborsi di `pagamenti`»*) ma non è costruita. È la domanda **D8** di [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md), ora precisata |

### 17.4 Al cantiere perimetro emittente

| # | Cosa | Perché |
| --- | --- | --- |
| **EM-1** | I **registri intestati a un emittente sono irraggiungibili** dalla pipeline | §12.4-bis.4. Lo corregge la slice **N2b** di questo piano, ma il rilievo è dello stesso quadro e va conosciuto lì: la doc di `registri_fatturazione` promette che *«la separazione dei registri evita collisioni di numerazione»* fra più aziende, e oggi quella promessa non è raggiungibile |

---

## 18. Definizione di «fatto»

Le sette voci del §10 restano. Queste otto descrivono ciò che l'analisi ha
aggiunto, e senza le quali il cerchio non si chiude:

* [ ] l'accredito si scarica sulla **spedizione da cui la merce è tornata**, non
      sull'ultima della riga d'ordine — e il test asserisce la **ripartizione**,
      non solo il totale (D-NC-1);
* [ ] ogni riga di nota di credito ha una **riga di fattura gemella**: stesso
      articolo, stesso prezzo, stesso sconto, stessa IVA, quantità non superiore
      — verificato da una query, non da una convenzione (N-1, D-NC-9);
* [ ] la NC è un documento con una **natura dichiarata**, leggibile da
      `vendite.fatture`, sul **suo sezionale** — pronta per il `TipoDocumento`
      della FatturaPA (D-NC-3, D-NC-3b);
* [ ] `natura = NOTA_CREDITO ⟺ totale_a_pagare ≤ 0` è un **invariante
      verificato prima della numerazione**, non una convenzione (D-NC-2);
* [ ] la **ri-consegna dopo una NC** rifattura, e quella **senza** NC continua a
      non rifatturare: il caso D di luglio resta verde (D-NC-4);
* [ ] **due click non producono due accrediti**, e il secondo lo scopre chi
      clicca — non il batch a fine giro (D-NC-10);
* [ ] un **registro intestato a un emittente si risolve**, e la parità sui
      documenti di oggi è **misurata** (N2b);
* [ ] `vendite.fatture_rettifiche` smette di essere una tabella a **zero righe**:
      ogni NC nomina i documenti che rettifica, come **proiezione** del legame di
      riga e non come seconda verità.

---

## 19. Sequenza consigliata

```text
N0  fotografia
 │
 ├─ N1  natura ──► N1b  la natura viaggia ──► N2  registro ──► N2b  🔴 fix emittente
 │                                                              │
 │                                                              ▼
 │                                                        N3  chiave documento
 │                                                        ⭐ qui il documento è separato
 │
 ├─ N4  resi_righe_accrediti ──► N5  tracciabilità riga↔riga
 │
 └─────────────────► N6  la partita sottrae  🔴  ──► N7  ri-consegna
                          (parità PRIMA di N7)          │
                                                        ▼
                                          N8  la madre  🔴  ──► N9  la coda
                                                        │
                                                        ▼
                                          N10 legame ──► N11 presidi + seed ──► N12 doc
```

⭐ **Fino a N5 compreso il sistema non cambia comportamento**: si aggiungono un
asse con un solo valore in uso, una tabella vuota e tre colonne nullable. Il
primo momento in cui qualcosa fa una cosa diversa è **N6**, e ci si arriva con
la fotografia in mano.

⚠️ **N8 e N11 vanno insieme**: il verbo e la riclassificazione del Backlog sono
**la stessa decisione vista da due punti**. Rilasciarne uno solo produce
l'applicazione che si contraddice — il difetto descritto nel §9-bis.

⚠️ **N6 e N7 sono due changeSet distinti**, e non è pignoleria: la parità di N6
si misura prima che N7 cambi i numeri.

---

# PARTE III — L'ESECUZIONE

> Scritta il **2026-08-18**, subito dopo aver applicato le slice.
> **Ventitré changeSet**, `20260818-24` → `-46`. Applicati fino a `-45`;
> `-46` è da riapplicare (vedi §20.5).
>
> ⚠️ Qui non c'è il riepilogo di cosa è stato scritto — quello lo dicono i
> changeSet, che portano il loro perché in testa. Qui c'è **ciò che il piano
> non sapeva**: tre punti in cui scrivere il codice ha smentito il piano, e i
> residui veri.

## 20. Cronaca, correzioni e residui

### 20.0 Lo stato, slice per slice

Tutti i changeSet sono **applicati**. La colonna «esito» dice se la slice ha
fatto quello che il piano prevedeva, o se scrivere il codice ha smentito il
piano (le tre correzioni sono ai §20.2 → §20.4).

| Slice | changeSet | Esito |
| --- | --- | --- |
| **N0** fotografia | *(nessuno)* | ✅ presa come owner, 7 misure — §20.1. 🔴 Ha rivelato che la prima riga in coda è un **kit a tre componenti**: da lì la correzione §20.2 |
| **N1** asse natura | `-24` `-25` `-26` `-28` | ✅ `config.nature_doc_fiscale` + 4 colonne `natura_doc_id` + lock immutabilità. Slice **inerte** per costruzione: `DEFAULT FATTURA` |
| **N5** tracciabilità riga↔riga | `-27` | ✅ **anticipata**: le colonne prima di N1b, così la fn a 40 parametri si è DROPpata una volta sola invece di due |
| **N1b** la catena impara | `-29` | ✅ `fn_upsert_commessa_attivita` (DROP+CREATE) e `fn_emit_attivita_fatturabili_da_commessa` portano natura e riga rettificata. Tutti i chiamanti usano argomenti nominali: nessuno toccato |
| **N2** registro della natura | `-30` `-31` | ✅ mapping `(tipo_doc, natura) → (registro, serie)`; `fn_get_registro_id` cambia tipo di ritorno |
| **N2b** 🔴 fix emittente | `-32` | ✅ i sezionali intestati tornano raggiungibili. **Parità misurata**: zero registri intestati oggi → nessun documento cambia registro |
| **N3** chiave documento | `-33` `-34` | ✅ chiave a **11 elementi**; `serie` finalmente **scritta** dalla INSERT (non lo era mai stata). Presidiato da `test-chiave-fattura-tre-specchi-v1` |
| **N4** ponte accrediti | `-35` `-36` | ⚠️ **corretta**: i due tetti non hanno lo stesso proprietario — §20.2. Due colonne in più del piano (`qta_partita`, `gruppo`) |
| **N6** la partita somma | `-37` | ✅ colonna `rettificato`. **Parità piena** su tutte le partite (zero righe RETTIFICA prima) |
| **N7** ri-consegna dopo NC | `-38` | ✅ D-NC-4 implementata. Un numero cambia su 2 righe, dichiarato al §20.4-bis. Caso D del pgTAP di luglio **resta verde** |
| **N8** 🔴 la madre | `-39` | ⚠️ **corretta** nel tipo di ritorno — §20.4. Il resto come da piano |
| **N9** la coda | `-40` | 🔴 **non era «un LEFT JOIN»**: era un difetto nella distribuzione — §20.3 |
| **N10** legame documentale | `-41` | ✅ `fn_popola_fatture_rettifiche`, proiezione idempotente. ⚠️ Il **task di pipeline** che la chiama è BE-8 |
| **N11** presidi + seed | `-42` `-43` + CSV | ✅ `#RET:` nel classificatore push, 7ª condizione D-K, `motivi_fermo` riclassificato |
| **N12** doc e richieste | *(doc)* | ✅ 8 manuali nuovi, 10 aggiornati, doc di `fatture` **corretta** (indicava `tipi_doc_fiscale` per la natura). Richieste §17 tutte aperte |
| **seed** | `-44` `-45` `-46` | ✅ nature, sezionale NC + mapping, policy indici FK (`-46` corretto e riapplicato, §20.5) |

**Collaudo**: 2 pgTAP nuovi (22 asserzioni), 4 esistenti riallineati, baseline
`vendite` (188 file) e `script` (59) **senza regressioni** — §20.6.


### 20.1 N0 — la fotografia, presa come owner il 2026-08-18

Le tabelle hanno RLS: uno zero letto come applicazione non è un dato, è un
fail-closed. Queste sono lette come owner.

| # | Misura | Esito |
| --- | --- | --- |
| 1 | righe in coda accrediti | **3** — 2 `DOVUTA`, 1 `FACOLTATIVA` |
| 2 | corsia che ha fatturato le partite in coda | **entrambe**: la riga di reso 24 è fatturata dalla corsia ORD, le 5797/5799 dalla corsia DDT → ⭐ **D-NC-1 è quotidiano**, il pgTAP non deve costruirsi il caso: esiste |
| 3 | partite con più righe di fattura a prezzi diversi | **5**, tutte con 3 righe e 3 prezzi distinti → D-NC-5 è esercitabile su dati veri |
| 4 | attività in coda con `fattura_riga_id` NULL | **0 su 41** → il guard è una cintura, non una toppa: nessun dato lo attraversa oggi |
| 5 | righe di ri-consegna | **6**, su 3 righe di reso (una riga di reso ne ha due: la ripartizione greedy serve davvero) |
| 6 | conteggio del tab Backlog, area `RESI` | **1** → dopo la riclassificazione diventa **4**. `valore_fermo` è NULL su tutte, già oggi |
| 7 | registri con `utility_id` o emittente non nulli | **0** → il difetto del §12.4-bis.4 era latente e **non teorico**: zero occorrenze, e nulla lo impediva |

🔴 **E la misura 2 ha rivelato una cosa che il piano non prevedeva**: la prima
riga in coda — la 24, quella costruita a mano il 2026-08-17 validando DL-27 —
è un **articolo composito con tre componenti**, ciascuno con la sua riga di
fattura a prezzo diverso (1, 2 e 14 euro). Il kit non è un caso di scuola da
coprire per completezza: è il **caso più comune della coda di oggi**. Da lì
viene la correzione §20.2.

### 20.2 🔴 Correzione 1 — i due tetti non hanno lo stesso proprietario

Il §15 (N4) mette **entrambi** i tetti nel guard del ponte. **Non regge sul
kit**, e lo dimostra la prima riga della coda:

```text
la MERCE si misura in UNITÀ PADRE        →  accredito dovuto = 1
il DOCUMENTO in unità di riga di fattura →  tre righe di ponte, qta 1+1+1
```

Un tetto «Σ qta per riga di reso ≤ accredito dovuto» valutato **riga per riga**
direbbe «3» dove la merce dice «1», e rifiuterebbe il secondo componente di un
accredito perfettamente legittimo. È lo stesso motivo per cui
`vw_af_merce_per_riga` calcola `quantita_padre = max(quantita / coeff_qta)`
invece di sommare i componenti.

✅ **Ciascun tetto vive dove è esattamente definibile:**

| Tetto | Chi lo tiene | Forma |
| --- | --- | --- |
| **DOCUMENTO** — Σ qta per riga di fattura ≤ qta della riga | `trgfn_resi_accrediti_guard` | `≤`, riga per riga, vale anche contro una scrittura diretta |
| **MERCE** — Σ unità padre = accredito dovuto | `fn_accredita_riga_reso` | **uguaglianza** (D-NC-6), perché è l'unica a sapere quando l'operazione è finita |
| doppione esatto | `UNIQUE (resi_riga_id, fattura_riga_rettificata_id)` | il doppio click |

⚠️ **Non è un tetto in meno**: è lo stesso tetto messo dove può essere vero.

⭐ E ne discendono due colonne che il piano non nominava: `qta_partita` (la
quota in unità di merce, accanto a quella di documento) e **`gruppo`** —
perché `qta_partita` va sommata **una volta per unità consumata**, non una per
riga, e i due casi che lo impongono tirano in direzioni opposte e coesistono:

```text
kit           →  N righe con la STESSA quota padre   →  sommarle la moltiplica
consumo LIFO  →  N righe con quote padre DIVERSE     →  vanno sommate
```

### 20.3 🔴 Correzione 2 — N9 non era «un LEFT JOIN», era un difetto

Il §15 (N9) descrive la slice come *«un `LEFT JOIN` per esporre
`gia_accreditato`»*. **Non basta**, e si è visto provando la madre su dati veri.

La coda ripartisce l'accredito della **partita** fra le righe di reso con una
finestra `ORDER BY resi_riga_id`, e quella finestra **non sapeva nulla degli
accrediti già fatti**. Misurato sulla partita 17163 (accredito 8, due righe di
reso da 5 e da 3):

```text
prima                 5797 → 5   ·  5799 → 3            ✅
accredito 5797, poi emissione: l'accredito della partita scende a 3
dopo, col difetto     5797 → 3   ·  5799 → 0 (sparita)  🔴
```

Cioè: **la riga già accreditata torna in coda a chiedere altri 3**, e la riga
che quei 3 li deve davvero **esce dalla coda**. La madre respinge la prima
(`E_ACCREDITO_GIA_ESEGUITO`) e la seconda non è più raggiungibile: la quota
resta lì per sempre.

⚠️ **È la malattia per cui questo cantiere esiste** (§2), in una forma nuova —
creata proprio dal rimedio.

✅ La correzione: la finestra si applica alla quantità **ancora accreditabile**
(`quantità − già accreditato`), non alla quantità resa.

⭐ **E regala una cosa che il §12.6-E dava per impossibile.** Quel paragrafo
descriveva la finestra fra il verbo e l'emissione, in cui la riga è ancora in
coda e un secondo click sarebbe coerente col conto. Con la quota già
accreditata nella distribuzione, **la riga esce dalla coda AL VERBO**:
l'idempotenza smette di dipendere da una finestra temporale e diventa un numero
che è già sceso.

### 20.4 ⚠️ Correzione 3 — il tipo di ritorno della madre

Il §15 (N8) scrive `RETURNS bigint`. Non basta a dire il risultato: con D-NC-5
un accredito produce **più rettifiche**, e non per scelta — se l'accredito
dovuto copre due righe di fattura a prezzi diversi ne nascono due, e su un kit
ne nasce una per componente. Un `bigint` dovrebbe sceglierne una (mentirebbe) o
contarle (non servirebbe).

✅ `RETURNS TABLE(accredito_id, commessa_attivita_id, fattura_riga_rettificata_id,
qta, qta_partita)`: una riga per rettifica creata.
⚠️ Chi la modificherà: `CREATE OR REPLACE` **non cambia** una `RETURNS TABLE`.

### 20.4-bis ⚠️ Un numero che cambia, e va saputo

`vw_partite_merce.consegnato` su una riga di **RI-CONSEGNA** smette di essere la
quantità della riga di DDT e diventa **la quota che ha cambiato casa** — cioè 0
finché non c'è una nota di credito. Sui dati di oggi sono **due righe**
(`ddt_righe` 524 e 525: da 6 e 2 a 0 e 0), entrambe con `differenza` NULL prima
e dopo, quindi **nessun consumatore che calcola cambia risultato**.

⭐ Ed è una correzione, non un effetto collaterale: `consegnato` è la base
**contabile** della partita, non la quantità fisica (sull'origine vale già
`dr.quantita + riconsegnato`). Contando i pezzi ri-consegnati sia sull'origine
sia sulla riga nuova, la somma delle partite superava la merce realmente uscita
— 25 contro 17 — e l'invariante che il pgTAP deve asserire («i pezzi si
spostano, non si moltiplicano») **non era vero**. Ora lo è. La quantità fisica
resta dov'è sempre stata: `vendite.ddt_righe.quantita`.

### 20.5 Cosa resta da fare, in ordine

1. ✅ **`20260818-46` applicato.** Era fallito al primo migrate, e vale la pena
   che resti scritto: `chk_fk_index_policy_dll_command_forma` pretende un
   `CREATE INDEX IF NOT EXISTS …` ben formato **su ogni riga**, anche a
   `consentito=false`. Non è pedanteria del vincolo — con il flag a `false` la
   procedura **non ignora** il comando: ne estrae il **nome** ed esegue il
   `DROP`. Una cella vuota le toglierebbe il solo dato che le serve. Corretto e
   riapplicato: cinque indici creati, `dbops.vw_fk_senza_indice` non riporta
   più nessuna FK scoperta fra quelle del cantiere;
2. **Confermare i quattro valori del sezionale NC** (§14.3), che sono seedati
   con un default dichiarato: `codice` `NC`, `descrizione` «Note di credito»,
   `serie_default` vuota (il registro è già distinto), `reset_policy` `ANNUALE`.
   Il registro **non** è per emittente. Sono quattro celle di CSV;
3. **Le richieste del §17**, tutte ancora aperte. Le due che bloccano il giro
   end-to-end sono **BE-4** (il generatore righe non aggrega le rettifiche e
   copia prezzo/sconto/IVA dalla riga rettificata) e **BE-5** (scrive
   `riga_rettificata_id`): senza, la nota di credito nasce ma le sue righe non
   sono gemelle di nulla. **BE-6** (rigenerare `error_policies_generated.py`)
   tiene rosso un cancello finché non è fatta;
4. **`NOTA_DEBITO` non ha mapping registro**, ed è voluto: `fn_get_registro_id`
   risponde `E_CONFIG_MANCANTE`. Nessuno ha ancora deciso su quale registro
   numerarla, e ripiegare su quello delle fatture la emetterebbe nel posto
   sbagliato in silenzio. È una riga di CSV il giorno in cui servirà.

### 20.6 Come è stato collaudato

* **verifica in transazione** (`BEGIN … ROLLBACK`) di tutte le slice prima di
  ogni consegna, con **parità misurata** su `vw_partite_merce`: l'unico
  scostamento è quello dichiarato al §20.4-bis;
* **`db/pgtap/vendite/test-fn-accredita-riga-reso-v1.sql`** — 14 test: il verbo,
  il segno negativo, il segmento della spedizione, il prezzo copiato, il ponte,
  l'uscita dalla coda al verbo, il doppio click, il **contratto del §2** (la
  partita pareggia), i guard e il tetto del documento;
* **`db/pgtap/vendite/test-vw-partite-merce-riconsegna-dopo-nc-v1.sql`** — 8
  test su D-NC-4, con il caso **senza** nota di credito accanto a quello **con**:
  la regola dev'essere inerte quando non c'è nulla da accreditare;
* ⭐ **entrambi costruiscono il caso passando dalla MADRE**, non inserendo la
  riga di rettifica a mano: al 2026-08-17 le righe `RETTIFICA` erano zero, e una
  fixture scritta a mano avrebbe potuto **confermare un ramo morto**;
* i pgTAP esistenti girati contro il codice nuovo: il **caso D** di
  `test-fn-list-ddt-da-pushare-contatore-v1` resta verde (è la garanzia che
  D-NC-4 non riapre il buco di luglio), e così
  `test-vw-resi-da-accreditare-contatore-v1`, `test-ponte-riconsegna-copre-riga-v1`,
  `test-porta-oneri-contatore-cieco-v1`. `test-vw-partite-merce-v1` chiedeva
  aggiornamento: il suo `columns_are` è un **contratto**, e passa da 21 a 23
  colonne.

---

# PARTE IV — IL PIANO BE/FE

> Scritta il **2026-08-18**, dopo il push del perimetro DB (PR #1295, commit
> `06b661061`). Copre le richieste del **§17.1** (backend) e **§17.2**
> (frontend), e nient'altro: `db/` non si tocca.
>
> **Metodo, e il suo limite dichiarato.** Ogni riga di questo piano è letta
> **contro il codice vivo** — `backend/apps/`, `frontend/src/`, i seed CSV, la
> documentazione auto-generata `docs/it/dbzero/`. Dove il §17 dava per
> da-fare qualcosa che risulta **già fatto**, o **descritto male**, sta scritto
> nel §21.2 con la misura accanto: è la parte che vale più dell'elenco.
>
> ⚠️ **Nessuna riga di codice è stata scritta.** Questo è il piano.

---

## 21. Il terreno, misurato

### 21.1 🔴 L'applicazione si contraddice **già oggi**, e questo cambia la priorità

Il §9-bis dice che tre posti raccontano lo stesso fatto — «merce resa già
fatturata» — e che *«nel momento in cui il rimedio esiste, tutti e tre devono
cambiare voce; cambiarne uno solo produce un'applicazione che si
contraddice»*.

**Il perimetro DB ne ha cambiato uno.** `20260818-42/-43` + il CSV hanno
portato `motivi_fermo` id 14 da `FISIOLOGICO` a `RECUPERABILE` **con l'azione**
(verificato nel diff del commit):

```text
- 14,MERCE_RESA_GIA_FATTURATA,…,FISIOLOGICO,NULL,140,true,{}
+ 14,MERCE_RESA_GIA_FATTURATA,…,RECUPERABILE,Emetti la nota di credito dalla coda accrediti,140,true,{}
```

Quindi, in questo momento, in-app:

| Dove | Cosa dice | Vero? |
| --- | --- | --- |
| Backlog fatturazione, area `RESI` | «Emetti la nota di credito dalla coda accrediti» | ⛔ **no**: il verbo non esiste in nessuna schermata |
| Pannello situazione merce (ordine e DDT) | «L'emissione della nota di credito non è ancora disponibile: il dato qui sotto è informativo» | ⛔ **no**: la madre `fn_accredita_riga_reso` esiste e funziona |
| Coda accrediti (`Vendite → Resi → Da accreditare`) | elenca, senza verbi | ✅ vero, ma è il posto dove l'azione **dovrebbe** essere |

⚠️ **Ne discende che BE/FE non è «il seguito» di questa slice: è ciò che chiude
una contraddizione già in esercizio.** Il §19 avvertiva che «N8 e N11 vanno
insieme»; N11 è passato da solo, e il debito è aperto da oggi.

### 21.2 Cosa il §17 dava per da-fare, verificato una richiesta alla volta

| # | Il §17 dice | Verificato contro il codice, oggi |
| --- | --- | --- |
| **BE-6** | rigenerare `error_policies_generated.py` **e** scrivere i messaggi di ripiego | ✅ **FATTO** (2026-08-18). 🔴 **E i codici erano NOVE, non otto**: il generatore ha portato dentro anche `W_MESSAGGIO_ARITA` (classe `AVVISO`, di un'altra slice DB), che mancava. 🔴 **E la mia riga qui era SBAGLIATA**: avevo scritto che i ripieghi non servivano perché i messaggi a catalogo portano `%s`. È l'opposto — vedi §21.2-bis |
| **BE-7** | la coda espone `gia_accreditato`: non ricalcolarlo in Python | ✅ **già servito, zero righe da scrivere**. `ResiRepository._list_coda` proietta `SELECT v.*`: `gia_accreditato` e `blocco_codice` sono **già** nel payload di `GET /resi/da-accreditare/` dal giorno del migrate. Il lavoro qui è **non** scrivere niente |
| **BE-9** | verificare che la pipeline risolva uno step per la natura nuova | ✅ **verificato: nessun seed serve**. La pipeline si risolve su `(stato_doc_fiscale_id, tipo_lotto, tipo_doc_fiscale_id)` e tutte e otto le righe di `fatturazione_pipeline.csv` hanno `tipo_doc_fiscale_id = null`. La **natura non è una dimensione del lotto** (§12.4-bis.8) e non entra nella risoluzione — era «probabilmente», ora è misurato |
| **FE-5** | label i18n del motivo `MERCE_RESA_GIA_FATTURATA` | ✅ **c'è già**, `it.json` e `en.json` riga 1823 (`"Merce resa già fatturata — accredito in attesa"`). La richiesta di luglio *«da prevedere da subito»* era stata onorata |
| **FE-6** | `valore_fermo` NULL non si renda come `0 €` | ✅ **vero per costruzione**: `CellaConfigurabile.formatValue` apre con `if (value == null) return ''`. ⚠️ Resta da **guardare** la card di classe, che fa `Number(c.valore_fermo_tot ?? 0)`: lì lo zero è un **totale di classe** e non una riga, ed è corretto. Verifica, non lavoro |
| **FE-2** | dal pannello un collegamento alla coda **già filtrata** | ⭐ Il predicato di filtro **esiste già** ed è collaudato: `VenditeRepository._list_coda_su_partite` filtra la stessa vista per `ddt_id` o, lato ordine, per il **fulfillment** della riga di DDT resa. È la stessa fonte da cui la partita deriva la sua origine. Il lavoro è **esporlo** come filtro della coda, non scriverlo |
| **BE-8** | il task di pipeline che popola `fatture_rettifiche` | ⚠️ **e va messo DOPO `numera_fatture`, non dopo la generazione righe** — §22.7. Il motivo non è nel brief e l'ho trovato leggendo il reset |
| **BE-3** | `post_permission` dedicato sul verbo | 🔴 il codename **non è a catalogo**: `config.azioni_processo.csv` si ferma a id 30 (`cambia_stato_commessa`). Fino al seed il verbo è **fail-closed**, cioè utilizzabile dal solo SUPER_ADMIN — stesso precedente di `code_manage` (§Coda lavori del catalogo BB). → **P-1** |
| **BE-4/BE-5** | il generatore non aggrega e copia dalla riga rettificata | ✅ confermate entrambe, ed è la slice più grossa del giro: §22.5 |
| **BE-10** | il drawer del lotto non deve assumere «sono tutte fatture» | ✅ confermata. ⚠️ E il perimetro è più largo di quanto suoni: **`natura_doc_id` non è nominata da nessun punto del backend** (0 occorrenze in `backend/apps/vendite/`), quindi non è che il drawer «assume»: **non ha il dato**. §22.6 |

### 21.2-bis 🔴 Una correzione a questo piano, pagata subito

> Scritta il 2026-08-18 dopo aver eseguito B0: il cancello ha smentito una riga
> del §21.2, e il *perché* dell'errore vale più della correzione.

**Cosa avevo scritto**: *«i messaggi di ripiego NON vanno scritti: tutti e otto
portano `%s`, e `error_messages_fallback.py` è per definizione la variante senza
segnaposto»*.

**Cosa dice il cancello**, eseguito: `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`
è rosso finché **ogni** codice vivo non ha il suo ripiego. Sono due regole
diverse, e le avevo fuse in una:

| Regola | Cosa dice davvero |
| --- | --- |
| `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` | **ogni** codice non ritirato **deve** avere un ripiego |
| `test_i_messaggi_di_ripiego_non_hanno_segnaposto` | e quel ripiego **non deve** contenere `%s` |

⭐ **Il `%s` nel messaggio a catalogo non è un'esenzione: è la ragione per cui il
ripiego esiste.** Il commento del test lo dice esattamente — *«questi messaggi si
mostrano QUANDO GLI ARGOMENTI NON CI SONO: uno con `%s` dentro arriverebbe a
video con il segnaposto in chiaro»*. Un codice con segnaposti a catalogo è
**quello che più ne ha bisogno**, non quello che se ne può privare.

⚠️ **Come ho sbagliato, ed è il pezzo da ricordare**: ho letto la *descrizione*
del modulo nel catalogo BB (*«la variante senza segnaposto»*) e ne ho dedotto il
perimetro, invece di leggere il **test che lo presidia**. La descrizione dice
com'è fatto il contenuto; il test dice chi deve esserci. Sono due domande
diverse, e solo la seconda è un cancello.

**Esito**: 9 ripieghi scritti (7 `E_ACCREDITO_*`, `E_RESO_ACCREDITO_SUPERA_RIGA_FATTURA`,
`W_MESSAGGIO_ARITA` — quest'ultimo sul precedente di `W_TXID_NOT_REGISTERED`, che
un ripiego ce l'ha già benché un `W_` non raggiunga mai il client). **3744 test
verdi.**

### 21.3 🔴 I sei prerequisiti che NON sono di BE/FE

> Regola di progetto: DDL, trigger, funzioni, migrations e seed non si toccano
> da qui — si scrive un brief al team DB su `dev/db-tid` e si **aspetta**.
> Questi vanno mandati **prima** di aprire il ramo BE.
>
> ✅ **Tutti e sei approvati da Tid il 2026-08-18** (sera). Il brief di
> passaggio è [brief-db-note-credito-prerequisiti-be-fe.md](brief-db-note-credito-prerequisiti-be-fe.md);
> le tre decisioni che li hanno chiusi sono nel §21.4.

| # | Cosa | Perché blocca | Blocca chi |
| --- | --- | --- | --- |
| **P-1** | Azione di processo **`accredita_riga_reso`** su area `vendite` (id 2), riga nuova in `config/azioni_processo.csv` — è la porta di un **documento fiscale**, precedente `carica_voce_manuale` (id 29) | senza, `post_permission` non risolve e il verbo resta accessibile al solo SUPER_ADMIN: si può sviluppare, non si può consegnare | B2, F1 |
| **P-2** | **Registry del task** `popola_fatture_rettifiche`: riga in `dbops.pipeline_task_registry` + `_impl` (`handler_code = popola_fatture_rettifiche_default`), e il task nei `processi` delle pipeline **4** e **6** (DEFINITIVA massiva e giornaliera), **fra `numera_fatture` e `stampa_documenti_lotto`** | `get_task_handler_code` interroga `dbops.fn_get_pipeline_task_implementation`: un handler Python senza la sua riga a registro non viene mai chiamato (`E_PIPELINE_TASK_HANDLER_NOT_FOUND`) | B6 |
| **P-3** | 🔴 **`script.fn_check_rinuncia_reversibile` è rimasta dormiente.** Il §20 non la nomina. Il commento vivo della funzione dice: *«QUANDO ARRIVERÀ LA SLICE NC: il divieto va aggiunto QUI, e si attiva da sé»*, e il punto d'innesto è ancora un commento vuoto. ✅ **Soglia decisa (D-NC-12): scatta AL VERBO** | **oggi si può riaprire una rinuncia su una quota già accreditata**, cioè sfalsare un documento fiscale. Non è un rilievo di stile: è il gate che la slice di luglio aveva lasciato apposta a questa | nessuno lato BE — è un buco di dominio da chiudere a DB, con il suo codice errore a catalogo |
| **P-4** | I **quattro valori del sezionale NC** (§20.5 punto 2) | ✅ **confermati da Tid il 2026-08-18**: `NC`, «Note di credito», `serie_default` vuota, `reset_policy` ANNUALE, registro **non** per emittente. Il seed applicato è già quello: nessun changeSet da scrivere, la voce si chiude | — |
| **P-5** | 🔴 **La madre `fn_annulla_accredito_riga_reso`** (D-NC-11): l'annullo dell'**accredito**, non del documento. Precondizioni **identiche a quelle della catena**: rettifica `NON_EMESSA` e non agganciata a un lotto vivo. Forma in §21.4 | senza, un click sbagliato è **definitivo**: il reset del lotto annulla il documento ma **non** l'accredito, che resta dovuto e rigenera la NC al giro dopo | B2-bis, F1 |
| **P-6** | 🔴 **Nessun registro è intestato a un emittente** — misurato il 2026-08-18: i tre registri (`Front-office` 3, `Back-office` 4, `NC` 5) hanno tutti `emittente_soggetto_ruolo_id` NULL, e gli **emittenti fiscali attivi sono 2**, che ✅ **emettono entrambi** (Tid). Non è un difetto della NC: vale sulle fatture da gennaio. §21.5 | due aziende emittenti **condividono lo stesso progressivo**, ed è un difetto fiscale in esercizio. La macchina sa separarli da `20260818-32` (N2b): manca la **configurazione**, non il codice | ⛔ non blocca BE/FE. Sul **registro NC** si separa subito e costa un registro + due righe di mapping; sui registri **3 e 4** è un cantiere suo, perché tocca numerazione già emessa |

📌 **Tutti e sei sono nel brief di passaggio**
[brief-db-note-credito-prerequisiti-be-fe.md](brief-db-note-credito-prerequisiti-be-fe.md),
pronto per `dev/db-tid`.

⚠️ **P-3, P-5 e P-6 questo piano li ha *trovati*, non ereditati.** La slice DB
si dichiara chiusa: uno dei tre era scritto nero su bianco come «da attivare
quando arriva la NC», gli altri due non erano scritti da nessuna parte.

### 21.4 ✅ Le tre decisioni del 2026-08-18 (sera)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-NC-11** | Dopo il verbo non esiste nessuna strada indietro. È voluto? | ✅ **No: serve l'annullo.** 🔴 **CORRETTA da Tid subito dopo**: *«valgono le stesse regole della fatturazione, il processo deve finire nella pipeline»* — non un verbo parallelo. Forma esatta qui sotto |
| **D-NC-12** | La soglia del gate `fn_check_rinuncia_reversibile`: quando scatta «emessa»? | ✅ **AL VERBO**: non si riapre una rinuncia appena esiste la riga in `resi_righe_accrediti`. Una soglia sola in tutto il giro, coerente con «la riga esce dalla coda al verbo» (§20.3) |
| **P-4** | I quattro valori del sezionale NC | ✅ **Confermati i default**: `NC`, «Note di credito», `serie_default` vuota, `reset_policy` ANNUALE, registro non intestato. ⚠️ **E la domanda era mal posta**: vedi §21.5 |

#### 🔴 D-NC-11, nella forma corretta — *il documento e l'accredito sono due cose*

La prima stesura proponeva una madre di annullo «limitata alla finestra
pre-emissione», come se fosse **una** strada indietro. Ne sono **due**, e
confonderle costruirebbe la seconda pipeline che tutto questo brief evita.

```text
ANNULLARE IL DOCUMENTO   →  ESISTE GIÀ, ed è la pipeline
   reset del lotto in DRAFT: fn_elimina_fattura_da_lotto_draft /
   fn_riporta_lotto_a_draft / fn_annulla_lotto_da_draft
        └─► fn_cleanup_fatture_by_ids riporta commesse_attivita a NON_EMESSA
            e sblocca le attivita_fatturabili
   ⭐ quindi la rettifica torna disponibile e il giro dopo RIGENERA la NC.
      Ed è corretto: la merce resa non è cambiata, l'accredito è ancora dovuto.
   ⛔ oltre la numerazione non si annulla niente: come qualunque fattura.

ANNULLARE L'ACCREDITO    →  MANCA, ed è il caso «ho cliccato la riga sbagliata»
   sta A MONTE del documento, e non è ciò che il reset fa.
```

✅ **Forma di `fn_annulla_accredito_riga_reso(p_resi_riga_id)`**, con le
precondizioni **prese dalla catena, non inventate qui**:

* ammesso **solo** se la rettifica è `stato_emissione = NON_EMESSA` **e** non è
  agganciata a un lotto vivo (`lock_in_fatturazione` falso, `fatturato` falso) —
  sono le stesse condizioni con cui la catena tratta qualunque attività non
  ancora emessa;
* **non cancella l'attività**: la porta a `stato_emissione = 'ANNULLATA'`, valore
  che tutte le porte verso fattura e cockpit già filtrano. ⭐ Precedente esatto:
  `ANNULLA riga manuale` sulle commesse (`POST /commesse/<id>/attivita/<att_id>/annulla/`,
  2026-07-28), con motivo obbligatorio tracciato;
* **cancella la riga di `resi_righe_accrediti`** — ed è l'unica cosa che non ha
  un precedente: senza, la coda resterebbe muta per sempre, perché è quella riga
  a farne scendere l'`accredito_dovuto` (§20.3).

⚠️ **Le due strade devono restare distinte, e vanno dette insieme**: dopo un
reset del lotto la NC **ricompare** al giro successivo. Chi vuole che
l'accredito non ci sia più deve annullare *l'accredito*, non il documento. Un
operatore che resetta il lotto aspettandosi di aver cancellato l'accredito
troverebbe la nota di credito il giorno dopo, e non capirebbe perché.

### 21.5 🔴 Il numeratore e l'emittente — la domanda P-4 era mal posta

> Rilievo di Tid, 2026-08-18: *«il numeratore non è collegato all'emittente? mi
> sembra veramente strano»*. Misurato subito, e il sospetto è fondato — ma il
> difetto **non è della nota di credito**.

**Cosa la macchina sa fare, dopo N2b** (`20260818-32`): `fn_build_fattura_key`
passa oggi **emittente e utility** a `fn_get_registro_id`, che ha il fallback a
quattro livelli e sceglie il registro **più specifico** disponibile. Prima della
slice quei registri erano **irraggiungibili** — è esattamente il difetto che il
§12.4-bis.4 aveva trovato e che N2b ha corretto.

**Cosa la configurazione fa**, misurato il 2026-08-18 sul database:

```text
vendite.registri_fatturazione
  3  Front-office   emittente_soggetto_ruolo_id = NULL   serie_default R2
  4  Back-office    emittente_soggetto_ruolo_id = NULL   serie_default R1
  5  NC             emittente_soggetto_ruolo_id = NULL   serie_default (vuota)

anagrafiche.emittenti_fiscali attivi  →  2
```

🔴 **Ne discende che due aziende emittenti condividono lo stesso progressivo di
numerazione** — e non da oggi: vale sui registri **3 e 4**, cioè sulle
**fatture**, da gennaio. La nota di credito non introduce il problema: lo
eredita.

✅ **E il fatto che decide è arrivato (Tid, 2026-08-18): i due emittenti fiscali
attivi emettono ENTRAMBI documenti verso i clienti.** Quindi non è una
configurazione volutamente accorpata: è un **difetto fiscale già in esercizio**,
e la doc di `registri_fatturazione` lo dichiara da sempre — *«in presenza di più
aziende abilitate, la separazione dei registri evita collisioni di
numerazione»*.

✅ **La strada l'ha data Tid (2026-08-18), e il perimetro è più libero di quanto
avevo scritto: siamo solo in ambiente di test, quindi si fa la cosa giusta e
basta.** Nessun backfill, nessuna continuità di numerazione da conservare: si
intestano i tre registri all'emittente che li ha usati e si creano quelli del
secondo. È la regola generale del progetto — *non in produzione: breaking change
ammessi, niente fasi di compatibilità.*

⚠️ **Resta un solo vincolo, ed è di sequenza dentro l'apply**: nel momento in
cui il registro 3 diventa intestato, il livello 4 del fallback di
`fn_get_registro_id` — *«utility NULL e emittente NULL»* — non esiste più per
quel tipo documento, e un documento del secondo emittente risponde
`E_CONFIG_MANCANTE`. È il comportamento **giusto** (meglio fermarsi che numerare
sul registro dell'altra azienda), ma intestare i vecchi e creare i nuovi vanno
nello stesso changeSet, non in due.

⭐ **Sul registro NC, invece, si può fare subito e costa niente**: zero documenti
emessi, nessuna continuità da conservare. Ed è la forma già prevista dal
modello — il mapping `tipi_doc_fiscale_registri` ammette **più registri** per la
stessa coppia `(tipo_doc, natura)`, e `fn_get_registro_id` sceglie fra loro
proprio con l'emittente. Oggi il seed manda entrambi i canali sul registro **5**
(`FRONTOFFICE_NC` e `BACKOFFICE_NC` → 5): separarlo per emittente sono un
registro in più e due righe di mapping.

⚠️ **E la domanda P-4 era formulata male.** Ho chiesto *«il registro NC è per
emittente?»* proponendo come default *«no, allineato agli altri due»* — cioè
allineato a una configurazione che è **essa stessa la cosa da guardare**. La
domanda giusta è un'altra: **perché nessun registro lo è, con due emittenti
attivi?** È materia fiscale, non tecnica, e non si decide qui.

⭐ **Ma c'è una ragione di tempo che vale la pena mettere agli atti**: il
registro NC ha **zero documenti**. È l'unico momento in cui separarlo per
emittente costa **tre righe di CSV** e nessuna decisione su numeri già emessi.
Sui registri 3 e 4 quel momento è passato.

⚠️ **Quanto sia già successo non l'ho potuto misurare**: `vendite.fatture` ha la
RLS, e leggendo come applicazione senza GUC operatore il conteggio delle fatture
numerate esce **0** — che è un **fail-closed, non un dato** (è la trappola
descritta in `feedback_rls_query_contesto_sistema`). Se esistono già fatture
numerate su **entrambi** gli emittenti, separare i registri adesso significa
anche decidere cosa fare della numerazione già emessa: è la parte che deve
guardare una persona, con i registri IVA in mano.

---

## 22. Il piano backend — nove slice

> Ordine di lettura, non di consegna: la sequenza è nel §25. Ogni slice dichiara
> i building block che riusa — la prima difesa contro le duplicazioni.

### B0 — ✅ FATTO — Il dizionario dei codici torna in pari *(BE-6)*

```bash
./manage-env.sh genera_error_policies          # riscrive il modulo
./manage-env.sh genera_error_policies --check  # deve uscire pulito
```

* ⛔ `error_policies_generated.py` **non si edita a mano**: la sorgente è
  `config.vw_codici_errore_identita`;
* i codici e la loro classe (già decise dal team DB):

  | Codice | Classe | HTTP derivato |
  | --- | --- | --- |
  | `E_ACCREDITO_NON_IN_CODA` | `NON_ESEGUIBILE` | 422 |
  | `E_ACCREDITO_SENZA_SPEDIZIONE` | `TECNICO` | 500 |
  | `E_ACCREDITO_GIA_ESEGUITO` | `CONFLITTO_STATO` | 409 |
  | `E_ACCREDITO_ATTIVITA_NON_FATTURATA` | `NON_ESEGUIBILE` | 422 |
  | `E_ACCREDITO_KIT_NON_MISURABILE` | `NON_ESEGUIBILE` | 422 |
  | `E_ACCREDITO_QUOTA_NON_COPERTA` | `NON_ESEGUIBILE` | 422 |
  | `E_ACCREDITO_SEGMENT_DUPLICATO` | `CONFLITTO_STATO` | 409 |
  | `E_RESO_ACCREDITO_SUPERA_RIGA_FATTURA` | `CONFLITTO_STATO` | 409 |

* 🔴 **E i ripieghi vanno scritti, uno per codice** — la riga opposta era mia ed
  era sbagliata (§21.2-bis): il `%s` a catalogo è la *ragione* del ripiego, non
  la sua esenzione. Nove messaggi, senza segnaposto;
* è la **prima** slice perché tiene rossi i cancelli
  `test_error_codes_db_policy_guardrail` e `test_error_policies_divergenza_db`
  (opt-in `ZEROERP_TEST_DB_E2E`, **acceso in CI**): finché non è fatta, ogni PR
  che tocca il backend eredita un rosso che non è suo.

### B1 — Il verbo: repository + service *(BE-1)*

```text
ResiRepository.accredita_riga_reso(resi_riga_id) -> list[dict]
    SELECT * FROM vendite.fn_accredita_riga_reso(%s)
```

* ⚠️ **`RETURNS TABLE`, non uno scalare** (§20.4): la madre restituisce **una
  riga per rettifica creata** — su un kit ne nascono N, sul consumo LIFO
  altrettante. Un `fetchone()` qui perderebbe in silenzio tutte le righe dopo
  la prima. `rows_to_list(cursor)`, non `fetchone_scalar`;
* service `resi_service.accredita_riga_reso(resi_riga_id)`: **una sola
  `SELECT fn_()`** → atomica per costruzione, **nessun `transaction.atomic()`**
  (regola api.md §Atomicità: l'orchestrazione Python non c'è);
* traduzione errori con il context manager **già esistente** nel modulo,
  `_db_errors("accredita_riga_reso")` (`make_db_errors_translator`): i codici
  di dominio arrivano dal campo strutturato `CONSTRAINT` su `P0001`, letto una
  volta sola da `db_error_fields` — **non** si riscrive l'estrazione;
* ⚠️ **nessun guard applicativo** che ripeta la madre: «è in coda», «l'attività
  è finita in fattura», «non già accreditata» sono nel DB. Replicarli in Python
  è logica duplicata fra i livelli (filosofia DB-first, §Principi di api.md).

### B2 — L'endpoint, massivo dal primo giorno *(BE-2, BE-3, D-NC-7)*

```text
POST /api/v1/vendite/resi/accrediti/
body: { "resi_riga_ids": [5797, 5799, …] }
```

✅ **Un endpoint solo, e la riga singola è una lista di uno.** Due superfici
che chiamano lo stesso verbo divergono su permessi, conferme e forma
dell'esito — è l'argomento 2 del §12.7-ter, applicato al backend. E il
frontend che leggesse due forme di risposta (scalare per uno, esito
aggregato per N) avrebbe due strade da tenere allineate per sempre.

* base class `DomainAPIView`, `area_funzionale = "vendite"`,
  **`post_permission = "accredita_riga_reso"`** (→ P-1);
* `handle_post_json(..., require_idempotency_key=True)`: modifica stato, quindi
  la chiave è obbligatoria (api.md §Idempotency-Key);
* il fan-out è **`run_fan_out`** di `apps/core/services/fan_out.py`, **mai un
  ciclo scritto a mano** (BE-2): porta il savepoint per elemento, il log dello
  stack una volta per tutte e l'esito a tre stati;
* forma della risposta:

  ```json
  { "data": { "esito": "PARZIALE", "totale": 20, "ok": 19,
              "accrediti": [ … righe della madre … ],
              "falliti": [ {"resi_riga_id": 5799,
                            "codice": "E_ACCREDITO_GIA_ESEGUITO",
                            "messaggio": "Riga di reso 5799: accredito gia' eseguito."} ] } }
  ```

* ⚠️ **`PARZIALE` è `200`, non un errore.** Il verbo non è l'atto fiscale (il
  documento nasce dopo, nel giro): un esito parziale non lascia mai mezzo
  documento, lascia righe non lavorate che restano in coda. Sollevare
  butterebbe via anche i 19 riusciti;
* ⚠️ **lista vuota rifiutata**, non trattata come «tutte»: stesso criterio di
  `parse_gruppi` per l'emissione mirata, dove indovinare male significa
  lavorare un perimetro che nessuno ha chiesto. E un **cap** sulla lunghezza,
  sul modello di `MAX_GRUPPI_EMISSIONE_MIRATA`;
* ⚠️ `resi_riga_ids` va **normalizzato e deduplicato con ordine preservato**:
  lo stesso id due volte nello stesso body produrrebbe un
  `E_ACCREDITO_GIA_ESEGUITO` autoinflitto, che a video sembra un difetto del
  sistema e invece è il body.

### B2-bis — L'annullo dell'accredito *(D-NC-11)*

```text
POST /api/v1/vendite/resi/<reso_id>/righe/<riga_id>/annulla-accredito/
body: { "motivo": "…" }        ← obbligatorio, come sull'annullo riga manuale
```

* thin wrapper sulla madre **P-5** `fn_annulla_accredito_riga_reso`: una sola
  `SELECT fn_()`, nessun guard applicativo che ripeta le precondizioni;
* stesso `post_permission = "accredita_riga_reso"` — chi può accreditare può
  disfare il proprio click. ⚠️ **Non** un permesso nuovo: due codename per le due
  facce dello stesso atto si sfilano al primo profilo configurato a mano;
* ⚠️ **Il messaggio d'errore quando la precondizione non regge deve dire quale
  strada prendere**, e sono due diverse: se la rettifica è già in un lotto vivo
  la risposta è «resetta il lotto» (che però **non** annulla l'accredito), se è
  già emessa la risposta è «non si può». Un unico «operazione non consentita»
  manderebbe l'operatore a cercare la strada sbagliata;
* ⛔ **Non si aggiunge nessuna strada per annullare il DOCUMENTO**: quella è la
  pipeline, esiste, ed è la stessa delle fatture (§21.4).

### B3 — ✅ FATTO — La coda si filtra sul documento *(prerequisito di FE-2)*

`GET /resi/da-accreditare/?ddt_id=…` e `?ordine_id=…`.

Il repository ha già il posto dove infilarli: `_list_coda(..., extra_conditions,
extra_params)`, che la coda accrediti usa già per il filtro `etichetta`.

⭐ **E il predicato non va inventato**: è quello di
`VenditeRepository._list_coda_su_partite`, che alimenta le sezioni «da
accreditare» / «da ri-consegnare» del pannello situazione merce —

```sql
-- DDT
v.ddt_id = %s
-- ORDINE (il legame è il FULFILLMENT della riga di DDT resa)
EXISTS (SELECT 1 FROM vendite.ordini_righe_fulfillment f
          JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
         WHERE f.ddt_riga_id = v.ddt_riga_id AND orr.ordine_id = %s)
```

#### ✅ Esito (2026-08-18)

Predicato estratto in `apps/vendite/db/_coda_documento_filtro.py`
(`filtro_coda_per_documento`), consumato dai **due** chiamanti: il pannello
(`VenditeRepository._list_coda_su_partite`) e le code
(`ResiRepository._list_coda` via `_aggiungi_filtro_documento`). Query param
`?ddt_id=` / `?ordine_id=` su **list ed export** di **entrambe** le code,
documentati nei quattro `@extend_schema`.

⭐ **Fatto su entrambe le code, non solo sugli accrediti.** Il pannello mostra «da
accreditare» e «da ri-consegnare» una sopra l'altra: dare il collegamento
filtrato a una sola sarebbe un'asimmetria visibile a colpo d'occhio — e la regola
del progetto è simmetria piena subito, non rinviata a una fase 2.

⚠️ **I due id sono alternativi**, con guard nel service (`E_RESO_VALIDAZIONE`) e
il repository che **non viene chiamato affatto**: accettarli insieme sarebbe due
domande in una, con la seconda che restringe la prima in silenzio.

⚠️ **E l'export li dichiara** nel foglio «Filtri applicati», per la stessa
ragione per cui dichiarava già l'etichetta: un file estratto dalla coda filtrata
su un documento, senza quella riga, si legge come la coda intera.

**Verificato sui dati** (2026-08-18, contesto operatore — le viste hanno la RLS):

```text
coda accrediti = 3 righe
  DDT 140   → 1     ORD 240   → 1
  DDT 15848 → 2     ORD 19151 → 2
  somma per DDT = totale ✅        id inesistente → 0, non «tutto» ✅
```

🔴 **E una cosa trovata scrivendo i test**: `apps/vendite/tests/db/` **non aveva
`__init__.py`**, quindi i 6 test del BB nuovo non venivano scoperti dalla suite —
passavano solo se invocati per nome. Un test che non gira è peggio di un test
assente: è copertura che *sembra* esserci. Aggiunto il file; ora la suite ne
conta 1557 su `apps.vendite` invece di 1551.

⚠️ **L'unica rete sulla stringa SQL sono i test del BB**: i test del service
situazione merce mockano il repository, quindi il predicato non lo attraversano.
Verificato per **mutazione** (sostituendo `v.ddt_id` con `v.ordine_riga_id`
diventano rossi) e a mano sui dati, non per lettura.

**Collaudo**: 6 test nuovi sul BB + 6 sul service, **3757 verdi** sull'intera
suite.

✅ **REGOLA DEL 2 — approvata da Tid il 2026-08-18.** Questa è la
**seconda** occorrenza dello stesso predicato su `vw_resi_da_accreditare` /
`vw_resi_da_riconsegnare`. Se le due copie divergono, il pannello dirà «8 da
accreditare» e la coda filtrata ne mostrerà 7 — e nessun test lo intercetta,
perché ognuna delle due è coerente con sé stessa. Proposta: estrarre il
predicato in un helper condiviso di `apps/vendite/db/` e farlo consumare da
entrambi i chiamanti. **Ok ricevuto: si estrae.**

⚠️ I query param si normalizzano con `qp_int_optional(raw, name)` (strict:
`?ddt_id=banana` → 400, non un filtro che sparisce in silenzio), e vanno
aggiunti anche all'**export** della coda, o l'export di una coda filtrata
esporterebbe tutto.

### B4 — ✅ FATTO — Il generatore righe impara la rettifica *(BE-4 + BE-5)*

È la slice che decide se la nota di credito è un documento **leggibile accanto
alla fattura che rettifica** o un foglio di carta con dei numeri sopra.

**1. I dati devono arrivare al generatore.** `AttivitaDaFatturare` e
`GroupAttivitaInput` (`apps/vendite/db/pipeline_repository.py`) guadagnano
`tipo_movimento`, `fattura_riga_rettificata_id` e i valori **della riga
rettificata**, letti con un `LEFT JOIN vendite.fatture_righe fr ON fr.id =
a.fattura_riga_rettificata_id` in `list_attivita_da_fatturare` e
`batch_get_group_attivita_inputs`: `fr.prezzo_unitario`,
`fr.sconto_percentuale`, `fr.iva_id`.

**2. Le rettifiche NON si aggregano** (§12.6). Nel `bucket` di `_aggrega` la
chiave di una rettifica è **l'identità dell'attività**, non la sua forma:

```text
attività NORMALE   →  bucket = (fattura, group_key, kit_*)            invariato
attività RETTIFICA →  bucket = (fattura, group_key, kit_*, attivita_id)
```

⚠️ **E `_chiave_ordinamento` deve seguire**, o il `riga_nr` cambia fra due
rigenerazioni dello stesso lotto: due rettifiche con articolo, prezzo e uom
identici oggi sarebbero indistinguibili per l'ordinamento, e l'ordine delle
righe di una nota di credito diventerebbe casuale. Va appeso
`fattura_riga_rettificata_id` (e, a parità, `attivita_id`) in coda alla tupla.

**3. Prezzo, sconto e IVA si copiano dalla riga rettificata** — strada **β**
del §12.6, ed è *«più fedele alla richiesta: la copia avviene nel momento in cui
il documento si scrive, leggendo il documento che rettifica»*.

🔴 **La trappola gemella, e va detta prima di scrivere**: il prezzo copiato deve
entrare **anche nella chiave di raggruppamento**, non solo nell'`INSERT`. Se la
chiave prendesse `gi.prezzo_unitario` (dell'attività) e la riga scrivesse
`fr.prezzo_unitario` (della fattura), si ricadrebbe esattamente nella
trappola che il §12.4-bis.3 descrive per la serie: *«se la chiave lo calcola e
la INSERT non lo scrive, le due metà si annullano»*. Oggi i due numeri
coincidono per costruzione — ed è precisamente il motivo per cui l'errore non
si vedrebbe.

**4. `riga_rettificata_id` e `sconto_percentuale` si scrivono all'INSERT**
(BE-5, §12.6-bis): due array nuovi in `batch_insert_righe_and_mark` e due
colonne nella `INSERT ... SELECT`.
⚠️ Il guard `E_BATCH_ARRAY_DISALLINEATI` che già presidia il metodo va esteso
alle due liste nuove: il commento vivo lo dice bene — *«`unnest` con array di
lunghezze diverse NON solleva: riempie di NULL i più corti»*, e il risultato
sarebbero righe di fattura silenziosamente sbagliate.

**5. Il guard `fattura_riga_id IS NULL`** (§12.6): un'attività mai finita in
fattura non ha un prezzo da cui accreditare. Lo solleva già la madre
(`E_ACCREDITO_ATTIVITA_NON_FATTURATA`) al **verbo**; qui non va replicato — ma
se il generatore incontra una rettifica con `fattura_riga_rettificata_id`
NULL, quella è una **rottura di invariante**, non un caso: va fermata con un
errore parlante, non lasciata scorrere a prezzo zero.

**6. Cosa NON cambia**: `natura_doc_id` **non si scrive sulla riga**. Vive
sulla testata, e la testata la crea `fn_get_or_create_fattura_header` dalla
chiave a 11 elementi. Il generatore non deve saperne nulla.

#### ✅ Esito (2026-08-18) — e il rischio del kit, misurato invece che temuto

Fatto come progettato, con **una scelta di forma** che il piano non specificava e
**una trappola trovata scrivendo**.

⭐ **La forma: `fattura_riga_rettificata_id` sta NELLA CHIAVE di gruppo**, non in
un ramo `if` dentro `_aggrega`. Ne discende, senza scrivere altro, che due
rettifiche di righe di fattura **diverse** non si fondono mai — anche quando
articolo, prezzo, uom e IVA coincidono, che è il caso in cui l'errore sarebbe
invisibile. E due rettifiche della **stessa** riga restano aggregabili, il che è
corretto: la riga prodotta è comunque la gemella di quella, e il tetto per riga
di fattura lo tiene il guard DB.

🔴 **La trappola: `sconto_percentuale` ha `DEFAULT 0` a DB e finora la colonna
non era NOMINATA nella `INSERT`.** Nominarla passando `NULL` per le righe
normali l'avrebbe portata a NULL su **ogni** riga di fattura futura — un cambio
di comportamento silenzioso su tutto lo storico, per una colonna che serve alle
sole note di credito. Risolto con `COALESCE(d.sconto_percentuale, 0)` nella
`SELECT` della CTE: il default resta il default.

✅ **Il kit non è un rischio, ed è misurato**: al 2026-08-18 i componenti di kit
in `commesse_attivita` sono **15, tutti con `coeff_qta = 1.000000`** (letto in
contesto operatore — la tabella ha la RLS, e come applicazione senza GUC il
conteggio esce 0 e non è un dato). Quindi le quantità dei componenti sono
uguali fra loro e **R10 regge**, sia sul kit normale sia su quello di rettifica.
⚠️ La trappola resta **latente**: il giorno in cui un kit avrà un coefficiente
diverso da 1, `E_KIT_QUANTITA_DISOMOGENEE` fermerà la generazione **anche sul
percorso normale**. È un difetto pre-esistente, non di questa slice, e va
guardato quando succederà.

**Collaudo**: 10 test nuovi in `test_fatture_righe_service.py` (28 in tutto nel
file), **3745 verdi** sull'intera suite. ⭐ E i quattro test centrali sono stati
**verificati per mutazione**: azzerando il campo nella chiave diventano rossi —
senza quella prova sarebbero verdi per sottrazione, che è il difetto che il §16
mette in guardia di non commettere.

#### ⚠️ Il rischio specifico di questa slice: il kit, e non è teorico

La misura 2 del §20.1 dice che la **prima riga della coda è un kit a tre
componenti** con tre prezzi diversi (1, 2 e 14 €): *«il kit non è un caso di
scuola da coprire per completezza: è il caso più comune della coda di oggi»*.

E nel generatore c'è un guard che il kit di rettifica non ha mai incontrato:
`_guard_quantita_kit_omogenee` (regola **R10**) pretende che i componenti che
confluiscono nella stessa riga padre portino **la stessa quantità**, perché
`vw_fattura_righe_esposte` stampa `avg(qta)` come quantità del padre. La madre
scrive `p_quantita => -(v_quota * coeff_qta)`: **quantità diverse per
componente quando i coefficienti differiscono**.

⚠️ Con il punto 2 (niente aggregazione) ogni componente diventa un gruppo a sé,
quindi il guard confronta N gruppi dello stesso `kit_key`: se i coefficienti
non sono tutti uguali, `E_KIT_QUANTITA_DISOMOGENEE` **ferma la generazione**.
**Va provato sui dati, sulla riga 24 della coda, prima di dichiarare fatta la
slice** — non per lettura del codice. Se fallisce, la domanda da portare a Tid
è se R10 valga anche per una riga padre di rettifica, e non è una domanda che
si risolve nel backend.

### B5 — La natura del documento esce dal backend *(BE-10)*

Oggi **`natura_doc_id` non è nominata da nessun punto di `backend/apps/`**. Non
è che il drawer del lotto «assume che siano tutte fatture»: **non ha il dato**.

| Dove | Cosa aggiungere |
| --- | --- |
| `apps/core/db/dbops_repository.py` | `config.nature_doc_fiscale` nella whitelist del lookup generico. La tabella ha `id/codice_interno/codice/descrizione/attivo` → struttura standard, **nessun endpoint dedicato** (memoria `feedback_lookup_whitelist_first`) |
| lista fatture del lotto (`get_lotto_fatture`) | `natura_doc_codice` + `natura_doc_descrizione` via JOIN — display field lato BE, mai lookup client-side |
| dettaglio fattura (`vendite_service.get_fattura_dettaglio`) | idem in testata, accanto a `serie` che il servizio già proietta |
| esiti / liste fatture | idem dove la testata è già decodificata |

⚠️ E la conseguenza che il §12.4-bis.8 chiede di mettere agli atti: **un lotto
può contenere documenti di natura diversa**, e il verbo «numera» li numera
entrambi sui rispettivi registri. Il conteggio «N fatture» del drawer lotto
diventa «N documenti».

### B6 — Il task di pipeline che popola il legame documentale *(BE-8)*

Handler `_handle_popola_fatture_rettifiche_task` in `PipelineStepExecutor`,
registrato come `"popola_fatture_rettifiche_default"` nel `handler_registry`;
chiama `vendite.fn_popola_fatture_rettifiche(fattura_id)` per ogni fattura del
lotto (proiezione idempotente, `ON CONFLICT DO NOTHING`, ritorna quante coppie
ha aggiunto).

🔴 **Dove va, e perché non dove sembrerebbe.** L'istinto è metterlo subito dopo
`generate_fatture_righe`, dove il dato nasce. **Non si può**, e il motivo è nel
reset:

```text
fn_cleanup_fatture_by_ids  cancella, in ordine:
   note · riepiloghi_iva · fatture_righe · fatture_log ·
   fatturazione_lotti_fatture · fatture
                                   ⛔ e NON cancella vendite.fatture_rettifiche
```

`fk_fatture_ret_fattura` non è `ON DELETE CASCADE`: con la proiezione scritta
in DRAFT, il primo reset di lotto sbatterebbe su una violazione di chiave
esterna grezza, su una funzione che i tre chiamanti del reset
(`fn_annulla_lotto_da_draft`, `fn_elimina_fattura_da_lotto_draft`,
`fn_riporta_lotto_a_draft`) danno per infallibile.

✅ **Il task va nella pipeline DEFINITIVA, fra `numera_fatture` e
`stampa_documenti_lotto`** (→ P-2). Due ragioni, e la seconda non è meno
importante della prima:

1. **oltre la numerazione il reset non arriva** — i tre chiamanti del cleanup
   sono tutti `*_da_draft`, quindi la proiezione non incontra mai una
   cancellazione;
2. **la stampa viene dopo** — una TD04 porta `DatiFattureCollegate`, cioè
   numero e data del documento rettificato: il PDF va costruito **dopo** che il
   legame esiste, non prima.

⚠️ La dipendenza d'ordine va **dichiarata**, non affidata al seed:
`_TASK_ORDER_DEPENDENCIES["popola_fatture_rettifiche"] = ("numera_fatture",)`.
Il meccanismo esiste già (oggi ci vive `genera_scadenze_lotto` →
`ricalcola_iva_lotto`) e verifica la sequenza **prima** che il primo task
scriva.

⚠️ **Da verificare, non da assumere**: che nessun percorso di reset possa
raggiungere un documento **numerato**. Se ne esiste uno, la cancellazione della
coppia va chiesta al team DB dentro `fn_cleanup_fatture_by_ids` — non aggirata
in Python.

### B7 — Il legame riga↔riga si legge dal drawer fattura

Il dettaglio fattura (`GET /vendite/fatture/<id>/`) è il posto dove *«una nota
di credito si legge accanto alla fattura riga per riga»* (§12.6). Serve:

* in **testata**: la natura (B5) e i documenti rettificati, letti da
  `vendite.fatture_rettifiche` (numero + data + id, per il link);
* su ogni **riga**: `riga_rettificata_id` e la sua decodifica minima (numero
  fattura + `riga_nr` della gemella).

⚠️ **Ordine di lettura vincolante**, ed è la regola già scritta per questo
endpoint: la **testata è l'unico cancello di scope** — `vendite.fatture` ha la
RLS, `fatture_righe` e `fatture_rettifiche` **no**. Il legame si legge **dopo**
il cancello di testata, mai prima, o si espone il numero di un documento fuori
perimetro.

### B8 — I test

| Dove | Cosa |
| --- | --- |
| `apps/vendite/tests/services/test_resi_accrediti_service.py` | il service: mock del repository, traduzione dei codici DB, normalizzazione/dedup della lista, lista vuota rifiutata, cap |
| `apps/vendite/tests/api/test_resi_accrediti_api.py` | l'endpoint: `PARZIALE` → 200 con l'elenco dei falliti, `post_permission` negato → 403, `Idempotency-Key` mancante → 400 |
| `apps/vendite/tests/services/test_fatture_righe_service.py` (esistente) | 🔴 **il cuore**: una rettifica non si aggrega mai con un'altra; prezzo/sconto/IVA presi dalla riga rettificata; `riga_rettificata_id` scritto; `riga_nr` **stabile** su due generazioni dello stesso lotto; array allineati |
| smoke bash `backend/scripts/smoke-test-nota-credito.sh` | end-to-end reale: verbo → giro → documento. Con **cleanup proattivo all'inizio** (memoria `feedback_smoke_test_idempotenti`) |

⚠️ **`unittest.TestCase` con i mock**, non `django.test.TestCase`: oggi in
`backend/apps` nessun test dichiara un database, e il primo che lo dichiarasse
farebbe creare al runner un DB vuoto per **tutta** la suite, rompendo i tre
test end-to-end di `test_db_error_fields` in una PR che non c'entra niente.

---

## 23. Il piano frontend — sei slice

### F1 — 🔴 Il verbo nella coda accrediti *(FE-3, FE-4)* — il cuore

`ResiCodaTable.vue`, variante `accreditare`. Il componente è già una
`<ListaConfigurabile>` con lo scaffolding `useListaConfigurabilePage`: quasi
tutto quello che serve c'è.

| Pezzo | Building block da riusare | Nota |
| --- | --- | --- |
| selezione multipla | slot **`selection`** / `selection-header` di `<ListaConfigurabile>` + **`useSelezioneToggle`** | ⚠️ PrimeVue 4 non ha più il predicato per-riga: la checkbox è **custom per forza**, e la colonna è chrome del BB (non si personalizza, non si esporta). `selezionabili` = le righe con `blocco_codice == null` |
| gate del bottone | **`data.blocco_codice`** e `data.gia_accreditato`, già in riga | ⛔ **mai** una capability per riga di lista (§12.7): il gate si fa sui codici che la riga porta |
| permesso | `useActionPermission('accredita_riga_reso')` | il pulsante **sparisce** a chi non ha l'azione; il 403 del BE resta la difesa vera |
| azione di riga | `RowActionsMenu` + `MANAGE_ICONS` | accanto all'«apri reso» che c'è già |
| azione massiva | `extraActions` di `useListaConfigurabilePage` → `PageActionsBar` | etichetta con il conteggio della selezione |
| conferma | **`useConfirmAction`** | ⚠️ destructured e con callback **`onAccept`** (non `accept`): la forma sbagliata fallisce **in silenzio** (memoria `feedback_useconfirmaction_destructuring`) |
| chiamata | `useApiHandler.execute()` | ⚠️ solo per response axios — qui lo è |
| **annulla accredito** | `RowActionsMenu`, azione secondaria sulla riga | visibile **solo** se `gia_accreditato > 0` e la rettifica non è emessa. ⚠️ Il messaggio deve distinguere le due strade (§21.4): questo annulla **l'accredito**, non il documento — e resettare il lotto fa l'opposto, lascia l'accredito dovuto |

⚠️ **Il testo della conferma deve dire cosa succede davvero**, e non è ovvio:
il verbo **non emette** la nota di credito. Registra l'accredito e lo mette nel
giro di fatturazione; il documento nasce dopo. Una conferma che dice «emetti
nota di credito» promette un documento che l'operatore poi non trova.

⚠️ **E la finestra è breve, non nulla**: il giro di fatturazione gira su
worker/cron. Appena il verbo esiste, un giro non presidiato emetterà il
documento. È il motivo per cui **B4 deve essere finito prima** di F1 (§25).

### F2 — L'esito parziale si legge *(FE-4)*

`run_fan_out` risponde «19 su 20, una segnalata» — *«va mostrato, non
nascosto»*.

* **COMPLETATO** → toast success + `store.fetchList()`;
* **PARZIALE** → toast warn **+ un pannello/dialog con l'elenco delle righe non
  servite e il loro messaggio**. ⚠️ Un «19 su 20» che non dice **quale** non è
  interpretabile: l'operatore non sa cosa riprovare;
* **ERRORE** → toast error con i messaggi.

⭐ Il vocabolario `COMPLETATO | PARZIALE | ERRORE` è già in casa lato FE
(`ESITO_RICHIESTO` in `core/constants.js` per un altro dominio, e i tre valori
nei dialog di smistamento/ri-consegna): la severity si allinea a quelli, non se
ne inventa una quarta.

### F3 — Il pannello collega, e smette di dire il falso *(FE-1 + FE-2)*

Due cose nello **stesso** commit, o l'applicazione resta contraddittoria in
senso opposto.

**1. Via la nota temporanea.** `SituazioneMerceContenuto.vue` riga ~118 e le
due chiavi:

```text
frontend/src/locales/it.json : "vendite.situazione_merce.nc_non_disponibile"
frontend/src/locales/en.json : idem
```

Il commento sopra il `<Message>` lo dichiara *«TEMPORANEO PER COSTRUZIONE»* e
rimanda a questo brief: il promemoria ha funzionato, va onorato.

**2. Al suo posto, il collegamento alla coda filtrata.**

```text
"8 da accreditare  →  apri la coda"
router.push({ name: 'vendite-resi',
              query: { tab: 'da-accreditare', ddt_id: … | ordine_id: … } })
```

* `ResiView.vue` legge `route.query` e imposta `activeTab` + i filtri dello
  store della coda;
* ⚠️ **in `onActivated`, non solo in `setup`/`onMounted`**: la vista vive sotto
  KeepAlive, e un deep-link su una vista già in cache non rimonta niente
  (memoria `feedback_keepalive_onactivated`). L'applicazione dei filtri dev'essere
  **idempotente**;
* ⚠️ Il pannello vive dentro una **dialog** (`SituazioneMerceDialog`): il
  collegamento la chiude prima di navigare, o si resta con un overlay sopra la
  coda;
* ⚠️ **Filtrata sul serio**: una coda non filtrata è *«un percorso spezzato
  uguale, solo con un click in più»*. E la coda deve **dirlo** che è filtrata —
  un elenco corto senza spiegazione si legge come «non c'è quasi niente da
  fare».

⭐ **Il pannello resta una lettura** (D-NC-8): nessun verbo lì dentro. Non ha
permessi di scrittura, conferme, gestione errori né ricarico dopo l'azione, e
sono quattro cose che dovrebbe acquisire tutte insieme.

### F4 — La natura del documento a video *(conseguenza di B5)*

* **drawer fattura**: un `Tag` «Nota di credito» in testata. ⚠️ Non `danger`:
  una NC non è un errore. Severity neutra/info, e il totale negativo si mostra
  **come tale** — è il documento a essere di segno opposto, non un difetto;
* **drawer lotto, tab fatture**: colonna natura, e il conteggio del tab smette
  di chiamarsi «fatture». ⚠️ La riga di un documento a totale negativo non deve
  finire nella colorazione «anomalia» di nessuna lista;
* **liste fatture**: colonna natura (catalogo lista → richiesta al team DB se
  la si vuole personalizzabile; per ora basta il campo).

### F5 — Il legame documentale si vede *(conseguenza di B7)*

Nel drawer fattura: una riga di testata «Rettifica: FT 2026/1234 del …», e sulla
riga di NC il riferimento alla riga gemella. È la forma leggibile
dell'invariante del §12.6-bis — *«questo accredito vale 12 € perché la riga 7
della fattura 2026/1234 valeva 12 €»*.

### F6 — Le due verifiche, e l'annuncio *(FE-5, FE-6, §12.8)*

* **FE-5**: la chiave i18n del motivo Backlog **c'è già** → verificare, non
  scrivere;
* **FE-6**: `valore_fermo` NULL rende **stringa vuota** per costruzione
  (`CellaConfigurabile`) → verificare a video sull'area `RESI`, che è la prima
  volta che quel ramo si popola davvero;
* ⚠️ **L'annuncio**: il conteggio del tab Backlog area `RESI` passa da **1 a 4**
  (§20.1 misura 6) — ed è **già successo**, col seed di N11. Il §12.8 chiede di
  avvisare chi lo usa prima del rilascio: *«è comunque un salto da
  annunciare»*. Non è codice, è una riga di rilascio.

---

## 23-bis. 🔎 La revisione critica di B0/B3/B4 (2026-08-18)

> Richiesta di Tid a slice fatte: *«controllo critico alla ricerca e correzione
> di bug, codice fragile, duplicato e hardcoded»*. Sette rilievi, tutti
> **verificati** prima di toccare e **corretti**. Due erano pre-esistenti e uno
> era un test che non verificava niente — il mio.

| # | Rilievo | Gravità | Esito |
| --- | --- | --- | --- |
| **R-1** | `get_group_attivita_input` faceva `articolo_id=int(row[1])` su una colonna che è un **UUID** → `ValueError` a ogni chiamata. La gemella batch faceva `str()`. **Pre-esistente** | 🔴 bug | ✅ risolto **togliendo la seconda copia** — §R-1 |
| **R-2** | `?ddt_id=0` passava il parsing strict (0 è un intero valido) e produceva `WHERE v.ddt_id = 0`, cioè **coda vuota in silenzio**. Codice mio | 🟠 bug | ✅ guard `> 0` nel service, con test |
| **R-3** | Guard **asimmetrico** sulla coppia `(tipo_movimento, fattura_riga_rettificata_id)`: bloccava «RETTIFICA senza puntatore», lasciava passare «puntatore senza RETTIFICA». Codice mio | 🟠 fragile | ✅ guard simmetrico, estratto in un metodo unico usato **anche dalla facade** |
| **R-4** | `gk` usato per **due cose diverse** nella stessa funzione (la chiave dell'attività e quella del gruppo). Codice mio | 🟡 fragile | ✅ rinominata la prima in `chiave` |
| **R-5** | `_aggiungi_filtro_documento` + due call-site nei wrapper, per un filtro **comune alle due code** quando `_list_coda` è già la sede dei filtri comuni. Codice mio | 🟠 duplicato | ✅ spostato **dentro** `_list_coda`: −20 righe, un solo punto |
| **R-6** | `"NORMALE"` ×5 e `"RETTIFICA"` ×1 come literal, con **`TIPO_MOVIMENTO_NORMALE` già esistente** in `commesse_repository`. Codice mio | 🟠 hardcoded | ✅ costanti; aggiunta `TIPO_MOVIMENTO_RETTIFICA` accanto alla gemella, con il vocabolario del CHECK scritto |
| **R-7** | Cinque cast `%s::int[]` su colonne **bigint** (`fattura_id`, `uom_id`, `dest_billing_account_id`, `attivita_fatturabili.id`). **Pre-esistente**, nel blocco che B4 modificava | 🟡 fragile | ✅ allargati a `bigint[]`. ⚠️ Trigger **remoto** (gli id di oggi sono decine di migliaia contro un tetto di 2,1 miliardi): non era un difetto in esercizio, ma il cast giusto costa lo stesso |

### R-1 — 🔴 il bug e la duplicazione erano la stessa cosa

Le due letture di `GroupAttivitaInput` — singola e batch — proiettavano le
**stesse 19 colonne** in due `SELECT` copiate, con **due mapping riga→dataclass
scritti a mano**. E le due copie erano già divergenti: quella singola castava a
`int` un UUID.

⭐ **Non l'ho corretto in due punti: ho tolto il secondo punto.** Una costante
`_GROUP_ATTIVITA_SELECT` e una funzione `_group_attivita_input_da_row`, e il
difetto non ha più due posti in cui esistere. Il commento in testa alla costante
racconta perché, così chi la trova non la ri-espande.

⚠️ **Nessun test lo vedeva** — i test mockano il repository — e **nessun percorso
vivo la invocava**: la facade `pipeline_service.fn_group_attivita_fatturabili`
non ha chiamanti. Il difetto stava lì ad aspettare il primo. È il motivo per cui
l'ho corretto invece di lasciarlo: un ramo morto non è un ramo sicuro.

### 🔴 E un test mio che non verificava niente

Scrivendo R-2 ho aggiunto un `test_puntatore_senza_etichetta_rettifica_solleva`
che importava due simboli e li cancellava. **Verde, e verificava zero.** È
esattamente il difetto contro cui il §16 mette in guardia, commesso mentre lo
citavo. Rimosso, e il test vero scritto nel file giusto
(`test_fatture_righe_service.py`), dove ha accesso al fixture del generatore.

### Come sono state verificate le correzioni

* **mutazione sui guard nuovi**: sabotando il guard simmetrico e quello `> 0`, la
  suite dà **5 rossi**. Senza questa prova sarebbero verdi per sottrazione;
* **`EXPLAIN` sul DB vero** per l'SQL che i test non eseguono (i mock coprono il
  cursore, non la query): il `WITH … unnest(…)` di
  `batch_insert_righe_and_mark` pianifica, e la proiezione condivisa pianifica in
  **entrambe** le forme (`= %s` e `= ANY(%s)`) proiettando **19 colonne** — le
  stesse che il mapper indicizza da `row[0]` a `row[18]`;
* **3772 test**, un solo rosso: la divergenza `error_policies_generated.py`,
  che è il DB locale **avanti rispetto a git** (P-5 seminato dal team DB e non
  ancora pushato). Non è una regressione di queste slice.

⚠️ **Un difetto trovato nella struttura dei test, non nel codice**:
`apps/vendite/tests/db/` non aveva `__init__.py`, quindi i test del BB nuovo
**non venivano scoperti** dalla suite. Un test che non gira è copertura che
*sembra* esserci.

---

## 24. Sequenza e dipendenze

```text
  ┌─ P-1  azione processo ──────────────────────────┐   (team DB)
  ├─ P-2  registry task + processi pipeline 4 e 6 ──┤
  ├─ P-3  🔴 gate fn_check_rinuncia_reversibile ────┤
  └─ P-4  i quattro valori del sezionale ───────────┘

  B0  dizionario codici  ← per prima: tiene rossi due cancelli in CI
   │
   ▼
  B4  🔴 il generatore righe          ← PRIMA del verbo, non dopo
   │      (prezzo/sconto/IVA copiati · niente aggregazione · riga_rettificata_id)
   │      ⚠️ e il kit va provato sui DATI, sulla riga 24 della coda
   ▼
  B1 → B2 → B2-bis  il verbo e il suo annullo ─┐
  B3  filtro documento ────────────────────────┤
                                 ▼
                          F1  il verbo nella coda   ─┐
                          F2  esito parziale         ├─ ⭐ QUI la contraddizione
                          F3  il pannello collega   ─┘    del §21.1 si chiude
                                 │
                                 ▼
                          B6  task legame documentale  (dopo P-2)
                                 │
                                 ▼
                          B5 → B7  la natura e il legame escono dal BE
                                 │
                                 ▼
                          F4 → F5  e si vedono
                                 │
                                 ▼
                          F6  verifiche + annuncio
```

🔴 **L'ordine che conta è uno solo: B4 prima di F1.** Il verbo crea una riga di
rettifica in commessa; il giro di fatturazione gira su worker e cron. Nel
momento in cui il primo operatore clicca, un giro **non presidiato** produrrà
un documento fiscale. Se il generatore non ha ancora imparato la rettifica,
quel documento nascerà con lo sconto perso, senza `riga_rettificata_id`, con le
rettifiche aggregate fra loro — cioè *«righe gemelle di nessuno»*, su una
categoria di dato che meno di tutte si può rifare.

⚠️ **F1 e F3 vanno insieme**, per la stessa ragione per cui N8 e N11 dovevano
andare insieme: dare il verbo lasciando il pannello che dichiara «non
disponibile» sposta la contraddizione invece di chiuderla.

---

## 25. Definizione di «fatto» — BE/FE

* [ ] i **cancelli sono verdi**: `genera_error_policies --check` pulito, i due
      test di divergenza codici passano (B0);
* [ ] **una riga di nota di credito è gemella di una riga di fattura**: stesso
      articolo, stesso prezzo, stesso **sconto**, stessa IVA, quantità non
      superiore — e lo dice `riga_rettificata_id`, non una convenzione (B4);
* [ ] **due rettifiche non si fondono mai in una riga sola**, e il `riga_nr` è
      lo stesso su due generazioni dello stesso lotto (B4);
* [ ] il **kit** della coda di oggi (riga 24, tre componenti) attraversa il
      generatore **sui dati veri**, non in un fixture (B4);
* [ ] dalla coda l'operatore **accredita più righe selezionate**, e un esito
      parziale gli dice **quali** non sono passate e perché (B2, F1, F2);
* [ ] **due click non producono due accrediti**, e il secondo lo scopre chi
      clicca — la riga esce dalla coda **al verbo** (§20.3), quindi la prova è
      che la lista si accorcia subito;
* [ ] i **tre posti** dicono la stessa cosa: Backlog con l'azione (già fatto),
      coda col verbo, pannello **senza** la nota e **con** il collegamento
      filtrato (F1, F3);
* [ ] `vendite.fatture_rettifiche` **smette di essere a zero righe**, e la
      proiezione non impedisce nessun reset (B6);
* [ ] il documento **dichiara la sua natura** dove si guarda: drawer fattura,
      drawer lotto, liste (B5, F4);
* [ ] il verbo è **gated** su `accredita_riga_reso` e non sul solo bypass
      SUPER_ADMIN (P-1, B2);
* [ ] un accredito **si può disfare** finché la rettifica non è emessa, e chi
      resetta il lotto **legge** che l'accredito resta dovuto (D-NC-11, B2-bis);
* [ ] non si riapre una rinuncia su una quota già accreditata (D-NC-12, P-3).

---

## 26. Le trappole di questo giro

1. 🔴 **Il kit è il caso normale, non il caso limite.** La prima riga della coda
   è un articolo composito a tre componenti con tre prezzi diversi. Un piano
   che lo tratta come «copertura per completezza» scopre il guard R10 in
   esercizio, sul primo click di un operatore.
2. 🔴 **Il prezzo va copiato nella chiave E nella riga.** Oggi il prezzo
   dell'attività e quello della riga di fattura **coincidono per costruzione**:
   sbagliare quale dei due entra nel raggruppamento non produce nessun sintomo
   finché non divergono — e quando divergeranno, il difetto sarà su documenti
   già emessi.
3. ⚠️ **`SELECT v.*` è un'arma a doppio taglio.** La coda espone già
   `gia_accreditato` e `blocco_codice` senza che nessuno li abbia aggiunti: è
   un guadagno, ma significa anche che **una colonna nuova della vista arriva
   al frontend senza passare da nessuna decisione**. Il gate del bottone va
   scritto sui nomi, non sulla posizione.
4. ⚠️ **`useConfirmAction` fallisce in silenzio** se destrutturato male o se il
   callback si chiama `accept` invece di `onAccept`. Su un verbo che produce
   documenti fiscali, un dialog che non chiama niente è peggio di un errore.
5. ⚠️ **KeepAlive**: il deep-link della coda filtrata (F3) non funziona in
   `onMounted`. Va in `onActivated`, e dev'essere idempotente — scatta anche al
   primo mount.
6. ⚠️ **Non ricalcolare in Python quello che il DB già dice.** Né
   `gia_accreditato` (BE-7), né i guard della madre, né il verso del segno. Due
   traduzioni divergono, e quella sbagliata è sempre quella che nessuno
   guarda.
7. ⚠️ **Non aggiungere dipendenze** npm o Python: tutto quello che serve —
   `run_fan_out`, `useSelezioneToggle`, `ListaConfigurabile`,
   `useConfirmAction`, `useActionPermission` — è già in catalogo.
8. ⚠️ **La regola del 2 morde una volta sola in questo giro** (B3, il predicato
   di filtro sul documento): si dichiara a Tid **prima** di estrarre, e si
   aspetta l'ok.
