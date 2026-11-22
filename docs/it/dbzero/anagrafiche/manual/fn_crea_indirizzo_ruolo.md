## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_crea_indirizzo_ruolo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — la riga che la funzione scrive
> * [config.tipi_ruolo_tipi_indirizzo](/dbzero/config/tabelle/tipi_ruolo_tipi_indirizzo) — i tipi che il tipo di ruolo ammette
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento) — la grammatica dell'indirizzo
> * [anagrafiche.fn_indirizzo_elemento_dettaglio](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_dettaglio) — il dettaglio, se l'indirizzo non è libero
> * [anagrafiche.fn_check_tipo_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_ruolo) — il giudizio sul tipo
> * [anagrafiche.trgfn_guard_istanza_del_ruolo](/dbzero/anagrafiche/funzioni/trgfn_guard_istanza_del_ruolo) — l'istanza dello stesso soggetto
> * [anagrafiche.fn_crea_indirizzi_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_ruolo) — la plurale, che scrive da questa
> * [anagrafiche.fn_crea_copie_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_copie_indirizzo_ruolo) — la copia verso il ruolo, che scrive da questa
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — la gemella del soggetto
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — le tre forme e i tipi

---

### 🎯 Scopo Principale

`anagrafiche.fn_crea_indirizzo_ruolo` scrive un indirizzo di un ruolo, o di una sua istanza, e restituisce l'id della
riga. È la sede unica dell'inserimento in `anagrafiche.indirizzi`: ci passano la plurale e la copia di un indirizzo.

---

### L'indirizzo e la sua chiave

L'indirizzo è un oggetto con la grammatica di `anagrafiche.fn_indirizzo_elemento`, la stessa della gemella del
soggetto: il tipo, per id o per codice interno, e l'indirizzo libero, un dettaglio già risolto o una via da risolvere.
Se l'elemento porta insieme un testo libero e un dettaglio, **vale il libero**, e la riga nasce libera.

In più, facoltativa, l'**istanza** (`istanza_utility_id`): senza, l'indirizzo è del ruolo; con, è di quel servizio
del ruolo. Ruolo e istanza sono la chiave della riga, e un tipo è unico dentro la sua chiave: lo stesso tipo può stare
sul ruolo e su ognuna delle sue istanze.

⭐ L'istanza la legge questa funzione, non la grammatica comune: un indirizzo del soggetto non ha istanze. Per la
stessa ragione la plurale, che passa dalla grammatica, non accetta istanze.

---

### ⭐ Il tipo lo giudica la check, prima di scrivere

Prima dell'inserimento la madre chiede a `anagrafiche.fn_check_tipo_indirizzo_ruolo` i motivi per cui quel tipo non
si può scrivere su quella chiave, e solleva il primo, col campo `tipo_indirizzo_codice_interno`. I motivi sono tre,
in quest'ordine:

1. la chiave (il ruolo, o quell'istanza) ha già un indirizzo di quel tipo;
2. il tipo di ruolo non lo ammette;
3. la natura del soggetto del ruolo non lo ammette.

Il giorno è quello operativo, lo stesso dei guard. La metà della check che dà i motivi,
`anagrafiche.fn_check_tipo_indirizzo_ruolo_su_contesto`, è la stessa che leggono il picker della chiave
(`anagrafiche.fn_tipi_indirizzo_proponibili_ruolo`) e il guard della tabella: ciò che il picker propone, la madre
accetta e il guard lascia passare sono la stessa regola. Restano sulla tabella, per ogni altra strada e contro due
scritture concorrenti, il guard `anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` e gli indici
`uq_indirizzi_ruolo_tipo_no_istanza` e `uq_indirizzi_ruolo_istanza_tipo`.

---

### Che cosa lascia alla tabella

* **L'istanza dello stesso soggetto**: un'istanza di un altro soggetto la rifiuta `anagrafiche.trgfn_guard_istanza_del_ruolo`
  (`E_ISTANZA_ALTRO_SOGGETTO`, campo `istanza_utility_id`). È una regola della riga, che vale anche per le modifiche,
  e la madre non la ripete.
* **La forma dell'indirizzo libero** la dice `anagrafiche.trgfn_indirizzi_guard_forma_libera`.
* **Gli indirizzi obbligatori** del ruolo li pretendono i guard differiti, al COMMIT.
* **Il permesso** lo decide l'applicazione.

---

### Codici errore

* `E_SOGGETTO_RUOLO_NON_TROVATO` — il ruolo non esiste.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — l'indirizzo non è un oggetto.
* `E_CAMPO_NON_AMMESSO` — una chiave che un indirizzo non ha, col suo nome.
* `E_TIPO_INDIRIZZO_NON_TROVATO` — il codice del tipo manca o non esiste.
* `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE` — la chiave ha già quel tipo.
* `E_TIPO_INDIRIZZO_NON_PERMESSO` — il tipo di ruolo non ammette quel tipo.
* `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` — la natura del soggetto non ammette quel tipo.
* `E_ISTANZA_ALTRO_SOGGETTO` — dal guard della tabella.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-singolare-e-plurale-v1.sql` — l'indirizzo del ruolo e quello di un'istanza, il
  tipo già presente, la chiave estranea, il ruolo che non c'è.
* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — la check chiamata dalla madre, il tipo già presente sul
  ruolo e libero sull'istanza, la riga scaduta.
* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` — l'istanza di un altro soggetto.

---

### Note di migrazione

* 2026-10-19 — nasce, e la plurale scrive le sue righe da lei: l'inserimento ha una sede sola, e l'istanza entra solo
  da qui.

---

{% include-markdown "signature-core.md" %}
