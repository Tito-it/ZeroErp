## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_soggetto_dettaglio_tipi_indirizzo](/dbzero/config/tabelle/tipi_soggetto_dettaglio_tipi_indirizzo) — la matrice della natura, col flag obbligatorio
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_tipo_indirizzo_ammesso_per_natura](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_ammesso_per_natura) — la riga attiva e valida
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto) — i mancanti del soggetto, col ripiego
> * [anagrafiche.fn_crea_indirizzi_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzi_soggetto) — la copia degli obbligatori
> * [anagrafiche.fn_tipi_indirizzo_proponibili_natura](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_natura) — il picker di un soggetto da creare
> * [anagrafiche.fn_tipi_indirizzo_proponibili_soggetto](/dbzero/anagrafiche/funzioni/fn_tipi_indirizzo_proponibili_soggetto) — il picker di un soggetto salvato
> * [anagrafiche.fn_tipo_indirizzo_obbligatorio_per_ruolo](/dbzero/anagrafiche/funzioni/fn_tipo_indirizzo_obbligatorio_per_ruolo) — la gemella del livello ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la regola R9, gli indirizzi obbligatori

---

### 🎯 Scopo Principale

`anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura` dice se un tipo d'indirizzo è obbligatorio per una natura
di soggetto, in un giorno dato: vero quando la matrice della natura ha la riga del tipo col flag obbligatorio, e
quel giorno la riga è attiva e valida.

---

### ⭐ Una domanda, una sede

Sul livello del soggetto, «questo tipo è obbligatorio per la natura?» ha una risposta sola, e sta qui. La
leggono i mancanti del soggetto (`anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto`), la copia degli
obbligatori (`anagrafiche.fn_crea_indirizzi_soggetto`), la colonna «obbligatorio» dei due picker
(`anagrafiche.fn_tipi_indirizzo_proponibili_natura` e `_soggetto`), i builder dei soggetti di prova
(`dbops.fn_pgtap_crea_soggetto_pf` e `_pg`) e il provisioning dei dati di sviluppo
(`anagrafiche.fn_provisiona_dati_di_sviluppo`). Così ciò che si copia, ciò che il form segna obbligatorio e
ciò che il guard pretende sono la stessa cosa, anche per una riga scaduta o spenta.

La riga conta solo se il predicato della natura (`anagrafiche.fn_tipo_indirizzo_ammesso_per_natura`) la
ammette quel giorno: una riga obbligatoria spenta, o fuori dalla sua finestra di validità, non chiede niente.

---

### Natura assente: niente è obbligatorio

Un soggetto senza natura non deve avere nessun indirizzo: la risposta è falso.

---

### Il ripiego non conta qui

Il ripiego di una riga obbligatoria è un'alternativa al tipo, non un secondo tipo obbligatorio: questa funzione
non lo guarda. Se il ripiego basti, e se la natura lo ammetta, lo dicono i mancanti del soggetto.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-requisito-nuovo-v1.sql` (1, 2) — la funzione esiste, ed è
  l'unica che legge «obbligatorio» dalla matrice della natura.

---

### Note di migrazione

* 2026-11-24 — nasce come sede unica della domanda: prima la facevano sette posti in tre modi, e i builder di
  prova e il provisioning leggevano il flag senza la finestra di validità.

---

{% include-markdown "signature-core.md" %}
