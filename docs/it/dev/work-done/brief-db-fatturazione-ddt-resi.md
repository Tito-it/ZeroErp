# Brief DB — DDT e resi: fatturazione corretta e visibile nelle lenti

> **Tipo**: brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-16 · **Owner**: Tid
> **Stato**: ✅ **COMPLETO E CHIUSO** (2026-07-19) — slice DB **realizzata, applicata e
> mergiata** (PR #1002, apply incrementale step-per-step): tracker §9 tutto ✅ (steps 1-13,
> 12 file pgTAP verdi), decisioni **tutte chiuse** (nessuna ❓ residua). L'esecuzione BE/FE
> è avvenuta su `dev/backend-tid` ([brief BE/FE](brief-be-fe-ddt-resi-dashboard.md),
> realizzato 2026-07-18 + review 8-finder). Reperti fuori slice tracciati nei brief dedicati
> ([guard sorgente polimorfa](brief-db-guard-sorgente-polimorfa.md) ·
> [immutabilità quantità](../work-in-progress/brief-db-immutabilita-quantita-e-porta-oneri.md)); alla slice NC
> resta il **contratto del §7** (NC attribuibile alla merce, con quantità).
> **Origine**: analisi 2026-07-16 con Tid. Le due lenti a monte (Situazione aperta, Backlog)
> sono state disegnate prima che esistessero DDT e resi e non li conoscono. Nell'analisi sono
> emersi **due bug di fatturazione a monte** che le dashboard non possono vedere: mostrerebbero
> la doppia fatturazione come transito legittimo. Si chiudono insieme — stessa funzione, stesso
> apply.
> **Design-of-record**: [brief-design-fatturazione-due-lenti.md](brief-design-fatturazione-due-lenti.md)
> §6-quater, decisioni **DL-19..28** (DL-27 = il contatore · DL-28 = solo trasporto via causale; DL-23/24/26 emendati 2026-07-17).
> **Non si tocca la Lente 1 (Competenza)**: parte dalla commessa ed è sorgente-agnostica — il
> DDT che pusha ci entra da solo. Decisione Tid.
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]]) → **breaking
> secchi**, nessuna fase di compatibilità, nessun doppio binario, guard restrittivi da subito.
> Numeri temporaneamente sbagliati **non sono un criterio di progetto** (decisione Tid).

---

## 0. Il rilievo di radice, in una frase

`config.tipi_reso.riapre_residuo` è un flag **logistico**: dice se la merce torna indietro per
sempre o se verrà rispedita. Oggi decide anche cosa succede ai **soldi**. Sono due domande
diverse, e da questa sovrapposizione discendono i bug del §1.

La domanda che governa i soldi è un'altra — **«quella merce l'avevamo già fatturata?»** — ed è
un **fatto** già scritto nel DB, non una scelta di nessuno. Oggi nessun oggetto lo guarda.

## 1. I quattro rilievi

### 1a. La ri-consegna fattura una seconda volta

Ordine 10 pz, `fatturazione_trigger = CONSEGNATO`. DDT₁ 10 pz consegnato → push → **fattura
10**. Reso 3 pz `RESO_PER_RICONSEGNA` → conferma → riapre il residuo (parziale: nessun flip).
Riparo e ri-spedisco: `fn_genera_ddt_riconsegna` crea DDT₂ **col suo `ordini_righe_fulfillment`**
→ DDT₂ è a tutti gli effetti pushabile → consegnato → push → **fattura altri 3**.

**Totale fatturato: 13 pz su un ordine da 10**, senza nessuna nota di credito — perché il reso
*per ri-consegna*, per costruzione, non alimenta la coda accrediti.

La logistica è corretta (residuo 10 − 10 + 3 = 3, DDT₂ evade, ordine EVASO). È la fatturazione
a contare due volte, perché è per riga-DDT e le righe DDT sono append-only fra DDT₁ e DDT₂.

**L'asimmetria che lo prova**: la reso-awareness del 2026-07-13 è stata applicata a
`fn_ordine_ha_residuo_evasione` v2 e a `trgfn_ordini_ful_guard_consistenza` v2 — cioè ai
consumatori **logistici** — ma **non** a `fn_list_ddt_da_pushare`, il consumatore **di
billing**. Al push nessuno chiama l'helper.

### 1b. Nota di credito su merce mai fatturata

`vw_resi_da_accreditare` filtra `stato = CONFERMATO AND tipi_reso.riapre_residuo = false`.
**Non verifica che la merce sia mai stata fatturata.**

Con `trigger = CONSEGNATO` e un reso **totale a credito** prima che il batch giri: il flip
`CONSEGNATO → RESO` toglie il DDT dall'eleggibilità → quella merce **non viene mai fatturata**
→ ma sta in coda accrediti, e la futura NC accrediterebbe merce che il cliente non ha mai
pagato. Con `trigger = SPEDITO` lo stesso reso è invece corretto (il push era già avvenuto a
SPEDITO). **La correttezza dipende dal trigger e dal tempismo del batch, non dai fatti.**

### 1c. Bug orfano del push DDT

`fn_list_ddt_da_pushare`, ramo order-backed (citazione **completa** — rev 2026-07-17):

```sql
(src.src_fatturazione_trigger IS NOT NULL
 AND src.src_fatturazione_trigger != 'CONFERMATO'        -- cintura XOR: NON toccarla (§3e.1)
 AND sdd.codice_interno = src.src_fatturazione_trigger)  -- ← uguaglianza STRETTA: il bug è QUI
```

Il bug è la **terza riga** (l'uguaglianza stretta); la **seconda** è la cintura
anti-doppia-fatturazione e **sopravvive al fix** — dettagli §3e.

Un DDT con `trigger = SPEDITO` che passa a `CONSEGNATO` prima che il batch giri **non è più
eleggibile: non verrà mai fatturato, e nulla lo segnala.**

È lo stesso bug corretto sugli **ordini** il 2026-07-10 — il commento vivo in
`fn_list_ordini_da_pushare` lo dice: *«l'eleggibilita' push NON dipende piu' dallo stato di
spedizione ... Esclusi solo DRAFT/ANNULLATO ... e FATTURATO»*. Sul DDT non è stato replicato.
Che sia un'asimmetria e non una scelta lo prova il ramo **standalone** della stessa funzione,
che usa già la logica giusta: `sdd.codice_interno IN ('SPEDITO','CONSEGNATO')`.

### 1d. Il buco cieco delle lenti (e un falso positivo già vivo)

**Buco cieco.** Ordine con `trigger = CONSEGNATO`: quando il DDT ha evaso tutte le righe
l'ordine passa a **EVASO** → `fase = CHIUSO` → **esce dalla Situazione aperta**. Ma il DDT è
ancora SPEDITO, non ha pushato, in commessa non c'è nulla → **la Lente 1 non lo vede**. E il
DDT non è in nessuna union. **Quel valore, che diventerà fattura, non è in nessuna delle tre
viste.**

**Falso positivo, già vivo oggi.** [vw_dash_fatturazione_ordini](../../dbzero/vendite/views/vw_dash_fatturazione_ordini.md)
**non conosce affatto `fatturazione_trigger`** → marca `PUSH_NON_ESEGUITO` (🟠 RECUPERABILE,
azione *«Esegui il push in commessa»*) su ordini che non pusheranno **mai**, perché
`fn_list_ordini_da_pushare` filtra `fatturazione_trigger = 'CONFERMATO'`. **Azione impossibile
suggerita all'utente.** Precede il DDT (bastava un billing account con
`fatturazione_ordini = CONSEGNATO`) ma ora diventa la norma.

## 2. Il principio (DL-26, Tid 2026-07-16)

> **Si fattura la merce che il cliente tiene in mano alla fine.**

Invariante per riga: `fatturato − accreditato = merce tenuta dal cliente`.

Il **come** lo decide un conto, non una regola (rev 2026-07-17, DL-26 precisato + DL-27): per
ogni partita di merce si confrontano **tenuti** e **fatturati**, e **il segno della differenza
decide** — positiva si fattura, negativa si accredita, zero niente. «Togliere prima del push» e
«accreditare dopo» non sono due regole da coordinare: sono le **due letture dello stesso conto**
(il §3 è la forma operativa; il §3f spiega perché la formulazione a due regole non reggeva).

Le quattro combinazioni, con 10 pz consegnati e 3 resi — **lettura narrativa**; il capitolato
operativo sono le **dieci righe della tabella §3a**, che includono anche i casi di tempismo
(reso prima/dopo il push) che questa griglia non distingue:

| | Merce **non** fatturata | Merce **già** fatturata |
|---|---|---|
| **A credito** | non fatturarla → 7. *Oggi*: coda dice "accredita 3" su merce mai pagata ❌ | fattura 10, accredita 3 → 7 ✅ (unico caso già corretto) |
| **Per ri-consegna** | fattura 7 + 3 alla ri-spedizione → 10. *Oggi*: 10 + 3 = **13** ❌ | ha già pagato 10, la ri-consegna non rifattura → 10. *Oggi*: **13** ❌ |

## 3. Cosa serve — il motore (NON come)

> **Rev 2026-07-16 — §3 riscritto.** La stesura precedente esprimeva l'invariante DL-26 con
> **tre predicati booleani** (sottrai / accredita / non-rifatturare) coordinati fra loro.
> Verificata contro il DB vivo, quella forma **non regge**: due dei tre si sommano e
> producono una doppia correzione, e il predicato *«era già fatturata?»* cerca la risposta
> solo sul segmento DDT — perdendola sulla configurazione di default. Dettaglio dei rilievi
> in fondo alla sezione (§3f). Qui c'è la forma che li chiude tutti **con una regola sola**.

### Il punto di partenza è il §1a di questo brief

Il §1a dice la cosa giusta: la reso-awareness del 13/07 è stata data ai consumatori
**logistici** e non al consumatore **di billing**. Ma vale la pena guardare *cosa* è stato dato
ai consumatori logistici:

```text
residuo da spedire = ordinato − Σ spedito + Σ reso_per_riconsegna
```

Un **conto**. Una formula sola (`fn_ordine_ha_residuo_evasione` v2 + l'helper
`fn_ordine_riga_qta_riconsegna`), letta da tutti quelli che devono saperlo — la fn di
generazione DDT, il guard fulfillment, la proiezione stato ordine.

Alla fatturazione non manca un semaforo: **manca il suo contatore**. È la stessa simmetria,
sull'altro asse:

| | Domanda | Formula |
|---|---|---|
| **Logistica** (esiste dal 13/07) | quanti pezzi devo ancora **spedire**? | `ordinato − Σ spedito + Σ riconsegnato` |
| **Fatturazione** (non esiste) | quanti pezzi devo ancora **fatturare**? | `tenuti − fatturati` |

### 3a. Il contatore — fonte unica, set-based (**farlo per primo**)

Per ogni **partita di merce**, due numeri:

- **tenuti** = `Σ consegnati − Σ resi + Σ ri-consegnati` → i pezzi che il cliente ha **in mano
  adesso** (§3b);
- **fatturati** = i pezzi che gli sono già stati **messi in fattura** (§3c).

E **una regola sola**:

> **La differenza decide.**
> `tenuti − fatturati > 0` → **fattura** la differenza.
> `tenuti − fatturati < 0` → **accredita** la differenza.
> `= 0` → **niente da fare**.

Non c'è più un *prima* e un *dopo* la fattura, quindi non c'è un **confine** da definire né un
momento in cui la regola cambia: c'è una sottrazione, e il **segno** dice da che parte si sta.
È l'invariante DL-26 (`fatturato − accreditato = merce tenuta`) scritto **come si calcola**
invece che come si spera.

**Consumatori** (la fonte dev'essere una — [[feedback_regola_del_2_estrai_bb]]):

| Consumatore | Legge |
|---|---|
| `fn_list_ddt_da_pushare` | la differenza **positiva** = quanto pushare |
| `vw_resi_da_accreditare` (§3c) | la differenza **negativa** = quanto accreditare |
| resolver `vw_dash_fatturazione_ddt` (§4a) | il **segno** = `motivo_fermo` |
| `fn_available_actions_ddt` · `ddt_repository.count_righe_pushable` | il segno, per riga/documento |

Quattro consumatori, un numero. Forma **set-based** (una vista, presumibilmente); quale,
lo sceglie il team. È il primo step perché tutto il resto ci si appoggia.

⚠️ **`fn_list_ddt_da_pushare` proietta oggi `dr.quantita` grezza**: con il contatore proietta
la differenza. Non è un filtro in più sul WHERE, è la **quantità** che cambia.

**La verifica — dieci righe, sono il capitolato dei pgTAP** (ordine 10 pz, il cliente ne rende 3):

| # | Situazione | Tenuti | Fatturati | Diff. | Esito atteso |
|---|---|---|---|---|---|
| 1 | a credito, reso **prima** del push | 7 | 0 | +7 | fattura 7 |
| 2 | …e subito dopo | 7 | 7 | 0 | **niente** (doppia correzione impossibile) |
| 3 | a credito, reso **dopo** la fattura | 7 | 10 | −3 | accredita 3 |
| 4 | reso **totale** a credito prima del push (flip a RESO) | 0 | 0 | 0 | niente (chiude **1b**) |
| 5 | per ri-consegna, non fatturata | 7 | 0 | +7 | fattura 7 |
| 6 | …poi ri-spedisce i 3 | 10 | 7 | +3 | fattura 3 → **totale 10** |
| 7 | per ri-consegna, **già** fatturata | 7 | 10 | −3 | accredito in attesa |
| 8 | …poi ri-spedisce i 3 | 10 | 10 | 0 | **niente** → totale 10 (chiude **1a**) |
| 9 | …oppure emette la NC e **poi** ri-spedisce ⁽*⁾ | 10 | 7 | +3 | fattura 3 → totale 10 |
| 10 | **trigger CONFERMATO** (default), reso a credito | 7 | 10 (sull'**ordine**) | −3 | accredita 3 |

Le righe **2** e **8** sono quelle che la stesura precedente sbagliava; la **10** è quella che
perdeva del tutto. La **8** merita una nota: *è il §3d*, e non è scritto da nessuna parte —
**viene fuori da solo**. La ri-consegna non rifattura perché il conto è già a zero, non perché
una regola glielo vieti.

⁽*⁾ La riga **9** è **condizionale**: vale solo se la futura NC rispetta il contratto del §7
(attribuibile alla merce, con quantità). In questa slice non è testabile — le altre nove sì.

### 3b. «Tenuti» — quanta merce ha il cliente in mano

```text
tenuti = Σ consegnati − Σ resi (CONFERMATI, attivi, QUALUNQUE tipo) + Σ ri-consegnati
```

⚠️ **L'unità di conto è la PARTITA DI MERCE, non la riga DDT.** I 3 pezzi resi e poi
ri-spediti **non sono merce nuova**: sono gli stessi pezzi che escono di nuovo, e vanno
attribuiti alla stessa partita. Questo è ciò che rende la riga 8 uno zero invece di un +3.

**Le catene esistono già tutte — nessuna tabella nuova**:

| Anello | Oggetto |
|---|---|
| ordine ↔ DDT | `ordini_righe_fulfillment` |
| DDT ↔ reso | `resi_righe.ddt_riga_id` (**NOT NULL**) |
| reso ↔ DDT di ri-consegna | `resi_righe_riconsegne` (il ponte, brief resi §4b) |

**✅ DECISO (Tid, 2026-07-16) — la chiave della partita**: **`ordine_riga_id` quando c'è
l'ordine** (`resi_righe.ordine_riga_id` è nullable apposta), **catena DDT + ponte per lo
standalone**. È lo stesso **doppio binario** che la slice resi ha già scelto e motivato (brief
resi §9 R2: *«chiavi diverse, non duplicazione; lo standalone ha solo il ponte»*).

**Perché NON la sorgente polimorfa** (domanda posta e chiusa in fase di brief — si registra il
razionale perché non si riapra):

1. **Servono archi pesati, non identità di nodo.** La
   [guida sorgente polimorfa](../../guide/sorgente-polimorfa.md) §6 prescrive la chiave
   `(sorgente_tipo_id, sorgente_uid)` come **«identità del nodo»**, e il guard
   `trgfn_guard_sorgente_polimorfa` produce una risposta **booleana** (*«quel documento esiste
   davvero?»*). Il contatore non deve sapere *«questa riga è quel documento»*: deve sapere
   ***«3 dei 10 pezzi»***. Nella macchina **non c'è dove mettere il numero** — e appena ce lo
   aggiungi hai ricostruito il ponte, col polimorfismo sopra come strato inutile. I due ponti
   portano `qta_evasa` / `qta`: **è quella colonna il senso dell'oggetto**.
2. **È un altro strato, non un'alternativa.** La guida §4 nomina **due** meccanismi (polimorfo
   *vs* colonne tipizzate dirette tipo `ddt.sorgente_uid`/`resi.sorgente_uid`, «uuid a sé»), e
   il §6 elenca le seconde fra le cose **«fuori dal meccanismo»**, da tradurre sulla chiave
   polimorfa *solo per costruire grafi tra documenti*. `ordini_righe_fulfillment` e
   `resi_righe_riconsegne` **non sono né le une né le altre**: sono FK concrete a grana riga con
   un peso. Terzo strato. La guida governa i **grafi tra documenti**; il contatore è un **libro
   mastro tra righe**. Si sfiorano, non si sovrappongono.
3. **L'integrità.** Il link polimorfo **non ha FK** (`resi.sorgente_uid` non ne ha: è per
   costruzione). Costo accettato dove il bersaglio varia su dieci sorgenti; qui i bersagli sono
   **due tabelle note**, e il manufatto è il **libro mastro dei soldi**: link rotto = fattura
   sbagliata. Barattare l'integrità referenziale per uniformità cosmetica, sul percorso del
   denaro, è un cattivo affare.
4. **Il precedente: a grana riga è già stato provato e ritirato.** `config.sorgenti` contiene
   `PREVENTIVO_RIGA` (3), `CONTRATTO_RIGA` (5), `ORDINE_VENDITA_RIGA` (7), `DDT_VENDITA_RIGA`
   (9), `FATTURA_RIGA` (11) — `scope = ROW_VALIDATOR`, tutti **archiviati**
   (`attivo=false`, `meta.archived=true`), con `db/pgtap/config/test-sorgenti-scope-pulizia-v1.sql`
   a presidiare la decisione (5 archiviati, 0 attivi). Nulla lo vietava *tecnicamente*
   (`target_table` può puntare a `ordini_righe`): quella strada è stata percorsa **potendo**, e
   si è tornati indietro. ⚠️ **Da riconfermare con la Query 2 della guida §5** prima
   dell'apply: la guida avverte che l'elenco dei tipi **non si legge da una lista scritta a
   mano** ma dal DB, e il CSV di seed è `loadUpdateData` (non cancella → non è autoritativo
   sulle righe assenti). Gli altri tre argomenti reggono comunque.

⚠️ **`fn_ordine_riga_qta_riconsegna` NON è riusabile tal quale** (il rilievo resta valido dalla
stesura precedente): filtra `riapre_residuo = true` — un filtro **logistico** dentro una domanda
**economica**. Qui servono **tutti i tipi**. È il rilievo del §0 un livello più in basso.

⚠️ **Esistono già QUATTRO definizioni divergenti di «quanta merce è tornata indietro»** — ed è
qui, non sull'eleggibilità, che la regola del 2 è più urgente:

| Oggetto | Stato reso | `rr.attivo` | Tipi |
|---|---|---|---|
| `vw_resi_da_accreditare` / `vw_resi_da_riconsegnare` | `= CONFERMATO` | **sì** | filtrato |
| `fn_ordine_riga_qta_riconsegna` | `= CONFERMATO` | **no** | solo `riapre_residuo` |
| `fn_conferma_reso` / `fn_annulla_reso` (calcolo flip a RESO) | ~~`<> ANNULLATO`~~ → **`= CONFERMATO`** (fix step 2b, `20260717-05/06`) | **no** | tutti |
| `trgfn_resi_righe_guard_quantita` (guard over-return) | `<> ANNULLATO` (**include i DRAFT**) | — | — |

La definizione canonica del contatore è **CONFERMATI + attivi + tutti i tipi**. Le prime tre
vanno ricondotte a un helper solo, ciascuna col suo filtro-tipo applicato **sopra**, non dentro.

> 🔔 **PROMEMORIA STEP 2 — il quarto `<> ANNULLATO` NON è un errore da correggere alla cieca.**
> Il guard over-return (`trgfn_resi_righe_guard_quantita`, `20260713-24`) usa anche lui
> `<> 'ANNULLATO'`, ma qui **contare le bozze è difendibile**: è una *prenotazione*, e serve a
> impedire che due bozze di reso sovrapposte, sommate, rendano più merce di quella consegnata
> (residuo = consegnato − Σ resi non-annullati, riga corrente esclusa). Non è la stessa domanda
> delle altre tre — non risponde a *«quanta merce è tornata»* (fatto economico) ma a *«questa
> nuova riga di reso ci sta nel consegnato?»* (vincolo di inserimento). Chi scrive l'helper
> unico dello step 2 **non deve** assorbire questo guard nell'helper: va lasciato dov'è, con la
> sua semantica. Se un domani lo si volesse allineare a `= CONFERMATO`, sarebbe una **decisione
> a sé** (renderebbe più lasco il guard: due bozze potrebbero prenotare oltre il consegnato
> finché non si confermano) — da valutare con Tid, non un refactoring meccanico. Registrato
> perché emerso durante lo step 2b (2026-07-17) e facile da confondere con gli altri tre.

**✅ DECISO (Tid, 2026-07-16) — i resi in DRAFT nel flip a RESO sono un DIFETTO: si corregge in
questa slice.** `fn_conferma_reso` e la gemella `fn_annulla_reso` contano i resi
`<> 'ANNULLATO'` — cioè **CONFERMATO + le bozze** — per decidere se il DDT è tutto reso.

**Il danno** (DDT 10 pz: una bozza altrui da 6 + il tuo reso confermato da 4 → somma 10 → flip a
`RESO`, ma il cliente ne tiene 6):

1. il DDT **dichiara il falso** e va in sola lettura;
2. **si perdono i soldi**: un DDT in `RESO` non è più eleggibile al push (lo stato non combacia
   più col trigger) → **i 6 pezzi che il cliente tiene non si fatturano mai, senza segnalazione**.
   È la famiglia del §1b;
3. **si auto-ripara solo in un caso su tre** — il ricalcolo gira **solo** dentro le due madri:

   | Cosa succede alla bozza | DDT torna `CONSEGNATO`? |
   |---|---|
   | annullata | ✅ `fn_annulla_reso` ricalcola |
   | corretta (6 → 2) | ❌ nessuna funzione gira → resta `RESO` per sempre |
   | lasciata in bozza | ❌ idem |

**Perché è un difetto e non una scelta** — tre riscontri, il terzo dirimente:

1. **contraddice il principio che la slice resi ha scritto per sé** (brief resi §2.1: *«gli
   effetti scattano alla CONFERMA, non in bozza»*) — e questo è l'effetto più pesante di tutti:
   cambia lo stato di un altro documento e ne blocca la fatturazione;
2. **è l'unico dei quattro consumatori che conta le bozze**: coda accrediti, coda ri-consegne e
   `fn_ordine_riga_qta_riconsegna` filtrano tutti `= CONFERMATO`;
3. **`<> ANNULLATO` non compra nulla.** Verificato l'ordine dei passi: il **passo 2** fa
   `UPDATE resi SET stato = CONFERMATO`, il **passo 4** conta. Quando si conta, **il reso che si
   sta confermando è già CONFERMATO** → `= 'CONFERMATO'` lo includerebbe comunque. L'unico
   effetto reale del filtro attuale è **contare in più le bozze degli altri**. Nessuna ragione
   tecnica: è un `<> ANNULLATO` scritto pensando alla coppia CONFERMATO/ANNULLATO, dimenticando
   che `DRAFT` esiste.

**Il fix**: `<> 'ANNULLATO'` → `= 'CONFERMATO'` in **entrambe** le madri (`fn_conferma_reso`,
`fn_annulla_reso`), assorbito dall'helper unico. ⚠️ **Nessun test esistente si rompe**: il flip
è coperto dal solo test **20** di `db/pgtap/vendite/test-resi-motore-v1.sql`, che usa un reso
**singolo confermato** → passa identico. Il caso-bozza **non è coperto da nulla**: va aggiunto,
ed è il test che dimostra il fix ([[feedback_guard_breaks_existing_tests]]).

### 3c. «Fatturati» — e la coda accrediti sui fatti

```text
fatturati = Σ quantità sulle attività EMESSA dei segmenti della partita
```

⚠️ **I segmenti possibili sono DUE, non uno**:

```text
ORD:<ordine.uid>:R:<ordine_riga.id>     ← quando fattura l'ordine  (trigger CONFERMATO)
DDT:<ddt.uid>:R:<ddt_riga.id>           ← quando fattura il DDT    (trigger SPEDITO/CONSEGNATO)
```

**Lo XOR garantisce che ne esista al massimo uno** → si guardano **entrambi** e si somma, senza
leggere il trigger e senza replicarne la logica. Chi non c'è vale zero.

Questo chiude un buco che la stesura precedente apriva: `anagrafiche.billing_account.fatturazione_ordini`
ha **default `'CONFERMATO'`**, quindi sul cliente standard la merce è fatturata sotto `ORD:…`.
Cercandola solo sotto `DDT:…` la si dichiara *«mai fatturata»* → la riga **esce** dalla coda →
**nessuna NC, nessun segnale**, sulla configurazione più diffusa. Oggi quella riga si vede
(per fortuna, non per progetto).

**La coda `vw_resi_da_accreditare` — nuova forma.** Smette di chiedere *«che tipo di reso è?»* e
espone l'**accredito dovuto** = `fatturati − tenuti` (se `> 0`). Chi ha differenza `≤ 0`
**esce** (chiude **1b**, e chiude anche il caso 2 della tabella: dopo una sottrazione al push il
conto è a zero, quindi non c'è nulla da accreditare). Breaking secco: la forma vecchia sparisce.

Le **due popolazioni** restano — ma sono un'**etichetta** sul tipo di reso, non il criterio di
popolamento (che ora è il conto):

| Popolazione | Etichetta quando | Natura |
|---|---|---|
| NC **dovuta** | tipo *a credito*: la merce non torna più | obbligo — è lavoro arretrato (§4d) |
| NC **facoltativa** | tipo *per ri-consegna*: la merce tornerà fuori | opzione — vedi §5 |

⚠️ **`security_invoker=on` va RI-specificato** nel `CREATE OR REPLACE VIEW` della coda: la
reloption non è visibile in `pg_get_viewdef` e PostgreSQL la azzera silenziosamente. È la
regressione **V-1** già capitata una volta (resolver contratti, `20260707-03`) e già costata un
rework. `vw_resi_da_accreditare` legge `resi` sotto scope emittente (brief resi 0.10):
perderla = **bypass della RLS**. `test-vw-dash-security-invoker.sql` copre la famiglia dash,
**non** le viste resi → il pgTAP va esteso.

**✅ DECISO (Tid, 2026-07-16) — la frontiera è l'EMISSIONE.** *«Lo stato EMESSA serve una nota
di credito»* (Tid): la frontiera **è** quella definizione. Tre ragioni, in ordine di peso:

1. **qualunque frontiera più in là pretende un push che il sistema rifiuta**: nella finestra
   emessa-non-fatturata (uno **stadio dichiarato** della Lente 1, lungo quanto il batch dei
   lotti) il contatore direbbe «fattura 7» ma il lister esclude per costruzione le righe con
   attività EMESSA → falso positivo garantito, il §1d ricreato;
2. **è già la frontiera del sistema**: il `NOT EXISTS ... stato_emissione = 'EMESSA'` è in
   entrambi i lister, e il commento vivo di `fn_list_ordini_da_pushare` la battezza *«verità
   di billing»*. Sceglierne un'altra = due frontiere = la violazione di fonte unica che questa
   slice esiste per chiudere;
3. **è l'ultimo atto deliberato** (una persona emette; la fattura la fa il batch): oltre, il
   *come* correggere dipenderebbe dal calendario — il difetto che il §1b condanna.

**La misura, semplificata dai fatti (verifica 2026-07-16/17)**: la riga di
`attivita_fatturabili` **esiste se e solo se** la commessa_attivita è EMESSA — la crea
l'emissione, niente la cancella mai (il reset-lotto fa solo UPDATE: sblocca, non elimina).
Quindi:

```text
fatturati = Σ attivita_fatturabili.quantita  delle righe AF della partita
            (la loro sola esistenza È la frontiera EMESSA)
```

- ⚠️ Il collegamento AF↔CA si fa via **`commessa_attivita_id`** (FK NOT NULL + UNIQUE), **non**
  via l'hash `md5(segment_key)` di `sorgente_uid` (dove vive il caveat di collisione C1 già
  documentato).
- ⚠️ Il predicato è **`= 'EMESSA'`** (whitelist), mai `<> 'NON_EMESSA'`: il dominio contiene
  anche `ANNULLATA` — è lo stesso errore del flip a RESO corretto allo step 2b.
- ⚠️ **Nota a DL-5** (*«nessuna re-emissione possibile»*): quella frase e l'uscita di sicurezza
  di Tid (lotto EMESSA→DRAFT, demolizione e rifacimento — guida fatturazione, riquadro
  `reset_lotto_draft`) **convivono**: DL-5 dice che la **riga AF** non viene mai ricreata
  (stabilità di `data_insert`); il reset demolisce le **fatture**, non le AF. Due letture della
  parola «emissione», entrambe vere — registrarlo evita che la prossima persona legga DL-5 come
  «il reset non esiste».
- Con [brief-db-immutabilita-quantita-e-porta-oneri.md](../work-in-progress/brief-db-immutabilita-quantita-e-porta-oneri.md)
  vale inoltre **AF.quantita = CA.quantita sempre** → la misura è stabile per costruzione, e le
  righe manuali (segmenti `MAN:`, `tipo_movimento` non-NORMALE) non entrano mai nel conto.

### 3d. La ri-consegna — **derivata, niente da costruire**

Non serve nessuna regola dedicata e **nessuna colonna nuova** sulla riga DDT: la ri-consegna
alza i **tenuti** (§3b), e il conto fa il resto — righe 6, 8 e 9 della tabella. Se la merce era
già fatturata il conto torna a zero e la ri-consegna **non rifattura** (riga 8); se non lo era,
la ri-consegna **rifattura** (riga 6). Nessuna delle due è una regola: sono lo stesso conto.

**Quando arriverà la slice NC** — e qui la forma va detta come **requisito**, non come
previsione, perché le NC **non sono ancora definite** (Tid, 2026-07-16): *se* la nota di
credito **abbassa i fatturati** della merce che accredita, allora la differenza torna positiva
e la ri-consegna rifattura da sé (riga 9), la scelta umana del §5 funziona senza codice
dedicato, **zero rework** ([[feedback_concentrico_no_yagni]]). Il *se* è il contratto che
questa slice pone alla prossima — formalizzato nel §7. Se la NC nascesse invece come puro
legame documento↔documento (la forma dell'attuale `fatture_rettifiche`), **il contatore non la
vedrebbe mai** e la riga 9 non varrebbe.

⚠️ **Il nodo pratico da sciogliere**: quando i tenuti **risalgono** su una partita la cui
attività è **già EMESSA** (riga 6: pushati 7, poi ri-spedisco 3), i 3 pezzi in più **non**
possono andare sull'attività esistente — il lister esclude per costruzione le righe con
attività EMESSA, e l'upsert è per `segment_key`. Vanno sul segmento del **DDT nuovo** (`DDT:<ddt₂.uid>:R:<riga₂.id>`),
che è un segmento vergine. La catena regge — i **fatturati** sommano su tutti i segmenti della
partita, quindi 7 + 3 = 10 — ma il punto va scritto: **il contatore è per partita, il push è per
segmento**.

### 3e. Fix orfano push DDT (§1c)

L'eleggibilità order-backed deve valere **dallo stato-trigger in poi**, non solo **a** quello
stato — allineandosi a quanto già fatto sugli ordini il 2026-07-10 e al ramo standalone della
stessa funzione. Tre precisazioni **verificate**, tutte e tre load-bearing:

⚠️ **1. La citazione del §1c è incompleta.** Il WHERE vivo non è
`AND sdd.codice_interno = src.src_fatturazione_trigger` ma:

```sql
(src.src_fatturazione_trigger IS NOT NULL
 AND src.src_fatturazione_trigger != 'CONFERMATO'      -- ← la cintura XOR
 AND sdd.codice_interno = src.src_fatturazione_trigger)
```

Quel `!= 'CONFERMATO'` **è ciò che impedisce al DDT di un ordine trigger CONFERMATO di
fatturare merce già fatturata alla conferma**. Chi riscrive partendo dalla citazione del §1c la
perde → doppia fatturazione su **tutti** gli ordini in configurazione di default. **Va
preservata**, ed è il motivo per cui esiste il §3f.2.

⚠️ **2. NON un confronto di rank puro.** `config.stati_doc_ddt` ha già la colonna `ordine`, ma
il seed vivo è:

| stato | `ordine` | `fase` | `is_abortito` |
|---|---|---|---|
| DRAFT | 10 | APERTO | f |
| EMESSO | 20 | IN_CORSO | f |
| SPEDITO | 40 | IN_CORSO | f |
| CONSEGNATO | 50 | CHIUSO | f |
| RESO | 60 | CHIUSO | f |
| **ANNULLATO** | **70** | CHIUSO | **t** |

`ordine >= ordine(trigger)` rende **ANNULLATO (70) ≥ SPEDITO (40)**: un DDT annullato diventa
eleggibile e **viene fatturato**. L'argomento *«tanto con la sottrazione la quantità è
azzerata»* vale solo per RESO (che nasce da un reso totale): **un DDT ANNULLATO non ha resi, i
tenuti non si azzerano, e pusha**. La risposta al *«va confermata, non dedotta»* della stesura
precedente è quindi: **l'esclusione NON è ridondante**.

Forma corretta: `ordine >= ordine(trigger)` **AND `NOT sdd.is_abortito`** AND esclusione
esplicita di `RESO`. Il `NOT is_abortito` sostituisce l'hardcode di ANNULLATO ed è data-driven —
il DB *dichiara già* che quel documento è morto.

> **Precisazione sullo scenario** (verificata sul DB vivo, 2026-07-18 — emersa scrivendo il
> pgTAP dello step 5). `config.transizioni_stati_ddt` **non ammette** `SPEDITO → ANNULLATO`
> (riga assente) né `CONSEGNATO → ANNULLATO` (riga presente ma `attivo = f`): un DDT si annulla
> solo da `DRAFT` o `EMESSO`, cioè **prima che la merce parta**. La storia raccontata sopra
> («un DDT spedito, poi annullato») non è quindi percorribile oggi — **ma il rischio resta
> intatto**, perché un DDT annullato da `EMESSO` ha comunque `ordine = 70 ≥ 40` e senza
> `NOT is_abortito` verrebbe pescato lo stesso. Cambia l'aneddoto, non la necessità della
> clausola.

⚠️ **3. Il vocabolario del trigger non è un sottoinsieme degli stati DDT.**
`ordini.fatturazione_trigger` ∈ {`CONFERMATO`, `SPEDITO`, `CONSEGNATO`} (varchar + CHECK,
nessuna lookup): **`CONFERMATO` è uno stato *ordine***, non esiste in `stati_doc_ddt`. *«Dallo
stato-trigger in poi»* è quindi **indefinito** proprio nel caso di default — ed è esattamente il
perché della clausola al punto 1.

### 3f. Perché la stesura precedente non reggeva (per il verbale)

Tre rilievi verificati contro il DB vivo. Si registrano qui perché il §2 e il §9 li citano.

**3f.1 — §3b e §3c si sommavano.** Erano lo **stesso `EXISTS`** valutato in due momenti su uno
stato che cambia. Sequenza ordinaria, trigger CONSEGNATO: DDT 10 pz CONSEGNATO, batch non ancora
girato → reso 3 a credito → §3b sottrae, pusha 7 → l'attività va EMESSA a 7 → **fattura 7** ✅ →
**ma ora §3c interroga la coda**: la merce di quella riga reso *ha* un'attività EMESSA → entra in
coda come NC dovuta 3 → **7 − 3 = 4** ❌. L'`EXISTS` non distingue *«l'attività emessa include
quella merce»* da *«ne è già stata depurata»*. Il §3 affermava *«verificate le sei combinazioni:
con tutti e tre tornano tutte»*: la verifica non teneva conto del **tempo relativo fra reso e
push** — cioè della variabile che il §1b stesso condanna (*«la correttezza dipende dal tempismo
del batch, non dai fatti»*). **Il rimedio reintroduceva il difetto che diagnostica.**
Aggravante: il push è un **upsert** su `(commessa_id, segment_key)` e il lister esclude solo le
attività già EMESSA → una riga pushata-ma-non-emessa **viene aggiornata** da un ri-push. Quindi
lo **stesso identico stato di fatto** dava 7 o 4 a seconda che il batch fosse girato o no.

**3f.2 — §3c perdeva la configurazione di default.** Vedi §3c: il predicato cercava l'attività
EMESSA solo sul segmento DDT, mentre col default `CONFERMATO` la merce è fatturata sotto `ORD:…`
→ riga fuori dalla coda → nessuna NC su merce realmente fatturata. **Regressione secca e
silenziosa rispetto a oggi.**

**3f.3 — la radice comune.** L'invariante DL-26 è **quantitativa**; §3b/§3c/§3d la
implementavano con **booleani**. Con resi parziali, push parziali e ri-push, i booleani perdono
informazione. Il §0 dice che *«è un fatto già scritto nel DB»*: vero — ma il fatto è
**quantitativo** e raggiungibile **solo** risalendo il percorso di billing, e la stesura
precedente non modellava né l'una né l'altra cosa.

## 4. Cosa serve — le lenti (NON come)

### 4a. Resolver DDT — sesta area della union (DL-21, emendato 2026-07-17)

Nuovo resolver `vw_dash_fatturazione_ddt`, stessa forma dei cinque gemelli, unito in
`vw_dash_fatturazione_documenti`. Da lì **entrambe** le lenti lo prendono da sole: il serbatoio
filtra `fase <> CHIUSO`, il backlog filtra `classe <> FISIOLOGICO`. Il FE è già fail-visible
sulle aree extra (le accoda, non dà 400).

**✅ DECISO (Tid, 2026-07-17) — la popolazione: solo i DDT con un ruolo di fatturazione.**

| DDT | Nel resolver? | Perché |
|---|---|---|
| da ordine con trigger **CONFERMATO** | **NO — si segue l'ordine** | non fatturerà mai lui (XOR: ha fatturato l'ordine alla conferma); l'ordine porta già il valore **pieno** (DL-23 emendato) |
| con causale di trasporto **non fatturabile** | **NO — solo trasporto** | la merce viaggia ma non c'è una vendita (vedi decisione qui sotto) |
| da ordine con trigger **SPEDITO/CONSEGNATO** | SÌ | è lui il veicolo di fatturazione |
| **standalone** (senza ordine), causale fatturabile | SÌ | fattura in proprio a SPEDITO/CONSEGNATO |

L'esclusione chiude **due** difetti con zero meccanismi:

1. **il falso positivo**: un DDT di ordine CONFERMATO non ha uno stato-trigger confrontabile
   (`CONFERMATO` è uno stato *ordine*) → sarebbe scivolato su 🟠 `PUSH_NON_ESEGUITO` **per
   sempre**, con l'azione che il DB stesso rifiuta (`DDT_NON_PUSHABILE`) — il §1d ricreato sul
   DDT, sulla configurazione di default;
2. **il doppio conteggio speculare**: con DL-23 emendato l'ordine CONFERMATO sta nel serbatoio
   a valore **pieno** (1.000 €) — il suo DDT con il valore spedito (500 €) avrebbe fatto
   1.500 € per una fattura da 1.000. Escluso il documento, escluso il valore: niente motivo
   dedicato, niente azzeramenti.

Il criterio di popolazione è **lo stesso discriminatore del lister** (la cintura XOR
`src_fatturazione_trigger != 'CONFERMATO'`, §3e): la card mostra la stessa popolazione che il
motore di push considera sua — fonte unica anche qui. ⚠️ Nota pratica: oggi un DDT nasce da
**un solo ordine** (`fn_genera_ddt_da_ordine` è per-ordine) → il trigger si legge dalla
sorgente di testata, nessun caso misto. Costo dichiarato: il DDT di un ordine CONFERMATO è
invisibile nei cruscotti di *fatturazione* (resta in lista DDT, drawer, lineage) — coerente
con DL-14 («documenti che se conclusi vanno in commessa»: lui non ci andrà mai).

**✅ DECISO (Tid, 2026-07-17) — DDT di solo trasporto: l'intento si dichiara con la CAUSALE
(DL-28).** Il DDT ammette righe senza prezzo per design (*«solo trasporto»*, guida DDT §3.2/§8.1),
ma `fn_list_ddt_da_pushare` **non le esclude** (il gemello ordini sì): uno standalone senza
prezzi a SPEDITO risulterebbe «da fatturare» con prezzo vuoto → push di attività senza prezzo +
🟠 perpetuo nei cruscotti. Invece di *inferire* l'intento dall'assenza di prezzo (ambiguo:
dimenticanza o scelta?), l'intento si **dichiara a monte** col campo che l'operatore già
compila — la **causale di trasporto**:

1. **Nuova colonna `fatturabile boolean NOT NULL` su `config.causali_trasporto`** + seed:
   `VENDITA = true`; `CONTO_VISIONE / RESO / RIPARAZIONE / CAMPIONATURA / TRASFERIMENTO /
   CONTO_LAVORO / OMAGGIO = false`. Pattern `tipi_reso.riapre_residuo`: il vocabolario guida,
   zero IF hardcoded. I casi ambigui (OMAGGIO: c'è chi lo fattura a sconto 100%) sono **una
   cella di seed**, non codice.
2. **Gate all'emissione** (mirror di `trgfn_ddt_guard_indirizzi_obbligatori`, stesso
   posizionamento): causale **fatturabile** → ogni riga attiva deve avere un prezzo
   **risolvibile** (proprio, o dalla riga ordine via fulfillment — le righe da evasione senza
   prezzo restano legittime); altrimenti blocco parlante (nuovo codice errore, append CSV —
   [[feedback_messaggi_errore_no_new_loader]]). Causale **non fatturabile** → prezzi
   irrilevanti. Il prezzo dimenticato diventa un **errore all'emissione**, non un documento
   silenziosamente mal classificato.
3. **Causale obbligatoria all'emissione** (oggi `ddt.causale_trasporto_id` è nullable):
   dettaglio del gate — come trattare i NULL lo fissa il team (raccomandato: obbligatoria
   all'emissione, come l'indirizzo).
4. **Lister e resolver escludono i non fatturabili**: `fn_list_ddt_da_pushare` guadagna il
   predicato sulla causale (cintura: quei DDT non sono mai eleggibili) e la popolazione del
   resolver resta a criterio unico — *dentro chi fattura, fuori chi no*.

- **Valore**: il DDT **non ha importi in testata**. Le righe da evasione possono avere
  `prezzo_unitario` **NULL** ed ereditarlo dalla riga ordine → serve la stessa
  `COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)` che fa
  `fn_list_ddt_da_pushare`. ⚠️ **`vw_ddt_righe_iva_base` NON è riusabile**: filtra
  `prezzo_unitario IS NOT NULL` → perderebbe proprio quelle righe.
- **`data_riferimento` = `ddt.data`**. Non esiste una data di spedizione/consegna reale
  (`data_ora_consegna_prev` è *prevista*). Coerente con DL-17.
- **`motivo_fermo` trigger-aware** — deve distinguere *"in viaggio"* da *"in ritardo"*, e il
  predicato *"il push è dovuto?"* **non va ricopiato**: è §3a.

  | Situazione | Motivo | Classe |
  |---|---|---|
  | DRAFT | `DOC_BOZZA` (esistente) | 🟢 FISIOLOGICO |
  | stato **prima** del trigger | `IN_TRANSITO` (**nuovo**) | 🟢 FISIOLOGICO |
  | stato **dal trigger in poi**, non pushato | `PUSH_NON_ESEGUITO` (esistente) | 🟠 RECUPERABILE |
  | idem, push parziale | `PUSH_PARZIALE` (esistente) | 🟠 RECUPERABILE |

- ⚠️ **La `fase` si legge dal catalogo, non da `vw_stato_sorgente`.** Verificato: i cinque
  resolver gemelli fanno tutti `JOIN config.stati_doc_<tipo>` e leggono `fase`/`esito` da lì —
  **nessuno** passa da `script.vw_stato_sorgente`. Il resolver DDT segue lo stesso pattern
  (`JOIN config.stati_doc_ddt`, che ha già `fase` e `is_abortito` NOT NULL). Nessuna dipendenza
  nuova. Ma vedi la decisione qui sotto: è proprio questa autonomia a lasciare scoperto
  l'altro consumatore.

**✅ DECISO (Tid, 2026-07-17) — il quinto ramo si fa, dentro la slice.** Il DDT manca da
`script.vw_stato_sorgente` **solo perché è uno sviluppo recente** (Tid) — non c'è mai stata una
scelta contraria: va aggiunto come gli altri. Il contesto, per chi implementa:

- la proiezione di dominio ha **4 rami** (`vw_stato_sorgente_{preventivo, offerta, ordine,
  contratto}`); oggi `pratiche.fn_stato_sorgente` su un DDT cade nella **sentinella** e risponde
  `stato='UNKNOWN'`, `risolto=false`, **`fase='APERTO'`** — mentre `config.stati_doc_ddt`
  dichiara che `CONSEGNATO` è **`fase=CHIUSO`**. Il dato di mappatura esiste (fase/`is_abortito`
  atterrati con la slice lineage `20260714-01`) e non è mai proiettato;
- l'aggancio pratica→DDT è **già possibile oggi** (sorgente `DDT_VENDITA` registrata, il guard
  polimorfo la accetta): il buco è esercitabile, non teorico;
- la [guida sorgente polimorfa](../../guide/sorgente-polimorfa.md) usa **proprio il DDT** come
  esempio della promessa della macchina (§3) e il §6 enumera i mattoni pronti — quattro. Col
  quinto ramo la promessa torna vera.

**Forma**: `vendite.vw_stato_sorgente_ddt` a specchio dei quattro + aggiunta del ramo nella
union `script.vw_stato_sorgente` (⚠️ `CREATE OR REPLACE` della union: la vista **non** ha
`security_invoker` — verificato — ma controllare i pgTAP della proiezione prima,
[[feedback_guard_breaks_existing_tests]]). Dettaglio da sciogliere in scrittura: le gemelle
espongono `esito`, che sul catalogo DDT non esiste come colonna → derivarlo (es.
ANNULLATO→NEGATIVO) o lasciarlo NULL — scelta al team, purché documentata nel manuale della
vista.

**✅ DECISO (Tid, 2026-07-17) — anche il ramo RESO, insieme, in posizione naturale.** Il reso è
nella stessa condizione (sorgente `RESO_VENDITA` registrata, nessun ramo) e la mappa esiste già
anche per lui (`config.stati_doc_reso` ha `fase`: DRAFT=APERTO, CONFERMATO=CHIUSO — brief resi
§2.1). **Non si rinvia**: quinto e sesto ramo (`vw_stato_sorgente_ddt` + `vw_stato_sorgente_reso`)
si scrivono **insieme, nello stesso step**, così il traduttore copre tutti i tipi documento
registrati e lo sviluppo resta coerente — niente code da ricordare per la prossima slice.

### 4b. Ordini trigger-aware (DL-20)

Il resolver ordini deve conoscere `fatturazione_trigger`: con `trigger ∈ {SPEDITO, CONSEGNATO}`
non è l'ordine a pushare → **nuovo motivo `IN_ATTESA_DDT`, classe FISIOLOGICO**.

Effetto: l'ordine **resta nel serbatoio** (giusto — è aperto e pre-commessa) e **sparisce dal
backlog** (giusto — non c'è niente da fare su di lui). Nessun caso speciale nel FE: la regola
di classe DL-6/DL-7 fa tutto da sola.

### 4c. Ordine al residuo nel serbatoio (DL-23)

**Problema**: ordine 1.000 €, trigger CONSEGNATO, metà spedita. L'ordine è PARZIALMENTE_EVASO →
nel serbatoio con valore **pieno** 1.000 €; il DDT ci starebbe con 500 € → le due card dicono
1.500 € per un valore che diventerà fattura di 1.000. **I 500 già spediti contati due volte.**

**Decisione Tid**: nel serbatoio l'ordine porta il **valore ancora da spedire**
(`ordinato − evaso`), non il valore pieno. Card sommabili, staffetta ordine→DDT pulita: quando
spedisco tutto l'ordine va a zero e sparisce, il DDT prende in carico i 1.000, e in ogni
istante la somma fa 1.000. Chiude anche il buco cieco del §1d.

- ⚠️ È il residuo **da spedire** (via `ordini_righe_fulfillment`), **non** il "non transitato":
  per un ordine trigger CONSEGNATO il transitato è sempre 0 e non aiuta.
- ⚠️ **La formula esiste già ed è reso-aware**: `fn_ordine_ha_residuo_evasione` v2 +
  `fn_ordine_riga_qta_riconsegna` (`quantita − Σ qta_evasa + Σ qta_riconsegna`). **Riusarla,
  non riscriverla.**
- ✅ **VERIFICATO (2026-07-16) — un ordine `trigger = CONFERMATO` PUÒ generare DDT.** Nessun
  vincolo lo impedisce: `fn_genera_ddt_da_ordine` **non legge mai** `fatturazione_trigger` (il
  suo unico guard è sullo stato ordine, `CONFERMATO|PARZIALMENTE_EVASO` — omonimia da non
  confondere), e nessun trigger su `ddt`/`ddt_righe`/`ordini_righe_fulfillment` lo referenzia.
  È **deliberato e documentato** (`vendite/manual/ordini.md`, `manual/ddt.md`): il DDT è un
  documento **logistico**, disaccoppiato dalla fatturazione; il cancello anti-doppia-fattura
  vive nel **lister** (`src_fatturazione_trigger != 'CONFERMATO'`, §3e), non nella generazione.
- 🔴 **La conseguenza ribalta la decisione — DL-23 va condizionato al trigger.** La stesura
  precedente presentava le due risposte come equivalenti (*«se può, cambia anche per lui»*):
  **non lo sono, quella è un bug.** Un ordine `trigger = CONFERMATO` **fattura il pieno alla
  conferma**, indipendentemente dalla spedizione. Con la misura netta, un ordine da 1.000 €
  interamente spedito ma non ancora pushato mostrerebbe **0 €** — e il DDT **non compensa**,
  perché non pusherà mai. **Nuovo buco cieco, creato dalla misura che doveva chiuderne uno**, e
  per giunta sulla configurazione di **default** (`billing_account.fatturazione_ordini` ha
  default `'CONFERMATO'`).

  **Regola corretta**: la misura netta vale **solo quando è il DDT il veicolo di billing**
  (`trigger ∈ {SPEDITO, CONSEGNATO}`); con `trigger = CONFERMATO` l'ordine resta al **valore
  pieno** — non c'è doppio conteggio da evitare, perché il DDT non conta nulla. È lo stesso
  lavoro di DL-20 (rendere il resolver ordini trigger-aware), non un secondo.

  ✅ **Emendamento a DL-23 — FATTO (Tid, 2026-07-17)**: registrato nel §10 del
  [brief di design](brief-design-fatturazione-due-lenti.md) — misura netta **solo** per
  `trigger ∈ {SPEDITO, CONSEGNATO}`, ordine CONFERMATO al valore pieno; barrata la
  giustificazione «somma sempre 1.000». Lo step 8 del §9 lo recepisce già.
- ⚠️ **La giustificazione *«in ogni istante la somma fa 1.000»* NON regge** — e va tolta, perché
  lo step 11 chiedeva un pgTAP proprio su quella proprietà. Seed verificato:
  `fase(CONSEGNATO) = CHIUSO`, e DL-15 filtra `fase <> 'CHIUSO'` → quando il DDT arriva a
  CONSEGNATO **esce dal serbatoio** mentre l'ordine è già a 0: somma **0** per un valore che
  farà fattura di 1.000. Il buco cieco è chiuso **solo nella finestra EMESSO/SPEDITO**; a
  CONSEGNATO il valore vive nel **Backlog** — che è esattamente ciò che DL-22 dichiara e
  accetta. Le due affermazioni si contraddicono a una pagina di distanza. **L'argomento vero e
  sufficiente per DL-23 resta l'altro**: il doppio conteggio ordine-pieno + DDT
  (1.000 + 500 = 1.500).
- Accettato: l'area Ordini diventa l'unica con misura **netta**, le altre restano lorde.

### 4d. Ramo resi sul Backlog (DL-24)

**I resi NON entrano in `vw_dash_fatturazione_documenti`**: quella union è il funnel
pre-commessa, e `config.sorgenti.RESO_VENDITA` (id 15) è **`REVERSE_FLOW`**, non
`PUSH_COMMESSA` — la migration `20260714-07` lo motiva esplicitamente. Entrano **solo nel
Backlog**, con un ramo dedicato:

| Popolazione | Fonte | Motivo (nuovo) | Classe |
|---|---|---|---|
| Riga reso per ri-consegna, copertura incompleta | `vw_resi_da_riconsegnare` | `RICONSEGNA_NON_ESEGUITA` — azione *«Genera il DDT di ri-consegna»* | 🟠 RECUPERABILE |
| Riga reso con **accredito dovuto** (differenza negativa) | `vw_resi_da_accreditare` (forma **§3c**) | `MERCE_RESA_GIA_FATTURATA` | 🟢 FISIOLOGICO **oggi** |

- `RICONSEGNA_NON_ESEGUITA` è 🟠 a pieno titolo: l'azione esiste (`fn_genera_ddt_riconsegna`) e
  la sua **mancata esecuzione blocca la fatturazione** (il residuo dell'ordine resta riaperto
  per sempre).
- **`MERCE_RESA_GIA_FATTURATA`** (rinominato dalla stesura precedente, che lo chiamava
  `NC_DOVUTA`): il motivo nomina **il fatto**, non il rimedio — perché le NC **non sono ancora
  definite** (Tid, 2026-07-16) e il rimedio non è univoco: quando la slice NC esisterà sarà la
  nota di credito, e la coda espone comunque *cosa è successo* («fatturata per 10, tenuta 7»),
  non *cosa fare*. Un motivo chiamato `NC_DOVUTA` pre-deciderebbe la risposta e mentirebbe se
  il rimedio scelto fosse un altro.
- È 🟢 oggi con una motivazione **verificata**: non esiste alcuna azione che un operatore possa
  compiere — la NC non c'è, e la correzione manuale della quantità è **vietata dal principio di
  immutabilità** ([brief-db-immutabilita-quantita-e-porta-oneri.md](../work-in-progress/brief-db-immutabilita-quantita-e-porta-oneri.md)).
  Con la slice NC diventa 🟠 cambiando **una riga di seed**. ⚠️ Il precedente citato dalla
  stesura precedente (*«stessa forma di `CANONE_NON_GENERATO`»*) è **falso**: verificato,
  `CANONE_NON_GENERATO` non è emesso da nessuna vista (`vw_dash_fatturazione_contratti` ha
  `motivo_fermo` hardcoded NULL) — è seed morto, cambiarne la classe non produrrebbe nulla. La
  tesi qui regge per un motivo diverso: **questo ramo il §4d lo costruisce davvero**, quindi il
  motivo è emesso e la classe è viva.
- ⚠️ **Forma della vista Backlog**: oggi `vw_dash_backlog_documenti` è costruita **sopra** la
  union (`FROM vw_dash_fatturazione_documenti`). «Resi fuori dalla union ma dentro il Backlog»
  significa che il **Backlog stesso diventa una union** (documenti + ramo resi): fattibile e
  piccolo, ma è un cambio di forma della vista, va dichiarato — non è «un ramo in più» gratis.
- ⚠️ Le NC **facoltative** (§3c/§5) **non** sono arretrato: sono un'opzione dell'operatore →
  **fuori dal backlog**.
- **Misura a conteggi** (i resi non hanno importi): `valore_fermo` NULL — mai 0 — e
  `unita_ferme` = righe. Precedente DL-11 (Offerte/Contratti).
- **✅ DECISO (Tid, 2026-07-17) — grana: una riga di backlog per (reso × motivo).** Il tipo di
  reso è **per riga per costruzione** (`tipi_reso` agganciato a `resi_righe.tipo_reso_id`, non
  alla testata) → esiste il **reso misto** (3 pz da ri-spedire + 2 a credito), che ha davvero
  due cose in corso: a grana documento qualunque motivo scelto mentirebbe; a grana riga il
  backlog diventerebbe rumore (10 righe per la stessa azione). Con (reso × motivo): ogni riga
  di backlog ha la **sua azione e la sua classe** (il filtro 🟠 mostra solo la parte da
  lavorare), i conteggi tornano senza doppi (ogni riga reso ha un tipo solo → un motivo solo),
  ed è la grana **più vicina alle fonti** (le due code sono già per riga reso: aggregare a
  (reso × motivo) è un gradino, a documento sarebbero due, perdendo la distinzione per cui i
  motivi esistono). **Deroga dichiarata**: unica area dove un documento può comparire due
  volte in lista — motivata dal modello, limitata ai resi misti.

### 4e. Seed `config.motivi_fermo` — quattro nuovi

| `codice_interno` | classe | azione |
|---|---|---|
| `IN_ATTESA_DDT` | FISIOLOGICO | — (fattura il DDT, non l'ordine) |
| `IN_TRANSITO` | FISIOLOGICO | — (merce in viaggio, push non ancora dovuto) |
| `RICONSEGNA_NON_ESEGUITA` | RECUPERABILE | Genera il DDT di ri-consegna |
| `MERCE_RESA_GIA_FATTURATA` | FISIOLOGICO | — (nessuna azione esiste oggi; 🟠 con la slice NC) |

## 5. La scelta umana — dove vive (DL-26, Tid)

La scelta *«emetto la nota di credito?»* esiste **in una sola casella** delle quattro (§2):
merce **già fatturata** + reso **per ri-consegna**. Altrove la decidono i fatti.

**È una scelta sola, non due**: accreditare e rifatturare sono la stessa decisione vista dai due
lati — se emetti l'NC il cliente non ha più pagato quella merce e la ri-consegna **deve**
rifatturare; se non la emetti la fattura è in piedi e la ri-consegna **non deve**. All'utente si
chiede una cosa sola; il resto si deriva. Il conto torna in entrambi i casi: la scelta cambia le
carte, non i soldi.

**Non è un campo da congelare alla creazione del reso**: la decisione può arrivare dopo («passa
del tempo prima della nuova spedizione e il cliente la richiede» — Tid). È un'**azione sulla
coda accrediti**, esercitabile **fino alla ri-spedizione**: da lì in poi quella merce è
sistemata, e un eventuale credito successivo è un reso nuovo.

**In questa slice non c'è nulla da costruire** per la scelta (l'NC non esiste): serve solo che
il modello non la impedisca — cioè la coda etichetta dovuta/facoltativa (§3c).

> **Nota alla rev del §3 (2026-07-16).** Col contatore la scelta non va nemmeno *protetta*:
> l'emissione della NC **abbassa i fatturati**, la differenza torna positiva e la ri-consegna
> rifattura da sé (riga 9 della tabella §3a). Non c'è nessun *«fatto che oggi è sempre falso»*
> da predisporre, e nessun ramo da aggiungere alla slice NC: **zero rework**. Che una decisione
> di dominio decisa a tavolino funzioni senza codice dedicato è la conferma che la forma del
> §3 è quella giusta.

## 6. Cosa NON serve (deciso, per chiudere le domande)

- **DL-22 — fase DDT invariata.** `CONSEGNATO` e `RESO` restano `fase = CHIUSO`. Conseguenza
  voluta: un DDT **dovuto e non pushato** compare nel **Backlog** e **non** nel serbatoio —
  corretto per costruzione (non sta aspettando: è in ritardo).
- **DL-25 — `area <> 'COMMESSE'` resta com'è.** Con i resi fuori dalla union (§4d) non è più
  una blacklist da manutenere: è una frase sola e stabile, *«escludi il punto di arrivo»*. La
  commessa non è un'eccezione da ricordare, è il traguardo. Filtrare per
  `config.sorgenti.scope` sarebbe lavoro a comportamento invariato: il criterio resta
  disponibile nel DB se un giorno servisse.
- **Lente 1 (Competenza)**: invariata.

## 7. Fuori perimetro

- **Guard sorgente polimorfa — buco scoperto dallo step 6b (2026-07-18)**: il guard
  `trgfn_guard_sorgente_polimorfa` non è agganciato a **nessuna** tabella (la doc lo dava per
  attivo), ed è scritto per un modello (`attivita_fatturabili`: `sorgente_riga`/`sorgente_uid`
  tipizzate) diverso da quello delle tabelle di collegamento (`sorgente_uid` TEXT secondo
  `key_selector`). Conseguenza viva: `commesse_sorgenti` stocca l'**uid** anche per i tipi a
  chiave `id` → 23 righe (ordini/contratti/DDT) **non risolvono** in `vw_stato_sorgente`, bug
  latente (l'unico consumatore odierno legge solo `pratiche_sorgenti`, che è corretta). Chiusura
  completa — guard giusto per modello, normalizzazione in `fn_link_commessa_sorgente`, backfill,
  doc, pgTAP — nel brief dedicato
  [brief-db-guard-sorgente-polimorfa.md](brief-db-guard-sorgente-polimorfa.md) (Tid: *«i buchi
  vanno chiusi e non con delle toppe»*). Lì anche il reperto collaterale del **settimo ramo
  COMMESSA** mancante.
- ~~**Catalogo reso: `CONFERMATO` aveva `fase = IN_CORSO`**~~ → **CORRETTO in questa slice**
  (2026-07-18, deciso Tid): cella CSV `stati_doc_reso.csv` a `CHIUSO` (loader `runOnChange`
  ripesca) + refresh del `COMMENT` della vista (`20260718-11`). Un reso confermato **è**
  concluso — la ri-consegna è un altro documento; l'annullo (`CONFERMATO → ANNULLATO`,
  guardato) resta come storno: *terminale = conclusione commerciale, non lucchetto*. Censimento
  consumatori prima della modifica: proiezione di stato (effetto voluto) e lineage (per il reso
  la fase è solo display, arco R escluso dalla frontiera per progetto); BE e viste resi usano
  `codice_interno`. pgTAP: `test-vw-stato-sorgente-ddt-reso-v1` esteso a `plan(9)`, verde.
- **Emissione della nota di credito** (slice NC): qui solo la coda che la alimenta, resa
  veritiera. **Ma questa slice le pone un CONTRATTO** — le NC non sono ancora definite (Tid,
  2026-07-16), quindi va scritto ora, prima che vengano disegnate:

  > **La nota di credito deve essere attribuibile alla merce e portare una quantità.**
  > Un puro legame documento↔documento (la forma dell'attuale `fatture_rettifiche`, tabella-ponte
  > senza quantità né importi) **non basta**: il contatore chiude il cerchio solo se sa *quanti
  > pezzi* di *quale merce* sono stati accreditati. Una NC che non abbassa i «fatturati» della
  > partita è invisibile al contatore → la coda accrediti continuerebbe a chiedere l'accredito
  > **per sempre, anche a NC emessa**. (E la riga 9 della tabella §3a resterebbe una promessa.)

- **Valorizzazione economica dei resi**: rinviata alla slice NC, che è la **proprietaria delle
  regole di valorizzazione** (sconti, IVA, arrotondamenti). L'importo si ricaverà da
  `ddt_righe.prezzo_unitario` (COALESCE con la riga ordine) — il meccanismo è lo stesso che il
  §4a costruisce, quindi *si potrebbe*; non si fa perché la valorizzazione è una decisione di
  quella slice, non perché manchi il dato.
- Movimenti di magazzino.
- **Quantità immutabili + porta oneri** — emersa verificando la frontiera del §3c: la
  correzione della quantità post-emissione non deve esistere come UPDATE (né su CA né su AF) —
  le correzioni sono **righe nuove** attraverso porte dedicate, e le correzioni di **merce**
  restano interamente su questo brief (reso → contatore → NC). **La misura del contatore non ne
  dipende** (misura AF in ogni caso, e con l'immutabilità AF = CA sempre) → brief a sé:
  [brief-db-immutabilita-quantita-e-porta-oneri.md](../work-in-progress/brief-db-immutabilita-quantita-e-porta-oneri.md).
- **Segnalazione collaterale (fix a parte, non di questa slice)**: i trigger anti-disattivazione
  `dbops.trgfn_prevent_deactivate_if_children` su `config.causali_trasporto` **e** su
  `config.stati_doc_ddt` proteggono solo i figli in **`acquisti`** (`acquisti.ddt/ordini`), non
  `vendite.ddt` — una causale o uno stato usati solo da DDT di vendita risultano disattivabili.
  Emerso verificando §4a/DL-28; da sanare con un changeset dedicato alla famiglia.

## 8. Cosa comunicare indietro a BE/FE

- ~~La forma scelta per *"questa riga DDT non fattura"*: se è una colonna, il BE la espone.~~
  **Superato dalla rev del §3**: nessuna colonna, nessuno stato nuovo — la ri-consegna è
  **derivata** dal contatore (§3d). **Niente da esporre**: il BE non tocca nulla su questo.
- La nuova forma di `vw_resi_da_accreditare` (colonne + popolazione + etichetta
  dovuta/facoltativa): il BE ha già `GET /vendite/resi/da-accreditare/` e il FE ha la coda a
  tab → vanno adeguati. **Breaking secco**, nessuna compat. ⚠️ La coda ora espone una
  **quantità** (l'accredito dovuto = `fatturati − tenuti`), non solo l'elenco delle righe: è
  una colonna in più nel contratto, e la slice NC ci si appoggerà.
  **Forma effettiva (`20260718-01`, applicata 2026-07-18)** — grana invariata (riga di reso,
  `resi_riga_id` resta la chiave):
  - **colonne nuove**: `accredito_dovuto` (la quantità da accreditare), `etichetta`
    (`DOVUTA` | `FACOLTATIVA`), `tenuti`, `fatturati` (il conto, esposto perché la coda dica
    *cosa è successo* — «fatturata per 10, tenuta 7»);
  - **colonne preservate**: tutte quelle su cui `resi_repository._CODA_META` ordina e cerca
    (`reso_numero`, `data`, `destinatario_denominazione`, `descrizione`, `ddt_numero`,
    `qta_operativa`, `motivo`, `ba_codice`, `quantita`) → gli `order_cols` non si rompono;
  - ⚠️ **`ddt_numero`/`ddt_id` ora possono essere NULL** (il join al DDT è diventato LEFT: la
    partita si aggancia via `ordine_riga_id`, non più via `ddt_riga_id` obbligatorio);
  - ⚠️ **la popolazione cambia in entrambe le direzioni**: spariscono righe che il FE mostra
    oggi (a credito già pareggiate), ne compaiono di nuove mai viste (ri-consegne su merce
    fatturata, etichetta `FACOLTATIVA`) → il conteggio del tab **cambierà a colpo d'occhio**,
    va detto a chi lo usa prima del rilascio, o sembrerà una perdita di dati.
- **Due aree nuove** (`DDT`, `RESI`): il FE le accoda da solo (fail-visible), ma servono label
  i18n e la rotta *apri documento* in `vendite/dashboardAree.js`.
- **Backlog, forma effettiva (`20260718-14`)**: `vw_dash_backlog_documenti` è ora una union
  (documenti + rami resi a grana **reso × motivo**). Per il BE/FE tre conseguenze concrete:
  - nell'area `RESI` **`valore_fermo` è NULL** (misura a conteggi, DL-11): il FE non deve
    renderlo come 0 € — NULL significa *non misurabile in euro*, e le somme di card devono
    usare `COALESCE` come già fa `vw_dash_backlog_riepilogo`;
  - la **deroga di grana**: un reso misto può comparire **due volte** in lista (una per
    motivo, ciascuna con la sua azione) — non è un doppione da de-duplicare;
  - `MERCE_RESA_GIA_FATTURATA` oggi **non appare** (FISIOLOGICO): quando la slice NC lo
    promuoverà via seed, l'area RESI si popolerà anche di quello **senza rilascio BE/FE** —
    prevedere da subito la label i18n.
- Il **ramo resi ha misura a conteggi** (`valore_fermo` NULL) → card come Offerte/Contratti.
- **Quattro motivi nuovi** → i18n (`dash_comune`).
- **`causali_trasporto.fatturabile`** (DL-28): il BE la espone dove serve (lookup causali già in
  whitelist), e il **nuovo errore del gate emissione** («righe senza prezzo su causale
  fatturabile») va gestito nel drawer DDT → i18n + mapping in `error_policies.py`.
  **Forma effettiva (`20260718-03..06`, applicata 2026-07-18)**:
  - `config.causali_trasporto.fatturabile` boolean NOT NULL, **default `false`** (una causale
    nuova nasce non fatturabile: una dimenticanza tiene il DDT fuori dalla coda — visibile e
    recuperabile — invece di farlo fatturare per sbaglio). Seed: `VENDITA` sola `true`.
  - **Due codici errore nuovi**, entrambi sollevati all'emissione del DDT:
    `E_DDT_CAUSALE_OBBLIGATORIA` (544) e `E_DDT_PREZZO_NON_RISOLVIBILE` (545) → i18n +
    `error_policies.py`. Il secondo nomina la **riga** colpevole (`riga_id` nel context).
  - ⚠️ **La causale diventa obbligatoria all'emissione**: il FE deve renderla un campo
    richiesto nel drawer DDT prima dell'azione «emetti», altrimenti l'utente scopre il vincolo
    solo dall'errore. In bozza resta facoltativa (si compila prima di emettere, come
    l'indirizzo).
  - ⚠️ **Prezzo risolvibile ≠ prezzo presente**: una riga da evasione senza prezzo proprio è
    legittima se l'ordine lo fornisce (stessa `COALESCE` del lister). Il FE non deve pretendere
    il prezzo sulla riga DDT: pretenderlo bloccherebbe un caso valido.
- La **card Ordini del serbatoio cambia significato**: da "valore dell'aperto" a "valore ancora
  da spedire" (§4c) → etichetta e guida da rivedere.
- Eventuali nuovi codici errore.

## 9. Avanzamento

| # | Step | Stato |
|---|---|---|
| 0 | **Cancelli di correttezza: TUTTI CHIUSI** (§3b chiave partita ✅ · §3b resi DRAFT ✅ · §3c frontiera EMESSA ✅ · §4c ordine CONFERMATO ✅) — gli step 1-8 sono scrivibili | ✅ |
| 1 | **Il contatore** — `tenuti − fatturati` per partita, set-based, fonte unica (§3a) — primo, ci si appoggia il resto | ✅ **APPLICATO + TESTATO** (scritto 2026-07-17, applicato 2026-07-18): vista `20260717-11` `vw_contatore_merce` (grana = riga d'ordine; `tenuti = Σ fulfillment.qta_evasa − Σ vw_resi_righe_effettive.quantita`, `fatturati = Σ AF NORMALE` sui segmenti `ORD:*:R:<ordine_riga>` + `DDT:*:R:<ddt_riga>` via fulfillment, `differenza`; `security_invoker=on`) + pgTAP `test-vw-contatore-merce-v1` (`plan(10)`, 7 dei 10 casi §3a — gli altri 3 sono varianti aritmetiche o richiedono la NC). ⚠️ **Perimetro ORDER-BACKED, deciso con Tid**: standalone (ponte + ri-consegne ricorsive, gated da 5b) e **compositi** (`is_composito`: AF `#CMP` in unità-componente vs fulfillment/resi in unità-padre) **esclusi** → follow-up flaggati. Nessun link strutturato AF→partita: si parsa il `segment_key` (robusto a `#CMP` via `substring ':R:([0-9]+)'`) |
| 2 | Helper unico «merce tornata indietro» (CONFERMATI + attivi + tutti i tipi) e riconduzione delle **tre** definizioni divergenti (§3b) | ✅ **APPLICATO + TESTATO** (scritto 2026-07-17, applicato 2026-07-18): vista `20260717-07` `vw_resi_righe_effettive` (CONFERMATE+attive, tutti i tipi, chiavi `ordine_riga_id`/`ddt_riga_id` + `riapre_residuo`, `security_invoker=on`) + pgTAP dedicato `test-vw-resi-righe-effettive-v1` (`plan(9)`). Ricondotte **2 su 3**: `fn_ordine_riga_qta_riconsegna` (`20260717-08`, filtro `riapre_residuo` sopra) e la flip conferma/annullo (`20260717-09/-10`, tutti i tipi). ⚠️ Aggiunge il filtro `attivo` canonico (no-op in pratica); test 25/26 di `test-resi-motore` passano identici = riconduzione behavior-preserving. **Differite le code** (`vw_resi_da_accreditare`/`_riconsegnare`): le riscrive lo step 4/9 — adotteranno la vista lì, riconducirle ora sarebbe throwaway. La **quarta** (guard over-return) resta fuori di proposito (§3b promemoria) |
| 2b | **Fix flip a RESO**: `<> 'ANNULLATO'` → `= 'CONFERMATO'` in `fn_conferma_reso` **e** `fn_annulla_reso` (§3b, deciso) — assorbito dall'helper dello step 2. **Buco sui soldi già vivo oggi**, indipendente dal contatore | ✅ **APPLICATO + TESTATO** (scritto 2026-07-17, applicato 2026-07-18): `20260717-05` (conferma) + `20260717-06` (annullo, speculare) + pgTAP 25-26 in `test-resi-motore-v1` (`plan(26)`→`plan(28)`): bozza 6 + confermato 4 su DDT da 10 → **resta CONSEGNATO**; confermata anche la bozza → flip a RESO (il flip non è rotto). Perimetro: **solo l'asse stato** — `rr.attivo` e filtro tipi restano allo step 2 |
| 3 | `fn_list_ddt_da_pushare` legge la differenza **positiva** (quantità, non filtro) + **`security_invoker`** ri-specificato ovunque si tocchi una vista (§3a/§3c) | ✅ **APPLICATO + TESTATO** (scritto 2026-07-17, applicato 2026-07-18): `20260717-12` — proietta come `quantita` la **differenza del contatore** distribuita per riga DDT (greedy oldest-first, cappata a `dr.quantita`), non più `dr.quantita` grezza; `qta_operativa` scalata proporzionalmente; filtro `quantita_push > 0`. Cintura XOR + frontiera EMESSA **intatte** (il fix orfano §3e è lo step 5). Standalone + compositi → ramo ELSE `dr.quantita` grezza (fuori dal contatore, invariati). pgTAP `test-fn-list-ddt-da-pushare-contatore-v1` (`plan(7)`, verde): reso riduce il push (7 non 10), **caso 8 chiude la doppia fatturazione** (ri-consegna già fatturata → proietta 0), + **caso F** (2026-07-18) sulla distribuzione §3d: partita 10 spezzata in due DDT parziali (6+4) con reso 5 → il 1° assorbe 5 (cappato), al 2° resta 0. Legge `vw_contatore_merce` (security_invoker) → RLS preservata; la funzione resta INVOKER default (come il vivo). ⚠️ **Il greedy distribuisce solo in BATCH**: con `p_ddt_id` il filtro è dentro la CTE `cand`, quindi il DDT mirato è l'unico candidato e prende `min(sua quantità, differenza)` ignorando i fratelli di partita — corretto e convergente (la AF creata abbassa la differenza al giro dopo), ma push mirati e push batch danno **ordini di allocazione diversi** a parità di stato |
| 4 | `vw_resi_da_accreditare` = differenza **negativa**, segmenti `ORD:`+`DDT:` entrambi, etichetta dovuta/facoltativa (§3c, breaking) | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-01` — popolazione dalla differenza negativa del contatore (`accredito_dovuto = fatturati − tenuti > 0`), tipo reso degradato a **etichetta** `DOVUTA`/`FACOLTATIVA`; colonne del conto esposte (`tenuti`, `fatturati`). I due segmenti arrivano già sommati dal contatore: qui **non si legge il trigger**. **Grana = riga di reso** (decisa con Tid: §7 dice «riga reso», ed è la grana su cui il BE ordina) con accredito **distribuito greedy oldest-first** tra le righe della stessa partita, cappato alla quantità della riga; chi riceve 0 esce. `DROP`+`CREATE` (cambiano numero e tipo delle colonne) con **`security_invoker=on` ri-specificato** (regressione V-1). Le due direzioni volute: **escono** le righe a credito già pareggiate (chiude 1b), **entrano** le ri-consegne su merce già fatturata (oggi invisibili). Perimetro ORDER-BACKED ereditato dal contatore: le righe reso senza `ordine_riga_id` non entrano più (standalone gated 5b). pgTAP `test-vw-resi-da-accreditare-contatore-v1` (`plan(8)`, verde) |
| 5 | Fix orfano push DDT: `ordine >= trigger` **AND `NOT is_abortito`** AND no `RESO`, preservando `!= 'CONFERMATO'` (§3e) | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-02` — il ramo order-backed passa da uguaglianza secca (`sdd.codice_interno = trigger`) a `sdd.ordine >= sdd_trg.ordine AND NOT sdd.is_abortito AND codice_interno <> 'RESO'`. Il rank del trigger si risolve con `LEFT JOIN config.stati_doc_ddt ON codice_interno = fatturazione_trigger` (chiave naturale stabile, §6b): per `CONFERMATO` **non risolve** → predicato falso → il §3e.3 si chiude da sé, senza clausole aggiuntive, e la **cintura XOR resta intatta** accanto. Quantità (contatore, step 3), frontiera EMESSA e ramo standalone **invariati**. pgTAP `test-fn-list-ddt-da-pushare-orfano-v1` (`plan(5)`, verde): orfano recuperato · caso «a stato» non regredito · ANNULLATO escluso · RESO escluso · cintura XOR regge. ⚠️ **Effetto all'apply**: i DDT orfani storici compaiono nella coda di push al primo giro (è l'intento §1c) — la quantità la decide comunque il contatore, quindi ciò che era già fatturato per altra via proietta 0 e non compare |
| 5b | **Solo trasporto via causale** (§4a, DL-28): colonna `fatturabile` su `config.causali_trasporto` + seed · gate emissione prezzi-risolvibili (mirror gate indirizzi, nuovo codice errore) · causale obbligatoria all'emissione · esclusione dal lister | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-03` colonna `fatturabile` (NOT NULL, **default false** — una causale nuova nasce non fatturabile) · CSV `causali_trasporto` + **loader `20260709-11` esteso** (era già `runOnChange`, ripesca da sé — deciso con Tid contro un secondo loader sulla stessa tabella) con `VENDITA` sola fatturabile · `20260718-04` **gate all'emissione** `trgfn_ddt_guard_causale_emissione` (mirror di `trgfn_ddt_guard_indirizzi_obbligatori`, `BEFORE UPDATE OF stato_doc_ddt_id`, fase a10): R1 causale obbligatoria + R2 prezzo **risolvibile** (proprio o ereditato via fulfillment) se fatturabile · `20260718-05` lister con `JOIN` sulla causale fatturabile (**entrambi i rami**: la causale descrive il viaggio della merce, non la provenienza del documento) · `20260718-06` **backfill** `VENDITA` sui DDT già oltre DRAFT senza causale · codici errore **544/545** in append al CSV. pgTAP `test-ddt-solo-trasporto-causale-v1` (`plan(6)`, verde) con **controprova** sul caso non-fatturabile. **Niente trattamento speciale del NULL** (Tid: «se è obbligatoria che senso ha controllare il NULL?»): in DRAFT il NULL resta legittimo, e il lister guarda solo stati ≥ SPEDITO |
| 6 | Resolver `vw_dash_fatturazione_ddt` + union (§4a) — **popolazione = solo DDT con ruolo di fatturazione** (esclusi gli order-backed trigger CONFERMATO, deciso); `motivo_fermo` = **segno del contatore**, mai un predicato ricopiato | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-07` resolver (stesse 19 colonne dei gemelli, `security_invoker=on`) + `20260718-08` sesto ramo in `vw_dash_fatturazione_documenti` (reloption **ri-specificata**) + `IN_TRANSITO` in append a `motivi_fermo.csv` (id 11, FISIOLOGICO — il loader `runOnChange` lo ripesca; **anticipato dallo step 10** perché senza la riga il backlog tratterebbe la merce in viaggio come da recuperare). Popolazione: fuori trigger CONFERMATO e causali non fatturabili. `motivo_fermo` trigger-aware con soglia = **rank del trigger**, `SPEDITO` per lo standalone (primo stato in cui il lister lo considera). Valore per riga con la `COALESCE` di lister/gate. pgTAP `test-vw-dash-fatturazione-ddt-v1` (`plan(8)`, verde), incluso il **valore col prezzo ereditato** — il caso che `vw_ddt_righe_iva_base` avrebbe perso. ⚠️ **Scelta di merito**: il trigger si legge **via fulfillment**, non dalla sorgente di testata come dice la nota pratica del §4a — perché il §4a stesso impone «lo stesso discriminatore del lister», e il lister usa il fulfillment; due strade per lo stesso dato sono la divergenza che questa slice chiude. Risultato identico finché un DDT nasce da un solo ordine |
| 6b | **Quinto e sesto ramo** `vw_stato_sorgente_ddt` + `vw_stato_sorgente_reso` + aggiunta alla union `script.vw_stato_sorgente` (§4a, deciso: insieme, posizione naturale) — indipendente dagli altri step | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-09` i due rami + `20260718-10` union da 4 a 6 rami. Nessun `security_invoker` (verificato: la famiglia non ne ha — non si aggiunge di straforo in un changeset che dichiara di aggiungere rami). 🔑 **CHIAVE = `id::text`**, non l'uid: `config.sorgenti.key_selector` dice `id` per **entrambi** i tipi (solo PREVENTIVO/OFFERTA usano `uid`), come il gemello ordine e come il lineage. Con l'uid il ramo non avrebbe agganciato **nulla, in silenzio** — nessun errore, solo proiezione sempre vuota: il test 2 asserisce che cercare per uid NON trova, così la convenzione non si può «ripulire» per sbaglio. `esito`/`terminale` **derivati** (i cataloghi DDT/reso non li espongono), regola meccanica scelta con Tid: `is_abortito` → NEGATIVO · `fase CHIUSO` non abortito → POSITIVO · resto NULL · `terminale = (fase = CHIUSO)`. Conseguenza dichiarata: il DDT in stato RESO risulta POSITIVO, perché il catalogo lo dichiara non abortito (merce tornata ≠ documento annullato) — cambiarla è materia di **catalogo**, non di vista. pgTAP `test-vw-stato-sorgente-ddt-reso-v1` (`plan(8)`, verde). **Due reperti aperti, entrambi fuori slice** → vedi §7 |
| 7 | Resolver ordini trigger-aware → `IN_ATTESA_DDT` (§4b) | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-12` — un `WHEN` nuovo in `vw_dash_fatturazione_ordini`, **posizione load-bearing**: dopo `DOC_BOZZA` (una bozza resta bozza qualunque sia il trigger), prima dei motivi di push (per trigger `SPEDITO`/`CONSEGNATO` il push non è dovuto → `PUSH_NON_ESEGUITO`/`PARZIALE` mai raggiunti — era il falso positivo §1d sul ramo ordini). `IN_ATTESA_DDT` in append a `motivi_fermo.csv` (id 12, **FISIOLOGICO**) → l'uscita dal backlog è **per costruzione** (filtro `classe <> FISIOLOGICO`), zero casi speciali FE. `security_invoker=on` ri-specificato. Trigger `CONFERMATO` invariato — verificato PRIMA sulle fixture esistenti (`test-vw-dash-fatturazione-v1` #6, `test-vw-dash-backlog-v1` #7: ordini a trigger default CONFERMATO), rilanciate verdi dopo l'apply. pgTAP nuovo `test-vw-dash-fatturazione-ordini-trigger-v1` (`plan(5)`, verde) — asserisce anche l'**effetto a valle** (assenza dal backlog), non solo il motivo |
| 8 | Ordine al residuo da spedire nel serbatoio (§4c, riusare la formula esistente) — ⚠️ **solo per trigger SPEDITO/CONSEGNATO**, vedi §4c | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-13` — `valore_totale` di `vw_dash_fatturazione_ordini` a **residuo da spedire** per riga (`GREATEST(0, quantita − Σ fulfillment.qta_evasa + fn_ordine_riga_qta_riconsegna)` × prezzo scontato — formula **riusata** dal single-source reso-aware, non riscritta), **condizionato al trigger** come da emendamento DL-23: netto solo `SPEDITO`/`CONSEGNATO`, `CONFERMATO` resta al pieno. La misura vive nel **resolver** (fonte unica §4a): serbatoio la eredita, backlog non mostra questi ordini (step 7), viste competenza **non leggono** questo resolver (censite). `security_invoker=on` ri-specificato. pgTAP `test-vw-dash-fatturazione-ordini-residuo-v1` (`plan(6)`, verde): evasi 4/10 → 150 · evaso tutto → 0 · **reso 3 per riconsegna → risale a 75** (la parte reso-aware) · CONFERMATO → pieno 250 · serbatoio eredita 150 a valle |
| 9 | Ramo resi sul backlog (§4d) — dopo lo step 4 | ✅ **APPLICATO + TESTATO** (2026-07-18): `20260718-14` — **cambio di forma dichiarato**: `vw_dash_backlog_documenti` diventa una **union** (ramo documenti invariato + due rami resi a grana **reso × motivo**). `RICONSEGNA_NON_ESEGUITA` (RECUPERABILE, azione) da `vw_resi_da_riconsegnare`; `MERCE_RESA_GIA_FATTURATA` (FISIOLOGICO oggi) da `vw_resi_da_accreditare` **solo etichetta DOVUTA** (le facoltative sono opzione, non arretrato). I rami emettono il *motivo*; classe/azione + filtro `classe <> FISIOLOGICO` risolti **una volta a valle** → la promozione NC è **una cella di seed**, la vista non si ritocca. Misura a conteggi (DL-11): `valore_fermo` NULL mai 0. `vw_dash_backlog_riepilogo` intatta (eredita il ramo RESI da sé). `security_invoker=on` ri-specificato. pgTAP `test-vw-dash-backlog-resi-v1` (`plan(7)`, verde): dentro/azione/conteggi/sparizione a copertura completa · accredito dovuto **emesso ma filtrato** (la classe è viva, test 5-6) · resi mai nella union pre-commessa. Regressione `test-vw-dash-backlog-v1` verde (ramo documenti invariato provato) |
| 10 | Seed motivi (§4e) | ✅ **COMPLETATO PER COSTRUZIONE** (2026-07-18): i quattro motivi sono entrati ciascuno con lo step che li emette — `IN_TRANSITO` (11, step 6) · `IN_ATTESA_DDT` (12, step 7) · `RICONSEGNA_NON_ESEGUITA` (13, step 9) · `MERCE_RESA_GIA_FATTURATA` (14, step 9) — tutti in append a `motivi_fermo.csv`, loader `runOnChange` `20260706-02`, classi come da tabella §4e. Nessun changeset dedicato: niente seed morto in attesa del consumatore ([[feedback_messaggi_errore_no_new_loader]]) |
| 11 | pgTAP **nuovi**: le **dieci righe della tabella §3a** + caso orfano + DDT annullato **non** fatturato + **caso-bozza del flip** (bozza 6 + confermato 4 su DDT da 10 → il DDT **resta** `CONSEGNATO` e i 6 pz **restano fatturabili** — oggi non lo copre nulla, §3b) + buco cieco + falso positivo ordini sparito + resi solo nel backlog + **solo trasporto** (causale non fatturabile mai eleggibile/mai nei cruscotti · emissione VENDITA con riga senza prezzo risolvibile **bloccata** · evasione con prezzo ereditato **passa**) + `security_invoker` sulle viste resi | ✅ **COPERTO ATTRAVERSO GLI STEP** (2026-07-18) — mappa: §3a **7/10** in `test-vw-contatore-merce-v1` + **caso 8** in `-contatore-v1` #5 (⚠️ **3 righe residue = varianti aritmetiche o richiedono la NC → differite dichiaratamente alla slice NC**) · orfano `-orfano-v1` #1 · DDT annullato non fatturato `-orfano-v1` #3 · caso-bozza flip `test-resi-motore-v1` #25-26 · buco cieco/staffetta `-ordini-residuo-v1` #2-4 (finestra a DDT CONSEGNATO dichiarata a Backlog, DL-22/§4c) · falso positivo ordini `-ordini-trigger-v1` #2-3 · resi solo nel backlog `-backlog-resi-v1` #7 · solo trasporto `test-ddt-solo-trasporto-causale-v1` (6) + mai nei cruscotti `-dash-fatturazione-ddt-v1` #4 · `security_invoker` viste resi: `-backlog-resi-v1` #1 (`bool_and` su backlog + le due code) + contatore/effettive/accreditare nei rispettivi #1 |
| 12 | pgTAP **esistenti da aggiornare** (censire prima di scrivere — [[feedback_guard_breaks_existing_tests]]): `test-fn-list-ddt-da-pushare-v1/-v2`, `test-resi-motore-v1`, `test-vw-dash-fatturazione-v1`, `test-vw-dash-backlog-v1`, `test-vw-dash-aperto-v1`, `test-vw-dash-security-invoker` | ☐ — ⚠️ nota 2026-07-18: `test-fn-list-ddt-da-pushare-v1` era **rotto prima di questa slice** (fallout del lavoro emittente `20260713-xx`: la fixture non passava `emittente_fiscale_id` e `trgfn_ordini_default_emittente` non lo risolve in contesto pgTAP). Riparato in corsa — BA vincolato a emittente risolvibile + emittente esplicito su ordini e sul DDT senza BA, usando **`fn_get_emittente_fiscale_pk`** (è la funzione con cui il guard confronta, non `_id`). Ora 12/12: copre anche i casi 7-8 standalone, cioè il ramo che lo step 3 dichiara invariato. Riparato anche per la slice (2026-07-18): causale `VENDITA` sui quattro DDT di fixture, servita dal nuovo `JOIN` del lister. **12/12 verde.** — **Censimento COMPLETO** (fine slice): `-v2` verde senza modifiche · `test-resi-motore-v1` `plan(27)` (#21 rimossa, step 4; #25-26 aggiunti, step 2b) · `test-vw-dash-fatturazione-v1` e `-backlog-v1` verdi senza modifiche (fixture a trigger CONFERMATO; il secondo rilanciato dopo la union, ramo documenti provato invariato) · `test-vw-dash-security-invoker` verde senza modifiche · **`test-vw-dash-aperto-v1` RIPARATO** (2026-07-18): era rotto da fixture emittente **preesistente** (stessa famiglia del lister-v1) — BA vincolato a emittente derivabile + «emittente B» ora su un **secondo BA col proprio emittente** (`tmp_ap_refs_b`; se non esiste → skip come prima), 14/14 verde |
| 12-bis | **pgTAP aggiornati per gli step 3/4/5/5b** (2026-07-18) — censimento fatto contro il DB vivo, non per ipotesi | ✅ **12 file verdi**: `test-fn-list-ddt-da-pushare-v1` (12) · `-contatore-v1` (7) · `-orfano-v1` (5, nuovo) · `test-ddt-solo-trasporto-causale-v1` (6, nuovo) · `test-vw-resi-da-accreditare-contatore-v1` (8, nuovo) · `test-vw-contatore-merce-v1` (10) · `test-vw-resi-righe-effettive-v1` (9) · `test-resi-motore-v1` (**27**, era 28) · `test-ddt-read-side-v1` · `test-fn-genera-ddt-da-ordine-v1` · `test-fn-list-ordini-da-pushare-v3` · `script/test-fn-available-actions-pdf-v1`. Intervento tipico = causale `VENDITA` in fixture prima dell'emissione. **Tre reperti**: (a) `test-resi-motore-v1` #21 («riga a credito confermata ⇒ in coda») **RIMOSSA**: era la popolazione per tipo di reso, superata dallo step 4 — la fixture rende 5 su 5 senza mai fatturare, quindi non c'è nulla da accreditare e la vista ha ragione a escluderla; la coda ha ora il suo test dedicato. È stato il **primo consumatore reale** della nuova semantica, e ha fallito nel modo giusto. (b) `script/test-fn-available-actions-pdf-v1` era **già latentemente rotto** (fixture senza indirizzo CON): il guard indirizzi lo colpiva, il nuovo guard causale lo mascherava scattando prima. (c) ⚠️ **~60 test della suite fallivano già prima di questa slice**, su aree estranee ai DDT (RLS, stradario, profili utente, contratti, pricing): non toccati, ma la suite **non è una rete di sicurezza affidabile** finché non si censiscono |
| 13 | Apply dev + comunicazione a BE/FE (§8) | ✅ **CHIUSO LATO DB** (2026-07-18): apply dev fatto **incrementalmente** step per step (Tid), ogni changeset applicato+testato prima del successivo — nessun big-bang finale. La comunicazione a BE/FE **è il §8**, tenuto aggiornato in corsa: forma effettiva coda accrediti (colonne nuove, `ddt_numero` nullable, popolazione che cambia a vista) · `causali_trasporto.fatturabile` + causale obbligatoria all'emissione + errori 544/545 · backlog a union (`valore_fermo` NULL ≠ 0 €, deroga reso misto, promozione NC via seed) · quattro motivi i18n · due aree nuove. **L'esecuzione BE/FE è la prossima slice** (branch `dev/backend-tid`), fuori da questo brief |

> **Decisioni — stato: TUTTE CHIUSE** (2026-07-17). Nessuna ❓ residua nel testo.
>
> | § | Domanda | Stato |
> |---|---|---|
> | §3b | Chiave della **partita di merce** | ✅ **CHIUSA** (Tid, 2026-07-16): `ordine_riga_id` + catena DDT/ponte. **NO sorgente polimorfa** — razionale in §3b (archi pesati vs identità di nodo, guida §6) |
> | §4c | Un ordine `trigger = CONFERMATO` può generare DDT? | ✅ **VERIFICATO: SÌ**, per progetto documentato. Ne discendono §3e, §4a e l'emendamento a DL-23 (§4c) |
> | §4a | Il DDT di un ordine trigger CONFERMATO nei cruscotti? | ✅ **CHIUSA** (proposta Tid, 2026-07-17): **escluso dalla popolazione** — «si segue l'ordine». Chiude falso positivo + doppio conteggio senza motivi dedicati (DL-21 emendato). Razionale in §4a |
> | §3b | `fn_conferma_reso` conta i resi in **DRAFT** per il flip a RESO — difetto o scelta? | ✅ **CHIUSA** (Tid, 2026-07-16): **difetto**, si corregge in questa slice (step 2b). Razionale in §3b — decisivo: al passo 4 il reso è già CONFERMATO, quindi `<> ANNULLATO` conta **solo** le bozze altrui |
> | §3c | La frontiera è `stato_emissione = 'EMESSA'` (e non `fattura_riga_id IS NOT NULL`)? | ✅ **CHIUSA** (Tid, 2026-07-16): **EMISSIONE** — *«lo stato EMESSA serve una nota di credito»*. Misura: Σ `attivita_fatturabili.quantita` via `commessa_attivita_id` (l'esistenza della riga AF **è** la frontiera). Razionale e nota a DL-5 in §3c |
> | §4a | Quinto ramo `vw_stato_sorgente_ddt`: dentro la slice o §7 motivato? | ✅ **CHIUSA** (Tid, 2026-07-17): **dentro la slice** (step 6b) — mancava solo perché sviluppo recente. **E anche il ramo RESO, insieme** (Tid: non rinviare, posizione naturale, sviluppo coerente): il traduttore copre tutti i tipi registrati |
> | §4d | Grana del backlog resi: una riga per (reso × motivo)? | ✅ **CHIUSA** (Tid, 2026-07-17): **(reso × motivo)** — il tipo è per riga per costruzione; il reso misto ha davvero due cose in corso. Razionale e deroga dichiarata in §4d |
> | §4a | DDT di **solo trasporto** (righe senza prezzo)? | ✅ **CHIUSA** (Tid, 2026-07-17, DL-28): l'intento si dichiara con la **causale di trasporto** — flag `fatturabile` sul vocabolario (opzione B, scelta Tid), gate all'emissione, esclusione da lister e popolazione. Razionale in §4a |
>
> ⚠️ **Da riconfermare prima dell'apply** (§3b, punto 4): la **Query 2** della
> [guida sorgente polimorfa](../../guide/sorgente-polimorfa.md) §5 su `config.sorgenti`, per
> verificare sul **DB vivo** che i tipi `ROW_VALIDATOR` siano ancora archiviati — la guida
> avverte che l'elenco non si legge da liste scritte a mano, e il CSV di seed non è
> autoritativo sulle righe assenti.
