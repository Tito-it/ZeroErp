## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_guard_validazione`

### 🎯 Scopo Principale
(rev 2026-08-21)

Le **condizioni su una transizione che la matrice non sa esprimere**, perché
dipendono da colonne della riga e non dalla coppia di stati. Sono due, e stanno
insieme perché sono la stessa specie:

1. **entrando in `VALIDATA`** — se la distinta dichiara un totale, la somma delle
   righe deve corrispondere;
2. **uscendo da `VALIDATA` verso `BOZZA`** — solo se la distinta è `MANUALE`.

⚠️ **Chi legge la sola matrice non vede queste regole.** È il motivo per cui i due
codici errore esistono e per cui i loro messaggi nominano il totale e l'origine:
senza, l'operatore leggerebbe «transizione ammessa» in un posto e un rifiuto
nell'altro, senza capire quale dei due mente.

---

### ⭐ 1) La quadratura scatta al gesto «ho finito», non alla registrazione

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

### Quando si attiva
* `BEFORE UPDATE OF stato_id` su `pagamenti.vendite_contabili`.

### ⚠️ Error handling
* `E_CONTABILE_TOTALE_DICHIARATO_NON_QUADRA` (`DATO_ERRATO`, 400) — il messaggio
  dice **quanto** è stato dichiarato e **quanto** sommano le righe;
* `E_CONTABILE_RIAPERTURA_NON_MANUALE` (`CONFLITTO_STATO`, 409) — il messaggio
  nomina l'origine in parole («arrivata da un file», «prodotta dal sistema»).

### ⚠️ Ordine fra i quattro guard della testata
I `BEFORE ROW` scattano in ordine alfabetico: `guard_chiusura` →
`guard_ente_centro` → `guard_transizione` → `guard_validazione`. ⭐ È l'ordine
giusto: **la transizione si valuta prima delle sue condizioni**, così chi tenta un
passaggio inesistente legge «non ammessa» e non un dettaglio sulla quadratura di
una transizione che comunque non poteva fare.

{% include-markdown "signature-core.md" %}
