# Brief di design — generalizzare la «partita»: dalla riga d'ordine alla riga di merce

> **Tipo**: brief di design + **piano DB** · **Data**: 2026-08-17 · **Owner**: Tid ·
> **Stato**: 🟢 **PERIMETRO DB CHIUSO** (2026-08-17) — tutte e otto le slice
> S0→S7 fatte e **applicate** (9 changeSet, `20260817-06` → `-14`), pgTAP verdi
> come applicazione, baseline `vendite` senza regressioni.
>
> ✅ **Anche BE e FE sono chiusi dal 2026-08-18 (§23).** Il testo qui sotto è
> quello del 2026-08-17, quando restavano fuori: le richieste a backend e frontend (§19) e
> i due cantieri che ora possono partire — **pannello situazione merce** e
> **nota di credito**.
>
> ⚠️ **Il §8 va letto prima del §10.** L'analisi ha trovato che il conto di oggi
> è corretto **perché è stretto**: le tre esclusioni (riga d'ordine obbligatoria,
> compositi fuori, nessuna partita senza ordine) tengono nascosti **sei difetti
> di misura**. Allargare la porta li fa entrare tutti insieme, e il pannello del
> cantiere 2 li mostrerebbe a una persona come «da accreditare». Il piano del §10
> è costruito per chiuderli nello stesso passo, non dopo.
>
> **Cos'è**: oggi il conto della merce (`vendite.vw_contatore_merce`) esiste
> **solo** per la merce nata da una riga d'ordine. Tutto il resto — righe di DDT
> aggiunte a mano, e come si vedrà anche gli **articoli compositi** — è merce
> reale che il sistema muove, fattura, e di cui **non tiene il conto**.
>
> **Perché ora**: è il **prerequisito** di due cantieri già decisi. Farlo dopo
> significa rifarli.

---

## 🔢 L'ORDINE CON CUI ESEGUIRE I LAVORI COLLEGATI

Quattro cantieri nati fra il 2026-08-16 e il 2026-08-17. Tre sono in catena,
uno è indipendente.

| #     | Cantiere                                        | Brief                                                                              | Perché in questa posizione                                                                                                                     |
| ----- | ----------------------------------------------- | ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Partita generalizzata**                       | **questo**                                                                         | È la nozione su cui gli altri due poggiano. Cambiarla dopo obbliga a rifarli                                                                   |
| **2** | Pannello «situazione merce» su ordine **e DDT** | [brief-design-situazione-merce-ordine.md](brief-design-situazione-merce-ordine.md) | Legge la partita. Fatto prima, mostrerebbe spedizioni miste con conti parziali **sul DDT**, dove l'incoerenza si vede a occhio                 |
| **3** | Nota di credito (emissione dell'accredito)      | [brief-design-note-credito-resi.md](brief-design-note-credito-resi.md)             | Attribuisce l'accredito **alla partita**. Scritta sulla chiave di oggi, andrebbe riscritta — e nel frattempo avrà emesso **documenti fiscali** |
| **—** | Righe DDT a prezzo zero                         | [brief-ddt-righe-senza-prezzo.md](brief-ddt-righe-senza-prezzo.md)                 | **Indipendente**: riguarda il pricing in inserimento, non la partita. Può procedere in parallelo e sblocca la validazione DL-28                |

⚠️ **La catena 1 → 2 → 3 non è una preferenza di comodo.** Il punto 3 produce
documenti fiscali: rifarlo significa riconciliare note di credito già emesse,
cioè la categoria di dato che meno si può correggere a posteriori.

---

## 1. Come funziona la partita oggi, letto dal codice

`vw_contatore_merce` compone tre grandezze e le àncora **tutte** alla riga
d'ordine:

```text
tenuti      = Σ ordini_righe_fulfillment.qta_evasa  −  Σ vw_resi_righe_effettive.quantita
fatturati   = Σ attivita_fatturabili.quantita  (solo tipo_movimento = 'NORMALE')
differenza  = tenuti − fatturati
```

E la chiusura è questa:

```sql
partite = (SELECT ordine_riga_id FROM ful) UNION (SELECT ordine_riga_id FROM res)
...
FROM partite p JOIN vendite.ordini_righe orr ON orr.id = p.ordine_riga_id
```

⭐ **La riga d'ordine non è un attributo della partita: è la partita.** Ciò che
non ha una riga d'ordine non compare come riga a conto zero — **non esiste**.

### Il passaggio che spiega tutto: come `fatturati` risale alla riga d'ordine

Le attività fatturabili non portano un `ordine_riga_id`: portano una
`segment_key`, e il contatore la interpreta:

```text
segment 'ORD:<uid>:R:<id>'  →  <id> È la riga d'ordine
segment 'DDT:<uid>:R:<id>'  →  <id> è una riga di DDT
                               →  JOIN ordini_righe_fulfillment ON ddt_riga_id
                               →  da lì si ricava la riga d'ordine
```

⚠️ **Ed è esattamente lì che la riga manuale cade.** Il suo segmento è
`DDT:…:R:<id>`, il `JOIN` sul fulfillment non trova nulla, e la riga **esce dal
conto senza errore**: fatturata, ma invisibile. Non è una dimenticanza — è la
conseguenza di aver scelto la riga d'ordine come chiave.

## 2. 🔴 La seconda falla, trovata scrivendo questo brief

L'ultima riga della vista:

```sql
WHERE NOT COALESCE(art.is_composito, false)
```

**Gli articoli compositi sono esclusi dal conto della merce.** Qualunque
spedizione di un composito — con o senza ordine — è merce che si muove e che il
contatore non vede.

Ne discende che **la merce senza partita non è un caso di nicchia**: sono almeno
tre famiglie.

| Famiglia                          | Perché fuori                        | Frequenza                                                                         |
| --------------------------------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| Righe di DDT aggiunte a mano      | nessun fulfillment                  | il caso che ha aperto la questione                                                |
| Articoli **compositi**            | esclusi dalla vista per costruzione | **12 righe d'ordine su 107** (misurato 2026-08-17): l'11%, non un caso di nicchia |
| DDT **standalone** (senza ordine) | nessuna riga d'ordine a monte       | `fn_list_ddt_da_pushare` li fattura da sempre, ramo standalone                    |

⚠️ **La terza riga è la più significativa**: un DDT standalone viene **fatturato**
(l'abbiamo verificato oggi, `DDT0000034`) e non ha **mai** avuto un conto della
merce. Non è una regressione introdotta: è un buco che c'è da sempre e che nessuno
aveva visto perché il contatore non era mai stato mostrato a nessuno.

## 3. Cosa serve (il «cosa», non il «come»)

**La partita deve diventare la riga di merce, e la riga d'ordine una delle sue
possibili origini.**

* ogni riga di **DDT** ha una partita, che esista o no una riga d'ordine a monte;
* quando l'origine c'è, il conto si aggrega **anche** per riga d'ordine — è la
  lettura che serve all'ordine, e non deve peggiorare;
* quando l'origine non c'è, la partita **esiste comunque** e il conto è quello
  della sola riga di merce;
* i **compositi** entrano nel conto, o la loro esclusione diventa una scelta
  **dichiarata** con la sua ragione — non una condizione ereditata.

### Cosa ne consegue a valle, e va garantito

1. **`vw_resi_da_accreditare`** oggi si aggancia a `ordine_riga_id`: deve poter
   attribuire un accredito anche a merce senza origine ordine. `resi_righe`
   ha già `ddt_riga_id` **NOT NULL** e `ordine_riga_id` **nullable** — la strada
   è già aperta nel dato (2 righe su 17 hanno l'ordine vuoto).
2. **`vw_resi_da_riconsegnare`**: stessa verifica.
3. **Il conto per riga d'ordine non deve cambiare valore** dove oggi esiste. È il
   collaudo più importante: la generalizzazione è a **parità** sui casi già
   coperti, altrimenti non è una generalizzazione ma un cambio di semantica.

## 4. Vincoli

1. **Nessuna doppia contabilizzazione.** Se una riga di merce ha origine ordine,
   il suo conto deve comparire **una volta**: nella partita di merce e
   nell'aggregato d'ordine, che sono due letture della stessa cosa, non due righe.
2. **A parità sui casi coperti** (§3.3): i valori di oggi restano.
3. **Il vocabolario dei movimenti resta** `NORMALE | RETTIFICA | ONERE`. Oggi
   `fatturati` conta i soli `NORMALE`: la rettifica della NC (§4 del brief NC)
   dovrà **abbassare** il conto, quindi il criterio va rivisto insieme al punto 3
   della catena — ma la decisione è di quel cantiere, non di questo.
4. **Niente sui verbi**: questo brief cambia una nozione e ciò che la legge, non
   ciò che la scrive.

## 5. Cosa NON serve

* **Nessun cambio alla chiave di aggregazione della fattura**
  (`fn_build_fattura_key`): riguarda su chi si fattura, non di quale merce si
  tiene il conto.
* **Nessun cambio a `ordini_righe_fulfillment`**: resta il legame fra riga di DDT
  e riga d'ordine quando esiste. La generalizzazione sta nel **non pretenderlo**.
* **Nessuna bonifica retroattiva** decisa qui: se le partite storiche senza
  origine vadano ricostruite è una domanda del §6.

## 6. Domande aperte — per il team DB

> ✅ **Le quattro domande hanno una risposta dal 2026-08-17.** Restano scritte
> qui **come erano poste**, perché la risposta si legge meglio accanto alla
> domanda; il ragionamento e la misura che le chiudono stanno nel §9.

1. **Dove vive la partita**: una vista che generalizza `vw_contatore_merce`, o una
   tabella? Oggi è calcolata; se resta calcolata, la chiave «riga di merce» va
   derivata a ogni lettura.
   → ✅ **RISPOSTA: una vista, e la chiave non va derivata — esiste già.** §9.1 e
   §9.4. La riga di merce **è** `vendite.ddt_righe.id`, che è una chiave primaria
   vera: non c'è niente da inventare e niente da mantenere in sincronia.
2. **I compositi**: entrano o l'esclusione si dichiara? ✅ La misura c'è già —
   **12 righe d'ordine su 107** portano un articolo composito, e il contatore ha
   in tutto **12 partite**: l'ordine di grandezza dice che l'esclusione non è
   marginale. Resta la domanda di merito: il conto di un composito è quello del
   padre o dei componenti? Probabilmente è **la ragione per cui l'esclusione
   esiste**, e va riletta prima di toglierla — non è detto sia una dimenticanza.
   → ✅ **RISPOSTA: entrano, contati in unità del PADRE.** E l'intuizione era
   giusta: **l'esclusione non è una dimenticanza**, è una toppa. §8.2 mostra il
   numero che la spiega — misurato, non dedotto.
3. **Retroattività**: le partite oggi inesistenti (DDT standalone, righe manuali,
   compositi) vanno ricostruite sullo storico o valgono dai prossimi documenti?
   ⚠️ Se non si ricostruiscono, il pannello del punto 2 mostrerà «nessun conto»
   su documenti vecchi, e va detto invece di sembrare un guasto.
   → ✅ **RISPOSTA: la domanda si dissolve** — con la vista non esiste un
   «prima». §9.6.
4. **La riga manuale con l'articolo dell'ordine** (§7-bis del brief NC, caso
   «stesso articolo»): con la partita generalizzata smette di falsare i conti, ma
   resta **indistinguibile da un errore dell'operatore**. Serve ancora un
   avviso, o la generalizzazione basta?
   → ✅ **RISPOSTA: serve ancora un avviso, ma non un blocco** — ed è una
   **lettura**, non un guard. §10 slice S6.

## 7. Definizione di «fatto» (bozza)

* [x] una riga di DDT **senza ordine a monte** ha un conto della merce
      (consegnato, fatturato, reso, saldo);
* [x] una riga di DDT **aggiunta a mano** su un DDT da ordine ha lo stesso;
* [x] i conti **per riga d'ordine** esistenti hanno gli **stessi valori** di
      prima (parità verificata su dati reali, non su fixture);
* [x] un reso su merce senza origine ordine produce un accredito **calcolabile**;
* [x] la sorte dei **compositi** è decisa e scritta;
* [x] la **retroattività** è decisa e scritta.

### 7-bis. Aggiunte alla definizione di «fatto» (dal §8, 2026-08-17)

Le sei voci sopra descrivono la generalizzazione. Queste sei descrivono ciò che
la generalizzazione **scoperchia**, e senza le quali il cantiere 2 mostrerebbe
numeri falsi a una persona:

* [x] **nessuna riga d'ordine fatturata-e-non-spedita chiede un accredito**
      (§8.1 — oggi sarebbero 12 falsi «da accreditare» su 18 righe di corsia ORD);
* [x] un **kit** consegnato per intero e fatturato per intero ha saldo **zero**,
      non −2 (§8.2);
* [x] la merce su un **DDT in bozza** non risulta consegnata **e non sparisce**:
      si legge come `in_riconsegna` (§8.3-bis — vincolata alla decisione D1);
* [x] la merce su **causale non fatturabile** non risulta «da fatturare» (§8.4);
* [x] un conto **non calcolabile** (kit senza coefficiente, RLS che nasconde la
      commessa) si dichiara tale e **non si presenta come zero** (§8.2, §8.6);
* [x] `fn_list_ddt_da_pushare` **fattura le stesse quantità di prima** sui casi
      già coperti (§8.7 — è la voce che protegge documenti fiscali, non una
      schermata).

---

## PARTE II — ANALISI CRITICA E PIANO DB

> Scritta il **2026-08-17**. Le misure vengono dal **DB di sviluppo**, con query
> in sola lettura eseguite come owner (per non leggere zeri prodotti dalla RLS).
> ⚠️ **I dati di sviluppo sono dati di test**: non misurano la gravità di un
> difetto, misurano che il difetto **è raggiungibile**. Dove un caso ha zero
> occorrenze ma nulla lo impedisce, sta scritto così.

## 8. 🔬 Cosa la generalizzazione SMASCHERA

Il contatore di oggi dà numeri giusti. Ma li dà giusti **perché guarda poco**:
tre esclusioni — la riga d'ordine obbligatoria, i compositi fuori, la merce senza
ordine invisibile — fanno da coperchio a difetti di misura che stanno sotto.

⭐ **È il punto che cambia la natura del lavoro.** Il §3 lo descriveva come
«allargare la chiave». Non lo è: allargare la chiave **toglie il coperchio**, e
sotto ci sono sei cose. Quattro producono numeri sbagliati, una li produce
illeggibili, una riguarda la fatturazione e non la lettura.

| #     | Rilievo                                                                          | Oggi è nascosto perché                                                         | Misura (dev, 2026-08-17)                                                                                             | Gravità |
| ----- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- | ------- |
| **A** | La corsia ORD fattura **prima** che la merce esca                                | quelle righe non hanno fulfillment → non entrano nella `UNION` delle partite   | **16** righe d'ordine fatturate più di quanto spedito, di cui **12 mai spedite**                                     | 🔴       |
| **B** | I compositi contano i **componenti** contro un consegnato in **pezzi del padre** | `WHERE NOT is_composito`                                                       | **4** partite darebbero **−2** invece di 0 · una quinta riga cumula B e A (17 ordinati, **51** fatturati, 0 spediti) | 🔴       |
| **C** | Il fulfillment conta anche i DDT in **bozza**                                    | il `differenza` positivo si legge come «da fatturare», che non allarma nessuno | **4** righe di fulfillment su DDT `DRAFT`, **6 pezzi**, su **2** partite                                             | 🟠       |
| **D** | Le causali **non fatturabili** entrerebbero come «da fatturare»                  | quelle righe non hanno partita                                                 | **5** righe (CONTO_VISIONE 2, CONTO_LAVORO 2, CAMPIONATURA 1)                                                        | 🟠       |
| **E** | `resi_righe.ordine_riga_id` è nullable **senza guard di coerenza**               | nessuno lo compila male, per ora                                               | **0** violazioni — e **0 guard**                                                                                     | 🟡       |
| **F** | La RLS di `commesse_attivita` passa da una **strada diversa** da quella dei DDT  | il contatore non è mai stato mostrato a un utente applicativo                  | 2 percorsi di scope distinti                                                                                         | 🟡       |

### 8.0 ✅ Precisazione al §2 — la prova del DDT standalone è un'altra, ed è più forte

Il §2 cita `DDT0000034` come DDT standalone fatturato. Verificato oggi: quel DDT
è **eleggibile** al push (`fn_list_ddt_da_pushare` lo restituisce) ma **non è
ancora stato inviato**. La prova vera è un altro documento, e non lascia margine:

```text
DDT0000030 · riga 46 · 24 pezzi · segment DDT:019f4c7d-…:R:46
attività fatturabile 886 · fatturato = TRUE · riga di fattura 332
```

⭐ **24 pezzi sono già dentro una fattura, e di quella merce non esiste nessun
conto.** La tesi del §2 regge — è solo il documento citato a essere quello
sbagliato: uno è la porta aperta, l'altro è qualcuno che c'è già passato.

### 8.1 🔴 Rilievo A — la corsia ORD fattura prima che la merce esca

`vendite.ordini.fatturazione_trigger` ha due valori in uso: **93 ordini
`CONFERMATO`** e **2 `SPEDITO`**. Con `CONFERMATO` si fattura **l'ordine
confermato, e la spedizione è ortogonale** — è scritto testualmente nel commento
di `fn_list_ordini_da_pushare` (rev 2026-07-10, fix orfano).

Ne discende che `fatturati` può esistere **senza che sia uscito un pezzo**:

```text
ORD0000140 · riga 149 · ordinato 100 · fatturati 100 · evaso 0
ORD0005175 · riga 5406 · ordinato  99 · fatturati  99 · evaso 0
… e altre 10 righe così
```

⚠️ **Oggi non si vede, e non per una protezione: per un caso.** Le partite del
contatore nascono da `ful UNION res`; una riga mai spedita e mai resa non sta in
nessuna delle due, quindi la riga **non esiste** e il `fatturati` calcolato viene
buttato via.

🔴 **Con la partita generalizzata quel coperchio salta.** Se «ogni merce ha una
partita» diventa «ogni riga ha una partita», quelle 12 righe compaiono con
`tenuti 0 · fatturati N · differenza −N`. E `differenza < 0` è **esattamente** il
segnale su cui il §5.4 del brief pannello ha deciso di scrivere **«N da
accreditare»**.

**Il risultato sarebbe che l'applicazione chiede all'operatore di emettere note
di credito per merce che deve ancora spedire.** Su **12 righe su 18** della
corsia ORD.

⭐ **La lettura giusta del rilievo**: `differenza` oggi ha **tre** significati
diversi appiattiti in un numero.

| `differenza`          | Significa                                      | È un compito?                            |
| --------------------- | ---------------------------------------------- | ---------------------------------------- |
| `> 0`                 | merce consegnata e non ancora fatturata        | sì: **fatturare**                        |
| `< 0` **con un reso** | merce resa dopo essere stata fatturata         | sì: **accreditare**                      |
| `< 0` **senza reso**  | fatturato in anticipo, merce non ancora uscita | **no**: è un arretrato di **spedizione** |

Le prime due sono il conto della merce. La terza non lo è, ed è la maggioranza.

### 8.2 🔴 Rilievo B — i compositi: il numero che spiega l'esclusione

Il §6.2 chiedeva se l'esclusione fosse una dimenticanza. **Non lo è.** Ecco cosa
direbbe il contatore, oggi, se si togliesse quella riga e basta:

```text
ORD0000163 · art-comp-001 · tenuti 1 · fatturati 3 · differenza −2
ORD0000227 · art-comp-001 · tenuti 1 · fatturati 3 · differenza −2
ORD0000580 · art-comp-001 · tenuti 1 · fatturati 3 · differenza −2
ORD0000608 · art-comp-001 · tenuti 1 · fatturati 3 · differenza −2
ORD0005174 · art-comp-001 · ordinato 17 · fatturati 51   (17 × 3)
```

**Il 3 non è un errore: è il numero di componenti del kit.** Al push, un articolo
composito viene esploso in N attività — una per componente — con
`quantita = quantita_padre × coeff_qta` e `segment_key` col suffisso
`#CMP:<componente>` (`BoMComponentExpander`, decisioni DEC-2/DEC-3).

E il contatore le **raccoglie tutte**, perché la sua espressione di estrazione
non distingue:

```sql
substring(segment_key, ':R:([0-9]+)')   -- su 'ORD:…:R:172#CMP:abc' restituisce 172
```

Verificato: la riga d'ordine 172 riceve **3** attività da 1 pezzo ciascuna.
Sommate fanno 3. Il consegnato è **1 kit**.

⭐ **Quindi `fatturati` e `tenuti` sono in due unità di misura diverse, e la
sottrazione fra loro non significa niente.** `WHERE NOT is_composito` è la toppa
che impedisce a quel numero di uscire. Toglierla senza normalizzare non
«include i compositi»: **produce cinque partite sbagliate**, che finiscono nella
coda accrediti e nel dosaggio della fatturazione.

✅ **E non è una ricostruzione: chi ha scritto la vista lo aveva messo per
iscritto.** L'intestazione del changeSet `20260717-11`, riga per riga:

> *«COMPOSITI (`is_composito`): i loro AF sono i COMPONENTI (segmenti `#CMP`, in
> unità-componente = padre × coeff), mentre fulfillment e resi sono in
> unità-**PADRE** → **mismatch di unità che il contatore non può riconciliare
> senza la macchina BoM**. Esclusi qui (`WHERE NOT is_composito`), **follow-up a
> sé**.»*

⭐ **Questo cantiere è quel follow-up**, e la «macchina BoM» che allora mancava
oggi c'è: è il `coeff_qta` che il push scrive nel `meta`. La domanda del §6.2 —
*«non è detto sia una dimenticanza»* — aveva ragione al 100%: era una **rinuncia
dichiarata, con la sua data e il suo motivo**.

✅ **E la strada per normalizzare c'è già, ed è a costo zero.** Il push scrive
nel `meta` dell'attività il coefficiente con cui ha moltiplicato:

```text
commesse_attivita.meta ->> 'coeff_qta'       -- il moltiplicatore
commesse_attivita.meta ->> 'componente_di'   -- l'articolo padre
```

Quindi la quantità del padre si **ricostruisce**: `quantita ÷ coeff_qta`.
Verificato su tutte e 5 le istanze di kit del DB: il valore ricostruito è
**identico** partendo da qualunque componente (min = max) e **coincide con la
quantità ordinata**. Zero coefficienti mancanti.

⚠️ **Ma la verifica è debole dove conta.** In sviluppo **tutti i `coeff_qta`
valgono 1**: la divisione non è mai esercitata davvero. Un kit con `coeff_qta = 2`
(due viti per telaio) non esiste nei dati, e il ramo che lo gestisce sarebbe
verde senza essere provato. **Il pgTAP deve costruirne uno.**

⭐ **Una nota di merito su questa scelta.** Il contratto `#CMP:` + `meta` è
dichiarato nel codice BE (`_kit_meta.py`) come *«un contratto con due estremi
lontani, e in mezzo nulla lo verifica»* — scrittura al push, lettura alla
fattura. Questa vista ne diventa il **terzo consumatore, e il primo che lo
verifica su ogni riga**: se un giorno il `coeff_qta` sparisse, oggi lo si
scoprirebbe da una fattura sbagliata, domani da una partita che si dichiara **non
misurabile**.

### 8.3 🟠 Rilievo C — il fulfillment conta anche i DDT in bozza

La CTE `ful` del contatore è questa, per intero:

```sql
SELECT ordine_riga_id, sum(qta_evasa) FROM vendite.ordini_righe_fulfillment GROUP BY 1
```

**Nessun join al DDT.** Quindi non guarda in che stato è il documento. Misurato:

| Stato del DDT | Righe di fulfillment | Pezzi |
| ------------- | -------------------- | ----- |
| CONSEGNATO    | 16                   | 86    |
| **DRAFT**     | **4**                | **6** |
| SPEDITO       | 2                    | 5     |
| EMESSO        | 1                    | 6     |
| RESO          | 1                    | 1     |

Due delle 12 partite (righe d'ordine 236 e 239) hanno dentro `tenuti` la merce di
un DDT **ancora in bozza**: merce che non è uscita dal magazzino.

⚠️ **Oggi è innocuo per un motivo che sta per venire meno.** Quel `tenuti`
gonfiato produce un `differenza` **positivo**, che si legge «da fatturare» — e
nessuno lo legge, perché la fatturazione ha un cancello suo
(`sdd.ordine >= rank del trigger`) che le bozze non passano. Il numero è sbagliato
e non fa danno **finché nessuno lo guarda**.

🔴 **Il cantiere 2 è precisamente «qualcuno lo guarda».** Il pannello dirà
«consegnato: 5» su merce ferma in magazzino, e lo dirà **anche sul DDT**, dove
sotto si legge lo stato «Bozza» due centimetri più in basso.

#### 8.3-bis 🔴 Il caso è una **ri-consegna**, e il difetto non è solo del contatore

Guardato da vicino il 2026-08-17, il caso non è generico: è il **giro del reso
per ri-consegna**, e le due bozze sono il DDT di ri-consegna che qualcuno ha
preparato e non ha ancora emesso.

```text
riga d'ordine 236
  DDT0000057 (CONSEGNATO)  5 pezzi   ← usciti davvero
  RESO0000…  su quel DDT   3 pezzi   ← tornati indietro
  DDT (BOZZA) righe 117+118  1 + 2   ← la ri-consegna, PREPARATA e non spedita
```

Il cliente ha in mano **2 pezzi**. Il contatore dice **5**.

⚠️⚠️ **E il difetto non sta solo nel contatore: `vw_resi_da_riconsegnare`
anticipa allo stesso modo.** Il ponte `resi_righe_riconsegne` punta a quelle
righe in bozza, quindi `fn_resi_riga_residuo_riconsegna` le conta come già
ri-consegnate e i due resi **non compaiono più nella coda** (verificato: 0 righe).

⭐ **Ma qui la lettura cambia, e non è un secondo difetto: è la stessa
constatazione che significa due cose diverse.**

| Vista                     | Domanda                      | Cosa deve fare la bozza                                                                                                                                |
| ------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `vw_resi_da_riconsegnare` | «cosa devo ancora **fare**?» | ✅ **uscire dalla coda** — qualcuno se ne sta già occupando. È una prenotazione, e il modello la usa così apposta (stessa scelta del guard over-return) |
| il contatore della merce  | «dove **sta** la merce?»     | ❌ **non contare** — la bozza non ha mosso nulla                                                                                                        |

**Ne discende che le due viste non vanno allineate fra loro, e che correggere il
solo contatore è corretto** — ma apre un buco di lettura: con `tenuti = 2` e
`da riconsegnare = 0`, un operatore chiederebbe *«e gli altri 3 dove sono?»*.

✅ **Serve una terza grandezza, esattamente come per il fatturato anticipato**
(§9.3): **`in_riconsegna` — merce tornata, già impegnata su un DDT non ancora
emesso**. Tre pezzi che non sono né dal cliente né in coda: sono sul banco.

🔴 **È la decisione D1 del §10.** Non è un dettaglio implementativo: cambia due
numeri che oggi esistono.

### 8.4 🟠 Rilievo D — la causale non fatturabile

`config.causali_trasporto.fatturabile`: **una sola causale è `true`** (VENDITA),
sette sono `false` (CAMPIONATURA, CONTO_LAVORO, CONTO_VISIONE, OMAGGIO, RESO,
RIPARAZIONE, TRASFERIMENTO). Sulle righe DDT attive:

```text
VENDITA         24 righe   fatturabile
(nessuna)       12 righe   → DDT in bozza: la causale è obbligatoria solo all'emissione
CONTO_VISIONE    2 righe   NON fatturabile
CONTO_LAVORO     2 righe   NON fatturabile
CAMPIONATURA     1 riga    NON fatturabile
```

Quelle 5 righe sono **merce che si muove e che non verrà mai fatturata** — è il
senso stesso della colonna, seedata il 2026-07-17 e già usata come cintura in
`fn_list_ddt_da_pushare`.

⚠️ Con la partita generalizzata «ogni riga di DDT ha un conto», quelle 5 righe
avrebbero `fatturati 0` e `differenza = +quantità` → il pannello direbbe **«5 da
fatturare»** su un conto visione.

⭐ La conclusione è che `differenza` non deve valere **zero** lì: deve **non
esistere**. `fatturabile = false` → il conto di fatturazione **non si applica**.
È la stessa distinzione del brief prezzi-zero §3.2 — *«`0` è un'affermazione,
`NULL` è un'astensione»* — e vale identica qui.

#### 8.4-bis ⚠️ Correzione alla regola, trovata SCRIVENDO S2 (2026-08-17)

La regola qui sopra, presa alla lettera, è **sbagliata**, e il caso che la
smentisce è nei dati:

```text
riga di DDT 47 · causale CONTO_VISIONE (non fatturabile)
                 ordine ORD0000163 fatturato per intero (corsia ORD)
```

Con `fatturabile = false` la partita usciva `NON_FATTURABILE` con `differenza`
NULL — cioè **dichiarava che quella merce non si fattura mentre la si stava
fatturando**. E se poi tornasse indietro, l'accredito resterebbe nascosto.

⭐ **La causale dice cosa ci si aspetta dal VIAGGIO, non se la merce è stata
fatturata.** Le due cose viaggiano su assi diversi: la causale è del DDT, il
fatturato può nascere sull'ordine, indipendentemente dalla spedizione.

✅ **Regola corretta**: il conto si spegne solo se la causale non è fatturabile
**e** non c'è alcun fatturato. Se un fatturato c'è, il conto si applica — è un
**fatto**, non una previsione. Applicata in `20260817-07`, e verificata: la riga
47 passa da `NON_FATTURABILE` a `PAREGGIATA` (1 consegnato, 1 fatturato).

### 8.5 🟡 Rilievo E — `resi_righe.ordine_riga_id` senza guard

Oggi `vw_contatore_merce` sottrae i resi così:

```sql
FROM vendite.vw_resi_righe_effettive e WHERE e.ordine_riga_id IS NOT NULL
```

Un reso con `ordine_riga_id` vuoto **non viene sottratto**. Sui 17 resi:

|                                                             | Righe |
| ----------------------------------------------------------- | ----- |
| con `ordine_riga_id`                                        | 15    |
| vuoto, e riga DDT **standalone** (corretto: non c'è ordine) | 2     |
| vuoto, ma riga DDT **agganciata a un ordine** ← incoerente  | **0** |

Zero, oggi. Ma `ordine_riga_id` è **nullable** e **nessun trigger** verifica che
sia compilato quando il DDT di origine ha un fulfillment. Un reso registrato così
oggi **sparirebbe dal conto senza errore** — è lo stesso meccanismo del §1, un
`JOIN` che non trova nulla.

⭐ Riancorare la partita al `ddt_riga_id` — che è **NOT NULL** — chiude il buco
per costruzione: il reso sa **sempre** da quale riga di merce viene. Il guard
serve comunque, perché `ordine_riga_id` resta e resta letto altrove.

### 8.6 🟡 Rilievo F — la RLS arriva alla merce da due strade diverse

| Tabella                                                                                       | RLS | Come si decide se la vedi                                 |
| --------------------------------------------------------------------------------------------- | --- | --------------------------------------------------------- |
| `vendite.ddt`                                                                                 | ✅   | `fn_scope_ef_whitelist(utente, emittente_fiscale_id)`     |
| `vendite.commesse_attivita`                                                                   | ✅   | `fn_scope_ef_whitelist_via_commessa(utente, commessa_id)` |
| `ddt_righe`, `ordini_righe`, `ordini_righe_fulfillment`, `resi_righe`, `attivita_fatturabili` | ❌   | ereditano dal padre via `security_invoker`                |

⚠️ **Il consegnato e il fatturato passano da due cancelli diversi.** In pratica
l'emittente è lo stesso, ma **non è garantito per costruzione**: sono due funzioni
di scope distinte, su due entità distinte.

🔴 **E qui vale la regola che il progetto ha già imparato**: *su una tabella con
RLS, zero non è un dato — è fail-closed*. Un operatore che vede il DDT ma non la
commessa leggerebbe `fatturato = 0` e il pannello direbbe **«da fatturare»** su
merce già fatturata. Indistinguibile da un difetto vero.

**Ne discende un requisito**: la partita deve saper dire «non lo so» — e va
provato con un pgTAP che gira in un contesto di scope ristretto, non solo come
owner.

### 8.7 ⚠️ Il rilievo che cambia il RISCHIO: il contatore non è una lettura

Il brief pannello (§1) dice che `vw_contatore_merce` *«non è consumato da
nessuno — né dal backend né dal frontend»*. È vero per le persone. **Non è vero
per le macchine**, e la differenza è tutta:

```sql
-- vendite.fn_list_ddt_da_pushare, rev 2026-07-17 (step 3)
LEFT JOIN vendite.vw_contatore_merce ct ON ct.ordine_riga_id = src.src_ordine_riga_id
…
THEN GREATEST(0, LEAST(dr.quantita, COALESCE(ct.differenza, 0) - <già distribuito>))
```

⭐ **`differenza` non descrive la fatturazione: la dosa.** È la quantità che
finisce nella riga di fattura.

🔴 **Ne discendono due cose, e sono la ragione dell'ordine delle slice del §10.**

1. **Ogni modifica al contatore è una modifica alla fatturazione.** «A parità sui
   casi coperti» (§4.2) non è una gentilezza verso chi legge: è la proprietà che
   impedisce a questo cantiere di **cambiare gli importi di documenti fiscali**.
2. **Un `differenza` negativo azzera il push.** Oggi i compositi sono salvati da
   un caso speciale (`ELSE dr.quantita` per composito/standalone). Se domani il
   contatore restituisse le partite composite con `−2` e qualcuno togliesse quel
   caso speciale come «non più necessario», **i kit smetterebbero di essere
   fatturati in silenzio**. Il caso speciale nel dosatore e l'esclusione nella
   vista sono la **stessa toppa in due posti**: vanno tolte insieme, o nessuna.

---

## 9. Il modello proposto

### 9.1 La chiave: la partita è la riga di DDT

> **`vendite.ddt_righe.id` è la partita. `ordini_righe.id` diventa l'origine.**

Quattro ragioni, tutte verificabili nel modello di oggi:

1. **La merce passa tutta da lì.** Nessuna eccezione misurata: ogni pezzo che si
   muove è una riga di DDT.
2. **Chi torna indietro sa già da dove viene**: `resi_righe.ddt_riga_id` è **NOT
   NULL**, mentre `ordine_riga_id` è nullable. La chiave robusta è già quella
   giusta, ed è già obbligatoria (chiude il §8.5).
3. **L'origine è già un attributo della riga di merce**:
   `ordini_righe_fulfillment` è la coppia `(ordine_riga_id, ddt_riga_id)`. Non
   c'è niente da costruire: c'è da smettere di **pretenderla**.
4. **La fatturazione parla già questa lingua**: il `segment_key`
   `DDT:<uid>:R:<ddt_riga_id>` esiste dal primo giorno. La riga di merce è già la
   chiave con cui il sistema dice *«questi pezzi sono stati fatturati»*.

⚠️ **Un vincolo del modello da conoscere.** `uq_ordini_r_ful_v_pair` è unica sulla
**coppia**, non su `ddt_riga_id`: una riga di DDT **potrebbe** evadere due righe
d'ordine. Oggi non succede (24 righe di DDT order-backed, tutte con **una** riga
d'ordine), ma il modello lo ammette. La vista deve reggerlo senza duplicare la
merce: l'origine è **al più una** per la lettura, e se ce ne fossero due la
partita si dichiara **a origine multipla**, non si moltiplica.

### 9.2 ⚠️ Ma la corsia ORD non ha una riga di merce — la regola di allocazione

È la difficoltà vera del cantiere, ed è il §8.1 visto dal lato della soluzione:
con `fatturazione_trigger = 'CONFERMATO'` (**93 ordini su 95**) il fatturato nasce
sull'**ordine**, quando di DDT non ce n'è ancora nessuno.

Una partita ancorata alla riga di DDT **non ha dove metterlo**.

✅ **La regola proposta — allocazione greedy, la merce più vecchia per prima.**

```text
Per ogni riga d'ordine:
  fatturato_ord = Σ attività sui segmenti ORD:<uid>:R:<riga>  (in unità del padre)
  righe di merce = le righe di DDT di quella riga d'ordine, dalla più vecchia
  si versa fatturato_ord nelle righe di merce fino a CAPIENZA, in ordine
  ciò che avanza  →  fatturato_anticipato   (non appartiene a nessuna merce)
```

**Capienza = il consegnato, non i tenuti.** Distinzione che sembra sottile e
invece decide tutto: se la capienza fosse `tenuti` (consegnato − reso), un reso
«libererebbe» capienza, l'accredito verrebbe riassorbito e **la coda accrediti
resterebbe vuota**. È lo scenario che il §2 del brief NC descrive come il difetto
da non commettere.

⭐ **Non è una regola nuova: è la regola che il sistema applica già.** La
distribuzione greedy con finestra `ROWS BETWEEN UNBOUNDED PRECEDING AND 1
PRECEDING` è la stessa di `fn_list_ddt_da_pushare` (dosaggio) e di
`vw_resi_da_accreditare` (accrediti). Se ne scrive una terza applicazione, ma non
un terzo criterio.

**Prova su dati reali** che la regola tiene insieme parità e correzione:

| Caso                    | Consegnato | Fatturato ORD     | Allocato | Anticipato | Differenza | Oggi                                  |
| ----------------------- | ---------- | ----------------- | -------- | ---------- | ---------- | ------------------------------------- |
| riga 588                | 1          | 1                 | 1        | 0          | **0**      | 0 ✅ parità                            |
| riga 607                | 1          | 1                 | 1        | 0          | **0**      | 0 ✅ parità                            |
| riga 172 (kit)          | 1          | 3 → **1** padre   | 1        | 0          | **0**      | *esclusa* ✅ entra a zero              |
| riga 5405 (kit)         | 0          | 51 → **17** padre | 0        | 17         | —          | *invisibile* ✅ nessun falso accredito |
| riga 18946 (corsia DDT) | 21         | —                 | —        | —          | **−8**     | −8 ✅ parità                           |

⭐ **La terza riga è la prova che la normalizzazione in unità del padre è la
scelta giusta e non una preferenza**: fa tornare a **zero** un conto che a unità
componente darebbe −2, e lo fa senza alcuna eccezione scritta per i kit.

### 9.3 Le tre grandezze, disambiguate

Il §8.1 ha mostrato che `differenza` porta tre significati. Il modello li separa,
e **`differenza` conserva il suo**, che è l'unico che riguarda la merce:

| Grandezza              | Domanda a cui risponde                                       | Dove vive                                               |
| ---------------------- | ------------------------------------------------------------ | ------------------------------------------------------- |
| `differenza`           | «di questa merce, cosa resta da fatturare o da accreditare?» | partita di merce                                        |
| `fatturato_anticipato` | «quanto è stato fatturato di merce non ancora uscita?»       | riga d'ordine                                           |
| `in_riconsegna`        | «quanto è tornato e sta già su un DDT non ancora emesso?»    | partita di merce — **solo se D1 = `EMESSO`** (§8.3-bis) |
| `da_riconsegnare`      | «quanto deve ancora tornare al cliente?»                     | già esistente, `vw_resi_da_riconsegnare`                |

⭐ **Le prime tre hanno la stessa forma**: sono ciò che resta quando si smette di
appiattire in un solo numero cose che accadono in momenti diversi. Il fatturato
può precedere la merce; la merce resa può precedere la ri-consegna. Ogni volta
che due tempi non coincidono, serve una grandezza che dica **dove sta la roba nel
mezzo** — altrimenti il saldo la nasconde e il pannello mente per omissione.

E il verso di `differenza` si traduce **una volta sola**, dentro la partita, con
una colonna `stato` — che è la richiesta esplicita del §5.4 del brief pannello
(*«il verso del saldo va tradotto una volta sola, in un punto condiviso»*):

```text
PAREGGIATA        differenza = 0
DA_FATTURARE      differenza > 0
DA_ACCREDITARE    differenza < 0
NON_FATTURABILE   causale non fatturabile        → differenza NULL   (§8.4)
NON_MISURABILE    kit senza coeff, o scope RLS   → differenza NULL   (§8.2, §8.6)
```

⚠️ **`NON_MISURABILE` e `PAREGGIATA` non vanno confusi**, ed è lo stesso
requisito del §5.2 del brief pannello (*«tutto regolare deve essere visibilmente
diverso da non ancora calcolato»*). Qui è il DB a garantirlo, così il FE non deve
inventarselo.

### 9.4 ✅ Vista o tabella? — vista (risposta al §6.1)

**Vista.** Tre argomenti, in ordine di forza:

1. ⭐ **La chiave fisica esiste già.** L'argomento della tabella era «serve un
   riferimento stabile alla partita, per la NC». Ce l'ha: `ddt_righe.id` è una
   chiave primaria, non un calcolo. Una tabella aggiungerebbe una **seconda**
   identità alla stessa cosa.
2. 🔴 **Il contatore dosa la fatturazione** (§8.7). Una tabella materializzata
   introdurrebbe una finestra in cui il numero letto **non è** il numero vero — su
   una grandezza che determina la quantità in fattura. Una vista è letta dentro la
   stessa transazione che decide.
3. **Quattro tabelle già presidiate.** Fulfillment, resi, attività e righe DDT
   hanno già trigger di audit, storico e coerenza. Una tabella-partita andrebbe
   tenuta allineata a tutte e quattro: quattro trigger nuovi, quattro modi nuovi
   di divergere.

⚠️ **Il costo, dichiarato**: la vista non è indicizzabile, e ha dentro una
finestra di allocazione. Non è un problema **oggi** (ordini di grandezza: decine
di righe) e non lo sarà finché il contatore si legge per documento — che è come lo
usano sia il dosatore (`p_ddt_id`) sia il pannello (un ordine, un DDT). **Diventa
un problema il giorno in cui qualcuno lo aggrega su tutto**: se succede, la
risposta è una vista materializzata **accanto**, non al posto.

### 9.5 ✅ Compositi: entrano, in unità del padre (risposta al §6.2)

**La riga di DDT dice «1 kit».** È un kit che si muove, è un kit che si rende, è
un kit che il cliente ha in mano. I componenti sono il dettaglio del **prezzo**,
non l'unità di misura della **merce**.

Perché non l'altra: contare i componenti obbligherebbe a esplodere anche il
consegnato e il reso, cioè a inventare N righe di merce dove il magazzino ne ha
mossa una. E renderebbe possibile lo stato assurdo *«mezzo kit reso»*.

**Come**: normalizzazione via `meta->>'coeff_qta'` (§8.2). Coefficiente mancante
o zero → partita **`NON_MISURABILE`**, mai zero.

### 9.6 ✅ Retroattività: la domanda si dissolve (risposta al §6.3)

Con una vista **non esiste un «prima»**. Le partite storiche — DDT standalone,
righe manuali, kit — appaiono con i loro valori dalla prima lettura, calcolate sui
dati che ci sono sempre stati. Nessuna bonifica, nessuna migrazione dati, nessuna
data di attivazione.

⚠️ **Restava un'eccezione onesta**: se un documento fosse stato fatturato **fuori**
dal push su commessa, il suo `fatturato` risulterebbe 0 e la partita direbbe «da
fatturare» a torto.

✅ **Chiusa per misura il 2026-08-17**: su **41 righe di fattura**, **zero** sono
prive di un'attività fatturabile a monte. Non esiste una fatturazione che scavalchi
il push, quindi la ricostruzione è **completa** e non c'è nulla da bonificare.

---

## 10. 🗺️ Il piano DB — otto slice

### ✅ D1 — DECISA (Tid, 2026-08-17): la partita nasce dal DDT **EMESSO** in poi

> **Con la voce `in_riconsegna`**, e le due cose insieme: correggere la soglia
> senza aggiungere la voce farebbe **sparire dalla lettura** la merce tornata e
> già impegnata su un DDT non ancora emesso (§8.3-bis).
>
> Le due righe d'ordine **236 e 239** passano da `tenuti 5` a `tenuti 2`, che è il
> numero vero: il cliente quei 3 pezzi li ha resi e non li ha ancora ri-ricevuti.
> Verificato che il cambio è **isolato** — quelle righe hanno `fatturati = 0`, non
> sono in coda accrediti, e le bozze non passano il cancello del push: nessun
> documento fiscale e nessuna coda di lavoro le vede.

**La domanda com'era posta, e le due strade valutate:**

|                          | Se **EMESSO** (raccomandato)                                                                                                  | Se **DRAFT**, cioè come oggi                                                                        |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Righe d'ordine 236 e 239 | `tenuti` 5 → **2** · `differenza` 5 → **2**                                                                                   | invariate                                                                                           |
| Corrisponde a            | quanti pezzi il cliente ha **davvero** in mano                                                                                | quanti ne avrà **se** la ri-consegna parte                                                          |
| Costo                    | 2 valori cambiano · serve la colonna `in_riconsegna` (§8.3-bis)                                                               | zero                                                                                                |
| Rischio                  | nessuno a valle: quelle 2 righe hanno `fatturati = 0`, non sono in coda accrediti e le bozze non passano il cancello del push | il pannello del cantiere 2 **nasce dicendo il falso**, e lo dice sul DDT accanto allo stato «Bozza» |

✅ **Raccomandazione: `EMESSO`.** Il numero corretto è 2, e i due valori che
cambiano sono **isolati** — verificato che non toccano né la fatturazione né la
coda accrediti. Rimandare significa costruirci sopra il pannello e correggere
dopo un numero che nel frattempo qualcuno avrà letto.

⚠️ **Non è però una correzione gratuita**: porta con sé `in_riconsegna`, senza la
quale 3 pezzi spariscono dalla lettura (né dal cliente, né in coda). Le due cose
si fanno insieme o nessuna delle due.

---

> ⛔ **Nessuna migrazione va applicata.** Il piano descrive **cosa** scrivere e in
> **che ordine**; l'applicazione la autorizza Tid, per quel comando, a voce.
>
> ⚠️ **Numerazione**: `YYYYMMDD-NN`, con **NN sequenza globale per data fra tutte
> le cartelle** — non per cartella. Al 2026-08-17 sono occupati `01`–`05`. I
> numeri sotto sono **indicativi**: si assegnano quando si scrive, guardando cosa
> c'è.

| Slice  | Cosa                                             | Cartella             | Rischio                             | Stato                                                                             |
| ------ | ------------------------------------------------ | -------------------- | ----------------------------------- | --------------------------------------------------------------------------------- |
| **S0** | Fotografia di riferimento delle 12 partite       | *(nessun changeSet)* | —                                   | ✅ **fatta** — `db/pgtap/vendite/fixtures/S0-fotografia-partita-merce-20260817.md` |
| **S1** | `vw_af_merce_per_riga` — normalizza kit e corsie | `20_code`            | 🟢 nuovo oggetto                     | ✅ **APPLICATA** — `20260817-06`, pgTAP **11/11** come applicazione                |
| **S2** | `vw_partite_merce` — **la partita**              | `20_code`            | 🟢 nuovo oggetto                     | ✅ **APPLICATA** — `20260817-07`, pgTAP **10/10** come applicazione                |
| **S3** | `vw_contatore_merce` riscritta come aggregato    | `20_code`            | 🔴 **dosa la fatturazione**          | ✅ **APPLICATA** — `20260817-08` (+ `-12`), pgTAP **11/11**, parità 18/18          |
| **S4** | `vw_resi_da_accreditare` riancorata              | `20_code`            | 🟠 documenti fiscali a valle         | ✅ **APPLICATA** — `20260817-09`, pgTAP **10/10**, output identico                 |
| **S5** | `fn_list_ddt_da_pushare` legge la partita        | `20_code`            | 🔴 **cambia le quantità in fattura** | ✅ **APPLICATA** — `20260817-10` + `-11`/`-12`, parità piena                       |
| **S6** | Guard di coerenza + avviso riga sospetta         | `20_code`            | 🟠 vedi §11                          | ✅ **APPLICATA** — `20260817-13`/`-14`, pgTAP **6/6** e **11/11**                  |
| **S7** | Doc manuale + richieste ad altri perimetri       | `docs/`              | 🟢                                   | ✅ **fatta** — §19                                                                 |

> ✅ **S1 e S2 applicate da Tid il 2026-08-17 alle 18:45** (`DATABASECHANGELOG`
> 12492 e 12493), con l'auto-gen della doc rigenerato.
>
> ✅ **E con l'applicazione è caduto il limite che restava.** Fino a quel momento
> i pgTAP erano girati solo come **owner** — che salta la RLS — perché farli
> girare come `zeroerp_app` richiede che le viste ESISTANO, e crearle è DDL che
> il ruolo applicativo giustamente non ha. Rifatti con `PGTAP_RUNNER=app`:
> **11/11 e 10/10 con la RLS attiva**. Il rilievo F (§8.6) è ora esercitato.
>
> ✅ **Nessuna regressione sui vicini**, ricontrollati come applicazione:
> `test-vw-contatore-merce-v1`, `test-vw-resi-da-accreditare-contatore-v1`,
> `test-fn-list-ddt-da-pushare-contatore-v1` → **PASS**. Atteso, perché S1 e S2
> sono oggetti nuovi che nessuno legge ancora: il primo cambio di comportamento
> è S3.

### S0 — La fotografia, prima di toccare (mezz'ora, nessun changeSet)

Congelare i **12 valori attuali** del contatore in un file, che diventa il
riferimento del test di parità di S3.

⭐ **Va fatto per primo e non è burocrazia**: il §4.2 chiede la parità «su dati
reali, non su fixture», e dopo S3 il **prima** non è più interrogabile. Se la
fotografia non si scatta adesso, la parità si può solo dichiarare.

Dove: `db/pgtap/vendite/fixtures/` (o allegato al brief) — non un changeSet, è
una misura.

### S1 — `vendite.vw_af_merce_per_riga` (nuova)

**Che cos'è**: l'unico posto in cui il sistema traduce *«un'attività fatturabile»*
in *«N pezzi di quale riga di documento»*. Oggi quella traduzione è **dentro** il
contatore, ed è il motivo per cui i kit lo rompono.

**Grana**: una riga per `(corsia, riga_id, tipo_movimento)`.

| Colonna          | Contenuto                                                                                           |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| `corsia`         | `'ORD'` \| `'DDT'` — da `split_part(segment_key, ':', 1)`                                           |
| `riga_id`        | `substring(segment_key, ':R:([0-9]+)')::bigint` — riga d'ordine o riga di DDT **secondo la corsia** |
| `tipo_movimento` | `NORMALE` \| `RETTIFICA` \| `ONERE` — **esposto, non filtrato**                                     |
| `quantita`       | in **unità della riga sorgente** (kit già normalizzati)                                             |
| `misurabile`     | `false` se un kit ha `coeff_qta` mancante o zero                                                    |

**Le due regole che stanno qui e in nessun altro posto:**

1. **Kit** → raggruppa per `split_part(segment_key, '#CMP:', 1)` (l'istanza di
   kit) e riporta `max(quantita / coeff_qta)`. `max` e non `sum`: i componenti
   sono **letture ripetute della stessa quantità di padre**, non addendi.
2. **Non-kit** → la quantità così com'è.

⚠️ **`tipo_movimento` si espone e non si filtra.** Il filtro `= 'NORMALE'` resta
nel consumatore. Così il cantiere 3 (nota di credito) accende la `RETTIFICA`
cambiando **un consumatore**, non la base su cui poggia tutto — che è il vincolo
§4.3 di questo brief e la sua richiesta di non pre-decidere.

**Sicurezza**: `WITH (security_invoker=on)` — `commesse_attivita` ha RLS
(⚠️ **da ri-specificare in ogni `CREATE OR REPLACE`**, PostgreSQL la azzera).

**pgTAP** (`test-vw-af-merce-per-riga-v1.sql`): esistenza · `security_invoker` ·
colonne · kit con `coeff_qta = 1` · **kit con `coeff_qta = 2`** (costruito
apposta, §8.2) · kit con `coeff_qta` assente → `misurabile = false` · corsia ORD e
corsia DDT distinte sullo stesso `riga_id` numerico · `ONERE` presente e
distinguibile.

### S2 — `vendite.vw_partite_merce` (nuova) — **la partita**

**Grana**: una riga per riga di DDT **attiva**, su un DDT **non abortito** e in
uno stato **da EMESSO in poi** (`stati_doc_ddt.ordine >= 20`).

🔴 **Quella soglia è la decisione D1**, in testa a questo §10: è la correzione del
§8.3 / §8.3-bis e **rompe la parità su 2 partite** (righe d'ordine 236 e 239,
`tenuti` 5 → 2). Con `EMESSO` la vista porta anche `in_riconsegna`; con `DRAFT`
si scrive come oggi e non serve.

| Colonna                                            | Note                                                                |
| -------------------------------------------------- | ------------------------------------------------------------------- |
| `ddt_riga_id`                                      | **la chiave della partita**                                         |
| `ddt_id`, `ddt_uid`, `articolo_id`, `is_composito` | contesto                                                            |
| `ordine_riga_id`, `ordine_id`                      | **nullable** — l'origine                                            |
| `origine`                                          | `ORDINE` \| `NESSUNA` \| `MULTIPLA` (§9.1)                          |
| `fatturabile`                                      | da `config.causali_trasporto` (§8.4)                                |
| `consegnato`                                       | `ddt_righe.quantita` — vedi la nota qui sotto                       |
| `reso`                                             | Σ `vw_resi_righe_effettive.quantita` **per `ddt_riga_id`** ⭐        |
| `in_riconsegna`                                    | reso già impegnato su un DDT **non emesso** — solo se D1 = `EMESSO` |
| `tenuti`                                           | `consegnato − reso`                                                 |
| `fatturato_merce`                                  | da S1, corsia `DDT`                                                 |
| `fatturato_da_ordine`                              | quota allocata della corsia `ORD` (§9.2)                            |
| `fatturato`                                        | somma dei due                                                       |
| `differenza`                                       | `tenuti − fatturato`, **NULL** se non fatturabile o non misurabile  |
| `stato`                                            | l'etichetta del §9.3 — **la traduzione unica del verso del saldo**  |

⭐ **La riga `reso` è il cuore della generalizzazione.** Passare da
`ordine_riga_id` a `ddt_riga_id` fa entrare nel conto i **2 resi standalone** che
oggi vengono scartati dal `WHERE ordine_riga_id IS NOT NULL`, e chiude il §8.5
per costruzione, perché `ddt_riga_id` è NOT NULL.

⚠️ **`consegnato` è `ddt_righe.quantita`, non `Σ qta_evasa`, e la differenza va
capita.** Sono due numeri diversi: *quanta merce è uscita* contro *quanta di
quella merce è attribuita a un ordine*. Oggi coincidono sempre (verificato: 24
righe order-backed, **0 discordanze**) e la parità è salva. Ma la riga di merce
deve dire quanta merce è uscita — **è proprio il caso della riga mista**, dove
una parte è ordinata e una no.

**pgTAP** (`test-vw-partite-merce-v1.sql`): le tre famiglie del §2 (standalone,
manuale su DDT da ordine, kit) · DDT in bozza **assente** · causale non
fatturabile → `NON_FATTURABILE` con `differenza` **NULL** e non 0 · reso su merce
standalone che produce `DA_ACCREDITARE` (è la §3.1 di questo brief) ·
`security_invoker` · **un test in contesto di scope ristretto**, che verifichi
`NON_MISURABILE` e **non** uno zero (§8.6).

### S3 — `vendite.vw_contatore_merce` riscritta (🔴 la slice critica)

Il contatore **resta**, con lo stesso nome e le stesse sei colonne, e diventa
**l'aggregato per riga d'ordine delle partite di S2**, più la corsia ORD.

**Perché non si rinomina**: ha due consumatori vivi (`vw_resi_da_accreditare` e
`fn_list_ddt_da_pushare`) e uno di essi decide quantità in fattura. Il nome è un
contratto.

**Colonne**: le sei di oggi **identiche, in posizione identica**, più — **in
coda** — `consegnato`, `reso`, `fatturato_su_merce`, `fatturato_su_ordine`,
`fatturato_anticipato`, `partite_merce`, `misurabile`.

⭐ **Aggiungere in coda ha una conseguenza pratica che vale la pena sfruttare**:
`CREATE OR REPLACE VIEW` accetta le colonne aggiunte in fondo, quindi **non serve
il `DROP`** — e senza `DROP` non si tocca `vw_resi_da_accreditare`, che dal
contatore dipende. Se anche una sola colonna esistente cambiasse nome, tipo o
posizione, servirebbe la coreografia del §11.2.

**Sparisce `WHERE NOT COALESCE(art.is_composito, false)`** (§8.2, §9.5).

**Il collaudo è la parità, e ha due metà:**

|                                      | Atteso                                                                                                                              |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| **12 righe di oggi**                 | **stessi identici valori** su `tenuti`/`fatturati`/`differenza` — tranne 236 e 239, che cambiano per la correzione dichiarata di S2 |
| **6 righe nuove** (kit order-backed) | compaiono, con `differenza 0` o positiva — **mai negativa**                                                                         |

⚠️ **`columns_are` va aggiornato nello stesso changeSet.** Il test 3 di
`test-vw-contatore-merce-v1.sql` elenca le sei colonne una per una: aggiungerne
sette lo fa fallire. E il test 10 (*«articolo COMPOSITO → riga d'ordine ESCLUSA
dalla vista (follow-up)»*) **verifica la toppa**: va riscritto per verificare
l'opposto, cioè che il kit c'è e vale 0.

⭐ Quel test è la prova che l'esclusione era **dichiarata provvisoria** («follow-up»)
da chi l'ha scritta a luglio: questo cantiere è il follow-up.

### S4 — `vw_resi_da_accreditare` riancorata sulla partita

Tre cambi, e il terzo è quello che sposta dei numeri:

1. la CTE `acc` legge `vw_partite_merce` invece di `vw_contatore_merce`;
2. il `JOIN` con `vw_resi_righe_effettive` passa da `ordine_riga_id` a
   `ddt_riga_id` — **NOT NULL**, quindi nessuna riga si perde e i 2 resi
   standalone entrano;
3. ⚠️ la finestra che scala i resi precedenti passa da `PARTITION BY
   e.ordine_riga_id` a `PARTITION BY e.ddt_riga_id`.

✅ **Il punto 3 era il rischio della slice, ed è stato chiuso per misura il
2026-08-17: oggi non sposta nulla.** Cambierebbe i valori solo se una riga
d'ordine avesse resi provenienti da **DDT diversi**. Verificato:

```text
righe d'ordine evase da 3 DDT ....................... 3  (236, 239, 610)
di queste, con resi da PIÙ DI UN DDT ................ 0
coda accrediti oggi ................ 2 righe, stesso reso, stesso DDT0010839
```

⚠️ **Ma «non sposta nulla» non è «è verificato».** Il ramo esiste e nessun dato
lo attraversa: **va provato con una fixture costruita apposta** — due resi sulla
stessa riga d'ordine da due DDT diversi — altrimenti è un ramo verde che nessuno
ha percorso. E il collaudo di non-regressione è secco: le **2 righe** di
`vw_resi_da_accreditare` (5 DOVUTA + 3 FACOLTATIVA su `RESO0005122/23`) devono
restare identiche.

✅ **`vw_resi_da_riconsegnare` non va toccata.** Verificato: espone già
`rr.ddt_riga_id` e non legge il contatore. La voce §3.2 di questo brief è **già
soddisfatta dal modello di oggi** — nessun lavoro.

### S5 — `fn_list_ddt_da_pushare` legge la partita (🔴 quantità in fattura)

Oggi la funzione fa **due lavori**: prende la differenza per riga d'**ordine** e
poi la **ridistribuisce** sulle righe di DDT, con un caso speciale per
composito/standalone.

Con la partita, **la differenza è già per riga di DDT**: la ridistribuzione
sparisce, e con essa il caso speciale.

```text
LEFT JOIN vw_contatore_merce ct ON ct.ordine_riga_id = src.src_ordine_riga_id
  + finestra greedy + CASE composito/standalone → dr.quantita
      ↓
JOIN vw_partite_merce pm ON pm.ddt_riga_id = dr.id     →  pm.differenza
```

⚠️ **Slice a sé, dopo la parità di S3, con i suoi test.** È l'unico punto del
piano in cui cambia **quanto** finisce in una riga di fattura. Il test è
`test-fn-list-ddt-da-pushare-contatore-v1.sql`, che esiste già.

⭐ **E qui il cantiere restituisce qualcosa**: le righe standalone e le righe
manuali, che oggi vanno in fattura a `dr.quantita` **grezza** (nessuno tiene il
conto, quindi nessuno sa se sono già state fatturate), passano sotto lo stesso
dosatore delle altre. **Il doppio-invio su una riga standalone oggi è possibile e
non è presidiato dal contatore** — solo dal classificatore
`fn_get_stato_push_segment`. Dopo, lo è da entrambi.

### S6 — I due presidi

**S6a — guard di coerenza sull'origine del reso** (§8.5).
`vendite.trgfn_resi_righe_guard_origine_coerente`, fase `_a20_` su `resi_righe`:
se il `ddt_riga_id` ha un fulfillment, `ordine_riga_id` dev'essere **NULL o
coincidente**. Errore via `script.fn_log_and_raise_error` con codice registrato
(**mai `E_GENERICO`**; codice nuovo = **solo append al CSV**, nessun loader nuovo).

⚠️ **Prima di scriverlo, `grep` sui pgTAP dei resi.** Un guard restrittivo su una
tabella con fixture esistenti rompe test che non c'entrano: è già successo in
questo progetto, ed è il motivo per cui la regola esiste. `test-resi-motore-v1`,
`test-resi-rinunce-*` e `test-vw-resi-*` costruiscono righe di reso.

**S6b — l'avviso sulla riga manuale sospetta** (risposta al §6.4).

Non un blocco: **una lettura**. Colonna `sospetto_duplicato_ordine` su
`vw_partite_merce`, vera quando **tutte e tre**:

* la riga di DDT non ha origine (`origine = 'NESSUNA'`), **e**
* il DDT ha altre righe **con** origine (spedizione mista), **e**
* l'articolo compare fra le righe dell'ordine che quelle altre righe evadono.

⭐ **Perché una lettura e non un guard.** Il caso legittimo esiste ed è comune —
lo stesso articolo spedito in più del dovuto, o un ricambio dello stesso codice
— e vietarlo significherebbe l'opzione B, scartata dal §7-bis del brief NC per un
costo **fisico**: due documenti di trasporto su un solo viaggio. L'avviso mette
davanti agli occhi ciò che prima era invisibile, e lascia decidere.

⚠️ **Presuppone che il pannello lo mostri**: è una richiesta al cantiere 2, ed è
scritta nel §12.

### S7 — Documentazione e richieste

* `docs/it/dbzero/vendite/manual/vw_partite_merce.md` — cos'è una partita, in
  parole comprensibili anche a chi non scrive SQL;
* aggiornare `manual/vw_contatore_merce.md`: **è diventato un aggregato**, e le
  colonne nuove hanno un senso che il nome non dice;
* ⛔ **non toccare a mano** i file in `dbzero/<schema>/{views,funzioni,tabelle}/`:
  si rigenerano;
* ⛔ **non rigenerare `changelog-autogen.yaml` a mano**: lo fa `liquibase5.sh` al
  migrate, ed è gitignored;
* §12 di questo brief → aperto ai perimetri BE e FE.

---

## 11. ⚠️ Le trappole di QUESTO cantiere

### 11.1 `security_invoker=on` si perde a ogni `CREATE OR REPLACE`

Non compare in `pg_get_viewdef`, quindi **non si vede copiando la definizione
dalla doc auto-gen** — e senza, la vista legge scavalcando la RLS. Le tre viste
toccate (`vw_contatore_merce`, `vw_resi_da_accreditare`, più le due nuove) la
richiedono. La doc auto-gen la riporta a parte, in un riquadro: **è lì che va
letta**, non nel corpo.

### 11.2 Se una colonna esistente cambiasse, servirebbe una coreografia

Il piano evita il `DROP` aggiungendo **solo in coda** (S3). Se per qualunque
motivo si dovesse rinominare o ritipare una colonna del contatore:

1. `vw_resi_da_accreditare` **dipende** dal contatore → il `DROP` fallisce;
2. **mai `CASCADE`** — cancellerebbe la dipendente in silenzio, e l'autogen la
   ricreerebbe (o no) a seconda dei numeri;
3. l'autogen include `00_schema` e `20_code` **ordinando per NN**, non per
   cartella: chi **ricrea** una dipendenza deve avere un numero **più alto** di
   chi la droppa. Tre changeSet, tre numeri crescenti, un ordine che va guardato.

### 11.3 `runOnChange` e `validCheckSums`

`runOnChange: true` è **vietato** in `00_schema` e `20_code` — presidiato in CI.
Se serve come appoggio locale, va **spento prima del commit** e va detto a Tid.
E chi lo spegne corregge anche la chiave: `validCheckSums` è **al plurale**, il
singolare è ignorato da Liquibase e diventa un migrate rosso proprio nel momento
in cui il `runOnChange` si spegne.

### 11.4 Il pgTAP gira come l'applicazione, con la RLS attiva

Dal 2026-08-07: `zeroerp_app` + contesto operatore. Tre righe di preambolo
obbligatorie e presidiate (`BEGIN;`, contesto, `SET CONSTRAINTS ALL IMMEDIATE`).
`throws_ok` **sempre con lo SQLSTATE** (`P0001` per un errore di dominio),
altrimenti accetta anche il crash del guard che dovrebbe provare.

⚠️ E per il §8.6 serve **di più del contesto standard**: un test che gira con uno
scope che **non** vede la commessa, per verificare che la partita dica
`NON_MISURABILE` e non `0`. Attenzione: **svuotare `app.current_user_id` non è
fail-closed** — il cancello è `app.ruolo_applicativo`.

### 11.5 La misura della suite vuole `ON_ERROR_STOP=1`

Senza, `psql` tira dritto dopo l'errore: gli `ok` risultano gonfiati e i file
rossi sottostimati. E la suite **ha rossi preesistenti**: usare
`scripts/pgtap-baseline.sh vendite` per distinguere una regressione propria da un
debito noto, invece di inseguirlo.

### 11.6 Il fatturato di una tabella con RLS: zero non è un dato

Vale in fase di **collaudo**, non solo di disegno. Se una misura di verifica gira
come applicazione e restituisce `fatturato = 0`, la prima domanda è *«è zero o
non lo vedo?»*. Le misure di parità di S0 e S3 vanno fatte **come owner**, e
quelle di scope **come applicazione**: sono due domande diverse e vogliono due
utenti diversi.

### 11.7 🔴 Niente `preCondition` su dati di `80_data` dentro `20_code`

**Successo davvero, sul migrate di S6a** (`20260817-13`):

```text
SQL Precondition failed. Expected '1' got '0'
```

La `sqlCheck` verificava che il codice errore `E_RESO_ORIGINE_INCOERENTE` fosse
già in `config.codici_errore`. Ma Liquibase applica **`20_code` prima di
`80_data`**: quando il changeSet gira, il seed del codice non è ancora passato —
e al primo migrate non lo sarà mai, per costruzione.

⭐ **E la verifica non serviva comunque**: il codice viene risolto **a runtime**
da `fn_log_and_raise_error`, cioè quando il guard scatta, non quando la funzione
si crea. Il presidio che il codice esista ha già la sua sede — il cancello sui
codici non dichiarati.

⚠️ **La regola generale**: una `preCondition` in `20_code` può guardare solo
cose di `00_schema` e `20_code` — tabelle, colonne, viste, funzioni. Mai una
riga di dati.

---

## 12. Richieste agli altri perimetri

> Questo brief è **perimetro DB**: non si tocca `backend/`. Le richieste si
> scrivono qui.

### Al backend

| #        | Richiesta                                                          | Perché                                                                                                                                   |
| -------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **BE-1** | Esporre `vw_partite_merce` filtrata per DDT e per ordine           | È il pannello del cantiere 2. La vista porta già `ddt_id` e `ordine_id`: sono due filtri, non due letture                                |
| **BE-2** | **Non ri-tradurre il verso del saldo in Python**                   | La colonna `stato` esiste apposta (§9.3, e §5.4 del brief pannello: *«una volta sola, in un punto condiviso»*). Due traduzioni divergono |
| **BE-3** | Trattare `differenza = NULL` come **«non si applica»**, non come 0 | §8.4 e §8.6. Un `COALESCE(…, 0)` nel repository rimette dentro esattamente i falsi allarmi che questo cantiere toglie                    |
| **BE-4** | Verificare che `_kit_meta` continui a scrivere `coeff_qta`         | Da S1 in poi quel campo non serve più solo alla fattura: senza, la partita del kit diventa `NON_MISURABILE`                              |

### Al frontend

| #        | Richiesta                                                   | Perché                                                                                               |
| -------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **FE-1** | `NON_MISURABILE` e `PAREGGIATA` devono **apparire diversi** | §5.2 del brief pannello: *«tutto regolare deve essere visibilmente diverso da non ancora calcolato»* |
| **FE-2** | Mostrare `sospetto_duplicato_ordine` sulla riga             | È la risposta al §6.4, e senza il FE l'avviso non esiste                                             |
| **FE-3** | `fatturato_anticipato` non è un accredito                   | §8.1. Se il pannello lo somma alla differenza, torna il difetto che il piano ha appena tolto         |

### 🔴 Al cantiere 3 (nota di credito) — due cose che si vedono solo da qui

**NC-1 — `uq_commesse_attivita_commessa_segment` blocca la strada scelta.**

Il §4 del brief NC propone che l'accredito diventi *«un'attività di commessa di
rettifica con quantità negativa, legata alla stessa partita»*. Ma esiste:

```sql
UNIQUE (commessa_id, segment_key)   -- uq_commesse_attivita_commessa_segment
```

**Una seconda attività sullo stesso segmento della stessa commessa non può
esistere.** La rettifica avrà bisogno di un `segment_key` **proprio** — plausibile
un suffisso, sul modello di `#CMP:` che il sistema già usa e già sa leggere.

⭐ **E la buona notizia è che il modello lo regge già**: l'estrazione
`substring(segment_key, ':R:([0-9]+)')` **continua a funzionare** con un suffisso
in coda — è esattamente ciò che fa oggi con i kit. La rettifica resterà
attribuita alla partita giusta **senza toccare S1**.

⚠️ Va però verificato l'effetto su `script.fn_get_stato_push_segment`, che
classifica per uguaglianza **o** prefisso `#CMP:%`: un suffisso nuovo va
aggiunto lì, o una riga rettificata risulterebbe `LIBERA` e verrebbe **ri-spinta**
in fatturazione.

**NC-2 — il filtro `NORMALE` è già pronto a spostarsi.**

S1 espone `tipo_movimento` senza filtrarlo (§4.3 di questo brief: *«il criterio va
rivisto insieme al punto 3 della catena, ma la decisione è di quel cantiere»*).
Quando la NC arriverà, far scendere i `fatturati` sarà **cambiare un `WHERE` in
un consumatore** — non rifare la base.

---

## 13. Sequenza consigliata, in una riga

```text
S0 fotografia → S1 base AF → S2 la partita → S3 contatore a parità
   → S4 coda accrediti → S5 dosatore fatturazione → S6 presidi → S7 doc
```

⭐ **Le prime tre non toccano nulla di vivo** (S0 misura, S1 e S2 sono oggetti
nuovi che nessuno legge ancora). Il primo momento in cui il sistema cambia
comportamento è **S3**, e ci si arriva con la fotografia in mano.

**Il cantiere 2 può partire dopo S3.** Il cantiere 3 dopo S5.

---

## 14. 📓 Diario di esecuzione — 2026-08-17

### 14.1 Cosa c'è nel repository

| File                                                                                            | Cos'è                                                                                                   |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `db/pgtap/vendite/fixtures/S0-fotografia-partita-merce-20260817.md`                             | La misura di riferimento: contatore, due code, dosatore. **Non è un test**, è l'unica copia del «prima» |
| `db/changelog/migrations_v2/20_code/vendite/20260817-06-create-vw-af-merce-per-riga-mctit.yaml` | S1 — la base che normalizza kit e corsie                                                                |
| `db/pgtap/vendite/test-vw-af-merce-per-riga-v1.sql`                                             | 11 test, **11 verdi**                                                                                   |
| `db/changelog/migrations_v2/20_code/vendite/20260817-07-create-vw-partite-merce-mctit.yaml`     | S2 — la partita                                                                                         |
| `db/pgtap/vendite/test-vw-partite-merce-v1.sql`                                                 | 10 test, **10 verdi**                                                                                   |

Cancelli statici: `guardrail_run_on_change` ✅ · `guardrail_pgtap_preambolo` ✅
(debito `throws_ok` invariato a 137, la soglia) · `check_license` ✅ · YAML ✅.

**Applicazione e collaudo (Tid, 2026-08-17)**: migrazione applicata alle 18:45
(`DATABASECHANGELOG` 12492-12493), auto-gen della doc rigenerato, e
`scripts/pgtap-baseline.sh vendite` sull'intero schema → **nessuna regressione**.
I due file nuovi girano verdi **come applicazione** (`PGTAP_RUNNER=app`), quindi
con la RLS attiva: è la corsa che vale, e chiude il rilievo F.

### 14.2 La parità, misurata

Aggregando le partite per riga d'ordine e confrontando con il contatore vivo:

```text
10 righe su 12 .......... IDENTICHE
 2 righe (236, 239) ...... cambiate, ed è la decisione D1
```

Nessuna riga inattesa si è mossa. E i due `DA_ACCREDITARE` che restano hanno
**entrambi un reso a monte**: il falso allarme del rilievo A non si presenta.

### 14.3 ⭐ Un accredito che oggi il sistema non vede

Emerso applicando S2 ai dati veri:

```text
ORD0000227 · riga di DDT 126 · articolo COMPOSITO
1 kit consegnato · 1 kit fatturato · 1 kit reso  →  differenza −1
```

**È un accredito dovuto, e oggi non lo vede nessuno**, perché la riga è tagliata
da `WHERE NOT is_composito`. Non è un caso costruito per il test: è nel database
di sviluppo da prima che questo cantiere iniziasse.

### 14.4 Le due cose imparate scrivendo, non progettando

1. **§8.4-bis** — `fatturabile` da solo non può spegnere il conto: la causale
   parla del viaggio, il fatturato è un fatto. Corretta nella vista.
2. **Il ramo dei kit non era davvero verificato.** In sviluppo tutti i
   `coeff_qta` valgono 1: la divisione che normalizza non veniva esercitata. Il
   pgTAP di S1 costruisce un kit con coefficienti **2 / 1 / 0.5** su quantità
   20 / 10 / 5, che devono concordare tutti sul padre **10**. È il test che i
   dati reali non potevano dare.

### 14.5 Cosa resta, e da dove riprendere *(diario del 2026-08-17 — superato, vedi §23)*

**S3** — riscrivere `vw_contatore_merce` come aggregato di `vw_partite_merce`.
È la prima slice che cambia il comportamento del sistema. Due avvertenze già
verificate:

* si aggiungono colonne **in coda**, quindi `CREATE OR REPLACE` basta e
  `vw_resi_da_accreditare` non va toccata (niente `DROP`, niente coreografia);
* ⚠️ il test 3 di `test-vw-contatore-merce-v1.sql` elenca le sei colonne con
  `columns_are`: **va aggiornato nello stesso changeSet**. E il suo test 10
  verifica *l'esclusione dei compositi*: va riscritto per verificare l'opposto.

Poi S4 (coda accrediti), S5 (dosatore), S6 (presidi), S7 (doc).

---

## 15. 📓 Diario — S3, e la documentazione concettuale

### 15.1 La documentazione delle due viste nuove

Scritte in `docs/it/dbzero/vendite/manual/` — la sede giusta, perché
`views/`, `tabelle/` e `funzioni/` si rigenerano e non vanno toccate a mano:

* `manual/vw_af_merce_per_riga.md` — le **due trappole** che questa vista
  esiste per disinnescare: le due corsie con numeri che si somigliano, e i kit
  contati in unità sbagliata;
* `manual/vw_partite_merce.md` — che cos'è una partita, in parole comprensibili
  anche a chi non scrive SQL;
* `manual/vw_contatore_merce.md` — **aggiornata**: non calcola più, legge. In
  testa c'è un rimando esplicito, perché chi cerca il conto della merce per
  lavorarci deve finire sulle partite, non qui.

Auto-gen rigenerato (`DB_DOC_SCHEMAS=vendite`): la riga di `include-markdown`
compare in testa alle due viste, e tutti i link sono stati verificati.

### 15.2 S3 — il contatore diventa un aggregato

**Parità, verificata riga per riga contro la vista viva:**

```text
10 righe su 12 .......... IDENTICHE (tenuti, fatturati, differenza)
 2 righe (236, 239) ...... cambiate — decisione D1
+6 righe nuove ........... i kit, che l'esclusione teneva fuori
```

**pgTAP `test-vw-contatore-merce-v1.sql`: 11/11**, e i quattro test che leggono
il contatore (`vw-resi-da-accreditare-contatore`, `fn-list-ddt-da-pushare-contatore`,
`resi-rinunce-scenario`, `porta-oneri-contatore-cieco`) restano verdi sotto la
definizione nuova.

⚠️ **Il test 10 andava riscritto, non aggiustato.** Verificava che *«la riga
d'ordine con articolo COMPOSITO è ESCLUSA dalla vista»* — cioè **presidiava la
toppa**. Un test che difende una rinuncia va riscritto quando la rinuncia
finisce, altrimenti difende il difetto. Ora verifica l'opposto: il kit c'è, e
conta in unità del padre.

⭐ **E ne è nato un test 11 che i dati reali non potevano dare**: spedito 4 di
10, fatturato 10 sull'ordine → `differenza −6` **e** `fatturato_anticipato 6`.
Le due asserzioni insieme sono il punto — il saldo resta negativo per parità,
ma accanto c'è finalmente la colonna che dice che non è un accredito, è merce
da spedire.

### 15.3 🔴 L'unico effetto a valle, e va guardato prima di applicare

**La coda accrediti passa da 2 righe a 3.** Le due esistenti sono **identiche**
(5 DOVUTA, 3 FACOLTATIVA su `RESO0005122/23`): non cambia un valore. Ne entra
una:

```text
RESO0000017 · DDT0000062 · ORD0000227 · articolo COMPOSITO
1 kit consegnato · 1 kit fatturato · 1 kit reso  →  accredito dovuto 1 · DOVUTA
```

✅ **È un accredito vero**, ed è il motivo per cui il cantiere esiste: quella
merce è stata fatturata e restituita, e finora la coda non poteva vederla
perché la riga era tagliata dall'esclusione dei compositi.

⚠️ **Ma è comunque una riga nuova in una coda che produrrà documenti fiscali**,
e va vista da una persona prima di applicare — non scoperta dopo.

### 15.4 Un limite di `fatturato_anticipato`, dichiarato

La colonna copre la spedizione **parziale**, non l'**assenza** di spedizione:
una riga fatturata sull'ordine e mai spedita non è nella vista per niente
(non lo era nemmeno prima), quindi il suo anticipo non si vede.

**È voluto.** Portarla dentro significherebbe far comparire **12 righe con
saldo negativo** su merce che deve solo partire — cioè il falso allarme del
rilievo A, esattamente ciò che il cantiere serve a togliere. Se un giorno
servirà leggerlo, è una lettura a sé e non un allargamento di questa vista.

---

## 16. 📓 Diario — S4, la coda accrediti

`20260817-09`. Tre cambi, e solo il terzo può spostare numeri.

|     |                                                                         |
| --- | ----------------------------------------------------------------------- |
| 1   | la CTE `acc` legge **vw_partite_merce** invece di `vw_contatore_merce`  |
| 2   | il `JOIN` con i resi passa da `ordine_riga_id` a **`ddt_riga_id`**      |
| 3   | la finestra che scala i resi già serviti partiziona per **riga di DDT** |

⭐ **Il punto 2 è il cantiere in una riga**: `ordine_riga_id` è *facoltativo*,
`ddt_riga_id` è **obbligatorio**. Agganciarsi al primo significa che un reso su
merce senza ordine esce dal conto **senza dare errore**.

### 16.1 Sul database di oggi non cambia nulla

Confronto riga per riga contro la vista viva: **le 3 righe sono identiche** —
accredito e etichetta — e le **24 colonne** del contratto restano tutte, una per
una. Il backend le whitelista per nome (`_CODA_META`) e il frontend ci mappa le
severity: bastava toglierne una per rompere entrambi.

`ordine_riga_id` vuoto: **0 righe oggi**. Non perché il caso non esista, ma
perché i due resi su merce standalone del DB non hanno un accredito dovuto —
quella merce non era stata fatturata. ⭐ **Ed è il modello che funziona**: *«un
reso entra in commessa solo se fatturato»*.

### 16.2 I due rami che nessun dato attraversa — costruiti nel test

**Test 9 — merce senza origine ordine.** Riga aggiunta a mano, 6 pezzi usciti e
fatturati, 2 tornati: accredito **2**, e `ordine_riga_id` **NULL**. Le due cose
in un'asserzione sola, perché è la coppia a essere il punto.

**Test 10 — una riga d'ordine, due spedizioni.** È l'unico posto in cui la
partizione nuova e quella vecchia danno numeri diversi:

```text
spedizione A:  4 usciti · 4 fatturati · 4 tornati   →  accredito 4
spedizione B:  6 usciti · 0 fatturati · 3 tornati   →  accredito 0
```

⚠️ **Con la partizione per riga d'ordine il conto si mescolava**: tenuti 3,
fatturati 4 → accredito di partita 1, e la prima riga di reso ne prendeva **1
invece di 4**. Il reso *non fatturato* della spedizione B diluiva l'accredito
dovuto sulla A. Il caso non esiste nei dati — 3 righe d'ordine sono evase da 3
DDT, ma nessuna ha resi da più di un DDT — quindi la fixture lo costruisce.

### 16.3 Verifiche

`test-vw-resi-da-accreditare-contatore-v1.sql` → **10/10**. E i tre test che
leggono la coda (`resi-rinunce-scenario`, `vw-dash-backlog-resi`, `resi-motore`)
restano verdi sotto la definizione nuova.

Doc concettuale aggiornata: `manual/vw_resi_da_accreditare.md`.

### 16.4 ⚠️ Una richiesta al backend che nasce qui

Il commento di `resi_repository.py` dice oggi: *«`ddt_numero`/`ddt_id` possono
essere NULL (aggancio partita via `ordine_riga_id`, join DDT diventato LEFT)»*.
**Da S4 in poi è esattamente al contrario**: il DDT c'è sempre (i join sono
tornati `INNER`), e a poter mancare è `ordine_riga_id`. Il commento va corretto,
e va verificato che nulla a valle usi `ordine_riga_id` come chiave.

---

## 17. 📓 Diario — S5, e la regressione che un test vecchio ha fermato

### 17.1 🔴 Il difetto: la ri-consegna contata come merce nuova

Scritta S5, un test è diventato rosso — e non era un test da aggiornare:

> `test-fn-list-ddt-da-pushare-contatore-v1`, caso D:
> *«ri-consegna di merce già fatturata → il DDT nuovo proietta 0, non pushato
> (chiude bug 1a)»*

⭐ **Quel test presidia un comportamento del 2026-07, e ha intercettato una
regressione del modello del 2026-08.** È la ragione per cui i test che
descrivono *cosa deve succedere* non si riscrivono quando cambia
l'implementazione sotto: sono l'unica cosa che sopravvive al rifacimento.

**Il difetto era nella slice S2, non in S5.** Quando il cliente rende merce e
gliela si rispedisce, nasce una riga di DDT **nuova** per pezzi **già consegnati
e già contati**. `vw_partite_merce` la trattava come una partita a sé:
`consegnato = N`, `fatturato = 0`, quindi `DA_FATTURARE N`. Cioè **merce da
fatturare una seconda volta**.

⚠️ **E non era solo nel test.** Sul database, applicata la S2:

```text
riga di DDT 524 · 6 pezzi · DA_FATTURARE   ← ri-consegna della riga 521
riga di DDT 525 · 2 pezzi · DA_FATTURARE   ← ri-consegna della riga 521
```

Il vecchio modello non aveva il problema perché aggregava per riga d'ordine, e
lì la ri-consegna era solo un fulfillment in più che rialzava il consegnato.
**Spostando la chiave sulla riga di merce quella compensazione si è persa.**

### 17.2 La correzione, e perché sono due changeSet

`20260817-07` era già applicata, quindi si corregge **in avanti**.

**`20260817-11`** — la ri-consegna rientra nel `consegnato` della partita
d'**origine** e non ne apre una propria. La riga resta visibile con
`e_riconsegna = true`, `differenza` NULL e `stato = 'RICONSEGNA'`: senza, il
pannello del DDT di ri-consegna mostrerebbe righe sotto e nessun conto sopra.

⭐ **E rende simmetrico ciò che prima era scritto in due posti che non si
parlavano**: la ri-consegna in bozza è `in_riconsegna`, quella emessa torna nel
`consegnato`. Stesso fatto, due momenti.

**`20260817-12`** — e qui c'è la parte che il primo changeSet da solo peggiorava.
`vw_contatore_merce` aggrega tutte le partite che hanno una riga d'ordine, e una
riga di ri-consegna ce l'ha (`fn_genera_ddt_riconsegna` le crea un fulfillment).
Quindi i pezzi venivano contati **due volte**: una nel consegnato dell'origine,
una come partita a sé.

```text
riga d'ordine 610    corretto ............ tenuti  9
                     col -11 da solo ..... tenuti 17     ← peggio di prima
```

⚠️ **I due changeSet vanno applicati insieme**, e la parità si misura dopo
entrambi.

### 17.3 Verifiche, dopo `-10` + `-11` + `-12`

|                                |                              |
| ------------------------------ | ---------------------------- |
| contatore                      | **18 righe su 18 identiche** |
| dosatore (quantità in fattura) | **2 su 2 identiche**         |
| coda accrediti                 | **3 su 3 identiche**         |

pgTAP: `fn-list-ddt-da-pushare-contatore` **7/7** (compreso il caso D che aveva
fermato tutto), `vw-partite-merce` **10/10**, `vw-contatore-merce` **11/11**,
`vw-resi-da-accreditare-contatore` **10/10**, più `fn-list-ddt-da-pushare-v1/v2`,
`push-list-gia-inviato`, `ddt-solo-trasporto-causale`, `resi-rinunce-scenario`,
`porta-oneri-contatore-cieco` — tutti verdi.

⚠️ `test-fn-list-ddt-da-pushare-orfano-v1` è rosso, **e non è di questo
cantiere**: è in `baseline-rossi.tsv` come `ERRORE_FIXTURE`, e fallisce identico
senza alcuna modifica.

### 17.4 I test riscritti, e perché è legittimo

**Caso F** (`fn-list-ddt-da-pushare-contatore`, test 6-7). Riga d'ordine da 10
spezzata in due spedizioni (6 e 4), reso 5 sulla prima:

```text
prima:   il greedy d'ordine scaricava tutto sulla più vecchia   →  5  e  0
adesso:  ogni spedizione porta il suo residuo                   →  1  e  4
```

⚠️ **Il totale non cambia: 5 in entrambi i casi** — ed è quello che finisce in
fattura. La ripartizione decide solo su quale documento compare la riga. Per
questo il test 6 ora asserisce l'**invariante** (il totale) e il 7 la
ripartizione: se un domani cambiasse il totale, il 6 lo direbbe subito. Il
greedy d'ordine non sapeva *da quale spedizione* la merce fosse tornata; la
partita lo sa.

### 17.5 Due cose imparate, che valgono oltre questo cantiere

1. ⭐ **Un test che presidia un comportamento vale più del modello che lo ha
   generato.** Il caso D è stato scritto a luglio per una struttura che a
   agosto non esiste più, e ha fermato una regressione che nessuna delle mie
   verifiche di parità avrebbe visto — perché la parità si misura su ciò che
   *c'è*, e la doppia fatturazione sarebbe arrivata al **prossimo** documento.
2. ⚠️ **`CREATE OR REPLACE VIEW` non cambia il tipo di una colonna esistente.**
   `consegnato` era `numeric(18,6)` e la somma con la ri-consegna lo allargava a
   `numeric`: changeSet fallito. Il cast non è cosmetico, ed è annotato nel file
   perché la prossima volta si veda subito.

---

## 18. 📓 Diario — S6, i due presidi

### 18.1 Il guard sull'origine del reso (`20260817-13`)

`vendite.trgfn_resi_righe_guard_origine_coerente`, fase `_a20_`.

**La regola è un bicondizionale**, e le due direzioni sono lo stesso errore
visto dai due lati:

```text
la riga di DDT evade un ordine   →  ordine_riga_id valorizzato e coincidente
la riga di DDT non evade nulla   →  ordine_riga_id vuoto
```

⭐ **La direzione che conta di più è la seconda metà della prima**: il campo
*vuoto* su merce ordinata. È il caso più probabile, perché non richiede di
sbagliare nulla — basta non compilare. E il costo è che il residuo dell'ordine
**non si riapre**: la merce torna e l'ordine non se ne accorge.

**Perché è stato sicuro introdurlo ora**, verificato prima di scriverlo:

* **0 violazioni** sulle 17 righe di reso esistenti;
* il backend **deriva già** il campo dallo snapshot della riga DDT — il
  chiamante passa solo `ddt_riga_id`;
* gli **11 file pgTAP** che inseriscono in `resi_righe` lo ricavano tutti dal
  fulfillment: nessuno diventa rosso.

### 18.2 ⚠️ Il guard bloccava con l'errore sbagliato

Prima versione: le tre violazioni venivano respinte, ma con
`42883 — la funzione script.fn_log_and_raise_error non esiste`. Mancava
l'argomento **VARIADIC**: senza almeno un valore la risoluzione dell'overload
fallisce, e quello che esce non è l'errore di dominio ma il crash del guard.

🔴 **Un `throws_ok` senza SQLSTATE avrebbe dato quel rosso per verde**: il test
avrebbe visto «ha sollevato un'eccezione» e sarebbe passato, presidiando un
guard rotto. È il motivo per cui il progetto ha una soglia su quel debito, e la
ragione è più concreta di quanto sembri leggendola.

Il test di S6a passa `P0001` esplicito su tutti e tre i casi, e ne ha un quarto
che verifica che il caso **corretto passi** — un guard che blocca tutto non è un
guard.

### 18.2-bis 🔴 Il guard HA rotto un test, e la verifica era mal posta

Applicato il guard, la baseline ha trovato un rosso:
`test-resi-rinunce-fondamenta-v1` — *«La riga d'ordine indicata sul reso non
corrisponde a quella della riga DDT resa»*.

⚠️ **Eppure il §18.1 dice che gli 11 file pgTAP erano stati verificati.** Lo
erano, e la verifica era **sbagliata nella domanda**: avevo cercato *come* i
file valorizzano `ordine_riga_id`. Per costruzione quella ricerca mostra solo i
file che la colonna ce l'hanno — **chi la omette non poteva comparire**.

La domanda giusta è l'opposto: *chi inserisce **senza** la colonna?* Fatta così,
trova esattamente un file:

```text
INSERT INTO vendite.resi_righe (reso_id, riga_nr, ddt_riga_id, articolo_id, …)
                                            ↑ ordine_riga_id assente → NULL
```

⭐ **E il guard aveva ragione.** La riga di DDT che quella fixture pesca dai dati
di sviluppo **evade un ordine**: il reso risultava su merce ordinata senza
riferimento all'ordine, cioè esattamente la condizione in cui
`fn_ordine_riga_qta_riconsegna` — che prende la riga d'ordine come parametro —
non riapre il residuo. La merce torna e l'ordine non se ne accorge.

Corretta la **fixture**, non il guard: ricava `ordine_riga_id` dal fulfillment
come fanno gli altri dieci file. `NULL` resta corretto se la riga di DDT non
evade nulla, ed è quello che il sotto-select produce da sé.

✅ **Baseline `vendite` completa dopo la correzione: 24 rossi, tutti già noti in
`baseline-rossi.tsv` — nessuna regressione.** E la scansione rifatta bene, estesa
a `db/`, `backend/` e agli `UPDATE` oltre che agli `INSERT`, non trova più
nessuna scrittura che possa violare il guard.

### 18.3 L'avviso sulla riga sospetta (`20260817-14`)

Colonna `sospetto_duplicato_ordine` su `vw_partite_merce`. Tre condizioni
insieme: riga senza origine, **su spedizione mista**, con un articolo **già
nell'ordine** che le altre righe evadono.

Senza la seconda segnalerebbe ogni DDT standalone; senza la terza ogni riga
extra, pallet a rendere e omaggi compresi. Insieme descrivono esattamente la
situazione ambigua.

⭐ **È una lettura, non un divieto** — risposta alla domanda §6.4. Il caso
legittimo esiste ed è comune, e vietarlo sarebbe l'opzione B del brief nota di
credito, scartata per un costo **fisico**: due documenti di trasporto per una
sola spedizione.

⚠️ **Senza il frontend non esiste.** Una colonna che nessuno mostra non avvisa
nessuno: finché FE-2 non è fatta, il presidio è a metà.

---

## 19. 📌 S7 — Le richieste agli altri perimetri, in blocco

> Questo cantiere è **perimetro DB**: `backend/` e `frontend/` non sono stati
> toccati. Qui c'è tutto ciò che serve dall'altra parte, raccolto in un posto
> solo perché non vada perso in sette diari.
>
> **Nessuna di queste è bloccante per il DB**, che è completo e verde. Sono ciò
> che serve perché il lavoro **si veda** e perché nulla rimanga a raccontare il
> mondo di prima.

### 19.1 Backend — le cinque cose

| #        | Cosa                                                                           | Perché, in una riga                                                                                                                                         | Dove                                    |
| -------- | ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| **BE-1** | Esporre `vw_partite_merce` filtrata per DDT e per ordine                       | è il pannello del cantiere 2; la vista porta già `ddt_id` e `ordine_id`, sono due filtri non due letture                                                    | nuovo endpoint                          |
| **BE-2** | **Non ri-tradurre** il verso del saldo in Python                               | la colonna `stato` esiste apposta; due traduzioni divergono e diventano due frasi per lo stesso numero                                                      | —                                       |
| **BE-3** | Trattare `differenza = NULL` come «non si applica», **mai** come 0             | un `COALESCE(…, 0)` nel repository rimette dentro i falsi allarmi che il cantiere ha tolto                                                                  | repository                              |
| **BE-4** | 🔴 **Correggere il commento in `resi_repository.py`**                           | dice *«`ddt_numero`/`ddt_id` possono essere NULL (aggancio via `ordine_riga_id`)»*: **da S4 è l'opposto** — il DDT c'è sempre, a mancare è `ordine_riga_id` | `resi_repository.py`, coda accrediti    |
| **BE-5** | Verificare che nulla usi `ordine_riga_id` come **chiave** sulla coda accrediti | può essere NULL: è la merce senza ordine che finalmente entra                                                                                               | `resi_repository.py`, `resi_service.py` |

⚠️ **BE-4 è quello da fare per primo**, e non perché sia grosso: è un commento
che oggi **dice il falso** a chi legge, ed è il tipo di errore che nessun test
intercetta.

**Da verificare (non una richiesta, una conferma)**: il codice
`E_RESO_ORIGINE_INCOERENTE` è dichiarato nel CSV con classe `DATO_ERRATO`, come
tutti i suoi gemelli. Va confermato che il cancello del terzo lato
(`test_error_codes_db_policy_guardrail`) resti verde senza aggiunte a
`error_policies.py`.

### 19.2 Frontend — le tre cose

| #        | Cosa                                                        | Perché                                                                                          |
| -------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| **FE-1** | `NON_MISURABILE` e `PAREGGIATA` devono **apparire diversi** | *«tutto regolare»* e *«non ancora calcolato»* non sono la stessa cosa (§5.2 del brief pannello) |
| **FE-2** | Mostrare `sospetto_duplicato_ordine` sulla riga             | è la risposta al §6.4, e **senza il FE non esiste**                                             |
| **FE-3** | `fatturato_anticipato` **non è** un accredito               | se il pannello lo somma alla differenza, torna il falso allarme appena tolto                    |

Nuovi stati da mappare nella tavolozza: `RICONSEGNA` e `NON_MISURABILE` si
aggiungono ai quattro già previsti.

### 19.3 🔴 Cantiere nota di credito — tre cose che si vedono solo da qui

**NC-1 — `uq_commesse_attivita_commessa_segment` blocca la strada scelta.**
Una seconda attività sullo stesso segmento della stessa commessa **non può
esistere**: la rettifica avrà bisogno di un `segment_key` proprio, plausibilmente
con un suffisso sul modello di `#CMP:`. ✅ L'estrazione
`substring(segment_key, ':R:([0-9]+)')` continua a funzionare con un suffisso in
coda, quindi la rettifica resta attribuita alla partita giusta **senza toccare
S1**.

**NC-2 — il filtro `NORMALE` è già pronto a spostarsi.** `vw_af_merce_per_riga`
espone `tipo_movimento` senza filtrarlo: far scendere i `fatturati` sarà
cambiare un `WHERE` in un consumatore, non rifare la base.

**NC-3 — ⚠️ e la cintura che tiene è una sola.** Quando la rettifica abbasserà
il `fatturato`, la `differenza` della partita tornerà **positiva** su una riga
già fatturata, e `fn_list_ddt_da_pushare` la ri-spingerebbe in fattura. Non
succede **solo** perché `script.fn_get_stato_push_segment` esclude ogni riga già
instradata. Chi introdurrà un `segment_key` nuovo per la rettifica **deve
insegnarglielo**, o quella cintura si apre.

### 19.4 Lavoro a valle rimasto al DB

* **`fn_ddt_push_diagnosi` non conosce il motivo nuovo**: una riga non spinta
  perché la sua partita non è misurabile oggi non ha una spiegazione. Il push la
  salta correttamente e in modo esplicito, ma chi cerca *perché* non la trova.
* **Assunzione da presidiare se cambia `fn_genera_ddt_riconsegna`**: oggi la
  quantità del ponte copre **tutta** la riga di ri-consegna (verificato sui 6
  ponti esistenti). Se un domani una riga fosse in parte ri-consegna e in parte
  merce nuova, quella parte nuova resterebbe fuori dal conto.

---

## 20. ✅ Stato di sviluppo al 2026-08-17 — perimetro DB chiuso

### 20.1 I nove changeSet, tutti applicati

| #   | ChangeSet     | Cosa                                                                                                                         |
| --- | ------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| S1  | `20260817-06` | `vw_af_merce_per_riga` — la base: attività fatturabili → quantità per riga di documento, kit normalizzati in unità del padre |
| S2  | `20260817-07` | `vw_partite_merce` — **la partita**                                                                                          |
| S3  | `20260817-08` | `vw_contatore_merce` diventa un aggregato                                                                                    |
| S4  | `20260817-09` | `vw_resi_da_accreditare` agganciata alla partita                                                                             |
| S5  | `20260817-10` | `fn_list_ddt_da_pushare` legge la partita                                                                                    |
| 🔴   | `20260817-11` | **correzione**: la ri-consegna non è merce nuova                                                                             |
| 🔴   | `20260817-12` | **correzione**: l'aggregato esclude le ri-consegne                                                                           |
| S6a | `20260817-13` | guard di coerenza sull'origine del reso                                                                                      |
| S6b | `20260817-14` | `sospetto_duplicato_ordine`                                                                                                  |

Più il codice errore `E_RESO_ORIGINE_INCOERENTE` (`config/codici_errore.csv` +
`messaggi_errore.csv`), la fotografia S0 e la documentazione concettuale (S7).

### 20.2 Il collaudo, come applicazione

**Baseline `vendite` completa, come applicazione** (`PGTAP_RUNNER=app`, 184
file): **24 rossi, tutti già noti in `baseline-rossi.tsv` — nessuna
regressione**. I quindici file nuovi, riscritti o toccati da questo cantiere
sono verdi con la RLS attiva.

⚠️ Un rosso è comparso e **non era preesistente**: `test-resi-rinunce-fondamenta-v1`,
rotto dal guard di S6a. Fixture corretta, non guard allentato — le ragioni nel
§18.2-bis.

⚠️ `test-fn-list-ddt-da-pushare-orfano-v1` resta rosso, **e non è di questo
cantiere**: è in `baseline-rossi.tsv` come `ERRORE_FIXTURE` da prima.

### 20.3 Il conto della merce, oggi

```text
27 partite di merce, di cui
    7  senza ordine dietro   ← prima non esistevano nel conto
    9  articoli compositi    ← prima erano esclusi per costruzione
    2  righe di ri-consegna  ← dichiarate, senza conto proprio

stati:  13 DA_FATTURARE · 7 PAREGGIATA · 3 NON_FATTURABILE
         2 DA_ACCREDITARE · 2 RICONSEGNA

contatore per riga d'ordine ....... 18 righe, 0 non misurabili
coda accrediti .................... 3 righe
righe eleggibili alla fatturazione . 2
```

⭐ **Il numero che riassume il cantiere è il primo: sette partite di merce che
prima non comparivano affatto** — non a zero, proprio assenti. Più nove kit che
l'esclusione teneva fuori.

E le due `DA_ACCREDITARE` hanno **entrambe un reso a monte**: nessun falso
allarme è entrato insieme alla generalizzazione.

### 20.4 Cosa questo cantiere ha lasciato agli altri

|                                            |                                                                                                                                                                                     |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Cantiere 2** — pannello situazione merce | ✅ **sbloccato**: legge `vw_partite_merce`, che copre ordine, DDT, righe manuali e kit con una lettura sola, e porta `stato` già tradotto                                            |
| **Cantiere 3** — nota di credito           | ✅ **sbloccato**, e con tre avvertenze precise (§19.3) — la più importante è che `fn_get_stato_push_segment` è l'**unica** cintura che impedirà di ri-fatturare una riga rettificata |
| **Backend / Frontend**                     | ✅ otto richieste in §19 **tutte fatte** (BE 2026-08-17, FE 2026-08-18)                                                                                                                                |

### 20.5 Le tre cose che questo cantiere ha insegnato

1. 🔴 **Un test che presidia un comportamento vale più del modello che l'ha
   generato.** Il caso D di luglio ha fermato una doppia fatturazione che
   nessuna verifica di parità avrebbe visto — la parità misura ciò che c'è, il
   danno sarebbe arrivato al documento successivo.
2. ⚠️ **Un guard che blocca non è un guard che funziona.** Il primo tentativo di
   S6a respingeva le violazioni con «la funzione non esiste»: un `throws_ok`
   senza SQLSTATE l'avrebbe dato per verde.
3. ⚠️ **Una verifica può essere fatta e restare sbagliata.** Prima del guard
   avevo controllato gli 11 file che scrivono i resi — cercando *come*
   valorizzano il campo. Quella domanda non poteva trovare chi lo **omette**, e
   il file che lo ometteva è finito in baseline. Quando si cerca «chi rompe una
   regola nuova», la domanda va posta sull'**assenza**, non sulla presenza.
4. ⚠️ **Le esclusioni dichiarate vanno riaperte, non ereditate.** `WHERE NOT
   is_composito` era una rinuncia scritta a luglio con la sua data e il suo
   motivo; il test che la presidiava andava riscritto, non aggiustato. Un test
   che difende una rinuncia, quando la rinuncia finisce, difende il difetto.

---

## 21. 📌 Perimetro BE/FE — cosa è già fatto e cosa resta da decidere

> Scritto il **2026-08-17**, dopo il push del DB. Questa parte non tocca il
> modello: raccoglie l'esecuzione delle otto richieste del §19 e le domande che
> non si possono chiudere senza Tid.

### 21.1 ✅ Fatto subito — e una delle tre cose era **rossa adesso**

| #            | Cosa                                                        | Esito                                                  |
| ------------ | ----------------------------------------------------------- | ------------------------------------------------------ |
| **BE-0**     | policy + messaggio di ripiego del codice errore nuovo       | 🔴 **tre cancelli erano rossi**, vedi sotto — ora verdi |
| **BE-4**     | commento di `resi_repository.list_da_accreditare`           | ✅ corretto: diceva l'opposto del vero                  |
| **BE-5**     | `ordine_riga_id` usato come **chiave** sulla coda accrediti | ✅ **zero occorrenze**, misurato — nessuna modifica     |
| **§12 BE-4** | `_kit_meta` scrive ancora `coeff_qta`                       | ✅ sì, e la sede è quella che S1 legge                  |

#### 🔴 BE-0 — la «conferma» del §19.1 aveva una risposta, ed era «no»

Il §19.1 chiudeva con *«Da verificare (non una richiesta, una conferma): va
confermato che il cancello del terzo lato resti verde senza aggiunte a
`error_policies.py`»*. **La domanda era ben posta e la risposta misurata è che il
cancello non era affatto verde**:

```text
test_error_codes_db_policy_guardrail            →  FAIL (verso 1)
  E_RESO_ORIGINE_INCOERENTE  [da trigger]  (vendite.trgfn_resi_righe_guard_origine_coerente)
test_error_policies_divergenza_db               →  FAIL (--check: il modulo DIVERGE dal catalogo)
test_ogni_codice_vivo_ha_un_messaggio_di_ripiego →  FAIL (codice vivo senza fallback)
```

⭐ **E non perché mancasse una decisione: la decisione c'era già, nel CSV.** Il
codice è seminato con `classe = DATO_ERRATO`; ciò che mancava era la **seconda
metà del gesto** — `error_policies_generated.py` è generato dal catalogo, e
nessuno lo aveva rigenerato dopo il seed. Rimedio:

```bash
./manage-env.sh genera_error_policies      # 696 → 697 voci, una riga + il suo commento
```

`error_policies.py` **non è stato toccato**, ed è esattamente ciò che il §19.1 si
aspettava: la classe viene dal catalogo, status e `ui_action` si derivano.

⚠️ **Il terzo cancello non era prevedibile leggendo il §19.1, ed è il più
interessante.** `USER_MESSAGE_FALLBACK` (`error_messages_fallback.py`) pretende
un messaggio **senza segnaposto** per ogni codice **vivo**: è ciò che l'operatore
legge quando il messaggio del database non arriva. Il codice nuovo non ce
l'aveva. Aggiunto a mano — quel modulo *non* è generato, ed è voluto: il catalogo
ha i buchi che `fn_log_and_raise_error` riempie a runtime, questi sono quelli che
si mostrano quando gli argomenti non ci sono. **Una riga.**

⚠️ **La regola che ne esce, e vale oltre questo cantiere**: *un codice errore
nuovo seminato dal DB lascia il repository rosso finché il backend non fa le sue
due mosse* — rigenerare le policy **e** scrivere il messaggio di ripiego. Le metà
stanno in perimetri e commit diversi, quindi il rosso non compare a chi applica
la migrazione: compare al primo che manda una PR. Va nella lista di consegna del
team DB, accanto al changeSet.

#### BE-4 — il commento diceva l'opposto, verificato contro la definizione viva

```text
prima:  «ddt_numero/ddt_id possono essere NULL (aggancio partita via
         ordine_riga_id, join DDT diventato LEFT)»
oggi:   i join a ddt_righe e ddt sono INNER  →  ddt_id/ddt_numero ci sono SEMPRE
        a poter mancare è ordine_riga_id, che non è più la chiave
```

Il commento nuovo dice anche **perché** può mancare (merce senza origine ordine:
riga aggiunta a mano, DDT standalone) e che **nessun consumatore lo usi come
chiave** — così BE-5 resta presidiato da qualcosa che si legge, non solo da una
misura fatta una volta.

#### BE-5 — la misura, in quattro punti

| Dove                                                                      | `ordine_riga_id` usato come chiave?         |
| ------------------------------------------------------------------------- | ------------------------------------------- |
| `_CODA_META` (`order_cols` / `search_cols`)                               | ❌ assente                                   |
| `resi_service.list_da_accreditare`                                        | ❌ assente (filtra etichetta/BA/date/search) |
| FE — `resiCoda.js`, `ResiCodaTable.vue`, `constants.js`                   | ❌ assente                                   |
| seed `ui.lista_colonna` della lista `vendite.resi_da_accreditare` (id 10) | ❌ assente                                   |

Viaggia solo come campo passante nel `SELECT v.*`. **Niente da correggere**, ed è
il modello che ha funzionato: la merce senza ordine entra nella coda senza che
nessun consumatore se ne accorga.

#### §12 BE-4 — il `coeff_qta` è ancora scritto, e nella sede giusta

`BoMComponentExpander` scrive `meta['coeff_qta']` su **`commesse_attivita`**
(`commesse_source_handlers.py`), col contratto centralizzato in `_kit_meta.py`
(`META_KEY_COEFF_QTA`). `vw_af_merce_per_riga` legge `ca.meta ->> 'coeff_qta'`
sulla **stessa tabella**: la catena si chiude. ⭐ Il §8.2 lo aveva anticipato —
la vista è ora il **terzo consumatore** di quel contratto e il primo che lo
verifica su ogni riga.

### 21.2 ✅ BE-1 — FATTO (2026-08-17)

**Cosa**: due letture read-only della stessa fonte.

```text
GET /api/v1/vendite/ordini/<ordine_id>/situazione-merce/
GET /api/v1/vendite/ddt/<ddt_id>/situazione-merce/
```

✅ **Realizzato come descritto qui sotto**, con in piu' le decisioni D-2/D-3/D-4:
quattro sezioni in un round-trip (`righe_ordine` · `partite` · `accrediti` ·
`riconsegne`). Doc:
[api_situazione_merce.md](../../backend/vendite/manual/api_situazione_merce.md).
9 test service verdi + prova con chiamata REALE al DB (i mock non vedono il
binding SQL). ✅ **Integrato** (PR #1283, insieme a `20260817-15`).

⭐ **La prova che vale piu' dei test**: l'ordine del §3 del brief pannello — le
cinque schermate — torna in **una chiamata sola**.

```text
righe_ordine  riga 1 · ordinato 21 · tenuti 13 · fatturato 21
                     · differenza -8 · da_spedire 3 · DA_ACCREDITARE
partite       DDT0010839 · origine ORDINE · consegnato 21 · -8 · DA_ACCREDITARE
accrediti     RESO0005122 · 5 · DOVUTA     RESO0005123 · 3 · FACOLTATIVA
riconsegne    RESO0005123 · residua 3 · DA_RICONSEGNARE
```

| Scelta                                                                            | Perché                                                                                                                                                                                               |
| --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Un factory**, sul modello di `build_riepilogo_iva_view` e `build_passaggi_view` | due domini dal primo giorno, e il §5.1 del brief pannello ne dichiara due **per costruzione**. ⚠️ È la **regola del 2**: dichiarata qui, in attesa dell'ok di Tid                                     |
| **Due filtri, una lettura** (`ddt_id` / `ordine_id` su `vw_partite_merce`)        | è testualmente la richiesta BE-1: *«sono due filtri, non due letture»*                                                                                                                               |
| **Display fields via JOIN**                                                       | la vista porta il solo `articolo_id`: servono codice/descrizione/UoM (e sul lato ordine numero e `riga_nr`). JOIN nella lettura, mai lookup client-side                                              |
| **`stato` passa così com'è** (BE-2)                                               | nessun `if differenza > 0` in Python: la traduzione del verso del saldo è **una sola**, e sta nella vista                                                                                            |
| **`differenza = NULL` viaggia come `null`** (BE-3)                                | nessun `COALESCE`, né in Python né **in SQL nel repository** — la vista lo mette NULL apposta, e `0` rimetterebbe dentro i falsi allarmi del §8.4 e del §8.6                                         |
| **Nessun filtro applicativo di scope**                                            | `security_invoker=on`: il cancello è la RLS su `ddt`/`commesse_attivita`. Si legge con la connessione dell'utente, **mai da un canale di sistema** (stessa regola di `vw_fondi_fattura_da_decidere`) |
| **Nessuna paginazione**                                                           | le partite di un documento sono decine. Come `ApiDdtRighe`: `success_response` con la lista                                                                                                          |
| `DomainAPIView`, `area_funzionale = "vendite"`, LETTURA, `@extend_schema`         | checklist nuovo endpoint di `api.md`                                                                                                                                                                 |

⚠️ **E vale il §8.6 anche a video**: `misurabile = false` non è uno zero. Il
backend lo trasporta, il frontend lo distingue (FE-1).

**Dove**: lettura in `vendite_repository.py` (perimetro «generico schema»,
convenzione di naming di `AGENTS.md`), orchestrazione in `vendite_service.py`,
view dal factory in `apps/vendite/api/`. Test service con repository mockato
(`unittest.TestCase`, niente DB — regola CI).

### 21.3 ✅ FE-1 / FE-2 / FE-3 — FATTE (2026-08-18)

> Il testo qui sotto e' rimasto **com'era scritto** il 2026-08-17, perche' la
> ragione per cui allora non si potevano fare si legge meglio accanto a com'e'
> andata a finire: **avevano bisogno del pannello**, e il pannello ora c'e'.
>
> * **FE-1** — `NON_MISURABILE` e' **rosso** in `STATO_MERCE_MAP`, contro il
>   grigio di `NON_FATTURABILE` e il verde di `PAREGGIATA`. I due «grigi» non
>   sono lo stesso grigio: uno e' sano («non si applica»), l'altro e' un conto
>   che non si **puo'** fare.
> * **FE-2** — il chip «da verificare» su `sospetto_duplicato_ordine`, con il
>   tooltip che spiega perche' il caso legittimo esiste. Senza, la colonna di
>   S6b non avvisava nessuno.
> * **FE-3** — `fatturato_anticipato` **non e'** fra i chip-compito e non entra
>   in nessuna somma di saldo: compare nel dettaglio, dichiarato («di cui N
>   gia' fatturati e non ancora spediti»).
>
> E i due stati nuovi in tavolozza (`RICONSEGNA`, `NON_MISURABILE`) sono
> arrivati **col** loro consumatore, non prima.

#### Com'era la situazione il 2026-08-17

Le tre richieste frontend del §19.2 sono **requisiti sul pannello del cantiere
2**, che non esiste: `NON_MISURABILE` contro `PAREGGIATA` (FE-1),
`sospetto_duplicato_ordine` (FE-2), `fatturato_anticipato` che non è un
accredito (FE-3) sono tutte cose che *un pannello* deve fare.

⚠️ **Anche i due stati nuovi da mettere in tavolozza** (`RICONSEGNA`,
`NON_MISURABILE` in `core/utils/severity.js`) **non vanno anticipati**: una mappa
di severity che nessun componente consuma è codice morto, e la scelta dei colori
si fa guardando il pannello, non il vocabolario.

⭐ **Le tre richieste non si perdono**: sono già scritte in §19.2 e vanno
riprese come **definizione di fatto** del cantiere 2 — la loro sede è quel brief,
non questo.

### 21.4 ❓ Domande aperte — servono a Tid, non le decido io

**D-1 · Il perimetro di «procedi allo sviluppo».** Il cantiere 2 (pannello
situazione merce su ordine e DDT) è **dentro** questo giro o è il passo
successivo?
→ **Raccomandazione: fuori.** BE-1 adesso, perché è la richiesta scritta ed è il
prerequisito; il pannello come cantiere a sé, che ha le sue cinque decisioni di
forma già prese nel §5 del suo brief e una definizione di fatto propria.
⚠️ Il costo dichiarato di questa scelta: BE-1 nasce **senza consumatore**, e un
endpoint che nessuno chiama è esattamente ciò che il §8.7 di questo brief
descrive come pericoloso — *«non è mai stato mostrato a una persona»*.

**D-2 · La forma della lettura sull'ordine.** La partita è per **riga di DDT**:
un ordine da 3 righe evase con 2 DDT dà fino a 6 partite, e il §5.2 del brief
pannello vuole un **riassunto in testata**. Due strade:

|           | Cosa restituisce l'endpoint                                                                                                                                      |
| --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **(a)**   | le partite grezze; il riassunto lo somma il frontend                                                                                                             |
| **(b)** ⭐ | **due livelli**: righe d'ordine da `vw_contatore_merce` (che *è già* l'aggregato per riga d'ordine e porta `fatturato_anticipato`, cioè FE-3) + le partite sotto |

→ **Raccomandazione: (b).** L'aggregato esiste già a DB: ri-sommarlo in Python
sarebbe la **terza** copia della stessa somma, ed è la stessa ragione per cui
BE-2 vieta di ri-tradurre `stato`.

**D-3 · Le righe d'ordine mai spedite** — ed è la domanda che tocca il modello.
Il §15.4 dichiara che una riga fatturata sull'ordine e **mai spedita** non sta in
nessuna delle due viste: né partita, né contatore. Sul pannello dell'ordine
quella riga **non compare affatto** — l'operatore vedrebbe 3 righe su 4. Sono le
**12 righe** del rilievo A.

|           | Cosa si vede                                                                                            |
| --------- | ------------------------------------------------------------------------------------------------------- |
| **(a)**   | solo ciò che si è mosso, **dichiarando** quante righe non sono ancora partite                           |
| **(b)** ⭐ | l'endpoint fa `LEFT JOIN` da `ordini_righe`: la riga compare con `consegnato 0` e **`differenza` NULL** |
| **(c)**   | niente: si vedono solo le partite (è il comportamento di oggi)                                          |

→ **Raccomandazione: (b), ma solo con `differenza` NULL.** Un pannello d'ordine
che non nomina una riga ordinata mente per omissione — è lo stesso difetto del
§8.3-bis, la merce che sparisce dalla lettura. ⚠️ **Con `differenza` valorizzata
sarebbe invece la riapertura del rilievo A**: 12 righe con saldo negativo su
merce che deve solo partire, cioè il falso allarme che questo cantiere ha appena
tolto.
⚠️ E (b) porta con sé una coda: quella riga vorrebbe uno **stato** che oggi non
è nel vocabolario del §9.3 (`DA_SPEDIRE`?). Nascerebbe nel frontend o come
colonna a DB — e la prima strada è quella che BE-2 vieta.

**D-4 · Le due code dentro lo stesso endpoint?** Il §4 del brief pannello chiede
anche *«da accreditare»* con l'etichetta dovuto/facoltativo e *«da
riconsegnare»* col residuo: stanno in `vw_resi_da_accreditare` e
`vw_resi_da_riconsegnare`, **non** nella partita.
→ **Raccomandazione: dentro**, un round-trip solo, sul modello di
`GET /vendite/fatture/<id>/` che restituisce il documento completo. Il costo è
due letture in più nel service; il guadagno è che il pannello **non può**
contraddire le code, che è l'ultima voce della definizione di fatto del cantiere 2.

**D-5 · L'ok alla regola del 2.** Chiedo l'autorizzazione a estrarre
`build_situazione_merce_view` come **factory** invece di scrivere due view
gemelle: due domini dal primo giorno, e i due precedenti in casa
(`build_riepilogo_iva_view`, `build_passaggi_view`) hanno la stessa forma.

### 21.5 ✅ Decisioni di Tid (2026-08-17) e risposta a D-1

| #       | Esito                                                                                           |
| ------- | ----------------------------------------------------------------------------------------------- |
| **D-2** | ✅ due livelli — ⚠️ **con una correzione sulla fonte del livello 1**, vedi §21.6                  |
| **D-3** | ✅ `LEFT JOIN` da `ordini_righe`, `differenza` NULL sulle righe mai spedite                      |
| **D-4** | ✅ le due code dentro lo stesso endpoint, un round-trip solo                                     |
| **D-5** | ✅ estrazione del BB autorizzata (`build_situazione_merce_view`)                                 |
| **D-1** | ❓ *«il pannello del cantiere 2 ha bisogno di attività DB?»* → **sì, ed è UNA sola cosa**, §21.6 |

#### La risposta a D-1, voce per voce

| Cosa serve al pannello                                      | Da dove                                                                                    | DB?                                      |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------- |
| situazione **della spedizione** (lato DDT)                  | `vw_partite_merce` filtrata per `ddt_id`                                                   | ✅ **c'è**                                |
| dettaglio per partita sull'ordine                           | `vw_partite_merce` filtrata per `ordine_id`                                                | ✅ **c'è**                                |
| `sospetto_duplicato_ordine` (FE-2), `NON_MISURABILE` (FE-1) | colonne della partita                                                                      | ✅ **c'è**                                |
| «da accreditare» con etichetta dovuto/facoltativo (D-4)     | `vw_resi_da_accreditare`                                                                   | ✅ **c'è**                                |
| «da riconsegnare» col residuo (D-4)                         | `vw_resi_da_riconsegnare`                                                                  | ✅ **c'è**                                |
| codice/descrizione/UoM articolo, numero ordine, `riga_nr`   | JOIN nella lettura del repository                                                          | ✅ nessun oggetto nuovo                   |
| tabella del pannello                                        | DataTable annidata `app-datatable--inner` in un drawer, **non** una `<ListaConfigurabile>` | ✅ **nessun seed** `ui.lista_definizione` |
| testi                                                       | `it.json` / `en.json`                                                                      | ✅ solo FE                                |
| scope                                                       | la **testata** è il cancello (`vendite.ordini` / `vendite.ddt` hanno la RLS, le righe no)  | ✅ pattern BE già in uso sulla fattura    |
| **riassunto per riga d'ordine** (livello 1, D-2 + D-3)      | ⛔ **non esiste un oggetto che lo dia con la semantica giusta**                             | 🔴 **una vista nuova**                    |

### 21.6 🔴 Il rilievo che corregge D-2 — misurato, non dedotto

**Avevo raccomandato `vw_contatore_merce` come livello 1. È la fonte sbagliata**,
e lo dice la documentazione della vista stessa, scritta da questo cantiere:

> *«Questa resta il contatore **GREZZO** che dosa le macchine; chi vuole la
> semantica parlante (`stato`, NULL = "non si applica") legge
> `vw_partite_merce`.»*

Due difetti concreti, non stilistici.

**1. Il contatore appiattisce i NULL, e il pannello mostrerebbe un falso allarme.**
`vw_contatore_merce.differenza` **non è mai NULL** — è deliberato, perché
`fn_list_ddt_da_pushare` fa `COALESCE(differenza, 0)` e un NULL smetterebbe di
fatturare una riga in silenzio. Ma la formula è `tenuti − fatturato` e non guarda
né `fatturabile` né `misurabile`. Quindi su una riga d'ordine le cui partite sono
tutte `NON_FATTURABILE`:

```text
livello 2 (partite):    differenza NULL   →  «non si applica»
livello 1 (contatore):  differenza = tenuti − 0 > 0  →  «N da fatturare»
```

⚠️ **È esattamente il falso allarme che il §8.4 ha tolto**, rientrato dalla porta
del livello 1.

**Zero occorrenze oggi — e nulla lo impedisce**, che è la distinzione del
preambolo della PARTE II:

```text
partite NON_FATTURABILE ......................... 3, tutte SENZA ordine  → oggi salvo
righe di DDT order-backed su causale NON fatturabile ................ 5  → la porta è aperta
```

⭐ **E una di quelle cinque è il caso dell'§8.4-bis**: riga di DDT 47,
`CONTO_VISIONE`, riga d'ordine 172. Non si contraddice **solo perché** la corsia
ORD l'aveva già fatturata (`PAREGGIATA`, 1 e 1). Con `fatturazione_trigger =
'SPEDITO'` (2 ordini su 95) o col push non ancora passato, quella riga darebbe
`NULL` al livello 2 e **«1 da fatturare» al livello 1**, su un conto visione.

**2. Il contatore non ha `stato`, e D-3 ne chiede un sesto valore.**
Le sue colonne sono numeri grezzi. La traduzione del verso del saldo — che BE-2
vieta di rifare in Python — sul livello 1 **non esiste**. E la riga mai spedita
di D-3 vuole un valore che il vocabolario del §9.3 non ha.

**3. E il livello 1 non può nemmeno partire dal contatore**, per D-3: il
contatore è `FROM pm JOIN ordini_righe`, quindi le righe mai spedite non ci sono.
Misurato:

```text
righe d'ordine attive ......................... 107
di cui SENZA alcuna partita (mai spedite) ...... 89   ← l'83%
di cui gia' fatturate sulla corsia ORD ......... 12   ← il rilievo A
```

⭐ **Con l'opzione (c) il pannello dell'ordine sarebbe vuoto su 89 righe su
107.** D-3 non era una raffinatezza: senza, il pannello non si vede quasi mai.

#### ✅ Cosa ne discende: una vista sola, e la sede giusta

Il **principio** di D-2 resta intero — due livelli, e il livello 1 non si somma
in Python. Cambia la **fonte**: non `vw_contatore_merce`, ma una vista nuova che
sia l'aggregato **parlante** per riga d'ordine.

```text
vendite.vw_situazione_merce_ordine     (nome di lavoro)
  FROM ordini_righe  LEFT JOIN  (aggregato di vw_partite_merce)   ← D-3
  + ordinato, consegnato, reso, tenuti, fatturato, in_riconsegna
  + fatturato_anticipato                                          ← FE-3
  + differenza con la propagazione dei NULL                       ← il difetto 1
  + stato, col sesto valore per la riga mai spedita               ← D-3
```

⚠️ **`vw_contatore_merce` non si tocca**: dosa la fatturazione (§8.7). La vista
nuova è **accanto**, non al posto — la stessa forma della raccomandazione del
§9.4 per l'eventuale materializzata.

✅ **FATTA dal team DB il 2026-08-17** — `20260817-15`, pgTAP 11/11, con tre
cambi rispetto alla richiesta. Brief chiuso e archiviato:
[work-done/brief-db-situazione-merce-ordine.md](../work-done/brief-db-situazione-merce-ordine.md).

🟡 **RIAPERTO il 2026-08-18** — rilievo del perimetro BE: alla vista mancava la
**soglia sullo stato dell'ordine**, gemella della decisione D1 sul DDT. 60 righe
su 107, tutte su ordini in bozza, dichiaravano «N da spedire» — un'intenzione
presentata come un arretrato — e su un ordine annullato mai spedito il numero
sarebbe rimasto lì per sempre. Rilievo accolto, **rimedio modificato**: la riga
NON sparisce (il pannello è per ordine e sparire lo renderebbe vuoto), sparisce
il numero — `da_spedire` NULL e `stato` col **settimo** valore `NON_IMPEGNATA`,
con le partite che hanno la precedenza. changeSet `20260818-06`, pgTAP a 17.
✅ **Applicato**, baseline senza regressioni, e il FE l'ha gia' assorbito nella
stessa giornata. Analisi completa nel §10 del brief archiviato.

✅ **Pushata e integrata il 2026-08-18** (PR #1282). Il backend era stato
costruito introspezionando la vista **viva**: il corpo pubblicato coincide.

🔴 **E due cose le ho sbagliate io, scritte lì**: la formula di `da_spedire`
(divergeva proprio sulla riga da 21 pezzi che ha generato il cantiere) e la
misura «5 righe su causale non fatturabile», che erano **1** — le altre 4 le
contava un `COALESCE(fatturabile, false)` che tratta *«causale assente»* come
*«non fatturabile»*, cioè esattamente l'errore che questo brief descrive due
volte.

**Perché a DB e non nel repository backend**: il vocabolario di `stato` e la
regola *«se tutte le partite dicono non-si-applica, il livello 1 dice
non-si-applica»* sono **la stessa nozione del §9.3**. Scriverle in Python
significherebbe una **seconda sede** del vocabolario — cioè precisamente ciò che
BE-2 vieta — presidiata da nessun pgTAP. È il motivo per cui il §9.3 dice *«qui
è il DB a garantirlo, così il FE non deve inventarselo»*: vale identico per il BE.

#### Cosa può partire subito, senza aspettare

| Pezzo                                                        | Dipende dalla vista nuova? |
| ------------------------------------------------------------ | -------------------------- |
| il factory `build_situazione_merce_view` (D-5)               | ❌ no                       |
| lato **DDT**: partite filtrate per `ddt_id`                  | ❌ no — è completo oggi     |
| lato **ordine**, livello 2: partite filtrate per `ordine_id` | ❌ no                       |
| le due code nell'envelope (D-4)                              | ❌ no                       |
| lato **ordine**, livello 1: il riassunto per riga d'ordine   | ✅ **sì**                   |

---

## 22. ✅ Stato del perimetro BACKEND al 2026-08-18 — chiuso

> Speculare al §20, che chiude il perimetro DB. Qui c'è cosa il backend ha
> fatto delle otto richieste del §19, e cosa resta.

### 22.1 Le richieste del §19, una per una

| #                           | Richiesta                                                   | Stato                                                                        |
| --------------------------- | ----------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **BE-1**                    | esporre `vw_partite_merce` filtrata per DDT e per ordine    | ✅ **fatto**, e cresciuto in un pannello a 4 sezioni (D-2/D-3/D-4)            |
| **BE-2**                    | non ri-tradurre il verso del saldo in Python                | ✅ `stato` passa così com'è — presidiato da un test                           |
| **BE-3**                    | `differenza = NULL` è «non si applica», mai 0               | ✅ nessun `COALESCE`, né in Python né in SQL — presidiato da un test          |
| **BE-4**                    | correggere il commento di `resi_repository.py`              | ✅ diceva l'opposto del vero                                                  |
| **BE-5**                    | nulla usi `ordine_riga_id` come chiave sulla coda accrediti | ✅ **zero occorrenze**, misurato in 4 punti                                   |
| **§12 BE-4**                | `_kit_meta` scrive ancora `coeff_qta`                       | ✅ sì, e nella tabella che S1 legge                                           |
| *(la «conferma» del §19.1)* | il cancello del terzo lato resta verde?                     | 🔴 **no, era rosso** — §21.1                                                  |
| **FE-1/2/3** | tavolozza, avviso, anticipo | ✅ **fatte** col pannello del cantiere 2 (2026-08-18), validato in-app |

### 22.2 Cosa è stato scritto

| File                                                      | Cosa                                                                             |
| --------------------------------------------------------- | -------------------------------------------------------------------------------- |
| `core/services/error_policies_generated.py`               | rigenerato dal catalogo (696 → 697)                                              |
| `core/services/error_messages_fallback.py`                | il messaggio di ripiego del codice nuovo                                         |
| `vendite/db/vendite_repository.py`                        | 6 letture: le due `exists_*` di perimetro, il livello 1, le partite, le due code |
| `vendite/services/vendite_service.py`                     | `get_situazione_merce` — orchestrazione e cancello di scope                      |
| `vendite/api/situazione_merce_views.py`                   | **nuovo**: il factory + le due view di dominio                                   |
| `vendite/api/urls_ordini.py`, `urls_ddt.py`               | le due rotte                                                                     |
| `vendite/db/resi_repository.py`                           | BE-4, il commento corretto                                                       |
| `vendite/tests/services/test_situazione_merce_service.py` | **nuovo**: 9 test                                                                |
| `docs/it/backend/vendite/manual/api_situazione_merce.md`  | **nuovo**: il manuale                                                            |
| `docs/it/dev/api.md`                                      | la riga nell'inventario endpoint                                                 |

### 22.3 Il collaudo

```text
suite Django ............ 3702 test verdi (9 nuovi)
schema OpenAPI .......... due rotte registrate, nessun warning proprio
check_i18n_keys ......... pulito
chiamata REALE al DB .... il caso del §3 in un round-trip, 404 no-leak su entrambe
```

⭐ **La prova che conta non è un test**: è la chiamata vera. I mock non vedono il
binding SQL — è la lezione di `feedback_rinomina_db_binding_mockato`, e qui le
letture attraversano **quattro viste** e la RLS.

### 22.4 ⚠️ Cosa resta, e il vincolo di merge

✅ **Il vincolo di merge è caduto il 2026-08-18**: `20260817-15` è in
repository (PR #1282) e il backend che la consuma pure (PR #1283). Verificato a
`Tito-dev`: changeSet, doc auto-gen e suite Django (3702 verdi) allineati.

✅ **Il frontend**: il pannello del cantiere 2 è stato fatto il 2026-08-18 e le
tre richieste FE vivono lì, come previsto — la tavolozza è arrivata **col** suo
consumatore, non prima. Validato in-app su `ORD0018586` e `ORD0018585`.

### 22.5 Le tre cose imparate, dal lato backend

1. 🔴 **Un codice errore seminato dal DB lascia il repository rosso.** Servono
   **due** mosse lato backend — rigenerare le policy *e* scrivere il messaggio
   di ripiego — e stanno in perimetri e commit diversi. Il rosso non lo vede chi
   applica la migrazione: lo vede il primo che manda una PR. Va nella lista di
   consegna del team DB, accanto al changeSet.
2. ⚠️ **Una grandezza che il sistema già calcola non si ri-deriva con una
   formula «equivalente».** La mia `da_spedire` divergeva proprio sulla riga da
   21 pezzi che ha generato il cantiere. Le due formule non si scoprono diverse
   in revisione: si scoprono su un caso reale.
3. ⚠️ **Un `COALESCE` in una MISURA falsifica la misura.** Contando le righe su
   causale non fatturabile avevo scritto `COALESCE(fatturabile, false)`, che
   tratta «causale assente» come «non fatturabile»: 5 invece di 1. È lo stesso
   errore che questo brief vieta ai consumatori — commesso nello strumento con
   cui lo si dimostrava.

---

## 23. ✅ Stato al 2026-08-18 — i tre perimetri chiusi, e cosa NON è chiuso

> Sezione di stato, non di chiusura. ⛔ **Il brief resta in
> `work-in-progress/`** — le ragioni sono nel §23.4, e la prima non è tecnica.

### 23.1 Chiuso: DB, backend, frontend

| Perimetro | Stato |
| --- | --- |
| **DB** | ✅ nove changeSet `20260817-06`→`-15`, più `20260818-06` (soglia di impegno) |
| **BE** | ✅ BE-1..BE-5 + il codice errore; `situazione-merce` su ordine e DDT |
| **FE** | ✅ pannello del cantiere 2, con FE-1/2/3 dentro |
| **Definizione di fatto** (§7 + §7-bis) | ✅ **12/12** |
| **Validazione in-app** (Tid) | ✅ `ORD0018586` (il caso del §3) e `ORD0018585` (confermato e fermo) |

⭐ **Il numero che riassume tutto è ancora il primo del §20.3**: sette partite di
merce che prima non comparivano affatto — non a zero, **assenti** — più nove kit
che l'esclusione teneva fuori. Oggi si leggono in una riga sul drawer.

### 23.2 🔴 NON chiuso — e non era il residuo che credevamo

Il §19.4 elencava *«`fn_ddt_push_diagnosi` non conosce il motivo nuovo»* come una
lacuna minore. **Il team DB l'ha riqualificata il 2026-08-18, ed è un'altra
cosa**: la diagnosi non ha una lacuna, è **ferma a prima di S5**.

Verificato leggendo i due oggetti vivi:

| | `fn_list_ddt_da_pushare` (dopo `20260817-10`) | `fn_ddt_push_diagnosi` |
| --- | --- | --- |
| fonte del dosaggio | `JOIN vw_partite_merce ON ddt_riga_id` | `LEFT JOIN vw_contatore_merce` (per riga d'**ordine**) |
| ridistribuzione greedy | **tolta** | ancora `SUM() OVER (PARTITION BY ord_riga …)` |
| caso speciale compositi | **tolto** | ancora `NOT COALESCE(a_composito, false)` |

🔴 **Sono due implementazioni della regola che dosa la fatturazione** — e una
delle due si dichiara *«Fonte unica: … Riproduce i predicati di
`fn_list_ddt_da_pushare` in un unico posto (equivalenza … blindata da pgTAP)»*.
Oggi quel `COMMENT` dice il falso. Non è cosmesi: `fn_available_actions_ddt`
consuma il `min(rank)` della diagnosi per il ramo `reason`, quindi il drawer può
spiegare la mancata spinta con una regola diversa da quella che l'ha decisa.

⚠️ **E la rete che doveva accorgersene non tiene.** Il test 1 di
`test-fn-available-actions-ddt-reason-catch-all-v1` è un `EXCEPT` bidirezionale
fra i due oggetti — la forma giusta — ma **gira prima che le fixture esistano**:
gli `INSERT` che sembrano precederlo sono dentro il *corpo* di
`pg_temp.mk_caso`, e le fixture vere nascono al `CREATE TEMP TABLE f AS SELECT
pg_temp.mk_caso(…)`, **dopo**. Quindi confronta solo i dati vivi, e dopo S5 è
verde perché **nessuna riga attraversa la divergenza**, non perché la
divergenza non ci sia. La sua intestazione dice «indipendente dai dati»: vero
della forma, falso della copertura.

✅ **Presa in carico dal team DB** (2026-08-18) come **richiesta**, non come
residuo accettato. La richiesta giusta non è «aggiungi un motivo nuovo» ma:
**riallineare `fn_ddt_push_diagnosi` alla partita, e far girare l'equivalenza
anche sulle fixture** — il motivo nuovo cade fuori da sé.

### 23.3 Il secondo residuo, con un invariante invece di una dichiarazione

L'assunzione su `fn_genera_ddt_riconsegna` (§19.4): oggi il ponte copre **tutta**
la riga di ri-consegna, verificato sui 6 ponti esistenti. Se un domani una riga
fosse in parte ri-consegna e in parte merce nuova, quella parte resterebbe fuori
dal conto.

⭐ **Resta dichiarata qui, ma con un pgTAP** (proposta del team DB, accolta):
*nessun ponte copre meno della quantità della sua riga di DDT*. Una
dichiarazione invecchia da sola e nessuno se ne accorge; un invariante fallisce
il giorno in cui l'assunzione cade.

### 23.4 ⛔ Perché il brief NON va in `work-done/`

1. **È l'indice della catena** (decisione di Tid, 2026-08-18). La tabella in
   testa — «l'ordine con cui eseguire i lavori collegati» — è la roadmap dei
   cantieri: il **3 (nota di credito)** e le **righe DDT a prezzo zero** sono
   ancora da fare. Archiviare l'indice mentre i lavori che indicizza sono aperti
   è il modo più rapido per perderli.
2. **Ha lavoro vivo**: il §23.2 è una richiesta DB presa in carico, non un
   residuo.
3. I link, che è la ragione **più debole** e va detta col numero giusto:
   spostandolo si romperebbero **5** link markdown con path (3 brief in
   `work-in-progress`, il brief DB in `work-done`, il manuale BE) — non 19. Le
   **19** occorrenze in `db/` (changeSet e pgTAP, di cui molte immutabili) sono
   citazioni **per nome**, non path: un file che cambia cartella conserva il
   nome, quindi non si rompono. Restano 5, tutte correggibili nello stesso
   commit — quindi da sole non deciderebbero niente.

### 23.5 La quarta cosa imparata, che è la terza volta

Il §20.5 ne elencava tre. Questa è la quarta, e ha la stessa forma delle altre:

> ⚠️ **Una verifica può essere fatta, essere precisa, e guardare la cosa
> sbagliata.** Per controllare se il test 1 girasse dopo le fixture ho cercato
> gli `INSERT` e confrontato i numeri di riga: 80-92 contro 108, quindi «le
> fixture vengono prima». Ma quegli `INSERT` erano dentro il **corpo di una
> funzione**, cioè testo che non esegue nulla al momento in cui lo si legge.
> La domanda giusta non era *dove stanno gli `INSERT`* ma **dove viene chiamata
> la funzione che li contiene**.

⭐ È la stessa lezione del §20.5.3 («la domanda va posta sull'assenza, non sulla
presenza») e del §18.2-bis, sul terzo travestimento diverso. In tutti e tre i
casi lo strumento ha risposto con precisione a una domanda che non era quella.
