## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_guard_validazione`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — dove è montato, e la colonna `origine` da cui le regole pendono
> * [pagamenti.transizioni_stati_contabile](/dbzero/pagamenti/tabelle/transizioni_stati_contabile) — la matrice, che queste condizioni completano
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — la bandiera `righe_lavorabili` dello stato d'arrivo
>
> Approfondimento funzioni:
>
> * [script.fn_check_contabile_validabile](/dbzero/script/funzioni/fn_check_contabile_validabile) — i motivi che impediscono di validare
> * [script.fn_raise_primo_motivo_se_presente](/dbzero/script/funzioni/fn_raise_primo_motivo_se_presente) — solleva il primo motivo della check
> * [pagamenti.trgfn_vendite_contabili_guard_transizione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_guard_transizione) — il guard della matrice
> * [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — il congelamento delle righe sotto un'annullata

---

### 🎯 Scopo Principale

Le condizioni su una transizione della distinta che la matrice non sa esprimere, perché
dipendono da colonne della testata o dalle sue righe e non dalla coppia di stati. Sono tre,
e stanno insieme perché sono la stessa specie:

1. **entrando in `VALIDATA`**: nessuna riga ancora da lavorare e, se la distinta dichiara un
   totale, la somma delle righe deve corrispondere;
2. **da `VALIDATA` a `BOZZA`**: solo se la distinta è `MANUALE`;
3. **entrando in uno stato che congela le righe** (`ANNULLATA`): solo se la distinta è
   `MANUALE`.

⚠️ **Chi legge la sola matrice non vede queste regole.** È il motivo per cui i codici errore
sono propri e le frasi nominano il totale e l'origine: senza, l'operatore leggerebbe
«transizione ammessa» in un posto e un rifiuto nell'altro, senza capire quale dei due mente.

---

### ⭐ Entrando in `VALIDATA`: la check decide, il guard solleva

`VALIDATA` vuol dire *«ogni riga è stata guardata»*. Il guard chiama
[script.fn_check_contabile_validabile](/dbzero/script/funzioni/fn_check_contabile_validabile)
e solleva il codice del **primo** motivo, nell'ordine della check:

1. **righe non lavorate**: righe attive in uno stato che il catalogo dichiara non lavorato
   (`IMPORTATA`, `DA_ABBINARE`). La sospesa è stata guardata e passa;
2. **la quadratura** col totale dichiarato.

Il guard **non fa i conti da sé**: la stessa check la legge il dettaglio della distinta, così
«Porta a VALIDATA» si spegne col motivo e il pulsante e il rifiuto non possono divergere.

⚠️ Il totale dichiarato che la check riceve è **quello che sta entrando** con l'aggiornamento,
non una rilettura dalla tabella: il guard gira prima della scrittura, e una rilettura
verificherebbe il totale di ieri.

---

### La quadratura scatta al gesto «ho finito», non alla registrazione

È una decisione, non un dettaglio: se hai dichiarato 1.500 € e ne hai digitati 1.480, te lo
dice **lì**, mentre sei ancora nel flusso di inserimento, invece che al momento di
registrare, quando il lavoro è finito e il contesto è perso.

⚠️ **E non può stare in un trigger di riga.** Durante un caricamento le righe entrano una
alla volta e la somma torna **solo alla fine**: un trigger di riga rifiuterebbe la prima riga
di ogni import. È la regola del progetto — *il guard tiene la riga, la madre tiene
l'uguaglianza*. Qui il momento in cui la somma è completa lo dichiara l'operatore, ed è il
passaggio a `VALIDATA`.

⚠️ **La somma conta tutte le righe attive, `SCARTATA` comprese.** Quel denaro **è arrivato**:
la quadratura dice *«abbiamo letto tutto ciò che c'era»*, non *«tutto è nostro»*. Se una riga
scartata uscisse dalla somma, il **primo scarto romperebbe la quadratura di una distinta
sana**.

ℹ️ Senza totale dichiarato non si controlla la somma: sulla distinta manuale è facoltativo
per decisione, e i totali si vedono comunque al momento di registrare.

---

### ⭐ La riapertura è solo della manuale

`VALIDATA → BOZZA` è seminata come **ammessa** nella matrice, perché una matrice non porta
condizioni. La restrizione vive qui: una distinta **automatica** è la copia di un file ed è
immutabile; una **generata** non si corregge, si rigenera.

---

### ⭐ L'annullo è solo della manuale

Una distinta **generata** (fondi fattura, sistemazioni) la governa il giro che l'ha
prodotta: per togliere un fondo si cancella il fondo, per togliere una sistemazione si
annulla la sistemazione. Annullarne la testata a mano era un gesto che il giro disfaceva: al
ricalcolo successivo della fattura il sync dei fondi **spostava** la riga in una distinta
nuova, e il denaro «mai successo» tornava a contare. Con le righe congelate sotto
un'annullata
([trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale)),
quel gesto diventerebbe un blocco: un errore sul ricalcolo, o un fondo che non si cancella
più.

* ⭐ La regola guarda la **bandiera** dello stato d'arrivo (`righe_lavorabili = false` sul
  [catalogo](/dbzero/pagamenti/tabelle/vendite_contabili_stati)), non il nome `ANNULLATA`: la
  collisione col giro nasce dal congelamento delle righe, e uno stato nuovo che le
  congelasse la riprodurrebbe identica.
* ⚠️ È una whitelist sull'origine: l'**automatica** (l'import non esiste ancora) cade nel
  rifiuto, finché il cantiere dell'import non decide.
* Il codice è proprio: quello della riapertura dice «non si riapre».

---

### ⚠️ L'ordine fra i guard della testata

I trigger `BEFORE ROW` sull'aggiornamento della testata scattano in ordine di nome:
`guard_emittente_scope` → `guard_ente_centro` → `guard_transizione` → `guard_validazione` →
`guard_verifica_chiusura`. ⭐ **La transizione si valuta prima delle sue condizioni**, così chi
tenta un passaggio inesistente legge «non ammessa» e non un dettaglio sulla quadratura, o sulle
righe pronte, di una transizione che comunque non poteva fare. Vale per questo guard e per
quello della chiusura.

---

### Codici errore

* `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE` — entrando in `VALIDATA` ci sono righe
  attive non lavorate; la frase dice **quante**, il dettaglio porta gli id.
* `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` — entrando in `VALIDATA` la somma delle righe
  non è il totale dichiarato; la frase dice **quanto** è dichiarato e **quanto** sommano.
* `E_CONTABILE_RIAPERTURA_NON_MANUALE` — `VALIDATA → BOZZA` su una distinta non manuale; la
  frase nomina l'origine in parole («arrivata da un file», «prodotta dal sistema»).
* `E_CONTABILE_ANNULLO_NON_MANUALE` — una distinta non manuale entra in uno stato che
  congela le righe; stessa frase della riapertura.
* i guard di chiamata della check (`E_CONTABILE_NON_TROVATA`,
  `E_PAGAMENTI_CHIAMATA_NON_VALIDA`), che dal guard non si raggiungono.

---

### Test

* `db/pgtap/pagamenti/test-contabile-validabile-v1.sql` — i due motivi della check e il loro
  ordine, il guard che solleva la frase del primo, il dichiarato che entra e non quello di
  ieri, la scartata nella somma, la riapertura della manuale.
* `db/pgtap/pagamenti/test-contabili-origine-e-quadratura.sql` — la quadratura col
  dichiarato, le scartate comprese, la riapertura rifiutata a una distinta non manuale.
* `db/pgtap/pagamenti/test-righe-distinta-annullata-congelate-v1.sql` — l'annullo della
  manuale da `BOZZA` e da `VALIDATA`, e il rifiuto `E_CONTABILE_ANNULLO_NON_MANUALE`.

---

### Note di migrazione

* 2026-08-21 — nasce con le due regole della quadratura entrando in `VALIDATA` e della
  riapertura della sola manuale.
* 2026-09-18 — entrando in `VALIDATA` si chiede anche che ogni riga sia stata guardata, e i
  conti passano alla check condivisa con il dettaglio della distinta. Fino ad allora si validava con righe `DA_ABBINARE` sotto,
  che alla chiusura restavano senza strada.
* 2026-09-30 — l'annullo diventa un gesto della sola manuale, con un codice proprio.

---

{% include-markdown "signature-core.md" %}
