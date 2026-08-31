# Brief DB/BE — l'IVA non ha un risolutore: l'articolo decide da solo, e il regime del cliente è scritto e mai letto

> **Destinatario:** team DB (`dev/db-tid`) per le voci 1 e 3, backend per la 2.
>
> **Origine.** Domanda di Tid del 2026-08-27, durante il collaudo della prova 9 di
> [collaudo-in-app-ddt-righe-senza-prezzo.md](../work-done/collaudo-in-app-ddt-righe-senza-prezzo.md):
> *«nel caso ad esempio di omaggio o anche di reverse charge l'IVA non discende
> più dall'articolo, è giusto che possa essere modificata o no?»*.
>
> Il caso da cui è partita — una riga di ri-consegna senza aliquota — è
> l'inciampo, non il tema: quello sta in
> [brief-db-ddt-riconsegna-eredita-testata.md](../work-done/brief-db-ddt-riconsegna-eredita-testata.md).
> Cercando la risposta è emerso che **l'IVA, in questo progetto, la decide
> l'articolo e nessun altro** — e che le colonne dove vive il regime fiscale del
> cliente sono compilate dall'operatore e lette da nessuno.
>
> **Stato.** 2026-08-27 — analisi sulla **struttura**: corpo delle funzioni,
> colonne, whitelist del backend, template del frontend. Nessuna misura sui dati,
> nessun file scritto, nessuna migrazione.
>
> ⭐ **Rev 2 — 2026-08-28.** Rilettura critica con Tid. `D2` è **superata** da
> `D7`, e con essa cade l'idea che il regime del cliente viva in una colonna di
> default: l'influenza del soggetto sull'IVA passa **sempre** da un titolo
> registrato e documentato. Ne discendono `D7`…`D11`, la correzione di quattro
> fatti che il documento dava per veri (§R) e una voce **nuova** che con l'IVA
> non c'entra — CIG/CUP/commessa sul cliente (`D9`).
>
> ✅ **2026-08-29 — nessuna decisione resta aperta.** `D1`, l'ultima, è decisa:
> l'IVA di riga **non è modificabile a mano**. Il brief è **completo lato
> disegno**; quello che resta è costruire, nell'ordine del §5.
>
> ⭐ Le decisioni stanno nel §D e nel §D-bis, etichettate una per una, e non vanno
> ri-discusse a valle.
>
> **Correlati:**
> [config.iva](/dbzero/config/tabelle/iva) ·
> [anagrafiche.clienti](/dbzero/anagrafiche/manual/clienti) ·
> [fn_get_iva_override](/dbzero/script/funzioni/fn_get_iva_override) ·
> [trgfn_ddt_guard_causale_emissione](/dbzero/vendite/funzioni/trgfn_ddt_guard_causale_emissione) ·
> [causali_trasporto §fatturabile](/dbzero/config/manual/causali_trasporto)

---

## 0. Le voci in una riga

| # | Cosa | Gravità | Chi lo vede oggi |
| --- | --- | --- | --- |
| **1** | L'IVA si determina in **due punti indipendenti** (riga di documento, riga di fattura) e in entrambi **dal solo articolo**. Uno dei due è nel **frontend** | 🔴 il numero fiscale di una riga non ha una sede | nessuno: finché tutti i clienti sono a regime ordinario i due valori coincidono |
| **2** | `clienti.iva_id` (**`NOT NULL`**), `clienti.split_payment`, `clienti.cliente_pa`: l'operatore li compila nel drawer, **nessun documento li legge**. ⭐ Rev 2: il rimedio **non** è farli leggere — è `D7` (l'`iva_id` si toglie) e `D8` (gli altri due salgono al soggetto) | 🔴 un campo che promette una cosa che non succede | chi imposta un cliente in reverse charge e ritrova l'aliquota ordinaria in fattura |
| ~~**3**~~ | ~~Il gate all'emissione del DDT pretende il **prezzo** e non l'**aliquota**~~ — ✅ **FATTA il 2026-08-28**, e con una regola migliore di quella scritta qui: §R-1 | — | — |
| **4** | La **dichiarazione d'intento** non ha nessuna sede: la natura `N3.5` è seminata e **orfana** — nessun codice IVA la usa, nessuna tabella tiene protocollo, validità e plafond. ⭐ Rev 2: non è un caso unico ma **il primo di una famiglia** (`D10`) | 🔴 un titolo di non imponibilità che il sistema non sa rappresentare | chi vende a un esportatore abituale: oggi non ha nessuna strada |
| **5** | ⭐ **Voce nuova (Rev 2), e con l'IVA non c'entra**: `clienti.codice_cig`, `codice_cup`, `codice_commessa` stanno su una riga **per fornitura**, mentre nominano un **contratto**. Un cliente PA con tre contratti ha tre CIG | 🔴 un dato per-contratto tenuto in anagrafica: si ripete su ogni fornitura dello stesso contratto e non ne regge due sulla stessa | nessuno **ancora**: non li legge niente, e il builder XML FatturaPA non è scritto. È la ragione per cui spostarli **adesso** costa zero |

⭐ **Cosa hanno in comune**: sono lo stesso buco visto da tre distanze. Il prezzo
ha un risolutore centralizzato e una memoria che ne vieta gli scavalcamenti
(`feedback_pricing_centralizzato`); l'IVA — l'**altro** numero di una riga
fiscale — non ha niente.

> ### ⚠️ Questa tabella è la DIAGNOSI del 2026-08-27, ed è scritta al presente
>
> Al **2026-08-30** tre voci su quattro non descrivono più il sistema, e la
> tabella **non si riscrive**: è il punto di partenza, e cancellarlo renderebbe
> incomprensibili le decisioni che ne sono nate. Ecco però cosa è cambiato, per
> non lasciare un lettore con un quadro falso — il dettaglio è nel **§8-sexies**.
>
> | Voce | Oggi |
> | --- | --- |
> | **1** — due determinazioni indipendenti | 🟡 **una sede c'è**: `vendite.fn_resolve_iva_riga`. ⛔ Ma i due punti la chiamano **ancora no** — è `I3`/`I4`, ed è backend. La voce resta aperta finché non chiamano |
> | **2** — i tre campi su `clienti` | ✅ **chiusa**: `iva_id` tolta, `split_payment` e `cliente_pa` saliti su `soggetti`, e dal 2026-08-30 **qualcuno li legge** (`I5`) |
> | **4** — la dichiarazione d'intento senza sede | ✅ **chiusa**: `anagrafiche.soggetti_titoli_iva` e la sua famiglia, con plafond e movimenti; `N3.5` non è più orfana |
> | **5** — CIG/CUP/commessa in anagrafica | ✅ **chiusa** lato dati: sono su `vendite.contratti`. 📌 Lo **snapshot in fattura** va con `I4`, cioè col backend |

---

## D. Decisioni e questioni aperte — 2026-08-27

> Stanno qui in testa perché ognuna delle richieste del §5 discende da una di
> esse, e perché una decisione che vive solo dentro una conversazione viene
> ri-aperta al primo dubbio.
>
> ⚠️ **Ognuna dice di chi è.** `D2` e `D3` sono **decisioni di Tid**, prese a
> parole il 2026-08-27. ~~`D1` è **aperta**~~ → **decisa il 2026-08-29**, e il
> testo che segue conserva la proposta e i due argomenti perché è così che ci si
> è arrivati. `D4` non è una decisione affatto — è una constatazione
> tecnica. Attribuire a qualcuno una scelta che non ha fatto è il modo in cui un
> documento diventa inaffidabile, e qui non serve nemmeno: l'argomento regge da
> sé anche senza una firma sotto.

### D1 · ✅ **DECISA (Tid, 2026-08-29)** — l'IVA di riga **non è modificabile a mano**

> ✅ **Chiusa.** L'argomento contro — *«esistono titoli per-operazione che il
> risolutore non coprirà, e togliere la casella toglie l'unica uscita»* — è
> **caduto con `D10`**: la famiglia dei titoli assorbe tutti e quattro i casi
> noti, e ognuno **si registra** invece di digitarsi. Non resta nessun titolo
> fuori dal risolutore.
>
> **La regola:** su DDT, ordini e preventivi, in **CREATE e in EDIT**, il valore
> lo produce il risolutore. L'operatore non lo digita e non lo corregge.
> Realizzazione in `I6`, che va **per ultima** — vedi l'avvertenza sull'ordine.
>
> ⚠️ **E oggi è mezzo bloccata, che è la forma peggiore** (verificato 2026-08-29):
> in **EDIT** il campo è grigio nei tre form (`:disabled="isEdit"`), in **CREATE**
> è libero, e l'**API accetta l'aggiornamento in tutti e tre i casi** — `iva_id`
> è dentro le chiavi di update di `ddt_service`, `ordini_service` e
> `preventivi_service`. Non protegge (chi chiama l'endpoint scavalca) e impedisce
> lo stesso (all'operatore il campo è grigio, e ciò che è grigio oggi è il valore
> **detto dall'articolo**). `I6` deve chiudere entrambe le metà, non una.

**Proposta originale (2026-08-27): no**, su nessun documento. Varrebbe per **DDT, ordini e preventivi**
— le tre sedi che hanno una riga con aliquota — sia in CREATE che in EDIT: il
valore lo produce il risolutore (**D2**), l'operatore non lo digita e non lo
corregge.

**L'argomento a favore, ed è il cuore di tutto il brief**: *l'IVA non è una scelta, è una
conseguenza*. Qui sta la differenza col **prezzo**, che invece è editabile a
ragion veduta — un prezzo si **negozia**, e infatti chi lo scavalca passa dal
workflow di approvazione L1/L2. L'IVA non si negozia con nessuno: si applica. Un
campo digitabile inviterebbe ad «aggiustare» un dato che dipende dalla legge, e
lo farebbe **senza traccia e senza approvazione**, perché per l'IVA un workflow
di scostamento non ha nemmeno senso.

⚠️ **Ma «non modificabile» è corretto solo se il valore c'è ed è giusto.** Oggi
il blocco c'è (`:disabled="isEdit"` nei tre form) e blocca ciò che ha detto
l'articolo: su un cliente fuori regime ordinario blocca un valore **sbagliato**
che nessuno può correggere, e su una riga generata dal DB blocca un **buco**.
Bloccare un buco non protegge una scelta, la impedisce. Per questo D1 **non è
applicabile prima** di D2: vedi l'avvertenza sull'ordine in `I6`.

⭐ **L'argomento contro, e va guardato prima di decidere**: esistono casi in cui
la controparte comunica il proprio titolo **sull'operazione singola** e non sul
rapporto — una dichiarazione d'intento che copre un plafond, un'operazione
occasionale fuori regime. Se quei casi si modellano (una dichiarazione d'intento
è un documento con validità e importo, non un flag), allora restano dentro il
risolutore e D1 regge; se non si modellano, l'unica uscita per l'operatore
sarebbe proprio la casella che D1 chiude. **La domanda da decidere non è «bloccare
sì o no», è «il risolutore arriverà a coprire tutti i titoli, o ne resta fuori
qualcuno?»** — e finché la risposta non c'è, bloccare significa scegliere di non
avere un'uscita.

⭐ **Aggiornamento in giornata**: la dichiarazione d'intento — che era proprio il
caso che sembrava non copribile — ha una sua forma modellabile, ed è il **§2.6**.
Se quella strada si prende, l'argomento contro cade e `D1` può essere decisa
«non modificabile». Resta da verificare che non ci siano **altri** titoli
per-operazione fuori dal risolutore: è quello, e solo quello, che tiene `D1`
ancora aperta.

⚠️ **E oggi il blocco è una convenzione del solo frontend.** Il backend
l'aggiornamento dell'IVA lo accetta: `iva_id` è dentro `_UPDATE_KEYS_RIGA` in
`ddt_service.py`. Una regola presidiata da un `:disabled` in un template non è
una regola — è un suggerimento che chiunque chiami l'endpoint scavalca.

### ~~D2 · quando cliente e articolo divergono, vince il cliente~~ — ⛔ **SUPERATA il 2026-08-28 da `D7`**

> ⛔ **Non applicare.** Tenuta per storia, perché è l'inquadramento da cui è
> partito tutto il brief e perché §2.4 e `I2` sono nati con il suo vocabolario.
> La regola valida è in **`D7`**.
>
> **Perché è caduta, in una riga**: la domanda «chi vince?» ha senso solo se i
> due rispondono alla **stessa** domanda, e `D6` — decisa lo stesso giorno,
> poche ore dopo — ha stabilito che non è così. Sotto `D6` non c'è nessuna
> precedenza da assegnare: l'articolo dice sempre l'aliquota ordinaria, il
> soggetto può solo **sostituirla** con un titolo. `D2` è il residuo
> dell'inquadramento precedente, rimasto scritto accanto a quello che lo
> smentisce.
>
> ⚠️ E c'era un secondo difetto, strutturale: la regola faceva vincere
> `clienti.iva_id`, che è **`NOT NULL` senza default DB** e che il backend
> riempie col parametro `DEFAULT_IVA_ID` quando il chiamante non la passa
> (`clienti_service.py`). Ogni cliente porta quindi un codice IVA **che nessuno
> ha scelto**, indistinguibile da uno scelto apposta: «vince il cliente»
> significava far vincere un valore *mai espresso* su uno *espresso*.
> Specularmente `catalogo.articoli.iva_id` è **nullable** — è l'articolo, non il
> cliente, ad avere la forma di chi *può* tacere.

~~La ragione sta sul modello, non sulla preferenza: *l'articolo dichiara la natura
merceologica* — cosa è quella merce, e quindi quale aliquota le compete in via
ordinaria. *Il cliente dichiara il regime* — in che rapporto fiscale è quella
controparte con chi vende (esente art. 8, reverse charge, PA in scissione dei
pagamenti). Il regime è una proprietà del **rapporto**, e un rapporto vince su
una classificazione merceologica perché la modifica **per legge**, non per scelta.~~

### D3 · ✅ **DECISA (Tid)** — un'aliquota assente, **dove serve il prezzo**, è un errore, non un'annotazione

Rilievo di Tid: *«l'IVA deve esserci sempre, se non indicata deve andare in
errore — forse solo se il prezzo è null, IVA null»*. La condizione è **la stessa**
del prezzo e la dichiara la stessa causale: dove la merce si vende servono
entrambi, dove non si vende non serve nessuno dei due. Realizzazione nel §3.

⛔ **Opzione scartata, ed era mia**: un Tag «Senza IVA» nella lista righe, sul
modello del «Senza prezzo» della DEC-6. Sbagliata, e la differenza è netta — il
prezzo **può legittimamente mancare** (DDT di solo trasporto: il Tag distingue
«non si applica» da «me ne sono dimenticato», ed è per quello che esiste),
l'aliquota su un documento che vende **no**. Rendere elegante la vista di uno
stato che non deve esistere è il modo di farlo sopravvivere.

### D4 · 📌 **Constatazione, non decisione** — `split_payment` e `cliente_pa` non sono un codice IVA

La scissione dei pagamenti non cambia l'aliquota: cambia **chi versa l'imposta
all'erario**, e in fattura elettronica è l'`EsigibilitaIVA`. Restano **fuori** dal
risolutore e viaggiano sulla testata della fattura e nel payload SDI (`I5`).
Confonderli farebbe nascere codici IVA fasulli a catalogo — e un codice fasullo,
una volta seminato, se lo porta dietro ogni documento emesso.

### D5 · ✅ **APPROVATA (Tid)** — il consumo del plafond è un **registro di movimenti**, non un numero sovrascritto

`imponibile_utilizzato` resta la colonna memorizzata che `P3` chiede, ma è la
**somma di un registro**: ogni fattura, ogni nota di credito e ogni **forzatura
manuale** è una **riga**, con motivo, autore e data. Dettaglio e ragioni nel
**§2.6.2**.

⭐ La ragione per cui non poteva restare un numero: una colonna memorizzata *e*
forzabile a mano diverge in silenzio da ciò che rappresenta, e su un plafond quel
numero è precisamente ciò che l'Agenzia delle Entrate verifica. Una forzatura che
sovrascrive non lascia traccia del **perché**; una forzatura che è una riga **è**
la traccia.

### D6 · ✅ **DECISA (Tid)** — il risolutore ha **due stadi**, e la cascata è solo sul primo

Sotto la parola «regime» convivevano due meccanismi che rispondono a domande
diverse: **quale aliquota compete alla merce** (varia per utility perché varia la
**merce**) e **se la controparte ha un titolo che la sostituisce** (della partita
IVA). Non competono, quindi non c'è nessuna precedenza da invertire. Forma
completa nel **§2.7**.

---

## D-bis. Le decisioni della Rev 2 — 2026-08-28

> Tutte prese a parole da Tid il 2026-08-28, salvo dove indicato. `D7` sostituisce
> `D2`; le altre sono nuove e nessuna ri-apre ciò che era già deciso il 27.

### D7 · ✅ **DECISA (Tid)** — l'aliquota la dice la **merce**; il soggetto porta solo un **titolo documentato**

**Sostituisce `D2`.** Non è un'inversione di precedenza: è la constatazione che
non c'era nessuna precedenza da assegnare.

* **quale aliquota compete** → la decide la **merce e il suo uso**: articolo →
  catena del prezzo → tipo di utenza (`D11`). Il soggetto non entra **mai** in
  questa domanda;
* **se quella aliquota viene sostituita** → lo decide un **titolo del soggetto**,
  registrato, datato e con una prova documentale (`D10`). Mai una colonna di
  default appesa all'anagrafica.

⭐ **Il principio, ed è ciò che il brief cercava dall'inizio**: *l'influenza del
soggetto sull'IVA passa sempre da un titolo, mai da un default.* È la ragione per
cui `clienti.iva_id` se ne va (`D7-bis`) e **non** viene sostituita da un
`soggetti.iva_id`: spostare la colonna avrebbe riprodotto il difetto un piano
più su.

⚠️ **La prova che regge**: `catalogo.articoli.iva_id` è nullable, quindi
l'articolo può dire «non ho un'opinione»; `clienti.iva_id` è `NOT NULL` con
default di sistema, quindi non può. Una regola che fa vincere chi non sa tacere
su chi sa tacere è invertita rispetto alla struttura, indipendentemente da quale
sia la risposta fiscale giusta.

#### D7-bis · ✅ **DECISA (Tid)** — `anagrafiche.clienti.iva_id` **si toglie**, non si sposta

Poteva avere tre significati, e tutti e tre hanno già una sede migliore:

| Se significava… | Sede giusta | Stato |
| --- | --- | --- |
| «questo soggetto ha un'agevolazione» | un **titolo** del soggetto (`D10`) | da costruire |
| «questa utility tratta l'IVA in modo suo» | `config.tipi_utenze.iva_id` (`D11`) | **esiste già**, nessuno la legge |
| «questa merce ha questa aliquota» | `catalogo.articoli.iva_id` | esiste, ed è l'unica che arriva sui documenti |

Non le resta un quarto lavoro. ⭐ **`DROP COLUMN` diretto, senza passare da un
`nullable` transitorio** (Tid: *«si può fare subito perché non usato e non ho
produzione»*, coerente con `project_no_produzione_solo_sviluppo`). Si porta
dietro la whitelist del BE (`clienti_repository.py`, `clienti_service.py`, il
default `DEFAULT_IVA_ID`), il campo nel `ClienteDrawer.vue` e il ramo in
`anagrafiche.fn_update_cliente`.

⚠️ **C'è un consumatore da non dimenticare**, ed è l'unico: `clienti.iva_id`
**non** è letta da «nessuno» come dice il §4. La legge
`BillingAccountRepository.get_cliente_defaults` e la restituisce l'endpoint
`/vendite/preventivi/form-defaults/` (`iva_id`, `iva_codice`, `iva_descrizione`).
È il **frontend** a buttarla via: il `PreventiviDrawer.vue` commenta *«per
termine/iva sovrascriviamo solo se vuoti»* ma l'`apply` tocca solo il termine di
pagamento — e comunque `vendite.preventivi` una colonna IVA di testata non ce
l'ha. Vanno tolte anche quelle tre chiavi dal payload.

### D8 · ✅ **DECISA (Tid)** — `split_payment` e `cliente_pa` salgono su **`anagrafiche.soggetti`**

Un ente **è** o **non è** una Pubblica Amministrazione: non lo è per il gas e non
per l'acqua. Oggi stanno su `anagrafiche.clienti`, che è **una riga per
fornitura** (`UNIQUE uq_clienti_istanza_utility`): due forniture dello stesso
soggetto possono dichiarare cose opposte e niente lo impedisce.

⭐ **Restano fuori dai titoli di `D10`**, ed è `D4`: non cambiano l'aliquota,
cambiano **chi versa l'imposta** — in fattura elettronica sono `EsigibilitaIVA`.

⭐ **Il binario d'arrivo esiste già e non va costruito**: `vendite.fatture_righe`
ha già le colonne `esigibilita` e `split_payment`, e
`vendite.fatture_riepiloghi_iva` raggruppa già per `iva_id` + `natura_id` +
`esigibilita` + `split_payment` (lo fa `fn_ricalcola_riepilogo_iva_fattura`).
Manca **solo l'anello che le riempie**: una lettura in più quando nasce la riga
di fattura. Questo rende `I5` una voce corta, non un cantiere.

⚠️ **Sede: `soggetti`, non `soggetti_ruoli`** — decisione di Tid, con la porta
lasciata aperta: *«aggiungerlo in futuro sui ruoli se dovesse servire si farà, e
sarà predominante rispetto al soggetto»*. Chi scriverà il lettore lo tenga
presente: la forma futura è un `COALESCE(ruolo, soggetto)`, quindi conviene che
la lettura passi da **un solo punto** fin da subito, anche se oggi quel punto
legge una colonna sola.

### D9 · ✅ **DECISA (Tid)** — CIG, CUP e commessa vanno **sul contratto**, e in fattura come **snapshot**

È la voce 5 del §0, e con l'IVA non c'entra niente: si è trovata guardando le
colonne vicine sul cliente.

**Tutti e tre insieme, su `vendite.contratti`.** La ragione è che in fattura
elettronica stanno **nello stesso blocco** (`DatiContratto` / `DatiOrdineAcquisto`:
`IdDocumento`, `CodiceCUP`, `CodiceCIG`, `CodiceCommessaConvenzione`): nascono
insieme, si compilano insieme e nominano lo stesso atto. Separare la commessa
sull'ordine vorrebbe dire costruire un blocco XML da due tabelle con due cicli di
vita, senza guadagnarci nulla.

⚠️ **Non basta metterli sul contratto, o non arrivano mai in fattura**:
`vendite.fatture` **non ha nessun collegamento al contratto** — solo
`billing_account_id` e la coppia `sorgente_tipo_id`/`sorgente_uid`. Servono
**copiati sulla fattura all'emissione**, ed è anche la forma giusta nel merito:
un CIG corretto in anagrafica domani non deve cambiare su una fattura già emessa.
⭐ Il pattern esiste già su quella stessa tabella — `emittente_snapshot`,
`cliente_snapshot`, `termine_pagamento_snapshot` (jsonb).

⭐ **Perché adesso e non dopo**: oggi quelle tre colonne **non le legge nessuno**
tranne il CRUD del cliente (verificato: non esistono in nessun'altra tabella del
progetto), e il **generatore XML FatturaPA non è ancora scritto** —
`fn_prepare_sdi_payload` prepara solo il tentativo d'invio, non il contenuto.
Spostarle prima che il builder nasca costa zero; dopo significa riscriverlo.

📌 **Fuori perimetro, dichiarato**: negli accordi quadro PA il contratto ha un CIG
«padre» e ogni ordine attuativo ne ha uno derivato. Se quel caso arriverà, la
forma è **gli stessi tre campi sull'ordine**, nullable, col contratto come
ripiego (`COALESCE`). Non si fa ora e non è una previsione sui dati: è
l'annotazione di dove andrebbe, visto che il lettore sarà uno solo.

### D10 · ✅ **DECISA (Tid)** — non `soggetti_intento` ma **`anagrafiche.soggetti_titoli_iva`**: è una **famiglia**

Il §2.7.5 lo sospettava (*«è la prima di una famiglia, conviene che nasca
sapendolo»*). Non è più un sospetto: Tid ha nominato i casi, e sono almeno
quattro.

| Titolo | Di chi | Vale per | Ha un tetto? | La prova |
| --- | --- | --- | --- | --- |
| **Dichiarazione d'intento** | soggetto → **verso un emittente** | tutto | **sì**, il plafond | protocollo Agenzia Entrate |
| **Uso industriale/agricolo** gas-EE | soggetto → verso un emittente | solo quella fornitura | no | dichiarazione resa al fornitore |
| **Agevolata disabili** (L. 104) | soggetto | **solo certe merci** | no | certificazione / prescrizione |
| **Cooperative sociali, ONLUS** | soggetto | certe prestazioni | no | iscrizione all'albo |

⭐ **Uno schema solo**: *chi* × *per cosa vale* × *da quando a quando* × *con
quale prova* → **quale codice IVA sostituisce quello ordinario**. Solo il primo
ha un contatore che si consuma — e quindi il plafond è una **proprietà di un
tipo di titolo**, non la colonna portante della tabella. Nascere col nome
`soggetti_intento` avrebbe scambiato il caso particolare per la regola.

**La forma:**

* **`anagrafiche.soggetti_titoli_iva`** — il soggetto proprietario;
  l'**emittente fiscale destinatario**; il **tipo di titolo** (vocabolario a
  seed: `INTENTO`, `USO_INDUSTRIALE`, `AGEVOLATA_104`, `COOPERATIVA`…);
  `validita` come **`daterange`**; l'`iva_id` che sostituisce; gli estremi
  documentali (protocollo, data di ricezione, riferimento);
* **l'ambito, dichiarato esplicitamente** — non lasciato al `NULL`
  (`feedback_null_nelle_chiavi_due_forme`): una colonna che dice *se* il titolo
  vale per tutto o è ristretto, e quando è ristretto le righe figlie che dicono a
  cosa. ✅ **Decisione di Tid: l'ambito arriva fino al singolo articolo** — quindi
  i livelli sono **categoria di merce** (`catalogo.articoli.gruppo_voce_id` /
  `tipo_voce_id`, che esistono già) **e articolo**;
* **il plafond e il registro dei movimenti** (`D5`) **solo per i tipi che un tetto
  ce l'hanno**. Il registro resta esattamente come deciso: fattura `+`, nota di
  credito `−`, forzatura manuale `±` con motivo obbligatorio;
* ⚠️ **il guard di non sovrapposizione** di §2.6.4 va ripensato sulla forma nuova:
  la chiave non è più «un soggetto», è **(soggetto, emittente, tipo, ambito)**.
  Due titoli dello **stesso tipo e stesso ambito** validi insieme restano
  un'ambiguità da chiudere con `EXCLUDE USING gist`; due titoli di **tipo
  diverso** possono coesistere legittimamente, ed è il caso da non bloccare per
  errore.

#### D10-bis · ⭐ Perché l'**emittente** compare, se il titolo è del soggetto

Tid, 2026-08-28: *«è una tabella legata al soggetto e basta, quella partita IVA
ha una dichiarazione d'intento»*. Il **proprietario** è il soggetto, ed è giusto:
è lui l'esportatore abituale, non un suo contratto.

⚠️ Ma una dichiarazione d'intento non è un'etichetta che il cliente si appende
addosso: è un **documento che presenta a un fornitore preciso**, con un
protocollo suo e un importo suo. Lo stesso esportatore abituale che compra da due
società emittenti presenta **due dichiarazioni**, ognuna col suo plafond. E il
modello ammette più emittenti: `vendite.contratti.emittente_fiscale_id` è
**`NOT NULL`**.

⛔ Senza quella seconda colonna, i plafond di due emittenti si consumerebbero da
**un solo contatore** — un errore silenzioso su precisamente il numero che
l'Agenzia delle Entrate verifica. **Proprietario: il soggetto. Destinatario:
l'emittente.** Due colonne, stessa riga.

### D12 · ⚠️ **PRECISAZIONE** — lo stadio B si valuta **per riga**, e l'ambito è un **filtro**, non un'etichetta

Rilievo di Tid, 2026-08-28: *«alcune aliquote agevolate, esempio quelle per
disabilità, si possono applicare solo su alcune categorie di prodotti; se alla
seconda passata vince quella del soggetto il rischio è che si applichi a tutto»*.

⛔ **È il difetto giusto da temere**, e nasce da come `D7` era stato raccontato:
«il titolo sostituisce l'aliquota ordinaria» suona come un interruttore di
documento. Non lo è.

**Lo stadio B si valuta riga per riga**, e per ogni riga il titolo entra **solo
se l'articolo di quella riga ricade nel suo ambito**. Un documento con dieci
righe e un titolo `AGEVOLATA_104` ristretto a due articoli produce **due** righe
agevolate e otto ordinarie. L'ambito di `D10` non è documentazione del titolo:
è la **condizione di applicabilità**, e senza di essa il titolo sarebbe
esattamente il `clienti.iva_id` che `D7-bis` ha tolto — un valore che vince su
tutto perché nessuno gli ha detto dove fermarsi.

⚠️ **Corollario sulla firma**: il risolutore riceve **l'articolo**, non solo il
documento. Era già così per lo stadio A; ora è vincolante anche per B.

### D13 · ✅ **DECISA (Tid)** — due titoli sulla stessa riga: **vince il più specifico**

Discende da `D12`. L'`EXCLUDE` di `D10` impedisce due titoli **dello stesso tipo
e stesso ambito** validi insieme; due titoli di **tipo diverso** che coprono la
stessa riga sono invece possibili in linea di principio.

**Regola: articolo > categoria di merce > tutto.** È la stessa dello stadio A e
della cascata degli indirizzi — nessun secondo vocabolario. A parità di
specificità restano due titoli indistinguibili: quello è un **errore di
configurazione** e si solleva, non si risolve scegliendone uno.

⭐ **Ma è un presidio, non un percorso ordinario, e la ragione è di modello**
(rilievo di Tid, 2026-08-28): l'esempio che avevo portato — intento +
agevolazione disabili sullo stesso soggetto — **non regge**, perché la
dichiarazione d'intento presuppone una **partita IVA** (un esportatore abituale)
mentre l'agevolazione per disabilità è di una **persona fisica**, sul codice
fiscale. Gli altri incroci sono altrettanto improbabili.

⚠️ **Per questo la regola resta scritta lo stesso.** Non è impossibile che i due
identificativi convivano — `anagrafiche.soggetti` porta `partita_iva` **e**
`codice_fiscale`, entrambe nullable, e una ditta individuale le ha tutte e due —
ed è il caso di `AGENTS.md`: *«zero occorrenze non significa che il caso non
esiste»*. Una regola dichiarata che non scatta mai costa una riga; un'ambiguità
che si risolve sull'ordine degli id costa una fattura sbagliata.

### D14 · ✅ **DECISA (Tid)** — il risolutore prende una **data di riferimento**, non legge `now()`

Rilievo di Tid, 2026-08-28: *«la differenza tra documento e fattura è che,
temporalmente, venendo eseguito prima potrebbe stabilire l'aliquota di quel
momento, che potrebbe essere diversa da quella del momento della fattura»*.

⭐ **È più preciso di come `P1` era scritto.** «Il documento proietta, la fattura
decide» faceva pensare a due calcoli di natura diversa. Non lo sono: è la
**stessa funzione, eseguita due volte, in due momenti**. Il DDT non produce un
valore "provvisorio" perché è di seconda classe — produce il valore **giusto alla
sua data**, e la fattura produce quello giusto **alla sua**. Se divergono non c'è
nessun errore: è cambiato il mondo in mezzo (un titolo scaduto, un plafond
esaurito, una dichiarazione revocata).

⛔ **Ne discende un vincolo di firma, e va preso adesso come la ripartizione del
§2.7.3**: la funzione riceve una **data di riferimento come parametro** e non
chiama mai `now()` / `CURRENT_DATE` al suo interno.

Le ragioni, dopo la correzione di `D15`:

* ⭐ **la principale**: la fattura deve risolvere **alla propria data documento**,
  che non è l'istante in cui gira il calcolo. `vendite.fatture.data` ha default
  `script.fn_data_operativa()` — il progetto ha già una nozione di data operativa
  distinta dall'orologio, e un risolutore che guardasse `CURRENT_DATE`
  risponderebbe alla domanda sbagliata ogni volta che il lotto gira il giorno
  dopo;
* un **pgTAP** non potrebbe costruire il caso «titolo scaduto» senza aspettare il
  calendario.

⛔ ~~«senza, ristampare un documento vecchio darebbe un risultato diverso da
quello stampato»~~ — **argomento ritirato il 2026-08-28**: era sbagliato, e lo
corregge `D15`. Una ristampa **non chiama il risolutore affatto**, quindi non
poteva provare niente sulla sua firma. La conclusione regge, la ragione no —
ed è il caso peggiore di `AGENTS.md`: *la conclusione giusta appoggiata
all'argomento sbagliato*.

⚠️ **Secondo corollario, e tiene pulita la parte più delicata**: il risolutore è
in **sola lettura** (`STABLE`). Non consuma il plafond. Il consumo è un
**passo separato**, che fa **solo la fattura** (`P1`), scrivendo una riga nel
registro di `D5`. Un risolutore che consuma sarebbe impossibile da chiamare per
mostrare un'anteprima — cioè proprio l'uso che ne fa il documento.

### D15 · ✅ **DECISA (Tid)** — il risolutore gira **fino alla DEFINITIVA**, e da lì il valore è **congelato**

Rilievo di Tid, 2026-08-28: *«la ristampa di un documento non dovrebbe far girare
il risolutore, in quel caso si prende sempre l'IVA esistente nel documento. In
bozza passa il risolutore, tra bozza e definitiva dovrebbe ripassare, ma da
definitiva (compreso) in poi si ristampa sempre senza rigenerare l'aliquota.
Questo vale anche per la fattura»*.

| Momento | Il risolutore gira? |
| --- | --- |
| documento in **bozza** | ✅ sì, a ogni modifica delle righe |
| passaggio **bozza → definitiva** | ✅ sì, ed è **l'ultima volta** |
| da **definitiva** compresa in poi (ristampa, invio, riemissione del PDF) | ⛔ **mai più**: si legge il valore scritto sulla riga |

⭐ **Non è una regola nuova: è la stessa che il DB già applica al riepilogo IVA.**
`vendite.fn_ricalcola_riepilogo_iva_fattura` rifiuta il ricalcolo fuori da
`('DRAFT', 'EMESSA')` — *«oltre quella soglia il documento è uno snapshot
fiscale»*. Il risolutore deve obbedire **alla stessa soglia**, non a una sua:
due finestre di congelamento diverse sullo stesso documento sono due verità che
divergono in silenzio.

⚠️ **Ma la soglia oggi è una lista di codici scritta a mano nel corpo della
funzione** (`NOT IN ('DRAFT','EMESSA')`), e va **dichiarata** — il progetto la
regola dell'hardcode ce l'ha già (`chiude_lotto` come unico meccanismo di
chiusura lotto).

✅ **DECISO (Tid, 2026-08-29)**: nasce **`config.stati_doc_fiscale.congela_fiscale`**,
e **`fn_ricalcola_riepilogo_iva_fattura` va portata a leggerlo** al posto della
lista. → richiesta **`I10`**.

⛔ **`DEFAULT true`, e correggo qui una riga che avevo scritto sbagliata**
(`DEFAULT false`, in questa sezione fino al 2026-08-29). Il ragionamento era:
*«il `NOT IN` dice la cosa per esclusione, quindi si allarga da sola a ogni stato
nuovo»* — trattato come un difetto. **Non lo è: è la direzione sicura**, ed è
l'unica parte di quella forma che meritava di sopravvivere.

Cosa succede a uno stato futuro che nessuno classifica:

| Default | Stato nuovo non classificato | Se la classificazione giusta era l'altra |
| --- | --- | --- |
| `false` | ricalcolo **ammesso** | uno **snapshot fiscale cambia in silenzio** |
| `true` | ricalcolo **rifiutato** | un **errore parlante**, e qualcuno sistema il seed |

⭐ Il difetto del `NOT IN` era **solo** che è cablato e destinato a essere
duplicato dal risolutore. Il suo default era giusto, e `DEFAULT true` lo
conserva: chi introduce uno stato senza pensarci trova un errore, non una fattura
riscritta.

⚠️ Due avvertenze operative per chi lo scriverà:

* il valore si semina **dal CSV** `80_data/sql/config/stati_doc_fiscale.csv`, che
  va esteso di una colonna su **tutte** le righe — non con un `UPDATE` SQL, che
  creerebbe una seconda sorgente di verità;
* la funzione è **esistente**: il corpo si prende dalla **doc auto-gen** e si
  crea un file **nuovo** con numerazione successiva. Partire dallo YAML che la
  definisce oggi farebbe regredire le revisioni intermedie (fra cui il fix
  del 2026-08-02 sui due guard di stato).

📌 `congela_fiscale = true` su `DEFINITIVA`, `INVIATA`, `REGISTRATA`, `ANNULLATA`;
`false` su `DRAFT` ed `EMESSA`. ⭐ Scritto così il flag dice **una cosa sola** ed è
verificabile riga per riga — a differenza della lista `NOT IN`, che diceva la
stessa cosa **per esclusione** e quindi si allargava da sola a ogni stato nuovo.

⛔ **Tre scorciatoie da non prendere, tutte e tre disponibili e tutte e tre
sbagliate**, verificato sul seed di `config.stati_doc_fiscale`:

1. **`fase`** non serve: `EMESSA` (ricalcolo ammesso) e `DEFINITIVA` (congelata)
   hanno **la stessa** `fase = 'IN_CORSO'`. Il flag che cerchiamo non c'è;
2. **`ordine`** non serve, ed è la trappola più invitante (`DRAFT` 10, `EMESSA`
   20, `DEFINITIVA` 30): *«la colonna `ordine` di `config.stati_doc_*` non è un
   ciclo di vita»*. `INVIATA` è 40 e `ANNULLATA` 70, ma una soglia numerica su
   quella colonna è una convenzione grafica scambiata per una macchina a stati;
3. ⛔ **`chiude_lotto` non si riusa**, benché oggi sia `true` esattamente su
   `DEFINITIVA` e su nessun altro stato (c'è pure un `UNIQUE` che lo garantisce).
   Risponde a **un'altra domanda** — «questo stato chiude il lotto?» — e
   appoggiarci sopra il congelamento fiscale è la forma esatta di
   `reference_flag_composto_non_e_invertibile`: il giorno che le due risposte
   divergono, non c'è modo di separarle.

#### D15-bis · Il plafond si consuma **nello stesso momento in cui il valore si congela**

Discende da `D15` e da `P1`. Il consumo non avviene «quando si fa la fattura» in
senso vago: avviene **nella transizione a DEFINITIVA**, insieme all'ultima corsa
del risolutore. Le due cose sono **una sola unità atomica**
(`feedback_atomicita_madre_db`) — l'ultima risoluzione decide la spezzatura di
`P2`, e la spezzatura decide quanto plafond va consumato. Separarle
significherebbe scrivere nel registro una quota che il documento non porta.

⚠️ **E qui il lock diventa necessario, non prudenziale.** Finché due fatture
stanno in bozza o in EMESSA, entrambe **proiettano** sullo stesso residuo non
ancora consumato: è corretto, sono anteprime. Ma se arrivano alla DEFINITIVA in
parallelo, senza un lock sul titolo consumano tutte e due la stessa capienza e il
plafond va sotto zero in silenzio. ⭐ Serve anche un **ordine deterministico** fra
le due — chi arriva prima si prende la capienza — e «prima» dev'essere una regola
del dominio (data documento, poi numero), non l'ordine di arrivo dei processi.
📌 Da risolvere dentro `I7`, non nel risolutore, che resta in sola lettura.

### D11 · 📌 **Constatazione** — l'anello «uso della fornitura» esiste già: `config.tipi_utenze`

§2.4 e §2.7.2 lo davano per assente (*«non esiste da nessuna parte»*). **Esiste**:
[config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze) — *«tipo d'uso
(Domestico, Altri usi, Condominio, Pubblico)»* — ha `iva_id` con FK, indice e
`COMMENT ON COLUMN … IS 'Id IVA'`, ed è agganciata alla fornitura via
`vendite.contratti_utilities.tipo_utenza_id`. Non la legge nessuno.

⭐ **E risolve un'apparente contraddizione con `D7`.** Il gas e l'energia a usi
industriali scontano l'aliquota ridotta, e lì sembra che a decidere sia il
*soggetto*. Non è così, e l'incastro è pulito:

* la **classificazione dell'uso** sta sulla **fornitura** — ed è giusto lì: la
  stessa società può avere uno stabilimento industriale e un ufficio;
* la **dichiarazione del cliente** è il **documento che giustifica** quella
  classificazione, e sta fra i titoli di `D10`.

Chi ha creato `tipi_utenze` con dentro un `iva_id` questa cosa l'aveva già vista.

---

## R. Rev 2 — i quattro fatti che il documento dava per veri

> Verificati il 2026-08-28 sulla **doc auto-gen** e sul codice, non sui dati.
> Stanno qui e non sparsi nel testo perché ognuno invalida una richiesta del §5.

### R-1 · ✅ `I1` è **già fatta**, e con una regola **diversa** da quella scritta nel §3

`E_DDT_RIGA_IVA_MANCANTE` è entrato in `script.fn_check_ddt_emittibile` come
**sesto motivo** con i changeSet `20260828-02` e `20260828-03`
(decisione di Tid, R4-ter di
[brief-db-ddt-riconsegna-eredita-testata](../work-done/brief-db-ddt-riconsegna-eredita-testata.md), Fase C).

⛔ **La regola applicata non è quella di `D3`.** Il §3 dice *«se la causale è
fatturabile, ogni riga attiva deve avere un'aliquota»*. L'implementato dice **il
discrimine è il PREZZO, non la causale**, e il controllo sta **fuori** dal ramo
`fatturabile`. La ragione è migliore di quella scritta qui: `vw_ddt_righe_iva_base`
filtra `prezzo_unitario IS NOT NULL` e **non** guarda la causale, quindi anche un
conto visione valorizzato entrava nel riepilogo con imponibile pieno e imposta
zero. *Il vincolo deve avere lo stesso perimetro del consumatore che protegge.*

### R-2 · ⛔ Il primo pgTAP atteso del §6 codificherebbe la regola **sbagliata**

Il §6 chiede: *«causale non fatturabile + riga senza `iva_id` → l'emissione
passa»*. Con la regola di R-1, se quella riga **ha un prezzo** l'emissione **si
ferma**. Il test va riscritto sul prezzo: riga **senza** prezzo e senza `iva_id`
→ passa (è il DDT di solo trasporto); riga **con** prezzo e senza `iva_id` →
blocca, qualunque sia la causale.

### R-3 · 🔴 Lo stesso difetto è aperto su ordini e preventivi — ⚠️ **ma sui preventivi NON è silenzioso**

> ⛔ **Correzione del 2026-08-29, ed è emersa solo provando.** La frase qui sotto
> — *«`vendite.preventivi_riepiloghi_iva` ha la stessa forma»* — è **giusta sulla
> struttura e sbagliata sull'effetto**. Sui preventivi una riga senza aliquota
> **non si riesce nemmeno a salvare**: il trigger `AFTER`
> `trg_preventivi_righe_z90_ricalcola_totali` chiama
> `fn_ricalcola_riepilogo_iva_preventivo`, che chiama
> `config.fn_get_aliquota_iva(NULL, …)` — e quella **solleva** invece di
> ritornare `NULL`. L'`INSERT` fallisce con *«Parametro non valido: p_iva_id
> obbligatorio e > 0»*.
>
> ⚠️ **Il `COALESCE` che sembrava una guardia non lo era**: per proteggere
> avrebbe dovuto ricevere un `NULL`, e il `NULL` non arriva mai perché la
> funzione solleva prima. È un `COALESCE` che *sembra* difendere e non difende.
>
> ⭐ **E non era una decisione di dominio, era una svista**: le viste gemelle la
> guardia ce l'hanno (`vw_ordini_righe_iva_base` scrive
> `CASE WHEN r.iva_id IS NOT NULL THEN config.fn_get_aliquota_iva(…)`), solo
> quella funzione no. Il risultato divergeva da DDT e ordini su tre punti tutti
> contrari a quanto deciso qui: il vincolo scattava **in bozza al salvataggio**,
> il messaggio **nominava un parametro PL/pgSQL** a un operatore, e l'errore
> arrivava da una funzione di catalogo **tre livelli sotto** l'azione.
>
> ✅ Risolto con `20260829-12` (guardia) **insieme a** `20260829-10` (cancello
> all'emissione) — vedi §8-bis. Decisione di Tid, 2026-08-29.
>
> ⚠️ **`fn_ricalcola_riepilogo_iva_fattura` ha lo stesso `COALESCE` senza
> guardia e NON è stata toccata**, ed è una scelta: lì non esiste ancora un
> cancello IVA all'emissione, quindi togliere il raise scambierebbe un errore
> rumoroso con un **numero sbagliato silenzioso** — il contrario di ciò che
> questo cantiere fa. **Va fatto dentro `I4`**, quando la riga di fattura
> ri-risolve l'aliquota.

`vendite.vw_ordini_righe_iva_base` filtra solo `attivo IS TRUE AND quantita > 0` —
**non filtra nemmeno `prezzo_unitario`** — e con `iva_id IS NULL` produce
imponibile pieno e aliquota nulla in `vw_ordini_riepilogo_iva_dettaglio`. Non
esiste nessun `fn_check_ordine_emittibile` (solo `fn_check_ordine_annullabile`), e
`vendite.preventivi_riepiloghi_iva` ha la stessa forma. Il gate è stato messo su
**una delle tre sedi**. → nuova richiesta `I9`.

### R-4 · ⛔ Il §2.4 cita l'ingrediente **rotto** e ignora quello **vivo**

[script.fn_get_iva_override](/dbzero/script/funzioni/fn_get_iva_override) legge
`i.assoggettamento_iva` e `s.assoggettamento_override`: **nessuna delle due
colonne esiste**. Le vive sono `config.iva.assoggettamento_id` e
`config.iva_stati.assoggettamento_id_override`. Non è «esiste già e non la chiama
nessuno»: **è rotta a runtime**, e va riscritta o ritirata.

⭐ Quella viva è [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)`(iva_id, stato_id)`,
già chiamata dentro le `vw_*_righe_iva_base`. ⚠️ È dichiarata **`VOLATILE`** pur
essendo sola lettura, e gira dentro delle viste: va portata a `STABLE`.

---

## 1. Il fatto: due determinazioni, un solo ingrediente

### 1.1 Dove nasce l'IVA di una riga di documento

Nel **frontend**, in `DdtRigaForm.vue` (e nei gemelli ordini/preventivi):

```js
function onArticoloSelect(item) {
  ...
  // Auto-fill IVA dall'articolo (sovrascrivibile prima del save).
  if (item.iva_id != null) form.value.iva_id = item.iva_id
}
```

Il backend l'accetta e basta: `iva_id` è in `_CREATE_KEYS_RIGA` **e** in
`_UPDATE_KEYS_RIGA` (`ddt_service.py`), senza nessuna validazione di merito.

⛔ È logica di dominio fiscale che vive in un componente Vue, contro il *«zero
logica business nel frontend»* di `AGENTS.md`. E il campo è `:disabled="isEdit"`,
cioè la regola «non si cambia dopo» è **una convenzione del solo template**: chi
chiama l'endpoint la scavalca senza accorgersene.

### 1.2 Dove nasce l'IVA di una riga di fattura — e **non** è quella di sopra

La riga di fattura **non legge** l'IVA del documento: la rilegge dall'articolo.
In `pipeline_repository.py`, la proiezione delle attività da raggruppare dice

```sql
art.iva_id
```

e `vendite.attivita_fatturabili` una colonna IVA **non ce l'ha proprio**: il
valore non transita nella catena, viene ri-preso a valle.

⚠️ **Conseguenza pratica, ed è il motivo per cui questo difetto è invisibile**:
oggi i due valori coincidono *per costruzione*, perché la sorgente è la stessa.
Il giorno che una delle due strade impara qualcosa che l'altra non sa, divergono
su documenti già emessi. È esattamente la forma già incontrata e scritta in
`fatture_righe_service.py` per prezzo e sconto delle rettifiche:

> *«Oggi i due valori COINCIDONO per costruzione, ed è precisamente il motivo per
> cui prendere quello dell'attività non darebbe nessun sintomo: si vedrebbe solo
> il giorno in cui divergono, su documenti già emessi.»*

### 1.3 ⭐ Il confronto che rende evidente il buco

| | Prezzo | IVA |
| --- | --- | --- |
| Risolutore | `PricingService` / `fn_resolve_prezzo_listino_v2` | **nessuno** |
| Catena | listino → contratto → promo → override | articolo |
| Dove gira | DB, chiamato dal BE | **frontend**, e di nuovo nel BE a valle |
| Scavalcabile? | no — `feedback_pricing_centralizzato` lo vieta | non c'è niente da scavalcare |
| Modificabile a mano? | sì, ed è **giusto**: un prezzo si negozia, e infatti esiste il workflow di approvazione L1/L2 | — |

⭐ **E qui sta la risposta alla domanda che ha aperto il brief.** Il prezzo è
editabile perché è una **scelta**, e una scelta che scavalca la catena passa da
un'approvazione. L'IVA non è una scelta: è una **conseguenza**, e non si negozia
con nessuno. Quindi il campo resta **bloccato** — ma «bloccato» è corretto solo
se blocca un valore **calcolato**. Oggi blocca ciò che l'articolo ha detto, e per
un cliente fuori regime ordinario blocca un valore **sbagliato** che nessuno può
correggere.

---

## 2. 🔴 La catena che manca

### 2.1 L'errore da non fare: pensare che il reverse charge sia «un'aliquota diversa»

In questo modello un'inversione contabile o un'esenzione **non sono un'aliquota
sovrascritta**: sono un **codice IVA a sé** in `config.iva`, con `aliquota_iva = 0`
più `natura_iva_id` o `assoggettamento_id`. Lo impone il CHECK
`chk_iva_zero_requires_natura_or_assogg`, ed è la ragione per cui
`formatIvaLabel` lato FE può mostrare il codice parlante (`N1`, `ESENTE17`) al
posto di uno `0%` muto.

> Quindi la domanda giusta non è *«l'operatore può cambiare l'aliquota?»* ma
> **«chi sceglie il codice IVA, e l'articolo ha l'ultima parola?»**.

### 2.2 E l'omaggio non è un caso di IVA

`OMAGGIO` è già modellato, e a un altro livello: è una **causale di trasporto**
con `fatturabile = false`. Il manuale delle causali lo dice per esteso — *«i casi
ambigui — l'omaggio, che qualcuno fattura a sconto 100% — si risolvono cambiando
una cella di seed»*. Un documento che dichiara di non vendere non ha bisogno né
di prezzo né di aliquota. **Nessuna richiesta in questo brief lo riguarda**: si
cita perché era nella domanda di partenza e la risposta è «già fatto, altrove».

### 2.3 ⭐ Chi vince: il cliente

Decisione **D2**, con il suo argomento: non si ripete qui per non avere due sedi
della stessa regola che invecchiano separate.

### 2.4 Gli ingredienti

> ⚠️ **La *forma* del risolutore è nel §2.7** (`D6`: due stadi, cascata solo sul
> primo, ritorno a ripartizione). Qui ci sono i soli **ingredienti**, cioè le
> sedi che esistono già e che nessuno legge — la ragione per cui questo brief
> parla di anelli mancanti e non di cose da inventare.
>
> ⭐ **Riscritto in Rev 2** (2026-08-28): la lista di ieri dava per assente un
> anello che esiste (`D11`), per esistente uno che è rotto (`R-4`), e teneva
> `clienti.iva_id` fra gli ingredienti quando invece **si toglie** (`D7-bis`).

* **articolo** — `catalogo.articoli.iva_id`: la proposta ordinaria dello
  **stadio A**. ⚠️ È **nullable**: l'articolo può legittimamente non avere
  un'opinione, e quel caso va gestito;
* **catena del prezzo** — ⭐ e nessuno se n'era accorto: l'aliquota è **già**
  accanto al prezzo a ogni livello — `vendite.listini_righe_componenti.iva_id`,
  `contratti_righe_componenti.iva_id`,
  `offerte_commerciali_eccezioni_componenti.iva_id`. Lo stadio A non è una catena
  da inventare: è una catena **già cablata in colonne e mai letta**;
* **fornitura / uso** — `config.tipi_utenze.iva_id`, agganciata via
  `vendite.contratti_utilities.tipo_utenza_id`. **Esiste** (`D11`), contro quanto
  scriveva la versione di ieri;
* ~~**cliente / soggetto** — `anagrafiche.clienti.iva_id`~~ ⛔ **fuori**: si toglie
  (`D7-bis`). Non è un anello mancante, è una colonna senza lavoro;
* **titolo documentato** — `anagrafiche.soggetti_titoli_iva` (`D10`, §2.6), lo
  **stadio B**: da costruire, con la natura `N3.5` che è già a seed e orfana;
* **stato** — `config.fn_get_aliquota_iva(iva_id, stato_id)` + `config.iva_stati`:
  è la funzione **viva**, già chiamata dalle `vw_*_righe_iva_base`.
  ⛔ **Non** `script.fn_get_iva_override`, che è **rotta**: vedi `R-4`.

⚠️ **`split_payment` e `cliente_pa` NON sono un codice IVA e non entrano nel
risolutore.** La scissione dei pagamenti non cambia l'aliquota: cambia **chi versa
l'imposta all'erario**, e in fattura elettronica è l'`EsigibilitaIVA`, non una
natura. Sono un secondo esito, che viaggia sulla testata della fattura e nel
payload SDI. Confonderli farebbe nascere codici IVA fasulli.

### 2.5 ⚠️ Due avvertenze per chi scriverà

1. **La sede del risolutore è UNA.** Se il DB lo espone e il BE lo chiama ma il
   frontend continua a fare il suo `onArticoloSelect`, ci saranno *due* risposte
   diverse alla stessa domanda — cioè il difetto di oggi con un pezzo in più.
   L'auto-fill nel form va **sostituito** da una chiamata al risolutore, non
   affiancato.
2. **Cambia il comportamento delle fatture esistenti**, perché la riga di fattura
   smette di leggere `art.iva_id`. È un breaking change dichiarato, e in questo
   progetto è ammesso (`project_no_produzione_solo_sviluppo`) — ma va **detto**,
   non scoperto.

### 2.6 🔴 La dichiarazione d'intento — ~~`anagrafiche.soggetti_intento`~~ → **`anagrafiche.soggetti_titoli_iva`**

> ⭐ **Rev 2, 2026-08-28 — il nome e la forma cambiano: leggere `D10` prima di
> questo paragrafo.** La dichiarazione d'intento **non è un caso unico**: è il
> primo di una famiglia di **almeno quattro** titoli (intento, uso
> industriale/agricolo gas-EE, agevolata disabili L.104, cooperative sociali e
> ONLUS). Il plafond, che qui sotto è la colonna portante, è la **proprietà di un
> tipo** — solo l'intento ce l'ha.
>
> **Resta valido tutto il merito**: le sei domande di `P1`…`P5` + sede, il
> registro dei movimenti di `D5`, il fatto che la fattura ri-risolve e non
> trasporta. **Cambiano** il nome, la chiave (entra l'**emittente destinatario**,
> `D10-bis`), l'**ambito** (che arriva fino al singolo articolo) e la forma del
> guard di non sovrapposizione (§2.6.4).

Richiesta di Tid, 2026-08-27: *«serve una tabella specifica dove si salvano le
informazioni della dichiarazione d'intento con data inizio e fine validità e il
plafond; se i valori sono validi si "sovrascrive" il codice IVA con quello del
plafond, per il tetto valido»*. **Nome deciso: `anagrafiche.soggetti_intento`.**

#### 2.6.1 Cosa c'è oggi

* ⛔ **Nessuna tabella**: `dichiarazioni_intento`, `plafond` o equivalenti non
  esistono in nessuno schema;
* ✅ **`config.iva_natura` ha già `N3.5`** (id 8) — *«non imponibili - a seguito di
  dichiarazioni d'intento»*, seminata dal 2025;
* ⛔ **e nessun `config.iva` la usa**: dei 14 codici a seed, **zero** hanno
  `natura_iva_id = 8`. La natura è **orfana**.

⭐ Qualcuno, tempo fa, ha seminato la natura giusta. Manca tutto il resto — il
codice IVA che la porta, la tabella che dice quando si applica, il risolutore che
la sceglie. È il segno che la direzione era già stata vista, non che il caso sia
nuovo.

#### 2.6.2 ✅ Le decisioni di Tid (2026-08-27)

Un plafond non è un predicato come una finestra di validità: è un
**accumulatore**, e ogni fattura ne mangia un pezzo. Le domande che ne discendono
sono state poste e **risolte tutte**.

| # | Domanda | ✅ Decisione |
| --- | --- | --- |
| **P1** | Quando si consuma: fattura o DDT? | **La fattura, assolutamente.** Il DDT *simula e applica*, ma in fattura **va rifatto**. Vale per **tutti** i documenti a monte |
| **P2** | Documento che supera il residuo | **Si spezza**: non imponibile fino a capienza, il resto ad aliquota ordinaria |
| **P3** | Residuo calcolato o memorizzato | **Memorizzato** — ed è un nodo voluto: serve a poterlo **ridurre manualmente** (forzatura) quando esistono fatturazioni fuori dal sistema. ✅ Realizzato col registro di `D5` |
| **P4** | La nota di credito restituisce plafond? | **Sì.** ⭐ E si memorizza l'**imponibile già applicato**, non il residuo: è verificabile direttamente, e il residuo è aritmetica (`plafond − imponibile`). ✅ Realizzato col registro di `D5` |
| **P5** | Il protocollo arriva in fattura e nell'XML? | **Sì, anche in XML** |
| **sede** | A chi appartiene | **Al soggetto, senza dubbio** |

##### ⭐ P1 è un principio, non un dettaglio: **il documento a monte proietta, la fattura decide**

*«Il documento fiscale è legge; il DDT simula e applica, ma poi nella fattura va
rifatto.»* Ha due conseguenze che vanno scritte perché cambiano il codice:

1. **L'IVA di una riga di DDT/ordine/preventivo è una proiezione, non un fatto.**
   Serve a far vedere all'operatore che cosa verrà applicato, e al riepilogo IVA
   del documento. Non è il valore che finirà in fattura;
2. ⛔ **quindi il valore NON si trasporta a valle**: l'alternativa che avevo messo
   in `I4` — *«o l'IVA entra nella catena `attivita_fatturabili` e viaggia»* — è
   **esclusa per decisione**. La fattura ri-risolve. Oggi in effetti *ri-fa* già
   (rilegge `art.iva_id`), solo che ri-fa **con l'ingrediente sbagliato**: il
   difetto non è che ricalcoli, è **che cosa** legge per ricalcolare.

##### ⚠️ P3 + P4: quello che memorizzo è un accumulatore, e un accumulatore forzabile ha bisogno di un registro

Le due risposte insieme dicono una cosa precisa: la colonna da tenere è
**`imponibile_utilizzato`**, non `residuo`. Giusto, ed è la scelta più
verificabile — quel numero si confronta con la somma degli imponibili fatturati,
mentre un residuo si confronta con niente.

⛔ **Ma un numero memorizzato *e* forzabile a mano diverge in silenzio da ciò che
dovrebbe rappresentare**, ed è la forma esatta di `feedback_duplicazione_nasconde_il_bug`:
due sorgenti della stessa verità, e nessuna delle due sa di essere sbagliata.
Su un plafond il costo non è un numero storto in una lista — è il dato che
l'Agenzia delle Entrate **verifica**.

⭐ **✅ APPROVATA da Tid il 2026-08-27** (`D5`): non una colonna che si
sovrascrive, ma un **registro di movimenti** —
`anagrafiche.soggetti_intento_movimenti`:

| Movimento | Segno | Da dove |
| --- | --- | --- |
| fattura emessa sotto la dichiarazione | `+` | riga di fattura |
| nota di credito | `−` | riga di rettifica (**P4**) |
| **forzatura manuale** | `±` | operatore, con **motivo obbligatorio** |

`imponibile_utilizzato` resta la colonna memorizzata che **P3** chiede — ma è la
somma del registro, non un numero scritto sopra a un altro. Si guadagnano tre
cose che la colonna nuda non dà: la forzatura ha un **motivo, un autore e una
data**; il consumo è **algebrico** senza casi speciali per la NC; e la riconcilia-
zione col fatturato è una query, non un'indagine.

⚠️ È lo stesso schema che il progetto usa già in due punti: il ponte
`resi_righe_riconsegne` e le rettifiche di `vw_partite_merce`, dove *«il fatturato
somma anche le RETTIFICHE, negative o zero»*. Non è un pattern nuovo da inventare.

#### 2.6.3 ✅ La sede: il soggetto — e il rilievo che ne discende

Deciso: **appartiene al soggetto**. Che è anche l'unica risposta che regge sul
modello — la dichiarazione è della **partita IVA**, e un esportatore abituale con
tre forniture ha **una** dichiarazione, non tre.

⛔ Il motivo per cui la domanda andava posta: `anagrafiche.clienti` è **una riga
per istanza di utenza** (`UNIQUE uq_clienti_istanza_utility`). Agganciarci la
dichiarazione l'avrebbe moltiplicata per il numero di forniture, e tre copie
hanno **tre plafond che si consumano separatamente**: il tetto sarebbe diventato
il triplo di quello vero, in silenzio.

⚠️ **E lo stesso rilievo investe `clienti.iva_id`, cioè la catena di `D2`.** Se il
regime fiscale è del soggetto — e la decisione appena presa dice di sì — allora
una colonna di regime su una riga per istanza è nella sede sbagliata: due istanze
dello stesso soggetto possono oggi dichiarare regimi diversi e niente lo impedisce.
Un'**aliquota** diversa per utility è legittima (la porta l'articolo); un
**regime** diverso per fornitura dello stesso soggetto no.

> **Resta al team DB** una sola domanda, e decide se `I2` tocca anche `clienti`:
> `clienti.iva_id` è nato per essere *«il regime fiscale del cliente»* o
> *«l'aliquota di default di questa fornitura»*? Il modello concettuale la mette
> accanto a `cliente_pa` e `split_payment` e scrive `iva ||--o{ clienti : vat_of`,
> il che suggerisce la prima — e allora è una **migrazione** verso
> `soggetti_ruoli`, non solo una lettura in più.

#### 2.6.4 La forma proposta della tabella

Da leggere come **punto di partenza**, non come DDL: la sede delle definizioni è
il team DB.

* `anagrafiche.soggetti_intento` — soggetto (o `soggetto_ruolo_id`, secondo la
  risposta del §2.6.3), **protocollo** e **data di ricezione** dell'Agenzia
  (**P5**: viaggiano fino all'XML), `validita` come **`daterange`** — la
  convenzione del progetto dal 2026-04, non due colonne date sciolte —
  `plafond` (imponibile massimo), `iva_id` del codice non imponibile da applicare,
  `imponibile_utilizzato` (**P3/P4**), `attivo`, audit `data_*`/`user_*`, `tx_id`;
* `anagrafiche.soggetti_intento_movimenti` — il registro del §2.6.2;
* **un codice `config.iva` nuovo** con `natura_iva_id = 8`, che oggi non esiste:
  senza, la natura resta orfana e il risolutore non ha niente da restituire;
* ⚠️ **guard di non sovrapposizione**: due dichiarazioni valide contemporaneamente
  sullo stesso soggetto rendono la scelta del risolutore ambigua — e
  un'ambiguità che dipende dall'ordine degli id è precisamente ciò che
  `AGENTS.md` chiama *«un'ambiguità del modello, non una scelta»*. `daterange` +
  `EXCLUDE USING gist` la chiude a livello di vincolo.

#### 2.6.5 Effetto su `D1`, e il punto che Tid ha aggiunto

Era proprio la dichiarazione d'intento il caso che sembrava non copribile dal
risolutore. Modellata così, ci rientra: il titolo non è più qualcosa che
l'operatore *digita sulla riga*, è qualcosa che **si registra una volta** — con
protocollo, validità e tetto — e che il risolutore legge. Che è anche il posto
giusto: un titolo di non imponibilità è un **fatto documentato**, non una scelta
di riga.

⭐ E Tid ci ha messo sopra la ragione generale: *«avere un risolutore ci permette
di gestire anche altre eccezioni in un unico punto»*. È il criterio con cui
guardare le prossime — ogni titolo che oggi non ha una sede si registra, non si
digita.

~~⚠️ **`D1` resta formalmente aperta** solo per la verifica che non ci siano
**altri** titoli per-operazione fuori dal risolutore.~~ ✅ **Verifica fatta con
`D10` (2026-08-28) e `D1` chiusa il 2026-08-29**: i titoli sono quattro, hanno
tutti una sede, e nessuno si digita sulla riga.

### 2.7 ⭐ La forma del risolutore: due stadi, una cascata, una ripartizione

Origine: domanda di Tid del 2026-08-27 — *«il regime è anche sotto utility: fra
gas, EE e acqua i regimi possono essere diversi… potremmo gestire la cascata con
un fallback, come accade con gli indirizzi. L'unico problema è che il soggetto
vincerebbe in presenza di dichiarazione d'intento mentre vincerebbe il BA se non
presente… brutto vero?»*.

**È brutto**, e lo è perché la parola «regime» tiene insieme **due meccanismi**.
Separati, la precedenza che si inverte sparisce.

#### 2.7.1 Due domande, non due livelli della stessa domanda

| | Domanda | Da cosa dipende | Esempio |
| --- | --- | --- | --- |
| **A · aliquota ordinaria** | *quale aliquota compete a questa merce?* | dalla **cosa venduta** — e quindi legittimamente dall'utility e dalla fornitura | EE al 10%; gas «uso domestico» vs «altri usi» |
| **B · titolo di non imponibilità** | *questa controparte, oggi, ha un titolo che **sostituisce** l'aliquota?* | dalla **partita IVA** | dichiarazione d'intento, inversione contabile, art. 8 |

⭐ **L'EE al 10% non è un regime del soggetto: è l'aliquota dell'energia
elettrica, uguale per tutti i clienti.** Varia per utility perché varia **la
merce**, non perché vari il cliente. È chiamarla «regime» che faceva sembrare che
i due livelli si contendessero qualcosa.

⛔ **Quindi non c'è nessuna inversione**: A e B non competono, perché non
rispondono alla stessa domanda. B non «vince su» A in una cascata — B
**sostituisce il risultato di A**, dopo che A ha risposto.

```
Stadio A   quale aliquota ordinaria?          articolo → … → fornitura   [più specifico vince]
Stadio B   c'è un titolo che la sostituisce?  soggetto                   [se sì, rimpiazza]
```

Nessun livello compare in tutti e due: il soggetto non entra mai in A, la
fornitura non entra mai in B. Non c'è niente da invertire.

#### 2.7.2 La cascata serve — ed è dello **stadio A**

Il livello fornitura in A non è un ripiego: per le utility l'aliquota dipende
spesso dall'**uso della fornitura** (gas uso domestico vs altri usi), che è una
proprietà della fornitura — non dell'articolo, e men che meno del soggetto.

⚠️ **Se si riusa il vocabolario della cascata degli indirizzi, si riusa intero**:
nel progetto è a **tre** livelli — `FONTE_ORDER = { soggetto: 0, ruolo: 1, istanza: 2 }`
in `core/utils/string.js`, con `sortByFonte` che li ordina. Una versione a due
gradini nata qui sarebbe un secondo vocabolario che qualcuno dovrà riallineare.

#### 2.7.3 ⭐ Il risolutore non ritorna un codice IVA: ritorna una **ripartizione**

Firma: una lista di `(quota imponibile, codice IVA)`, con **un solo elemento** nel
caso ordinario.

**La ragione è `P2`, e da sola basta**: plafond esaurito a metà riga → parte non
imponibile fino a capienza, il resto ad aliquota ordinaria. Una funzione che
ritorna *un* codice non sa esprimere quella risposta, e chi la chiama dovrebbe
ricostruire la spezzatura per conto suo — cioè la regola tornerebbe fuori dal
risolutore proprio nel caso per cui il risolutore esiste.

⚠️ **È una decisione da prendere adesso perché è la *firma*.** Cambiarla dopo
significa toccare ogni chiamante.

#### 2.7.4 ⛔ Fuori perimetro, dichiarato: gli scaglioni del gas

Uno scaglione di consumo è **un tetto che spezza una riga**: la stessa forma di
`P2`. La ripartizione del §2.7.3 lo accoglierebbe senza costo.

**Decisione di Tid, 2026-08-27: NON si fa adesso.** Resta scritto qui come
memoria, non come lavoro.

⭐ **E la ragione per cui è giusto tenerlo fuori sta nella regola zero, non nella
fretta**: gli scaglioni **non sono modellati** — cercato il 2026-08-27, «scaglioni»
compare nel repository solo come concetto di *prezzo* nella prosa di
`contratti_righe` e `listini_versioni`, mai come banda di aliquota. Progettare su
di loro sarebbe progettare su una previsione dei dati, che è precisamente ciò che
`AGENTS.md` vieta.

⚠️ **Prova del nove, ed è il motivo per cui il §2.7.3 resta in piedi**: togliendo
gli scaglioni dall'argomento, la ripartizione serve **lo stesso** — la pretende
`P2`, che è già decisa. Gli scaglioni sono un di più che quella forma accoglie,
non la ragione per cui la si sceglie. Se l'argomento fosse stato *«serve la
ripartizione perché un giorno faremo gli scaglioni»*, andava rifiutato.

#### 2.7.5 ❓ Aperto: lo stadio B è probabilmente una **famiglia**, non una colonna

L'ho descritto come «del soggetto», ma non tutti i titoli lo sono davvero: il
**reverse charge edile** dipende dal *tipo di operazione*, non dalla controparte;
la **dichiarazione d'intento** è già un documento con protocollo, validità e
tetto, non un flag.

Il che suggerisce che B non sia una colonna sul soggetto ma un insieme di
**qualificazioni**, ognuna con il proprio ambito e la propria prova documentale.

> ⭐ Se è così, `anagrafiche.soggetti_intento` è **la prima di una famiglia**, e
> conviene che nasca sapendolo — allargare dopo una tabella nata come caso unico
> è il modo in cui si ottengono due meccanismi per la stessa cosa. Non serve
> costruire la famiglia adesso: serve non chiudere la porta.


---

## ~~3. 🟠 Il gate all'emissione: chiede il prezzo, non l'aliquota~~ — ✅ **CHIUSA il 2026-08-28**

> ✅ **Fatta e applicata**, ma **non come scritto qui**: la regola entrata guarda
> il **prezzo** e non la **causale**, ed è migliore. Dettaglio e conseguenze in
> **`R-1`**; il pgTAP che il §6 chiede va riscritto (**`R-2`**).
> Il testo sotto resta per storia — è l'inquadramento da cui è partita la voce.

### ~~Testo originale (2026-08-27)~~

`vendite.trgfn_ddt_guard_causale_emissione` (che delega la valutazione a
`script.fn_check_ddt_emittibile`, single source con la capability) oggi verifica:

1. la causale di trasporto è dichiarata;
2. se la causale è **fatturabile**, ogni riga attiva ha un **prezzo risolvibile**.

⭐ **Manca il terzo, ed è simmetrico al secondo**: se la causale è fatturabile,
ogni riga attiva deve avere anche un'**aliquota**. Rilievo di Tid, 2026-08-27:
*«l'IVA deve esserci sempre, se non indicata deve andare in errore — forse solo
se il prezzo è null, IVA null»*. È esattamente la stessa condizione: **dove serve
il prezzo serve l'IVA**, e a dichiararlo è la stessa causale.

### 3.1 Perché **non** una `NOT NULL` sulla colonna

`vendite.ddt_righe.iva_id` è nullable, e deve restarlo: un DDT di **solo
trasporto** (conto visione, campionatura, trasferimento, omaggio) non vende, e
un'aliquota lì è un dato che non si applica — la stessa ragione per cui il prezzo
non è `NOT NULL`. Una `NOT NULL` spegnerebbe i documenti legittimi per prendere
quelli difettosi.

### 3.2 La sede

Dentro `script.fn_check_ddt_emittibile`, accanto a `E_DDT_PREZZO_NON_RISOLVIBILE`.
Da lì raggiunge **da sé** i tre consumatori — il trigger che solleva,
`fn_available_actions_ddt` che spegne il pulsante, e il motivo che il frontend
mostra — senza che nessuno dei tre vada toccato. Serve un codice nuovo a
catalogo, con la sua classe (`DATO_ERRATO`, 400: il dato lo fornisce una persona)
e il ripiego senza `%s` (`feedback_ripiego_ogni_codice_vivo`).

---

## 4. 🔴 I campi scritti e mai letti

`anagrafiche.clienti` porta il regime fiscale della controparte:

| Colonna | Nullable | Chi la scrive | Chi la legge | ⭐ Rev 2: destino |
| --- | --- | --- | --- | --- |
| `iva_id` | **`NO`** | `fn_update_cliente` + `ClienteDrawer.vue` (con default da `DEFAULT_IVA_ID`) | ⚠️ **quasi nessuno** — la legge `BillingAccountRepository.get_cliente_defaults` e la espone `/vendite/preventivi/form-defaults/`; è il FE a scartarla (`D7-bis`) | ⛔ **si toglie** (`D7-bis`) |
| `split_payment` | `NO`, default `'N'` | `ClienteDrawer.vue` | ⛔ **nessuno** — non è né su `vendite.fatture` né in `fn_prepare_sdi_payload` | ⬆️ **sale su `soggetti`** (`D8`) |
| `cliente_pa` | `NO`, default `'N'` | `ClienteDrawer.vue` | ⛔ **nessuno** | ⬆️ **sale su `soggetti`** (`D8`) |
| `codice_cig` | `SI` | `ClienteDrawer.vue` | ⛔ **nessuno** — non esistono in nessun'altra tabella | ➡️ **al contratto** (`D9`) |
| `codice_cup` | `SI` | `ClienteDrawer.vue` | ⛔ **nessuno** | ➡️ **al contratto** (`D9`) |
| `codice_commessa` | `SI` | `ClienteDrawer.vue` | ⛔ **nessuno** | ➡️ **al contratto** (`D9`) |

⭐ **Le sei colonne non erano un gruppo solo, ed è la scoperta della Rev 2.**
Erano tutte lì per la stessa ragione — Tid le aveva messe su `clienti` perché
*«potevano essere diverse in base alla utility»*, e `clienti` era l'unica tabella
per fornitura disponibile. Ma rispondono a **tre domande con tre padroni
diversi**: `iva_id` alla merce e al suo uso, `split_payment`/`cliente_pa` alla
partita IVA, i tre codici al **contratto**.

Il modello concettuale della tabella li dichiara: *«classificazioni speciali (PA,
split payment)»*, e il diagramma scrive `iva ||--o{ clienti : vat_of`.

⛔ **Non è un campo dimenticato: è un campo che l'operatore compila.** C'è il
drawer, c'è perfino il parametro di sistema per il default. Chi imposta un cliente
in reverse charge ha tutto il diritto di credere di aver deciso qualcosa, e in
fattura ritrova l'aliquota dell'articolo. È peggio di un campo assente, perché un
campo assente non mente.

⚠️ **O entrano nella catena (voce 2), o si dichiarano non usati.** Quello che non
va fatto è lasciarli così: la terza via — «li sistemiamo quando serviranno» — è il
modo in cui questo difetto è arrivato fin qui.

---

## 5. La richiesta, in ordine

> ⭐ **Tabella riscritta in Rev 2** (2026-08-28). `I1` è chiusa; `I7` sale a
> **prerequisito di `I2`**; entrano `I8` (CIG/CUP/commessa) e `I9` (il gate
> mancante su ordini e preventivi).

| # | Cosa | A chi | Stato |
| --- | --- | --- | --- |
| ~~**I1**~~ | ~~Gate IVA all'emissione dentro `script.fn_check_ddt_emittibile`~~ | DB | ✅ **FATTA** 2026-08-28, con regola diversa e migliore (`R-1`) |
| **I0** | ⭐ **Nuova, ed è il passo che sblocca gli altri**: `DROP` di `anagrafiche.clienti.iva_id` (`D7-bis`) + salita di `split_payment`/`cliente_pa` su `anagrafiche.soggetti` (`D8`). Si porta dietro `fn_update_cliente`, la whitelist BE e il `ClienteDrawer.vue` | DB + BE + FE | ✅ **APPLICATA** — metà additiva e metà che toglie, entrambe |
| **I7** | **`anagrafiche.soggetti_titoli_iva`** (`D10`) — famiglia con vocabolario dei tipi, **emittente destinatario** in chiave (`D10-bis`), ambito fino al **singolo articolo**, `validita` `daterange`, registro movimenti (`D5`) e plafond **solo per i tipi che ce l'hanno**; + codice `config.iva` con `natura_iva_id = 8` (oggi la natura è **orfana**); + `EXCLUDE` anti-sovrapposizione sulla chiave nuova. ✅ Le sei domande di §2.6.2 restano decise | DB + BE | ✅ **APPLICATA** 2026-08-29 — §8-ter. Lo stadio B ha la sua sorgente: `I2` è sbloccata |
| **I2** | Risolutore IVA a **due stadi** (§2.7, `D6`+`D7`): A = aliquota ordinaria, cascata `articolo → catena prezzo → tipo utenza`; B = **titolo documentato** dal soggetto, che sostituisce A. ⭐ **Ritorna una ripartizione** `(quota, codice IVA)`, non un codice (§2.7.3). Sul modello di `fn_resolve_prezzo_listino_v2` | DB | ✅ **APPLICATA** 2026-08-29 — §8-quinquies, con 15 casi pgTAP |
| **I3** | Il BE chiama `I2` alla creazione della riga; il FE **smette** di fare l'auto-fill e mostra il risultato del risolutore (§2.5.1) | BE + FE | 🟢 **sbloccata**: `I2` c'è. ⛔ Interamente BE+FE, niente da fare lato DB |
| **I4** | La riga di fattura smette di rileggere `art.iva_id` e **ri-risolve** via `I2`. ⛔ L'alternativa «l'IVA viaggia nella catena `attivita_fatturabili`» è **esclusa da P1**: la fattura rifà, non trasporta. ⚠️ **Breaking change dichiarato** (§2.5.2) | ~~DB + BE~~ → **solo BE** | 🟢 **sbloccata**: `I2` c'è. ⛔ Verificato che **nessuna funzione DB inserisce in `vendite.fatture_righe`** — le costruisce `pipeline_repository.py`, quindi la metà DB non esiste |
| **I5** | `split_payment` / `cliente_pa` → riga e riepilogo fattura + payload SDI (`EsigibilitaIVA`), **fuori** dal risolutore (`D4`). ⭐ **Voce corta**: `fatture_righe` e `fatture_riepiloghi_iva` hanno **già** le colonne e il raggruppamento — manca solo chi le riempie (`D8`) | DB + BE | ✅ **metà DB APPLICATA** 2026-08-30 — le riempie il trigger dal soggetto cliente (§8-quinquies, voce `I5`). Resta il payload SDI, che è BE |
| **I8** | ⭐ **Nuova, e non è IVA**: `codice_cig` / `codice_cup` / `codice_commessa` da `clienti` a **`vendite.contratti`**, + **snapshot** sulla fattura all'emissione (`D9`). ⚠️ `vendite.fatture` non ha nessun link al contratto: senza snapshot non arrivano mai | DB + BE + FE | 🟢 **da fare adesso**: ✅ **APPLICATA** (metà additiva + metà che toglie) |
| **I9** | ⭐ **Nuova**: il gate «riga con prezzo senza aliquota» esiste **solo sul DDT**. `vw_ordini_righe_iva_base` non filtra nemmeno `prezzo_unitario`, e per ordini e preventivi non c'è nessun `fn_check_*_emittibile` (`R-3`) | DB | ✅ **APPLICATA**, entrambe le metà |
| **I10** | ⭐ **Nuova** (`D15`): `config.stati_doc_fiscale.congela_fiscale` — colonna nuova + seed **dal CSV** su tutte le righe, e `vendite.fn_ricalcola_riepilogo_iva_fattura` portata a leggerla al posto della lista `NOT IN ('DRAFT','EMESSA')`. È la **soglia unica** cui dovrà obbedire anche il risolutore | DB | ✅ **APPLICATA** 2026-08-29 — ed è servita: è il guard che ha smascherato il difetto di `D30` |
| **I0** | ⭐ **Nuova, ed è il passo che sblocca gli altri**: `DROP` di `anagrafiche.clienti.iva_id` (`D7-bis`) + salita di `split_payment`/`cliente_pa` su `anagrafiche.soggetti` (`D8`). Si porta dietro `fn_update_cliente`, la whitelist BE e il `ClienteDrawer.vue` | DB + BE + FE | ✅ **CHIUSA 2026-08-29**: DB applicato; BE/FE nel [piano Fase 1](brief-be-fe-iva-risolutore-e-regime-cliente.md) (`S1` + `S2`) |
| **I7** | **`anagrafiche.soggetti_titoli_iva`** (`D10`) — famiglia con vocabolario dei tipi, **emittente destinatario** in chiave (`D10-bis`), ambito fino al **singolo articolo**, `validita` `daterange`, registro movimenti (`D5`) e plafond **solo per i tipi che ce l'hanno**; + codice `config.iva` con `natura_iva_id = 8` (oggi la natura è **orfana**); + `EXCLUDE` anti-sovrapposizione sulla chiave nuova. ✅ Le sei domande di §2.6.2 restano decise | DB + BE | ⛔ **prerequisito di `I2`**: senza, lo stadio B non ha nessuna sorgente |
| **I2** | Risolutore IVA a **due stadi** (§2.7, `D6`+`D7`): A = aliquota ordinaria, cascata `articolo → catena prezzo → tipo utenza`; B = **titolo documentato** dal soggetto, che sostituisce A. ⭐ **Ritorna una ripartizione** `(quota, codice IVA)`, non un codice (§2.7.3). Sul modello di `fn_resolve_prezzo_listino_v2` | DB | dopo `I7` |
| **I3** | Il BE chiama `I2` alla creazione della riga; il FE **smette** di fare l'auto-fill e mostra il risultato del risolutore (§2.5.1) | BE + FE | dopo `I2` |
| **I4** | La riga di fattura smette di rileggere `art.iva_id` e **ri-risolve** via `I2`. ⛔ L'alternativa «l'IVA viaggia nella catena `attivita_fatturabili`» è **esclusa da P1**: la fattura rifà, non trasporta. ⚠️ **Breaking change dichiarato** (§2.5.2) | DB + BE | dopo `I2` |
| **I5** | `split_payment` / `cliente_pa` → riga e riepilogo fattura + payload SDI (`EsigibilitaIVA`), **fuori** dal risolutore (`D4`). ⭐ **Voce corta**: `fatture_righe` e `fatture_riepiloghi_iva` hanno **già** le colonne e il raggruppamento — manca solo chi le riempie (`D8`) | DB + BE | dopo `I0` |
| **I8** | ⭐ **Nuova, e non è IVA**: `codice_cig` / `codice_cup` / `codice_commessa` da `clienti` a **`vendite.contratti`**, + **snapshot** sulla fattura all'emissione (`D9`). ⚠️ `vendite.fatture` non ha nessun link al contratto: senza snapshot non arrivano mai | DB + BE + FE | 🟡 **quasi chiusa**: DB e PATCH fatti ([piano](brief-be-fe-iva-risolutore-e-regime-cliente.md) `S1` + `S3-a`); resta la **CREATE**, gated su [brief-db-fn-create-contratto-codici-atto.md](../work-done/brief-db-fn-create-contratto-codici-atto.md) |
| **I9** | ⭐ **Nuova**: il gate «riga con prezzo senza aliquota» esiste **solo sul DDT**. `vw_ordini_righe_iva_base` non filtra nemmeno `prezzo_unitario`, e per ordini e preventivi non c'è nessun `fn_check_*_emittibile` (`R-3`) | DB | ✅ **CHIUSA 2026-08-29**: ordini e preventivi applicati; le due `reason_key` i18n mancanti aggiunte dal [piano Fase 1](brief-be-fe-iva-risolutore-e-regime-cliente.md) (`S4`) |
| **I10** | ⭐ **Nuova** (`D15`): `config.stati_doc_fiscale.congela_fiscale` — colonna nuova + seed **dal CSV** su tutte le righe, e `vendite.fn_ricalcola_riepilogo_iva_fattura` portata a leggerla al posto della lista `NOT IN ('DRAFT','EMESSA')`. È la **soglia unica** cui dovrà obbedire anche il risolutore | DB | ✅ **APPLICATA** 2026-08-29 — §8-bis. Nessun consumatore BE/FE da adeguare |
| **I6** | ✅ **Sbloccata da `D1` (2026-08-29)**: l'IVA di riga non si digita. **Due metà, servono entrambe** — (a) BE: `iva_id` **fuori** da `_UPDATE_KEYS_RIGA` **e** da `_CREATE_KEYS_RIGA` in `ddt_service`, `ordini_service`, `preventivi_service` (in `preventivi_service` è una tupla inline, non una `frozenset`); (b) FE: `<IvaSelect>` disabilitata **anche in CREATE** nei tre `*RigaForm.vue`, e il campo mostra il risultato del risolutore. ⚠️ In `PreventiviRigaForm` il `canSave` pretende `f.iva_id`: va ripensato, o la creazione si blocca da sola | BE + FE | ⛔ **per ultima** |

⛔ **L'ordine fra I6 e le altre non è indifferente, ed è l'unico modo di sbagliare
in silenzio.** `I6` toglie all'operatore l'ultima uscita manuale: applicata
**prima** di I2/I3 — cioè prima che le righe nascano con l'aliquota giusta —
cementerebbe i buchi e i valori sbagliati che oggi si possono ancora correggere
via API. `I6` va **per ultima**.

⚠️ **Ora che `D1` è decisa, quel vincolo è più fragile, non meno**: la decisione
c'è, quindi `I6` sembra «pronta» e la si può fare in mezz'ora. È proprio per
questo che va scritto — *una voce sbloccata non è una voce da anticipare*. Finché
`I2`/`I3` non girano, chiudere la casella significa congelare i valori di oggi
senza lasciare a nessuno il modo di correggerli.

⭐ **La dipendenza nuova della Rev 2, e va nel verso non ovvio**: `I7` **non** è
una voce parallela a `I2`, è il suo **prerequisito**. Finché i titoli non hanno
una sede, lo stadio B non ha niente da leggere — e con `clienti.iva_id` tolta da
`I0`, un risolutore scritto prima di `I7` sarebbe uno **stadio A soltanto**, cioè
il comportamento di oggi con più codice intorno.

⚠️ **`I0`, `I8`, `I9` e `I10` sono indipendenti fra loro e da tutto il resto**, e
conviene farle subito: sono quelle che oggi costano meno e che dopo costeranno di
più — `I0` perché non ha consumatori veri, `I8` perché il builder FatturaPA non
esiste ancora, `I9` perché è la stessa regola già scritta e collaudata sul DDT,
`I10` perché finché la soglia è un hardcode il risolutore la **ricopierà**, e
allora gli hardcode diventano due.

### Il processo di sviluppo, in quattro fasi

> Aggiornato il 2026-08-29, con `D1` decisa. Le fasi sono **sequenziali fra
> loro**; dentro una fase le voci sono indipendenti e si possono fare in
> parallelo. Ogni fase si chiude con i suoi pgTAP, non alla fine di tutto.

```text
FASE 1 — sgombero          I0 · I8 · I9 · I10      ✅ FATTA e APPLICATA  29/08
FASE 2 — le sedi           I7                      ✅ FATTA e APPLICATA  29/08
FASE 3 — il risolutore     I2 · I5(DB)             ✅ FATTE e APPLICATE  29-30/08
                           I3 · I4                 🟢 sbloccate, ma sono BE/FE
FASE 4 — la chiusura       I6                      ⛔ dopo I3/I4, ed e' BE+FE
```

**FASE 1 — sgombero.** Sono le quattro voci che non dipendono da niente e che
oggi costano meno di quanto costeranno dopo: `I0` perché quelle colonne non hanno
consumatori veri, `I8` perché il builder XML FatturaPA non è ancora scritto, `I9`
perché è la stessa regola già collaudata sul DDT, `I10` perché finché la soglia di
congelamento è un hardcode il risolutore la **ricopierà**. ⭐ Si può cominciare
oggi, e nessuna delle quattro ha bisogno che il disegno del risolutore sia
finito.

**FASE 2 — le sedi.** `I7` costruisce `anagrafiche.soggetti_titoli_iva`, il
vocabolario dei tipi, l'ambito, il registro dei movimenti, il lock e il codice
`config.iva` con `natura_iva_id = 8`. ⛔ **È il prerequisito di `I2`, non una
voce parallela**: senza titoli lo stadio B non ha sorgenti, e un risolutore
scritto prima sarebbe uno stadio A soltanto — cioè il comportamento di oggi con
più codice intorno.

**FASE 3 — il risolutore.** `I2` è la funzione (firma da `D14`: articolo, data di
riferimento, sola lettura, ritorna una ripartizione). Poi, in parallelo, i tre
consumatori: `I3` la riga di documento, `I4` la riga di fattura, `I5` esigibilità
e split. ⚠️ `I4` è un **breaking change dichiarato** — le fatture smettono di
rileggere `art.iva_id`.

**FASE 4 — la chiusura.** `I6` toglie all'operatore la casella. Ha senso **solo**
quando le righe nascono già con l'aliquota giusta, cioè a valle della Fase 3.

⭐ **Il pgTAP che chiude il cantiere** è quello del §6 sull'unione delle due
determinazioni: la stessa riga letta come documento e come attività di
fatturazione deve dare lo **stesso** `iva_id`. Finché restano due strade, è
l'unico test che si accorge quando divergono.

---

## 6. Presidi attesi

* ~~**pgTAP su I1**: causale fatturabile + riga senza `iva_id` → l'emissione
  solleva il codice nuovo; causale **non** fatturabile + riga senza `iva_id` →
  l'emissione **passa**~~ ⛔ **SBAGLIATO, vedi `R-2`**: il discrimine è il
  **prezzo**, non la causale. La forma giusta è — riga **senza** prezzo e senza
  `iva_id` → **passa** (è il DDT di solo trasporto, e senza questo test la voce
  diventa una `NOT NULL` mascherata); riga **con** prezzo e senza `iva_id` →
  **blocca**, qualunque sia la causale;
* **pgTAP su I2**, e va **costruito**, non cercato: soggetto con un **titolo**
  valido diverso dall'aliquota dell'articolo → il risolutore ritorna **quello del
  titolo**; stesso soggetto con il titolo **scaduto** → ritorna quello
  dell'articolo. ⭐ Rev 2: il test di ieri diceva «cliente con `iva_id` diverso»,
  e non si può più scrivere — quella colonna non esiste (`D7-bis`). Un test che
  itera sui soggetti di oggi passerebbe comunque a vuoto: è il «verde per
  sottrazione» che `AGENTS.md` vieta;
* ⭐ **pgTAP su I7, ed è quello che nessuno penserebbe di scrivere**: stesso
  soggetto, **due emittenti**, un titolo per ciascuno → il consumo di plafond
  dell'uno **non** intacca l'altro (`D10-bis`). È l'errore che si vedrebbe solo
  su un plafond esaurito prima del dovuto, cioè sul numero che l'Agenzia delle
  Entrate verifica;
* **pgTAP su I7 / ambito**: titolo con ambito ristretto a un **articolo** → il
  risolutore lo applica su quella riga e **non** su una riga di un altro
  articolo dello stesso documento (è il caso «agevolata disabili», `D10`);
* **il test che nessuno scrive**: `split_payment = 'S'` **non** cambia il codice
  IVA risolto. È la confusione più facile da fare e la più cara da scoprire in
  fattura;
* ⭐ **la prova che le due determinazioni si sono unite** (I4): stessa riga letta
  come documento e come attività di fatturazione → **stesso** `iva_id`. Finché
  restano due strade, è l'unico test che si accorge quando divergono.

---

## 7. Cosa NON è in questo brief

* la riga di ri-consegna che nasce senza IVA: è
  [brief-db-ddt-riconsegna-eredita-testata.md](../work-done/brief-db-ddt-riconsegna-eredita-testata.md)
  §3-bis / R4. Le due cose si toccano ma non si sostituiscono — la ri-consegna
  deve ereditare l'aliquota **applicata sulla spedizione d'origine**, che è un
  fatto storico e non il risultato del risolutore di oggi;
* l'omaggio (§2.2): già risolto dalla causale;
* ⛔ **gli scaglioni di aliquota del gas** (§2.7.4): fuori perimetro **per
  decisione di Tid**, 2026-08-27. La documentazione resta come **memoria futura** —
  la forma del risolutore li accoglierebbe, ma non sono modellati e non si
  progetta su una previsione;
* 📌 **il manuale dell'IVA**: Tid, 2026-08-27 — *«poi nel caso vedo se generare un
  manuale specifico per l'IVA che indica tutto il funzionamento e descrive cosa
  esiste / da fare»*. Questo brief è un documento di **cantiere**: nasce da un
  difetto e muore quando il difetto è chiuso. Un manuale è un'altra cosa e ha
  un'altra sede (`docs/it/backend/.../manual/`, template `manual-standard.md`) —
  quando si scriverà, questo brief è materiale, non il documento;
* qualunque misura sui dati. Qui non ce n'è nessuna, ed è voluto: la domanda
  «quanti clienti hanno un'IVA diversa da quella dei loro articoli?» non decide
  niente. Il modello ammette la divergenza — `clienti.iva_id` è una colonna
  `NOT NULL` con una FK a `config.iva` — e tanto basta.

---

## 8. ⭐ Come funziona l'IVA, con le regole decise

> Il racconto in linguaggio piano, richiesto da Tid il 2026-08-28. È la stessa
> cosa detta dalle decisioni sopra; serve a chi arriva e vuole capire il disegno
> prima di leggere le colonne.

**Una riga di documento ottiene la sua IVA in due tempi.**

**Tempo 1 — quale aliquota compete a questa merce.** Risponde la merce e il suo
uso, mai la controparte. Si guarda l'articolo; se la riga viene da un listino, un
contratto o un'offerta, quelli possono dire la loro perché ognuno porta già un
`iva_id` accanto al prezzo; e per le utility si guarda il **tipo d'uso** della
fornitura (domestico, altri usi, condominio, pubblico), che è dove sta scritto
perché il gas di casa non paga come il gas di uno stabilimento. Vince il livello
**più specifico**, esattamente come per il prezzo. A questo punto esiste
un'aliquota ordinaria, e per chiunque è quella.

**Tempo 2 — questo cliente ha un titolo che la sostituisce *su questa riga*?** Si
va a vedere se il **soggetto** — la partita IVA, non la singola fornitura — ha un
**titolo registrato e valido a quella data**: una dichiarazione d'intento, una
dichiarazione di uso industriale, un'agevolazione per disabile, la qualifica di
cooperativa sociale. Se non ce n'è, il Tempo 1 è la risposta finale. Se ce n'è
uno **e l'articolo di questa riga ricade nel suo ambito**, prende il posto
dell'aliquota ordinaria.

⚠️ **Le tre parole «su questa riga» sono la sostanza, non una precisazione**
(`D12`). Un titolo non accende un documento: si valuta **riga per riga**. Un
cliente con un'agevolazione limitata a due articoli, su un documento di dieci
righe, ottiene due righe agevolate e otto ordinarie. Senza questo, il titolo
sarebbe la stessa cosa che abbiamo appena tolto dal cliente: un valore che vince
su tutto perché nessuno gli ha detto dove fermarsi.

Un titolo non è un flag: è un **documento**. Ha un protocollo o una prova, una
data di inizio e una di fine, dice **a chi** è stato presentato (l'emittente) e
dice **per cosa vale** — tutto, oppure solo certe categorie di merce, oppure un
articolo solo. Se ha un tetto — è il caso della dichiarazione d'intento — ogni
fattura ne consuma un pezzo, ogni nota di credito ne restituisce uno, e se il
tetto finisce a metà riga la riga **si spezza**: non imponibile fino a capienza,
il resto ad aliquota ordinaria.

**L'operatore non digita l'IVA.** Non è una scelta, è una conseguenza: si applica.
Il prezzo si negozia — e infatti chi lo scavalca passa da un'approvazione —
l'aliquota no. Se un cliente ha diritto a qualcosa di diverso, quel diritto **si
registra una volta** come titolo, con la sua carta, e da quel momento vale da solo
su tutti i documenti finché è valido.

**Il documento a monte proietta, la fattura decide — ed è una differenza di
*quando*, non di *come*** (`D14`). È la **stessa funzione**, eseguita due volte in
due momenti. Il DDT non produce un valore di serie B: produce quello **giusto
alla sua data**, e la fattura quello giusto **alla sua**. Se divergono non c'è
nessun errore — è cambiato qualcosa in mezzo: un titolo scaduto, un plafond
esaurito, una dichiarazione revocata.

⭐ Per questo il risolutore **si fa dare la data** invece di guardare l'orologio:
la fattura deve rispondere alla **propria data documento**, non all'istante in
cui il lotto gira — che può essere il giorno dopo.

**E a un certo punto il calcolo si ferma per sempre** (`D15`). Il risolutore gira
finché il documento è in bozza, ripassa un'ultima volta quando diventa
**definitivo**, e da lì in poi non gira **mai più**: una ristampa, un invio, un
PDF rigenerato leggono l'aliquota **scritta sulla riga**, non la ricalcolano. Un
documento definitivo è uno snapshot fiscale, e uno snapshot che si ricalcola non
è uno snapshot.

⭐ È anche il momento in cui il **plafond si consuma**: l'ultima risoluzione
decide come si spezza la riga, e la spezzatura decide quanta capienza va via —
sono la stessa operazione, non due. Prima di quel momento tutte le anteprime
guardano lo stesso residuo senza toccarlo, ed è giusto così: sono anteprime.

Per lo stesso motivo il risolutore **legge e basta**. Se consumasse, non lo si
potrebbe chiamare per mostrare un'anteprima — che è precisamente l'uso che ne fa
il documento.

**Restano fuori due cose che sembrano IVA e non lo sono.** Lo *split payment* e
il *cliente PA* non cambiano l'aliquota: cambiano chi versa l'imposta all'erario,
e viaggiano per conto loro fino alla fattura elettronica. E CIG, CUP e commessa
non c'entrano con l'IVA affatto: sono i riferimenti del **contratto**, e in
fattura ci arrivano copiati da lì.

---

## 8-bis. Avanzamento — cosa è scritto e cosa è applicato

> ⛔ ~~**Niente di quanto segue è applicato.** I file esistono nel branch
> `dev/db-tid` e nessun `liquibase update` è stato lanciato: lo stato reale si
> legge da `databasechangelog`, non da questa tabella.~~
>
> ⚠️ **SUPERATA il 2026-08-29 — questa riga è rimasta indietro rispetto al
> proprio paragrafo.** Le singole voci qui sotto dicono già «✅ APPLICATA», e la
> **Fase 1 lato DB è chiusa**: verificato sulla doc auto-generata di
> `docs/it/dbzero/` — le sei colonne non ci sono più su `anagrafiche.clienti`,
> `split_payment`/`cliente_pa` sono su `anagrafiche.soggetti`, i tre codici su
> `vendite.contratti`, `congela_fiscale` su `config.stati_doc_fiscale`.
>
> ⭐ **Perché la correzione vale la riga che costa**: è l'apertura della sezione,
> cioè quello che si legge per primo e si smette di leggere se dice che non c'è
> niente. Chi si è fermato qui ha creduto che il backend avesse tempo — mentre
> creazione cliente, dettaglio cliente e form-defaults preventivo erano **già in
> 500**. La riga resta barrata e non cancellata perché è così che si vede che era
> vera quando è stata scritta.
>
> 📌 Resta valido il criterio: **lo stato reale si legge da `databasechangelog`**,
> non da una tabella scritta a mano.

### ✅ `I10` — soglia di congelamento — **APPLICATA** (§8-sexies)

| File | Cosa |
| --- | --- |
| `00_schema/config/20260829-03-alter-stati-doc-fiscale-congela-fiscale-mctit.yaml` | colonna `congela_fiscale BOOLEAN NOT NULL DEFAULT true` + `COMMENT` + backfill su `codice_interno` |
| `80_data/sql/config/stati_doc_fiscale.csv` | colonna aggiunta su tutte e 6 le righe (`f` su DRAFT/EMESSA, `t` sugli altri quattro) |
| `20_code/vendite/20260829-04-update-fn-ricalcola-riepilogo-iva-fattura-congela-fiscale-mctit.yaml` | la funzione legge la colonna invece della lista cablata |
| `db/pgtap/config/test-stati-doc-fiscale-congela-fiscale.sql` | 7 asserzioni |

**Verifica fatta** (SQL **estratto** dagli YAML, non riscritto, eseguito intero
in una transazione con `ON_ERROR_STOP=1` che si chiude in `ROLLBACK`): entrambi i
changeSet passano, `UPDATE 2` conferma che il backfill tocca esattamente DRAFT ed
EMESSA. I 7 pgTAP sono verdi.

⭐ **E il test 7 è stato provato dal percorso reale**: rilanciato contro la
funzione **vecchia** (quella del blocco `rollback`, con la lista cablata) diventa
**rosso**. Senza questa controprova non si saprebbe se è verde perché la funzione
legge il dato o perché l'asserzione non sa produrre il caso.

✅ **APPLICATA il 2026-08-29** (Tid; `databasechangelog`: `20260829-03` e
`-04` EXECUTED, `20250912-01` RERAN). Nessuna regressione sulla baseline `config`.

**I due limiti dichiarati sono stati chiusi dopo il migrate:**

1. ✅ pgTAP **rilanciato come app** (`scripts/testpgtap.sh`, ruolo `zeroerp_app`,
   RLS attiva): **7/7 verdi**. La corsa pre-apply girava per forza da owner —
   la DDL non ancora applicata va iniettata nella stessa transazione — quindi
   non aveva esercitato la RLS;
2. ⛔ il secondo limite non era un dubbio: era **una trappola armata**, e ne è
   uscito un file in più. Il mirror `20250912-01` dichiara **10 colonne su 13**:
   `fase` e `is_abortito`, nate dieci mesi dopo (`20260714-02`), non sono mai
   state aggiunte alla sua lista, e `congela_fiscale` sarebbe stata la terza.
   Tutte e tre hanno avuto il loro backfill, quindi **il DB è giusto e niente
   segnala il problema** — ma una colonna fuori dalla lista del mirror **non è
   governata dal CSV**: cambiare quella cella e lanciare il migrate non sposta
   niente, senza errori.
   ⭐ E per questo cantiere non è un dettaglio: `D15` promette che *«cambiare la
   soglia è una cella di CSV»*, e senza rimedio quella frase era **falsa**.
   → **`20260829-05-riancora-mirror-stati-doc-fiscale-mctit.yaml`**, che
   ri-ancora il mirror con tutte e 13 le colonne (pattern di `20260806-13/-14`).
   Verificato prima di scriverlo che CSV e tabella viva **coincidono su tutte e
   13 le colonne, riga per riga** (quindi ri-ancorare non riporta indietro
   nulla), e che l'upsert su **tutte e sei** le righe passa in transazione
   annullata — cioè che il mirror è risvegliabile e non è una mina della specie
   «irriscrivibile».
   ⚠️ Differenza voluta rispetto a `20260806-14`, dove `fase`/`terminale`/`esito`
   restano **fuori** perché le governa un altro changeSet: qui nessun processo
   vivo le governa (il `20260714-02` era un backfill una-tantum). *La domanda
   «chi governa questa colonna?» va rifatta ogni volta, non ereditata.*

📌 **Strascico noto e non chiuso**: il codice sollevato resta
`E_PARAMETRO_INVALIDO`, mentre «documento congelato» è un **conflitto di stato** e
meriterebbe un codice `CONFLITTO_STATO` come i tre gemelli del gate DDT. Coniarlo
è catalogo + CSV + classe, cioè un changeSet suo.

### ✅ `I9` — gate su ordini — ~~scritta, non applicata~~ → **APPLICATA** (§8-sexies)

| File | Cosa |
| --- | --- |
| `20_code/script/20260829-06-create-fn-check-ordine-confermabile-mctit.yaml` | `script.fn_check_ordine_confermabile`, funzione pura |
| `20_code/vendite/20260829-07-update-trgfn-ordini-guard-transizione-iva-mctit.yaml` | **Regola 4** nel guard: ogni ingresso in `CONFERMATO` passa dalla funzione |
| `20_code/script/20260829-08-update-fn-available-actions-ordine-conferma-iva-mctit.yaml` | il **bottone** espone la reason, così guard e capability non divergono |
| `80_data/sql/config/codici_errore.csv` + `messaggi_errore.csv` | `E_ORDINE_RIGA_IVA_MANCANTE`, classe `CONFLITTO_STATO` (id messaggio 1013) |
| `db/pgtap/vendite/test-ordini-guard-conferma-iva.sql` | 8 asserzioni |

⭐ **Tre decisioni di forma che vale la pena non ri-discutere:**

1. **funzione specifica dell'AZIONE**, gemella di `fn_check_ordine_annullabile`, e
   **non** una `fn_check_ordine_confermabile` «completa» che assorbe anche
   «documento senza righe». Quel motivo non è una regola della conferma: è una
   precondizione generica guidata dalla **matrice** (`meta.requires_righe`), che
   il lato lettura applica a qualunque transizione la dichiari. ⛔ Oggi
   `requires_righe` risulta su **una sola** transizione, ma è una lettura del
   **seed**: portarla nel codice avrebbe trasformato un meccanismo data-driven in
   un hardcode sulla base di una fotografia;
2. ⭐ **il perimetro della Regola 4 è QUALUNQUE transizione verso `CONFERMATO`**,
   non il solo `DRAFT→CONFERMATO` della Regola 2 che le sta accanto. La matrice
   ammette il rientro da `PARZIALMENTE_EVASO` e da `EVASO`, e la vista del
   riepilogo **non sa da dove si arriva**. È la stessa lezione di `R-1` sul DDT:
   *il vincolo deve avere lo stesso perimetro del consumatore che protegge*;
3. **la condizione `prezzo_unitario IS NOT NULL` è scritta anche se oggi è sempre
   vera** — `vendite.ordini_righe.prezzo_unitario` è `NOT NULL`, quindi di fatto
   la regola vale su ogni riga attiva. Si scrive perché è la forma vera della
   regola, e perché in questo progetto una colonna prezzo è **già** diventata
   facoltativa una volta (`20260819-13` su `ddt_righe_componenti`).

**Verifica fatta** (SQL estratto dagli YAML, eseguito intero in transazione
annullata): i tre changeSet passano. **8/8 pgTAP verdi**, con i due codici errore
iniettati in transazione perché il CSV di `80_data` arriva solo al migrate.

⭐ **Controprova dal percorso reale**: rilanciato il test contro il guard e la
capability **vecchi** (i blocchi `rollback` di `-07` e `-08`, tenendo la funzione
pura), cadono **esattamente** le tre asserzioni che provano la regola nuova —
bottone spento, blocco su `DRAFT→CONFERMATO`, blocco sul rientro da `EVASO` —
mentre le altre restano verdi. Il test discrimina, non è verde per sottrazione.

✅ **APPLICATA il 2026-08-29** (Tid). Baseline `vendite` rilanciata **come app**:
**242 file, 5 rossi, tutti e 5 già noti in baseline — nessuna regressione**.

⛔ **Ma una regressione c'era stata, ed è un errore di metodo da scrivere.** Il
guard nuovo ha fatto fallire `vendite/test-ordini-guard-transizione-v1.sql`: le
sue quattro fixture inserivano righe d'ordine **senza `iva_id`**, e siccome
`prezzo_unitario` è `NOT NULL` quelle righe un prezzo ce l'hanno per forza —
descrivevano cioè un documento che il dominio non ammette più. Fixture adeguata
(`iva_id` nei riferimenti e nelle quattro righe), ora 8/8.

⚠️ **La regola per non ricascarci non è «grep del nome della tabella»**: quasi
tutti i test toccano `vendite.ordini_righe`. Il grep che trova i candidati veri è
sulle **liste di colonne** degli `INSERT` — quelli che *non nominano* la colonna
che il guard ora pretende. Sono usciti 6 file su 44; provati uno per uno, solo
quello regrediva.

⚠️ **E un rosso trovato strada facendo NON era mio**:
`script/test-seed-stati-doc-ordini-evaso-v1.sql` fallisce perché asserisce che
`EVASO` è terminale mentre la matrice ha `EVASO→CONFERMATO`. È **già in
`baseline-rossi.tsv`** — verificato prima di attribuirselo.

✅ Coperte anche le suite fuori dal perimetro della baseline `vendite` — cinque
test di `script/` e `rls/` che portano un ordine a CONFERMATO, tutti verdi — e
gli **smoke Django**: `smoke-push-termine-documento-commessa.py` valorizza già
`iva_id`, quindi è salvo.

📌 **Debito verso il frontend, dichiarato**: la `reason_key`
`vendite.ordini.azione_reason.iva_mancante` **non esiste nei locales** — la
gemella del DDT (`vendite.ddt.azione_reason.iva_mancante`) sì. Va aggiunta, ed è
fuori dal perimetro DB di questo branch.

### ✅ `I9` — metà preventivi — ~~scritta, non applicata~~ → **APPLICATA** (§8-sexies)

| File | Cosa |
| --- | --- |
| `20_code/script/20260829-09-create-fn-check-preventivo-emettibile-mctit.yaml` | `script.fn_check_preventivo_emettibile`, funzione pura |
| `20_code/vendite/20260829-12-update-fn-ricalcola-riepilogo-iva-preventivo-guardia-iva-mctit.yaml` | ⭐ la **guardia** `iva_id IS NOT NULL` che mancava (§R-3) |
| `20_code/vendite/20260829-10-update-trgfn-preventivi-guard-transizione-iva-mctit.yaml` | **Regola 2** nel guard: ogni ingresso in `EMESSO` passa dalla funzione |
| `20_code/script/20260829-11-update-fn-available-actions-preventivo-emetti-iva-mctit.yaml` | il bottone **Emetti** espone la reason |
| `80_data/…/codici_errore.csv` + `messaggi_errore.csv` | `E_PREV_RIGA_IVA_MANCANTE`, `CONFLITTO_STATO` (id messaggio 1014) |
| `db/pgtap/vendite/test-preventivi-guard-emissione-iva.sql` | 8 asserzioni |

⛔ **`-12` e `-10` sono UNA slice e non si applicano separati**: la guardia da
sola aprirebbe la strada a una riga senza aliquota, che finirebbe nel riepilogo
con imponibile pieno e imposta zero. Il cancello all'emissione è la rete.

⭐ **Tre asimmetrie con la gemella sugli ordini**, tutte verificate sulla
struttura, e per cui la funzione **non è una copia**:

1. `preventivi_righe` **non ha `riga_nr`** — ha `ordine smallint DEFAULT 0`, che è
   una chiave di ordinamento. Nel messaggio va la **descrizione**: «la riga 0»
   non aiuterebbe nessuno;
2. `preventivi_righe.quantita` è **nullable e senza `CHECK` di positività**,
   mentre `ordini_righe` ha `chk_ordini_v_r_qta_pos`. Il filtro `quantita > 0`
   qui **serve davvero** — è nel predicato del consumatore, e senza si
   bloccherebbe un preventivo per una riga che nel riepilogo non entra mai;
3. `preventivi_righe.attivo` è **nullable** (su `ordini_righe` è `NOT NULL`):
   `attivo IS TRUE` esclude il `NULL`, esattamente come fa il consumatore.

⭐ **Il test 5 prova il lato che nessuno prova mai — che il guard NON blocchi più
del dovuto**: riga senza aliquota ma a **quantità zero** → l'emissione **passa**,
perché quella riga nel riepilogo non entra. Con il predicato copiato dagli ordini
bloccherebbe un preventivo sano.

**Verifica**: i quattro changeSet eseguono in transazione annullata, **8/8 pgTAP
verdi**.

⭐ **E questa volta lo sweep dei test esistenti è stato fatto PRIMA**, non dopo:
27 file che toccano preventivi provati con la DDL iniettata. Tre rossi — tutti e
tre **già in `baseline-rossi.tsv`** e rossi identici senza le modifiche.
**Zero regressioni nuove.**

📌 Debito verso il frontend: la `reason_key`
`vendite.preventivi.azione_reason.iva_mancante` va aggiunta ai locales.

### ✅ `I8` e `I0` — la **metà additiva** — ~~scritta, non applicata~~ → **APPLICATA** (§8-sexies)

> ⭐ Entrambe si dividono in due: una parte **additiva**, che non rompe niente e
> si può applicare subito, e una parte **che toglie**, che rompe il backend
> perché oggi quelle chiavi le scrive. La seconda è **gated**, e la richiesta al
> BE è qui sotto.

| File | Cosa |
| --- | --- |
| `00_schema/vendite/20260829-13-alter-contratti-add-cig-cup-commessa-mctit.yaml` | `I8-A`: `codice_cig`, `codice_cup`, `codice_commessa` su `vendite.contratti` |
| `00_schema/anagrafiche/20260829-14-alter-soggetti-add-split-payment-cliente-pa-mctit.yaml` | `I0-A`: `split_payment` e `cliente_pa` su `anagrafiche.soggetti` + `CHECK ('S','N')` + travaso una tantum |
| `db/pgtap/anagrafiche/test-soggetti-split-payment-cliente-pa.sql` | 5 asserzioni |

**Verifica**: entrambi eseguono in transazione annullata; il travaso fa
`UPDATE 1` e la controprova nella stessa transazione conta **0 soggetti
incoerenti** rispetto alle proprie righe cliente. **5/5 pgTAP verdi.**

⭐ **Il travaso usa `bool_or`, e la direzione è una decisione**: quando le righe
cliente dello stesso soggetto dissentono, **vince `'S'`**. Lo split payment è un
obbligo quando si applica, quindi ometterlo è un errore *fiscale*, mentre
applicarlo in più è un errore *visibile e correggibile*.

⚠️ **Tipo `character(1)` con `CHECK ('S','N')`, non un boolean** — è la forma
dell'origine, tenuta apposta: cambiare tipo nello stesso passo in cui si cambia
sede avrebbe reso il travaso qualcosa di diverso da una copia. Il pgTAP prova che
il `CHECK` **morde**, e non è burocrazia: senza, la colonna accetterebbe `'Y'`,
`'t'`, `'1'` o uno spazio, e ognuno si comporterebbe come «non applicare lo
split» al primo `= 'S'` — un errore fiscale silenzioso, nella direzione peggiore.

⚠️ **E il default qui è `'N'`, l'opposto della scelta fatta per
`congela_fiscale`.** Là un dato mancante deve **bloccare**; qui un soggetto di
cui nessuno ha detto nulla **non è** in scissione — dichiararlo tale d'ufficio
produrrebbe fatture sbagliate su tutta l'anagrafica. *La domanda «qual è la
direzione sicura?» si rifà ogni volta, non si eredita.*

#### ⭐ `I8` lato fattura: dove atterrano i tre codici — **deciso sulla struttura**

Il §`D9` diceva «snapshot sulla **testata** della fattura». **È sbagliato**, e lo
decide una lettura del modello: `vendite.fatture_righe` porta
`sorgente_tipo_id`/`sorgente_uid` con **15 tipi** possibili
(`config.sorgenti`), fra cui `CONTRATTO` e `CONTRATTO_RIGA`. Una fattura nasce
aggregando attività di **sorgenti diverse**, quindi **può mescolare righe di più
contratti**: un campo di testata dovrebbe sceglierne uno fra tanti.

**La sede giusta è la RIGA di fattura**, ed è anche ciò che la FatturaPA
prevede — `DatiContratto` / `DatiOrdineAcquisto` possono portare
`RiferimentoNumeroLinea`.

⛔ **Ma la colonna non si aggiunge adesso, ed è una scelta.** Chi la riempie è la
generazione della fattura, che deve risalire `riga → sorgente → contratto`
passando dalla chiave polimorfa (`reference_sorgente_polimorfa_key_selector`:
`uid` per preventivo/offerta, `id::text` per il resto). Aggiungere ora una
colonna che nessuno riempie ricreerebbe **esattamente** il difetto della voce 2
di questo brief — un campo che promette una cosa che non succede. **Va costruita
insieme a `I4`**, quando la riga di fattura viene rifatta.

### ✅ `I0-B` e `I8-B` — le sei colonne **spariscono** da `clienti` — **APPLICATE** (§8-sexies)

> ⚠️ **Autorizzate da Tid il 2026-08-29**: *«fai tutto, non c'è produzione;
> appena abbiamo fatto tutto farò iniziare il BE per la sistemazione»*. Avevo
> segnalato che rompono il CRUD del cliente; la decisione è di procedere.

**Tre passi, e l'ordine È il contratto** — l'autogen mescola `00_schema` e
`20_code` ordinando per **numero**, quindi è il numero a garantire la sequenza:

| # | File | Cosa |
| --- | --- | --- |
| 1 | `20_code/anagrafiche/20260829-20-update-fn-update-cliente-drop-sei-chiavi` | chi **scrive** smette |
| 2 | `20_code/dbops/20260829-21-recreate-vw-diag-v-clienti-links-senza-iva` | chi **legge** smette |
| 3 | `00_schema/anagrafiche/20260829-22-alter-clienti-drop-iva-flag-e-codici` | le colonne **spariscono** |

> ⚠️ **Erano `-15`/`-16`/`-17` e sono stati rinumerati a `-20`/`-21`/`-22`**, perché
> `-15`…`-17` sono stati presi da un altro cantiere lo stesso giorno (numero documento in
> fattura, lineage, reso sourceless). ⛔ **Dentro i tre YAML i commenti citano ancora i
> numeri vecchi**, e non sono stati corretti di proposito: i changeSet sono **applicati e
> committati**, e `-22` non porta `validCheckSums` — riscriverne anche un commento farebbe
> fallire il prossimo migrate con un errore di checksum. *Il riferimento buono è questa
> tabella.* Manual e pgTAP sono invece allineati (18 riferimenti corretti).

#### ⛔ Quattro dipendenze censite prima di toccare, e due non si vedono da un `\d`

1. **`dbops.vw_diag_v_clienti_links`** leggeva `c.iva_id` → ricreata senza (passo 2).
   ⚠️ `DROP + CREATE` e non `CREATE OR REPLACE`: le tre colonne uscivano **da in
   mezzo** alla proiezione, e `REPLACE` sa solo aggiungere in coda. ⚠️ E
   `security_invoker=on` **ripetuto**, altrimenti si azzera in silenzio e una
   diagnostica su dati di clienti tornerebbe a leggere fuori dal perimetro RLS.
   ⛔ Nessun `CASCADE`: verificato che nessuno dipende dalla vista, né nel DB né
   nel repo.
2. **`anagrafiche.fn_update_cliente`** le scriveva tutte e sei → adeguata (passo 1).
   ⚠️ Il plpgsql è a legatura **tardiva**: il `DROP` sarebbe passato lo stesso e
   la funzione avrebbe iniziato a fallire al primo salvataggio. *L'ordine dei tre
   passi serve esattamente a questo.*
3. **`trg_clienti_a10_iva_require_attivo_ins_upd`** su `clienti` → tolto esplicitamente.
4. ⛔ **`trg_iva_a10_clienti_block_deact_upd` su `config.iva` — LA MINA.** Chiama
   `dbops.trgfn_prevent_deactivate_if_children('anagrafiche','clienti','iva_id',…)`:
   la colonna è nominata come **stringa**, quindi PostgreSQL non registra nessuna
   dipendenza. Sarebbe **sopravvissuto** al `DROP` per poi fallire a **runtime**,
   su un'**altra tabella** e in un momento lontano — quando qualcuno disattiva un
   codice IVA. *Nessun `CASCADE` l'avrebbe preso, perché non c'era niente da
   cascatare.* ⚠️ Tolto **solo** quello dei clienti: i 19 gemelli su `config.iva`
   restano, e la controprova lo verifica.

⭐ **Quinta cosa, che non è una dipendenza ma avrebbe ucciso il migrate
successivo**: la riga di `dbops.fk_index_policy` per `fk_iva_config`. La FK e
l'indice se ne vanno con la colonna, ma **la riga di policy resta**, e al
prossimo `90_end` `apply_fk_index_policy()` proverebbe a creare un indice su una
colonna inesistente. Cancellata — ed è il caso in cui un `DELETE` su `dbops` è
legittimo: `loadUpdateData` non cancella, e la riga descrive un vincolo che non
c'è più.

ℹ️ Lo **storico non è toccato**: `storico.clienti` conserva uno `snapshot` jsonb,
non colonne speculari. Gli snapshot vecchi continuano a portare le sei chiavi, ed
è corretto — raccontano com'era il cliente allora.

**Verifica**: i cinque changeSet (`-13`…`-17`) eseguono in un'unica transazione
annullata, con quattro controprove nella stessa transazione: **0** colonne
residue, **0** trigger-mina, **0** righe di policy, **19** trigger gemelli su
`config.iva` sopravvissuti.

#### ⭐ Due pgTAP adeguati — e il secondo non era un rattoppo

- `anagrafiche/create-cliente.sql`: fixture con `iva_id` (era `NOT NULL`) → tolta;
- `anagrafiche/test-fn-update-cliente-v1.sql`: ⚠️ il suo **cuore** è la prova di
  **atomicità** — «se l'UPDATE del cliente fallisce, la categoria scritta sul BA
  viene annullata» — ed era costruita proprio su `iva_id` e `codice_commessa`. La
  **proprietà** resta identica, cambia il **veicolo**: la FK inesistente ora è su
  `modalita_pagamento_id`, e il campo che deve restare invariato è
  `servizio_da_fatturare`. ⭐ Ne è uscito anche più preciso: prima passava
  `NULL` come SQLSTATE perché l'errore poteva arrivare da due parti (FK o guard
  iva-attivo), ora asserisce `23503`.

**Sweep pre-apply**: ⛔ **e qui ho sbagliato di nuovo il grep, nello stesso punto
e in modo diverso.** Avevo cercato le sei colonne con una regex **legata alla
riga** (`clienti` e il nome di colonna entro 40 caratteri): ma le liste di
colonne degli `INSERT` **vanno a capo**, quindi `iva_id` cadeva fuori dalla
finestra. Uscivano 4 file su 86; ne mancavano **quattro**, tutti trovati da Tid
sull'applicato.

⭐ **Il grep che funziona non ha vincoli di prossimità**: si cercano i nomi di
colonna **da soli** in tutta la suite (`grep -rlE '\b(iva_id|split_payment|…)\b'`),
e poi si restringe a chi tocca la tabella. 86 file → 7 candidati → 4 rotti.
*Due volte di fila la regola «fai il grep» è stata rispettata e il grep era
comunque sbagliato: la parte difficile non è ricordarsi di cercare, è la forma
della ricerca.*

**I quattro adeguati** (nessuno era in `baseline-rossi.tsv`, quindi tutte
regressioni mie): `anagrafiche/test-istanza-cliente-chain` (4 blocchi: CTE `iva`,
colonna, valore e join), `anagrafiche/test-simula-subentro` (2 blocchi — ⚠️ e la
rimozione lasciava una **virgola pendente** che il primo giro non aveva visto),
`anagrafiche/test-clienti-sync-utility-pdp-policy` (4 blocchi),
`script/test-fn-disdetta-cliente` (il più intrecciato: colonna di temp table,
termine in un'asserzione, variabile, `SELECT INTO` e `INSERT`).

⚠️ In due file la temp table `tmp_iva` è stata **lasciata**, con la sua
asserzione: fa parte del `plan` e verifica ancora `config.iva`, che esiste.
Toglierla avrebbe cambiato il conteggio senza guadagnare nulla.

#### ⛔ Richiesta al BACKEND — da fare adesso

> ✅ **PRESA IN CARICO E CHIUSA il 2026-08-29**, in
> [brief-be-fe-iva-risolutore-e-regime-cliente.md](brief-be-fe-iva-risolutore-e-regime-cliente.md)
> — il piano BE/FE della Fase 1, che contiene anche `I8` lato contratto, `I0`
> lato soggetto e il debito i18n di `I9`. La tabella qui sotto resta come
> **richiesta originale**, e va letta con due correzioni che sono emerse
> eseguendola:
>
> ⛔ **L'effetto non era il solo «silenzio»**: quello vale per la sola PATCH, che
> passa da `fn_update_cliente`. Gli altri tre percorsi — `POST` di creazione
> cliente, `GET` di dettaglio e `/vendite/preventivi/form-defaults/` — sono **SQL
> diretto sulla tabella**, quindi erano **500**. `S1` è stata un ripristino, non
> una pulizia. *La richiesta era stata scritta guardando la whitelist, non le
> query.*
>
> ⛔ **Mancava un prerequisito DB**, ed è l'unica coda ancora aperta:
> `vendite.fn_create_contratto` ha una whitelist interna che **scarta in
> silenzio** i tre codici in CREATE — stesso difetto di `fatturazione_immediata`
> del 2026-07-27, sulla stessa funzione. Richiesta in
> [brief-db-fn-create-contratto-codici-atto.md](../work-done/brief-db-fn-create-contratto-codici-atto.md).

Dal momento in cui `-15` è applicato, un payload che contiene una delle sei
chiavi **non viene respinto: viene ignorato in silenzio**, perché la whitelist
non le conosce più. ⭐ È il comportamento meno peggiore dei due — sollevare
avrebbe bloccato ogni salvataggio cliente — **ma va saputo**: finché il FE manda
ancora `iva_id`, l'operatore salva, non vede errori, e quel valore non va da
nessuna parte.

| Dove | Cosa togliere |
| --- | --- |
| `apps/anagrafiche/db/clienti_repository.py` | le sei chiavi dalle liste di colonne (righe ~167, ~381-386, ~445-447) |
| `apps/anagrafiche/services/clienti_service.py` | le sei chiavi + **il default `DEFAULT_IVA_ID`** (righe ~227-233, ~238) |
| `apps/anagrafiche/api/views_clienti.py` | `iva_id` dai serializer (righe ~84, ~125) |
| `apps/anagrafiche/db/billing_account_repository.py` | `cl.iva_id` e il `LEFT JOIN config.iva` da `get_cliente_defaults` (righe ~281, ~289) |
| `apps/vendite/services/vendite_form_defaults_service.py` | `iva_id`/`iva_codice`/`iva_descrizione` dal payload di `/vendite/preventivi/form-defaults/` (righe ~452, ~518) |
| `frontend/src/anagrafiche/components/ClienteDrawer.vue` | il campo `IvaSelect`, i tre codici e il default `DEFAULT_IVA_ID` |
| `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue` | il commento «per termine/iva sovrascriviamo solo se vuoti», che ora è falso |

📌 **E dove rimetterli**: i tre codici sul form del **contratto**
(`vendite.contratti.codice_cig`/`_cup`/`_commessa`), i due flag sul form del
**soggetto** (`anagrafiche.soggetti.split_payment`/`cliente_pa`).

### 📄 Documentazione manual — fatta il 2026-08-29

> ⚠️ Solo i `manual/` (documentazione **concettuale**): l'auto-gen la rigenera Tid.

**Due manual NUOVI**, per le due funzioni nate in questo cantiere:
`script/manual/fn_check_ordine_confermabile.md` e
`script/manual/fn_check_preventivo_emettibile.md`. Il secondo porta anche la tabella delle
**tre asimmetrie** con la gemella (niente `riga_nr`, `quantita` senza `CHECK`, `attivo`
nullable), che è la ragione per cui le due funzioni non sono copie.

⛔ **Tre manual dicevano il FALSO** dopo i `DROP`, e sono stati corretti:

| File | Cosa affermava di falso |
| --- | --- |
| `anagrafiche/manual/clienti.md` | le regole di validazione di `cliente_pa` e `split_payment`, colonne non più lì |
| `anagrafiche/manual/fn_update_cliente.md` | la whitelist con tutte e sei le chiavi |
| `dbops/manual/vw_diag_v_clienti_links.md` | il blocco IVA fra le entità collegate, i join e le colonne |

⚠️ **E su `fn_update_cliente` la doc era già indietro prima di me**: la whitelist elencava
`tipo_gg_scadenza_ft` e `nr_giorni_scadenza`, tolte il **2026-07-31** e mai aggiornate lì.
*Un elenco senza presidio invecchia in silenzio, e chi lo legge non ha modo di accorgersene.*

**Tre manual arricchiti** con le colonne nuove — incompleti, non falsi:
`config/manual/stati_doc_fiscale.md` (`congela_fiscale`, con le tre scorciatoie sbagliate e
il perché del `DEFAULT true`), `anagrafiche/manual/soggetti.md`
(`split_payment`/`cliente_pa`, con il default `N` e perché va nella direzione **opposta**),
`vendite/manual/contratti.md` (CIG/CUP/commessa, con la conclusione che in fattura la sede è
la **riga** e non la testata).

### ✅ Fase 1 completata lato DB

---

## 8-ter. Fase 2 — `I7`, le sedi dei titoli — ✅ **APPLICATA il 2026-08-29**

> ✅ **Applicata da Tid il 2026-08-29**, dodici changeSet. Baseline `anagrafiche` e
> `script` rilanciate: **verdi, nessuna regressione**.
>
> ⭐ **E con il migrate si chiude il limite dichiarato più sotto**: i due pgTAP nuovi
> stanno in `db/pgtap/anagrafiche/`, quindi la baseline li ha eseguiti **come
> applicazione** — la RLS delle tre tabelle è stata esercitata sul serio, non solo
> nella corsa pre-apply da owner.

### I file

| # | File | Cosa |
| --- | --- | --- |
| 23 | `00_schema/config/…-create-config-tipi-titolo-iva` | il **vocabolario** dei tipi (`D10`), con `ha_plafond` |
| 24 | `00_schema/anagrafiche/…-create-soggetti-titoli-iva` | la **sede**: soggetto + emittente in chiave, ambito, `validita` `daterange`, plafond, `EXCLUDE` |
| 25 | `00_schema/anagrafiche/…-create-soggetti-titoli-iva-ambiti` | l'**ambito** su tre livelli — articolo, gruppo voce, tipologia voce |
| 26 | `00_schema/anagrafiche/…-create-soggetti-titoli-iva-movimenti` | il **registro** di `D5` |
| 27 | `00_schema/anagrafiche/…-enable-rls-soggetti-titoli-iva` | il **perimetro emittente** sulle tre tabelle |
| 28 | `20_code/anagrafiche/…-guard-coerenza` | plafond ⇔ tipo, e «TUTTO non ha righe di ambito» |
| 29 | `20_code/anagrafiche/…-guard-ambito-sovrapposizione` | `fn_check_titolo_iva_ambito` + **due** trigger che la chiamano |
| 30 | `20_code/anagrafiche/…-movimenti-accumulatore` | `imponibile_utilizzato` = somma del registro |
| 31 | `20_code/anagrafiche/…-fn-consuma-plafond-titolo-iva` | la **primitiva** con il lock di `D15-bis` e la ripartizione di `P2` |
| 32 | `80_data/changelog/…-seed-config-tipi-titolo-iva` | i quattro tipi, da CSV |
| — | `80_data/sql/config/iva.csv` | append del codice **`NI35`** (id 18), `natura_iva_id = 8`: la natura non è più orfana |
| 33 | `80_data/changelog/…-fk-index-policy-titoli-iva` | undici FK: **un sì e dieci no** |
| 34 | `90_end/…-grant-titoli-iva-app` | i privilegi runtime, che fuori CI nessuno concede |
| — | `80_data/sql/config/codici_errore.csv` + `messaggi_errore.csv` | **sette** codici nuovi, id messaggio 1015‑1021 |
| — | `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` | 23 asserzioni, runner **app** |
| — | `db/pgtap/anagrafiche/test-soggetti-titoli-iva-due-emittenti.sql` | 5 asserzioni, runner **owner** dichiarato |

### ⭐ Cinque decisioni di forma da non ri-discutere a valle

1. **L'anti-sovrapposizione è un vincolo vero solo su metà dei casi, ed è
   dichiarato** (decisione di Tid, 2026-08-29). La chiave di `D10` è
   (soggetto, emittente, tipo, **ambito**), e l'ambito dei titoli ristretti vive
   in una tabella **figlia**: un `EXCLUDE` non la può leggere. Quindi `EXCLUDE`
   reale su `ambito = 'TUTTO'`, guard sulle figlie per i ristretti. ⛔ Scriverli
   entrambi come guard avrebbe indebolito il caso forte; pretendere un `EXCLUDE`
   anche sul caso debole avrebbe voluto dire denormalizzare quattro colonne sulla
   figlia e tenerle in sync.
2. 🔴 **Il guard dell'ambito sta su DUE trigger, e il secondo è quello che si
   dimentica.** Due titoli diventano sovrapposti anche quando cambia il **padre**
   — si allarga `valido_al`, si riattiva un titolo spento, si cambia il tipo — e
   in nessuno di quei casi la tabella figlia viene toccata. ⭐ La regola sta in
   **una funzione pura** (`anagrafiche.fn_check_titolo_iva_ambito`) e i due
   trigger la **chiamano**: il presidio non è «gli esiti coincidono», è «il guard
   non contiene più il predicato».
3. ⭐ **Solo il pareggio esatto è un'ambiguità.** Due titoli su **livelli
   diversi** (articolo e categoria) convivono legittimamente — li risolve `D13`
   per specificità. Un guard scritto largo avrebbe passato tutti i test e
   rifiutato la configurazione normale: per questo il pgTAP ha il test gemello
   che pretende che **passi**.
4. ⛔ **Il tetto non si controlla nell'accumulatore**, ed è una decisione. Sulle
   fatture il caso non si presenta (la spezzatura di `P2` la calcola la
   primitiva); sulle **forzature** un superamento è un'informazione sul mondo —
   una forzatura esiste per registrare fatturazioni fuori dal sistema, e
   impedire di scriverla impedirebbe di **accorgersene**. 📌 Il presidio giusto
   per quel caso è una **lista di titoli sfondati che qualcuno guarda**, e non
   fa parte di `I7`.
5. ⚠️ **`imponibile_utilizzato` non ha un `CHECK >= 0`.** Quella colonna la
   scrive un trigger che gira dentro una scrittura su un'**altra** tabella: un
   `23514` lì sarebbe un errore muto, lontano dal gesto dell'operatore. Il conto
   sotto zero lo rifiuta il trigger, con un codice registrato e una frase che
   nomina il titolo.

### ⛔ La metà di `D15-bis` che il DB non può tenere — richiesta al BACKEND

`D15-bis` chiede due cose e il DB ne dà **una**:

* ✅ **il lock**: `SELECT … FOR UPDATE` sulla riga del titolo dentro
  `fn_consuma_plafond_titolo_iva`. Due transizioni a DEFINITIVA in parallelo si
  serializzano, e il plafond non va sotto zero;
* ⛔ **l'ordine deterministico** — «chi arriva prima si prende la capienza», e
  «prima» dev'essere una regola del dominio (data documento, poi numero) — **non
  è realizzabile nella primitiva**: un lock non può sapere che esiste una
  fattura precedente non ancora arrivata.

**La sede è il ciclo che chiama**: il giro di lotto deve iterare le fatture
`ORDER BY data documento, numero`. Va scritto quando `I4` porta il consumo nella
transizione a DEFINITIVA. ⭐ Il registro lo rende comunque **verificabile a
posteriori**: `data_movimento` e `fattura_id` dicono in quale ordine la capienza
è andata via.

### ✅ Verifica fatta

**L'SQL provato è quello VERO, non una riscrittura**: generato con
`liquibase updateSQL` su una copia dei dodici changelog privata delle sole
`preConditions` (che vengono valutate contro il database vivo, dove le tabelle
non esistono ancora, e avrebbero fatto `HALT` dal secondo file in poi). I 363
statement girano interi in una transazione con `ON_ERROR_STOP=1` che si chiude in
`ROLLBACK`: **zero errori**.

**pgTAP**: 23/23 e 5/5 verdi, con la DDL iniettata nella stessa transazione.

⭐ **E discriminano — provato spegnendo i presidi uno per uno:**

| mutazione | cadono |
| --- | --- |
| spento il guard sull'ambito (figlie + padre) | **esattamente** 10, 11, 13 |
| spento l'accumulatore del registro | **esattamente** 14, 15, 16 |
| tolto l'`EXCLUDE` anti-sovrapposizione | **esattamente** 7 |
| spento il guard di coerenza del plafond | 4 e 5, e poi la corsa **si ferma**: le righe che il guard avrebbe rifiutato fanno saltare l'`EXCLUDE` due test dopo |
| l'emittente **esce** dalla chiave dell'`EXCLUDE` | il file «due emittenti» non riesce nemmeno a **costruire** il caso: il secondo titolo prende un `23P01` |

⚠️ E i due test «non blocca più del dovuto» — il rinnovo annuale (8) e i due
titoli su livelli diversi (12) — restano **verdi** sotto tutte le mutazioni: è
quello che devono fare.

~~⚠️ **Limite dichiarato**: la corsa pre-apply gira per forza da **owner** (la DDL
non applicata va iniettata nella stessa transazione), quindi la **RLS non è stata
esercitata**. Va rilanciata come app dopo il migrate.~~ ✅ **Chiuso il 2026-08-29
con il migrate**: la baseline `anagrafiche` gira come `zeroerp_app` e ha eseguito
entrambi i file — verdi.

### ⭐ Un fatto misurato che CORREGGE una riga del §8-bis

Il §8-bis scrive, a proposito del mirror di `stati_doc_fiscale`, che *«una colonna
fuori dalla lista del mirror non è governata dal CSV: cambiare quella cella e
lanciare il migrate non sposta niente, senza errori»*. **È falso su Liquibase
5.0.3**, e si è visto generando l'SQL invece di ragionarci sopra:

```text
INSERT INTO config.stati_doc_fiscale (id, codice, descrizione, attivo, ordine, meta,
  codice_interno, applica_lotto, applica_fattura, chiude_lotto, fase, is_abortito,
  congela_fiscale) VALUES (…)
```

Il mirror storico `20250912-01` ne dichiara **dieci**, e ne emette **tredici**: il
blocco `columns:` configura i **tipi**, non restringe quali colonne si caricano —
Liquibase prende **tutto l'header del CSV**. Stessa prova su `config.iva`, il cui
mirror dichiara perfino una colonna **cancellata** nel 2025 (`assoggettamento_iva`)
e la ignora senza rumore.

⭐ **Conseguenze, e sono due:**

1. la promessa di `D15` — *«cambiare la soglia è una cella di CSV»* — **era già
   vera**. `20260829-05` non ha fatto danni ed è più esplicito di prima, ma la
   ragione con cui è stato scritto non regge: va letto come una **pulizia**, non
   come una riparazione;
2. per questo `I7` **non ri-ancora** il mirror di `config.iva` prima di
   appenderci `NI35`: non serve. ⚠️ Verificato comunque che il file non sia una
   **mina** — CSV e tabella viva coincidono su tutte e 14 le righe, l'upsert
   completo passa in transazione annullata, e la riga nuova supera entrambi i
   `CHECK` di `config.iva`.

⭐ *È il caso peggiore descritto da `AGENTS.md` al contrario: una conclusione
giusta appoggiata a un meccanismo che non esiste. Il rimedio non era rifare il
lavoro, era generare l'SQL e guardarlo.*

### 📄 Documentazione manual — fatta il 2026-08-29

> ⚠️ Solo i `manual/` (documentazione **concettuale**): l'auto-gen la rigenera Tid.

**Dieci file nuovi**, uno per ogni oggetto nato con `I7` — verificato contro
`pg_class`/`pg_proc` che non ne manchi nessuno e che nessuno sia di troppo:

| Dove | Cosa |
| --- | --- |
| `config/manual/tipi_titolo_iva.md` | perché è un **vocabolario** e non una tabella «dichiarazioni d'intento», e perché `ha_plafond` è la sola colonna che porta informazione |
| `anagrafiche/manual/soggetti_titoli_iva.md` | il principio di `D7`, i **due proprietari** (`D10-bis`), l'ambito come condizione di applicabilità, e l'anti-sovrapposizione che è un vincolo vero solo su metà dei casi |
| `…/soggetti_titoli_iva_ambiti.md` | perché queste righe sono **la differenza fra un titolo e il `clienti.iva_id` appena tolto** |
| `…/soggetti_titoli_iva_movimenti.md` | perché un registro e non una colonna, e perché il **tetto non si controlla lì** |
| `…/fn_consuma_plafond_titolo_iva.md` | la ripartizione di `P2`, il lock, e **la metà di `D15-bis` che il DB non tiene** |
| `…/fn_check_titolo_iva_ambito.md` | cosa è un **pareggio** e cosa invece si risolve da sé |
| `…/trgfn_*` (quattro) | uno per guard: perché `AFTER` contro la convenzione, perché il nome sceglie l'**ordine**, e il caso del movimento spostato fra due titoli |

⭐ **Due cose che il DDL non racconta, e per cui i manual esistono**: perché
l'emittente sta in **chiave** (senza, due plafond diventano un contatore solo), e
perché l'`EXCLUDE` copre soltanto i titoli `ambito = 'TUTTO'`. Chi legge lo schema
vede un vincolo parziale e pensa a una dimenticanza.

⚠️ **Non c'è un manual per il file di test né per i changeSet**: la loro sede è
questo brief.

### 📌 Residui dichiarati di `I7`

* ✅ ~~⚠️ **tre righe di `fk_index_policy` sono un «no» RIMANDATO**~~ → **il «no»
  è confermato, e non per inerzia**. Il residuo diceva: *«se la query vera di
  `I2` entrerà dall'articolo, si accende una cella di CSV»*. `I2` è stata
  scritta, e la sua query dello stadio B entra da
  `anagrafiche.soggetti_titoli_iva` e raggiunge gli ambiti con
  `LEFT JOIN … ON a.titolo_iva_id = t.id` — cioè **dal titolo**, esattamente come
  previsto. Le tre celle restano `consentito = false`, ed è ora una **decisione
  verificata** invece di un rinvio. ⭐ È anche il motivo per cui non si
  indicizza su una previsione: la previsione andava messa alla prova, non
  assecondata;
* 📌 la **lista dei titoli sfondati** (punto 4 qui sopra) non esiste;
* ⚠️ l'**applicazione** del titolo su una riga di documento è di `I2`: qui si
  prova che l'ambito è registrabile e coerente, non che qualcuno lo legga;
* 📌 i tre tipi diversi da `INTENTO` non hanno ancora un `config.iva` da
  applicare, e **non se ne conia nessuno al buio**: si sceglie fra i codici a
  catalogo quando si registrerà il primo titolo di quella specie.

---


## 8-quater. Fase 3 — ~~aperta e **sospesa**~~ → **RIPRESA E CHIUSA** lato DB

> ~~⛔ **Il risolutore (`I2`) NON è stato iniziato**: decisione di Tid, a lavoro
> appena avviato.~~
>
> ⭐ **La sospensione è finita lo stesso giorno**: `I2` è scritta, applicata e
> coperta da 15 casi pgTAP (§8-quinquies). ⚠️ **La sezione resta**, e non per
> archeologia: quello che segue è ciò che è emerso *prima* di fermarsi — la
> misura sulla struttura che ha cambiato la forma dello stadio A, e le due
> questioni aperte. Entrambe hanno poi deciso il disegno, e cancellarle
> renderebbe incomprensibile il perché.

### 🔴 Un fatto misurato sulla struttura che cambia la forma dello stadio A

Il §2.4 dice che l'aliquota è *«già accanto al prezzo a ogni livello»*, citando
listini, contratti e offerte. **È vero solo per i COMPONENTI di bundle**:

| Tabella | prezzo | `iva_id` |
| --- | --- | --- |
| `listini_righe` · `contratti_righe` · `offerte_commerciali_eccezioni` | ✅ | ⛔ |
| `listini_righe_componenti` · `contratti_righe_componenti` · `offerte_commerciali_eccezioni_componenti` | ✅ | ✅ |
| `promo_articoli` | — | ⛔ |

⭐ Per un articolo venduto **da solo** — la forma ordinaria — listino, contratto
e offerta **non hanno niente da dire sull'IVA**. La domanda che il §5 lasciava
aperta («lo stadio A segue lo stesso ordine di `fn_resolve_prezzo_listino_v2`?»)
in gran parte **si dissolve**: non c'è nessuna cascata da riprodurre, perché su
quei tre livelli l'aliquota non esiste.

### ✅ Tre decisioni di Tid, 2026-08-29

* **`D16`** — **i bundle restano fuori dal risolutore.** Le righe di documento
  hanno già le loro `*_righe_componenti` con un `iva_id` proprio: l'aliquota del
  componente è materia di chi costruisce la riga (`I3`/`I4`). ⛔ Non si tocca il
  nucleo del pricing per esporre quale componente ha vinto il prezzo — sarebbe un
  cambio di `RETURNS TABLE` su una funzione con molti chiamanti. Lo stadio A resta
  a **due** livelli;
* **`D17`** — **l'uso della fornitura entra dove l'articolo TACE**, cioè
  `COALESCE(articoli.iva_id, tipi_utenze.iva_id)`. ⚠️ L'ordine inverso sembrava
  più naturale — il tipo d'uso distingue due aliquote a parità di articolo — ma
  `config.tipi_utenze.iva_id` **non ha nessun modo di dire su quali merci vale**:
  applicato per primo si prenderebbe ogni riga della fornitura, cauzioni e servizi
  compresi. È il difetto *«vince su tutto perché nessuno gli ha detto dove
  fermarsi»* che `D12` ha chiuso un piano sopra. ⭐ E la struttura dice come
  uscirne: `catalogo.articoli.iva_id` è **nullable**, cioè l'articolo *può* tacere
  — è lo stesso argomento di `D7`. Chi vuole l'aliquota d'uso su una merce le
  toglie l'opinione;
* **`R-4` chiusa** — `config.fn_get_aliquota_iva` passa da `VOLATILE` a `STABLE`.

### Cosa c'è nel branch, e cosa no

| Voce | Stato |
| --- | --- |
| `20_code/config/20260829-35-update-fn-get-aliquota-iva-stable` | ✅ **APPLICATO** — corpo invariato, `provolatile = 's'` verificato sul catalogo |
| `I2` — il risolutore e il suo helper `fn_get_tipo_utenza_fornitura` | ~~⛔ **sospesi**~~ → ✅ **APPLICATI** come `20260829-46`, `-49`, `-50`. ⭐ E le due questioni qui sotto **sono state risolte prima di scrivere**, non aggirate: l'helper prende `(billing_account, utility, data)` e non un `contratto_id` |

### ⚠️ Le due questioni ancora aperte, per quando si riparte

1. **`config.tipi_utenze` si raggiunge solo via `contratti_utilities.contratto_id`,
   e NESSUNA testata di documento porta un `contratto_id`** — verificato su ddt,
   ordini, preventivi e fatture: tutte portano invece la terna
   `(billing_account_id, utility_id, data)`. Il predicato «contratto attivo per
   quella terna» **esiste già** dentro `fn_resolve_prezzo_listino_v2_esito`, con
   il suo `ORDER BY c.id DESC` per essere deterministico sugli overlap. O lo si
   estrae da lì (toccando il nucleo del pricing), o lo si riscrive dichiarando il
   debito e la **sede designata**. La scelta va fatta, non ereditata;
2. ⚠️ **Il risolutore legge `soggetti_titoli_iva`, che ha la RLS.** L'applicazione
   passa l'emittente del documento che sta lavorando — in perimetro per
   costruzione — e i ruoli batch hanno `BYPASSRLS`. ⛔ Ma un chiamante **senza
   contesto** legge zero titoli e ottiene l'aliquota ordinaria **in silenzio**, e
   qui il costo non è una lista più corta: è un'imposta applicata dove non andava.
   Va deciso se resta `SECURITY INVOKER` con il contratto scritto, o se la lettura
   dei titoli si eleva.

📌 **`D15` non entra nella firma del risolutore**: il congelamento oltre la
DEFINITIVA è una proprietà del **documento**, e il risolutore riceve un articolo.
È un contratto dei chiamanti — `I3`/`I4` leggono `congela_fiscale` prima di
ri-risolvere. Va scritto lì, o sembrerà una dimenticanza.

---


## 8-quinquies. Il disegno del risolutore, esteso — 2026-08-29

> Impostazione di Tid, presa a parole dopo la sospensione della Fase 3. Riguarda
> **come sarà fatto** il risolutore, non quando: sono le cose che dopo costano
> care da cambiare. Le decisioni stanno qui e non vanno ri-discusse a valle.

### ✅ Le decisioni

* **`D18` — il ritorno è un COMPOSITO, non un numerico.** Aliquota, natura
  dell'operazione, esigibilità, reverse charge, split payment, riferimento
  normativo da stampare. ⭐ La ragione: *le operazioni non imponibili hanno tutte
  aliquota zero ma non sono la stessa cosa fra loro, e la fattura elettronica
  pretende che tu dica quale zero è*. Con un composito, aggiungere un paese
  significa aggiungere valori al dominio di natura; con un numerico significa
  aggiungere colonne dappertutto;
* **`D19` — risolvere in scrittura, leggere il congelato.** Il trattamento
  risolto si **scrive sulla riga** e da lì si rilegge. ⛔ Se la ristampa di una
  fattura del 2024 richiama il risolutore, il giorno che cambia un'aliquota si
  riscrive la storia — e su un documento fiscale non è un difetto estetico. *Il
  risolutore serve a produrre il valore, non a rappresentarlo*;
* **`D20` — la firma prende il paese delle DUE parti e la natura
  dell'operazione** (cessione di beni / prestazione di servizi, che in ambito
  intracomunitario determina il luogo di imposizione). ⭐ È la firma a
  determinare il costo dell'internazionalizzazione, molto più della logica
  interna: con `(articolo, cliente, data)` funziona benissimo in Italia e
  obbliga a toccare **ogni chiamante** quando si aggiunge un paese. Costa niente
  adesso, anche se per ora l'unico paese possibile è l'Italia;
* **`D21` — un GUSCIO CHE SMISTA**, non un parametro con rami interni. Stampo
  del dispatcher già esistente `anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch`
  → `script.fn_validate_cf_piva_it`. ⛔ **Ma con il ramo `ELSE` che SOLLEVA**: il
  dispatcher del codice fiscale non ce l'ha — paese diverso da `IT` e non valida
  niente, in silenzio. Su una validazione è un buco; su un risolutore IVA
  sarebbe un'imposta sbagliata senza errore;
* **`D22` — reverse charge = flag esplicito** nel composito. Oggi è implicito
  nella natura `N6.x`, cioè leggibile solo da chi conosce la tabella;
* **`D23` — la natura dell'operazione nasce come flag su `config.nature_vendita`**
  (vocabolario a seed: una cella di CSV), non come colonna sull'articolo.
  ⚠️ `config.nature_vendita` esiste già con `MERCE` / `SERVIZIO_UNA_TANTUM` /
  `SERVIZIO_RICORRENTE`, ma risponde a **un'altra domanda** — il routing
  post-preventivo verso ordine, commessa o contratto. Riusare `destinazione_tipo`
  per dedurre beni/servizi sarebbe la forma esatta del flag composto che il
  progetto ha già pagato. Il flag è nuovo e dice una cosa sola. ⭐ Precedente
  della stessa specie: `config.listini_tipologie.e_servizio`;
* **`D24` — il riferimento normativo NON diventa una colonna.** ⭐ `config.iva`
  è **già più fine della natura**: `EC`, `VG` e `VF` condividono
  `natura_iva_id = 10` e differiscono solo per l'articolo citato — il
  riferimento è già modellato come **identità della riga**. Una colonna sarebbe
  una seconda sede. ⚠️ Ma lo **slot nel composito si mette ora**, riempito da
  `descrizione`: l'asimmetria dei costi è netta — aggiungere una colonna a
  `config.iva` domani è una cella di CSV, cambiare la forma del ritorno del
  risolutore domani è un `DROP` più ogni chiamante;
* **`D25` — le tabelle delle aliquote NON si versionano.** In Italia una
  variazione IVA non si comporta come un listino: vale per le operazioni da
  quella data in poi, e le precedenti tengono la loro — che è esattamente ciò
  che uno snapshot **completo** sulla riga dà (`D19`). ⭐ Lo snapshot non è un
  ripiego al versionamento: **lo rende non necessario**. Lo storico serve a
  ricostruire com'era un catalogo, non a garantire che una fattura si ristampi
  identica.

### ✅ Fatto in giornata: la storia delle tabelle IVA

Misurato prima di toccare: la macchina c'era e **il rubinetto era chiuso**.

| | trigger | gemella `storico.*` | `storicizza` nel seed |
| --- | --- | --- | --- |
| `config.iva` | ✅ | ✅ | era **`f` su tutte e 15 le righe** → ora `t` |
| `config.iva_assoggettamenti` | ✅ | ✅ | era `f` su tutte e 3 → ora `t` |
| `config.iva_natura` | ⛔ | ⛔ | colonna **aggiunta** (`20260829-38`) + seed `t` |
| `config.iva_stati` | ⛔ | ⛔ | ⛔ **resta fuori**, vedi sotto |

⭐ Per `iva_natura` **basta la colonna**: `dbops.fn_run_automations_storico_provision`
crea la gemella e `fn_run_automations_storico` aggancia il trigger, e il
`DEFAULT true` fa registrare la tabella fra quelle a storicizzazione
**permanente** (`proc_sync_storico_set_storicizza` guarda proprio il default).
⚠️ Girano solo nel contesto `ci_apply`: dopo un migrate manuale arrivano col
`db-ci-apply` o col job serale, non subito.

⚠️ **La storia non retroagisce**: da qui in avanti ogni modifica lascia traccia,
il passato no. Tid, 2026-08-29: *«sulle tabelle non è un problema, non perdiamo
nulla, solo test»*.

### ✅ ~~🟡 Residuo~~: `config.iva_stati` non era storicizzabile — **CHIUSO da `20260829-42`**

Ha una **PK composita** `(iva_id, stato_id)`, mentre le tabelle di storico
portano **una sola** colonna di riferimento — `storico.iva` ha `iva_id integer`.
Aggiungerle `storicizza` produrrebbe un provisioning storto invece di uno storico.

⭐ Il rimedio è la convenzione del progetto (linee-guida §4: *per chiavi composte
preferire una surrogate key*): un `id` identity, e la coppia retrocessa a
`UNIQUE`. ✅ Verificato che **nessuna FK punta a `config.iva_stati`**, quindi si
può fare senza toccare altro — ma è un cambio di chiave primaria su una tabella
viva, cioè un'altra cosa da «aggiungere la storicizzazione». Da decidere.

### ⛔ Aperto: il buco IVA sulla riga di fattura

Lo snapshot su `vendite.fatture_righe` **è parziale**:

```text
iva_id      integer      ← puntatore VIVO
iva_natura  varchar      ← testo COPIATO, snapshot vero
esigibilita, split_payment
```

Sulla stessa riga una colonna congela e l'altra no. ⛔ **CORREZIONE del 2026-08-29, ed è un mio errore da non lasciare in
piedi**: avevo scritto che *«la fattura del 2024 cambia numero»*. **Non cambia.**
`fatture_riepiloghi_iva` porta `imponibile`, `imposta` e `arrotondamento`
**memorizzati**, `fatture.imposta_tot` pure, e il ricalcolo si rifiuta di girare
oltre `congela_fiscale`: gli euro di allora sono scritti. Mi ero fermato a
`fatture_righe`, dove l'aliquota non c'è, senza guardare il riepilogo, dove il
risultato c'è.

⭐ E questo spiega perché il drop di giugno **non fece danni**: l'imposta era già
salva altrove, quindi `iva_perc` sulla riga *era* davvero un duplicato. La
decisione era giusta anche nel merito, non solo nel principio.

**Il difetto vero è più piccolo, e resta un difetto**: congelato è il
*risultato*, non la **percentuale che lo spiega** — quella le viste la ripescano
viva. Dopo un cambio di aliquota un documento vecchio direbbe «23%» accanto a
un'imposta calcolata al 22%: **un documento che contraddice sé stesso**.

⛔ **Ma l'aliquota non è «mancante»: è stata tolta apposta.** `20260604-05`:
*«l'aliquota si deriva da `iva_id` via `config.iva`, non si denormalizza in
colonna (no logica/dato duplicato)»* — e `fatture_righe.iva_perc` era già uscita
nell'ottobre 2025. Rimetterla e basta riaprirebbe una decisione presa bene.

⭐ **Le due cose non sono in conflitto: parlano di oggetti diversi**, e la prova
è sulla stessa riga — `iva_natura` è sopravvissuta alla stessa potatura.

| | Cos'è | Verdetto |
| --- | --- | --- |
| un'aliquota su un documento **vivo** | denormalizzazione per evitare un join: invecchia | duplicato, giustamente tolto |
| un'aliquota su un documento **congelato** | **fatto storico**, come `emittente_snapshot` e `cliente_snapshot` | non è un duplicato |

### ✅ `D26` — l'aliquota va su ENTRAMBE le tabelle (Tid, 2026-08-29)

Avevo proposto il solo riepilogo. **L'argomento di Tid lo batte**: *«a volte
viene richiesto di rigenerare i riepiloghi, che prendono la riga: è necessario
sapere l'aliquota che era stata applicata al tempo»*.

⭐ `fn_ricalcola_riepilogo_iva_fattura` ricostruisce i riepiloghi **dalle
righe**, e ricavava l'aliquota chiamando il catalogo — cioè **viva**. Una
rigenerazione dopo un cambio di aliquota produrrebbe numeri diversi
dall'originale, e **niente nella riga potrebbe smentirla**: la riga non ha
memoria. Quindi la colonna serve in due punti per due ragioni:

* sulla **riga** → perché è la sorgente da cui si ricostruisce;
* sul **riepilogo** → perché è dove vivono imponibile e imposta, i due numeri
  che l'aliquota deve spiegare.

⛔ **E non riapre giugno**: quella decisione riguardava una denormalizzazione su
un documento **vivo**, che invecchia. Questa è uno **snapshot** — la stessa
specie di `iva_natura`, che alla stessa potatura era **sopravvissuta**, sulla
stessa riga e nella stessa funzione.

### ✅ Fatto, verificato e ~~(non applicato)~~ **APPLICATO**

| # | Cosa |
| --- | --- |
| `20260829-39` | `aliquota_iva` su `fatture_righe` e `fatture_riepiloghi_iva`, + backfill |
| `20260829-40` | `trgfn_fatture_righe_guard_normalize` congela anche l'aliquota, accanto alla natura che già copiava |
| ~~`20260829-41`~~ | ~~la rigenerazione **legge la riga** invece di ricalcolare~~ — ⛔ **SUPERATO da `20260829-51`**, vedi `D30`: era sbagliato, e la parte che resta viva è solo «scrive l'aliquota sul riepilogo» |
| `20260829-42` | `config.iva_stati`: chiave surrogata + `storicizza` |

⛔ **Il backfill delle RIGHE si ferma ai documenti vivi, ed è una scoperta**:
`trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt` rifiuta qualunque
scrittura sulle righe di una fattura oltre la soglia. Il guard **ha** un bypass
(`zeroerp.maintenance_reset_lotto_draft`) e **non si usa**: quel nome dice a cosa
serve, e dirottarlo farebbe credere al prossimo lettore che sia in corso un reset
di lotto. ⭐ Ma soprattutto **non si deve**: scrivere su una riga congelata è
esattamente ciò che il guard esiste per impedire, e non diventa lecito perché la
colonna è nuova. Quelle righe restano a `NULL`, e il `NULL` **significa**
«anteriore allo snapshot». Non perdono niente: per loro l'aliquota resta sul
riepilogo, che invece si riempie per tutti — non è protetto dal guard dei
satelliti, e lì non si tocca nessun numero fiscale, si aggiunge la percentuale
che spiega quelli già scritti.

⭐ **La prova che conta**: presa una fattura vera **al 22%** e rigenerati i
riepiloghi, `imponibile`, `imposta` e `arrotondamento` risultano **identici**. La
formula non è cambiata di una parentesi; la sottoquery serve solo a usare
l'aliquota due volte. ⚠️ Il primo giro era finito su una fattura ad aliquota
**zero** — un'uguaglianza fra zeri sarebbe passata anche con la formula rotta, e
il test è stato stretto perché potesse fallire.

### ✅ `D27` — il `MAX` non si risolve allargando l'unica: si chiude a monte (Tid, 2026-08-29)

Domanda di Tid: *«come è possibile che lo stesso codice IVA abbia due aliquote
diverse?»*. ⭐ **Sulla stessa fattura non è possibile**: l'aliquota è funzione di
*(codice IVA, stato dell'emittente)*, entrambi costanti sul documento.

Diventa possibile in **un solo modo**: se qualcuno modifica
`config.iva.aliquota_iva` *in place* fra la scrittura di una riga e quella della
successiva. ⛔ E verificato: **quella colonna non aveva nessun lock**, era
modificabile a piacere.

⭐ Quindi il difetto non era il `MAX`, era a monte: **cambiare l'aliquota di un
codice in uso ne riscrive il significato retroattivamente** su ogni documento che
l'ha applicato. La cura è il lock, non l'allargamento di `uq_fatture_r_iva_key`:
un cambio di aliquota diventa un **codice nuovo**, che è come funziona nella
realtà — un'aliquota che cambia non trasforma il vecchio codice, ne affianca uno.
Con il lock il caso che il `MAX` collasserebbe è **irraggiungibile**.

`aliquota_iva` e `natura_iva_id` entrano in `dbops.automation_lock_columns` con
`E_IVA_TRATTAMENTO_IMMUTABILE` (`CONFLITTO_STATO`, id messaggio 1022). Uscita
dichiarata per il refuso su un codice appena creato: `zeroerp.allow_lock_columns_override`.

### ✅ `D28` — `config.iva` prende `codice_interno` (Tid, 2026-08-29)

Backfill `codice_interno = codice`. Serve al dispatch per paese di `D21`, che
deve nominare un codice IVA senza dipendere da un id soggetto a reseed, e a
`D24`, dove il testo del riferimento normativo vive in `descrizione` — una label
**modificabile**, mentre la chiave ora non lo è.

⭐ È anche il **primo dei tre passi** che linee-guida-sql §6b descrive per il
debito `DEFAULT_IVA_ID`, che oggi stocca un id numerico.

⚠️ **La trappola del provisioning, evitata di proposito**:
`fn_run_automations_lock_columns` crea il trigger **solo se non esiste**, quindi
aggiungere una colonna al lock dopo non fa più niente, in silenzio. Per questo
`20260829-43` fa un `DROP TRIGGER IF EXISTS` esplicito: `codice_interno`
(implicito) e le due colonne del trattamento devono finire **nello stesso**
trigger.

✅ **Verificato in transazione annullata**: l'automazione crea **un** trigger con
**tutte e tre** le colonne; l'`UPDATE` di `aliquota_iva` e di `codice_interno`
viene rifiutato; e — il lato che nessuno prova — `descrizione` resta
**modificabile**, che è tutto il senso di `D24`.

### ✅ `I2` — IL RISOLUTORE È SCRITTO ~~(non applicato)~~ e **APPLICATO** (2026-08-29)

| # | Cosa |
| --- | --- |
| `20260829-47` | `config.iva_natura.is_reverse_charge` (`D22`) — sede scelta da Tid |
| `20260829-48` | `config.nature_vendita.e_cessione_beni` (`D23`) |
| `20260829-49` | `vendite.fn_resolve_iva_riga_it` — la logica italiana |
| `20260829-50` | `vendite.fn_resolve_iva_riga` — **il guscio che smista** (`D21`) |
| — | tre codici errore, id messaggio 1023‑1025 |

**Il ritorno è il composito di `D18`**: quota, codice IVA, aliquota, natura,
inversione contabile, esigibilità, split payment, riferimento normativo, più
`origine` e `titolo_iva_id`.

⚠️ **`esigibilita` e `split_payment` sono TRASPORTATI, non usati** — ed è ciò che
tiene insieme `D4` e `D18`, che sembravano in conflitto: la scissione non cambia
l'aliquota, cambia **chi versa**, quindi non entra nella scelta del codice ma
esce nel composito perché chi costruisce la riga di fattura vuole un oggetto solo.

⚠️ **Il guscio accetta tre parametri che oggi non usa** — paese emittente, paese
cliente, cessione di beni (`D20`). Normalmente è il difetto che questo cantiere
combatte, e la differenza va detta: quello è un **campo che un operatore
compila** credendo di decidere qualcosa, questo è un **punto di estensione
dichiarato** — costa niente adesso e costerebbe *ogni chiamante* dopo. Tutti e
tre sono derivati quando non passati.

### ✅ Verificato in transazione annullata

| Prova | Esito |
| --- | --- |
| stadio A, articolo che parla → composito pieno (22%, esigibilità, norma) | ✅ |
| articolo muto senza fornitura → `origine = ASSENTE`, **e non solleva** | ✅ |
| ⭐ paese non implementato → **SOLLEVA** (il dispatcher CF/PIVA invece tace) | ✅ |
| anteprima senza importo → una riga sola, quota `NULL` | ✅ |
| ~~⛔ il ramo **`TIPO_UTENZA`**~~ | ~~**non esercitato**~~ → ✅ **CHIUSO** dal pgTAP di `I2`, caso 3 |

⛔ **Il ramo `TIPO_UTENZA` non è coperto, e la ragione è strutturale**: i
contratti attivi di questa macchina stanno tutti su utility **senza dimensione
tipo/classe**, e `trgfn_contratti_utilities_guard_tipo_classe` impedisce — a
ragione — di forzarne una: una utility ha quella dimensione *se e solo se*
esistono `config.tipi_utenze` per lei, e allora tipo **e** classe sono
obbligatori e coerenti. Forzarlo non sarebbe una scorciatoia di test, sarebbe
**un dato che il dominio non ammette**.

~~📌 **Va coperto dal pgTAP di `I2`, che il soggetto se lo fabbrica**~~ → ✅
**FATTO in giornata**, `db/pgtap/vendite/test-fn-resolve-iva-riga.sql`: la
fornitura si costruisce — si clona un contratto esistente sulla **utility che la
dimensione ce l'ha davvero**, lo si inserisce **già in `ATTIVO`** (transitarci
avrebbe provato il guard delle transizioni, che è un altro soggetto), e si
aggiorna `contratti_utilities` con tipo e classe coerenti.

⚠️ **E la riga di `contratti_utilities` non si inserisce: la crea un trigger.**
`uq_contratti_utilities_contratto_id` lo dice al primo tentativo. È il genere di
cosa che si scopre solo provando, ed è scritta nel test perché il prossimo non la
riscopra.

⭐ Vale la pena rileggere il perché: il caso **si costruisce, non si cerca**. Un
test che cerca il caso e non lo trova diventa **muto** — verde per sottrazione,
esattamente il difetto che questo cantiere ha già pagato altrove.

### ✅ `D29` — il predicato «contratto attivo» si ESTRAE (Tid, 2026-08-29)

Vive dentro `vendite.fn_resolve_prezzo_listino_v2_esito` e serve **identico** al
risolutore IVA, che da quel contratto arriva al tipo d'uso della fornitura.
⛔ Se le due funzioni scegliessero contratti diversi sullo stesso overlap,
**prezzo e aliquota della stessa riga verrebbero da forniture diverse**, e non lo
direbbe nessun errore.

⭐ Avevo difeso la copia con un argomento che Tid ha smontato: *«i chiamanti non
sono importanti, tu estrai una porzione interna e non modifichi la firma»* — ed è
esatto. Il nucleo ha **4** chiamanti e il guscio **11**, e nessuno vede la
differenza. Il rischio vero è un altro: **la trascrizione di 619 righe**.

**Come è stato mitigato**: il corpo non è stato riscritto a mano. È stato preso
dalla doc auto-gen (l'oggetto vivo), trasformato con una **sostituzione unica** e
verificato con un `diff` che mostra **solo** il blocco voluto — 619 righe
diventano 625, e le uniche cambiate sono quelle del predicato.

| # | Cosa |
| --- | --- |
| `20260829-44` | `vendite.fn_get_contratto_attivo` — la sede unica |
| `20260829-45` | il nucleo del pricing la **chiama** invece di contenerla |
| `20260829-46` | `fn_get_tipo_utenza_fornitura`, che la chiama a sua volta (`D11`) |

✅ **Verificato in transazione annullata** su 47 combinazioni reali, prese da
righe di DDT vere e da tutti i contratti attivi: **tutti e 15 i campi dell'esito
identici**, codici di errore compresi. E la prova diretta: il contratto che il
pricing riporta e quello che `fn_get_contratto_attivo` sceglie **coincidono
sempre**.

⚠️ **Copertura sottile, e va detta**: su questa macchina ci sono **3** contratti
attivi, e nessuno degli input di prova risolve un **tipo d'uso** — quel ramo non
è stato esercitato affatto. Non cambia il disegno (si progetta sul modello), ma
il pgTAP di `I2` dovrà **costruire** quel caso invece di cercarlo.

### ✅ `D23` confermata: la natura dell'operazione non è in `config.iva`

Verificato: né `config.iva` né `config.iva_natura` hanno qualcosa che distingua
beni da servizi. ⭐ E non potrebbero: sarebbe **circolare** — beni-vs-servizi
serve a *scegliere* il codice natura (`N3.1` esportazioni è merce, `N7` è
prestazione di servizi), quindi ricavarlo da lì significherebbe ricavare
l'**input** del risolutore dal suo **output**. Resta un flag su
`config.nature_vendita`.

### 📌 Residuo **neutralizzato**: l'aliquota è aggregata con `MAX` — reso irraggiungibile da `D27`

Il gruppo del riepilogo non comprende l'aliquota e **non può**: lo impedisce
`uq_fatture_r_iva_key`, l'unica sulla tabella. Dentro un gruppo il valore è uno
solo per costruzione — è funzione di (codice IVA, stato emittente), costanti sulla
fattura. ⛔ Ma **può** divergere, ed è proprio lo scenario per cui il cantiere
esiste: righe scritte prima e dopo un cambio di aliquota, sullo stesso documento
ancora in bozza. Lì `MAX` prende la più alta e la divergenza sparisce: **è un
caso collassato, non risolto**. La forma giusta è l'aliquota nel gruppo *e*
nell'unica — un changeSet suo, che tocca un vincolo su cui si appoggiano altri
consumatori.

⭐ **Superato da `D27` (stesso giorno)**: con il lock su `config.iva.aliquota_iva`
il caso diventa **irraggiungibile**, e l'allargamento dell'unica non serve più.
Il residuo resta scritto perché la ragione per cui non si allarga è una
decisione, non una dimenticanza.

### ⛔ `D30` — `20260829-41` era **sbagliato**, e si corregge con `20260829-51`

Trovato da un pgTAP esistente, `db/pgtap/vendite/test-ricalcola-riepiloghi-iva.sql`,
caso 7 «Override `iva_stati` applicato»: registra un override del 5% **dopo**
aver inserito le righe e pretende che il ricalcolo lo applichi. Con il `COALESCE`
di `-41` vinceva lo snapshot della riga e l'imposta restava a **zero**.

**Il difetto in una riga.** `fn_ricalcola_riepilogo_iva_fattura`, per
costruzione, **vede solo documenti NON congelati**: il guard su
`congela_fiscale`, sette righe più su nella funzione stessa, rifiuta tutti gli
altri. Quel `COALESCE` non poteva quindi proteggere nessun documento emesso —
agiva **solo sulle bozze**, cioè esattamente dove il catalogo di adesso è la
risposta giusta.

⭐ **E la conseguenza era già scritta, lo stesso giorno**, dentro
`trgfn_fatture_righe_guard_normalize` (`20260829-40`):

> «lo stesso identico percorso di `fn_ricalcola_riepilogo_iva_fattura`: se i due
> divergessero, riga e riepilogo dello stesso documento porterebbero aliquote
> diverse e nessuno se ne accorgerebbe finché non quadrasse un totale.»

Il `COALESCE` **produceva proprio quella divergenza**. Il trigger di riga
riscrive l'aliquota a **ogni** scrittura — non è uno snapshot «una volta» — e il
riepilogo si ancorava invece al valore che la riga aveva all'**ultima**
scrittura.

#### La regola, e perché le colonne di `20260829-39` restano

> **Lo snapshot dell'aliquota diventa una fotografia quando il documento smette
> di essere scritto, non perché qualcuno smette di leggerlo.**

Il rilievo di Tid — *«serve sapere l'aliquota applicata al tempo»* — è
soddisfatto dal **dato memorizzato**, non da un ripiego in lettura. Le due
colonne servono e restano: sono ciò che il documento porta con sé una volta
congelato. Il consumatore è **chi rigenera un documento già emesso**, un
percorso che **oggi non esiste** perché questa funzione lo rifiuta; il giorno che
nascerà, quel percorso leggerà la riga e non il catalogo.

#### Cosa fa `20260829-51`

**Riallinea le righe** al catalogo *prima* di aggregarle, guardato da
`IS DISTINCT FROM`. Così la coerenza fra riga e riepilogo è vera **per
costruzione** invece che sperata, ed è la stessa regola che segue il trigger.

⚠️ E l'aggregazione **continua a chiamare** `config.fn_get_aliquota_iva` invece
di leggere `r.aliquota_iva`, che dopo il riallineamento porta lo stesso valore:
su una riga **senza codice IVA** la funzione **solleva**, mentre la colonna
sarebbe `NULL` e diventerebbe uno **zero muto**. Trasformare un errore in uno
zero su una funzione fiscale non si fa di contrabbando dentro un altro lavoro —
è il difetto `§R-3`, e si chiude dove vive.

#### Le prove

* il pgTAP `test-ricalcola-riepiloghi-iva` passa **12/12** con `-51` caricato
  dentro la sua stessa transazione (e falliva sul 7 senza);
* **riga e riepilogo escono allineati**: entrambi a `5.00`, cioè all'override —
  la riga era nata a `0.00` e **si è riallineata**;
* a regime **nessuna riga resta disallineata**: il secondo giro non ha nulla da
  muovere, quindi l'`IS DISTINCT FROM` non produce storico a vuoto;
* il diff sul corpo tocca **tre soli hunk**: il blocco di commento con la
  `UPDATE`, il `MAX`, e il `COMMENT ON`.

---

### ✅ La pulizia della fattura: due voci nuove, e una decisione che vincola `I5`

`db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` è diventato rosso
il giorno dopo l'apply della Fase 2, e ha nominato la tabella nuova:
`anagrafiche.soggetti_titoli_iva_movimenti` ha una FK verso `vendite.fatture` e
una verso `vendite.fatture_righe`. **È esattamente il lavoro per cui quel file
esiste.**

Classificate **`SCOPERTA_NOTA`** — non per rimandare, ma perché è la categoria
**armata**: scade da sola nel momento in cui la decisione diventa reale. Oggi il
presupposto è vero e verificabile — **0 righe e nessuno scrittore**,
`fn_consuma_plafond_titolo_iva` non ha chiamanti.

⛔ **La categoria definitiva dipende da `I5`, e nel verso non ovvio: è `I5` a
essere vincolata da qui.** Il punto è *dove* si consuma il plafond.

| Se il consumo si registra… | …allora la categoria è | …e la conseguenza |
| --- | --- | --- |
| all'**emissione** | `BLOCCO_VOLUTO` | la pulizia lavora su documenti in `DRAFT` e non incontrerà mai un movimento; il giorno che lo incontrasse, **rifiutare è la risposta giusta** — stessa posizione di `pagamenti.sistemazioni` |
| già **in bozza** | `GESTITA` | un ripristino **deve stornare** il movimento prima di cancellare, altrimenti il plafond di un terzo resta mangiato da un documento che non esiste più — e `fn_cleanup_fatture_by_ids` va estesa |

⚠️ **E il file passa a `pgtap-runner: owner`.** Dieci asserzioni su undici leggono
il catalogo, che la RLS non filtra; la undicesima — il test 5 — è l'unica che
**conta righe**, ed è proprio su quello zero che si fonda l'eccezione.
`soggetti_titoli_iva_movimenti` ha **RLS attiva** con policy per emittente:
da `zeroerp_app` quel conteggio sarebbe stato **fail-closed**, e il presidio si
sarebbe **autoassolto**. Nessuna copertura RLS si perde, perché in quel file non
ce n'era.

⭐ **Provato per mutazione**: popolata davvero la tabella in una transazione
annullata, il presidio **diventa rosso e dice chi** —
`anagrafiche.soggetti_titoli_iva_movimenti (1 righe)`. Un presidio mai visto
rosso non è un presidio provato.

---

### ✅ Il pgTAP di `I2` — 14 casi, e ha trovato subito un difetto

`db/pgtap/vendite/test-fn-resolve-iva-riga.sql`. Chiama **sempre il guscio**, mai
`_it` direttamente: provare l'implementazione scavalcando il dispatcher vorrebbe
dire non provare `D21`.

| # | Cosa verifica |
| --- | --- |
| 1 | la fixture è completa, **e dice cosa manca** se non lo è |
| 2 | stadio A: l'articolo che ha un'opinione decide da solo |
| 3 | ⭐ stadio A2: l'uso della fornitura entra **dove l'articolo tace**, e porta **il suo** codice |
| 4 | ⭐ il verso opposto di `D17`: con l'articolo che parla, la fornitura **non** scavalca |
| 5 | articolo muto senza fornitura → `ASSENTE`, **e non solleva** (in bozza è legittimo) |
| 6 | il ritorno è un **composito** pieno (`D18`) |
| 7 | anteprima senza importo → **una** riga, quota `NULL` |
| 8 | ⭐ il guscio **smista**: paese non implementato → solleva `P0001` (`D21`) |
| 9 | stadio B: un titolo **sostituisce** l'aliquota ordinaria |
| 10 | ⭐ fra due titoli vince il **più specifico** (`D13`) |
| 11 | ⛔ due titoli in pari specificità → **solleva**, non sceglie |
| 12 | ⭐ plafond incapiente: la riga si **spezza** in due parti |
| 13 | e le due parti **sommano esattamente** l'imponibile |
| 14 | `is_reverse_charge` viene dalla natura — **skip dichiarato**, vedi sotto |

⚠️ **Il caso 4 non è un doppione del 3.** Senza di lui, un risolutore che
applicasse *sempre* il tipo d'uso passerebbe il caso 3 e sarebbe sbagliato:
`tipi_utenze` non sa dire «non ho opinione», quindi applicato per primo si
prenderebbe cauzioni e servizi.

⚠️ **Il caso 14 è uno skip, non un'asserzione.** Oggi **nessun** codice IVA attivo
porta una natura di inversione contabile, quindi il ramo non è esercitabile senza
inventare un codice di catalogo dentro un test — un dato finto in una tabella
vera. Si è preferito dichiarare lo skip invece di scrivere un'uguaglianza fra
`false` e `false`, che sarebbe **verde anche con il valore inchiodato**. ⭐ Il
giorno che un codice `N6` entra in catalogo, il caso si accende da solo.

⚠️ **I casi 9-12 si smontano a vicenda**: ogni caso riparte da zero titoli. Due
casi che si lasciano dietro il proprio dato si verificano l'un l'altro, e il primo
che sbaglia rende illeggibile il secondo.

---

### ⛔ `D31` — il pgTAP ha trovato un difetto **nel risolutore**, al primo giro

Caso 6, «il composito esce pieno». Rosso.

Nel composito, `split_payment` usciva **`NULL`** ogni volta che il soggetto non
era noto — cioè in **ogni anteprima sul solo articolo**, che è un uso previsto —
mentre `esigibilita`, calcolata dalla **stessa variabile**, usciva `'I'`, cioè
**«non scissa»**:

```
aliquota=22.00  esigibilita=I  split=NULL  norma=Aliquota I.V.A. al 22%
```

⛔ **Due campi che rispondono alla stessa domanda dicevano cose diverse sulla
stessa riga.** La causa è di una riga sola: `v_split := (v_split_sogg = 'S')` dà
`NULL` su un soggetto ignoto, ma il `CASE WHEN v_split THEN 'S' ELSE 'I' END`
subito sotto fa cadere quel `NULL` nell'`ELSE`. Chi consuma il composito ne
prende uno dei due, e i due consumatori si comportano diversamente.

**Corretto da `20260829-52`**: `v_split := ((v_split_sogg = 'S') IS TRUE)`.

⚠️ **E si allinea a `false`, non a `NULL`.** La simmetria opposta — rendere
ignota anche l'esigibilità — non è disponibile:
`vendite.fatture_righe.esigibilita` non ammette il nullo. Ci si allinea quindi al
valore che l'altra metà **già produceva**, e la coppia torna a dire una cosa sola.

⭐ Con `-52` caricato nella sua stessa transazione, il file passa **14/14** (13
verdi + lo skip dichiarato).

---

### ⛔ `D32` — `20260829-52` aveva corretto **nel verso sbagliato**, e la motivazione era falsa

`D31` aveva trovato la disparità fra `esigibilita` e `split_payment`, e l'aveva
chiusa allineandoli **verso il valore**. La motivazione scritta era:

> *«non si allinea verso il nullo perché `fatture_righe.esigibilita` non lo
> ammette»*

⛔ **È falsa.** `vendite.fatture_righe.esigibilita` è **nullabile**, e non ha
nemmeno un `CHECK` — ce l'ha la sola `fatture_riepiloghi_iva`. Quella frase non
era stata letta dal catalogo: era un ricordo, e ha deciso il verso di una
correzione fiscale.

⭐ **Il verso giusto è l'altro.** Senza il soggetto, il regime di scissione **non
è stato determinato**; rispondere «immediata, non scissa» non è prudente, è
un'**affermazione** su un documento che potrebbe andare a una PA. Ed è la
disciplina che il risolutore segue già: quando l'aliquota non si trova scrive
`origine = 'ASSENTE'` invece di tacere. **`20260829-53`** fa uscire entrambi i
campi `NULL` quando il soggetto non è noto.

ℹ️ Sul percorso vero (`I5`) il soggetto c'è sempre: il nullo esce solo nelle
**anteprime**, dove è esatto.

#### ⚠️ E il pgTAP aveva ereditato l'assunzione

Il caso 6, «il composito esce pieno», chiamava il risolutore **senza soggetto** e
pretendeva i campi valorizzati. Era stato scritto **insieme** alla correzione
sbagliata, e ne aveva ereditato la premessa — **cementandola**.

> Un test scritto nello stesso momento della correzione non la verifica: la
> ripete.

Corretto: la pienezza si prova sul percorso **con** il soggetto, e nasce il caso
**15**, che asserisce **la coppia** (`'NULL/NULL'`) e non i due campi separati —
il difetto non era «un campo nullo», era «due campi in disaccordo», e due
asserzioni separate sarebbero passate anche con la coppia rotta nell'altro verso.

---

### ✅ `I5` — la metà DB è fatta: adesso qualcuno **scrive** quelle due colonne

`esigibilita` e `split_payment` esistevano su riga e riepilogo, erano già nel
raggruppamento, ed erano **`NULL` su tutte le 37 righe**: non le riempiva nessuno.
Il brief la chiamava «voce corta» proprio per questo.

**`20260829-54`**: le riempie `trgfn_fatture_righe_guard_normalize`, derivandole
dal soggetto **cliente** (`D8`) — `fatture → billing_account → soggetti_ruoli →
soggetti`.

⚠️ **La domanda è del cliente, non dell'emittente.** Nella stessa funzione il
blocco 2 usa `emittente_soggetto_ruolo_id`, ma per un'altra domanda — lo stato
dell'emittente per l'override di aliquota. Due percorsi diversi, e non è una
svista.

#### ⭐ Perché il trigger e non il chiamante

Due motivi, e il secondo decide: il riepilogo **raggruppa** per
`(iva, natura, esigibilita, split)`. Se due righe della stessa fattura portassero
valori diversi, **la stessa aliquota si spezzerebbe in due riepiloghi** e la
fattura direbbe due cose sul proprio regime. Derivandoli dall'unico cliente della
testata, sono costanti per costruzione.

#### ⚠️ Le due metà si comportano diversamente, **apposta**

| Campo | Regola | Perché |
| --- | --- | --- |
| `split_payment` | **si riscrive sempre** | derivazione pura: non esiste una scelta legittima per riga |
| `esigibilita` | `'S'` **imposta** con la scissione; fuori da lì riempie **solo il vuoto** | `'D'` (differita) è una **scelta del documento** che nessuna colonna sa dedurre — sovrascriverla la cancellerebbe **senza un errore** |

#### La coda: `20260829-55`, l'asimmetria che si vedeva solo adesso

`fatture_riepiloghi_iva.esigibilita` aveva un `CHECK`; `fatture_righe` **no**. Ma
il riepilogo si costruisce **dalle righe** copiando il valore. Un valore fuori
dominio entrava sulla riga, restava finché nessuno rigenerava, e poi faceva
esplodere il ricalcolo con una violazione grezza — **su un'altra tabella, in un
altro momento**. Innocuo finché la colonna era `NULL` ovunque; `-54` ha appena
creato **il primo scrittore**, e il secondo (il backend) non avrebbe avuto
recinto.

⭐ Il `NULL` resta ammesso ed è una decisione: significa «non determinato», ed è
ciò che il trigger scrive di proposito quando il cliente non si risolve (`D32`).

#### Le prove

`db/pgtap/vendite/test-fatture-righe-esigibilita-split.sql`, **8/8 al primo
giro**. E provato **per mutazione**, che è ciò che distingue un presidio da una
decorazione:

| Mutazione | Cosa si rompe |
| --- | --- |
| i due rami dell'esigibilità si «uniformano» | **solo** il caso 4 — la `'D'` scelta sparisce |
| `split_payment` diventa «riempi solo il vuoto» | il caso 6 **e il 7** — e il 7 è la dimostrazione della sede: il riepilogo si spezza in due |

📌 **Resta al BE**: `I3` (la riga di documento chiama il risolutore, e il FE
smette di fare l'auto-fill) e `I4` (la riga di fattura smette di rileggere
`art.iva_id` in `pipeline_repository.py`). ⚠️ Verificato: **nessuna funzione DB
inserisce in `vendite.fatture_righe`** — quelle due voci sono interamente
backend, e la metà DB che le riguardava è quella appena chiusa.

---

## 8-sexies. ⭐ Stato al 2026-08-30 — **il DB di questo cantiere è chiuso**

> Letto da `databasechangelog`, non ricordato: **51 changeSet su 51 applicati**,
> dal `20260829-01` al `20260829-55`. Nessun file scritto è rimasto fuori.

### Le quattro fasi

| Fase | Voci | Stato |
| --- | --- | --- |
| 1 — sgombero | `I0` · `I8` · `I9` · `I10` | ✅ applicata, entrambe le metà di `I0`/`I8` |
| 2 — le sedi | `I7` | ✅ applicata — titoli, ambiti, movimenti, plafond, RLS |
| 3 — il risolutore | `I2` · `I5` (metà DB) | ✅ applicate |
| 3 — i consumatori | `I3` · `I4` | 🟢 **sbloccate**, ma sono **BE/FE**: niente da fare lato DB |
| 4 — la chiusura | `I6` | ⛔ **per ultima**, e dopo `I3`/`I4`. BE + FE |

> ### ✅ Un residuo trovato **dalla documentazione**, e chiuso in giornata

> `I10` aveva spostato la soglia di congelamento su
> `config.stati_doc_fiscale.congela_fiscale` con questa motivazione: *«chiunque
> scriva un secondo consumatore la ricopia»*. ⚠️ Ma era stato portato a leggerla
> **un solo** consumatore: le altre **sette** ricopiavano ancora, e le due
> peggiori erano **le guardie di congelamento stesse**.
>
> ⭐ **Rilievo di Tid che ha corretto la mia analisi**: avevo indicato come caso
> pericoloso «`EMESSA` che diventa congelante». È **impossibile** —
> `EMESSA → DRAFT` è una transizione **ammessa**, il confine è `DEFINITIVA`. Il
> difetto restava, il modo in cui l'avevo descritto no.
>
> ✅ **Chiuso il 2026-08-30 (`D33`)**: sette changeSet, `20260830-01`…`-07`.

⛔ **`I4` non è più «DB + BE».** Verificato sul catalogo: **nessuna funzione del
database inserisce in `vendite.fatture_righe`** — le righe le costruisce
`pipeline_repository.py`. La metà DB che le competeva era l'aliquota
storicizzata e la coppia esigibilità/split, e sono entrambe fatte.

### Cosa è stato costruito nella coda del risolutore

| # | Cosa |
| --- | --- |
| `20260829-44` · `-45` · `-46` | il predicato «contratto attivo» **estratto**, il pricing che lo chiama, l'anello al tipo d'uso |
| `20260829-47` · `-48` | `is_reverse_charge` e `e_cessione_beni` diventano **dati** (`D22`, `D23`) |
| `20260829-49` · `-50` | la logica italiana e **il guscio che smista** (`D21`) |
| `20260829-51` | ⛔ corregge `-41` (`D30`) |
| ~~`20260829-52`~~ | ~~allinea la coppia esigibilità/split~~ — ⛔ **superato da `-53`**: verso sbagliato |
| `20260829-53` | ⭐ la coppia dice «non lo so» quando non lo sa (`D32`) |
| `20260829-54` · `-55` | `I5` metà DB: chi **scrive** esigibilità e split, e il `CHECK` che mancava |

### I presidi che questo cantiere lascia

| File | Casi |
| --- | --- |
| `db/pgtap/vendite/test-fn-resolve-iva-riga.sql` | 15 — i due stadi, i due versi di `D17`, il composito, la spezzatura del plafond, l'ambiguità che solleva, il guscio che smista |
| `db/pgtap/vendite/test-fatture-righe-esigibilita-split.sql` | 8 — e **due mutazioni rilevate** |
| `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` | 23 |
| `db/pgtap/anagrafiche/test-soggetti-titoli-iva-due-emittenti.sql` | 5, runner `owner` con motivo scritto |
| `db/pgtap/vendite/test-cleanup-fattura-copertura-figlie-v1.sql` | 11 — **adeguato**: due voci nuove e il runner passato a `owner` |

### ⚠️ Tre difetti trovati **dai presidi**, non da una rilettura

E vale la pena tenerne il conto, perché è la misura di quanto servono:

1. **`D30`** — `-41` faceva vincere lo snapshot sulle bozze, cioè l'opposto di
   quel che serviva. Trovato dal caso 7 di `test-ricalcola-riepiloghi-iva`. ⭐ La
   conseguenza era **già scritta** nel commento di `-40`, dallo stesso giorno.
2. **`D31`** — `split_payment` usciva `NULL` mentre `esigibilita`, dalla stessa
   variabile, diceva «non scissa». Trovato dal caso 6 del pgTAP di `I2`, **al
   primo giro**.
3. **`D32`** — `D31` era stata corretta nel **verso sbagliato**, con una
   motivazione **falsa** letta a memoria invece che dal catalogo. ⚠️ E il caso 6
   del pgTAP, scritto insieme a quella correzione, **ne aveva ereditato la
   premessa**: *un test coevo alla correzione non la verifica, la ripete*.

### 📌 Residui dichiarati, verificati il 2026-08-30

| Residuo | Stato verificato |
| --- | --- |
| indici FK sulle colonne di ambito | ✅ **il «no» è confermato**: `I2` entra dal titolo, non dall'articolo — decisione verificata, non rinvio |
| `config.iva_stati` non storicizzabile | ✅ chiuso da `-42` (chiave surrogata) |
| il `MAX` che collassa sul riepilogo | 📌 resta scritto, ma **`D27` lo rende irraggiungibile**: il lock su `config.iva.aliquota_iva` toglie il caso |
| `script.fn_get_iva_override` | ⛔ **ancora rotta e ancora lì**: pretende `config.iva.assoggettamento_iva`, che **non esiste**. ⭐ Ma ha **zero chiamanti** — è codice morto che fallirebbe se qualcuno lo svegliasse. Va **ritirata**, non riparata |
| lista dei «titoli sfondati» | 📌 non esiste ancora |
| i tre tipi diversi da `INTENTO` senza un `config.iva` | 📌 invariato, e resta giusto: non se ne conia nessuno al buio |
| `fatture_righe.contratto` (snapshot di `D9`) | 📌 va con `I4`, cioè col backend |
| ✅ ~~la soglia di congelamento non è unica~~ | **CHIUSO il 2026-08-30 con `D33`**: tutte e sette portate a leggere `congela_fiscale` (`20260830-01`…`-07`), con presidio pgTAP che le tiene |

### ⛔ Cosa NON è chiuso, e non lo chiude il DB

`I3`, `I4` e `I6` sono **interamente backend e frontend**. Il DB ha finito: c'è
una funzione sola da chiamare, `vendite.fn_resolve_iva_riga`, che ritorna il
composito e smista per paese.

⚠️ **E `I6` resta per ultima**, per il motivo che il §5 già scrive: toglie
all'operatore l'ultima uscita manuale, e applicata prima che le righe nascano
con l'aliquota giusta cementerebbe i valori sbagliati di oggi.

---

## 8-septies. ✅ `D33` — la soglia di congelamento ha **una sede sola**

> Nato da una domanda di Tid sul residuo trovato documentando: *«a naso mi sembra
> una cosa importante da risolvere»*. Lo era.

### Il fatto

«Da che punto in poi un documento fiscale non si tocca più» è **una** domanda.
Era scritta in **otto posti**: la colonna `congela_fiscale` (letta da un solo
consumatore) e sette liste `NOT IN ('DRAFT','EMESSA')` dentro altrettante
funzioni.

⛔ **Le due copie peggiori erano le guardie di congelamento stesse.**

### ⭐ La correzione di Tid, che ha cambiato l'analisi

Avevo indicato come scenario pericoloso *«qualcuno decide che anche `EMESSA`
congela»*. Tid ha fatto notare che **il confine è `DEFINITIVA`**, perché da
`EMESSA` si torna in bozza. Verificato: `EMESSA → DRAFT` è una transizione
**ammessa** su `config.stati_doc_fiscale_transizioni`, e `DEFINITIVA` non ha
ritorno.

⚠️ Quindi lo scenario che avevo descritto **non era improbabile: era
impossibile**. Il difetto restava — otto copie di una regola — ma il modo in cui
l'avevo raccontato no.

### Cosa è stato fatto

| # | Funzione | Nota |
| --- | --- | --- |
| `20260830-01` | `trgfn_fatture_righe_guard_congelamento` | ⛔ la guardia sulle righe |
| `20260830-02` | `trgfn_fattura_satellite_guard_congelamento` | ⛔ la guardia sui satelliti |
| `20260830-03` | `fn_genera_scadenze_fattura` | ⚠️ ramo «stato ignoto» permissivo, **lasciato com'era** |
| `20260830-04` | `fn_genera_scadenze_lotto` | qui la soglia **filtra**, non solleva |
| `20260830-05` | `fn_snapshot_fattura_lotto` | diceva già «soglia identica al guard»: ora lo è **davvero** |
| `20260830-06` | `fn_check_fattura_eliminabile_da_lotto` | **due** copie in una funzione sola |
| `20260830-07` | `fn_check_lotto_riportabile_a_draft` | è la funzione che *rende vero* il ritorno da `EMESSA` |

### ⚠️ Due cose che NON sono state fatte, di proposito

1. **Lo stato mancante resta trattato funzione per funzione**, e non allo stesso
   modo: alcune lasciano passare, altre bloccano. Uniformarlo sarebbe giusto in
   sé, ma sarebbe un **cambiamento di comportamento nascosto** dentro un lavoro
   di sede. Ogni `COALESCE` e ogni `IS TRUE` è scelto per **conservare** il ramo
   esistente, e ognuno lo dice nel commento.
2. **Non è stata separata «numerato» da «congelato».** Due funzioni descrivono il
   confine come «non ancora numerato». Oggi è lo stesso evento — il numero si
   prende a `DEFINITIVA`, che è anche il primo stato che congela — e per il
   dominio *è* lo stesso evento. ⭐ Se un domani si staccassero, quella è la
   riga da cui ripartire, ed è segnalata nel changeSet.

### Le prove

* **zero** copie eseguibili rimaste, **otto** funzioni leggono la colonna;
* ⭐ **equivalenza misurata su tutti e sei gli stati**: la vecchia frase e la
  nuova danno la stessa risposta. Il comportamento non si sposta di un caso;
* ⭐ **il guard segue la colonna in entrambi i versi**: spostata a `true`
  rifiuta, rimessa a `false` riaccetta — che è ciò che distingue «legge la
  colonna» da «per caso oggi la lista dice lo stesso».

### 🔒 Il presidio

`db/pgtap/config/test-soglia-congelamento-sede-unica.sql`, 4 casi.

⚠️ **Il caso 2 non è un doppione del 1**: senza, il test 1 diventerebbe verde
anche *cancellando* la soglia da una funzione invece di spostarla — cioè
togliendo una difesa invece di trasferirla.

⭐ **Provato per mutazione senza doverla costruire**: lanciato sul database
prima dell'apply è **rosso**, nomina tutte e sette, e il caso 3 dimostra che il
guard non seguiva la colonna.

---

## 8-octies. ✅ `D34` — le due guardie di congelamento diventano **una**

> Nato dalla domanda di Tid dopo `D33`: *«ma le sette funzioni sono simili, hanno
> senso di esistere o sono duplicazioni?»*. La risposta è **diversa per due
> gruppi**, e l'ho misurata invece di stimarla.

### La misura

Somiglianza a coppie sul corpo **senza commenti** (i commenti gonfiano il
confronto e non sono codice):

| Coppia | Somiglianza | Verdetto |
| --- | --- | --- |
| le due **guardie** di congelamento | **0.63** | ⛔ è la stessa funzione |
| `fn_genera_scadenze_lotto` ↔ `fn_snapshot_fattura_lotto` | **0.70** | 🟡 candidato, **non fatto** |
| tutte le altre coppie | 0.11 – 0.31 | ✅ lavori diversi, nessuna duplicazione |

⭐ **Cinque delle sette non erano duplicazioni**: due rifiutano, due generano il
piano rate, una fa lo snapshot, due elencano motivi ostativi. Condividevano
**una frase**, ed è quella che `D33` ha centralizzato.

### ⛔ Le due guardie erano la stessa funzione, e le date lo spiegano

Messe una accanto all'altra differiscono in **due punti**:

* come trovano la fattura — `NEW.fattura_id` scritto fisso, contro
  `to_jsonb(NEW) ->> TG_ARGV[0]`, cioè **la colonna gliela dici tu**;
* il codice errore.

Tutto il resto — bypass via GUC, lettura dello stato, ramo dello stato mancante,
ritorni — è **identico riga per riga**.

⭐ La versione sulle righe è del **28 luglio**, la generica del **30 luglio**, ed
è già montata su tre tabelle. La generica è la generalizzazione scritta due
giorni dopo, e **nessuno è tornato indietro a riassorbire la prima**. Non era una
duplicazione voluta: era un lavoro lasciato a metà.

### ⚠️ La cosa che si perde fondendo, e che è il vero soggetto

**Il codice errore.** Se le righe si prendessero `E_FATTURA_SATELLITE_CONGELATO`
il database continuerebbe a rifiutare la scrittura — quindi **niente sembrerebbe
rotto** — ma il backend commuta su quel codice e vedrebbe arrivare un errore che
non è il suo. Un difetto che non fa rumore.

#### ⛔ E qui ho ribaltato una decisione scritta, senza saperlo

Il manuale della guardia generica conteneva questa, del 2 agosto:

> *«Il piano prevedeva un secondo `TG_ARGV` col codice errore per tabella. È stato
> **scartato**: due argomenti dove ne basta uno sono due posti in cui sbagliare il
> montaggio, e `error_policies.py` mappa comunque **un codice solo**.»*

⚠️ **La premessa era vera quando è stata scritta e non lo è più.** Verificato: il
backend mappa **due** codici, con messaggi diversi per l'operatore — «non
consente più di modificare **le righe**» contro «…**questi dati**».

⭐ Ed è proprio quella premessa a rendere il parametro **necessario**: senza,
fondendo, le righe si sarebbero prese il messaggio generico e nessuno se ne
sarebbe accorto, perché il rifiuto sarebbe arrivato lo stesso. L'argomento
originale resta valido e si paga volentieri: il secondo argomento è
**opzionale**, i tre montaggi esistenti non cambiano, e in cambio sparisce
un'intera funzione duplicata. La decisione vecchia è **marcata come ribaltata**
nel manuale, con il perché.

`20260830-08` insegna alla generica il codice come **`TG_ARGV[1]`**, opzionale:
`TG_ARGV` fuori range dà `NULL`, quindi i tre trigger già montati **non si
toccano**. `20260830-09` rimonta le righe sulla generica e **toglie** la funzione
dedicata.

#### ⚠️ L'arità dei messaggi, che era la trappola

```
E_FATTURA_RIGA_CONGELATA       2 segnaposto   «Fattura %s in stato %s: le righe…»
E_FATTURA_SATELLITE_CONGELATO  3 segnaposto   «Fattura %s in stato %s: %s non è…»
```

La funzione ne passa **tre sempre**. Misurato che `format()` **ignora gli
argomenti in più**: il messaggio a due segnaposto esce corretto. È il verso
opposto — meno valori dei segnaposto — che rompe, e non capita.

#### ⚠️ E il nome del trigger non cambia

Resta `trg_fatture_righe_a10_guard_congelamento_ins_upd_dlt`. I `BEFORE ROW`
scattano in **ordine alfabetico**: rinominarlo lo sposterebbe rispetto agli altri
`a10` sulla stessa tabella. Un cambio di nome qui sarebbe **un cambio di
comportamento travestito da pulizia**.

### Le prove

`db/pgtap/vendite/test-guard-congelamento-fusione-v1.sql`, 5 casi.

⭐ **La forma dei rossi è la dimostrazione**: lanciato sul database *prima* della
fusione, falliscono **solo il 1 e il 2** — quelli strutturali — mentre il **3, il
4 e il 5** (i comportamenti: messaggio delle righe, messaggio dei satelliti,
scrittura sotto soglia) **passano già**. Il comportamento non cambia: cambia chi
lo produce.

⚠️ **Il caso 4 non è ornamentale**: senza, un parametro sbagliato al contrario —
il codice delle righe passato a tutti — lascerebbe verde il caso 3.

⚠️ Adeguato anche il presidio di `D33`: l'elenco esplicito passa da **otto a
sette** funzioni, con scritto **perché** una è sparita — «riassorbita», non
«dimenticata». Un elenco che cala senza spiegazione è il modo in cui un presidio
smette di presidiare.

### ⛔ La documentazione di un oggetto ritirato **si cancella**

Rilievo di Tid, e correggeva una mia scelta sbagliata: avevo lasciato un
«moncone di ritiro» in `docs/it/dbzero/vendite/manual/`, ragionando che chi
arriva da un vecchio link meriti una spiegazione.

⚠️ **Ma `scripts/gen_db_docs.py` costruisce `index.ci.md` scansionando la
cartella `manual/`**: un file che resta continua a comparire nell'indice della
documentazione, e l'indice smette di essere l'elenco di ciò che c'è.

⭐ **La regola dei brief — «si marca, non si cancella» — vale per i brief, non
per `manual/`**, e la differenza è la sede: un brief è un racconto con una
storia, `manual/` è il catalogo di ciò che esiste **ora**.

ℹ️ La spiegazione del ritiro non si perde, **cambia sede**: sta nel `manual/`
della guardia che ha preso il posto («è stata riassorbita qui, ecco perché») e in
questa sezione.

---

### 📌 Richiesta al BACKEND (perimetro DB, non si tocca) — raccolta anche al **§8-nonies**

Due **commenti** nominano la funzione che sparisce:

| File | Riga |
| --- | --- |
| `backend/apps/vendite/api/fatture_views.py` | 9 |
| `backend/apps/vendite/db/note_repositories.py` | 89 |

⭐ Verificato: sono **solo commenti**, nessuna dipendenza funzionale — il codice
non chiama né nomina la funzione. Ma diventano falsi. Il nome nuovo è
`vendite.trgfn_fattura_satellite_guard_congelamento`, e la protezione delle righe
**non è cambiata**: stesso codice errore, stesso messaggio, stesso bypass.

### 🟡 Cosa NON è stato fatto, e perché

I due **wrapper di lotto** (somiglianza 0.70) restano due. Sono lo stesso schema
— *scegli le fatture lavorabili, cicla, chiama la funzione per-fattura, logga,
conta gli scarti* — ma estrarli costa più che nelle guardie: la funzione
per-fattura andrebbe invocata dinamicamente, e i due ritorni non coincidono.

```
scadenze : fatture_count, deleted_rows, inserted_rows, skipped_rows, skipped_errore_rows, failed_rows
snapshot : fatture_count, inserted_rows, updated_rows, intestazioni_scritte, skipped_rows, failed_rows
```

📌 Con **due** istanze il guadagno è dubbio. **Alla terza si estrae**, ed è
scritto qui perché la terza si riconosca.

---

## 8-nonies. 📌 TUTTO CIÒ CHE RESTA AL BACKEND — l'elenco unico

> ⚠️ **Perché questa sezione esiste.** Le richieste al backend erano scritte
> **dove nascevano**, cioè sparse in quattro punti diversi di questo documento più
> le righe della tabella del §5. Ognuna era corretta e motivata nel suo contesto,
> e messe insieme non si vedevano: chi apre il brief per sapere «cosa devo fare
> io» doveva leggerlo tutto.
>
> ⛔ **Questa sezione NON sostituisce quei punti**: là c'è il ragionamento, qui
> c'è solo l'elenco con il rimando. Duplicare la motivazione la farebbe divergere.

### 1. `I3` — la riga di documento chiama il risolutore · **BE + FE**

Il backend chiama `vendite.fn_resolve_iva_riga` alla creazione della riga; il
frontend **smette** di fare l'auto-fill e mostra il risultato.

⚠️ **La sede del risolutore è UNA.** Se il DB lo espone, il BE lo chiama e il FE
continua col suo `onArticoloSelect`, ci sono **due** risposte alla stessa domanda
— cioè il difetto di oggi con un pezzo in più. L'auto-fill va **sostituito**, non
affiancato. → §2.5.1

### 2. `I4` — la riga di fattura smette di rileggere l'articolo · **solo BE**

`pipeline_repository.py` proietta `art.iva_id`: da lì la fattura ri-legge l'IVA
dall'articolo invece di ri-risolverla. ⚠️ **Breaking change dichiarato.**

⭐ Verificato: **nessuna funzione del database inserisce in `vendite.fatture_righe`**
— la metà DB di questa voce non esiste. → §1.2, §2.5.2

Si porta dietro due cose:

* la colonna **`fatture_righe.contratto`** (snapshot di `D9`): la sede è la
  **riga** e non la testata, perché una fattura può mescolare più contratti;
* ⛔ **l'ordine deterministico del consumo di plafond**, che è la metà di
  `D15-bis` che il DB non può tenere: il giro di lotto deve iterare
  `ORDER BY data documento, numero`. Un lock non può sapere che esiste una
  fattura precedente non ancora arrivata. → §8-ter

### 3. `I5` — resta il payload SDI · **solo BE**

✅ La metà DB è fatta: riga e riepilogo portano `esigibilita` e `split_payment`,
riempiti dal trigger. Resta portarli nel payload FatturaPA (`EsigibilitaIVA`).

### 4. `I6` — la casella IVA si chiude · **BE + FE**, ⛔ **per ultima**

* **BE**: `iva_id` fuori da `_UPDATE_KEYS_RIGA` **e** da `_CREATE_KEYS_RIGA` in
  `ddt_service`, `ordini_service`, `preventivi_service` (in `preventivi_service`
  è una tupla inline, non una `frozenset`);
* **FE**: `<IvaSelect>` disabilitata **anche in CREATE** nei tre `*RigaForm.vue`.
  ⚠️ In `PreventiviRigaForm` il `canSave` pretende `f.iva_id`: va ripensato, o la
  creazione si blocca da sola.

⛔ **Non prima di `I3`/`I4`**: toglie all'operatore l'ultima uscita manuale, e
applicata prima che le righe nascano con l'aliquota giusta **cementerebbe i
valori sbagliati di oggi**. → §5

### 5. Le sei chiavi tolte da `clienti` — **da fare adesso** · BE + FE

⛔ Dal changeSet `-15` un payload che contiene una delle sei chiavi **non viene
respinto: viene ignorato in silenzio**. L'operatore salva, non vede errori, e il
valore non va da nessuna parte. L'elenco file-per-file, con le righe, è al
**§8-bis** — non si ricopia qui.

### 6. 🆕 Tre riferimenti diventati falsi con `D34` — **solo commenti e doc**

`vendite.trgfn_fatture_righe_guard_congelamento` **non esiste più**: riassorbita
dalla guardia generica.

| File | Riga | Cos'è |
| --- | --- | --- |
| `backend/apps/vendite/api/fatture_views.py` | 9 | commento |
| `backend/apps/vendite/db/note_repositories.py` | 89 | commento |
| `docs/it/backend/vendite/manual/api_fattura_dettaglio.md` | 159 | doc del backend |

⭐ **Nessuna dipendenza funzionale** — verificato, il codice non la chiama. Il
nome nuovo è `vendite.trgfn_fattura_satellite_guard_congelamento`, e per chi usa
il sistema **non cambia niente**: stesso trigger, stesso codice errore
`E_FATTURA_RIGA_CONGELATA`, stesso messaggio, stesso bypass GUC.

---

### ✅ Cosa il backend NON deve fare

Vale la pena scriverlo, perché sono le domande che tornano:

* **non deve calcolare l'IVA**: c'è una funzione sola, e ritorna un composito
  già completo (aliquota, natura, reverse charge, esigibilità, split,
  riferimento normativo, origine);
* **non deve decidere esigibilità e split** sulla riga di fattura: li scrive il
  database dal soggetto cliente;
* **non deve conoscere la soglia di congelamento**: è un dato,
  `config.stati_doc_fiscale.congela_fiscale`, e il database la applica.

---

---

## 9. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-27 | Nascita del brief dalla domanda di Tid sul collaudo delle righe DDT senza prezzo. Quattro voci, `D1`…`D5`, poi `D6` in giornata (due stadi) — che senza dirlo rendeva `D2` priva d'oggetto |
| 2026-08-28 (mattina) | ✅ `I1` **applicata** fuori da questo brief, dalla Fase C di `brief-db-ddt-riconsegna-eredita-testata`: `E_DDT_RIGA_IVA_MANCANTE`, e con il discrimine sul **prezzo** invece che sulla causale (`R-1`) |
| 2026-08-28 (Rev 2) | Rilettura critica con Tid, partita dal suo dubbio: *«avevo dato prioritaria l'IVA su soggetto rispetto all'articolo, credo debba essere il contrario»*. ⛔ **`D2` superata da `D7`**: non c'era una precedenza da invertire, c'erano due domande diverse. Verificati sulla doc auto-gen quattro fatti che il documento dava per veri (§R): `I1` già fatta, il pgTAP del §6 sbagliato, il gate mancante su ordini/preventivi, `fn_get_iva_override` **rotta**. Trovato che l'anello «uso fornitura» **esisteva già** (`config.tipi_utenze`, `D11`) e che l'aliquota **cavalca già la catena del prezzo** in tre tabelle mai lette |
| 2026-08-28 (Rev 2, seguito) | Partendo dalle colonne che Tid aveva messo sul cliente *«perché potevano essere diverse per utility»*: ⭐ **non erano un gruppo solo**. `clienti.iva_id` **si toglie** (`D7-bis`), `split_payment`/`cliente_pa` salgono su **`soggetti`** (`D8`), CIG/CUP/commessa vanno al **contratto** con snapshot in fattura (`D9`) — voce che nel brief non c'era |
| 2026-08-28 (Rev 2, rilievi di Tid sul racconto) | Due precisazioni nate dal §8. ⚠️ **`D12`**: lo stadio B si valuta **per riga**, e l'ambito è la **condizione di applicabilità** — un titolo ristretto a due articoli non agevola le altre otto righe. Il rischio che Tid ha visto (*«si applica a tutto»*) era nel racconto, non nel disegno, ma senza l'ambito il titolo sarebbe stato il `clienti.iva_id` appena tolto. ❓ Ne esce **`D13` APERTA**: due titoli di tipo diverso sulla stessa riga — proposta «vince il più specifico», da verificare sul merito fiscale. ✅ **`D14`**: la differenza documento/fattura è **temporale, non di natura** — stessa funzione, due momenti; quindi la **data è un parametro** e il risolutore è in **sola lettura** |
| 2026-08-28 (Rev 2, il congelamento) | ✅ **`D13` chiusa**: vince il più specifico — ma Tid smonta l'esempio che la motivava (intento è su **partita IVA**, disabilità su **codice fiscale**: non convivono). Resta scritta come presidio, perché `soggetti` porta entrambi gli identificativi e una ditta individuale li ha tutti e due. ⛔ **`D15`, ed è una correzione mia**: una **ristampa non fa girare il risolutore** — il calcolo si ferma alla **DEFINITIVA** e da lì il documento è uno snapshot. L'argomento che avevo usato per `D14` («ristampare darebbe un numero diverso») era sbagliato: **ritirato**, la conclusione regge sulla **data documento**. ⭐ Scoperto che la soglia **esiste già** in `fn_ricalcola_riepilogo_iva_fattura` (`NOT IN ('DRAFT','EMESSA')`) ma è **hardcoded**, e che le tre scorciatoie disponibili — `fase`, `ordine`, `chiude_lotto` — sono tutte e tre sbagliate. **`D15-bis`**: il plafond si consuma **nella stessa transizione**, atomica, con lock e ordine deterministico |
| 2026-08-29 | ✅ Tid conferma i consigli aperti. Diventano decisioni: **`congela_fiscale`** su `config.stati_doc_fiscale` con il porting di `fn_ricalcola_riepilogo_iva_fattura` (→ **`I10`**), e il **lock + ordine deterministico** sul consumo del plafond dentro `I7`. Aggiunto l'**ordine consigliato** delle voci: `I0`/`I8`/`I9`/`I10` subito e in parallelo, poi `I7`, poi `I2` con la sua coda, `I6` per ultima |
| 2026-08-29 (costruzione) | ⛔ **`I10` applicata**, e con essa una trappola trovata per caso: il mirror del CSV degli stati fattura dichiarava **10 colonne su 13** — `fase`, `is_abortito` e `congela_fiscale` non erano governate dal CSV, e nessuno se ne sarebbe accorto. Ri-ancorato (`20260829-05`). ⛔ **Corretta una mia decisione del brief**: `congela_fiscale` nasce `DEFAULT true`, non `false` — il `NOT IN` congelava d'ufficio ogni stato nuovo, ed **era la direzione sicura**. ✅ **`I9` ordini applicata**: una regressione mia su un pgTAP esistente (fixture senza `iva_id`), corretta; ⚠️ e la lezione utile non è «fai il grep» ma **quale** grep — sul nome della tabella escono 44 file, sulle **liste di colonne degli `INSERT`** ne escono 6, e uno solo regrediva |
| 2026-08-29 (preventivi) | ⛔ **La premessa del §R-3 era sbagliata**, e si è visto solo provando: sui preventivi la riga senza aliquota **non si salva nemmeno**, perché `fn_get_aliquota_iva` **solleva** su NULL e il `COALESCE` che sembrava una guardia non poteva intervenire. Non era una decisione di dominio ma una **svista** — le viste gemelle la guardia ce l'hanno. ✅ Guardia + cancello all'emissione applicati **come slice unica**. ⚠️ La gemella sulle **fatture** ha lo stesso difetto e **non è stata toccata**: lì manca il cancello, e togliere il raise scambierebbe un errore rumoroso con un numero sbagliato silenzioso → legata a `I4`. ⭐ Lo sweep dei test esistenti stavolta **prima**: 27 file, 3 rossi tutti già in baseline, zero regressioni |
| 2026-08-29 (`I8`/`I0`) | Scritta la metà **additiva** di entrambe: i tre codici sul **contratto**, `split_payment`/`cliente_pa` sul **soggetto** con travaso `bool_or` (vince `'S'`) e `CHECK ('S','N')`. ⭐ **Il §`D9` sbagliava sul lato fattura**: `fatture_righe` porta una sorgente **per riga** fra 15 tipi, quindi una fattura **può mescolare più contratti** — la sede è la **riga**, non la testata, e la colonna si aggiunge con `I4` insieme a chi la riempie, per non creare l'ennesimo campo scritto e mai letto. ⛔ Le due metà che **tolgono** sono gated sul BE, con la richiesta puntuale nel §8-bis |
| 2026-08-29 (`I0-B`/`I8-B`) | ✅ Su autorizzazione esplicita di Tid, le sei colonne **spariscono** da `anagrafiche.clienti` in tre passi ordinati (chi scrive → chi legge → il DROP). ⛔ **Quattro dipendenze censite prima di toccare**, e la peggiore non si vedeva: `trg_iva_a10_clienti_block_deact_upd` su `config.iva` nomina la colonna come **stringa**, quindi PostgreSQL non ha nessuna dipendenza da invalidare — sarebbe sopravvissuto al DROP per fallire a **runtime**, su un'altra tabella, alla prima disattivazione di un codice IVA. ⭐ E una quinta cosa che avrebbe ucciso il migrate successivo: la riga di `dbops.fk_index_policy`, che avrebbe fatto indicizzare una colonna inesistente al prossimo `90_end`. ⭐ Due pgTAP adeguati, e il secondo non è un rattoppo: la prova di **atomicità** di `fn_update_cliente` era costruita sulle chiavi rimosse — la proprietà resta, cambia il veicolo, e ne è uscita **più precisa** (SQLSTATE `23503` invece di «un errore qualsiasi») |
| 2026-08-29 (chiusura del disegno) | ✅ **`D1` DECISA: l'IVA di riga non è modificabile a mano**, in CREATE e in EDIT. L'argomento contro era caduto con `D10` — i titoli si registrano, non si digitano — e non restava nessun caso per-operazione fuori dal risolutore. ⚠️ Verificato lo stato reale prima di deciderla, ed era **mezzo bloccata**: campo grigio in EDIT nei tre form, libero in CREATE, e **API aperta in tutti e tre i casi** (`iva_id` nelle chiavi di update di `ddt_service`, `ordini_service`, `preventivi_service`). Non proteggeva e impediva lo stesso. `I6` diventa concreta e a **due metà** (BE + FE), e resta **per ultima**. ⭐ Il §5 diventa un **processo in quattro fasi**. **Nessuna decisione resta aperta: il brief è completo lato disegno, e niente è ancora applicato** |
| 2026-08-29 (Fase 2, `I7`) | ✅ **Le sedi dei titoli scritte**, dodici changeSet + due pgTAP, niente applicato (§8-ter). ⭐ Tre decisioni di forma prese con Tid prima di scrivere: l'anti-sovrapposizione è un `EXCLUDE` **vero solo su `ambito = 'TUTTO'`** e un guard sui ristretti — la chiave attraversa una tabella figlia e un vincolo non la può leggere; la **RLS si accende subito**, su tabelle che nascono vuote; il codice della natura N3.5 è **`NI35`**, e da oggi quella natura non è più orfana. 🔴 Il guard dell'ambito sta su **due** trigger: due titoli diventano sovrapposti anche quando cambia il **padre**, e in quei casi la figlia non viene toccata — la regola sta in una funzione pura che entrambi **chiamano**. ⛔ Di `D15-bis` il DB dà **una metà**: il lock c'è, l'**ordine deterministico è del chiamante** e diventa una richiesta al BE per `I4` — un lock non può sapere che esiste una fattura precedente non ancora arrivata. ⭐ E una riga del §8-bis è stata **corretta misurando invece di ragionare**: «una colonna fuori dalla lista del mirror non è governata dal CSV» è **falsa** su Liquibase 5.0.3 — il blocco `columns:` configura i tipi, non restringe il caricamento. La promessa di `D15` era già vera, e `20260829-05` va riletto come una pulizia. |
| 2026-08-29 (Fase 2 applicata) | ✅ **`I7` applicata** (Tid). Baseline `anagrafiche` e `script` verdi, nessuna regressione — e siccome girano come applicazione, il limite della corsa pre-apply (owner, RLS non esercitata) **si chiude da sé**. ⭐ Da qui in poi `I2` non ha più prerequisiti: lo stadio B ha una sorgente da leggere, ed è la Fase 3. |
| 2026-08-29 (Fase 3, disegno) | ⛔ **Il risolutore aperto e SOSPESO** su decisione di Tid (§8-quater), ma non a vuoto: verificato sulla struttura che l'aliquota accanto al prezzo esiste **solo sui componenti di bundle** — su una riga standalone listino, contratto e offerta non dicono niente sull'IVA, quindi la cascata da riprodurre **non esiste** e la domanda del §5 sull'ordine si dissolve. ✅ `D16` i bundle restano fuori, `D17` l'uso della fornitura entra **dove l'articolo tace** (l'articolo può dichiarare di non avere un'opinione, `tipi_utenze` no: applicato per primo si prenderebbe cauzioni e servizi). ⭐ Poi l'impostazione estesa di Tid, §8-quinquies: `D18` ritorno **composito** e non numerico, `D19` **risolvere in scrittura, leggere il congelato**, `D20` firma con il paese delle **due parti**, `D21` **guscio che smista** con l'`ELSE` che solleva — il dispatcher CF/PIVA quel ramo non ce l'ha e tace, `D22` reverse charge come flag, `D24` il riferimento normativo resta l'**identità della riga** di `config.iva`, `D25` niente versionamento delle tabelle. |
| 2026-08-29 (Fase 3, `I2` e la correzione) | ✅ **Il risolutore scritto**: `20260829-44`…`-50` — il predicato «contratto attivo» **estratto** (`D29`, 47 esiti di pricing identici dopo l'estrazione), `is_reverse_charge` e `e_cessione_beni` come **dati** (`D22`/`D23`), l'implementazione italiana e il **guscio che smista** con l'`ELSE` che solleva. ⛔ **Il ramo `TIPO_UTENZA` resta scoperto**: i contratti attivi stanno tutti su utility **senza dimensione tipo/classe**, e costruirla è vietato da `trgfn_contratti_utilities_guard_tipo_classe` — a ragione. Va coperto dal pgTAP di `I2`, che il soggetto se lo fabbrica. ⛔ Poi **due rossi**, e uno era mio: `20260829-41` faceva vincere lo snapshot sulle bozze, cioè **l'opposto** di quel che serviva, e la conseguenza era già scritta nel commento di `20260829-40` — corretto da `20260829-51` (`D30`). L'altro era il presidio della pulizia che **faceva il suo mestiere**: due voci nuove classificate `SCOPERTA_NOTA`, e il file passa a runner **owner** perché sotto RLS il suo unico conteggio era fail-closed. |
| 2026-08-29 (Fase 3, il pgTAP di `I2`) | ✅ **Il buco dichiarato è chiuso**: il test costruisce la fornitura — clona un contratto sulla utility che la dimensione ce l'ha, lo inserisce **già in `ATTIVO`**, e scopre che la riga di `contratti_utilities` **la crea un trigger** (si aggiorna, non si inserisce). 14 casi: i due stadi, i **due versi** di `D17`, il composito, la spezzatura del plafond con l'invariante della somma, l'ambiguità che **solleva**, e il guscio che smista. ⛔ E ha trovato **un difetto del risolutore al primo giro** (`D31`): `split_payment` usciva `NULL` su soggetto ignoto mentre `esigibilita`, calcolata dalla **stessa variabile**, diceva «non scissa» — due campi che rispondono alla stessa domanda, in disaccordo sulla stessa riga. Corretto da `20260829-52`. ⚠️ Un caso resta **skip dichiarato**: nessun codice IVA attivo porta una natura `N6`, e un'uguaglianza fra `false` e `false` sarebbe verde anche con il valore inchiodato. |
| 2026-08-29 (Fase 3, `I5` e la seconda correzione) | ⛔ **`D31` era stata corretta nel verso sbagliato**, e la motivazione era **falsa**: «`fatture_righe.esigibilita` non ammette il nullo» — quella colonna è **nullabile e senza `CHECK`**, e la frase non era stata letta dal catalogo. `20260829-53` mette il verso giusto: senza soggetto **entrambi** i campi escono `NULL`, perché «non scissa» sarebbe un'affermazione su un documento che potrebbe andare a una PA. ⚠️ E il pgTAP aveva **ereditato l'assunzione** — il caso 6 era stato scritto insieme alla correzione sbagliata e la cementava: *un test scritto nello stesso momento della correzione non la verifica, la ripete*. ✅ Poi **`I5`, metà DB**: `esigibilita` e `split_payment` erano `NULL` su tutte le righe perché **non le scriveva nessuno**. Ora le deriva il trigger dal soggetto **cliente** (`20260829-54`), e la sede è il trigger perché il riepilogo **raggruppa** per quei campi — due righe discordi spezzerebbero la stessa aliquota in due riepiloghi. ⭐ Le due metà si comportano diversamente **apposta**: `split` è derivazione pura e si riscrive sempre, l'esigibilità fuori dalla scissione riempie **solo il vuoto** perché la `'D'` è una scelta che nessuna colonna deduce. `20260829-55` chiude l'asimmetria del `CHECK`, invisibile finché la colonna era vuota. 8/8 e **due mutazioni rilevate**. |
| 2026-08-30 (chiusura DB) | ✅ **Applicato tutto**: 51 changeSet su 51, letti dal `databasechangelog`. Baseline `vendite` senza regressioni, doc auto-gen rigenerata. ⭐ **Il DB di questo cantiere è chiuso**: restano `I3`, `I4` e `I6`, che sono **interamente BE/FE** — e `I4` ha smesso di essere «DB + BE» perché è stato verificato che nessuna funzione del database inserisce in `vendite.fatture_righe`. 📌 Residui ripassati **verificandoli**, non ricordandoli: il «no» sugli indici di ambito è **confermato** (la query di `I2` entra dal titolo, come previsto — la previsione è stata messa alla prova invece che assecondata); `iva_stati` chiuso da `-42`; il `MAX` reso irraggiungibile da `D27`; ⛔ `script.fn_get_iva_override` **ancora rotta** (pretende `config.iva.assoggettamento_iva`, che non esiste) ma con **zero chiamanti** — va ritirata, non riparata. ⚠️ Il conto che vale la pena tenere: **tre difetti su tre li hanno trovati i presidi**, non una rilettura — e uno era una correzione precedente andata nel verso sbagliato per una motivazione letta a memoria invece che dal catalogo. |
| 2026-08-30 (`D33`, la soglia) | ⭐ **Chiuso il residuo trovato documentando**: la soglia di congelamento era scritta in **otto posti** — la colonna e sette liste di codici — e le due copie peggiori erano **le guardie di congelamento stesse**. Sette changeSet (`20260830-01`…`-07`) le portano tutte a leggere `congela_fiscale`. ⚠️ **Rilievo di Tid che ha corretto la mia analisi**: il confine è `DEFINITIVA`, non `EMESSA`, perché da `EMESSA` si torna in bozza — verificato, `EMESSA → DRAFT` è una transizione ammessa. Lo scenario che avevo descritto non era improbabile, era **impossibile**; il difetto restava, il racconto no. ⭐ Comportamento **invariato e misurato**: equivalenza su tutti e sei gli stati. ⚠️ E due cose NON fatte di proposito: lo stato mancante resta trattato funzione per funzione (uniformarlo sarebbe un cambiamento nascosto dentro un lavoro di sede), e «numerato» non è stato separato da «congelato». Presidio pgTAP a 4 casi, rosso prima dell'apply e con i nomi. |
| 2026-08-30 (`D34`, le guardie) | ⭐ Da una domanda di Tid — *«sono simili o sono duplicazioni?»* — e la risposta è **diversa per gruppo**, misurata: cinque delle sette non si somigliano affatto (0.11–0.31), ma **le due guardie di congelamento erano la stessa funzione** (0.63, e differenze in due punti soli). Le date lo spiegano: la generica è del 30 luglio, quella sulle righe del 28 — è la generalizzazione scritta due giorni dopo, mai riassorbita. ✅ Fuse: la generica impara il **codice errore** come `TG_ARGV[1]` opzionale (`20260830-08`) e le righe ci si montano sopra (`-09`). ⚠️ La trappola era l'**arità dei messaggi**, 2 contro 3: misurato che `format()` ignora gli argomenti in più. E il nome del trigger **non cambia**, perché i `BEFORE ROW` scattano in ordine alfabetico. ⭐ La prova più bella è la forma dei rossi: prima della fusione falliscono **solo i due casi strutturali**, mentre i tre comportamentali passano già — il comportamento non cambia, cambia chi lo produce. 📌 Due commenti del backend diventano falsi (richiesta scritta). 🟡 I due wrapper di lotto (0.70) restano due: alla terza si estrae. |
| 2026-08-29 (Fase 3, la storia e l'aliquota) | ✅ Storicizzazione delle tabelle IVA: `config.iva` aveva `storicizza = f` su **tutte e 15 le righe** — la macchina c'era e il rubinetto era chiuso; `iva_natura` non aveva né trigger né gemella; `iva_stati` non era storicizzabile per **PK composita**, e prende una chiave surrogata (`D26`, «ho fatto una cazzata»). ⛔ **Corretto un mio errore**: avevo scritto che una fattura vecchia «cambia numero» ristampata — **non cambia**, imponibile e imposta sono memorizzati sul riepilogo. Il difetto vero è più piccolo: la **percentuale** è derivata viva, quindi un documento può contraddire sé stesso. ⭐ E l'argomento di Tid batte la mia proposta di mettere l'aliquota sul solo riepilogo: **la rigenerazione parte dalle righe**, quindi la riga deve ricordare. ⛔ Scoperto che il backfill non può toccare le righe congelate — il guard ha un bypass e **non si usa**, perché scrivere su uno snapshot fiscale è ciò che quel guard esiste per impedire: quelle righe restano a NULL, e il NULL significa «anteriore allo snapshot». |
| 2026-08-28 (Rev 2, chiusura) | Tid nomina i casi che rendono la famiglia reale — agevolata disabili, società al 10% senza dichiarazione d'intento. ⭐ `soggetti_intento` diventa **`anagrafiche.soggetti_titoli_iva`** (`D10`), con l'**emittente destinatario** in chiave (`D10-bis`) e l'**ambito fino al singolo articolo**. `I7` sale a **prerequisito di `I2`**. Aggiunto il §8, il racconto in linguaggio piano |
| 2026-08-29 (Fase 1 chiusa) | ✅ **La metà BE/FE della Fase 1 è fatta**, in [brief-be-fe-iva-risolutore-e-regime-cliente.md](brief-be-fe-iva-risolutore-e-regime-cliente.md): sei chiavi via dal cliente, i due flag sul soggetto, i tre codici sul contratto in PATCH, le due `reason_key` di `I9`. ⛔ **Due correzioni alla «Richiesta al BACKEND» del §8-bis**, entrambe emerse eseguendola: l'effetto **non era solo il silenzio** — tre percorsi su quattro erano **500**, perché SQL diretto sulla tabella e non passano da `fn_update_cliente` (*la richiesta era stata scritta guardando la whitelist, non le query*); e mancava un **prerequisito DB** — `fn_create_contratto` ha una whitelist interna che scarta i tre codici in CREATE, stesso difetto di `fatturazione_immediata` sulla stessa funzione. ⛔ Corretta anche l'apertura del §8-bis, che diceva *«niente di quanto segue è applicato»* mentre le sue stesse voci dicevano APPLICATA. 🟡 Unica coda: `I8` lato CREATE, con [brief-db-fn-create-contratto-codici-atto.md](../work-done/brief-db-fn-create-contratto-codici-atto.md). **La Fase 2 (`I7`) è ora il prossimo passo** |

