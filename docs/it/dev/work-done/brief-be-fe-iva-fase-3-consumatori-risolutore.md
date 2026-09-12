# Piano BE/FE — Fase 3 del cantiere IVA: i consumatori del risolutore

> ## ✅ CHIUSO — 2026-08-31: il risolutore ha i suoi consumatori
>
> **Tutte le slice sono fatte**: `F0`, `F2` (a·b·c·d), `F3-a`, `F3-b1`, `F3-b2`,
> `F3-c`, `F5`, `F6`, `F7`. Il consuntivo di ognuna sta nel §9.
>
> ⭐ **Cosa è cambiato davvero.** Il 2026-08-31 mattina
> `grep -rn "fn_resolve_iva_riga" backend/ frontend/` dava **zero occorrenze**:
> il DB aveva finito e non lo chiamava nessuno. Adesso lo chiamano il form dei
> tre documenti, il salvataggio delle loro righe e il giro di fatturazione — e
> il plafond dei titoli **si consuma**, provato sul database vero.
>
> ⛔ **`art.iva_id` non è più la risposta di nessuno.** Era la nona sede che
> rispondeva per conto suo alla domanda «che IVA ha questa riga», e scavalcava
> l'uso della fornitura e i titoli documentati del cliente: su un esportatore
> abituale scriveva l'aliquota piena, senza sintomo.
>
> 📌 **Resta UNA coda, ed è stata raccolta altrove**: `F4` / `I5` — il blocco
> `EsigibilitaIVA` nel payload SDI — non ha dove atterrare finché il **builder
> XML FatturaPA non esiste**. Non è lavoro rimandato: è un sottosistema che non
> c'è. La coda vive nell'**item 9** di
> [fatturazione-roadmap.md](fatturazione-roadmap.md), insieme agli altri due
> blocchi che aspettano lo stesso builder (`DatiContratto` e le righe **spezzate**
> dal plafond). ⚠️ Ci è stata messa apposta **prima** di chiudere qui: un residuo
> che resta in un documento chiuso è un residuo perso.

> **Destinatario:** backend (`dev/backend-tid`) e frontend.
>
> **Base.** [brief-db-be-iva-risolutore-e-regime-cliente.md](brief-db-be-iva-risolutore-e-regime-cliente.md)
> — le voci `I3`, `I4`, `I5`, `I6` del suo §5, l'elenco unico nel suo §8-nonies.
> Questo documento non ri-discute nessuna decisione di quel brief: **costruisce
> la metà BE/FE che il DB non può fare.**
>
> **Perché un documento nuovo e non un capitolo del piano di Fase 1.** Perché è
> la convenzione che il cantiere ha già: la Fase 2 ha avuto il suo
> ([brief-be-fe-titoli-iva-soggetto.md](../work-done/brief-be-fe-titoli-iva-soggetto.md)), e
> il [piano di Fase 1](../work-done/brief-be-fe-iva-risolutore-e-regime-cliente.md) è chiuso
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
> [brief-db-fatture-atti-riferimenti-contratto.md](../work-done/brief-db-fatture-atti-riferimenti-contratto.md) (figlio, gate di `F3`) ·
> [brief-be-fe-titoli-iva-soggetto.md](../work-done/brief-be-fe-titoli-iva-soggetto.md) (Fase 2)

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
| **`F3-c`** | ⛔ le righe di fattura sono ordinate per **UUID** articolo | decisione di Tid del 31/08, trovata chiudendo `F3-a` |

⚠️ **`F6` non è più «solo seed», e non è più prima del DB**: il team DB ha
trovato che `parameters.csv` non è riscrivibile (mina `DEFAULT_UTILITY`, già
esplosa il 25/08) e la voce è scesa **in fondo** all'ordine di lavoro DB, dietro
un passo di `20_code` che nessuno aveva chiesto. Il lettore BE —
`catalogo_service.py`, il form-defaults dell'articolo — si adegua **quando il
seed è cambiato**, non prima. Dettaglio in
[brief-db-default-iva-chiave-naturale.md](../work-done/brief-db-default-iva-chiave-naturale.md) §2-bis.

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

📌 Brief al team DB: [brief-db-fatture-atti-riferimenti-contratto.md](../work-done/brief-db-fatture-atti-riferimenti-contratto.md). ⛔ **`F3` è gated su quello.**

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

### 4.1 `F0` — 🔴 i codici errore senza policy — ⛔ **sono UNDICI, non cinque**

> ⭐ **AGGIORNAMENTO 2026-08-31 (2), verificato su `46fbf56ab`: il gate è
> caduto, e il conto è cambiato.** Il quinto codice —
> `E_FATTURA_REGISTRO_EMITTENTE_INCOERENTE` — **è in git**. E con lui sono
> arrivati **altri tre** codici dello stesso cantiere, che questa sezione non
> nominava:
>
> | Codice | Classe | id msg | changeSet |
> | --- | --- | --- | --- |
> | `E_DOCUMENTO_DATA_ANTERIORE_ULTIMO_NUMERO` | `DATO_ERRATO` | 1030 | `20260831-06` |
> | `E_FAMIGLIA_DOCUMENTO_RIFERIMENTO_INESISTENTE` | `TECNICO` | 1031 | `20260831-18` |
> | `E_EMITTENTE_CODICE_FORMA_NON_VALIDA` | `DATO_ERRATO` | 1032 | `20260831-23` |
>
> ⇒ **La corsa unica di `genera_error_policies` va fatta su undici**, e i
> ripieghi in `error_messages_fallback.py` sono **undici**, senza segnaposto.
> ⚠️ Rigenerare contandone cinque o nove non fallisce subito: il `--check`
> confronta **carattere per carattere**, quindi il rosso arriva in CI il giorno
> dopo, su una PR che con l'IVA non c'entra niente.
>
> ⛔ **E ne mancherà un dodicesimo**: il guard anti-catena della colonna
> capofila (voce 5 dell'ordine di lavoro DB) conierà un codice `TECNICO` suo.
> Se `F0` parte prima che quella voce sia applicata, la corsa andrà rifatta.
> Il prossimo id messaggio libero è **1033**.

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

### 4.3 `F3` — `I4`: la riga di fattura ri-risolve · 🟡 **una metà è fatta**

> ⭐ **La voce ha due metà, e solo una aspettava il DB.** Scoperto il 2026-08-31
> rispondendo alla domanda di Tid *«c'è qualcosa di Fase 3 che non dipende dal
> DB?»*: la **group key** è puro Python — `attivita_fatturabili.contratto_id`
> esiste già, con la sua FK. È stata fatta (§9, `F3-a`). Resta gated la
> **spezzatura della riga**, e su un prerequisito che nessuno aveva chiesto (§9,
> `F3-b`).

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

### 4.6 `F6` — `DEFAULT_IVA_ID` alla chiave naturale (`P8`) · ✅ **fatta**

Un lettore solo: [catalogo_service.py](../../../../backend/apps/catalogo/services/catalogo_service.py) ~1434.
È il secondo dei tre passi di [linee-guida-sql §6b](../../linee-guida-sql.md).
Consuntivo in §9.

### 4.7 `F7` — `I6`: la casella si chiude · ✅ **fatta il 2026-08-31**

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
F0  i codici errore               ✅ il cancello è VERDE — 31/08
F5  congela_fiscale               ✅
F6  DEFAULT_IVA → chiave naturale ✅ 31/08 — ⛔ il BE era ROTTO, non «da fare»
F2  I3 · documento                ✅ (a·b·c·d)
F3a I4 · group key contratto      ✅ 31/08 — non aspettava nessuno
F3c I4 · ordinamento leggibile    ✅ 31/08 — le righe erano ordinate per UUID
F3b1 I4 · l'IVA dal risolutore    ✅ 31/08 — `art.iva_id` esce dalla proiezione
F3b  I4 · spezzatura della riga   🟢 il DB è pronto (fatture_atti + capofila)
F3b2 I4 · consumo del plafond     ✅ 31/08 — seed applicato, smoke 21/21
F4  I5 · SDI                      📌 quando nascerà il builder FatturaPA
F7  I6 · la casella si chiude     ✅ 31/08 — P9 soddisfatta (vedi §9)
```

⭐ **Il 2026-08-31 il team DB ha chiuso tutte e cinque le richieste**
([elenco](../work-done/brief-db-richieste-aperte-dal-backend.md), ora in
`work-done`). Da quel momento in Fase 3 **non c'è più niente di gated sul DB**:
resta `F3b`, che è lavoro nostro, e `F4`, che aspetta un sottosistema che non
esiste.

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
| 2026-08-31 (3) | ⭐ **Il team DB ha ri-verificato l'ordine di lavoro su `46fbf56ab` e quattro cose di questo piano sono cambiate.** `F0` non è più gated ma **conta undici codici, non cinque** (tre ne sono arrivati il 31/08 dal cantiere registri, e un dodicesimo arriverà col guard della capofila). `F3-b` ha la sua forma: colonna `riga_capofila_id`, «stessa fattura» come **vincolo** e non come guard, «niente catene» come trigger con un codice `TECNICO` nuovo. ⛔ E la riga del brief DB che diceva *«per la vista la forma del kit non si inventa»* **era sbagliata**: il kit **aggrega**, e aggregare le due parti produrrebbe un solo `DettaglioLinee` — forma decisa: **due righe sorelle**, mai `livello 1`. `F6` è scesa in fondo all'ordine DB (mina `parameters.csv`). ⭐ Nata `F3-c` da una frase di Tid — *«negli elenchi organizzare per codice articolo»* — che ha scoperchiato un difetto vivo: le righe di fattura sono ordinate per **UUID** |
| 2026-08-31 (4) | ⭐ **`F3-b1` chiusa**: la riga di fattura chiede l'IVA al risolutore, e `art.iva_id` esce dalla proiezione — era la **nona** risposta autonoma alla stessa domanda, e scavalcava titoli e uso della fornitura. ⛔ Trovato che il **consumo del plafond** non è scrivibile: serve un **task di pipeline**, che è un **seed DB** — nuovo elenco, voce 1. ⚠️ Stesso schema della voce 5, ma stavolta trovato **prima** di scrivere il codice che ne dipende |
| 2026-08-31 (3) | ⭐ **Il team DB ha chiuso tutte e cinque le richieste** (`69252ebe7`), compresa la voce 5 nata quella mattina. Da lì: `F6` chiusa — e ⛔ **il BE era rotto**, non «da fare»: il seed era passato alla chiave naturale e `catalogo_service` chiedeva ancora `DEFAULT_IVA_ID`, prendendo il ripiego in silenzio; `F3-c` chiusa (le righe erano ordinate per **UUID**); `S3-b` verificata già fatta, meno due commenti che dicevano il contrario del codice. ⇒ **In Fase 3 non resta nulla di gated sul DB**: solo `F3b`, che è lavoro nostro |
| 2026-08-31 (2) | ⭐ Domanda di Tid: *«hai cose da fare in Fase 3 a prescindere dal DB?»*. Controllando voce per voce sono venute fuori **tre** cose: `F3` ha due metà e solo una aspettava il DB (la **group key** è puro Python — fatta, `F3-a`); i due cataloghi BB che il piano chiedeva **non erano stati compilati**; e ⛔ la spezzatura di `N3` era bloccata su una colonna di `fatture_righe` che **nessuno aveva mai chiesto** al team DB, ora voce 5 dell'elenco. ⚠️ Trovato anche che gli smoke di `F2-a` e `F2-d` non erano stati salvati come file: uno smoke che non sta nel repo non è un presidio |
| 2026-08-31 | Piano scritto su richiesta di Tid, dopo la chiusura DB di Fase 2, Fase 3 e delle decisioni `D33`/`D34`. Nove decisioni prese nello scambio (§2). ⭐ **`P1` si è rivelata un ramo già scritto nel DB** (`p_imponibile IS NULL`): la regola «non spezzare le righe sul documento» non richiede una riga di codice DB. ⛔ Due difetti vivi trovati verificando invece di assumere: il **cancello dei codici errore è rosso** con un quinto codice applicato al DB e non in git, e **`contratto_id` non è nella group key** delle righe di fattura — due attività di contratti diversi collassano oggi nella stessa riga. Quattro decisioni restano aperte (§3), e `N3` — a chi puntano le attività quando la riga di fattura si spezza — è il punto duro del piano |

---

## 9. Avanzamento

> Scritto il 2026-08-31, a lavoro in corso.

### ✅ `F2-a` — il building block del risolutore

Prima voce eseguita, e la ragione della priorità è che è **pura addizione**: due
file nuovi, nessun consumatore ancora agganciato, quindi rischio di regressione
zero — ed è il gate di tutto il resto di `F2`.

| File | Cosa |
| --- | --- |
| `apps/vendite/db/iva_resolver_repository.py` | **nuovo** — wrapper su `fn_resolve_iva_riga`, ritorna una **lista** |
| `apps/vendite/services/iva_resolver_service.py` | **nuovo** — `risolvi`, `risolvi_anteprima`, `meta_riga`, guard di `P3` |
| `apps/vendite/tests/services/test_iva_resolver_service.py` | **nuovo** — 10 casi |
| `docs/it/dev/backend/catalogo-building-block-backend.md` | il BB registrato a catalogo |

⭐ **Trovato un accoppiamento che il piano non aveva previsto, e aggirato senza
pagarlo.** `test_error_codes_declared_guardrail` esige che **ogni** codice `E_*`
nominato in un punto di chiamata Python abbia la sua classe: nominare
`E_IVA_TITOLI_AMBIGUI` o `E_IVA_PAESE_NON_IMPLEMENTATO` nel service avrebbe reso
**rosso** quel cancello, perché `F0` è gated sul seed del quinto codice. Cioè
`F2-a` sarebbe stata bloccata da `F0`.

⇒ **Il BB non nomina nessuno dei quattro**, e non è un ripiego: dal 2026-08-05 il
codice di dominio viaggia in un **campo strutturato** dell'eccezione e
`translate_db_errors` lo legge da sé. È il debito che
`pricing_service._KNOWN_DB_ERROR_MARKERS` dichiara nel proprio commento come «da
togliere quando quel refactor sarà fatto» — **è fatto**, e il BB nuovo non lo
eredita. Il fallback è `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`, già
dichiarato), che il catalogo descrive esattamente come *«guard di parametro su
valori che nessuna interfaccia può produrre: se arrivano, è rotto il chiamante»* —
cioè `P3` alla lettera.

⚠️ **Finché `F0` non arriva** un `E_IVA_*` sollevato dal DB risolve sulla
scorciatoia dei codici `E_` non registrati (400 «errore di validazione») invece
che sulla sua classe. Non è un test rosso e si sana da sé il giorno del seed, ma
va saputo.

#### Le prove, e cosa prova ciascuna

| Prova | Esito |
| --- | --- |
| 10 test unitari (repository mockato) | ✅ verdi |
| ⭐ **mutazione** — spento il guard sull'emittente e quello sulla ripartizione | ✅ **7 asserzioni cadono**: i presidi discriminano |
| ⭐ **smoke sul DB vero**, in transazione annullata | ✅ dieci colonne, `quota = NULL`, `origine = 'ARTICOLO'` — l'SQL lega davvero |

⚠️ **Perché lo smoke serviva**: i test unitari mockano il repository, quindi
provano la catena Python e **non** che la funzione esista né che i parametri
leghino. Un `RETURNS TABLE` con una colonna in più o un cast sbagliato sarebbe
passato verde.

⭐ E lo smoke ha **confermato `D32`**: senza `soggetto_id`, `esigibilita` e
`split_payment` escono entrambi `NULL` — *«senza il soggetto il regime di
scissione non è determinato»*. La coppia dice «non lo so» invece di affermare
«non scissa».

### ✅ `F5` — `congela_fiscale`: la nona copia cade, e con essa il pulsante muto

⭐ **La voce si è rivelata più grande e migliore di come era scritta.** Il piano
diceva «il BE espone `congela_fiscale`, il FE lo legge». Guardando il DB è
emerso che `script.fn_check_fattura_eliminabile_da_lotto` **esiste già**, è
`STABLE` e pura, legge `congela_fiscale` (post-`D33`) e ritorna l'array ordinato
dei motivi con `{codice, reason, reason_key}` — e il suo `Scopo` dichiara **due**
consumatori: *«`fn_elimina_fattura_da_lotto` (solleva il codice del primo
motivo) e il BE, per spiegare invece di far fallire»*. Il secondo non esisteva.

⇒ Non si è esposto un flag: si è esposta la **capability**, e questo toglie non
una copia della soglia ma **tutto il ragionamento duplicato**.

| File | Cosa |
| --- | --- |
| `apps/vendite/db/vendite_repository.py` | `LEFT JOIN LATERAL` sulla funzione + `can_reset_fattura` / `_reason` / `_reason_key` |
| `apps/vendite/types.py` | la terna su `LottoFattureRow` |
| `frontend/.../LottoDrawer.vue` | `PRE_FISCALI` **eliminata**; l'azione resta visibile e **spenta col motivo** |
| `backend/scripts/tests/smoke-lotto-capability-reset-fattura.py` | **nuovo**, 5 casi |

⭐ **E l'operatore guadagna una cosa che prima non aveva**: fino a oggi l'azione
*spariva* e basta. Ora resta a video, spenta, con il perché — reso nel kebab via
`app-menu-item-motivo`, dove il tooltip non arriva perché su touch non c'è hover.

⚠️ **Fail-closed**: capability assente ⇒ azione spenta. Su un verbo che
**cancella** il documento, «non lo so» non può voler dire «vai».

✅ **Le chiavi i18n c'erano già tutte** (`vendite.lotti.azione_reason.*`, it+en):
il DB le dichiarava e nessuno le leggeva.

#### Le prove

| Prova | Esito |
| --- | --- |
| smoke sul DB vero, transazione annullata, **contesto operatore impostato** | ✅ 5/5 |
| il caso **negativo** (lotto e fattura oltre soglia) | ✅ `False` + motivo + chiave |
| ⭐ il caso **positivo** (lotto e fattura sotto soglia) | ✅ `True`, motivo assente |
| ⭐ **mutazione**: il flag smette di derivare dal motivo | ✅ **2 casi cadono** |

⚠️ **Il contesto operatore nello smoke non è cerimonia**: senza i cinque GUC
`vendite.fatture` risponde zero righe sotto RLS e lo smoke sarebbe verde **per
sottrazione** — «nessuna riga sbagliata» perché nessuna riga.

### ✅ `F2-b` — l'endpoint di anteprima

`POST /api/v1/vendite/iva/resolve/` (`apps/vendite/api/views_iva.py`), calco di
`pricing/resolve/`. Sei test (`apps/vendite/tests/api/test_iva_resolve_api.py`).

⛔ **Non accetta un imponibile, ed è il contratto che tiene `P1`.** Il modo
solido di garantire «sui documenti la riga non si spezza» non è ricordarselo: è
non dare al client il parametro con cui romperlo.

⛔ **La PK dell'emittente, non il `soggetto_ruolo_id`** — trappola già pagata dal
progetto (`feedback_emittente_pk_vs_soggetto_ruolo`), e qui sarebbe stata muta:
con l'id sbagliato la funzione non trova l'emittente, quindi non trova i suoi
titoli, e risponde con l'aliquota ordinaria.

### ⛔ Un difetto muto trovato costruendo `F2-b`, e corretto nel BB

`fn_resolve_iva_riga_it` applica lo **stadio B** — i titoli documentati, cioè le
dichiarazioni d'intento — solo se riceve **insieme** `p_soggetto_id` e
`p_emittente_fiscale_id` (riga 174 del corpo). E il soggetto dal billing account
**non lo deriva**, a differenza del paese che il guscio deriva da sé.

⇒ Un chiamante che ha in mano il solo BA — cioè **il caso ordinario di un
form** — otterrebbe l'aliquota piena su un esportatore abituale, e niente
segnalerebbe che i titoli non sono stati nemmeno guardati.

✅ Corretto **nel BB e non nei chiamanti**: `IvaResolverService` deriva il
soggetto dal BA quando manca, con `BillingAccountRepository.get_soggetto_id`
(nuovo). È la stessa catena che il trigger di `I5` percorre per esigibilità e
split — la domanda fiscale è del **cliente**. Due test nuovi: la derivazione
avviene, e un soggetto esplicito **non** viene sovrascritto.

### ✅ `F6` — `DEFAULT_IVA`, e il BE era **rotto**, non «da fare»

⛔ **Non era una voce BE**, e il piano la classificava male: `linee-guida-sql §6b`
descrive **quattro passi** e ne nomina proprio questo parametro. I primi due
(`codice_interno` su `config.iva` + lock) li ha fatti `D28`; il terzo e il
quarto sono **seed DB**, e il team li ha applicati il 2026-08-31
([brief](../work-done/brief-db-default-iva-chiave-naturale.md)).

⛔ **Il giro DB è passato e quello BE no**, quindi da quel momento
`catalogo_service` chiedeva `DEFAULT_IVA_ID` — un parametro che a catalogo **non
esiste più**. Non falliva: prendeva il ripiego, e il form di creazione articolo
**smetteva di proporre l'aliquota**, in silenzio.

| File | Cosa |
| --- | --- |
| `catalogo/services/catalogo_service.py` | legge `DEFAULT_IVA` e **risolve** l'id con `resolve_config_id_by_codice_interno` (BB che esisteva già) |
| `catalogo/api/views.py` | il commento che diceva ancora `DEFAULT_IVA_ID` |
| `catalogo/tests/services/test_catalogo_service.py` | 3 casi → **5** |
| `core/tests/services/test_parameter_service.py` | il nome-fixture `DEFAULT_IVA_ID` → `PARAM_TEST` |

⛔ **E il punto che rende questa voce diversa da un rename: NON si fa `int()`
sul valore.** Il `codice_interno` è `22`, cioè **un numero**: un lettore rimasto
indietro non fallirebbe — otterrebbe l'**id 22**. Verificato sul DB vero:

| | |
| --- | --- |
| `config.iva` con `codice_interno = '22'` | ✅ **id 16** — la stessa aliquota di prima, il comportamento a video non cambia |
| `config.iva` con `id = 22` | ⛔ **non esiste** — oggi. Ma il modello lo ammette eccome, e il giorno che esistesse sarebbe un'aliquota **sbagliata** proposta in silenzio, su un dato che finisce sui documenti fiscali |

⭐ **Il caso che discrimina** è proprio questo, ed è nei test: il lookup dice `7`
mentre il parametro dice `"22"` — a vincere deve essere il lookup. Un test che
avesse solo cambiato il nome della chiave sarebbe passato anche sull'`int()`.

⚠️ **Il ripiego resta best-effort ma NON muto**: `None` a video è
indistinguibile da «non c'è un default configurato», quindi un seed che punta a
un'aliquota disattivata sparirebbe senza lasciare traccia. Il `logger.warning` è
l'unico posto in cui quella differenza resta leggibile.

✅ **Il gemello negativo del brief**: `DEFAULT_IVA_ID` cercato per nome nudo in
`backend/` → restano solo commenti **al passato** («non esiste più», «Leggeva»,
«fino al 2026-08-31») e una variabile di shell omonima in uno smoke bash, che
con il parametro non c'entra. Nessun lettore vivo.

### ✅ `F3-c` — le righe di fattura non sono più ordinate per **UUID**

Decisione di Tid: *«negli elenchi dovremmo sempre organizzare per codice
articolo»*. Non era un'aggiunta — era un difetto vivo, e la chiave diceva
`str(group_key["articolo_id"])`, cioè l'**UUID**: deterministico per la
macchina, **rumore** per chi legge la fattura.

| File | Cosa |
| --- | --- |
| `db/pipeline_repository.py` | `art.codice` nella `SELECT` di `list_attivita_da_fatturare` (**in fondo**) + campo su `AttivitaDaFatturare` |
| `services/fatture_righe_service.py` | `_GruppoRiga.articolo_codice`, e l'ordinamento lo usa |
| test | `test_riga_nr_deterministico` → **3 casi**: l'ordine per codice, la stabilità, e la riga senza codice |

⭐ **I codici di prova sono in ordine INVERSO rispetto agli UUID** (`ART_A` ha
l'UUID minore e il codice `ZZZ-001`), ed è l'unica forma che discrimina: con
codici concordi all'ordine degli id **entrambe** le implementazioni passerebbero.

⚠️ **`codice` e non `codice_interno`**: qui l'ordinamento serve a chi **legge il
documento**, e chi legge vede il `codice`. Ne discende che se qualcuno rinomina
un articolo fra due rigenerazioni di un lotto in bozza l'ordine cambia — ⭐ ed è
**corretto** che cambi. Sta scritto accanto alla chiave, o il prossimo lettore
torna all'UUID credendo di riparare qualcosa.

⭐ **La stabilità fra due rigenerazioni resta**, ed è l'altra metà dello scopo di
quella chiave: c'è un caso apposta, perché senza, un'implementazione che non
ordinasse affatto passerebbe il primo.

#### Le prove di `F6` e `F3-c`

| Prova | Esito |
| --- | --- |
| suite backend intera | ✅ **4251** |
| ⭐ **mutazione** su `F3-c` — torna all'UUID · nessun ordinamento | ✅ **1 e 3** casi cadono |
| ⭐ smoke sul DB vero, esteso ai casi 8-10 | ✅ `art.codice` lega, è il codice **vero**, e `tipo_movimento` **non è scivolato** |
| ⭐ `DEFAULT_IVA` sul DB vero | ✅ `'22'` → **id 16**; `id 22` → **non esiste** |

ℹ️ **Una cosa che lo smoke dichiara invece di nascondere**: sui dati di oggi
l'ordine per codice e quello per UUID **coincidono**, quindi lì il confronto non
discrimina — e lo stampa. A discriminare sono i test unitari, dove il caso è
costruito.

### ✅ `S3-b` — i tre riferimenti dell'atto anche in CREATE

Sbloccata dal changeSet `20260831-24`. BE e FE erano già stati allineati; qui
sono caduti **due commenti che dicevano ancora il contrario** del codice
(*«in CREATE non compaiono ancora … gated sul DB»*), uno dei quali duplicava
alla lettera il blocco sotto di sé. ⚠️ Un commento che contraddice il codice non
è rumore: è la prossima persona che riapre una voce già chiusa.

### ✅ `F2-c` — i tre service chiamano il risolutore

`P10-bis` (Tid, 2026-08-31): **opzione B** — il payload vince, ma si registra
cosa avrebbe detto il risolutore.

| File | Cosa |
| --- | --- |
| `iva_resolver_service.applica_riga_documento` | la regola, **una volta sola** per i tre domini |
| `ddt_service` · `ordini_service` · `preventivi_service` | `_risolvi_iva_riga`, wrapper sottile col contesto di testata |

⚠️ **Le due risoluzioni non hanno lo stesso peso**, ed è il pezzo che non si
vede leggendo in fretta: senza `iva_id` nel payload la risoluzione è
**autoritativa** e gli errori **passano** (meglio fermarsi che scrivere un'IVA
inventata); con `iva_id` è di **audit**, best-effort dentro un savepoint —
stesso idioma di `BaseSourceHandler._resolve_pricing_audit`.

⭐ **`MANUALE` solo quando DIVERGE**: se l'operatore conferma il valore
proposto non ha sovrascritto niente, e marcarlo manuale renderebbe manuale
tutto il traffico del form — cioè toglierebbe al campo ogni capacità di dire
qualcosa.

⛔ **Due guard nuovi**, e sono `P3` che morde: senza emittente o senza data la
riga **non si scrive**. In `preventivi_service` l'emittente segue i due passi
già usati per i componenti (testata → operatore) — ma qui l'assenza **non è**
uno skip silenzioso come là.

#### Le prove

| Prova | Esito |
| --- | --- |
| suite vendite | ✅ 1781 |
| ⭐ **mutazione**: il risolutore staccato dalla scrittura in DDT e preventivi | ✅ **2 presidi cadono** |
| ⭐ mutazione sul BB: `MANUALE` sempre + payload ignorato | ✅ 2 casi cadono |

⚠️ **Sette test esistenti adeguati**, e la ragione è sempre la stessa: il
risolutore è un **collaboratore nuovo** di `gestisci_riga` e va mockato come il
repository — senza, test che parlano di componenti BoM aprirebbero una
connessione vera e in CI fallirebbero per un motivo che non c'entra.

### ✅ `F2-d` — il frontend smette di rispondere per conto suo

Scelta **(c)** (Tid, 2026-08-31): l'endpoint prende le **coordinate del
documento** e deriva il contesto dalla testata.

| File | Cosa |
| --- | --- |
| `services/_iva_contesto_documento.py` | **nuovo** — `carica_testata` (I/O) + `contesto_da_testata` (**pura**) |
| `api/views_iva.py` | prende `documento_tipo` + `documento_id`; ⛔ `data_riferimento` **tolta dal contratto** |
| i tre `_risolvi_iva_riga` | delegano allo **stesso** estrattore |
| `frontend/.../api/iva.js` · `_shared/righe/useIvaRisolta.js` | **nuovi** — BB alla 3ª occorrenza |
| i tre `*RigaForm.vue` | l'auto-fill **sparisce**; compare l'hint che dice **da dove viene** l'aliquota |
| `it.json` · `en.json` | il vocabolario `vendite.iva_origine.*` |

⭐ **La separazione fra le due funzioni dell'estrattore è la cosa che conta**:
`contesto_da_testata` è **pura**, così i service — che la testata l'hanno già
caricata — non spendono un secondo round-trip, mentre la view, che ha solo un
id, usa il loader. Anteprima e salvataggio guardano la **stessa fonte**: non
possono dire due numeri diversi.

⛔ **E `data_riferimento` è uscita dal contratto dell'endpoint.** Accettarla dal
client avrebbe ammesso che l'anteprima rispondesse per una data diversa da
quella su cui il salvataggio calcola — cioè avrebbe **costruito** il disaccordo
che questo endpoint esiste per togliere. Un campo dichiarato e ignorato è la
stessa promessa falsa da cui il cantiere è partito.

⭐ **L'hint sotto il campo IVA è il pezzo che ripaga `P2`**: `I6` sta per
togliere la casella, e un'aliquota che non si può cambiare **e** che non viene
spiegata è la forma peggiore. Ora il form dice se viene dall'articolo, dall'uso
della fornitura o da un titolo del cliente — con `labelOrCode`, perché il
vocabolario è del DB ed è **aperto**.

⚠️ **La chiamata è best-effort di proposito**: se l'anteprima non risponde il
campo resta vuoto e si salva lo stesso. L'autorità è il backend al salvataggio,
non questa chiamata, che serve a far **vedere** — non a decidere.

#### Le prove

| Prova | Esito |
| --- | --- |
| suite backend intera | ✅ **4204** |
| build FE + eslint sui file toccati | ✅ |
| `check_i18n_keys.py` | ✅ **5 problemi, gli stessi identici di prima** (verificato con `git stash`) |
| ⭐ smoke sul DB vero della catena intera: coordinate → testata → contesto → anteprima | ✅ |
| ⭐ presidio «il client non detta il contesto» | ✅ un BA e una data mandati dal client vengono **ignorati** |

### ✅ `F3-a` — l'ATTO entra nella chiave, e la voce non aspettava nessuno

⭐ **Nata da una domanda di Tid**: *«hai cose da fare in Fase 3 a prescindere dal
DB?»*. Controllando voce per voce è venuto fuori che `F3` ha **due metà**, e che
il piano le teneva insieme sotto un unico ⛔ — quindi una metà risultava bloccata
senza esserlo.

`contratto_id` fuori dalla chiave di aggregazione era un **difetto vivo che col
cantiere IVA non c'entra**: due attività di contratti diversi collassavano nella
stessa riga di fattura. Il CIG è solo ciò che l'ha fatto notare — la riga
aggregata è già sbagliata senza.

| File | Cosa |
| --- | --- |
| `db/pipeline_repository.py` | `a.contratto_id` nella proiezione (**in fondo**, §sotto) + campo sulla dataclass |
| `types.py` | `contratto_id` in `GroupAttivitaKey`, col perché accanto |
| `services/fatture_righe_service.py` | nella chiave di gruppo **e** nell'ordinamento |
| `tests/services/test_fatture_righe_service.py` | 6 casi nuovi (30-35) |
| `backend/scripts/tests/smoke-group-attivita-contratto.py` | **nuovo**, 11 controlli |

⭐ **E la sede per il dato esiste già, senza aspettare la tabella**: la
`group_key` finisce per intero nel `meta` della riga, quindi l'atto della riga è
**già scritto** oggi (`meta.group_key.contratto_id`). Quando
`vendite.fatture_atti` arriverà, il dato per popolarla non va ricostruito.

⛔ **Sulla RETTIFICA il contratto NON entra nella chiave**, ed è una decisione,
non una dimenticanza: l'identità di una riga di nota di credito è la **riga di
fattura che rettifica**, che è strettamente più specifica del contratto. Dargli
peso potrebbe spezzare due rettifiche della **stessa** riga su un dato incoerente
a monte — cioè rompere in silenzio l'invariante «due rettifiche della stessa riga
restano aggregabili». Quando `fatture_atti` darà alla riga di fattura una sede
per l'atto, la rettifica lo copierà **da lì**, come già fa con prezzo, sconto e
IVA (`N-1`).

⚠️ **La voce è entrata anche nell'ORDINAMENTO dei gruppi, e non è un dettaglio**:
da quando la chiave spezza, due gruppi possono differire **solo** per l'atto. Due
gruppi che l'ordinamento non distingue prendono il `riga_nr` nell'ordine in cui
le attività sono arrivate — cioè la numerazione delle righe smette di essere
stabile fra due rigenerazioni dello stesso lotto, che è precisamente ciò che
quella chiave esiste per impedire.

#### Le prove, e cosa prova ciascuna

| Prova | Esito |
| --- | --- |
| 6 test nuovi + i 29 esistenti | ✅ 35 |
| ⭐ **il gemello negativo** — stesso contratto ⇒ **una** riga sommata | ✅ senza, un'implementazione che spezza sempre passerebbe il caso principale |
| ⭐ **senza contratto il raggruppamento non cambia** | ✅ è la promessa «non sposta nessun raggruppamento esistente», ed è la maggior parte del traffico |
| ⭐ **mutazione** ×3 — atto fuori dalla chiave · fuori dall'ordinamento · dentro anche sulla rettifica | ✅ **3, 1 e 1 casi cadono**: ogni decisione ha il suo presidio |
| ⭐ **smoke sul DB vero**, transazione annullata | ✅ **11/11** |
| suite backend intera | ✅ **4221** |

⛔ **Perché lo smoke serviva, e non era cerimonia.** La proiezione è una tupla
letta **per indice**: una colonna aggiunta in mezzo invece che in fondo
sposterebbe tutte quelle dopo, e il difetto sarebbe **muto** — `rett_iva_id`
finirebbe in `contratto_id` e viceversa, entrambi interi, entrambi plausibili. Il
controllo che discrimina confronta la riga **campo per campo** prima e dopo aver
posato l'atto: l'unica differenza ammessa è l'atto stesso.

⭐ **E il caso è stato COSTRUITO**: `attivita_fatturabili` ha 52 righe e **zero**
con un contratto. Uno smoke che avesse *cercato* l'attività con l'atto sarebbe
passato a vuoto — verde per sottrazione, che è il difetto che questo cantiere
insegue da giorni.

### 🆕 `F3-c` — ⛔ le righe di fattura sono ordinate per **UUID**

> **Decisione di Tid, 2026-08-31**: *«negli elenchi dovremmo sempre organizzare
> per codice articolo»*. ⭐ **Non è un'aggiunta: è la correzione di un difetto
> vivo**, trovato guardando la chiave di ordinamento mentre si chiudeva `F3-a`.

Le righe di fattura sono già ordinate «per articolo». Ma con questa chiave —
`_chiave_ordinamento` in `apps/vendite/services/fatture_righe_service.py`:

```python
str(g.group_key["articolo_id"] or ""),   # ← l'UUID dell'articolo
```

⛔ È l'**UUID**. Per il computer è un ordinamento perfettamente deterministico e
stabile; per una persona che guarda la fattura è **rumore casuale**. Due
articoli della stessa famiglia finiscono agli antipodi del documento, e non
c'è nemmeno un ordine sbagliato da criticare: non c'è proprio un ordine
leggibile.

⚠️ **Il commento sopra quella funzione dichiara lo scopo per metà**: dice che la
chiave esiste per rendere `riga_nr` **stabile fra due rigenerazioni**. Vero, e
la stabilità va tenuta. Ma un ordinamento serve anche a **essere letto**, e su
questo l'UUID vale zero. Sostituirlo con il `codice` articolo tiene la prima
proprietà e recupera la seconda.

**La richiesta.**

1. in `_chiave_ordinamento`, l'UUID lascia il posto al **`codice`** articolo;
2. ⚠️ **il dato oggi non arriva**: `AttivitaDaFatturare`
   (`apps/vendite/db/pipeline_repository.py`) porta `articolo_descrizione` ma
   **non** il codice — la query prende `art.descrizione` e basta. Va aggiunto
   `art.codice` alla `SELECT` e il campo alla dataclass. Se non lo si dice, chi
   implementa trova il dato mancante e ripiega sulla **descrizione**, che è
   un'altra cosa.

⚠️ **`codice` e non `codice_interno`, di proposito.** Per convenzione di
progetto `codice` è l'etichetta che l'utente può cambiare e `codice_interno` è
la chiave immutabile. Qui l'ordinamento serve **a chi legge il documento**, e
chi legge vede il `codice`. La conseguenza è che se qualcuno rinomina un
articolo fra due rigenerazioni dello stesso lotto in bozza, l'ordine delle righe
cambia. ⭐ **È corretto che cambi** — il documento riflette i codici di adesso —
e non tocca nulla di già emesso, dove le righe esistono col loro `riga_nr`.
**Va scritto proprio perché** il prossimo lettore, vedendo *«la chiave deve
essere stabile»*, potrebbe tornare all'UUID credendo di riparare qualcosa.

ℹ️ Le righe **senza articolo** (rettifiche, oneri) restano dove sono oggi:
chiave vuota, quindi in testa. Il comportamento non cambia.

⭐ **E si sposa con `F3-b`**: le due parti di una riga spezzata hanno lo stesso
articolo, quindi con l'ordinamento per codice escono già adiacenti da sole.
L'`ordinamento` uguale alla capofila resta comunque necessario — è quello che le
tiene attaccate anche quando in mezzo c'è un'altra riga dello stesso articolo a
prezzo diverso — ma non lavora contro l'ordine generale: lo rifinisce.

📌 **Perimetro dichiarato**: la decisione riguarda le **righe dei documenti**
(fattura per ora, e la stessa regola dove vale — DDT, ordini, preventivi), non
le liste di navigazione, che hanno le loro colonne ordinabili configurabili.

### ✅ `F3-b1` — la riga di fattura chiede l'IVA al risolutore

⭐ **La nona copia cade, ed era la più grossa.** Fino al 2026-08-31
`_GROUP_ATTIVITA_SELECT` leggeva `art.iva_id`: la risposta autonoma alla stessa
domanda a cui risponde il risolutore, che scavalcava **l'uso della fornitura** e
**i titoli documentati del cliente**. Su un esportatore abituale scriveva
l'aliquota piena, in fattura, senza sintomo.

⭐ **E togliendola non si perde niente**: `articoli.iva_id` è lo **stadio A1** del
risolutore, che la ritorna con `origine = 'ARTICOLO'` (verificato nel corpo di
`fn_resolve_iva_riga_it`, riga 102). Non è una funzione in più: è la stessa
risposta, più gli stadi che prima si saltavano.

| File | Cosa |
| --- | --- |
| `db/pipeline_repository.py` | `art.iva_id` **fuori** dalla proiezione e dalla dataclass · nuovo `batch_get_fattura_iva_context` |
| `services/fatture_righe_service.py` | le **testate prima delle chiavi**, `_risolvi_iva_attivita` con cache, `_build_group_key(row, *, iva_id)` |
| test | 7 casi nuovi (36-42) |
| `scripts/tests/smoke-group-attivita-contratto.py` | casi **5-bis** e **11** |

⛔ **`iva_id` è un PARAMETRO della chiave, non un campo della riga**, e non è
pignoleria di firma: se fosse rimasto sulla dataclass con un default, un
chiamante distratto avrebbe prodotto righe a IVA `None` **senza nessun errore**.
Così costruire una chiave senza aver risolto è impossibile.

⚠️ **L'ordine dei passi è diventato un requisito**: le testate si creano **prima**
delle chiavi, perché il risolutore vuole cliente, emittente e data — tre cose che
stanno sulla testata. ⭐ Lo scambio non costa niente: quella chiamata dipende solo
da lotto e attività, mai dalle chiavi.

⛔ **La PK dell'emittente, non il `soggetto_ruolo_id`.** `vendite.fatture` porta
`emittente_soggetto_ruolo_id`; il risolutore vuole la PK di
`anagrafiche.emittenti_fiscali`, e si passa da
`anagrafiche.fn_get_emittente_fiscale_pk`. È la trappola che il progetto ha già
pagato tre volte, e qui sarebbe stata **muta**. ✅ Provata sul DB vero: **PK 32**
contro **soggetto-ruolo 72** — due numeri diversi, quindi il controllo
discrimina.

⭐ **Cache per (fattura, articolo)**, e non è un'ottimizzazione opzionale: la
risposta dipende da articolo, cliente, emittente e data, e dentro una fattura gli
ultimi tre sono fissi. Un lotto massivo arriva a **50.000** attività — senza
cache, 50.000 round-trip.

⚠️ **`risolvi_anteprima`, cioè SENZA imponibile**, ed è deliberato *in questa
slice*: con l'importo il risolutore può tornare **due parti**, e la riga andrebbe
spezzata. La spezzatura vive nel giro del lotto, dove il plafond si **consuma**
(`P5`) — qui una proiezione a due parti sarebbe un numero che invecchia fino alla
DEFINITIVA.

⛔ **La RETTIFICA non passa dal risolutore**: `N-1`, *«la nota di credito non può
differire da quanto fatturato»*. L'IVA è quella della riga rettificata, e
ri-risolvere produrrebbe una gemella con un'aliquota diversa dal documento che
corregge.

#### Le prove

| Prova | Esito |
| --- | --- |
| 7 casi nuovi + i 37 esistenti | ✅ **44** |
| ⛔ **il presidio più importante del piano** (`P3`): senza emittente ci si **ferma**, e non si scrive nulla | ✅ |
| ⭐ **mutazione** ×4 — guard `P3` spento · cache senza fattura · rettifica al risolutore · meta senza origine | ✅ **1 caso ciascuna** |
| ⭐ smoke sul DB vero, casi **5-bis** e **11** | ✅ gli indici tengono dopo l'uscita della colonna; la PK è la PK |
| suite backend intera | ✅ **4258** |

⛔ **Perché il caso 5-bis è nato**: la proiezione è una tupla letta **per
indice**, e togliere una colonna in mezzo fa scivolare tutte quelle dopo. Il
confronto prima/dopo del caso 5 vede solo ciò che **cambia** fra due letture —
uno scivolamento **costante** gli sfugge. Il 5-bis confronta i valori con la riga
vera, sui tipi che uno scivolamento renderebbe assurdi.

### 🟡 `F3-b2` — il consumo del plafond: **scritto**, e in attesa di due righe di seed

> ⚠️ **Correzione a una mia frase sbagliata** (Tid, 2026-08-31: *«scusa ma il
> task pipeline non è BE?»*). **Sì**: l'handler, il servizio, il repository e i
> test sono BE, e sono stati scritti. A essere del team DB è solo la
> **configurazione** che dice *quali* task girano in quale step — e lo dice il
> codice stesso, nel commento di `_TASK_ORDER_DEPENDENCIES`: *«la configurazione
> la scrive un altro team»*. Avevo scritto «non è scrivibile»: era falso.

| File | Cosa |
| --- | --- |
| `services/plafond_fattura_service.py` | **nuovo** — l'ordine, la risoluzione con l'imponibile vero, il consumo, la spezzatura |
| `db/pipeline_repository.py` | 5 metodi nuovi + `consuma_plafond_lotto` fra i task Python |
| `services/pipeline_step_executor.py` | il gestore, il registry e la **dipendenza d'ordine** |
| `tests/services/test_plafond_fattura_service.py` | **nuovo**, 14 casi |

⭐ **L'autorità è la madre che prende il LOCK, non il risolutore.** Il risolutore
è `STABLE`: proietta il residuo che vede, e fra la proiezione e il lock
un'altra transazione può aver consumato. La ripartizione buona è quella che
torna da `fn_consuma_plafond_titolo_iva`. ⚠️ E quando la copertura effettiva è
**minore** della proiezione, la seconda parte del risolutore può non esserci:
l'aliquota ordinaria si **richiede alla stessa autorità**, non si deduce — a
plafond ormai esaurito il risolutore risponde con lo stadio A, che è
esattamente ciò che serve.

⭐ **La quantità si deriva dall'imponibile** (`imponibile / prezzo effettivo`,
sconto incluso), che è l'inverso esatto della formula con cui il DB calcola
`imponibile_riga`. ⛔ E **non passa per l'arrotondamento di riga**: applicarlo
rimetterebbe la deriva **nel verso sbagliato**, lasciando plafond non consumato
— cioè riducendo in silenzio un diritto documentato del cliente.
⭐ **Il centesimo va sulla parte residua, e qui è vero per costruzione**:
`qta_residua = qta_totale − qta_coperta`, quindi le due parti sommano
esattamente la riga di partenza comunque cada la divisione.

⭐ **La dipendenza d'ordine è già in guardia**: `numera_fatture` dichiara
`consuma_plafond_lotto` come predecessore. Finché il task non è nel seed la riga
non fa nulla — un predecessore assente è una configurazione valida — ma il
giorno che arriva, se arriva **girata**, lo step si ferma **prima** che il primo
task scriva, invece di scoprirsi a documenti già numerati.

#### Le prove

| Prova | Esito |
| --- | --- |
| 14 casi | ✅ |
| ⭐ **mutazione** ×5 — ordine per id · centesimo arrotondato · sconto fuori dal divisore · autorità al risolutore · guard `P3` spento | ✅ **1 caso ciascuna** |
| suite backend intera | ✅ **4248** |

⛔ **Non c'è smoke, ed è dichiarato**: il giro non è invocabile finché il seed
non esiste, quindi uno smoke oggi proverebbe solo il servizio chiamato a mano —
cioè quello che i test già fanno. Lo smoke va scritto **con** la riga di
configurazione, ed è il presidio che il brief al DB chiede.

### ✅ `F7` — `I6`: la casella IVA si chiude

⭐ **`P9` letta come soddisfatta, e la ragione sta nel merito della decisione.**
`P9` diceva «`I3` → `I4` → `I6`, in sequenza» perché *«`I4` è un breaking change
dichiarato, e collaudarlo mentre le righe di documento cambiano sotto rende
illeggibile quale dei due ha rotto cosa»*. Quel cambiamento è **finito**: le
righe di documento (`F2`) e quelle di fattura (`F3-b1`) nascono già con l'IVA
del risolutore. Ciò che non è in esercizio è il **consumo del plafond**, che
tocca la spezzatura — non la casella del form. Decisione di Tid.

| File | Cosa |
| --- | --- |
| `ddt_service` · `ordini_service` | `iva_id` fuori da `_CREATE_KEYS_RIGA` **e** `_UPDATE_KEYS_RIGA`; `payload_iva_id=None` |
| `preventivi_service` | idem, ma la whitelist di UPDATE è una **tupla inline** e la CREATE non ne ha affatto: lì l'unico cancello è `payload_iva_id=None` |
| i tre `*RigaForm.vue` | `<IvaSelect>` **spenta sempre**, `iva_id` fuori dal payload, e ⛔ il `canSave` non lo pretende più |
| `it.json` · `en.json` | i **tre messaggi dei gate** riscritti (coda di `N4`) |

⛔ **Il `canSave` andava tolto, non era ripulisti.** Con la casella spenta e
l'auto-fill morto, se l'anteprima non risponde il campo resta vuoto: la riga non
si sarebbe potuta salvare, e **la creazione si sarebbe bloccata da sola** senza
che nulla lo spiegasse. È il difetto che il brief madre aveva già nominato.

⛔ **E i tre messaggi dicevano ancora «scegli l'aliquota»** — cioè mandavano
l'operatore a cercare un campo ormai spento. Ora dicono dove si imposta davvero:
*«L'aliquota non si sceglie sul documento: si imposta sull'articolo, e la riga la
riprende.»* È la coda di `N4`, e senza sarebbe stata la forma peggiore: un
numero che non si può cambiare **e** un messaggio che dice di cambiarlo.

⚠️ **La chiave non viene RESPINTA, viene SCARTATA**: un client vecchio che manda
ancora `iva_id` non riceve un errore, il valore semplicemente non arriva. È il
motivo per cui BE e FE vanno **insieme**, come per `F2`.

#### Le prove, e due difetti nei presidi stessi

| Prova | Esito |
| --- | --- |
| suite backend intera | ✅ **4255** · build FE ✅ · eslint ✅ · i18n pulito |
| ⭐ **mutazione**: `iva_id` rimesso nelle whitelist di DDT e ordini | ✅ **2 casi cadono** |
| ⭐ **mutazione**: `iva_id` rimesso nella tupla di UPDATE dei preventivi | ✅ **1 caso cade** |
| ⭐ **mutazione**: `payload_iva_id` torna a leggere il payload | ✅ **1 caso cade** (preventivi: lì è l'unico cancello) |

⛔ **Nessun test è caduto quando la chiusura è stata scritta**, e la cosa è
istruttiva: **nessun presidio copriva «il payload vince»**. La regola dell'opzione
B era vissuta per tre giorni senza prova. I quattro casi nuovi la chiudono nei
due versi.

⚠️ **E il primo dei quattro era VACUO**: cercava `iva_id` dentro una chiave
`update_fields` che non esiste — `update_riga(id, **campi)` passa i campi
sparsi — quindi trovava un dizionario vuoto e passava **sempre**. Se ne è accorta
la mutazione, non la corsa verde. Ora asserisce anche che il test ha davvero
morso (`descrizione` c'è).

### 🔎 Controllo critico del codice di `F7` — 2026-08-31

> Richiesta di Tid a lavoro finito. **Tre rilievi**, tutti corretti, e il primo
> è la fragilità peggiore del giro.

⛔ **Un silenzio, dove doveva esserci un rifiuto.** Dopo `I6` `payload_iva_id`
vale sempre `None`. Se un chiamante gli passasse di nuovo un valore **non
otterrebbe un errore**: `applica_riga_documento` scivolerebbe sul ramo di
**AUDIT**, che è best-effort dentro un savepoint — gli errori si **inghiottono**
e a vincere è il payload. Cioè una riga si salverebbe anche quando l'IVA non è
determinabile, su un documento che diventerà fiscale.
⇒ `make_risolvi_iva_riga` ora **rifiuta** un `payload_iva_id` valorizzato.
⚠️ Non è ridondante con le whitelist: quelle fermano il **client**, questo ferma
il **chiamante** — un service che un giorno rileggesse il valore da un'altra
strada. Due presidi nuovi, e il gemello positivo perché un guard che rifiuta
sempre spegnerebbe l'intera scrittura di righe sui tre domini.

⛔ **Una seconda sorgente per lo stesso fatto**, ed era mia: scrivevo
`meta.plafond_spezzatura = CAPOFILA|PARTE` per spiegare la quantità non tonda.
Ma quel fatto lo dice già **`riga_capofila_id`**, ed è da lì che
`vw_fattura_righe_esposte` deriva `tipo_riga = 'PARTE_PLAFOND'`. Basta un
`UPDATE` sulla colonna senza il `meta` (o viceversa) e la riga si racconta in
due modi, senza che niente sollevi. **Tolto.**

📌 **Un ramo diventato irraggiungibile, dichiarato invece che nascosto.** Il ramo
di audit di `applica_riga_documento` oggi non lo percorre nessuno: i suoi test
provano una strada che nessun chiamante vive, quindi **non difendono niente**.
Non l'ho tolto — è la decisione `P10-bis` resa in codice, e ritirarla è una
scelta di Tid, non una pulizia da fare in una revisione.

✅ **E due controlli che non hanno trovato niente**, che vanno detti perché la
loro assenza è un risultato: nessun altro punto del frontend manda `iva_id` in
un payload di riga (le occorrenze restanti sono **risposte** dei riepiloghi), e
non c'è **asimmetria di modello** — `offerte_righe` e `contratti_righe` non
hanno affatto `iva_id`, quindi il perimetro dei tre domini è completo.

| Prova | Esito |
| --- | --- |
| suite backend intera | ✅ **4257** |
| ⭐ **mutazione**: il guard di `I6` spento · il guard che rifiuta sempre | ✅ **1 caso** e **1 caso** |
| build FE · eslint su tutto `src/vendite` · i18n · licenze | ✅ |

### ✅ `F3-b2` — il consumo del plafond è in esercizio (2026-08-31)

Il team DB ha applicato il seed **come chiesto**: `consuma_plafond_lotto` **in
testa** allo step DEFINITIVA su **entrambe** le pipeline (4 e 6), e ⭐ **senza
chiave `fn`** — cioè nessuna madre SQL, che era la duplicazione che questo
cantiere ha già pagato una volta con `fn_generate_fatture_righe`.

⇒ Scritto lo smoke che il brief chiedeva *«con la riga di configurazione»*:
`backend/scripts/tests/smoke-consuma-plafond-lotto.py`, **21 controlli, tutto
verde sul DB vero**.

| Cosa prova | Esito |
| --- | --- |
| ⭐ **il cablaggio**: il seed nomina il task e il codice sa eseguirlo | ✅ le due metà che possono divergere si conoscono |
| ⛔ il task **non dichiara una `fn`** | ✅ l'implementazione è Python |
| ⚠️ sta **prima** di `numera_fatture`, su entrambe | ✅ dopo, il guard di congelamento rifiuterebbe |
| ⚠️ **il gemello**, e sta PRIMA: senza titolo il giro non tocca niente | ✅ zero righe nuove, zero movimenti |
| ⭐ la riga **si spezza**: 24 pezzi → 12 + 12 | ✅ |
| ⭐ le due parti **sommano esattamente** | ✅ 12 + 12 = 24 |
| ⭐ l'accumulatore ha **visto** il consumo | ✅ 120,00 su un plafond di 120,00 |
| ⭐ la vista le mostra **sorelle**: `PARTE_PLAFOND`, livello 0, stesso ordinamento, **entrambe con importo** | ✅ |

⭐ **Il caso si è costruito, e due volte contro il modello** — ed entrambe le
volte il modello aveva ragione:

1. il primo giro **scongelava** una fattura per poterla spezzare: la macchina a
   stati rifiuta `DEFINITIVA → EMESSA` (`E_LOTTO_PARAMETRO_NON_COERENTE`), e ha
   fatto bene. Il caso si costruisce su una fattura **già `EMESSA`**, che è
   anche il momento vero in cui il task gira;
2. il gemello **spegneva il titolo** dopo averlo usato:
   `trgfn_prevent_deactivate_if_children` lo rifiuta — figli prima del padre. Il
   gemello è passato **prima** della costruzione del titolo, ed è anche più
   onesto: prova lo stato «prima», non uno stato forzato.

⚠️ **E la 2263 è esclusa per nome** nella selezione della fixture: è la fattura
che non va numerata. Qui non si numera e si annulla tutto, ma non la si tocca.

### 🟢 Cosa manca davvero

Verificato il 2026-08-31, e non era previsto: il consumo del plafond deve vivere
in un **task di pipeline nuovo**, nello step DEFINITIVA e **prima** di
`numera_fatture` (la fattura lì è ancora `EMESSA`, e il guard di congelamento
legge lo stato **vivo**).

⛔ **Ma i task della pipeline sono un SEED**, non codice:
`db/changelog/migrations_v2/80_data/sql/vendite/fatturazione_pipeline.csv`.
Verificato: lo step DEFINITIVA contiene oggi
`['numera_fatture', 'popola_fatture_rettifiche', 'stampa_documenti_lotto']`, su
**due** pipeline (massiva e giornaliera).

⇒ ⚠️ **È lo stesso schema della voce 5**: un lavoro che sembrava «solo BE» è
fermo su un prerequisito che nessuno ha chiesto. L'handler, il servizio e i suoi
test si possono scrivere per intero — semplicemente **non verrebbero invocati da
niente** finché il seed non c'è.

📌 Richiesta passata al team DB:
[brief-db-richieste-aperte-dal-backend-2.md](brief-db-richieste-aperte-dal-backend-2.md),
voce 1. ⚠️ **File nuovo e non il precedente riaperto**, come quello stesso
prescrive: *«un ordine di lavoro che si riapre smette di dire cosa è finito»*.

⭐ **Il resto è pronto**: `anagrafiche.fn_consuma_plafond_titolo_iva` esiste,
prende il **lock** di riga (`D15-bis`) e ritorna già la ripartizione
(`quota_coperta`, `quota_ordinaria`, `residuo_dopo`, `movimento_id`) — quindi il
BE non deve calcolarla, deve **ordinare** le fatture (`P5`: `data documento,
numero`) e scrivere le due parti.

### ⛔ `F3-b` — la spezzatura: il DB è pronto, il resto è nostro

✅ **Applicato il 2026-08-31** (voce 5, `20260831-30`/`31`/`33`), e il team ha
chiuso anche due decisioni che il brief non aveva posto:

| | |
| --- | --- |
| `riga_capofila_id` | nullable, **FK composita** `(riga_capofila_id, fattura_id)` → `(id, fattura_id)` |
| «stessa fattura» | ⭐ **decisione `D`**: non un guard ma un **vincolo** — il database non lo lascia violare, e con `riga_capofila_id` a `NULL` non si applica affatto |
| «niente catene» | resta un trigger (`E_FATTURA_RIGA_CAPOFILA_INCOERENTE`, `TECNICO`): nessun vincolo PostgreSQL sa guardare la riga puntata |
| la vista | ⭐ **decisione `B`**: due righe **sorelle** — `tipo_riga = 'PARTE_PLAFOND'`, **entrambe a `livello 0`**, `ordinamento` della capofila |

⛔ **`livello 1` è stato scartato, e non per estetica**: in
`vw_fattura_righe_esposte` significa *«riga descrittiva, senza importo»*, e il
codice che fa «salta il livello 1» **esiste perché è la regola della vista**. Su
una fattura spezzata perderebbe la seconda parte **senza nessun errore**, con un
totale semplicemente più basso.

⚠️ E la forma del kit era la strada sbagliata per la ragione opposta: **aggrega**,
e aggregare le due parti produrrebbe **un solo** `DettaglioLinee` — cioè
cancellerebbe la ragione per cui la riga si è spezzata.

#### ✅ La forma decisa dal team DB (2026-08-31), e cosa deve sapere il BE

Il team DB ha preso le due decisioni che mancavano. Non si ri-discutono qui:
questa è la parte che cambia il codice del backend.

**1. Il legame è `vendite.fatture_righe.riga_capofila_id`** — nullable, `NULL`
sulla capofila, valorizzata sulle parti successive. Con **due** invarianti
imposte in modi diversi:

* **«stessa fattura» è un VINCOLO**, non un guard: FK composita
  `(riga_capofila_id, fattura_id) → fatture_righe(id, fattura_id)`. ⇒ Il BE non
  può sbagliarlo nemmeno per errore, e non deve verificarlo lui;
* **«niente catene» è un TRIGGER** — una parte deve puntare a una riga che ha
  `riga_capofila_id` a `NULL`. ⇒ **Solleverà un codice `TECNICO` nuovo**
  (`F0` lo dovrà includere): il BE deve scrivere sempre *capofila → parti*, mai
  *parte → parte*.

**2. ⛔ La vista NON aggrega le due parti, e la riga del brief DB che diceva
«la forma del kit non si inventa» era sbagliata.** Aggregare produrrebbe **un
solo `DettaglioLinee`**, cioè cancellerebbe la ragione per cui la riga si
spezza.

✅ **Forma decisa: due righe sorelle.** In `vw_fattura_righe_esposte` le due
parti escono **entrambe con il loro imponibile**, entrambe a `livello 0`, con lo
stesso `ordinamento` (quello della capofila) e un `tipo_riga` nuovo sulla
seconda.
⛔ **Scartato `livello 1`**, che nella vista significa *«riga descrittiva, senza
importo»* — i componenti di kit escono infatti con `imponibile` a `NULL`. ⚠️ Il
codice che fa *«salta il livello 1, è solo descrizione»* esiste **perché è la
regola della vista**: su una fattura spezzata perderebbe la seconda parte senza
nessun errore, con un totale semplicemente più basso.

⇒ **Per il FE**: le due righe vanno rese riconoscibili come una sola origine a
partire dal `tipo_riga`, non da un'indentazione.

### ✅ I due cataloghi, che il piano chiedeva e non erano stati fatti

`useIvaRisolta` + `api/iva.js` nel catalogo BB **frontend** (il §4.2 lo chiedeva
esplicitamente); `applica_riga_documento`, `carica_testata` /
`contesto_da_testata`, `make_risolvi_iva_riga` e `normalizza_iva_id` in quello
**backend**.

⚠️ **E una riga di verità sulle prove**: la voce a catalogo dichiarava «10 casi»
(oggi sono 18, più 12 + 7) e nessuno dei due smoke di `F2-a`/`F2-d` era stato
**salvato come file** — erano corse *ad hoc*. Uno smoke che non sta nel repo non
è un presidio: è un controllo fatto una volta. Il catalogo ora lo dice invece di
vantare una copertura che non c'è.

### ~~🔴 `F2-d` — ferma, e su una cosa trovata guardando i file~~

I tre `*RigaForm.vue` devono chiamare l'endpoint di anteprima al posto
dell'auto-fill. ⛔ Ma **solo `PreventiviRigaForm` conosce il billing account**:
`OrdiniRigaForm` e `DdtRigaForm` hanno il solo id del documento.

⚠️ Senza BA l'anteprima **non può derivare il soggetto**, quindi salta lo stadio
B: il form mostrerebbe l'aliquota ordinaria e il salvataggio scriverebbe quella
del titolo. **L'operatore vedrebbe un numero e ne otterrebbe un altro** — e non
sarebbe un errore, sarebbe un disaccordo silenzioso fra due schermate della
stessa riga.

Vedi §10 per la scelta.

---

## 10. ❓ La domanda che ferma `F2-c`

> Nata scrivendo il cablaggio, e non era prevedibile leggendo il piano.

`I6` — «la casella IVA si chiude» — è **decisa** (`D1`) ma va **per ultima**,
perché applicata prima cementerebbe i valori sbagliati di oggi. Quindi durante
`F2-c` l'operatore **può ancora** scegliere l'IVA a mano.

⇒ Ne discende una domanda che il piano non poneva: **al salvataggio di una riga,
chi è autoritativo?**

| | Comportamento | Conseguenza |
| --- | --- | --- |
| **(A)** | il BE risolve **sempre** e scrive il suo valore | la scelta manuale sparisce **senza dirlo** — e `I6` diventa un no-op, ma per tre settimane l'operatore vede un campo che non serve a niente |
| **(B)** | il BE risolve **solo se il payload non porta `iva_id`** | l'override manuale resta vivo fino a `I6`, e `I6` diventa letteralmente «togli la chiave dalla whitelist» |

⭐ **Propendo per (B)**: è l'unica in cui la sequenza «`I3` poi `I6`» ha un senso —
se il valore manuale venisse già ignorato, `I6` non avrebbe niente da chiudere.

⚠️ **E si porta dietro una seconda domanda, sul `meta`.** Con (B), quando
l'operatore sovrascrive, `iva_origine` cosa dice? Il vocabolario del DB
(`ARTICOLO`, `TIPO_UTENZA`, `TITOLO`, `ASSENTE`) non ha un valore per «l'ha
scelto una persona». Proposta: risolvere **comunque** — così si sa sempre cosa
*avrebbe* detto il risolutore — e scrivere `iva_origine = 'MANUALE'` quando il
payload diverge, tenendo il resto. ⛔ `MANUALE` sarebbe un valore **nostro** nel
`meta`, non del vocabolario DB: la distinzione va scritta, o il prossimo lettore
lo cerca in `config`.

📌 Fino alla risposta, `F2-c` e `F2-d` restano ferme.

---

## 10-bis. ❓ La forma dell'anteprima — `F2-d`

I tre form hanno **tutti** l'id del proprio documento (`preventivoId`,
`ordineId`, `ddtId`, tutti `required`). Nessuno ha, in modo uniforme, il
contesto che il risolutore vuole.

| | Strada | Costo |
| --- | --- | --- |
| **(a)** | far scendere `billingAccountId` come prop | ⚠️ attraversa **due** livelli (`*RigheTable` → `*RigaForm`) in due domini, e le tabelle porterebbero un prop che non usano |
| **(c)** | l'endpoint accetta **le coordinate del documento** (`tipo` + `id`) e deriva BA, utility e data dalla testata | ⭐ nessun prop drilling, e soprattutto **il FE smette di dover sapere quali campi servono al risolutore** — che è precisamente la conoscenza che invecchia |

⭐ **Propendo per (c)**: è la stessa testata che il BE già legge al salvataggio,
quindi anteprima e salvataggio guardano **la stessa fonte** — ed è l'unico modo
di garantire per costruzione che mostrino lo stesso numero.

⚠️ Cambia l'endpoint appena scritto: i campi espliciti restano (diagnostica), si
aggiungono le coordinate. Non è una riscrittura, ma è la forma di `N2` che era
stata approvata come «calco di `pricing/resolve/`», e questo la allarga.

✅ **Scelta (c)** (Tid, 2026-08-31). Applicata: vedi §9.

