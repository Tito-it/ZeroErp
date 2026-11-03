## 📘 Documentazione Concettuale – Vista `pagamenti.vw_eccedenze_da_sistemare`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — il registro di ciò che si è deciso, compagno di questo elenco
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — i documenti candidati, con il loro totale a pagare
>
> Approfondimento viste:
>
> * [pagamenti.vw_rate_fuori_capienza](/dbzero/pagamenti/views/vw_rate_fuori_capienza) — lo stesso sguardo sulle singole rate
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — il saldo del documento, che la vista legge e non riscrive
> * [pagamenti.fn_conferma_sistemazione](/dbzero/pagamenti/funzioni/fn_conferma_sistemazione) — dove la stessa eccedenza si ricontrolla al momento della conferma
>
> Guide:
>
> * [Gestione dei pagamenti](/guide/gestione-dei-pagamenti) — il processo dei rimborsi, per chi non è tecnico

---

### 🎯 Scopo Principale

L'elenco del processo rimborsi: i documenti il cui residuo ha cambiato segno, cioè che in valore assoluto hanno incassato più del loro totale.

Si legge insieme al suo registro:

```text
vw_eccedenze_da_sistemare   →  che cosa c'è DA FARE
sistemazioni                →  che cosa è STATO FATTO
```

---

### ⭐ La condizione non ha estremi fissi, ed è ciò che la salva

Un documento entra quando il **segno del saldo è l'opposto del segno del totale**. Su
una **fattura** vuol dire saldo negativo; su una **nota di credito** vuol dire saldo positivo. La
regola è la stessa perché **non nomina né l'una né l'altra**.

⚠️ Un intervallo fra zero e il totale, su un documento a credito, diventa **vuoto**: è la
trappola che questa forma evita per costruzione, la stessa della regola di capienza sulle rate.

---

### ⭐ «Per cliente» senza perdere il documento

La compensazione ha senso solo guardando il cliente, ma l'azione si fa **su un documento**. La
vista fa entrambe le cose: **una riga per documento**, e le colonne del cliente
(`eccedenza_cliente`, `documenti_cliente`) calcolate sull'insieme dei documenti dello stesso
cliente presso lo stesso emittente. Ordinata per cliente si legge come un elenco per cliente, e
ogni riga resta azionabile. ⚠️ Una vista già aggregata avrebbe perso proprio ciò che serve per
agire.

---

### ⭐ `chi_e_in_credito`: la colonna che evita l'errore di verso

| Documento | Residuo | Chi è in credito |
| --- | --- | --- |
| fattura (totale positivo) | negativo: ha incassato **di più** | il **cliente** |
| nota di credito (totale negativo) | positivo: si è restituito **di più** | l'**azienda** |

Farlo dedurre a chi legge è chiedergli di rifare il ragionamento ogni volta, e sbagliarlo
significa **rimborsare denaro che si deve incassare**.

---

### ⚠️ I due contatori segnalano, non filtrano

Fra la decisione e l'effetto ci sono **due** passi, non uno:

```text
BOZZA        →  nessuno ha ancora fatto niente
CONFERMATA   →  il documento c'è, ma non è ancora REGISTRATO
(registrato) →  i movimenti esistono, e la riga sparisce DA SOLA
```

⛔ Un documento con un atto in bozza **resta nell'elenco**: la decisione è presa ma il denaro non
si è mosso. Toglierlo sarebbe **nascondere**, ed è l'opposto di «la vista presenta, la persona
decide».

⚠️ Per questo i contatori sono due (`sistemazioni_in_bozza`, `sistemazioni_confermate`): con un
solo segno sulla bozza, un documento con l'atto già confermato e la distinta ancora da
registrare comparirebbe **senza nessun segno**, indistinguibile da uno su cui nessuno ha mai
guardato.

---

### ⭐ I saldi si leggono, non si conservano

* **È una vista, non una tabella.** Materializzarla richiederebbe un automatismo che la tiene
  aggiornata, cioè una rincorsa fra il dato e la sua copia.
* Il saldo lo dà `pagamenti.fn_get_saldo_fattura`, non una somma riscritta qui: due definizioni
  della stessa cosa divergono al primo aggiustamento. La vista ne usa solo il saldo.
* Si parte dai documenti con un totale diverso da zero e con **almeno un movimento attivo**:
  senza denaro registrato il residuo coincide col totale e non può aver cambiato segno.
* ⚠️ La vista dipende dalla forma del risultato della funzione del saldo: cambiarne le colonne
  vuol dire togliere e ricreare la vista nello stesso passo, così il database non resta mai
  senza l'una o senza l'altra.

---

### 🔒 `security_invoker`, da ripetere a ogni ricreazione

La vista legge tabelle con le policy (fatture, movimenti, sistemazioni): senza
`security_invoker` girerebbe come proprietario, mostrando a ciascun emittente i documenti
dell'altro. ⚠️ Ricreandola, `security_invoker` e i `GRANT` vanno ripetuti: si perdono **in
silenzio**.

---

### Test

* `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql` — i test 2 e 3: la vista vede la
  fattura sovra-incassata con l'eccedenza e con chi è in credito, e un atto in bozza si conta
  senza far sparire la riga.

---

### Note di migrazione

* 2026-08-22 — prima stesura, insieme al registro `sistemazioni`.
* 2026-08-25 — ricreata senza cambiare nessuna colonna: `fn_get_saldo_fattura` è passata da due
  numeri a quattro, e per sostituire la funzione bisognava prima togliere la vista che la usa.
  Le due cose hanno viaggiato nello stesso passo.

---

{% include-markdown "signature-core.md" %}
