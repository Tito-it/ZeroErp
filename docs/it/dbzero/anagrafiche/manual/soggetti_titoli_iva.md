## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_titoli_iva`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [config.tipi_titolo_iva](/dbzero/config/tabelle/tipi_titolo_iva) — di che specie è il titolo
> • [anagrafiche.soggetti_titoli_iva_ambiti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_ambiti) — per cosa vale
> • [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — quanto plafond è stato consumato
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — a chi il titolo è stato presentato
> • [config.iva](/dbzero/config/tabelle/iva) — il codice che prende il posto di quello ordinario
>
Approfondimento funzioni:
> • [anagrafiche.fn_consuma_plafond_titolo_iva](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva) — chi consuma il tetto
> • [anagrafiche.fn_check_titolo_iva_ambito](/dbzero/anagrafiche/funzioni/fn_check_titolo_iva_ambito) — chi verifica che l'ambito stia in piedi

---

### 🎯 Scopo Principale

(rev 2026-08-29 — tabella nata il 2026-08-29)

Qui si registrano i **titoli** per cui un cliente non paga l'IVA ordinaria: una
dichiarazione d'intento, una dichiarazione di uso industriale del gas,
un'agevolazione per disabilità, la qualifica di cooperativa sociale.

**Un titolo non è un flag: è un documento.** Ha una prova, una data di inizio e una
di fine, dice **a chi** è stato presentato e dice **per cosa vale**. Registrato una
volta, da quel momento vale da solo su tutti i documenti finché è valido — nessuno
lo digita più.

---

### ⭐ Il principio che questa tabella realizza

> *L'influenza del cliente sull'IVA passa **sempre** da un titolo, mai da un default.*

È la decisione `D7` del cantiere, e spiega una cosa che altrimenti sembrerebbe
strana: fino al 2026-08-29 esisteva `anagrafiche.clienti.iva_id`, una colonna che
prometteva di dire «questo cliente ha un'IVA sua». **È stata tolta e non
sostituita** da una colonna equivalente sul soggetto: spostarla avrebbe riprodotto
lo stesso difetto un piano più su — *un valore che vince su tutto perché nessuno gli
ha detto dove fermarsi*.

L'aliquota ordinaria la decide la **merce** e il suo uso. Il cliente può soltanto
**sostituirla**, e solo mostrando una carta.

---

### 🔴 Perché ci sono due «proprietari»: il soggetto **e** l'emittente

Il titolo **appartiene al soggetto** — è lui l'esportatore abituale, non un suo
contratto e non una sua fornitura. Un cliente con tre forniture ha **una**
dichiarazione, non tre.

⚠️ Ma una dichiarazione d'intento non è un'etichetta che il cliente si appende
addosso: è un documento che **presenta a un fornitore preciso**, con un protocollo
suo e un importo suo. Lo stesso esportatore abituale che compra da due società
emittenti presenta **due dichiarazioni**, ognuna col suo plafond.

⛔ **Senza la colonna dell'emittente, i due plafond si consumerebbero da un solo
contatore.** Non darebbe nessun errore: si vedrebbe solo su un plafond esaurito
prima del dovuto — cioè su precisamente il numero che l'Agenzia delle Entrate
verifica.

**Proprietario: il soggetto. Destinatario: l'emittente. Due colonne, stessa riga**
(decisione `D10-bis`).

---

### ⚠️ L'ambito: «vale per tutto» oppure «vale per queste voci»

`ambito` è **dichiarato**, mai dedotto da una colonna vuota:

| valore | significato |
| --- | --- |
| `TUTTO` | il titolo copre ogni riga di documento |
| `RISTRETTO` | copre solo ciò che dicono le righe di `soggetti_titoli_iva_ambiti` |

⭐ **Le parole «su questa riga» sono la sostanza, non una precisazione** (`D12`). Un
titolo non accende un documento intero: si valuta **riga per riga**. Un cliente con
un'agevolazione limitata a due articoli, su un documento di dieci righe, ottiene
**due righe agevolate e otto ordinarie**.

⛔ **Un titolo `RISTRETTO` senza righe figlie non copre niente, ed è voluto.** Il
caso si può costruire solo in due passaggi — prima il titolo, poi il suo ambito —
quindi un vincolo lo rifiuterebbe a metà strada. Chi calcola l'IVA lo legge come
«nessun articolo nell'ambito» e lascia l'aliquota ordinaria: è la direzione sicura.

---

### ⚠️ L'anti-sovrapposizione è un vincolo vero solo su metà dei casi

Due titoli dello stesso tipo, dello stesso cliente, verso lo stesso emittente e
validi nello stesso periodo sono un'ambiguità: non c'è modo di dire quale si
applica. La chiave dell'ambiguità è però **(soggetto, emittente, tipo, ambito)**, e
l'ambito dei titoli ristretti vive in una **tabella figlia** — un vincolo di
database non la può leggere.

Divisione **dichiarata**, non subita:

| caso | chi lo chiude |
| --- | --- |
| `ambito = 'TUTTO'` | `ex_soggetti_titoli_iva_no_overlap`, un `EXCLUDE USING gist` **reale** |
| `ambito = 'RISTRETTO'` | il guard `trgfn_soggetti_titoli_iva_ambiti_guard`, che confronta anche livello e oggetto |

⚠️ **Due titoli di tipo diverso possono convivere legittimamente**, ed è il caso da
non bloccare per errore: il tipo è in chiave apposta. Quale dei due vince su una
riga lo decide `D13` — **articolo > categoria di merce > tutto**, la stessa cascata
degli indirizzi — e sta nel risolutore, non qui.

---

### Il plafond, e perché non basta una colonna

Solo la dichiarazione d'intento ha un **tetto che si consuma**. Il tipo lo dichiara
(`config.tipi_titolo_iva.ha_plafond`), la riga porta il valore.

⚠️ La regola «il plafond esiste se e solo se il tipo ne prevede uno» attraversa due
tabelle, quindi **non è un `CHECK`**: la tiene `trgfn_soggetti_titoli_iva_guard_coerenza`,
e la tiene sui **due versi** — un tetto assente dove serve, e un tetto presente dove
non serve. Il secondo è quello che si dimentica: un numero che nessuno consuma, e
che chi lo legge scambia per un limite.

`imponibile_utilizzato` dice quanto tetto è stato usato. È **memorizzato**, come
chiede `P3`, ma non è un numero scritto sopra a un altro: è la **somma** del
registro dei movimenti (`D5`). Ogni fattura ne mangia un pezzo, ogni nota di credito
ne restituisce uno, ogni forzatura manuale è una riga **con il suo motivo**.

⭐ Si memorizza l'imponibile **usato** e non il residuo (`P4`), ed è la scelta più
verificabile: quel numero si confronta con la somma degli imponibili fatturati,
mentre un residuo si confronta con niente. Il residuo è aritmetica.

---

### Chi può vederli

La tabella ha **row security**: un operatore vede e scrive solo i titoli presentati
a un emittente del suo perimetro (`rls_soggetti_titoli_iva_ef_whitelist`). Senza,
l'elenco — protocolli e plafond compresi — sarebbe comune a tutti gli emittenti, e
**si vedrebbe come un dato e non come un errore**: una lista più lunga del vero non
la mette in dubbio nessuno.

---

### ⛔ Due cose che sembrano IVA e non stanno qui

* **`split_payment` e `cliente_pa`** non sono titoli: non cambiano l'aliquota,
  cambiano **chi versa l'imposta all'erario** (in fattura elettronica sono
  l'`EsigibilitaIVA`). Vivono su [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti);
* **l'aliquota ordinaria** la dice la merce e il suo uso — articolo, catena del
  prezzo, [config.tipi_utenze](/dbzero/config/tabelle/tipi_utenze). Il cliente non
  entra **mai** in quella domanda.

---

### 📌 Stato

La **sede** esiste ed è collaudata. Chi la legge — il risolutore IVA a due stadi —
è la voce `I2` dello stesso cantiere e **non è ancora scritto**: oggi nessun
documento cambia aliquota per effetto di un titolo registrato qui.

Cantiere: `brief-db-be-iva-risolutore-e-regime-cliente.md`, `I7` / `D10`.

---

{% include-markdown "signature-core.md" %}
