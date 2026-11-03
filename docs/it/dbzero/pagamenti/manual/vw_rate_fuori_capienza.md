## 📘 Documentazione Concettuale – Vista `pagamenti.vw_rate_fuori_capienza`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze) — le rate candidate, con il loro importo col segno
> * [config.nature_doc_fiscale](/dbzero/config/tabelle/nature_doc_fiscale) — la natura del documento, che dà all'etichetta il dato per dire il verso
>
> Approfondimento viste:
>
> * [pagamenti.vw_eccedenze_da_sistemare](/dbzero/pagamenti/views/vw_eccedenze_da_sistemare) — lo stesso sguardo sul documento intero, da cui parte il processo rimborsi
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldi_rate](/dbzero/pagamenti/funzioni/fn_get_saldi_rate) — il nucleo dei saldi delle rate, chiamato una volta sull'insieme dei candidati
> * [pagamenti.trgfn_vendite_contabili_righe_guard_rata](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_rata) — il guard di capienza che ammette la forzatura, e di cui la vista è la contropartita
> * [vendite.fn_numero_documento_fattura](/dbzero/vendite/funzioni/fn_numero_documento_fattura) — la sede unica del numero del documento
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — la regola dei saldi, per chi non è tecnico

---

### 🎯 Scopo Principale

L'elenco delle rate il cui residuo è uscito dalla banda: ha attraversato lo zero, oppure supera l'importo della rata in valore assoluto.

🔴 **Esiste per una ragione precisa.** Il guard della rata **accetta** una registrazione fuori
capienza, purché qualcuno la dichiari. Senza un elenco a valle quella dichiarazione sarebbe un
modo per nascondere, non per registrare: fra sei mesi quei pagamenti non li ritroverebbe
nessuno. È per questo che la vista è nata insieme al guard che permette la forzatura, e non
dopo.

---

### ⭐ La banda si legge con segno e valore assoluto

La banda non è l'intervallo fra zero e l'importo: quell'intervallo a estremi fissi, su una
rata **negativa** (la rata della nota di credito), si inverte. La forma è quella del guard: **segno e
valore assoluto**, senza estremi da invertire. Una rata è fuori capienza quando:

* il residuo è diverso da zero e ha il segno **opposto** all'importo (ha attraversato lo zero),
  oppure
* il residuo, in valore assoluto, **supera** l'importo.

Non è un terzo criterio inventato qui: è la **stessa regola del guard letta a posteriori** («un
movimento riduce ciò che manca e non lo supera»), applicata al risultato invece che al singolo
movimento.

---

### ⭐ Due motivi, non uno

| `motivo` | Che cosa è successo | Su una fattura | Su una nota di credito |
| --- | --- | --- | --- |
| `SOVRA_INCASSATA` | il residuo ha **attraversato lo zero**: è entrato più del dovuto; su una nota di credito, si è rimborsato più del credito | rata 100, incassato 110 | rata −20, rimborsato 30 |
| `MOVIMENTO_CONTRARIO` | il residuo **supera l'importo**: è uscito denaro dove non era entrato; su una nota di credito, è entrato denaro invece di uscire | rata 100, rimborso 30 senza incasso | rata −20, il cliente paga 15 |

Il vocabolario resta a **due** valori: la sfumatura della nota di credito la dice l'etichetta,
non un terzo codice. E l'etichetta ha il dato per dirla: la riga porta la natura del documento
(`natura_doc_codice_interno`, `natura_doc_descrizione`), su cui il frontend ramifica. La natura
è obbligatoria sul documento, quindi unirla non toglie nessuna riga.

⭐ Il nome dice entrambi i versi. «Rate sovra-incassate» avrebbe detto meno di ciò che l'elenco
contiene: fuori capienza si esce in due versi, e il secondo (pagato 110, rimborso 15 invece di
10) è proprio il caso che ha fatto cambiare la regola.

---

### ⭐ Chi entra fra i candidati

Il costo si limita **prima** del nucleo: entrano solo le rate che hanno almeno un movimento, una
riga forzata, oppure un movimento **senza rata** sul loro documento. Una rata che nessuno ha
toccato ha residuo uguale all'importo, cioè dentro la banda per costruzione, e chiederlo a una
funzione sarebbe lavoro per una risposta nota.

⚠️ Il terzo ramo non si può togliere: il nucleo dei saldi imputa alle rate anche i movimenti
senza rata, quindi una rata può uscire dalla banda senza che nessun movimento la nomini (130
incassati senza rata su rate da 30 e 70: la seconda va a −30). Senza quel ramo l'elenco
tacerebbe proprio dove serve.

⭐ La formula del saldo **non è ricopiata**: la vista chiama il nucleo
`fn_get_saldi_rate` **una** volta sull'insieme dei candidati. Due copie della regola darebbero prima o poi due
risposte diverse, e la divergenza si vedrebbe come un elenco che segnala ciò che il guard ha
lasciato passare.

---

### ⚠️ Sui fatti, non sulle intenzioni

Contano i **movimenti registrati**, non le righe ancora in lavorazione: una riga dichiarata e
non registrata non ha ancora fatto danno, e metterla qui vorrebbe dire chiedere a qualcuno di
guardare una cosa che potrebbe non succedere mai. `in_lavorazione` c'è comunque **come
colonna**, per chi legge la riga e si chiede «e questo?».

Allo stesso modo le righe forzate sono la **traccia**, non il criterio: una rata può essere fuori
capienza **senza che nessuno abbia forzato niente**, perché bastano due incassi legittimi
arrivati sullo stesso documento. Per questo `righe_forzate` e `motivi_forzatura` sono colonne,
non condizioni.

---

### L'elenco si guarda per decidere

La riga porta i riferimenti del documento (anno, serie, numero, billing account, emittente) e
`numero_documento`, dalla sede unica `fn_numero_documento_fattura`: il contatore nudo sarebbe
ambiguo fra una fattura 1 e una nota di credito 1 dello stesso anno. Per decidere serve sapere
di chi si sta parlando.

Le rate che compaiono qui sono la materia prima del **processo rimborsi**: un documento il cui
residuo ha cambiato segno è un credito, e le tre strade (riporto, rimborso, compensazione)
partono da [vw_eccedenze_da_sistemare](/dbzero/pagamenti/views/vw_eccedenze_da_sistemare).

---

### 🔒 `security_invoker`, da ripetere a ogni ricreazione

Senza, PostgreSQL la azzera a ogni `CREATE OR REPLACE` e la vista tornerebbe a girare coi
diritti del proprietario: chiunque vedrebbe le rate di **tutti** gli emittenti. Con l'invoker,
la RLS su `vendite.fatture` e `vendite.fatture_scadenze` filtra da sé.

---

### Test

* `db/pgtap/pagamenti/test-abbinamento-rata.sql` — i test 13 e 14: la vista mostra la rata
  sovra-incassata con il suo motivo, e anche il verso contrario.
* `db/pgtap/vendite/test-nc-rata-unica-v1.sql` — i test da 10 a 13: sulla rata negativa della
  nota di credito i due motivi escono nel verso giusto, e la riga porta `numero_documento` e la
  natura del documento.

---

### Note di migrazione

* 2026-08-22 — nasce insieme al guard di capienza che ammette la forzatura. Il piano la
  chiamava `vw_rate_sovra_incassate`.
* 2026-09-17 — la banda passa da un intervallo a estremi fissi a segno e valore assoluto, la
  stessa forma del guard: sulle rate positive il risultato non cambia, sulla nota di credito i
  due motivi, prima invertiti, escono giusti. Il saldo arriva dal nucleo `fn_get_saldi_rate` in
  una chiamata sull'insieme (prima `fn_get_saldo_rata` per ogni rata), e i candidati includono
  i documenti con movimenti senza rata.
* 2026-09-18 — la riga porta `numero_documento` e la natura del documento: il giorno prima la
  sfumatura della nota di credito era stata affidata all'etichetta senza darle la natura.

---

{% include-markdown "signature-core.md" %}
