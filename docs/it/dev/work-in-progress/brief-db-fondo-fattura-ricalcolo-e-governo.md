# Fondo fattura — un numero ricalcolato che muove denaro

> # ✅ STATO AL 2026-08-31 (notte): **applicato, e il backend è chiuso**
>
> 🟢 **L'apply è stato fatto** (autorizzato da Tid) e **verificato sul database
> vivo**, non sul documento: `fn_cancella_fondo_fattura` e
> `fn_check_fondo_cancellabile` esistono, `fatture_fondi_fattura_source` ha
> `relrowsecurity = true` con **due policy**, i **cinque codici `E_`** sono a
> catalogo, `governa_fondo_fattura` è seminata (id 34, area 2, `pericolosa`), il
> guard risponde anche in `INSERT`, e in `pagamenti` il varco `RIPORTO` è dentro
> il guard con `fn_annulla_sistemazione` che chiama la cancellazione.
>
> ### Che cosa è stato fatto adesso
>
> | Passo | Stato |
> | --- | --- |
> | **BE — ripiego e policy** | ✅ **fatto**. I sette codici nuovi sono in `error_policies_generated.py`; **sette ripieghi** in `error_messages_fallback.py` — i cinque `E_` **e i due `W_`**, che il cancello pretende come i loro gemelli. Status risolti: `E_FONDO_NON_TROVATO` → **404**, gli altri quattro → **409** |
> | **BE-4** — `DELETE /api/v1/vendite/fondi-fattura/{id}/` | ✅ **fatto**: repository + service + view + rotta + **otto test**. Il metodo dice il verbo (niente `/cancella/` nel path), `post_permission = governa_fondo_fattura`, `Idempotency-Key` obbligatoria |
> | **FE-3** — «annulla» su una sistemazione `CONFERMATA` di tipo `RIPORTO` | ✅ **fatto**: `SistemazioneDrawer.vue`, `vocabolari.js`, i18n it/en |
> | **FE-1 · FE-2** — la colonna `azioni` sulla lista 44 | ✅ **fatti il 2026-08-31 (notte, 2)**, appena il seed è atterrato: kebab su `FondiFatturaDaDecidereTab.vue`, gated su `governa_fondo_fattura`, conferma **rossa**, e il client `DELETE` con `Idempotency-Key` |
>
> ✅ **Verde**: `2687` test backend (con `ZEROERP_TEST_DB_E2E=1`, quindi anche la
> prova del **binding reale** con la madre DB), build frontend, parità i18n it/en.
>
> ### ✅ FE-1 non era un passo frontend: era mezzo seed DB — ed è arrivato
>
> ⛔ **Il rilievo regge, ed è servito.** §9.3 assegnava FE-1 a «`80_data/sql/ui/`
> + il `.vue`»: la prima metà era una riga di **`lista_colonna.csv`**, cioè un
> **seed del catalogo DB** della stessa specie di D-19 e D-23. Passata al team
> (§9.12), è arrivata col merge su `Tito-dev` — colonna `619`, `tipo_colonna =
> 'azione'`, etichetta `common.col_azioni`, più la riga nel preset `sistema`. ✅
> **Verificata a database, non nel CSV**: la colonna c'è ed è nel preset.
>
> ⭐ **E la ragione per cui FE-2 non si poteva scrivere prima si è vista subito.**
> `ListaConfigurabile.vue` rende quella colonna **solo se il catalogo la dichiara
> `tipo_colonna = 'azione'` E il caller passa lo slot `#actions`** — servono
> entrambi, e mancandone uno **non si vede niente, senza errori**. Scritto prima
> del seed sarebbe stato codice che sembra fatto e non fa nulla.
>
> ⚠️ **E la stessa trappola è scattata una seconda volta, dentro FE-2**: la prima
> stesura del kebab portava `hideWhenReadonly: true` — proprietà che legge
> `DrawerActionsBar` e **non** `RowActionsMenu`. Sarebbe stata ignorata in
> silenzio, cioè un kebab attivo su una pagina in sola lettura. Sostituita col
> gating esplicito (`useInjectReadonly`). *Due proprietà con lo stesso nome e due
> letture diverse sono la stessa specie di difetto della colonna che non c'è:
> nessuno dei due dà un errore.*
>
> ### 📮 Che cosa resta aperto
>
> | A chi | Che cosa |
> | --- | --- |
> | **Tid / amministrazione** | 🔵 **assegnare `governa_fondo_fattura` a un profilo**, in-app. Verificato: la riga c'è, la concessione no — l'azione resta chiusa per tutti tranne il super admin, esattamente come `registra_distinta` |
> | **team DB** | rilanciare i pgTAP toccati **come applicazione** (`PGTAP_RUNNER=app`): nella prova giravano da owner, quindi la RLS appena accesa non è stata esercitata se non nel file `rls/` |
> | — | ⭐ **Il frontend non ha più niente in coda**: FE-1, FE-2 e FE-3 sono chiusi |
>
> ⭐ **Chiuso di rimbalzo**: le tre chiavi i18n che mancavano
> (`amministrazione.registri_fatturazione.disattiva_blocco.*`, dal cantiere
> **numerazione**) sono arrivate con lo stesso merge, e ne sono state seminate
> **sei** invece di tre. `check_i18n_keys.py` è **tutto pulito**.
>
> ➡️ Il riquadro qui sotto è lo stato **prima dell'apply**, tenuto per storia.

---

> # 📮 AL TEAM DB — stato al 2026-08-31 (sera): **i sette passi sono SCRITTI**
>
> 🟢 **Tutti e sette i passi DB del riquadro precedente sono stati scritti,
> provati e documentati.** ⛔ **Non sono APPLICATI**: nessun `liquibase update` è
> stato lanciato, e l'apply lo autorizza Tid. L'elenco dei changeSet, gli
> scostamenti dal piano e le cinque cose che il collaudo ha trovato stanno in
> **§9.11** — che è l'unica sezione da leggere per sapere dove siamo.
>
> | # | Passo | Dove | Stato |
> | :---: | --- | --- | --- |
> | 1 | **D-19** | `80_data` (CSV) | ✅ scritto — la descrizione a catalogo racconta ora quattro stati **e** la nascita |
> | 2 | **D-22** | `20_code/vendite` | ✅ `20260831-61` — il guard risponde anche in `INSERT` |
> | 3 | **D-20** | `00_schema/vendite` | ✅ `20260831-62` — le due policy + `ENABLE`, in un changeSet solo |
> | 4 | **D-21** | `20_code/vendite` | ✅ `20260831-63` (predicato) · `-64` (cancellazione) · `-65` (il reset ci si appoggia) |
> | 5 | **D-23** | `80_data` + in-app | 🔵 seminata (`azioni_processo.csv`, id 34) — ⚠️ **la CONCESSIONE resta da fare in-app**, e senza quella l'azione è chiusa per tutti tranne il super admin |
> | 6 | **D-25** | 🔴 `pagamenti` | ✅ `20260831-66` (il varco) · `-67` (`fn_annulla_sistemazione` estesa) |
> | 7 | **D-24** | `db/pgtap` | ✅ tre file nuovi (38 asserzioni) + due esistenti allineati |
>
> ➕ **E un ottavo, arrivato dopo**: la **colonna `azioni` della lista 44**, che il
> team BE ha girato al DB perché metà di FE-1 è un seed del catalogo. ✅ Seminata
> (due righe in append, nessun changeSet). 🔴 **Ma la sua catena ha un buco in
> mezzo**: `DELETE /api/v1/vendite/fondi-fattura/{id}/` **non esiste su nessun
> branch**, contrariamente a quanto la richiesta dava per fatto. **§9.12**.
>
> ### ⚠️ Le tre cose da sapere prima di applicare
>
> 1. ⛔ **L'ordine di apply è quello dei numeri**, e ha una dipendenza vera:
>    `-67` (pagamenti) non funziona senza `-66` (il varco) e senza `-64`, e le
>    sue `preConditions` lo dicono. I codici errore nuovi arrivano da `80_data`,
>    che gira **dopo** `20_code`: a fine migrate il quadro è coerente.
> 2. 🔴 **Sette codici errore nuovi**, non due. Il conto e il perché per ognuno in
>    §9.11; ⚠️ due sono `W_` e non hanno (né devono avere) una riga in
>    `config.messaggi_errore`.
> 3. 📮 **Due richieste al backend che nascono dai codici**, e vanno nello stesso
>    giro dell'apply o il primo errore arriva a video con un ripiego 400:
>    `manage.py genera_error_policies` e la frase di ripiego in
>    `error_messages_fallback.py` per ognuno dei cinque `E_`.
>
> ### ⛔ Cosa NON è del team DB
>
> **BE-4** (un solo `DELETE /api/v1/vendite/fondi-fattura/{id}/`) e **FE-1**,
> **FE-2**, **FE-3**: perimetro invariato, in §9.3. Partono dopo l'apply.
>
> ---
>
> <details><summary>📜 <b>Il riquadro precedente (i sette passi da fare) — tenuto per storia</b></summary>
>
> > # 📮 AL TEAM DB — i punti aperti al 2026-08-31 (mattina)
> >
> > ⭐ **Leggi questo riquadro e le sezioni che nomina. Non serve rileggere il
> > brief.** §1…§8 sono il **ragionamento** da cui questi passi discendono: sono
> > tenuti per storia, sono lunghi, e **non contengono lavoro aperto**. Tutto ciò
> > che resta da fare sta in **§9**.
> >
> > 🟢 **Non c'è nessuna domanda da fare e nessuna decisione da prendere**: le
> > cinque questioni di dominio (G-1…G-5) sono state **chiuse da Tid il
> > 2026-08-29**. Da qui è solo lavoro.
> >
> > 🔴 **Il fatto da cui discende tutto, in tre righe.** Dal **2026-08-22**
> > `pagamenti.fn_conferma_sistemazione` (lotto 7), ramo `RIPORTO`, fa un `INSERT`
> > **diretto** in `vendite.fatture_fondi_fattura_source`. ⭐ **Ed è la scelta
> > giusta** — `api.md` vieta le chiamate laterali fra moduli di pari livello, e il
> > DB è l'unica sede in cui i due schemi si toccano. **Il difetto non è che
> > `pagamenti` scriva: è che il presidio che accompagna quella scrittura non l'ha
> > costruito nessuna delle due parti.** Oggi si può **creare** un atto che muove
> > denaro e **non lo si può disfare**.
> >
> > I sette passi, in ordine di lavorazione, erano: D-19 (`80_data`), D-22
> > (`20_code/vendite`), D-20 (`00_schema/vendite`), D-21 (`20_code/vendite`),
> > D-23 (`80_data` + in-app), D-25 (`pagamenti`), D-24 (`db/pgtap/vendite`).
> > Dipendenze: 1, 2, 3 e 5 indipendenti da tutto; **4 (D-21) è il pezzo che gli
> > altri consumano**, e da lui dipendono 6 e 7.
> >
> > ➡️ Il dettaglio con le motivazioni d'ordine è in **§9.10**.
>
> </details>

---

> **Cos'è.** Il brief di un problema **strutturale** del meccanismo dei fondi
> fattura, emerso il **2026-08-09** analizzando gli incassi e messo da parte
> perché è un cantiere suo, in `vendite`, non in `pagamenti`.
>
> **Perché esiste questo file.** L'analisi è già stata fatta, in profondità, e
> sarebbe andata persa dentro il brief di un altro cantiere.
>
> ⭐ **Dal 2026-08-15 non è più solo una diagnosi: c'è il piano di sviluppo**, in
> **§8** — passi DB prima, logica BE poi, su richiesta di Tid. Le cinque domande
> di §6 hanno una risposta proposta in §8.1.
>
> ✅ **Stato al 2026-08-15 (notte)**: **Fase A** (rete di sicurezza), **Fase B**
> (registro degli atti) e la **coda della Fase E** (D-15…D-17) sono **applicate e
> verdi** — 16 changeSet, cinque codici errore, baseline `vendite` senza
> regressioni. Anche la **Fase C** (proposta + elenco) è **applicata e verde** —
> cinque changeSet `-19`…`-23`, §8.2-quinquies. ✅ **Anche la Fase F è fatta**:
> era dichiarativa e le sue due metà sono scritte nel cantiere incassi — la
> bilancia che regge da sé col posting atomico (§1-bis di quel brief) e
> «incassato ≠ postato», con i centri non-cassa da escludere dalle misure.
> ~~**Resta la sola Fase D** (atto manuale, e aspetta il processo rimborsi in
> `pagamenti` — che dal 2026-08-21 ha un nome e un posto: **slice 4 / lotto 7**
> del cantiere posting, vedi sotto).~~
> 🔴 **La Fase D non aspetta più niente: è stata SCAVALCATA.** Il processo
> rimborsi è arrivato il 2026-08-22 e scrive il fondo **da sé**, senza passare
> dalla porta che questa fase doveva costruire. Che cosa ne resta, e che cosa
> cambia, in **§9**.
>
> ✅ **Lato BE**: **R-1**, **R-2**, **R-3**, **BE-2**, **BE-3** e **BE-5** sono
> fatti e verdi (3676 test in env CI); **BE-1** è assorbito in R-3. Stato per
> passo in **§8.3**, esito di R-3 in **§8.3-bis** (DB) e **§8.3-ter** (BE).
>
> ✅ **Seed `ui.lista_*` applicato e verificato** (lista `id 44`, 16 colonne,
> attiva). ~~🔵 **la pagina Vue non è più bloccata da nulla** — è l'unico lavoro
> rimasto che non aspetta un'altra squadra.~~ ✅ **E la pagina Vue è FATTA**: la
> ha montata il **2026-08-22** un altro cantiere
> (`brief-db-liste-drawer-lotto.md`, commit `6e0256eaf`) —
> `vendite/components/FondiFatturaDaDecidereTab.vue`, con `ListaConfigurabile`,
> export che rispetta i filtri e click di riga sul drawer fattura.
> ⚠️ **Nessuno l'ha registrato qui per sei giorni**: è la stessa specie di
> difetto di D-17 — *chi chiude un lavoro non sa in quale brief era scritto come
> aperto*.
>
> 🔴 **Resta fermo il solo BE-4**, ~~e non per un prerequisito mancante: aspetta la
> **Fase D**, che a sua volta aspetta il processo rimborsi.~~ **e va
> ri-perimetrato**: metà non serve più al consumatore per cui era scritto,
> l'altra metà serve **di più** di prima. **§9**.
>
> ~~🔴 **Lato DB resta la sola Fase D** (D-11…D-13), che però aspetta a sua volta
> il **processo rimborsi in `pagamenti`**: costruire la porta prima della stanza
> è lecito, aprirla al pubblico no.~~
> 🔴 **La stanza si è fatta il muro da sé.** `pagamenti.fn_conferma_sistemazione`
> (lotto 7, applicato il **2026-08-22 alle 12:20**) fa un `INSERT` **diretto** in
> `vendite.fatture_fondi_fattura_source` sul ramo `RIPORTO`. La porta di D-11 non
> è stata aperta: è stata **aggirata**, e con essa il presidio che la giustificava.
> Diagnosi e conseguenze in **§9**.
>
> ⭐ **AGGIORNAMENTO 2026-08-22 — la stanza ha un progetto e un posto in coda.**
> Fino al 20 agosto «il processo rimborsi» era un'attesa senza indirizzo: la
> **Q-9** del cantiere posting era l'ultima domanda aperta di quel brief. È stata
> **chiusa da Tid il 2026-08-21, restringendosi** — le tre uscite (rimborso,
> compensazione, riporto a fondo) *hanno già tutte il loro meccanismo*, e mancano
> soltanto **una vista** e **un registro**. Da lì è nata la
> **slice 4 — «le sistemazioni»**, che è il **lotto 7** del piano DB:
> [brief-db-posting-e-abbinamento-rata.md §2.3-bis](brief-db-posting-e-abbinamento-rata.md).
>
> | | |
> | --- | --- |
> | Il passo che ci riguarda | **S4-4 — i tre verbi**: è quello che chiama D-11. Gli altri quattro (S4-1 rinomina `compensazioni` → `sistemazioni`, S4-2 verso del legame, S4-3 `vw_eccedenze_da_sistemare`, S4-5 codici/pgTAP/doc) non ci toccano |
> | Stato al 2026-08-22 (mattina) | ~~🔴 **non scritto**. Verificato sugli oggetti, non sul documento: `pagamenti.sistemazioni` non esiste (c'è ancora `compensazioni`), `vw_eccedenze_da_sistemare` neppure. I lotti applicati sono **1…6**~~ → 🔴 **la misura è invecchiata in quattro ore**: il lotto 7 è atterrato **lo stesso giorno alle 12:20**. `pagamenti.sistemazioni`, `vw_eccedenze_da_sistemare`, `fn_conferma_sistemazione` e `fn_annulla_sistemazione` **esistono tutti** (riverificato sul catalogo il 2026-08-29). ⚠️ *È il caso da manuale di un numero misurato che si porta dietro la data e non il contesto: qui il contesto era «e il lotto è in corso stamattina»* |
> | Quanto dista | **un lotto solo**, e avviabile subito: il §6.4 di quel brief dichiara i lotti **6 e 7 indipendenti fra loro**, entrambi abilitati dal 5 — che è chiuso. L'ordine fra i due era una scelta di priorità, non una dipendenza |
> | Cosa resta aperto **dentro** il lotto 7 | il solo **D15-e**: se `sistemazioni.contabile_id` debba far **sparire** `vendite_contabili.compensazione_id` invece di rinominarlo |
>
> ~~➡️ **La catena, per intero**: lotto 7 → **S4-4** → sblocca la **Fase D**
> (D-11…D-13) → sblocca **BE-4** → questo cantiere chiude.~~
>
> 🔴 **La catena si è percorsa da sola, e all'ultimo anello ha girato.** Il lotto
> 7 e S4-4 sono fatti; ma S4-4 **non chiama D-11** — la scrive dentro di sé. La
> Fase D non è stata sbloccata: è stata **saltata**, e ciò che resta da fare non
> è più quello che c'è scritto qui sotto. **§9**.
>
> ⚠️ Il resto del **rimborso in sé non è mai stato il problema**: la tabella
> **F-3** di §8.1 lo marca già *«niente da costruire»* (è una contabile a importi
> negativi), e dal lotto 4 quel percorso esiste davvero — dal lotto 5 sa anche a
> quale rata appartiene. Quello che manca non è il rimborso: è **chi decide e
> chiama**.
>
> ~~*«Qui non c'è un piano: c'è la diagnosi e ciò che è già stato deciso a
> tampone altrove.»*~~ — vera fino al 2026-08-14, tenuta per storia.
>
> 🔴 **E non è più vero nemmeno che «lo diventa il giorno del primo incasso».**
> §3 dava il fondo negativo per irraggiungibile finché non esistono movimenti:
> **la conclusione è sbagliata**, e il perché sta in **§8.0**. La finestra la
> apre il primo che scrive una riga contabile, che non è per forza il posting.
>
> **Origine**: [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md)
> §2-bis D1-bis.

---

## 1. La tesi, in una frase

> **Il fondo fattura è un numero che viene ricalcolato, e che muove denaro.**

Le due cose insieme non stanno in piedi. Un numero **derivato** può essere
ricalcolato quante volte si vuole: se sbaglia, al giro dopo si corregge, e nel
frattempo non è successo niente. Un numero che **muove denaro** — che viene
assegnato a una fattura figlia e ne cambia l'importo — è un **atto**, e un atto
non si ricalcola: si compie, e semmai si annulla con un altro atto.

Oggi il fondo è tutte e due le cose insieme. È da lì che discende il resto.

---

## 2. Come funziona oggi — misurato il 2026-08-09

### Il calcolo

`vendite.fn_genera_fondi_fattura_source(...)` calcola, per le fatture con
`minimo IS TRUE` di un dato billing account / tipo doc / emittente / valuta:

```text
importo_target = pagamenti.fn_get_saldo_fattura(f.id).saldo
               − pagamenti.fn_get_saldo_fattura_contabili(f.id).saldo_contabile
```

e poi:

| Ramo | Condizione | Effetto |
| --- | --- | --- |
| `UPDATE` | il fondo esiste già e il valore è cambiato | `importo = target`; `stato = ANNULLATO` **se e solo se** `target = 0`, altrimenti `DISPONIBILE` |
| `INSERT` | il fondo non esiste e `target <> 0` | crea il fondo `DISPONIBILE` |

⚠️ **`<> 0` è l'unica condizione sull'importo.** Non c'è limite inferiore.

### Il resto della catena

| Pezzo | Cosa fa |
| --- | --- |
| `vendite.fatture_fondi_fattura_source` | stati `DISPONIBILE` → `ASSEGNATO` → `ANNULLATO`. ⚠️ **Nessun CHECK sull'importo**: un fondo negativo è strutturalmente ammesso |
| task `genera_fondi_source_lotto` | `attivo = true` nel registry — **codice vivo** |
| task `applica_fondi_lotto` | `attivo = true` — assegna i fondi `DISPONIBILE` a una fattura figlia |
| `fn_sync_contabili_fondo_fattura(fattura_figlia)` | crea **righe contabili** per il fondo applicato; chiamata da `fn_ricalcola_totali_fattura` |
| `fn_reset_fondi_fattura(fattura)` | riporta `ASSEGNATO` → `DISPONIBILE` |
| centro `FONDI_FATTURA` (id 37, `is_fondo_fattura`) | la corsia contabile dedicata |

### ⚠️ Una funzione il cui nome mente — e nessuno la chiama

`vendite.fn_sync_pagamento_fondo_fattura(p_fattura_figlia_id)` restituisce
`TABLE(inserted_movimenti, updated_movimenti, annullati_source)`.

Il nome e le colonne dicono **movimenti**. Il corpo, letto per intero, è un
guscio: delega **tutto** a `fn_sync_contabili_fondo_fattura` e si limita a
rinominare `inserted_righe` → `inserted_movimenti`. **Non crea nessun
movimento**, e ✅ **nessuna funzione del database la chiama**.

🔴 Va segnalata per due ragioni:

1. chi legge la firma crede che il **posting esista** — ed è probabilmente una
   delle ragioni per cui la guida lo descrive come se ci fosse (non c'è: vedi il
   brief incassi §1-bis);
2. è **codice morto con un nome che promette**, cioè il tipo di residuo che al
   prossimo giro qualcuno chiama pensando di aver trovato il pezzo mancante.

~~Da decidere: rinominarla onestamente o ritirarla.~~ → ✅ **Deciso il
2026-08-15: si ritira** (`DROP`). Il difetto non è il nome, è che la funzione
**esiste**: un nome onesto lascerebbe in piedi un oggetto che nessuno chiama.
Motivi e costo — una sezione di pgTAP — in §8.1 F-4; il passo è **D-15**.

---

## 3. 🔴 Il fatto che rende la cosa non rimandabile all'infinito

> **Il meccanismo dei fondi non ha mai visto un pagamento.**

Il fondo si calcola da `fn_get_saldo_fattura`, che è il residuo *dopo i
movimenti*. Ma **nessuna funzione, in tutto il database, scrive
`pagamenti.vendite_movimenti`**: il posting non è implementato.

Ne segue che finora `fn_get_saldo_fattura` ha sempre restituito, per costruzione,
**l'intero `totale_a_pagare`**. Il fondo è stato progettato, scritto e messo in
pipeline in un mondo in cui **quel termine non si muoveva mai**.

**La slice 1 del cantiere incassi cambia questo per sempre**, e da quel momento
il fondo comincia a oscillare a ogni incasso. Non è un difetto che si manifesta:
è un comportamento che **non è mai stato esercitato**.

### Le due serrature, e chi apre quale

| Serratura | Stato al 2026-08-09 | Chi la apre |
| --- | --- | --- |
| `f.minimo IS TRUE` | **0 fatture a minimo** su 12; **0 fondi** generati | ~~una configurazione, in qualunque momento~~ → 🔴 **non è una configurazione: è un calcolo**, vedi §8.0-b |
| ~~saldo negativo (sovra-incasso)~~ | ~~impossibile: nessun movimento esiste~~ | ~~🔴 **la slice 1 del cantiere incassi**~~ → 🔴 **riga sbagliata**, vedi §8.0-a |

Con entrambe aperte, un sovra-incasso genera un fondo di importo **negativo** in
stato **`DISPONIBILE`**, che `applica_fondi_lotto` assegna a una fattura figlia.
Nessun `CHECK` lo ferma.

> 🔴 **Questa tabella è superata su entrambe le righe** (rimisurato il
> 2026-08-15 leggendo i corpi vivi): la seconda serratura non è «nessun
> movimento» ma **l'assenza di scrittori di righe contabili**, e la prima non è
> un flag che qualcuno accende ma il risultato di un confronto fra il totale
> della fattura e le soglie dell'emittente. Le due correzioni stanno in **§8.0**
> e cambiano *quando* il lavoro è urgente, non *cosa* c'è da fare.

---

## 4. Il difetto strutturale, oltre il caso del segno

Il fondo negativo è il sintomo che si vede per primo. Il problema è più a monte, e
si chiude solo separando due cose che oggi sono una sola:

| | Natura | Regola |
| --- | --- | --- |
| **I fatti** | denaro entrato o uscito, con o senza destinazione | si **aggiungono**, non si aggiornano mai |
| **I saldi** | residuo per fattura, per rata, credito del cliente | si **leggono**, non si conservano — quindi non possono divergere |
| **Le decisioni** | rimborsare, portare avanti, compensare | le prende una **persona**, e ognuna diventa un fatto |

Il fondo oggi sta **in mezzo**: è calcolato come un saldo, ma si comporta come una
decisione. Andrebbe portato **fra le decisioni** — un atto deliberato, non un
numero che un batch riscrive ogni notte.

### ⭐ Perché questo elimina il rischio di rincorsa

Il timore — legittimo — è di *«rincorrere gli incassi»*: un automatismo che
aggiorna un numero, un altro che lo rilegge e ne aggiorna un terzo, all'infinito.

Un ciclo del genere richiede che **un automatismo riscriva un numero che un altro
rilegge**. Se l'unica scrittura è l'aggiunta di un fatto e tutto il resto è
derivato, **non c'è niente che possa rincorrersi**: un saldo non insegue sé
stesso. Non «improbabile» — **impossibile per costruzione**.

---

## 5. Cosa è già stato deciso (a tampone) nel cantiere incassi

Non aspetta questo brief: sta in
[brief-incassi…](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis D1-bis
ed è **dentro la slice 1**, ~~perché è la slice che apre la seconda serratura~~.

> 🔴 **La motivazione è sbagliata, la collocazione no** (2026-08-15). La slice 1
> non è la sola ad aprire la seconda serratura — la apre **chiunque scriva righe
> contabili**, e non serve un movimento: §8.0-a. Quindi i tamponi restano dentro
> la slice 1 *se la slice 1 arriva prima*, ma la scadenza non è la sua: è il
> **primo scrittore**, chiunque sia. Sono la **Fase A** del piano (§8.2), e non
> si fanno due volte.

1. ~~**Limite inferiore alla generazione**: si crea un fondo solo per
   `importo_target > 0`. Il verso opposto **non è un fondo**: è denaro in
   eccesso, un fatto di natura diversa.~~
   > 🔴 **RITIRATO il 2026-08-15: era sbagliato, ed è l'errore più grave di
   > tutto il brief.** Le due soglie sono i **due capi di una banda che
   > contiene lo zero** (§8.0-b): il capo inferiore esiste **apposta** per
   > riportare avanti i **crediti**, quindi un fondo negativo è metà del
   > meccanismo, non un difetto. `importo_target > 0` avrebbe spento quella
   > metà **in silenzio**. Il controllo giusto non è sul segno ma sulla
   > **corrispondenza col documento** — vedi **§8.1 F-5** e **§8.6**. La stessa
   > frase è già stata ritirata nel cantiere incassi (§2-bis D1-bis).
   > ⚠️ Lasciata barrata e non cancellata: è il tampone su cui il piano ha
   > lavorato per sei giorni, e chi ritrova quella frase altrove deve poter
   > risalire a perché è caduta.
2. **Nessun automatismo tocca il fondo in base agli incassi.** Un fondo già
   esistente il cui target diventa negativo **resta com'è**; la fattura compare
   in un **elenco da guardare**, insieme alle rate sovra-incassate.

⭐ La seconda regola chiude anche la domanda *«il fondo va portato ad `ANNULLATO`
quando il target diventa negativo?»* — non scegliendo fra le due strade, ma
osservando che chiuderlo in automatico **sarebbe un automatismo che scrive**, e
sono stati esclusi tutti. Se non ci si fida di un automatismo a **creare** un
fondo, tanto meno a **cancellarlo**.

⚠️ **Sono tamponi, non la soluzione.** Impediscono al meccanismo di peggiorare
quando gli incassi arriveranno; non risolvono il fatto che un numero ricalcolato
muova denaro.

⚠️ **E il primo tampone da solo lascia scoperto un fondo**, cosa che il 2026-08-09
non era stata vista: togliendo l'`ANNULLATO` automatico a target zero, un fondo
non più giustificato **resta `DISPONIBILE`** e `applica_fondi_lotto` lo assegna
comunque. Il pezzo che chiude il buco è il **guard all'applicazione** — D-3 di
§8.2 — e va nello stesso lotto di lavoro, non dopo.

---

## 6. Le domande aperte

> ⭐ **Dal 2026-08-15 tutte e cinque hanno una risposta proposta**, con il perché
> e con ciò che la ribalterebbe: **§8.1**. Le domande restano scritte qui perché
> una risposta senza la domanda che l'ha generata non si sa più valutare.
>
> 🔴 **E dal 2026-08-29 ce ne sono due nuove, in §9.4** — **G-1** e **G-2**. Non
> sostituiscono queste cinque: nascono dal fatto che il processo rimborsi è
> arrivato e ha scavalcato la Fase D, quindi la strada manuale esiste **senza**
> il presidio che F-1 le aveva dato.

| | Domanda | Risposta proposta (§8.1) |
| --- | --- | --- |
| **F-1** | Il fondo diventa un **atto** (creato da una decisione, con la sua causale) o resta un numero derivato che qualcuno approva prima che muova denaro? | **Atto** — ma l'atto può nascere da una **regola permanente**, purché crei una volta sola e non riscriva mai |
| **F-2** | Che cosa succede a un fondo `ASSEGNATO` se la fattura sorgente riceve poi un incasso che ne cambia la base? Oggi `fn_reset_fondi_fattura` sa riportarlo a `DISPONIBILE`, ma **chi decide** che vada fatto? | **Non si tocca.** Il doppio pagamento diventa un **credito sulla sorgente** e si governa come qualunque eccedenza (F-3) |
| **F-3** | L'eccedenza di un sovra-incasso: rimborso, compensazione (`pagamenti.compensazioni` esiste ed è il candidato naturale) o applicazione a una fattura futura? Sono tre atti diversi con tre tracce diverse | **Tre strade, e due sono di `pagamenti`.** La terza — applicazione a una fattura futura — **è un fondo di segno opposto**, cioè un atto manuale su questa stessa tabella |
| **F-4** | `fn_sync_pagamento_fondo_fattura` — rinominare o ritirare? | **Ritirare** (`DROP`). Il difetto è che **esiste**, non come si chiama |
| **F-5** | Serve un `CHECK` sull'importo di `fatture_fondi_fattura_source`, o basta il limite inferiore nella funzione? (Un CHECK è una garanzia strutturale; un `WHERE` è una garanzia da ricordare) | **Servono tutti e due, e non sono la stessa regola.** Due CHECK, nessuno dei quali è `> 0` secco |

---

## 7. Dove guardare

| Cosa | Dove |
| --- | --- |
| 🔴 **Che cosa resta da fare, oggi** | **§9** — riscritto il 2026-08-29 dopo che il processo rimborsi ha scavalcato la Fase D. ⚠️ **Si legge prima di §8**: §8 è il ragionamento, §9 è lo stato |
| Che cosa era stato pianificato | **§8 — il piano di sviluppo** (DB in §8.2, BE in §8.3) |
| Il calcolo | `vendite.fn_genera_fondi_fattura_source` |
| Dove `minimo` viene **scritto** | `vendite.fn_ricalcola_totali_fattura` (in coda all'`UPDATE` di testata) + soglie su `anagrafiche.emittenti_fiscali_utilities` |
| La tabella e i suoi stati | [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) + il suo `manual` |
| L'applicazione alla figlia | task `applica_fondi_lotto` → `fn_applica_fondi_fattura`; le righe contabili le scrive `fn_sync_contabili_fondo_fattura`, chiamata da `fn_ricalcola_totali_fattura` |
| Il giro lato BE | `apps/vendite/db/pipeline_repository.py` (`run_genera_fondi_source_lotto_task`, `run_applica_fondi_lotto_task`) |
| Il reset | `vendite.fn_reset_fondi_fattura` — ⚠️ reset **tecnico** della figlia, non una reazione ai pagamenti |
| Il guscio vuoto | `vendite.fn_sync_pagamento_fondo_fattura` — **da ritirare**, D-15 |
| I due saldi che lo alimentano | `pagamenti.fn_get_saldo_fattura`, `fn_get_saldo_fattura_contabili` |
| I test che ci passano sopra | `db/pgtap/vendite/test-fondi-fattura.sql`, `test-fattura-utils-critical-termini.sql` §6 |
| Il modello contabile intorno | [gestione-dei-pagamenti.md](/guide/gestione-dei-pagamenti) |
| Il cantiere accanto | [brief-incassi…](brief-incassi-riconciliazione-rate-promemoria.md) §2-bis D1-bis (i tamponi), §3-bis (il principio dei tre livelli), §7 (le tre slice) |

---

## 8. Il piano di sviluppo

> ⭐ **Scritto il 2026-08-15 su richiesta di Tid**, per passare dalla diagnosi
> all'implementazione. **Prima tutti i passi DB (§8.2), poi la logica BE che ne
> discende (§8.3).**
>
> Il piano assume risolte le cinque domande di §6: le risposte, col perché e con
> ciò che le ribalterebbe, sono in **§8.1**. Due sono decisioni di dominio (F-1 e
> F-3) e vanno confermate da Tid: se cambiano, cambia la Fase B in avanti. ⭐ **La
> Fase A non dipende da nessuna delle cinque** e si può applicare comunque —
> anzi, va applicata prima delle altre in ogni scenario.

---

### 8.0 🔴 Prima del piano: due misure di §3 non reggono

Il piano parte da qui perché queste due righe cambiano **quando** il lavoro è
urgente, e §3 le dava per acquisite.

#### (a) La seconda serratura non è «nessun movimento»

§3 dice che il fondo negativo è irraggiungibile finché non esistono movimenti,
perché `fn_get_saldo_fattura` non può andare sotto zero senza incassi. **La
premessa è vera, la conclusione no**: il fondo non si genera su `saldo`, si
genera sulla **differenza**

```text
importo_target = fn_get_saldo_fattura(...).saldo            ← movimenti
               − fn_get_saldo_fattura_contabili(...).saldo_contabile   ← righe POSTABILI
```

e il **secondo** termine non ha niente a che vedere coi movimenti. Basta che la
somma delle righe contabili `is_postabile` di una fattura superi il suo residuo
perché `importo_target` vada sotto zero, **con zero movimenti nel database**.

Serve che qualcuno scriva una riga contabile più grande del dovuto, e oggi:

| | Stato |
| --- | --- |
| guard di quadratura sulle righe contabili | **non esiste** — è la slice **2** del cantiere incassi, non la 1 |
| vincolo che leghi `vendite_contabili_righe.importo` alla fattura che nomina | **nessuno** |
| scrittori vivi di righe contabili | **uno solo**: `fn_sync_contabili_fondo_fattura`, che scrive l'importo del fondo — un valore che per costruzione non supera il residuo, e che al giro dopo **si scorpora da sé** (`v_saldo_contabile_source`) |

⭐ **Quindi la seconda serratura non è un vincolo: è l'assenza di scrittori.**
Regge finché l'unico che scrive righe contabili è il circuito del fondo stesso, e
si apre col **primo** altro scrittore — l'import del flusso bancario (D6 del
cantiere incassi), una correzione manuale, la slice 1. Non necessariamente il
posting, e non necessariamente in quest'ordine.

🔴 **Conseguenza operativa**: la Fase A **non si appende alla slice 1** come se
fosse la sola porta. Va applicata prima del primo scrittore di righe contabili,
chiunque sia.

ℹ️ Misurato **leggendo** i corpi vivi (doc auto-generata) e la struttura delle
tabelle, non eseguendo SQL sul DB: formula di `fn_genera_fondi_fattura_source`,
assenza di `CHECK` su `fatture_fondi_fattura_source.importo`, assenza di guard di
quadratura su `vendite_contabili_righe`.

#### (b) `minimo` non è una configurazione: è un calcolo, e si richiude su sé stesso

§3 dice che la prima serratura la apre *«una configurazione, in qualunque
momento»*. Non è un flag che qualcuno accende sulla fattura: `minimo` è
**riscritto a ogni ricalcolo** da `fn_ricalcola_totali_fattura`

```text
minimo = (soglia_min IS NOT NULL AND totale_a_pagare >= soglia_min)
     AND (soglia_max IS NULL OR totale_a_pagare <= soglia_max)
```

con le soglie che stanno su `anagrafiche.emittenti_fiscali_utilities`
(`minimo_soglia_min`, `minimo_soglia_max`), per coppia **emittente × utility**.

#### ⭐ Che cosa significano davvero le due soglie (Tid, 2026-08-15)

Non sono «un minimo e un tetto» nel senso ingenuo. Sono i **due capi di una
banda**, e la banda contiene lo zero:

```text
                −500 €              0              +10 €
    ────────────────┼───────────────┼───────────────┼──────────────
     RIMBORSO       │      F O N D O   F A T T U R A     │  PAGAMENTO
     (troppo        │   il documento non si incassa      │  ordinario
      grande per    │   da solo: si riporta sulla        │  del cliente
      riportarlo)   │   fattura successiva               │
```

| Totale della fattura | Che cosa succede |
| --- | --- |
| **> +10 €** | pagamento ordinario del cliente. Niente fondo |
| **fra +10 e 0** | troppo piccola per essere incassata da sola → **fondo a debito**, riportato avanti |
| **fra 0 e −500** | credito troppo piccolo per un rimborso → **fondo a credito**, riportato avanti |
| **< −500 €** | credito importante → **processo rimborsi** (§8.1 F-3) |

🔴 **Ne discende che un fondo NEGATIVO è normale, non un difetto.** L'intero
capo inferiore della banda esiste per riportare avanti dei **crediti**. È la
correzione più importante di tutta questa sezione, e ribalta il tampone scritto
sia qui sia nel cantiere incassi — vedi F-5.

#### 🔴 «Soglia non impostata = meccanismo spento» oggi vale solo a metà

| Configurazione | Cosa dovrebbe fare | Cosa fa oggi |
| --- | --- | --- |
| nessuna delle due | spento | ✅ spento (`soglia_min IS NOT NULL` è falsa) |
| entrambe | attivo sulla banda | ✅ corretto |
| **solo il minimo** | ⛔ errore di configurazione | 🔴 **`soglia_max IS NULL` rende vera la seconda condizione**: *ogni* fattura sopra il minimo diventa «di minimo» |
| **solo il massimo** | ⛔ errore di configurazione | ✅ spento (per l'altro ramo) |

**Con l'esempio reale**: chi imposta `−500` e dimentica `+10` non ottiene un
meccanismo a metà — ottiene **tutto il fatturato trasformato in fondi
riportati**. Una configurazione incompleta oggi non chiude: **spalanca**.

✅ **Deciso (Tid, 2026-08-15): dev'essere un errore di configurazione**, non un
comportamento. Passo **D-0** in §8.2.

ℹ️ Il vincolo esistente `chk_emittenti_fiscali_utilities_soglie` presidia solo
`min <= max`, e ammette esplicitamente il caso a una sola soglia
(`min IS NULL OR max IS NULL OR min <= max`).

#### ⚠️ E `minimo` si richiude su sé stesso

`totale_a_pagare` **contiene** `fn_get_totale_fondi_fattura`, cioè i fondi già
applicati. Una figlia che riceve un fondo viene ricalcolata, il suo totale
cambia, e con esso può cambiare il proprio `minimo`: la figlia può diventare a
sua volta sorgente di un fondo per la nipote. **È il comportamento voluto** —
nelle utenze il riporto si incatena finché non si esce dalla banda — ed è
leggibile: `fatture_fondi_fattura.riferimento_fattura_id` porta già la fattura di
provenienza, quindi la catena si ricostruisce senza aggiungere niente.

#### ⚠️ Nota di lettura: «BASE» è una utility, non l'assenza di utility

`config.utilities` contiene `BASE` (*Servizio Base*, id 5) accanto a GAS,
ENERGIA, IDRICO, FONIA, e `anagrafiche.billing_account.utility_id` è **NOT
NULL**. Quindi ogni fattura ha una utility e le soglie si trovano **sempre**:
non esiste il caso «fattura senza utility» da gestire a parte. ⚠️ Una riga di
`vendite.fatture` con `utility_id` vuoto (la colonna lì è nullable) non è una
fattura BASE: è un dato incompleto, e va trattata come tale.

---

### 8.1 Le cinque domande, risolte

#### F-1 — Il fondo diventa un **atto**. Ma l'atto può nascere da una regola permanente

⭐ **Non è una scelta nuova: discende da §3-bis del cantiere incassi**, il
principio già fissato con Tid il 2026-08-09 — *i fatti si aggiungono, i saldi si
leggono, le decisioni le prende una persona*. Applicato al fondo dà una sola
risposta: il fondo sta fra le **decisioni**, cioè è un fatto che qualcuno compie.

Ma «qualcuno» non deve per forza essere una persona **per ogni riga**. Nelle
utilities i fondi sono migliaia al mese: un'approvazione che si dà in blocco per
inerzia non è una decisione, è un timbro — e sarebbe un peggioramento, perché
metterebbe una firma umana sotto un numero che nessuno ha guardato.

**La forma che si propone:**

| | Regola |
| --- | --- |
| **Ogni riga del registro è un atto** | ha un'**origine** (`AUTOMATICA` \| `MANUALE`), un **motivo** quando è straordinaria, e un **importo congelato al momento dell'atto** |
| **Nessun atto si aggiorna** | l'`UPDATE … SET importo = target` **sparisce**. Il fondo si crea una volta, con l'importo letto in quel momento, e non si ricalcola più |
| **L'automatismo crea solo dentro la banda** | sorgente **DEFINITIVA**, dentro `[soglia_min, soglia_max]`, e ancora capiente **nell'istante dell'atto**. Fuori da lì non fa niente: **presenta** (§8.2 Fase C) |
| **La regola permanente è la delibera** | la decisione è stata presa quando si sono configurate le due soglie; il giro di fatturazione la **esegue**, non la prende |

⭐ **Perché questo chiude la tesi di §1.** Il fondo smetteva di stare in piedi
perché era *ricalcolato* **e** *muoveva denaro*. Qui il ricalcolo resta — ma
diventa una **lettura** (§8.2 D-9), non una scrittura; e il denaro lo muove solo
un atto, che è scritto una volta e mai riscritto. Le due cose non sono più lo
stesso oggetto.

**Cosa la ribalterebbe.** Se Tid decidesse che *ogni* fondo va approvato a mano
prima di muovere denaro, cade solo la riga «la regola permanente è la delibera»:
la Fase B resta identica, e la Fase D (l'atto manuale) diventa l'**unica** strada
invece che quella straordinaria. Il piano non va riscritto, va accorciato.

**Scartata**: lasciare il fondo com'è e mettergli davanti un'approvazione. Non
risolve niente — approvare un numero che al giro dopo il batch riscrive significa
approvare qualcosa che non c'è più.

#### F-2 — Un fondo `ASSEGNATO` non si tocca

Se la sorgente riceve un incasso **dopo** che il fondo è stato applicato, il
cliente ha pagato due volte lo stesso importo: una sulla sorgente e una dentro la
figlia. Il fatto è reale e va **registrato**, non annullato: diventa un **saldo
negativo sulla sorgente**, cioè un credito, e si governa come qualunque eccedenza
(F-3). Nessun automatismo interviene — è la regola pratica di §5.2, e vale anche
qui.

⚠️ **`fn_reset_fondi_fattura` non è la risposta a questa domanda**, e il nome non
lo dice: è il reset **tecnico della figlia** (ritorno del lotto a DRAFT), non una
reazione ai pagamenti. Va scritto nel suo `COMMENT` — **D-16** — perché è
esattamente il tipo di funzione che al prossimo giro qualcuno chiama pensando di
aver trovato il pezzo giusto (lo stesso difetto di `fn_sync_pagamento_fondo_fattura`).

#### F-3 — Tre strade, e la terza è già questa tabella

✅ **Confermato da Tid il 2026-08-15, con il perimetro**: *«il processo rimborsi
sta nei pagamenti, e le uscite sono tre: rimborso, compensazione, riporto a
fondo fattura»*.

| Strada | Dove vive | Stato |
| --- | --- | --- |
| **Rimborso** | contabile con importi negativi | ✅ **niente da costruire**: D3-d del cantiere incassi ha già deciso che la correzione è un importo di segno opposto, e la guida dice già che il movimento rappresenta «l'incasso **o il rimborso**» |
| **Compensazione** | `pagamenti.compensazioni` | ⏸️ oggi è uno **scheletro** (`id`, `data_esecuzione`, `meta` + audit): è un cantiere suo, in `pagamenti`, non qui |
| **Applicazione a una fattura futura** | ⭐ **è un fondo fattura di segno opposto** | 🔵 la apre la **Fase D** di questo piano |

⭐ **E il passaggio è PASSIVO** (Tid, 2026-08-15): niente meccanismo che «mette in
coda» una fattura sotto la soglia minima. Il processo rimborsi, in `pagamenti`,
**se le va a cercare** — è coerente con «i saldi si leggono» e non aggiunge
nessuna scrittura in `vendite`. Il confine è quindi netto:

> **`vendite` espone un solo punto d'ingresso** (l'atto manuale, D-11), e non sa
> nulla di rimborsi e compensazioni. **`pagamenti` decide** e chiama, quando
> l'operatore sceglie la terza uscita.

⭐ **La terza riga è la scoperta che vale il paragrafo.** «Portare avanti un
credito sulla prossima fattura» non è un meccanismo nuovo da inventare: è
**esattamente** ciò che il fondo fattura fa, col segno invertito. E il vocabolario
c'è già — `tipi_fondi_fattura` id 1 si chiama *«Fondo fattura per
addebiti/**accrediti**»*. Il meccanismo è stato costruito per due versi e ne ha
usato uno solo.

🔴 **Ed è la ragione per cui F-5 non può essere `importo > 0` secco**: un CHECK
così chiuderebbe la terza strada nello stesso changeSet in cui si apre la prima.

**Chi sceglie fra le tre**: una persona, dall'elenco (**D-10**). Non è una
gerarchia: sono tre atti diversi con tre tracce diverse, e la scelta dipende dal
cliente, non dal sistema.

#### F-4 — `fn_sync_pagamento_fondo_fattura` si **ritira**

Verificato il 2026-08-15:

| | Misura |
| --- | --- |
| chiamate da funzioni DB | **zero** — `fn_ricalcola_totali_fattura` chiama direttamente `fn_sync_contabili_fondo_fattura` |
| chiamate da Python | **zero** |
| `COMMENT` vivo | già *«Wrapper deprecato: delega a fn_sync_contabili_fondo_fattura»* |
| unico riferimento vivo | `db/pgtap/vendite/test-fattura-utils-critical-termini.sql` §6 — collauda il guard di parametro **di un guscio** |

**Ritirare batte rinominare** perché il difetto non è il nome: è che la funzione
**esiste**. Un nome onesto lascerebbe in piedi una funzione che nessuno chiama,
cioè un secondo oggetto da mantenere e da spiegare. E non siamo in produzione: il
breaking è secco e costa un `DROP` più una sezione di test.

#### F-5 — Un CHECK e un guard. E 🔴 **non è il segno che va controllato**

> 🔴 **Questa risposta è stata riscritta il 2026-08-15, e la prima versione era
> sbagliata in modo istruttivo.** Diceva: *«l'automatismo crea solo fondi
> positivi»*, con un CHECK a renderlo strutturale. **Con la banda a due capi
> (§8.0-b) è falso**: una fattura fra −500 e 0 *deve* diventare di minimo e
> riportare un **credito** sulla successiva. Il `> 0` avrebbe spento metà del
> meccanismo — e la stessa frase sbagliata sta nel tampone del cantiere incassi,
> dove va corretta.

**Il pericolo non era il segno: era la mancata corrispondenza col documento.**
Una fattura da 8 € su cui qualcuno scrive una riga di lavorazione da 40 €
produce un fondo di −32 su un documento che vale +8. Il fondo non «è negativo»:
**non assomiglia alla sua sorgente**. Ed è quello che va vietato.

```text
regola di corrispondenza (fondo AUTOMATICO)
   l'importo non è zero
   ha lo stesso segno del totale della fattura sorgente
   non lo supera in valore assoluto
```

⚠️ **Va scritta così, mai come «compreso fra 0 e il totale»**: con un totale
negativo gli estremi si invertono e il controllo diventa una porta chiusa. È la
trappola già registrata nel cantiere incassi, e qui si presenterebbe **come caso
ordinario**, non di bordo.

**Dove vive che cosa** — e il confine non è una preferenza, è ciò che un CHECK
può vedere:

| | Strumento | Perché |
| --- | --- | --- |
| `importo <> 0` | **CHECK** di tabella | guarda solo la propria riga: un fondo da zero non è un atto, è rumore |
| corrispondenza col totale della sorgente | **guard trigger** (`_a10_`) | deve **leggere `vendite.fatture`**, e un CHECK non può |
| «l'automatismo non lo fa» | **`WHERE` nella funzione** | il caso è **ordinario**: va *non fatto*, non rifiutato con un'eccezione che ferma il giro di un lotto intero |

🔴 **E qui `origine` torna a servire, per una ragione diversa da quella che
avevo dato.** Non per vietare i fondi negativi all'automatismo, ma per dire
**quale regola si applica**: la corrispondenza vale sulla strada
**automatica**; sulla strada **manuale** no, ed è dimostrabile con il caso
principale di F-3 — l'eccedenza di un sovra-incasso è un fondo **a credito su
una fattura dal totale positivo**, cioè segno opposto per costruzione. Un guard
unico rifiuterebbe proprio l'atto per cui la strada manuale esiste.

Il manuale non resta però senza presidio: è **motivato, gated da un'azione di
processo e originato dal processo rimborsi**, che l'eccedenza la conosce. È la
differenza fra un atto **vincolato** e un atto **governato** — ed è il punto di
F-1.

⚠️ **Un CHECK in più, che §6 non chiedeva e serve comunque**: `stato` è oggi un
`character varying` **senza CHECK e senza FK**. Il vocabolario
`DISPONIBILE`/`ASSEGNATO`/`ANNULLATO` vive solo nelle stringhe letterali di
quattro funzioni.

---

### 8.2 I passi DB

> **Convenzioni** (AGENTS.md + linee-guida-sql, non ripetute passo per passo):
> un changeSet per file, `YYYYMMDD-NN-<tipo>-<descrizione>-mctit.yaml`,
> `logicalFilePath` sempre, `runOnChange: false` in `00_schema`/`20_code`,
> **corpo delle funzioni dalla doc auto-generata** e mai dagli YAML,
> **numerazione `NN` globale per data** fra tutte le cartelle, e mai una modifica
> a un changeSet già mergiato.
>
> ⚠️ **Ordine dei changeSet, che qui morde davvero.** L'autogen mescola
> `00_schema` e `20_code` ordinando per `NN`: ogni funzione che nomina una
> colonna nuova deve avere un numero **più alto** dell'`ALTER TABLE` che la
> aggiunge. Vale per D-8 rispetto a D-5, e per D-9/D-10 rispetto a D-5.

#### Fase A — La rete di sicurezza *(condivisa con la slice 1 del cantiere incassi)*

> ✅ **APPLICATA E VERDE il 2026-08-15.** Sette changeSet (`20260815-03` … `-09`),
> due codici errore a catalogo, un pgTAP nuovo (12/12) e la fixture di quello
> esistente adeguata (19/19). **`pgtap-baseline.sh vendite`: nessuna
> regressione** — 24 rossi, tutti già noti. Cronaca, residui e il difetto
> trovato nel collaudo in **§8.2-bis**.
>
> 🔴 **Chi arriva prima la fa, e non si fa due volte.** Il cantiere incassi la
> dichiara dentro la sua slice 1 (§2-bis D1-bis); §8.0-a dice che la finestra si
> apre anche senza di lei. Se la slice 1 parte prima, questi quattro passi sono
> suoi; altrimenti sono il primo lavoro di questo cantiere.

| | Passo | Dove |
| --- | --- | --- |
| **D-0** | ⛔ **Le due soglie: entrambe o nessuna.** Una configurazione a metà oggi **spalanca** il meccanismo invece di spegnerlo (§8.0-b) | `00_schema/anagrafiche/` |
| **D-1** | **La generazione cambia perimetro**: solo sorgenti **DEFINITIVA**, e il ramo `UPDATE` **sparisce** | `20_code/vendite/` |
| **D-2** | **CHECK** `importo <> 0` + CHECK sul vocabolario di `stato` | `00_schema/vendite/` |
| **D-3** | **Due guard**: corrispondenza col totale della sorgente, e capienza **al momento dell'applicazione** | `20_code/vendite/` |
| **D-4** | **La chiave a nove elementi** al posto dei cinque parametri sciolti | `20_code/vendite/` |

##### D-0 — Un errore di configurazione, non un comportamento

```sql
ALTER TABLE anagrafiche.emittenti_fiscali_utilities
  ADD CONSTRAINT chk_emittenti_fiscali_utilities_soglie_coppia
  CHECK ((minimo_soglia_min IS NULL) = (minimo_soglia_max IS NULL));
```

Entrambe vuote = meccanismo **spento**; entrambe valorizzate = attivo sulla
banda; **una sola = si rifiuta di salvare**. Il vincolo esistente
(`chk_…_soglie`) presidia solo `min <= max` e la coppia incompleta la **ammette**
per costruzione.

⚠️ **Prima di applicarlo, misurare le righe già a metà** e sanarle a mano — su
dev i dati sporchi si correggono così, non con un fix software. Un CHECK che
scatta all'apply su righe preesistenti fa fallire il migrate.

⭐ E l'errore va reso parlante: la violazione arriva al backend come vincolo, e
si mappa a un codice di dominio (`E_FONDO_SOGLIE_INCOMPLETE`, classe
`DATO_ERRATO`) con il campo dichiarato, così l'operatore vede *quale* soglia
manca invece di un messaggio di database.

##### D-1 — Sorgente **DEFINITIVA**, e il ramo `UPDATE` sparisce

Due modifiche, e discendono entrambe dalle regole di Tid (§8.1 F-1):

1. **filtro di stato sulla sorgente**: solo `DEFINITIVA`. Oggi la generazione
   **non filtra nessuno stato** — e non è un dettaglio: `fn_get_saldo_fattura`
   non guarda lo stato, quindi una fattura **`ANNULLATA`** con `minimo = true`
   restituisce il totale intero e **genera un fondo**, che finisce addebitato su
   un altro documento. Non è mai successo perché di fondi non ne è mai stato
   generato nessuno;
2. **niente più `UPDATE`**: il fondo si crea una volta, con l'importo letto in
   quel momento, e non si ricalcola più.

⭐ **Le due cose si tengono a vicenda, ed è il motivo per cui «DEFINITIVA» è la
soglia giusta**: misurato su `config.stati_doc_fiscale_transizioni`, da
`DEFINITIVA` si va **solo a `INVIATA`**, e l'unico ritorno a `DRAFT` parte da
`EMESSA`. Una sorgente definitiva **non torna indietro**: «congelato quando la
sorgente è definitiva» non ha eccezioni da gestire.

⚠️ **Con l'`UPDATE` sparisce anche l'`ANNULLATO` automatico a target zero.** Il
buco che questo apre — un fondo non più dovuto che resta `DISPONIBILE` e viene
comunque applicato — lo chiude **D-3**, non un altro automatismo. 🔴 **D-1 senza
D-3 è peggio di non fare niente.**

##### D-3 — Due guard diversi, e non vanno confusi

**(a) Corrispondenza col documento** — trigger `_a10_` BEFORE INSERT/UPDATE, solo
per `origine = 'AUTOMATICA'`:

```text
l'importo non è zero
ha lo stesso segno del totale_a_pagare della fattura sorgente
non lo supera in valore assoluto
```

⚠️ Scritta così, **mai** come «compreso fra 0 e il totale»: su una sorgente a
credito gli estremi si invertono e il guard diventa una porta chiusa. Qui il caso
non è di bordo — è **metà della banda**.

**(b) Capienza al momento dell'atto** — dentro `fn_applica_fondi_fattura`:

```text
prima di assegnare il fondo s alla figlia, verifica che
    saldo_sorgente_al_netto_del_proprio_contributo(s)  copra ancora  s.importo
altrimenti NON assegnare, e lascia la riga dov'è (finirà nell'elenco)
```

⭐ **È il pezzo che rende inutile qualunque automatismo di allineamento**: invece
di tenere aggiornato un numero perché sia giusto quando servirà, lo si **rilegge
quando serve**. Livello 2 di §3-bis alla lettera — *i saldi si leggono, non si
conservano*. E non è un ricalcolo del fondo: è il controllo che la sorgente non
sia stata pagata nel frattempo.

⚠️ **Trappola del doppio conteggio, già risolta una volta.** Il
`saldo_contabile` della sorgente **contiene già** la riga contabile del fondo, se
il fondo è passato di lì. `fn_sync_contabili_fondo_fattura` la scorpora già, con
`v_saldo_contabile_source`: **quella formula si estrae e si riusa**, non si
riscrive.

> **Regola del 2** → nuova `vendite.fn_saldo_sorgente_fondo(p_fattura_sorgente_id, p_source_id)`
> `STABLE`, che ritorna il saldo della sorgente **al netto del contributo del
> fondo indicato**; la usano D-3(b), `fn_sync_contabili_fondo_fattura` (che
> smette di calcolarlo inline) e D-9. Tre chiamanti, una formula.

##### D-4 — 🔴 La chiave: il fondo ne usa metà, e il progetto ha **già pagato** questo difetto

La chiave con cui si accorpano le attività in una fattura è
`vendite.fn_build_fattura_key`, e ha **nove** elementi:

```text
billing_account · tipo_doc_fiscale · valuta · emittente · reseller
utility · registro · termine_pagamento · modalita_pagamento
```

| Funzione | Elementi usati | Mancano |
| --- | ---: | --- |
| `fn_genera_fondi_fattura_source` | **4** (`utility` scritta ma non filtrata) | utility, reseller, registro, termine, modalità |
| `fn_applica_fondi_fattura` | **5** | reseller, registro, termine, modalità |

**Conseguenza concreta**: un fondo nato da una fattura a 30 giorni può essere
applicato a una figlia a 60 giorni — due documenti che il sistema ha
**deliberatamente tenuti separati**, visto che il termine è nella chiave proprio
per non accorparli.

⭐ **E questo identico difetto è già stato corretto un anello prima.** Il
`COMMENT` di `fn_get_or_create_fattura_header` lo dice:

> *«il WHERE del lookup confronta TUTTI e nove gli elementi della chiave —
> **utility_id (che mancava da sempre)** … Chiave e lookup disallineati **si
> annullano a vicenda**»*

Il fondo è il **terzo specchio**, e nessuno l'ha riallineato.

⭐ **La correzione è anche una semplificazione.** Sorgente e figlia sono
entrambe righe di `vendite.fatture`, e tutti e nove gli elementi sono **colonne
di quella tabella**: il confronto si fa **riga contro riga**, con
`IS NOT DISTINCT FROM` sui quattro nullable. Le funzioni del fondo smettono
quindi di ricevere cinque parametri sciolti dal Python, e con loro spariscono:

* il difetto dell'`utility_id` che si ribalta a ogni giro (era il chiamante a
  passare uno scope incoerente, un giro per utility);
* le **N chiamate in autocommit** del repository (BE-2): resta una chiamata per
  lotto.

⚠️ Sul caso **BASE**: `BASE` è una **utility** (`config.utilities` id 5,
*Servizio Base*) e `billing_account.utility_id` è **NOT NULL** — quindi la
utility c'è sempre e combacia per uguaglianza. Una riga di `vendite.fatture` con
`utility_id` vuoto non è una fattura BASE: è un dato incompleto, e resta fuori
(comparirà nell'elenco di D-10 col suo motivo).

#### Fase B — Il registro degli atti

> ✅ **APPLICATA E VERDE il 2026-08-15.** Sette changeSet (`20260815-12` … `-18`),
> tre codici errore a catalogo, sette asserzioni pgTAP in più (sei sulla Fase B +
> la ragione dell'annullamento **sul dato**). **`pgtap-baseline.sh vendite`:
> nessuna regressione.** Elenco, cronaca e residui in **§8.2-quater**.

| | Passo | Dove |
| --- | --- | --- |
| **D-5** | **Colonne dell'atto** su `fatture_fondi_fattura_source`: `origine` (`varchar` NOT NULL DEFAULT `'AUTOMATICA'`, CHECK `IN ('AUTOMATICA','MANUALE')`) e `motivo` (`text` NULL, obbligatorio per `origine = 'MANUALE'` e per `stato = 'ANNULLATO'`) | `00_schema/vendite/` |
| **D-6** | **Lock delle colonne portanti**: `importo`, `fattura_sorgente_id`, `tipo_fondo_fattura_id`, `origine` immutabili dopo l'INSERT, via `script.trgfn_lock_columns` (già usato su `tipi_fondi_fattura`) | `20_code/vendite/` |
| **D-7** | **Guard di transizione** `trgfn_fondi_source_guard_transizione`, trigger `_a10_` BEFORE UPDATE | `20_code/vendite/` |
| **D-8** | **Un solo atto vivo per sorgente** — indice unico parziale | `00_schema/vendite/` |

> 🔴 **`atto_precedente_id` è stato tolto** (2026-08-15). Serviva alla revoca +
> riemissione, che con la regola «il fondo non si ricalcola mai» **non esiste
> più**. E la catena dei riporti resta comunque leggibile:
> `fatture_fondi_fattura.riferimento_fattura_id` porta già la fattura di
> provenienza. *Una colonna che esiste per un meccanismo che non c'è più è debito
> al primo giorno.*

##### D-5 — ⭐ `origine` non dice «chi l'ha creato»: dice **quale regola si applica**

È la correzione di F-5. La colonna non serve a vietare i fondi negativi
all'automatismo — quelli sono metà del meccanismo — ma a distinguere:

| `origine` | Presidio |
| --- | --- |
| `AUTOMATICA` | **vincolato**: il guard di corrispondenza D-3(a) legge la sorgente e rifiuta ciò che non le assomiglia |
| `MANUALE` | **governato**: motivo obbligatorio, azione di processo, e viene dal processo rimborsi — che l'eccedenza la conosce, mentre il database no |

> 🔴 **Delle tre gambe del «governato», oggi ne reggono due** (misurato il
> 2026-08-29). Il **motivo** c'è — e regge per una simmetria non casuale:
> `pagamenti.sistemazioni.motivo` è obbligatorio **proprio su `RIPORTO`**, che è
> l'unico ramo che crea il fondo, quindi `chk_fondi_source_motivo_obbligatorio`
> trova sempre di che soddisfarsi. L'**origine** c'è. ⛔ **L'azione di processo
> no**: `governa_fondo_fattura` non è a catalogo, e il fondo lo scrive
> `pagamenti` senza attraversare nessun cancello di `vendite`. **§9.**

🔴 **Il caso che dimostra perché il guard non può essere unico**: l'eccedenza di
un sovra-incasso è un fondo **a credito su una fattura dal totale positivo**,
cioè di segno opposto per costruzione. Un guard applicato a tutti rifiuterebbe
proprio l'atto per cui la strada manuale esiste.

##### D-6 — ⭐ È il lock, non la buona volontà, a rendere il fondo un atto

Con `importo` bloccato dopo l'INSERT, *«non si ricalcola mai»* smette di essere
una regola che qualcuno deve ricordare e diventa una cosa che il database non
lascia fare. È la traduzione strutturale della regola di Tid: *una volta che la
fattura è definitiva, il suo fondo resta quello.*

⭐ **Ed è la stessa regola che il progetto applica già agli altri satelliti della
fattura.** `trgfn_fattura_satellite_guard_congelamento` — *«superata la soglia
DRAFT/EMESSA i suoi satelliti sono uno snapshot e non si toccano più»* — è
montato su `fatture_scadenze` e `fatture_indirizzi`. **Sui fondi no.** Il fondo è
l'unico satellite della fattura che non è congelato; la regola non è nuova, è la
regola della casa applicata a un satellite che se n'era dimenticata.

⚠️ **Perché il lock di colonna e non quel trigger.** Sui fondi non si può
congelare la **riga**: l'assegnazione alla figlia avviene dopo, ed è legittima.
Si congelano l'**importo** e la sorgente, non l'assegnazione.

⚠️ **Due trappole note su questo passo.** (1) Le automazioni che montano i trigger
girano **solo in contesto `ci_apply`**: sul migrate manuale il trigger di lock
arriva col pgagent di fine giornata, non subito. (2) Se un domani si aggiungono
colonne all'elenco dei lock su una tabella che ce l'ha già, su DB esistenti serve
**DROP + rigenera**: qui è un montaggio nuovo, quindi il caso non si presenta.

##### D-7 — Le transizioni, e ⚠️ il test che le contraddice già

```text
DISPONIBILE  →  ASSEGNATO | ANNULLATO
ASSEGNATO    →  DISPONIBILE (solo dal reset tecnico) | ANNULLATO
ANNULLATO    →  ∅   (terminale)
```

~~Tre stati, non quattro: `REVOCATO` è caduto con la revoca+riemissione.~~

> 🔴 **SUPERATO il 2026-08-21: gli stati diventano QUATTRO.** Non torna
> `REVOCATO` — arriva **`ESEGUITO`**, e lo porta il **posting**, che quando
> questa sezione fu scritta non esisteva.
>
> ```text
> ASSEGNATO  →  ESEGUITO      ← lo scrive un trigger, quando la riga
> ESEGUITO   →  ∅ (terminale)   contabile del fondo viene REGISTRATA
> ```
>
> **Perché.** `ANNULLATO` portava **tre** significati, e solo uno era un
> annullamento. In particolare il ramo bloccante di `fn_reset_fondi_fattura`
> scrive `ANNULLATO` **lasciando `fattura_figlia_id` valorizzato** — un fondo
> «annullato» che risulta ancora assegnato: un record che si contraddice. Quel
> ramo non voleva dire «annullato», voleva dire **«già eseguito»**, e non aveva
> la parola.
>
> ⭐ **E il guadagno è strutturale, non lessicale.** Tutti e tre i lettori dei
> fondi filtrano su `stato`: un fondo che esce da `ASSEGNATO` esce da tutti e tre
> **gratis**. Ne discende che due difetti del posting — il sync che riscrive
> righe registrate e il fondo che si auto-annulla — **smettono di essere
> raggiungibili** invece di essere tamponati, e cade la necessità di correggere
> lo scorporo di `fn_saldo_sorgente_fondo`.
>
> ⚠️ **Cambia anche D-16 (il reset)**: l'atto **non eseguito** si **cancella**
> invece di tornare `DISPONIBILE`; un `ESEGUITO` non si tocca mai, si segnala e
> basta; sparisce il ramo che scriveva `ANNULLATO`.
>
> ⚠️ **E cambia la risposta del riquadro qui sotto** («perché un CHECK e non una
> tabella di stati»): la conclusione **regge ancora** — restano valori interni
> senza etichette né azioni di UI — ma il vocabolario passa da tre a quattro e il
> `CHECK` `chk_fondi_source_stato` va sostituito.
>
> Decisione **D11** in
> [brief-incassi-riconciliazione-rate-promemoria.md](brief-incassi-riconciliazione-rate-promemoria.md)
> §3-bis; passi **S1-14 … S1-17** in
> [brief-db-posting-e-abbinamento-rata.md](brief-db-posting-e-abbinamento-rata.md)

⚠️ **E la matrice è INCOMPLETA, non sbagliata — rilievo del 2026-08-29.** Dice
da quale stato si passa a quale, e **non dice niente su quale stato si possa
NASCERE**. Non era una dimenticanza finché l'unico a fare `INSERT` era il giro
automatico, che scrive sempre `DISPONIBILE`; dal **2026-08-22**
`pagamenti.fn_conferma_sistemazione` fa nascere il fondo del riporto
**`ASSEGNATO`**, ed è legittimo.

```text
stati di nascita ammessi:  DISPONIBILE (giro automatico) | ASSEGNATO (riporto)
stati di nascita vietati:  ESEGUITO | ANNULLATO   ← un atto che nasce già
                                                    terminale è un record che
                                                    non è mai stato vero
```

🔴 **Oggi i due vietati passerebbero senza che nulla protesti**: il trigger è
montato **solo `BEFORE UPDATE`** (verificato sul catalogo), e il `CHECK`
`chk_fondi_source_stato` ammette tutti e quattro i valori. È il passo **D-22**
(§9.2-c), che monta il guard anche in `INSERT` — ⚠️ **dopo** aver verificato che
non rompa il riporto, che è il caso da **ammettere**, non da bloccare.
> §2.1. ~~⛔ **Non applicato**: è un piano.~~
> ✅ **APPLICATO il 2026-08-21**, e non da questo cantiere: `20260821-49`
> (vocabolario `stato` a quattro valori), `-50` (guard di transizione esteso),
> `-54` (`fn_reset_fondi_fattura` che **cancella** l'atto non eseguito invece di
> riportarlo a `DISPONIBILE`), più il trigger
> `pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito` che scrive
> `ESEGUITO`. ⚠️ Ne discende che **anche D-16 è cambiato** e che il testo di
> D-16 in Fase E descrive un reset che non esiste più: la voce del `manual/`
> della tabella è quella giusta.
> 🔴 **E resta un residuo di catalogo**: la descrizione di
> `E_FONDO_STATO_NON_AMMESSO` in `codici_errore.csv` racconta ancora la matrice a
> **tre** stati. È il posto in cui uno sviluppatore va a cercare la regola quando
> il codice scatta — passo **D-19** in §9.

🔴 **Prima di scrivere il guard, leggere `db/pgtap/vendite/test-fondi-fattura.sql`.**
Quel file percorre `ASSEGNATO → DISPONIBILE` (test 9-10) e `→ ANNULLATO` (test
15-16): un guard restrittivo scritto senza guardarlo lo fa diventare rosso, e il
rosso sembrerà una regressione del fondo invece che una fixture da adeguare.

**Perché un CHECK + trigger e non una tabella di stati con le transizioni
dichiarate**: gli stati del fondo non sono un workflow che l'operatore vede — non
hanno etichette, icone, azioni di UI. Sono tre valori interni. Se un domani
servono etichette o transizioni configurabili, la lookup si aggiunge allora.

##### D-8 — Un solo atto vivo per sorgente

Oggi **nulla** impedisce due fondi vivi sulla stessa fattura sorgente: il
`NOT EXISTS` dell'`INSERT` è dentro una funzione, non un vincolo.

```sql
CREATE UNIQUE INDEX uq_fondi_source_atto_vivo_automatico
  ON vendite.fatture_fondi_fattura_source (fattura_sorgente_id, tipo_fondo_fattura_id)
  WHERE stato IN ('DISPONIBILE','ASSEGNATO') AND origine = 'AUTOMATICA';
```

⚠️ **Non è pignoleria**: due fondi vivi sulla stessa sorgente producono **due
righe contabili** su di lei, la cui somma supera il suo residuo — ed è
esattamente il modo in cui `importo_target` va sotto zero senza che esista un
solo movimento (§8.0-a). Il vincolo chiude quella porta dall'interno.

⚠️ **Il predicato è ristretto a `origine = 'AUTOMATICA'` di proposito**: è
l'automatismo che non deve poterne creare due. Un secondo atto **manuale** sulla
stessa sorgente (un accredito accanto a un addebito, F-3) è la scelta di una
persona, ed è visibile nell'elenco.

⚠️ E l'indice **non** ha `NULLS NOT DISTINCT`: le due colonne della chiave sono
`NOT NULL`, quindi non serve — ma va verificato e non dato per scontato, perché è
il punto in cui una chiave con NULL fallisce in silenzio.

#### Fase C — La proposta derivata e l'elenco da guardare

> ✅ **APPLICATA E VERDE il 2026-08-15.** Cinque changeSet (`20260815-19` … `-23`),
> pgTAP del governo da 18 a **29** asserzioni, baseline `vendite` senza
> regressioni. Elenco, scoperte e residui in **§8.2-quinquies**. ⚠️ I passi sono
> **due sulla carta e cinque nei file**: la ragione — la stessa regola non può
> stare in due posti — è la scoperta principale della fase.

| | Passo | Dove |
| --- | --- | --- |
| **D-9** | **`vendite.fn_fondo_fattura_proponibile(p_fattura_sorgente_id, p_tipo_fondo_fattura_id)`** `STABLE` — il numero, **mai conservato**. Costruita su `fn_saldo_sorgente_fondo` (D-3), così proposta e guard non possono divergere | `20_code/vendite/` |
| **D-10** | **`vendite.vw_fondi_fattura_da_decidere`** — l'elenco. ⚠️ `security_invoker = true` **obbligatorio** | `20_code/vendite/` |

##### D-10 — I casi che chiedono una persona

| Caso | Motivo | Azione suggerita |
| --- | --- | --- |
| sorgente nella banda e definitiva, **nessun atto vivo** | `PROPOSTA_SENZA_ATTO` | emettere il fondo (o lasciarlo) |
| sorgente nella banda **senza `utility_id`** (dato incompleto, esclusa da D-4) | `UTILITY_NON_ATTRIBUIBILE` | completare il dato sulla fattura |
| atto `DISPONIBILE` non più capiente (rifiutato da D-3b) | `NON_PIU_CAPIENTE` | annullare l'atto, o gestire il pagamento ricevuto |
| ⭐ **aggiunto scrivendo**: residuo che **non corrisponde** al documento — l'automatismo tace in silenzio | `IMPORTO_NON_CORRISPONDENTE` | capire da dove viene la riga contabile che sfonda il documento |
| ~~soglie configurate **a metà** sull'emittente × utility~~ | ~~`CONFIGURAZIONE_INCOMPLETA`~~ | 🔴 **non esiste**: D-0 è applicato dal 2026-08-15 e rende il caso irraggiungibile (vedi qui sotto — era previsto) |

> 🔴 **Il caso «eccedenza da destinare» è uscito da questo elenco** (2026-08-15).
> Un sovra-incasso è materia del **processo rimborsi**, che sta in `pagamenti` e
> **se le va a cercare da sé** (§8.1 F-3, decisione di Tid): metterlo anche qui
> significherebbe due elenchi che raccontano lo stesso fatto e che divergono al
> primo cambio. `vendite` espone un punto d'ingresso, non un secondo cruscotto.

⚠️ **`CONFIGURAZIONE_INCOMPLETA` ha una data di scadenza**: dopo D-0 quella riga
non può più esistere, perché il vincolo la rende insalvabile. Va tenuta finché il
CHECK non è applicato **e le righe storiche non sono sanate**, poi tolta — una
riga di elenco che non può accadere insegna una cosa falsa a chi la legge.

⚠️ **La vista presenta, non sana.** Nessuna riga di questa vista deve avere un
gemello che la corregge da sola. È la regola pratica di §5.2, e qui è dove si
vede se è stata rispettata.

⚠️ **`security_invoker` non è una rifinitura**: `vendite.fatture` ha la RLS
operatori, `fatture_fondi_fattura_source` **no**. Una vista che le unisce senza
`security_invoker` mostrerebbe a ogni operatore i fondi di **tutti** gli
emittenti. Il progetto ha già pagato questo difetto una volta (fix V-1 della
fatturazione a due lenti).

**Il vocabolario dei motivi** sta in un `CHECK` sulla colonna della vista, non in
una lookup: sono quattro valori chiusi e nessuno li configura. Le etichette le
mette il FE con `labelOrCode` (fail-visible), come per i motivi di fermo del
cruscotto backlog. ℹ️ Oltre i sei-sette valori la scelta si ribalta e diventa una
`config.motivi_fondo_fattura` sul modello di `config.motivi_fermo`.

#### Fase D — L'atto manuale · **è la porta del processo rimborsi**

> ⭐ **Chi chiama non è uno schermo di `vendite`**: è il **processo rimborsi**, in
> `pagamenti`, quando l'operatore sceglie la terza uscita (§8.1 F-3). Questa fase
> costruisce **la porta**, non la stanza dietro.
>
> 🔴 **SUPERATA il 2026-08-22, e va letta sapendolo** (rilievo del 2026-08-29).
> Il processo rimborsi è arrivato e **non è passato di qui**:
> `pagamenti.fn_conferma_sistemazione`, ramo `RIPORTO`, scrive il fondo con un
> `INSERT` diretto. Di questi quattro passi **D-11 e D-13 vanno ridiscussi**
> (il consumatore per cui erano scritti non li userebbe), mentre **D-12 diventa
> più urgente di prima**: è la contropartita che manca a una strada già aperta.
> Tutto in **§9** — questa tabella resta com'era perché è il ragionamento su cui
> §9 lavora.

| | Passo | Dove |
| --- | --- | --- |
| **D-11** | **`vendite.fn_crea_fondo_fattura_manuale(...)`** — madre DB. Crea l'atto `MANUALE`: sorgente, tipo, importo (**segno libero**), motivo **obbligatorio**. Guard: sorgente esistente, scope emittente, `importo <> 0`. ⚠️ **Non** applica la corrispondenza di D-3(a): sarebbe proprio il caso che deve passare | `20_code/vendite/` |
| **D-12** | ~~**`vendite.fn_annulla_fondo_fattura(p_source_id, p_motivo)`** — porta ad `ANNULLATO` con motivo obbligatorio. **Rifiuta** se il fondo è `ASSEGNATO` su una figlia la cui contabile è `CHIUSA` — stesso criterio di `fn_reset_fondi_fattura`, **riusato e non riscritto**~~ 🔴 **SUPERATO il 2026-08-29 (G-1)**: non si **annulla**, si **cancella** — `fn_cancella_fondo_fattura(p_source_id)`, senza motivo, perché un atto che non è mai diventato un fatto non lascia una riga di registro. Diventa **D-21** (§9.3), che è un'**estrazione** da `fn_reset_fondi_fattura` e non una funzione nuova. ⭐ Il criterio del rifiuto sopravvive, e cresce: ai **tre** blocchi (che parlano di **denaro**) si aggiunge la quarta condizione sullo stato della **figlia** — G-3, §9.7 | `20_code/vendite/` |
| **D-13** | **Azione di processo** `governa_fondo_fattura` — append a `config/azioni_processo.csv` (area 2 = vendite, id 31, `pericolosa = t`) | `80_data/` |
| **D-14** | **Codici errore a catalogo** — append a `config/codici_errore.csv` (codice + **classe**) e `config/messaggi_errore.csv` (id progressivo: l'ultimo è 902) | `80_data/` |

⚠️ **D-14: solo append ai CSV, mai un loader nuovo.** I loader `runOnChange`
esistenti ripescano il file. Codici proposti, con la classe che ne deriva lo
status lato BE:

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_FONDO_NOT_FOUND` | `NON_TROVATO` | il fondo indicato non esiste |
| `E_FONDO_IMPORTO_NON_VALIDO` | `DATO_ERRATO` | importo zero |
| `E_FONDO_NON_CORRISPONDE_SORGENTE` | `DATO_ERRATO` | guard D-3(a): segno opposto al totale della sorgente, o superiore in valore assoluto |
| `E_FONDO_MOTIVO_OBBLIGATORIO` | `DATO_ERRATO` | atto manuale o annullamento senza motivo |
| `E_FONDO_STATO_NON_AMMESSO` | `CONFLITTO_STATO` | transizione fuori dalla matrice di D-7. 🔴 ⚠️ **Seminato, ma la sua descrizione a catalogo racconta ancora TRE stati** mentre dal 21/08 sono **quattro**: è il passo **D-19**, ed è un testo **falso oggi** — lo legge uno sviluppatore proprio quando il guard scatta |
| ~~`E_FONDO_ANNULLAMENTO_BLOCCATO`~~ | ~~`CONFLITTO_STATO`~~ | ~~annullamento rifiutato: contabile già `CHIUSA`~~ 🔴 **CADE con D-12 (2026-08-29, G-1): mai seminato, e non serve più.** Il gesto non è più un annullamento ma una **cancellazione**, e il rifiuto ha ora **quattro** motivi e non uno — chi rifiuta è il **predicato** di D-21 (§9.7-b), che dice *perché* non si può. ⚠️ Se serva un codice nuovo o basti riusarne uno esistente lo decide chi scrive il changeSet **col ramo davanti**: è la domanda «riuso o conio» di §9.7-c, e la risposta si dà guardando **chi può rimediare**, non il nome |
| `E_FONDO_SOGLIE_INCOMPLETE` | `DATO_ERRATO` | D-0: una sola delle due soglie valorizzata |

⚠️ **Leggere il ramo che solleva, non il nome del codice.** Il suffisso
*suggerisce* la classe, non la decide: `E_FONDO_ANNULLAMENTO_BLOCCATO` è un 409 e
non un 403 perché non è un diritto che manca, è lo **stato** della contabile a
impedirlo. ⭐ **La regola resta valida anche se quel codice è caduto** — anzi vale
di più adesso, perché il predicato di D-21 ha quattro rami e uno solo di essi
parla di uno stato di **documento** (la figlia già fatturata) mentre gli altri tre
parlano di **denaro**.

⚠️ **`E_FONDO_NON_CORRISPONDE_SORGENTE` non è un errore che l'operatore può
correggere sul giro automatico**: lì il caso non arriva a sollevare, perché il
`WHERE` della generazione non lo produce (§8.1 F-5). Il codice serve al percorso
manuale e ai presidi — un guard che non solleva mai è un guard di cui nessuno si
accorge quando smette di funzionare.

⭐ **Su `E_FONDO_IMPORTO_NON_VALIDO`, `E_FONDO_MOTIVO_OBBLIGATORIO` e
`E_FONDO_SOGLIE_INCOMPLETE` vale la pena usare `RAISE … USING COLUMN = …`**: il
backend legge già `diag.column_name` e lo consegna al client in `error.fields` —
sono campi di form veri, ed è il caso per cui quel canale è stato aperto. Su
D-0 il campo dice **quale delle due soglie** manca, che è l'unica cosa utile.

#### Fase E — Pulizia e verità documentale

> ✅ **D-15, D-16 e D-17 FATTI** (D-17 in due giri: la bonifica il 2026-08-15, la
> riscrittura al presente delle note 🟠 subito dopo l'apply della Fase B).
> **D-18 è aperto per costruzione**: cresce con ogni fase.

| | Passo |
| --- | --- |
| **D-15** | ✅ **FATTO il 2026-08-15** — **`DROP FUNCTION vendite.fn_sync_pagamento_fondo_fattura(bigint)`** (F-4) + rimozione della §6 di `db/pgtap/vendite/test-fattura-utils-critical-termini.sql` e `plan(15)` → `plan(14)`. ⚠️ Le due metà nello **stesso lotto**: il presidio dei riferimenti morti gira dopo il `migrate` e un `DROP` senza il test diventa rosso in CI |
| **D-16** | ✅ **FATTO il 2026-08-15** — `COMMENT` su `fn_reset_fondi_fattura`: è il reset **tecnico della figlia**, non una reazione ai pagamenti (F-2) |
| **D-17** | ✅ **Bonifica documentale — FATTA il 2026-08-15** (ordine di Tid: *«procedi alla correzione di tutti»*). Inventario e stato per documento qui sotto. ⚠️ Solo i `manual/`, le guide e i doc di lavoro: gli auto-gen si rigenerano. ✅ **Secondo giro fatto** dopo l'apply di Fase A e Fase B: le note 🟠 sono state riscritte **al presente**. Resta la stessa regola per le fasi che verranno |
| **D-18** | pgTAP — §8.5 |

##### D-17 — L'inventario, e ⚠️ la distinzione che conta

Ricognizione fatta il **2026-08-15** su tutta `docs/` più il codice, su richiesta
di Tid; **correzioni applicate lo stesso giorno**. ⭐ **La distinzione utile non è
«giusto/sbagliato», è *quando*:**

* 🔴 **sbagliato oggi** — il documento non descrive il codice che gira. Va
  corretto **subito**, indipendentemente dal piano;
* 🟠 **lo diventa con l'implementazione** — oggi è fedele. ⭐ **Non riscritto al
  futuro, ma annotato**: la descrizione di com'è resta, e accanto c'è una tabella
  *«oggi → diventerà, con quale passo»*. Riscriverlo al presente adesso
  racconterebbe un sistema che non esiste; lasciarlo muto lo farebbe progettare
  sopra da chi arriva domani.

###### 🔴 Sbagliato oggi — tre

| Documento | Che cosa dice di falso |
| --- | --- |
| `dbzero/vendite/manual/fn_genera_fondi_fattura_source.md` | *«Seleziona fatture nel perimetro BA/**utility**/tipo_doc/emittente/valuta»* — **la funzione su `utility` non filtra affatto** (D-4). La doc dichiara un perimetro che il codice non applica: è il difetto e la sua smentita nello stesso posto |
| `dev/work-done/fatturazione-attivita-progetto.md` §«Analisi fondi fattura (WIP)» | Un **design mai eseguito** parcheggiato in `work-done/`: policy `riapribile` per tipologia di fondo, *«se arriva uno storno la source torna DISPONIBILE»* — cioè un **automatismo che scrive in reazione a un pagamento**, escluso da §3-bis del cantiere incassi; e *«lo storno»*, che dopo D3-d **non è più un concetto**. In più `SUM(importo) >= totale_a_pagare` come regola di «pagata»: su un documento a credito il confronto si inverte |
| `guide/gestione-dei-pagamenti.md` §Fondi fattura | *«es. importo minimo **non raggiunto**»* — racconta **solo il capo superiore** della banda. Chi legge conclude che un fondo è sempre a debito: è **precisamente l'errore che abbiamo commesso noi** scrivendo il tampone `> 0`. E delle due soglie — la configurazione che accende tutto — non c'è traccia |

###### 🟠 Diventeranno sbagliati — quattro, ognuno legato al suo passo

| Documento | Cosa supera | Con |
| --- | --- | --- |
| `manual/fn_genera_fondi_fattura_source.md` | *«mantiene allineata la source in base al saldo»*, il ramo `UPDATE`, l'`ANNULLATO` a saldo zero, *«idempotente: riallinea i dati»* | **D-1** |
| `manual/fn_applica_fondi_fattura.md` | la chiave a cinque elementi; nessun controllo di capienza | **D-3b**, **D-4** |
| `manual/fatture_fondi_fattura_source.md` | *«In caso di storni, la policy di riapertura va gestita per tipologia fondo»* + *«Reset per tipologie non standard (WIP)»*; `ANNULLATO` = «documento sorgente già saldato» | **D-1**, e D3-d incassi |
| `manual/fn_sync_pagamento_fondo_fattura.md` | **il file intero**: è il manuale di una funzione che si ritira | **D-15** |

> ✅ **Secondo giro fatto il 2026-08-15**, applicate Fase A e Fase B: le quattro
> note sono state **riscritte al presente**, non lasciate al futuro. Le prime due
> con la Fase A; la terza (`manual/fatture_fondi_fattura_source.md`) con la Fase
> B — la tabella *«oggi → diventerà»* è diventata *«prima → adesso, e chi lo fa»*,
> con l'elenco degli otto presidi vivi; la quarta è sparita **col file**.
> Aggiornati nello stesso giro `manual/fn_reset_fondi_fattura.md` e
> `manual/fn_sync_contabili_fondo_fattura.md` (annullamento **con ragione sul
> dato**, saldo letto da `fn_saldo_sorgente_fondo`) e la sezione «perimetro» di
> `manual/trgfn_fondi_source_guard_importo.md`, che dava al futuro il ritiro dalla
> strada manuale ormai applicato dal `-18`. ⭐ **Scritto il `manual/` nuovo** di
> `trgfn_fondi_source_guard_transizione`.

###### ⭐ Due documenti che invece avevano ragione, e che avremmo dovuto leggere prima

| Documento | Cosa dice |
| --- | --- |
| `manual/fn_ricalcola_totali_fattura.md` | *«Imposta `minimo = true` quando `totale_a_pagare` **rientra nella soglia** (`minimo_soglia_min`/`minimo_soglia_max`)»* — è **l'unico posto in tutta la documentazione dove la banda è detta correttamente**. Manca solo l'avvertenza sul fail-open (D-0) |
| `manual/tipi_fondi_fattura.md` | *«addebiti/**accrediti** fatture precedenti»* — il verso a credito era **previsto dall'origine**. Il tampone `> 0` contraddiceva il catalogo, non solo il dominio |

🔴 **La lezione, e vale oltre questo cantiere**: la banda era scritta in due
documenti su venti, e nessuno dei due era quello che descrive il **fondo**. La
regola vive nella funzione che scrive `minimo`, non in quella che legge il flag —
*chi documenta un consumatore non documenta la regola che lo governa.*

###### Rifiniture minori (stesso lotto, costo nullo)

* `manual/fatture.md`: *«opzione "fattura di minimo"»* — non è un'opzione, è un
  **calcolo**. È l'equivoco di §8.0-b in due parole;
* `manual/centri_riscossione.md`: corretto, ma manca la nota **non-cassa** —
  quei centri vanno esclusi da ogni misura di «incassato» (Fase F);
* `mappa-concentrica.md` §406: *«Non urgente oggi, lo diventa col primo incasso
  reale»* — superato da §8.0-a.

⚠️ **Una classificazione da correggere altrove**:
`dev/work-done/analisi-attivazione-rls-operatori.md` archivia
`fatture_fondi_fattura_source` come **«NO — config. Config di fatturazione»**. La
*conclusione* (niente RLS) resta giusta — il perimetro passa dalla fattura — ma
la **ragione** è falsa: non è configurazione, è un registro transazionale che
muove denaro. Una ragione sbagliata produce la decisione sbagliata al giro dopo,
quando la domanda cambia.

**✅ Nessuna azione** su: `readme.md`, `soggetti-e-ruoli-anagrafici.md`,
`api_fattura_dettaglio.md`, i tre brief RLS, `correzione-e-generico.md`,
`fn_cleanup_fatture_by_ids.md` (anzi: la sua nota *«il reset non cancella la
source, ne azzera l'assegnazione»* è **esatta e utile**),
`fn_scope_ba_ownership_via_fattura.md`, `api_lookup_codici.md`. Sono elenchi e
censimenti. **Nel codice** (`backend/`, `frontend/src/`) non esiste una sola
riga che descriva la logica del fondo: due sole occorrenze, entrambe etichette
(`"Tipo fondo fattura non trovato."`, `'Tipi Fondi Fattura'`).

#### Fase F — Il confine col posting: qui si **dichiara**, non si fa

⭐ **Verificato il 2026-08-15, e corregge in meglio un timore del cantiere
incassi.** Il B-1 di quel brief teme che portare una riga a `POSTATA` faccia
rigenerare il fondo. Con un posting **atomico** (D3-b: cambio di stato e
creazione del movimento nella stessa unità) **la bilancia regge da sé**:

```text
prima :  target = totale − 0        − importo      = totale − importo
dopo  :  target = (totale − importo) − 0           = totale − importo
```

I due termini si scambiano lo stesso importo. 🔴 **Il rischio B-1 è tutto nella
non-atomicità**, che D3-b risolve per costruzione — non c'è un secondo lavoro da
fare qui.

⚠️ **Ma resta una cosa da scrivere adesso nel brief incassi, non da scoprire
dopo.** La riga contabile che il fondo crea è `ABBINATA`, cioè **postabile**:
quando il posting esisterà diventerà un `vendite_movimenti` — ed è **giusto**,
perché la sorgente è davvero stata saldata, per **trasferimento** e non per
cassa. Segue che **ogni misura di «incassato» deve escludere i centri non-cassa**
(`is_fondo_fattura`, `is_compensazione`), altrimenti conta come denaro arrivato
ciò che è solo stato spostato da una fattura a un'altra.

---

### 8.2-bis Fase A — applicata il 2026-08-15

> ✅ **Migrazione applicata, suite verde, doc rigenerata.** Resta il **commit**.
>
> | Verifica | Esito |
> | --- | --- |
> | `migrate` dei 7 changeSet | ✅ applicati (i due CHECK e il trigger risultano nell'auto-gen) |
> | `test-fondi-fattura-governo.sql` | ✅ **12/12** (dopo la correzione di §8.2-ter) |
> | `test-fondi-fattura.sql` (fixture adeguata) | ✅ **19/19** |
> | `pgtap-baseline.sh vendite` | ✅ **nessuna regressione** — 24 rossi, tutti noti |
> | guardrail statici CI (`runOnChange`, preambolo pgTAP) | ✅ verdi; il debito `throws_ok` resta a 137 su soglia 137 |
> | doc `dbzero` | ✅ rigenerata: i due `manual/` nuovi sono agganciati alle pagine auto-gen |

| File | Passo | Cosa fa |
| --- | --- | --- |
| `00_schema/anagrafiche/20260815-03-add-check-emittenti-fiscali-utilities-soglie-coppia` | **D-0** | CHECK «entrambe le soglie o nessuna». ✅ Applicabile senza sanatoria: le due righe esistenti hanno entrambe vuote (verificato con Tid) |
| `00_schema/vendite/20260815-04-add-check-fondi-source-importo-e-stato` | **D-2** | `importo <> 0` + vocabolario chiuso di `stato`. Tabella a zero righe |
| `20_code/vendite/20260815-05-create-fn-saldo-sorgente-fondo` | **D-3** | La formula unica «quanto regge ancora la sorgente», estratta dalla copia inline |
| `20_code/vendite/20260815-06-create-trgfn-fondi-source-guard-importo` | **D-3a** | Guard di corrispondenza fondo ↔ sorgente (segno + valore assoluto) |
| `20_code/vendite/20260815-07-update-fn-genera-fondi-fattura-source-atto-unico` | **D-1 + D-4** | Solo sorgenti `DEFINITIVA`; via il ramo `UPDATE` e l'`ANNULLATO` automatico; `utility_id` entra nel filtro |
| `20_code/vendite/20260815-08-update-fn-applica-fondi-fattura-chiave-e-capienza` | **D-3b + D-4** | Chiave a nove elementi riga-contro-riga + rilettura della capienza |
| `20_code/vendite/20260815-09-update-fn-sync-contabili-fondo-adotta-saldo-sorgente` | coda D-3 | La sync adotta la formula estratta (behavior-preserving) |
| `80_data/sql/config/{codici_errore,messaggi_errore}.csv` | **D-14** parziale | `E_FONDO_NON_CORRISPONDE_SORGENTE`, `E_FONDO_SOGLIE_INCOMPLETE` — solo append, nessun loader nuovo |
| `db/pgtap/vendite/test-fondi-fattura-governo.sql` | **D-18** | 12 asserzioni sulla Fase A |
| `db/pgtap/vendite/test-fondi-fattura.sql` | — | ⚠️ **fixture adeguata**: la fattura sorgente nasceva senza stato e senza utility, e con i nuovi filtri non avrebbe più generato niente |
| `dbzero/vendite/manual/fn_saldo_sorgente_fondo.md` · `trgfn_fondi_source_guard_importo.md` | — | Doc concettuale delle due funzioni nuove, nello standard dei `manual/` |

#### ⚠️ Tre scelte fatte scrivendo, che vale la pena conoscere

**1. Le firme non cambiano, e non è pigrizia.** La chiave a nove elementi si
chiude **dentro** `fn_applica_fondi_fattura`, che ha già sotto mano entrambe le
fatture: nessun parametro nuovo, nessun tocco a `backend/` — che è fuori dal
perimetro DB. La madre DB per lotto resta una **richiesta al BE** (§8.3).

**2. I cinque parametri di scope cambiano mestiere.** Da filtro sulla *source* a
verifica sulla *figlia*. Applicati alla source erano ridondanti e potevano far
**saltare in silenzio** un fondo la cui colonna denormalizzata fosse rimasta
indietro; sulla figlia sono una sanity check che non può nascondere niente.

**3. La preCondition sul codice errore è stata tolta dal changeSet -06.** `20_code`
gira **prima** di `80_data`: su un DB ricostruito da zero avrebbe cercato un seed
che arriva due fasi dopo. Trappola già registrata, e già pagata una volta.

### 8.2-ter 🔴 Il difetto trovato nel collaudo: ho collaudato il guard credendo di collaudare il CHECK

La prima corsa ha dato **una regressione**, e il rosso era del test — non del
codice. Vale la pena scriverla per intero, perché è **la trappola che avevo
appena finito di scrivere in §8.5**.

```text
# Failed test 3: "D-2: importo zero rifiutato dal CHECK"
#       caught: P0001: Fondo fattura di importo 0 non coerente con la
#               fattura di origine (totale 100.00).
#       wanted: 23514
```

**Perché.** I trigger `BEFORE ROW` girano **prima** dei CHECK. Su una sorgente
da 100, un `importo = 0` non arriva mai al vincolo: lo intercetta il guard di
corrispondenza, perché `sign(0)` non è il segno di **nessun** totale diverso da
zero. Il test chiedeva `23514` e otteneva `P0001` — cioè misurava il presidio
sbagliato.

**La correzione, ed è più di un cambio di SQLSTATE.** Il CHECK
`importo <> 0` è raggiungibile **solo da una sorgente a totale zero**, dove il
guard passa (0 e 0 hanno lo stesso segno e lo stesso valore assoluto). Il test
ha quindi una quinta fixture, `SRC_ZERO`, e collauda il vincolo dove il vincolo
esiste davvero. ⭐ Che è poi l'unico caso in cui serve: una fattura da zero non
genera fondo, e se qualcuno lo inserisse a mano è lì che il CHECK lo ferma.

> **La lezione, e non è «leggere meglio»**: avevo scritto l'avvertenza,
> l'ho ripetuta nel `COMMENT` della funzione, e ci sono cascato lo stesso —
> perché la trappola non sta nel *sapere* l'ordine di esecuzione, sta nel
> **nominare l'asserzione**. «Rifiutato dal CHECK» descrive il *meccanismo* che
> credo agisca; se avessi scritto «importo zero rifiutato» avrei asserito il
> *fatto*, e il test sarebbe passato dicendo una cosa vera. *Un test che nomina
> il meccanismo invece del comportamento verifica la propria ipotesi, non il
> sistema.*

#### 🔵 Cosa resta scoperto

* **Il caso «sorgente non più capiente» non ha un test runtime.** Per costruirlo
  serve una riga contabile `ABBINATA` sulla sorgente — cioè la fixture pesante
  che `test-fondi-fattura.sql` costruisce già. È l'assenza più importante di
  §8.5: il guard di capienza (D-3b) oggi è **collaudato solo per la via che
  passa**, non per quella che deve fermare;
* **l'`ANNULLATO` automatico dentro `fn_sync_contabili_fondo_fattura` resta.** È
  della stessa specie di quello rimosso dalla generazione, ma opera su fondi
  **già assegnati**: il denaro si è mosso, e toglierlo senza il processo rimborsi
  di `pagamenti` lascerebbe scoperto il doppio conteggio. 🔵 Candidato Fase B;
* **le tre richieste al BE** (§8.3) non sono state fatte: sono fuori perimetro.
  ⚠️ **R-1 è la più urgente** — finché `error_policies_generated.py` non viene
  rigenerato, i due codici nuovi sono a catalogo ma non hanno una classe lato
  backend, e il cancello `test_error_codes_db_policy_guardrail` lo vedrà.

ℹ️ Il dubbio sul test D-0 è risolto: il ruolo applicativo **ha** la scrittura su
`anagrafiche.emittenti_fiscali_utilities`, e il CHECK scatta come previsto
(`23514`). Nessun marcatore `-- pgtap-runner: owner` necessario.

---

### 8.2-quater Fase E (coda) e Fase B — **applicate** il 2026-08-15

> ✅ **Applicate e verdi.** `migrate` dei 9 changeSet `20260815-10`…`-18` (tutti
> `EXECUTED`), `test-fondi-fattura-governo` **18/18**, `test-fondi-fattura`
> **20/20**, `test-fattura-utils-critical-termini` **14/14**,
> `pgtap-baseline.sh vendite` **senza regressioni**. Dettaglio di cosa ha detto
> l'applicazione: più sotto, in *«L'applicazione, e cosa ha detto»*.

#### Coda della Fase E — i due passi facili

| File | Passo | Cosa fa |
| --- | --- | --- |
| `20_code/vendite/20260815-10-drop-fn-sync-pagamento-fondo-fattura` | **D-15** | `DROP` del guscio. ⚠️ Nello **stesso commit**: sezione tolta da `test-fattura-utils-critical-termini.sql` (`plan(15)` → `plan(14)`, indice rinumerato) e `manual/` eliminato |
| `20_code/vendite/20260815-11-comment-fn-reset-fondi-fattura-reset-tecnico` | **D-16** | Solo il `COMMENT`: il reset è **tecnico sulla figlia**, non una reazione ai pagamenti (F-2) |

#### Fase B — il registro degli atti

| File | Passo | Cosa fa |
| --- | --- | --- |
| `00_schema/vendite/20260815-12-add-fondi-source-origine-e-motivo` | **D-5** | Colonne `origine` (`AUTOMATICA`\|`MANUALE`) e `motivo` |
| `20_code/vendite/20260815-13-update-fn-fondi-annullamento-con-motivo` | **D-5** | I due scrittori automatici **valorizzano `motivo`** quando annullano |
| `00_schema/vendite/20260815-14-add-check-fondi-source-motivo-obbligatorio` | **D-5** | `motivo` obbligatorio su `MANUALE` e su `ANNULLATO` |
| `20_code/vendite/20260815-15-create-trg-fondi-source-lock-atto` | **D-6** | Lock di colonna: `importo`, sorgente, tipo, `origine` immutabili |
| `20_code/vendite/20260815-16-create-trgfn-fondi-source-guard-transizione` | **D-7** | Matrice degli stati, `ANNULLATO` terminale |
| `00_schema/vendite/20260815-17-add-uq-fondi-source-atto-vivo` | **D-8** | Indice unico parziale: un solo atto automatico vivo per sorgente |
| `20_code/vendite/20260815-18-update-trgfn-...-solo-automatica` | coda **D-5** | Il guard di corrispondenza si **ritira dalla strada manuale** |
| `80_data/…/{codici_errore,messaggi_errore}.csv` | **D-14** parz. | `E_FONDO_ATTO_IMMUTABILE`, `E_FONDO_STATO_NON_AMMESSO`, `E_FONDO_MOTIVO_OBBLIGATORIO` |
| `db/pgtap/vendite/test-fondi-fattura-governo.sql` | **D-18** | da 12 a **18** asserzioni |
| `db/pgtap/vendite/test-fondi-fattura.sql` | **D-18** | da 19 a **20**: la ragione dell'annullamento verificata **sul dato** |
| `docs/it/dbzero/vendite/manual/` | **D-17** | nuovo `trgfn_fondi_source_guard_transizione`; aggiornate la pagina della tabella, `trgfn_fondi_source_guard_importo`, `fn_reset_fondi_fattura`, `fn_sync_contabili_fondo_fattura` |

#### ⚠️ Tre cose scoperte scrivendo la Fase B

**1. `motivo` obbligatorio impone di toccare due funzioni che il piano non
nominava.** Un fondo passa ad `ANNULLATO` in due punti automatici — la sync
contabili e il reset bloccato — e nessuno dei due scriveva una ragione: nel
secondo la ragione esisteva, ma **in un messaggio di `fatture_log`**, cioè in un
diario invece che sul dato. Da qui il changeSet `-13`, e l'**ordine obbligato**
`-12` → `-13` → `-14`: mettere il vincolo prima degli scrittori lo farebbe
passare sulla tabella vuota di oggi e fallire al primo reset vero — un migrate
verde e un guasto rimandato a quando fa più male.

**2. `origine` senza il changeSet `-18` non governa niente.** Il piano diceva
che il guard di corrispondenza «si restringerà a `AUTOMATICA` con la Fase B», ma
non lo elencava fra i passi. Senza, la colonna esisterebbe e il guard
continuerebbe a rifiutare **proprio** l'atto per cui la strada manuale esiste —
l'eccedenza di un sovra-incasso, che è un credito su una fattura positiva.

**3. `atto_precedente_id` è stato tolto per davvero.** Non c'è nel `-12`: serviva
alla revoca+riemissione, e la catena dei riporti resta leggibile da
`fatture_fondi_fattura.riferimento_fattura_id`.

#### ✅ L'applicazione, e cosa ha detto

Gli oggetti vivi sulla tabella dopo il migrate — verificati sul catalogo, non
dedotti dai file:

| Presidio | Oggetto |
| --- | --- |
| vocabolario `stato` · vocabolario `origine` · `importo <> 0` · `motivo` obbligatorio | `chk_fondi_source_stato`, `chk_fondi_source_origine`, `chk_fondi_source_importo_non_zero`, `chk_fondi_source_motivo_obbligatorio` |
| corrispondenza · cammino degli stati · identità dell'atto | `..._a10_guard_importo_ins_upd`, `..._a10_guard_transizione_upd`, `..._a10_lock_atto_upd` |
| un solo atto automatico vivo | `uq_fondi_source_atto_vivo_automatico` |
| i cinque codici | tutti presenti in `config.codici_errore` con la loro classe |

**⚠️ Ma il migrate verde non è una prova, e qui si vede bene.** La tabella
`fatture_fondi_fattura_source` ha **zero righe**: i cinque presidi nuovi sono
passati senza incontrare un solo dato. Se `motivo` fosse stato reso obbligatorio
su una tabella popolata, il `-14` sarebbe fallito; con la tabella vuota
sarebbe passato **comunque**, e il guasto si sarebbe visto al primo reset vero.
L'unica prova che i presidi funzionano sono i pgTAP.

**⭐ E la prova che l'ordine `-12` → `-13` → `-14` era necessario esisteva già,
senza che nessuno l'avesse chiesta.** `test-fondi-fattura.sql` esercita da mesi
il ramo «reset bloccato da contabile `CHIUSA`» — cioè **l'annullamento
automatico**. Se il `-13` non avesse preceduto il `-14`, quella sezione sarebbe
diventata rossa: il reset avrebbe scritto `ANNULLATO` senza `motivo` e il CHECK
lo avrebbe respinto. Il test era verde **per merito**, ma non lo diceva.

🔵 Da qui l'unica aggiunta di oggi: `test-fondi-fattura.sql` passa da 19 a **20**
asserzioni, e la ventesima verifica che la ragione dell'annullamento stia **sul
dato** (`motivo`) e non solo in `fatture_log`. Non aggiunge copertura — la
aggiungeva già il vincolo — ma **la dichiara**: un verde per sottrazione e un
verde per merito si somigliano troppo perché la differenza resti implicita.

ℹ️ Verificato di conseguenza anche che il **lock di colonna non rompe i percorsi
vivi**: applicazione, reset, sync e annullamento aggiornano `stato`,
`fattura_figlia_id`, `data_assegnazione` e `motivo` — mai le quattro colonne
bloccate. Non è un ragionamento: sono le funzioni che i due pgTAP chiamano
davvero.

#### 🔵 Cosa resta scoperto dopo la Fase B

* il **caso «sorgente non più capiente»** continua a non avere un test runtime
  (serve una riga contabile in fixture) — è il residuo più vecchio;
* l'**`ANNULLATO` automatico** della sync resta: ora almeno **dichiara la sua
  ragione**, ma è ancora uno stato cambiato senza una persona. Si toglie quando
  `pagamenti` avrà il processo rimborsi;
* le **richieste al BE** (§8.3) sono ora **cinque codici errore** da portare in
  `error_policies_generated.py`, non due.

---

### 8.2-quinquies Fase C — **applicata** il 2026-08-15

> ✅ **Applicata e verde.** `migrate` dei 5 changeSet `20260815-19`…`-23`,
> `test-fondi-fattura-governo` **29/29**, `test-fondi-fattura` **20/20** (il
> refactor di generazione e applicazione non sposta niente),
> `test-fattura-utils-critical-termini` **14/14**, `pgtap-baseline.sh vendite`
> **senza regressioni**. Doc `dbzero` rigenerata, tre `manual/` nuovi.
> ⚠️ **Un incidente durante l'applicazione**, per colpa mia: in fondo alla sezione.

| File | Passo | Cosa fa |
| --- | --- | --- |
| `20_code/vendite/20260815-19-create-fn-fondo-fattura-proponibile` | **D-9** | `fn_fondo_fattura_proponibile(sorgente, tipo)`: l'importo che l'automatismo scriverebbe **oggi**, o `NULL` se non farebbe niente |
| `20_code/vendite/20260815-20-update-fn-genera-fondi-consuma-proponibile` | coda **D-9** | La generazione **consuma** la proposta invece di riscrivere l'inviluppo |
| `20_code/vendite/20260815-21-create-fn-check-fondo-fattura-capiente` | serve **D-10** | La regola di capienza estratta in un predicato **puro e `IMMUTABLE`** |
| `20_code/vendite/20260815-22-update-fn-applica-fondi-usa-check-capiente` | coda **D-10** | `fn_applica_fondi_fattura` lo consuma, e legge la capienza **una volta sola** |
| `20_code/vendite/20260815-23-create-vw-fondi-fattura-da-decidere` | **D-10** | L'elenco, `security_invoker=on`, quattro motivi |
| `db/pgtap/vendite/test-fondi-fattura-governo.sql` | **D-18** | da 18 a **29** asserzioni |

#### ⭐ La scoperta della fase: «costruita su» non bastava

Il piano diceva che D-9 andava costruita su `fn_saldo_sorgente_fondo` **«così
proposta e guard non possono divergere»**. È vero e insufficiente: il guard non è
l'unico posto da cui la proposta può divergere. L'**inviluppo** — sorgente
`DEFINITIVA`, dentro la banda, utility attribuita, atto unico, corrispondenza col
documento — viveva nel `WHERE` di `fn_genera_fondi_fattura_source`, e scrivere
D-9 senza toccarlo avrebbe creato la **seconda copia** proprio della regola che
D-9 esiste per condividere.

Il divario avrebbe avuto una forma precisa e silenziosa: un elenco che **propone**
un fondo che il giro notturno non crea, o che **tace** su uno che crea. Nessun
errore, nessun log. Da qui il changeSet `-20`.

**E la stessa cosa, una seconda volta, per la capienza.** Il caso
`NON_PIU_CAPIENTE` dell'elenco è la regola del guard D-3b, negata: due copie
avrebbero detto che un fondo è inapplicabile mentre il giro lo applica. Estratta
in `fn_check_fondo_fattura_capiente` (`-21`) e consumata da entrambi (`-22`).

> ⚠️ **E lì si è visto un difetto che nessuno cercava**: il guard chiamava
> `fn_saldo_sorgente_fondo` **due volte sulla stessa riga** — una per il segno e
> una per il valore assoluto. È una funzione `VOLATILE` che interroga
> `pagamenti`: non è solo il doppio del lavoro, sono **due valutazioni
> indipendenti** che in teoria possono rispondere numeri diversi, accettando
> metà condizione e rifiutando l'altra. Ora si legge una volta, in `LATERAL`.

#### ⚠️ Quattro motivi, e nessuno dei due elenchi è quello del piano

| Motivo | Da dove viene |
| --- | --- |
| `PROPOSTA_SENZA_ATTO` | dal piano |
| `UTILITY_NON_ATTRIBUIBILE` | dal piano |
| `NON_PIU_CAPIENTE` | dal piano |
| **`IMPORTO_NON_CORRISPONDENTE`** | ⭐ **nuovo** |
| ~~`CONFIGURAZIONE_INCOMPLETA`~~ | 🔴 **morto alla nascita** |

🔴 **`CONFIGURAZIONE_INCOMPLETA` non c'è**, e il piano lo aveva previsto: *«ha una
data di scadenza, dopo D-0 quella riga non può più esistere»*. D-0 è stato
applicato **questo pomeriggio** (`20260815-03`): una configurazione a metà non è
più salvabile, quindi il caso è irraggiungibile. *Una riga di elenco che non può
accadere insegna una cosa falsa a chi la legge.*

⭐ **`IMPORTO_NON_CORRISPONDENTE` invece non era previsto.** Quando il residuo
non assomiglia al documento — segno diverso, o più grande in valore assoluto —
la generazione **non fa niente**, ed è giusto: un lotto intero non si ferma per
un caso ordinario. Ma «non fare niente **in silenzio**» è esattamente ciò che
questa vista esiste per rendere visibile. È il caso già disegnato nel manuale
del guard: sorgente da +8, riga contabile da +40, fondo che verrebbe −32 — non
«negativo», **di un'altra fattura**.

#### ⚠️ Tre trappole trovate scrivendo la vista

**1. Il `CHECK` sul vocabolario dei motivi non esiste.** Il piano diceva «sta in
un CHECK sulla colonna della vista»: PostgreSQL **non ha** vincoli `CHECK` sulle
colonne di una vista (`WITH CHECK OPTION` governa le scritture, è un'altra cosa).
Il vocabolario è chiuso **per costruzione** — quattro letterali nei rami della
`UNION`, nessun dato li produce — e il presidio contro un quinto valore aggiunto
di nascosto è **il pgTAP**, che asserisce l'**insieme** dei motivi e non la
presenza dei quattro.

**2. 🔴 Il ramo `NON_PIU_CAPIENTE` parte da una tabella senza RLS.**
`fatture_fondi_fattura_source` non ha politiche: quel ramo è protetto dal **JOIN
`INNER` con `vendite.fatture`**, non da un filtro proprio. `security_invoker=on`
è necessario ma non sufficiente — chi un giorno trasformasse quel join in `LEFT`,
o lo togliesse perché «i dati della fattura non servono», aprirebbe l'elenco a
tutti gli emittenti senza accorgersene. Sta scritto nel `COMMENT` della vista.

**3. ⚠️ L'ordine dei rami della `UNION` non è libero.** Per non scrivere i tipi a
mano, i rami senza valore usano `NULL` nudo e prendono il tipo da chi il valore
ce l'ha; ma PostgreSQL risolve a coppie, da sinistra, e il ramo che **non porta
nessuna colonna propria** deve stare per ultimo. Messo per primo, la `CREATE
VIEW` fallisce — rumorosamente, ed è la ragione per cui la scelta è accettabile.

#### ✅ Chiusa la lacuna più vecchia del cantiere

Il caso **«sorgente non più capiente»** era scritto e mai percorso da Fase A,
perché serviva una **riga contabile postabile** in fixture. Adesso c'è: il pgTAP
crea una testata con `fn_get_or_create_vendite_contabile` e due righe `ABBINATA`,
e da lì escono **due** collaudi che prima non esistevano — il motivo
`NON_PIU_CAPIENTE` dell'elenco **e** il guard D-3b che rifiuta l'applicazione
(test 27).

⚠️ Il test 27 ha un **controllo**: accanto al fondo non capiente ne gira uno
capiente che deve essere applicato. Da solo, «il fondo resta `DISPONIBILE`»
sarebbe passato anche se l'applicazione non avesse fatto **niente**.

#### 🔵 Cosa resta scoperto dopo la Fase C

* nessun **indice** su `vendite.fatture (minimo)`: il pre-filtro della vista è un
  `seq scan` su una tabella che oggi ha 12 righe e domani no. ⚠️ Non è stato
  aggiunto perché su dev **non è misurabile** (zero fatture di minimo), e un
  indice scelto senza una misura è una scommessa;
* la vista non è ancora letta da nessuno: **BE-3** in §8.3;
* restano **Fase D** (l'atto manuale, e aspetta il processo rimborsi in
  `pagamenti`) e **Fase F** (dichiarativa).

#### 🔴 L'incidente: ho droppato oggetti che il migrate aveva appena creato

Va scritto perché la forma dell'errore è generale, e il danno era **peggiore di
quello che sembrava**.

**Cosa è successo.** Le prove del lotto sono state fatte eseguendo il SQL in una
transazione poi annullata. Al termine gli oggetti della Fase C risultavano
**presenti** nel database. Ho concluso che una mia prova avesse lasciato
residui — e li ho tolti, ripristinando anche i corpi pre-Fase C di
`fn_genera_fondi_fattura_source` e `fn_applica_fondi_fattura`.

**Cosa era in realtà.** Il `migrate` di Tid era già girato, **in parallelo al mio
lavoro**:

```text
16:56  scrivo il primo file di prova
16:57  ⭐ il migrate applica -19 … -23   ← non lo sapevo
16:59  eseguo le prove
17:01  🔴 "ripulisco" i residui che residui non erano
```

**Perché era peggio di un DROP.** Le righe di `databasechangelog` restavano —
`EXECUTED`, con la loro data — e gli oggetti no. Un `migrate` successivo **non
li avrebbe ricreati**, perché per Liquibase erano già fatti: il database sarebbe
rimasto senza la Fase C, e il changelog avrebbe giurato il contrario. Il difetto
si sarebbe visto solo al primo test rosso, o al primo consumo della vista.

**Come è stato rimediato.** Ri-applicando **il SQL dei cinque changeSet**, senza
toccare `databasechangelog`: è ciò che Liquibase aveva fatto, quindi lo stato
torna esattamente quello atteso invece di riscrivere la storia. Verificato dopo:
oggetti presenti, `29/29` + `20/20` + `14/14`, `fn_genera` e `fn_applica` di
nuovo sui corpi di Fase C.

> ⭐ **La lezione, e vale oltre questo cantiere.** «I miei oggetti di prova hanno
> lasciato residui» era **un'ipotesi**, non una misura — e c'era un modo
> immediato di verificarla che non ho usato: `databasechangelog.dateexecuted`.
> Su un database condiviso **un DROP non è mai una pulizia**: è la rimozione di
> qualcosa che qualcun altro può avere messo lì un minuto fa. La verifica costa
> una query, il danno costa un disallineamento silenzioso fra codice e
> changelog.

---

### 8.3 La logica BE

> **Regola che vale per tutti i passi**: nessun ricalcolo del fondo in Python,
> nessuna scrittura diretta su `fatture_fondi_fattura_source` da un repository.
> Il BE **chiama** e **legge**. È DB-first, e qui è anche l'unico modo di tenere
> la promessa di F-1: un secondo posto che scrive un importo la annulla.

| | Passo | Perimetro | Stato al 2026-08-15 (sera) |
| --- | --- | --- | --- |
| **BE-1** | **La firma cambia, e si accorcia**: le due task passano da 6-7 parametri sciolti a **`(lotto_id, tipo_fondo_id)`**. Conseguenza di D-4 | `apps/vendite/db/pipeline_repository.py` | ⏸️ **assorbito in R-3**: la Fase A ha scelto di **non** cambiare le firme (§8.2-bis), quindi BE-1 non ha più un oggetto proprio |
| **BE-2** | **Atomicità del giro fondi** — difetto esistente, che BE-1 chiude di conseguenza | idem | ✅ **fatto**, ma diversamente da come è scritto qui: vedi il riquadro sotto |
| **BE-3** | **L'elenco «fondi da decidere»** — lettura sola su `vendite.vw_fondi_fattura_da_decidere` (scritta, §8.2-quinquies). ⚠️ La vista è `security_invoker`: va letta con la connessione dell'utente, **non** con un ruolo di servizio, o il perimetro emittente salta. Le etichette dei quattro motivi con `labelOrCode` (fail-visible) | repo + service + view | ✅ **fatto** — `GET /api/v1/vendite/fondi-fattura/da-decidere/`, doc [api_fondi_fattura.md](/backend/vendite/manual/api_fondi_fattura). Il divieto di canale di sistema è un **guard fail-closed** (`connection_role_bypasses_rls`), non un commento |
| **BE-4** | ~~**La porta dell'atto manuale** — D-11 e D-12, chiamate dal processo rimborsi~~ 🔴 **il perimetro finale è in §9.3 e non è più questo**: i due `POST` **cadono** (il chiamante non passa di qui, e il gesto sul riporto è `POST /pagamenti/sistemazioni/{id}/annulla/`, che esiste già), e resta **un solo** comando — `DELETE /api/v1/vendite/fondi-fattura/{id}/` su **D-21**, per l'**altra** popolazione (il fondo `AUTOMATICA` non più capiente) | repo + service + view | 🔴 **da RI-PERIMETRARE, non «fermo»** (2026-08-29). I tre oggetti continuano a non esistere — verificato — ma la ragione è cambiata: il chiamante è arrivato e **non passa da qui**. ⛔ E c'è di più: `api.md` §Comunicazione cross-modulo **vieta** le chiamate laterali fra moduli di pari livello, quindi un service di `pagamenti` **non potrebbe** chiamare un endpoint di `vendite` nemmeno volendo — è lo stesso scoglio già pagato su **Q-8** dal cantiere posting. **§9** |
| **BE-5** | **Rigenerare le policy errore** dopo il seed di D-14: `./manage-env.sh genera_error_policies` | comando | ✅ **fatto** (= R-1) |
| **FE** | La lista dentro il dominio vendite | `frontend/src/vendite/` | ✅ **FATTO il 2026-08-22**, da un altro cantiere: `FondiFatturaDaDecidereTab.vue` (montato in `ToolFatturazioneView`), store `userScoped` senza pavimento temporale, `ListaConfigurabile` + `useListaConfigurabilePage` + `PageActionsBar`, export coi filtri della lista, motivi via `labelOrCode`. ⚠️ **Nessuna colonna `azioni`**: le due azioni di riga aspettano ancora il cancello — §9 |

#### 📮 Le tre richieste al BE dalla Fase A — ✅ **tutte e tre eseguite** (2026-08-15)

| | Richiesta | Perché |
| --- | --- | --- |
| **R-1** | ✅ **FATTO dal BE il 2026-08-15** (verificato: i cinque codici sono in `error_policies_generated.py` con la loro classe, e in `error_messages_fallback.py`). ~~URGENTE — Rigenerare `error_policies_generated.py`~~ (`./manage-env.sh genera_error_policies`): i codici nuovi a catalogo dal 2026-08-15 sono **cinque**, non due — `E_FONDO_NON_CORRISPONDE_SORGENTE`, `E_FONDO_SOGLIE_INCOMPLETE` (Fase A), `E_FONDO_ATTO_IMMUTABILE`, `E_FONDO_STATO_NON_AMMESSO`, `E_FONDO_MOTIVO_OBBLIGATORIO` (Fase B). Tutti già presenti in `config.codici_errore` sul DB | Senza, il cancello `test_error_codes_db_policy_guardrail` diventa rosso: **ogni codice che il DB può nominare deve avere la sua classe** |
| **R-2** | ✅ **FATTO dal BE il 2026-08-15** (`emittenti_fiscali_service.py`, con i test). ~~Mappare il vincolo `chk_emittenti_fiscali_utilities_soglie_coppia`~~ su `E_FONDO_SOGLIE_INCOMPLETE` via `map_integrity_error`, con il **campo** dichiarato nella voce. 🔵 Con la Fase B se ne aggiungono due, **non urgenti** perché raggiungibili solo dalla strada manuale che il BE non ha ancora: `chk_fondi_source_motivo_obbligatorio` (`23514`) → `E_FONDO_MOTIVO_OBBLIGATORIO` e `uq_fondi_source_atto_vivo_automatico` (`23505`) | Altrimenti chi configura le soglie a metà legge un messaggio di database invece di *quale* soglia manca. Il canale `error.fields` esiste già |
| **R-3** | ✅ **Madre DB per lotto — parte DB APPLICATA il 2026-08-15** (`20260815-33`…`-35`): `fn_get_scope_fatture_lotto`, `fn_genera_fondi_fattura_lotto(lotto, **codice interno**)`, `fn_applica_fondi_lotto(lotto, **codice interno**)`. ✅ **Consumo lato BE FATTO** lo stesso giorno: il repository fa **una `SELECT` per task** e ha perso `get_tipo_fondo_fattura_id`, `_SCOPE_FATTURE_LOTTO_SQL` e `list_fatture_scope_by_lotto` (94 righe). Contratto: **§8.3-bis**; esito BE: **§8.3-ter** | ~~Oggi le due task fanno **N `cursor.execute` in autocommit**: se il quinto fallisce, i primi quattro restano committati.~~ 🔴 **La motivazione era sbagliata** (il parziale non era possibile sul giro di pipeline). Le due ragioni vere sono altre, e sono emerse scrivendo: la **utility passata non è quella filtrata**, e il giro gira **una volta per fattura invece che per chiave** |

**Stato**: ✅ **R-1**, ✅ **R-2** e ✅ **R-3** — quest'ultima chiusa su
entrambi i lati il 2026-08-15 (DB in §8.3-bis, BE in §8.3-ter).

⭐ **R-3 non dipendeva dalla Fase D** — la ragione per cui si è potuta chiudere
subito, mentre BE-4 resta fermo (verificato il 2026-08-15): i due insiemi di oggetti sono
disgiunti — R-3 incapsula `fn_genera_fondi_fattura_source` e
`fn_applica_fondi_fattura`, che esistono già, mentre la Fase D crea le funzioni
dell'atto manuale, che non esistono; i nomi delle madri proposte sono liberi; e
`E_PIPELINE_SCOPE_INCOMPLETE` è **già a catalogo**, quindi la validazione dello
scope può spostarsi dentro la funzione DB senza seed aggiuntivi. Si può fare in
qualunque momento.

---

### 8.3-bis R-3 — la parte DB, **applicata** il 2026-08-15

> ✅ **Applicata** (`migrate` dei tre changeSet `20260815-33` … `-35`, ore 23:01),
> **puramente additiva**: le funzioni per-scope non sono state toccate, come
> chiede la specifica. Doc `dbzero` rigenerata e tre `manual/` nuovi.
>
> ✅ **Test verdi e `pgtap-baseline.sh vendite` senza regressioni** — corsa fatta
> da Tid, non da me: qui è riportato l'esito che mi ha dato. La mia unica misura
> diretta è la prova in transazione annullata **prima** dell'apply
> (`test-fondi-fattura-lotto.sql` **14/14**).

| File | Oggetto |
| --- | --- |
| `20_code/vendite/20260815-33-create-fn-get-scope-fatture-lotto` | `fn_get_scope_fatture_lotto(lotto)` — la **definizione unica** dello scope, guard compresi |
| `20_code/vendite/20260815-34-create-fn-genera-fondi-fattura-lotto` | `fn_genera_fondi_fattura_lotto(lotto, **codice interno**)` → `(fatture_count, chiavi_count, fondi_creati)` |
| `20_code/vendite/20260815-35-create-fn-applica-fondi-lotto` | `fn_applica_fondi_lotto(lotto, **codice interno**)` → `(fatture_count, fondi_applicati)` |
| `db/pgtap/vendite/test-fondi-fattura-lotto.sql` | 14 asserzioni |

#### ⚠️ Tre scostamenti dalla specifica, e perché

La specifica di §8.3 è stata seguita su tutto il resto — firma col **codice
interno** (il punto centrale: con l'id il backend farebbe comunque una query di
lookup), nessun `DEFAULT`, lookup + validazione **prima** di scrivere, funzioni
per-scope intatte. Tre cose sono diverse:

**1. Il ritorno è una tabella, non un `integer`.** La specifica chiedeva la sola
somma. Le madri tornano anche `fatture_count` e — la generazione — `chiavi_count`,
che è **la prova osservabile** del guadagno vero di R-3 (vedi sotto): senza quel
numero, «una volta per chiave» non è verificabile da un test. Per il chiamante
non cambia niente — `SELECT * FROM …` resta una query sola — e i contatori
servono al log della task run.

**2. Lo scope legge `f.utility_id`, non `COALESCE(fl.utility_id, ba.utility_id)`.**
🔴 La specifica chiede di conservare il `COALESCE` **e** di validare
`utility_id IS NULL` → le due cose non stanno insieme: `ba.utility_id` è `NOT
NULL`, quindi dopo il `COALESCE` quel campo non è mai nullo e **la validazione
non può scattare**. È esattamente ciò che succede oggi in Python
(`list_fatture_scope_by_lotto` controlla il valore già coalescizzato). Data la
validazione, `COALESCE(f.utility_id, …)` ≡ `f.utility_id`: toglierlo non cambia
il comportamento, lo rende **onesto** — e allinea il valore passato alla colonna
che le funzioni filtrano davvero.

**3. Il pgTAP è un file nuovo** (`test-fondi-fattura-lotto.sql`) e non una
sezione di `test-fondi-fattura.sql`: le fixture del lotto sono cinque tabelle in
più e il file esistente ne ha già venti asserzioni. Stessa scelta fatta per
`test-fondi-fattura-governo.sql`. Coperti tutti e sei i casi chiesti dalla
specifica, più tre che ne discendono.

#### 🔴 La motivazione di R-3 non era l'atomicità: sono altre due, e sono peggiori

L'atomicità era già chiusa dal BE con lo statement set-based. Scrivendo la madre
sono emerse **due ragioni vere**, entrambe invisibili da fuori.

**1. La utility passata non è la utility filtrata.** Lo scope Python la ricava da
`COALESCE(fl.utility_id, ba.utility_id)` — dal **lotto** o dal **billing
account** — mentre `fn_genera_fondi_fattura_source` filtra su `f.utility_id`, la
colonna **della fattura**. Se divergono, la funzione non trova niente e **non fa
niente**: nessun errore, nessun log, nessun fondo.

> ✅ Misurato su dev il 2026-08-15: 12 fatture in lotto, **zero** divergenze e
> zero utility mancanti. La correzione è per «può succedere» —
> `vendite.fatture.utility_id` è nullable, ed è esattamente il motivo per cui il
> Python faceva `COALESCE`.

**2. Il giro gira una volta per FATTURA invece che per CHIAVE.** La query Python
fa `SELECT DISTINCT f.id, …`: con l'id in proiezione il `DISTINCT` non deduplica
niente. Ma la generazione **non riceve una fattura, riceve una chiave**, e ogni
chiamata riesamina tutte le sorgenti di quella chiave. Su un lotto di 500 fatture
dello stesso emittente sono **500 scansioni identiche**, di cui 499 non creano
nulla perché l'atto unico le blocca.

⭐ Non è un'ottimizzazione: è la conseguenza di aver messo la chiave nel posto
giusto. *Chi itera sulle fatture per passare una chiave sta iterando
sull'oggetto sbagliato.* Il pgTAP lo asserisce con tre fatture e **due** chiavi.

#### ⚠️ Un cambio di comportamento da conoscere

Una fattura di lotto **senza `utility_id`** adesso **ferma il giro**
(`E_PIPELINE_SCOPE_INCOMPLETE`), mentre prima il `COALESCE` la riempiva e il giro
proseguiva senza fare niente. È la scelta fail-closed, e per il fondo è quella
giusta: *una fattura emessa senza il fondo che le spettava non se ne accorge
nessuno, un task rosso sì.*

#### 📮 Cosa deve fare il BE (perimetro `backend/`)

```python
# run_genera_fondi_source_lotto_task  →  lotto_id, tipo_fondo_codice_interno
SELECT * FROM vendite.fn_genera_fondi_fattura_lotto(%s, %s)

# run_applica_fondi_lotto_task
SELECT * FROM vendite.fn_applica_fondi_lotto(%s, %s)
```

* **si cancellano** `get_tipo_fondo_fattura_id`, `_SCOPE_FATTURE_LOTTO_SQL`
  (venti righe di SQL di dominio in un repository) e la validazione Python
  `list_fatture_scope_by_lotto` — stesso codice errore, stesso momento, ma una
  regola sola;
* ⚠️ **la validazione Python non è equivalente a quella nuova**: controlla la
  utility **già coalescizzata**, che non può essere nulla. Cancellandola non si
  perde un controllo, se ne guadagna uno che scatta davvero;
* ⚠️ **il registry non cambia**: `pipeline_task_registry_impl` continua a puntare
  a `genera_fondi_source_lotto_default` / `applica_fondi_lotto_default`;
* 🔵 i contatori di ritorno (`fatture_count`, `chiavi_count`, `fondi_creati` /
  `fondi_applicati`) sono utili nel log della task run: oggi il BE ignora il
  valore di ritorno;
* ⚠️ va adeguato `apps/vendite/tests/services/test_pipeline_step_executor.py`,
  che nomina le funzioni con la firma vecchia.

#### ⚠️ Nota di numerazione, e vale per il prossimo giro

I tre changeSet erano nati `-24`/`-25`/`-26` e sono stati **rinumerati a
`-33`/`-34`/`-35`**: il merge del branch backend ha portato nel repository i
changeSet `-24` … `-32` di un altro cantiere, **già applicati** su questo
database. La numerazione `NN` è **globale per data fra tutte le cartelle**, e va
riverificata **dopo ogni merge**, non solo all'inizio del lavoro.

#### 📮 R-3 — la specifica per il team DB *(scritta il 2026-08-15, sera)*

> 🔴 **Correzione a quanto scritto sopra e in §8.4**: R-3 **non** cambia la firma
> delle funzioni esistenti, quindi **non** vale il vincolo «DB e repository nello
> stesso lotto». Le due madri sono oggetti **nuovi** che incapsulano
> `fn_genera_fondi_fattura_source` e `fn_applica_fondi_fattura` **lasciandole
> intatte**: il passo DB è **puramente additivo** e può essere applicato da solo,
> senza toccare `backend/` e senza rompere niente. Il BE ci passa sopra in un
> secondo momento. (Il vincolo del lotto unico veniva da D-4/BE-1, dove a
> cambiare erano le firme *esistenti* — cosa che §8.2-bis ha poi deciso di non
> fare.)

**Le due firme.** ⚠️ Prendono il **codice interno**, non l'id del tipo fondo, e
la differenza è il punto di R-3: il parametro che arriva dalla configurazione
del task è `tipo_fondo_codice_interno` (una stringa), quindi con l'id il
backend dovrebbe comunque fare **prima** una query di lookup — e «una `SELECT`
per task» non si otterrebbe.

```sql
vendite.fn_genera_fondi_fattura_lotto(
    p_lotto_id                 bigint,
    p_tipo_fondo_codice_interno varchar
) RETURNS integer

vendite.fn_applica_fondi_lotto(
    p_lotto_id                 bigint,
    p_tipo_fondo_codice_interno varchar
) RETURNS integer
```

⚠️ **Senza `DEFAULT`**: il default `'F_F_ADD_ACC'` lo risolve già il chiamante
(`params.get(...) or 'F_F_ADD_ACC'`), e un `DEFAULT` qui aprirebbe la strada
all'ambiguità di overload che il progetto ha già pagato altrove.

**Cosa si sposta dentro** — sono i tre pezzi che oggi vivono nel repository:

| | Oggi | Dopo |
| --- | --- | --- |
| lookup del tipo fondo | `get_tipo_fondo_fattura_id` (query a sé) → `E_TIPO_FONDO_NOT_FOUND` | dentro la madre |
| definizione dello scope | sottoquery del repository (`_SCOPE_FATTURE_LOTTO_SQL`) | dentro la madre |
| validazione dello scope | check Python sui campi NULL → `E_PIPELINE_SCOPE_INCOMPLETE` | dentro la madre |

**Corpo, nell'ordine** (lo scope è lo stesso dei due giri, quindi va scritto
**una volta** in una CTE e riusato, non copiato):

1. guard dei parametri — `p_lotto_id` NULL o `<= 0`, `p_tipo_fondo_codice_interno`
   NULL o vuoto → `E_PARAMETRO_INVALIDO` (convenzione di AGENTS.md);
2. risoluzione del tipo fondo (`attivo IS TRUE`, `ORDER BY id LIMIT 1`) →
   `E_TIPO_FONDO_NOT_FOUND` se assente;
3. 🔴 **validazione dello scope prima di toccare i dati**: se una fattura del
   lotto ha `utility_id` / `tipo_doc_fiscale_id` / `emittente_soggetto_ruolo_id`
   / `valuta_id` a NULL → `E_PIPELINE_SCOPE_INCOMPLETE`, nominando la **fattura**
   colpevole nel contesto. È fail-fast: oggi lo è, e deve restarlo;
4. applicazione **set-based** — `SELECT COALESCE(SUM(vendite.fn_...(s.…)), 0)`
   sulla CTE di scope. Un solo statement.

⚠️ Lo scope è `SELECT DISTINCT` su `fatturazione_lotti_fatture` con
`COALESCE(fl.utility_id, ba.utility_id)`: il `COALESCE` non è un dettaglio, la
utility del lotto vince su quella del billing account.

**Ritorno**: `integer`, la somma di quanto tornano le funzioni interne (0 su
lotto senza fatture). È il numero che il BE non usa oggi, ma che serve ai pgTAP
per distinguere «ha lavorato» da «non ha trovato niente» — la lacuna che §8.2-quinquies
ha già pagato una volta sul guard di capienza.

✅ **Nessun seed necessario**: `E_PARAMETRO_INVALIDO`, `E_PIPELINE_SCOPE_INCOMPLETE`
e `E_TIPO_FONDO_NOT_FOUND` sono **tutti e tre già a catalogo** (verificato).

**pgTAP** — in `db/pgtap/vendite/test-fondi-fattura.sql` (è lì che vive il giro):

| | Cosa verifica |
| --- | --- |
| 1 | lotto con più fatture: **una sola chiamata** genera i fondi di tutte, e il ritorno è il conteggio |
| 2 | lotto **vuoto** → ritorno `0`, nessun errore |
| 3 | fattura con `utility_id` NULL nel lotto → `E_PIPELINE_SCOPE_INCOMPLETE` (`P0001`) e ⚠️ **nessun fondo creato per le altre**: la validazione precede la scrittura |
| 4 | `codice_interno` inesistente → `E_TIPO_FONDO_NOT_FOUND` |
| 5 | `p_lotto_id` NULL / `<= 0` → `E_PARAMETRO_INVALIDO` |
| 6 | idem per `fn_applica_fondi_lotto`, più il caso «sorgente non più capiente» che il giro deve continuare a scartare |

**Il cambio BE che segue** (mio, dopo l'apply — non serve lo stesso lotto):
i due metodi di `pipeline_repository.py` tornano a **una `SELECT` sola** e
spariscono `get_tipo_fondo_fattura_id`, `_SCOPE_FATTURE_LOTTO_SQL` e
`list_fatture_scope_by_lotto` se nessun altro li usa. 🔴 **Il binding va provato
con una chiamata reale**: `test_pipeline_step_executor.py` mocka il repository e
resterebbe verde anche con la firma sbagliata — è la trappola già registrata
(`feedback_rinomina_db_binding_mockato`).

⛔ **Cosa NON fare**: droppare o modificare `fn_genera_fondi_fattura_source` e
`fn_applica_fondi_fattura`. Restano le funzioni per-scope, le chiamano i pgTAP
esistenti e sono il mattone su cui le madri si appoggiano.

> 🔴 **La motivazione di R-3 era sbagliata, e va corretta prima che qualcuno la
> usi per stabilire una priorità** (misurato il 2026-08-15, sera). «N chiamate
> in autocommit, se la quinta fallisce le prime quattro restano committate»
> **non poteva accadere sul giro di pipeline**: `run_pipeline` avvolge già ogni
> step in `transaction.atomic()` (Fase 2 del runner). L'esposizione autocommit
> valeva **solo** per la facciata single-step `fn_execute_pipeline_step` e per
> le chiamate dirette.
>
> ⚠️ È la trappola di §8.5 applicata a sé stessi: *la misura era stata presa dal
> **corpo** della funzione invece che dal **percorso** che la attraversa.*
>
> **Cosa compra davvero R-3**, quindi: portare **dentro il database** anche la
> definizione dello scope e la sua validazione — oggi lo scope è una sottoquery
> del repository e `E_PIPELINE_SCOPE_INCOMPLETE` un check Python — cioè un'unica
> sede per l'inviluppo del giro. Non un incidente da riparare.
>
> ⚠️ Da adeguare nello stesso lotto:
> `apps/vendite/tests/services/test_pipeline_step_executor.py`, che nomina le
> funzioni con la firma attuale.

📮 **Due voci di `map_integrity_error` restano in attesa della Fase D**, perché
oggi nessun percorso applicativo scrive `fatture_fondi_fattura_source` e una
mappa senza service dove vivere non si scrive:

| Vincolo | SQLSTATE | Codice | Campo |
| --- | --- | --- | --- |
| `chk_fondi_source_motivo_obbligatorio` | `23514` | `E_FONDO_MOTIVO_OBBLIGATORIO` | `motivo` |
| `uq_fondi_source_atto_vivo_automatico` | `23505` | da decidere col comando | — |

#### 🔴 Il pezzo che il piano non aveva previsto: il seed del catalogo liste

La riga di §8.3 sul frontend dice che l'elenco è *«una lista sola dentro il
dominio vendite (`useListaConfigurabilePage` + `ListaConfigurabile`)»* e che
*«non c'è niente da inventare»*. È vero per il codice Vue, **non per ciò che lo
alimenta**: `<ListaConfigurabile>` non è una tabella, è un componente che si
**costruisce dal catalogo** — chiede al backend la configurazione delle colonne
e la disegna da lì. Senza il seed la pagina non parte in modo degradato:
risponde **`E_UI_LISTA_NON_TROVATA`**.

Serviva un append ai CSV di `80_data/sql/ui/` (perimetro DB) — ✅ **fatto**, il dettaglio di com'è stato seminato è nel riquadro in fondo a questa sezione:

| File | Cosa |
| --- | --- |
| `lista_definizione.csv` | una riga `vendite.fondi_fattura_da_decidere`, area `vendite` |
| `lista_colonna.csv` | le colonne sotto |
| `lista_preset.csv` + `lista_preset_colonna.csv` | preset `sistema`, ordinamento `data` DESC, 25 righe |

**Le colonne che il BE spedisce già** — l'endpoint è vivo, quindi il catalogo si
scrive sul dato vero e non su una previsione:

| Codice colonna | Formato | Note |
| --- | --- | --- |
| `motivo` | — | identificatore visivo (Tag); etichette FE via `labelOrCode` |
| `data` | `date_short` | ordinamento default, DESC |
| `anno`, `serie`, `numero` | — | il documento sorgente |
| `totale_a_pagare` | `currency_eur` | il totale della fattura |
| `capienza_attuale` | `currency_eur` | il residuo della sorgente, su **tutte** le righe |
| `importo_proposto` | `currency_eur` | ⚠️ solo su `PROPOSTA_SENZA_ATTO` |
| `importo_atto`, `stato_atto`, `origine`, `atto_motivo`, `atto_data` | vari | ⚠️ solo su `NON_PIU_CAPIENTE` |

⭐ **Le colonne mezze vuote non sono un difetto del dato**, e conviene saperlo
prima di configurarle: le cinque dell'atto esistono solo sul ramo in cui l'atto
c'è, e negli altri tre l'atto **non esiste ancora** — che è esattamente il
motivo per cui la riga è in elenco. Suggerimento: `visibile_default = false`
sulle cinque, così la lista nasce leggibile e chi indaga le accende.

##### ✅ Seed fatto il 2026-08-15 — 16 colonne, e due scelte da conoscere

Append ai quattro CSV di `80_data/sql/ui/` (nessun loader nuovo: quelli
esistenti sono `runOnChange` e ripescano il file). Lista `id 44`, preset
`fondi_fattura_da_decidere_default`, `pagina_dimensione` **50** e ordinamento
`data` DESC — cioè **i default veri dell'endpoint**, non valori scelti a occhio.

🔴 **`filtrabile` e `ordinabile` rispecchiano le whitelist dell'API, non il
desiderabile.** L'endpoint filtra solo su `motivo` e ordina solo su `data`,
`motivo`, `anno`, `numero`, `totale_a_pagare`, `importo_proposto`,
`capienza_attuale`; tutto il resto è `f`. *Una colonna dichiarata ordinabile che
l'API rifiuta con un 400 è un controllo che esiste per rompersi* — e il catalogo
è l'unico posto dove quel disallineamento non si vedrebbe finché non lo clicca
qualcuno.

⭐ **Quattro colonne dell'atto nascoste su cinque, non cinque.** `importo_atto`
resta **visibile**: senza, una riga `NON_PIU_CAPIENTE` mostrerebbe la capienza e
non l'importo che non ci sta più dentro — cioè tutto tranne il confronto che la
mette in elenco. Le altre quattro sono spente, come suggerito.

⚠️ **E `stato_atto` è spenta per una ragione diversa dalle altre**: sul ramo
`NON_PIU_CAPIENTE` la vista filtra `s.stato = 'DISPONIBILE'`, quindi quella
colonna vale **sempre lo stesso** su ogni riga dell'elenco. Non è mezza vuota:
è costante. *Una colonna che ha sempre lo stesso valore non informa* — resta a
catalogo (accendibile) perché il giorno in cui la vista mostrasse anche altri
stati diventerebbe utile senza un seed nuovo.

🔵 **Nessuna colonna `azioni`**: le due azioni dell'atto manuale (BE-4) non
esistono ancora, e una colonna che apre un menu vuoto è la stessa cosa di una
riga di elenco che non può accadere. Si aggiunge con la Fase D.

📮 **Al frontend**: le 16 chiavi i18n sono `vendite.fondi_fattura_da_decidere.col_*`.
Finché non ci sono, `labelOrCode` mostra l'etichetta del catalogo — che è già in
italiano, quindi la lista è leggibile da subito e le traduzioni non bloccano.

#### BE-1 + BE-2 — Il giro fondi e la chiave

> ✅ **FATTO il 2026-08-15, ma non come è scritto qui sotto** — e la differenza
> vale più della conclusione. Il testo originale è tenuto perché il ragionamento
> su D-4 resta valido; ciò che è caduto è la **misura** che lo apriva.

~~`run_genera_fondi_source_lotto_task` e `run_applica_fondi_lotto_task` fanno **N
`cursor.execute` in autocommit**, uno per ogni scope di fattura del lotto. Se il
quinto fallisce, i primi quattro restano committati: il lotto resta a metà, con
dei fondi generati e altri no. È la regola «una azione = una unità atomica»
(api.md §Atomicità), violata dal 2026-02.~~

> 🔴 **Sul giro di pipeline il parziale non era possibile**: `run_pipeline`
> avvolge già ogni step in `transaction.atomic()`. Il varco era solo la facciata
> single-step e le chiamate dirette. *La misura era stata presa dal corpo della
> funzione invece che dal percorso che la attraversa* — la trappola di §8.5,
> pagata su sé stessi.
>
> ✅ **Come è stato chiuso**: ogni giro è ora **un unico statement set-based**
> — `SELECT vendite.fn_...(s.*) FROM (<scope del lotto>) s` — atomico per
> costruzione, **un** round-trip invece di N, senza `transaction.atomic()`.
> Chiude anche il varco della facciata. Lo scope resta definito una volta sola
> (`_SCOPE_FATTURE_LOTTO_SQL`), condiviso fra la validazione Python e i due
> giri: due copie divergerebbero in silenzio.

⭐ **Con D-4 il difetto non si corregge: sparisce.** Il giro per scope esiste solo
perché la funzione riceve la pseudo-chiave a cinque parametri e va chiamata una
volta per combinazione. Se la chiave la legge il database dalle righe di
`vendite.fatture`, la firma diventa:

```text
vendite.fn_genera_fondi_fattura_lotto(p_lotto_id, p_tipo_fondo_id)
vendite.fn_applica_fondi_lotto(p_lotto_id, p_tipo_fondo_id)
```

e il repository torna a **una `SELECT` sola** per task — atomica per costruzione,
senza `transaction.atomic()` da ricordarsi, e senza il round-trip per scope.

⚠️ Il registry **non cambia**: `pipeline_task_registry_impl` continua a puntare a
`genera_fondi_source_lotto_default` / `applica_fondi_lotto_default`. Cambia il
corpo del metodo, non il cablaggio. ⚠️ E va adeguato
`apps/vendite/tests/services/test_pipeline_step_executor.py`, che oggi nomina le
funzioni con la firma vecchia.

~~ℹ️ Il ripiego, se la Fase A dovesse uscire prima di D-4: `with transaction.atomic()`
attorno al loop. Chiude l'atomicità e lascia in piedi il round-trip.~~ — superato:
lo statement set-based non lascia in piedi nemmeno il round-trip.

#### BE-3 — L'elenco

```text
GET /api/v1/vendite/fondi-fattura/da-decidere/?motivo=&page=&page_size=&order_by=&order_dir=
```

* **view**: `DomainAPIView`, `area_funzionale = "vendite"`, `is_search_endpoint = True`,
  `@extend_schema` con `inline_serializer`;
* **service**: `validate_pagination` + `validate_enum_param` sul filtro `motivo`
  (whitelist ordinata = i quattro motivi di D-10);
* **repository**: `fetch_paged_with_total` (o `query_paged_view` se si vuole la
  pagina **effettiva** nell'envelope), `sql_order_direction` +
  `sql_tiebreak_direction` per l'`ORDER BY`, tiebreak su `id`;
* **scope**: la RLS filtra da sé grazie a `security_invoker` (D-10); il filtro
  applicativo `get_emittenti_sr_ids` resta come **defense-in-depth**, com'è la
  convenzione del progetto.

⭐ **Nessun building block nuovo**: sono tutti già a catalogo. E ⚠️ **nessuna
capability per riga** — le liste non chiamano `fn_available_actions_*` riga per
riga; il gate lo fa il FE sui codici che la vista porta già in riga
(`motivo_codice`, `azione_suggerita`).

#### BE-4 — I due comandi

```text
POST /api/v1/vendite/fondi-fattura/                 → crea atto manuale
POST /api/v1/vendite/fondi-fattura/<id>/annulla/    → annulla con motivo
```

* `handle_post_json` con `require_idempotency_key=True` (modificano stato);
* `post_permission = "governa_fondo_fattura"` (D-13);
* **una sola `SELECT fn_...()`** per comando → atomico per costruzione, **niente**
  `transaction.atomic()`;
* traduzione errori con `translate_db_errors` / `raise_from_database_error`: dal
  2026-08-05 il codice viaggia in `diag.constraint_name` su `P0001`, quindi basta
  che le funzioni DB usino `script.fn_log_and_raise_error` — che è già la regola.

⚠️ **Dove vive il codice, e perché non un file nuovo.** Tre endpoint (una lista e
due comandi) **non** fanno un sottodominio: stanno in `vendite_service.py` e
`vendite_repository.py`. La convenzione di AGENTS.md è esplicita — un file
`<sottodominio>_*` si crea solo quando c'è logica orchestrata autonoma (runner,
executor, saga), non per tre metodi.

#### E il frontend — fuori dalla richiesta, ma il contratto lo prevede

Una riga per non lasciare il contratto monco: l'elenco è una lista sola dentro il
dominio vendite (`useListaConfigurabilePage` + `ListaConfigurabile`), con due
azioni di riga gated su `governa_fondo_fattura` e i motivi decodificati via
`labelOrCode`. Non c'è niente da inventare, e **non fa parte di questo piano**.

---

### 8.3-ter R-3 — la parte BE, **applicata** il 2026-08-15

> ✅ Il repository consuma le madri: **una `SELECT` per task**, e il giro fondi
> non ha più nulla di dominio in Python. Suite **3676 verdi** (env CI).

| Cosa | Prima | Dopo |
| --- | --- | --- |
| chiamate per task | 1 lookup tipo + 1 lettura scope + 1 statement | **1** `SELECT * FROM vendite.fn_…_lotto(%s, %s)` |
| pseudo-chiave a 5 parametri | nel repository | sparita |
| SQL dello scope | 20 righe nel repository | sparito (`fn_get_scope_fatture_lotto`) |
| ritorno dei metodi | `None` | `dict` coi contatori del giro, loggati |

**Cancellati** perché diventati morti (94 righe): `get_tipo_fondo_fattura_id`,
`_SCOPE_FATTURE_LOTTO_SQL`, `list_fatture_scope_by_lotto` — nessun altro
chiamante, verificato.

#### 🔴 Un effetto collaterale di R-3, trovato e chiuso: i tre codici sarebbero diventati `E_TASK`

Non era nella specifica, e sarebbe passato inosservato perché **non rompe
niente**: degrada in silenzio il diario.

`E_TIPO_FONDO_NOT_FOUND`, `E_PIPELINE_SCOPE_INCOMPLETE` e il nuovo
`E_LOTTO_NON_TROVATO` **nascevano in Python** come `ServiceError`, quindi
`_fail_task_run_safely` ne registrava il codice esatto sulla `task_run`. Con R-3
nascono nel **database**: arrivano come `DatabaseError`, e quel metodo leggeva il
codice *solo* da `ServiceError` — ripiegando su `E_TASK` per tutto il resto.
Cioè: R-3 avrebbe spostato la logica nel posto giusto e, per strada, reso
**non attribuibili** i suoi stessi errori.

Chiuso leggendo il codice strutturato con `db_error_code` (la lettura unica di
`apps/core/services/db_error_fields`, mai `diag.constraint_name` a mano).
⭐ **Vale per ogni task che delega a una funzione DB**, non solo per i fondi: era
un buco del telaio, che R-3 ha solo reso visibile.

#### Verifiche, e cosa hanno mostrato

⚠️ Il binding è stato provato con **chiamate reali**, non coi mock:
`test_pipeline_step_executor` mocka il repository e sarebbe rimasto verde anche
con la firma sbagliata (`feedback_rinomina_db_binding_mockato`).

| Prova | Esito |
| --- | --- |
| lotto **inesistente** | `E_LOTTO_NON_TROVATO` — prima era **silenzio** (scope vuoto → no-op) |
| lotto **esistente e vuoto** | `(0, 0, 0)` e `(0, 0)`, nessun errore: i due casi ora si distinguono |
| codice estratto dall'eccezione | `E_LOTTO_NON_TROVATO`, non `E_TASK` |
| suite completa (env CI) | **3676 verdi** |

⚠️ **Allineata anche `ALLOWED_TASK_FUNCTIONS`**, che continuava a nominare le
funzioni per-scope: oggi è inerte (la configurazione dei due task dichiara
`fn = NULL`, verificato sul DB **e** sul seed, quindi la whitelist non viene
consultata) — ma una mappa che nomina ciò che il codice non chiama più insegna
una cosa falsa al primo che la legge.

ℹ️ Aggiunto un `logger` di modulo a `pipeline_repository.py`, che ne era privo e
importava `logging` **dentro** due metodi: le due occorrenze ci passano sopra.

---

### 8.4 Ordine, dipendenze e il vincolo esterno

```text
Fase A  ─── indipendente, si applica subito ──────────────┐
   │                                                       │
   ├─→ Fase B (registro)  ─→  Fase C (proposta + elenco)  ─→  Fase D (atto manuale)
   │
Fase E  ─── in qualunque momento, conviene con A
Fase F  ─── dichiarativa: si scrive nel brief incassi
```

> ✅ **Stato al 2026-08-16**: A, B, C, E, F applicate; ~~**resta la sola Fase D**,
> ferma per scelta finché `pagamenti` non ha un processo rimborsi.~~
> 🔴 **Rimisurato il 2026-08-29**: la Fase D **non è più ferma per scelta** — il
> processo rimborsi c'è dal 22/08 e ha scritto il fondo per conto suo. Il grafo
> qui sotto vale fino alla Fase C; da lì in poi la mappa è **§9**.
> ⭐ **Aggiornato al 2026-08-22**: quel processo è la **slice 4 / lotto 7** del
> cantiere posting — progettata, non ancora scritta, e **avviabile subito**
> (lotti 6 e 7 indipendenti). Dettaglio in testata.
> Fuori dal grafo perché non sono fasi: **R-1/R-2/R-3 fatte**, **seed
> `ui.lista_*` fatto**, **BE-2/BE-3/BE-5 fatti**; aperti **BE-4** (aspetta la
> Fase D) e la **pagina Vue** (non più bloccata).

| Dipendenza | Perché |
| --- | --- |
| **D-0 per primo** | finché una configurazione a metà spalanca il meccanismo, tutto il resto presidia un cancello con il muro aperto accanto |
| D-1 **con** D-3 | D-1 da solo lascia scoperto un fondo non più dovuto, che verrebbe applicato lo stesso (§8.2 Fase A) |
| ~~D-4 **prima o insieme** a BE-1~~ | ~~la firma delle funzioni cambia: DB e repository nello stesso lotto, o la pipeline si rompe~~ — ⏸️ **decaduto**: §8.2-bis ha scelto di **non** cambiare le firme, e R-3 (che ne eredita l'intento) è additivo — le madri incapsulano, non sostituiscono. Nessun vincolo di lotto unico: vedi la specifica R-3 in §8.3 |
| Fase B **dopo** Fase A | il CHECK sul vocabolario di `stato` viene prima del guard che lo presidia |
| Fase C **dopo** Fase B | l'elenco distingue gli **atti** dalle **proposte**: senza `origine` non sa dirlo |
| ~~Fase D **dopo** Fase C~~ | ~~e comunque **dopo** che `pagamenti` ha un processo rimborsi da cui chiamarla: costruire la porta prima della stanza è lecito, aprirla al pubblico no. ⭐ **2026-08-22**: la stanza è il **lotto 7** del cantiere posting, e il gancio preciso è il passo **S4-4** (i tre verbi)~~ — 🔴 **decaduto il 2026-08-22**: la stanza è stata costruita **con la sua porta dentro**. La dipendenza non è stata soddisfatta, è stata **resa inutile**, ed è un esito diverso: §9 |

🔴 **Il vincolo esterno, ed è l'unico che ha una scadenza.** La Fase A deve essere
applicata **prima del primo scrittore di righe contabili** — la slice 1 del
cantiere incassi, l'import del flusso bancario (D6), o una correzione manuale,
quello che arriva prima (§8.0-a). Se è la slice 1, la Fase A è dentro di lei e
**non si fa due volte**.

---

### 8.5 Le verifiche

**pgTAP** — file nuovo `db/pgtap/vendite/test-fondi-fattura-governo.sql`, più
l'adeguamento dei due esistenti.

| | Cosa verifica |
| --- | --- |
| 1 | ⛔ una sola soglia valorizzata **non si salva** (D-0) |
| 2 | soglie assenti ⇒ **nessun fondo generato** (meccanismo spento) |
| 3 | ⭐ **una fattura fra `soglia_min` e 0 genera un fondo NEGATIVO** — è il capo inferiore della banda, non un difetto |
| 4 | una fattura fuori banda (sopra il massimo, sotto il minimo) **non genera niente** |
| 5 | sorgente **non `DEFINITIVA`** (DRAFT, EMESSA, **ANNULLATA**) ⇒ nessun fondo (D-1) |
| 6 | un secondo giro **non riscrive** l'importo di un fondo già creato (D-1 + D-6) |
| 7 | un fondo di segno opposto o più grande del totale della sorgente è **rifiutato** su `origine = 'AUTOMATICA'` e **ammesso** su `'MANUALE'` (D-3a, D-5) |
| 8 | `fn_applica_fondi_fattura` **non assegna** un fondo la cui sorgente non è più capiente (D-3b) |
| 9 | il fondo **non passa** a una figlia che differisce anche per **un solo** elemento dei nove (D-4) — almeno `utility`, `termine_pagamento`, `reseller` |
| 10 | i CHECK rifiutano importo zero e stato fuori vocabolario (D-2) |
| 11 | le transizioni fuori matrice sono rifiutate (D-7) |
| 12 | l'indice parziale rifiuta due atti automatici vivi sulla stessa sorgente (D-8) |
| 13 | `vw_fondi_fattura_da_decidere` **non mostra** i fondi di un altro emittente (D-10, RLS) |

⚠️ **Trappole da non ripagare**, tutte già pagate altrove nel progetto:

* **il preambolo è obbligatorio** — `BEGIN;`, riga di contesto operatore,
  `SET CONSTRAINTS ALL IMMEDIATE` **subito dopo**. Senza, il file diventa verde
  per sottrazione;
* **`throws_ok` sempre con lo SQLSTATE** (`'P0001'` per gli errori di dominio):
  senza, accetta anche il crash del guard che doveva verificare. ⚠️ E i trigger
  BEFORE ROW girano **prima** dei CHECK: il test 10 rischia di collaudare il guard
  di D-7 credendo di collaudare un CHECK — asserire il **codice**, non il fatto
  che sollevi;
* **niente `LIMIT 1` senza `ORDER BY`** nelle fixture;
* 🔴 **il fondo NON corrispondente va attraversato dal percorso reale**, non
  fabbricato. Una riga inserita a mano nella source *conferma* un ramo che nessuno
  percorre. Il percorso vero passa dal **secondo termine** della bilancia
  (§8.0-a): una riga contabile `ABBINATA` più grande del residuo porta il target
  sotto zero **senza bisogno di movimenti**, ed è creabile oggi. È così che vanno
  costruiti i test 7 e 8;
* ⚠️ **e non confondere quel caso col fondo negativo legittimo** (test 3), che
  nasce da una fattura a credito dentro la banda. Sono due fondi negativi con due
  cause opposte: uno è il meccanismo che funziona, l'altro è il difetto. Un test
  che asserisse solo «il fondo è negativo» non distingue fra i due;
* **misurare con `ON_ERROR_STOP=1`** e confrontare con
  `scripts/pgtap-baseline.sh vendite` prima di attribuire un rosso a questo
  lavoro.

**Non-pgTAP:**

* `test_transaction_atomicity_guardrail` deve restare verde dopo BE-2;
* `./manage-test.sh apps.vendite.tests -v 2` dopo BE-3/BE-4;
* il presidio dei riferimenti morti gira **dopo** `manage.py migrate`: il `DROP`
  di D-15 e il taglio del pgTAP nello stesso lotto.

---

### 8.6 Cosa il piano **non** fa, e perché

| | Perché |
| --- | --- |
| Nessun automatismo che «sistema» i fondi | è la regola pratica di §5.2: l'elenco **presenta**, non sana. Un automatismo correttivo riaprirebbe la rincorsa che §4 ha chiuso |
| Nessun `ANNULLATO` come effetto di un pagamento | se non ci si fida di un automatismo a **creare** un fondo, tanto meno a **cancellarlo** |
| 🔴 **Nessun limite `> 0` sull'importo**, né CHECK né `WHERE` | **il fondo negativo è metà del meccanismo**: il capo inferiore della banda (`−500`) esiste per riportare avanti i **crediti**. Il limite `> 0` — scritto sia qui sia nel cantiere incassi fino al 2026-08-15 — avrebbe spento quella metà. Si controlla la **corrispondenza col documento**, non il segno |
| Nessuna quadratura per **fattura** | l'intervallo `[0, totale_a_pagare]` si inverte sulle fatture a credito: è una porta chiusa travestita da controllo. Trappola già scritta nel brief incassi, e qui il caso non è di bordo — è ordinario |
| Nessun elenco delle eccedenze in `vendite` | il sovra-incasso è del **processo rimborsi**, in `pagamenti`, che se le va a cercare. Due elenchi sullo stesso fatto divergono al primo cambio |
| ~~Nessuna RLS su `fatture_fondi_fattura_source`~~ | ~~il perimetro passa dalla fattura, che ce l'ha. Una RLS in più su una tabella satellite è un secondo posto dove sbagliare — e `security_invoker` sulla vista (D-10) fa già il lavoro.~~ 🔴 **RIBALTATA il 2026-08-29 (G-2, decisione di Tid): la RLS si accende** — passo **D-20**. ⚠️ E non è cambiata solo la conclusione: era **la premessa** a essere scaduta. Quando la riga fu scritta la tabella aveva un lettore solo, protetto da un `JOIN`; oggi ha un lettore applicativo, una pagina Vue, **uno scrittore in un altro schema** e — col gesto di D-21 — un accesso **per id**, che nessun `JOIN` protegge. §9.9 |
| Nessun tocco a `pagamenti` | il posting, la quadratura, il rimborso e la compensazione sono dell'altro cantiere. Qui si dichiara il confine (Fase F) e si costruisce **una porta** (Fase D), non si attraversa. ⚠️ **Resta vero come regola di questo cantiere, ma il confine è stato attraversato dall'altra parte**: §9 |

---

## 9. 🔴 Lo sviluppo che resta — riscritto il 2026-08-29

> ⭐ **Perché questa sezione esiste.** Il piano di §8 finiva con *«resta la sola
> Fase D, e aspetta il processo rimborsi»*. Il processo rimborsi è arrivato il
> **2026-08-22** e non ha aspettato la Fase D: l'ha **scavalcata**. Ciò che resta
> da fare non è quindi «il pezzo che mancava», è **un pezzo diverso** — e va
> scritto qui, non riscrivendo §8, perché §8 è il ragionamento da cui questo
> discende e serve leggibile com'era.
>
> ⚠️ Tutto quello che segue è misurato sulla **struttura** — corpi di funzione
> dalla doc auto-generata, vincoli e trigger dal catalogo, righe dei CSV di seed,
> file di `backend/` e `frontend/src` — mai su un conteggio di righe.

---

### 9.1 Il fatto: la porta è stata costruita e sono entrati dalla finestra

`pagamenti.fn_conferma_sistemazione` (lotto 7 del cantiere posting, applicato il
**2026-08-22 alle 12:20**), ramo `RIPORTO`, scrive **direttamente** nella tabella
degli atti di questo cantiere:

```sql
INSERT INTO vendite.fatture_fondi_fattura_source (
    fattura_sorgente_id, tipo_fondo_fattura_id, importo, stato,
    fattura_figlia_id, data_assegnazione, user_assegnazione, …,
    origine, motivo, meta)
VALUES (…, 'ASSEGNATO', …, 'MANUALE', v_atto.motivo,
        jsonb_build_object('origine','SISTEMAZIONE','sistemazione_id', v_atto.id));
```

mentre `vendite.fn_crea_fondo_fattura_manuale` (**D-11**) non esiste,
`fn_annulla_fondo_fattura` (**D-12**) non esiste e `governa_fondo_fattura`
(**D-13**) non è in `config/azioni_processo.csv`.

⭐ **E la scelta di `pagamenti` è quella giusta**, va detto subito perché cambia
che cosa si costruisce adesso. Un `INSERT` dentro la madre è **atomico per
costruzione**, è DB-first, e soprattutto è l'**unica** forma possibile: `api.md`
§Comunicazione cross-modulo vieta le chiamate laterali fra moduli di pari
livello, quindi un service di `pagamenti` non potrebbe chiamare un endpoint di
`vendite` nemmeno volendo. È lo stesso scoglio che il cantiere posting ha già
pagato su **Q-8** (i saldi delle rate). ⛔ **Il difetto non è che `pagamenti`
scriva: è che il presidio che doveva accompagnare quella scrittura non è stato
costruito da nessuna delle due parti.**

---

### 9.2 Che cosa si è rotto, in ordine di gravità

#### (a) 🔴 Una strada di creazione senza la sua contropartita

`pagamenti.trgfn_sistemazioni_guard_transizione` dichiara `CONFERMATA`
**terminale**: *«da CONFERMATA non si torna perché il denaro si è già mosso, e la
correzione è una sistemazione NUOVA»*. La regola è giusta, e per due
destinazioni su tre ha davvero una contropartita:

| Destinazione | Che cosa produce | Come si rimedia a uno sbaglio |
| --- | --- | --- |
| `RIMBORSO` | una distinta contabile | ✅ la **correzione guidata** (S6, `fn_crea_distinta_correzione`) |
| `COMPENSAZIONE` | una distinta contabile | ✅ idem |
| **`RIPORTO`** | ⛔ **un fondo `ASSEGNATO`, non una distinta** | 🔴 **niente**: la correzione della distinta non lo tocca, e `fn_annulla_fondo_fattura` non esiste |

⭐ *Una sistemazione nuova non è la contropartita di un riporto sbagliato*: la
sistemazione pretende un'eccedenza, e quel riporto l'eccedenza **l'ha già
consumata**. Il verso opposto passa per forza dall'atto, cioè da **D-12**.

🔴 **Ed è un'asimmetria del modello, non una funzione che manca**: si può creare
un atto che muove denaro e non lo si può disfare. Vale la regola di casa —
un'asimmetria si chiude per intero e subito, non in una «fase 2».

#### (b) 🔴 Il «governato» di F-1 regge su due gambe su tre

F-1 e D-5 dicevano che l'atto `MANUALE` non è *vincolato* come l'automatico ma
**governato**: motivo obbligatorio, **azione di processo**, e origine dal
processo rimborsi. Verificato oggi:

| Gamba | Stato |
| --- | --- |
| **motivo obbligatorio** | ✅ regge, e per una simmetria che vale la pena conoscere: `pagamenti.sistemazioni.motivo` è obbligatorio **proprio su `RIPORTO`**, cioè sull'unico ramo che crea il fondo. `chk_fondi_source_motivo_obbligatorio` trova sempre di che soddisfarsi — non è fortuna, sono due vincoli scritti sullo stesso dominio |
| **origine dal processo rimborsi** | ✅ regge, ed è tracciata: `meta ->> 'sistemazione_id'` |
| **azione di processo** | ⛔ **non esiste**. Chi può confermare una sistemazione crea un fondo in `vendite`, e non c'è nessun cancello di `vendite` in mezzo |

#### (c) ⚠️ Un atto può **nascere** in qualunque stato

Il guard delle transizioni è montato **solo su `UPDATE`**:

```text
trg_…_a10_guard_importo_ins_upd        BEFORE INSERT · BEFORE UPDATE
trg_…_a10_guard_transizione_upd        BEFORE UPDATE          ← solo
trg_…_a10_lock_atto_upd                BEFORE UPDATE
```

Il `CHECK` `chk_fondi_source_stato` ammette tutti e quattro i valori, quindi
l'unico presidio sullo stato **di nascita** è la buona volontà di chi fa
l'`INSERT`. Oggi ne sono esercitati due — `DISPONIBILE` (giro automatico) e
`ASSEGNATO` (riporto) — ed entrambi sono legittimi; ma **`ESEGUITO` e
`ANNULLATO` alla nascita** passerebbero senza che nulla protesti: un atto che
nasce già terminale, cioè un record che non è mai stato vero.

⚠️ E la matrice di D-7 non descrive `ASSEGNATO` come stato di nascita: non è
sbagliata, è **incompleta** da quando esiste il riporto.

#### (d) ⚠️ La ragione per cui la RLS non serviva è scaduta

§8.6 dichiara *«nessuna RLS su `fatture_fondi_fattura_source`: il perimetro passa
dalla fattura»*. La **conclusione** può reggere ancora; la **premessa** no. Il
giorno in cui è stata scritta la tabella aveva un lettore (la vista
`security_invoker`, protetta dal `JOIN INNER` con `vendite.fatture`) e nessuno
scrittore fuori da `vendite`. Oggi ha:

* un lettore applicativo — `GET /vendite/fondi-fattura/da-decidere/`;
* una **pagina Vue** aperta agli operatori;
* uno **scrittore in un altro schema** — `pagamenti.fn_conferma_sistemazione`.

⭐ **E il cantiere accanto ha appena pagato esattamente questo.** Il passo **E-4**
del brief posting (2026-08-28) ha trovato `pagamenti.enti_incasso` **senza row
security** — trovato non da un conteggio (le tabelle erano vuote: zero ovunque,
verde per sottrazione) ma da una **misura strutturale**, `relrowsecurity` tabella
per tabella, più due operatori veri di due emittenti diversi. *Qui la stessa
misura dà lo stesso esito, e la differenza è che qui era una scelta dichiarata —
il che la rende una scelta da **riconfermare**, non un buco.*

#### (e) 🔵 Quattro punti del brief che raccontavano un sistema che non c'è più

Corretti in questo giro, e registrati qui perché la lezione è la stessa di D-17:

| Diceva | Dice il codice |
| --- | --- |
| *«la pagina Vue è l'unico lavoro rimasto»* | ✅ fatta il 22/08 **da un altro cantiere** (`brief-db-liste-drawer-lotto.md`) |
| D-7, quarto stato: *«⛔ non applicato, è un piano»* | ✅ applicato il 21/08 (`20260821-49/-50/-54`), reset compreso |
| *«il lotto 7 è non scritto»* (misurato il 22/08 mattina) | ✅ atterrato **lo stesso giorno alle 12:20** |
| *«la Fase D aspetta il processo rimborsi»* | 🔴 il processo è arrivato e **non è passato di lì** |

⭐ **La lezione, e non è «aggiornare più spesso»**: tre di questi quattro sono
stati chiusi da **squadre diverse** che non sapevano di chiudere una riga di
questo documento. Un brief che descrive un'attesa deve nominare **chi la
soddisfa**, o non saprà mai di essere stato accontentato.

---

### 9.3 I passi

> ~~⚠️ **Nessuno di questi passi è stato scritto.** E tre dipendono da una
> decisione di dominio (§9.4): finché non c'è, si scriverebbe la cosa sbagliata
> in fretta.~~
>
> ✅ **SUPERATO il 2026-08-31 (sera): sono stati scritti tutti e sette**, provati
> e documentati — changeSet `20260831-61` … `-67`, più tre CSV di `80_data` e tre
> file pgTAP nuovi. ⛔ **Non applicati.** Elenco, scostamenti dal piano e le cinque
> cose trovate dal collaudo in **§9.11**.
>
> ⚠️ **La tabella qui sotto resta com'era, e si legge insieme a §9.11**: descrive
> ciò che andava fatto, non ciò che è stato scritto. Dove le due divergono — la
> soglia che è un dato e non una lista, i sei motivi invece di quattro, l'ordine
> invertito dentro D-25 — a valere è §9.11, che dice anche perché.

| | Passo | Dove | Dipende da |
| --- | --- | --- | --- |
| **D-19** | ⭐ **La descrizione di `E_FONDO_STATO_NON_AMMESSO` a catalogo racconta la matrice a TRE stati** (*«DISPONIBILE ↔ ASSEGNATO, entrambi verso ANNULLATO, ANNULLATO terminale»*), mentre gli stati sono **quattro** dal 21/08. È il testo che uno sviluppatore legge quando il codice scatta: si corregge la riga in `config/codici_errore.csv` (edit del CSV, **mai** un `UPDATE` SQL) | `80_data/` | — |
| **D-20** | 🔴 **Accendere la RLS** su `fatture_fondi_fattura_source` (**G-2**, decisione di Tid): le **due** policy della famiglia — `ef_whitelist` e `ba_ownership` — come su ogni altro satellite della fattura. ⭐ E qui **non serve il `JOIN` via fattura** che gli altri satelliti hanno dovuto fare: la riga porta `emittente_soggetto_ruolo_id` e `billing_account_id` **NOT NULL** in colonna. §9.9. ~~⚠️ Va **riscritta anche la ragione** in §8.6, non solo la conclusione~~ ✅ **la parte di documento è FATTA (2026-08-31)**: §8.6 porta la ragione riscritta, e la stessa scelta ribaltata è annotata anche in [api_fondi_fattura.md](../../backend/vendite/manual/api_fondi_fattura.md) §Note. ⚠️ **Quelle due righe vanno riscritte al momento dell'apply**, non prima: oggi descrivono lo stato di fatto (la RLS non c'è) e diventano false il giorno del changeSet | `00_schema/vendite/` | ✅ nessuna |
| **D-21** | 🔴 **`vendite.fn_cancella_fondo_fattura(p_source_id)`** — era D-12. ⭐ **Non è una funzione nuova: è una funzione ESTRATTA.** I tre blocchi («non ancora fatturato») e la cancellazione in tre passi vivono già dentro `fn_reset_fondi_fattura`, e con D-25 avrebbero un **secondo** consumatore: è la regola del 2, e questo cantiere l'ha già pagata una volta con `fn_saldo_sorgente_fondo`. La consumano `fn_reset_fondi_fattura` (che smette di farlo inline) e `pagamenti.fn_annulla_sistemazione`. ⭐ **E si spacca in due**, perché i due consumatori reagiscono in modo opposto: un **predicato** che dice *perché* non si può, e la funzione che **cancella** — §9.7-b | `20_code/vendite/` | ✅ nessuna |
| **D-22** | **Il guard di transizione anche in `INSERT`** (§9.2-c): stati di nascita ammessi `DISPONIBILE` e `ASSEGNATO`, gli altri due rifiutati con `E_FONDO_STATO_NON_AMMESSO`. ⚠️ Va montato **dopo** aver verificato che non rompa il riporto — che nasce `ASSEGNATO` ed è il caso da ammettere, non da bloccare. E la matrice di D-7 va riscritta con lo stato di nascita dentro | `20_code/vendite/` | — |
| **D-23** | **`governa_fondo_fattura`** — l'azione di processo di D-13. ✅ **Serve**: G-1 dice che il gesto esiste, e un gesto che cancella denaro non può avere una porta più larga di quello che lo ha scritto (è la regola con cui il cantiere posting ha gated la correzione guidata sullo stesso cancello della registrazione). ⚠️ **Il seed non è la concessione**: il precedente è `registra_distinta` (id 32, area 7), a catalogo dal 25/08 e **ancora chiuso per tutti tranne il super admin** perché nessuno l'ha assegnata a un profilo. Se si semina, si assegna nello stesso giro | `80_data/` | — |
| **D-24** | **pgTAP**: la cancellazione di un fondo nato da sistemazione, il rifiuto su ognuno dei **quattro** motivi del predicato (§9.7-b) — compresa la **figlia `DEFINITIVA`**, che è il caso nuovo e va **costruito** in fixture — e i due stati di nascita vietati. ⚠️ `throws_ok` **sempre** con lo SQLSTATE, e la fixture va **costruita** — un test che itera su ciò che c'è passa a vuoto su un DB ricostruito | `db/pgtap/vendite/` | D-21, D-22 |
| **D-25** | 📮 **NON È DI QUESTO CANTIERE — è una richiesta a `pagamenti`.** `CONFERMATA → ANNULLATA` va aperta nella matrice delle sistemazioni (oggi **entrambi** terminali) e `fn_annulla_sistemazione` va estesa: sull'atto `RIPORTO` confermato chiama D-21 e, **solo se la cancellazione riesce**, porta l'atto ad `ANNULLATA` col motivo. ⚠️ Il varco dev'essere **chirurgico** su due assi: solo la transizione di stato (il guard oggi *«rifiuta OGNI update e non solo quelli di stato»*, e deve continuare) e **solo `destinazione = 'RIPORTO'`** (G-5). ⚠️ E il rifiuto sugli altri due tipi deve **nominare la correzione guidata**, non dire «immutabile». §9.6 · §9.8 | `pagamenti` — **brief al team DB** | ✅ nessuna |

#### Lato BE / FE

| | Passo | Perimetro | Nota |
| --- | --- | --- | --- |
| **BE-4** | 🔴 **Ri-perimetrato una seconda volta, e si accorcia ancora.** Il gesto dell'operatore sul riporto sbagliato **non è un endpoint nuovo**: è `POST /api/v1/pagamenti/sistemazioni/{id}/annulla/`, **che esiste già ed è scritto** (S-4 del cantiere posting). Lato BE non c'è niente da costruire: cambia solo *quando* il FE lo offre. 🔵 Resta **un** comando da scrivere, e per l'**altra** popolazione — il fondo `AUTOMATICA` `DISPONIBILE` non più capiente, che l'elenco della lista 44 addita e che non ha nessuna sistemazione dietro: `DELETE /api/v1/vendite/fondi-fattura/{id}/` su D-21. ⭐ **Il metodo dice il verbo**, e `api.md` §Grammatica URL vieta di scriverlo nel path. `post_permission` di D-23, una sola `SELECT fn_…()`, errori tradotti da `translate_db_errors`, `Idempotency-Key` (il gesto è irreversibile) | `vendite_service.py` + `vendite_repository.py` — ⛔ **nessun file di sottodominio**: un metodo non fa un sottodominio (AGENTS.md) | D-21 |
| **FE-1** | La **colonna `azioni`** sulla lista `id 44` (`vendite.fondi_fattura_da_decidere`): oggi non c'è, e il seed lo dichiara — *«una colonna che apre un menu vuoto è la stessa cosa di una riga di elenco che non può accadere»*. Si aggiunge **con** BE-4, mai prima. ⚠️ Serve **solo** al motivo `NON_PIU_CAPIENTE`: gli altri tre non hanno un atto da cancellare, e un kebab che si disegna a zero voci è un difetto già trovato e corretto dal cantiere posting | `80_data/sql/ui/` + `FondiFatturaDaDecidereTab.vue` | BE-4 |
| **FE-2** | `RowActionsMenu` + `MANAGE_ICONS.KEBAB` sulla riga, azione gated sul permesso di D-23, dialogo di conferma **rosso** (`useConfirmAction` destrutturato, callback `onAccept`) — è irreversibile. ⛔ Mai la matita, e `if (result !== null)` sul ritorno | `frontend/src/vendite/` | BE-4, D-23 |
| **FE-3** | ⭐ **L'altra metà, e sta in `pagamenti`**: offrire «annulla» anche su una sistemazione **`CONFERMATA` di tipo `RIPORTO`** — oggi il drawer lo offre solo in `BOZZA`, perché fino a ieri `CONFERMATA` era terminale. ⚠️ Il gesto **si spegne da sé** sugli altri due tipi e sul fondo già fatturato: il FE non ricalcola la regola, legge il rifiuto. E dopo l'annullamento il drawer **si chiude** — l'eccedenza in testata è cambiata (stessa scelta già fatta su S-5) | `frontend/src/pagamenti/` | D-25 |

#### Ordine

```text
D-19  ─── indipendente, costo nullo, si fa subito
D-20  ─── decisione (G-2), poi al massimo un changeSet
D-22  ─── indipendente da G-1: il buco dello stato di nascita c'è comunque

✅ G-1 · ✅ G-2 · ✅ G-3 · ✅ G-4 · ✅ G-5  (Tid, 2026-08-29 — tutte e cinque chiuse)
        │
        └─▶ D-21  ─┬─▶ D-25 (📮 team DB, schema pagamenti) ─▶ FE-3
                   ├─▶ BE-4 ─▶ FE-1 ─▶ FE-2      ← l'ALTRA popolazione
                   └─▶ D-24

🟢 NESSUN PASSO ASPETTA PIU' UNA DECISIONE, E NESSUNA DOMANDA E' APERTA.
   Da qui e' tutto lavoro: i passi DB si passano al team (§9.10).

D-23  ─── indipendente: il cancello serve comunque, e va ASSEGNATO nello stesso giro
D-19 · D-20 (RLS) · D-22  ─── indipendenti da tutto quanto sopra
```

---

### 9.4 Le domande aperte

> ⚠️ **Sono domande di dominio, non di implementazione**: la risposta cambia
> quali passi esistono, non come si scrivono.

| | Domanda | Che cosa dipende | Stato |
| --- | --- | --- | --- |
| **G-1** | **Un riporto già confermato si può disfare?** | D-21 · D-23 · BE-4 · FE-1 · FE-2 — cioè **tutto il resto del cantiere** | ✅ **CHIUSA da Tid, 2026-08-29**: **sì, e il fondo si CANCELLA** — permesso solo se non è già stato **fatturato**. §9.5 |
| **G-2** | **La RLS su `fatture_fondi_fattura_source` si accende?** Oggi il perimetro passa dal `JOIN` con `vendite.fatture` dentro la vista; da agosto la tabella ha un lettore applicativo, una pagina e uno scrittore di un altro schema | D-20 | ✅ **CHIUSA da Tid, 2026-08-29**: **sì, si accende**. §9.9 |
| **G-3** | ⭐ **Nata dalla risposta a G-1.** «Non ancora **fatturato**»: la soglia è quella con cui il progetto congela già gli altri satelliti della fattura — `stato NOT IN ('DRAFT','EMESSA')` — oppure è più stretta? §9.5-a | il guard di D-21 | ✅ **CHIUSA da Tid, 2026-08-29**: **la stessa soglia**. §9.7 |
| **G-4** | ⭐ **Nata da una misura, non da un dubbio.** Il `DELETE` del fondo oggi è **impossibile**: la FK di `pagamenti.sistemazioni` lo trattiene e l'atto che lo trattiene è **immutabile**. Che cosa succede a quell'atto quando il fondo si cancella? §9.5-b | la forma di D-21 | ✅ **CHIUSA da Tid, 2026-08-29**: **si annulla anche lui**. §9.6 |
| **G-5** | ⭐ **Nata dalla risposta a G-4.** L'apertura `CONFERMATA → ANNULLATA` vale **solo per il `RIPORTO`**, o anche per `RIMBORSO` e `COMPENSAZIONE`? | il perimetro di D-25 | ✅ **CONFERMATA da Tid, 2026-08-29**: **solo `RIPORTO`**. Gli altri due restano terminali com'erano. §9.8 |

⭐ **G-1 era quella che decideva se il cantiere avesse ancora dei passi**: la
risposta è sì, e ne ha aperte due che nessuno aveva visto — una di soglia (G-3) e
una di **struttura** (G-4), che non era un'opinione ma un vincolo che oggi non si
può soddisfare. ✅ **G-4 è chiusa lo stesso giorno**, e la sua risposta ha
**accorciato** il lavoro invece di allungarlo: §9.6.

---

### 9.5 G-1 è chiusa: si **cancella**. E la risposta apre due nodi

> ✅ **Decisione di Tid, 2026-08-29**: *«sì, ma devo cancellare il fondo, e questo
> sarà permesso solo se il fondo stesso non è stato già fatturato»*.

⭐ **«Cancellare» e non «annullare» non è una sfumatura, ed è coerente con una
decisione già presa altrove.** Il vecchio **D-12** proponeva il passaggio ad
`ANNULLATO` con motivo obbligatorio; ma il **2026-08-21** il cantiere posting ha
già riscritto `fn_reset_fondi_fattura` perché **cancelli** l'atto non eseguito
invece di riportarlo a `DISPONIBILE` (changeSet `-54`), e la ragione era che
`ANNULLATO` portava tre significati diversi. *Un atto che non è mai diventato un
fatto non lascia una riga di registro: lascia il posto vuoto che aveva prima.*
🔴 **Quindi D-12 come era scritto è superato**, e con esso il codice
`E_FONDO_ANNULLAMENTO_BLOCCATO` proposto in D-14, che non è mai stato seminato.

#### (a) ⭐ «Non ancora fatturato»: il criterio esiste già, e si riusa

`fn_reset_fondi_fattura` — letta dal corpo vivo, non ricordata — non cancella
tutto: separa gli atti in **tre** che non si toccano e uno che si cancella.

| Chi non si tocca | Come lo riconosce | Che cosa fa |
| --- | --- | --- |
| l'atto **`ESEGUITO`** | `s.stato = 'ESEGUITO'` | solo **segnala** (`W_FONDO_ESEGUITO_NON_RESETTABILE` in `fatture_log`): il trasferimento è già stato registrato |
| l'atto con una riga contabile **`POSTATA`** | join su `vendite_contabili_righe` × stato | blocca — ed è un'**anomalia**: l'invariante vuole che in quel caso l'atto sia già `ESEGUITO` |
| l'atto la cui riga sta in una distinta **`CHIUSA`** | join su `vendite_contabili` × stato | blocca (`W_FONDO_MINIMO_NON_RIPRISTINABILE`) |
| **tutti gli altri** | — | ⭐ **si cancellano** |

⛔ **Questi tre blocchi non si riscrivono in D-21: si estraggono.** È la regola
del 2, ed è già stata pagata una volta in questo cantiere — `fn_saldo_sorgente_fondo`
nacque esattamente così, estraendo una formula che era inline in due posti.

⚠️ **Ma i tre parlano tutti di DENARO, non di DOCUMENTO** — ed è il buco che
§9.7 chiude. La parola di Tid è *«fatturato»*. Il fondo di un riporto nasce **`ASSEGNATO` a una fattura figlia**
e ne entra nel `totale_a_pagare`: se quella figlia è già stata emessa,
cancellare il fondo cambia un documento fiscale, e nessuno dei tre blocchi se ne
accorgerebbe. Serve quindi **una quarta condizione, sullo stato della figlia** —
ed è **G-3**.

⭐ **La soglia di casa esiste e non va inventata**: `trgfn_fattura_satellite_guard_congelamento`
congela scadenze e indirizzi quando la fattura esce da `('DRAFT','EMESSA')`, e il
`COMMENT` dice *«oltre la soglia il documento è uno snapshot fiscale e i suoi
satelliti non si toccano più»*. ⚠️ Il fondo è **l'unico satellite della fattura
non congelato** — lo dice D-6 — quindi qui non si aggiungerebbe una regola: si
finirebbe di applicarne una che c'è già.

#### (b) 🔴 Il nodo: oggi quel `DELETE` non è vietato, è **impossibile**

Misurato sul catalogo il 2026-08-29, e non è una previsione:

```text
pagamenti.sistemazioni.fondo_source_id
   → FK fk_sistemazioni_fondo_source ... ON DELETE NO ACTION
   → UNIQUE uq_sistemazioni_fondo_source

pagamenti.trgfn_sistemazioni_guard_transizione
   → su un atto CONFERMATA rifiuta OGNI update, non solo quelli di stato
     (E_SISTEMAZIONE_IMMUTABILE)
```

Ne discende un cul-de-sac chiuso da entrambi i capi:

1. il `DELETE` del fondo è **trattenuto dalla FK** finché la sistemazione lo punta;
2. per staccare il puntatore serve un `UPDATE` su `pagamenti.sistemazioni`;
3. ma quella riga è `CONFERMATA`, e **ogni** `UPDATE` su un atto terminale è rifiutato.

⭐ **Non è un difetto di nessuno dei due cantieri**: ognuna delle tre regole è
giusta presa da sola, ed è la loro **intersezione** a non essere mai stata
percorsa — perché il gesto che la percorre è quello che stiamo progettando
adesso. *È il caso di scuola di due modelli corretti che si incastrano nel punto
in cui si toccano.*

⚠️ E la FK è `NO ACTION` **di proposito**: il `COMMENT` della colonna gemella su
`vendite_contabili_righe` lo dichiara — *«cancellare un atto pretende di aver
prima cancellato le sue righe; una FK differita nasconderebbe l'ordine invece di
dirlo»*. Quindi la strada non è cambiare la FK: è decidere **che ne è dell'atto
di sistemazione**, ed è **G-4**.

ℹ️ Un precedente di forma, se la strada sarà quella di un varco: il guard dei
satelliti ne ha già uno, via GUC `zeroerp.maintenance_reset_lotto_draft`, che
`fn_cleanup_fatture_by_ids` imposta per il reset lotto. ⛔ Non è una proposta —
è per dire che il progetto un modo per attraversare un guard senza spegnerlo ce
l'ha già, e non se ne inventa un secondo.

---

### 9.6 G-4 è chiusa: si annulla anche l'atto. E il lavoro si **accorcia**

> ✅ **Decisione di Tid, 2026-08-29**: *«annulliamo anche lui»* — la sistemazione
> che aveva deciso il riporto va ad `ANNULLATA` insieme al fondo che aveva creato.

⭐ **La risposta scioglie il nodo dal capo giusto.** Il varco all'immutabilità
resta l'ipotesi scartata: non si stacca un puntatore lasciando in piedi un atto
che dichiara di aver fatto una cosa che non c'è più. *L'atto e il suo effetto
cadono insieme, o il registro racconta un fatto che non è avvenuto.*

#### (a) Chi guida: **`pagamenti`**, e non è una preferenza

Tre ragioni, e nessuna è di gusto:

| | |
| --- | --- |
| **Chi alza la bandiera la abbassa** | il fondo l'ha creato `pagamenti.fn_conferma_sistemazione`; la stessa porta lo disfa. Due porte diverse per i due versi dello stesso atto divergono al primo cambio |
| **`api.md` non lascia scelta** | un service di `vendite` non può chiamarne uno di `pagamenti` (chiamate laterali vietate), e viceversa. La sola sede in cui i due schemi si toccano è **il database**, ed è dove il verso di andata già vive |
| **L'atto sta in `pagamenti`** | il fondo è la **conseguenza**, la sistemazione è la **decisione**. Si annulla la decisione, e la conseguenza cade con lei |

#### (b) La forma, e ⭐ perché D-21 diventa un'**estrazione** invece di una funzione nuova

La cancellazione del fondo non è un pezzo nuovo di logica: è **esattamente** ciò
che `fn_reset_fondi_fattura` fa già, dai tre blocchi fino all'ordine dei `DELETE`
che la FK impone. Con D-25 quel codice avrebbe **due** consumatori.

```text
vendite.fn_cancella_fondo_fattura(p_source_id)          ← D-21, estratta
    ├─ i tre blocchi («non ancora fatturato», §9.5-a) + la quarta condizione di G-3
    └─ i tre DELETE nell'ordine che la FK impone:
           vendite_contabili_righe → fatture_fondi_fattura → …_source

consumata da:
    vendite.fn_reset_fondi_fattura      (smette di farlo inline)
    pagamenti.fn_annulla_sistemazione   ← D-25, sul solo ramo RIPORTO
```

⚠️ **L'ordine dentro D-25 non è indifferente**: prima si cancella il fondo, e
**solo se riesce** si porta l'atto ad `ANNULLATA`. Al contrario si otterrebbe una
sistemazione annullata con il suo fondo ancora vivo — cioè il record che si
contraddice da cui è nato lo stato `ESEGUITO` (D-7). ⭐ E l'atomicità è gratis:
è tutto dentro una funzione, che è la riga preferita di `api.md` §Atomicità.

#### (c) ⚠️ Tre conseguenze da conoscere prima di scrivere

1. 🔴 **La matrice delle sistemazioni cambia**, e oggi dice il contrario:
   `BOZZA → CONFERMATA | ANNULLATA`, **entrambi terminali**. Va aperta
   `CONFERMATA → ANNULLATA`, e il varco dev'essere **chirurgico** — il guard
   attuale *«rifiuta OGNI update e non solo quelli di stato»*, e deve continuare
   a farlo per tutto il resto. ⛔ Non è una riga di questo cantiere: è una
   richiesta al team DB (**D-25**).
2. ⚠️ **Cancellare RIAPRE la rigenerazione automatica**, e non è una scoperta —
   `fn_reset_fondi_fattura` lo **dichiara già** nel suo `COMMENT`: *«l'"atto
   unico" guarda se un atto esiste in qualunque stato, quindi il giro successivo
   ne rifà uno leggendo il residuo di adesso»*. Sul riporto è il comportamento
   giusto (l'eccedenza è tornata al suo posto, e se merita un fondo lo rifà), ma
   va **detto**, non scoperto al primo giro notturno.
3. ⚠️ **La tabella non è storicizzata**: il `DELETE` è definitivo. La traccia di
   ciò che è successo resta **solo** in `pagamenti.sistemazioni`, che diventa
   `ANNULLATA` **con il motivo** — ed è la ragione per cui il motivo lì è
   obbligatorio. *È il registro a ricordare, non la conseguenza.*

#### (d) ⭐ Che cosa si accorcia

| Prima si pensava | Adesso |
| --- | --- |
| un comando BE nuovo per disfare il riporto | ⭐ **niente**: `POST /pagamenti/sistemazioni/{id}/annulla/` **esiste già** (S-4). Cambia solo *quando* il FE lo offre — **FE-3** |
| D-21 funzione nuova da progettare | **estrazione** di logica che esiste, con un secondo consumatore che la giustifica |
| l'azione di processo su tutto il gesto | il gesto sul riporto passa dal cancello **di `pagamenti`**, che c'è già; `governa_fondo_fattura` (**D-23**) serve per l'**altra** popolazione — il fondo `AUTOMATICA` non più capiente della lista 44 |

✅ **E la derivazione è stata confermata** (**G-5**, Tid, 2026-08-29): l'apertura
`CONFERMATA → ANNULLATA` vale **solo** per il `RIPORTO`. Gli altri due tipi
producono una **distinta**, e per quella il rimedio esiste già ed è la
**correzione guidata** — aprire anche lì l'annullamento darebbe *due* strade per
disfare lo stesso fatto, che è il modo in cui due meccanismi cominciano a
divergere. Che cosa ne discende per il messaggio di rifiuto: **§9.8**.

---

### 9.7 G-3 è chiusa: «fatturato» è la soglia di casa, e D-21 diventa scrivibile

> ✅ **Decisione di Tid, 2026-08-29**: *«la stessa soglia»* — **`DEFINITIVA`**.

⭐ **Non si aggiunge una regola: si finisce di applicarne una che c'è già.** Il
fondo è **l'unico satellite della fattura non congelato** — lo dice D-6, ed era
un'osservazione senza conseguenze finché nessuno poteva toglierlo di mezzo a
mano. Adesso che qualcuno può, la soglia è quella che il progetto usa già su
scadenze e indirizzi, per `codice_interno` e mai per `codice`:

```text
figlia in DRAFT o EMESSA   →  il fondo si può ancora cancellare
figlia da DEFINITIVA in poi →  congelata: il fondo non si tocca
```

⚠️ **La quarta condizione riguarda solo i fondi `ASSEGNATO`.** Un fondo
`DISPONIBILE` non ha una figlia (`fattura_figlia_id IS NULL`): lì la condizione è
vuota e non blocca niente — che è il caso della lista 44 (**BE-4**).

⚠️ **E un corollario dichiarato, non scoperto**: `ANNULLATA` sta anch'essa fuori
da `('DRAFT','EMESSA')`, quindi il fondo di una figlia annullata **non è
cancellabile da questo gesto**. È lo stesso comportamento che il guard dei
satelliti ha già su scadenze e indirizzi, e la strada per quei casi resta quella
tecnica — `fn_cleanup_fatture_by_ids` col suo bypass di manutenzione. *Non è una
svista: è che il gesto di una persona e la pulizia di un lotto non sono la stessa
porta.*

#### (a) 🟢 Da qui D-21 non aspetta più niente

Le tre decisioni di oggi lo chiudono per intero: **si cancella** (G-1), **con
l'atto che cade insieme** (G-4), **fino a `DEFINITIVA`** (G-3). Resta aperta solo
**G-5**, che riguarda il **perimetro di D-25** — non D-21.

#### (b) ⭐ E la «estrazione» si spacca in due, perché i consumatori reagiscono al contrario

Scrivendo la condizione viene fuori che i due consumatori **non vogliono la
stessa cosa** dallo stesso criterio:

| Consumatore | Che cosa fa quando l'atto è bloccato |
| --- | --- |
| `fn_reset_fondi_fattura` | ⭐ **segnala e prosegue** — scrive `W_FONDO_…` in `fatture_log` e passa all'atto dopo: è un giro tecnico su N atti, e un'eccezione fermerebbe il reset di un lotto intero |
| `fn_cancella_fondo_fattura` | 🔴 **rifiuta e lo dice** — è il gesto di **una persona** su **un** atto: qui il silenzio è il difetto |

⛔ **Quindi non si estrae la funzione: si estrae il PREDICATO**, e i due ci
costruiscono sopra reazioni diverse.

```text
vendite.fn_check_fondo_cancellabile(p_source_id)  →  motivo bloccante | NULL
    STABLE, vocabolario chiuso:
      ATTO_ESEGUITO · RIGA_REGISTRATA · CONTABILE_CHIUSA · FIGLIA_CONGELATA
                                                          └─ la quarta, da G-3

    ├─ fn_reset_fondi_fattura      → mappa il motivo sul suo W_… e prosegue
    └─ fn_cancella_fondo_fattura   → solleva, e il motivo è la frase
```

⭐ **È lo stesso pattern che questo cantiere ha già applicato due volte**, e non
per eleganza: `fn_saldo_sorgente_fondo` (una formula, tre chiamanti) e
`fn_check_fondo_fattura_capiente` — *«il caso `NON_PIU_CAPIENTE` dell'elenco è la
regola del guard, negata: due copie avrebbero detto che un fondo è inapplicabile
mentre il giro lo applica»*. Qui il divario sarebbe **peggiore**: un reset che
cancella un atto che il gesto manuale dichiara intoccabile.

⚠️ **Attenzione a non ripetere il difetto già trovato in Fase C**: il guard
chiamava `fn_saldo_sorgente_fondo` **due volte sulla stessa riga**, accettando
metà condizione e rifiutando l'altra. Il predicato si legge **una volta sola**.

#### (c) I codici errore che servono, e la domanda «riuso o conio»

Il reset di oggi ha **due** codici di avviso con la `cause` nel `meta`
(`W_FONDO_ESEGUITO_NON_RESETTABILE` con due cause diverse,
`W_FONDO_MINIMO_NON_RIPRISTINABILE`): è la forma della casa, e il rifiuto la
rispecchia.

| Codice | Classe | Quando |
| --- | --- | --- |
| `E_FONDO_NON_CANCELLABILE` | `CONFLITTO_STATO` | i tre motivi che parlano di **denaro**, con la `cause` nel contesto |
| `E_FONDO_FIGLIA_CONGELATA` | `CONFLITTO_STATO` | il quarto: la figlia è `DEFINITIVA` o oltre |

⚠️ **Sul secondo va posta la domanda prima di coniarlo**: `E_FATTURA_SATELLITE_CONGELATO`
**esiste già** ed è la stessa regola sulla stessa soglia. Il criterio di AGENTS.md
non è «la condizione è la stessa?» ma **«chi può rimediare?»** — e qui è la stessa
persona, davanti alla stessa frase. ⭐ L'unico argomento per coniarne uno nuovo è
che il messaggio esistente riceve `TG_TABLE_NAME` nel `VARIADIC`, cioè
**infilerebbe il nome di una tabella nella frase che l'operatore legge**. Decide
chi scrive il changeSet, col ramo davanti — ⛔ non si sceglie dal nome.

⚠️ E su entrambi vale `RAISE … USING COLUMN`: il canale `error.fields` esiste già
e il backend lo consegna al client.

---

### 9.8 G-5 è confermata: si annulla **solo** il `RIPORTO`

> ✅ **Conferma di Tid, 2026-08-29**: l'apertura `CONFERMATA → ANNULLATA` vale
> **solo** per il `RIPORTO`; `RIMBORSO` e `COMPENSAZIONE` restano terminali.

**Il perché, in una riga**: le tre destinazioni non producono la stessa cosa.

| Destinazione | Che cosa lascia dietro | Come si disfa |
| --- | --- | --- |
| `RIPORTO` | un **fondo** in `vendite` | ⭐ **si annulla l'atto**, e il fondo cade con lui — D-25 |
| `RIMBORSO` · `COMPENSAZIONE` | una **distinta contabile** | ✅ la **correzione guidata** (S6, `fn_crea_distinta_correzione`), che esiste già |

⛔ **Due strade per disfare lo stesso fatto è il modo in cui due meccanismi
cominciano a divergere**: la prima volta fanno la stessa cosa, alla prima regola
nuova no — e nessuno sa più quale delle due è quella giusta.

#### ⚠️ La conseguenza che si vede a video, e va scritta nella richiesta al team DB

Con il varco ristretto al `RIPORTO`, un operatore che prova ad annullare un
`RIMBORSO` confermato riceve `E_SISTEMAZIONE_IMMUTABILE` — **e non è abbastanza**.
⭐ Non lo dico io: lo dice già il `COMMENT` di quel guard, che si autocritica
proprio su questo —

> *«"non può passare da CONFERMATA a BOZZA" è vero ma non aiuta chi sta provando
> a correggere un importo già eseguito»*

Quindi il rifiuto su `RIMBORSO`/`COMPENSAZIONE` deve **nominare l'alternativa**:
non «questo atto è immutabile», ma *«un rimborso già eseguito si corregge con la
correzione guidata sulla sua distinta»*. 🔵 Se serva un codice suo o basti la
frase del codice esistente lo decide chi scrive il changeSet, col ramo davanti —
è la stessa domanda «riuso o conio» di §9.7-c, e la risposta si dà **guardando
chi può rimediare**, non il nome.

⭐ **E il predicato del guard è banale e va detto**: la condizione è
`destinazione = 'RIPORTO'`, cioè una colonna della **stessa riga**. Nessun JOIN,
nessuna lettura in `vendite`: il varco si apre su un dato che il guard ha già
sotto mano.

---

### 9.9 G-2 è chiusa: la RLS si accende. ⭐ E la misura dice che il fondo era l'assente di **due** famiglie

> ✅ **Decisione di Tid, 2026-08-29**: **sì**, si accende la row security su
> `vendite.fatture_fondi_fattura_source`.

#### (a) L'argomento che il 15 agosto non c'era

La riga di §8.6 non era sbagliata quando fu scritta: l'unico accesso era **la
lista**, e la lista è protetta dal `JOIN INNER` con `vendite.fatture`. Il gesto di
**D-21** ne apre uno di natura diversa —

```text
DELETE /api/v1/vendite/fondi-fattura/{id}/
                                     └── un id non ha nessun JOIN davanti
```

— cioè **un accesso per id**, in cui un operatore dell'emittente A può nominare
un fondo dell'emittente B. ⭐ È **la stessa forma** del buco che **E-4** ha
appena trovato nel cantiere accanto (`GET /conti-incasso/?soggetto_ruolo_id=…`,
2026-08-28), e la lezione lì è che *«un conteggio non l'avrebbe trovato: le
tabelle sono vuote, quindi tutti i contesti danno zero — verde per sottrazione»*.

#### (b) ⭐ La scoperta della misura: è lo stesso assente di D-6

Guardando **quali** satelliti della fattura hanno le policy, viene fuori una
simmetria che vale più dell'argomento di (a):

| Satellite | Congelamento oltre `EMESSA` | RLS `ef_whitelist` + `ba_ownership` |
| --- | :---: | :---: |
| `fatture_scadenze` | ✅ | ✅ |
| `fatture_indirizzi` | ✅ | ✅ |
| `fatture_righe` · `fatture_riepiloghi_iva` | ✅ | ✅ |
| **`fatture_fondi_fattura_source`** | ⛔ **no** (→ G-3, §9.7) | ⛔ **no** (→ G-2, qui) |

🔴 **Il fondo è l'assente di entrambe le famiglie, e non se n'era accorto
nessuno perché le due assenze erano state discusse in due posti diversi**: la
prima in D-6 (*«il fondo è l'unico satellite non congelato»*, osservata e
accettata), la seconda in §8.6 (*«niente RLS: il perimetro passa dalla
fattura»*, decisa). Sono la stessa dimenticanza, vista da due lati. ⭐ *Due
eccezioni ragionevoli prese una alla volta fanno una regola che non vale per un
oggetto solo — e quell'oggetto è l'unico che muove denaro.*

#### (c) La forma, e ⚠️ perché qui è **più semplice** che sugli altri satelliti

`fatture_scadenze` ha dovuto delegare a `script.fn_scope_ba_ownership_via_fattura`
— *«risolve il BA della fattura e delega»* — perché la riga il billing account non
ce l'ha. ⭐ Qui invece la riga porta **tutto in colonna, e NOT NULL**:

```text
emittente_soggetto_ruolo_id   bigint  NOT NULL   → ef_whitelist, senza JOIN
billing_account_id            bigint  NOT NULL   → ba_ownership, senza JOIN
```

⚠️ **E questo è precisamente ciò che evita l'errore che il team DB ha dovuto
correggere su `enti_incasso`**: là la `WITH CHECK` proposta *«cercava il legame
che l'`INSERT` stesso stava scrivendo»*, e avrebbe reso la tabella non
scrivibile. Qui i due valori sono **dentro `NEW`**: la `WITH CHECK` li legge
senza cercare niente altrove, e `pagamenti.fn_conferma_sistemazione` continua a
scrivere.

#### (d) ⚠️ Le tre cose da verificare accendendola, e non sono formalità

1. 🔴 **Sei file pgTAP scrivono su questa tabella** — `test-fondi-fattura.sql`,
   `-governo`, `-lotto`, `test-fondo-fattura-eseguito`,
   `test-cleanup-fattura-copertura-figlie-v1`, `rls/test-role-batch-fatturazione-postura`.
   Dal **2026-08-07** i pgTAP girano **come l'applicazione**, con le policy
   attive: una fixture che scrive dove l'applicazione non scrive **non passa
   più**. ⛔ Vanno guardati tutti e sei **prima** dell'apply, non dopo il rosso.
2. ⚠️ **Il giro notturno non deve fermarsi**: `fn_genera_fondi_fattura_source` e
   `fn_applica_fondi_fattura` girano nel contesto batch, e
   `zeroerp_batch_fatturazione` ha `BYPASSRLS` — quindi non cambia niente. **Va
   verificato, non dedotto**: è l'unico percorso che, rompendosi, si vedrebbe
   solo la mattina dopo.
3. ⚠️ **Un conteggio a zero non è una prova.** La tabella oggi ha zero righe:
   qualunque misura sui dati darà lo stesso numero con e senza policy. Le due
   prove che valgono sono quelle di E-4 — **strutturale** (`relrowsecurity` e le
   policy sul catalogo) e **comportamentale** (la stessa lettura fatta da due
   operatori di due emittenti diversi).

---

### 9.10 📮 Che cosa passa al team DB

> ⛔ **Le azioni DB non le esegue questo cantiere**: si scrivono e si aspetta. È
> qui e non in un documento a parte — un brief separato si giustifica quando
> cambia il **soggetto**, non quando cambia **chi lavora**.

| Ordine | Passo | Schema | Perché in quest'ordine |
| :---: | --- | --- | --- |
| 1 | **D-19** — la descrizione di `E_FONDO_STATO_NON_AMMESSO` a catalogo (tre stati → quattro) | `80_data` | costo nullo, e sana un testo **falso oggi** |
| 2 | **D-22** — il guard di transizione anche in `INSERT` | `20_code/vendite` | indipendente, e chiude un buco che c'è **adesso** |
| 3 | **D-20** — le due policy RLS | `00_schema/vendite` | prima di D-21, che apre l'accesso per id |
| 4 | **D-21** — il predicato + `fn_cancella_fondo_fattura` | `20_code/vendite` | è il pezzo che gli altri consumano |
| 5 | **D-23** — `governa_fondo_fattura` ⚠️ **e la sua assegnazione a un profilo** | `80_data` + in-app | il seed non è la concessione: il precedente `registra_distinta` è chiuso per tutti da quattro giorni |
| 6 | **D-25** — matrice + `fn_annulla_sistemazione` estesa sul solo `RIPORTO` | **`pagamenti`** | dipende da D-21, ed è **l'unico passo fuori da `vendite`** |
| 7 | **D-24** — i pgTAP | `db/pgtap/vendite` | ⚠️ nello **stesso lotto** dei passi che collauda |

Poi il backend (**BE-4**) e il frontend (**FE-1**, **FE-2**, **FE-3**), che non
aspettano altro.

---

### 9.11 ✅ Che cosa è stato scritto il 2026-08-31 (sera)

> ⛔ **Scritto e provato, NON applicato.** Nessun `liquibase update` è stato
> lanciato. L'SQL è stato **reso dagli YAML** — non riscritto a mano, che salta
> `COMMENT` e `GRANT` — ed eseguito in una transazione chiusa in `ROLLBACK`.

#### (a) I sette changeSet

| # | File | Che cosa fa |
| --- | --- | --- |
| `20260831-61` | `20_code/vendite/…-update-trgfn-fondi-source-guard-transizione-nascita` | **D-22** — il guard risponde anche in `INSERT`; il trigger si rinomina `…_ins_upd` |
| `20260831-62` | `00_schema/vendite/…-enable-rls-fatture-fondi-fattura-source` | **D-20** — `ef_whitelist` (FOR ALL) + `ba_ownership` (FOR SELECT) + `ENABLE` |
| `20260831-63` | `20_code/vendite/…-create-fn-check-fondo-cancellabile` | **D-21** — il **predicato** |
| `20260831-64` | `20_code/vendite/…-create-fn-cancella-fondo-fattura` | **D-21** — la cancellazione, e la sede unica dei tre `DELETE` |
| `20260831-65` | `20_code/vendite/…-update-fn-reset-fondi-fattura-su-predicato` | **D-21** — il reset smette di portare la propria copia del criterio |
| `20260831-66` | `20_code/pagamenti/…-update-trgfn-sistemazioni-guard-transizione-varco-riporto` | **D-25** — il varco `CONFERMATA → ANNULLATA`, solo `RIPORTO` |
| `20260831-67` | `20_code/pagamenti/…-update-fn-annulla-sistemazione-cancella-riporto` | **D-25** — annullare il riporto fa cadere il suo fondo |

⚠️ **I numeri sono stati riassegnati due volte.** Il primo blocco (55-57) è stato
occupato da un altro cantiere **mentre lo scrivevo**, e il secondo (58-60) è
stato spostato su richiesta di Tid. *Con cantieri paralleli il numero «libero»
scade nel minuto: si ricontrolla prima di salvare, non prima di scrivere.*

#### (b) I CSV di `80_data` — solo edit e append, nessun loader nuovo

* `config/codici_errore.csv` — **1 riga corretta** (D-19) e **7 righe nuove**;
* `config/messaggi_errore.csv` — **1 riga corretta** (D-19, `causa` + `soluzione`)
  e **5 righe nuove** (id 1034-1038);
* `config/azioni_processo.csv` — **1 riga nuova**: `governa_fondo_fattura`,
  id 34, area 2 (vendite), `pericolosa = t`.

> ⚠️ **Il seed non è la concessione**, ed è la trappola dichiarata nel riquadro in
> testa: `registra_distinta` è a catalogo dal 25/08 e **ancora chiusa per tutti**
> tranne il super admin, perché nessuno l'ha assegnata a un profilo.
> `config.profili_accesso_azioni` non ha un CSV di seed — la concessione si dà
> **in-app**, e va data nello stesso giro dell'apply.

#### (c) I pgTAP

| File | Asserzioni | Che cosa collauda |
| --- | :---: | --- |
| `vendite/test-fondo-fattura-cancellazione.sql` | 14 | gli stati di nascita, il predicato, la cancellazione, il bypass |
| `pagamenti/test-sistemazione-annullo-riporto.sql` | 13 | il varco su tre assi, la caduta del fondo, il rifiuto sugli altri due |
| `rls/test-rls-fondi-fattura-source-functional.sql` | 11 | le due policy, e soprattutto che la tabella resti **scrivibile** |
| `vendite/test-fondi-fattura-governo.sql` | 29 → **30** | riscritto il caso 4 e aggiunta la rete strutturale (vedi (e)) |
| `vendite/test-cleanup-fattura-copertura-figlie-v1.sql` | 11 | esteso il perimetro del presidio (vedi (e)) |

Tutti gli otto file toccati o vicini sono stati eseguiti **con l'SQL della slice
pre-applicato nella stessa transazione**, e confrontati con la corsa senza:
nessuna regressione residua.

⚠️ **Girano da owner**, perché il DDL non è ancora applicato: la RLS **non è
esercitata** in questa prova, tranne che nel file `rls/`, che se la arma da sé
con un `FORCE` locale alla transazione. Dopo l'apply vanno rilanciati come
applicazione.

#### (d) ⭐ Cinque scostamenti dal piano, e perché

| Il piano diceva | Che cosa è stato scritto | Perché |
| --- | --- | --- |
| **quattro motivi** nel predicato (§9.7-b) | **sei** | `ATTO_NON_TROVATO` nasce con D-20 stessa: da quando c'è la row security, «non esiste» e «non è tuo» devono dare la stessa risposta, e il posto per dirlo una volta sola è il predicato. `SISTEMAZIONE_ATTIVA` è la **FK** `fk_sistemazioni_fondo_source` detta prima che scatti — cioè un `23503` nudo evitato sul gesto della persona, e un reset di lotto che smette di fallire per intero |
| soglia `stato NOT IN ('DRAFT','EMESSA')` | `config.stati_doc_fiscale.congela_fiscale` | 🔴 **il brief era stantìo di un giorno**: dal `20260830-02` la guardia dei satelliti non porta più la lista, legge la colonna. Riscrivere la lista qui avrebbe rimesso in circolo la nona copia di una frase che quel passo aveva appena tolto |
| «prima si cancella il fondo, e **solo se riesce** si annulla l'atto» (§9.6-b) | prima si stacca e si annulla, **poi** si cancella | alla lettera non è eseguibile: la FK `NO ACTION` trattiene il `DELETE` finché l'atto punta il fondo, e per staccare il puntatore serve proprio quell'`UPDATE`. ⭐ La garanzia regge lo stesso **per costruzione** — è tutto dentro una funzione, quindi se la cancellazione solleva l'`UPDATE` non sopravvive, e il record che il brief temeva non è raggiungibile |
| **due** codici nuovi (§9.7-c) | **sette** | i due previsti, più `E_FONDO_NON_TROVATO` (D-20), `E_FONDO_TRATTENUTO_DA_SISTEMAZIONE` (il rifiuto che nomina l'alternativa), `E_SISTEMAZIONE_ANNULLO_NON_AMMESSO` (§9.8, la domanda lasciata a chi scrive il changeSet) e due `W_` per i rami nuovi del reset — che non hanno riga in `messaggi_errore`, come i loro gemelli |
| il varco «chirurgico su **due** assi» (§9.3 D-25) | **tre** | stato e destinazione erano i due dichiarati; il terzo sono le **colonne**, e senza di quello «rifiuta OGNI update e non solo quelli di stato» sarebbe diventato falso proprio sul ramo aperto |

⭐ **Sul terzo asse una scelta che vale la riga**: il confronto elenca le colonne
**ammesse** e non quelle vietate, così una colonna nuova sulla tabella nasce
**chiusa** invece di diventare modificabile in silenzio.

⚠️ **E una perdita, dichiarata**: portando l'atto ad `ANNULLATA`,
`chk_sistemazioni_eseguita` pretende `data_esecuzione`, `contabile_id` e
`fondo_source_id` a `NULL`. Il registro perderebbe *quando* l'atto era stato
eseguito. La memoria finisce in `meta -> 'annullata_dopo_esecuzione'`, che nessun
`CHECK` vincola. ⛔ **Allargare il `CHECK` era l'altra strada, ed è scartata**:
indebolire un vincolo per non perdere una data significa ammettere per sempre un
atto `ANNULLATA` che dichiara di essere stato eseguito.

#### (e) 🔴 Cinque cose che ha trovato il COLLAUDO, non il ragionamento

> ⭐ Sono qui perché sono la parte che non si sarebbe potuta scrivere a tavolino,
> e ognuna ha lasciato un presidio.

1. 🔴 **Il predicato era fail-open al contrario, e ha reso rossi sette test.** La
   prima stesura faceva `COALESCE(v_congela, TRUE)` — «una figlia che non si
   risolve vale congelata» — e bloccava anche la figlia che si legge e **non ha
   stato**, che il modello ammette (la colonna è nullabile). Sette asserzioni di
   `test-fondi-fattura.sql` sono diventate rosse, perché la loro figlia nasce
   così. ⭐ La correzione non è un `COALESCE` diverso: è **distinguere i due
   casi**, e per il secondo prendere la decisione che
   `trgfn_fattura_satellite_guard_congelamento` prende già — *due risposte
   diverse alla stessa domanda sono la divergenza che questo cantiere sta
   chiudendo.*
2. ⚠️ **Il guard di nascita OSCURA il `CHECK`.** Un `BEFORE ROW` scatta prima che
   i vincoli di tabella siano valutati: uno stato fuori vocabolario dà ora
   `P0001` e non più `23514`. Il test che lo asseriva è stato riscritto — e gli
   si è aggiunta un'asserzione che il `CHECK` **esista ancora, con tutti e
   quattro i valori**, perché senza quella spegnere il vincolo passerebbe
   inosservato: a fermare l'`INSERT` basterebbe il guard.
3. ⚠️ **Il presidio di copertura della pulizia aveva un perimetro invecchiato.**
   `test-cleanup-fattura-copertura-figlie-v1.sql` cerca il nome di ogni figlia
   «GESTITA» dentro il **testo** di `fn_cleanup_fatture_by_ids` +
   `fn_reset_fondi_fattura`. Spostando i `DELETE` in `fn_cancella_fondo_fattura`,
   `pagamenti.vendite_contabili_righe` non era più nominata → rosso. ⭐ Il
   presidio ha funzionato: la pulizia era davvero cambiata di sede, e l'elenco
   delle funzioni è stato esteso.
4. ⛔ **Un mio test diceva di presidiare un asse e non lo presidiava.** La prova
   di mutazione (togliere dal varco il confronto sulle colonne) lo lasciava
   **verde**: un `UPDATE` del solo importo non chiede l'annullamento, quindi a
   rifiutarlo bastava l'asse dello stato. L'asse delle colonne si esercita solo
   cambiando lo stato **e** un'altra colonna nella stessa istruzione — ed è un
   test in più, non lo stesso scritto meglio.
5. ⛔ **E un altro era verde per il motivo sbagliato.** Il caso «`INSERT` fuori
   scope rifiutato» stava in fondo al file, dopo un caso che lascia la sessione
   in veste `CLIENTE_PORTALE`: l'`INSERT` falliva davvero, ma per il **ruolo**,
   non per l'emittente. Il contesto ora si rimette esplicitamente prima
   dell'asserzione. *Se ne è accorto il riordino, non la rilettura.*

⚠️ **Sette mutazioni provate in tutto**, e ognuna doveva far cadere un test
preciso: il guard di nascita, il bypass di manutenzione, il confronto sulle
colonne, la caduta del fondo, la `USING` e la `WITH CHECK` della policy. ⛔ **Una
non ha fatto cadere niente**, ed è dichiarata nel file: il ramo «la figlia non si
legge» resta **scoperto**, perché la FK non lascia costruire un atto che punta
una fattura irraggiungibile.

#### (f) 📮 Che cosa resta, e a chi

| A chi | Che cosa |
| --- | --- |
| **Tid** | 🔴 l'**apply** dei sette changeSet, nell'ordine dei numeri |
| **Tid / amministrazione** | 🔵 **assegnare `governa_fondo_fattura` a un profilo**, in-app. Il seed non è la concessione |
| **team DB, dopo l'apply** | rilanciare come applicazione i cinque pgTAP toccati (`PGTAP_RUNNER=app`) e aggiornare la baseline se serve. ⚠️ In questa prova giravano da owner, quindi la RLS non è stata esercitata se non nel file `rls/` |
| **backend** | `manage.py genera_error_policies` per i sette codici nuovi, **e** la frase di ripiego in `error_messages_fallback.py` per i cinque `E_` — il test `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` è rosso finché mancano |
| **backend** | **BE-4**: il solo `DELETE /api/v1/vendite/fondi-fattura/{id}/` su `fn_cancella_fondo_fattura`, con `post_permission = governa_fondo_fattura` |
| **frontend** | **FE-1**, **FE-2**, **FE-3** — perimetro invariato, §9.3 |

🔵 **Un'annotazione per il giorno in cui servirà**, e non è un passo aperto: se il
frontend vorrà mostrare *perché* un fondo non si può cancellare **sulla riga**
della lista 44, la sede è `fn_check_fondo_cancellabile` — non una seconda
formula. Oggi il predicato non espone `reason_key`, perché nessuno la legge.

---

### 9.12 ✅ La colonna `azioni` della lista 44 — seminata, e 🔴 il resto della catena non c'è

> 📮 **Richiesta del team BE, 2026-08-31.** ⛔ **Perché è una voce DB e non FE-1:**
> metà di FE-1 è un **seed del catalogo**, cioè la stessa specie di D-19 e D-23.
> *Un passo si assegna per la sede in cui si scrive, non per il consumatore che
> lo userà.* La richiesta è accolta e **fatta**.

#### (a) Che cosa è stato scritto

Due righe, in append ai CSV che i mirror `loadUpdateData` già leggono — nessun
changeSet nuovo. `git diff --numstat` dà **`1 0`** su entrambi.

| File | Riga |
| --- | --- |
| `80_data/sql/ui/lista_colonna.csv` | `619,44,azioni,Azioni,,,azione,string,,70,999,center,,,f,f,f,f,f,t,…,common.col_azioni,100` |
| `80_data/sql/ui/lista_preset_colonna.csv` | `44,619,999,t,f` |

⚠️ **Tre scelte diverse da come la richiesta le descriveva**, e tutte per
allinearsi a ciò che il catalogo già fa:

* **`ordine_default = 999`** e non un numero in coda alla serie della 44 (che
  arriva a 160): tutti e **29** i precedenti usano 999 — «in coda» qui è una
  costante, non un calcolo;
* **`gruppo_ordine` vuoto** e non `99`: le liste 1/2/3 hanno 99, ma tutte e
  sedici le colonne della 44 hanno gruppo e gruppo_ordine vuoti. Con 99 sarebbe
  stata l'unica con un ordinamento di gruppo in una lista **senza gruppi**;
* **`priorita = 100`**: in `useResponsiveColumns` si ritira per prima la priorità
  **più bassa**, quindi la colonna delle azioni vuole la più alta.

✅ **Provato in transazione con `ROLLBACK`**: il resolver restituisce **17
colonne** con `azioni` ultima e **`colonne_nuove = 0`** — il banner DEF-2 resta
spento, ed è il motivo per cui la riga nel preset non è opzionale. I quattro
pgTAP che presidiano il seed liste restano verdi identici, compresa l'invariante
«ogni colonna di un preset appartiene alla stessa lista del preset».

#### (b) 🔴 «Il consumatore è pronto» non è vero, e va corretto qui

La richiesta si chiudeva con *«ℹ️ `DELETE /api/v1/vendite/fondi-fattura/{id}/`
esiste, è gated su `governa_fondo_fattura` e i suoi rifiuti arrivano tradotti.
Manca solo la colonna»*. ⚠️ **Tutte e tre le affermazioni sono false**, misurato
il 2026-08-31 su **cinque** branch dopo un `fetch` — `dev/db-tid`,
`dev/backend-tid`, `Tito-dev`, `main` e i rispettivi `origin/`:

```text
git grep "fondi-fattura"  in backend/  → solo /da-decidere/ e /da-decidere/export/  (due GET)
git grep "governa_fondo_fattura|fn_cancella_fondo_fattura"  in backend/  → 0 occorrenze
```

⭐ **È la stessa specie di difetto registrato stamattina** su
`docs/it/backend/vendite/manual/api_fondi_fattura.md`, dove tre affermazioni
erano false da nove giorni: *il documento che si legge PRIMA di scrivere il
codice non è quello che qualcuno rilegge quando il progetto cambia.*

#### (c) La catena è a CINQUE anelli, e la colonna è l'ultimo

| | Pezzo | Stato al 2026-08-31 | Se manca, l'anello dopo… |
| :---: | --- | --- | --- |
| 1 | `vendite.fn_cancella_fondo_fattura` | scritta (`20260831-64`), **non applicata** | `42883 function does not exist` |
| 2 | `governa_fondo_fattura` **concessa a un profilo** | seminata, non applicata, **mai concessa** | kebab spento per tutti tranne il super admin |
| 3 | `DELETE /api/v1/vendite/fondi-fattura/{id}/` (**BE-4**) | 🔴 **non esiste su nessun branch** | `404` |
| 4 | lo slot `#actions` nel `.vue` (**FE-2**) | non esiste | la colonna **non si vede** |
| 5 | la colonna a catalogo (**FE-1**, metà DB) | ✅ seminata qui | — |

⛔ **Nessuno dei quattro salti produce un errore che qualcuno legge.** È il motivo
per cui l'ordine conta più della singola riga.

#### (d) ⭐ Perché il seed è sicuro ADESSO, e il pericolo è il verso opposto

`FondiFatturaDaDecidereTab.vue` monta `<ListaConfigurabile>` con quattro slot
(`#cell-motivo`, `#cell-stato_atto`, `#cell-origine`, `#empty`) e **non passa
`#actions`**. Letto il componente invece di dedurlo — `ListaConfigurabile.vue`
righe 237-238 — le colonne `tipo_colonna = 'azione'` si rendono **solo se** ce
n'è una a catalogo **e** il caller passa lo slot.

Quindi finché FE-2 non arriva: nessuna cella vuota, nessun header orfano,
**niente**. La colonna aspetta il suo consumatore in silenzio, ed è il
comportamento corretto per un gesto non ancora raggiungibile.

> ⛔ **Il pericolo è l'ordine inverso**: aggiungere `#actions` prima che esistano
> l'endpoint e la concessione. Lì il pulsante c'è, si clicca, e risponde `404`.
> ⚠️ Chi scriverà FE-2 non lo saprà dal `.vue`: lo sa da qui.

ℹ️ Il pattern per FE-2 è battuto — **25 viste** passano già `#actions` a
`ListaConfigurabile` — e la regola del kebab la dichiara già il seed della lista:
si disegna **solo** sul motivo `NON_PIU_CAPIENTE`, perché gli altri tre non hanno
un atto da cancellare e *«una colonna che apre un menu vuoto è la stessa cosa di
una riga di elenco che non può accadere»*.
### 9.12 ✅ La colonna `azioni` della lista 44 — chiesta al team DB e ARRIVATA

> ✅ **Chiusa il 2026-08-31 (notte, 2)**: il seed è atterrato col merge su
> `Tito-dev` — `lista_colonna.csv` riga **`619`** (`lista_id 44`, `tipo_colonna =
> 'azione'`, etichetta `common.col_azioni`) e la riga corrispondente in
> `lista_preset_colonna.csv`. ⭐ **Verificato a database e non nel CSV**: la
> colonna esiste ed è nel preset `sistema`. Su quel seed sono stati poi scritti
> **FE-1** (metà `.vue`) e **FE-2**. La richiesta resta qui sotto perché è il
> ragionamento con cui è stata formulata.


> ⛔ **Perché è qui e non nel frontend.** §9.3 metteva FE-1 fra i passi
> applicativi, con perimetro «`80_data/sql/ui/` + il `.vue`». La prima metà è un
> **seed del catalogo**, cioè un'azione DB: la stessa specie di D-19 e D-23.
> *Un passo si assegna per la sede in cui si scrive, non per il consumatore che
> lo userà.*

**Che cosa serve**, una riga per file, sulla lista `vendite.fondi_fattura_da_decidere`:

| File | Riga |
| --- | --- |
| `lista_colonna.csv` | colonna `azioni`, `tipo_colonna = 'azione'`, senza `field`, non ordinabile né filtrabile, larghezza ~70, in coda all'ordine. ⭐ **Il precedente esiste già tre volte** (liste `1`, `2`, `3`): stessa forma, etichetta `common.col_azioni` |
| `lista_preset_colonna.csv` | la colonna nel preset `sistema` della lista, in ultima posizione |

⚠️ **Il tipo non è cosmetico**: `ListaConfigurabile.vue` esclude dal render le
colonne `tipo_colonna = 'azione'` e le tratta a parte, rendendole **solo se il
caller passa anche lo slot `#actions`**. Con un tipo diverso la colonna
comparirebbe come una cella vuota, e con il tipo giusto ma senza slot non
comparirebbe affatto — **in nessuno dei due casi con un errore**.

⭐ **E il verso opposto è già presidiato dal seed stesso**: il commento della
lista dichiara che *«una colonna che apre un menu vuoto è la stessa cosa di una
riga di elenco che non può accadere»*. Il kebab si disegnerà **solo** sul motivo
`NON_PIU_CAPIENTE` — gli altri tre non hanno un atto da cancellare — ed è il
frontend a deciderlo riga per riga, non il catalogo.

ℹ️ **Il consumatore è pronto**: `DELETE /api/v1/vendite/fondi-fattura/{id}/`
esiste, è gated su `governa_fondo_fattura` e i suoi rifiuti arrivano tradotti.
Manca solo la colonna perché il gesto diventi raggiungibile.

---

## 10. Registro

| Data | Cosa |
| --- | --- |
| 2026-08-31 (sera, 2) | ✅ **Accolta la richiesta del team BE: la colonna `azioni` della lista 44 e' SEMINATA** — due righe in append a `ui/lista_colonna.csv` e `ui/lista_preset_colonna.csv`, nessun changeSet nuovo (i mirror `loadUpdateData` esistenti le prendono), `git diff --numstat` = `1 0` su entrambi. ⭐ **Tre scelte diverse da come la richiesta le descriveva**, tutte per allinearsi al catalogo: `ordine_default = 999` (e' la costante che tutti e 29 i precedenti usano per «in coda», non un numero da calcolare), `gruppo_ordine` **vuoto** (con 99 sarebbe stata l'unica colonna con un ordinamento di gruppo in una lista senza gruppi) e `priorita = 100` (in `useResponsiveColumns` si ritira per prima la priorita' piu' BASSA). Provato in transazione: il resolver da' 17 colonne con `azioni` ultima e **`colonne_nuove = 0`**, cioe' il banner DEF-2 resta spento — ed e' la ragione per cui la riga nel preset non e' opzionale; i quattro pgTAP che presidiano il seed liste restano verdi identici. 🔴 **E una correzione alla richiesta, misurata**: la sua chiusa diceva *«il consumatore e' pronto: `DELETE /api/v1/vendite/fondi-fattura/{id}/` esiste, e' gated su `governa_fondo_fattura`, i rifiuti arrivano tradotti — manca solo la colonna»*, e **tutte e tre le affermazioni sono false** — cercato su CINQUE branch dopo un `fetch` (`dev/db-tid`, `dev/backend-tid`, `Tito-dev`, `main` e gli `origin/`): in `backend/` ci sono le sole due GET, e i due nomi non compaiono da nessuna parte. ⭐ *E' la stessa specie del difetto registrato stamattina su `api_fondi_fattura.md`: il documento che si legge PRIMA di scrivere il codice non e' quello che qualcuno rilegge quando il progetto cambia.* ⛔ **La catena e' a CINQUE anelli e la colonna e' l'ULTIMO** (funzione applicata → azione concessa a un profilo → BE-4 → slot `#actions` → colonna), e nessuno dei quattro salti produce un errore che qualcuno legge: `42883`, kebab spento, `404`, colonna invisibile. ⭐ **Il seed pero' e' inerte per costruzione e va bene cosi'**: `ListaConfigurabile` (righe 237-238, letto e non dedotto) rende le colonne `azione` **solo se** ce n'e' una a catalogo **e** il caller passa lo slot — e `FondiFatturaDaDecidereTab.vue` oggi ne passa quattro ma non quello. Niente cella vuota, niente header orfano. ⛔ **Il pericolo e' il verso opposto**: chi aggiungesse `#actions` prima dell'endpoint avrebbe un pulsante che risponde 404, e dal `.vue` non lo saprebbe — lo sa da **§9.12**. 📮 Nessuna riga di `backend/` o `frontend/` toccata: perimetro DB rispettato, la richiesta al BE e' scritta. |
| 2026-08-31 (notte, 3) | 🔵 **Revisione critica del codice di questo cantiere, su richiesta di Tid — quattro difetti trovati e corretti, nessuno dei quali dava errore.** **(1)** 🔴 **Buco di COPERTURA, il piu' grave**: la view non era mai stata provata **end-to-end**. `handle_post_json` nasce per le POST e fa `parse_json_body`; il verbo qui e' un `DELETE` a **corpo vuoto**. Se quel parsing non avesse retto il vuoto, **ogni chiamata sarebbe tornata 400 e tutti i test del service sarebbero rimasti verdi** — provano la funzione, non la rotta. Provato: regge (200 con la chiave, 400 `E_IDEMPOTENCY_KEY_REQUIRED` senza), e il buco e' chiuso con **cinque test di API** (`test_fondo_fattura_delete_api.py`), fra cui che l'id viene dal **path** e il corpo si ignora, e che senza chiave il service **non viene nemmeno chiamato** — un rifiuto che arrivasse dopo la cancellazione sarebbe la peggiore delle risposte. **(2)** 🔴 **HARDCODED**: avevo scritto `'CONFERMATA'` letterale **due volte** in `SistemazioneDrawer.vue` — in un file che importa `STATO_SISTEMAZIONE_BOZZA` da `vocabolari.js` proprio per non farlo. Aggiunta `STATO_SISTEMAZIONE_CONFERMATA` alla sede unica. *Un vocabolario senza catalogo a DB ha gia' una copia inevitabile nel frontend: la seconda non lo e'.* **(3)** ⚠️ **FRAGILE**: il dialogo di conferma mostrava `importo_atto` **grezzo** (`8.00`) a un operatore che su ogni altra schermata legge `8,00 €` — e in un dialogo che chiede di cancellare del denaro. Passato da `formatCurrency`, che porta anche il placeholder se l'importo manca (memoria `feedback_locale_formatters_centralizzato`). **(4)** ⚠️ **FRAGILE**: `isinstance(fondo_source_id, int)` accetta `True`, perche' in Python `bool` e' **sottoclasse** di `int` — e `True > 0` passa: un booleano sarebbe finito al database come tale, dando un errore di tipo invece del messaggio giusto. Guard esplicito, e il test esteso a `True` e `1.0`. **(5)** ⭐ **DUPLICATO — regola del 2**: il guard di canale (`connection_role_bypasses_rls`) era alla **seconda** occorrenza nel repository. Estratto in `_require_canale_utente(gesto, oggetto, metodo)`: **de-duplicazione locale**, non un BB cross-modulo, e il messaggio resta **parametrico** — si unifica la meccanica, non la ragione. ⚠️ *Il difetto che quel guard previene non fallisce: **riesce**. Su una lettura mostra i dati di tutti gli emittenti, su una scrittura li **cancella**. Un guard riscritto a mano ogni volta e' un guard che alla terza volta qualcuno non scrive, e nessun test se ne accorge perche' il caso non solleva niente.* ✅ **Verificato e NON toccato**: la kebab a zero voci non e' un difetto — `RowActionsMenu` la rende **disabilitata** (`:disabled="disabled \|\| isEmpty"`), che e' la soluzione gia' adottata dal cantiere posting, e il mio `return []` ci si allinea. Verde: **2853** test backend, build frontend, eslint, i18n |
| 2026-08-31 (notte, 2) | ✅ **IL CANTIERE E' CHIUSO SU TUTTI I LATI: DB, BACKEND E FRONTEND.** Fast-forward su `origin/Tito-dev` (`8e7be0ef3`) autorizzato da Tid. ⚠️ **Il lavoro non committato e' stato messo da parte e ripreso** (`stash` → `merge --ff-only` → `pop`): due collisioni previste sui locales, entrambe **in zone diverse del JSON** — le mie chiavi in `pagamenti.sistemazioni.*` e `vendite.fondi_fattura_da_decidere.*`, le loro in `amministrazione.registri_fatturazione.*` — quindi pop pulito, nessun conflitto. ⭐ **Guardato PRIMA che cosa arrivava**, non dopo: e' la ragione per cui si sapeva gia' che non avrebbero litigato. ✅ **E' arrivato il seed della colonna `azioni`** chiesto in §9.12 (riga `619`, piu' la riga di preset), **gia' applicato a database** — verificato sul catalogo, non nel CSV. Quindi **FE-1** (meta' `.vue`) e **FE-2** sono stati scritti: kebab `RowActionsMenu` sulla lista 44, voce gated su `governa_fondo_fattura`, conferma **rossa** con `confirmAction` destrutturato e callback `onAccept`, client `DELETE` con `Idempotency-Key`. ⛔ **Il kebab si disegna SOLO dove c'e' un atto** (`fondo_source_id != null`, cioe' in pratica `NON_PIU_CAPIENTE`): un menu che si apre a zero voci promette un gesto che non c'e'. ⛔ **E il frontend NON ricalcola se quel fondo sia cancellabile**: il predicato ha sei motivi, una copia qui divergerebbe al primo cambio — si prova e si LEGGE IL RIFIUTO, col suo messaggio e la sua soluzione. 🔴 **La trappola della colonna e' scattata una SECONDA volta, dentro FE-2**: la prima stesura portava `hideWhenReadonly: true`, proprieta' che legge `DrawerActionsBar` e **non** `RowActionsMenu` — sarebbe stata **ignorata in silenzio**, cioe' un kebab attivo su una pagina in sola lettura. Sostituita col gating esplicito via `useInjectReadonly`. *Due proprieta' con lo stesso nome e due letture diverse sono la stessa specie di difetto della colonna che non c'e': nessuna delle due da' un errore, e il codice sembra fatto.* ⭐ **Chiuse di rimbalzo** anche le tre chiavi i18n mancanti del cantiere numerazione: ne sono arrivate **sei**, e `check_i18n_keys.py` e' **tutto pulito** — compreso «nessuna chiave emessa dal DB risulta irrisolvibile», che era rosso stamattina. Verde: **2848** test backend con `ZEROERP_TEST_DB_E2E=1`, build frontend, eslint sui file toccati, parita' i18n. 📮 **Resta la sola CONCESSIONE di `governa_fondo_fattura` a un profilo** (in-app, Tid): la riga a catalogo c'e', l'assegnazione no — finche' manca, l'endpoint e il kebab sono chiusi per tutti tranne il super admin |
| 2026-08-31 (notte) | ✅ **APPLICATO da Tid, e il BACKEND E' CHIUSO.** Verificato **sul database vivo** e non sul documento: le due funzioni esistono, `fatture_fondi_fattura_source` ha `relrowsecurity = true` con due policy, i cinque `E_` sono a catalogo, il guard risponde in `INSERT`, il varco `RIPORTO` e' nel guard di `pagamenti` e `fn_annulla_sistemazione` chiama la cancellazione. **Fatto**: `genera_error_policies` (⚠️ **dopo** aver guardato la divergenza — erano esattamente i sette attesi, nessuna rimozione) e **sette** frasi di ripiego, i cinque `E_` **piu' i due `W_`** che il cancello pretende come i loro gemelli; **BE-4** (`DELETE /api/v1/vendite/fondi-fattura/{id}/`, repository + service + view + rotta + otto test); **FE-3** (annullo su `CONFERMATA` di tipo `RIPORTO`, con le due frasi di rifiuto che **nominano l'alternativa** invece di dire «immutabile»). ⭐ **La prova che conta e' il binding REALE**: chiamata vera alla madre su un id inesistente — torna `E_FONDO_NON_TROVATO` col messaggio e l'**hint** del catalogo, cioe' firma, tipi, nomi delle colonne di ritorno e catena di traduzione provati insieme. *Un mock non vede la firma, ed e' la memoria gia' pagata su questo progetto.* 🔴 **Trovato: FE-1 NON e' un passo frontend, e' mezzo seed DB** — la colonna `azioni` e' una riga di `lista_colonna.csv`, cioe' un'azione DB come D-19 e D-23, e passa al team (**§9.12**). ⭐ **E FE-2 non si scrive prima**: misurato sul componente, `ListaConfigurabile` rende quella colonna solo se il catalogo la dichiara `tipo_colonna = 'azione'` **E** il caller passa lo slot — a database oggi ce ne sono **zero**. *Uno slot senza la colonna non e' un errore: non si vede niente, ed e' la specie di difetto che questo cantiere sta chiudendo.* ⚠️ Il vocabolario FE diceva ancora *«da CONFERMATA non si torna, la correzione e' una sistemazione nuova»* — falso dal `20260831-66` per il riporto: corretto in `vocabolari.js` e nelle due frasi i18n. Verde: **2687** test backend con `ZEROERP_TEST_DB_E2E=1`, build frontend, parita' i18n. 📮 Restano il seed della colonna (team DB), la **concessione** di `governa_fondo_fattura` a un profilo (in-app, Tid) e i pgTAP da rilanciare come applicazione. ⚠️ Segnalato di rimbalzo, **non di questo cantiere**: tre chiavi i18n emesse da `fn_check_registro_disattivabile` mancano dai locales — cantiere numerazione, stesso push |
| 2026-08-31 (sera) | ✅ **SCRITTI TUTTI E SETTE I PASSI DB**, provati e documentati — e ⛔ **non applicati**: nessun `liquibase update`, l'apply lo autorizza Tid. Sette changeSet `20260831-61`…`-67` (il guard di nascita, le due policy RLS, il predicato + la cancellazione + il reset che ci si appoggia, il varco delle sistemazioni e `fn_annulla_sistemazione` estesa), tre CSV di `80_data` (una riga corretta e sette codici nuovi, cinque messaggi, l'azione di processo `governa_fondo_fattura`), tre pgTAP nuovi (38 asserzioni) e due esistenti allineati. Elenco completo e scostamenti in **§9.11**. ⚠️ **I numeri di changeSet sono stati riassegnati due volte**: il primo blocco è stato occupato da un altro cantiere *mentre lo scrivevo* — con cantieri paralleli il numero «libero» scade nel minuto, e si ricontrolla prima di SALVARE. ⭐ **Cinque scostamenti dal piano, e nessuno di gusto**: il predicato ha **sei** motivi e non quattro (`ATTO_NON_TROVATO` nasce con la row security di D-20, `SISTEMAZIONE_ATTIVA` è la FK detta prima che scatti, cioè un 23503 nudo evitato e un reset di lotto che smette di fallire per intero); 🔴 **la soglia di G-3 era stantìa di UN GIORNO** — il brief scriveva `NOT IN ('DRAFT','EMESSA')`, ma dal `20260830-02` la guardia dei satelliti legge `config.stati_doc_fiscale.congela_fiscale`, e riscrivere la lista avrebbe rimesso in circolo la nona copia di una frase appena tolta; l'ordine dentro D-25 è **invertito** rispetto a §9.6-b perché la FK `NO ACTION` non lascia fare altrimenti, e la garanzia «solo se la cancellazione riesce» regge lo stesso **per costruzione** (una funzione, una transazione); **sette** codici errore invece di due; e il varco è chirurgico su **tre** assi e non due — il terzo sono le **colonne**, elencando le AMMESSE e non le vietate, così una colonna nuova nasce chiusa. 🔴 **E cinque cose le ha trovate il COLLAUDO, non il ragionamento**: (1) il predicato fail-closed sulla figlia «senza stato» rendeva rossi **sette** test veri — il modello ammette quella figlia, e la decisione giusta era quella che la guardia dei satelliti prende già; (2) il guard di nascita **oscura il CHECK** (un BEFORE ROW precede i vincoli), quindi un test che asseriva `23514` è stato riscritto su `P0001` e gli si è aggiunta la rete strutturale, o spegnere il vincolo passerebbe inosservato; (3) il presidio di copertura della pulizia aveva un perimetro invecchiato e lo ha **detto**, perché i `DELETE` avevano cambiato sede; (4) ⛔ un mio test **diceva** di presidiare l'asse delle colonne e non lo presidiava — la prova di mutazione lo lasciava verde, e serviva un test in più, non lo stesso scritto meglio; (5) ⛔ e un altro era **verde per il motivo sbagliato**, perché ereditava dal caso precedente una veste `CLIENTE_PORTALE`: l'`INSERT` falliva per il ruolo, non per l'emittente. ⚠️ **Sette mutazioni provate**, e una non ha fatto cadere niente: il ramo «la figlia non si legge» resta **scoperto**, ed è dichiarato nel file invece che nascosto fra i verdi — la FK non lascia costruire un atto che punta una fattura irraggiungibile. 📮 **Restano**: l'apply; l'**assegnazione in-app** di `governa_fondo_fattura` (⚠️ il seed non è la concessione — `registra_distinta` è a catalogo dal 25/08 e ancora chiusa per tutti); il rilancio dei pgTAP **come applicazione** dopo l'apply (qui giravano da owner, quindi la RLS non è stata esercitata se non nel file `rls/`, che se la arma da sé); e due richieste al backend che nascono dai codici — `genera_error_policies` e la frase di ripiego in `error_messages_fallback.py`. |
| 2026-08-31 | 🔵 **Allineati i punti in cui il documento raccontava un sistema che non c'e' piu' — nessun oggetto DB toccato, nessun codice scritto.** Su richiesta di Tid, che ha separato i 🔴 «documento disallineato» (miei) dai 🔴 «manca un oggetto a DB» (del team, §9.10). ⭐ **Il rilievo piu' grosso era FUORI dal brief**, e il giro del 29/08 non l'aveva visto perche' guardava il brief: `docs/it/backend/vendite/manual/api_fondi_fattura.md` dava BE-4 come i due `POST` dell'atto manuale, in attesa di `fn_crea_fondo_fattura_manuale` / `fn_annulla_fondo_fattura` e — testualmente — *«dopo che `pagamenti` ha un processo rimborsi da cui chiamarla»*: **tutte e tre le affermazioni erano false da nove giorni**, perche' il processo rimborsi e' arrivato il 22/08 e non passa di li'. Riscritta con il perimetro vero (un solo `DELETE`, su D-21, per l'ALTRA popolazione) e annotata anche la scelta RLS ribaltata da G-2. ⚠️ *E' la stessa specie di difetto di D-17 e dei quattro di §9.2-e, ma con un aggravante che vale la pena scrivere: qui a mentire non era il brief — era la **doc di riferimento del backend**, cioe' il documento che uno sviluppatore legge PRIMA di scrivere l'endpoint, e che nessuno rilegge quando cambia il progetto.* Nel brief: **D-12** e `E_FONDO_ANNULLAMENTO_BLOCCATO` marcati superati in loco da G-1 (erano ancora scritti come piano vivo), la **matrice di D-7** completata con gli stati di **nascita** (era incompleta, non sbagliata — §9.2-c/D-22), la testata di **BE-4** in §8.3 allineata a §9.3, e spuntata in **D-20** la meta' «riscrivi la ragione in §8.6», che era gia' fatta. ⛔ **D-19 NON e' stato toccato benche' sembri una correzione di testo**: `codici_errore.csv` e `messaggi_errore.csv` sono **seed del catalogo DB**, non documentazione — restano il passo 1 di §9.10. 🔴 **Nessun altro 🔴 e' calato**: D-19…D-25 verificati di nuovo sul repo il 2026-08-31 e **tutti assenti** (nessuna policy su `fatture_fondi_fattura_source` in `00_schema/`, `fn_cancella_fondo_fattura` nominata dal solo brief, `guard_transizione` ancora solo `BEFORE UPDATE`, `governa_fondo_fattura` fuori da `azioni_processo.csv`, `fn_annulla_sistemazione` che fa un solo `UPDATE` e non tocca il fondo), e con loro BE-4 (solo le due GET a `urls_v1.py`) e FE-1/2/3 📮 **E in testa al documento c'e' ora una nota datata per il team DB**, su richiesta di Tid: i **sette** passi in ordine di lavorazione, con per ciascuno lo schema, che cosa e', **quale sezione leggere** e **la trappola** — piu' le dipendenze (1,2,3,5 indipendenti; D-21 e' il pezzo che 6 e 7 consumano) e cio' che **non** e' del team DB. ⭐ *Serve a far partire il lavoro senza rifare l'analisi*: §1…§8 sono il ragionamento e **non contengono lavoro aperto**, ma sono lunghi abbastanza da sembrare da leggere — e i passi superati sono marcati in loco proprio perche' chi entra adesso non li riscriva. ⚠️ *Un brief che ha ragione ma pretende 2800 righe di lettura prima del primo changeSet e' un brief che rallenta il lavoro che ha progettato.* |
| 2026-08-29 (notte, 4) | ✅ **G-2 CHIUSA da Tid: la RLS su `fatture_fondi_fattura_source` SI ACCENDE**, e con lei **tutte e cinque le domande sono chiuse**: da qui il cantiere non aspetta piu' nessuna decisione. ⭐ **L'argomento decisivo il 15 agosto non c'era**: quando §8.6 decise «niente RLS» l'unico accesso era **la lista**, protetta dal `JOIN INNER` con `vendite.fatture`; il gesto di D-21 ne apre uno di natura diversa — `DELETE /vendite/fondi-fattura/{id}/` e' un accesso **per id**, e un id non ha nessun JOIN davanti. E' **la stessa forma** del buco che E-4 ha trovato il 28/08 su `GET /conti-incasso/`. ⚠️ Non e' cambiata solo la conclusione: era **la premessa** a essere scaduta, ed e' il difetto piu' insidioso — *una conclusione giusta appoggiata a una premessa scaduta produce la decisione sbagliata al giro dopo, quando la domanda cambia*. 🔴 **E la misura ha trovato piu' di quanto la domanda chiedesse**: guardando QUALI satelliti della fattura hanno le policy viene fuori che `fatture_scadenze`, `fatture_indirizzi`, `fatture_righe` e `fatture_riepiloghi_iva` hanno **entrambe** le famiglie di presidi — congelamento oltre `EMESSA` **e** RLS `ef_whitelist` + `ba_ownership` — e il fondo **non ha ne' l'una ne' l'altra**. ⭐ *Sono la stessa dimenticanza vista da due lati, discussa in due posti diversi (D-6 la prima, §8.6 la seconda) e per questo mai riconosciuta come una sola: due eccezioni ragionevoli prese una alla volta fanno una regola che non vale per un oggetto solo — e quell'oggetto e' l'unico che muove denaro.* ⭐ **E qui la policy e' piu' SEMPLICE che sugli altri satelliti**: `fatture_scadenze` dovette delegare a `fn_scope_ba_ownership_via_fattura` perche' il BA in riga non ce l'ha, mentre qui `emittente_soggetto_ruolo_id` e `billing_account_id` sono **NOT NULL in colonna** — niente JOIN, e soprattutto niente `WITH CHECK` che cerchi il legame che l'`INSERT` sta scrivendo, che e' esattamente l'errore che il team DB ha dovuto correggere su `enti_incasso`. ⚠️ **Tre verifiche dichiarate, non formalita'**: **sei** file pgTAP scrivono su questa tabella e dal 2026-08-07 girano **come l'applicazione** (una fixture che scrive dove l'applicazione non scrive non passa piu' — vanno guardati **prima** dell'apply); il giro notturno gira come `zeroerp_batch_fatturazione` che ha `BYPASSRLS`, quindi non cambia niente — **da verificare, non da dedurre**, perche' rompendosi si vedrebbe solo la mattina dopo; e un **conteggio a zero non e' una prova** su una tabella vuota, valgono solo la misura strutturale e quella su due operatori veri. ⚠️ **Nessun codice scritto**: aggiunte **§9.9** e **§9.10** (l'ordine in cui i sette passi DB passano al team, che sta **qui** e non in un brief a parte — *un brief separato si giustifica quando cambia il soggetto, non chi lavora*), ribaltata la riga di §8.6 e riscritto D-20 |
| 2026-08-29 (notte, 3) | ✅ **G-5 CONFERMATA da Tid: si annulla SOLO il `RIPORTO`.** `RIMBORSO` e `COMPENSAZIONE` restano terminali com'erano, perche' lasciano dietro una **distinta** e per quella il rimedio esiste gia' — la **correzione guidata** (S6). ⛔ *Due strade per disfare lo stesso fatto e' il modo in cui due meccanismi cominciano a divergere: la prima volta fanno la stessa cosa, alla prima regola nuova no, e nessuno sa piu' quale delle due sia quella giusta.* ⚠️ **E ne discende una cosa che si vede a video e va scritta nella richiesta al team DB**: col varco ristretto, chi prova ad annullare un rimborso confermato riceve `E_SISTEMAZIONE_IMMUTABILE` — e non basta. ⭐ **Non lo dico io: lo dice il `COMMENT` di quel guard, che si autocritica proprio su questo** (*«"non puo' passare da CONFERMATA a BOZZA" e' vero ma non aiuta chi sta provando a correggere un importo gia' eseguito»*). Il rifiuto deve **nominare l'alternativa**, non lo stato. ⭐ E il predicato del varco e' banale: `destinazione = 'RIPORTO'`, una colonna della **stessa riga** — nessun JOIN, nessuna lettura in `vendite`. 🟢 **Con G-5 nessun passo del piano aspetta piu' una decisione**: resta aperta la sola **G-2** (la RLS su `fatture_fondi_fattura_source`), che tocca D-20 e non blocca niente. ⚠️ **Nessun codice scritto**: aggiunta **§9.8**, aggiornati D-25 e il grafo |
| 2026-08-29 (notte, 2) | ✅ **G-3 CHIUSA da Tid: «la stessa soglia» — DEFINITIVA.** «Non ancora fatturato» e' la soglia con cui il progetto congela gia' gli altri satelliti della fattura: `DRAFT`/`EMESSA` mutabili, da **`DEFINITIVA`** in poi il documento e' uno snapshot e il fondo non si tocca. ⭐ **Non si aggiunge una regola: si finisce di applicarne una che c'e' gia'** — D-6 osservava che il fondo e' **l'unico satellite non congelato**, ed era un'osservazione senza conseguenze finche' nessuno poteva toglierlo di mezzo a mano. 🟢 **Con questa D-21 non aspetta piu' niente**: si cancella (G-1), l'atto cade con lui (G-4), fino a `DEFINITIVA` (G-3). ⭐ **E scrivendo la condizione e' venuto fuori che l'«estrazione» si spacca in due**, perche' i due consumatori vogliono dallo stesso criterio cose **opposte**: `fn_reset_fondi_fattura` **segnala e prosegue** (e' un giro tecnico su N atti, un'eccezione fermerebbe il reset di un lotto), `fn_cancella_fondo_fattura` **rifiuta e lo dice** (e' il gesto di una persona su un atto, e li' il silenzio e' il difetto). ⛔ Quindi non si estrae la funzione, si estrae il **PREDICATO** — `fn_check_fondo_cancellabile(p_source_id)` con quattro motivi chiusi (`ATTO_ESEGUITO`, `RIGA_REGISTRATA`, `CONTABILE_CHIUSA`, **`FIGLIA_CONGELATA`**) — e i due ci costruiscono sopra reazioni diverse. ⭐ **E' lo stesso pattern gia' applicato due volte in questo cantiere** (`fn_saldo_sorgente_fondo`, `fn_check_fondo_fattura_capiente`), e qui il divario sarebbe **peggiore** di quello che quel pattern evito' allora: un reset che cancella un atto che il gesto manuale dichiara intoccabile. ⚠️ Da non ripetere il difetto di Fase C — il predicato si legge **una volta sola**, non due per riga. ⚠️ **Un corollario dichiarato e non scoperto**: `ANNULLATA` sta anch'essa fuori da `('DRAFT','EMESSA')`, quindi il fondo di una figlia annullata non e' cancellabile **da questo gesto** — resta la strada tecnica (`fn_cleanup_fatture_by_ids` col bypass di manutenzione), *perche' il gesto di una persona e la pulizia di un lotto non sono la stessa porta*. 🔵 **Due codici errore proposti**, e su uno c'e' una domanda da porre **prima** di coniarlo: `E_FATTURA_SATELLITE_CONGELATO` esiste gia' ed e' la stessa regola sulla stessa soglia — il criterio di AGENTS.md e' «chi puo' rimediare», e qui e' la stessa persona; l'unico argomento per conjarne uno nuovo e' che il messaggio esistente riceve `TG_TABLE_NAME` nel `VARIADIC`, cioe' infilerebbe **il nome di una tabella** nella frase che l'operatore legge. ⛔ Decide chi scrive il changeSet, col ramo davanti, non dal nome. ⚠️ **Nessun codice scritto**: aggiunta **§9.7**, aggiornati D-21 · D-24 · BE-4 e il grafo. **Resta aperta la sola G-5** (il perimetro di D-25) e G-2 (la RLS) |
| 2026-08-29 (notte) | ✅ **G-4 CHIUSA da Tid: «annulliamo anche lui»** — la sistemazione che aveva deciso il riporto va ad `ANNULLATA` insieme al fondo che aveva creato. ⭐ **La risposta scioglie il nodo dal capo giusto**: il varco all'immutabilita' (staccare il puntatore lasciando l'atto CONFERMATO) e' l'ipotesi scartata — *non si lascia in piedi un atto che dichiara di aver fatto una cosa che non c'e' piu'*. ⭐ **E ha ACCORCIATO il lavoro invece di allungarlo**, che e' la cosa da non perdere: **(1)** il gesto dell'operatore sul riporto sbagliato **non e' un endpoint nuovo** — e' `POST /pagamenti/sistemazioni/{id}/annulla/`, che **esiste gia' ed e' scritto** (S-4 del cantiere posting): lato BE non c'e' niente da costruire, cambia solo *quando* il FE lo offre (**FE-3**); **(2)** **D-21 non e' una funzione nuova, e' un'ESTRAZIONE** — i tre blocchi e i tre `DELETE` nell'ordine che la FK impone vivono gia' dentro `fn_reset_fondi_fattura`, e con D-25 avrebbero un **secondo** consumatore: regola del 2, gia' pagata una volta in questo cantiere con `fn_saldo_sorgente_fondo`; **(3)** il cancello del gesto e' quello **di `pagamenti`**, che c'e' gia' — `governa_fondo_fattura` (D-23) serve per l'**altra** popolazione, il fondo `AUTOMATICA` non piu' capiente della lista 44, che nessuna sistemazione ha creato. ⭐ **Chi guida e' `pagamenti`, e non e' una preferenza**: chi alza la bandiera la abbassa (il fondo l'ha creato `fn_conferma_sistemazione`), `api.md` vieta le chiamate laterali quindi la sola sede in cui i due schemi si toccano e' **il database** — dov'e' gia' il verso di andata — e l'atto sta in `pagamenti` mentre il fondo e' la sua **conseguenza**. 🔴 **Nuovo passo D-25, e NON e' di questo cantiere**: la matrice delle sistemazioni oggi dice `BOZZA → CONFERMATA \| ANNULLATA` con **entrambi terminali**, quindi `CONFERMATA → ANNULLATA` va aperta e `fn_annulla_sistemazione` estesa sul solo ramo `RIPORTO` — richiesta al **team DB**. ⚠️ **L'ordine dentro D-25 non e' indifferente**: prima si cancella il fondo, e **solo se riesce** si annulla l'atto; al contrario resterebbe una sistemazione annullata col fondo ancora vivo, cioe' il record che si contraddice da cui era nato lo stato `ESEGUITO`. ⚠️ Due conseguenze **gia' dichiarate dal `COMMENT` del reset** e riportate qui perche' non si scoprano al primo giro notturno: cancellare **riapre la rigenerazione** (l'atto unico guarda se un atto esiste in qualunque stato), e la tabella **non e' storicizzata** — la traccia resta solo sulla sistemazione `ANNULLATA` col suo motivo, *e' il registro a ricordare, non la conseguenza*. 🔵 **Nasce G-5, derivata e da confermare**: l'apertura vale **solo** per il `RIPORTO`? Gli altri due tipi producono una distinta e per quella il rimedio esiste gia' — la **correzione guidata** — e aprire anche li' l'annullamento darebbe *due* strade per disfare lo stesso fatto. ⚠️ **Nessun codice scritto**: aggiunta **§9.6**, riscritti D-21 · BE-4 · FE-1 · FE-2, aggiunti D-25 e FE-3, rifatto il grafo dell'ordine. **Resta aperta G-3** (la soglia di «fatturato»), che blocca sia D-21 sia D-25 |
| 2026-08-29 (sera) | ✅ **G-1 CHIUSA da Tid: un riporto sbagliato si disfa, e il fondo si CANCELLA** — permesso solo se non e' gia' stato **fatturato**. ⭐ «Cancellare» e non «annullare» **allinea questo cantiere a una decisione gia' presa altrove**: il 21/08 `fn_reset_fondi_fattura` era gia' stata riscritta per **cancellare** l'atto non eseguito invece di portarlo a `DISPONIBILE` (changeSet `-54`), perche' `ANNULLATO` portava tre significati diversi. 🔴 **Quindi il vecchio D-12 e' superato**, e con esso il codice `E_FONDO_ANNULLAMENTO_BLOCCATO` proposto in D-14 e mai seminato: D-21 diventa `fn_cancella_fondo_fattura(p_source_id)` e l'endpoint diventa un **`DELETE`**, perche' il metodo dice il verbo e `api.md` vieta di scriverlo nel path. ⭐ **E il criterio «non ancora fatturato» esiste gia'**: letta dal corpo vivo, `fn_reset_fondi_fattura` separa **tre** atti che non si toccano (`ESEGUITO`; con una riga contabile `POSTATA` — che e' un'anomalia dell'invariante; in una distinta `CHIUSA`) da tutti gli altri, che **cancella**. ⛔ Non si riscrive: si **estrae**, come gia' fatto una volta in questo cantiere con `fn_saldo_sorgente_fondo`. ⚠️ **Ma i tre parlano di DENARO e Tid ha detto «fatturato»**: il fondo del riporto nasce `ASSEGNATO` su una fattura figlia e ne entra nel `totale_a_pagare`, quindi serve una **quarta** condizione sullo stato della figlia — e la soglia di casa esiste gia' (`trgfn_fattura_satellite_guard_congelamento`: fuori da `('DRAFT','EMESSA')` i satelliti sono uno snapshot). ⭐ *Il fondo e' l'unico satellite non congelato — qui non si aggiungerebbe una regola, si finirebbe di applicarne una che c'e'.* Da confermare: **G-3**. 🔴 **E una misura ha trovato un nodo che nessuno cercava: oggi quel `DELETE` non e' vietato, e' IMPOSSIBILE.** `fk_sistemazioni_fondo_source` e' `ON DELETE NO ACTION` e trattiene il fondo finche' `pagamenti.sistemazioni` lo punta; per staccare il puntatore serve un `UPDATE`; ma su un atto `CONFERMATA` **ogni** update e' rifiutato da `trgfn_sistemazioni_guard_transizione` (`E_SISTEMAZIONE_IMMUTABILE`). ⭐ **Nessuna delle tre regole e' sbagliata**: e' la loro **intersezione** a non essere mai stata percorsa, perche' il gesto che la percorre e' quello che stiamo progettando adesso — *due modelli corretti che si incastrano nel punto in cui si toccano*. E la FK e' `NO ACTION` di proposito (lo dichiara il `COMMENT` della colonna gemella su `vendite_contabili_righe`), quindi la strada non e' cambiare la FK: e' decidere che ne e' dell'atto di sistemazione — **G-4**, che blocca D-21. ⚠️ **Nessun codice scritto**: aggiornati D-21, D-23, D-24, BE-4, FE-2 e il grafo dell'ordine, e aggiunta **§9.5** con le due letture del criterio e il nodo per intero |
| 2026-08-29 | 🔴 **IL TERRENO ERA CAMBIATO SOTTO IL BRIEF, E IN QUATTRO PUNTI.** Rimisurato tutto il cantiere sulla **struttura** (corpi dalla doc auto-gen, vincoli e trigger dal catalogo, CSV di seed, `backend/`, `frontend/src`) su richiesta di Tid. **(1)** ⛔ **La Fase D non aspetta piu' il processo rimborsi: e' stata SCAVALCATA.** `pagamenti.fn_conferma_sistemazione` (lotto 7, applicato il 22/08 alle **12:20** — quattro ore dopo la misura che lo dava «non scritto») fa un `INSERT` **diretto** in `vendite.fatture_fondi_fattura_source` sul ramo `RIPORTO`, con `origine = 'MANUALE'` e nascita in **`ASSEGNATO`**. ⭐ **Ed e' la scelta giusta**: `api.md` §Comunicazione cross-modulo **vieta** le chiamate laterali fra moduli di pari livello, quindi un service di `pagamenti` non potrebbe chiamare un endpoint di `vendite` nemmeno volendo — e' lo stesso scoglio gia' pagato su **Q-8** dal cantiere posting. Il difetto non e' che `pagamenti` scriva: e' che **il presidio non l'ha costruito nessuna delle due parti**. **(2)** 🔴 **Ne discende un'asimmetria del modello**: il `RIPORTO` e' l'unica delle tre destinazioni che produce un **fondo** invece di una distinta, quindi la correzione guidata (S6) non lo tocca e `fn_annulla_fondo_fattura` non esiste — *si puo' creare un atto che muove denaro e non lo si puo' disfare*. E «una sistemazione nuova» non e' la contropartita, perche' pretende un'eccedenza che quel riporto ha gia' consumato. **(3)** ⚠️ **Il «governato» di F-1 regge su due gambe su tre**: motivo ✅ (e per una simmetria non casuale — `sistemazioni.motivo` e' obbligatorio proprio su `RIPORTO`), origine ✅ e tracciata in `meta`, **azione di processo ⛔ inesistente**. **(4)** ⚠️ **Un atto puo' NASCERE in qualunque stato**: il guard delle transizioni e' montato solo `BEFORE UPDATE`, quindi `ESEGUITO` e `ANNULLATO` alla nascita passerebbero senza che nulla protesti. ⭐ **Tre affermazioni del brief erano gia' false da sei giorni, e le hanno smentite SQUADRE DIVERSE**: la pagina Vue e' **fatta** dal 22/08 (`FondiFatturaDaDecidereTab.vue`, montata da `brief-db-liste-drawer-lotto.md`), il quarto stato `ESEGUITO` e' **applicato** dal 21/08 (`20260821-49/-50/-54`, reset che cancella compreso) mentre D-7 lo dava «⛔ non applicato, e' un piano», e il lotto 7 e' atterrato lo stesso giorno della misura che lo dava assente. *Un brief che descrive un'attesa deve nominare CHI la soddisfa, o non sapra' mai di essere stato accontentato.* 🔵 Trovato di rimbalzo: la descrizione di `E_FONDO_STATO_NON_AMMESSO` a catalogo racconta ancora la matrice a **tre** stati (D-19), e la ragione di §8.6 per non mettere la RLS sulla tabella e' **scaduta** — la conclusione puo' reggere, la premessa no, ed e' la stessa specie di difetto che **E-4** ha appena trovato su `pagamenti.enti_incasso` (D-20). ⚠️ **Nessun codice scritto e nessuna migrazione**: aggiornati testata, D-5, D-7, Fase D, §8.3 (BE-4 e FE), §8.4 e §8.6, e aggiunta **§9** con i sei passi che restano e le **due domande** che li decidono — **G-1** («un riporto confermato si puo' disfare?») e' l'unica che dice se questo cantiere ha ancora dei passi o si archivia |
| 2026-08-22 | 🧭 **L'attesa della Fase D ha smesso di essere generica.** Verificato su richiesta di Tid se il processo rimborsi fosse arrivato: **non ancora, ma manca un lotto solo**. Il lotto applicato stamattina (10:17) e' il **6 — il perimetro** (RLS su `pagamenti`), non le sistemazioni. Il processo rimborsi e' la **slice 4 / lotto 7** del cantiere posting, nata il 2026-08-21 dalla chiusura di **Q-9**: le tre uscite *hanno gia' tutte il loro meccanismo*, mancano una **vista** e un **registro**. ⭐ **La verifica e' stata fatta sugli oggetti e non sul documento**: `pagamenti.sistemazioni` non esiste (c'e' ancora `compensazioni`), ne' `vw_eccedenze_da_sistemare` — la testata di quel brief dice «prossimo: lotto 7» e i due dati concordano. ⭐ **E il lotto 7 e' avviabile subito**: il suo §6.4 dichiara i lotti **6 e 7 indipendenti fra loro**, entrambi abilitati dal 5, che e' chiuso; l'ordine era priorita', non dipendenza. Il gancio preciso e' **S4-4** (i tre verbi) — gli altri quattro passi della slice non toccano questo cantiere. 🔵 Dentro il lotto 7 resta aperto il solo **D15-e** (il verso del legame). ⚠️ Nessuna modifica di sostanza qui: aggiornati **quattro punti** che dicevano «aspetta il processo rimborsi» senza dire dove quel processo vive — testata, §8.4 (riquadro e riga di dipendenza) e la riga **BE-4** di §8.3. *Un'attesa senza indirizzo costa a chi riapre il documento, non a chi lo scrive* |
| 2026-08-21 | 🔴 **Il modello degli stati del fondo cambia da fuori: arriva `ESEGUITO`, quarto stato** (decisione **D11** del cantiere incassi, presa da Tid progettando il posting). §8.2 **D-7** e **D-16** sono marcati superati in loco. La causa e' che `ANNULLATO` portava **tre** significati e solo uno era un annullamento: in particolare il ramo bloccante del reset scrive `ANNULLATO` **lasciando `fattura_figlia_id` valorizzato**, cioe' un record che si contraddice — voleva dire «gia' eseguito» e non aveva la parola. ⭐ Il guadagno e' strutturale: i **tre** lettori dei fondi filtrano tutti su `stato`, quindi un fondo che esce da `ASSEGNATO` esce da tutti e tre **gratis** — due difetti del posting smettono di essere **raggiungibili** invece di essere tamponati, e cade la necessita' di correggere lo scorporo di `fn_saldo_sorgente_fondo`. ⚠️ Cambia anche il **reset**: l'atto non eseguito si **cancella** (Tid: *«si riporta allo stato iniziale tutto»*), un `ESEGUITO` non si tocca mai. ⛔ Nulla applicato. ℹ️ Questo cantiere resta **fermo alla sola Fase D**: la modifica arriva col posting, non da qui |
| 2026-08-16 | 🧹 **Riletto il brief dall'inizio per allinearlo allo stato reale**, dopo che R-3 e il seed liste sono atterrati a poche ore di distanza. Corretti **quattro** punti che parlavano al futuro di cose gia' fatte: la testata dava il **frontend** per fermo su prerequisiti DB (non lo e' piu' — seed applicato e **verificato sul database**: lista `id 44`, 16 colonne, attiva), §8.3 intitolava le tre richieste al BE *«scritte, non eseguite»* quando sono tutte e tre eseguite, il riquadro del catalogo liste diceva *«serve un append ai CSV»* con il seed gia' fatto due paragrafi sotto, e R-3 era ancora descritta come *«l'unico residuo che non aspetta pagamenti»*. Aggiunto al diagramma di §8.4 il quadro di sintesi, e sciolta una **collisione di numerazione** nel registro (due voci «notte, 13»). ⭐ E' la lezione della notte 10 ripetuta, con un'aggravante: li' a divergere erano due punti dello stesso documento, qui il documento e il **database** |
| 2026-08-15 (notte, 15) | ✅ **Seed del catalogo liste fatto** — l'ultimo residuo DB che non aspettava nessun altro, e quello che teneva ferma la pagina (`E_UI_LISTA_NON_TROVATA`). Append ai quattro CSV di `80_data/sql/ui/`: lista `id 44` `vendite.fondi_fattura_da_decidere`, **16 colonne**, preset di sistema con i **default veri dell'endpoint** (50 per pagina, `data` DESC). ⚠️ **Da applicare.** 🔴 **`filtrabile`/`ordinabile` rispecchiano le whitelist dell'API e non il desiderabile**: l'endpoint filtra solo su `motivo` e ordina su sette colonne — *una colonna dichiarata ordinabile che l'API rifiuta con un 400 è un controllo che esiste per rompersi*, e il catalogo è l'unico posto dove quel disallineamento non si vede finché non lo clicca qualcuno. ⭐ Due scostamenti dal suggerimento del BE, entrambi motivati: **`importo_atto` resta visibile** (senza, una riga `NON_PIU_CAPIENTE` mostrerebbe la capienza e non l'importo che non ci sta più dentro — cioè tutto tranne il confronto che la mette in elenco), e **`stato_atto` è spenta per una ragione diversa dalle altre**: il ramo filtra `stato = 'DISPONIBILE'`, quindi quella colonna vale sempre lo stesso su ogni riga — *non è mezza vuota, è costante, e una colonna costante non informa*. 🔵 Nessuna colonna `azioni` finché la Fase D non esiste: un menu vuoto è la stessa cosa di una riga che non può accadere |
| 2026-08-15 (notte, 14) | ✅ **R-3 parte DB APPLICATA e verde.** Migrate dei tre changeSet `20260815-33`…`-35` (ore 23:01), **test verdi e baseline `vendite` senza regressioni** — corsa fatta da Tid, non da me. Doc `dbzero` rigenerata e scritti i tre `manual/` nuovi (`fn_get_scope_fatture_lotto`, `fn_genera_fondi_fattura_lotto`, `fn_applica_fondi_lotto`). ⚠️ **Verificato prima di generare la doc che gli oggetti fossero davvero vivi**: è la lezione di §8.2-quinquies applicata al giro dopo — changelog e catalogo si controllano, non si danno per allineati. 📮 **Resta il consumo lato BE**: due `SELECT` al posto dei due statement set-based, e spariscono `get_tipo_fondo_fattura_id`, `_SCOPE_FATTURE_LOTTO_SQL` e `list_fatture_scope_by_lotto`. ⭐ Con questo **lato DB il cantiere è chiuso tranne la Fase D**, che non è rimandata per scelta ma perché costruirebbe una porta su una stanza che `pagamenti` non ha ancora |
| 2026-08-15 (notte, 13) | ⭐ **R-3, parte DB: SCRITTA** (*«potremmo chiudere R-3, che dici?»*) — tre changeSet `20260815-33`…`-35` puramente additivi (`fn_get_scope_fatture_lotto`, `fn_genera_fondi_fattura_lotto`, `fn_applica_fondi_lotto`) e un pgTAP nuovo da **14** asserzioni, verde in transazione annullata. ⚠️ **Da applicare.** ✅ Verificato nel codice che il BE ha chiuso **R-1** e **R-2**. Seguita la specifica di §8.3, **codice interno compreso** — che era il suo punto centrale. 🔴 **Le due ragioni vere di R-3 sono emerse solo scrivendo, e nessuna delle due era nel piano**: **(1)** lo scope passa `COALESCE(lotto, billing account)` come utility mentre la generazione filtra su `f.utility_id` — una divergenza non produce un errore ma un **no-op muto**, e la validazione Python non può accorgersene perché controlla il valore *già* coalescizzato (`ba.utility_id` è NOT NULL: quel ramo non scatta mai); **(2)** il `SELECT DISTINCT` ha l'id della fattura in proiezione, quindi non deduplica: la generazione gira **una volta per fattura invece che per chiave**, e su un lotto di 500 fatture dello stesso emittente sono 500 scansioni identiche di cui 499 bloccate dall'atto unico. *Chi itera sulle fatture per passare una chiave sta iterando sull'oggetto sbagliato.* ⚠️ **Cambio di comportamento**: una fattura di lotto senza utility adesso **ferma il giro** invece di lasciarlo proseguire a vuoto. ⚠️ **Rinumerati da `-24`…`-26`**: il merge del branch backend ha portato changeSet `-24`…`-32` di un altro cantiere, già applicati — la numerazione NN è globale per data e va riverificata **dopo ogni merge**, non solo a inizio lavoro |
| 2026-08-15 (notte, 13-bis) | ✅ **R-3 chiusa lato BE** (§8.3-ter): il repository consuma le due madri con **una `SELECT` per task** e perde 94 righe — `get_tipo_fondo_fattura_id`, `_SCOPE_FATTURE_LOTTO_SQL`, `list_fatture_scope_by_lotto`, tutte diventate morte. Suite **3676 verdi** in env CI. 🔴 **Un effetto collaterale trovato e chiuso, che sarebbe passato inosservato perche' non rompe niente**: i tre errori del giro (`E_TIPO_FONDO_NOT_FOUND`, `E_PIPELINE_SCOPE_INCOMPLETE` e il nuovo `E_LOTTO_NON_TROVATO`) nascevano in **Python** come `ServiceError`, e `_fail_task_run_safely` ne registrava il codice esatto; passando al **database** arrivano come `DatabaseError`, che quel metodo appiattiva su `E_TASK` — R-3 avrebbe spostato la logica nel posto giusto rendendo **non attribuibili** i propri errori. Chiuso con `db_error_code`, e vale per **ogni** task che delega a una funzione DB: era un buco del telaio che R-3 ha solo reso visibile. ⚠️ Binding provato con **chiamate reali** e non coi mock (`test_pipeline_step_executor` mocka il repository e sarebbe rimasto verde anche con la firma sbagliata): lotto inesistente → `E_LOTTO_NON_TROVATO` dove prima c'era **silenzio**, lotto vuoto → zeri senza errore. Allineata `ALLOWED_TASK_FUNCTIONS` (inerte — i due task dichiarano `fn = NULL` — ma nominava funzioni non piu' chiamate) e aggiunto il `logger` di modulo che il repository non aveva |
| 2026-08-15 (notte, 12) | 📮 **Scritta la specifica di R-3 per il team DB** (§8.3), su richiesta di Tid. 🔴 **Due correzioni al piano emerse scrivendola.** **(1)** R-3 **non** cambia la firma delle funzioni esistenti: le due madri le **incapsulano** lasciandole intatte, quindi il passo DB e' **puramente additivo** e cade il vincolo «DB e repository nello stesso lotto» — che veniva da D-4/BE-1, dove a cambiare erano le firme *esistenti*, cosa che §8.2-bis ha poi deciso di non fare. Il DB puo' applicare da solo, il BE passa sopra dopo. **(2)** Le madri prendono il **codice interno** del tipo fondo, non l'id come diceva la riga R-3: il parametro che arriva dalla configurazione del task e' una **stringa**, quindi con l'id il backend dovrebbe comunque fare prima una query di lookup — e «una SELECT per task», che e' il senso di R-3, non si otterrebbe. ✅ Verificato che R-3 **non ha prerequisiti di seed**: `E_PARAMETRO_INVALIDO`, `E_PIPELINE_SCOPE_INCOMPLETE` e `E_TIPO_FONDO_NOT_FOUND` sono tutti e tre gia' a catalogo. Specificati corpo (guard → lookup → **validazione scope prima di scrivere** → applicazione set-based), ritorno, sei asserzioni pgTAP e il cambio BE che segue |
| 2026-08-15 (notte, 11) | 🧹 **Un secondo brief è stato scritto e poi CANCELLATO, su richiesta di Tid** (*«che senso ha averne 2 che ripetono quasi le stesse cose?»*) — e aveva ragione: `brief-db-fondo-fattura-prerequisiti-be-fe.md` teneva aperto un secondo documento sullo **stesso cantiere ancora aperto**, cioè due sedi destinate a divergere al primo aggiornamento. ⭐ La regola che ne esce: *un brief separato si giustifica quando cambia il **soggetto** (modello / changelog / piano), non quando cambia il **lato** che lavora — BE e FE non sono un altro cantiere, sono l'altra metà di questo.* Contenuto innestato qui dove viveva già il suo argomento: colonna **Stato** sulla tabella dei passi §8.3, riquadro sul **seed `ui.lista_*`** (il pezzo che il piano non aveva previsto), premessa di **R-3** corretta, due voci `map_integrity_error` in attesa della Fase D |
| 2026-08-15 (notte, 10) | 🔴 **Due difetti del brief stesso, trovati rispondendo a «il cantiere e' chiuso?».** **(1)** Il punto 1 di **§5** dichiarava ancora **vivo** il tampone `importo_target > 0` — cioe' esattamente la frase che §8.1 F-5 e §8.6 additano come *l'errore piu' grave*, e che il cantiere incassi aveva gia' barrato. Il documento si contraddiceva su un dato che avrebbe spento **meta' del meccanismo**: chi fosse arrivato da §5 avrebbe implementato il filtro sbagliato leggendo un brief che altrove lo vieta. Barrato e annotato (non cancellato: e' il tampone su cui il piano ha lavorato sei giorni, e chi ritrova quella frase altrove deve poter risalire al perche' e' caduta). **(2)** La testata dava la **Fase F** per pendente: e' invece **fatta** — era dichiarativa, e le sue due meta' sono nel corpo del brief incassi (§1-bis «la bilancia regge da se'» e §4 «incassato ≠ postato», centri non-cassa esclusi). ⭐ La lezione e' quella di §8.5 applicata ai documenti: *un brief lungo va riletto dall'inizio quando lo si dichiara chiuso — le sezioni vecchie non si aggiornano da sole, e una decisione ritirata a valle resta viva a monte* |
| 2026-08-15 (notte, 9-bis) | 🔍 **Review critica del giro BE (8 angoli in parallelo): 11 rilievi, 10 corretti, 1 archiviato.** ⭐ **Il filo conduttore e' `feedback_whitelist_dal_percorso_reale`, pagato due volte in un giorno.** **(1)** 🔴 La premessa di **BE-2** era letta dal **corpo** della funzione e non dal **percorso** che la attraversa: `run_pipeline` avvolge gia' ogni step in `transaction.atomic()`, quindi il parziale non poteva accadere sul giro notturno — il varco era la sola facciata single-step. Riscritti i due giri come **un unico statement set-based** (`SELECT fn(...) FROM (scope) s`): atomico per costruzione, **un** round-trip invece di N, e via il `transaction.atomic()`. **(2)** Per la stessa ragione e' stato **archiviato senza modifica** il rilievo su `FOR UPDATE SKIP LOCKED` (un giro concorrente salterebbe i fondi lockati): vero in astratto, ma il comportamento non cambia rispetto al pre-diff, perche' la transazione unica c'era gia'. 🔴 **(3)** La promessa «mai da canale di sistema» sull'elenco era **solo un commento**: su ruolo BYPASSRLS la vista `security_invoker` non filtra e il filtro applicativo no-opa con `auth_user_id=None` (che e' anche il valore legittimo del superuser, quindi non discrimina) — un consumer headless avrebbe letto i fondi di **tutti** gli emittenti senza che nulla fallisse. Ora e' un guard **fail-closed** (`connection_role_bypasses_rls`), lo stesso presidio inverso del motore documentale. **(4)** Il test «mirror» dei quattro motivi confrontava la tupla con una **seconda copia hardcoded**: verificava la propria ipotesi. Ora e' un guardrail e2e che estrae i motivi da `pg_get_viewdef` sulla **vista viva**. **(5)** Tre duplicazioni rientrate nei BB: il context manager dei vincoli era una **6ª copia** di `translate_db_errors` **che perdeva il ramo P0001** (un RAISE da trigger sarebbe uscito come 500 non tradotto), la validazione ordinamento la 7ª copia di `validate_order_params`, e due closure `isoformat` al posto di `iso_or_none`. **(6)** Mapping di riga da **22 indici posizionali** a tupla condivisa SELECT↔dict: con 20 campi nullable e coerciti, uno shift avrebbe servito dati sbagliati **senza nessuna eccezione**. Suite **3666 verdi** |
| 2026-08-15 (notte, 9) | ✅ **Giro BE fatto** sulle Fasi A/B/C/E appena applicate: **R-1** (`genera_error_policies`: i cinque `E_FONDO_*` hanno la classe — 695 voci — piu' il **messaggio di ripiego** dei cinque, che il piano non nominava e senza cui il cancello `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego` era rosso: *un codice a catalogo non e' registrato finche' non ha ENTRAMBI*), **R-2**, **BE-2** (⚠️ corretto la sera stessa: vedi la riga sotto), **BE-3** (`GET /vendite/fondi-fattura/da-decidere/`, 12 test) e **BE-5**. Suite backend **3660 verdi**. 🔴 **Difetto collaterale trovato applicando R-2, piu' grande di quello che chiudeva**: OGNI `IntegrityError` di `emittenti_fiscali_utilities` passava da `create_with_dedup` e usciva come «esiste gia' un record per questa coppia» — la tabella ha **quattro CHECK** oltre alla UNIQUE, quindi chi sbagliava le soglie non leggeva un messaggio povero ma **falso**, e sul percorso di UPDATE non c'era traduzione affatto (500). Corretto su entrambi i percorsi, 6 test. ⚠️ Il **campo** non e' dichiarato sulle due voci delle soglie ed e' voluto: i vincoli guardano la COPPIA, e `error.fields` porta un nome solo — accenderne uno sbaglierebbe meta' delle volte, *che e' peggio di non accenderne nessuno perche' manda a correggere un campo giusto*. 🔵 **Restano BE-4 e il frontend, fermi su prerequisiti DB**: la Fase D (D-11…D-13 assenti) e — non previsto dal piano — il **seed del catalogo `ui.lista_*`**, senza cui `<ListaConfigurabile>` risponde `E_UI_LISTA_NON_TROVATA`. La riga di §8.3 «non c'e' niente da inventare» e' vera per il codice Vue, non per il catalogo che lo alimenta. Richieste al DB in §8.3 |
| 2026-08-15 (notte, 8) | ✅ **Fase C APPLICATA e verde.** Migrate dei 5 changeSet `20260815-19`…`-23`, `test-fondi-fattura-governo` **29/29**, `test-fondi-fattura` **20/20**, `test-fattura-utils-critical-termini` **14/14**, baseline `vendite` senza regressioni. Doc `dbzero` rigenerata e scritti i tre `manual/` nuovi (`fn_fondo_fattura_proponibile`, `fn_check_fondo_fattura_capiente`, `vw_fondi_fattura_da_decidere`), più la riscrittura al presente di `fn_genera_fondi_fattura_source` e `fn_applica_fondi_fattura` — la prima dichiarava ancora il difetto della utility come «di oggi», la seconda i due presidi come «previsti». 🔴 **Un incidente, mio**: il migrate di Tid è girato **in parallelo** al mio lavoro (16:57) e io alle 17:01 ho droppato gli oggetti credendoli residui di una mia prova, ripristinando anche i corpi pre-Fase C di `fn_genera` e `fn_applica`. ⚠️ **Il danno era peggiore di un DROP**: le righe di `databasechangelog` restavano `EXECUTED`, quindi un migrate successivo **non li avrebbe ricreati** — database senza Fase C e changelog che giura il contrario. Rimediato ri-applicando il SQL dei cinque changeSet senza toccare `databasechangelog`, e verificato. ⭐ La lezione in §8.2-quinquies: *«la mia prova ha lasciato residui» è un'ipotesi, non una misura — e `dateexecuted` costa una query. Su un DB condiviso un DROP non è mai una pulizia* |
| 2026-08-15 (notte, 7) | ⭐ **Scritta la Fase C (D-9, D-10)** — cinque changeSet `20260815-19`…`-23`, pgTAP del governo da 18 a **29** asserzioni. ⚠️ **Da applicare**, ma **provata**: eseguita in transazione annullata dà 29/29, e `test-fondi-fattura` resta 20/20 col refactor. ⭐ **La scoperta della fase**: «costruita su `fn_saldo_sorgente_fondo`» non bastava — l'**inviluppo** (definitiva, banda, utility, atto unico, corrispondenza) viveva nel `WHERE` della generazione, e D-9 da sola ne avrebbe creato la seconda copia: un elenco che propone ciò che il giro non crea, senza nessun errore. Da qui il `-20`. **La stessa cosa una seconda volta per la capienza** (`-21` + `-22`), e lì è saltato fuori che il guard chiamava `fn_saldo_sorgente_fondo` **due volte per riga** — una funzione VOLATILE valutata due volte può accettare metà condizione e rifiutare l'altra. 🔴 **`CONFIGURAZIONE_INCOMPLETA` è morto alla nascita**: D-0, applicato oggi pomeriggio, rende quel caso irraggiungibile — e il piano lo aveva previsto. ⭐ **Motivo nuovo `IMPORTO_NON_CORRISPONDENTE`**: dove l'automatismo tace in silenzio, l'elenco parla. ⚠️ Tre trappole: il `CHECK` sul vocabolario di una vista **non esiste in PostgreSQL** (il presidio è il pgTAP che asserisce l'insieme dei motivi); il ramo `NON_PIU_CAPIENTE` parte da una tabella **senza RLS** ed è protetto dal JOIN, non dalla vista; l'**ordine dei rami** della UNION non è libero. ✅ **Chiusa la lacuna più vecchia**: la fixture con riga contabile esiste, e il guard di capienza D-3b ha finalmente un test runtime — con un controllo accanto, perché da solo sarebbe stato verde anche se l'applicazione non avesse fatto niente. ⚠️ Correzione di Tid in corso d'opera: le firme erano tornate ai tipi espliciti, `%TYPE` ripristinato su parametri e `DECLARE` |
| 2026-08-15 (notte, 6) | ✅ **Coda della Fase E e Fase B APPLICATE e verdi.** Migrate dei 9 changeSet `20260815-10`…`-18`, `test-fondi-fattura-governo` **18/18**, `test-fondi-fattura` **20/20**, `test-fattura-utils-critical-termini` **14/14**, `pgtap-baseline.sh vendite` **senza regressioni**, guardrail statici verdi, doc `dbzero` rigenerata. Verificati sul catalogo gli **otto presidi vivi** sulla tabella e i **cinque codici** in `config.codici_errore`. ⚠️ **Il migrate verde non è una prova, e qui si vede**: `fatture_fondi_fattura_source` ha **zero righe**, quindi i cinque presidi nuovi sono passati senza incontrare un dato — su una tabella popolata il `-14` sarebbe fallito. L'unica prova sono i pgTAP. ⭐ **E la prova che l'ordine `-12` → `-13` → `-14` era necessario esisteva già, senza che nessuno l'avesse chiesta**: `test-fondi-fattura.sql` esercita da mesi il ramo «reset bloccato da contabile CHIUSA», cioè l'annullamento automatico — senza il `-13`, il `-14` avrebbe reso rossa quella sezione. Era verde **per merito** ma non lo diceva, e da qui l'unica aggiunta di oggi: **ventesima asserzione**, la ragione dell'annullamento verificata **sul dato** (`motivo`) e non solo in `fatture_log`. ℹ️ Verificato di conseguenza che il **lock di colonna non rompe i percorsi vivi** — applicazione, reset, sync e annullamento non toccano mai le quattro colonne bloccate, e non è un ragionamento: sono le funzioni che i pgTAP chiamano davvero. 📮 **R-1 al BE ora vale cinque codici** e non due |
| 2026-08-15 (notte, 5) | ⭐ **Scritte la coda della Fase E (D-15, D-16) e la Fase B (D-5…D-8)** — 9 changeSet `20260815-10`…`-18`, tre codici errore, pgTAP da 12 a **18** asserzioni. ⚠️ **Da applicare**: nessun migrate, nessun test su questo lotto. Tre cose scoperte scrivendo: **(1)** `motivo` obbligatorio impone di toccare **due funzioni che il piano non nominava** — un fondo passa ad `ANNULLATO` in due punti automatici e la ragione, dove esisteva, viveva in un **messaggio di `fatture_log`** invece che sul dato; da qui l'ordine obbligato `-12` → `-13` → `-14`, perché il vincolo prima degli scrittori passerebbe sulla tabella vuota di oggi e fallirebbe al primo reset vero. **(2)** 🔴 **`origine` senza il changeSet `-18` non governa niente**: il piano diceva che il guard di corrispondenza «si restringerà ad AUTOMATICA» ma non lo elencava fra i passi, e senza quel passo la colonna esisterebbe mentre il guard continua a rifiutare **proprio** l'atto per cui la strada manuale esiste. **(3)** `atto_precedente_id` è stato tolto per davvero: la catena dei riporti si legge già da `riferimento_fattura_id` |
| 2026-08-15 (notte, 4) | ✅ **Fase A APPLICATA e verde.** Migrate dei 7 changeSet, `test-fondi-fattura-governo` **12/12**, `test-fondi-fattura` **19/19**, `pgtap-baseline.sh vendite` **senza regressioni** (24 rossi, tutti noti), guardrail statici verdi, doc `dbzero` rigenerata. Scritti i due `manual/` delle funzioni nuove (`fn_saldo_sorgente_fondo`, `trgfn_fondi_source_guard_importo`) e agganciati alle pagine auto-gen. 🔴 **La prima corsa era rossa, e il difetto era del test**: chiedevo `23514` sul CHECK `importo <> 0` e ottenevo `P0001` — perché i trigger BEFORE ROW girano **prima** dei CHECK, quindi su una sorgente da 100 lo zero lo intercetta il guard di corrispondenza (`sign(0)` non è il segno di nessun totale non nullo) e il vincolo non entra mai in gioco. È **la trappola che avevo appena scritto in §8.5**. Corretto con una quinta fixture a **totale zero**, l'unico terreno da cui il CHECK è raggiungibile — e la lezione, in §8.2-ter, non è «leggere meglio»: *un test che nomina il MECCANISMO invece del COMPORTAMENTO verifica la propria ipotesi, non il sistema*. 🔵 Resta scoperto il caso «sorgente non più capiente» (serve una riga contabile in fixture) e restano da fare le tre richieste al BE — **R-1 è urgente**: senza rigenerare `error_policies_generated.py` i due codici nuovi non hanno classe lato backend |
| 2026-08-15 (notte, 3) | ⭐ **Fase A scritta** (*«puoi procedere con lo sviluppo»*, con la conferma che le due righe di `emittenti_fiscali_utilities` hanno entrambe le soglie vuote e quindi il CHECK non fallisce all'apply). Sette changeSet `20260815-03`…`-09`, due codici errore in append ai CSV, un pgTAP nuovo da 12 asserzioni, e la **fixture del pgTAP esistente adeguata** — la sua fattura sorgente nasceva senza stato e senza utility, e con i nuovi filtri non avrebbe più generato niente. Dettaglio in **§8.2-bis**. ⚠️ **Nulla è stato applicato né eseguito**: né migrate né test né commit. Tre scelte da conoscere: le **firme non cambiano** (la chiave a nove elementi si chiude dentro `fn_applica_fondi_fattura`, che ha già entrambe le fatture — così il perimetro DB regge senza toccare `backend/`); i cinque parametri di scope passano da filtro sulla *source* a verifica sulla *figlia* (sulla source potevano far saltare un fondo **in silenzio**); e la preCondition sul codice errore è stata tolta dal changeSet -06 perché `20_code` gira **prima** di `80_data`. 🔵 Due assenze dichiarate: manca il test runtime del caso «sorgente non più capiente» (serve una riga contabile in fixture), e l'`ANNULLATO` automatico dentro `fn_sync_contabili_fondo_fattura` resta — è su fondi **già assegnati**, e toglierlo senza il processo rimborsi scoprirebbe il doppio conteggio |
| 2026-08-15 (notte, 2) | ✅ **Bonifica documentale eseguita** (*«procedi alla correzione di tutti»*). **11 documenti** toccati: i tre sbagliati oggi riscritti (il manuale della generazione ha ora la **banda** e la dichiarazione del perimetro corretta; la sezione «Analisi fondi fattura (WIP)» di `fatturazione-attivita-progetto` è **marcata superata** con la tabella di ciò che è stato deciso diversamente; la guida dei pagamenti ha una sezione nuova sulle **due soglie** in linguaggio non tecnico, con lo schema della fascia e l'avvertenza sulla configurazione a metà). I quattro 🟠 **annotati, non riscritti**: la descrizione di oggi resta, accanto c'è «oggi → diventerà, con quale passo». Aggiunte la nota **non-cassa** su `centri_riscossione` (manual + guida) e l'avvertenza sul **fail-open** delle soglie su `fn_ricalcola_totali_fattura`, che è la pagina dove la banda era già detta bene. Corretta la motivazione «è config» su `fatture_fondi_fattura_source` in `analisi-attivazione-rls-operatori` (la conclusione regge, la ragione no) e la riga «non urgente» della mappa concentrica. ⚠️ **Difetto collaterale trovato e sanato**: in due manual la convenzione ASCII degli accenti (`e\``) produceva **code span accidentali** — due «e\`» sulla stessa riga si accoppiano e il testo in mezzo viene renderizzato come codice. Allineati agli accenti veri, come i manual recenti |
| 2026-08-15 (notte) | 🔍 **Ricognizione documentale su richiesta di Tid** (tutta `docs/` + il codice): inventario in **D-17**. **Tre documenti sono sbagliati OGGI**, non domani — il manuale di `fn_genera_fondi_fattura_source` **dichiara un filtro su `utility` che il codice non applica**; `fatturazione-attivita-progetto.md` parcheggia in `work-done/` un design mai eseguito con una policy `riapribile` che è **un automatismo che scrive in reazione a un pagamento**; la guida dei pagamenti racconta **solo il capo superiore** della banda. Altri quattro lo diventeranno con l'implementazione, ognuno legato al suo passo. ⭐ E due avevano ragione: `fn_ricalcola_totali_fattura` è **l'unico posto dove la banda è detta bene**, e `tipi_fondi_fattura` dice «addebiti/**accrediti**» dall'origine — il tampone `> 0` contraddiceva il **catalogo**, non solo il dominio. Lezione: *chi documenta un consumatore non documenta la regola che lo governa* — la banda stava nella funzione che **scrive** `minimo`, non in quelle che leggono il flag. Nel codice BE/FE non c'è **nessuna** descrizione della logica: due sole occorrenze, entrambe etichette |
| 2026-08-15 (sera) | 🔴 **Piano riscritto dopo le decisioni di Tid, e due parti erano sbagliate.** **(1)** Il limite `> 0` sulla generazione — scritto sia qui sia nel cantiere incassi — **spegneva metà del meccanismo**: le due soglie di `emittenti_fiscali_utilities` sono i **due capi di una banda che contiene lo zero** (esempio: `−500 / +10`), e il capo inferiore esiste **apposta** per riportare avanti i *crediti*. Il controllo giusto non è sul segno ma sulla **corrispondenza col documento** (stesso segno del totale della sorgente, non superiore in valore assoluto), e sta in un **guard trigger** perché un CHECK non può leggere `vendite.fatture`. Cadono con esso il CHECK «automatico ⇒ positivo», la revoca+riemissione (D-8 vecchio) e `atto_precedente_id`. **(2)** 🔴 «Soglia non impostata = meccanismo spento» **vale solo a metà**: manca il massimo e la condizione diventa vera per tutti — una configurazione incompleta **spalanca** invece di chiudere. Nuovo passo **D-0** (CHECK «entrambe o nessuna»), su decisione di Tid. ⭐ **Trovata la chiave che mancava**: `fn_build_fattura_key` ha **nove** elementi, il fondo ne usa 4-5 — mancano reseller, registro, termine e modalità di pagamento — e il progetto **ha già corretto lo stesso difetto un anello prima** (*«utility_id, che mancava da sempre… chiave e lookup disallineati si annullano a vicenda»*). Il confronto passa a **riga contro riga**, e con esso spariscono il ribaltamento dell'utility e le N chiamate in autocommit. ⭐ Chiarito che **BASE è una utility** (id 5) e `billing_account.utility_id` è NOT NULL: non esiste il caso «fattura senza utility». ⭐ Verificato che **da DEFINITIVA non si torna indietro** (unica transizione: → INVIATA), quindi è la soglia di congelamento giusta — e che il fondo è **l'unico satellite della fattura non congelato**: `trgfn_fattura_satellite_guard_congelamento` è montato su scadenze e indirizzi, non sui fondi. ✅ Confermato il perimetro del **processo rimborsi** (in `pagamenti`, tre uscite, passaggio **passivo**): l'elenco delle eccedenze esce da `vendite`, che espone **una porta** (Fase D) e non un secondo cruscotto |
| 2026-08-15 | ⭐ **Aggiunto il piano di sviluppo (§8)** su richiesta di Tid: passi DB prima, logica BE poi. Risolte le cinque domande di §6 (§8.1): il fondo diventa un **atto** con importo congelato e lock strutturale, l'automatismo crea una volta sola dentro l'inviluppo `> 0`, l'aggiornamento sparisce e diventa **revoca + riemissione**; `fn_sync_pagamento_fondo_fattura` si **ritira**; due CHECK e nessuno `> 0` secco, perché l'accredito riportato è la terza strada di F-3 e passa da questa stessa tabella. 🔴 **Corrette due misure di §3** (§8.0): la seconda serratura non è «nessun movimento» ma l'**assenza di scrittori di righe contabili** — il target si genera sulla *differenza* dei due saldi, e il secondo termine non dipende dai movimenti; e `minimo` non è una configurazione ma un calcolo che **si richiude su sé stesso** (`totale_a_pagare` contiene i fondi già applicati). 🔴 **Difetto nuovo misurato**: la generazione non filtra su `utility_id` ma lo scrive, e su un BA con due utility **l'attribuzione del fondo si ribalta a ogni giro** (D-4). Altri due rilievi: il giro fondi lato BE è **N scritture in autocommit** (BE-2), e con un posting atomico la bilancia di B-1 **regge da sé** (Fase F) |
| 2026-08-09 | Stesura, estraendo l'analisi dal cantiere incassi su indicazione di Tid — «meglio un brief apposito per non dimenticare, dato che l'analisi è già approfondita». Misurati: l'unico filtro `<> 0`, l'assenza di CHECK sull'importo, i due task `attivo = true`, le due serrature (0 fatture a minimo / nessun movimento), e il guscio vuoto `fn_sync_pagamento_fondo_fattura` che nessuno chiama |
