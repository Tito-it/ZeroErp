## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale`

### 🎯 Scopo Principale
(rev 2026-08-21)

Impedire che una riga contabile finisca sotto una distinta in stato **finale**
(`CHIUSA` o `ANNULLATA`).

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

### Regole applicate — tre mosse, non una
Sotto una distinta finale una riga può arrivare in tre modi, e chiuderne uno solo
non serve a niente:

1. **nascendoci** (INSERT di una riga attiva);
2. essendo **riattivata** (`attivo` da falso a vero);
3. essendo **spostata** lì da un'altra distinta (`contabile_id` cambiato).

⚠️ **Ciò che non si rifiuta**: le altre scritture su una riga già lì. Rifiutare
tutto impedirebbe perfino di correggere il motivo di sospensione di una riga di una
distinta annullata.

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
