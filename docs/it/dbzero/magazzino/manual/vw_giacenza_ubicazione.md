## 📘 Documentazione Concettuale – Vista `magazzino.vw_giacenza_ubicazione`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.movimenti](/dbzero/magazzino/tabelle/movimenti) — il registro che la vista somma
> * [magazzino.ubicazioni](/dbzero/magazzino/tabelle/ubicazioni) — le posizioni dentro un magazzino
> * [magazzino.trasferimenti](/dbzero/magazzino/tabelle/trasferimenti) — lo spostamento interno, che qui si vede
>
> Approfondimento viste:
>
> * [magazzino.vw_giacenza](/dbzero/magazzino/views/vw_giacenza) — la stessa somma senza la posizione

---

### 🎯 Scopo Principale

**La giacenza per posizione**: la somma delle quantità del registro per articolo, magazzino
**e ubicazione**. La merce senza posizione dichiarata (ubicazione vuota) è un gruppo come
gli altri.

È la vista che dà senso allo spostamento interno: un trasferimento fra due ubicazioni dello
stesso magazzino scrive una coppia di movimenti, un'uscita e un'entrata. In
[vw_giacenza](/dbzero/magazzino/views/vw_giacenza) la coppia si annulla (la giacenza del
magazzino non cambia), qui si vede.

---

### Legge con gli occhi di chi interroga

La vista è `security_invoker`: la row level security del registro e dei magazzini passa
attraverso, e un operatore vede i magazzini del **proprio emittente**. Meccanismo comune:
[Linee guida SQL — sezione 10 RLS](/linee-guida-sql#10-row-level-security-rls).

---

### Test

* `db/pgtap/magazzino/test-valore-giacenza-forma-v1.sql` — due ubicazioni dello stesso
  magazzino restano distinte; la vista è `security_invoker`.

---

### Note di migrazione

* 2026-09-15 — prende la forma di oggi con il Lotto 1 (`brief-db-magazzino-lotto-1-terreno-vuoto`).
  Prima nessuna vista di magazzino era `security_invoker`.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}
