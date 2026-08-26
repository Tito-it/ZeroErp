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
> ✅ **Stato: COMPLETO E CHIUSO (2026-08-18).** DB, BE e FE realizzati, applicati
> e mergiati; §4-bis e §4-ter chiusi (consuntivo in §4-quater); DL-1 e DL-2
> misurati. Baseline `vendite` e `ui` senza regressioni.
>
> ⏸️ **Una sola casella resta aperta in §8, e non è lavoro**: la voce «cliente
> non determinabile» (D-5) non ha soggetti su cui mostrarsi — DL-1 ha misurato
> **zero billing account con padre**. Si chiude da sé quando finisce
> [brief-db-perimetro-emittente-liste-e-gerarchia-ba.md](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md).
>
> 📌 **Un lavoro è uscito da qui e vive altrove**: DL-2 ha trovato un costo che
> la ricerca non c'entra (166 ms per 45 righe, il 78% per risolvere
> `riferimento`) → [brief-db-riferimento-gruppi-lateral-costosa.md](../work-in-progress/brief-db-riferimento-gruppi-lateral-costosa.md).
>
> ⭐ **Stato al 2026-08-17 (sera): perimetro DB APPLICATO e VERDE.**
>
> - ✅ `20_code/vendite/20260817-04-update-vw-dash-competenza-attivita-billing-account-mctit.yaml`
>   — espone `billing_account_id` (§5.1);
> - ✅ `20_code/vendite/20260817-05-update-vw-dash-competenza-gruppi-cliente-fatturazione-mctit.yaml`
>   — le quattro colonne del cliente di fatturazione (§5.2);
> - ✅ `db/pgtap/vendite/test-vw-dash-competenza-gruppi-cliente-v1.sql` —
>   **8 asserzioni, 8 eseguite, nessuno skip** (§5-bis);
> - ✅ **seed `ui.lista_colonna` scritto e applicato** (ids 476/477): è
>   accoppiato a BE-5 ed è viaggiato nel suo stesso PR (§5.4), come previsto.
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
> ✅ **BE-1…BE-6 e FE-1…FE-4 REALIZZATI e mergiati** il 2026-08-17 (PR #1280),
> seed compreso. Consuntivo, scelte prese dove il brief lasciava aperto, e
> presidi automatici: **§13**. Restano tre verifiche in app e i due DL (§8, §10).
>
> ⛔ **Correzione del 2026-08-17 (rilievo BE)**: **§4 D-4 diceva il falso su
> `sensibile`**, e ha prodotto una colonna invisibile a tutti. La correzione e
> il perché sono in **§4-bis**; il difetto del contatore che ne rendeva il
> sintomo incomprensibile è in **§4-ter**. Chi legge D-4 senza §4-bis riparte
> dalla premessa sbagliata.
>
> ✅ **Entrambi CHIUSI il 2026-08-18.** `sensibile = f` era già applicato; il
> difetto del contatore è corretto da `20_code/ui/20260818-04-update-fn-resolve-lista-config-contatore-colonne-nuove-mctit.yaml`,
> applicato, con pgTAP dedicato (5/5) **provato rompendolo** e baseline `ui`
> senza regressioni. Il consuntivo è in **§4-quater**.
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

**Stato**: ✅ **CORRETTO il 2026-08-18** — `20260818-04`. Il consuntivo, con la
prova che il test presidia davvero, è in §4-quater. Quanto segue resta perché
descrive il difetto e il ragionamento con cui era stato rinviato: serve a chi
rileggerà, non è più lavoro aperto.

⭐ **E dal 2026-08-17 non è più «non attivabile per fortuna»: c'è un cancello.**
`apps/core/tests/test_liste_configurabili_seed.py` →
`test_colonna_sensibile_ha_sempre_un_grant` fallisce se una colonna attiva ha
`sensibile = t` **senza** una riga di grant in `ui.lista_colonna_permesso` (il
cui seed oggi **non esiste affatto** nella cartella `ui`, quindi l'insieme dei
grant è vuoto per costruzione). Chi proverà a seminare una colonna sensibile
troverà la CI rossa **prima** di applicarla, con scritto nel messaggio perché —
ed è esattamente il momento in cui questo §4-ter va corretto.

⚠️ Il cancello **non corregge il contatore**: rende impossibile arrivarci per
distrazione. Il giorno in cui una colonna andrà protetta davvero, servono i
grant **e** la correzione di `colonne_nuove`, nello stesso passo. Il test si
stringe da sé sulla singola colonna appena il seed dei grant esisterà, senza
modifiche. *Provato rompendolo: riportando `id_fiscale` a `sensibile = t` il
test fallisce nominando la colonna.*

**Direzione proposta**: `colonne_nuove` va calcolato **dopo** il filtro dei
permessi — deve contare ciò che l'utente può davvero trovare, non ciò che è
stato mergiato. In pratica: registrare al §3 i codici mergiati, e al §5
ricontarli sull'array sopravvissuto.

~~⚠️ **Perché non è stato corretto subito**: il rimedio è un `CREATE OR REPLACE` di
una funzione da ~350 righe da cui dipende **ogni lista del prodotto**, per
sistemare un contatore che oggi non può sbagliare. Il momento giusto è quello in
cui qualcuno userà davvero `sensibile = t` con i grant — la stessa modifica che
lo rende visibile. Va fatto **prima** di quel seed, non dopo.~~

⛔ **Superato il 2026-08-18 (insistenza del team BE, decisione di Tid).** Il
rinvio aveva una logica, e un difetto: finché in un brief resta scritto «resta da
correggere», il cantiere che l'ha scoperto **non si chiude** — e questo non è
nemmeno un residuo suo, è un difetto dello schema `ui` che questo cantiere ha
*trovato*. Correggerlo il giorno del seed protetto avrebbe inoltre significato
mettere le mani in quella funzione **mentre** si introduce la condizione che la
esercita: due cose insieme, ognuna difficile da isolare se qualcosa va storto.

## 4-quater. ✅ Consuntivo della correzione (2026-08-18)

`20_code/ui/20260818-04-update-fn-resolve-lista-config-contatore-colonne-nuove-mctit.yaml`,
applicato. `ui.fn_resolve_lista_config` è **STABLE** e **SECURITY INVOKER**:
nessun giro di `dbops.fn_sync_functions_owner`.

### La modifica, in tre punti

| Dove | Cosa |
| --- | --- |
| `DECLARE` | una variabile nuova: `v_codici_mergiati TEXT[]` |
| passo **3** | oltre a *contarle*, registra i **codici** delle colonne mergiate |
| passo **5-bis** | dopo il filtro dei permessi, li riconta sull'array sopravvissuto |

Nient'altro è stato toccato.

### ⚠️ La trappola che ha quasi rovinato la correzione

Nella funzione ci sono **due** blocchi `IF v_config_colonne IS NULL THEN`: uno
**prima** del filtro dei permessi e uno **dopo**. Il primo tentativo di ancorare
l'inserimento è fallito su un assert proprio perché il blocco non era univoco.

⭐ **Senza quell'assert il ricalcolo sarebbe finito nel punto sbagliato** — prima
del filtro — dove avrebbe ricontato esattamente lo stesso numero. La correzione
sarebbe risultata *applicata* e *inefficace*, che è il modo peggiore di
chiudere un difetto. Il blocco nuovo è ancorato alla sezione 6 apposta.

### Il collaudo

`db/pgtap/ui/test-fn-resolve-lista-config-contatore-colonne-nuove-v1.sql`,
`plan(5)`: la colonna sensibile senza grant non compare **e** non è contata; col
grant torna in entrambi; una colonna nuova normale continua a essere contata.

⭐ **Provato rompendolo**, ed è l'unica prova che conta qui: rieseguito contro il
corpo **pre-correzione**, il **test 2 fallisce** con `have: 1, want: 0` — cioè
esattamente il difetto, il contatore che annuncia la colonna appena rimossa. Gli
altri quattro passano in entrambe le versioni: descrivono comportamento che era
già corretto, e **solo il 2 discrimina**. Detto, per non far credere a una rete
più larga di quella che è.

⚠️ **Due cose imparate dalla fixture**, tutte e due «verde per sottrazione»
evitato per un soffio:

1. `campo_sorgente` **non si inventa**: `trgfn_ui_lista_colonna_a10_valida_campo_sorgente`
   pretende un attributo reale della vista della lista. La fixture riusa quello
   di una colonna già a catalogo — il codice è nuovo, ed è il codice a
   identificare la colonna;
2. l'utente del contesto pgTAP **non ha alcun profilo di accesso**, quindi su di
   lui il ramo «colonna sensibile CON grant» è irraggiungibile: un grant si
   aggancia a un profilo, e senza profili la colonna resta bloccata comunque. I
   test 3-4 sarebbero stati verdi per la ragione sbagliata. La fixture **sceglie**
   il primo utente che ha davvero un profilo sotto la veste corrente, con un
   criterio esplicito e non un id fisso — e salta con motivo dichiarato se non
   ce n'è nessuno.

### Non-regressione

- **44 liste su 44** restituiscono `colonne_nuove` e numero di colonne
  **identici** a prima della modifica (confronto diretto, non a campione);
- baseline `ui`: **4 rossi su 9, tutti già noti** — fra cui
  `test-lista-contratti-seed`, registrato come `ASSERZIONE` da prima;
- gli altri due pgTAP che esercitano la funzione (`test-fn-resolve-lista-config`,
  `…-preset-aggiornato-v1`) restano verdi: 13 e 6 asserzioni.

### Cosa resta possibile, e ora è sicuro

Il giorno in cui una colonna andrà protetta davvero, servono **i grant** in
`ui.lista_colonna_permesso` (il cui seed oggi non esiste) e basta: la correzione
del contatore non è più un prerequisito da ricordare. Il cancello lato BE
`test_colonna_sensibile_ha_sempre_un_grant` continua a impedire lo stato
intermedio — `sensibile = t` senza grant — che non è «protetto», è **rotto per
tutti**.

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

| # | Cosa | Dove | Stato |
| --- | --- | --- | --- |
| **BE-1** | Parametro `ba_fatturazione_id` (filtro cliente) in `_where_gruppi` — così lista **e** totali lo seguono insieme (§3.8) | `vendite_repository.py` | ✅ |
| **BE-2** | Parametro di ricerca libera, stessi cinque campi di D-6, anch'esso in `_where_gruppi`; min 3 caratteri | idem | ✅ |
| **BE-3** | Nuova facet «clienti» — voci con conteggio, calcolate **senza** applicare il filtro cliente né la ricerca, come già fa la facet dei tipi. Etichetta `«Ragione sociale — CODICE_BA»` (D-3). Include la voce «cliente non determinabile» (D-5) | idem, gemella di `list_dash_competenza_gruppi_tipi` | ✅ |
| **BE-4** | `ba_codice_fatturazione` e `id_fiscale` nel payload di riga | idem | ✅ |
| **BE-5** | ⛔ Le due colonne in `DASH_COMPETENZA_GRUPPI_SORT_COLUMNS` — **stesso PR del seed CSV**, §5.4: i test del seed le legano nei due versi. **Con** il tiebreaker `(gruppo_key, stadio)` già in uso, o la paginazione smette di essere deterministica | idem | ✅ |
| **BE-6** | Stessi filtri sull'endpoint di **export** (D-7) | `views_dashboard_competenza.py` | ✅ |

⚠️ **BE-5 non è una formalità.** Il tiebreaker esiste perché la vista mette lo
stesso gruppo su più righe (§2): senza, ordinando per una colonna nuova le
righe si ripetono o si saltano cambiando pagina.

---

## 7. Richieste al Frontend

| # | Cosa | Stato |
| --- | --- | --- |
| **FE-1** | Filtro cliente come scelta strutturata (non testo libero): valore = `ba_fatturazione_id`, etichetta = `«Ragione sociale — CODICE_BA»` | ✅ `<Select filter>` in `DashboardCompetenzaView` |
| **FE-2** | Ricerca libera separata dal filtro. Sono **due bisogni diversi**: «dov'è finito questo documento» e «dammi tutto di questo cliente» | ✅ `<InputText>` con debounce (BB `useDebouncedAction`) |
| **FE-3** | **Ogni** cambio di filtro o di ricerca azzera la selezione in corso e torna a pagina 1 — come già fa `onGruppiTipoChange` | ✅ `applicaFiltroGruppi`, **una sede per tutti e tre** i filtri |
| **FE-4** | Le due colonne nuove non richiedono lavoro FE: arrivano spente dal merge automatico (§3.9) | ✅ confermato: nessuna riga di FE |

**FE-3 è la regola che regge tutto il resto.** Fatturare righe che non si hanno
davanti è l'incidente che questo brief esiste per evitare, e la selezione
sopravvive al cambio pagina per scelta (le chiavi sono di dominio, non indici di
riga): al cambio di **perimetro**, no.

---

## 8. Definizione di fatto

> ⭐ **Stato al 2026-08-17 (notte).** BE-1…BE-6 e FE-1…FE-4 sono **implementati e
> mergiati** (PR #1280); il seed è applicato, `sensibile = f` compreso. Le
> caselle qui sotto non aspettano più codice: aspettano di essere **guardate in
> app**. Tre sono state chiuse da presidi automatici — dove un test può dire il
> vero, vale più di un click, perché resta vero anche domani.

- [x] ✅ scelto un cliente, la lista mostra **tutti** i suoi gruppi del mese, e
      solo quelli — su qualunque pagina si trovino · *verificato in app da Tid,
      2026-08-17*;
- [x] ✅ il cliente su cui si filtra è **lo stesso elemento** che
      `fn_build_fattura_key` mette in chiave (`COALESCE(parent_account_id, id)`)
      · *pgTAP test 5, con padre costruito*;
- [⏸️] un gruppo il cui cliente di fatturazione non è determinabile **si vede**,
      in una voce sua, contato nei totali (D-5) · **RINVIATA (Tid, 2026-08-17)**.
      L'invariante è coperta dal pgTAP test 8 e la voce di filtro esiste (BE-3),
      ma **non c'è un caso su cui mostrarsi**: servirebbe un albero BA che
      attraversa due emittenti — cioè la configurazione che il cantiere
      [perimetro emittente](brief-db-perimetro-emittente-liste-e-gerarchia-ba.md)
      sta rendendo **impossibile** proprio ora. Costruirla apposta significherebbe
      seminare il difetto per collaudare la rete (§5-bis, «Limiti dichiarati»).
      ⭐ Si chiude **da sé** quando quel cantiere finisce: se la causa a monte
      sparisce, la voce resta come rete e non ha più occasioni di comparire —
      che è l'esito voluto, non una verifica mancata.
      ⭐ **Confermato da DL-1 (§10)**: oggi **nessun billing account ha un
      padre**, quindi il caso non ha proprio soggetti su cui mostrarsi — non era
      una prova saltata, era una prova impossibile;
- [x] ✅ la riga può mostrare codice BA e identificativo fiscale, ed entrambi sono
      **disponibili e spenti** di default · *verificato in app da Tid dopo la
      migrazione: «Id fiscale» compare, quindi la correzione `sensibile = f`
      (§4-bis) è arrivata a destinazione sul dato*;
- [x] ✅ cercando riferimento documento, codice commessa, identificativo fiscale,
      codice BA o ragione sociale si trova la riga attesa · *verificato in app da
      Tid, 2026-08-17*;
- [x] ✅ numero di righe e totali di riepilogo restano coerenti fra loro e con
      filtro **e** ricerca · *per costruzione: filtro cliente e ricerca vivono in
      `_where_gruppi`, il predicato che lista e riepilogo condividono — non due
      scritture che possono divergere. Coperto da
      `test_where_gruppi_filtro_cliente_e_ricerca`*;
- [x] ✅ paginazione e ordinamento restano deterministici anche ordinando per le
      colonne nuove · *`DashCompetenzaGruppiOrdinamentoTests`: ordinando per
      `ba_codice_fatturazione` e `id_fiscale` il tiebreaker `(gruppo_key, stadio)`
      resta nell'ORDER BY*;
- [x] ✅ l'export produce esattamente le righe che si vedono a video · *cancello
      `DashCompetenzaGruppiExportParitaTests`: confronta i parametri-filtro di
      `fn_dash_competenza_gruppi` con le chiavi del dict `filtri` dell'endpoint di
      export. Un filtro aggiunto alla lista e dimenticato nell'export fa rosso —
      ed è l'unico modo in cui questo si rompe, perché l'export continuerebbe a
      funzionare esportando un perimetro più largo. **Provato rompendolo**:
      tolto `search` dall'export, il test fallisce nominando il filtro*;
- [x] ✅ **il conteggio delle righe non cambia** rispetto a prima delle
      modifiche, a parità di filtri (controllo anti-fan-out, §5.2 punto 2)
      · *pgTAP test 3, su tutto il perimetro visibile*;
- [x] ✅ **il contatore `colonne_nuove` dice il vero** anche in presenza di una
      colonna `sensibile` senza grant · *`20260818-04`, pgTAP 5/5 provato
      rompendolo, 44 liste su 44 invariate — §4-quater*;
- [x] ✅ **DL-2 misurato** (2026-08-18) · e ha trovato un costo **che la ricerca
      non c'entra**: 166 ms per 45 righe **senza filtri**, di cui il 78% per
      risolvere `riferimento`. Misura, causa e conseguenze in §10; il lavoro è
      passato al DB in un brief suo. Il rimedio previsto da D-6 («ancorare la
      ricerca alla sorgente») **decade**: risolverebbe un decimo del problema.

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
| **DL-1** | Quante commesse hanno `emittente_soggetto_ruolo_id` diverso da `fn_get_emittente_fiscale_id(BA di fatturazione)` | §3.5. Se ci sono, il filtro cliente resta corretto ma può ancora produrre due fatture per emittente diverso · ✅ **misurato 2026-08-18 — sotto** |

### ✅ DL-1 misurato (2026-08-18) — zero divergenze, ma il dato che conta è un altro

```text
commesse esaminate ....................... 59
divergenti (emittente commessa ≠ fattura) . 0
emittente di fatturazione non risolto ..... 0
billing account CON PADRE ................. 0   ← il numero che conta
```

**Zero divergenze è vero e non chiude niente.** Il §3.5 elencava due strade per
divergere: emittente **forzato a mano** alla creazione della commessa, e albero
BA che **attraversa due emittenti**. La prima è genuinamente a zero: nessuno ha
mai forzato un emittente, ed è un'informazione. La seconda **non poteva
risultare**, perché *nessun billing account ha un padre*.

⚠️ **Con zero padri, `COALESCE(parent_account_id, id)` è sempre `id`.** Cioè:

- la divergenza padre/figlio non ha **soggetti** su cui manifestarsi — non è
  prevenuta, è che la popolazione che potrebbe esibirla è vuota;
- il filtro cliente di **D-3** oggi è **indistinguibile** da un filtro sul BA
  della riga. È corretto, ma i dati non lo esercitano: l'unica cosa che ha mai
  verificato la risalita al padre è il **pgTAP test 5/6, col padre costruito
  apposta**. Il brief lo aveva scelto per prudenza (§5-bis, *«il padre è
  COSTRUITO, non cercato»*) — ora si vede che era l'unica strada possibile;
- **D-5** («cliente non determinabile») non ha soggetti per la stessa ragione, e
  questo conferma il rinvio della sua casella in §8: il padre fuori scope
  richiede un padre.

⭐ **Il giorno in cui nascerà il primo billing account con padre**, tre cose di
questo brief passano dall'essere corrette all'essere *esercitate*: la risalita di
D-3, la voce di D-5 e il test 7 (che verifica la premessa di D-2 sui dati veri —
ed è quello **da non silenziare** se un giorno diventa rosso).

⚠️ **Nota di metodo confermata**: un DL a zero non chiude il punto. Qui il numero
utile non era `divergenti` ma `con_padre`, cioè **il denominatore** — senza, lo
zero sembrava una rassicurazione mentre era un'assenza di casi.
| **DL-2** | Tempo di risposta di lista + totali + facet con ricerca attiva su un mese pieno | §3.7, D-6 · ⚠️ **misurato 2026-08-17, e la misura va letta bene — sotto** |

### ✅ DL-2 misurato (2026-08-18) — e ha trovato tutt'altro

**La domanda era sbagliata.** DL-2 doveva misurare *il costo della ricerca*;
l'`EXPLAIN (ANALYZE, BUFFERS)` col contesto operatore ha trovato un costo che
**la ricerca non c'entra**, perché si paga **a ogni apertura della lista**.

Misura su competenza giugno 2026, **nessun filtro, nessuna ricerca**:

| Nodo | Tempo | Buffer |
| --- | --- | --- |
| **Totale (45 righe)** | **166 ms** | 35.057 |
| Aggregato base — i 45 gruppi | 11 ms | 2.424 |
| **`LATERAL` documenti** — `loops=45` | **~130 ms** | **28.058** |
| ↳ `Seq Scan on preventivi` — `loops=34` | **~105 ms** | **22.951** |

La risoluzione di `riferimento` è il **78% del tempo e l'80% dei buffer**. Per
ogni gruppo scandisce l'intera tabella dei preventivi, scarta 164 righe e ne
tiene 1 — e ogni riga scartata paga il predicato RLS, **~5.600 chiamate a
funzione** per una lista di 45 righe. L'indice che eviterebbe tutto questo
(`ix_preventivi_uid_text`) **esiste e non viene usato**; sugli altri cinque rami
della union non esiste affatto.

⚠️ **Tre conseguenze che cambiano le decisioni prese qui:**

1. **il rimedio di D-6 non serve più.** «Ancorare la ricerca alla sorgente»
   risolverebbe un decimo del problema, e solo quando si cerca;
2. **non è lavoro BE.** Il costo è dentro la vista: nessuna strategia di query
   del repository lo aggira;
3. **scala con i gruppi, non con la pagina.** `loops=45` è il perimetro, non le
   righe mostrate: a 450 gruppi sono ~1,3 s, e la paginazione non contiene nulla
   perché la `LATERAL` gira prima di poter impaginare.

→ Aperto **[brief-db-riferimento-gruppi-lateral-costosa.md](../work-in-progress/brief-db-riferimento-gruppi-lateral-costosa.md)**
(perimetro DB), con la misura, la causa dal piano e il metodo per riprodurla.
Il beneficio va oltre questa lista: `vw_dash_fatturazione_documenti` la leggono
anche altri consumatori.

⚠️ **Nota di metodo, pagata sul campo**: la prima esecuzione del 2026-08-17 aveva
`app.ruolo_applicativo` vuoto. La vista è fail-closed: **zero righe in 0,1 ms**,
con l'aria di essere velocissima. Un `EXPLAIN` senza il contesto operatore non
misura l'applicazione — misura il cancello che si chiude.

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

---

## 13. Consuntivo BE/FE (2026-08-17, PR #1280)

> Cosa è stato costruito, **le scelte prese dove il brief lasciava aperto**, e i
> presidi che tengono chiuso ciò che un test può tenere chiuso. Il perimetro DB è
> §5; qui c'è tutto il resto.

### 13.1 Le tre scelte che il brief non fissava

Non sono dettagli d'implementazione: cambiano il comportamento, e chi rilegge il
brief senza questo paragrafo non le troverebbe scritte da nessuna parte.

**a) Entrambe le facet sul perimetro BASE (competenza + stadio).** BE-3 chiedeva
la facet clienti «senza filtro cliente né ricerca, come già fa la facet dei
tipi», ma non diceva se dovesse seguire `tipo_gruppo`. Sceglierlo cambia le
cose: se `clienti` seguisse il tipo e `tipi` no, le due tendine
descriverebbero **perimetri diversi**, e i conteggi cambierebbero a seconda
dell'**ordine** in cui l'operatore sceglie i filtri. Quindi nessuna delle due
segue l'altra — è anche l'unica lettura che lascia invariata la facet esistente.

**b) «Cliente non determinabile» è un parametro suo, non un id sentinella.**
D-5 chiede una voce di filtro per i gruppi senza BA di fatturazione risolvibile.
Rappresentarla con un id finto (`0`, `-1`) avrebbe messo un valore inventato in
un campo che trasporta chiavi vere, e prima o poi qualcuno lo confronta con una
PK. L'API espone quindi `ba_non_determinabile` (booleano) **alternativo** a
`ba_fatturazione_id`. Il sentinella esiste solo nel frontend — una `<Select>` ha
un valore solo — e lo store lo traduce: `GRUPPI_CLIENTE_NON_DETERMINABILE`,
stringa e non numero, così non può collidere con nessun id.

**c) Ricerca sotto i 3 caratteri: ignorata.** Non un 400 e non una lista
svuotata. Il termine arriva mentre l'operatore sta ancora digitando: un errore
sarebbe un errore su un'azione legittima, e una lista vuota gli direbbe «non
c'è niente» quando la verità è «non ti ho ancora cercato». La soglia
(`SEARCH_MIN_LEN`) vive nel repository e non nel service, perché vale **anche per
l'export**, che non passa dalla validazione della view.

### 13.2 Due trappole trovate implementando

**`qp_bool` ha `default=True` sul parametro assente.** Usandolo per
`ba_non_determinabile`, aprire la lista **senza** quel parametro avrebbe
significato «true»: si sarebbero visti i soli gruppi senza cliente
determinabile — quasi nulla — senza che alcun filtro risultasse attivo a video.
Usato `qp_bool_optional`, che è anche rigoroso sui valori non riconosciuti.

**Tre test rossi con `IndexError`.** Le fixture di
`DashCompetenzaGruppiRepositoryTests` costruivano righe a **17** colonne mentre
la proiezione ne ha **19**. Allineate, con la ragione scritta accanto: una riga
finta più corta esplode su un indice, ma una più **lunga** farebbe **passare** il
test leggendo la colonna sbagliata — il modo silenzioso di sbagliare.

### 13.3 I presidi automatici

Tre caselle della §8 sono chiuse da test, non da un click: dove un test può dire
il vero, vale di più, perché resta vero anche domani. **Tutti e tre provati
rompendoli** — un test che non si è mai visto fallire non presidia nulla.

| Presidio | Dove | Cosa impedisce |
| --- | --- | --- |
| `test_colonna_sensibile_ha_sempre_un_grant` | `apps/core/tests/test_liste_configurabili_seed.py` | Che qualcuno semini `sensibile = t` senza grant, cioè la condizione che attiva il difetto §4-ter. ⚠️ Il seed di `ui.lista_colonna_permesso` **non esiste** nella cartella `ui`: oggi l'insieme dei grant è vuoto per costruzione |
| `DashCompetenzaGruppiExportParitaTests` | `apps/vendite/tests/services/test_dashboard_competenza_service.py` | Che un filtro aggiunto alla lista venga dimenticato nell'export (D-7). È l'unico modo in cui si rompe: nessun errore, l'export continua a funzionare esportando **più righe** di quelle a video |
| `DashCompetenzaGruppiOrdinamentoTests` | idem | Che ordinando per le colonne nuove sparisca il tiebreaker `(gruppo_key, stadio)`. Senza, a offset alti tornano righe già viste — e neanche questo dà errore |

A cui si aggiunge `test_where_gruppi_filtro_cliente_e_ricerca`, che pinna il
predicato condiviso: i cinque rami della ricerca in **un solo gruppo
parentesizzato** (senza le parentesi l'OR si legherebbe all'ultima AND e la
ricerca **allargherebbe** il perimetro invece di stringerlo), e «non
determinabile» che vince sull'id invece di sommarsi.

### 13.4 Fuori tabella

- **BB estratto**: `core/composables/useDebouncedAction.js` (regola del 2, ok
  Tid), con `SEARCH_DEBOUNCE_MS = 400` che ora **`useSearchTable` importa** — il
  valore non vive più in due posti. Il pezzo che il BB porta non è il timer, sono
  sei righe: è il **cleanup** su unmount/deactivate, che fa `cancel` e non
  `flush` (un'azione ritardata va abbandonata quando esci, non eseguita in
  fretta: se è una fetch riscriverebbe una lista che l'operatore ha lasciato).
- **i18n**: due chiavi colonna (emesse dal seed, quindi verificate da
  `check_i18n_keys.py`) più sette di interfaccia, in `it` **e** `en`.
- **CSS**: `.app-dash-filtro-cliente` e `.app-dash-ricerca-gruppi` in `main.css`,
  con larghezze **massime e non fisse** — la toolbar è flex-wrap e i due
  controlli devono stringersi invece di spingere fuori «Fattura selezionati».
- **Suite**: 3683 test Django verdi sul perimetro toccato, build ed eslint puliti,
  `check_i18n_keys.py` pulito.

---

## 2026-08-26 · ⚠️ Postilla: la colonna era nata SPENTA

Scoperto chiudendo il cantiere
[registro e data prevista in competenza](brief-db-registro-e-data-prevista-in-competenza.md),
e corretto lo stesso giorno su richiesta di Tid.

⛔ **Il seed in `ui.lista_colonna` non basta perche' una colonna si veda.** Lo
step 3 di `ui.fn_resolve_lista_config` — «merge automatico colonne nuove dal
catalogo» — unisce con **`visibile => FALSE`** ogni colonna che non abbia una
riga nel **preset** (`ui.lista_preset_colonna`).

⇒ Le colonne consegnate da questo cantiere sulla lista 42
(`vendite.dash_competenza_gruppi`) sono rimaste **a catalogo ma invisibili**:
comparivano solo nel contatore `colonne_nuove`, cioe' nel badge «Personalizza»,
e nessun operatore le vedeva senza spuntarle a mano.

✅ **Corretto**: righe aggiunte al preset di sistema `42`
(`dash_competenza_gruppi_default`) in `80_data/sql/ui/lista_preset_colonna.csv`.
Nessun changeSet nuovo — il loader `20260507-09` e' `loadUpdateData`
`runOnChange: true` con chiave `(preset_id, colonna_id)`.

⭐ **La lezione, che vale oltre queste colonne**: chi aggiunge una colonna a
catalogo decide **anche** se nasce accesa o spenta, e lo scrive. «Spenta» e' una
scelta legittima per una colonna di nicchia — ma dev'essere una scelta, non
l'esito di un passo saltato. Qui erano **tre** colonne su due cantieri diversi,
il che dice che il passo si dimentica per abitudine.
