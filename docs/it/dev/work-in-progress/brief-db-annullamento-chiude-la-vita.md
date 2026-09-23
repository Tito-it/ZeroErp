# Brief DB — L'annullamento chiude la vita: un lotto annullato esce dai controlli

> **Destinatari:** team DB (`dev/db-tid`). Nessun prerequisito BE/FE: la
> modifica è tutta lato database.
>
> **Tipo:** brief di cantiere, nato da una **decisione di Tid del 2026-09-22**
> (§1) presa davanti a un difetto trovato lo stesso giorno (§2).
>
> **Da leggere per primo: §1 — la regola. Il §2 è il fatto che l'ha fatta
> emergere, non la sua ragione.**
>
> **Stato (2026-09-22):** 🔵 aperto, da fare lato DB.
>
> **In una riga:** un lotto **annullato** non deve comparire in nessun
> controllo; la regola ha già un nome nel modello
> (`config.stati_doc_fiscale.is_abortito`), e oggi
> `vendite.vw_lotti_chiusi_con_gruppi_in_errore` non la rispetta — più il
> fatto che quel controllo **non è a catalogo**, quindi il suo allarme non
> arriva a nessuno.

---

## 1. La regola

> **L'annullamento chiude la vita.** Un lotto annullato non compare nei
> controlli.
> — Tid, 2026-09-22

È una regola sul **modello**, non una risposta alle righe di oggi: l'annullo è
un atto dichiarato e tracciato, non una cancellazione, e ciò che è chiuso non
è più lavoro di nessuno. Un controllo elenca **cose da fare**; un lotto
annullato non ne è una, qualunque cosa gli sia successa prima.

### 1.1 La regola ha già un nome, e non va inventato

Il modello sa già dire «questa cosa è morta»:

| Dove | Che cosa dice |
| --- | --- |
| `config.stati_doc_fiscale.is_abortito` | il flag. ⭐ **`ANNULLATA` è l'unico stato che ce l'ha acceso** — letto sul vivo il 22-09, sei stati in tabella |
| `vendite.vw_lotti_fase.is_abortito` | lo **proietta già**, accanto a `pre_fiscale` e `in_gioco` |
| 17 viste di `vendite` | lo leggono già (dashboard, lineage, preventivi, offerte, stato sorgente) |

⇒ La regola si scrive `NOT is_abortito`, in un flag che esiste, con una vista
che lo espone già. **Non serve una colonna nuova né un elenco di stati
cablato**: un `stato_codice_interno <> 'ANNULLATA'` sarebbe la stessa regola
scritta peggio, e si romperebbe il giorno che nasce un secondo stato abortito.

---

## 2. Il difetto che l'ha fatta emergere — 2026-09-22, letto su `dbdev`

⚠️ *Fatto datato. È un **controesempio**, non la ragione della regola: la
ragione sta nel §1 e regge anche a zero righe.*

`vendite.vw_lotti_chiusi_con_gruppi_in_errore` elenca una contraddizione — un
lotto chiuso `COMPLETATO` che contiene documenti in `ERRORE`. Il suo
`COMMENT` dichiara l'invariante:

> ⛔ L'INVARIANTE NON È PIÙ «VUOTO», È «NESSUNA RIGA NON DICHIARATA»
> (rev 2026-09-07). […] sono i lotti ANNULLATI PRIMA del 2026-09-07 19:09
> […] ⇒ Una riga su un lotto annullato DOPO quel momento è un allarme vero,
> e va guardata.

**Oggi le righe sono 7, e il pregresso dichiarato è 6.**

| Lotto | `stato_lotto` | Stato fiscale | Annullato il | Dichiarato? |
| --- | --- | --- | --- | --- |
| `LTF-0009900` `LTF-0009901` `LTF-0009931` `LTF-0009960` `LTF-0009961` `LTF-0009962` | `COMPLETATO` | `ANNULLATA` | 2026-09-07, fra 11:28 e 17:53 | ✅ sì (prima delle 19:09) |
| **`LTF-0010972`** (id 13337, 2 gruppi in errore, `E_PULL_COMMESSA`) | `COMPLETATO` | `ANNULLATA` | **2026-09-12 11:21** | 🔴 **no** |

⭐ Il criterio del `COMMENT` e i dati concordano perfettamente sui sei: è la
prova che il criterio è quello giusto, e che il settimo è davvero l'allarme
che quella riga descrive.

### 2.1 ⭐ Il secondo difetto, ed è quello che è costato di più

**L'allarme è suonato e non l'ha sentito nessuno: è lì dal 12-09, dieci
giorni.** La vista si chiama `PRESIDIO` nel proprio `COMMENT` e dichiara un
invariante preciso, ma **non ha una riga in `dbops.presidi`** — quindi è fuori
dal digest, dal pallino e da ogni conteggio.

* letto il 22-09: 45 presidi a catalogo di schema `dbops`, 1 di `maintenance`,
  **0 di `vendite`**;
* ⭐ e non c'è niente che lo vieti: `chk_presidi_vista_qualificata` chiede solo
  la forma `schema.nome`, e `maintenance` è già dentro. Non è una convenzione
  a tenerla fuori, è una dimenticanza;
* ⚠️ il pgTAP citato come verifica (`test-lotti-gruppi-esito.sql`, `plan(13)`,
  casi 11-12) prova il **meccanismo** su casi costruiti apposta — e dichiara di
  non dipendere dal pregresso. Giusto così, ma vuol dire che **nessuno guarda
  il contenuto vivo**: resterebbe verde con cento righe lì dentro.

### 2.2 Perché il conteggio può solo crescere

Il changeSet `20260907-08` ha tolto una falsificazione vera: prima, annullare
un lotto **riscriveva** `stato_lotto = COMPLETATO`, cioè cancellava la memoria
di com'era andata. Ora non lo fa più — ed è giusto.

⇒ Conseguenza: ogni giro che finisce con un gruppo fallito e viene poi
annullato **aggiunge una riga qui**. Le sei dichiarate sono un insieme chiuso;
tutte le righe nuove sono vere per costruzione; e non le guarda nessuno.
`LTF-0010972` è la prima, non l'ultima.

---

## 3. Dove vale la regola — il censimento, 2026-09-22

Sweep su tutti i presidi a catalogo **più** la vista non catalogata: i
controlli che toccano i lotti sono **due**.

| Controllo | Esclude gli annullati? | Come |
| --- | --- | --- |
| `vendite.vw_lotti_chiusi_con_gruppi_in_errore` | 🔴 **no** | filtra solo `stato_esecuzione='ERRORE' AND stato_lotto='COMPLETATO'` |
| `dbops.vw_lotti_fermi_da_guardare` | ✅ sì — **ma per un'altra ragione** | `WHERE … f.pre_fiscale`, e `pre_fiscale = NOT congela_fiscale` |

⚠️ **Il secondo va guardato lo stesso, ed è il punto del §4.3.** Oggi non
mostra gli annullati perché `ANNULLATA` **congela il fiscale**, non perché sia
annullato. Sono due proprietà diverse che oggi viaggiano insieme: il giorno che
uno stato abortito non congelasse il fiscale — o che il congelamento cambiasse
perimetro — quel controllo ricomincerebbe a mostrare lotti morti, **senza che
nessuno abbia toccato la vista**. La regola del §1 lì è rispettata per
coincidenza, e una coincidenza non è un presidio.

---

## 4. La richiesta al team DB

### 4.1 La vista esclude gli annullati

`vendite.vw_lotti_chiusi_con_gruppi_in_errore`: aggiungere l'esclusione dei
lotti abortiti, letta dal flag e non da un elenco di stati. La vista oggi
`JOIN`a `vendite.fatturazione_lotti` diretta, quindi serve arrivare a
`is_abortito` — via `vendite.vw_lotti_fase` (che lo proietta già) o via
`config.stati_doc_fiscale`. ⭐ La scelta è vostra; il vincolo è che la regola
resti **una sola** e nominata, non ricopiata.

✅ Effetto atteso, verificato sui dati del 22-09: **7 righe → 0**, perché tutte
e sette sono `ANNULLATA`.

### 4.2 L'invariante torna «vuoto», e il pregresso dichiarato sparisce

⭐ **È la parte elegante, e va scritta nel `COMMENT`.** Le sei righe del
pregresso erano annullate: con la regola del §1 **escono da sole**. Quindi:

* l'invariante torna da «nessuna riga non dichiarata» a **«vuoto»**;
* il registro delle eccezioni **non serve più** — non nasce proprio;
* il blocco del `COMMENT` sul pregresso (rev 2026-09-07) va riscritto: non
  cancellato, ma raccontato come **chiuso** e col perché, che è la ragione per
  cui quel testo esiste.

⚠️ Il difetto che il pregresso descriveva (`stato_lotto` falsificato su undici
lotti) **resta un fatto storico vero** e la decisione di Tid del 07-09 di non
correggerlo non cambia: semplicemente quei lotti non sono più affari di questo
controllo. ⛔ Non è «nascondere le righe»: è che un lotto annullato non è una
cosa da fare — che è esattamente la regola, non una scorciatoia per farle
tacere.

### 4.3 La regola si scrive anche dove oggi è una coincidenza

`dbops.vw_lotti_fermi_da_guardare`: rendere **esplicita** l'esclusione degli
abortiti, accanto a `pre_fiscale` e non al posto suo. Non cambia una riga del
risultato di oggi (§3) — e questo è precisamente il motivo per cui va fatto
ora: è un guard che non costa niente e che regge il giorno in cui le due
proprietà si separano.

⛔ Argomento da rifiutare, se venisse in mente: *«oggi è ridondante»*. Zero
occorrenze non significa che il caso non esiste, e la vista aggiornata
dichiarerebbe la regola invece di ereditarla.

### 4.4 Il controllo entra a catalogo

Iscrivere `vendite.vw_lotti_chiusi_con_gruppi_in_errore` in
`dbops.presidi` (`80_data/.../dbops/presidi.csv`):

| Campo | Valore proposto | Perché |
| --- | --- | --- |
| `natura` | `ZERO` | dopo il §4.1 l'invariante è di nuovo «vuoto» |
| `cadenza` | `GIORNALIERA` | stessa ragione del gemello: una contraddizione nata ieri sera va vista stamattina |
| `perimetro` | da decidere: le tabelle sotto hanno la RLS | ⚠️ **da verificare**: il gemello è `DEFINER` perché `security_invoker` + RLS dà «zero per cecità». Va provato, non assunto |
| `registro` | `NULL` | §4.2: non nasce |
| `presidiato_da` | `NULL` | `ZERO` non lo richiede (`chk_presidi_cancello_ha_presidio` vincola solo `CANCELLO`) |

⚠️ `chk_presidi_fuori_digest_cadenza_mai` non morde: vincola `INVENTARIO` e
`CANCELLO`, non `ZERO`.

### 4.5 Il pgTAP cresce di due casi

`db/pgtap/vendite/test-lotti-gruppi-esito.sql` (oggi `plan(13)`, casi 11-12 sul
meccanismo). Due casi **costruiti**, non misurati sulla popolazione:

1. un lotto `COMPLETATO` con un gruppo in `ERRORE` **e annullato** → **non**
   viene nominato (è la regola del §1);
2. lo stesso lotto **non** annullato → viene nominato (il presidio non si è
   spento del tutto).

⭐ Il secondo è quello che conta: senza, la regola si potrebbe soddisfare
svuotando la vista, e sarebbe verde per sottrazione.

E la riga a catalogo del §4.4 va provata come le altre (natura/perimetro/
cadenza/attivo, sulla falsariga del caso 19 di `test-lotti-fermi-verdetto-a-db-v1.sql`).

---

## 5. La conseguenza, dichiarata

⚠️ **Con questa regola, annullare un lotto fa sparire il suo allarme.**
`LTF-0010972` era una contraddizione vera, e dopo il §4.1 non si vedrà più.

Va detto perché è il prezzo della regola, e va detto che **è un prezzo accettato
e non un effetto collaterale scoperto dopo**. Le ragioni per cui regge:

* l'annullo non è una cancellazione: è un atto **tracciato**, con il suo stato,
  la sua data e il suo autore. La storia conserva tutto, e resta interrogabile;
* il controllo continua a prendere le contraddizioni sui lotti **vivi**, cioè
  finché servono a qualcuno;
* ⛔ e l'alternativa era peggiore: un controllo che elenca per sempre lotti
  morti smette di essere letto — e allora non presidia più nemmeno il caso per
  cui è nato. È esattamente quello che è successo qui, dieci giorni.

⇒ Se un domani servisse sapere «quante volte un giro è finito in contraddizione
ed è stato annullato», quella è una **misura sullo storico**, non un controllo:
sede diversa, e non è questo brief.

---

## 6. Cosa resta

* 🔵 §4.1 la vista esclude gli abortiti (7 → 0);
* 🔵 §4.2 `COMMENT` riscritto: invariante «vuoto», pregresso chiuso col perché;
* 🔵 §4.3 la regola esplicita anche in `dbops.vw_lotti_fermi_da_guardare`
  (nessun cambio di risultato oggi, ed è il punto);
* 🔵 §4.4 la riga in `presidi.csv` — ⚠️ `perimetro` da **provare**, non assumere;
* 🔵 §4.5 due casi pgTAP costruiti + la riga di catalogo;
* ▶ niente da fare lato BE/FE: nessun endpoint e nessuna schermata leggono
  questa vista (verificato il 22-09 — i soli riferimenti fuori da `db/` e
  `docs/` sono commenti).

---

## 7. Come sono stati letti i numeri di questo brief

⚠️ Per chi rifarà le misure: le tabelle sotto hanno la **RLS** e le viste sono
`security_invoker`. Da una sessione senza veste rispondono **zero**, e quello
zero **non è un dato** — è cecità. Le letture del §2 e del §3 sono state fatte
con `SET app.ruolo_applicativo = 'OPERATORE'` lasciando vuoto
`app.current_user_id`, che cade nel ramo «job batch» (`p_auth_user_id IS NULL
→ true`) di `script.fn_check_user_emittente_scope`. I conteggi dei presidi
vengono invece da `dbops.fn_conta_presidio`, che è `SECURITY DEFINER`.
