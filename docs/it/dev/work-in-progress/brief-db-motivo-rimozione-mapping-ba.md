# Brief DB — il motivo per cui un mapping BA non si toglie deve arrivare **sulla riga**

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Consegna **BE-1** di
> [brief-db-billing-account-cambio-emittente.md](brief-db-billing-account-cambio-emittente.md),
> chiusa il 2026-08-26. Il cancello funziona e l'endpoint restituisce il **409**
> con la frase giusta — provato sul database vero. Ma il pulsante che lo innesca
> è **acceso**, e l'operatore scopre il vincolo premendolo.
>
> ⭐ **È M7 riscritto nella forma giusta.** Il brief d'origine (§6.7) aveva messo
> in pausa una *capability di dettaglio* «finché il frontend non la chiede».
> Guardando il frontend, la richiesta c'era già e non era quella: l'azione è
> **per riga**, quindi la sede non è il blob del dettaglio ma la forma del
> **§12.5** di [linee-guida-sql.md](../../linee-guida-sql.md) — una `fn_check_*`
> che la madre **chiama**, più una colonna sulla riga.
>
> ✅ **Stato (2026-08-27): Q-1 decisa da Tid — forma (a). N1, N2, N4 e N7
> ESEGUITI** (changeSet `20260827-01`, `-02`, `-03`; pgTAP a `plan(14)`).
> **N5 assorbito in N1** (§5.4). Restano **N6** e le consegne BE/FE del §8.
> ⭐ **N7 è nato da una segnalazione del BE, ed è la parte che ha insegnato di
> più**: il buco c'era, ma la causa non era quella indicata — §5.6.

---

## 1. Il difetto in una frase

Nel tab «Billing Account» di un emittente fiscale il cestino di riga è **sempre
acceso**. Su un cliente che ha già fatture o commesse presso un altro emittente
il gesto viene rifiutato dal database — correttamente — **dopo** che l'operatore
ha premuto e confermato un dialog.

⇒ È alla lettera la «terza via» che il **§12.1** vieta (*«lasciare l'azione
accesa su qualcosa che il guard rifiuterà: l'operatore clicca, prende un 409, e
scopre il vincolo sbagliando»*), nella forma **per riga** descritta dal §12.5 —
la stessa specie del pulsante «Annulla l'accredito» che ha fatto nascere quel
paragrafo cinque giorni fa.

---

## 2. Cosa dice la struttura, e c'è già uno slot vuoto ad aspettare

| Pezzo | Stato al 2026-08-26 |
| --- | --- |
| `EmittentiFiscaliBillingAccountService.list_mapping` | mette `row["can_remove"] = True` **scritto a mano, per ogni riga** |
| `EmittenteFiscaleBillingAccountTab.buildRowActions` | costruisce il cestino **incondizionato**: `can_remove` non lo legge nessuno |
| la madre che rifiuta | `anagrafiche.fn_guard_ba_cambio_emittente`, chiamata da `trgfn_efba_guard_storia_emittente` sui tre movimenti |
| il codice sollevato | `E_BA_EMITTENTE_CON_STORIA`, **già a catalogo** (`CONFLITTO_STATO` → 409) |

⭐ **Lo slot esiste e mente.** Non manca un canale: manca il **dato**. E il
commento accanto a quella riga dice, dal giorno in cui è nata, che `can_remove` è
*«una capability esplicita per allineare la UI col pattern utility, delegando il
gating al BE invece di derivarlo dalla presenza del record»* — cioè la promessa
era già quella, e da oggi non è più vera.

> ✅ **Verificato dal team DB il 2026-08-27**: `emittenti_fiscali_service.py:242`
> assegna `can_remove = True` incondizionato, e `buildRowActions` restituisce
> l'azione secca. ⭐ Nello **stesso file**, alla riga 361, un altro metodo
> popola `can_remove` da una condizione: la forma giusta esisteva già a otto
> righe di distanza.

---

## 3. ⛔ La trappola: il motivo **non è** «questo cliente ha storia»

È la cosa da leggere prima di scrivere il predicato, ed è quella che il brief
d'origine ha già pagato una volta in fase di collaudo.

Togliere un mapping specifico fa ricadere il billing account sul **gestore
globale**. Quindi il movimento «cambio di emittente» c'è **solo se** l'emittente
della riga è **diverso** da quello del default globale: se coincidono non si
sposta niente, e il ramo 2 di `fn_guard_ba_cambio_emittente`
(`prima IS NOT DISTINCT FROM dopo`) lascia passare — che è la manutenzione
ordinaria, e deve restare accesa.

> **Il predicato della riga è una coppia**: *l'emittente cambia davvero* **e**
> *il billing account ha storia*. Scriverne solo la seconda metà spegnerebbe il
> cestino su quasi tutte le righe di un'installazione a un solo emittente, tutte
> **a torto**.

⚠️ **E il rovescio è la ragione per cui questo brief non poteva nascere da un
collaudo distratto**: sullo stesso database, il primo `DELETE` provato è
**passato** proprio per quel ramo. Chi avesse provato solo quello avrebbe
concluso che il presidio non c'è.

---

## 4. ✅ Q-1 CHIUSA — forma **(a)**: il `LATERAL` nell'SQL che c'è già

> ~~❓ Su quale superficie vive la colonna.~~
> ✅ **Decisa da Tid il 2026-08-27: (a).**

Il **§12.5.3** dice che la domanda non è «quale lista parla di questa cosa» ma
**«da dove si preme quel pulsante?»**. Qui la risposta è netta: dalla lista dei
mapping **dentro il drawer dell'emittente**, servita da
`EmittentiFiscaliBillingAccountRepository.list_by_emittente` — SQL scritto in
Python.

| | Forma | Esito |
| --- | --- | --- |
| **a** | il backend aggiunge un `LEFT JOIN LATERAL script.fn_check_…` all'SQL che ha già | ✅ **scelta** |
| **b** | nasce `anagrafiche.vw_emittenti_fiscali_ba_mapping` | ⛔ scartata |

### ⛔ Perché l'argomento del brief per la **b** non reggeva

Il brief la raccomandava come *«esattamente il precedente del §12.5.3»*.
Misurato il 2026-08-27 sul catalogo `ui` (che è **contratto**, non popolazione):

```text
liste a catalogo: 49 | con vista_sql: 15 | SENZA vista_sql: 34
```

Una lista configurabile **senza vista è la norma**, non l'anomalia —
`anagrafiche.emittente_billing_account` è una delle 34. Il precedente di
`vw_resi_righe_dettaglio` parlava dei **dettagli documento**, famiglia molto più
stretta, dove essere senza vista era davvero l'eccezione: là la frase *«l'unico
dettaglio documento servito da SQL scritto in Python»* era vera, qui non lo è.

⭐ **E la domanda era mal posta.** Non è «dove vive la regola di lettura»: la
regola vive in **N1** in entrambe le forme, ed è l'unico posto. Resta solo
*«questa lista prende una vista?»*, che è una scelta locale.

⚠️ Controllato anche l'argomento che avrebbe potuto salvare la **b** — il guard
su `ui.lista_colonna` che, senza vista, non valida i `campo_sorgente` — e **non
si applica**: il motivo viaggia nel *payload di riga*, come `can_remove` oggi,
non come colonna a catalogo.

⚠️ L'obiezione *«nessun altro consumatore la trova»* riguarda la **query**, non
la regola: un secondo consumatore chiama la funzione, che è l'unità condivisa.

> ⚠️ **Se un domani si volesse comunque la vista**, la motivazione da scrivere è
> *«questa lista merita una vista»* — non *«è il precedente del §12.5.3»*,
> altrimenti quel precedente verrà usato per creare le altre 33.

---

## 5. I lotti

| Lotto | Cosa | Fase | Stato |
| --- | --- | --- | --- |
| **N1** | `script.fn_check_ba_cambio_emittente` — il predicato, che **nomina** e non solleva | `20_code` | ✅ `20260827-01` |
| **N2** | `fn_guard_ba_cambio_emittente` **chiama** N1 e solleva il codice del primo motivo | `20_code` | ✅ `20260827-02` |
| **N3** | il motivo sulla riga | — | ⇒ con la **(a)** non è un oggetto DB: è **BE-3** |
| **N4** | pgTAP | `db/pgtap` | ✅ `plan(8)` → `plan(13)` |
| **N5** | il messaggio nomina l'emittente per **id** | — | ⇒ **assorbito in N1** (§5.4) |
| **N6** | documentazione | `docs/` | 🔴 |
| **N7** | ⛔ la **riga del gestore globale** aveva il cestino acceso — segnalazione BE | `20_code` | ✅ `20260827-03` |

### 5.1 N1 — la check

`[]` se ammesso; altrimenti l'array **ordinato** del §12.5.1
(`codice` · `reason` · `reason_key` · `dettaglio` · `valori`).

⚠️ **`SECURITY DEFINER` come la madre**, e per la stessa ragione: la storia si
conta su `vendite.fatture` e `vendite.commesse`, che hanno la RLS accesa. Da
`SECURITY INVOKER` risponderebbe «nessuna storia» proprio nel caso da spegnere.

⚠️ **Nessun codice errore nuovo** (§12.5.2): la check *nomina* un codice che c'è.

**`reason_key` consegnata**: `amministrazione.emittenti_fiscali.ba_blocco.con_storia`
— va nei locales **it e en**, o il pulsante resta grigio col tooltip vuoto.

### 5.2 N2 — la madre chiama, non riscrive

⭐ **Il presidio da scrivere non è «gli esiti coincidono»**, è **«la madre non
contiene più il predicato»**: il primo prova che oggi vanno d'accordo, il secondo
che non possono divergere. ⇒ È il **test 13** del pgTAP, e legge
`pg_get_functiondef`.

⚠️ **L'ordine dell'array è il contratto**: la madre solleva il primo.

### 5.3 N3 — il motivo sulla riga ⇒ consegna **BE-3**

Per ogni riga di mapping il «dopo» è **l'emittente del gestore globale**.

⛔ **E si legge dalla riga `is_default`, non da `script.fn_get_ba_emittente_sr_id`**:
lì il mapping specifico c'è ancora, quindi il risolutore risponderebbe la riga
che si sta guardando — «prima» e «dopo» coinciderebbero e la colonna direbbe
«togliabile» sempre. È la stessa trappola del §6.3 del brief d'origine, un
livello più in là.

**Nome della colonna**: `rimozione_blocco_reason` — ⚠️ §12.5.4, *un verbo una
colonna, con un nome che dice quale*. Porta il `reason` del primo motivo,
**`NULL` = ammesso**.

### 5.4 ✅ N5 — assorbito in N1, e non per fretta

Il messaggio diceva:

> *«Il cliente **BAC/0000042** ha già 10 fatture e 15 commesse con l'emittente
> **72**»*

— un `soggetto_ruolo_id` nudo in mezzo a una frase italiana, **nella stessa
frase** in cui il cliente è nominato per codice. Il `VARIADIC` è il canale che
parla **all'operatore**.

⇒ **Non è diventato un changeSet suo**, e la ragione è strutturale: dopo N2 i
`valori` del messaggio si compongono **dentro la check**. Farlo a parte avrebbe
voluto dire scrivere l'etichetta sbagliata in N1 e correggerla in N5 il minuto
dopo. `anagrafiche.emittenti_fiscali.codice` è `NOT NULL`: la simmetria è un
`COALESCE`.

⚠️ Presidiato dal **test 12**, che confronta il quarto valore col `codice`
dell'emittente — non con «qualcosa che non sia un numero».

### 5.5 N4 — i casi che si vedono solo dalla riga

Aggiunti a `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql`
(`plan(8)` → `plan(13)`):

1. **senza storia** ⇒ `[]` — il cestino resta acceso;
2. **emittente che non cambia davvero** ⇒ `[]`, *anche con storia*: è la metà
   del predicato che si dimentica;
3. **cambia + storia** ⇒ un motivo, col codice a catalogo;
4. il messaggio nomina l'emittente per **codice**;
5. ⭐ **strutturale**: la madre chiama la check e **non contiene più** il
   predicato.

⚠️ Le fixture **si fabbricano** il billing account e la commessa: un test che
cerca fra i dati esistenti passa a vuoto in CI — e su questa tabella è già
successo una volta.

### 5.6 ⛔ N7 — la riga del gestore globale, e perché la gemella sarebbe stata sbagliata

**Segnalazione del BE (2026-08-27), corretta**: `fn_check_ba_cambio_emittente`
usciva al primo `IF` — *«senza billing account non è il suo caso»* — e su quella
riga il cestino restava **acceso**. ⚠️ Ed è pure **la prima riga della lista**:
il repository ordina `is_default DESC` apposta, per tenerla in testa.

⭐ **E il BE ha fatto la cosa giusta a non tapparlo**: dedurlo in Python sarebbe
stato ricalcolare la regola fuori dalla sua sede.

#### ⛔ Ma la causa non è quella, ed è più forte

Il BE attribuiva il rifiuto a `fn_guard_ba_gestore_globale_storia` (raggio N) e
proponeva di scriverne la gemella `fn_check_*`. Verificato:

> `anagrafiche.trgfn_emittenti_fiscali_default_guard` è un **AFTER** sui tre
> movimenti e impone il **singleton**: *«deve esistere esattamente un default»*.
> Cancellare quella riga porta il conteggio a **0**.

⇒ **Quella riga non si toglie MAI**, con o senza storia.

#### ⭐ Per questo la gemella sarebbe stata la risposta sbagliata

Avrebbe prodotto un motivo **condizionale** — *«c'è storia»* — dove la risposta è
**incondizionata**. Sul tooltip suggerirebbe che *senza* storia la riga si
potrebbe togliere.

> **Un tooltip che dichiara una condizione inesistente è peggio di nessun
> tooltip: manda a cercare come soddisfarla.**

⇒ Il motivo giusto è `E_EMITTENTE_DEFAULT_SINGLETON` (già a catalogo,
`CONFLITTO_STATO`), `reason = DEFAULT_SINGLETON`, secco.

#### ⭐ E la correzione entra nella check che c'è già

Non in una funzione nuova, e non per pigrizia: **il frontend chiama una cosa per
riga**. Con due check sarebbe il backend a dover dedurre *«che tipo di riga è
questa»* — cioè esattamente il §7 che il BE ha invocato per non tapparlo da solo,
riaperto un passo più in là.

⚠️ **Il guard raggio N resta necessario e non è coperto da qui**: presidia il
**cambio** dell'emittente del gestore globale — un `UPDATE`, o un `DELETE`
seguito da un `INSERT` — non la cancellazione secca, che il singleton rende
comunque impossibile.

⚠️ **Il motivo del singleton serve alla RIGA, non al raise**: a rifiutare è il
guard singleton, che compone la propria frase. I `valori` portano il conteggio
che *risulterebbe*.

**Chiave i18n in più per FE-3**:
`amministrazione.emittenti_fiscali.ba_blocco.default_singleton`.

---

---

## 6. ❓ Q-2 — e il gesto «Aggiungi BA»?

Lo stesso vincolo colpisce l'`INSERT`: agganciare all'emittente **B** un cliente
che ha storia sotto **A** viene rifiutato con lo stesso 409, e nella UI si arriva
lì scegliendo un billing account da un lookup.

⚠️ **Non è la stessa forma del §12.5** — non c'è una riga da spegnere, c'è un
pulsante che dipende da ciò che si è appena scelto nel lookup.

⛔ **Non si decide in questo brief**, ed è deliberato: il §12.1 nomina il costo
della «terza via» nel lavoro che l'operatore ha già fatto quando prende il
rifiuto. Qui quel lavoro è **un click**. Non è lo stesso caso del cestino, e
trattarlo come se lo fosse allargherebbe il cantiere senza un motivo sul modello.

> ✅ **Il team DB concorda** (2026-08-27), e per la stessa ragione: la misura del
> costo è quella giusta, e non c'è niente sul modello che chieda di anticiparla.

---

## 7. Cosa questo piano **non** costruisce

* ⛔ **Nessun codice errore nuovo** (§12.5.2).
* ⛔ **Nessuna capability di dettaglio**: M7 del brief d'origine è **superato**,
  non rimandato — l'azione è per riga.
* ⛔ **Nessun ricalcolo della regola nel backend o nel frontend**.
* ⛔ **Non si tocca la decisione D-1** (forma **b**: libero finché non c'è
  storia, vietato dopo). Qui si cambia solo **chi lo dice, e quando**.
* ⛔ **Nessuna vista nuova** (Q-1 = a).

---

## 8. Consegne fuori dal database

⛔ **Ferme finché N1…N2 non sono applicati.**

| | Dove | Cosa |
| --- | --- | --- |
| **BE-2** | `apps/anagrafiche/services/emittenti_fiscali_service.py` | `can_remove` smette di essere `True` scritto a mano e diventa il `reason` che arriva dalla riga (`NULL` ⇒ ammesso); il messaggio del tooltip resta una **chiave**, mai testo dal database |
| **BE-3** | `apps/anagrafiche/db/emittenti_fiscali_repository.py` | `LEFT JOIN LATERAL script.fn_check_ba_cambio_emittente(m.billing_account_id, m.emittente_soggetto_ruolo_id, <emittente della riga is_default>)` nell'SQL di `list_by_emittente`, esposto come `rimozione_blocco_reason` |
| **FE-2** | `EmittenteFiscaleBillingAccountTab.buildRowActions` | `disabled` + **`tooltip`** sull'azione — ⛔ il campo si chiama `tooltip`, non `motivo`: `RowActionsMenu` legge solo quello |
| **FE-3** | `locales/it.json` · `locales/en.json` | la chiave `amministrazione.emittenti_fiscali.ba_blocco.con_storia`, in **tutte e due** |

⚠️ **BE-3, la riga da non sbagliare**: il «dopo» è l'emittente della riga
`is_default`, **non** `script.fn_get_ba_emittente_sr_id(ba)` — vedi §5.3.

⭐ **E prima di dire che FE-2 è fatto, guardare a video che il tooltip arrivi**:
§12.5.5 — un campo dichiarato e non letto sembra presidiato, e in questo progetto
il motivo di un pulsante spento non era **mai** stato reso.

---

## 9. Registro

### 2026-08-26 · Nascita

Nato dalla verifica di **BE-1**: il 409 c'è ed è giusto, ma è la fine sbagliata
del gesto. ⭐ La cosa che ha deciso la forma del brief non è stata leggere il
frontend — è stato leggere il **§12.5**, scritto cinque giorni prima per un
pulsante di un altro dominio: la regola c'era già, e questo è il secondo caso
della stessa specie.

⛔ Nessuna decisione presa sul database, nessun file scritto.

### 2026-08-27 · Q-1 decisa, N1·N2·N4 eseguiti

✅ **Q-1 → (a)** (Tid). ⛔ L'argomento del brief per la **b** non ha retto la
misura: 34 liste su 49 sono senza vista, quindi *«è il precedente del §12.5.3»*
non si applica — quel precedente parlava dei dettagli documento, dove
l'eccezione era vera. §4.

✅ **Q-2** confermata aperta, con l'accordo del team DB.

**ChangeSet**: `20260827-01` (N1, la check) e `20260827-02` (N2, la madre che
chiama). **pgTAP** portato da `plan(8)` a `plan(13)`.

⭐ **N5 si è dissolto**: dopo N2 i valori del messaggio si compongono dentro la
check, quindi l'etichetta giusta atterra per costruzione. Tenerlo separato
avrebbe significato scrivere quella sbagliata e correggerla il minuto dopo.

⚠️ **Il presidio che conta è il test 13**, ed è strutturale: legge
`pg_get_functiondef` e verifica che la madre **chiami** la check e **non
contenga più** il conteggio. Se un giorno qualcuno lo ricopiasse dentro «per non
fare una chiamata in più», è l'unico posto in cui quel passo indietro si
vedrebbe.

⛔ Nessuna migrazione applicata: l'apply lo autorizza Tid.

### 2026-08-27 · N7 — la riga che nessuno aveva guardato

Segnalazione del BE: la check usciva al primo `IF` e sulla **riga del gestore
globale** il cestino restava acceso — la prima della lista, per giunta.

⭐ **Il buco c'era. La causa no.** Non era il guard raggio N ma il **singleton**:
quella riga non si toglie mai, con o senza storia. ⇒ La gemella `fn_check_*`
proposta avrebbe dato un motivo **condizionale** dove la risposta è secca, e un
tooltip che dichiara una condizione inesistente manda a cercare come
soddisfarla.

⭐ **E la correzione è entrata nella check esistente**, non in una funzione
nuova: il frontend chiama una cosa per riga, e con due sarebbe stato il backend
a dedurre di che riga si tratta — il §7 riaperto un passo più in là.

`20260827-03`; pgTAP `plan(13)` → `plan(14)`.
