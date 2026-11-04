## 📘 Documentazione Concettuale – Funzione `dbops.fn_get_child_fk_col`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_run_automations_attivo](/dbzero/dbops/funzioni/fn_run_automations_attivo) — il runner che la usava, e che oggi ricava la colonna da solo
> * [dbops.fn_foreign_keys_info](/dbzero/dbops/funzioni/fn_foreign_keys_info) — le chiavi esterne di una tabella, con le colonne

---

### 🎯 Scopo Principale

Dato l'identificativo di un vincolo di chiave esterna, restituisce il nome della **prima** colonna
del lato figlio. Restituisce nullo se il vincolo non esiste.

---

### ⚠️ Solo la prima colonna

Per una chiave esterna su più colonne la funzione restituisce la colonna in prima posizione e tace
sulle altre. Chi ha bisogno di tutte le colonne non può usarla.

La funzione non verifica che il vincolo passato sia davvero una chiave esterna: su un vincolo d'altro
tipo restituisce la prima colonna di quel vincolo.

---

### Oggi non la chiama nessuno

La usava `dbops.fn_run_automations_attivo` per sapere su quale colonna figlia montare i trigger di
attivazione. Il runner oggi ricava la colonna nella stessa interrogazione che elenca le chiavi
esterne, e considera solo quelle su una colonna sola. La funzione resta come attrezzo di
consultazione.

---

{% include-markdown "signature-core.md" %}
