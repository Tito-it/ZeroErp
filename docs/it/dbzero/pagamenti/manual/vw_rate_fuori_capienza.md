## 📘 Documentazione Concettuale – Vista `pagamenti.vw_rate_fuori_capienza`

### 🎯 Scopo Principale

(rev 2026-08-22)

L'elenco delle rate il cui residuo è **uscito dalla banda** `[0, importo]`.

🔴 **Esiste per una ragione precisa.** Il guard della rata **accetta** la
registrazione fuori capienza, purché qualcuno la dichiari. Senza un elenco a
valle quella dichiarazione sarebbe *«un modo per nascondere, non per
registrare»*: fra sei mesi quei pagamenti non li ritroverebbe nessuno.

⇒ È per questo che la vista sta **nello stesso lotto** del guard che permette la
forzatura, e non in un lotto dopo.

---

### ⭐ Due motivi, non uno — e il nome del piano ne diceva uno solo

| `motivo` | Che cosa è successo | Esempio |
| --- | --- | --- |
| `SOVRA_INCASSATA` | è entrato più del dovuto: il residuo è **negativo** | rata 100, incassato 110 |
| `MOVIMENTO_CONTRARIO` | è uscito denaro dove non era entrato: il residuo **supera l'importo** | rata 100, rimborso 30 senza incasso |

> ⭐ Il piano la chiamava `vw_rate_sovra_incassate`. Sarebbe stato un nome che
> **dice meno di ciò che l'elenco contiene**: fuori capienza si esce in due
> versi, e il secondo è esattamente il caso che ha fatto cadere l'asimmetria
> della decisione originale — *pagato 110, rimborso 15 invece di 10*. Chiamarla
> «sovra incassate» avrebbe lasciato fuori dal nome proprio il caso che ha
> cambiato la regola.

### Come si decide chi entra

Il residuo **fuori dalla banda** `[0, importo]`. Non è un terzo criterio
inventato qui: è la **stessa regola del guard letta a posteriori** — *un
movimento riduce ciò che manca e non lo supera* — applicata al risultato invece
che al singolo movimento.

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
