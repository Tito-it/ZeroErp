## 📘 Documentazione Concettuale – Funzione `script.fn_get_contabile_stato_origine`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta di cui risponde stato e origine
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — le righe, che si vedono anche dalla fattura
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_distinta_finale) — la usa per lo stato della distinta, nelle cinque mosse
> * [pagamenti.trgfn_vendite_contabili_righe_guard_contenuto](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_righe_guard_contenuto) — la usa nella porta 2, per origine e stato
> * [script.fn_get_sistemazione_di_contabile](/dbzero/script/funzioni/fn_get_sistemazione_di_contabile) — la sorella con la stessa forma: un dato della distinta, fuori dalla row security

---

### 🎯 Scopo Principale

Risponde lo **stato** e l'**origine** di una distinta contabile, letti fuori dalla row security.
È il building block dei guard delle righe contabili, che devono giudicare la distinta anche
quando chi scrive la riga non la vede.

---

### 🔴 Perché i guard non possono leggere la distinta da soli

Una riga contabile si vede per due strade: dall'emittente della **distinta** oppure da quello
della **fattura**. La seconda serve alla riga «mista», cioè denaro arrivato sulla distinta di
un'azienda e abbinato alla fattura di un'altra. Il modello la ammette: la scrive chi ha in
perimetro tutte e due le aziende (un super admin), e l'azienda della fattura la deve vedere per
capire dove è finito il suo incasso.

Chi lavora per l'azienda della fattura vede e scrive la riga, ma **non vede la distinta**. I
guard delle righe girano con i diritti di chi scrive: letta sotto la row security, per lui la
distinta non c'è, e un guard che non la trova lascia passare. Questa funzione gira con i diritti
del proprietario delle tabelle, e la distinta la trova sempre.

---

### ⚠️ Risponde il minimo, e non il numero

Risponde soltanto lo stato e l'origine: quanto basta per sapere se le righe di quella distinta
si lavorano ancora. Il **codice** della distinta non lo risponde. I guard lo leggono a parte,
sotto la row security, e lo usano solo nel messaggio: chi non vede la distinta ne legge l'id,
non il numero.

Non allarga niente: il chiamante nomina una distinta che è già la testata della riga che sta
scrivendo. Che possa poi toccarla lo decidono le policy e i guard di perimetro.

Una distinta inesistente risponde zero righe. Per un guard non è un caso di perimetro: la
chiave esterna della riga la rende impossibile.

---

### ⚠️ Dipende dalla row security non forzata

Funziona perché la row security delle tabelle è abilitata e **non forzata**, e il proprietario
della funzione è quello delle tabelle. Con un `FORCE ROW LEVEL SECURITY` va rivista, come le
sorelle `script.fn_get_sistemazione_di_contabile` e `script.fn_resolve_emittente_fiscale_id`.

---

### Test

* `db/pgtap/pagamenti/test-righe-guard-distinta-vista-dalla-fattura-v1.sql` — i due guard che la
  usano, sulla riga mista vista dalla fattura; e che la funzione sia `SECURITY DEFINER` con il
  `search_path` fissato.

---

### Note di migrazione

* 2026-11-03 — nasce per i guard `guard_distinta_finale` e `guard_contenuto` (porta 2), che fino
  a quel giorno leggevano la distinta sotto la row security e tacevano sulla riga vista dalla
  fattura.

---

{% include-markdown "signature-core.md" %}
