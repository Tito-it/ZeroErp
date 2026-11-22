## 📘 Documentazione Concettuale – Tabella `anagrafiche.categorie_clienti_listini`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.categorie_clienti](/dbzero/anagrafiche/tabelle/categorie_clienti) — le categorie che la matrice mappa
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — porta la categoria del cliente
> * [vendite.listini](/dbzero/vendite/tabelle/listini) — il listino scelto dalla riga
> * [config.classi_utenze](/dbzero/config/tabelle/classi_utenze) — la classe d'utenza, quando la riga la distingue
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_categorie_clienti_listini_guard_listino](/dbzero/anagrafiche/funzioni/trgfn_categorie_clienti_listini_guard_listino) — il listino è della utility e dell'azienda della riga
> * [script.fn_check_listino_documento](/dbzero/script/funzioni/fn_check_listino_documento) — la stessa domanda per contratti e offerte
> * [script.trgfn_guard_date_validita](/dbzero/script/funzioni/trgfn_guard_date_validita) — l'ordine delle due date
> * [vendite.fn_resolve_prezzo_listino_v2_esito](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2_esito) — il calcolo del prezzo che legge la matrice
>
> Guide:
>
> * [Gestione listini](/guide/gestione-listini) — dove la matrice sta nel calcolo del prezzo

---

### 🎯 Scopo Principale

`anagrafiche.categorie_clienti_listini` è la matrice che porta da una categoria di clienti al listino da
usare: per una categoria, una utility, un'azienda e (se serve) una classe d'utenza, in un periodo, dice quale
listino vale e con quale variazione.

Il calcolo del prezzo la legge per un billing account senza contratto individuale: se non trova una riga,
risponde `E_CATEGORIA_LISTINO_NON_MAPPATA`.

---

### Una riga per contesto e periodo

Il contesto della riga è la quadrupla categoria, utility, azienda (`emittente_soggetto_ruolo_id`) e classe
d'utenza. Fra le righe **attive** di uno stesso contesto i periodi non si sovrappongono
(`ex_categ_cli_listini_no_overlap`); una riga spenta non conta, e si tiene come memoria di una configurazione
passata. Il periodo è `validita`, calcolata da `valido_dal` e `valido_al` (aperto senza fine); l'ordine delle
due date lo controlla il guard comune delle date di validità.

---

### ⭐ La classe d'utenza vuota vale per tutte le altre

Una riga senza classe d'utenza è il **ripiego** del contesto: vale per ogni classe che non ha una riga sua. Il
calcolo del prezzo, fra le righe valide alla data, preferisce quella della classe del cliente e ricade su
quella senza classe. Per il vincolo di esclusione la classe vuota è un valore a sé: una riga specifica e il
ripiego convivono nello stesso periodo.

Dove le classi d'utenza non esistono (il commercio) le righe hanno sempre la classe vuota.

---

### La variazione è facoltativa

Senza variazione vale il prezzo del listino così com'è. Con la variazione, il tipo è una percentuale o un
valore fisso, e tipo e valore ci sono tutti e due o mancano tutti e due. Il prezzo fisso, che le promozioni
conoscono, qui non c'è: la matrice sposta un prezzo di listino, non lo sostituisce.

---

### ⭐ Il listino è della utility e dell'azienda della riga

Una riga «clienti dell'azienda A, servizio gas» può puntare solo a un listino dell'azienda A per il gas: lo
controlla `anagrafiche.trgfn_categorie_clienti_listini_guard_listino`, con la stessa domanda che contratti e
offerte fanno sul loro listino. Accanto, il guard comune utility-ruolo controlla che il tipo di ruolo
dell'azienda sia ammesso per quella utility, dove la utility lo dichiara, e due controlli al commit vogliono la categoria e il listino attivi.

---

### Chi vede la matrice

La tabella è in RLS, con una policy sola: l'**operatore** vede e scrive le righe dei listini delle aziende del
suo perimetro (`rls_categorie_clienti_listini_ef_whitelist`). L'azienda di una riga è letta dal suo listino.
Nessun altro ruolo applicativo vede la matrice.

---

### Codici errore

* `E_CATEGORIA_LISTINO_UTILITY_DIVERSA`, `E_CATEGORIA_LISTINO_EMITTENTE_DIVERSO` — il listino non è della
  utility o dell'azienda della riga (dal guard del listino).
* `E_UTILITY_RUOLO_NON_AMMESSO` — l'azienda della riga non è ammessa per la utility.
* `E_DATA_AL_MINORE_DAL` — la fine della validità precede l'inizio.

---

### Test

* `db/pgtap/anagrafiche/test-categorie-clienti-listini-v1.sql` — variazione, date, esclusione fra righe attive
  (anche con la classe vuota), la riga spenta che non partecipa, il periodo calcolato.
* `db/pgtap/anagrafiche/test-categorie-clienti-listini-guard-listino-v1.sql` — il listino della utility e
  dell'azienda della riga.
* `db/pgtap/rls/test-rls-listini-satelliti.sql` — il perimetro dell'operatore.
* `db/pgtap/vendite/test-fn-resolve-prezzo-listino-v2-v1.sql` — la matrice dentro il calcolo del prezzo.

---

### Note di migrazione

* 2026-05-14 — `validita` diventa una colonna generata da `valido_dal` e `valido_al`.
* 2026-10-16 — nasce il guard del listino: prima una riga verso il listino di un'altra azienda entrava, e lo
  sbaglio emergeva solo al passaggio in commessa.

---

{% include-markdown "signature-core.md" %}
