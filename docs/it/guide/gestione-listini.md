# Guida — Gestione Listini e Pricing

> **Ultimo aggiornamento**: 28 ottobre 2026
>
> **Destinatari**: analisti funzionali, sviluppatori backend/frontend, DBA
>
> **Vedi anche** — schemi DB:
>
> * [vendite.listini](/dbzero/vendite/tabelle/listini) / [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) / [vendite.listini_righe](/dbzero/vendite/tabelle/listini_righe)
> * [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti) + [categorie_clienti_listini](/dbzero/anagrafiche/tabelle/categorie_clienti_listini)
> * [vendite.contratti](/dbzero/vendite/tabelle/contratti) + [contratti_righe](/dbzero/vendite/tabelle/contratti_righe) + [contratti_utilities](/dbzero/vendite/tabelle/contratti_utilities)
> * [vendite.promo_articoli](/dbzero/vendite/tabelle/promo_articoli)
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) (BoM versionata immutabile)
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
>
> **Vedi anche** — API e service backend:
>
> * [PricingService (backend)](/backend/vendite/manual/pricing_service)
> * [API Pricing (resolver + limiti L2)](/backend/vendite/manual/api_pricing)
> * [API Approvazioni prezzo (workflow L3)](/backend/vendite/manual/api_approvazioni_prezzo)
> * [API Preventivi](/backend/vendite/manual/api_preventivi) (con flag `richiesta_approvazione` per L3)
> * [API Contratti](/backend/vendite/manual/api_contratti) / [API Promo articoli](/backend/vendite/manual/api_promo_articoli) / [API Matrice categorie/listini](/backend/anagrafiche/manual/api_categorie_clienti_listini)
>
> **Vedi anche** — guide correlate:
>
> * [Il modello del documento di vendita](/guide/modello-documento-di-vendita) — **le regole comuni a tutti i documenti**: nascita, cambio di stato, permesso sul passaggio, emissione, annullo
> * [Gestione Preventivi](/guide/gestione-preventivi) — dove il prezzo viene sovrascritto (L1/L2/L3)
> * [Gestione Commesse](/guide/gestione-commesse) — dove lo snapshot pricing vive
> * [Fatturazione](/guide/fatturazione) — la propagazione dello snapshot alle righe fatturabili
> * [Modello pre-v5 (archivio)](archive/gestione-listini-pre-v5.md) — la versione precedente, per riferimento storico

---

## 1. Cosa risponde il sistema pricing

> *"Quanto costa questo articolo, per questo cliente, in questa data, per questa utility?"*

Il sistema pricing v5 risponde deterministicamente attraverso **3 stadi** valutati in sequenza:

1. **STADIO 0 — PROMO**: esiste una promozione temporanea attiva su quella coppia (articolo, uom)? Se sì, vince.
2. **STADIO 1 — CONTRATTO**: il cliente ha un contratto individuale attivo? Se sì, il prezzo viene dal contratto (modalità A/B/C).
3. **STADIO 2 — CATEGORIA**: in assenza di contratto, il cliente ha una categoria commerciale? Se sì, la matrice categoria→listino determina il prezzo base.

Non ci sono tie-break: la struttura dati **garantisce** che ogni stadio produca al massimo una risposta.

---

## 2. Le entità in gioco

### 2.1 Listino

È un **contenitore di prezzi** identificato dalla combinazione:

* `utility_id` — il servizio (Gas, Energia, Idrico, "Base" per commercio)
* `tipologia_id` — la categoria di voce (CONSUMO, QUOTA_FISSA, IMPOSTA, ONERE_SISTEMA, PRODOTTI, SERVIZI)
* `emittente_soggetto_ruolo_id` — chi emette la fattura (dimensione interna)

**Un solo listino** per ogni quadrupla (utility, tipologia, emittente, codice). Non esistono "listini derivati": le variazioni commerciali vivono altrove.

Un listino contiene:

* **Versioni** (`listini_versioni`) — finestre temporali con stato BOZZA → ATTIVA → CHIUSA. Per ogni data al più una versione in vigore (ATTIVA o CHIUSA) per listino (vincolo `EXCLUDE`).
* **Righe** (`listini_righe`) — per ogni versione: (articolo, uom) → prezzo. Forma pura, senza dimensioni di scope.

⭐ **Come finisce un listino.** Dipende dalla sua **storia**: un listino ha storia se ha
almeno una versione che è stata attivata (oggi ATTIVA o CHIUSA, anche spenta); una bozza
non conta ([vendite.fn_listino_ha_storia](/dbzero/vendite/funzioni/fn_listino_ha_storia)).

* **Senza storia** (nessuna versione, o solo bozze) si spegne con l'interruttore «Attivo».
* **Con storia** non si spegne: ha dato prezzi ai documenti, e quei prezzi devono restare
  riproducibili. Si chiude mettendo la **fine validità** alla versione in vigore: alla
  scadenza la versione passa CHIUSA. Chi prova a spegnerlo riceve
  `E_LISTINO_CON_STORIA_NON_SPEGNIBILE`, con questo rimedio.
* Una versione CHIUSA ha **sempre** la fine validità: è un periodo di prezzi finito.

⭐ **Lo stato di una versione** segue il [modello del documento di vendita](/guide/modello-documento-di-vendita):
gli stati sono un vocabolario ([config.stati_doc_listino_versioni](/dbzero/config/tabelle/stati_doc_listino_versioni)),
i passaggi una matrice ([config.transizioni_stati_listino_versioni](/dbzero/config/tabelle/transizioni_stati_listino_versioni)),
e lo stato lo cambiano solo due operazioni del database.

* **Attiva** ([vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino)), con
  l'azione `attiva_listino`: la versione deve essere accesa e avere almeno un prezzo (una riga, o un
  composito col prezzo bundle); le versioni attive precedenti che si sovrappongono si chiudono il giorno
  prima della decorrenza nuova, nella stessa operazione. Il dialogo di conferma mostra quali, dallo stesso
  lettore ([vendite.fn_versioni_listino_da_chiudere](/dbzero/vendite/funzioni/fn_versioni_listino_da_chiudere)).
* **La chiusura a scadenza**: una versione ATTIVA con la fine validità passata diventa CHIUSA col job
  della chiusura per scadenza ([vendite.fn_chiudi_versioni_listino_scadute](/dbzero/vendite/funzioni/fn_chiudi_versioni_listino_scadute)).
  Fra la scadenza e il passaggio del job la versione è ATTIVA con la chiusura programmata.

Che cosa si cambia in ogni stato: in **bozza** tutto, e la versione si può eliminare; di una versione
**attiva** solo la fine validità; di una **chiusa** niente. Una versione nasce sempre in bozza.
Per cambiare i prezzi di una versione in uso si crea una versione nuova (anche clonandola) e la si attiva.

### 2.2 Categoria cliente

Rappresenta la **politica commerciale trasversale** (STANDARD, BASE, SILVER, GOLD, PLATINUM).

Caratteristiche:

* ogni `billing_account` ha esattamente una `categoria_cliente_id` (default STANDARD)
* la categoria decide se il cliente **partecipa alle promo** (flag `partecipa_promo`)
* la categoria indirizza al listino corretto via la **matrice**

### 2.3 Matrice categoria → listino

Tabella `anagrafiche.categorie_clienti_listini`. Per ogni quadrupla:

```text
(categoria_cliente, utility, emittente, classe_utenza opz.) → listino + variazione opz.
```

La variazione è opzionale (`tipo_variazione` + `valore_variazione`, coppia coerente):

* `PERCENTUALE` — firmata (negativo = sconto, positivo = maggiorazione)
* `VALORE_FISSO` — firmato
* Nessuna variazione → prezzo base del listino tal quale

`classe_utenza_id` è opzionale: la ricerca prova prima il match esatto poi il fallback a NULL (dimensione pricing per utility con gradazione, es. DOM-BTA su energia).

Vincolo `EXCLUDE`: non possono esistere due righe attive sovrapposte per la stessa quadrupla → il resolver STADIO 2 non ha ambiguità.

### 2.4 Contratto

È l'**accordo individuale** tra cliente ed emittente. Tre modalità possibili:

| Modalità                            | Listino | Variazione globale | Righe override                  | Quando usarla                             |
| ----------------------------------- | ------- | ------------------ | ------------------------------- | ----------------------------------------- |
| **A** — listino + variazione        | sì      | sì                 | vuote o parziali                | "Listino standard 2026 scontato 10%"      |
| **B** — listino con override mirati | sì      | sì o no            | alcune righe con prezzo forzato | "Listino standard, ma art X a €50 fisso"  |
| **C** — interamente negoziato       | no      | no                 | tutte le righe con prezzo       | Grande cliente con condizioni 100% custom |

Un trigger DB blocca la transizione DRAFT → ATTIVO se la modalità C ha righe vuote (errore `E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE`).

### 2.5 Promo

Tabella `vendite.promo_articoli`. È un **overlay temporale** indipendente:

* (articolo, uom, validità) → tipo e valore variazione
* batte qualsiasi altro stadio se il cliente appartiene a una categoria con `partecipa_promo = true`
* ammette `PREZZO_FISSO` (prezzo assoluto sostitutivo) — vietato negli altri stadi
* non si crea su un articolo **solo componente**: un articolo che si vende solo dentro un kit non
  ha un prezzo suo, e dentro un kit le promo non si applicano. Il kit invece la promo la può
  avere: la riceve quando il contratto gli dà un prezzo suo. Nella ricerca dell'articolo della
  promo un solo componente compare in grigio, col motivo, e non si sceglie

---

## 3. Resolver — i 3 stadi in dettaglio

La funzione `vendite.fn_resolve_prezzo_listino_v2` riceve:

* articolo, uom, data, billing_account
* utility, emittente (derivato dal JWT dell'operatore, 1-a-1)
* classe_utenza (opzionale, derivata da contratto o istanza)

### STADIO 0 — Promo overlay

```text
Esiste riga in promo_articoli (articolo, uom, data) attiva?
  E la categoria del BA ha partecipa_promo = true?
    → SÌ: prezzo_base = STADIO 1/2, applica variazione promo → STOP
           origine = PROMO
    → NO: vai allo STADIO 1
```

### STADIO 1 — Contratto

```text
Esiste contratto ATTIVO per (ba, utility, data)?
  → SÌ:
      Esiste riga override per (articolo, uom) con prezzo_unitario NOT NULL?
        → SÌ: prezzo = prezzo_unitario; origine = CONTRATTO_OVERRIDE
        → NO: se contratto ha listino_id (modalità A o B senza override):
               prezzo_base = riga listino
               applica variazione_globale se presente
               origine = CONTRATTO_LISTINO
             altrimenti (modalità C senza riga):
               ERRORE E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C
  → NO: vai allo STADIO 2
```

### STADIO 2 — Categoria cliente

```text
BA ha categoria_cliente_id (sempre sì: default STANDARD)?
  → SÌ:
      Cerca in matrice (categoria, utility, emittente, data):
        - prima: classe_utenza_id = <derivato>
        - fallback: classe_utenza_id IS NULL
      Se nessun match: ERRORE E_CATEGORIA_LISTINO_NON_MAPPATA
      Altrimenti:
        prezzo_base = riga listino
        applica variazione matrice se presente
        origine = CATEGORIA
```

### Output

Il resolver ritorna sempre:

* `prezzo` (persistito su `commesse_attivita.prezzo_snapshot`) e `prezzo_base_snapshot`
* `origine_prezzo` ∈ `{PROMO, CONTRATTO_OVERRIDE, CONTRATTO_LISTINO, CATEGORIA, MANUALE}`
* `tipo_variazione_applicata` ∈ `{PERCENTUALE, VALORE_FISSO, PREZZO_FISSO, NESSUNA}`, `valore_variazione_applicata`
* FK popolate del caso: `listino_versione_id` + `listino_riga_id`, `contratto_id`, `promo_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`

Su ogni riga `vendite.commesse_attivita` vengono persistite **8 nuove dimensioni snapshot v5** (`prezzo_base_snapshot`, `origine_prezzo`, `tipo_variazione_applicata`, `valore_variazione_applicata`, `promo_id`, `contratto_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`), che si aggiungono ai campi pricing già presenti nel modello operativo (`prezzo_snapshot`, `prezzo_bloccato`, `listino_versione_id`, `listino_riga_id`, `pricing_mode`, `prezzo_da_riallineare`). Il ciclo di vita di questi ultimi è descritto nel §7.

Le stesse 8 dimensioni sono propagate su `vendite.attivita_fatturabili` all'emissione, preservando la tracciabilità fino alle righe fattura.

---

## 4. Convenzione segno delle variazioni

Le variazioni di tipo `PERCENTUALE` e `VALORE_FISSO` sono **firmate**:

| Valore                 | Effetto                                         |
| ---------------------- | ----------------------------------------------- |
| **Negativo** (es. -10) | Sconto (10%  di riduzione o -10€ di correzione) |
| **Positivo** (es. +5)  | Maggiorazione                                   |
| **Zero**               | Vietato dal service (no-op inutile)             |

`PREZZO_FISSO` (ammesso solo in promo) è un prezzo assoluto ≥ 0 che **sostituisce** il prezzo base.

Formule applicate dal resolver:

```text
PERCENTUALE:  prezzo_finale = prezzo_base × (1 + valore / 100)
VALORE_FISSO: prezzo_finale = prezzo_base + valore
PREZZO_FISSO: prezzo_finale = valore
```

---

## 5. Articoli, tipologia e BoM

### 5.1 Tipologia articolo

Ogni articolo ha `listino_tipologia_id` (FK a `config.listini_tipologie`). Un articolo può essere inserito solo in listini con la **stessa tipologia** (lo dice la check per tipo di riga `script.fn_check_articolo_riga`, che il guard `trg_listini_righe_a10_guard_articolo_ammesso_ins_upd` solleva; dal 2026-10-13 anche: niente articoli «solo componente», e un kit entra coi suoi componenti).

Nella ricerca dell'articolo di una riga di versione trovi prima gli articoli che la versione
può usare; gli altri compaiono in grigio, col motivo sotto, e non si scelgono. Un **kit**
compare col suo avviso («entra come bundle») ma si sceglie: apre i prezzi dei suoi componenti.
Anche il componente di una distinta si cerca così: un componente con un'IVA diversa da quella
del kit, o il kit stesso, compaiono in grigio col motivo.

Esempi:

* articolo di tipologia `PRODOTTI` → inseribile solo in listini PRODOTTI
* articolo di tipologia `CONSUMO` (voce utility) → solo in listini CONSUMO per quella utility

### 5.2 Distinta base (BoM) — componenti di un kit

Un articolo composito (`is_composito = true`) ha una distinta base in `articoli_componenti`. Dal modello unificato del 2026-05-13 **ogni articolo composito è CASO A**: ogni componente attivo della distinta diventa una **riga negoziabile a se' stante** dentro il documento sorgente — vedi §5.2.1 sotto — e il prezzo del kit è la somma dei componenti. Al push, la pipeline espande l'articolo composito in N righe `commesse_attivita` separate. CASO B resta il nome dell'articolo **non** composito, con il suo prezzo unico.

**Una distinta contiene solo articoli semplici.** Un kit non può contenere un altro kit: vendita, magazzino e fattura leggono i componenti diretti, e i componenti di un kit interno resterebbero invisibili. Se serve, si mettono nella distinta direttamente i componenti del kit interno. Per la stessa ragione un articolo che è componente di una distinta, in vigore o che entrerà in vigore, non si può marcare composito: nel form il campo è spento.

**Come si vede il componente in fattura** è un'altra scelta della distinta, per singolo componente: l'**esposizione in fattura**. Non cambia né il prezzo né le righe del documento, solo cosa legge il cliente:

| Esposizione | Cosa vede il cliente in fattura |
| --- | --- |
| **Nascosto** (il default) | solo il kit: il componente non compare, il suo valore è nel prezzo del kit |
| **Descrittivo** | il componente come riga sotto il kit, **senza prezzo**: il suo valore è nel prezzo del kit |
| **Valorizzato** | il componente come riga sotto il kit **con il suo prezzo e il suo importo**, fuori dal prezzo del kit |

Il totale della fattura è lo stesso nei tre casi. Le regole complete sono nella [guida fatturazione](/guide/fatturazione) (§ *Come si espone un kit*). Fino al 2026-10-01 la scelta era un sì/no («esposto in fattura»: no = nascosto, sì = descrittivo), e fino al 2026-05-13 quel flag decideva anche CASO A / CASO B.

Logica completa in [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2),
che è **bundle-aware** tramite `p_articolo_padre_contesto`: il vecchio
`fn_resolve_prezzo_composito` è stato ritirato e il resolver canonico è uno solo
(cfr. `dev/work-done/brief-db-drop-fn-resolve-prezzo-composito.md`).

#### 5.2.1 Componenti CASO A nel ciclo preventivo → commessa

> **Decisione di dominio 2026-05-11**: il prezzo della riga padre di un
> composito CASO A non e' negoziabile direttamente — e' un valore
> derivato dalla somma dei componenti. Ogni componente esposto vive
> come riga propria, con prezzo proprio risolto dal resolver e
> override manuale ammesso (L1).

**Razionale.** Prima del 2026-05-11 la riga preventivo di un composito
CASO A salvava un `prezzo_unitario` sul padre che pero' veniva
**ignorato silenziosamente al push**: il resolver risolveva N prezzi
per i componenti dal listino e quelli finivano in fattura. Cliente
vedeva X nel preventivo e Y nella fattura. Inoltre, se anche solo un
componente non aveva mappa listino, il push esplodeva **dopo** che
l'utente aveva accettato il preventivo. Bug logico del modello:
asimmetria fra preventivo (prezzo manuale ammesso sul padre) e push
(prezzo manuale ignorato, resolver obbligatorio per ogni componente).

**Modello nuovo**: per ogni documento sorgente che genera commesse
(preventivi, ordini, contratti, DDT, attivita consumi) esiste una
tabella `<sorgente>_righe_componenti` parallela a `<sorgente>_righe`.
Quando l'operatore inserisce una riga su articolo composito CASO A:

1. Il backend chiama `fn_<sorgente>_riga_componenti_init` che invoca
   il resolver e popola un record per ogni componente attivo della distinta, con
   `prezzo_unitario` = prezzo suggerito + `origine_prezzo` (PROMO /
   CONTRATTO_OVERRIDE / CONTRATTO_LISTINO / CATEGORIA — vedi §3).
2. Se il resolver fallisce su un componente (es. listino mancante),
   il componente viene comunque creato con `prezzo_unitario = 0` e
   `origine_prezzo = 'MANUALE'`. L'UI mostra un warning e l'operatore
   digita il prezzo a mano (richiede L1, vedi §6).
3. Il `prezzo_unitario` della riga padre e' **readonly** lato UI e
   ricalcolato automaticamente da un trigger DB come
   `SUM(prezzo_componente × coeff_qta_snapshot)`. Cambia ad ogni
   modifica di componenti.
4. Al push commessa, il `BoMComponentExpander` legge direttamente i
   prezzi gia' fissati su `<sorgente>_righe_componenti` — **senza
   ri-chiamare il resolver**. Snapshot pricing immutabile
   post-accettazione, simmetrico al pattern `prezzo_bloccato`.

**Componenti vs riga padre**: la riga padre composita CASO A esiste
sul documento sorgente come "ricetta" + totale calcolato. I componenti
vivono nella tabella parallela. Ogni componente, qualunque sia la sua
esposizione in fattura, genera 1 riga `commesse_attivita` con `articolo_id = componente_id`,
`quantita = quantita_componente × quantita_padre`, `prezzo_unitario =
quello fissato sul componente preventivo`.

**Cascade quantita padre**: se l'operatore cambia la `quantita` della
riga padre, un trigger DB propaga il ricalcolo della `quantita` di
tutti i componenti come `coeff_qta_snapshot × quantita_padre`. Il
prezzo unitario dei componenti resta invariato.

**Cosa entra nella tabella componenti**: tutti i componenti attivi e
validi della distinta, anche quelli che in fattura resteranno nascosti.
(Fino al 2026-05-13 ne restavano fuori i componenti col flag
`esposto_in_fattura = FALSE`, che contribuivano al prezzo solo via
fallback "somma componenti" del resolver: il modello unificato li ha
portati dentro, e l'esposizione è diventata una regola di sola
presentazione.)

**Workflow L1/L2/L3 sui componenti**: vedi §6.2.

### 5.3 Immutabilità della BoM — pattern "chiudi + nuova versione"

La distinta base è **immutabile nel tempo**: una volta inserita una riga in `articoli_componenti`, i campi di struttura (componente, `coeff_qta`, `esposizione_in_fattura`, `obbligatorio`, `valido_dal`) non possono essere modificati in place. Il trigger DB `trgfn_articoli_componenti_block_modifica_struttura` blocca gli UPDATE con errore `E_BOM_MODIFICA_VIETATA` e le DELETE (una riga BoM non si elimina mai: si chiude).

**Perché**: le commesse e le fatturazioni che hanno già consumato quella BoM restano ancorate alla struttura del momento, e lo snapshot `prezzo_bloccato` sulle righe commessa preserva il calcolo fatto all'epoca. Modificare la BoM "sotto" a una commessa emessa romperebbe la ricostruzione storica.

**Come si correggono errori o si evolve una distinta base**:

1. **Chiudi la riga corrente**: imposta `valido_al = oggi` (l'unico campo editabile in place). Dalla UI: menu kebab della riga → "Chiudi riga", oppure click sulla cella `valido_al` inline.
2. **Inserisci una nuova versione**: dalla UI → menu kebab → "Duplica come nuova versione". Il form si pre-compila con i valori della riga sorgente, `valido_dal = oggi`, `valido_al` vuoto. Modifica i campi desiderati e salva.

L'exclusion constraint daterange `ex_articoli_componenti_no_overlap` sull'indice GiST `(prodotto_id, componente_id, validita)` garantisce che non ci siano sovrapposizioni temporali tra versioni dello stesso componente.

**Campi ancora modificabili in place**: `note`, `meta`, `attivo`, `valido_al` (chiusura). Non sono campi di struttura.

---

## 6. Autorizzazioni override prezzo (L1)

Nel preventivo, il prezzo suggerito dal resolver può essere **sovrascritto manualmente** dall'operatore. L1 è attivo:

* Se il payload riga ha `prezzo_unitario` uguale al suggerito → passa sempre
* Se è diverso → il service verifica l'azione processo `prezzo_override_manuale`
  * Autorizzato: salva con origine `MANUALE`, traccia in `meta` il resolver originale
  * Non autorizzato: `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` (403)

Il badge UI mostra l'origine del prezzo (`PROMO` / `CONTRATTO_OVERRIDE` /
`CONTRATTO_LISTINO` / `CATEGORIA` / `MANUALE`) e il delta eventuale.

L2 (limite sconto/maggiorazione %) è attivo: vedi `VENDITE_MAX_SCONTO_PCT` / `VENDITE_MAX_MAGGIORAZIONE_PCT` in `config.parameters` e l'endpoint diagnostico `GET /vendite/pricing/limiti-utente/`.

### 6.1 L1/L2/L3 sui componenti BoM CASO A

> **Eccezione al §6**: su articoli compositi CASO A (vedi §5.2.1)
> l'override L1 si applica **sui singoli componenti**, non sul
> prezzo padre. Il prezzo padre e' un valore calcolato readonly. Solo
> i componenti sono righe negoziabili.

Stesso flusso L1 della riga normale, applicato alla riga componente:

* Se `prezzo_unitario` del componente = suggerito dal resolver → passa
* Se diverso → service verifica `prezzo_override_manuale`
  * Autorizzato: salva con `origine_prezzo = 'MANUALE'`, traccia in
    `prezzo_resolver_context` JSONB il suggerito originale + delta
  * Non autorizzato: `E_PREZZO_OVERRIDE_NON_AUTORIZZATO` (403)

**Listino mancante sul componente**: caso speciale del L1. Quando il
resolver fallisce su un componente al popolamento iniziale (es.
`E_CATEGORIA_LISTINO_NON_MAPPATA`), il componente viene creato con
`prezzo_unitario = 0`, `origine_prezzo = 'MANUALE'`,
`prezzo_resolver_context.error = '<codice_errore>'`. L'UI mostra
warning inline "listino mancante" e l'operatore digita il prezzo a
mano. Se ha `prezzo_override_manuale` passa, altrimenti errore L1
classico (e deve far aggiungere il listino prima di proseguire).

**L2 sui componenti**: stessi parametri di sistema della riga padre
(`VENDITE_MAX_SCONTO_PCT`, `VENDITE_MAX_MAGGIORAZIONE_PCT`). Il delta %
e' calcolato componente per componente vs il suo suggerito.

**L3 sui componenti**: workflow approvazione PENDING/APPROVED/REJECTED
opera anche su `<sorgente>_righe_componenti.stato_approvazione_prezzo`.
Dal 2026-09-24 un solo componente attivo PENDING o REJECTED blocca
l'uscita dalla bozza e l'accettazione del documento sorgente (es.
preventivo → EMESSO e → ACCETTATO): lo decide
[`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati),
chiesto dal guard di transizione di ogni documento. La
modifica della struttura del componente PENDING e' bloccata da
`trgfn_<sorgente>_righe_componenti_guard_pending` (simmetrico al guard
della riga padre).

### 6.2 L3 — Workflow approvazione out-of-policy

Quando l'operatore richiede un prezzo che viola i limiti L2, può **richiedere approvazione al responsabile** invece di rinunciare. Il flusso:

1. **Riga oltre L2 + flag `richiesta_approvazione=true`**: il backend NON solleva errore. Crea una pratica `APPROVAZIONE_PREZZO` (stato APERTA, priorità NORMALE) e salva la riga con `stato_approvazione_prezzo='PENDING'` collegata alla pratica via `pratica_approvazione_prezzo_id`.
2. **Email best-effort al recipient configurato** in `VENDITE_APPROVAZIONE_PREZZO_RECIPIENT_EMAIL` (parameter scope user/group/emittente). Se il parameter non è configurato, la pratica resta visibile in coda senza notifica push.
3. **L'approver** (utente con azione `approva_prezzo_override` abilitata) vede la coda in `/vendite/approvazioni-prezzo/` filtrata per scope emittente. Per ogni pratica può:
   * **Approvare** → riga `stato_approvazione_prezzo='APPROVED'`, pratica CHIUSA con nota interna OK
   * **Rifiutare** → riga `stato_approvazione_prezzo='REJECTED'`, pratica CHIUSA con nota interna KO + motivazione

**Trigger DB di guardia**:

* [`script.fn_check_prezzi_autorizzati`](/dbzero/script/funzioni/fn_check_prezzi_autorizzati) (dal 2026-09-24): un prezzo in attesa (`PENDING`) o rifiutato (`REJECTED`), su righe o componenti BoM attivi, blocca l'uscita dalla bozza e l'accettazione di preventivi, contratti, offerte, ordini e DDT (`E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`); l'annullamento resta sempre possibile. Sul preventivo la chiede [`vendite.trgfn_preventivi_guard_transizione`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_transizione), che ha preso il posto del trigger ritirato `trgfn_preventivi_guard_transizione_approvazione`
* `trgfn_preventivi_righe_guard_pending`: blocca modifica struttura riga PENDING; permette solo transizione di stato approvazione (`E_RIGA_PREZZO_PENDENTE`)

**Endpoint API**:

* `POST /api/v1/vendite/righe/<riga_id>/approva-prezzo/` (body `{nota?}`)
* `POST /api/v1/vendite/righe/<riga_id>/rifiuta-prezzo/` (body `{motivazione?}`)
* `GET /api/v1/vendite/approvazioni-prezzo/?limit=&offset=`

**Riavvio richiesta**: se l'approver rifiuta, l'utente può modificare il prezzo (riga REJECTED non è bloccata) e ri-tentare. Una nuova violazione L2 con `richiesta_approvazione=true` crea una nuova pratica.

---

## 7. Ciclo di vita del prezzo sulla riga commessa

Il resolver calcola il prezzo al **momento del push sorgente → commessa**. Da quel momento il prezzo vive sulla riga `commesse_attivita` con un piccolo set di stati operativi che ne governano riallineamento, blocco manuale e segnalazioni di revisione. Questo layer è distinto dal resolver (non lo invoca più) e opera esclusivamente su commesse in stato `modificabile` e righe **non ancora fatturate**.

### 7.1 Flag di stato pricing su `commesse_attivita`

| Campo                   | Tipo    | Default   | Ruolo operativo                                                                                        |
| ----------------------- | ------- | --------- | ------------------------------------------------------------------------------------------------------ |
| `prezzo_snapshot`       | numeric | —         | Prezzo corrente della riga (output del resolver o override manuale)                                    |
| `prezzo_bloccato`       | boolean | `FALSE`   | Se `TRUE`, il prezzo è "congelato" da override manuale: il riallineamento automatico/massivo lo salta  |
| `prezzo_da_riallineare` | boolean | `FALSE`   | Segnalazione: il prezzo di listino è cambiato rispetto allo snapshot e la riga è candidata a revisione |
| `pricing_mode`          | varchar | `'FIXED'` | Predisposizione per modalità di calcolo future (`FORMULA`, `SCAGLIONI`). Oggi solo `FIXED` è operativo |
| `listino_versione_id`   | bigint  | —         | Versione listino risolta al momento dello snapshot (serve al guard di riallineamento — vedi §7.3)      |

### 7.2 Variazione prezzo eccezionale — blocco manuale (N7)

**Scopo**: permettere all'operatore di forzare un prezzo fuori dalle regole di listino/contratto/promo per una singola riga, con motivo obbligatorio.

Endpoint: `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/variazione-prezzo-eccezionale/`
Service: `commesse_service.fn_variazione_prezzo_eccezionale` — endpoint e regole in [API Commesse pricing](/backend/vendite/manual/api_commesse_pricing)

Effetti:

* aggiorna `prezzo_snapshot = nuovo_prezzo`
* imposta `prezzo_bloccato = TRUE` (d'ora in poi il riallineamento salta la riga)
* appende una entry a `meta.variazioni_eccezionali` con `data`, `prezzo_precedente`, `prezzo_nuovo`, `motivo`, `stato_commessa`, `listino_versione_id_riferimento`
* scrive `origine_prezzo = 'MANUALE'` e azzera la provenienza da listino (`listino_versione_id`, `prezzo_base_snapshot`, variazione, promo, contratto, categoria, classe utenza): un prezzo deciso dall'operatore non ha una base di listino

Precondizioni: commessa `modificabile`, riga non fatturata. Il servizio non invoca il resolver: il prezzo è deciso dall'operatore.

### 7.3 Riallineamento dal listino

**Scopo**: ricalcolare il prezzo di una riga quando il listino è cambiato rispetto allo snapshot originale.

Endpoint: `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/riallinea-prezzo/`
Service: `fn_riallinea_prezzo`

Flusso:

1. Guard: se `prezzo_bloccato = TRUE` → errore `E_COMMESSA_VALIDATION` (per ricalcolare bisogna prima sbloccare — §7.4).
2. Invoca il resolver (`PricingService.resolve_prezzo`) sul contesto della riga: articolo, uom, data (`data_attivita`, o `competenza_mese` se manca), BA, utility, emittente, e il kit di cui la riga è componente (`meta.componente_di`). È lo stesso contesto che usa il push sorgente → commessa: lo costruisce un building block solo (`prezzo_riga_commessa`).
3. Se la **versione listino** è cambiata rispetto allo snapshot e il payload non contiene `conferma_versione_diversa=true`, ritorna un body di pre-conferma con `versione_originale_id`, `versione_attuale_id`, `prezzo_attuale`, `prezzo_ricalcolato`, `richiede_conferma=true`: l'UI chiede conferma all'operatore prima di procedere.
4. In caso di conferma (o versione invariata): aggiorna `prezzo_snapshot` con il nuovo valore e, insieme, la sua provenienza (`listino_versione_id`, `prezzo_base_snapshot`, `origine_prezzo` e gli altri campi di audit), tiene `prezzo_bloccato = FALSE`, appende a `meta.riallineamenti` la storia del cambio (`data`, `prezzo_precedente`, `prezzo_nuovo`, `listino_versione_id_precedente`, `listino_versione_id_nuovo`). Poiché la versione si aggiorna, il riallineamento successivo non chiede più conferma.

La versione «dello snapshot» è quella che il push registra sulla riga quando la crea: la versione da cui, alla data della riga, verrebbe il prezzo.

Il flag `prezzo_da_riallineare` viene azzerato come side-effect: la riga è allineata.

### 7.4 Sblocco prezzo bloccato (N7-sblocco)

**Scopo**: rimuovere un blocco da variazione eccezionale e tornare al prezzo di listino corrente.

Endpoint: `POST /api/v1/vendite/commesse/<commessa_id>/attivita/<att_id>/sblocca-prezzo/`
Service: `fn_sblocca_prezzo`

Effetti:

* guard: errore `E_VENDITE_SBLOCCO_PREZZO_NON_AMMESSO` se la riga non è bloccata
* ricalcola dal resolver (come §7.3 ma senza guard versione)
* imposta `prezzo_snapshot = ricalcolato`, `prezzo_bloccato = FALSE`, e riscrive la provenienza dal resolver
* appende a `meta.sblocchi_prezzo` (`data`, `prezzo_bloccato_precedente`, `prezzo_ricalcolato`, `motivo`)

Motivo obbligatorio come per il blocco.

### 7.5 Dashboard "prezzi da riallineare"

La funzione [`vendite.fn_get_commessa_stato`](/dbzero/vendite/funzioni/fn_get_commessa_stato) espone il contatore `total_prezzo_da_riallineare` per ogni commessa: conta le righe con `prezzo_da_riallineare = TRUE` e alimenta la coda di revisione prezzi nella dashboard commesse.

### 7.6 Propagazione a `attivita_fatturabili`

All'emissione (`fn_emit_attivita_fatturabili_da_commessa`) il flag `prezzo_bloccato` e lo snapshot pricing vengono **propagati** sulla riga AF. Questo garantisce che:

* gli step della pipeline fatturazione non sovrascrivano un prezzo manualmente bloccato;
* lo snapshot resolver (8 dimensioni v5) resti tracciabile fino alla riga fattura.

Vedi [guida fatturazione §"Snapshot pricing su commessa"](fatturazione.md#snapshot-pricing-su-commessa-e-propagazione-ad-af).

### 7.7 Su `pricing_mode`

Il campo ha dominio CHECK `FIXED | FORMULA | SCAGLIONI` ed è predisposto per estensioni future del motore pricing (calcolo a formula su variabili di commessa, tariffe a scaglioni). **Oggi tutte le funzioni sorgente → commessa producono esclusivamente `FIXED`**: non esiste implementazione operativa per le altre due modalità. Le righe nate da `FIXED` sono quelle descritte nei §§3–6 (resolver v5 deterministico).

---

## 8. Ciclo di vita operativo

### 8.1 Nuovo listino

1. Admin: crea listino (codice, descrizione, utility, tipologia) — emittente derivato dall'operatore
2. Crea versione BOZZA con `valido_dal`
3. Popola righe prezzo (articoli coerenti con tipologia)
4. Attiva versione → BOZZA passa ad ATTIVA; le versioni precedenti che si sovrappongono si chiudono il giorno prima (§2.1)

### 8.2 Assegnare un listino a un cliente (scope categoria)

1. Definisci la categoria cliente (STANDARD, SILVER, GOLD…)
2. Imposta sul `billing_account` la `categoria_cliente_id`
3. Admin: crea riga matrice per (categoria, utility, emittente, classe_utenza opz.) → listino + variazione

Tutti i clienti della stessa categoria, utility, emittente condivideranno la regola senza duplicare listini.

### 8.3 Contratto individuale

1. Commerciale: stipula contratto con BA, scegliendo modalità A/B/C
2. Inserisce righe (se C: obbligatorie per ogni articolo preventivabile)
3. Transizione DRAFT → ATTIVO → il resolver STADIO 1 userà il contratto

### 8.4 Promo

1. Admin vendite: crea riga in `promo_articoli` (articolo, uom, periodo, tipo+valore variazione, codice)
2. La promo vale per tutti i BA con categoria che partecipa promo
3. A scadenza periodo (`valido_al`), la promo smette di applicarsi automaticamente

---

## 9. Garanzie DB

Il database rafforza la determinismo con vincoli espliciti (non è "responsabilità del client"):

| Vincolo                                       | Tabella                     | Cosa garantisce                                                               |
| --------------------------------------------- | --------------------------- | ----------------------------------------------------------------------------- |
| `ex_contratti_no_overlap`                     | `contratti`                 | Un solo contratto attivo per (BA, istanza, utility, ambito) nel periodo       |
| `ex_categ_cli_listini_no_overlap`             | `categorie_clienti_listini` | Una sola riga matrice per (categoria, utility, emittente, classe) nel periodo |
| `ex_promo_articoli_no_overlap`                | `promo_articoli`            | Una sola promo attiva per (articolo, uom) nel periodo                         |
| `ex_listini_versioni_no_overlap`              | `listini_versioni`          | Una sola versione in vigore (ATTIVA o CHIUSA) per listino nel periodo         |
| `uq_listini_righe_key_attiva`                 | `listini_righe`             | Una sola riga attiva per (versione, articolo, uom)                            |
| `script.fn_check_articolo_riga` (guard `script.trgfn_righe_guard_articolo_ammesso`) | check + trigger | Articolo e listino della stessa tipologia; niente solo componente; il kit coi componenti (dal 2026-10-13) |
| `trgfn_contratti_modalita_c_righe_complete`   | trigger                     | Modalità C: attivazione blocca se righe incomplete                            |
| `script.fn_check_articolo_riga` (guard su `promo_articoli`) | check + trigger | Nessuna promo su un articolo solo componente (dal 2026-10-14) |
| `trgfn_contratti_utilities_guard_tipo_classe` | trigger                     | Tipo/classe utenza coerenti con ambito (NULL per COMMERCIO)                   |

Il resolver poggia su queste invarianti — il codice Python non deve duplicarle.

---

## 10. Errori espliciti

Nessun fallback silenzioso. Ogni scenario non risolvibile produce un errore strutturato:

| Codice                                    | Quando                                                                                                                                     |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `E_PREZZO_LISTINO_NON_TROVATO`            | BA senza contratto e senza categoria mappata                                                                                               |
| `E_CATEGORIA_LISTINO_NON_MAPPATA`         | Categoria esistente ma nessuna riga in matrice per la quadrupla                                                                            |
| `E_PREZZO_LISTINO_RIGA_NON_TROVATA`       | Listino risolto ma nessuna riga prezzo per (articolo, uom)                                                                                 |
| `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C` | Contratto modalità C senza riga per l'articolo richiesto                                                                                   |
| `E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE`      | Articolo in listino di tipologia diversa                                                                                                   |
| `E_PREZZO_OVERRIDE_NON_AUTORIZZATO`       | L1: override prezzo non autorizzato                                                                                                        |
| `E_VENDITE_PRICING_FAILED`                | Errore generico pricing (envelope, dettaglio in `detail`)                                                                                  |
| `E_BOM_MODIFICA_VIETATA`                  | Tentata modifica/eliminazione campo struttura BoM. Risolvere con pattern chiudi+inserisci nuova versione (vedi §5.3)                       |
| `E_DATA_AL_MINORE_DAL`                    | Tentata chiusura riga BoM con `valido_al < valido_dal` (guard comune delle date, come su ogni periodo di validità)                        |
| `E_DOC_PREZZO_PENDENTE`                  | Tentata emissione/accettazione di un documento di vendita con un prezzo in attesa di approvazione (L3). Sostituisce `E_PREVENTIVO_RIGHE_PRICING_PENDENTI`, ritirato il 2026-09-24 |
| `E_DOC_PREZZO_RIFIUTATO`                 | Tentata emissione/accettazione di un documento di vendita con un prezzo rifiutato (L3)                                                     |
| `E_RIGA_PREZZO_PENDENTE`                  | Tentata modifica struttura riga in stato `stato_approvazione_prezzo='PENDING'`                                                             |
| `E_APPROVAZIONE_PREZZO_NON_AMMESSA`       | Tentata approva/rifiuta su riga non PENDING o senza pratica collegata; oppure coda approvazioni richiesta da admin globale senza emittente |

Tutti gestiti dal frontend con messaggi user-friendly (vedi `error_policies.py` backend).

---
{% include-markdown "signature-core.md" %}
