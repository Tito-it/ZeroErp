## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — gli indirizzi del soggetto, su cui scatta
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice della natura
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — il predicato che legge
> * [anagrafiche.fn_check_tipo_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_check_tipo_indirizzo_soggetto) — la check con cui la madre lo anticipa
> * [anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo) — il guard gemello sugli indirizzi del ruolo
> * [anagrafiche.fn_check_cambio_natura_soggetto](/dbzero/anagrafiche/funzioni/fn_check_cambio_natura_soggetto) — chi giudica gli indirizzi già scritti quando cambia la natura
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — i due strati degli indirizzi e le loro regole

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_indirizzi_soggetti_guard_tipo_indirizzo` rifiuta un indirizzo del soggetto di un tipo che la
natura di dettaglio del soggetto non ammette. È il presidio della regola sullo strato del soggetto, qualunque
strada scriva la tabella.

---

### Che cosa giudica

Scatta prima della scrittura, alla nascita dell'indirizzo e quando ne cambia il tipo. Legge la natura del
soggetto e chiede al predicato `anagrafiche.fn_tipo_indirizzo_ammesso_per_natura`, sul giorno operativo; non
legge mai la matrice da sé. Un soggetto senza natura, o una natura senza righe di matrice, lascia gli indirizzi
liberi. Senza soggetto o senza tipo non giudica niente: lo dicono i NOT NULL.

Il tipo già presente non è affar suo: lo rifiuta l'indice unico, e prima ancora la check della madre.

---

### Il rifiuto parla come la check

Il codice, il campo da evidenziare (`tipo_indirizzo_id`) e i valori della frase (la natura e il tipo, per
descrizione; gli id nel contesto) sono quelli del motivo `TIPO_NON_AMMESSO_DALLA_NATURA` della check: chi
scrive dalla madre riceve lo stesso errore prima della scrittura, chi salta la madre lo riceve da qui. Lo stesso
codice lo solleva il guard degli indirizzi del ruolo quando è la natura del soggetto a non ammettere il tipo.

---

{% include-markdown "it/dbzero/anagrafiche/_tipo-indirizzo-ammesso.md" %}

---

### Codici errore

* `E_TIPO_INDIRIZZO_TIPO_SOGGETTO_NON_PERMESSO` — la natura del soggetto non ammette il tipo.

---

### Test

* `db/pgtap/anagrafiche/test-check-tipo-indirizzo-v1.sql` — la frase del guard da una strada che salta la madre,
  coi valori natura e tipo.

---

### Note di migrazione

* 2026-11-14 — il guard smette di leggere la matrice e chiede al predicato, estratto perché la stessa regola
  la legga il cambio di natura.

---

{% include-markdown "signature-core.md" %}
