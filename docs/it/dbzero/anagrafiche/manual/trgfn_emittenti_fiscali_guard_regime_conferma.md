## 📘 Documentazione Concettuale – Trigger Function `anagrafiche.trgfn_emittenti_fiscali_guard_regime_conferma`

> 👀 **Vedi anche**
>
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [anagrafiche.trgfn_emittenti_fiscali_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_regime_conferma)

### 🎯 Scopo

(02-10-2026 — brief `brief-db-esigibilita-iva-per-cassa-emittente`, sezione 10)

**La conferma del regime fiscale non si scrive da fuori.** Data e autore li deriva il
trigger `a20`
[trgfn_emittenti_fiscali_regime_conferma](/dbzero/anagrafiche/funzioni/trgfn_emittenti_fiscali_regime_conferma)
da una dichiarazione del regime. Un valore scritto direttamente direbbe una cosa che
quel trigger non ha visto: una conferma senza dichiarazione, o un autore che non è
chi ha scritto.

Si rifiuta invece di sovrascrivere: chi scrive quelle colonne ha capito male il
contratto, e una sovrascrittura silenziosa glielo nasconderebbe.

### Regole

* Trigger `trg_emittenti_fiscali_a10_guard_regime_conferma_ins_upd`, `BEFORE INSERT`
  e `UPDATE OF regime_fiscale_confermato_il, regime_fiscale_confermato_da`.
* `INSERT` con una delle due colonne valorizzata: rifiutata. La creazione non
  conferma mai.
* `UPDATE` che **cambia** una delle due colonne: rifiutato. Conta il valore, non la
  menzione: un salvataggio che riscrive tutta la riga con i valori che ha già passa.
* ⚠️ Fascia `a10`, prima del trigger `a20` che deriva: qui `NEW` porta ancora i valori
  del chiamante. Se il guard parlasse dopo, vedrebbe i valori derivati e
  rifiuterebbe ogni dichiarazione.
* Il `CHECK chk_emittenti_fiscali_regime_conferma_coppia` resta, per le strade che i
  trigger non percorrono.

### Errore

`E_EMITTENTE_REGIME_CONFERMA_DERIVATA` (`TECNICO`): lo produce solo un componente
rimasto alla forma di D-11, non chi compila un modulo. Il segnaposto è il codice
dell'emittente.

### Test

`db/pgtap/vendite/test-esigibilita-iva-per-cassa-v1.sql` (casi 29-33).

---

{% include-markdown "signature-core.md" %}
