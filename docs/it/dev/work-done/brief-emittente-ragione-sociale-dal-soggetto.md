# Brief DB/BE/FE — la ragione sociale dell'emittente viene dal soggetto

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-01.
> **A chi:** BE e FE (`dev/backend-tid`) — questo brief è **unico** perché la
> modifica non è divisibile: la colonna sta nel DB, i lettori sono in Python e
> in SQL, e l'ultimo miglio è a video.
> **Cos'è:** la proposta di eliminare `anagrafiche.emittenti_fiscali.descrizione`
> e far leggere ovunque la ragione sociale del **soggetto** associato.
> **Stato (agg. 2026-08-02): CHIUSA.** Decisione di Tid — **si toglie**. Tutte e
> quattro le fasi eseguite: DB (Fase 1 e 4, commit `4052c6d4e`), BE/FE (Fase 2 e
> 3, commit `b7f4695cd` + la cerniera successiva). La colonna **non esiste più**,
> i cinque criteri di §6 sono soddisfatti e **Tid ha validato a video il
> 2026-08-02**. Unico strascico, non un difetto di questo cantiere: il **caveat
> di copertura pgTAP** in §10.5, che resta al team DB. Il capitolo operativo è
> **§10** — le sezioni 1-9 restano come scritte, con due rettifiche di misura
> segnalate in loco.

---

## 0. Da dove nasce, perché non è una pulizia estetica

Non l'abbiamo cercata. È emersa il 2026-08-01 seedando il **sesto lotto** delle
liste configurabili
([piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md)): il controllo
di consegna ha dato `NUCLEO rotto: ragione sociale` su
`anagrafiche.categorie_clienti_listini`, perché la colonna
`emittente_ragione_sociale` era visibile ma non ordinabile.

Sembrava una voce di whitelist da chiedere — una riga. Verificandola è venuto
fuori che **quella** colonna è a posto (legge `s.ragione_sociale` dal soggetto),
ma che accanto ne vive un'altra che fa la stessa cosa in modo diverso e
sbagliato. La domanda di Tid è stata la chiave: *«un emittente fiscale non è
legato al soggetto uno a uno? Allora quella colonna è inutile.»*

Lo è. E la prova non è un'opinione: è nei vincoli.

---

## 1. Il problema, e la prova che non è teorico

`anagrafiche.emittenti_fiscali` ha una colonna `descrizione`, `NOT NULL`, a
testo libero. Accanto, tramite `soggetto_ruolo_id`, ha la ragione sociale del
soggetto. **I due valori divergono su tutti gli emittenti in tabella:**

| `codice` | `descrizione` dell'emittente | ragione sociale del soggetto |
|---|---|---|
| `PGTAP-EF-20260126172242554` | Emittente fiscale test 1 | Gestore Test pgTAP |
| `EMI-TEST` | TEST | Azienda SC REQUIRED con dati |

**2 su 2.** Non è deriva accidentale fra due copie dello stesso dato: è un campo
che non ha mai avuto niente a che fare con la ragione sociale, e che nessuno ha
mai allineato perché nessuno ha mai deciso che dovesse esserlo.

### 🔴 Il punto che alza la priorità: finisce su un documento

`offerta_document_context_builder.py:134` mette `emittente_fiscale_descrizione`
nel contesto di stampa dell'**offerta commerciale**:

```python
"emittente_fiscale": {
    "id":          testata.get("emittente_fiscale_id"),
    "codice":      testata.get("emittente_fiscale_codice"),
    "descrizione": testata.get("emittente_fiscale_descrizione"),   # <-- qui
},
```

Cioè un documento che va al cliente può portare **«TEST»** al posto di
«Azienda SC REQUIRED con dati».

È la stessa famiglia del difetto che il cantiere intestazione fattura ha appena
chiuso — dove la denominazione la prendiamo da `ragione_sociale_completa` del
soggetto, che è la scelta giusta, e dove abbiamo scritto che *tutto ciò che il
documento stampa è congelato dal documento*. Sull'offerta quella regola non c'è
ancora, e la sorgente è pure quella sbagliata.

**Non è quindi un problema estetico di nove liste: è un documento che può
stampare un'etichetta interna al posto della ragione sociale.**

> ⚠️ **Rettifica di misura (BE, 2026-08-02) — il rischio non era attivo.**
> `testata["emittente_fiscale_descrizione"]` non arriva da `ef.descrizione`:
> arriva da `_SELECT_COLS_OFFERTA` (`offerte_repository.py:158`), che dal
> 2026-07-13 proietta `COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)`.
> L'offerta stampava **già** la ragione sociale del soggetto; «TEST» sarebbe
> uscito solo con `ragione_sociale_completa` NULL, caso che §3 misura come
> inesistente (26/26 piene).
>
> La colonna era davvero fra i lettori — ma **come ramo di fallback**, non come
> sorgente. La lezione è quella di
> [[feedback_whitelist_dal_percorso_reale]]: il difetto non stava nella colonna,
> stava nel percorso, e il percorso era già stato sistemato da un altro
> cantiere. Prima di dichiarare urgente un punto di stampa, leggere la query che
> alimenta il dict, non solo la riga che lo compone.
>
> Questo **non** indebolisce la proposta: il fallback è comunque codice che
> tiene in vita una colonna sbagliata, e §7 dice giustamente che non lo
> vogliamo. Sposta solo la Fase 2.2 da «urgenza» a «pulizia», ed è la ragione
> per cui l'ordine BE+FE→DROP si è potuto seguire con calma.

### La prova che il problema era già stato sentito

In `core/composables/useEmittenteFiscaleField.js` il display dell'emittente è
composto così:

```js
export function formatEmittenteOptionLabel(opt) {
  const main = opt.ragione_sociale || opt.descrizione || ''
  ...
}
```

**C'è già un fallback**: qualcuno aveva notato che `descrizione` non è il nome
giusto e ha messo davanti la ragione sociale — ma a **livello di display**, che
è l'ultimo posto in cui si può rimediare e l'unico che non risolve niente a
monte. Infatti:

- dove l'opzione arriva dal **lookup admin**, `ragione_sociale` c'è (il
  repository proietta già `s.ragione_sociale_completa`) e a video si vede la
  cosa giusta;
- dove arriva dal **record denormalizzato in edit**, c'è solo
  `emittente_fiscale_descrizione` e si vede quella sbagliata.

Cioè **lo stesso campo, nello stesso componente, mostra due valori diversi a
seconda da dove è passato**. Quel `|| opt.descrizione` è il residuo che questo
cantiere esiste per poter togliere: finché serve, vuol dire che a monte la
sorgente non è unica.

---

## 2. Perché quella colonna non può avere lo scopo che sembra avere

L'unica giustificazione plausibile per un'etichetta separata sarebbe
**distinguere più emittenti dello stesso soggetto** (es. «sede di Milano»,
«sede di Roma»). Misurato sui vincoli, non sui dati:

```
anagrafiche.emittenti_fiscali : UNIQUE (soggetto_ruolo_id)
anagrafiche.soggetti_ruoli    : UNIQUE (soggetto_id, tipo_ruolo_id)
```

Concatenati: **un soggetto ha al massimo un ruolo `EF`, e quel ruolo al massimo
un emittente fiscale.** L'uno-a-uno è imposto dal database, non è una
convenzione che può cambiare domani.

Quindi lo scenario «due emittenti dello stesso soggetto» **non è
rappresentabile**, e con esso cade l'unica ragione d'essere di una descrizione
propria. Quel che resta è un campo obbligatorio che duplica un valore
derivabile — e che, come mostra §1, diverge.

---

## 3. Cosa la sostituisce, e perché **non** `ragione_sociale`

La sostituzione naturale sembrerebbe `soggetti.ragione_sociale`. **Non è
quella, e non è una sfumatura.** Misurato su tutti i `soggetti_ruoli`:

| Campo | Vuoto o NULL | Su |
|---|---|---|
| `vw_soggetti_ruoli_dettaglio.ragione_sociale_completa` | **0** | 26 |
| `soggetti.ragione_sociale` | **11** | 26 |

Su una **persona fisica** `ragione_sociale` non è *diversa*: è **vuota** — il
nome sta in `nome`/`cognome`, e `ragione_sociale_completa` è il campo che li
compone. Sono 11 casi su 26, il 42%.

⚠️ `soggetti.ragione_sociale` è **nullable**. Chi ripuntasse un lettore lì
otterrebbe **11 etichette bianche su 26** — e non se ne accorgerebbe subito,
perché i due emittenti attuali sono entrambi società e lì il campo è pieno. È il
difetto che comparirebbe al primo emittente **ditta individuale o
professionista**: caso non ipotetico, è lo stesso per cui il brief intestazione
ha incluso `RES` nella matrice indirizzi del ruolo `EF`.

➡️ **La sorgente canonica è `vw_soggetti_ruoli_dettaglio.ragione_sociale_completa`**,
la stessa che `vendite.fn_snapshot_intestazione_fattura` usa già per congelare
la denominazione dell'emittente sulla fattura. Scegliere quella significa che
fattura, offerta e liste diranno **lo stesso nome**, che è metà del punto.

⚠️ Chi ripunta un lettore su `s.ragione_sociale` invece che sulla vista fa un
lavoro che sembra giusto e che sulle società funziona: il difetto comparirebbe
solo il giorno del primo emittente persona fisica. Vale la pena dirlo una volta
qui invece di scoprirlo lì.

---

## 4. L'inventario dei consumatori — misurato, non stimato

| Strato | Quanti | Dove |
|---|---|---|
| **Funzioni DB** | 3 | `script.fn_get_operatore_detail`, `script.fn_get_user_emittenti_scope`, `script.fn_get_user_profile` |
| **Viste DB** | 6 | `vendite.vw_contratti_lista`, `vw_ddt_lista`, `vw_offerte_commerciali_lista`, `vw_ordini_lista`, `vw_preventivi_lista`, `vw_resi_lista` |
| **Python** | 42 occorrenze in 19 file | repository di `vendite` (contratti, ordini, offerte, DDT, preventivi), `documenti`, `anagrafiche`, `pratiche`, `amm_software`, `ui`, `config` · `types.py` di `vendite` e `documenti` · `offerta_document_context_builder` · 4 file di test |
| **Frontend** | 4 file | `EmittenteFiscaleField.vue`, `DdtForm.vue`, `TemplateDocumentoDrawer.vue`, `TemplateAssetDrawer.vue` |
| **Liste seedate** | 9 | contratti (4), preventivi (5), offerte (6), ordini (7), DDT (8), resi (9), emittenti fiscali (18), template documenti (24), template asset (25) |

Le sei viste sono il moltiplicatore: **una riga di vista serve un'intera lista**,
quindi il grosso del lavoro DB è concentrato lì e non nei 42 punti Python — molti
dei quali si limitano a trasportare l'alias.

---

## 5. Le attività, per strato e in ordine obbligato

L'ordine **non è negoziabile**: la DROP è l'ultimo passo. Invertirlo spegne nove
liste e un documento nello stesso istante.

### Fase 1 — DB: cambiare la sorgente, non il nome (owner DB)

> ⚠️ **Rettifica di misura (BE, 2026-08-02) — la Fase 1 è già in piedi per tre
> quarti, dal 13 luglio.** Le 6 viste `vw_*_lista` proiettano già
> `COALESCE(s_ef.ragione_sociale_completa, ef.descrizione)` — migration
> `20260713-06..09`, `20260713-33`, poi le `20260715-*` del lineage, dal brief
> `brief-db-ddt-emittente-user-e-etichetta-soggetto.md`. Idem
> `script.fn_get_user_emittenti_scope` e `script.fn_get_operatore_detail`.
> **Resta scoperta una sola funzione**: `script.fn_get_user_profile`, che legge
> `ef.descrizione AS emittente_descrizione` secco (due rami della union interna,
> poi la chiave `emittente_descrizione` del blocco `emittente`).
>
> Quindi la 1.1 non è «cambiare la sorgente» ma **togliere il ramo di
> fallback**, che §7 non vuole. Dettaglio operativo in §10.3.

| # | Attività |
|---|---|
| 1.1 | Le **6 viste** `vw_*_lista` proiettano `emittente_fiscale_descrizione` da `ragione_sociale_completa` invece che da `ef.descrizione`. **L'alias resta identico**: nessun lettore a valle si accorge di niente, ed è ciò che rende questa fase invisibile e reversibile |
| 1.2 | Le **3 funzioni** `script.fn_get_*` idem |
| 1.3 | pgTAP: per ogni vista, l'alias corrisponde alla ragione sociale del soggetto e **non** a `ef.descrizione` — con una fixture in cui i due valori **divergono di proposito**, altrimenti il test passa senza provare niente |

> 💡 **Perché l'alias non si rinomina.** Rinominarlo sarebbe più onesto
> (`emittente_ragione_sociale`), ma trasformerebbe una fase invisibile in un
> breaking su 42 punti Python e 4 FE. La rinomina, se la si vuole, è una **fase
> separata e successiva** — e a quel punto è puramente meccanica.

### Fase 2 — BE: i lettori che non passano dalle viste (owner BE)

| # | Attività |
|---|---|
| 2.1 | Censire quali dei 19 file leggono `ef.descrizione` **direttamente** e non tramite le viste di 1.1: quelli vanno ripuntati a mano |
| 2.2 | 🔴 **`offerta_document_context_builder.py:134`** — è il punto urgente. Il contesto di stampa deve portare la ragione sociale del soggetto. **Si può fare subito, indipendentemente dal resto del cantiere**, ed è l'unica attività che toglie un rischio già attivo |
| 2.3 | `types.py` di `vendite` e `documenti`: se il campo cambia semantica, il commento del TypedDict va allineato — è la documentazione che i chiamanti leggono per prima |
| 2.4 | I 4 test che asseriscono su `emittente_fiscale_descrizione`: le fixture vanno riviste perché oggi con ogni probabilità valorizzano solo `ef.descrizione` |

### Fase 3 — FE: l'ultimo miglio (owner FE)

| # | Attività |
|---|---|
| 3.1 | 🎯 **Togliere il fallback su `descrizione`** da `formatEmittenteOptionLabel` (`core/composables/useEmittenteFiscaleField.js`, il ramo `or opt.descrizione`). È **l'ultimo passo, non il primo**: finché anche un solo percorso porta la sola `descrizione`, toglierlo produce etichette vuote. Quando si può togliere senza rompere niente, il cantiere è finito — è la definizione di «fatto» del FE, più affidabile di qualunque verifica a video |
| 3.2 | Il percorso **edit** di `EmittenteFiscaleField.vue`: oggi sintetizza l'opzione dal record denormalizzato (`emittente_fiscale_descrizione`) mentre il percorso **create** usa il lookup, che ha già `ragione_sociale_completa`. È qui che nasce l'asimmetria di §1 — stesso componente, due valori diversi |
| 3.3 | `DdtForm.vue`, `TemplateDocumentoDrawer.vue`, `TemplateAssetDrawer.vue` |
| 3.4 | Verifica a video sulle **9 liste** seedate: dopo la Fase 1 devono mostrare la ragione sociale **senza che nessuno abbia toccato il seed** — se serve toccarlo, la Fase 1 non ha fatto il suo lavoro |

### Fase 4 — DB: la DROP, solo quando le prime tre sono verdi (owner DB)

| # | Attività |
|---|---|
| 4.1 | Censimento finale: **zero** lettori di `ef.descrizione` in `backend/`, `frontend/src`, funzioni e viste |
| 4.2 | `DROP COLUMN anagrafiche.emittenti_fiscali.descrizione` + adeguamento di `fn_crea_emittente_fiscale` / `fn_update_*` se la scrivono |
| 4.3 | Seed `lista_colonna` della **lista 18** (emittenti fiscali): oggi mostra e ordina per `descrizione`; deve passare alla ragione sociale, e con lei `ordinamento_default` del preset |
| 4.4 | pgTAP: la colonna non esiste più; i test che la valorizzavano sono rimossi |

#### ✅ ESEGUITA il 2026-08-02 — e il censimento di 4.1 era incompleto in due punti

Changeset `20260802-22` (DROP) e `20260802-23` (lista 18) applicati; pgTAP
`anagrafiche/test-emittente-denominazione-da-soggetto-v1.sql` `plan(13)` verde;
baseline `anagrafiche script vendite documenti pratiche rls config` senza
regressioni. Il censimento 4.1 è stato riscritto come **precondizione** del
changeset invece che come controllo manuale: un censimento fatto a mano è vero
una volta, una precondizione si rifà a ogni apply su ogni ambiente.

🔴 **Due categorie di lettore che 4.1 non prevedeva**, entrambe invisibili a un
`grep` della colonna:

1. **I `%TYPE`.** `fn_get_user_profile` dichiarava
   `v_ef_descrizione anagrafiche.emittenti_fiscali.descrizione%TYPE`. Non
   somiglia a una lettura, ma blocca la DROP esattamente come una `SELECT`.
   Ci è caduto dentro il pattern testuale per fortuna, non per progetto.
2. ⭐ **I consumatori GENERICI, ed è la scoperta che vale.**
   `script.fn_get_entita_ruolo_detail` non nomina mai la colonna: introspeziona
   `config.tipi_ruoli.entita_tabella` ed emette in JSONB tutte le colonne non
   di sistema. Il suo test asseriva che la riga dell'emittente avesse `codice`
   **e `descrizione`** — cioè descriveva la *forma della tabella*, non un
   contratto. **Nessun grep poteva trovarlo**, perché il nome della colonna
   nel codice non compare: si scopre a runtime. L'unica cosa che l'ha visto è
   stata la **suite pgTAP** girata contro la baseline.

   ➡️ Regola che ne esce, valida per ogni DROP futura: **il censimento
   testuale non copre i lettori che leggono lo schema invece del nome.** Dopo
   una DROP la suite completa non è una verifica di cortesia, è l'unico
   strumento che vede quella categoria.

⚠️ Il pattern della precondizione va tenuto **stretto** (`ef\.descrizione`,
`emittenti_fiscali\.descrizione`) e i commenti vanno tolti da `prosrc` prima di
cercare. Entrambe le lezioni sono state pagate in giornata con due falsi
allarmi: la stringa che sopravvive nelle note che spiegano la rimozione, e
l'alias nudo `e` che aggancia tabelle estranee.

---

## 6. Definizione di «fatto»

1. Un emittente il cui soggetto ha ragione sociale **diversa** dalla vecchia
   `descrizione` compare con la **ragione sociale** su tutte e 9 le liste;
2. l'**offerta commerciale** stampata riporta la ragione sociale del soggetto;
3. un emittente **persona fisica** (ditta individuale) compare col nome
   completo — è il caso che distingue `ragione_sociale_completa` da
   `ragione_sociale`, e senza questo test la scelta di §3 non è dimostrata;
4. `grep -r "ef\.descrizione\|emittenti_fiscali.descrizione"` su tutto il repo:
   **zero**;
5. la colonna non esiste più, e la suite pgTAP è verde senza righe rimosse per
   comodità.

---

## 7. Cosa **non** chiediamo

| Cosa | Perché no |
|---|---|
| Bonificare i dati storici | Non serve: la colonna sparisce, non si allinea |
| Rinominare l'alias `emittente_fiscale_descrizione` | Fase separata (§5 Fase 1): mescolarla qui trasforma una modifica invisibile in un breaking su 46 punti |
| Toccare `emittenti_fiscali.codice` | È l'identificativo stabile e va benissimo dov'è |
| Un fallback «se la ragione sociale è vuota usa la descrizione» | La sorgente scelta (`ragione_sociale_completa`) è **piena su 26 soggetti_ruoli su 26**: il fallback coprirebbe un caso che non esiste, e sarebbe codice che nasce da rimuovere. ⚠️ Vale **solo** per quella sorgente — su `soggetti.ragione_sociale` un fallback servirebbe eccome, ed è un'altra ragione per non usarla (§3) |

---

## 8. Le decisioni che servono prima di partire

1. **Si toglie o si tiene?** Se si tiene, va detto **a quale scopo** — perché
   §2 dimostra che non può essere «distinguere emittenti dello stesso soggetto».
   L'unica alternativa sensata sarebbe rinominarla in qualcosa che dica cos'è
   davvero (`nota_interna`?) e toglierla da tutte le proiezioni verso i
   documenti. È una decisione di modello, non di implementazione.
2. **La Fase 2.2 (offerta) si può anticipare?** Per noi sì, ed è l'unica cosa
   che toglie un rischio già attivo. Non dipende dalla DROP.
3. **Chi tiene la regia?** Le quattro fasi hanno owner diversi e un ordine
   obbligato: serve che qualcuno dica «la Fase 1 è verde, partite con la 2».

---

## 9. Nota di metodo, perché si ripeta

Questa modifica non è stata trovata leggendo il codice: è stata trovata da un
**controllo automatico** (`--verifica-ordinamento`, regola del nucleo) che
segnalava una colonna non ordinabile su una lista. Da lì, una domanda di dominio
di Tid — *«non è uno a uno?»* — ha trasformato una richiesta di whitelist da una
riga in un difetto di modello con un documento sbagliato dentro.

Vale la pena notare che **nessuno dei due da solo bastava**: il controllo non
sapeva che la colonna fosse concettualmente sbagliata, e la domanda non sarebbe
stata fatta se il controllo non avesse messo il dito lì.

---

## 10. Esecuzione — stato al 2026-08-02 (scrive BE/FE)

### 10.1 Le decisioni di §8, prese

| # | Domanda | Decisione (Tid, 2026-08-02) |
|---|---|---|
| 1 | Si toglie o si tiene? | **Si toglie.** DROP come da §5 Fase 4 — niente rinomina in `nota_interna` |
| 2 | La 2.2 si anticipa? | Domanda superata: il rischio non era attivo (rettifica in §1). Fatta comunque insieme al resto |
| 3 | Regia | BE/FE eseguono per primi, senza aspettare nulla; il DB chiude con fallback + seed + DROP |

**Perché BE/FE è potuto partire subito**, contro l'abitudine di aspettare i
prerequisiti DB: ripuntare quei `SELECT` su `soggetti.ragione_sociale_completa`
usa join già disponibili e alias invariati. Non c'era niente da attendere, e
l'ordine di §5 («la DROP è l'ultimo passo») è rispettato per intero.

### 10.2 Fase 2 (BE) e Fase 3 (FE) — FATTE

**I lettori diretti ripuntati** (mostravano l'etichetta interna a video):

| File | Cosa |
|---|---|
| `pratiche/db/definizioni_repository.py` | `_DEFINIZIONE_SELECT`: `emittente_display` da `s_ef.ragione_sociale_completa` + join `soggetti_ruoli`/`soggetti`. Alimenta la colonna Emittente di *Definizioni workflow* (ordinabile) |
| `config/db/utilities_tipi_ruolo_repository.py` | `emittente_descrizione` e l'`ORDER BY` della lista usage. I due join stanno in `_USAGE_FROM_WHERE` (condiviso con la count): sono 1:1 su PK, la cardinalità non cambia |
| `ui/db/ui_admin_repository.py` | `_PRESET_SELECT_SQL` dei preset lista (Blocco F) |
| `amm_software/db/amm_software_repository.py` | `list_emittenti_fiscali`: `ef.descrizione` tolta dalla proiezione **e** dal tiebreaker d'ordine (ora `ef.codice`) |

**I fallback `COALESCE(..., ef.descrizione)` rimossi** — §7 non li vuole, e con
la DROP in arrivo sarebbero comunque diventati un errore a runtime: 2 punti in
`documenti_repository`, 1 in `contratti_repository`, 1 in `offerte_repository`,
1 in `preventivi_repository`, 1 nella `string_agg` degli emittenti in
`amm_software_repository`.

**Documentazione del tipo** (2.3): il commento di `emittente_fiscale_descrizione`
in `vendite/types.py` (`PreventivoDetailRow`, `OffertaRow`) e in
`documenti/types.py` dice ora a chiare lettere che l'alias porta la ragione
sociale del soggetto e che la rinomina è una fase separata. È la prima cosa che
legge chi arriva dopo.

**Test (2.4): nessuna fixture da rivedere.** I 5 punti che asseriscono su
`emittente_fiscale_descrizione` o sono assert sull'alias nel SQL (invariato) o
sono dict con ragioni sociali plausibili («Acme SRL», «Azienda Emittente Spa»).
La previsione di §5 non si è verificata.

**Fase 3 (FE)** — l'ordine di §3.1 è stato rispettato: il fallback è stato
tolto **dopo** aver verificato che tutte e tre le sorgenti portano
`ragione_sociale`.

| File | Cosa |
|---|---|
| `core/composables/useEmittenteFiscaleField.js` | 🎯 tolto il ramo `or opt.descrizione` da `formatEmittenteOptionLabel` — la definizione di «fatto» del FE secondo §3.1 |
| `core/components/EmittenteFiscaleField.vue` | tolta la chiave `descrizione` duplicata da `recordAsOption` e `operatoreAsOption`: era una copia dello stesso valore, viva solo grazie al fallback |
| `stores/auth.js` · `core/components/AppTopbar.vue` | tolto `?? emittente_descrizione`: il blocco `emittente` del profilo porta sempre `ragione_sociale_completa` (merge con `fn_get_soggetto_dati_by_ruolo`) — era codice morto |
| `amministrazione/components/UtilityTipoRuoloDrawer.vue` + locali IT/EN | header colonna da *Descrizione* a **Ragione sociale**: l'alias del payload resta, ma l'etichetta a video deve dire cosa mostra |

⚠️ **§3.3 era un falso bersaglio**: `DdtForm.vue`, `TemplateDocumentoDrawer.vue`
e `TemplateAssetDrawer.vue` non leggono `ef.descrizione` — **trasportano**
l'alias verso `EmittenteFiscaleField`, e la loro sorgente
(`documenti_repository`) era già corretta. Nessuna modifica necessaria.

**Verifica**: **3444 test BE verdi**, lint e build FE puliti, locali IT/EN
simmetrici (3651 chiavi per parte).

⚠️ **Ma le 3444 girano a DB mockato e non provano una riga di SQL.** Le query
toccate sono state quindi eseguite contro il **DB reale**, in sola lettura,
compreso l'`ORDER BY` sull'alias ripuntato — che è il punto cieco tipico
([[feedback_whitelist_dal_percorso_reale]]: la freccia c'è, e al click ripiega
in silenzio). Esito, sui due emittenti che §1 citava come divergenti:

| Query | Esito |
|---|---|
| `documenti.list_templates` / `list_asset`, `ORDER BY emittente_fiscale_descrizione` | 6 e 1 righe, ordina, valore «Gestore Test pgTAP» |
| `utilities_tipi_ruolo.list_emittenti_usage` | `PGTAP-EF-…` → «Gestore Test pgTAP» (era «Emittente fiscale test 1») |
| `pratiche.list_definizioni` | `emittente_fiscale_id=44` → «Azienda SC REQUIRED con dati» (era «TEST») |
| `amm_software.list_emittenti_fiscali` | 2 righe, nessuna `descrizione` in payload |
| `ui_admin.list_preset_by_lista(18)` | 1 riga, join preset↔soggetto ok |

I due valori sbagliati della tabella di §1 sono spariti dal video: è la
dimostrazione diretta del criterio 6.1, non un'inferenza dal codice.

> 💡 Per la validazione in-app serve `kill -HUP` sul master gunicorn: il BE di
> sviluppo non ha autoreload ([[project_backend_gunicorn_reload]]).

### 10.3 Cosa resta, e a chi

**Owner DB — Fase 1 residua** (indipendente, si può fare subito):

1. Togliere il ramo `ef.descrizione` dal `COALESCE` delle **6 viste**
   `vw_*_lista` e delle **2 funzioni** `fn_get_user_emittenti_scope` /
   `fn_get_operatore_detail`: resta la sola `ragione_sociale_completa`.
2. `script.fn_get_user_profile`: è l'unico lettore DB ancora **senza**
   `COALESCE`. Due rami della union interna proiettano `ef.descrizione AS
   emittente_descrizione` e la variabile finisce nella chiave
   `emittente_descrizione` del blocco `emittente`. Il FE non la legge più
   (10.2), quindi la chiave può sparire con la colonna.
3. pgTAP §5 1.3: la fixture deve far **divergere di proposito** i due valori,
   altrimenti il test passa senza provare niente.

**Owner DB + BE insieme — la cerniera, ed è l'unico punto che va sincronizzato.**
`anagrafiche/db/emittenti_fiscali_repository.py` è rimasto volutamente indietro:
è la lista 18 e il drawer dell'emittente stesso, dove `descrizione` è una
colonna **mostrata, ordinabile, ricercabile e scritta** (è `NOT NULL`). Toccare
una sponda sola rompe qualcosa in entrambi i versi:

| Se si fa prima… | Cosa si rompe |
|---|---|
| il BE (tolgo `descrizione` da whitelist/SELECT/search) | la colonna 261 del seed resta e la lista 18 mostra una colonna vuota |
| la DROP | il `SELECT ef.descrizione` del repository va in errore, e il drawer non può più creare un emittente |

Sequenza senza stati rotti, **in tre battute**:

1. **DB** — seed `lista_colonna`: via la riga `261` (`descrizione` della lista
   18) e `ordinamento_default` del preset `18` da `descrizione` a
   `ragione_sociale` (§5 4.3). È revisione di righe CSV, i loader sono
   `runOnChange` (cf. `piano-migrazione-primevue-5.md` §8-bis);
2. **BE/FE** — `emittenti_fiscali_repository` (whitelist `_EMITTENTI_ORDER_COLS`,
   proiezione lista + dettaglio, `ILIKE` di ricerca) e il drawer emittenti che
   scrive il campo;
3. **DB** — `DROP COLUMN` + adeguamento di `fn_crea_emittente_fiscale` /
   `fn_update_*` + pgTAP (§5 4.2/4.4).

### 10.4 La Fase 1 residua e la Fase 4 — FATTE dal DB (`4052c6d4e`)

Consegnato tutto quanto chiesto in 10.3: fallback tolto dalle 6 viste e dalle 2
funzioni, `fn_get_user_profile` allineata, seed della lista 18 (via la riga
`261`, preset su `ragione_sociale_completa`), `DROP COLUMN` (`20260802-22`) e un
test pgTAP nuovo — `test-emittente-denominazione-da-soggetto-v1.sql`, **13/13
verde**, con la fixture che fa divergere i valori di proposito come chiedeva
§5 1.3.

> ⚠️ **La cerniera è stata attraversata in due battute invece che in tre, e nel
> mezzo l'anagrafica emittenti è rimasta rotta.** La DROP è arrivata **prima**
> del passo 2: per qualche ora `emittenti_fiscali_repository` ha continuato a
> fare `SELECT ef.descrizione` su una colonna inesistente — lista, dettaglio,
> ricerca e creazione emittente rispondevano
> `ProgrammingError: la colonna ef.descrizione non esiste`. Nessun test lo ha
> intercettato: le 3444 girano a **DB mockato**, e il difetto era per
> costruzione invisibile lì.
>
> Chiuso il 2026-08-02 completando il passo 2 (sotto). La lezione è sull'ordine,
> non su chi: quando una modifica ha una cerniera dichiarata, la battuta di mezzo
> va **eseguita**, non solo scritta nel piano — e va verificata contro il DB
> vero, perché è l'unico posto dove quel tipo di rottura si vede.

**Passo 2 completato (BE/FE)** — `descrizione` rimossa da:

| File | Cosa |
|---|---|
| `anagrafiche/db/emittenti_fiscali_repository.py` | whitelist `_EMITTENTI_ORDER_COLS`, proiezione lista + dettaglio, `ILIKE` di ricerca, `INSERT` di `create_emittente`, `_UPDATE_ALLOWED`. Nuova costante `_EMITTENTI_ORDER_DEFAULT = "ragione_sociale_completa"` |
| `anagrafiche/services/emittenti_fiscali_service.py` | niente più `require_str(payload, "descrizione")` in `crea_emittente` |
| `anagrafiche/api/views_emittenti_fiscali.py` | serializer `@extend_schema` create/update, `default_order`, testo del parametro `search` |
| `amministrazione/components/EmittenteFiscaleDrawer.vue` | campo tolto dal form, dal payload e da `canSave`. In EDIT il nome è già a video: lo mostra il `SoggettoMessageBanner` |
| `stores/emittentiFiscali.js` · `views/EmittentiFiscaliListView.vue` | `orderBy` e `defaultSortField` su `ragione_sociale_completa` — **entrambi**: quando lo store preimposta l'ordine, il `defaultSortField` del componente è dormiente, e lasciarne uno indietro fa nascere la lista ordinata diversamente da come si dichiara |
| locali IT/EN | tolte le due chiavi orfane `field_descrizione`/`col_descrizione` del blocco emittenti; `search_placeholder` non promette più una ricerca su un campo che non esiste |
| `tests/api/test_emittenti_fiscali_api.py` | payload e fixture ripuliti. Passavano comunque (service mockato): il punto non era il rosso, era che descrivevano un contratto scomparso |

**Verifica del passo 2**, di nuovo contro il DB reale e non solo a test mockati:
lista (2/2, ordinata per ragione sociale), dettaglio, ricerca, e **ogni voce
della whitelist esercitata una per una** — nessuna ripiega in silenzio. Nel
payload non c'è più la chiave `descrizione`. Suite BE **3444 verde**, presidio
seed↔whitelist **7/7**, lint e build FE puliti, locali simmetrici (3649 chiavi
per parte).

### 10.5 Definizione di «fatto» — dove siamo

| § | Criterio | Stato |
|---|---|---|
| 6.1 | Ragione sociale su tutte e 9 le liste | ✅ verificato sui dati (i due emittenti che §1 citava come divergenti mostrano ora il nome giusto) **e validato a video da Tid il 2026-08-02** — §3.4 soddisfatta |
| 6.2 | Offerta stampata con la ragione sociale del soggetto | ✅ (lo era già; ora senza fallback) |
| 6.3 | Emittente **persona fisica** col nome completo | ✅ **garantito dal modello, non da un caso di prova** — vedi sotto |
| 6.4 | `grep` a zero su tutto il repo | ✅ zero occorrenze in `backend/` e `frontend/src`. Restano i 2 falsi positivi di `pratiche_repository` (lì `ef` è `config.esiti_flussi_pratiche`, non l'emittente) |
| 6.5 | Colonna sparita, pgTAP verde | 🟡 colonna sparita ✅, test del cantiere verde ✅ — ma vedi il caveat sotto |

**Su 6.3 il criterio si chiude sul modello, non su un caso di prova** (rilievo di
Tid, 2026-08-02). La sorgente scelta è **una sola** e non c'è alcun ramo che
distingua PF da PG: `ragione_sociale_completa` è una colonna
**`GENERATED ALWAYS AS COALESCE(ragione_sociale, cognome || ' ' || nome)`** —
la persona fisica è dentro la definizione della colonna. Misurato oggi: 37
soggetti, **27 senza `ragione_sociale`** (le PF) e **zero** senza
`ragione_sociale_completa` (`Terenzi Lucilla`, `Rossi Mario`, …).

Creare un emittente ditta individuale eserciterebbe la stessa identica riga di
codice: proverebbe il `COALESCE` di PostgreSQL, non questa modifica. Il criterio
6.3 nasceva dal timore che qualcuno ripuntasse i lettori su
`soggetti.ragione_sociale` (§3) — timore legittimo **prima** di scegliere, senza
oggetto **dopo**, perché nel repo quel nome non compare più come sorgente di
denominazione emittente. Resta valido l'avvertimento di §3 per chiunque tocchi
questi lettori in futuro.

⚠️ **Il caveat su 6.5, perché non venga letto come un verde pieno.** La baseline
pgTAP mostra oggi **15 rossi nuovi** (4 in `anagrafiche`, 11 in `script`) che
**non riguardano questo cantiere**: la causa comune è una violazione RLS
all'INSERT nelle *fixture* (`billing_account`, `ordini`), il sintomo di
[[feedback_rls_query_contesto_sistema]], non la colonna droppata. Vanno guardati
dal team DB, e sono citati qui solo perché chiunque rifaccia il conteggio li
troverà.

Più rilevante per **questo** cantiere: delle 3 funzioni modificate,
`fn_get_operatore_detail` ha un test **verde**, ma
`fn_get_user_emittenti_scope` e `fn_get_user_profile` sono coperte da file
**già rossi in baseline** — e un file che fallisce nel fixture non esegue
nessuna asserzione, quindi la sua copertura vale zero
(cf. `.codex/AGENTS.md`). Il cambio di sorgente su quelle due funzioni è
**verificato in applicazione** ma **non presidiato da un test verde**.
