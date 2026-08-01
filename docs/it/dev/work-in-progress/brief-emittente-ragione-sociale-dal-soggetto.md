# Brief DB/BE/FE — la ragione sociale dell'emittente viene dal soggetto

> **Chi scrive:** team DB (`dev/db-tid`), 2026-08-01.
> **A chi:** BE e FE (`dev/backend-tid`) — questo brief è **unico** perché la
> modifica non è divisibile: la colonna sta nel DB, i lettori sono in Python e
> in SQL, e l'ultimo miglio è a video.
> **Cos'è:** la proposta di eliminare `anagrafiche.emittenti_fiscali.descrizione`
> e far leggere ovunque la ragione sociale del **soggetto** associato.
> **Stato:** proposta misurata, **nessuna riga scritta**. Serve una decisione
> prima di aprire il cantiere.

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
