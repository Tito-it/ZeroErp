## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_guard_validazione`

### 🎯 Scopo Principale
(rev 2026-09-30)

Le **condizioni su una transizione che la matrice non sa esprimere**, perché
dipendono da colonne della riga e non dalla coppia di stati. Sono tre, e stanno
insieme perché sono la stessa specie:

1. **entrando in `VALIDATA`** — se la distinta dichiara un totale, la somma delle
   righe deve corrispondere;
2. **uscendo da `VALIDATA` verso `BOZZA`** — solo se la distinta è `MANUALE`;
3. **entrando in `ANNULLATA`** — solo se la distinta è `MANUALE` (dal 30-09-2026).

⚠️ **Chi legge la sola matrice non vede queste regole.** È il motivo per cui i due
codici errore esistono e per cui i loro messaggi nominano il totale e l'origine:
senza, l'operatore leggerebbe «transizione ammessa» in un posto e un rifiuto
nell'altro, senza capire quale dei due mente.

---

### ⭐ 1) Entrando in `VALIDATA`: la check decide, il guard solleva (dal 18-09-2026)

> **D20-a** — `VALIDATA` = *«ogni riga è stata guardata»*. Entrando in
> `VALIDATA` il guard chiama
> [script.fn_check_contabile_validabile](/dbzero/script/funzioni/fn_check_contabile_validabile)`(NEW.id, NEW.importo_dichiarato)`
> e solleva il codice del **primo** motivo con `fn_raise_primo_motivo_se_presente`:
>
> 1. **righe non lavorate** — righe attive in uno stato con `lavorata = false`
>    (`IMPORTATA`, `DA_ABBINARE`): `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE`,
>    con quante e gli id. La sospesa è stata guardata e passa;
> 2. **la quadratura** qui sotto, com'era — stesso codice, stessi valori.
>
> Il guard **non fa più i conti da sé**: la stessa check la legge il dettaglio
> della distinta (`can_validare`), così «Porta a VALIDATA» si spegne col motivo
> e il pulsante e il rifiuto non possono divergere. ⚠️ `NEW.importo_dichiarato`,
> non una rilettura: il guard gira `BEFORE ROW`, e il dichiarato che sta
> entrando non è ancora nella tabella — per questo la check lo prende come
> parametro. Fino al 18-09 si validava con righe `DA_ABBINARE` sotto, che alla
> chiusura restavano senza strada (brief §1).

#### La quadratura scatta al gesto «ho finito», non alla registrazione

È una decisione, non un dettaglio: se hai dichiarato 1.500 € e ne hai digitati
1.480, te lo dice **lì**, mentre sei ancora nel flusso di inserimento — invece che
al momento di registrare, quando il lavoro è finito e il contesto è perso.

⚠️ **E non può stare in un trigger di riga.** Durante un caricamento le righe
entrano una alla volta e la somma torna **solo alla fine**: un trigger di riga
rifiuterebbe la prima riga di ogni import. È la regola del progetto — *il guard
tiene la riga, la madre tiene l'uguaglianza*. Qui il momento in cui la somma è
completa lo dichiara l'operatore, ed è il passaggio a `VALIDATA`.

⚠️ **La somma conta TUTTE le righe attive, `SCARTATA` comprese.** Quel denaro **è
arrivato**: la quadratura dice *«abbiamo letto tutto ciò che c'era»*, non *«tutto è
nostro»*. Se una riga scartata uscisse dalla somma, il **primo scarto romperebbe la
quadratura di una distinta sana**.

ℹ️ Senza totale dichiarato non si controlla niente e si passa: sulla distinta
manuale è facoltativo per decisione, e i totali si vedono comunque al momento di
registrare.

---

### ⭐ 2) La riapertura è solo della manuale

`VALIDATA → BOZZA` è seminata come **ammessa** nella matrice, perché una matrice
non porta condizioni. La restrizione vive qui: una distinta **automatica** è la
copia di un file ed è immutabile; una **generata** non si corregge, si rigenera.

### ⭐ 3) L'annullo è solo della manuale (dal 30-09-2026, D-4)

Una distinta **generata** (fondi fattura, sistemazioni) la governa il giro che
l'ha prodotta: per togliere un fondo si cancella il fondo, per togliere una
sistemazione si annulla la sistemazione. Annullarne la testata a mano era un
gesto che il giro disfaceva: al ricalcolo successivo della fattura il sync dei
fondi **spostava** la riga in una distinta nuova, e il denaro «mai successo»
tornava a contare. Da quando sotto un'annullata le righe si leggono soltanto
([quinta mossa](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale)),
quel gesto sarebbe diventato un blocco: un errore sul ricalcolo, o un fondo che
non si cancella più.

* ⭐ La regola guarda la **bandiera** dello stato d'arrivo
  ([`righe_lavorabili = false`](/dbzero/pagamenti/tabelle/vendite_contabili_stati)),
  non il nome `ANNULLATA`: la collisione col giro nasce dal congelamento delle
  righe, e uno stato nuovo che le congelasse la riprodurrebbe identica.
* ⚠️ È una whitelist sull'origine: l'**automatica** (l'import non esiste ancora)
  cade nel rifiuto, finché il cantiere dell'import non decide.
* Il codice è proprio, `E_CONTABILE_ANNULLO_NON_MANUALE` (D-5): quello della
  riapertura dice «non si riapre».

### Quando si attiva
* `BEFORE UPDATE OF stato_id` su `pagamenti.vendite_contabili`.

### ⚠️ Error handling
* `E_CONTABILE_VALIDAZIONE_RIGHE_NON_LAVORATE` (`CONFLITTO_STATO`, 409) — dal
  18-09-2026, motivo 1 della check: il messaggio dice **quante** righe nessuno ha
  ancora lavorato, il dettaglio porta gli id;
* `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` (`DATO_ERRATO`, 400) — il messaggio
  dice **quanto** è stato dichiarato e **quanto** sommano le righe;
* `E_CONTABILE_RIAPERTURA_NON_MANUALE` (`CONFLITTO_STATO`, 409) — il messaggio
  nomina l'origine in parole («arrivata da un file», «prodotta dal sistema»);
* `E_CONTABILE_ANNULLO_NON_MANUALE` (`CONFLITTO_STATO`, 409) — dal 30-09-2026,
  stessi due valori della riapertura.

### ⚠️ Ordine fra i quattro guard della testata
I `BEFORE ROW` scattano in ordine alfabetico: `guard_chiusura` →
`guard_ente_centro` → `guard_transizione` → `guard_validazione`. ⭐ È l'ordine
giusto: **la transizione si valuta prima delle sue condizioni**, così chi tenta un
passaggio inesistente legge «non ammessa» e non un dettaglio sulla quadratura di
una transizione che comunque non poteva fare.

{% include-markdown "signature-core.md" %}
