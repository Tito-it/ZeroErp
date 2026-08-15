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

> 📌 **Stato al 2026-08-15, sera** (rimisurato, non riferito). Tutte le richieste
> originali (§3) sono chiuse, DB e video. Chiuse oggi, in ordine: le sei decisioni
> R1 del §7.3 (cantiere vie d'uscita), il verbo «Rendi pronta» (§6),
> **`gruppi_coperti`** (`20260815-02`, §5 — ultima voce DB), e nel pomeriggio la
> **segnalazione della riga bloccata in dashboard** più l'**adozione BE/FE di
> `gruppi_coperti`**: lucchetto+sblocco in lista, emissione parziale parlante
> (§6, §7.5, consuntivo nel **§8.1**).
>
> **Il brief però non è chiuso**, e la coda è cambiata di natura: da «cosa manca
> del piano» a «cosa il piano ha scoperto». Restano **la prova in app di Tid**
> (§8.4, l'unica che nessuno può fare al posto suo) e **due richieste nuove al
> DB** nate lavorando: `gruppi_coperti` è una *previsione* e serve un
> **consuntivo** del servito (**§8.2**, 🔴), e la descrizione dello stato commessa
> nelle due viste (**§8.3**, 🟠, non bloccante).

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
- [ ] **La prova che il giro si chiude**: sbloccare una commessa dall'interfaccia e
      fatturarne le attività, **una volta**.
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

- 🔴 **La prova in app di Tid** — sbloccare una commessa dall'interfaccia e
  fatturarne le attività, una volta. È l'unica voce del §6 ancora senza spunta,
  ed è l'unica che nessuno può fare al posto suo;
- 🟠 le due richieste qui sopra;
- ℹ️ il **dettaglio dei motivi è prosa italiana del BE** anche in locale EN
  (stesso trade-off già accettato per `ultimo_errore.message`): non lo tocchiamo
  in questa slice, ma è scritto perché non venga scambiato per una svista.
