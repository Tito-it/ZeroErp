# Brief DB — Chiusura della ri-consegna: rendere DEFINITIVO un reso per ri-spedizione

> **Tipo**: brief operativo DB · **Target**: `dev/db-tid` · **Data**: 2026-07-25
> · **Owner**: Tid
> **Stato**: ✅ **SLICE CHIUSA END-TO-END** (2026-07-26) — DB (10 voci del §8) +
> **BE/FE** (§7, esito in §9-ter) + **seed lista 11**. Le quattro scelte di
> progetto sono chiuse in §5 (ok Tid 2026-07-25). Resta la **validazione in-app**,
> che richiede un reso per ri-consegna nuovo (in dev la coda è vuota).
> ⚠️ Il lavoro DB è applicato ma **non ancora pushato**.
>
> **Esito**: `20260726-01..11` applicati. pgTAP **20 test verdi** su due file —
> `test-resi-rinunce-fondamenta-v1` (11: tabella, helper, guard) e
> `test-resi-rinunce-scenario-v1` (9: madri, ordine → **EVASO**, accredito
> invariato con etichetta **DOVUTA**, round-trip). Non-regressione confermata
> dopo il refactor. Dettaglio in §9 e §9-bis.
> **Origine**: rilievo emerso validando la ri-spedizione su RESO0000150 /
> DDT0000338 — una ri-consegna parziale (o mai eseguita) lascia l'ordine
> **PARZIALMENTE_EVASO per sempre**, senza alcun modo in-app di chiuderla.
> **Contesto**: non siamo in produzione ([[project_no_produzione_solo_sviluppo]])
> → breaking secco, nessuna compat.

<!-- separatore riquadri rev -->

> ⚠️ **Revisione critica 2026-07-25 (verificata sul codice vivo).** Il problema è
> reale e il disegno di fondo è confermato (tabella speculare, rinuncia come
> dichiarazione che non muove numeri, reversibilità). Ma **due punti di
> implementazione erano sottostimati** e sono stati riscritti:
>
> 1. la scelta lasciata «da decidere in sede di scrittura» al §4.2 ha **una sola
>    risposta valida** — l'altra farebbe **sparire l'accredito dalla coda**,
>    contraddicendo il §3. Chiusa qui: §4.2.
> 2. «una riga sola nell'helper unico» è **falso**: la formula del residuo
>    ri-consegnabile è **già triplicata** oggi, e il §6 ne richiede l'effetto in
>    4 punti. Si estrae l'helper mancante: §4.2-bis.
>
> 3. il guard gemello `trgfn_resi_riconsegne_guard` **va esteso alle rinunce**,
>    altrimenti la ri-consegna può eccedere (`Σric + Σrin > quantita`): §4.6.
>    Non era previsto nel brief originale.
>
> Più due minori (§4.1-bis nome colonna e UNIQUE, §5.1 gate NC come `fn_check_*`
> dormiente). Dettaglio nei riquadri ⚠️ **[rev]**.
>
> **Autocorrezione**: la 1ª stesura di questa revisione proponeva un
> `pg_advisory_xact_lock` nelle madri; è stata **ritirata** — la serializzazione
> esiste già via `FOR UPDATE` nel guard del ponte, che è il pattern di casa e più
> robusto. Vedi §4.6.

---

## 1. Scopo in una riga

Dare all'operatore un modo di dichiarare che una quota di merce resa **per
ri-consegna non tornerà al cliente**: il residuo ordine si chiude (EVASO) e
l'accredito su quella quota passa da facoltativo a **dovuto**.

## 2. Il buco

`fn_genera_ddt_riconsegna` è ri-eseguibile e gestisce bene il parziale: ri-spedisci
3 su 10, la riga resta in coda con residuo 7 e generi un altro DDT quando serve.
Ma **non esiste l'uscita opposta**. Se quei 7 non torneranno mai al cliente:

- `fn_ordine_ha_residuo_evasione` continua a contarli (addendo
  `fn_ordine_riga_qta_riconsegna`, che somma le righe reso `riapre_residuo`)
  → l'ordine resta **PARZIALMENTE_EVASO** a vita;
- la riga resta nell'elenco ri-spedizione, indistinguibile da una lavorabile;
- in `vw_resi_da_accreditare` l'accredito resta etichettato **FACOLTATIVA**,
  quindi l'operatore che lavora le dovute non lo vede mai.

A DB la riga si chiuderebbe disattivandola (`resi_righe.attivo`), ma il drawer
non espone l'edit righe su un reso CONFERMATO — e disattivare sarebbe comunque
sbagliato: cancellerebbe il fatto che la merce **è** rientrata.

## 3. La scoperta che rende il fix piccolo

**L'accredito è già in coda, e già del valore giusto.** Verificato in
`vw_contatore_merce`: la CTE `res` somma `vw_resi_righe_effettive` **senza
filtro sul tipo** →

```text
tenuti = evaso − reso          (il reso è già sottratto, qualunque tipo)
differenza = tenuti − fatturati
coda accrediti = differenza < 0
```

Su ordine 10 / evaso 10 / fatturato 10 / reso 3 per ri-consegna: `tenuti = 7`,
`differenza = −3` → la riga **è già in `vw_resi_da_accreditare` con
`accredito_dovuto = 3`**, etichettata FACOLTATIVA. Se poi la ri-consegna
avviene, il fulfillment rialza `evaso` a 13 → `tenuti` torna 10 → `differenza 0`
→ la riga **esce da sola** dalla coda.

Conseguenza di progetto: **chiudere la ri-consegna non cambia nessun numero.**
Non tocca `tenuti`, non tocca l'importo dell'accredito, non crea documenti.
Cambia solo la **natura** della quota pendente: da «tornerà indietro» a
«definitiva». Il fix è quindi una dichiarazione, non un calcolo.

> ✅ **[rev] Verificato.** [vw_contatore_merce.md:14-18](../../dbzero/vendite/views/vw_contatore_merce.md#L14):
> la CTE `res` filtra **solo** `WHERE e.ordine_riga_id IS NOT NULL`, nessun
> filtro tipo. [vw_resi_da_accreditare.md:13-15](../../dbzero/vendite/views/vw_resi_da_accreditare.md#L13)
> legge `vw_contatore_merce WHERE differenza < 0`. Il §3 è corretto — **ed è
> proprio ciò che rende obbligatoria la scelta del §4.2.**

## 4. Proposta

### 4.1 Una tabella speculare al ponte delle ri-consegne

`vendite.resi_righe_rinunce` — gemella di `resi_righe_riconsegne`, che già
registra il lato consegnato:

| colonna | note |
| --- | --- |
| `resi_riga_id` | FK `vendite.resi_righe` |
| `qta` | unità **base**, coerente con `resi_righe_riconsegne.qta`; CHECK `> 0` |
| `note` | testo **facoltativo** (vedi §4.1-bis e §5.3) |
| audit | `data_insert`/`user_insert`/`tx_id`/… da policy, come la gemella |

**Perché una tabella e non una colonna** `qta_riconsegna_rinunciata` su
`resi_righe`: la rinuncia, come la ri-consegna, può essere **parziale e
ripetuta** (rinuncio a 3 oggi, ad altri 2 la settimana prossima). Una colonna
accumula il totale e perde chi/quando/perché di ogni evento; la tabella rende
la formula del residuo perfettamente simmetrica —

```text
residuo = quantita − Σ riconsegnate − Σ rinunciate
```

— e rende la **reversibilità** (§5.1) la cancellazione di una riga, non
un'aritmetica all'indietro.

Regge il **parziale** senza casi speciali: 3 già ri-consegnati, 7 rinunciati,
la storia di entrambi resta leggibile.

#### 4.1-bis Due dettagli della gemella da non copiare a occhi chiusi

> ⚠️ **[rev] Nome colonna: `note`, non `motivo`.** La gemella
> `resi_righe_riconsegne` usa **`note` varchar** nullable
> ([tabella:11](../../dbzero/vendite/tabelle/resi_righe_riconsegne.md#L11)).
> `resi_righe.motivo` esiste anch'esso (varchar nullable), quindi *entrambi* i
> precedenti esistono con nomi diversi. Si adotta **`note`**: la simmetria con
> la tabella gemella è l'argomento portante del §4.1, e va tenuta anche nel nome.

<!-- separatore riquadri rev -->

> ⚠️ **[rev] Nessuna UNIQUE è possibile — e va detto.** La gemella ha
> `uq_resi_riconsegne_pair (resi_riga_id, ddt_riga_id)`: la coppia esiste perché
> ogni ri-consegna punta a una riga DDT. La rinuncia **non ha un secondo
> termine**, quindi non c'è coppia da rendere unica; e una UNIQUE sul solo
> `resi_riga_id` **vieterebbe le rinunce ripetute**, che sono esattamente il
> caso d'uso del §4.1. Chi implementa «per simmetria» rischia di aggiungerla:
> non va aggiunta. L'unicità non serve — serve il guard di non-eccedenza (§4.6).

### 4.2 Dove sottrarre la quota rinunciata — decisione chiusa

> ⚠️ **[rev] Il brief originale lasciava la scelta «da decidere in sede di
> scrittura» fra sottrarre nell'helper o esporre la quota in
> `vw_resi_righe_effettive`, con «l'unico vincolo è che resti un solo punto».
> Le due opzioni NON sono equivalenti: la seconda annulla la funzionalità.**
>
> `vw_resi_righe_effettive` ha **sei consumatori** (`fn_conferma_reso`,
> `fn_annulla_reso`, `fn_ordine_riga_qta_riconsegna`, `vw_contatore_merce`,
> `vw_resi_da_accreditare`, più sé stessa), e `vw_contatore_merce` la somma
> **senza filtro tipo** (§3):
>
> | Dove sottrai | Residuo ordine | Accredito in coda |
> | --- | --- | --- |
> | **`fn_ordine_riga_qta_riconsegna`** (filtra `riapre_residuo`) | ✅ si chiude → EVASO | ✅ **invariato**, come promette §3 |
> | `vw_resi_righe_effettive` | ✅ si chiude | 🔴 `reso` scende → `tenuti` sale → `differenza` → 0 → **la riga ESCE dalla coda accrediti** |
>
> Nella seconda opzione §3 («non cambia nessun numero») e §4.4 (etichetta
> DOVUTA) diventano autocontraddittori: si etichetterebbe DOVUTA una riga che
> non è più in coda, e **l'accredito dovuto al cliente sparirebbe in silenzio**
> — il tipo esatto di perdita che la rifondazione a contatore doveva chiudere.

**Decisione: la sottrazione dell'addendo residuo ordine va in
`vendite.fn_ordine_riga_qta_riconsegna`, MAI in `vw_resi_righe_effettive`.**

```sql
-- fn_ordine_riga_qta_riconsegna: l'addendo reso scende della quota rinunciata
SELECT COALESCE(SUM(e.quantita - <Σ rinunce della riga>), 0) ...
```

Quella funzione è già dichiarata «single source per
`fn_ordine_ha_residuo_evasione` e `trgfn_ordini_ful_guard_consistenza`
(coerenza formula)». Sottraendo lì, il residuo si chiude **e** il guard
anti over-fulfillment resta coerente, senza toccare né l'uno né l'altro.
La vista `vw_resi_righe_effettive` **non si tocca**: resta il fatto grezzo
«questa merce è rientrata», che è vero indipendentemente dalla rinuncia.

### 4.2-bis Il residuo ri-consegnabile è già triplicato: estrarre l'helper mancante

> ⚠️ **[rev] «Una riga sola nell'helper unico» è falso.** La formula
> `quantita − Σ riconsegnate` esiste **oggi in tre implementazioni indipendenti**,
> e il §6 richiede l'effetto della rinuncia in **quattro** punti:
>
> | # | Dove | Formula attuale | Serve per (§6) |
> | --- | --- | --- | --- |
> | 1 | [vw_resi_da_riconsegnare.md:23,41-45](../../dbzero/vendite/views/vw_resi_da_riconsegnare.md#L23) | `rr.quantita - COALESCE(ric.tot,0)` (LEFT JOIN) | «riga fuori dall'elenco ri-spedizione» |
> | 2 | [fn_genera_ddt_riconsegna.md:102,118](../../dbzero/vendite/funzioni/fn_genera_ddt_riconsegna.md#L118) | `v_riga.qta_resa - v_riga.gia_ric` (subquery SUM) | «non deve poter ri-spedire la quota rinunciata» |
> | 3 | `fn_ordine_riga_qta_riconsegna` | addendo residuo ordine (§4.2) | «ordine EVASO» |
> | 4 | `vw_resi_da_accreditare` | — (da aggiungere) | etichetta DOVUTA quando non resta copertura (§4.4) |
>
> Il §4.2 originale («è **il** punto», «un solo punto di sottrazione») era quindi
> in contraddizione col §6 dello stesso brief.

**Poiché la formula è già triplicata *prima* di questo lavoro, non si aggiunge la
quarta copia: si estrae l'helper che manca.**

```sql
vendite.fn_resi_riga_residuo_riconsegna(p_resi_riga_id bigint) RETURNS numeric
  -- = resi_righe.quantita − Σ resi_righe_riconsegne.qta − Σ resi_righe_rinunce.qta
  -- STABLE, guard parametro (NULL o <=0 → errore parlante).
```

Consumato dai punti 1, 2 e 4; il punto 3 resta la sottrazione del §4.2 (è un
addendo diverso — residuo *ordine*, non residuo *ri-consegnabile*). È lo stesso
principio che il brief invoca per `fn_ordine_riga_qta_riconsegna` («se la
modifica si facesse altrove, le due formule divergerebbero»), applicato dove
serve davvero: costo marginale minimo, e **sana un debito preesistente** invece
di aggravarlo.

⚠️ Rifattorizzare i punti 1 e 2 sull'helper è una modifica a **codice funzionante
oggi**: i pgTAP esistenti su ri-consegna vanno rieseguiti come non-regressione
([[feedback_guard_breaks_existing_tests]]).

### 4.3 La funzione di chiusura

`vendite.fn_chiudi_riconsegna_reso(p_reso_id bigint, p_righe jsonb DEFAULT NULL)`
— speculare a `fn_genera_ddt_riconsegna`:

- guard: reso **CONFERMATO** (stesso gate della generazione,
  `E_RESO_NON_CONFERMATO` già in uso);
- `p_righe = NULL` → rinuncia a **tutta** la copertura residua; altrimenti
  `[{resi_riga_id, qta}]` con `LEAST(richiesta, residuo)`, stessa semantica
  race-proof della generazione;
- errore se non c'è nulla da chiudere (`E_RESO_NESSUNA_RICONSEGNA_PENDENTE`,
  **riuso** — verificato già a catalogo e già usato dalla gemella);
- **ri-proiezione stato ordine** in coda, identica allo step 7 della generazione
  (`PARZIALMENTE_EVASO` / `EVASO`) — è ciò che chiude l'ordine.

### 4.4 L'etichetta della coda accrediti

`vw_resi_da_accreditare.etichetta` oggi è `CASE WHEN riapre_residuo THEN
'FACOLTATIVA' ELSE 'DOVUTA'` ([righe 54-56](../../dbzero/vendite/views/vw_resi_da_accreditare.md#L54)).
Diventa **DOVUTA anche quando non resta copertura ri-consegnabile**: la merce non
torna, l'accredito non è più una scelta. In pratica:
`riapre_residuo AND fn_resi_riga_residuo_riconsegna(...) > 0` → FACOLTATIVA,
altrimenti DOVUTA. (Il caso «tutto ri-consegnato» non serve gestirlo qui: quelle
righe escono dalla coda da sole, §3.)

### 4.5 Perché NON cambiare il `tipo_reso` della riga

L'alternativa ovvia — flippare la riga da RESO_PER_RICONSEGNA ad A_CREDITO —
sembra più economica ma rompe il **parziale**: su 3 già ri-consegnati e 7
rinunciati, il flip toglie `riapre_residuo` all'intera riga, quindi i 3
fulfillment di ri-consegna già esistenti si ritrovano senza l'addendo che li
giustificava → `trgfn_ordini_ful_guard_consistenza` vede un over-fulfillment
retroattivo. E si perderebbe il fatto che quella merce era rientrata *per*
essere ri-consegnata.

> ✅ **[rev] Confermato.** `fn_ordine_riga_qta_riconsegna` filtra
> `e.riapre_residuo IS TRUE`: togliendo quel flag alla riga, il suo contributo
> al residuo svanisce mentre i fulfillment restano. Il §4.5 è corretto.

### 4.6 Guard di non-eccedenza — e il difetto che nasconde

> ⚠️ **[rev] AUTOCORREZIONE (2026-07-25, 2ª passata).** Una precedente stesura di
> questo §4.6 affermava che «`fn_genera_ddt_riconsegna` non ha alcun lock» e
> proponeva di aggiungere `pg_advisory_xact_lock` nelle madri. **Era fuorviante.**
> La madre non ha il lock, ma la serializzazione **c'è già** ed è nel guard
> trigger del ponte: `vendite.trgfn_resi_riconsegne_guard`
> ([doc:30-33](../../dbzero/vendite/funzioni/trgfn_resi_riconsegne_guard.md#L30))
> fa `PERFORM 1 FROM vendite.resi_righe WHERE id = NEW.resi_riga_id FOR UPDATE`
> **più** il lock del gruppo riconsegne. È il pattern di casa (mirror di
> `trgfn_ordini_ful_guard_consistenza`) e **è migliore** dell'advisory lock nella
> madre: protegge anche le scritture dirette sul ponte, non solo quelle che
> passano dalla funzione.
>
> **Nessun advisory lock va aggiunto.** Il guard nuovo sulle rinunce replica lo
> stesso `FOR UPDATE` su `resi_righe`: essendo la **stessa riga padre**, rinuncia
> e ri-consegna concorrenti si serializzano fra loro senza altro meccanismo.

<!-- separatore riquadri rev -->

> 🔴 **[rev] Il difetto vero: il guard gemello va ESTESO, o la ri-consegna può
> eccedere.** `trgfn_resi_riconsegne_guard` calcola oggi
> `v_residuo := v_qta_resa − v_gia_ric` ([doc:50-56](../../dbzero/vendite/funzioni/trgfn_resi_riconsegne_guard.md#L50)):
> somma **solo** le riconsegne. Introdotte le rinunce, su una riga da 10 con 7
> rinunciati quel guard vedrebbe ancora `residuo = 10` e lascerebbe ri-spedire 10
> → `Σric + Σrin = 17 > 10`, cioè esattamente l'invariante che il §6 pretende.
> **È una modifica obbligatoria, non opzionale**, e il brief originale non la
> prevedeva: la voce 6 del §8 la include.

Due presidi simmetrici, entrambi con `FOR UPDATE` su `resi_righe` (mai advisory):

- **Guard nuovo** su `resi_righe_rinunce` — mirror di
  `trgfn_resi_riconsegne_guard`: tipo `riapre_residuo` obbligatorio (riuso
  `E_RESO_RICONSEGNA_TIPO_NON_VALIDO`, id 533) e `Σric + Σrin ≤ quantita`
  (codice nuovo **`E_RESO_RINUNCIA_SUPERA_RESO`, id 560** — nome simmetrico a
  `E_RESO_RICONSEGNA_SUPERA_RESO` id 534, 559 è l'ultimo occupato).
- **Guard gemello esteso**: `v_residuo := v_qta_resa − v_gia_ric − v_gia_rin`.
  Entrambi diventano `quantita − Σric − Σrin`, cioè la stessa formula
  dell'helper §4.2-bis letta dai due lati.

## 5. Decisioni prese (ok Tid 2026-07-25)

### 5.1 Reversibile, con il gate NC progettato ma dormiente

`vendite.fn_riapri_riconsegna_reso(p_reso_id, p_righe)` simmetrica: cancella (o
disattiva) le rinunce e ri-proietta lo stato ordine, che torna
PARZIALMENTE_EVASO. Un errore di digitazione su un reso CONFERMATO deve avere
rimedio, come `fn_annulla_reso` lo dà alla conferma.

⚠️ Il gate corretto sarebbe «reversibile **finché la nota di credito non è
stata emessa**» — ma **il ramo NC non esiste ancora** (slice a sé; la coda
accrediti oggi la alimenta e basta). Quindi nessun gate NC oggi.

> ⚠️ **[rev] Il commento non basta come presidio.** Il brief lo lasciava «esplicito
> nel commento della funzione»: un commento non è un punto di innesto, e la slice
> NC dovrà *cercare* dove agire. Meglio una funzione pura **dormiente**:
> `script.fn_check_rinuncia_reversibile(p_resi_riga_id) RETURNS jsonb` che oggi
> ritorna sempre `[]`, consumata da `fn_riapri_riconsegna_reso` con il solito
> `IF jsonb_array_length(...) > 0 THEN raise`. Domani la slice NC riempie **una
> sola funzione** e il gate si attiva da sé, senza toccare la madre. Stesso
> pattern di `fn_check_commessa_chiudibile` (brief guard-uscita §3.2), costo oggi
> ~10 righe. Coerente con [[feedback_concentrico_no_yagni]]: il guard si progetta
> per l'espansione, non si rinvia.

### 5.2 Audit: la tabella (§4.1), non la colonna

Decisa contestualmente alla struttura: rinunce parziali e ripetute, ognuna con
il suo chi/quando/perché, e reversibilità come cancellazione di riga.

### 5.3 Motivo facoltativo

Testo libero **nullable** (colonna `note`, §4.1-bis): la stessa forma della
gemella e di `resi_righe.motivo`. Obbligatorio no — sarebbe attrito su ogni
chiusura, e il caso «il cliente non lo rivuole» è la norma, non l'eccezione da
giustificare. Quando la slice NC avrà bisogno di una classificazione contabile,
diventerà un lookup: il campo c'è già e si stringe, mentre partire da un enum
inventato oggi vincolerebbe a codici mai validati sul campo.

### 5.4 Merce fisica: fuori perimetro, ma dichiarato

La quota rinunciata resta materialmente al fornitore. Senza modulo magazzino non
c'è nulla da movimentare, ma **va scritto nel `COMMENT ON FUNCTION`**: è
esattamente il tipo di conseguenza che sparisce dalla memoria del progetto e
riemerge come sorpresa quando il magazzino arriverà.

## 6. Verifica attesa

- Reso CONFERMATO con 10 resi per ri-consegna, 0 ri-spediti → `fn_chiudi_riconsegna_reso`
  senza righe → ordine passa a **EVASO**, riga fuori dall'elenco ri-spedizione,
  accredito in coda con etichetta **DOVUTA** e importo **invariato**.
- Parziale: 3 ri-spediti + 7 chiusi → ordine **EVASO**, `accredito_dovuto` invariato,
  nessun errore da `trgfn_ordini_ful_guard_consistenza`.
- Non-regressione: dopo una chiusura parziale, `fn_genera_ddt_riconsegna` sulla
  stessa riga **non** deve poter ri-spedire la quota rinunciata (il residuo la
  esclude → `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`).
- **Reversibilità**: `fn_riapri_riconsegna_reso` sulla stessa riga → l'ordine
  torna PARZIALMENTE_EVASO, la riga ricompare in elenco ri-spedizione, l'etichetta
  in coda torna FACOLTATIVA. Round-trip chiudi→riapri = stato iniziale.
- pgTAP: la formula del residuo resta identica fra `fn_ordine_ha_residuo_evasione`
  e `trgfn_ordini_ful_guard_consistenza` (è l'invariante che l'helper unico esiste
  per proteggere), **e la simmetria** `quantita − Σ riconsegnate − Σ rinunciate`
  non va mai negativa (over-rinuncia rifiutata come l'over-ri-spedizione).

> ⚠️ **[rev] Da aggiungere alla verifica:**
>
> - **L'accredito NON deve cambiare** — è la promessa del §3 e il discrimine
>   della decisione §4.2. Asserire `accredito_dovuto` **identico** prima e dopo la
>   chiusura, e che la riga **resti** in `vw_resi_da_accreditare`. Se sparisce, la
>   sottrazione è finita nel posto sbagliato.
> - **Non-regressione dei 3 punti rifattorizzati** (§4.2-bis): i pgTAP esistenti
>   su ri-consegna/contatore devono restare verdi senza adattamenti.
>   Grep preventivo: `grep -rln "riconsegna\|resi_da_riconsegnare" db/pgtap/`.
> - **Over-rinuncia in concorrenza** (§4.6): strutturale (`pg_get_functiondef`
>   contiene `pg_advisory_xact_lock` in entrambe le madri) + comportamentale sul
>   guard `E_RESO_RINUNCIA_ECCEDE_RESIDUO`. La serializzazione vera non è
>   riproducibile in pgTAP mono-sessione: prova manuale a 2 sessioni psql.

## 7. BE/FE a valle (dopo l'apply, non prima)

- Endpoint speculari a `genera-riconsegna`: POST `/vendite/resi/{id}/chiudi-riconsegna/`
  e POST `/vendite/resi/{id}/riapri-riconsegna/` (§5.1), con le policy dei codici
  errore nuovi in `error_policies.py` (incluso **560** → 409, conflitto di stato).
- FE: **stessa dialog** «DDT ri-spedizione» (`ResoRiconsegnaDialog`), stessa lista e
  stessa selezione, secondo esito nel footer — «Genera DDT» / «Rendi definitivo il
  reso». Due uscite della stessa attività in un posto solo, invece di una seconda
  dialog gemella. Conferma esplicita sul significato: *la merce non tornerà al
  cliente e l'accredito diventa dovuto*. Le righe già rinunciate restano visibili
  in elenco come consuntivo (colonna «rinunciata» accanto a «ri-consegnata»), con
  l'azione di riapertura sul kebab riga.
- La nota i18n `vendite.resi.riconsegna_nota_parziale` — già in app, spiega che il
  parziale non perde il resto — andrà estesa: il resto si può anche **chiudere**,
  non solo ri-spedire più tardi.

## 8. Riepilogo del lavoro DB (numerazione: `20260725-01..`, libera)

| # | Oggetto | Tipo |
| --- | --- | --- |
| 1 | ✅ `messaggi_errore.csv`: `E_RESO_RINUNCIA_SUPERA_RESO` **id 560** | append CSV, nessun loader nuovo |
| 2 | ✅ `vendite.resi_righe_rinunce` (§4.1) + trigger audit/tx_id come la gemella | `00_schema` |
| 3 | ✅ `vendite.fn_resi_riga_residuo_riconsegna` (§4.2-bis) | `20_code`, nuova |
| 4 | ✅ Guard non-eccedenza su `resi_righe_rinunce` (§4.6) | `20_code`, trigger |
| 5 | ✅ `fn_ordine_riga_qta_riconsegna`: sottrae le rinunce (§4.2) | `20_code`, `CREATE OR REPLACE` |
| 6 | ✅ `vw_resi_da_riconsegnare` + `fn_genera_ddt_riconsegna` sull'helper (§4.2-bis) **+ `trgfn_resi_riconsegne_guard` esteso alle rinunce** (§4.6, obbligatorio) | `20_code`, refactor |
| 7 | ✅ `vw_resi_da_accreditare`: etichetta (§4.4) | `20_code` |
| 8 | ✅ `script.fn_check_rinuncia_reversibile` dormiente (§5.1) | `20_code`, nuova |
| 9 | ✅ `fn_chiudi_riconsegna_reso` + `fn_riapri_riconsegna_reso` (§4.3, §5.1) | `20_code`, madri |
| 10 | ✅ pgTAP fondamenta (11) + scenario (9) + non-regressione (§6) | `db/pgtap/vendite/` |

⚠️ **Ordine vincolante**: 3 e 4 prima di 5/6/7 (che li consumano); 2 prima di
tutto; 9 per ultimo. `RETURNS TABLE`/viste → `DROP` + ricreazione dove il tipo di
ritorno cambia ([[feedback_pg_returns_table_drop_required]]); firma e `RETURNS`
dall'**ultimo YAML**, corpo dalla doc auto-gen ([[feedback_autogen_firma_perde_type]]);
apostrofi raddoppiati nei letterali `COMMENT ... IS '...'`.

## 9. Esito Fase 1 — fondamenta (2026-07-26)

**Applicata e verificata sul DB.** Voci 1-4 del §8.

| Consegna | Esito |
| --- | --- |
| `messaggi_errore.csv`: `E_RESO_RINUNCIA_SUPERA_RESO` **560** | ✅ append, caricato dal loader `runOnChange` |
| `00_schema/.../20260726-01-create-resi-righe-rinunce` | ✅ applicato |
| `20_code/.../20260726-03-create-fn-resi-riga-residuo-riconsegna` | ✅ applicato |
| `20_code/.../20260726-04-create-trgfn-resi-rinunce-guard` (+ gemello esteso) | ✅ applicato, `gemello_esteso = true` verificato su `pg_get_functiondef` |
| `80_data/.../20260726-02-upsert-dbops-fk-index-policy-resi-righe-rinunce` | ✅ `ix_resi_rinunce_resi_riga_id` creato dalla policy opt-in |
| `db/pgtap/vendite/test-resi-rinunce-fondamenta-v1.sql` | ✅ **11/11 PASS** |

### Il test che vale più degli altri

Il **test 8** distingue il guard esteso da quello vecchio: su una riga da 3 con
1 ri-consegnato e 1 rinunciato, una ri-spedizione di 2 viene **rifiutata**
(residuo effettivo 1). Col guard gemello non esteso il calcolo sarebbe `3 − 1 = 2`
e **sarebbe passata**, portando `Σric + Σrin = 4 > 3`. È la prova che il rilievo
§4.6 era fondato e la correzione efficace.

### Note di stesura emerse dai dati reali

- **Base 3, non 10**: la capienza di reso disponibile sui DDT consegnati di dev
  è al massimo 3 (`trgfn_resi_righe_guard_quantita` limita il reso a
  `consegnato − già reso`). L'aritmetica dei test è scalata; il discriminante
  regge identico. Il fixture ha una **precondizione esplicita** (test 6-bis) che
  fallisce in modo leggibile se i dati non bastassero.
- **`qta_operativa`, non `quantita`**, nell'INSERT di `resi_righe`: il trigger
  `qta_from_operativa` calcola la base ([[feedback_pgtap_eccezioni_fissa_qta_operativa]]).
- Il reso del fixture resta in **DRAFT**: i guard dei ponti non filtrano lo stato
  del reso, l'invariante di copertura vale comunque. La conferma è materia della
  madre (Fase 2).

### Non-regressione

`test-vw-contatore-merce-v1`, `test-vw-resi-da-accreditare-contatore-v1` e
`test-fn-list-ddt-da-pushare-contatore-v1` risultano **rossi**, ma per una causa
**preesistente e scollegata**: il guard sorgente polimorfa
(`atteso uuid, ricevuto SRC-...`, 2026-07-18) — nessuno dei tre file è stato
toccato da questa slice (verificato con `git status`). Sono fra i ~60 rossi noti
in attesa di bonifica fixture.

## 9-bis. Esito Fase 2 — madri e refactor (2026-07-26)

**Scritta e validata in transazione `ROLLBACK`, NON ancora applicata.**
Voci 5-9 del §8. Changeset `20260726-05..11` (7 file).

| # | Changeset | Contenuto |
| --- | --- | --- |
| 5 | `20260726-05-update-fn-ordine-riga-qta-riconsegna-rinunce` | l'addendo reso sottrae le rinunce → **è il punto che chiude l'ordine** |
| 6a | `20260726-06-update-vw-resi-da-riconsegnare-rinunce` | residuo dall'helper + colonna `qta_rinunciata` + stato `RINUNCIATA` |
| 6b | `20260726-07-update-fn-genera-ddt-riconsegna-helper` | la madre ri-spedizione legge l'helper: non ri-spedisce la quota rinunciata |
| 7 | `20260726-08-update-vw-resi-da-accreditare-etichetta` | `FACOLTATIVA` solo se resta copertura, altrimenti `DOVUTA` |
| 8 | `20260726-09-create-fn-check-rinuncia-reversibile` | gate NC **dormiente** (punto di innesto cablato) |
| 9a | `20260726-10-create-fn-chiudi-riconsegna-reso` | madre chiusura |
| 9b | `20260726-11-create-fn-riapri-riconsegna-reso` | madre riapertura, LIFO sulle rinunce |

### Scenario provato end-to-end (probe in rollback, fixture order-backed costruito)

| Passo | Esito |
| --- | --- |
| chiusura con `p_righe = NULL` | ✅ 1 riga chiusa |
| residuo dopo la chiusura | ✅ **0** |
| riga nell'elenco ri-spedizione | ✅ **assente** |
| **stato ordine** | ✅ `PARZIALMENTE_EVASO` → **`EVASO`** ← il buco del §2 è chiuso |
| ri-spedizione della quota rinunciata | ✅ **rifiutata** |
| riapertura → residuo | ✅ torna a **2** (valore iniziale) |
| riapertura → elenco | ✅ riga **ripresente** |
| riapertura → stato ordine | ✅ torna **`PARZIALMENTE_EVASO`** |

Il **round-trip chiudi → riapri = stato iniziale** richiesto dal §6 è verificato.

### ✅ Voce 10 — pgTAP di scenario: FATTO e VERDE (2026-07-26)

`db/pgtap/vendite/test-resi-rinunce-scenario-v1.sql`, **9/9 PASS**. Copre le
**madri** e le loro conseguenze, complementare a `test-resi-rinunce-fondamenta-v1`
(tabella, helper, guard).

**Il buco di verifica del probe è chiuso.** L'accredito ora è esercitato per
davvero: test 3 (etichetta `FACOLTATIVA` in partenza), **test 6** — la riga resta
**in coda** con l'importo **identico** e l'etichetta passa a `DOVUTA` — e test 9
(round-trip: etichetta torna `FACOLTATIVA`, importo sempre lo stesso). È la
verifica sperimentale della decisione §4.2: se la sottrazione delle rinunce
finisse in `vw_resi_righe_effettive`, la riga **uscirebbe** dalla coda e il test 6
diventerebbe rosso.

Come è stato reso possibile: `fatturati` in `vw_contatore_merce` **non guarda
`fattura_riga_id`** — somma le `attivita_fatturabili` NORMALE con `segment_key`
`DDT:<uid>:R:<id>` ricondotte alla riga ordine via fulfillment. Quindi non serve
una fattura vera: bastano commessa + `commessa_attivita` con quel segment + AF.
Il probe manuale aveva fallito la verifica solo perché il suo fixture non aveva
quella catena.

Copertura: madri presenti (1), stato iniziale (2-3), chiusura ed effetti (4-6),
non-regressione della ri-spedizione (7), round-trip (8-9).

⚠️ **Nota di stesura**: il test 8 inizialmente falliva per un errore del test, non
del codice — la funzione che *scrive* (`fn_riapri_riconsegna_reso`) stava dentro un
`AND` insieme alle letture che ne dipendono, e PostgreSQL **non garantisce
l'ordine di valutazione**. La riapertura ora si esegue in isolamento e poi si
asserisce. Vale come promemoria per i test futuri sulle madri.

### Correzione fatta strada facendo

`E_VALIDAZIONE`, copiato dalla gemella `fn_genera_ddt_riconsegna`, **non è a
catalogo**: usciva come `[MESSAGGIO NON DEFINITO]`. Le due madri nuove usano
`E_PARAMETRO_INVALIDO` (standard AGENTS.md, già a catalogo). ⚠️ La gemella
**conserva il difetto**: `fn_genera_ddt_riconsegna` e altre funzioni resi
sollevano ancora `E_VALIDAZIONE` con messaggio non definito. Non corretto qui
(fuori perimetro, tocca funzioni non in slice) ma **da sanare**: o si registra il
codice, o si uniformano a `E_PARAMETRO_INVALIDO`.

### Non-regressione (baseline pre-refactor registrata)

Baseline *prima* del refactor: `test-resi-motore-v1` 27 PASS,
`test-vw-dash-fatturazione-ordini-residuo-v1` 6 PASS,
`test-resi-rinunce-fondamenta-v1` 11 PASS. `test-vw-dash-backlog-resi-v1` era
**già rosso** prima (guard sorgente polimorfa).

✅ **Rieseguita DOPO l'apply della Fase 2 (2026-07-26): tutti confermati PASS**
con gli stessi conteggi. Il refactor delle voci 6a/6b — che tocca codice
funzionante — non ha regredito nulla.

⚠️ **Debito noto e scollegato**: i rossi per guard sorgente polimorfa hanno ora
un brief dedicato — [brief-db-bonifica-pgtap-sorgente-polimorfa.md](brief-db-bonifica-pgtap-sorgente-polimorfa.md).

## 9-ter. Esito BE/FE (2026-07-26) — §7 realizzato

**BE**: `resi_repository` — `chiudi_riconsegna`/`riapri_riconsegna` (madri),
`qta_rinunciata` nella whitelist `order_cols` della coda, e soprattutto
**`list_righe` ripuntata su `fn_resi_riga_residuo_riconsegna`**: era la
**QUARTA copia** della formula del residuo (§4.2-bis ne censiva tre a DB, questa
viveva nel BE) ed era diventata **sbagliata** con le rinunce — non le sottraeva,
quindi la dialog avrebbe proposto come ri-spedibile una quota già dichiarata
definitiva. Ora il residuo lo dice solo l'helper, e `stato_riconsegna` replica
1:1 la `CASE` della vista (incluso `RINUNCIATA`). `resi_service` —
`chiudi_riconsegna`/`riapri_riconsegna` con la stessa validazione righe della
gemella (degeneri → 400, mai degrado a «rendi definitivo tutto») e `note`
normalizzate a NULL. `views_resi`/`urls_resi` — i due endpoint;
`error_policies` — **560** `E_RESO_RINUNCIA_SUPERA_RESO` → 409 banner.

**FE**: `ResoRiconsegnaDialog` con **footer a due esiti** sulla stessa lista e
sulla stessa selezione — «Rendi definitivo il reso» (warn outlined, conseguenza
contabile) e «Genera DDT» (percorso normale, ultima posizione) — colonna
«Definitiva» accanto a «Ri-consegnata», e **riapertura** sul kebab delle sole
righe con rinuncia. Lo store notifica anche `ORDINE`: il suo stato cambia come
effetto collaterale (→ EVASO) ed è il caso che il refresh KeepAlive delle liste
deve cogliere.

**Verificato**: `list_righe` sul DB vivo (RESO0000150: riga COMPLETATA, residuo
0 dall'helper); traduzione errore reale `E_RESO_NESSUNA_RICONSEGNA_PENDENTE`;
payload degeneri rifiutati. Suite `apps.vendite`+`apps.core` **1961 verdi**,
build Vite verde, lint pulito, `kill -HUP` gunicorn.

### ✅ Seed lista 11 — applicato dal team DB (2026-07-26)

La colonna `qta_rinunciata` è ora nella config della lista
`vendite.resi_da_riconsegnare`: **id 204, etichetta «Definitiva», ordine 75** —
fra `qta_riconsegnata` (70) e `qta_residua` (80), così le due uscite della
copertura si leggono affiancate prima del residuo. Verificato sul DB vivo.
⚠️ Applicato al DB ma **non ancora pushato** (changelog sul branch del team DB).

Il seed referenzia `vendite.resi_da_riconsegnare.col_rinunciata`: la chiave
i18n **mancava** ed è stata aggiunta (it «Definitiva» / en «Final») — senza,
l'intestazione della colonna sarebbe uscita grezza in lista.

**Con questo la slice è chiusa end-to-end: DB, BE, FE, seed.** Resta solo la
validazione in-app, che richiede un reso per ri-consegna nuovo (in dev
`vw_resi_da_riconsegnare` è vuota — vedi §9-ter).

Rilievo minore ancora aperto, non bloccante: il ramo `RINUNCIATA` della `CASE`
è irraggiungibile *nella vista* (la `WHERE` filtra residuo > 0), mentre è vivo e
usato in `ResiRepository.list_righe` per il consuntivo nella dialog.

## 10. Riferimenti

- Helper unico residuo ordine: [fn_ordine_riga_qta_riconsegna](../../dbzero/vendite/funzioni/fn_ordine_riga_qta_riconsegna.md)
- Gemella: [resi_righe_riconsegne](../../dbzero/vendite/tabelle/resi_righe_riconsegne.md)
  · madre: [fn_genera_ddt_riconsegna](../../dbzero/vendite/funzioni/fn_genera_ddt_riconsegna.md)
- Elenco ri-spedizione: [vw_resi_da_riconsegnare](../../dbzero/vendite/views/vw_resi_da_riconsegnare.md)
- Contatore e coda: [vw_contatore_merce](../../dbzero/vendite/views/vw_contatore_merce.md)
  · [vw_resi_da_accreditare](../../dbzero/vendite/views/vw_resi_da_accreditare.md)
  · [vw_resi_righe_effettive](../../dbzero/vendite/views/vw_resi_righe_effettive.md)
