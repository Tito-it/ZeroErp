# Guida — Gli Emittenti Fiscali

> **Ultimo aggiornamento**: 27 novembre 2026
>
> **Destinatari**: amministratori dell'installazione (super admin), analisti funzionali, sviluppatori database, backend e frontend
>
> **Vedi anche** — schemi DB:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — le aziende che emettono documenti: una riga per azienda, il ruolo `EF` di un soggetto
> * [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — per quale azienda fattura ogni billing account, e il gestore globale
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — il conto che fattura: ha sempre il suo collegamento, e non si cancella
> * [config.valute](/dbzero/config/tabelle/valute) — il catalogo delle valute
> * [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — le eccezioni d'importo dell'azienda per una utility
> * [config.regimi_fiscali](/dbzero/config/tabelle/regimi_fiscali) — il catalogo dei regimi fiscali (RF01…RF19)
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali) — l'azienda dell'operatore: una al massimo
> * [config.user_emittente_attivo](/dbzero/config/tabelle/user_emittente_attivo) — l'azienda di lavoro scelta dal super admin, riproposta al login
>
> **Vedi anche** — funzioni e trigger DB:
>
> * [anagrafiche.fn_crea_emittente_fiscale](/dbzero/anagrafiche/funzioni/fn_crea_emittente_fiscale) — il verbo che fa nascere un emittente, col suo ruolo `EF`
> * [anagrafiche.trgfn_emittenti_fiscali_guard_codice_forma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_codice_forma) — la forma della sigla
> * [anagrafiche.trgfn_emittenti_fiscali_guard_ruolo_emi_fis](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_ruolo_emi_fis) — la riga è il ruolo `EF` di un soggetto
> * [anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_guard_regime_conferma) — la conferma del regime non si scrive a mano
> * [anagrafiche.trgfn_emittenti_fiscali_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_regime_conferma) — chi ha dichiarato il regime, e quando
> * [anagrafiche.trgfn_emittenti_fiscali_default_bootstrap](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_default_bootstrap) — il primo emittente diventa il gestore globale
> * [anagrafiche.trgfn_emittenti_fiscali_default_guard](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_default_guard) — il gestore globale è uno e uno solo
> * [anagrafiche.fn_parametri_importo_utility](/dbzero/anagrafiche/funzioni/fn_parametri_importo_utility) — i parametri d'importo effettivi, con l'eccezione dell'azienda
> * [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id) / [anagrafiche.fn_get_emittente_fiscale_pk](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_pk) — l'azienda che fattura un billing account, col suo ruolo o col suo `id`
> * [vendite.trgfn_emittenti_fiscali_provision_registri](/dbzero/vendite/funzioni/trgfn_emittenti_fiscali_provision_registri) — i registri delle famiglie non fiscali, alla nascita e alla riattivazione
> * [script.fn_get_ba_emittente_sr_id](/dbzero/script/funzioni/fn_get_ba_emittente_sr_id) — l'azienda di un billing account
> * [anagrafiche.trgfn_billing_account_link_ef](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — il billing account nasce collegato: all'azienda di chi lavora, o al gestore globale
> * [anagrafiche.trgfn_efba_guard_storia_emittente](/dbzero/anagrafiche/funzioni/trgfn_efba_guard_storia_emittente) / [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente) — il cambio d'azienda, solo senza documenti
> * [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente) — la storia: qualunque documento, anche in bozza
> * [anagrafiche.fn_guard_albero_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_albero_ba_emittente) — padre e figli sulla stessa azienda
> * [anagrafiche.fn_guard_istanza_ba_emittente](/dbzero/anagrafiche/funzioni/fn_guard_istanza_ba_emittente) — i billing account di un'istanza sulla stessa azienda
> * [script.trgfn_prevent_modification_generic](/dbzero/script/funzioni/trgfn_prevent_modification_generic) — il collegamento non si cancella e non si sposta
> * [script.trgfn_doc_guard_emittente_ba](/dbzero/script/funzioni/trgfn_doc_guard_emittente_ba) — ogni documento di vendita, fattura compresa, è dell'azienda del suo billing account
> * [script.fn_check_user_can_create_ba](/dbzero/script/funzioni/fn_check_user_can_create_ba) — chi può creare un billing account
> * [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — il verbo che assegna un operatore a un'azienda, riservato al super admin
> * [script.fn_get_user_emittenti_scope](/dbzero/script/funzioni/fn_get_user_emittenti_scope) — l'azienda dell'operatore, come la mostra il drawer
> * [script.fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo) — l'ultimo super admin non si sposta
> * [config.trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete) — l'assegnazione non si cancella fuori dal verbo
> * [config.fn_imposta_emittente_attivo](/dbzero/config/funzioni/fn_imposta_emittente_attivo) — la scelta dell'azienda di lavoro
> * [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin) — chi è super admin
> * [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope) — l'utente può lavorare su quest'azienda?
> * [script.fn_get_emittenti_scope_pk_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) — le aziende che l'utente vede
> * [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — l'azienda su cui agisce chi lavora
> * [script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale) — l'azienda di una riga nuova, presa da chi la scrive
> * [script.fn_get_setup_status](/dbzero/script/funzioni/fn_get_setup_status) — i contatori del banner degli operatori
> * [dbops.vw_emittenti_regime_non_confermato](/dbzero/dbops/views/vw_emittenti_regime_non_confermato) — le aziende attive col regime mai dichiarato
> * [dbops.vw_operatori_senza_emittente](/dbzero/dbops/views/vw_operatori_senza_emittente) — gli operatori che non vedono nessuna azienda
> * [dbops.vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti) — le aziende che un processo automatico non serve
>
> **Vedi anche** — API e service backend:
>
> * [API Emittenti Fiscali](/backend/anagrafiche/manual/api_emittenti_fiscali) — anagrafica dell'emittente, billing account e utilities
> * [API Amm. Software](/backend/amm-software/manual/api_amm_software) — l'azienda degli operatori e lo stato dell'impianto
> * [API User Profile](/backend/core/manual/api_user_profile) — `/me/` e l'emittente di lavoro
>
> **Vedi anche** — guide correlate:
>
> * [Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto e i suoi ruoli; perché il soggetto non ha un emittente
> * [Generazione di un Cliente](/guide/generazione-cliente) — l'emittente del cliente, che si sceglie una volta
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — il perimetro per azienda, le policy e i guard di scrittura
> * [Contratto GUC applicativo](/guide/contratto-guc-app) — `app.current_emittente_id`, l'azienda della sessione
> * [Risorse Umane e Accessi](/guide/risorse-umane-e-accessi) — il ciclo di vita dell'operatore e il primo amministratore
> * [Numerazione Documenti e Codici](/guide/numerazione-documenti-e-codici) — i registri per azienda e la sigla nei codici
> * [Configurazione Liste](/guide/configurazione-liste) — le liste certificate «multi-emittente»
> * [Configurazione e Gestione Parametri](/guide/configurazione-e-gestione-parametri) — i parametri per azienda

---

## Introduzione

Un **emittente fiscale** è un'azienda per cui l'installazione emette documenti: fatture, DDT, ordini, contratti.
Un'installazione può averne una sola, la ditta che usa il programma, oppure più di una: un gruppo con tre società,
uno studio che fattura per conto di più clienti. Ogni documento, ogni billing account e ogni operatore sta sotto
**un** emittente, e chi lavora vede i dati dell'emittente in cui sta lavorando.

Due persone hanno a che fare con gli emittenti, in due modi diversi:

* il **super admin** li definisce, decide per quale emittente lavora ciascun operatore e può lavorare dentro
  qualunque emittente;
* l'**operatore** lavora dentro il suo emittente e non lo sceglie: lo trova già deciso.

**Cosa troverai in questa guida:**

* che cos'è un emittente, e che cosa nasce con lui;
* come il super admin lo definisce, lo collega ai clienti e lo spegne;
* come il super admin assegna gli operatori;
* l'emittente di lavoro: come lo vive l'operatore, come lo sceglie il super admin;
* che cosa è rifiutato, e perché.

---

## Il modello in sintesi

```text
soggetto con partita IVA (chi è)
    └── ruolo EF (soggetti_ruoli)
            └── emittenti_fiscali (l'azienda che emette)
                    │   codice (sigla) · regime fiscale · bollo · arrotondamento · valuta · attivo
                    │
                    ├── emittenti_fiscali_billing_account   per quale azienda fattura ogni cliente
                    │       └── una riga «gestore globale» (is_default): l'azienda di riserva
                    ├── emittenti_fiscali_utilities          eccezioni d'importo per utility
                    ├── registri di numerazione              uno per famiglia di documento
                    │
                    ├── user_emittenti_fiscali               l'operatore che lavora per quest'azienda (una per operatore)
                    └── user_emittente_attivo                l'azienda scelta dal super admin, riproposta al login
```

* **Emittente** = il ruolo `EF` di un soggetto, più le impostazioni dell'emissione. Il nome non è suo: è la ragione
  sociale del soggetto.
* **Assegnazione** = l'unico emittente per cui un operatore lavora.
* **Emittente di lavoro** = l'azienda della sessione. Per l'operatore è sempre la sua; il super admin la sceglie
  dalla barra in alto.

### Due chiavi per la stessa azienda

L'emittente ha due identificativi: l'`id` della riga di `emittenti_fiscali` e il `soggetto_ruolo_id` del suo ruolo
`EF`. Alcune tabelle puntano al primo (ordini, contratti, l'assegnazione degli operatori), altre al secondo
(fatture, commesse, registri, listini, il collegamento dei billing account). Quale tabella usa quale chiave, e
perché, lo spiega [Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici), §5b.

L'azienda che fattura un billing account si chiede con una chiave o con l'altra: `fn_get_emittente_fiscale_id`
risponde il ruolo, `fn_get_emittente_fiscale_pk` l'`id`. Tutte e due partono dal **billing account**, non da una
delle due chiavi, e rispondono con il suo collegamento. Un id che non è un billing account è rifiutato: un id
sbagliato non diventa un'azienda, né quella di chi agisce né il gestore globale. Senza billing account (un lotto
di fatturazione, che raccoglie clienti diversi) `fn_get_emittente_fiscale_id` risponde il gestore globale.

---

## Chi fa che cosa

| | Super admin | Operatore |
| --- | --- | --- |
| Vede la pagina **Amm. Software → Emittenti Fiscali** | sì | no: il menu non c'è, e la rotta porta a «accesso negato» |
| Crea, modifica, spegne un emittente | sì | no |
| Collega billing account e utilities a un emittente | sì | no |
| Assegna un operatore a un emittente | sì | no |
| Lavora dentro un emittente | in quello che sceglie, oppure in «Tutti gli emittenti» in sola lettura | sempre e solo nel suo |
| Cambia l'emittente di lavoro | sì, dalla barra in alto | no: vede il nome del suo, come testo |
| Vede i dati | di tutti gli emittenti, o di quello scelto | del suo emittente; nessuno se non è assegnato |

**Super admin** vuol dire avere attivo il profilo `SUPER_ADMIN` sull'identità operatore
([script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin)). Lo si concede dal drawer dell'operatore,
con l'interruttore «Accesso Super Admin». Il superuser di Django non conta. Il primo super admin di
un'installazione nuova nasce col verbo di primo impianto: lo racconta
[Risorse Umane e Accessi](/guide/risorse-umane-e-accessi).

⚠️ **Un super admin assegnato a un emittente è un «admin di emittente»**: ha tutti i permessi del super admin, ma
vede e lavora solo dentro quell'emittente, come un operatore, e non ha la scelta in alto. Il super admin che sceglie
fra tutti gli emittenti è quello **senza** assegnazione.

---

## Parte 1 — Il super admin definisce l'emittente

La pagina è **Amm. Software → Emittenti Fiscali**. La lista mostra codice, ragione sociale, identificativo fiscale,
partita IVA, stato, valuta e regime, e si filtra per testo e per stato. Il pulsante «Nuovo emittente fiscale» apre
il drawer, e un clic su una riga apre lo stesso drawer in modifica. Dal menu della riga si aprono i drawer dei
billing account, delle utilities e dei registri di numerazione.

### Il soggetto: un'azienda con partita IVA

L'emittente si crea **da un soggetto che esiste già**, scelto nel drawer, e il soggetto deve avere la **partita
IVA**. Senza, il drawer lo dice e nasconde il resto del modulo. Un soggetto ha un emittente al massimo: il
secondo è rifiutato.

Il soggetto riceve il ruolo `EF`, se non ce l'ha già, e l'emittente **è** quel ruolo. Il legame non si cambia dopo:
un emittente non passa a un altro soggetto. Ragione sociale, partita IVA, sede e forma giuridica restano sul
soggetto e si modificano lì. L'emittente non ha una descrizione sua.

### Il codice: la sigla dell'azienda

Il **codice** è una sigla da 2 a 10 caratteri, solo lettere e cifre (`A-Z`, `0-9`). Il database la scrive in
maiuscolo e rifiuta tutto il resto: un trattino non viene tolto in silenzio, viene respinto
(`E_EMITTENTE_CODICE_FORMA_NON_VALIDA`). Il drawer blocca già i caratteri non ammessi mentre si scrive.

⛔ **La sigla non si cambia dopo la creazione** (`E_CODICE_NON_MODIFICABILE`), ed è unica nell'installazione. Va
scelta con cura perché entra nei codici dei documenti, per esempio quello della commessa `CMM-<sigla>-<anno>-<numero>`
([Numerazione Documenti e Codici](/guide/numerazione-documenti-e-codici)).

### Il regime fiscale: si dichiara, e resta scritto chi l'ha fatto

Il **regime fiscale** (RF01 ordinario, RF17 IVA per cassa…) si sceglie dal catalogo `config.regimi_fiscali` e
decide, fra le altre cose, l'esigibilità dell'IVA sui documenti: un emittente RF17 emette a esigibilità differita.

La **conferma** del regime è derivata dal database. Ogni volta che il regime viene scritto, anche con lo stesso
valore, il database annota data e autore (`regime_fiscale_confermato_il`, `_da`); nessuno scrive quelle due colonne a
mano (`E_EMITTENTE_REGIME_CONFERMA_DERIVATA`). Nel drawer si vede una di tre righe: «Regime confermato il … da …»,
«Regime non ancora confermato» col pulsante «Conferma il regime», oppure «Il regime sarà confermato al salvataggio».

⚠️ Un emittente creato senza regime nasce **RF01 non confermato**: il valore c'è, ma nessuno l'ha dichiarato. Le
aziende attive in questo stato stanno in `dbops.vw_emittenti_regime_non_confermato`, che deve restare vuota.

### Bollo, arrotondamento e valuta

* **Bollo automatico**, con la sua **soglia**: la soglia si compila solo se il bollo automatico è acceso.
* **Arrotondamento** degli importi: `UP`, `DOWN`, `HALF_UP`, `HALF_DOWN`.
* **Valuta** predefinita dei documenti: una valuta del catalogo (`config.valute`), come quella di un billing account.

I valori proposti alla creazione vengono dai parametri `EMITTENTE_DEFAULT_BOLLO_AUTO`, `EMITTENTE_DEFAULT_BOLLO_SOGLIA`
e `EMITTENTE_DEFAULT_ROUNDING_POLICY` ([Configurazione e Gestione Parametri](/guide/configurazione-e-gestione-parametri)).

### Che cosa nasce insieme all'emittente

La creazione è **un'operazione sola**
([anagrafiche.fn_crea_emittente_fiscale](/dbzero/anagrafiche/funzioni/fn_crea_emittente_fiscale)): il ruolo `EF`,
la riga dell'emittente e la conferma del regime, se è stato indicato. Con lei nascono, da sole:

* i **registri di numerazione delle famiglie non fiscali** (DDT, ordini, commesse, resi): l'emittente può emetterli
  subito. Rinascono anche quando un emittente spento si riaccende;
* se è il **primo emittente** dell'installazione, la riga del **gestore globale** (vedi sotto).

⚠️ **I registri delle fatture e le mappature tipo documento/natura non nascono da soli.** Il drawer lo ricorda alla
creazione: senza, la prima fattura dell'emittente si ferma con «configurazione mancante». Non c'è un registro
generico di ripiego, ed è voluto: meglio fermarsi che numerare sul progressivo di un'altra azienda. I registri si
configurano dal drawer «Registri di numerazione» dell'emittente.

### Il gestore globale

Fra i collegamenti dei billing account c'è **una riga speciale, senza billing account**: il **gestore globale**
(`is_default`). È l'azienda con cui nasce un billing account quando non c'è un utente che lavora (un processo
notturno, una migrazione) o quando chi lo crea non ha un'azienda sua. Decide solo i billing account che
**nasceranno**: ogni billing account già nato ha il suo collegamento, e spostare il gestore globale non cambia
l'azienda di nessun cliente.

* Il primo emittente creato diventa gestore globale da solo.
* Il gestore globale è **uno e uno solo** (`E_EMITTENTE_DEFAULT_SINGLETON`): si può spostare su un'altra azienda, ma
  non può sparire: si sposta modificando la sua riga, che non si cancella (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`) e non
  diventa il collegamento di un billing account (`E_BA_COLLEGAMENTO_NON_SI_SPOSTA`). Nel drawer dei billing account
  la riga non si rimuove, e «Crea default globale» è spento quando la riga c'è già.
* Senza nessun emittente non nasce nessun billing account (`E_EMITTENTE_DEFAULT_MISSING`): un cliente fattura sempre
  per un'azienda.
* ⛔ **Il gestore globale non è l'azienda di chi lavora.** Un operatore senza assegnazione, o un super admin in
  «Tutti gli emittenti», non ricade sul gestore globale: non ha un'azienda su cui scrivere.

### I billing account: per quale azienda fattura un cliente

Il cliente non ha un emittente: ce l'ha il suo **billing account**, uno solo, e sempre. Il collegamento nasce quando
nasce il billing account, con l'azienda in cui lavora chi lo crea o, senza, col gestore globale; dal drawer
«Gestisci billing account» il super admin vede i collegamenti. Un collegamento **non si cancella** e **non passa a un
altro billing account** (`E_BA_COLLEGAMENTO_NON_SI_TOGLIE`, `E_BA_COLLEGAMENTO_NON_SI_SPOSTA`), e il billing account
stesso non si cancella (`E_BA_NON_SI_CANCELLA`): un cliente si chiude annullandolo. Un cliente cambia azienda solo
**modificando l'azienda sul suo collegamento**. Come si decide l'azienda di un cliente, e quando non si può più
cambiare, lo spiega [Generazione di un Cliente](/guide/generazione-cliente). In breve, ogni cambio passa da tre
cancelli:

* **la storia**: un billing account con almeno un documento, di qualunque famiglia e in qualunque stato, **anche in
  bozza**, non cambia azienda (`E_BA_EMITTENTE_CON_STORIA`). La finestra per correggere c'è finché il billing account
  non ha nessun documento; chi ha sbagliato azienda e ha già scritto documenti li cancella prima;
* **l'albero**: un billing account padre e i suoi figli stanno sotto la stessa azienda (`E_ALBERO_EMITTENTE_MISTO`);
* **l'istanza**: i billing account di una stessa istanza di servizio stanno sotto la stessa azienda
  (`E_ISTANZA_EMITTENTI_DIVERSI`).

I cancelli guardano solo il collegamento di un billing account che nasce o cambia azienda: lo spostamento del
gestore globale non tocca nessun cliente, e non si giudica.

### Le utilities: le eccezioni d'importo

> ⚠️ **Cambio di modello deciso il 2026-11-27, non ancora costruito** ([brief-db-utility-gestite-dall-emittente](/dev/work-in-progress/brief-db-utility-gestite-dall-emittente)): la tabella diventa anche
> l'**elenco delle utility gestite** dall'azienda (riga accesa = utility attiva; un'azienda senza righe non ne gestisce
> nessuna), e i parametri d'importo restano facoltativi sulla riga. Questa sezione descrive il funzionamento di oggi,
> vero finché il giro DB non è applicato: si riscrive in quel giro.

Dal drawer «Gestisci utilities» il super admin vede la matrice delle utilities ammesse per il ruolo `EF` e, per
ciascuna, può configurare un'**eccezione** dell'azienda: i decimali degli importi (da 0 a 2), il metodo di
arrotondamento, le soglie minima e massima di fatturazione (tutte e due o nessuna). Senza una riga valgono i
parametri di sistema ([anagrafiche.fn_parametri_importo_utility](/dbzero/anagrafiche/funzioni/fn_parametri_importo_utility)).
Le utilities che la matrice offre sono quelle della matrice Utilities/Ruoli
([Configurazione Liste](/guide/configurazione-liste), §11.1).

### Spegnere un emittente, non cancellarlo

⛔ **Un emittente non si cancella** (`E_DELETE_NOT_ALLOWED`): si spegne togliendo «Attivo». Lo spegnimento è
respinto finché l'emittente ha ancora qualcosa di vivo collegato: billing account, utilities attive, operatori
assegnati, documenti come ordini, contratti, preventivi e DDT, il magazzino, i parametri per azienda
(`E_ATTIVO_BLOCK_CHILDREN_ACTIVE` quando le righe collegate vanno spente, `E_ATTIVO_BLOCK_CHILDREN_EXIST` quando vanno
tolte). L'elenco completo, e le eccezioni volute, stanno nella scheda
[anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali).

Il verso opposto: niente di nuovo nasce sotto un emittente spento (`E_ATTIVO_PADRE_NON_ATTIVO`), e un'utility può
essere salvata solo come inattiva.

---

## Parte 2 — Il super admin assegna gli operatori

### Un operatore, un emittente

Un operatore lavora per **un emittente al massimo**: la riga in `config.user_emittenti_fiscali` è una per utente.
L'assegnazione si fa nel drawer dell'operatore (**Amm. Software → Operatori**), scheda «Dati», solo in modifica, nel
riquadro «Scope emittenti fiscali»:

* «**Un solo emittente**» e la scelta dall'elenco: l'operatore lavora per quell'azienda;
* «**Tutti gli emittenti (solo SUPER_ADMIN)**»: solo per un super admin, che non ha assegnazione e vede tutte le
  aziende. A un operatore normale il riquadro la mostra spenta.

Il salvataggio passa dal verbo [script.fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope),
che solo un super admin può chiamare (`E_PERMESSO_NEGATO`) e che **sposta** l'operatore: toglie l'assegnazione di
prima e scrive la nuova nello stesso momento. Fuori dal verbo l'assegnazione di un utente attivo non si cancella
(`E_USER_EMITTENTE_DELETE_VIETATO`), e l'azienda di una riga non si riscrive (`E_EMITTENTE_NON_MODIFICABILE`).

⛔ **Un operatore normale non è mai «globale».** Per chi non è super admin il riquadro offre solo «Un solo
emittente»: un operatore appena creato lo trova già scelto, con l'elenco vuoto, e il Salva resta spento finché non
si sceglie l'azienda. Lo decide il database
([script.fn_get_user_emittenti_scope](/dbzero/script/funzioni/fn_get_user_emittenti_scope)), e il verbo rifiuta di
togliere l'azienda a un operatore normale (`E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN`). Per spostarlo si sceglie
un'altra azienda; per fermarlo si spegne l'operatore.

Il motivo: senza assegnazione un operatore normale **non vede nessuna azienda**. Non vede dati e non può creare
billing account finché esistono emittenti attivi.

### Chi non è ancora assegnato

«Non assegnato» non è «globale»: è lo stato di un operatore appena creato, che aspetta la sua azienda. Ci finisce
anche un super admin senza azienda a cui si toglie il profilo `SUPER_ADMIN`: diventa un operatore come gli altri, e va
assegnato.

Nella lista degli operatori un banner conta quelli non ancora assegnati a un emittente
([script.fn_get_setup_status](/dbzero/script/funzioni/fn_get_setup_status)). Lo stesso controllo, lato database,
è `dbops.vw_operatori_senza_emittente`: gli operatori attivi, non super admin, senza assegnazione. Deve restare a
zero righe.

### L'ultimo super admin non si sposta

Se l'operatore è l'**ultimo super admin attivo**, il riquadro è spento e il suggerimento spiega perché
(`E_PROFILO_ULTIMO_SUPER_ADMIN`): assegnarlo a un'azienda gli toglierebbe la vista su tutte le altre, e
l'installazione resterebbe senza nessuno che la amministri per intero.

### I processi automatici hanno bisogno di un utente per azienda

Un processo automatico di dominio (un job notturno, una coda) lavora con un **utente tecnico**, e anche l'utente
tecnico ha la sua azienda. Un emittente attivo che un processo vivo non serve sta in
`dbops.vw_emittenti_non_serviti`: quando si aggiunge un emittente, si guarda lì quali utenti tecnici mancano.
Il modello delle identità dei processi sta in [Processi automatici: classe e identità](/guide/processi-automatici-classe-e-identita).

---

## Parte 3 — L'emittente di lavoro

Ogni sessione lavora **dentro un emittente**. Il backend lo porta nel token di accesso e, a ogni richiesta, lo
consegna al database come `app.current_emittente_id`, dopo aver controllato che l'azienda sia ancora attiva
([Contratto GUC applicativo](/guide/contratto-guc-app)). Il database lo usa **solo per restringere**: l'emittente di
lavoro non allarga mai ciò che l'utente può vedere.

### L'operatore: il suo emittente, sempre

L'operatore **non sceglie**: al login lavora nell'emittente a cui è assegnato.

* In alto, al posto della scelta, c'è il **nome** del suo emittente, come testo.
* Nei moduli il campo emittente è in **sola lettura** e porta già la sua azienda: ciò che crea nasce lì
  ([script.trgfn_default_emittente_fiscale](/dbzero/script/funzioni/trgfn_default_emittente_fiscale)).
* Vede **solo** i dati del suo emittente. Le policy del database filtrano le righe, e i guard di scrittura
  respingono una riga di un'altra azienda (`E_SCOPE_EMITTENTE`), anche quando la si raggiunge per riferimento, come
  un lotto o una matricola di un'altra azienda (`E_RIFERIMENTO_DI_ALTRO_EMITTENTE`). Le regole stanno in
  [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni), §6.3 e §7.
* Un operatore non assegnato non vede niente: va assegnato (Parte 2).

### Il super admin: sceglie dove lavorare

Il super admin senza assegnazione **sceglie** l'emittente di lavoro.

* **Al primo accesso** si apre la finestra «Seleziona l'emittente di lavoro», che non si chiude con ESC: si sceglie
  un'azienda e si preme «Inizia», oppure «Continua senza selezionare». Con un solo emittente la scelta è già
  proposta. Con nessun emittente la finestra non compare.
* **Dopo**, la scelta sta nella barra in alto: «Tutti gli emittenti» in testa, poi le aziende attive. Cambiare chiede
  conferma, **chiude le schede aperte e ricarica la pagina**; la conferma dice quante schede hanno modifiche non
  salvate, che andrebbero perse.
* La scelta è una **preferenza**, non un permesso
  ([config.fn_imposta_emittente_attivo](/dbzero/config/funzioni/fn_imposta_emittente_attivo)): al login successivo
  viene riproposta, se l'azienda è ancora attiva. Se nel frattempo è stata spenta, la preferenza si cancella e la
  sessione riparte da «Tutti gli emittenti».

### ⛔ «Tutti gli emittenti» è sola lettura

In «Tutti gli emittenti» il super admin vede i dati di tutte le aziende, ma **non crea documenti**: una riga nuova
non saprebbe di quale azienda è (`E_EMITTENTE_NON_RISOLTO`), e un billing account nuovo è respinto finché esistono
emittenti attivi (`E_BA_ADMIN_GLOBALE_VIETATO`). Il modulo lo dice: «Stai lavorando su tutti gli emittenti: scegline
uno dalla barra in alto per poter creare.» Non c'è un ripiego sul gestore globale.

Altri tre segni della modalità «tutti»:

* una **lista non certificata multi-emittente**, che non mostra da quale azienda viene ogni riga, non si apre e
  chiede di scegliere un emittente («Scegli un emittente per continuare»). Le liste certificate si aprono, e la
  ricerca avvisa che voci con lo stesso nome possono appartenere ad aziende diverse
  ([Configurazione Liste](/guide/configurazione-liste), §11.6);
* le **schede KPI** portano l'etichetta «— tutti gli emittenti»;
* un **parametro per azienda** si scrive sull'emittente scelto in alto: in «tutti» non c'è un'azienda su cui
  scriverlo ([Configurazione e Gestione Parametri](/guide/configurazione-e-gestione-parametri)).

### Un esempio: due società, tre persone

Un gruppo ha due società, ALFA e BETA. Anna è super admin senza assegnazione, Bruno è operatore di ALFA, Carla è
operatrice di BETA.

* Bruno entra e lavora in ALFA: vede i clienti e le fatture di ALFA, e quello che crea nasce in ALFA. I dati di BETA
  per lui non esistono.
* Carla, lo stesso in BETA.
* Anna, al primo accesso, sceglie ALFA. Vede ciò che vede Bruno e crea in ALFA. Passa a «Tutti gli emittenti» per un
  controllo d'insieme: vede ALFA e BETA insieme, ma per emettere una fattura di BETA sceglie BETA in alto.
* Se Anna assegnasse sé stessa a BETA, diventerebbe un'amministratrice di BETA: niente più scelta in alto, niente più
  dati di ALFA. Se è l'ultima super admin, il drawer non glielo lascia fare.

---

## Che cosa è rifiutato

| Situazione | Codice |
| --- | --- |
| Sigla vuota, troppo corta o lunga, con caratteri diversi da lettere e cifre | `E_EMITTENTE_CODICE_FORMA_NON_VALIDA` |
| Sigla modificata dopo la creazione | `E_CODICE_NON_MODIFICABILE` |
| Emittente spostato su un altro soggetto | `E_EMITTENTE_SOGGETTO_IMMUTABILE` |
| Conferma del regime scritta a mano | `E_EMITTENTE_REGIME_CONFERMA_DERIVATA` |
| Una chiave che la creazione non conosce | `E_CAMPO_NON_AMMESSO` |
| Cancellazione dell'emittente | `E_DELETE_NOT_ALLOWED` |
| Spegnimento con righe collegate ancora vive | `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, `E_ATTIVO_BLOCK_CHILDREN_EXIST` |
| Una riga nuova sotto un emittente spento | `E_ATTIVO_PADRE_NON_ATTIVO` |
| Nessun gestore globale, con almeno un emittente (solo da una via di servizio: la sua riga non si toglie) | `E_EMITTENTE_DEFAULT_SINGLETON` |
| Un secondo gestore globale | violazione dell'indice unico `uq_emittenti_fiscali_ba_default` |
| L'azienda chiesta per un id che non è un billing account | `E_BILLING_ACCOUNT_NOT_FOUND` |
| I parametri d'importo chiesti per un ruolo che non è un emittente | `E_PARAMETRO_INVALIDO` |
| Un billing account con documenti, anche in bozza, che cambia azienda | `E_BA_EMITTENTE_CON_STORIA` |
| Il collegamento di un billing account, o la riga del gestore globale, cancellato | `E_BA_COLLEGAMENTO_NON_SI_TOGLIE` |
| Il collegamento passato a un altro billing account, o trasformato in gestore globale (o il contrario) | `E_BA_COLLEGAMENTO_NON_SI_SPOSTA` |
| Un billing account cancellato | `E_BA_NON_SI_CANCELLA` |
| Un billing account che nasce senza nessun emittente nell'installazione | `E_EMITTENTE_DEFAULT_MISSING` |
| Una valuta che non è nel catalogo | violazione di chiave esterna verso `config.valute` |
| Un albero di billing account su due aziende | `E_ALBERO_EMITTENTE_MISTO` |
| I billing account di un'istanza su due aziende | `E_ISTANZA_EMITTENTI_DIVERSI` |
| Un billing account creato in «Tutti gli emittenti» | `E_BA_ADMIN_GLOBALE_VIETATO` |
| Una riga nuova senza un'azienda di lavoro | `E_EMITTENTE_NON_RISOLTO` |
| Una riga, o un suo riferimento, di un'altra azienda | `E_SCOPE_EMITTENTE`, `E_RIFERIMENTO_DI_ALTRO_EMITTENTE` |
| Un operatore assegnato a più di un'azienda | `E_OPERATORE_SCOPE_MULTI_NON_AMMESSO` |
| «Tutti gli emittenti» per un operatore che non è super admin | `E_OPERATORE_SCOPE_GLOBALE_SOLO_SUPER_ADMIN` |
| L'assegnazione cambiata da chi non è super admin | `E_PERMESSO_NEGATO` |
| L'ultimo super admin assegnato a un'azienda | `E_PROFILO_ULTIMO_SUPER_ADMIN` |
| L'assegnazione di un utente attivo cancellata fuori dal verbo | `E_USER_EMITTENTE_DELETE_VIETATO` |
| Un emittente di lavoro spento o fuori dal perimetro dell'utente | `E_EMITTENTE_ATTIVO_NON_VALIDO` |

I testi dei messaggi stanno in `config.messaggi_errore`
([Messaggi di Errore e Generazione Log](/guide/Messaggi-di-Errore-e-Generazione-Log)).

---

## Che cosa oggi non copre

* **Fatture e commesse non fermano lo spegnimento.** I documenti che nominano l'azienda col ruolo `EF` (fatture,
  commesse, registri, listini, lotti di fatturazione) non sono fra le righe che il controllo dello spegnimento
  guarda: un emittente con fatture aperte si spegne, uno con un ordine no.

---

## Buone pratiche

* **Prima l'emittente, poi gli operatori.** Un'installazione nuova: il super admin crea gli emittenti, poi assegna
  ogni operatore al suo. Il percorso completo sta in [Preparare ZeroERP all'uso](/configurazione-iniziale).
* **Scegliere la sigla una volta**: corta, leggibile, stabile. Non si cambia.
* **Dichiarare il regime** alla creazione, e tenere vuota `dbops.vw_emittenti_regime_non_confermato`.
* **Configurare i registri delle fatture** subito dopo la creazione, prima della prima fattura.
* **Assegnare subito ogni operatore nuovo** al suo emittente: finché non lo è, non vede niente. «Globale» è la
  modalità del super admin, e per un operatore normale il database non la ammette.
* **Lavorare dentro un emittente** quando si crea; «Tutti gli emittenti» serve a guardare.
* **Controllare gli utenti tecnici** dei processi quando si aggiunge un emittente (`dbops.vw_emittenti_non_serviti`).

---

## I test

* `db/pgtap/anagrafiche/test-fn-crea-emittente-fiscale-v1.sql` — la creazione: il ruolo `EF`, i valori proposti, il
  regime RF01 non confermato, la conferma del regime dichiarato, i registri, le chiavi rifiutate, i doppioni.
* `db/pgtap/anagrafiche/test-emittenti-fiscali.sql` — il primo emittente fa nascere il gestore globale, il billing account
  che nasce collegato, il cambio d'azienda fatto modificando il collegamento, lo spegnimento respinto.
* `db/pgtap/anagrafiche/test-emittenti-fiscali-codice-forma.sql` — la forma della sigla.
* `db/pgtap/anagrafiche/test-emittente-soggetto-immutabile-v1.sql` — l'emittente resta sul suo soggetto.
* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql`, `test-ba-storia-qualunque-documento-v1.sql`,
  `test-guard-albero-ba-omogeneo-v1.sql` — i cancelli dei billing account: la storia (anche una bozza), l'albero, e
  lo spostamento del gestore globale che non tocca nessuno.
* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — il billing account nasce sempre collegato, il
  collegamento non si cancella né si sposta, il billing account non si cancella.
* `db/pgtap/anagrafiche/test-valuta-fk-billing-account-emittente-v1.sql` — la valuta dell'emittente e del billing
  account esiste nel catalogo.
* `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` — il collegamento alla nascita del billing account, e
  il divieto in «tutti».
* `db/pgtap/script/test-fn-change-user-emittenti-scope.sql` — l'assegnazione: un emittente o nessuno, mai due,
  l'ultimo super admin.
* `db/pgtap/config/test-user-emittenti-fiscali-immutable.sql`, `test-porta-scope-emittenti-v1.sql` — l'assegnazione
  non si riscrive e non si cancella fuori dal verbo.
* `db/pgtap/script/test-scope-emittenti-fail-closed-v1.sql` — l'operatore senza assegnazione non vede nulla.
* `db/pgtap/script/test-emittente-attivo-impersonazione-scope.sql` — l'emittente di lavoro restringe, non allarga.
* `db/pgtap/script/test-trgfn-default-emittente-fiscale-v1.sql` — l'azienda di una riga nuova, e il rifiuto in
  «tutti».
* `db/pgtap/vendite/test-registri-per-emittente-v1.sql` — i registri per emittente.

---

## Area tecnica — esempi

**Le aziende attive col regime mai dichiarato** — da tenere vuota:

```sql
SELECT * FROM dbops.vw_emittenti_regime_non_confermato;
```

**Gli operatori che non vedono nessuna azienda** — da assegnare dal drawer dell'operatore:

```sql
SELECT * FROM dbops.vw_operatori_senza_emittente;
```

**Le aziende che un processo automatico non serve** — mancano utenti tecnici:

```sql
SELECT * FROM dbops.vw_emittenti_non_serviti;
```

**Lo stato dell'impianto** — aziende attive e operatori assegnati, come li conta il banner:

```sql
SELECT jsonb_pretty(script.fn_get_setup_status());
```

---

{% include-markdown "signature-core.md" %}
