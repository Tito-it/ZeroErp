## 📘 Documentazione Concettuale – Vista `magazzino.vw_disponibilita`

> 👀 **Vedi anche**
>
Approfondimento tabelle e viste:
> • [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — il registro sommato
> • [magazzino.movimenti_attesi](/dbzero/magazzino/tabelle/movimenti_attesi) — i blocchi (e il loro drill-down: sono le righe `APERTA`)
> • [magazzino.vw_disponibilita_articolo](/dbzero/magazzino/views/vw_disponibilita_articolo) — la stessa cosa per articolo, sommata sui magazzini
>
Approfondimento funzioni:
> • [script.fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita) — la stessa formula, usata per rifiutare
>
Guide: brief `brief-db-magazzino-lotto-2-motore` (§4.6, M-3, D-L2-j)

---
### 🎯 Scopo Principale

(rev 2026-09-18 — Lotto 2 del magazzino)

**Il numero su cui si decide**: quanto c'è, quanto è promesso, quanto se ne può ancora usare —
per articolo e magazzino, in colonne:

| Colonna | Che cos'è |
| --- | --- |
| `giacenza` | la somma del registro (`vw_giacenza`) |
| `bloccata` | la somma **firmata** dei blocchi aperti (attesi `APERTA` **in uscita**, `qta < 0`): un numero negativo |
| `disponibile` | `giacenza + bloccata` — la **somma**, mai «meno»: i blocchi arrivano già col loro verso |
| `n_blocchi` | quanti sono |

Il nome «situazione merce» in vendite è preso e risponde a un'altra domanda (quanto è uscito,
tornato, fatturato di un ordine): qui è la **disponibilità**.

⚠️ **Un atteso in entrata non è un blocco.** La merce in arrivo non entra in `bloccata`:
farebbe uscire merce promessa da un arrivo non ancora avvenuto. Le colonne «impegnata»,
«potenziale», «in arrivo» **non ci sono** di proposito: entreranno con la vista che le sa
riempire (il satellite del ciclo acquisti), e il nome della vista non cambierà. Una colonna a
`NULL` che il nome promette è un campo vuoto che il template afferma.

⭐ Un articolo con un blocco e **senza movimenti** compare (giacenza 0, disponibile negativo):
la vista è un `FULL JOIN` fra registro e blocchi, non una lettura del solo registro.

È la stessa formula che [fn_check_disponibilita_uscita](/dbzero/script/funzioni/fn_check_disponibilita_uscita)
usa per rifiutare un'uscita — con una differenza: la vista conta **tutti** i blocchi aperti,
la check esclude quelli di chi chiede.

### Legge con gli occhi di chi interroga

`security_invoker`: la row level security del registro e degli attesi (via magazzino) passa
attraverso, e un operatore vede i magazzini del proprio emittente. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

Presidio: `db/pgtap/magazzino/test-vw-disponibilita-v1.sql`.

---

### Storia

* 2026-09-18 — nasce con il Lotto 2 (`20260918-24`).

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
