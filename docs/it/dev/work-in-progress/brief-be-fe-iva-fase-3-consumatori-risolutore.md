# Piano BE/FE — Fase 3 del cantiere IVA: i consumatori del risolutore

> **Destinatario:** backend (`dev/backend-tid`) e frontend.
>
> **Base.** [brief-db-be-iva-risolutore-e-regime-cliente.md](brief-db-be-iva-risolutore-e-regime-cliente.md)
> — le voci `I3`, `I4`, `I5`, `I6` del suo §5, l'elenco unico nel suo §8-nonies.
> Questo documento non ri-discute nessuna decisione di quel brief: **costruisce
> la metà BE/FE che il DB non può fare.**
>
> **Perché un documento nuovo e non un capitolo del piano di Fase 1.** Perché è
> la convenzione che il cantiere ha già: la Fase 2 ha avuto il suo
> ([brief-be-fe-titoli-iva-soggetto.md](brief-be-fe-titoli-iva-soggetto.md)), e
> il [piano di Fase 1](brief-be-fe-iva-risolutore-e-regime-cliente.md) è chiuso
> salvo una slice gated. Un piano che raccoglie fasi diverse smette di dire cosa
> è finito.
>
> **Origine.** Richiesta di Tid del 2026-08-31, dopo che il team DB ha chiuso
> Fase 2, Fase 3 (metà DB) e le decisioni `D33`/`D34`. Le dieci decisioni del §2
> sono state prese **in quello scambio**, e sono la ragione per cui questo piano
> si può scrivere adesso.
>
> **Stato.** 2026-08-31 — piano scritto, **niente scritto in codice**. Verificato
> sulla **struttura** (doc auto-generata delle funzioni DB, sorgenti BE/FE,
> catalogo). Nessuna misura sui dati.
>
> **Correlati:**
> [fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) ·
> [fn_resolve_iva_riga_it](/dbzero/vendite/funzioni/fn_resolve_iva_riga_it) ·
> [brief-db-fatture-atti-riferimenti-contratto.md](brief-db-fatture-atti-riferimenti-contratto.md) (figlio, gate di `F3`) ·
> [brief-be-fe-titoli-iva-soggetto.md](brief-be-fe-titoli-iva-soggetto.md) (Fase 2)

---

## 0. ⛔ Il fatto che rende questo piano scrivibile: c'è **una funzione sola**

Il §8-nonies del brief madre lo dice in una riga: *«Il DB ha finito: c'è una
funzione sola da chiamare, `vendite.fn_resolve_iva_riga`, che ritorna il
composito e smista per paese»*.

⭐ **E non la chiama nessuno.** Verificato:
`grep -rn "fn_resolve_iva_riga" backend/ frontend/` → **zero occorrenze**. Le
tre voci di questo piano sono, per intero, il lavoro di darle dei consumatori.

**Cosa restituisce** (`RETURNS TABLE`, e i nomi contano perché il BE li mappa):

```text
quota · iva_id · aliquota · natura_codice · is_reverse_charge
      · esigibilita · split_payment · riferimento_normativo
      · origine · titolo_iva_id
```

**Cinque proprietà da conoscere prima di scrivere una riga di codice**, tutte
verificate sul corpo della funzione e non dedotte dal racconto:

| Proprietà | Conseguenza |
| --- | --- |
| **Ritorna N righe**, non una: il plafond può finire a metà riga | un `fetchone()` è il difetto, e non fallisce — prende la parte coperta e butta il resto |
| **`SECURITY INVOKER`** | *«un chiamante senza contesto legge zero titoli e ottiene l'aliquota ordinaria in silenzio»* (dal `COMMENT`). Non è una lista più corta: è un'imposta applicata dove non andava |
| `origine = 'ASSENTE'` quando non trova nulla, **e non solleva** | in bozza è legittimo. Il BE non lo traduce in errore: lo lascia passare e a fermarlo è il gate all'emissione (`I9`, già applicato) |
| **`STABLE` — non consuma il plafond** | la ripartizione è una **proiezione**. Il consumo è `anagrafiche.fn_consuma_plafond_titolo_iva`, che oggi **non ha nessun chiamante** |
| il guscio **solleva** su paese ≠ IT | a differenza del dispatcher CF/PIVA, qui il silenzio non c'è. `E_IVA_PAESE_NON_IMPLEMENTATO` |

---

## 1. Perimetro

| Voce | Cosa | Lati | In questo piano |
| --- | --- | --- | --- |
| **`I3`** | la riga di documento chiama il risolutore; il FE **smette** l'auto-fill | BE + FE | **`F2`** |
| **`I4`** | la riga di fattura smette di rileggere `art.iva_id` e ri-risolve | solo BE | **`F3`** (⛔ gated su un brief DB) |
| **`I5`** | esigibilità e split nel payload SDI | solo BE | **`F4`** — dichiarata **non azionabile**, §4.4 |
| **`I6`** | la casella IVA si chiude | BE + FE | **`F7`** — ⛔ **per ultima**, è Fase 4 |

**Più tre voci che non sono nel brief madre** e che questo piano raccoglie perché
sono debito già maturato o conseguenze dirette di `D33`/`D28`:

| | Cosa | Origine |
| --- | --- | --- |
| **`F0`** | i **cinque codici errore** senza policy | il cancello è rosso **adesso** |
| **`F5`** | `congela_fiscale` esposto nelle capability | conseguenza di `D33`, decisione `P7` |
| **`F6`** | `DEFAULT_IVA_ID` alla chiave naturale | conseguenza di `D28`, decisione `P8` |

⛔ **Fuori**: il generatore XML FatturaPA, la lista dei «titoli sfondati» (residuo
dichiarato di `I7`), `T3-b` del piano Fase 2 (gated su un altro brief DB).

---

## 2. Le dieci decisioni già prese — non si ri-discutono a valle

> Prese da Tid il 2026-08-30/31 nello scambio che ha generato questo piano.
> Ognuna ha il suo perché scritto accanto, perché è così che ci si è arrivati.

### `P1` — sui documenti il risolutore si chiama **senza imponibile**

*«Applicheremo il plafond a tutto se c'è ancora capienza, non spezzeremo le
righe.»*

⭐ **È un ramo che il DB ha già scritto**, e questa è la parte che vale: passare
`p_imponibile = NULL` restituisce **una riga sola**, e il trattamento è quello del
titolo **se e solo se il residuo è > 0**, altrimenti l'ordinaria. Verificato nel
corpo:

```sql
IF p_imponibile IS NULL THEN
    -- ⭐ Anteprima senza importo: la spezzatura non e' calcolabile e
    --   non si inventa. Si dice cosa vale sul PRIMO euro.
    v_q1 := NULL;
    IF v_residuo > 0 THEN  v_iva1 := v_tit_iva; v_org1 := 'TITOLO';
    ELSE                   v_iva1 := v_iva_ord; ...
```

⚠️ **La riga è garantita una sola, non «di solito una»**: `v_due_parti` può
diventare `true` **solo** dentro il ramo `ELSE` di `p_imponibile IS NULL`. Con
l'imponibile assente il secondo record è irraggiungibile.

⚠️ **`quota` esce `NULL`, e non è zero.** Non ci si moltiplica niente.

⛔ **E la spezzatura non è un dato che il documento si porta dietro**: la
proiezione di gennaio non vale a marzo, perché il plafond nel frattempo si
consuma. Si **rifà** a ogni ricalcolo fino alla DEFINITIVA, dove congela e
diventa storia (`D19`, `D15`).

### `P2` — sulla riga di documento sopravvivono **due** informazioni, non nove

Il composito ha dieci caselle; `preventivi_righe` / `ordini_righe` / `ddt_righe`
ne hanno **una**, `iva_id`.

| Casella | Dove va |
| --- | --- |
| `iva_id` | la colonna che c'è già |
| `origine` · `titolo_iva_id` | in **`meta`** della riga (verificato: la colonna esiste su tutte e tre) |
| `riferimento_normativo` | ⭐ **non si copia: si deriva.** È `config.iva.descrizione` (`D24`), cioè l'unica colonna che il lock di `D27` ha lasciato **modificabile apposta** — copiarla su un documento vivo produrrebbe una frase che invecchia, come `fatture_righe.iva_perc` prima di giugno. E i tre repository **joinano già `config.iva`** sulle righe ([ordini](../../../../backend/apps/vendite/db/ordini_repository.py) ~332, [preventivi](../../../../backend/apps/vendite/db/preventivi_repository.py) ~424, [ddt](../../../../backend/apps/vendite/db/ddt_repository.py) ~349): arriva a video derivata e sempre aggiornata, a costo zero |
| le altre sei | **si buttano**, e la fattura le ri-risolve |

⭐ **Perché le due che restano non sono un lusso**: senza `origine` il frontend
non può **spiegare** niente — e `I6` sta per togliere all'operatore la casella
modificabile. Un numero che non si può cambiare **e** che non viene spiegato è la
forma peggiore.

### `P3` — l'emittente c'è **sempre**; se manca, il calcolo si ferma

*«Un operatore ha sempre emittente; se non lo ha il calcolo si ferma e segnala
l'errore.»*

⛔ È il contratto che `SECURITY INVOKER` impone e che il `COMMENT` della funzione
descrive come rischio. Si scrive come **guard nel service**, non come commento:
`p_emittente_fiscale_id` mancante ⇒ errore, mai una chiamata che ripiega
sull'aliquota ordinaria. I processi headless passano da `system_process_context`
(ruolo `BYPASSRLS`), che è la sede già in servizio.

### `P4` — CIG/CUP/commessa: satellite `vendite.fatture_atti`

Deciso il 2026-08-31 dopo aver verificato **come lo modella la FatturaPA**: il
blocco `DatiContratto` è ripetibile `0..N` e ogni occorrenza porta
`RiferimentoNumeroLinea`. Non è testata e non è una colonna di riga: sono N
blocchi agganciati alle loro righe.

📌 Brief al team DB: [brief-db-fatture-atti-riferimenti-contratto.md](brief-db-fatture-atti-riferimenti-contratto.md). ⛔ **`F3` è gated su quello.**

### `P5` — il plafond si consuma alla **DEFINITIVA**, e la pulizia non si tocca

*«L'assegnazione dell'IVA viene fatta quando il lotto passa da emessa a
fatturata, quindi non c'è nessun ripristino del lotto.»* ✅ **Confermato sulla
struttura**: nel seed di `config.stati_doc_fiscale`, `DEFINITIVA` è il primo
stato con `congela_fiscale = t` ed è anche quello con `chiude_lotto = t`; il
ritorno a bozza si può fare **solo** da `EMESSA`, dove nessun movimento esiste
ancora.

⇒ La pulizia non incontrerà **mai** un movimento di plafond: la categoria del
presidio `test-cleanup-fattura-copertura-figlie-v1` è `BLOCCO_VOLUTO`, e
`fn_cleanup_fatture_by_ids` **non va estesa**.

⚠️ **Resta però l'altra metà di `D15-bis`, ed è una specifica non una scelta**:
il giro di lotto deve iterare `ORDER BY data documento, numero` prima di
consumare. Un lock impedisce a due transazioni di andare sotto zero insieme, ma
non sa che esiste una fattura **precedente** non ancora arrivata: senza
quell'ordine, a plafond quasi esaurito **è la fortuna a decidere quale cliente
resta scoperto**.

### `P6` — `I5` aspetta il builder FatturaPA

*«Vero, lo SDI ancora non è pronto, quindi lo faremo al momento opportuno.»*
✅ Verificato: nessun modulo FatturaPA in `backend/apps`.

### `P7` — `congela_fiscale` si espone, e `PRE_FISCALI` cade

### `P8` — `DEFAULT_IVA_ID` passa alla chiave naturale `codice_interno`

### `P9` — l'ordine è `I3` → `I4` → `I6`, in sequenza

⚠️ **In sequenza e non in parallelo**: `I4` è un breaking change dichiarato, e
collaudarlo mentre le righe di documento cambiano sotto rende illeggibile quale
dei due ha rotto cosa.

### `P10` — la ricostruzione storica: **non una tabella nuova, un rubinetto per riga**

Richiesta di Tid: *«la riga a cui viene cambiata l'IVA sia salvata in qualche
tabella per un'eventuale ricostruzione storica»*, con l'avvertenza — giusta — che
storicizzare **tutte** le righe di fattura sarebbe *«un archivio troppo grosso»*.

⭐ **La sede esiste già, ed è spenta esattamente per quella ragione.** Verificato:

| | |
| --- | --- |
| `storico.fatture_righe` | ✅ esiste (`fatture_righe_id`, `change_type`, `snapshot` jsonb, `valid_from`/`valid_to`) |
| `trg_fatture_righe_z90_storico_upd_dlt` | ✅ **montato** su `UPDATE` e `DELETE` |
| `fatture_righe.storicizza` | ⛔ `NOT NULL DEFAULT **false**` |
| `script.trgfn_storico_generic` | ⭐ `IF TG_OP = 'UPDATE' AND NOT NEW.storicizza THEN RETURN NEW;` — **il rubinetto è PER RIGA** |

⇒ **Non serve una tabella nuova**, che sarebbe una seconda sede per una cosa che
esiste. Si accende `storicizza = true` **sulle sole righe che il risolutore
spezza o su cui cambia il trattamento**: l'archivio diventa proporzionale agli
**eventi**, non alle fatture — che è precisamente l'intento della richiesta.

⚠️ **E costa poco per costruzione**: oltre la soglia di congelamento la riga non
si aggiorna più, quindi una riga marcata non continua a produrre storico.

**Il «perché» però lo storico non ce l'ha, e va aggiunto alla riga**: come sui
documenti (`P2`), `origine` e `titolo_iva_id` vanno in **`meta` di
`fatture_righe`** — così finiscono nello `snapshot` senza che nessuno li copi.
`aliquota_iva`, `iva_natura`, `esigibilita` e `split_payment` sono **già**
colonne snapshot sulla riga.

⇒ La ricostruzione diventa: **la riga dice cosa e perché, lo storico dice quando
è cambiato.**

---

## 3. Le decisioni — tutte e quattro chiuse

> Tutte poste a Tid il 2026-08-31 e **tutte decise in giornata**. ⭐ Su due — `N4`
> e `N3` — la verifica sulla struttura ha corretto la premessa da cui partivano:
> è la ragione per cui il testo conserva anche la versione sbagliata.


### `N1` · ✅ **DECISA (Tid, 2026-08-31)** — sì, il risolutore è un building block

`preventivi_service`, `ordini_service` e `ddt_service` fanno la stessa chiamata:
`apps/vendite/db/iva_resolver_repository.py` (la chiamata SQL, `fetchall` — **mai**
`fetchone`) + `apps/vendite/services/iva_resolver_service.py` (guard di `P3`,
traduzione errori, normalizzazione del composito).

⚠️ **Si estraggono funzioni pure o una factory, non un oggetto con stato**
(`feedback_estrarre_non_condividere_stato`). Va nel catalogo BB backend.

Il precedente è `PricingService`, e la regola si ricalca: **mai leggere
`articoli.iva_id` in un service di dominio.**

### `N2` · ✅ **DECISA (Tid, 2026-08-31)** — sì, l'endpoint di anteprima

`POST /api/v1/vendite/iva/resolve/`, calco di `POST /vendite/pricing/resolve/`
([urls_v1.py](../../../../backend/apps/vendite/api/urls_v1.py) ~106): area
`vendite`, sola lettura, emittente derivato dal JWT. Il FE lo chiama in
`onArticoloSelect` **al posto** dell'auto-fill — sostituisce, non affianca.

### `N4` · ✅ **CHIUSA (2026-08-31)** — e la struttura ha corretto la premessa

Il dubbio era: *«solo il DDT accetta `iva_id` nullo, sugli altri documenti credo
ci sia già il `NOT NULL`»*.

⛔ **Verificato sulla doc auto-generata: sono nullable tutte e quattro.**

| Tabella | `iva_id` |
| --- | --- |
| `preventivi_righe` · `ordini_righe` · `ddt_righe` · `fatture_righe` | `integer`, **nullable** |

⭐ E non è una dimenticanza: il §3.1 del brief madre ha una sezione intitolata
*«Perché **non** una `NOT NULL` sulla colonna»* — *«un DDT di solo trasporto non
vende, e un'aliquota lì è un dato che non si applica … una `NOT NULL`
spegnerebbe i documenti legittimi per prendere quelli difettosi»*.

⇒ **Il disegno regge senza modifiche**: una riga che nasce con `origine =
'ASSENTE'` si salva in bozza su tutti e tre i documenti, e a fermarla
all'emissione è il gate di `I9`, già applicato.

⚠️ **Resta la coda che avevo segnalato, e ora è l'unica**: con `I6` la casella si
chiude, quindi l'operatore non potrà più rimediare **dal documento** — dovrà
passare dall'articolo. Il messaggio dei tre gate va riscritto di conseguenza,
o manda a cercare un campo che non esiste più.

### `N3` · ✅ **DECISA (Tid, 2026-08-31)** — `(a')`, e la verifica ha tolto dal tavolo la strada che preferivo

**La domanda**: in fattura si passa l'imponibile vero, quindi il risolutore può
restituire **due** parti e la riga si spezza. Ma `attivita_fatturabili` ha **una**
`fattura_riga_id`: se la riga che le raccoglieva diventa due, dove punta?

#### ⛔ La (c) — «si spezza l'attività a monte» — **il modello non la ammette**

Era la strada che avevo proposto. Verificato sulla struttura, e sono **due**
presidi indipendenti:

| Presidio | Cosa dice |
| --- | --- |
| `uq_attivita_fatturabili_commessa_attivita` | indice **UNIQUE** su `commessa_attivita_id`: **una** AF per riga di commessa. Una seconda AF sarebbe un `23505` |
| `trgfn_attivita_fatturabili_guard_quantita_immutabile` | *«la quantità dell'AF DEVE specchiare la commessa madre»* — ridurre la quantità dell'originale per fare spazio alla seconda parte è **bloccato** |

⭐ **E non è un blocco da aggirare: è il modello che parla.** L'attività
fatturabile **è lo specchio 1:1 della riga di commessa** — l'ha deciso il brief
`immutabilita-quantita` (§4a, 2026-07-21). Spezzarla vorrebbe dire che lo
specchio smette di essere uno specchio, e il bypass esiste (`zeroerp.maintenance_reset_lotto_draft`)
ma **dice un'altra cosa**: usarlo qui farebbe credere al prossimo lettore che sia
in corso un reset di lotto.

#### ⚠️ E la riga di fattura **deve** spezzarsi: non è una scelta

Una riga FatturaPA porta **una** `AliquotaIVA` e **una** `Natura`. Due
trattamenti diversi sullo stesso imponibile sono due `DettaglioLinee`, per
obbligo di formato. Quindi la spezzatura non si può evitare: si può solo
decidere **chi la regge**.

#### ⭐ La strada nuova: `(a')` — due righe legate, e il legame resta sulla capofila

Le due parti sono **due `fatture_righe`** in relazione padre/figlia, e
`attivita_fatturabili.fattura_riga_id` punta alla **capofila**. Dall'attività si
raggiunge la capofila, dalla capofila tutte le sue parti.

⭐ **Il precedente è sulla stessa tabella**: `fatture_righe` ha già `kit_key` e
`kit_articolo_padre_id`, cioè *due righe fisiche con una sola origine logica*, e
`vw_fattura_righe_esposte` le risolve già. La forma è nota, non si inventa.

✅ **Non viola niente**: nessuna unique, nessuno specchio, **zero modifiche a
`attivita_fatturabili`**.
⚠️ **Costa**: `vw_fattura_righe_esposte` e tutto ciò che somma righe deve
conoscere la relazione nuova — ma già conosce quella del kit.

#### ⚠️ Il momento: **prima** del cambio di stato, non durante

Verificato nel corpo di `trgfn_fattura_satellite_guard_congelamento`: legge lo
stato **vivo** della fattura (`JOIN config.stati_doc_fiscale` su
`f.stato_doc_fiscale_id`) al momento della scrittura. In una transazione che
porta prima `stato = DEFINITIVA` e poi scrive le righe, il guard vede
`congela_fiscale = t` e **rifiuta**.

⇒ **La sequenza è obbligata**, e non ha blocchi se rispettata:

```text
per ogni fattura del lotto, ORDER BY data documento, numero   ← P5
   risolvi con l'imponibile VERO
   spezza le righe                      ← fattura ancora EMESSA
   consuma il plafond                   ← fn_consuma_plafond_titolo_iva
   porta a DEFINITIVA                   ← da qui congela
```

#### ⚠️ La sotto-domanda che va con la risposta: come si spezza, in pratica

`fatture_righe.imponibile_riga` è **calcolato dal DB** da `qta × prezzo_unitario`
(meno sconto, con arrotondamento) — *«mai da chi scrive la riga: un valore
passato dall'esterno viene sovrascritto»*. Ma il risolutore ritorna la
ripartizione **in imponibile**, non in quantità.

⇒ Spezzare significa **spezzare la quantità** in proporzione, e le due parti
ricalcolate dal DB possono **non sommare esattamente** l'imponibile originale per
arrotondamento. Su un documento fiscale è un centesimo che qualcuno deve decidere
dove mettere. Va risolto insieme a `N3`, non dopo.

#### ✅ La risposta alla domanda che ha chiuso la voce

*«Se spezziamo la riga fattura, riusciamo lo stesso a legare bene le attività?»*
**Sì, e non si perde niente** — perché il legame che c'è oggi **non è** «attività
→ la sua fetta di riga»: è **N attività → una riga aggregata**, e la quota di
imponibile della singola attività non è registrata da nessuna parte nemmeno
adesso. La spezzatura aggiunge una seconda fetta allo **stesso** livello di
granularità.

✅ Verificato che il consumatore più esposto non si accorge di niente:
`attivita_fatturabili.fatturato` è
`GENERATED ALWAYS AS (fattura_riga_id IS NOT NULL) STORED` — finché l'attività
punta alla capofila resta `true`.

⚠️ **La sola cosa da presidiare**: chi legge un **importo** per attività
attraversando `fattura_riga_id` deve andare **capofila → parti** e sommare. Una
lettura che si ferma alla capofila vede metà valore, e non fallisce.

#### La quantità delle due parti, e il centesimo

⭐ **Metodo (Tid)**: la quantità della parte si ricava come
`imponibile / prezzo`, cioè l'**inverso esatto** della formula con cui il DB
calcola `imponibile_riga` (`qta × prezzo × (1 − sconto/100)`, arrotondato). In
aritmetica esatta l'imponibile ricalcolato **è** la quota: il centesimo sparisce.

⚠️ **Ma non sparisce per costruzione**: la quantità stessa può essere
arrotondata — `arrotondamento_quantita_dec` e `metodo_arrotondamento_quantita`
sono parametri **di riga**, e stanno nella group key. Se mordono, la deriva
torna.

⇒ **Valgono entrambe le cose**: il metodo è il meccanismo, e la regola *«il
centesimo va sulla parte residua»* (Tid) resta la **garanzia** — non il
comportamento quotidiano. La direzione è quella sicura: il plafond non risulta
mai consumato per più di quanto copre.

✅ **Sotto-scelta CHIUSA (Tid, 2026-08-31): quantità derivata, taglio esatto.**
Scartato il taglio a quantità intera. La ragione di Tid: *«preferisco che si
avvicinino il più possibile al tetto, e non possono avere tutto»* — il plafond è
un **diritto documentato** del cliente, e lasciarne indietro qualche centesimo per
avere un numero più bello lo **riduce in silenzio**. Su una riga che il titolo
copre solo in parte, l'unica cosa che si può dare per intero è la capienza.

⚠️ **Ne discende una regola che va scritta, o la decisione si perde**: la
quantità della parte **non passa per l'arrotondamento di riga**
(`arrotondamento_quantita_dec` / `metodo_arrotondamento_quantita`). Applicarlo
rimetterebbe la deriva — e la rimetterebbe **nel verso sbagliato**, lasciando
plafond non consumato, cioè esattamente ciò che questa decisione esclude. Il solo
arrotondamento ammesso è il centesimo residuo, e va **sull'altra parte**.

📌 **Conseguenza a video, accettata**: le due parti mostrano quantità non tonde
(«6,3492 pezzi»). Legittime in FatturaPA. ⭐ Vanno rese **riconoscibili come una
sola origine**, come già fa `vw_fattura_righe_esposte` con le righe di kit:
altrimenti l'operatore legge due righe scollegate con quantità strane.

## 4. Le slice

### 4.1 `F0` — 🔴 i cinque codici errore senza policy

Il cancello è rosso **adesso**: `genera_error_policies --check` risponde
*«DIVERGE dal catalogo»* (verificato il 2026-08-30).

| Codice | Classe | Origine |
| --- | --- | --- |
| `E_IVA_PAESE_NON_IMPLEMENTATO` | `NON_ESEGUIBILE` | Fase 3 IVA |
| `E_IVA_RESOLVE_NON_INVOCABILE` | `TECNICO` | Fase 3 IVA |
| `E_IVA_TITOLI_AMBIGUI` | `NON_ESEGUIBILE` | Fase 3 IVA |
| `E_IVA_TRATTAMENTO_IMMUTABILE` | `CONFLITTO_STATO` | Fase 3 IVA (`D27`) |
| ⛔ `E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE` | `TECNICO` | **altro cantiere** (registri di numerazione, C1-4) |

⛔ **Gated, e il perché va letto.** Il quinto è applicato sul DB di sviluppo —
codice inserito il 30/08 alle 21:30 UTC da `titodb`, funzione
`trgfn_fatture_guard_registro_emittente` presente, trigger
`trg_fatture_a10_guard_registro_emittente_ins_upd` **montato e attivo** — ma
**non è in git**: né il CSV del codice, né quello del messaggio, né il changeSet.

Rigenerare adesso cementerebbe nel backend un codice che in CI **non esiste**
(il database si ricostruisce da zero) e il `--check`, che confronta il file
**carattere per carattere**, farebbe rosso su una PR che non c'entra.

⇒ Si attende il seed in git (Tid lo fa gestire a parte), poi **una sola corsa**:
`genera_error_policies` + i **cinque ripieghi** in `error_messages_fallback.py`,
senza segnaposto.

⚠️ E il quinto **serve davvero**: il suo guard è vivo, e senza policy un rifiuto
tecnico arriverebbe all'operatore come **400 «errore di validazione»** — la
scorciatoia di `ErrorPolicyRegistry.resolve` sui codici `E_` non registrati.

### 4.2 `F2` — `I3`: la riga di documento chiama il risolutore

**Backend** (dopo `N1` e `N2`):

| File | Cosa |
| --- | --- |
| `db/iva_resolver_repository.py` · `services/iva_resolver_service.py` | **nuovi** (`N1`) — la chiamata, il guard di `P3`, la traduzione errori |
| `api/views_iva.py` + `urls_v1.py` | **nuovo** (`N2`) — `POST /vendite/iva/resolve/`, calco di `pricing/resolve/` |
| `services/preventivi_service.py` | risoluzione in `gestisci_riga` (~857-931); `iva_id` resta in whitelist finché non arriva `I6` |
| `services/ordini_service.py` | idem, `_CREATE_KEYS_RIGA` ~123 / `_UPDATE_KEYS_RIGA` ~128 |
| `services/ddt_service.py` | idem, ~108 / ~113 |

⚠️ **Il risolutore si chiama con `p_imponibile = NULL`** (`P1`) e si legge la
**riga unica**; `origine` e `titolo_iva_id` finiscono in `meta` (`P2`).

**Frontend** — i tre `*RigaForm.vue`: l'auto-fill sparisce e al suo posto va la
chiamata di anteprima.

| File | Riga |
| --- | --- |
| [PreventiviRigaForm.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue) | `onArticoloSelect` ~222 |
| [OrdiniRigaForm.vue](../../../../frontend/src/vendite/ordini/components/OrdiniRigaForm.vue) | ~93 |
| [DdtRigaForm.vue](../../../../frontend/src/vendite/ddt/components/DdtRigaForm.vue) | ~96 |

⚠️ **La 3ª occorrenza identica è già qui**: la chiamata di anteprima + il
tooltip di `origine` nascono come **un composable solo**
(`useIvaRisolta`), non copiati tre volte — e va nel catalogo BB FE.

⚠️ **`i18n`**: `origine` ha un vocabolario del DB (`TITOLO`, `ARTICOLO`,
`TIPO_UTENZA`, `ASSENTE`) ed è **aperto**. Si rende con `labelOrCode`, come il
vocabolario del giornale: un valore nuovo compare come codice grezzo, non come
path di chiave.

### 4.3 `F3` — `I4`: la riga di fattura ri-risolve · ⛔ gated

**Backend, e la metà DB non esiste** (verificato: nessuna funzione del database
inserisce in `vendite.fatture_righe`).

| File | Cosa |
| --- | --- |
| [pipeline_repository.py](../../../../backend/apps/vendite/db/pipeline_repository.py) | `art.iva_id` esce dalla proiezione (~235); la riga chiama il risolutore con l'**imponibile vero** |
| [fatture_righe_service.py](../../../../backend/apps/vendite/services/fatture_righe_service.py) | ⛔ **`contratto_id` entra in `_build_group_key`** (~148) |
| — | il consumo del plafond a DEFINITIVA, con l'ordine di `P5` |

⛔ **La group key è un difetto vivo, trovato scrivendo il brief `fatture_atti`.**
Oggi la chiave è `(articolo, dest_BA, uom, prezzo, iva, competenza,
arrotondamenti, rettifica)` — **zero occorrenze** di `contratto` nel file. Due
attività di contratti diversi **collassano nella stessa riga**, e su quella riga
il CIG non ha una risposta.

⭐ Aggiungerlo **non sposta nessun raggruppamento esistente**: le attività senza
contratto lo hanno `NULL`. Si spezzano solo le righe che oggi mescolano davvero
due atti.

⚠️ **Non si scrive `esigibilita` né `split_payment`**: li scrive il trigger dal
soggetto cliente (`I5` metà DB, `20260829-54`). Verificato che oggi il BE non li
tocca — e deve restare così.

### 4.4 `F4` — `I5`: dichiarata non azionabile

Resta il solo payload SDI (`EsigibilitaIVA`), e **non ha dove atterrare**: il
builder XML non esiste. Si chiude quando nascerà, e la coda è annotata lì.

### 4.5 `F5` — `congela_fiscale` nelle capability (`P7`)

Il BE espone il flag insieme allo stato del documento; il FE lo legge e
`PRE_FISCALI = ['DRAFT','EMESSA']` in
[LottoDrawer.vue](../../../../frontend/src/vendite/components/LottoDrawer.vue) ~730
sparisce.

⚠️ **Si unifica la sorgente, non le due domande**: quella lista risponde a
*«l'azione fallirebbe?»*, non a *«è congelato?»*. Oggi danno la stessa risposta e
per la regola 3 di `D15` non devono appoggiarsi l'una sull'altra.

### 4.6 `F6` — `DEFAULT_IVA_ID` alla chiave naturale (`P8`)

Un lettore solo: [catalogo_service.py](../../../../backend/apps/catalogo/services/catalogo_service.py) ~1434.
È il secondo dei tre passi di [linee-guida-sql §6b](../../linee-guida-sql.md).

### 4.7 `F7` — `I6`: la casella si chiude · ⛔ **per ultima**

* **BE**: `iva_id` fuori da `_CREATE_KEYS_RIGA` **e** `_UPDATE_KEYS_RIGA` nei tre
  service — ⚠️ in `preventivi_service` è una **tupla inline** (~1078-1080), non
  una `frozenset`;
* **FE**: `<IvaSelect>` disabilitata **anche in CREATE**. ⚠️ E in
  [PreventiviRigaForm.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue)
  il `canSave` pretende `f.iva_id` (~347, verificato): va ripensato, o la
  creazione **si blocca da sola**.

⛔ **Non prima di `F2` e `F3`**: toglie l'ultima uscita manuale, e applicata prima
che le righe nascano con l'aliquota giusta **cementa i valori sbagliati di oggi**.
⚠️ È decisa da `D1` e sembra pronta in mezz'ora — *una voce sbloccata non è una
voce da anticipare*.

---

## 5. L'ordine

```text
F0  i cinque codici errore        ⛔ gated sul seed del 5° (a cura di Tid)
F5  congela_fiscale               ⭐ indipendente, si può fare subito
F6  DEFAULT_IVA_ID                ⭐ indipendente, piccola
--- decisioni N1 e N2 ---
F2  I3 · documento                BE + FE, una slice sola
F3  I4 · fattura                  ⛔ gated su brief-db-fatture-atti + decisione N3
F4  I5 · SDI                      📌 quando nascerà il builder
F7  I6 · la casella si chiude     ⛔ dopo F2 e F3
```

⚠️ **`F2` non si spezza in BE-poi-FE.** Se il BE risolve e il FE continua
l'auto-fill, per un po' ci sono due risposte alla stessa domanda — cioè il
difetto che questo cantiere sta togliendo, riprodotto durante la sua correzione.

---

## 6. Presidi attesi

> Uno per slice, e nessuno è copertura: ognuno prova la cosa che, se sbagliata,
> **non darebbe nessun sintomo**.

* **`F2` · la riga non si spezza mai**: risolvere una riga di documento su un
  soggetto con plafond **incapiente** → **una** riga di ritorno, con il
  trattamento del titolo. ⚠️ Un test su plafond capiente passerebbe in entrambi i
  mondi: il caso va **costruito** incapiente, non cercato;
* **`F2` · l'auto-fill è morto**: scegliere un articolo con `iva_id` valorizzato e
  un titolo del soggetto che dice **un'altra cosa** → a video vince il titolo. Se
  il vecchio `onArticoloSelect` sopravvive da qualche parte, questo test lo trova;
* **`F2` · il guard di `P3`**: chiamare senza emittente → **errore**, non
  l'aliquota ordinaria. ⛔ È il presidio più importante del piano: il difetto che
  previene non ha nessun sintomo — una fattura semplicemente sbagliata;
* **`F3` · la group key**: due attività identiche in tutto **tranne il
  contratto** → **due** righe di fattura. E il gemello negativo: due attività con
  lo **stesso** contratto → **una** riga. Senza il secondo, un'implementazione che
  spezza sempre passerebbe il primo;
* **`F3` · l'ordine del consumo**: due fatture nello stesso lotto su un plafond
  che ne copre una sola → la capienza va a quella con **data documento** minore,
  non a quella che il giro incontra per prima. ⚠️ Va costruito, e il test deve
  poter fallire: con l'ordine sbagliato il risultato dipende dagli id;
* **`F5` · il flag segue il dato**: spostare `congela_fiscale` su uno stato e
  vedere il pulsante spegnersi, poi rimetterlo e vederlo riaccendersi. È ciò che
  distingue «legge la colonna» da «per caso oggi la lista dice lo stesso» — la
  stessa prova che il team DB ha usato per `D33`;
* **`F7` · la creazione non si blocca da sola**: creare una riga di preventivo
  con la `IvaSelect` disabilitata → il save **passa**. È il difetto che il brief
  madre ha già nominato e che nessun test esistente prenderebbe.

⭐ **Il presidio che chiude il cantiere**, e va scritto una volta sola: la stessa
riga letta **come documento** e **come attività di fatturazione** deve dare lo
stesso `iva_id`. È il §6 del brief madre, ed è l'unico test che si accorge quando
le due strade tornano a divergere.

---

## 7. Fuori perimetro, dichiarato

* ⛔ **Il generatore XML FatturaPA**;
* 📌 **La lista dei «titoli sfondati»** — residuo dichiarato di `I7`, sta nel
  piano di Fase 2;
* 📌 **`script.fn_get_iva_override`**, rotta e con zero chiamanti: va **ritirata**
  dal DB, non riparata. Non è roba di questo piano;
* ⛔ **Qualunque misura sui dati.** La domanda «quante righe useranno un titolo?»
  non decide niente. Decide che il modello ammette un titolo per riga, e che
  finché nessuno lo legge la sede costruita in Fase 2 resta una promessa.

---

## 8. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-31 | Piano scritto su richiesta di Tid, dopo la chiusura DB di Fase 2, Fase 3 e delle decisioni `D33`/`D34`. Nove decisioni prese nello scambio (§2). ⭐ **`P1` si è rivelata un ramo già scritto nel DB** (`p_imponibile IS NULL`): la regola «non spezzare le righe sul documento» non richiede una riga di codice DB. ⛔ Due difetti vivi trovati verificando invece di assumere: il **cancello dei codici errore è rosso** con un quinto codice applicato al DB e non in git, e **`contratto_id` non è nella group key** delle righe di fattura — due attività di contratti diversi collassano oggi nella stessa riga. Quattro decisioni restano aperte (§3), e `N3` — a chi puntano le attività quando la riga di fattura si spezza — è il punto duro del piano |
