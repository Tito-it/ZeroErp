## 📘 Documentazione Concettuale – Vista `magazzino.vw_disponibilita`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti_attesi](/dbzero/magazzino/tabelle/movimenti_attesi) — i blocchi; il loro dettaglio sono le righe aperte
>
> Approfondimento viste:
>
> * [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — il registro sommato
> * [magazzino.vw_disponibilita_articolo](/dbzero/magazzino/views/vw_disponibilita_articolo) — la stessa cosa per articolo, sommata sui magazzini
>
> Approfondimento funzioni:
>
> * [script.fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita) — la stessa formula, usata per rifiutare un'uscita
> * [magazzino.fn_apri_blocco](/dbzero/magazzino/funzioni/fn_apri_blocco) — apre un blocco manuale
> * [magazzino.fn_libera_blocco](/dbzero/magazzino/funzioni/fn_libera_blocco) — lo libera

---

### 🎯 Scopo Principale

**Il numero su cui si decide**: quanto c'è, quanto è promesso, quanto se ne può ancora usare,
per articolo e magazzino.

Il nome «situazione merce» in vendite è preso e risponde a un'altra domanda (quanto è uscito,
tornato, fatturato di un ordine): qui è la **disponibilità**.

---

### La formula sta nelle colonne

* `giacenza` — la somma del registro, da [vw_giacenza](/dbzero/magazzino/views/vw_giacenza);
* `bloccata` — la somma **con il segno** dei blocchi aperti in uscita: è un numero negativo;
* `disponibile` — la giacenza **sommata** alla quota bloccata, mai «meno»: i blocchi
  arrivano già con il loro verso;
* `n_blocchi` — quanti blocchi aperti concorrono.

---

### ⚠️ Un atteso in entrata non è un blocco

La merce in arrivo non entra nella quota bloccata: farebbe uscire merce promessa da un arrivo
non ancora avvenuto. Le colonne «impegnata», «potenziale», «in arrivo» **non ci sono** di
proposito: entreranno con la vista che le sa riempire (il satellite del ciclo acquisti), e il
nome della vista non cambierà. Una colonna vuota che il nome promette è un campo vuoto che il
template afferma.

---

### ⭐ Un blocco senza movimenti compare lo stesso

Un articolo con un blocco e **senza movimenti** compare, con giacenza zero e disponibile
negativo: la vista unisce registro e blocchi tenendo le righe di entrambi, non legge il solo
registro.

---

### La stessa formula del controllo di uscita

È la formula che [fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita)
usa per rifiutare un'uscita, con una differenza: la vista conta **tutti** i blocchi aperti,
il controllo esclude quelli di chi chiede.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la row level security del registro e degli attesi (attraverso
il magazzino) passa attraverso, e un operatore vede i magazzini del proprio emittente.
Meccanismo comune: [Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Test

* `db/pgtap/magazzino/test-vw-disponibilita-v1.sql` — la formula in colonne, un blocco
  liberato che non conta più, l'articolo bloccato senza movimenti, l'assenza delle colonne
  «impegnata» e «in arrivo», la postura `security_invoker`.

---

### Note di migrazione

* 2026-09-18 — nasce con il Lotto 2 (`brief-db-magazzino-lotto-2-motore`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
