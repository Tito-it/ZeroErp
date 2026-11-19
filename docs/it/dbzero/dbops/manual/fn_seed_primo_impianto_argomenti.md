## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_primo_impianto_argomenti`

> **Ultimo aggiornamento**: 18 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — chiamante: il trigger legge i suoi argomenti da qui
> * [dbops.fn_seed_primo_impianto_divergenze](/dbzero/dbops/funzioni/fn_seed_primo_impianto_divergenze) — chiamante: confronta gli argomenti vivi con gli attesi
> * [dbops.fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto) — chiamante: compone gli argomenti del trigger che monta
>
> Approfondimento tabelle:
>
> * [dbops.automazione_seed_primo_impianto](/dbzero/dbops/tabelle/automazione_seed_primo_impianto) — da dove vengono forma ed elenchi

---

### 🎯 Scopo Principale

La **grammatica** degli argomenti di un trigger montato su
[trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto), in un posto solo.
Il trigger, il confronto delle divergenze e il runner la leggono da qui: se ognuno la leggesse da
sé, un argomento letto in due modi farebbe sembrare giusto un trigger montato male.

---

### La grammatica

* `[0]` — la forma: `RIGA`, `COLONNA` o `SOLO_INSERIMENTO`.
* Nella forma `COLONNA`, `[1]` le colonne del software e `[2]` quelle dell'installazione, separate da
  virgola. I due elenchi non sono vuoti, non si sovrappongono e non nominano colonne libere.
* Nelle altre due forme non ci sono altri argomenti.

---

### Che cosa restituisce

Una riga sola:

* `valido`, `dettaglio` — se il montaggio rispetta la grammatica, e se no perché;
* `forma`, `colonne_software`, `colonne_installazione` — gli argomenti letti;
* `colonne_libere` — sempre presente: `id`, `meta`, `data_insert`, `user_insert`, `data_update`,
  `user_update`, `tx_id`. Sono le colonne che nessun elenco nomina e che non contano per
  «personalizzata».

Non solleva: decide il chiamante. Il trigger solleva `E_TRIGGER_ARGOMENTI_INVALIDI`, il confronto
segnala la divergenza.

---

### Test

Nessun pgTAP diretto. La grammatica la esercitano i test che passano dal trigger e dal confronto:

* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql`, asserzioni 1-3 — le due tabelle
  montate, nelle forme solo inserimento e per colonna, senza divergenze;
* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql`, asserzioni 21-22 — una colonna non
  classificata.

---

### Note di migrazione

* 2026-11-17 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive`).

---

{% include-markdown "signature-core.md" %}
