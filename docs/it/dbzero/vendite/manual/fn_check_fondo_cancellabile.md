## 📘 Documentazione Concettuale – Funzione `vendite.fn_check_fondo_cancellabile`

> **Ultimo aggiornamento**: 25 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale) — colonna `congela_fiscale`, la soglia della quarta condizione
>
> Approfondimento funzioni:
>
> * [vendite.fn_reset_fondi_fattura](/dbzero/vendite/funzioni/fn_reset_fondi_fattura) — consumatore: segnala e prosegue
> * [vendite.fn_applica_cancellazione_fondo_fattura](/dbzero/vendite/funzioni/fn_applica_cancellazione_fondo_fattura) — consumatore: la primitiva del gesto, rifiuta e lo dice
> * [vendite.fn_cancella_fondo_fattura](/dbzero/vendite/funzioni/fn_cancella_fondo_fattura) — il gesto «cancella il fondo», che chiama la primitiva
> * [vendite.trgfn_fattura_satellite_guard_congelamento](/dbzero/vendite/funzioni/trgfn_fattura_satellite_guard_congelamento) — la stessa soglia, sugli altri satelliti
>
> Guide:
>
> * [Fatturazione](/guide/fatturazione) — il reset del lotto e i fondi che non tocca

---

### 🎯 Scopo Principale

Risponde a una domanda sola: **«perché questo atto di fondo non si può
cancellare?»** — oppure `NULL`, che vuol dire *si può*.

Non scrive niente e non solleva errori di dominio: è un **criterio**, e la
reazione la costruiscono i chiamanti.

---

### Il vocabolario, chiuso

| Motivo | Che cosa dice |
| --- | --- |
| `NULL` | si può cancellare |
| `ATTO_NON_TROVATO` | non esiste, **oppure** non è nel perimetro di chi chiede |
| `ATTO_ESEGUITO` | il trasferimento è già stato registrato in contabilità |
| `RIGA_REGISTRATA` | una sua riga contabile è `POSTATA` — è **l'invariante rotta** |
| `CONTABILE_CHIUSA` | la sua riga sta in una distinta già chiusa |
| `FIGLIA_CONGELATA` | la fattura che lo ha ricevuto è oltre la soglia fiscale |
| `SISTEMAZIONE_ATTIVA` | un atto di `pagamenti.sistemazioni` lo trattiene |

---

### ⛔ Perché esiste: non si estrae la funzione, si estrae il PREDICATO

I tre blocchi «l'atto non è ancora un fatto» vivevano **dentro**
`fn_reset_fondi_fattura`. Con l'arrivo del gesto manuale sarebbero diventati due
copie — e le due copie avrebbero detto, senza nessun errore e senza nessun log,
che un atto è intoccabile mentre il reset lo cancella.

Ma non si è estratta la funzione intera, perché **i due consumatori vogliono
dallo stesso criterio cose opposte**:

| Chi | Che cosa fa quando l'atto è bloccato | Perché |
| --- | --- | --- |
| `fn_reset_fondi_fattura` | **segnala e prosegue** (`W_…` nel diario) | è un giro tecnico su N atti: un'eccezione fermerebbe il reset di un lotto intero per colpa di una fattura sola |
| `fn_applica_cancellazione_fondo_fattura`, la primitiva del gesto (la chiamano `fn_cancella_fondo_fattura` e l'annullo di una sistemazione) | **rifiuta e lo dice** (`E_…`) | è il gesto di **una persona** su **un** atto, e lì il silenzio è il difetto |

> ℹ️ È la «regola del 2», già applicata due volte in questo cantiere
> (`fn_saldo_sorgente_fondo`, `fn_check_fondo_fattura_capiente`).

---

### ⚠️ L'ordine dei motivi è portante, non estetico

`SISTEMAZIONE_ATTIVA` si dice per **ultimo**, ed è l'unico dei sei con un rimedio
che l'operatore può davvero compiere (*«annulla la sistemazione, e il fondo cade
con lei»*). Anticiparlo davanti a un blocco definitivo manderebbe a fare un gesto
destinato a fallire — cioè un pulsante in un vicolo cieco.

---

### ⭐ La quarta condizione: la soglia è un DATO, non una lista

```text
figlia con congela_fiscale = false   →  il fondo si può ancora cancellare
figlia con congela_fiscale = true    →  congelata: il fondo non si tocca
```

Si legge `config.stati_doc_fiscale.congela_fiscale` e **non** la lista
`NOT IN ('DRAFT','EMESSA')`: dal changeSet `20260830-02` quella lista non è più
la sede della soglia, e riscriverla qui rimetterebbe in circolo una delle otto
copie che quel passo ha tolto.

> ⭐ **Non si aggiunge una regola: si finisce di applicarne una che c'era già.**
> Il fondo era l'**unico satellite della fattura non congelato**, ed era
> un'osservazione senza conseguenze finché nessuno poteva toglierlo di mezzo a
> mano. Adesso che qualcuno può, vale la soglia di casa.

---

### 🔴 Due casi che sembrano uno, e non lo sono

La lettura della figlia distingue **la riga che non si legge** dalla **riga senza
stato**, e il modello ammette entrambi:

| Situazione | Risposta | Perché |
| --- | --- | --- |
| la figlia non si legge (cancellata, o invisibile sotto la row security) | `FIGLIA_CONGELATA` | da qui non si può certificare che sia lavorabile, e un satellite non si tocca su un documento che non si sa leggere |
| la figlia si legge ma **non ha stato** (la colonna è nullabile) | non blocca | ⭐ è la stessa decisione che `trgfn_fattura_satellite_guard_congelamento` prende già sullo stesso caso |

> ⚠️ **Trovato dal collaudo, non dal ragionamento.** La prima stesura le
> confondeva in un `COALESCE(v_congela, TRUE)` e rendeva rossi **sette** test di
> `db/pgtap/vendite/test-fondi-fattura.sql`, la cui figlia nasce senza stato. È
> la ragione per cui i file esistenti si guardano **prima** dell'apply.

---

### ⭐ Nessuna porta spegne la quarta condizione

Il criterio non legge nessuna GUC: vale identico per il reset e per il gesto, e
nessuno lo può allargare.

Nel reset di un lotto la figlia è la fattura che si sta pulendo, e i controlli
d'ingresso dei verbi del reset la vogliono **pre-fiscale**, cioè non congelata.
La quarta condizione quindi non scatta, per costruzione. Se un giorno il reset
toccasse una figlia congelata, il fondo resterebbe dov'è e il diario lo direbbe
(`W_FONDO_FIGLIA_CONGELATA`): lo stesso comportamento prudente che il gesto ha già.

---

### Regole principali

* `STABLE`, `SECURITY INVOKER`: gira come chi chiama. Le primitive che la
  chiamano girano come proprietario, e il perimetro lo rimettono loro prima di
  chiederla; chiamata dall'applicazione, gira sotto la row security, e un atto
  invisibile vale `ATTO_NON_TROVATO`.
* L'applicazione la può eseguire: è un criterio che legge soltanto, e senza
  porte non apre niente.
* Guard di parametro con `E_VENDITE_CHIAMATA_NON_VALIDA` (`TECNICO`): un id
  assente o `<= 0` non lo produce nessuna interfaccia — è il chiamante a essere
  rotto.
* Guard di configurazione con `E_CONFIG_MANCANTE` sugli stati `POSTATA` e
  `CHIUSA`: senza, un codice interno assente farebbe dire «nessuna riga
  registrata», cioè **fail-open sul caso più grave**.

> ⚠️ **Le due letture che possono essere cieche, quando la chiama l'applicazione.**
> `pagamenti.vendite_contabili` e `vendite_contabili_righe` hanno la row
> security, quindi in teoria un chiamante che vede l'atto ma non la sua distinta
> non vedrebbe `CONTABILE_CHIUSA`. Nel percorso reale non succede — la policy
> delle righe ammette anche `fn_scope_ef_whitelist_via_fattura`, e la riga del
> fondo porta la fattura sorgente — e comunque **la FK è la rete**: la
> cancellazione fallirebbe forte su `fk_vendite_contabili_righe_fondo_source`
> invece di riuscire in silenzio.
>
> ⛔ Un `SECURITY DEFINER` qui aprirebbe la lettura dell'atto stesso, cioè
> spegnerebbe proprio `ATTO_NON_TROVATO`.

---

### Si legge una volta sola per atto

⚠️ **Si legge una volta sola per atto.** Chiamare il criterio due volte sulla
stessa riga significa accettarne metà e rifiutarne l'altra: è il difetto già
pagato in Fase C di questo cantiere.

---

### Note di migrazione

* 2026-08-31 — nasce estraendo il predicato da `fn_reset_fondi_fattura`, per il gesto manuale
  (brief-db-fondo-fattura-ricalcolo-e-governo, D-21).
* 2026-11-25 — esce il ramo che, con `zeroerp.maintenance_reset_lotto_draft` accesa, saltava la
  quarta condizione: l'applicazione poteva accendere la GUC da sé e cancellare il fondo di una
  figlia congelata. Il consumatore che rifiuta è ora la primitiva
  `fn_applica_cancellazione_fondo_fattura` (brief-db-porte-aperte-dalla-sola-guc, D-Z a).

---

{% include-markdown "signature-core.md" %}
