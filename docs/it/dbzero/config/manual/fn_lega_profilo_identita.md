## 📘 Documentazione Concettuale – Funzione `config.fn_lega_profilo_identita()`

### 🎯 Scopo
(18-10-2026 — brief `brief-db-processi-accensione-per-ambiente`, 2b-1 lotto 8)

**Legare un'identità a un profilo di accesso.** Un'identità ha un profilo
solo: legarla di nuovo allo stesso profilo non cambia niente; legarla a un
profilo diverso, mentre ne ha già uno, è rifiutato dal vincolo della tabella,
non sostituito in silenzio.

È la sede unica del legame: la usano la creazione degli operatori (il super
admin), la creazione degli utenti tecnici, il backend e il provisioning dei
dati di sviluppo.

### 🔄 19-10-2026 — le gemelle

Il legame di un reparto e lo slegare (dall'identità e dal reparto) hanno ora le loro madri: [`fn_lega_profilo_reparto`, `fn_slega_profilo_reparto`, `fn_slega_profilo_identita`](/dbzero/config/manual/fn_lega_profilo_reparto) (R-BE-7, decisioni D-16b e D-16c di Tid).

---

### Test

`db/pgtap/config/test-fn-scrivi-profilo-accesso-v1.sql`.

---

{% include-markdown "signature-core.md" %}
