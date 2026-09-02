## 📘 Documentazione Concettuale – Funzione `vendite.fn_provision_registri_famiglia`

> 👀 **Vedi anche**
>
> **La regola vera sta qui:**
>
> • [vendite.fn_provision_registri](/dbzero/vendite/manual/fn_provision_registri) — la primitiva
>
> **La gemella:**
>
> • [vendite.fn_provision_registri_emittente](/dbzero/vendite/manual/fn_provision_registri_emittente) — la stessa cosa, dall'altro lato
>
> **Chi la chiama:**
>
> • [vendite.fn_crea_famiglia_documento](/dbzero/vendite/manual/fn_crea_famiglia_documento) — la madre del CRUD

---

### 🎯 Scopo Principale

*(rev 2026-09-01 — funzione nata il 2026-09-01)*

**Dà a UNA famiglia di documento il suo registro di numerazione su tutti gli
emittenti che ancora non ce l'hanno**, e dice quanti ne ha creati.

---

### ⛔ Il buco che chiude

Il provisioning esisteva solo **per emittente**, agganciato alla nascita di un
emittente fiscale. La simmetrica non c'era.

⇒ Una famiglia creata dal CRUD sarebbe nata **senza registri**, e i suoi
documenti non si sarebbero numerati. Il fail-closed di
`fn_get_registro_documento` lo dice — ma **al primo documento**, non alla
creazione: cioè a chi stava lavorando, non a chi ha configurato.

⚠️ La documentazione della tabella delle famiglie lo scriveva già — *«chi
aggiunge una famiglia deve anche darle un registro per emittente»* — e non
c'era nessuno a eseguirlo.

---

### Che cosa dice il numero che ritorna

⭐ **Zero non è sempre uguale a zero:**

| Situazione | Significa |
| --- | --- |
| famiglia **attiva**, zero registri creati | non c'è **nessun emittente**: quel documento non nascerà comunque. Da mostrare, non da ignorare |
| famiglia **spenta** | zero per costruzione: una famiglia spenta non deve far nascere registri. Non è un errore, è il caso «si prepara prima, si accende dopo» |
| seconda chiamata | zero perché è già a posto: la primitiva è idempotente sulla coppia (emittente, famiglia) |

---

### ⚠️ Una differenza con la gemella, e non è una svista

La gemella per emittente, se riceve un parametro vuoto, **torna 0 in silenzio**:
la chiama un trigger su ogni riga, e una riga senza soggetto-ruolo non è un
errore di dominio.

Qui invece un parametro vuoto **solleva**: nessun trigger la chiama a tappeto —
ci arriva chi ha deciso di provvisionare una famiglia precisa, e un vuoto lì è un
chiamante rotto.

---

### ⭐ È un involucro sottile, e deve restarlo

Il codice del registro, la descrizione, il reset e i default di forma **non sono
qui**: stanno nella primitiva. Qui c'è solo il filtro.

⚠️ Chi un domani volesse cambiare come nasce un registro deve toccare la
primitiva. Aggiungere la regola qui dentro ricrea le due copie che questo
impianto esiste per evitare.

---

*Piano: `brief-be-fe-crud-registri-di-numerazione`, sezione 11.6.*
