# Brief DB — I cataloghi globali che il seed non dichiara: `perimetro_emittente = false` manca a cinque liste

> Chi scrive: backend (`dev/backend-tid`), 2026-09-15.
> Origine: collaudo in-app di «Esegui ora» ([piano-be-fe-avvio-manuale-di-un-processo.md](../work-done/piano-be-fe-avvio-manuale-di-un-processo.md)
> §4.4.2). Aprendo *Processi automatici* con **«Tutti gli emittenti»** nella
> combo, la lista è sbarrata dal cancello di perimetro («Scegli un emittente
> per continuare») — su un registro che un emittente non ce l'ha.
>
> **In una riga:** sei righe nel CSV
> `80_data/sql/ui/lista_definizione_perimetro_emittente.csv`, dove oggi ce
> n'è una sola. Nessuna colonna, nessuna funzione, nessun changeSet nuovo
> oltre al seed. Più **cinque domande** su liste che una dimensione emittente
> ce l'hanno (§5) — ✅ **tutte decise da Tid il 2026-09-18**, in §5-bis, con
> il lavoro che ne discende (§7).

---

## 1. Il fatto, misurato il 2026-09-15 (dbdev, `fn_resolve_lista_config` via API)

Con un token **senza** `emittente_attivo_id` (la combo su «Tutti gli
emittenti»), super admin:

| Lista | `perimetro_emittente` | `multi_emittente` | `richiede_scelta_emittente` |
| --- | --- | --- | --- |
| `amm.processi` | true (default) | false | **true — sbarrata** |
| `anagrafiche.operatori` | true (default) | false | **true — sbarrata** |
| `anagrafiche.emittenti_fiscali` | true (default) | false | **true — sbarrata** |
| `ui.lista_definizione` | true (default) | false | **true — sbarrata** |
| `storico.audit_log` | true (default) | false | **true — sbarrata** |
| `vendite.famiglie_documento` | **false** (seed) | false | false — si entra |

Il super admin deve scegliere un emittente per vedere **l'elenco degli
emittenti**. La misura serve a trovare l'errore, non a disegnare: la regola è
già scritta, e sta nel commento della colonna stessa.

⚠️ Riletto il 2026-09-18 su dbdev: identico. Il brief era fermo dal 15-09,
zero passi lato DB (CSV a una riga, `databasechangelog` ai soli tre changeSet
del 02-09).

## 2. La regola c'è già: è il commento di `ui.lista_definizione.perimetro_emittente`

`00_schema/ui/20260902-01`, testuale: *«su un catalogo GLOBALE — le famiglie
di documento, **le liste tecniche di ui**, **i vocabolari di config** — non
c'è nessun emittente da dire, quindi il suo `false` è letteralmente vero e
l'effetto è sbagliato: la schermata chiede di scegliere un emittente prima di
entrare, e sbarra la strada proprio a chi ha lo scope più largo»*.

Il commento nomina **tre** famiglie; il seed (`20260902-02`,
`lista_definizione_perimetro_emittente.csv`) ne dichiara **una**: la riga
`vendite.famiglie_documento,false`. Le liste tecniche di `ui` e il registro dei
processi sono rimaste al default `true`, che è il verso prudente per una lista
**nuova** — non per una la cui natura è già stata scritta.

Il backend lo sa da mesi, ma nella sede sbagliata per questo effetto:
`apps/core/tests/test_perimetro_emittente_copertura.py::_ESENZIONI` motiva
l'assenza del cancello **sull'endpoint** (`AdminAPIView`) e per `amm.processi`
scrive *«registro di catalogo, senza perimetro emittente»*, per tre `ui.*`
*«nessun `emittente_fiscale_id` in tabella»*. Ma il cancello **del pannello**
lo calcola `richiede_scelta_emittente(...)` dai flag del seed
(`perimetro_emittente.py`, ramo 2: «la lista non ha un perimetro → non c'è
niente da scegliere»), e il seed dice il contrario del registro. Due sedi che
dicono due cose: la differenza si vede solo su «Tutti gli emittenti».

### 2.1 I due flag, in una frase ciascuno — perché il nome inganna

Sono flag della **lista**, non di chi la guarda e non di ciò che contiene:

* `perimetro_emittente = false` — *«nessuna riga di questa lista appartiene
  a un'azienda»*: catalogo del software. Si entra senza scegliere niente;
* `multi_emittente = true` — *«questa lista può mostrare righe di aziende
  DIVERSE insieme, perché ogni riga dichiara la sua»*. Il super admin su
  «Tutti» le vede tutte, con l'azienda accanto.

⚠️ `multi_emittente` **non** dice che l'operatore è multi-emittente: un
operatore ha **un** emittente, e l'unico attore multi-emittente è il super
admin (decisione Tid 2026-08-17, `fn_check_user_emittente_scope` passo 3).
Il 18-09 la domanda su `anagrafiche.operatori` è stata capita male proprio per
questo nome, e la §5 di questo brief parlava di *«scope n:m»* — corretto.

## 3. Cosa si chiede — sei righe di seed

In `80_data/sql/ui/lista_definizione_perimetro_emittente.csv`, accanto a
`vendite.famiglie_documento`:

| `codice` | `perimetro_emittente` | Perché (verificato sul dbdev il 15-09: nessuna colonna `emittente_fiscale_id`) |
| --- | --- | --- |
| `amm.processi` | false | `dbops.processi` è catalogo del software: le righe valgono identiche su ogni installazione. Le identità un emittente ce l'hanno, ma stanno nel **dettaglio**, non nella lista |
| `ui.lista_definizione` | false | catalogo delle liste |
| `ui.lista_colonna` | false | catalogo delle colonne |
| `ui.lista_colonna_permesso` | false | grant per colonna/profilo |
| `storico.audit_log` | false | diario delle modifiche ai dati: le colonne a catalogo sono `timestamp, tabella, tipo_operazione, user_modifica, dettaglio` — nessuna dimensione emittente sulla riga |
| `anagrafiche.emittenti_fiscali` | false | ✅ **D-1, Tid 18-09**: l'elenco degli emittenti è un registro globale. La riga non *appartiene* a un'azienda, la riga **è** l'azienda — non c'è niente da scegliere prima di entrare |

Tutte e sei hanno `multi_emittente = false`, quindi il CHECK
`chk_ui_lista_definizione_perimetro_coerente` (`perimetro OR NOT multi`) è
soddisfatto. ⚠️ Non si tocca `multi_emittente` su queste: dichiararle `true`
vanterebbe una capacità che non hanno, e
`dbops.vw_liste_multi_emittente_non_certificate` le intercetterebbe — è la
strada breve che il commento della colonna ha già rifiutato.

⭐ Sul rischio di INSERT monco che la preCondition di `20260902-02` difende
(conta la sola riga di `famiglie_documento`): le sei liste stanno tutte in
`lista_definizione.csv` (mirror `20260507-06`, id 18, 32, 56, 57, 59, 66), che
in `80_data` gira **prima** di `20260902-02`. Su un DB da zero le righe
esistono quando il mirror del perimetro le aggiorna: la preCondition resta
com'è, sufficiente anche se non completa.

## 4. Cosa NON si chiede

* Nessuna modifica a `fn_resolve_lista_config`: legge già la colonna e la
  porta nell'envelope (`perimetro_emittente`, `COALESCE(…, true)`).
* Nessun cambio al default `true` della colonna: una lista nuova nasce **con**
  perimetro e la globalità si dichiara — è giusto così, ed è il motivo per cui
  la richiesta è un seed e non un DDL.
* Nessuna riga per le liste di **dominio** (`vendite.*`, `catalogo.*`,
  `pratiche.*`): lì il perimetro esiste e il cancello è voluto.

## 5. Le domande al DB — le liste amministrative che una dimensione emittente ce l'hanno

Erano sbarrate allo stesso modo, ma per loro `perimetro_emittente = false`
sarebbe **falso**, quindi non stavano in §3. Poste a Tid una alla volta il
2026-09-18; la risposta è in §5-bis.

| Lista | Il fatto (verificato su dbdev e nel FE il 18-09) | Decisione |
| --- | --- | --- |
| `anagrafiche.emittenti_fiscali` | **è** l'elenco degli emittenti. Nessuna RLS, nessuna colonna `emittent*` a catalogo (codice, ragione sociale, P.IVA, stato, valuta, regime) | ✅ D-1 → `perimetro = false`, riga in §3 |
| `anagrafiche.emittente_billing_account` | mappa BA → emittente. Montata **solo** dentro il drawer di un emittente (`EmittenteFiscaleBillingAccountTab.vue`, `:emittente-esplicito="emittenteId"`): il ramo 1 di `richiede_scelta_emittente` la scioglie sempre, **non è sbarrata** | ✅ D-2 → **invariata** |
| `anagrafiche.operatori` | ogni operatore ha **un** emittente; la lista ne mescola di aziende diverse e ha **già** la colonna attiva `emittenti_descrizione` («Emittente fiscale»), che il presidio riconosce (`^emittent`) | ✅ D-3 → `multi_emittente = true` |
| `config.email_log` | ha `emittente_fiscale_id` (RLS `rls_email_log_ambito`: whitelist per azienda, o `SISTEMA`); **nessuna** colonna emittente a catalogo (inviato il, destinatario, oggetto, template, account, errore, stato) | ✅ D-4 → colonna «Emittente» + `multi_emittente = true` |
| `ui.lista_preset` | ha `emittente_fiscale_id` nullable + `ambito`; la colonna «Riferimento» mostra l'azienda per riga ma è **calcolata dal BE** (`campo_sorgente` vuoto) → invisibile a `vw_liste_multi_emittente_non_certificate` | ✅ D-5 → colonna `emittente_*` riconosciuta + `multi_emittente = true` |

## 5-bis. Decisioni di Tid — 2026-09-18

Poste in forma semplice, una alla volta, sempre con «lasciare com'è» fra le
opzioni. Nessuna delle cinque è rimasta com'era per pigrizia: D-2 lo è perché
il cancello **non scatta** già oggi.

* **D-1 — `anagrafiche.emittenti_fiscali` → `perimetro_emittente = false`.**
  Il registro degli emittenti si apre senza sceglierne uno. Alternativa
  scartata: certificarla `multi_emittente` avrebbe voluto una colonna
  `emittent*` che non esiste — e sarebbe stata la stessa informazione della
  ragione sociale, ripetuta per far contento un presidio.
* **D-2 — `anagrafiche.emittente_billing_account` → invariata.** Il perimetro
  esiste davvero (ogni riga è il BA di un'azienda) e il drawer lo fissa già:
  una riga `false` sarebbe falsa e non cambierebbe niente a video.
* **D-3 — `anagrafiche.operatori` → `multi_emittente = true`.** È il caso
  «so dire da quale azienda arriva ogni riga», e la colonna c'è già: il flag
  basta. L'operatore **resta** mono-emittente (§2.1).
* **D-4 — `config.email_log` → colonna «Emittente» a catalogo, poi
  `multi_emittente = true`.** Il super admin su «Tutti» vede le email di tutte
  le aziende con l'azienda accanto; le righe `SISTEMA` con la cella vuota.
* **D-5 — `ui.lista_preset` → colonna emittente riconosciuta, poi
  `multi_emittente = true`.** L'informazione c'è già («Riferimento»): serve
  una colonna con `campo_sorgente` che il presidio veda. Se affianca o
  sostituisce «Riferimento» lo decide il BE, che quella colonna la calcola.

## 6. Come si verifica che è arrivato

Le sei righe di §1 rilette con lo stesso token senza emittente: le sei di
§3 devono rispondere `richiede_scelta_emittente = false`, e
`anagrafiche.operatori` (D-3) anche — per il ramo 3, non per il 2. Lato BE,
dopo l'apply, un presidio piccolo e senza DB in
`test_perimetro_emittente_copertura`: ogni voce di `_ESENZIONI` la cui ragione
dichiara «senza perimetro» / «nessun `emittente_fiscale_id`» deve avere la
riga `false` nel CSV — così registro e seed non possono più dire due cose.
Lo scrive il backend a seed applicato. ⚠️ E la voce di `_ESENZIONI` per
`anagrafiche.emittenti_fiscali` («è l'elenco degli emittenti stessi») va
riscritta come quella di `famiglie_documento`: *catalogo globale
(`perimetro_emittente = false`)*.

## 7. Il lavoro che discende dalle decisioni — in ordine

Tre giri, perché D-4 e D-5 hanno un vincolo d'ordine che gli altri non hanno.

**Giro 1 — solo seed, un CSV e mezzo (DB).** Chiude §1 e D-1, D-3:

1. `lista_definizione_perimetro_emittente.csv`: le sei righe di §3. Il mirror
   `20260902-02` è `runOnChange` + `ANY`: riallinea da solo;
2. `lista_definizione.csv` (mirror `20260507-06`): `multi_emittente = t` sulla
   riga `id = 28` (`anagrafiche.operatori`). ⚠️ Solo questa, non `email_log` né
   `lista_preset`: il flag va **dopo** la colonna attiva, o
   `vw_liste_multi_emittente_non_certificate` esce da zero e i tre pgTAP che
   la vogliono vuota (`ui/test-lista-definizione-multi-emittente-v1`,
   `ui/test-lista-definizione-perimetro-emittente-v1`,
   `vendite/test-viste-dash-emittente-v1`) diventano rossi.

**Giro 2 — la colonna a catalogo (DB), con `attivo = false`.** Per
`config.email_log` (lista 31) e `ui.lista_preset` (lista 58) una riga in
`lista_colonna.csv` sullo stampo delle sei già certificate di `vendite`
(`codice = emittente_fiscale`, `campo_sorgente = emittente_ragione_sociale`,
gruppo «Emittente»), **spenta** finché il repository BE non emette il campo
(memoria: una colonna con `campo_sorgente` che il SELECT non produce rompe la
lista). La chiave i18n dell'etichetta va coniata (`config.email_log.col_emittente`,
`ui.lista_preset.col_emittente`).

**Giro 3 — BE, poi il flag (DB).** Il backend espone
`emittente_ragione_sociale` nei due repository (`ui_admin_repository.py`
per i preset — dove già calcola «Riferimento» — e quello del log email);
attiva le due colonne; a quel punto `multi_emittente = t` sulle righe `id = 31` e
`id = 58` di `lista_definizione.csv`, e il presidio le trova certificate. Poi §6.

⚠️ Sui pgTAP: nessuna firma cambia e nessun contratto di vista; i presidi da
rileggere sono i tre sulla vista di certificazione (devono restare a zero in
ogni giro) e `test_perimetro_emittente_copertura` lato BE.
