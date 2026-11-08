## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_piva_libera`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — dove la partita IVA deve essere libera
>
> Approfondimento funzioni:
>
> * [script.fn_valida_partita_iva](/dbzero/script/funzioni/fn_valida_partita_iva) — il validatore di dominio, l'ultima parola sulla forma
> * [dbops.fn_pgtap_cf_libero](/dbzero/dbops/funzioni/fn_pgtap_cf_libero) — la gemella per il codice fiscale
> * [dbops.fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg) — la fixture che la usa per una persona giuridica
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — perché gli identificativi non si scrivono a mano

---

### 🎯 Scopo Principale

Restituisce una **partita IVA valida e non ancora usata** in `anagrafiche.soggetti`, pronta
per una fixture. Ha due firme: senza argomenti dà la prima libera, con un numero salta le
prime libere.

⭐ Il calcolo sta in una firma sola: quella senza argomenti è la firma con salto zero, e le
delega tutto. Due copie dello stesso ciclo, prima o poi, risponderebbero in due modi.

---

### ⭐ Valida e libera, come il codice fiscale

È la gemella di [fn_pgtap_cf_libero](/dbzero/dbops/funzioni/fn_pgtap_cf_libero), con la
stessa doppia garanzia. *Valida* perché la partita IVA ha un carattere di controllo che i
guard verificano. *Libera* perché l'identificativo fiscale di un soggetto è unico e i
soggetti lasciati da altre corse non si possono cancellare. La libertà si controlla su tutte
e tre le colonne fiscali del soggetto: partita IVA, codice fiscale e identificativo univoco.

La fixture calcola da sé la cifra di controllo, ma ogni candidato passa comunque dal
validatore di dominio: se un giorno la regola cambia, la fixture smette di trovare partite
IVA e lo dice, invece di restituirne una che il dominio rifiuta.

---

### ⚠️ Due partite IVA nella stessa istruzione: si salta

Un identificativo diventa occupato solo quando il soggetto che lo usa è scritto. Due chiamate
danno valori diversi solo se fra l'una e l'altra c'è la scrittura del soggetto: dentro una
sola istruzione non c'è nessuna scrittura in mezzo, quindi due chiamate senza argomenti
rispondono la **stessa** partita IVA, e la fixture si schianta sull'unicità dando la colpa al
test.

Per questo c'è la seconda firma: il numero dice quante partite IVA libere saltare, e una
fixture che ne vuole due distinte chiede la numero zero e la numero uno. Un numero mancante o
negativo è rifiutato. La firma è separata, e senza valore di default, di proposito: un
default renderebbe ambigue le chiamate senza argomenti già scritte.

---

### Codici errore

Nessun codice registrato: un numero di salto non valido, o nessuna partita IVA libera, sono
eccezioni senza codice sollevate dalla fixture.

---

### Test

Nessun pgTAP dedicato: la esercitano i test che costruiscono persone giuridiche, attraverso
[fn_pgtap_crea_soggetto_pg](/dbzero/dbops/funzioni/fn_pgtap_crea_soggetto_pg), e quelli dei
dati societari, che chiedono più partite IVA nella stessa istruzione.

---

### Note di migrazione

* 2026-08-18 — nasce con la bonifica della baseline pgTAP di vendite (`brief-db-bonifica-baseline-pgtap-vendite`); la firma con il salto arriva subito dopo, quando una fixture ha chiesto due partite IVA nella stessa istruzione.
* 2026-11-04 — la firma senza argomenti delega alla firma con salto zero, invece di ricopiarne il ciclo; il messaggio quando non trova una partita IVA libera ora nomina la firma con il salto (`brief-db-revisione-dbops`).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
