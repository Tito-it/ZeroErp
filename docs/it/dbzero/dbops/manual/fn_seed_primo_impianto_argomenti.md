## 📘 Documentazione Concettuale – Funzione `dbops.fn_seed_primo_impianto_argomenti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [script.trgfn_seed_primo_impianto](/dbzero/script/funzioni/trgfn_seed_primo_impianto) — chiamante: il trigger legge i suoi argomenti da qui
> * [dbops.fn_seed_primo_impianto_divergenze](/dbzero/dbops/funzioni/fn_seed_primo_impianto_divergenze) — chiamante: confronta gli argomenti vivi con gli attesi
> * [dbops.fn_run_automations_seed_primo_impianto](/dbzero/dbops/funzioni/fn_run_automations_seed_primo_impianto) — chiamante: compone gli argomenti del trigger che monta
> * [dbops.fn_seed_elenco_colonne](/dbzero/dbops/funzioni/fn_seed_elenco_colonne) — chiamata: legge ciascun elenco della forma `COLONNA`
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

* `[0]` — la forma: `RIGA`, `COLONNA`, `SOLO_INSERIMENTO` o `FIGLIA`.
* Nella forma `COLONNA`, `[1]` le colonne del software e `[2]` quelle dell'installazione, separate da
  virgola. I due elenchi non sono vuoti, non si sovrappongono e non nominano colonne libere.
  Ciascun elenco lo legge [fn_seed_elenco_colonne](/dbzero/dbops/funzioni/fn_seed_elenco_colonne),
  la stessa lettura del trigger: gli spazi e le voci vuote non contano, e un elenco assente è vuoto,
  quindi rifiutato.
  Facoltativo, `[3]` le **colonne derivate**: quelle dell'installazione che il database deriva da sé
  (non vuote, tutte dentro `[2]`). La funzione le valida e non le restituisce: le legge il trigger,
  come colonna e padre della forma `FIGLIA`, e la firma resta quella che leggono gli altri.
* Nella forma `FIGLIA`, `[1]` la colonna della figlia che porta l'`id` del padre e `[2]` il padre,
  nella forma `schema.tabella`. La funzione ne controlla solo la forma del nome: colonna e padre li
  legge il trigger, dopo questa validazione, e un padre che non esiste lo ferma il trigger.
* Nelle forme `RIGA` e `SOLO_INSERIMENTO` non ci sono altri argomenti.

---

### Che cosa restituisce

Una riga sola:

* `valido`, `dettaglio` — se il montaggio rispetta la grammatica, e se no perché;
* `forma`, `colonne_software`, `colonne_installazione` — gli argomenti letti; gli elenchi sono
  `NULL` in tutte le forme tranne `COLONNA`;
* `colonne_libere` — sempre presente: `id`, `meta`, `data_insert`, `user_insert`, `data_update`,
  `user_update`, `tx_id`. Sono le colonne che nessun elenco nomina e che non contano per
  «personalizzata».

Non solleva: decide il chiamante. Il trigger solleva `E_TRIGGER_ARGOMENTI_INVALIDI`, il confronto
segnala la divergenza.

---

### Test

* `db/pgtap/dbops/test-fn-seed-elenco-colonne-v1.sql`, asserzioni 5-7 — un elenco del software o
  dell'installazione `NULL` è rifiutato; gli elenchi letti sono quelli del building block.

La grammatica la esercitano anche i test che passano dal trigger e dal confronto:

* `db/pgtap/config/test-seed-primo-impianto-installazione-v1.sql`, asserzioni 1-3 — le due tabelle
  montate, nelle forme solo inserimento e per colonna, senza divergenze;
* `db/pgtap/dbops/test-seed-primo-impianto-software-v1.sql`, asserzioni 21-22 — una colonna non
  classificata;
* `db/pgtap/ui/test-seed-primo-impianto-ui-software-v1.sql`, asserzioni 8-11 — la forma `FIGLIA`:
  valida con colonna e padre, non valida con due argomenti, col padre senza schema o con la colonna
  `NULL`; asserzioni 19-20 — il quarto argomento, le colonne derivate.

---

### Note di migrazione

* 2026-11-17 — nasce (`brief-db-seed-primo-impianto-non-si-riscrive`).
* 2026-11-20 — la forma `FIGLIA`, con la firma invariata.
* 2026-11-22 — le colonne derivate, quarto argomento della forma `COLONNA`; gli elenchi letti da
  `dbops.fn_seed_elenco_colonne`, e un elenco `NULL` non passa più per valido.

---

{% include-markdown "signature-core.md" %}
