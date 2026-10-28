# Brief BE → DB — l'emittibilità della commessa: renderla visibile e sbloccabile

**Chi scrive:** BE (`dev/backend-tid`), 2026-08-04.
**A chi:** team DB (`dev/db-tid`).
**Cos'è:** 15 attività di giugno stanno nella card «Da emettere» della dashboard
competenza e **non sono fatturabili da nessun verbo**, perché la loro commessa è
rimasta in `BOZZA`. La lista promette un lavoro che il motore non può fare, e
dall'interfaccia non esiste modo di sbloccarla.
**Decisione presa da Tid** (2026-08-04): i dati sporchi non sono il problema
(siamo in test) — **è un buco di modello e va chiuso**. E le attività bloccate
vanno **segnalate, non nascoste**: sono lavoro reale.

> ✅ **CANTIERE CHIUSO — 2026-08-16, dichiarato da Tid.** Documento spostato in
> `work-done/`. Le richieste originali (§3), le due nuove del §8, le quattro
> emerse lavorando e la domanda del §10.6 sono tutte chiuse: **dieci changeSet**
> (`20260815-24` … `-32`, `-36`), migrati e verificati, pgTAP verdi, baseline
> `vendite` senza regressioni, e il giro provato a video.
>
> ~~⚠️ **Una cosa esce dal cantiere ancora da fare, e va detta qui perché non si
> perda**: il §11.4 — il BE deve **consumare `terne_pronte`**.~~
> ✅ **CONSUMATA il 2026-08-16**, il giorno dopo: il BE legge `terne_pronte`, la
> incrocia con le terne fallite del giro (che aveva già negli esiti come fatti) e
> distingue «bloccato dal perimetro» da «l'esecuzione si è rotta, si rilancia».
> La soppressione è **per gruppo** come il §11.4 punto 3 pretendeva. Consuntivo
> nel **§12**. Il residuo è durato meno del documento che lo dichiarava.
>
> ---
>
> 📌 **Stato al 2026-08-15, notte** (rimisurato, non riferito). Tutte le richieste
> originali (§3) sono chiuse, DB e video. Chiuse in giornata, in ordine: le sei
> decisioni R1 del §7.3 (cantiere vie d'uscita), il verbo «Rendi pronta» (§6),
> **`gruppi_coperti`** (`20260815-02`, §5), e nel pomeriggio la **segnalazione
> della riga bloccata in dashboard** più l'**adozione BE/FE di `gruppi_coperti`**:
> lucchetto+sblocco in lista, emissione parziale parlante (§6, §7.5, consuntivo
> nel **§8.1**).
>
> 🟢 **DB CHIUSO** — le due richieste nuove del §8 sono fatte, migrate e
> verificate: il **consuntivo** del servito (§8.2) e la **descrizione** dello
> stato commessa nelle due viste (§8.3). La risposta DB, con l'analisi critica,
> il piano e le misure, è il **§9**.
>
> Lavorando sono emerse **quattro cose che il §8 non nominava**, tutte chiuse
> nello stesso giro: `documento_id` risolto due volte, `diagnostica_gruppi` come
> ultima copia della regola di emittibilità fuori dal DB, un `CHECK` mai
> validato, e il tetto della discovery che troncava una richiesta mirata in
> silenzio. Nove changeSet in tutto (`20260815-24` … `-32`).
>
> 🟢 **BE/FE CHIUSO** — le cinque richieste del §9.7 sono fatte e verificate:
> consuntivo al posto della previsione, i due JOIN tolti dal repository,
> diagnostica scesa a DB, docstring riallineata, policy del codice nuovo.
> Piano e consuntivo nel **§10**.
>
> **Cosa restava, e com'è finita:**
>
> - ~~🔴 la **prova in app di Tid** (§8.4)~~ ✅ **chiusa il 2026-08-16**;
> - ~~🟠 **una domanda al DB, aperta**: nel giro parziale una terna FALLITA viene
>   diagnosticata come problema di perimetro — **§10.6**.~~
>   ✅ **RISPOSTA DATA il 2026-08-16, §11**: la corsia non si prevede, si
>   **misura** — `terne_pronte` sulla diagnostica (`20260815-36`). Incrociata con
>   le terne fallite, che avete già negli esiti come fatti, distingue «perimetro»
>   da «esecuzione rotta» senza rimettere in gioco `gruppi_coperti`.
>   ~~Resta da **consumarla lato BE**: §11.4.~~ ✅ **consumata il 2026-08-16** — §12.
>
> 🟢 **CANTIERE CHIUSO (2026-08-16, sera).** La **prova in app è stata eseguita con
> successo** su una commessa reale: lucchetto → sblocca → rendi pronta → fattura,
> il giro si chiude (**§12.6**). La prova ha trovato un difetto che nessuna review
> aveva visto — «Sblocca commessa» portava a un drawer dove il verbo era nascosto
> a chi non ha `cambia_stato_commessa`: una via d'uscita promessa e non mantenuta,
> **corretta lo stesso giorno**.
>
> ✅ **Deciso da Tid nella stessa giornata**: `rendi_pronta` **resta** gattato col
> permesso delle azioni terminali — sbloccare una commessa è governo, non un
> gesto operativo, e chi fattura passa da chi governa (**§12.7**).
>
> **Nessun residuo aperto.** Il cantiere è chiuso per intero: DB, BE/FE, prova in
> app e decisioni. Chi cerca «cosa resta» qui non trova niente, ed è corretto.

**Correlati:**
[vw_dash_competenza_attivita](/dbzero/vendite/views/vw_dash_competenza_attivita) ·
[vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi) ·
[fn_list_emittibili_lane](/dbzero/vendite/funzioni/fn_list_emittibili_lane) ·
[transizioni_stati_commessa](/dbzero/vendite/tabelle/transizioni_stati_commessa) ·
[fn_available_actions_commessa](/dbzero/script/funzioni/fn_available_actions_commessa)

---

## 1. Il fatto, misurato

Tid ha chiesto l'emissione mirata sul gruppo
`ORDINE_VENDITA:019eb2ac-3058-704a-91ee-e15247e85145`, competenza giugno 2026.
Il job **141** è finito `FATTO`, con `lane: 0`, `lotti: []`, `falliti: 0`,
`per_motivo: {}`. Nessun errore, nessuna fattura.

La riga c'era ed era a posto:

| | |
| --- | --- |
| `commesse_attivita` 69 | `NON_EMESSA` + `APPROVATA`, `tipo_doc_fiscale_id = 1`, competenza `2026-06-01` |
| commessa 108 (`CMM-20260610175449872-e059eb`) | stato **`BOZZA`** → `stati_commessa.emittibile = **false**` |

`fn_list_emittibili_lane` richiede `sc.emittibile = true`: nessuna terna, nessun
lotto. Corretto, e completamente muto.

**Non è un caso isolato** (query sul DB di sviluppo):

| Stato commessa | `emittibile` | Commesse | Attività pronte | Competenze |
| --- | :---: | ---: | ---: | --- |
| `BOZZA` | false | **5** | **15** | giugno 2026 |
| `PRONTA_FATTURAZIONE` | true | 3 | 38 | giugno → agosto 2026 |

Sono le commesse 66, 103, 104, 107, 108, create fra il 5 e il 10 giugno. La
causa è databile: il ponte `_rendi_commessa_emittibile` — che dopo un push
riuscito approva le righe e porta la testata a `PRONTA_FATTURAZIONE` — è entrato
col commit `09df3dd35` **il 10 giugno**. Quelle commesse nascono da push
precedenti. È pregresso, non un difetto attivo del ponte.

---

## 2. I due buchi

### 2.1 La dashboard e il motore non applicano lo stesso filtro

`vw_dash_competenza_attivita` esclude solo le commesse `ANNULLATA`:

```sql
WHERE ... AND (sc.codice_interno)::text <> 'ANNULLATA'::text
  AND (ca.stato_emissione)::text <> 'ANNULLATA'::text
  AND (((ca.stato_approvazione)::text <> 'RIFIUTATA') OR (ca.stato_emissione = 'EMESSA'))
```

Nessun riferimento a `sc.emittibile`, che è invece il criterio della discovery.
Lo stadio `DA_EMETTERE` guarda solo la riga (`stato_emissione <> 'EMESSA'`), mai
la testata. Quindi la card mostra come emettibile ciò che non lo è.

### 2.2 Una commessa bloccata non ha via d'uscita

La transizione esiste ed è attiva, ma è dichiarata **non manuale**:

| da | a | `meta` |
| --- | --- | --- |
| `BOZZA` | `PRONTA_FATTURAZIONE` | `{"manuale": false}` |
| `APERTA` | `PRONTA_FATTURAZIONE` | `{"manuale": false}` |
| `IN_ESECUZIONE` | `PRONTA_FATTURAZIONE` | `{"manuale": false}` |

Risultato su `script.fn_available_actions_commessa(108)`:

```json
{"stato_codice": "BOZZA", "is_emittibile": false, "can_change_state": true,
 "available_actions": [{"key": "annulla", "target_state": "ANNULLATA", ...}]}
```

**Una sola azione: annullare.** Se il ponte automatico non scatta — push
fallito, dato caricato per altra via, o come qui una commessa più vecchia del
ponte — la commessa resta bloccata per sempre e l'unica uscita offerta è
distruggere il lavoro. Questo è il buco di modello.

---

## 3. Cosa chiediamo

### 3.1 🔴 La vista espone l'emittibilità della testata

Una colonna in `vw_dash_competenza_attivita`, propagata poi in
`vw_dash_competenza_gruppi` (dove entra nella `GROUP BY` insieme al gruppo, o
come `bool_and`/`bool_or` secondo la vostra preferenza):

| Colonna | Tipo | Da |
| --- | --- | --- |
| `commessa_emittibile` | `boolean` | `stati_commessa.emittibile` della testata |

**Segnalare, non nascondere** (decisione Tid): quelle 15 attività sono lavoro
reale e toglierle dalla card le renderebbe invisibili invece che bloccate. Col
flag, la lista marca la riga e ne spiega il motivo, e il verbo «Fattura questo»
può nascere già disabilitato invece di partire e non fare nulla.

Se preferite esporre lo `stato_commessa` (testo) al posto del solo booleano,
per noi va bene: ci serve poter dire *perché* è bloccata, non solo *che* lo è.

### 3.2 🔴 `BOZZA|APERTA|IN_ESECUZIONE → PRONTA_FATTURAZIONE` diventi manuale

Nel seed di `transizioni_stati_commessa`, `meta` con la stessa forma delle altre
azioni manuali (è il contratto che `fn_available_actions_commessa` già legge):

```jsonc
{
  "manuale":  true,
  "action_key": "rendi_pronta",
  "label_key":  "vendite.commesse.azione_rendi_pronta",
  "severity":   "success",
  "icon":       "pi pi-check-circle",
  "requires_confirm": true
}
```

Il ponte automatico **resta**: questa è la via di servizio per quando non
scatta, non un'alternativa al processo.

### 3.3 🟠 Un check che eviti di sostituire un buco con un altro

Rendere manuale la transizione senza guard permetterebbe di portare «pronta» una
commessa senza nulla di approvato — e il verbo di fatturazione fallirebbe di
nuovo, solo un passo più in là. Chiediamo la funzione pura, sul modello di
`fn_check_commessa_chiudibile` / `_annullabile` che avete già scritto il
2026-07-24:

```text
script.fn_check_commessa_pronta_fatturazione(p_commessa_id) → jsonb  -- [] = lecito
```

Verdetto su: almeno una riga `APPROVATA` + `NON_EMESSA` con
`tipo_doc_fiscale_id NOT NULL`; commessa con emittente e utility valorizzati.
Usata **sia** da `fn_available_actions_commessa` (per `enabled` + `reasons`)
**sia** dal guard di transizione — una sola sede, come per le sorelle.

La composizione esatta dei motivi decidetela voi: il vincolo che ci interessa è
che il bottone e il guard leggano **lo stesso** verdetto.

### 3.4 🟢 pgTAP

| # | Scenario | Atteso |
| --- | --- | --- |
| 1 | Commessa `BOZZA` con righe approvate | `available_actions` contiene `rendi_pronta` **abilitata** |
| 2 | Commessa `BOZZA` senza righe approvate | `rendi_pronta` presente ma `enabled: false` + motivo |
| 3 | Transizione eseguita al netto del check | commessa `PRONTA_FATTURAZIONE`, `emittibile = true` |
| 4 | Guard e capability sullo stesso caso | **stesso verdetto** (nessuna divergenza) |
| 5 | Vista: commessa `BOZZA` con righe da emettere | riga presente con `commessa_emittibile = false` |

---

## 4. Cosa NON chiediamo

- **Nessuna correzione dei 5 dati di giugno**: sono di test, e una volta esposto
  il verbo si sbloccano dall'interfaccia. Se preferite comunque una migrazione
  dati, per noi è indifferente — ma non serve a chiudere il buco.
- **Nessun nuovo stato**: la transizione esiste già, cambia solo la sua
  dichiarazione a dato.
- **Nessuna modifica al ponte automatico** post-push: funziona, e resta la via
  normale.

---

## 5. Cosa abbiamo già fatto noi (BE), oggi

Il silenzio del giro mirato era la metà nostra del problema, ed è **chiusa**
(commit sul ramo BE, suite 3526 verdi):

1. Un'emissione mirata che non produce **nemmeno un lotto** ora **fallisce** con
   `E_FATTURAZIONE_GIRO_NESSUN_LOTTO` invece di registrare `FATTO`. Il perimetro
   mirato è **nominale**: «zero lotti su N gruppi chiesti» è una richiesta non
   soddisfatta, non un giro senza lavoro. Il giro di **massa** a vuoto resta un
   successo — lì «questo mese non c'era nulla» è legittimo, e il cron lo produce
   di routine.
2. Il messaggio dice **perché**, per ciascun gruppo. Sul caso di Tid:

   > *Nessun lotto prodotto: il gruppo richiesto non è fatturabile.
   > CMM-20260610175449872-e059eb: la commessa è in stato BOZZA, che non ammette
   > fatturazione (1 attività pronta in attesa).*

   La diagnosi (`CommesseRepository.diagnostica_gruppi`) **descrive fatti**
   (stato testata + conteggi righe per stato); non riproduce il criterio di
   ammissibilità, che resta di `fn_list_emittibili_lane`. Se ritenete che debba
   scendere a DB come funzione, siamo d'accordo: ditecelo e ve la passiamo.
3. Il fallimento è dichiarato **deterministico**, quindi la coda va in ERRORE
   subito invece di ripetere il giro 5 volte con backoff. Effetto collaterale
   utile: anche i payload malformati (`E_FATTURAZIONE_GIRO_PAYLOAD`), che oggi
   venivano ritentati 5 volte, ora falliscono al primo colpo.

Resta scoperto un caso che **dipende da voi**: l'emissione **parziale** (3
gruppi chiesti, 2 serviti). Oggi non sappiamo quali gruppi siano finiti in quale
terna, perché `fn_list_emittibili_lane` aggrega per `(emittente, tipo_doc,
utility)` e i gruppi si perdono nell'aggregazione. Se la lane potesse
restituire anche `gruppi_coperti text[]`, l'esito potrebbe dire «2 su 3, il
terzo no perché…». **Non è urgente** e non blocca nulla: valutatelo insieme al
resto.

> 🟢 **FATTO il 2026-08-15** con `20260815-02`, su decisione di Tid di chiudere
> anche questa. La lane restituisce `gruppi_coperti text[]`: l'elenco
> **deterministico** dei gruppi che ciascuna terna ha davvero coperto. Il gruppo
> non servito si ricava per differenza, ed è la risposta che prima non esisteva.
>
> **Perché valeva la pena farla adesso, benché «non urgente».** Dei tre esiti
> possibili è l'unico **silenzioso**: «zero fatture» il BE l'ha già reso un errore
> parlante ad agosto, e insospettisce comunque; «2 su 3» sembra un successo, e il
> lavoro non fatturato resta fermo senza che nessuno lo vada a cercare.
>
> **La chiave arriva dalla sola fonte di verità** — `fn_build_gruppo_fatturabile_key`,
> la stessa che filtra nel `WHERE` e alimenta `vw_dash_competenza_gruppi` — e non è
> ricostruita nella lane: sarebbe la seconda copia della regola, l'errore che il §7.1
> ha già dovuto correggere una volta.
>
> ⚠️ **Il campo si calcola sempre, anche nel giro di massa**, ed è una scelta: costa
> una chiamata `STABLE` per riga candidata. L'alternativa — calcolarlo solo con
> `p_gruppi NOT NULL` — è stata scartata perché produrrebbe un campo che a volte vale
> `NULL` per «non calcolato» e a volte per «nessun gruppo»: l'ambiguità si paga sei
> mesi dopo, in silenzio. Se il costo mordesse sul cron, la mitigazione è scritta nel
> changeSet.
>
> ⚠️ **Il `RETURNS TABLE` cambia, quindi è servito un `DROP FUNCTION`.** Verificato
> prima: **zero** chiamanti DB (le due funzioni che nominano la lane la citano solo
> in un commento), la firma resta identica (i cinque `%TYPE` risolvono agli stessi
> tipi), i GRANT tornano dal meccanismo schema-wide, e il BE **non si rompe** perché
> nomina le cinque colonne una per una — il campo nuovo è **opt-in**: lo si prende
> aggiungendolo alla propria `SELECT`.
>
> **Presidio**: `test-fn-list-emittibili-lane.sql` passa da 9 a **11 test**. Il test
> 11 è il caso di questo paragrafo — si chiedono i gruppi veri più uno inesistente, e
> si verifica che il non servito si ricavi per differenza.

---

## 6. Definizione di «fatto»

- [x] `commessa_emittibile` (o `stato_commessa`) esposto dalle due viste — **entrambi**, §7.2;
- [x] transizione `→ PRONTA_FATTURAZIONE` manuale con `meta` completo;
- [x] `fn_check_commessa_pronta_fatturazione` come sede unica di capability+guard;
- [x] pgTAP §3.4 verdi — 7/7, §7.4;
- [x] FE, **verbo «Rendi pronta»** — fatto, e senza codice: il seed emette
      `action_key = rendi_pronta` da tutte e tre le origini (`BOZZA`, `APERTA`,
      `IN_ESECUZIONE`), attivo, con `vendite.commesse.azione_rendi_pronta` tradotta.
      Il drawer lo rende perché è data-driven (verificato sul DB il 2026-08-15);
- [x] FE, **riga bloccata segnalata in dashboard** — ✅ **fatto il 2026-08-15**
      (BE/FE, stesso rilascio del `gruppi_coperti`). La lista gruppi legge
      `commessa_emittibile` + `commessa_stato_codice_interno` dalla vista
      (repository → `DashCompetenzaGruppoRow` → FE) e la riga bloccata: (a) porta
      un lucchetto col motivo accanto al riferimento; (b) non è selezionabile
      (BB `useSelezioneToggle`, nato per questo); (c) ha «Fattura questo»
      **disabilitato** col motivo nel tooltip; (d) offre «Sblocca commessa» nel
      kebab, che apre il drawer di governo dove «Rendi pronta» è già esposto
      data-driven. «Segnalare, non nascondere»: la riga resta in lista;
- [x] **La prova che il giro si chiude**: sbloccare una commessa dall'interfaccia e
      fatturarne le attività, **una volta**. ✅ **Dichiarata chiusa da Tid il
      2026-08-16**, alla chiusura del cantiere.
      ⚠️ *Riformulata il 2026-08-15.* Diceva «le 5 commesse di giugno e le 15
      attività»: erano una fotografia di dati di **test** del 4 agosto, e a undici
      giorni non descrivono più niente. Quello che conta è la **catena**, non quelle
      righe — la si prova su una commessa qualsiasi. Non è una bonifica.
      *Ora la catena è tutta a video*: lucchetto → «Sblocca commessa» →
      «Rendi pronta» → riga selezionabile → «Fattura questo» → lotto. Resta la
      **prova in app di Tid**, che è l'unica voce aperta di questo brief.

---

## 7. Risposta DB (2026-08-04)

> **Chi scrive:** team DB (`dev/db-tid`). Da qui in avanti il documento è la
> risposta, non più la richiesta.

### 7.1 Il buco è reale, e la lettura del brief regge

Le tre richieste sono state accolte come scritte. Una precisazione sul §2.2, perché
cambia cosa si sistema: la transizione dichiarata non-manuale non era l'unico
problema. Sotto c'era una **seconda copia della regola**. Il guard di transizione
verificava «almeno una riga APPROVATA e NON_EMESSA» con una condizione scritta a mano
al proprio interno, mentre le uscite terminali (`CHIUSA`, `ANNULLATA`) delegavano già
alle funzioni pure con tanto di nota «sorgente UNICA, condivisa con
`fn_available_actions_commessa`». L'ingresso era rimasto indietro.

Finché la transizione era automatica la cosa non si vedeva: nessun bottone la
offriva, quindi non c'era un gemello da contraddire. Renderla manuale **senza**
estrarre la regola avrebbe creato il difetto del §3.3 nel momento stesso in cui si
chiudeva quello del §2.2.

### 7.2 Cosa è stato fatto

| # | Cosa | Dove |
| --- | --- | --- |
| 1 | `fn_check_commessa_pronta_fatturazione` — funzione pura, terza sorella di `_chiudibile` / `_annullabile` | `20260804-25` |
| 2 | Il guard smette di avere la regola in casa e legge la funzione: ingresso e uscite trattati allo stesso modo | `20260804-26` |
| 3 | `fn_available_actions_commessa` espone `enabled` + `reasons` anche per `PRONTA_FATTURAZIONE`, dalla **stessa** funzione | `20260804-27` |
| 4 | Le due viste espongono `commessa_emittibile` **e** `commessa_stato_codice` | `20260804-28` |
| 5 | Le tre transizioni verso `PRONTA_FATTURAZIONE` diventano manuali con `meta` completo | CSV `transizioni_stati_commessa.csv`, nessun changeSet (loader `runOnChange`) |
| 6 | `E_COMMESSA_EMITTENTE_MANCANTE` a catalogo, con causa e soluzione | CSV `messaggi_errore.csv` |

**Due colonne invece di una** (§3.1). Il brief ne chiedeva una dicendo però «ci serve
poter dire *perché* è bloccata, non solo *che* lo è»: il booleano da solo non lo
consente. Costano lo stesso, perché la vista fa già il JOIN su `stati_commessa` per
il filtro `ANNULLATA`.

**La regola la detta il motore.** I motivi della funzione pura sono lo specchio dei
filtri di `fn_list_emittibili_lane`, che è chi decide davvero cosa è fatturabile. Due
conseguenze:

- il criterio si **allarga** rispetto al guard vecchio, che ignorava
  `tipo_doc_fiscale_id`: una commessa con righe approvate ma senza tipo documento
  poteva dichiararsi pronta e non produrre nulla. Adesso viene fermata dove qualcuno
  può ancora rimediare;
- si aggiunge il motivo **emittente mancante**. La colonna è nullable e nessun trigger
  la pretende: una commessa senza emittente produrrebbe un raggruppamento che non
  diventa nessuna fattura. Lo stato `PRONTA_FATTURAZIONE` dichiara «questa si può
  fatturare»: se lo si raggiunge quando la promessa è falsa, il buco si riapre da
  un'altra porta.

Il `tipo_doc` invece **non** è diventato un motivo separato: esiste già un guard
dedicato che impedisce a una riga emittibile di averlo nullo, quindi sarebbe stato un
ramo irraggiungibile — codice che sembra coperto e non lo è. Resta nel filtro, dove
serve.

### 7.3 Sulla domanda «gli altri documenti sono a posto?»

La verifica è stata rifatta come **regola**, non come conta di righe: su dati di test
i numeri dicono cosa è stato cliccato di recente, non se il modello è corretto.

Il difetto specifico del brief — una capacità che governa un motore e si raggiunge
solo per via automatica — è **solo della commessa**: `stati_commessa.emittibile` è
l'unico flag di quel tipo fra tutte e otto le tabelle di stato. Le altre hanno flag
descrittivi (`terminale`, `is_bozza`, `is_abortito`) o riguardano il ciclo fatture,
che ha il proprio cantiere.

Ne è però uscita una regola generale che vale per ogni documento, presente e futuro:

> **R1 — da ogni stato con uscite attive deve esistere almeno un'uscita che una
> persona può azionare.** Se le uniche uscite sono automatiche, il documento dipende
> da un evento che potrebbe non arrivare mai. L'eccezione è legittima solo se lo stato
> è dichiarato senza ritorno, e allora va detto.

R1 adesso è un test, non un'indagine da rifare a mano:
[`test-transizioni-uscita-manuale-v1.sql`](../../../../db/pgtap/config/test-transizioni-uscita-manuale-v1.sql)
scorre tutte e sette le matrici.

> 🟢 **CHIUSO — aggiornamento del 2026-08-15.** Il test è **verde** e **fuori dalla
> baseline** (verificato eseguendolo). I sei stati elencati qui sotto sono
> esattamente quelli su cui Tid ha deciso il 2026-08-04, e il cantiere
> [vie d'uscita per l'operatore](../work-done/brief-db-vie-uscita-operatore.md) li ha
> chiusi tutti: due hanno riavuto l'annullamento, quattro dicono perché non ce
> l'hanno. Il paragrafo resta perché è **il punto in cui la regola R1 è nata** — da
> una domanda di questo brief, «gli altri documenti sono a posto?» — e quella genesi
> vale più della lista.
>
> ⚠️ La R1 ha poi mostrato un **punto cieco** che questo paragrafo non poteva
> prevedere: per costruzione non vede uno stato **senza nessuna uscita**, perché il
> test raggruppa le transizioni per stato di partenza. Sono stati proprio quelli a
> lasciare una barra muta a video. Il presidio dell'altro lato è
> `script/test-capability-motivi-e-nessuna-azione-v1.sql`; il punto cieco è
> dichiarato dentro il file stesso.

Quando fu scritto era **rosso**, e nominava sei stati:

```text
ddt.CONSEGNATO, ddt.RESO, ordine.CONFERMATO,
ordine.EVASO, ordine.PARZIALMENTE_EVASO, preventivo.ACCETTATO
```

Non è un'emergenza, è una **lista di decisioni**. Alcuni di quei casi sono
probabilmente legittimi — le transizioni fra `EVASO` e `PARZIALMENTE_EVASO` sono
ricalcoli guidati dalle quantità, non decisioni. Altri meno: le uscite manuali verso
`ANNULLATO` esistono con `meta` completo (`action_key`, label, icona) ma sono
**spente**, e da nessuna parte è scritto perché. Per ciascuno la risposta legittima è
una di due, e va messa nero su bianco: *aggiungere la via d'uscita* oppure *dichiarare
lo stato senza ritorno*. Il test è registrato in `baseline-rossi.tsv` proprio per
questo: è debito dichiarato, e la baseline deve calare.

### 7.4 Verifiche

[`test-commessa-pronta-fatturazione-v1.sql`](../../../../db/pgtap/vendite/test-commessa-pronta-fatturazione-v1.sql)
— **7/7 verdi**, i cinque casi del §3.4 più il preflight e la separazione fra
transizione lecita e rifiutata. La fixture è **costruita dentro il test** (due
commesse create copiando i riferimenti di una esistente), non pescata dai dati: i casi
valgono anche su un database appena creato e non passano in silenzio per assenza di
dati.

Il caso 4 è l'invariante che conta: `enabled` del bottone e `[]` della funzione pura
devono coincidere su entrambe le commesse. Non perché siano scritti «uguali», ma
perché sono **la stessa** funzione.

> ℹ️ **Una cosa scoperta scrivendo il test.** `vw_dash_competenza_attivita` filtra per
> scope emittente leggendo `app.current_user_id`: senza quella GUC,
> `fn_get_emittenti_scope_sr_ids` risponde `'{}'` e la vista non mostra **niente**. È
> corretto (è la RLS applicativa che fa il suo lavoro) ma va saputo: qualunque test o
> query manuale sulla dashboard senza GUC vede una lista vuota e sembra un bug dei
> dati.

### 7.5 Cosa resta

> 🟢 **Rimisurato il 2026-08-15.** Delle tre voci qui sotto **una è chiusa e una si è
> dimezzata**: le spunte del §6 e la nota nel §7.3 riportano la prova.

- ~~🔴 FE — la riga bloccata non è segnalata in dashboard.~~ ✅ **Fatto il
  2026-08-15**: la lista gruppi legge il flag e lo stato, marca la riga, spegne il
  verbo col motivo e offre lo sblocco dal kebab — dettaglio nella spunta del §6.
  Nello stesso rilascio il BE ha adottato `gruppi_coperti` (la SELECT della lane +
  `gruppi_non_coperti` nel summary del giro) e l'emissione parziale ora dice «2 su
  3, il terzo no perché…» — la diagnosi per-gruppo entra nell'esito del job senza
  fallirlo, e il toast FE la riporta. Resta la **prova in app** (voce sotto).
- ~~Le sei decisioni di R1 (§7.3), da prendere insieme.~~ ✅ **prese e chiuse** dal
  cantiere vie d'uscita; il test R1 è verde e fuori baseline.
- ~~Il `gruppi_coperti text[]` della lane (§5 del brief): non è stato fatto.~~
  ✅ **Fatto il 2026-08-15**, `20260815-02` — e nella sede giusta, la lane, non la
  diagnostica BE. Dettaglio e motivazioni in coda al §5; presidio ai test 10-11 di
  `test-fn-list-emittibili-lane.sql`.

---

## 8. Risposta BE/FE (2026-08-15) — cosa è stato fatto, e cosa serve ancora dal DB

> **Chi scrive:** BE/FE (`dev/backend-tid`). Chiude le due voci che il DB ci ha
> passato il 2026-08-15 e apre **due richieste**, scritte come *cosa serve* — il
> *come* è vostro.

### 8.1 Fatto, in questo rilascio

| # | Cosa | Dove |
| --- | --- | --- |
| 1 | La lista gruppi legge `commessa_emittibile` + `commessa_stato_codice_interno` dalla vista | `vendite_repository.list_dash_competenza_gruppi`, `DashCompetenzaGruppoRow` |
| 2 | Riga bloccata: **lucchetto col motivo**, **non selezionabile**, «Fattura questo» **disabilitato** col perché, «Sblocca commessa» nel kebab | `DashboardCompetenzaView` |
| 3 | `gruppi_coperti` adottato: la SELECT della lane lo porta, il core misura `gruppi_non_coperti` = richiesti − union(coperti) | `commesse_repository.list_emittibili_lane`, `fatturazione_driver_service` |
| 4 | Emissione **parziale** parlante: la diagnosi per-gruppo entra nell'esito **senza far fallire il job** — i lotti prodotti sono lavoro vero | `fatturazione_giro_handler` |

**Costo reale: zero sul cablaggio.** Il campo `stato_info_key` viaggia opaco nei
`call_jsonb_fn` e tutti e otto i drawer leggevano già la prop; le due colonne
nuove la vista le espone da giugno e il JOIN c'era già. Il lavoro è stato tutto
nel *dire le cose*, non nel trasportarle.

**Una cosa che la review ha trovato e che vale la pena sapere.** La prima
stesura del FE metteva l'avviso dei non-serviti in `else if` dopo quello degli
errori di terna: con **una terna fallita e un gruppo fuori perimetro nello
stesso giro**, la diagnosi che voi calcolate veniva scartata a video. Era di
nuovo il silenzio del «2 su 3», entrato dalla porta di servizio. Corretto: i due
avvisi coesistono. Lo scriviamo perché è la stessa classe di difetto che il
vostro `20260815-02` è nato per togliere, e si è ripresentata **a valle**.

### 8.2 🔴 Richiesta 1 — sapere quali gruppi un giro ha **davvero** fatturato

**Il problema, in una riga:** `gruppi_coperti` è una **previsione**, non un
consuntivo, e fra la previsione e il fatto c'è una finestra in cui il lavoro può
sparire senza che nessuno lo dica.

La discovery dichiara che una terna copre i gruppi A, B, C. Fra quel momento e
l'esecuzione della pipeline, le righe di C possono essere prese da un altro giro
(o smettere di essere candidate per qualunque motivo). La pipeline esce **senza
errore** e senza lotto per C. Il risultato: `falliti = 0`,
`gruppi_non_coperti = []`, e l'esito legge **pieno successo** mentre C non è
stato fatturato. È esattamente la forma di difetto del §5 — silenziosa, e quindi
peggiore di un errore — solo spostata di un passo più in là.

**Cosa ci serve:** poter dire, **a consuntivo di un giro**, quali gruppi
fatturabili hanno prodotto righe fatturate davvero. Non una previsione fatta
prima: una misura fatta dopo.

Vincoli che ci interessano, e nient'altro:

1. la risposta deve essere **per `gruppo_key`**, dalla stessa unica fonte
   (`fn_build_gruppo_fatturabile_key`): deve poter essere confrontata senza
   traduzioni con ciò che l'operatore ha spuntato a video;
2. deve essere **interrogabile dopo**, non solo durante il giro: l'operatore
   apre l'esito anche il giorno dopo, e la coda ripete i job;
3. deve valere l'invarianza **richiesti = serviti + non serviti**, sempre, con
   entrambi i termini *misurati* e nessuno dei due dedotto per differenza da una
   previsione.

⚠️ **`fatturazione_lotti_gruppi` non risponde**, e va detto per non farvi
guardare lì: registra il **permesso** («questo lotto può lavorare questi
gruppi»), non il servito. Un gruppo nel perimetro che non produce nulla lascia
la riga esattamente com'è.

**Quello che NON chiediamo:** non chiediamo di chiudere la finestra con un lock,
né di rendere transazionale discovery+pipeline. La concorrenza fra giri è
legittima e il lavoro «rubato» da un altro giro **è comunque stato fatturato**:
non è un errore, è solo una cosa che oggi non sappiamo raccontare. Ci basta
poterla nominare.

### 8.3 🟠 Richiesta 2 — la descrizione dello stato commessa nelle due viste

**Il problema:** `vw_dash_competenza_gruppi` espone `commessa_stato_codice_interno`
(`BOZZA`, `PRONTA_FATTURAZIONE`) ma non la **descrizione**. A video va la
descrizione: la convenzione del progetto è che le liste ricevono i campi di
display già decodificati dal DB, mai risolti lato client — e un codice interno
in un'interfaccia inglese («The job order is in state BOZZA») è il sintomo.

**Cosa abbiamo fatto intanto:** il repository fa un `LEFT JOIN` su
`vendite.stati_commessa` per prendersi `descrizione`. Funziona, ed è la ragione
per cui questa richiesta è **arancione e non rossa**: non siamo bloccati.

**Cosa ci serve:** che le due viste espongano anche la descrizione dello stato,
accanto al codice interno che già portano. Il motivo per cui la chiediamo a voi
invece di tenerci il JOIN: **le viste quel JOIN lo fanno già** (è da lì che
arrivano `emittibile` e `codice_interno`), quindi il nostro è una seconda copia
della stessa risoluzione — la stessa forma di duplicazione che il §7.1 vi ha
fatto estrarre sul guard. Se la prendete, togliamo il JOIN dal repository nello
stesso rilascio.

> ℹ️ Stessa osservazione, più in piccolo, per la diagnostica: anche
> `diagnostica_gruppi` restituisce il codice interno come `stato_commessa`, e
> quel valore finisce **nella frase** che l'operatore legge nel toast. Se la
> descrizione arriva, la prendiamo anche lì.

### 8.4 Cosa resta aperto, dichiarato

- ~~🔴 **La prova in app di Tid** — sbloccare una commessa dall'interfaccia e
  fatturarne le attività, una volta.~~ ✅ **eseguita con successo il 2026-08-16**,
  e ha trovato un difetto che nessuna review aveva visto — **§12.6**;
- ~~🟠 le due richieste qui sopra~~ ✅ **fatte dal DB** (§9) e **consumate dal
  BE/FE** (§10, §12);
- ℹ️ il **dettaglio dei motivi è prosa italiana del BE** anche in locale EN
  (stesso trade-off già accettato per `ultimo_errore.message`): non lo tocchiamo
  in questa slice, ma è scritto perché non venga scambiato per una svista.

---

## 9. Risposta DB (2026-08-15, sera) — verifica, analisi critica, piano

> **Chi scrive:** team DB (`dev/db-tid`). Risponde al §8 e apre il lavoro.
> Ogni numero qui sotto è **misurato**, non riferito: le viste dal catalogo vivo
> (`pg_attribute`), i test eseguiti, i tempi cronometrati.

### 9.1 Verifica di quanto il §7 dichiarava chiuso

Rifatta contro il DB, non contro gli YAML. **Nessun residuo.**

| Voce | Verifica |
| --- | --- |
| `commessa_emittibile` + `commessa_stato_codice_interno` | presenti **live** in entrambe le viste (19 colonne su `vw_dash_competenza_gruppi`, le due in coda) |
| `gruppi_coperti text[]` | presente nella lane, chiave da `fn_build_gruppo_fatturabile_key`, ordine deterministico |
| Transizione manuale | CSV `transizioni_stati_commessa.csv`, righe 2/5/7, `meta` completo con `action_key: rendi_pronta` |
| `fn_check_commessa_pronta_fatturazione` | esiste, pura, sede unica di guard + capability |
| `E_COMMESSA_EMITTENTE_MANCANTE` | a catalogo in `codici_errore.csv` **e** `messaggi_errore.csv`, con causa e soluzione |

pgTAP **eseguiti** (non riferiti): `test-commessa-pronta-fatturazione-v1.sql` **7/7**,
`test-fn-list-emittibili-lane.sql` **11/11**, `config/test-transizioni-uscita-manuale-v1.sql`
(R1) **3/3** — tutti verdi e fuori baseline.

### 9.2 Analisi critica del §8

#### F1 🔴 Il consuntivo del §8.2 **esiste già come dato**: non serve persistere nulla

`attivita_fatturabili.commessa_attivita_id` è **UNIQUE** — 1:1 con `commesse_attivita` —
e `fattura_riga_id` chiude la catena `lotto → fatture → fatture_righe → attività →
gruppo_key`. Prototipo **eseguito sui dati veri**:

```text
gruppo_key                                          | esito       | lotti_serventi
ORDINE_VENDITA:019fc4ba-79db-759c-967b-53744acca606 | SERVITO     | {1278}
ORDINE_VENDITA:019fc723-71ef-725a-a9b3-8b27c6994bab | NON_SERVITO |
```

Il lotto 1279 ha un perimetro richiesto e **zero righe fatturate**: è il caso del
§8.2, ed è già misurabile.

⭐ **Il pezzo che il §8.2 non ha visto: anche i «richiesti» sono già a DB.**
`set_lotto_gruppi` scrive l'**intera** tupla richiesta su **ogni** lotto del giro.
Quindi dai soli `lotto_id` il DB ricava richiesti *e* serviti, entrambi **misurati**,
e l'invarianza del vincolo 3 regge per costruzione dentro una sola funzione — senza
tabelle nuove, senza write path, senza il lock che il §8.2 giustamente non chiedeva.

⚠️ Va **dichiarato** che è una misura **viva**, non un log immutabile: se un lotto
torna a DRAFT il consuntivo cambia. È corretto (la fattura non c'è più) ma non deve
sorprendere fra sei mesi.

#### F2 🔴 La trappola vera: la RLS è **asimmetrica** fra richiesti e serviti

Misurato:

| RLS attiva | RLS assente |
| --- | --- |
| `commesse`, `commesse_attivita`, `fatture`, `fatture_righe`, `fatturazione_lotti` | `attivita_fatturabili`, `fatturazione_lotti_fatture`, **`fatturazione_lotti_gruppi`** |

Il perimetro **richiesto** è leggibile da chiunque, il **servito** no. Scritta in modo
ingenuo, la funzione direbbe `NON_SERVITO` a un operatore fuori scope su un gruppo
fatturato benissimo: un falso allarme con l'aria di un dato. È la regola del
fail-closed — zero non è una misura. **Il cancello dev'essere `fatturazione_lotti`**
(che la RLS ce l'ha): lotto fuori scope → **nessuna riga**, mai un «non servito».

#### F3 🟠 Il §8.3 arriva incompleto: c'è una **seconda** duplicazione, e non è nel brief

In `vendite_repository.list_dash_competenza_gruppi`, trenta righe sopra il JOIN della
§8.3, sta scritto:

> ⚠️ *Drift noto e accettato: la regola di risoluzione è scritta due volte — qui e
> dentro `vw_dash_competenza_gruppi`. La soluzione pulita è che la vista esponga
> `documento_id` accanto al `riferimento`: è una nota per il team DB.*

È **identica** alla §8.3 per forma e per causa, e la vista fa già la LATERAL da cui
`riferimento` arriva: aggiungere `d.documento_id` costa **una colonna nella stessa
subselect**. È rimasta in un commento di codice invece che nel brief. Le due vanno
nello stesso changeSet, o fra un mese se ne discute una terza.

#### F4 🟠 L'ultima copia della regola fuori dal DB è `diagnostica_gruppi`

Il BE l'ha offerta il 2026-08-04 (§5.2: *«Se ritenete che debba scendere a DB come
funzione, siamo d'accordo: ditecelo»*). **Non abbiamo risposto**, e nel frattempo è
cresciuta: ~60 righe di SQL in Python che riproducono i filtri della lane
(`APPROVATA` + `NON_EMESSA` + `tipo_doc NOT NULL` + competenza `<=`). Stessa forma che
il §7.1 ci ha fatto estrarre sul guard.

E ha già un difetto latente. Aggrega con `min(commessa_codice)`, `min(stato_commessa)`,
`bool_or(commessa_emittibile)` su `gruppo_key`. Ma `gruppo_key`, per una riga con
documento sorgente, è `<codice_interno>:<uid>` e **non contiene la commessa**. Se lo
stesso documento alimentasse due commesse, `bool_or` direbbe «emittibile» perché *una*
lo è, e la diagnosi cadrebbe in `NON_DETERMINATO` invece di dire «commessa in BOZZA».
⚠️ `vw_dash_competenza_gruppi` raggruppa **anche per `commessa_id`**: la vista ammette
già il caso, il BE lo collassa.

**Calibrazione onesta**: sul DB di sviluppo i gruppi multi-commessa sono **0**, e
`commesse_sorgenti` ha `UNIQUE (sorgente_tipo_id, sorgente_uid)` che rende il caso
improbabile. Ma **nessun vincolo** lega `commesse_attivita.commessa_id` a quel link:
non è «è successo», è «può succedere» — e in DB si evita gratis aggregando per
`(gruppo_key, commessa_id)`.

Portandola a DB, la descrizione dello stato del §8.3 arriva **anche nella frase del
toast**, che è il secondo punto della richiesta, quello lasciato in nota.

#### F5 🟢 Il costo di `gruppi_coperti`: misurato. E una promessa non mantenuta

`20260815-02` scrive: *«Se un giorno il costo mordera' sul cron, la mitigazione e'
nota e sta scritta qui»*. **Non c'è**: il paragrafo dopo passa al `DROP FUNCTION`.
Misurata quindi adesso, su 100.000 righe sintetiche:

| forma | tempo |
| --- | --- |
| `fn_build_gruppo_fatturabile_key` × 100k, scalare | 475 ms → **≈ 5 µs/chiamata** |
| lane attuale (`array_agg DISTINCT … ORDER BY <stessa espressione>`) | 540–637 ms |
| variante con chiave calcolata una volta in `LATERAL` | 527–537 ms |

⭐ **Le due forme sono equivalenti**: il parser deduplica l'espressione dell'`ORDER BY`
con quella dell'argomento, quindi la valutazione è **una sola per riga**. La
micro-ottimizzazione che sembrava ovvia **non esiste**, ed è bene che sia scritto:
qualcuno la rifarà. Il costo reale è ~0,5 s ogni 100k righe candidate (in dev oggi ne
risultano **38**). La scelta di calcolarlo sempre era giusta; va solo sostituita la
promessa a vuoto col numero.

#### F6 🟢 `diagnostica_gruppi` è usata fuori dal contratto che si è data — *nota al BE*

La sua docstring dice: *«Da chiamare SOLO quando il giro non ha emesso nulla»*. Il nuovo
`_diagnostica_e_spiega` la chiama anche nel caso **parziale**, cioè dopo un'emissione
riuscita. Per i gruppi non coperti la fotografia regge — **non è un difetto** — ma è un
contratto dichiarato e poi infranto nello stesso file. Da riallineare in prosa quando
la funzione scenderà a DB (F4).

#### F7 ℹ️ `LIMIT p_limit` può travestire un troncamento da «gruppo non coperto»

`fn_list_emittibili_lane` limita le **terne** (default 1000). Se un'emissione mirata ne
generasse di più, i gruppi delle terne tagliate risulterebbero «non coperti» senza
esserlo. Irrilevante oggi (le mirate sono da pochi gruppi), ma è **silenzioso**: merita
una riga di commento, non un fix.

### 9.3 Piano di esecuzione — decisioni di Tid del 2026-08-15

Tid ha deciso: **F4 si fa**; **vista + funzione** per il §8.2; **tutto il possibile lato
DB**, BE/FE a seguire. Numerazione `20260815-24` in avanti (sequenza **globale per
data**).

| # | Slice | ChangeSet | Stato |
| --- | --- | --- | --- |
| 1 | §8.3 — `commessa_stato_descrizione` su `vw_dash_competenza_attivita` | `20260815-24` | ✅ |
| 2 | §8.3 + F3 — `commessa_stato_descrizione` **e** `documento_id` su `vw_dash_competenza_gruppi` | `20260815-25` | ✅ |
| 3 | §8.2 — `vw_lotti_gruppi_serviti`, il **fatto** per `(lotto_id, gruppo_key)` | `20260815-26` | ✅ |
| 4 | §8.2 — `fn_esito_gruppi_giro(p_lotto_ids)`, il **verdetto** per giro | `20260815-27` | ✅ |
| 5 | F5 + F7 — `COMMENT` sulla lane: il numero misurato al posto della promessa | `20260815-28` | ✅ |
| 6 | F4 — `fn_diagnostica_gruppi_fatturabili`, grana `(gruppo_key, commessa_id)` | `20260815-29` | ✅ |

**Vincoli che il piano si dà**, perché è dove si sbaglia:

- ⚠️ ogni `CREATE OR REPLACE VIEW` **ri-specifica `WITH (security_invoker=on)`**: la
  reloption non è nel `pg_get_viewdef` e PostgreSQL la azzera in silenzio;
- ⚠️ le colonne nuove vanno **in coda**: `CREATE OR REPLACE VIEW` non riordina;
- ⚠️ ordine NN **vincolante**: la vista base (`-24`) prima della dipendente (`-25`),
  perché l'autogen mescola `00_schema` e `20_code` ordinando per numero;
- la chiave di gruppo si calcola **sempre** con `fn_build_gruppo_fatturabile_key` su
  `commesse_attivita`, **mai** sulle colonne gemelle di `attivita_fatturabili`: unica
  fonte, come per la lane;
- il verdetto legge `fatturazione_lotti_gruppi` **attraverso** `fatturazione_lotti`
  (F2), così un lotto fuori scope produce **zero righe** e non un falso «non servito»;
- `descrizione` è nullable a DDL ma popolata su tutte e 6 le righe di seed →
  `COALESCE(descrizione, codice)`, perché un campo di display non deve mai essere vuoto.

**Presidio pgTAP — eseguito, non previsto:**

| File | Casi | Esito |
| --- | --- | --- |
| `vendite/test-esito-gruppi-giro-v1.sql` (nuovo) | servito · non servito con residuo · **fatturato altrove** · invarianza · guard parametri · giro di massa · ⚠️ **lotto fuori scope → SOLLEVA** | **12/12** |
| `vendite/test-diagnostica-gruppi-fatturabili-v1.sql` (nuovo) | contatori per classe · bound competenza · gruppo ignoto · descrizione decodificata · ⚠️ **multi-commessa** · normalizzazione chiavi · input degeneri · ⚠️ **`n_senza_tipo_doc` è sentinella** | **10/10** |
| `vendite/test-vw-dash-competenza-v1.sql` (esteso, 15 → 17) | le due colonne nuove decodificano; `documento_id` NULL sul gruppo sourceless | **17/17** |
| `vendite/test-vw-dash-security-invoker.sql` (esteso) | la rete `vw_dash_*` non copriva `vw_lotti_gruppi_serviti`: coda esplicita | **2/2** |

### 9.4 Verifiche eseguite

> Tutto **misurato**, non riferito.

- **Migrazioni applicate** su dev (`liquibase update`): i sei changeSet passano,
  i pendenti residui sono i soli mirror `runOnChange` di sempre;
- **`vw_lotti_gruppi_serviti` + `fn_esito_gruppi_giro` provate sui dati veri**
  prima ancora dei test: sul lotto 1279 — perimetro richiesto, zero righe
  fatturate — l'esito dice `NON_SERVITO`. È il caso del §8.2, e prima non aveva
  risposta;
- ⭐ **`fn_diagnostica_gruppi_fatturabili` confrontata con la query Python del
  BE su tutti i 73 gruppi del database: zero differenze.** Il cambio di grana
  non altera i risultati odierni (nessun gruppo multi-commessa esiste oggi), che
  è esattamente ciò che rende la migrazione sicura;
- **baseline pgTAP `vendite`**: 178 file, 24 rossi, **tutti già noti — nessuna
  regressione**;
- **cancelli statici della CI**: guardrail `runOnChange` verde, guardrail
  preambolo pgTAP verde (430 file), guardrail naming `codice_interno`/`codice`
  verde. Il debito `throws_ok` senza discriminante **non è salito** (137 su
  soglia 137): i test nuovi passano sempre lo SQLSTATE;
- **doc auto-generata rigenerata** (`gen_db_docs.py`) e doc **manuale** scritta
  per i tre oggetti nuovi, più la nota sulle due colonne nelle viste.

⚠️ **Tre cose emerse verificando, che valgono più del verde:**

1. **Svuotare `app.current_user_id` NON è fail-closed.** Il primo tentativo di
   test sullo scope passava senza sollevare: misurato,
   `script.fn_scope_ef_whitelist_via_sr(NULL, …)` risponde **TRUE** — «nessuna
   restrizione», non «nessun accesso». Il cancello vero è il primo congiunto
   della policy (`ruolo_applicativo = 'OPERATORE'`). Chi scrive un test di scope
   su questa famiglia deve cambiare **veste**, non svuotare l'utente;
2. **`n_senza_tipo_doc` è un ramo che non si può percorrere.** La riga che lo
   alimenterebbe è rifiutata da `trgfn_commesse_attivita_guard_tipo_doc_emittibile`
   e da un `CHECK`. Il contatore resta — quel `CHECK` è `NOT VALID`, quindi le
   righe **legacy** non sono mai state verificate — ma è una **sentinella**, non
   un caso vivo: il test lo verifica dal *percorso* (il guard rifiuta), non
   fabbricando una riga che il database non ammette. Vale anche per il BE:
   `MOTIVO_TIPO_DOC_MANCANTE` non si accenderà su dati nuovi;
3. **Il cancello che si dichiara va applicato a tutte le uscite, non solo
   all'ingresso.** Rileggendo `fn_esito_gruppi_giro` prima di chiudere:
   `lotti_altrui` prendeva gli id da `fatturazione_lotti_fatture`, che RLS non
   ne ha. Poco — chi legge vede comunque solo fatture del proprio perimetro — ma
   avrebbe potuto restituire l'identificativo di un lotto non suo, in
   contraddizione col cancello che il changeSet stesso dichiara. Corretto: gli
   id passano da `fatturazione_lotti`, e un lotto non visibile esce come `NULL`
   invece che come numero. Il `LEFT JOIN` conserva la semantica del residuo.

Anche la **documentazione** è stata misurata, non supposta: build Zensical
eseguita due volte, sul ramo e su `HEAD` in un worktree separato — **5 warning
prima, 5 dopo, `include_warnings=0`**. Nessuna introdotta.

### 9.5 Coda chiusa: i due residui che il §9.4 aveva lasciato aperti

> Scritto dopo, il 2026-08-15 sera. Le due voci erano state presentate come
> «decisioni per Tid». **Non lo erano**, e la risposta è stata secca: *non siamo
> in produzione, i dati sono di test, si fanno gli aggiornamenti necessari e
> quello che si rompe per dati sporchi si sistema sul momento.* La regola
> esisteva già; il difetto era averla riaperta come domanda.

| # | Cosa | ChangeSet | Stato |
| --- | --- | --- | --- |
| 7 | `chk_commesse_attivita_tipo_doc_emittibile` da `NOT VALID` a **validato** | `20260815-30` | ✅ |
| 8 | Via `n_senza_tipo_doc` dalla diagnostica: ora è un ramo irraggiungibile | `20260815-31` | ✅ |
| 9 | F7 — il tetto `p_limit` **solleva** sul giro mirato invece di troncare | `20260815-32` | ✅ |
| — | `E_FATTURAZIONE_MIRATA_TRONCATA` a catalogo (append ai CSV, id 908) | CSV | ✅ |

**7 e 8 sono una cosa sola.** Il vincolo era `NOT VALID`: le righe preesistenti
non erano mai state lette, quindi il contatore `n_senza_tipo_doc` restava in vita
come «spia che non dovrebbe accendersi». Validato il vincolo, la garanzia vale su
**tutte** le righe e il ramo diventa irraggiungibile — e un ramo che sembra
coperto e non lo è vale meno di zero. ⚠️ Ordine vincolante: `-30` (schema) prima
di `-31` (codice), perché l'autogen ordina per NN. ⚠️ Ricaduta BE:
`MOTIVO_TIPO_DOC_MANCANTE` diventa morto anche in `classifica_gruppo_non_servito`.

**9 chiude il difetto F7.** Il tetto limita le *corsie*: tagliarne una fa sparire
i suoi gruppi, che a valle — dove il non servito si ricava per differenza —
diventano «non fatturabili». Una diagnosi **falsa** al posto di un errore: la
stessa classe di difetto di tutto il cantiere, spostata di un passo. Il rimedio è
asimmetrico e deliberato: sul giro di **massa** il tetto resta una valvola e
tronca in silenzio; sul giro **mirato** il perimetro è nominale e troncarlo
significa non aver risposto → si solleva.
⚠️ Il conteggio si fa leggendo **una corsia in più del tetto** e scorrendo il
risultato una volta sola: un secondo `SELECT count(*)` di controllo sarebbe stato
una seconda copia dei filtri di discovery dentro la stessa funzione — l'errore
che il §7.1 ha già dovuto correggere.

**Verifiche.** Tutti e tre provati prima in transazione (`BEGIN … ROLLBACK`), poi
**migrati** e rimisurati sul DB vero: `chk_commesse_attivita_tipo_doc_emittibile`
risulta `convalidated = true`, `n_senza_tipo_doc` non è più fra le colonne della
diagnostica, la lane porta il guard sul tetto, e
`E_FATTURAZIONE_MIRATA_TRONCATA` è a catalogo con il suo messaggio (arrivato dal
mirror CSV `runOnChange`, come da regola: solo append, nessun loader nuovo).

pgTAP estesi e **tutti verdi** dopo la migrazione:
`test-fn-list-emittibili-lane` 11 → **13**,
`test-diagnostica-gruppi-fatturabili` 10 → **11**, più i tre file già toccati
dal §9.5 e `test-guard-tipo-doc-emittibile` (che presidia il guard su cui poggia
la validazione del vincolo). Baseline `vendite`: **nessuna regressione**.
Guardrail riferimenti morti e codici errore strutturati: verdi. Doc auto-generata
rigenerata dal database vivo.

### 9.6 ⚠️ Un errore fatto qui, e la trappola che ha scoperto

**Il migrate si è fermato** sul `20260815-32`:

```text
SQL Precondition failed. Expected '1' got '0'
```

La precondizione chiedeva *«il codice errore che sollevo esiste a catalogo?»*.
Sembra la verifica ovvia, ed è **sbagliata**: i codici arrivano dai CSV di
`80_data`, che nel master gira **dopo** `20_code`. Al momento del controllo quel
codice non poteva esserci. Il codice serve a **runtime**, non al `CREATE`.

⚠️ **La parte che conta non è l'errore, è il gemello che ha svelato.** La stessa
precondizione era anche sul `20260815-27`, su `E_LOTTO_NON_TROVATO` — e lì era
**passata**, ma solo perché quel codice esisteva già da migrazioni precedenti. Su
un database ricostruito da zero — **la CI** — `config.codici_errore` a quel punto
è vuota e il migrate si sarebbe fermato uguale, in una pipeline che non c'entrava
niente. È esattamente la trappola d'ordine fra le fasi che su un DB di sviluppo
non si vede: qui si è vista solo perché il codice del `-32` era **nuovo**.

Entrambe rimosse, con il motivo scritto dentro i due file perché non tornino.
Verificato poi su tutti e nove i changeSet del cantiere che nessun'altra
precondizione dipenda da dati di `80_data`.

### 9.7 Richieste a BE/FE — il DB ha chiuso, tocca a voi

> Numerata in coda e non al posto della §9.4 perché è l'ultima cosa scritta: quando è stata redatta
> la prima volta il DB non aveva ancora finito, e il titolo diceva «quando il DB
> avrà chiuso». Adesso ha chiuso.

1. **sostituire `gruppi_non_coperti` con `fn_esito_gruppi_giro(lotti)`**:
   `gruppi_coperti` resta la diagnosi *prima* dell'esecuzione, il consuntivo è
   quello che dice cosa il giro ha fatturato davvero. Prende **solo i lotti**: i
   gruppi richiesti sono già persistiti, e passarglieli riaprirebbe la porta a
   passare la previsione al posto della misura;
2. **togliere dal repository due JOIN**: il `LEFT JOIN vendite.stati_commessa`
   (§8.3) **e** la LATERAL di `documento_id` (F3). Entrambi sono ora colonne di
   `vw_dash_competenza_gruppi`, e l'id del documento arriva dalla stessa riga del
   `riferimento` — non più due risoluzioni che possono divergere;
3. **adottare `fn_diagnostica_gruppi_fatturabili`** al posto dell'SQL in
   `CommesseRepository.diagnostica_gruppi`, tenendo in Python **solo** la prosa di
   `classifica_gruppo_non_servito` — quella è presentazione, non regola.
   ⚠️ Due cose cambiano nel contratto, ed entrambe sono deliberate:
   - la grana diventa **`(gruppo_key, commessa_id)`** (F4): un gruppo su due
     commesse dà due righe, ed è il caso che `min()`/`bool_or()` collassava;
   - **`n_senza_tipo_doc` non esiste più**, quindi
     `MOTIVO_TIPO_DOC_MANCANTE` in `classifica_gruppo_non_servito` va tolto
     insieme alla chiave in `GruppoDiagnosi`: dopo la validazione del `CHECK`
     (`20260815-30`) quella riga non può esistere, e un motivo che non può
     accendersi è un ramo morto anche lato BE;
4. **riallineare la docstring** di `diagnostica_gruppi` (F6): dice «da chiamare
   solo quando il giro non ha emesso nulla», ma `_diagnostica_e_spiega` la chiama
   anche nel caso parziale. Non è un difetto — per i gruppi non coperti la
   fotografia regge — ma è un contratto dichiarato e poi infranto nello stesso
   file;
5. ℹ️ **novità da sapere, non un'azione**: su un giro **mirato** la discovery ora
   può sollevare `E_FATTURAZIONE_MIRATA_TRONCATA` (perimetro oltre il tetto delle
   corsie). È un caso che oggi non capita — le mirate sono da pochi gruppi — ma
   se capitasse, prima usciva una diagnosi **falsa** e adesso esce un errore. Sul
   giro di massa non cambia niente.

---

## 10. Piano BE/FE sulle richieste del §9.7 (2026-08-15, notte)

> **Chi scrive:** BE/FE (`dev/backend-tid`). Le cinque voci del §9.7, prese come
> sono, più quello che il §9.7 non poteva sapere: le ricadute a valle nel nostro
> codice. Scritto **prima** di eseguire, aggiornato **mentre** si esegue.

### 10.1 Verifica preliminare — gli oggetti ci sono davvero

Controllati sulla doc auto-generata (mai dagli YAML), prima di scrivere una riga:

| Oggetto | Esito |
| --- | --- |
| `vw_dash_competenza_attivita.commessa_stato_descrizione` | ✅ `COALESCE(sc.descrizione, sc.codice)` |
| `vw_dash_competenza_gruppi.commessa_stato_descrizione` + `documento_id` | ✅ entrambe, `documento_id` dalla stessa LATERAL del `riferimento` |
| `vw_lotti_gruppi_serviti` | ✅ |
| `fn_esito_gruppi_giro(bigint[])` → `(gruppo_key, richiesto, esito, n_attivita_fatturate, n_attivita_residue, lotti_serventi, lotti_altrui)` | ✅ |
| `fn_diagnostica_gruppi_fatturabili(text[], date)` → 13 colonne, grana `(gruppo_key, commessa_id)` | ✅ |
| `E_FATTURAZIONE_MIRATA_TRONCATA` a catalogo, classe `NON_ESEGUIBILE` | ✅ |

⚠️ **Una cosa il §9.7 non la nominava, ed era rossa.** Il codice errore nuovo era
a catalogo ma **non nella mappa Python**: il guardrail del terzo lato
(`test_error_codes_db_policy_guardrail`, opt-in `ZEROERP_TEST_DB_E2E=1`) falliva
con «1 codici errore che il database può nominare non hanno una policy». Non si
edita a mano — la classe la decide il catalogo — quindi rigenerato con
`manage.py genera_error_policies`: diff di **una riga**, nessun riordino spurio.

### 10.2 Le cinque voci, e cosa comportano da noi

| # | Richiesta §9.7 | Ricaduta nel nostro codice | Stato |
| --- | --- | --- | --- |
| 1 | `fn_esito_gruppi_giro` al posto di `gruppi_non_coperti` | Il **consuntivo** sostituisce la previsione: sparisce la misura alla discovery nel driver, l'handler interroga i lotti prodotti. Il vocabolario passa da due stati a **tre** — `SERVITO` / `NON_SERVITO` / `FATTURATO_ALTROVE` — e il terzo va detto **diversamente**: non è un errore, è lavoro che un altro giro ha già fatturato | ✅ |
| 2 | Via i due JOIN dal repository | `LEFT JOIN stati_commessa` (§8.3) **e** LATERAL `documento_id` (F3): entrambi diventano colonne. Sparisce il «drift noto e accettato» dichiarato nel commento | ✅ |
| 3 | `fn_diagnostica_gruppi_fatturabili` al posto dell'SQL in `diagnostica_gruppi` | ~60 righe di SQL fuori dal BE. In Python resta **solo** la prosa di `classifica_gruppo_non_servito`. Contratto: grana `(gruppo_key, commessa_id)`, via `n_senza_tipo_doc` **e** `MOTIVO_TIPO_DOC_MANCANTE`, dentro `commessa_stato_descrizione` — che è il modo in cui la descrizione arriva **nella frase del toast** (il secondo punto del §8.3, quello lasciato in nota) | ✅ |
| 4 | Docstring di `diagnostica_gruppi` (F6) | Dichiara «solo a giro vuoto» ma la chiamiamo anche nel parziale. Prosa da riallineare | ✅ |
| 5 | ℹ️ `E_FATTURAZIONE_MIRATA_TRONCATA` | Nessuna azione oltre la policy del §10.1: il codice sale dal DB e il middleware lo mappa | ✅ |

### 10.3 Quello che il §9.7 non poteva sapere — le ricadute a valle

Sono nel nostro codice, quindi le nominiamo noi:

1. **`n_senza_tipo_doc` è citato in tre punti**, non uno: la chiave in
   `GruppoDiagnosi`, il ramo `MOTIVO_TIPO_DOC_MANCANTE` in
   `classifica_gruppo_non_servito`, e le **fixture dei test**
   (`test_fatturazione_job_helpers`). Togliere solo il primo lascerebbe un ramo
   morto che i test continuano ad accendere: un motivo che non può più esistere
   verrebbe ancora asserito come funzionante;
2. **`stato_commessa` cambia nome e natura.** La funzione DB ritorna
   `commessa_stato_codice_interno` **e** `commessa_stato_descrizione`. La prosa
   deve usare la **descrizione** (regola display-fields), il codice resta per la
   logica. È lo stesso difetto che avevamo corretto a mano nel tooltip della
   lista: qui sparisce alla radice;
3. **`gruppi_non_coperti` ha un consumatore FE.** Il toast dell'emissione
   parziale legge `gruppi_non_serviti` dall'esito del job. Cambiando la sorgente
   BE, il contratto verso il FE va tenuto **o cambiato con lui** — non lasciato
   a metà;
4. **Il caso `FATTURATO_ALTROVE` non ha un testo.** È un esito nuovo: senza una
   frase sua verrebbe raccontato come «non servito», cioè come un problema,
   mentre è lavoro fatturato. Serve una chiave i18n nuova.

### 10.4 Consuntivo — fatto, misurato

| # | Esito |
| --- | --- |
| 1 | ✅ Il driver **non misura più** nulla alla discovery: `gruppi_non_coperti` è sparito da `esegui_giro_fatturazione`. L'handler chiede `esito_gruppi_giro(lotti_prodotti)` e distingue i tre esiti. `NON_SERVITO` → diagnosi del perché (è il caso su cui si agisce); `FATTURATO_ALTROVE` → chiave sua e **nessuna diagnosi**, perché non c'è ostacolo da spiegare |
| 2 | ✅ Via la LATERAL su `vw_dash_fatturazione_documenti` **e** il `LEFT JOIN stati_commessa`. I test ora presidiano il **verso opposto**: che quelle risoluzioni non tornino (`assertNotIn`) |
| 3 | ✅ `diagnostica_gruppi` da ~90 righe di SQL a un wrapper: **−86 righe**. Ritirati `n_senza_tipo_doc` e `MOTIVO_TIPO_DOC_MANCANTE`; la prosa usa ora `commessa_stato_descrizione` |
| 4 | ✅ Docstring riallineata: dice che la diagnosi gira sul giro vuoto **e** sui non serviti di un parziale |
| 5 | ✅ Policy generata + **messaggio di ripiego** — vedi sotto |

**Il §10.3 ha fatto il suo lavoro: tutte e quattro le ricadute erano reali.** In
più ne è emersa una **quinta**, che nessuno aveva previsto: oltre alla policy,
un codice vivo deve avere un **messaggio di ripiego**
(`error_messages_fallback.py`), e un secondo presidio —
`test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` — lo pretende. Senza, il
codice risolve ma l'operatore legge una frase neutra che non parla del suo
problema: il degrado silenzioso che quel test esiste per impedire.

**Tre test hanno cambiato aspettativa, e nessuno è stato messo in baseline** —
fotografavano decisioni superate, non debito:

- due asserivano `BOZZA` nel messaggio: ora c'è `Bozza`, ed è la regola
  display-fields. Le asserzioni sono diventate `assertIn("Bozza")` **+
  `assertNotIn("BOZZA")`**, che presidia la scelta invece di subirla;
- il test del motivo «tipo documento mancante» è stato **rimosso**: accendeva un
  ramo irraggiungibile, cioè asseriva come funzionante un comportamento che il
  modello non produce più;
- i tre test di `gruppi_non_coperti` sono stati **rimossi con la funzione**, non
  lasciati a fotografare un meccanismo inesistente. Il consuntivo è coperto dove
  ora vive: nell'handler (7-bis e 7-ter).

**Verifiche eseguite** (misurate, non riferite):

- suite backend **3663 verdi**; build FE verde; lint pulito; guard i18n verde;
- **guardrail codici errore contro il DB reale** (`ZEROERP_TEST_DB_E2E=1`): da
  rosso a **verde**;
- le due funzioni nuove **provate sul DB vero** dal repository: la diagnostica
  torna le 13 chiavi del contratto nuovo (con `commessa_id` e le due dello
  stato); `fn_esito_gruppi_giro` su un lotto fuori scope **solleva**, che è il
  fail-closed del §9.2/F2 — mai un falso «non servito».

### 10.5 Cosa resta

- ~~🔴 **La prova in app di Tid** (§8.4)~~ ✅ **eseguita con successo il
  2026-08-16** — §12.6;
- ~~🟠 **la domanda del §10.6**, aperta e non risolta di nostra iniziativa~~
  ✅ **risposta dal DB** (§11, `terne_pronte`) e **consumata dal BE** (§12);
- ℹ️ il caso `E_FATTURAZIONE_MIRATA_TRONCATA` non è mai stato visto in esercizio
  (le mirate sono da pochi gruppi): la policy e il messaggio ci sono, la prova a
  video no. È dichiarato, non dimenticato.

### 10.6 🟠 Domanda al DB — una terna FALLITA finisce diagnosticata come problema di perimetro

> **Trovato** dalla review critica del codice appena scritto (2026-08-15, sera).
> **Non corretto di nostra iniziativa**, e il perché è il punto della domanda.

**Il fatto.** In un giro mirato **parziale** con una terna andata in errore, i
gruppi di quella terna hanno ancora righe da emettere: il consuntivo li
classifica — correttamente — `NON_SERVITO`. Noi però su ogni `NON_SERVITO`
facciamo girare la diagnosi di perimetro, che risponde con la causa più
prossima che vede: *«N attività risultano pronte ma il gruppo non è entrato in
nessun lotto: verificare emittente e utility della commessa»*.

Emittente e utility sono a posto. Il giro è fallito per un **lock transiente**,
o per un errore di pipeline. L'operatore viene mandato a controllare una cosa
giusta, e nel frattempo non sa che basta riprovare.

**Perché è la stessa regola che il codice già applica venti righe sopra.** Sul
giro **VUOTO** la distinzione c'è, ed è dichiarata:

> *terne trovate ma pipeline fallita (`falliti > 0`) → la causa vera è negli
> esiti per terna, e può essere TRANSIENTE: niente diagnosi di perimetro
> (racconterebbe la cosa sbagliata)*

Sul giro **PARZIALE** quella distinzione non c'è. Non è una svista di oggi: nel
parziale i lotti prodotti sono la prova che il perimetro era valido, quindi il
caso non si era mai presentato finché il «chi manca» era una previsione della
discovery. Con il consuntivo si presenta.

**Perché non l'abbiamo chiuso.** L'unico modo di sapere *quali gruppi*
appartenevano alla terna fallita è mappare `terna → gruppi`, e quella
mappa è `gruppi_coperti` della discovery — cioè la **previsione** che il §9.7 ha
chiesto di togliere, e che abbiamo tolto. Reintrodurla di nascosto per tappare
un caso raro significherebbe disfare in silenzio una decisione presa insieme
ieri. Preferiamo la domanda.

**Cosa ci servirebbe** (il *cosa*, il *come* è vostro), in ordine di quanto
costa:

1. **niente, e lo si dichiara**: il caso è raro, il messaggio è impreciso ma non
   dannoso, e si scrive nel codice perché il prossimo non lo scambi per un
   difetto. È una decisione legittima, va solo presa;
2. **poter distinguere, a consuntivo, «non servito perché il perimetro non lo
   ammetteva» da «non servito perché l'esecuzione si è rotta»**. Il primo è
   deterministico e si agisce sulla causa; il secondo è transitorio e si
   riprova. Oggi il consuntivo dice `NON_SERVITO` a entrambi, ed è corretto
   rispetto a ciò che misura — è la nostra prosa a valle che attribuisce una
   causa che non ha verificato;
3. se esistesse già un modo per legare un **fallimento di terna** ai gruppi che
   quella terna avrebbe servito, ci basterebbe saperlo: sopprimeremmo la
   diagnosi su quei gruppi, esattamente come già facciamo sul giro vuoto.

⚠️ **Nel frattempo non abbiamo messo un ripiego**, ed è voluto: un `if` che
sopprime la diagnosi quando `falliti > 0` spegnerebbe il messaggio **anche** sui
gruppi bloccati per davvero nello stesso giro — sostituendo un messaggio
impreciso con un silenzio, che è il difetto che questo intero cantiere ha
passato due settimane a togliere.

---

## 11. Risposta DB al §10.6 (2026-08-16)

> **Chi scrive:** team DB (`dev/db-tid`). La domanda era posta bene, e la
> reticenza a chiuderla da soli era la cosa giusta: il rimedio ovvio avrebbe
> disfatto in silenzio una decisione presa insieme il giorno prima.

### 11.1 La risposta breve: non serve una previsione, serve una misura

La corsia di un gruppo **non va prevista**. Si misura adesso: le righe ancora
pronte portano la terna con sé —

```text
commesse.emittente_soggetto_ruolo_id · commesse_attivita.tipo_doc_fiscale_id · commesse.utility_id
```

— e sono **esattamente** le tre colonne su cui `fn_list_emittibili_lane`
raggruppa. Non è «quale corsia la discovery pensava»: è «in quale corsia questo
lavoro **ricade**, in questo momento». `gruppi_coperti` resta dov'è, ritirato.

Dall'altra parte il pezzo mancante ce l'avete già: le terne **fallite** stanno in
`summary['esiti']` con `ok: false`, e sono fatti, non stime. Incrociando le due
cose la distinzione che chiedevate esce da sé:

| il gruppo è pronto e la sua corsia… | causa | cosa dire all'operatore |
| --- | --- | --- |
| **è fra le fallite** | l'esecuzione si è rotta, può essere transiente | «riprova» — e **niente** diagnosi di perimetro |
| **non è fra le fallite** | è davvero perimetro | la diagnosi che già componete, che dice il vero |

È la stessa distinzione che l'handler applica già sul giro **vuoto** («terne
trovate ma pipeline fallita → niente diagnosi di perimetro»), portata dove finora
non poteva arrivare.

### 11.2 Cosa è entrato

| ChangeSet | Cosa |
| --- | --- |
| `20260815-36` | `fn_diagnostica_gruppi_fatturabili` + **`terne_pronte jsonb`** — array di `{emittente_soggetto_ruolo_id, tipo_doc_fiscale_id, utility_id}` delle righe ancora pronte |

⚠️ **Perché nella diagnostica e non nel consuntivo.** Sembrava più naturale
metterlo in `fn_esito_gruppi_giro`, che i lotti del giro ce li ha già. Ma il
consuntivo **non conosce** i criteri di «riga pronta»: il suo
`n_attivita_residue` conta le sole `NON_EMESSA`, ed è deliberatamente ottuso
proprio per non ricopiare i filtri della lane. Dire «in quale corsia» avrebbe
richiesto `APPROVATA` + tipo documento + competenza, cioè importare lì quei
criteri — la duplicazione che questo cantiere ha passato due settimane a
togliere. Nella diagnostica ci sono già: sono quelli di `n_pronte`, il predicato
è scritto **una volta sola** e condiviso fra il contatore e la corsia, e la
corsia esce dalla stessa passata. Zero righe di regola in più.

⚠️ **Array e non tre colonne scalari.** Un gruppo può stare su più corsie perché
`tipo_doc_fiscale_id` sta sulla **riga**, non sulla testata (fatto G15 — è già il
motivo per cui l'esito verso di voi è una *lista* di `lotto_id`). Tre colonne
avrebbero dovuto sceglierne una arbitrariamente, o spaccare la grana in
`(gruppo, commessa, tipo_doc)` rompendo un contratto che avevate adottato lo
stesso giorno.

⚠️ **`[]` e mai `NULL`** quando non c'è nulla di pronto: «nessuna corsia» e «non
calcolato» devono restare distinguibili — la stessa ambiguità che il
`20260815-02` aveva già scelto di non creare su `gruppi_coperti`.

ℹ️ Cambia il `RETURNS TABLE`, quindi è servito un `DROP`. Chiamanti DB **zero**;
il vostro repository nomina le colonne una per una, quindi **non si rompe**: il
campo è **opt-in**, lo prendete aggiungendolo alla `SELECT`.

### 11.3 Verifiche

Provato in transazione sul DB vero, su gruppi reali: dove `n_pronte > 0` la
corsia esce ed è quella della commessa/riga; dove è zero l'array è `[]`.
Invariante controllata su **tutti** i gruppi del database più una chiave ignota:
`terne_pronte IS NULL` → 0 casi, `n_pronte = 0` con array non vuoto → 0 casi,
`n_pronte > 0` con array vuoto → 0 casi.

pgTAP: `test-diagnostica-gruppi-fatturabili` 11 → **12**. Il caso 12 fallisce
finché il changeSet non è applicato — è il rosso corretto.

### 11.4 Cosa serve da voi

> ✅ **Fatto il 2026-08-16** — consuntivo, correzioni della review e il punto
> sul ramo a vuoto nel **§12**.

1. **leggere `terne_pronte`** nella `SELECT` di `diagnostica_gruppi` e portarla
   in `GruppoDiagnosi`;
2. su un gruppo `NON_SERVITO` la cui corsia è fra le **terne fallite** del giro,
   **sopprimere la diagnosi di perimetro** e dire che si riprova — esattamente
   come già fate sul giro vuoto;
3. ⚠️ e la soppressione va fatta **per gruppo**, non per giro: il vostro §10.6
   lo dice già ed è il punto che rende la cosa non banale — un `if falliti > 0`
   globale spegnerebbe il messaggio anche sui gruppi bloccati sul serio nello
   stesso giro, sostituendo un messaggio impreciso con un silenzio.

ℹ️ **Opzione 1 del vostro §10.6 — «niente, e lo si dichiara» — scartata**: il
costo era una colonna in una funzione che quella passata la faceva già, e il
messaggio sbagliato manda una persona a controllare emittente e utility che sono
a posto. Fra dichiarare un difetto e toglierlo a quel prezzo, si toglie.

---

## 12. Consuntivo BE sul §11.4 (2026-08-16)

> **Chi scrive:** BE (`dev/backend-tid`). Chiude il residuo che il timbro di
> chiusura dichiarava, il giorno dopo che è stato dichiarato.

### 12.1 Cosa è stato fatto

| # | Richiesta §11.4 | Esito |
| --- | --- | --- |
| 1 | leggere `terne_pronte` e portarla in `GruppoDiagnosi` | ✅ colonna nella `SELECT` di `diagnostica_gruppi` + campo nel TypedDict |
| 2 | su un `NON_SERVITO` la cui corsia è fra le fallite, sopprimere la diagnosi di perimetro e dire che si riprova | ✅ motivo nuovo `ESECUZIONE_FALLITA`: «il perimetro è valido, si può rilanciare l'emissione su questo gruppo» |
| 3 | ⚠️ soppressione **per gruppo**, non per giro | ✅ il contesto entra nel classificatore, che decide riga per riga. Presidiato dal test `test_corsia_rotta_e_testata_bloccata_convivono_nello_stesso_giro` |

**Le terne fallite non sono una query nuova**: sono un fatto che il giro ha
appena registrato (`esiti` per terna, con `ok` False). Si leggono da lì — e
`_terne_fallite` va chiamata **prima** della compattazione del `result`, che
toglie `esiti`.

### 12.2 L'ordine dei rami è la regola

Nel classificatore il ramo nuovo sta **dopo** la testata bloccata e **prima** del
fallback, e non è un dettaglio:

- `terne_pronte` è popolata dal predicato di **riga** (`e_pronta`), che non
  guarda l'emittibilità della testata. Quindi anche una commessa in `BOZZA` ha
  la sua corsia elencata;
- se quella corsia si rompe per un'**altra** commessa della stessa terna, senza
  l'ordine giusto il gruppo bloccato si sentirebbe dire «riprova» — e riprovare
  non lo sbloccherebbe **mai**;
- una testata bloccata è una causa **certa** e vince comunque; la corsia rotta
  spiega il caso che restava, quello che prima cadeva nel fallback e si prendeva
  una causa di perimetro inventata.

Presidiato da `test_testata_bloccata_vince_sulla_corsia_rotta`.

### 12.3 ⚠️ Un difetto che solo la prova sul DB vero poteva trovare

`terne_pronte` è `jsonb`, e su questa connessione **psycopg la consegna come
STRINGA**, non come oggetto Python già decodificato. Scritta come
`list(valore or [])` — che è come l'avevo scritta — la stringa `'[]'` diventa
**`['[', ']']`**: due elementi finti dove il DB diceva «nessuna corsia».

I test con mock **non potevano vederlo**, perché un mock consegna già una lista:
sarebbero rimasti verdi su un comportamento inesistente. È emerso solo perché la
verifica è stata fatta anche contro il database reale, controllando l'invariante
«lista vuota ⟺ `n_pronte` = 0» — che rispondeva `False`.

Corretto con `_jsonb_lista`, lo stesso pattern già usato in
`core/db/email_repository` e `core/db/auth_repository`, e presidiato con **tre
test** che asseriscono esplicitamente il caso stringa, il caso `'[]'` e il caso
già-lista.

### 12.4 Verifiche

- suite backend **3674 verdi** (8 test nuovi: 4 sul classificatore, 1
  sull'handler, 3 sulla decodifica jsonb);
- `diagnostica_gruppi` provata **sul DB vero**: `terne_pronte` arriva come
  `list`, e l'invariante «lista vuota ⟺ `n_pronte` = 0» regge;
- build FE verde, guard i18n verde, gunicorn ricaricato.

### 12.5 Correzioni dalla review critica (2026-08-16, sera)

La review multi-finder sul codice del §12.1 ha trovato **e corretto** quattro
cose, una delle quali smentiva una frase di questo stesso documento:

1. ⭐ **Il §12.1 dichiarava la soppressione per-gruppo come chiusa, ma copriva
   solo il giro PARZIALE.** Sul giro a **vuoto** con `falliti > 0` il ramo
   per-errori-terna sollevava **prima** di ogni diagnosi — soppressione
   per-giro: una commessa in BOZZA nello stesso giro della corsia rotta
   restava muta, e il job non-terminale veniva ritentato 5 volte senza che
   nessuno la nominasse. La motivazione storica di quel ramo («la diagnosi
   racconterebbe la cosa sbagliata») era caduta proprio con `terne_pronte`:
   ora la diagnosi gira anche lì, le cause non-di-corsia entrano nel
   messaggio («Inoltre: …») e tutte nel context. Il test che fissava la
   decisione superata è stato riscritto, non messo a tacere;
2. **`not e.get("ok")` scambiava «chiave assente» per «fallito»**: gli esiti
   dry-run non hanno la chiave `ok`, e ogni corsia sarebbe risultata rotta →
   `e.get("ok") is False`;
3. **il testo affermava «il perimetro è valido»**, un claim che il codice non
   verifica (la corsia è condivisa fra commesse, il codice d'errore della
   terna non è ispezionato): riformulato su ciò che È misurato, con l'uscita
   onesta «se l'errore si ripete, verificare l'esito del giro»;
4. **il decoder jsonb del §12.3 era la quarta copia privata** del pattern — lo
   stesso file dichiara `_decode_jsonb` «unico punto di decodifica» 96 righe
   sopra, e il BB `jsonb_out` è a catalogo con «da usare in OGNI lettura raw».
   Sostituito, guadagnando anche il fail-soft sul percorso del giro a vuoto
   (un payload malformato non scavalca più il messaggio parlante).

   > ⚠️ **Aggiornamento 2026-10-28** (brief-modello-documento-vendita §15.17.3): `_decode_jsonb` è ritirato. Le letture per posizione usano il BB `jsonb_out` di `apps/core/db/_helpers.py`; le letture a dizionari (`row_to_dict`, `rows_to_list`, `fetch_paged_with_total`) decodificano i jsonb da sole.


Due rischi **dichiarati e non corretti**, con la ragione: il drift dei nomi
chiave della terna (verificato da test su entrambi i lati + pgTAP; il fail-fast
scavalcherebbe il messaggio parlante) e l'edge `fino_a_stato` anteriore
all'emissione via API diretta (fermata scelta dall'operatore, fallback
impreciso ma non dannoso).

### 12.6 ✅ La prova in app — eseguita con successo (2026-08-16)

**La catena è provata a video, su una commessa reale.** Tid ha percorso i cinque
passi su `CMM-20260610175449872-e059eb` (la commessa 108 del §1, una delle cinque
di giugno nate prima del ponte): lucchetto col motivo → riga non selezionabile →
«Fattura questo» disabilitato → «Sblocca commessa» → «Rendi pronta» → riga
selezionabile → emissione. **Il giro si chiude.**

⚠️ **La prova ha trovato un difetto che nessuna review aveva visto**, ed è
esattamente il genere di cosa per cui una prova in app esiste.

Ai primi tentativi «Rendi pronta» **non compariva affatto** nel drawer. Non era
un dato vecchio né una commessa incoerente: è il **gate del permesso**. Il verbo
sta dietro `cambia_stato_commessa`, e il gate FE — per convenzione di progetto —
**nasconde** il pulsante a chi non ha l'azione invece di disabilitarlo. Con
un'utenza SUPER_ADMIN (bypass totale) tutto si vede correttamente.

**Il difetto non è il permesso: è che ci portavamo l'operatore.** La sequenza
era: lucchetto → «Sblocca commessa» → *drawer senza il verbo*. Una via d'uscita
promessa e non mantenuta, che è **peggio di nessuna via d'uscita** — il vicolo
cieco lo si scopre solo dopo averlo imboccato. È la stessa classe di difetto che
questo brief ha passato due settimane a togliere, reintrodotta dalla scorciatoia
che doveva chiuderlo.

**Corretto lo stesso giorno**: «Sblocca commessa» compare solo a chi ha davvero
`cambia_stato_commessa`, e il tooltip del lucchetto ha **due voci** — a chi può
sbloccare indica il verbo, a chi non può dice che serve il permesso e di
chiedere a un amministratore. Nominare l'ostacolo vero invece di indicare una
porta chiusa.

### 12.7 ✅ Decisione di Tid — `rendi_pronta` resta gattato con le azioni terminali

Emersa dalla prova, e non è una svista di nessuno: è una **sovrapposizione di
date**.

- Il **2026-07-27** nasce `cambia_stato_commessa`, per **chiudi/annulla**: portano
  la commessa in uno stato *terminale irreversibile*, e gattarli è giusto. Il
  commento nel codice lo dice: «un solo codename per i tre verbi»;
- il **2026-08-04**, una settimana dopo, questo cantiere rende manuale
  `rendi_pronta` — che è l'**opposto**: non distrugge, **sblocca**. Ha ereditato
  un cancello disegnato per le azioni irreversibili.

**Conseguenza pratica**: un operatore che può fatturare (`genera_fatture_lotti`)
ma non cambiare stato vede il lavoro bloccato, ne legge il motivo, e non può
farci niente — deve chiedere a un altro. Può essere **esattamente ciò che si
vuole** (sbloccare una commessa è una decisione di governo, non un gesto
operativo) oppure un effetto collaterale non voluto.

Le due strade erano: lasciare com'è, oppure separare i codename — che significa
un'azione di processo nuova a catalogo, quindi lavoro DB e un brief.

> 🟢 **DECISO da Tid il 2026-08-16: si lascia com'è.** Sbloccare una commessa è
> una decisione di **governo**, non un gesto operativo: è corretto che chi
> fattura debba passare da chi governa. Nessun brief al DB, nessuna azione di
> processo nuova.

**Cosa comporta, scritto perché non si riapra fra sei mesi**: un operatore con
`genera_fatture_lotti` ma senza `cambia_stato_commessa` vede il lavoro bloccato,
ne legge il motivo, e **chiede a chi ha il permesso**. Il comportamento è
onesto — non vede una scorciatoia che non porta da nessuna parte, e il tooltip
gli dice che serve il permesso — quindi non è un difetto da correggere: è la
divisione dei ruoli, resa visibile.

⚠️ **Se un giorno si volesse cambiare idea**, la strada è quella scartata oggi:
un'azione di processo dedicata (es. `rendi_pronta_commessa`) a catalogo DB, e il
gate FE che punta a quella invece che a `cambia_stato_commessa`
(`DashboardCompetenzaView` e `CommessaGestioneDrawer`). Non è un lavoro grande —
è una decisione, ed è già stata presa.

### 12.8 Cosa resta

- ℹ️ il messaggio nuovo (`ESECUZIONE_FALLITA`) non è mai stato visto a video: per
  vederlo serve una corsia che si rompe davvero durante un giro parziale, che è
  un caso raro. Il percorso è coperto dai test, la prova a video no — dichiarato,
  non dimenticato;
- ~~🟠 la domanda del §12.7~~ ✅ **decisa il 2026-08-16**: si lascia com'è (§12.7).

🟢 **Nessun residuo aperto: il cantiere è chiuso per intero.** Questo documento
non ha più voci in sospeso — l'unica nota rimasta è informativa e dichiarata.
