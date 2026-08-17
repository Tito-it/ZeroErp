# Brief di design — la nota di credito: chiudere il ramo morto degli accrediti

> **Tipo**: brief di design (decisioni di dominio) · **Data**: 2026-08-17 ·
> **Owner**: Tid · **Stato**: 🟡 **APERTO — decisioni prese, perimetro da
> chiudere con il team DB.**
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
> ## 🔴 PREREQUISITO — leggere prima di iniziare
>
> **La generalizzazione della «partita» (opzione C del §7-bis) va fatta PRIMA di
> questa slice, non dopo.** Decisione di Tid, 2026-08-17.
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
