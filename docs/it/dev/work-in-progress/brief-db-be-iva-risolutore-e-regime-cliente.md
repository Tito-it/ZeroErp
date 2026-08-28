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
> ⭐ **Due decisioni di dominio già prese** (Tid, 2026-08-27) e **una ancora
> aperta**: sono nel §D, etichettate una per una. Le decise non vanno ri-discusse
> a valle; l'aperta **blocca** la richiesta `I6` e nient'altro.
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

---

## D. Decisioni e questioni aperte — 2026-08-27

> Stanno qui in testa perché ognuna delle richieste del §5 discende da una di
> esse, e perché una decisione che vive solo dentro una conversazione viene
> ri-aperta al primo dubbio.
>
> ⚠️ **Ognuna dice di chi è.** `D2` e `D3` sono **decisioni di Tid**, prese a
> parole il 2026-08-27. `D1` è **aperta**: c'è la proposta e l'argomento, non
> c'è la decisione. `D4` non è una decisione affatto — è una constatazione
> tecnica. Attribuire a qualcuno una scelta che non ha fatto è il modo in cui un
> documento diventa inaffidabile, e qui non serve nemmeno: l'argomento regge da
> sé anche senza una firma sotto.

### D1 · ❓ **APERTA** — l'IVA di riga è modificabile a mano o no?

**Proposta: no**, su nessun documento. Varrebbe per **DDT, ordini e preventivi**
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

### R-3 · 🔴 Lo stesso difetto silenzioso è **aperto su ordini e preventivi**

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

⚠️ **`D1` resta formalmente aperta** solo per la verifica che non ci siano
**altri** titoli per-operazione fuori dal risolutore. Il caso che la teneva in
piedi è risolto.

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
| **I0** | ⭐ **Nuova, ed è il passo che sblocca gli altri**: `DROP` di `anagrafiche.clienti.iva_id` (`D7-bis`) + salita di `split_payment`/`cliente_pa` su `anagrafiche.soggetti` (`D8`). Si porta dietro `fn_update_cliente`, la whitelist BE e il `ClienteDrawer.vue` | DB + BE + FE | 🟢 pronta: nessun consumatore vero |
| **I7** | **`anagrafiche.soggetti_titoli_iva`** (`D10`) — famiglia con vocabolario dei tipi, **emittente destinatario** in chiave (`D10-bis`), ambito fino al **singolo articolo**, `validita` `daterange`, registro movimenti (`D5`) e plafond **solo per i tipi che ce l'hanno**; + codice `config.iva` con `natura_iva_id = 8` (oggi la natura è **orfana**); + `EXCLUDE` anti-sovrapposizione sulla chiave nuova. ✅ Le sei domande di §2.6.2 restano decise | DB + BE | ⛔ **prerequisito di `I2`**: senza, lo stadio B non ha nessuna sorgente |
| **I2** | Risolutore IVA a **due stadi** (§2.7, `D6`+`D7`): A = aliquota ordinaria, cascata `articolo → catena prezzo → tipo utenza`; B = **titolo documentato** dal soggetto, che sostituisce A. ⭐ **Ritorna una ripartizione** `(quota, codice IVA)`, non un codice (§2.7.3). Sul modello di `fn_resolve_prezzo_listino_v2` | DB | dopo `I7` |
| **I3** | Il BE chiama `I2` alla creazione della riga; il FE **smette** di fare l'auto-fill e mostra il risultato del risolutore (§2.5.1) | BE + FE | dopo `I2` |
| **I4** | La riga di fattura smette di rileggere `art.iva_id` e **ri-risolve** via `I2`. ⛔ L'alternativa «l'IVA viaggia nella catena `attivita_fatturabili`» è **esclusa da P1**: la fattura rifà, non trasporta. ⚠️ **Breaking change dichiarato** (§2.5.2) | DB + BE | dopo `I2` |
| **I5** | `split_payment` / `cliente_pa` → riga e riepilogo fattura + payload SDI (`EsigibilitaIVA`), **fuori** dal risolutore (`D4`). ⭐ **Voce corta**: `fatture_righe` e `fatture_riepiloghi_iva` hanno **già** le colonne e il raggruppamento — manca solo chi le riempie (`D8`) | DB + BE | dopo `I0` |
| **I8** | ⭐ **Nuova, e non è IVA**: `codice_cig` / `codice_cup` / `codice_commessa` da `clienti` a **`vendite.contratti`**, + **snapshot** sulla fattura all'emissione (`D9`). ⚠️ `vendite.fatture` non ha nessun link al contratto: senza snapshot non arrivano mai | DB + BE + FE | 🟢 **da fare adesso**: il builder XML non è ancora scritto |
| **I9** | ⭐ **Nuova**: il gate «riga con prezzo senza aliquota» esiste **solo sul DDT**. `vw_ordini_righe_iva_base` non filtra nemmeno `prezzo_unitario`, e per ordini e preventivi non c'è nessun `fn_check_*_emittibile` (`R-3`) | DB | indipendente |
| **I6** | ❓ **Ferma su D1.** Se «l'IVA di riga non si cambia» è una regola, la sua sede non è un `:disabled` nel template: o scende nel BE (`iva_id` fuori da `_UPDATE_KEYS_RIGA`) o si dichiara che è solo un aiuto della UI | BE | **per ultima** |

⛔ **L'ordine fra I6 e le altre non è indifferente, ed è l'unico modo di sbagliare
in silenzio.** `I6` toglie all'operatore l'ultima uscita manuale: applicata
**prima** di I2/I3 — cioè prima che le righe nascano con l'aliquota giusta —
cementerebbe i buchi e i valori sbagliati che oggi si possono ancora correggere
via API. `I6` va **per ultima**, e solo dopo che D1 è stata decisa.

⭐ **La dipendenza nuova della Rev 2, e va nel verso non ovvio**: `I7` **non** è
una voce parallela a `I2`, è il suo **prerequisito**. Finché i titoli non hanno
una sede, lo stadio B non ha niente da leggere — e con `clienti.iva_id` tolta da
`I0`, un risolutore scritto prima di `I7` sarebbe uno **stadio A soltanto**, cioè
il comportamento di oggi con più codice intorno.

⚠️ **`I0`, `I8` e `I9` sono indipendenti fra loro e da tutto il resto**, e
conviene farle subito: sono le tre che oggi costano meno e che dopo costeranno di
più — `I0` perché non ha consumatori veri, `I8` perché il builder FatturaPA non
esiste ancora, `I9` perché è la stessa regola già scritta e collaudata sul DDT.

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

**Tempo 2 — questo cliente ha un titolo che la sostituisce?** Si va a vedere se
il **soggetto** — la partita IVA, non la singola fornitura — ha un **titolo
registrato e valido oggi**: una dichiarazione d'intento, una dichiarazione di uso
industriale, un'agevolazione per disabile, la qualifica di cooperativa sociale.
Se non ce n'è, il Tempo 1 è la risposta finale. Se ce n'è uno, **prende il posto**
dell'aliquota ordinaria per quella riga.

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

**Il documento a monte proietta, la fattura decide.** L'IVA che l'operatore vede
su un preventivo, un ordine o un DDT serve a mostrargli che cosa verrà applicato e
a fare il riepilogo del documento. Non è il valore che finirà in fattura: la
fattura **rifà** il calcolo al momento in cui nasce, perché nel frattempo un
titolo può essere scaduto o un plafond essersi esaurito.

**Restano fuori due cose che sembrano IVA e non lo sono.** Lo *split payment* e
il *cliente PA* non cambiano l'aliquota: cambiano chi versa l'imposta all'erario,
e viaggiano per conto loro fino alla fattura elettronica. E CIG, CUP e commessa
non c'entrano con l'IVA affatto: sono i riferimenti del **contratto**, e in
fattura ci arrivano copiati da lì.

---

## 9. Diario

| Data | Cosa |
| --- | --- |
| 2026-08-27 | Nascita del brief dalla domanda di Tid sul collaudo delle righe DDT senza prezzo. Quattro voci, `D1`…`D5`, poi `D6` in giornata (due stadi) — che senza dirlo rendeva `D2` priva d'oggetto |
| 2026-08-28 (mattina) | ✅ `I1` **applicata** fuori da questo brief, dalla Fase C di `brief-db-ddt-riconsegna-eredita-testata`: `E_DDT_RIGA_IVA_MANCANTE`, e con il discrimine sul **prezzo** invece che sulla causale (`R-1`) |
| 2026-08-28 (Rev 2) | Rilettura critica con Tid, partita dal suo dubbio: *«avevo dato prioritaria l'IVA su soggetto rispetto all'articolo, credo debba essere il contrario»*. ⛔ **`D2` superata da `D7`**: non c'era una precedenza da invertire, c'erano due domande diverse. Verificati sulla doc auto-gen quattro fatti che il documento dava per veri (§R): `I1` già fatta, il pgTAP del §6 sbagliato, il gate mancante su ordini/preventivi, `fn_get_iva_override` **rotta**. Trovato che l'anello «uso fornitura» **esisteva già** (`config.tipi_utenze`, `D11`) e che l'aliquota **cavalca già la catena del prezzo** in tre tabelle mai lette |
| 2026-08-28 (Rev 2, seguito) | Partendo dalle colonne che Tid aveva messo sul cliente *«perché potevano essere diverse per utility»*: ⭐ **non erano un gruppo solo**. `clienti.iva_id` **si toglie** (`D7-bis`), `split_payment`/`cliente_pa` salgono su **`soggetti`** (`D8`), CIG/CUP/commessa vanno al **contratto** con snapshot in fattura (`D9`) — voce che nel brief non c'era |
| 2026-08-28 (Rev 2, chiusura) | Tid nomina i casi che rendono la famiglia reale — agevolata disabili, società al 10% senza dichiarazione d'intento. ⭐ `soggetti_intento` diventa **`anagrafiche.soggetti_titoli_iva`** (`D10`), con l'**emittente destinatario** in chiave (`D10-bis`) e l'**ambito fino al singolo articolo**. `I7` sale a **prerequisito di `I2`**. Aggiunto il §8, il racconto in linguaggio piano |
