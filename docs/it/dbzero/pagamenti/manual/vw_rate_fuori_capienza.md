## 📘 Documentazione Concettuale – Vista `pagamenti.vw_rate_fuori_capienza`

### 🎯 Scopo Principale

(rev 2026-09-17)

L'elenco delle rate il cui residuo è **uscito dalla banda**: ha attraversato lo
zero, oppure supera l'importo della rata in valore assoluto.

⭐ **Dal 17-09-2026 la banda non è più `[0, importo]`.** Quella era la trappola
del §5 del brief madre — un intervallo a estremi fissi che su una rata
**negativa** (la nota di credito, P-5) si inverte — sciolta sul guard da D14-c e
non su questa vista. Ora la forma è quella del guard: **segno e valore
assoluto**, senza estremi da invertire. Sulle rate positive è identica a prima;
sulla nota di credito i due motivi escono giusti — prima uscivano invertiti.

🔴 **Esiste per una ragione precisa.** Il guard della rata **accetta** la
registrazione fuori capienza, purché qualcuno la dichiari. Senza un elenco a
valle quella dichiarazione sarebbe *«un modo per nascondere, non per
registrare»*: fra sei mesi quei pagamenti non li ritroverebbe nessuno.

⇒ È per questo che la vista sta **nello stesso lotto** del guard che permette la
forzatura, e non in un lotto dopo.

---

### ⭐ Due motivi, non uno — e il nome del piano ne diceva uno solo

| `motivo` | Che cosa è successo | Esempio (fattura) | Esempio (nota di credito) |
| --- | --- | --- | --- |
| `SOVRA_INCASSATA` | il residuo ha **attraversato lo zero**: è entrato più del dovuto — su una nota di credito, rimborsato più del credito | rata 100, incassato 110 | rata −20, rimborsato 30 |
| `MOVIMENTO_CONTRARIO` | il residuo **supera l'importo** in valore assoluto: è uscito denaro dove non era entrato — su una nota di credito, è entrato denaro invece di uscire | rata 100, rimborso 30 senza incasso | rata −20, il cliente paga 15 |

Il vocabolario resta a **due** valori: la sfumatura della nota di credito la
dice l'etichetta, non un terzo codice.

> ⭐ Il piano la chiamava `vw_rate_sovra_incassate`. Sarebbe stato un nome che
> **dice meno di ciò che l'elenco contiene**: fuori capienza si esce in due
> versi, e il secondo è esattamente il caso che ha fatto cadere l'asimmetria
> della decisione originale — *pagato 110, rimborso 15 invece di 10*. Chiamarla
> «sovra incassate» avrebbe lasciato fuori dal nome proprio il caso che ha
> cambiato la regola.

### Come si decide chi entra

Il residuo **fuori dalla banda**: `sign(saldo) <> sign(importo) AND saldo <> 0`
(ha attraversato lo zero) oppure `abs(saldo) > abs(importo)` (supera). Non è un
terzo criterio inventato qui: è la **stessa regola del guard letta a
posteriori** — *un movimento riduce ciò che manca e non lo supera* — applicata
al risultato invece che al singolo movimento.

⭐ **I candidati includono i documenti con movimenti senza rata.** Dal 17-09-2026
il nucleo dei saldi imputa quei movimenti alle rate: una rata può uscire dalla
banda senza che nessun movimento la nomini (130 senza rata su 30 + 70: la
seconda va a −30). Il pre-filtro ha un terzo ramo per questo — senza, l'elenco
tacerebbe proprio dove serve. Il saldo arriva dal nucleo in **una** chiamata
sull'insieme dei candidati, non più in `LATERAL` per rata.

⭐ **`numero_documento`** in coda, dalla sede unica `fn_numero_documento_fattura`:
la lista mostrava il contatore nudo, ambiguo fra una fattura 1 e una nota di
credito 1 dello stesso anno.

⚠️ **Sui fatti, non sulle intenzioni**: contano i **movimenti registrati**, non
le righe ancora in lavorazione. Una riga dichiarata e non registrata non ha
ancora fatto danno, e metterla qui vorrebbe dire chiedere a qualcuno di guardare
una cosa che potrebbe non succedere mai.

ℹ️ `in_lavorazione` c'è comunque **come colonna**, per chi legge la riga e si
chiede «e questo?».

### ⚠️ Le righe forzate sono la traccia, non il criterio

Una rata può essere fuori capienza **senza che nessuno abbia forzato niente**:
due incassi legittimi arrivati sullo stesso documento bastano. Per questo
`righe_forzate` e `motivi_forzatura` sono **colonne**, non condizioni.

---

### Regole principali

* La formula del saldo **non è ricopiata**: la vista chiama
  `pagamenti.fn_get_saldo_rata` in `LATERAL`. Due copie della regola darebbero
  prima o poi due risposte diverse, e la divergenza si vedrebbe come *un elenco
  che segnala ciò che il guard ha lasciato passare*.
* Il costo si limita **prima** della `LATERAL`: entrano solo le rate che hanno
  almeno un movimento o una riga forzata. Una rata che nessuno ha toccato ha
  residuo uguale all'importo, cioè dentro la banda per costruzione — chiederlo a
  una funzione sarebbe lavoro per una risposta nota.
* Espone anche i riferimenti del documento (anno, serie, numero, cliente,
  emittente): l'elenco si guarda per **decidere**, e per decidere serve sapere
  di chi si sta parlando.

### ⚠️ `security_invoker=on`, e va ri-specificata

Senza, PostgreSQL la azzera a ogni `CREATE OR REPLACE` e la vista tornerebbe a
girare coi diritti del proprietario: chiunque vedrebbe le rate di **tutti** gli
emittenti. Con l'invoker, la RLS su `vendite.fatture` e `vendite.fatture_scadenze`
filtra da sé.

### Dove porta

Le rate che compaiono qui sono la materia prima del **processo rimborsi** (la
slice 4 del cantiere incassi): un documento il cui residuo ha cambiato segno è
un credito del cliente, e le tre strade — riporto, rimborso, compensazione —
hanno già tutte il loro meccanismo.

{% include-markdown "signature-core.md" %}
