## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali) — il regime e le due colonne della conferma
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_emittenti_fiscali_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_regime_conferma) — il trigger che scrive la conferma

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma` impedisce di scrivere da fuori la conferma del regime
fiscale di un emittente: `regime_fiscale_confermato_il` e `regime_fiscale_confermato_da` le scrive solo il
database, da una dichiarazione del regime.

---

### ⭐ Una conferma scritta a mano direbbe una cosa non vista

Data e autore li deriva `anagrafiche.trgfn_emittenti_fiscali_regime_conferma` quando qualcuno scrive il regime.
Un valore scritto direttamente sarebbe una conferma senza dichiarazione, o un autore che non è chi ha scritto. Il
guard rifiuta invece di sovrascrivere: chi scrive quelle colonne ha capito male il contratto, e una
sovrascrittura silenziosa glielo nasconderebbe.

* **Alla creazione**: una delle due colonne valorizzata è rifiutata. La creazione non conferma mai.
* **Alla modifica**: è rifiutato un `UPDATE` che **cambia** una delle due colonne. Conta il valore, non la
  menzione: un salvataggio che riscrive tutta la riga con i valori che ha già passa.

---

### ⚠️ Parla prima del trigger che deriva

Il guard sta nella fascia `a10`, la derivazione nella `a20`: qui la riga porta ancora i valori del chiamante. Se
il guard parlasse dopo, vedrebbe i valori appena derivati e rifiuterebbe ogni dichiarazione.

Il CHECK `chk_emittenti_fiscali_regime_conferma_coppia` (le due colonne insieme, e un autore non vuoto) resta per
le strade che i trigger non percorrono.

---

### Codici errore

* `E_EMITTENTE_REGIME_CONFERMA_DERIVATA` — la conferma scritta da fuori. Lo produce un componente che scrive
  ancora le due colonne, non chi compila un modulo; il segnaposto è la sigla dell'emittente.

---

### Test

* `db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` (casi 29-33) — la conferma scritta alla creazione e
  alla modifica, rifiutata; la riga riscritta con gli stessi valori, che passa.

---

### Note di migrazione

* 2026-10-02 — nasce, quando la conferma passa dal form al database.

---

{% include-markdown "signature-core.md" %}
