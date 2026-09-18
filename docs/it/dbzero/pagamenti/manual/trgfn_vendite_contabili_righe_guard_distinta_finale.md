## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale`

### 🎯 Scopo Principale
(rev 2026-08-22)

Impedire che una riga contabile finisca — o **torni utile** — sotto una distinta
in stato **finale** (`CHIUSA` o `ANNULLATA`).

### 🔴 Il difetto, in tre negazioni
Una riga appesa lì dentro:

* **non entra** nel saldo contabile — la funzione che lo calcola esclude le righe
  la cui testata è finale;
* **non entra** nel saldo movimenti — non è registrata;
* **non verrà mai registrata** — la registrazione parte dalla testata.

È **denaro dichiarato che non compare da nessuna parte**. E la differenza fra il
residuo e la copertura la legge come «manca copertura»: il **fondo fattura si
rigenera**.

⚠️ **E il filtro che sembrava proteggere non protegge**: le righe di una distinta
chiusa sono già registrate, quindi escluse comunque. L'unica cosa che quel filtro
riesce a escludere è **proprio la riga anomala**. *Un filtro che nasconde ciò che
non sa gestire sembra un presidio finché non si guarda che cosa esclude davvero.*

### Regole applicate — quattro mosse, non una
Sotto una distinta finale una riga può diventare un problema in quattro modi, e
chiuderne uno solo non serve a niente:

1. **nascendoci** (INSERT di una riga attiva);
2. essendo **riattivata** (`attivo` da falso a vero);
3. essendo **spostata** lì da un'altra distinta (`contabile_id` cambiato);
4. ⭐ **diventandoci pronta da registrare** — restando dov'è (dal 2026-08-22).

> ⭐ **La quarta è nata con la madre del posting.** Fino al lotto 4 non era
> raggiungibile: una distinta si chiudeva a mano, e chi la chiudeva sapeva che
> cosa ci lasciava dentro. Adesso la chiusura è la **conseguenza** del
> registrare, e sotto possono restare righe «da abbinare» — che il guard di
> chiusura non considera un ostacolo, deliberatamente, *«o la distinta non si
> chiuderebbe mai»*.
>
> Abbinarne una il giorno dopo produrrebbe **denaro dichiarato e pronto sotto
> una distinta che non si registra più**: il posting parte dalla testata, e una
> chiusa la rifiuta. È il danno di sempre, dalla porta che il difetto originale
> non aveva nominato.

⚠️ **Ciò che non si rifiuta**: le altre scritture su una riga già lì. Rifiutare
tutto impedirebbe perfino di correggere il motivo di sospensione di una riga di una
distinta annullata — e, dalla quarta mossa in poi, impedirebbe di **dire che cosa
ne è stato** di quel denaro (sospenderla, scartarla), che è l'unica cosa che
resta da fare.

⚠️ **Non blocca il posting**, e vale la pena saperlo per due ragioni
indipendenti: lo stato «registrata» **non è** uno stato pronto, e la distinta è
ancora `VALIDATA` quando la madre muove le righe.

ℹ️ La domanda *«questo stato è pronto da registrare?»* si fa al **catalogo**
(`is_postabile`), non a un elenco di stati scritto dentro il guard: è la stessa
scelta del guard gemello sui dati (`richiede_abbinamento`).

### ⭐ La quarta mossa ha UNA porta (dal 18-09-2026, D20-b)

Una `SOSPESA` sotto una distinta **registrata** ha un futuro:
[pagamenti.fn_posta_riga_tardiva](/dbzero/pagamenti/funzioni/fn_posta_riga_tardiva)
la abbina e la registra nello stesso gesto. Per farlo la porta ad `ABBINATA` —
così girano tutti i guard dell'abbinamento — e a **questo** guard si presenta con
la GUC transazionale `app.registrazione_tardiva_riga_id = <id>`: la quarta mossa
lascia passare **solo** quella riga, **solo** in quella transazione, **solo**
nel ramo del cambio di stato. Le altre tre mosse non leggono la GUC: la tardiva
non fa nascere, non riattiva, non sposta.

⛔ Un `UPDATE` a mano di una sospesa verso uno stato pronto resta rifiutato; la
GUC settata su un **altro** id non apre; dopo la madre la porta è richiusa
(`test-posta-riga-tardiva-v1` 16-18). La regola resta vera: sotto una chiusa
nessuna riga *«pronta e mai registrata»* — perché non esiste più il momento in
cui sta pronta ad aspettare. Precedente della forma: `app.cessazione_automatica`.

### Le porte sono due
Questa è la porta d'**ingresso**. La porta d'**uscita** — *chiudere* una distinta
che ha ancora righe registrabili — è la strada che capita davvero, e la chiude
`pagamenti.trgfn_vendite_contabili_guard_chiusura`.

### Quando si attiva
* `BEFORE INSERT OR UPDATE` su `pagamenti.vendite_contabili_righe`.

### ⚠️ Error handling
* `E_RIGA_CONTABILE_DISTINTA_FINALE` (`CONFLITTO_STATO`, 409).

### ⚠️ Nota per chi porterà la RLS su `pagamenti`
Il guard **legge la testata**. Quando lo schema avrà le policy di riga, quella
lettura va riguardata: un guard che legge sotto RLS **non distingue «non lo vedo»
da «è di un altro»**, e il rimedio registrato nel progetto è una funzione
`SECURITY DEFINER`.

{% include-markdown "signature-core.md" %}
