# Brief BE/FE — La capability sta sotto `capabilities`: una forma sola

> **Destinatari:** backend e frontend (`dev/backend-tid`).
> ⛔ **Nessun prerequisito DB**: nessun changeSet, nessuna funzione da
> toccare, nessuna riga di catalogo. Le `script.fn_available_actions_*`
> restano **esattamente** quelle che sono — cambia solo dove il backend
> appoggia il blob che già riceve.
>
> **Tipo:** brief di refactor, nato da una **decisione di Tid del 2026-09-23**
> (§1) presa davanti a un'asimmetria trovata lo stesso giorno (§2).
>
> **Da leggere per primo: §1 — la regola. Il §3 è il perimetro misurato, cioè
> il costo: non è la ragione di niente.**
>
> **Stato (2026-09-23, sera):** 🟢 **consegnato BE + FE, in collaudo a video**
> (§6: nessun test di componente monta ancora un drawer). Le tre domande del
> §7 chiuse sulla raccomandazione (Tid: «non credo ci siano domande aperte»),
> con una deviazione su Q-3 dichiarata nel §8. Cosa è cambiato rispetto al
> piano, e perché: §8, riga del 23-09 sera. Dopo la consegna, una revisione
> critica del diff: un bug di preventivi, due BB estratti (regola del 2), il
> guard esteso — §8, riga «revisione».
>
> **In una riga:** una capability di documento viaggia in una chiave sua —
> `detail.capabilities.can_x` — e non si fonde nel dettaglio; oggi sette
> servizi la fondono e due no, e fino a ieri **nessun documento diceva quale
> fosse la forma giusta**.

---

## 1. La regola

> **Il blob sta sotto `capabilities`, non fuso nel dettaglio.**
> — Tid, 2026-09-23

Sede della regola: [api.md §Capability](../api.md), sottosezione «Il blob sta
SOTTO `capabilities`». Qui non si riscrive: si converte il pregresso.

**Perché, sul modello.** Il dettaglio dice **com'è fatto** il documento; la
capability dice **che cosa ci si può fare adesso**. Sono due cose con due
autori — le colonne la prima, una funzione che legge stato e guard la seconda —
e fonderle in un dizionario solo perde l'origine di ciascun campo.

Tre conseguenze, e sono il motivo per cui la forma non è indifferente:

* ⛔ **il merge nasconde le collisioni**: il giorno in cui una testata avrà una
  colonna che si chiama come un campo del blob, uno dei due vince **in
  silenzio**;
* ⛔ **il piatto invita a scriverci dentro** — e succede già (§5);
* ⛔ **il piatto non è presidiabile**: `detail.can_x` è indistinguibile da un
  campo qualunque del dettaglio, quindi nessun cancello può dire se quel nome
  è un campo che il database emette o un refuso. La forma annidata invece
  `npm run guard:capability` la vede, ed è nata il giorno prima di questa
  decisione.

⚠️ **Non è una preferenza di stile**: è la ragione per cui `preventivi` ha
potuto riscrivere in Python campi che il database aveva deciso, senza che
nessuno lo scegliesse. La forma lo ha reso facile.

---

## 2. Il fatto che l'ha fatta emergere

Scrivendo la barra del drawer di magazzino
([brief-db-magazzino-lotto-2-bis-be-fe.md](brief-db-magazzino-lotto-2-bis-be-fe.md)
R-1, consegnato il 23-09) il drawer nuovo **non ha potuto usare il BB**
`useEntityCapabilities`: il BB legge i flag dal dettaglio piatto
(`detailRef.value?.[key]`), magazzino li riceve annidati.

Guardando perché, è emerso che le due forme convivevano **da prima**: le
commesse annidano dal giorno in cui sono nate. Non c'era un lato giusto e uno
sbagliato — **non c'era una regola**, e due cantieri diversi avevano risolto la
stessa domanda in due modi, entrambi difendibili.

⭐ È il caso descritto in `.codex/AGENTS.md`: *una regola che non sta dove si
legge non esiste*. La prima cosa fatta è stata scriverla (api.md); questo brief
è la seconda.

---

## 3. Il perimetro, misurato il 2026-09-23

> ⚠️ Fatto datato, non motivo. Se domani i numeri fossero altri la regola
> resterebbe quella: si converte quello che c'è.

| Dove | Quanto |
| --- | --- |
| **BE** — punti di merge | **8 righe** in 6 service (5 domini + preventivi, §5) |
| **FE** — file che leggono in forma piatta | **27**, di cui **7 coperti dal BB** |
| **BE** — test che pinnano la forma | 7 file in `apps/vendite/tests` |

⚠️ **Il primo conteggio diceva 113 file, ed era falso**: `mode` (71 file) e
`pdf` (13) sono chiavi **interne** al sotto-oggetto `pdf` del blob, non campi
di primo livello, e `stato_codice_interno` (40) è un campo del **documento**.
Lo si scrive qui perché è il genere di numero che, preso per buono, avrebbe
fatto sembrare il lavoro cinque volte più grande — e avrebbe potuto far
rimandare una decisione che invece costa poco.

### 3.1 I servizi da convertire

| Service | Riga | Forma oggi |
| --- | --- | --- |
| `vendite/services/ddt_service.py` | 204 | `**capabilities` |
| `vendite/services/resi_service.py` | 217 | `**capabilities` |
| `vendite/services/ordini_service.py` | 278 | `**capabilities` |
| `vendite/services/contratti_service.py` | 717 | `testata.update(capabilities)` |
| `vendite/services/promo_articoli_service.py` | 207 | `result.update(capabilities)` |
| `vendite/services/preventivi_service.py` | 250, 265, 273 | ⚠️ §5 — non è solo forma |

✅ Già annidati e fuori dal lavoro: `commesse_service` (480) e
`magazzino_service` (277).

### 3.2 Il frontend, per come si tocca

| Gruppo | File | Che cosa serve |
| --- | --- | --- |
| **dal BB** | 7 drawer di vendite (contratti, offerte, promo, resi, ordini, preventivi, DDT) | **niente**: si converte il BB, loro seguono |
| **letture diverse** | `LottoDrawer` + `useLottoAzioni` (`available_actions`), `DistintaDrawer` + `RegistraDistintaDialog` (`stato_info_key`), `CommessaGestioneDrawer`, `DocumentoInternoDrawer` | già annidati o da guardare uno per uno |
| **`non_editable_fields` sparso** | `SoggettoDrawer`, `ArticoloDrawer`, `ArticoloUomDrawer`, `ConversioneUomDrawer`, `CategoriaClienteListinoDrawer`, `TipoRuoloTipoIndirizzoDrawer` | 🔴 **da qualificare**: vedi §4.0 |

---

## 4. Il piano

### 4.0 Passo zero — qualificare `non_editable_fields` *(prima di toccare qualunque cosa)*

> ✅ **Qualificato il 2026-09-23: tutti e sei FUORI.** Nessuno riceve il campo
> da una capability: `SoggettoDrawer` da `soggetti_service._compute_non_editable_fields`,
> `ArticoloDrawer`/`ArticoloUomDrawer`/`ConversioneUomDrawer` dal registro dei
> lock (`dbops.vw_non_editable_fields` / `fn_non_editable_fields` + gap Python
> in `catalogo_service`), `CategoriaClienteListinoDrawer` e
> `TipoRuoloTipoIndirizzoDrawer` da `compute_non_editable_fields`. Stesso nome,
> altra sorgente: sono **dichiarati** nel registro del cricchetto (§4.3) col
> loro motivo.

🔴 **Sei drawer leggono `non_editable_fields` e NON sono documenti con una
capability.** Vanno guardati prima, perché decidono il perimetro: se quel campo
lo emette una capability, entrano nel refactor; se lo emette il dettaglio di
un'anagrafica per altra via, **restano fuori e si dichiarano qui**.

⛔ Non si convertono «perché il nome somiglia»: sarebbe la forma di errore che
questo brief esiste per evitare.

### 4.1 Giro 1 — il BB legge entrambe le forme *(FE, non rompe niente)*

`useEntityCapabilities(detailRef)` prende il blob da `detail.capabilities` se
c'è, altrimenti dal dettaglio piatto. Una funzione sola, **sette drawer
coperti**, nessun backend toccato, nessun momento in cui l'app è rotta.

⭐ È ciò che rende i giri dopo **indipendenti**: da qui in avanti il frontend è
indifferente alla forma, e ogni service può migrare quando gli pare.

⚠️ La doppia lettura è un **ponte, non la sede definitiva**: va tolta quando
l'ultimo service è convertito, e finché c'è va scritta nel file con la data e
il motivo — o diventa il posto dove la vecchia forma sopravvive per sempre.

### 4.2 Giro 2 — i cinque service, uno per volta *(BE + FE)*

Per ciascuno, nello stesso commit: la riga del service, i suoi test, e il
drawer **solo** se non passa dal BB. Cinque giri piccoli, in quest'ordine —
dal più isolato al più intrecciato:

1. `promo_articoli` (il drawer legge `can_update_reason` a mano)
2. `resi`
3. `ddt`
4. `ordini`
5. `contratti`

### 4.3 Giro 3 — togliere il ponte e stringere il cancello *(FE)*

Tolta la doppia lettura dal BB, `guard:capability` va esteso: oltre a
verificare i nomi, **conta le letture piatte rimaste** e non le lascia
risalire. ⭐ Così la migrazione ha un **contatore che scende** invece di una
lista che qualcuno spunta a mano — stessa forma del registro delle `DataTable`
grezze.

---

## 5. `preventivi` non è un problema di forma, ed è la cosa più importante qui

> ✅ **Q-2 applicata il 2026-09-23**: preventivi annida. La riscrittura di
> `available_actions`/`can_edit_*` resta **dentro** `capabilities`, col debito
> scritto nel codice (`preventivi_service.get_preventivo`, 🔴 DEBITO
> DICHIARATO). ⚠️ I quattro campi aggiunti — `frozen_for_*` e `*_pricing_count`
> — sono andati sulla **testata**, non nel blob: sono un riepilogo delle righe
> (come `righe_count`), nessuna capability li emette, e sotto `capabilities` il
> cancello li avrebbe bocciati — con ragione, perché il contratto del database
> non li conosce. Il `PreventiviDrawer` li legge da lì, invariato.

`preventivi_service` non fonde e basta: **riscrive il blob in Python** prima di
consegnarlo. Aggiunge quattro campi propri (`frozen_for_pending_pricing`,
`frozen_for_rejected_pricing`, `pending_pricing_count`,
`rejected_pricing_count`) e **sovrascrive `can_edit_testata` e
`can_edit_righe`** con un calcolo suo, dichiarato nel codice come
*«defense-in-depth replica trgfn DB lato preventivi_righe»*.

⛔ Quella è la seconda sede di una regola del database, cioè esattamente ciò
che una capability esiste per evitare: *il backend trasporta, non deduce*. Il
fatto che sia scritta come difesa in profondità non cambia la sostanza — se il
trigger cambia, il Python non lo sa.

⇒ **Fuori dal perimetro di questo brief, e dichiarato**: convertirlo alla forma
annidata lo renderebbe più visibile ma non lo sanerebbe. La domanda vera —
*quel predicato deve stare in una `fn_check_*` che la capability legge?* — è di
dominio, vuole il team DB, e merita un brief suo.
⚠️ Finché non si decide, preventivi **annida come gli altri** (così il
frontend è uniforme) ma tiene la sua aggiunta: il debito resta, con un nome.

---

## 6. Presidi

* `guard:capability` — già in `npm run guards` dal 23-09; dopo §4.3 conta anche
  le letture piatte, con le parentesi (`detail['pdf']`) e per destrutturazione
  (`const { pdf } = detail.value`), e verifica i nomi passati ad
  `azioneNegata()` col loro motivo. ⚠️ Resta cieco sulla destrutturazione di
  un **parametro** (`({ pdf }) =>`), che non dice da dove viene l'oggetto:
  limite dichiarato nel guard;
* `useDrawerActions.spec.js` (11 test) — indipendente dalla forma, non va
  toccato;
* per ogni service convertito: i suoi test del dettaglio, che oggi pinnano le
  chiavi **piatte** (7 file in `apps/vendite/tests`) — un test che non fallisce
  durante la conversione è un test che non guardava la forma, e va guardato;
* 🔴 **quello che manca**: nessun presidio prova che un drawer **legga** il
  blob dopo la conversione. Un service annidato e un drawer non aggiornato
  danno un drawer senza barra e **nessun errore**. Finché non ci sono i test di
  componente (`@vue/test-utils` + `jsdom`, deciso di sì il 23-09, non ancora
  fatto), ogni giro vuole il **collaudo a video del suo drawer**.

---

## 7. Domande a Tid

| | Domanda | Raccomandazione |
| --- | --- | --- |
| **Q-1** | I sei drawer che leggono `non_editable_fields` (§4.0): dentro o fuori? | **Guardarli prima**, e decidere sul caso: se il campo non viene da una capability, fuori e dichiarati |
| **Q-2** | `preventivi`: annida ora tenendo la sua aggiunta, o si aspetta il brief sul predicato duplicato? | **Annidare ora** — il frontend diventa uniforme, e il debito resta con un nome invece che con una forma diversa |
| **Q-3** | I cinque giri in cinque PR o in una sola? | **Cinque**, uno per dominio: ciascuno è collaudabile a video da solo, e un rosso dice subito di chi è |

---

## 8. Registro

| Data | Cosa |
| --- | --- |
| 2026-09-23 | **Nascita.** L'asimmetria emerge scrivendo la barra del drawer di magazzino (brief 2-bis R-1): il drawer nuovo non può usare `useEntityCapabilities` perché le due forme convivono, e **nessun documento diceva quale fosse quella giusta**. Decisione di Tid: **annidata**, scritta in api.md §Capability. Perimetro misurato lo stesso giorno (§3), col primo conteggio corretto da 113 a 27 file. |
| 2026-09-23 (sera) | **Consegna BE + FE, in un giro solo.** ⭐ **Deviazione da Q-3 e dal §4.1, dichiarata**: nessun ponte e nessun giro per dominio — tutti i service convertiti insieme, il BB legge **solo** `detail.capabilities` dal primo momento. Con tutti i service convertiti nello stesso lavoro il ponte non avrebbe traghettato niente, e sarebbe rimasto il posto dove la forma vecchia sopravvive (§4.1 ⚠️); il collaudo resta per drawer (§6). **Quello che il perimetro del §3 non vedeva**, trovato convertendo: (1) 🔴 **`pdf` è una chiave di PRIMO livello** del blob di ddt, contratto, offerta, ordine e preventivo — non «interna al sotto-oggetto» come diceva il §3 — e i cinque drawer la passavano piatta (`:pdf="detail.pdf"`): annidato il blob, il pulsante PDF avrebbe perso il `mode` **senza nessun errore**; (2) **offerte** (`get_offerta`, `row.update`) e **lotto** (`fn_get_lotto`, `result.update`, più lo schema OpenAPI) fondevano anch'essi: nove punti di merge, non otto; (3) i sette drawer «dal BB» leggevano il blob **anche a mano** (`can_*_reason_key`, `stato_info_key`, `non_editable_fields`, `stato_temporale`, `min_valido_*`) — «niente da fare» del §3.2 non reggeva, ora leggono dal `capabilities` del BB; (4) **magazzino** teneva `stato_info_key` due volte (blob e testata): tolta la copia; (5) il contratto annidato non conosceva `fn_capability_promo_articolo` (famiglia di nomi diversa): il guard ora legge anche quella; (6) contratti: il blob porta `stato_codice_interno`, che la testata ha già — fuso, vinceva il blob in silenzio (stesso valore oggi); ora il test lo prova con valori **diversi**. **Presidi**: test BE che pinnano la forma annidata **e** l'assenza delle chiavi del blob dalla testata (ordini, contratti, promo, offerte, preventivi, lotto, magazzino; nuovi per DDT e resi, che non guardavano la forma); ripiego di offerte e lotto → `capabilities: {}`, mai assente; `useEntityCapabilities.spec.js` (6); `guard:capability` esteso — nomi passati a `flag()`/`editFlag`, e il **cricchetto** §4.3 sulle chiavi di primo livello lette dalla doc auto-gen, con gli omonimi in `frontend/scripts/capability-letture-piatte.json` (3 echi di stato, 10 file). Guard provato per **mutazione** su sei letture piatte e due refusi: la prima versione era **cieca proprio su `detail.pdf`** (scambiava l'attributo del template per una chiave i18n) — corretto. Verifica sul DB di sviluppo: gli otto dettagli escono annidati, `pdf` c'è dove la funzione lo emette, nessuna chiave trapela. BE 2475 test, FE `npm run verify` verde (300 test). Doc: api.md §Capability, manuali API di vendite, catalogo BB FE, frontend-standards. **Resta**: collaudo a video dei sette drawer + lotto + documento interno (barra azioni, nota di stato, pulsante PDF, campi bloccati, banner promo e congelamento preventivi); §5 — il predicato duplicato di preventivi, brief DB suo. |
| 2026-09-23 (revisione) | **Revisione critica del diff non committato**, e correzioni. (1) 🔴 **Bug di preventivi, fail-open**: il ramo «solo righe REJECTED» di `get_preventivo` scriveva `can_edit_righe = True` senza guardare il blob — un preventivo che il database dava non modificabile (fuori BOZZA) con una riga rifiutata diventava modificabile a video, e il salvataggio lo rifiutava il trigger. Ora il ramo può solo **restringere** (`pending == 0 and blob.can_edit_righe is True`); test costruito sul caso (REJECTED + DB spento → spento). Il debito del §5 resta com'è: si è tolto solo che potesse **allargare**. (2) ⭐ **Regola del 2, FE** (ok Tid): `pushCommessaDisabledAction` era identico in `DdtDrawer` e `OrdiniDrawer` → `useEntityCapabilities().azioneNegata(flag, forma)` (flag spento + `<flag>_reason[_key]` → entry `enabled: false` nella forma di `available_actions`; senza motivo, niente) e la forma del pulsante in `vendite/constants.js` (`AZIONE_PUSH_COMMESSA`); tolti i due `canPushCommessa` rimasti senza lettori; spec del BB da 6 a 8 test. (3) ⭐ **Regola del 2, BE** (ok Tid): il ripiego «capability layer rotto → `capabilities: {}` + warning» era scritto due volte (`get_offerta`, `fn_get_lotto`) → `apps/core/services/capability_blob.capabilities_o_vuoto`. In più, nell'estrarlo: un `DatabaseError` catturato **dentro** un blocco atomico lascia la transazione abortita, quindi la lettura va in un savepoint suo quando il chiamante è in transazione (in autocommit non se ne apre nessuno); 4 test. (4) **Guard esteso**: accesso con parentesi, destrutturazione (ricevente `capabilities` → verificata sul contratto; altro ricevente → lettura piatta nel cricchetto), argomenti di `azioneNegata` col loro motivo — provato **per mutazione** su un file con sei forme sbagliate e due giuste: tutte e sei rosse, le due giuste verdi. (5) Minori: commento stantio in `magazzino/api/magazzino.js` (diceva `stato_info_key` anche in testata, che il BE aveva appena tolto); uno spazio mancante in `error_messages_fallback.py`. **Verifica**: suite BE completa verde (5046 test, 59 skip), FE `npm run verify` verde (302 test). Doc: cataloghi BB BE e FE, frontend-standards §`DrawerActionsBar`. ⚠️ Nel working tree ci sono anche le modifiche del codice `E_LOTTO_COMPLETATO_NON_GUADAGNATO` (brief-db-annullamento-chiude-la-vita): non sono di questo brief, vanno committate a parte. |
