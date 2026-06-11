# Brief DB — `trgfn_pratiche_guard_contesto`: istanza senza ruolo (modello due rami)

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`). Spiega
> *cosa* fare e *perché*; niente DDL pronto.
>
> **Data**: 2026-06-11 · **Stato**: 🔴 APERTO — bug di modello confermato da
> Tid (dominio utilities) e verificato su schema/dati reali.
>
> **Impatto**: blocca l'aggancio di una pratica a un'istanza utility di un
> prospect puro (soggetto con istanza ma senza alcun ruolo) — che nel mondo
> utilities è il caso **normale**, non l'eccezione. Prerequisito del cantiere
> FE "selezione contesto pratica a 3 livelli" (residuo §4.3 di
> [gestione-pratiche-v2.md](gestione-pratiche-v2.md)).

## 1. Il bug di modello (verificato)

Il guard `pratiche.trgfn_pratiche_guard_contesto` (v2, migration
`20260328-12`) impone la catena lineare:

1. `istanza_utility_id` NOT NULL → `soggetto_ruolo_id` obbligatorio ← **ERRATA**
2. `soggetto_ruolo_id` NOT NULL → `soggetto_id` obbligatorio
3. `soggetto_ruolo_id` deve appartenere a `soggetto_id`
4. `istanza_utility_id` deve appartenere a `soggetto_id`

La regola 1 presume che il ruolo preceda l'istanza. Il dominio dice il
contrario, ed è verificato sullo schema reale:

- `anagrafiche.istanze_utilities.soggetto_id` è FK **diretta al soggetto**:
  l'istanza non passa da alcun ruolo;
- `anagrafiche.clienti` (billing account) richiede `soggetto_ruolo_id NOT NULL`
  **e** `istanza_utility_id NOT NULL`: il ruolo CL e il BA nascono *insieme*,
  *a valle* dell'istanza, solo quando si arriva all'emissione fattura;
- flusso utilities (gas/energia/acqua): arriva la richiesta → si genera
  l'**istanza** → la pratica pre-contrattuale lavora sull'istanza → solo se si
  arriva a fatturare nascono ruolo CL + BA. L'istanza può legittimamente
  restare ferma per sempre senza che il soggetto acquisisca mai un ruolo.

Il principio è documentato in
[guide/generazione-cliente.md](../../guide/generazione-cliente.md):

- §"Istanza utility": *"Perché l'istanza è legata al soggetto e non al ruolo?
  Perché l'istanza nasce prima del contratto. In fase precontrattuale il
  soggetto potrebbe non avere ancora il ruolo CLIENTE; il ruolo arriva dopo,
  con la specializzazione in `clienti`."*
- §"Creazione da pratica" (`config.utilities.richiede_pdp = true`): per le
  utility a ciclo tecnico (GAS/Energia/Idrico) la creazione del cliente passa
  **obbligatoriamente dal motore pratiche** — la pratica deve quindi potersi
  agganciare all'istanza *prima* che esista qualunque ruolo, perché è la
  pratica stessa il veicolo che a fine ciclo genera BA+cliente. Col guard
  attuale questo flusso è strutturalmente impossibile.
- §"Orchestrazione automatica": il ruolo CL è creato automaticamente dal
  `ClienteService` (`fn_get_or_create_soggetto_ruolo`) alla nascita di
  BA/cliente — **non** va anticipato dalla creazione pratica.

Conseguenza: per il prospect puro (istanza, zero ruoli — già presente nei dati
di sviluppo) il guard rende la pratica **non agganciabile** all'istanza, oppure
costringe a creare un ruolo CL prematuro, che nel modello appartiene alla
nascita del BA.

## 2. Modello corretto — due rami indipendenti dal soggetto

```text
soggetto ──→ soggetto_ruolo      (pratiche su ruoli: cliente attivo, fornitore, …)
        └──→ istanza_utility     (pratiche pre-contrattuali: nessun ruolo richiesto)
```

Ruolo e istanza possono coesistere (cliente attivo che chiede nuova fornitura
su nuova istanza): in quel caso valgono entrambe le regole di appartenenza.

## 2.bis Alternativa valutata e scartata — BA "guscio" alla nascita dell'istanza

Valutata su proposta Tid (2026-06-11): creare SEMPRE ruolo CL + billing
account senza codice contestualmente all'istanza, con regola "BA senza codice
= solo istanza, non cliente". Avrebbe unificato la catena (sempre
`soggetti_ruoli` ancorabile) eliminando il doppio ramo. **Scartata** dopo
verifica su schema reale — il BA in questo schema non e' una chiave neutra ma
una relazione di fatturazione ricca, e il guscio ne falsificherebbe la
semantica alla nascita:

1. `billing_account.codice` e' NOT NULL + UNIQUE + trigger di generazione
   all'INSERT (`trg_billing_account_a10_gen_codice_ins_upd`): il "BA senza
   codice" richiederebbe DDL (nullable + trigger condizionale + guard d'uso).
2. `trg_billing_account_z90_link_ef_ins` aggancia il BA a un **emittente
   fiscale** alla nascita: il guscio deciderebbe l'emittente quando non esiste
   alcuna relazione commerciale (e distorcerebbe lo scope emittente operatore
   sui ruoli CL).
3. `categoria_cliente_id` NOT NULL, `valido_dal` default CURRENT_DATE +
   `validita` daterange generated: attributi commerciali e validita' temporale
   della relazione di fatturazione partirebbero da una data falsa.
4. Superficie del discriminatore "solo BA veri": ~30 riferimenti SQL nel BE,
   8 viste (`vw_clienti_lista`, `vw_preventivi`, `vw_ordini_lista`, ...),
   2 policy RLS (`rls_fatture_ba_ownership`, `rls_ordini_cliente_ownership`),
   23 tabelle FK — ogni punto dimenticato = guscio contato come cliente.
5. Il doppio ancoraggio e' GIA' il pattern di sistema: preventivi / offerte /
   contratti / commesse_attivita / attivita_fatturabili portano tutti
   `istanza_utility_id` (operativo, spesso NOT NULL) + `billing_account_id`
   (fatturazione, opzionale dove il prospect e' ammesso). Il guscio andrebbe
   contro la direzione gia' presa dallo schema.

Conclusione: l'asimmetria pre-contrattuale/contrattuale e' del dominio (una
istanza puo' non avanzare mai); il modello la rappresenta con i due rami. La
biforcazione resta confinata nel punto di selezione (lookup pratiche), non
spalmata su tutti i consumatori di BA.

## 3. Cosa fare (DB)

Modificare `pratiche.trgfn_pratiche_guard_contesto` (nuovo changelog, la fn è
`CREATE OR REPLACE`):

- **Rimuovere** la regola 1 (`istanza ⇒ ruolo`).
- **Aggiungere** la regola sostitutiva: `istanza_utility_id` NOT NULL →
  `soggetto_id` obbligatorio (oggi era garantita solo transitivamente via
  ruolo).
- Regole 2, 3, 4 invariate.
- Messaggistica: il codice `PRATICHE_ISTANZA_SENZA_RUOLO` (304) decade;
  sostituirlo con `PRATICHE_ISTANZA_SENZA_SOGGETTO` (o riusare il 305 con
  messaggio adeguato — scelta del team DB). Aggiornare
  `config.messaggi_errore` di conseguenza.
- Nessuna ALTER su tabelle, nessuna sanatoria dati (nessuna riga viola il
  nuovo guard: è un rilassamento).

## 4. pgTAP richiesti

1. Pratica con `soggetto_id` + `istanza_utility_id`, **senza**
   `soggetto_ruolo_id` → INSERT OK (caso prospect puro, prima bloccato).
2. Pratica con `istanza_utility_id` e `soggetto_id` NULL → errore
   (nuova regola sostitutiva).
3. Regressione: istanza di un altro soggetto → errore (regola 4 invariata);
   ruolo di un altro soggetto → errore (regola 3 invariata).
4. Coesistenza: `soggetto_id` + `soggetto_ruolo_id` + `istanza_utility_id`
   tutti coerenti → OK (cliente attivo, nuova fornitura).

## 5. A valle (BE/FE, non DB — cantiere separato)

Alla consegna si sblocca il completamento del residuo §4.3 pratiche v2:

- lookup ricco `soggetti-ruoli` (una riga per ruolo + riga "senza ruolo" per
  i prospect) — BE nuovo, indipendente da questo brief;
- campo opzionale "Istanza utility" nel `PraticaDrawer` in creazione, via
  lookup esistente `IstanzaUtilityLookupView` filtrato per soggetto — il
  salvataggio col solo ramo istanza richiede QUESTO brief consegnato.

*Brief DB — guard contesto pratiche, istanza senza ruolo — ZeroERP
(2026-06-11). Da passare a `dev/db-tid`.*
