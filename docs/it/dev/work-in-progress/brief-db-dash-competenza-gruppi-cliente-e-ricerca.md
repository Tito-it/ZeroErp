# Gruppi fatturabili — isolare il cliente senza promettere una fattura sola

> **Cos'è.** Il brief **DB** della funzione «filtra e cerca per cliente» sulla
> lista dei **gruppi fatturabili** della dashboard Competenza
> (`vendite.vw_dash_competenza_gruppi`, lista configurabile
> `vendite.dash_competenza_gruppi`, `lista_id = 42`).
>
> **Origine.** Richiesta del team BE del **2026-08-17**. Questo file **sostituisce**
> quel testo: l'analisi critica del 2026-08-17 ha trovato una premessa falsa, una
> divergenza inesistente, una divergenza mancante e tre buchi di perimetro. Le
> decisioni prese con Tid sono in **§4**.
>
> ⭐ **Stato al 2026-08-17 (sera): perimetro DB APPLICATO e VERDE.**
>
> - ✅ `20_code/vendite/20260817-04-update-vw-dash-competenza-attivita-billing-account-mctit.yaml`
>   — espone `billing_account_id` (§5.1);
> - ✅ `20_code/vendite/20260817-05-update-vw-dash-competenza-gruppi-cliente-fatturazione-mctit.yaml`
>   — le quattro colonne del cliente di fatturazione (§5.2);
> - ✅ `db/pgtap/vendite/test-vw-dash-competenza-gruppi-cliente-v1.sql` —
>   **8 asserzioni, 8 eseguite, nessuno skip** (§5-bis);
> - ⛔ **seed `ui.lista_colonna` NON scritto**: è accoppiato a BE-5 e deve
>   viaggiare nel suo stesso PR (§5.4). Provato e rimosso, con la ragione.
>
> **Migrazione applicata da Tid**, e i test lo confermano sul dato: `has_column`
> passa, quindi le colonne esistono davvero nel database.
>
> ✅ **Baseline `vendite` senza regressioni**: 181 file, 24 rossi, **tutti già
> noti**. I cinque test che insistono su queste viste
> (`test-vw-dash-competenza-gruppi-v1`, `test-vw-dash-competenza-v1`,
> `test-vw-dash-security-invoker`, `test-emissione-mirata-gruppi-fatturabili-v1`,
> `test-diagnostica-gruppi-fatturabili-v1`) passano tutti.
>
> 🔵 **Da qui in poi il lavoro è fuori dal DB**: BE-1…BE-6 (§6) e FE-1…FE-4
> (§7). Il seed viaggia con BE-5.
>
> ⛔ **Correzione del 2026-08-17 (rilievo BE)**: **§4 D-4 diceva il falso su
> `sensibile`**, e ha prodotto una colonna invisibile a tutti. La correzione e
> il perché sono in **§4-bis**; il difetto del contatore che ne rendeva il
> sintomo incomprensibile è in **§4-ter**. Chi legge D-4 senza §4-bis riparte
> dalla premessa sbagliata.
>
> ⚠️ **La cosa più importante da leggere prima di tutto è §3.1**: il §1 del brief
> originario prometteva che «i gruppi dello stesso cliente confluiscono sulla
> stessa fattura». **Non è vero**, e non lo diventa con nessun filtro. Chi
> implementa senza aver letto §3.1 costruisce una funzione che mantiene una
> promessa che il motore non può mantenere.
>
> **Dipendenze dichiarate**: due pezzi di questo brief poggiano su un cantiere
> separato — [brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md).
> Vedi **§9**.

---

## 1. Perché nasce

Sulla dashboard Competenza l'operatore spunta dei **gruppi fatturabili** e preme
«Fattura selezionati». Tutti i gruppi di una selezione finiscono in **un solo
giro**, e lì il database li aggrega.

Il 2026-08-17 è stata valutata e **scartata** l'ipotesi di spezzare la selezione
in un job per gruppo, perché avrebbe fatto perdere l'aggregazione (giri diversi
⇒ lotti diversi ⇒ fatture diverse).

Il corollario è questo brief. Se per finire sullo stesso documento le righe
devono stare nella **stessa selezione**, comporre quella selezione dev'essere
facile. Oggi non lo è: la lista si filtra solo per tipo di documento, e per
raccogliere «tutto di un cliente» bisogna scorrere le pagine a occhio leggendo
la ragione sociale. Su un mese popolato è un lavoro di pazienza in cui è facile
dimenticare una riga — e **la riga dimenticata non dà errore**: diventa una
seconda fattura allo stesso cliente.

**Questo, e solo questo, è il valore della funzione.** Non «una selezione = una
fattura» (§3.1), ma «non mi sfugge niente di questo cliente».

---

## 2. Situazione di partenza

`vendite.vw_dash_competenza_gruppi` espone oggi, per ogni gruppo:
`competenza_mese`, `gruppo_key`, `tipo_gruppo`, `area_documento`, `riferimento`,
`commessa_id`, `commessa_codice`, `emittente_soggetto_ruolo_id`,
`cliente_display`, `stadio`, `n_attivita`, `valore`, `data_attivita_min/max`,
`ha_oneri`, `sorgente_tipo_id`, `sorgente_uid`, `documento_id`,
`commessa_emittibile`, `commessa_stato_codice_interno`,
`commessa_stato_descrizione`.

Del cliente c'è quindi **solo la stringa da mostrare**: nessun identificativo,
nessun codice, nessun dato fiscale.

**Grana della vista** — da tenere a mente per tutto il resto: l'aggregazione è
per `(competenza_mese, gruppo_key, …, stadio)`. **Lo stesso gruppo compare su
più righe** quando ha attività in stadi diversi (parte da emettere, parte già
fatturata). Il repository lo sa e ci mette il tiebreaker `(gruppo_key ASC,
stadio …)`.

---

## 3. Cosa è stato verificato contro il codice

Questa sezione esiste perché quattro affermazioni del brief originario sono
state misurate, e tre non reggevano. Sono fatti, non opinioni: ognuno ha il suo
punto nel codice.

### 3.1 🔴 «Cliente» è **1 elemento su 9** della chiave della fattura

`vendite.fn_get_or_create_fattura_header` lo scrive testualmente:

> *«Chiave documento dall'attività: **nove elementi**, e da qui in giù vanno
> usati tutti e nove.»*

I nove, da `vendite.fn_build_fattura_key`:

`billing_account_id` (padre) · `tipo_doc_fiscale_id` · `valuta_id` ·
`emittente_soggetto_ruolo_id` · `reseller_soggetto_ruolo_id` · `utility_id` ·
`registro_id` · `termine_pagamento_id` · `modalita_pagamento_id`

Basta che **uno** sia diverso e nascono due fatture. Stesso cliente + una nota
di credito, o una valuta diversa, o termini a 30 contro 60 → **due documenti**
nella stessa selezione, nello stesso giro.

**E il gruppo non è nemmeno atomico.** `tipo_doc_fiscale_id`, `valuta_id` e i
termini stanno sulla **singola attività** (`vendite.attivita_fatturabili`, e
`fn_resolve_termini_pagamento(p_attivita_id)`), mentre il gruppo è
`(sorgente, commessa)`. Quindi **una singola riga della lista può già spezzarsi
su più fatture**, senza che l'operatore abbia fatto nulla di strano.

→ **Decisione D-1** (§4).

### 3.2 ✅ La divergenza «BA della commessa vs BA dell'attività» **non esiste**

`vendite.fn_emit_attivita_fatturabili_da_commessa` scrive
`billing_account_id = v_commessa.billing_account_id` sia in INSERT sia in
UPDATE. Il BA dell'attività **è** quello della commessa. Il timore su questo
asse era infondato.

### 3.3 ✅ La divergenza padre/figlio esiste, ma **non tocca nome né id fiscale**

`cliente_display` nasce da `commesse.billing_account_id` →
`soggetti_ruoli` → `soggetti.ragione_sociale_completa`
(`vw_dash_competenza_attivita`). La chiave fattura usa invece
`COALESCE(ba.parent_account_id, a.billing_account_id)`: **il padre**.

Ma `anagrafiche.trgfn_billing_account_guard_normalize` §2.2 **impone** che padre
e figlio condividano lo stesso `id_fiscale_univoco_cf_piva`, e
`anagrafiche.soggetti` ha `UNIQUE(stato_id, id_fiscale_univoco_cf_piva)`.
Quindi stesso codice fiscale ⇒ stesso soggetto ⇒ **stessa ragione sociale, per
costruzione**. Il manuale lo dice anche a parole.

| Dato | Figlio vs padre |
| --- | --- |
| Ragione sociale (`cliente_display`) | **identica** — garantita dal guard |
| Identificativo fiscale | **identico** — è la chiave stessa del guard |
| **Codice billing account** | **diverso** — è l'unica cosa che cambia |

→ **Decisione D-2** (§4). `cliente_display` **non si tocca**.

⚠️ **Buco noto del guard**: il confronto è `IS DISTINCT FROM` e
`id_fiscale_univoco_cf_piva` è **nullable**. Due BA entrambi senza codice
fiscale passano il controllo anche se sono soggetti diversi. Registrato in
[brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)
§4, non qui.

### 3.4 🔴 La ragione sociale **non è un asse di filtro**

Un soggetto può avere **più alberi di billing account**, e sotto **emittenti
diversi**. Esempio reale portato da Tid: soggetto *Tid* con P.IVA X, quattro
BA sotto l'emittente *Tito* e quattro sotto *Pippo*. Tutti e otto con la stessa
ragione sociale e lo stesso codice fiscale.

Se il filtro fosse «per ragione sociale», raccoglierebbe alberi diversi — che
finiscono su fatture diverse, perché `utility_id` ed `emittente` sono due dei
nove elementi. E la tendina mostrerebbe **«Tid» due volte, identica**, senza
modo di distinguerle.

→ **Decisione D-3** (§4): il filtro lavora sull'**id del BA di fatturazione**,
e l'etichetta porta il codice BA. **Questa, e non «due omonimi», è la ragione
per cui serve la colonna codice BA.**

### 3.5 🔴 L'emittente può divergere, e il brief originario non lo vedeva

La lista espone `co.emittente_soggetto_ruolo_id`, che
`vendite.fn_get_or_create_commessa` risolve come
`COALESCE(p_emittente_soggetto_ruolo_id, fn_get_emittente_fiscale_id(BA FIGLIO))`.
La chiave fattura usa `fn_get_emittente_fiscale_id(BA PADRE)`, con fallback al
default globale e senza filtro su `attivo`.

Due strade per divergere: emittente **forzato a mano** alla creazione della
commessa, oppure **albero che attraversa due emittenti**. Se divergono, due
gruppi dello stesso identico cliente vanno su **due fatture**.

→ La seconda strada si chiude nel cantiere separato (§9). La prima resta e va
misurata: **DL-1** in §10.

### 3.6 🔴 Il join al padre può far sparire righe in silenzio

`anagrafiche.billing_account` ha **RLS attiva** (`rls_billing_account_ef_whitelist`,
Ondata 2) e le viste sono `security_invoker=on`: il join al padre **passa dalla
policy**. Se il padre è fuori dallo scope dell'operatore, il LEFT JOIN dà NULL e
il gruppo **esce dal filtro cliente pur restando in lista**, senza errore.

Il vincolo «nessuna apertura di visibilità» del brief originario presidia il
rischio **opposto**. Questa è una **chiusura silenziosa**, ed è peggio: è
esattamente la riga dimenticata di §1, resa invisibile.

→ **Decisione D-5** (§4) + dipendenza dal cantiere separato (§9).

### 3.7 🟠 La ricerca su `riferimento` è il punto costoso

`riferimento = COALESCE(doc.codice, commessa_codice, gruppo_key)`, dove `doc`
è una `LEFT JOIN LATERAL` su `vendite.vw_dash_fatturazione_documenti` — una
**UNION ALL a sei rami** (preventivi, ordini, offerte, contratti, commesse,
DDT) con `ORDER BY … LIMIT 1`. E `gruppo_key` è una chiamata a
`fn_build_gruppo_fatturabile_key` con lookup su `config.sorgenti`.

Un `ILIKE '%ORD0005174%'` su quell'espressione **non può usare alcun indice**:
la LATERAL va valutata per ogni gruppo del perimetro **prima** di poter
filtrare. Sugli altri campi l'infrastruttura invece c'è già:

| Campo | Indice |
| --- | --- |
| ragione sociale | `ix_soggetti_ragione_sociale_completa_trgm` |
| identificativo fiscale | `ix_soggetti_id_fiscale_univoco_trgm` |
| codice billing account | `ix_billing_account_codice_trgm` |
| riferimento documento | ⚠️ **nessuno utilizzabile** |

→ **Decisione D-6** (§4).

### 3.8 ✅ Tre cose che il brief chiedeva e che **esistono già**

Non sono lavoro: sono coerenza da mantenere.

- **Totali che seguono i filtri**: `_where_gruppi` è già il predicato condiviso
  fra lista e riepilogo. Aggiungere i filtri nuovi lì li fa seguire a entrambi
  per costruzione.
- **Facet che non si restringono**: `list_dash_competenza_gruppi_tipi` invoca
  già `_where_gruppi` **senza** `tipo_gruppo`, apposta.
- **Il cambio filtro azzera la selezione**: `onGruppiTipoChange` lo fa già per
  il filtro tipo (`DashboardCompetenzaView.vue`).

### 3.9 ✅ «Disponibili ma spente» si ottiene gratis

`ui.fn_resolve_lista_config` §3 fa il **merge automatico delle colonne nuove dal
catalogo**: una colonna presente in `ui.lista_colonna` e assente dal preset
viene aggiunta con `visibile: FALSE` e `ordine + 10000`, e conteggiata in
`colonne_nuove` (che alimenta il banner DEF-2).

→ **Basta NON toccare `ui.lista_preset_colonna`.** Aggiungerle al preset con
`visibile = f` sarebbe più lavoro e lo stesso risultato.

⚠️ Il contrario è la trappola: una colonna aggiunta **solo** al preset e non al
catalogo non esiste; una aggiunta al catalogo **compare comunque**, spenta.

---

## 4. Le decisioni prese

Prese con Tid il **2026-08-17**. Ogni decisione ha il fatto di §3 da cui nasce.

### D-1 — La funzione **non promette** una fattura sola · *da §3.1*

Il filtro serve a **non dimenticare righe**, non a garantire un unico documento.
Il testo dell'interfaccia, i messaggi e questo brief lo dicono in chiaro.

**Non si costruisce** l'anteprima «questa selezione produrrà N fatture». È la
cosa che all'operatore servirebbe davvero, ma è un lavoro suo: **brief separato,
da aprire**, non un pezzo di questo.

### D-2 — `cliente_display` **resta com'è** · *da §3.3*

Niente ridefinizione: nome e identificativo fiscale non divergono fra figlio e
padre, e il guard lo garantisce. L'unica cosa che cambia è il **codice BA**, che
è esattamente ciò che si aggiunge.

### D-3 — Il filtro lavora sull'**id del BA di fatturazione** · *da §3.4*

- **valore** del filtro: `ba_fatturazione_id` = `COALESCE(parent_account_id, id)`
  del BA della commessa — cioè **lo stesso identico elemento** che
  `fn_build_fattura_key` mette in chiave;
- **etichetta**: `«Ragione sociale — CODICE_BA»`. Il codice è obbligatorio
  nell'etichetta, non decorativo: senza, due alberi dello stesso soggetto sono
  indistinguibili;
- **mai** un filtro per ragione sociale o per soggetto.

### D-4 — Due colonne nuove, disponibili e spente · *da §3.3, §3.9*

| Codice | Etichetta | Contenuto | Note |
| --- | --- | --- | --- |
| `ba_codice_fatturazione` | Codice BA | `codice` del **BA di fatturazione** (padre se c'è, altrimenti sé stesso) | `ordinabile = t`, `sensibile = f` |
| `id_fiscale` | Id fiscale | `soggetti.id_fiscale_univoco_cf_piva` | `ordinabile = t`, **`sensibile = f`** — ⚠️ corretto il 2026-08-17, vedi sotto |

- **Perché il codice del padre e non del figlio**: la domanda a cui la colonna
  risponde è «a chi va la fattura», ed è la stessa cosa su cui filtra D-3. Il
  codice del figlio identifica l'utenza, ma quella la dicono già `riferimento`
  e `commessa_codice`. **Fuori perimetro**, aggiungibile dopo senza impatto.
- **`ordinabile = t` non è una scelta**: `NUCLEO_ORDINABILE` in
  `scripts/gen_seed_lista.py` dichiara che «billing account» (`billing_account`,
  `ba_codice`) e «id fiscale» (`id_fiscale`, `partita_iva`) **devono** ordinare
  quando la lista li ha. I due codici scelti contengono le sottostringhe
  riconosciute: cambiarli rompe il controllo del generatore.
- ⛔ **`sensibile` NON è un'etichetta: è un cancello.** ~~Il flag alimenta il tag
  nel pannello di personalizzazione. Non nasconde nulla — etichetta, non
  protezione.~~ **Falso, e ha prodotto un difetto vero.** Corretto il
  2026-08-17 su rilievo del team BE; il dettaglio è in §4-bis.
- **Ids liberi in `ui.lista_colonna`**: prossimi disponibili **476** e **477**
  (l'ultimo usato è 475). `lista_id = 42`.
- **`ui.lista_preset_colonna` non si tocca** (§3.9).

### D-5 — Cliente non risolvibile: **si vede**, non sparisce · *da §3.6*

Un gruppo il cui BA di fatturazione non è determinabile — padre fuori scope,
mapping assente — **non sparisce e non blocca**: finisce in una voce esplicita
del filtro, *«cliente non determinabile»*, con il suo conteggio, ed è compreso
nei totali di perimetro.

**Perché**: una riga che non si riesce ad attribuire è precisamente la riga
dimenticata da cui nasce tutto il brief. Nasconderla è il difetto, non la
soluzione. Bloccare sarebbe troppo: un problema di configurazione fermerebbe
una schermata di lavoro.

⚠️ La causa a monte si chiude altrove (§9): quando l'albero non attraversa
emittenti, questo caso resta solo per configurazioni incomplete.

### D-6 — Ricerca: cinque campi, due velocità · *da §3.7*

Un solo parametro di ricerca libera, che cerca su:

| Campo | Costo |
| --- | --- |
| ragione sociale | trgm |
| identificativo fiscale | trgm |
| codice BA di fatturazione | trgm |
| codice commessa | da verificare |
| **riferimento documento** | ⚠️ **nessun indice** |

Si implementa **tutto e cinque**, perché «dov'è finito ORD0005174» è la domanda
che l'operatore fa davvero. Ma il costo del quinto campo è **dichiarato**, non
scoperto dopo: va misurato su un mese pieno prima di considerare chiusa la
funzione (**DL-2**, §10). Se non regge, la soluzione **non** è togliere il
campo: è ancorare la ricerca alla sorgente del documento.

Regole di policy (`Policy-ricerca-e-paginazione(API-DB).md`): minimo 3
caratteri per il `contains`, paginazione obbligatoria, throttling
(`is_search_endpoint = True`, già impostato sull'endpoint).

### D-7 — L'export sta **dentro** · *da §5 del brief originario*

`GET /vendite/dashboard-competenza/gruppi/export/` dichiara di esportare *«la
STESSA lista con gli stessi filtri»*. Filtro cliente e ricerca entrano anche lì.
Un export che non corrisponde a ciò che si vede a video è peggio di nessun
export.

### D-8 — Il filtro cliente **mostra tutto** · *da §6 del brief originario*

Nessuna restrizione implicita per stadio o per emittibilità. «Tutti i gruppi di
questo cliente» significa tutti: il già fatturato, i non emittibili, tutto.
Restringere è compito degli **altri** filtri, che esistono già. Un filtro che
nasconde in silenzio è la stessa classe di difetto di D-5.

---

## 4-bis. ⛔ Correzione: `sensibile` è un cancello, non un'etichetta

> **Rilievo del team BE, 2026-08-17.** Segnalato perché la colonna «Id fiscale»
> non compariva. Non era un difetto di applicazione: era una **premessa
> sbagliata di questo brief**.

### Il fatto

`ui.fn_resolve_lista_config` §5:

```sql
COALESCE(v_permessi ->> (elem ->> 'codice'),
         CASE WHEN lc.sensibile THEN 'BLOCCATO' ELSE 'TUTTO' END) AS livello_eff
...
WHERE livello_eff <> 'BLOCCATO'
```

`sensibile = t` **senza una riga in `ui.lista_colonna_permesso`** non aggiunge un
tag: **toglie la colonna dalla configurazione risolta, per chiunque.** Non è
nascosta all'utente sbagliato — è invisibile a tutti finché qualcuno non semina
i grant. L'esatto contrario di «disponibile e spenta», che era l'obiettivo di
D-4.

Ecco perché «Codice BA» (`sensibile = f`) si vedeva e «Id fiscale» no.

### Perché l'errore è stato fatto, così non si ripete

Il flag era stato verificato **solo nel frontend**: `sensibile` compare in
`ListaColonneModal.vue` come tag nel pannello di personalizzazione, e da lì si
era concluso «è un'etichetta». Il tag c'è davvero — ma è **ciò che resta dopo il
cancello**, non il cancello.

⚠️ **La lezione riusabile**: un flag di configurazione va verificato **dove viene
letto per decidere**, non dove viene renderizzato. Il punto di decisione era in
`fn_resolve_lista_config`, cioè nello schema `ui` — a un passo, e non guardato.

### La decisione presa

**`sensibile = f`.** L'argomento non è che il codice fiscale sia un dato banale:
è che **compare sulla fattura che quella schermata sta per emettere**. Bloccarlo
nella lista dove si decide *se emettere*, mentre resta stampato sul documento
*emesso*, non protegge nessuno — toglie il controllo e lascia l'esposizione.
E il controllo è precisamente lo scopo per cui la colonna esiste (§3.2:
distinguere due omonimi **prima** di emettere).

La colonna resta comunque **fuori dallo schermo** finché qualcuno non l'accende:
lo fa il merge automatico del catalogo (§3.9), che è il meccanismo giusto per
«disponibile e spenta».

### Se un giorno la si volesse davvero proteggere

La strada è l'**opposta e completa**: `sensibile = t` **più** i grant in
`ui.lista_colonna_permesso` per i profili che devono vederla. Quello che non si
può lasciare è lo stato intermedio — `t` senza grant — che non è «protetto», è
**rotto per tutti**.

⚠️ E quel giorno va fatto insieme al difetto del contatore (§4-ter), perché è
esattamente la condizione che lo rende visibile.

## 4-ter. 🔴 Difetto latente nel contatore `colonne_nuove` (perimetro DB)

Secondo rilievo BE, e questo è **un difetto vero nella funzione**, non una
premessa sbagliata.

In `ui.fn_resolve_lista_config`:

- **§3** conta le colonne nuove mergiate dal catalogo → `v_colonne_nuove`;
- **§5** rimuove le colonne `BLOCCATO` dall'array — **senza decrementare il
  contatore**;
- **§6** restituisce `colonne_nuove` così com'è.

Risultato: il badge annuncia una colonna nuova che la funzione **ha appena
tolto**. Chi guarda vede «c'è una personalizzazione» e non trova nulla, senza
modo di distinguere fra «cerco male», «è rotto» ed «esiste ma non mi è
concessa». È esattamente il sintomo incomprensibile che ha portato al rilievo.

⚠️ **È latente su OGNI lista**, non solo questa: si manifesta ovunque ci sia una
colonna `sensibile = t` senza grant. Non si era mai visto perché nessuno ne
aveva mai seminata una.

**Stato**: con la correzione di §4-bis il difetto torna **non attivabile** (non
esiste più alcuna colonna `sensibile = t`). Resta da correggere.

**Direzione proposta**: `colonne_nuove` va calcolato **dopo** il filtro dei
permessi — deve contare ciò che l'utente può davvero trovare, non ciò che è
stato mergiato. In pratica: registrare al §3 i codici mergiati, e al §5
ricontarli sull'array sopravvissuto.

⚠️ **Perché non è stato corretto subito**: il rimedio è un `CREATE OR REPLACE` di
una funzione da ~350 righe da cui dipende **ogni lista del prodotto**, per
sistemare un contatore che oggi non può sbagliare. Il momento giusto è quello in
cui qualcuno userà davvero `sensibile = t` con i grant — la stessa modifica che
lo rende visibile. Va fatto **prima** di quel seed, non dopo.

---

## 5. Cosa si costruisce lato DB

> Perimetro DB puro. Le richieste al BE sono in §6, quelle al FE in §7.

### 5.1 `vendite.vw_dash_competenza_attivita` — esporre il BA

Aggiungere `co.billing_account_id` alle colonne esposte. È una proprietà della
**commessa**, quindi costante dentro un gruppo.

### 5.2 `vendite.vw_dash_competenza_gruppi` — le colonne del cliente

Aggiungere `billing_account_id` al `GROUP BY` della CTE `aggregato`
(**funzionalmente dipendente da `commessa_id`: non moltiplica righe**), e nella
SELECT esterna risolvere:

| Colonna nuova | Definizione |
| --- | --- |
| `ba_fatturazione_id` | `COALESCE(ba.parent_account_id, ba.id)` — asse del filtro D-3 |
| `ba_codice_fatturazione` | `codice` del BA di fatturazione |
| `cliente_fatturazione_display` | ragione sociale del BA di fatturazione |
| `id_fiscale` | `soggetti.id_fiscale_univoco_cf_piva` |

⚠️ **Tre cose da non sbagliare:**

1. **`security_invoker=on` va ri-specificato** nel `CREATE OR REPLACE VIEW`: non
   è visibile in `pg_get_viewdef` e PostgreSQL la azzera in silenzio → bypass
   RLS.
2. **Nessun join a `emittenti_fiscali_billing_account` o
   `resellers_billing_account` in questa vista.** La prima è `UNIQUE(billing_account_id)`
   e sarebbe 1:1, ma la seconda **no**: `fn_build_fattura_key` fa
   `ORDER BY rb.id LIMIT 1` proprio perché può esserci più di una riga. Un join
   ingenuo moltiplicherebbe le righe — e il conteggio, e i totali, e il
   «seleziona tutto».
3. **La grana resta `(…, stadio)`** (§2). Le colonne nuove non la cambiano.

### 5.3 Cosa **non** si tocca lato DB

- `vendite.fn_build_fattura_key` e tutta la pipeline di fatturazione;
- `vendite.vw_dash_competenza_gruppi_riepilogo`: il BE non la usa per i totali
  della lista (usa `_where_gruppi` sulla vista di dettaglio, perché il riepilogo
  aggrega per `(competenza, stadio, emittente)` e non conosce `tipo_gruppo`).
  Resta valida per gli altri consumatori;
- le altre liste della dashboard (commesse, errori);
- le policy RLS. **Nessun allentamento**: la causa si toglie a monte (§9).

### 5.4 Seed `ui.lista_colonna` — ⛔ **accoppiato a BE-5, non è DB puro**

Due righe nuove, ids **476** e **477**, `lista_id = 42`, secondo D-4.
Il CSV è la sede: **append**, mai `INSERT` SQL a parte. Nessuna riga in
`ui.lista_preset_colonna` (§3.9). Il mirror `20260806-15` è `runOnChange: true`
e ripesca il CSV a ogni migrate: **nessun changeSet nuovo serve**.

⛔ **Ma il seed NON può entrare da solo.** Provato il 2026-08-17 e rimosso
subito: `apps/core/tests/test_liste_configurabili_seed.py` presidia
l'allineamento **esatto e nei due versi** fra il catalogo e la whitelist di
ordinamento del repository —

- `test_whitelist_copre_le_colonne_ordinabili`: una colonna `ordinabile = t`
  assente dalla whitelist **fa rosso** («la freccia a video risponderebbe 400»);
- `test_seed_offre_tutto_cio_che_il_backend_sa_ordinare`: il verso opposto,
  una colonna in whitelist e marcata `ordinabile = f` fa rosso pure lei.

Quindi le due righe del CSV e **BE-5** sono **un passo solo**: devono stare
nello stesso PR, o la CI è rossa in un verso o nell'altro.

⚠️ **La scorciatoia da non prendere**: seedare le colonne con `ordinabile = f`
«per ora». Passerebbe oggi — e sarebbe **verde per sottrazione**, oltre a
violare D-4, dove `ordinabile = t` non è una preferenza ma la regola
`NUCLEO_ORDINABILE`. Il seed aspetta BE-5 e ci viaggia insieme.

⚠️ **Nota di perimetro**: il CSV sta in `db/`, la whitelist in `backend/`. Il
test che li lega **sta nel repo**, non fra due repo — quindi la coppia è
verificabile in locale prima di aprire il PR, e va verificata.

---

## 5-bis. Copertura pgTAP — cosa è verificato e cosa no

`db/pgtap/vendite/test-vw-dash-competenza-gruppi-cliente-v1.sql`, `plan(8)`.
Eseguito il 2026-08-17: **8 asserzioni su 8 girate, zero skip**.

| # | Cosa verifica | Perché conta |
| --- | --- | --- |
| 1-2 | Le colonne esistono (`-04` e `-05`) | Cancello su un deploy parziale |
| **3** ⭐ | **Le colonne nuove non aggiungono righe** | Il vincolo più importante: un fan-out cambierebbe conteggio e totali, e il «seleziona tutto» manderebbe **doppioni** a fatturare |
| 4 | Senza padre: `ba_fatturazione_id` = BA della commessa | Il ramo semplice |
| **5** ⭐ | **Con padre: `ba_fatturazione_id` = il PADRE** | È D-3: se restasse il figlio, la selezione non corrisponderebbe alla fattura |
| **6** ⭐ | **Con padre: il codice è quello del PADRE** | È l'unico dato che differisce, ed è ciò che rende distinguibili due alberi |
| 7 | `cliente_fatturazione_display` = `cliente_display` | Verifica la **premessa di D-2** sul dato reale |
| 8 | Mai `id_fiscale` senza `ba_codice_fatturazione` | La regola delle tre descrittive che vivono e muoiono insieme |

⭐ **Il padre è COSTRUITO, non cercato** — un secondo BA sulla stessa
`istanza_utility` con una `utility_id` diversa, poi agganciato come parent. Un
ramo si verifica dal percorso che lo attraversa: cercare una coppia
padre/figlio già esistente avrebbe fatto passare i test 5 e 6 **per assenza di
casi** il giorno in cui i dati non ne avessero avuta una.

⚠️ **Il test 3 confronta su TUTTO il perimetro visibile**, non sulla sola
commessa fixture: un fan-out si manifesta dove i dati sono ricchi. La fixture
serve a garantire che il perimetro non sia vuoto — con un ramo `skip` esplicito
se lo fosse, perché `0 = 0` sarebbe verde per sottrazione.

### Limiti dichiarati

🔴 **Il caso (b) di D-5 non è coperto**: BA della riga visibile ma **padre fuori
scope RLS**, cioè `ba_fatturazione_id` valorizzato e le tre descrittive NULL.
Servirebbe un albero che attraversa due emittenti — che è proprio la cosa che
[brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)
P-1 vuole rendere **impossibile**. Costruirla qui significherebbe seminare il
difetto per collaudare la rete. Il test 8 verifica l'invariante che regge quel
caso, ed è ciò che serve davvero.

🔴 **Il test 7 è quello da non silenziare.** Se un giorno diventa rosso, non è
un difetto del test: significa che la premessa di D-2 non regge più su questi
dati, e allora `cliente_display` va ridefinito sul BA di fatturazione.

---

## 6. Richieste al Backend

| # | Cosa | Dove |
| --- | --- | --- |
| **BE-1** | Parametro `ba_fatturazione_id` (filtro cliente) in `_where_gruppi` — così lista **e** totali lo seguono insieme (§3.8) | `vendite_repository.py` |
| **BE-2** | Parametro di ricerca libera, stessi cinque campi di D-6, anch'esso in `_where_gruppi`; min 3 caratteri | idem |
| **BE-3** | Nuova facet «clienti» — voci con conteggio, calcolate **senza** applicare il filtro cliente né la ricerca, come già fa la facet dei tipi. Etichetta `«Ragione sociale — CODICE_BA»` (D-3). Include la voce «cliente non determinabile» (D-5) | idem, gemella di `list_dash_competenza_gruppi_tipi` |
| **BE-4** | `ba_codice_fatturazione` e `id_fiscale` nel payload di riga | idem |
| **BE-5** | ⛔ Le due colonne in `DASH_COMPETENZA_GRUPPI_SORT_COLUMNS` — **stesso PR del seed CSV**, §5.4: i test del seed le legano nei due versi. **Con** il tiebreaker `(gruppo_key, stadio)` già in uso, o la paginazione smette di essere deterministica | idem |
| **BE-6** | Stessi filtri sull'endpoint di **export** (D-7) | `views_dashboard_competenza.py` |

⚠️ **BE-5 non è una formalità.** Il tiebreaker esiste perché la vista mette lo
stesso gruppo su più righe (§2): senza, ordinando per una colonna nuova le
righe si ripetono o si saltano cambiando pagina.

---

## 7. Richieste al Frontend

| # | Cosa |
| --- | --- |
| **FE-1** | Filtro cliente come scelta strutturata (non testo libero): valore = `ba_fatturazione_id`, etichetta = `«Ragione sociale — CODICE_BA»` |
| **FE-2** | Ricerca libera separata dal filtro. Sono **due bisogni diversi**: «dov'è finito questo documento» e «dammi tutto di questo cliente» |
| **FE-3** | **Ogni** cambio di filtro o di ricerca azzera la selezione in corso e torna a pagina 1 — come già fa `onGruppiTipoChange` |
| **FE-4** | Le due colonne nuove non richiedono lavoro FE: arrivano spente dal merge automatico (§3.9) |

**FE-3 è la regola che regge tutto il resto.** Fatturare righe che non si hanno
davanti è l'incidente che questo brief esiste per evitare, e la selezione
sopravvive al cambio pagina per scelta (le chiavi sono di dominio, non indici di
riga): al cambio di **perimetro**, no.

---

## 8. Definizione di fatto

- [ ] scelto un cliente, la lista mostra **tutti** i suoi gruppi del mese, e solo
      quelli — su qualunque pagina si trovino · *aspetta BE-1*;
- [x] ✅ il cliente su cui si filtra è **lo stesso elemento** che
      `fn_build_fattura_key` mette in chiave (`COALESCE(parent_account_id, id)`)
      · *pgTAP test 5, con padre costruito*;
- [ ] un gruppo il cui cliente di fatturazione non è determinabile **si vede**,
      in una voce sua, contato nei totali (D-5) — verificato con un caso
      costruito apposta, non per assenza di casi · *invariante coperta dal test
      8; la voce di filtro aspetta BE-3*;
- [ ] la riga può mostrare codice BA e identificativo fiscale, ed entrambi sono
      **disponibili e spenti** di default · *aspetta il seed, che viaggia con
      BE-5*;
- [ ] cercando riferimento documento, codice commessa, identificativo fiscale,
      codice BA o ragione sociale si trova la riga attesa;
- [ ] numero di righe e totali di riepilogo restano coerenti fra loro e con
      filtro **e** ricerca;
- [ ] paginazione e ordinamento restano deterministici anche ordinando per le
      colonne nuove;
- [ ] l'export produce esattamente le righe che si vedono a video;
- [x] ✅ **il conteggio delle righe non cambia** rispetto a prima delle
      modifiche, a parità di filtri (controllo anti-fan-out, §5.2 punto 2)
      · *pgTAP test 3, su tutto il perimetro visibile*;
- [ ] **DL-2** misurato e dichiarato (§10).

⚠️ **Il terzultimo e il penultimo sono i due che si dimenticano**, e sono quelli
che rompono il «seleziona tutto».

---

## 9. Dipendenze da altri cantieri

Due punti di questo brief **non si chiudono qui dentro**, e sono in
[brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md):

| Punto | Perché sta là |
| --- | --- |
| §3.6 / D-5 — il padre invisibile | La causa è che un albero BA può attraversare due emittenti. Si toglie con un guard, **non** allentando la RLS |
| §3.4 — «Tid» due volte nella tendina | Un operatore mono-emittente vede solo la metà sua e l'ambiguità quasi sparisce. Il buco è che la mono-emittenza **non è garantita** |

⭐ **Aggiornamento 2026-08-17**: il secondo punto ha una decisione. Solo il super
admin è legittimamente multi-emittente; l'operatore senza riga in
`config.user_emittenti_fiscali` è un errore di configurazione, e la catena dello
scope va portata **fail-closed**. Dopo quella correzione, l'ambiguità «Tid due
volte» resta possibile **solo per il super admin** — per tutti gli altri la
tendina mostra il solo albero del proprio emittente.

⚠️ **Non toglie nulla a D-3**: il codice BA nell'etichetta serve comunque, perché
lo stesso soggetto può avere **più alberi dentro lo stesso emittente** (istanze
e utility diverse). La decisione riduce l'ambiguità, non la elimina.

**Questo brief non aspetta quello.** D-5 e l'etichetta col codice BA funzionano
anche senza: sono la rete, non la cura.

---

## 10. Da misurare (non blocca, ma va fatto)

| # | Cosa | Perché |
| --- | --- | --- |
| **DL-1** | Quante commesse hanno `emittente_soggetto_ruolo_id` diverso da `fn_get_emittente_fiscale_id(BA di fatturazione)` | §3.5. Se ci sono, il filtro cliente resta corretto ma può ancora produrre due fatture per emittente diverso |
| **DL-2** | Tempo di risposta di lista + totali + facet con ricerca attiva su un mese pieno | §3.7, D-6 |

⚠️ **Nota di metodo.** I dati di sviluppo sono di test: un DL che torna «zero
casi» **non chiude** il punto — dice solo che oggi non è capitato. La domanda è
se può succedere, e per §3.5 la risposta è sì finché non c'è il guard.

---

## 11. Cosa NON è in perimetro

- **Il motore di fatturazione**: né la chiave (`fn_build_fattura_key`), né i
  lotti, né la pipeline. Questo brief riguarda **come si legge e si filtra** la
  lista;
- **L'anteprima «N fatture»** (D-1): brief separato, da aprire;
- **Le altre liste della dashboard**;
- **Il limite di 200 gruppi per chiamata** (`parse_gruppi`, lato BE);
- **Il codice BA del figlio** come colonna (D-4);
- **Il buco del CF nullo** nel guard padre/figlio (§3.3): sta nell'altro brief.

---

## 12. Riferimenti

| Cosa | Dove |
| --- | --- |
| Vista lista gruppi | `docs/it/dbzero/vendite/views/vw_dash_competenza_gruppi.md` |
| Vista attività (sorgente del cliente) | `docs/it/dbzero/vendite/views/vw_dash_competenza_attivita.md` |
| Vista riepilogo di perimetro | `docs/it/dbzero/vendite/views/vw_dash_competenza_gruppi_riepilogo.md` |
| Chiave della fattura (i nove elementi) | `docs/it/dbzero/vendite/funzioni/fn_build_fattura_key.md` |
| Dove i nove vanno usati tutti | `docs/it/dbzero/vendite/funzioni/fn_get_or_create_fattura_header.md` |
| Guard coerenza fiscale padre/figlio | `docs/it/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_normalize.md` §2.2 |
| Gerarchia BA (manuale) | `docs/it/dbzero/anagrafiche/manual/billing_account.md` §«Gerarchia padre/figlio» |
| Risoluzione colonne e merge automatico | `docs/it/dbzero/ui/funzioni/fn_resolve_lista_config.md` §3 |
| Regola colonne sempre ordinabili | `scripts/gen_seed_lista.py` — `NUCLEO_ORDINABILE` |
| Policy ricerca e paginazione | `docs/it/dev/Policy-ricerca-e-paginazione(API-DB).md` |
| Cantiere perimetro emittente | [brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md) |
