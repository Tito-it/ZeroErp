## 📘 Documentazione Concettuale – Funzioni `config.fn_lega_profilo_reparto()`, `fn_slega_profilo_reparto()`, `fn_slega_profilo_identita()`

> **Ultimo aggiornamento**: 26 novembre 2026
>
> 👀 **Vedi anche**
>
> [config.fn_lega_profilo_identita](/dbzero/config/manual/fn_lega_profilo_identita) — la gemella che lega le identità
> [config.profili_accesso_bindings](/dbzero/config/manual/profili_accesso_bindings) — i legami

---

### 🎯 Scopo Principale

(19-10-2026 — R-BE-7 del backend, decisioni D-16b e D-16c di Tid,
`brief-db-processi-accensione-per-ambiente` §6.16)

**Legare e slegare i profili di accesso.** Un profilo si lega a un reparto (i profili di tipo
REPARTO) o a un'identità digitale (AD_HOC, SUPER_ADMIN); ogni reparto e ogni identità ha al più
un legame.

| Funzione | Che cosa fa | Restituisce |
| --- | --- | --- |
| `fn_lega_profilo_identita` | lega un'identità a un profilo | l'id del legame |
| `fn_lega_profilo_reparto` | lega un reparto a un profilo | l'id del legame |
| `fn_slega_profilo_identita` | toglie il legame di un'identità da quel profilo | quanti legami ha tolto (0 o 1) |
| `fn_slega_profilo_reparto` | toglie il legame di un reparto da quel profilo | quanti legami ha tolto (0 o 1) |

---

### Le regole

* **legare lo stesso profilo due volte** restituisce lo stesso legame;
* **un altro profilo su un reparto (o un'identità) già legato** lo rifiuta il vincolo unico, col
  suo nome: la funzione non sostituisce in silenzio. Il backend, per i reparti, sostituiva; in
  pratica non cambia niente, perché il profilo di un reparto ha sempre lo stesso codice
  (`REPARTO_<codice del reparto>`) e quindi lo stesso id;
* **slegare** toglie il legame solo se punta a **quel** profilo; se non c'è, risponde 0 e non è
  un errore;
* **l'ultimo super admin attivo** non si slega: lo impedisce un controllo sulla tabella, che vale
  per ogni scrittore;
* coerenza fra tipo di profilo e bersaglio (reparto, identità) e notifica dei permessi: i
  controlli della tabella;
* ⛔ **il permesso**: sono verbi `SECURITY DEFINER` col `search_path` fissato, e nella prima riga chiedono il
  SUPER_ADMIN all'utente di sessione (`script.fn_guard_super_admin`): un altro operatore, o nessun utente, riceve
  `E_PERMESSO_NEGATO`. È lo stesso controllo dell'endpoint. La tabella dei legami è in sola lettura per
  l'applicazione, quindi questi verbi sono l'unica strada per cui un legame cambia.

---

### Chi ne ha preso il posto

Il backend legava il reparto con un `UPSERT` suo e slegava il SUPER_ADMIN con un `DELETE` suo: i
legami di reparto e lo slegare non avevano una madre. Lo slegare del reparto nasce insieme alla
madre che lega, prima che qualcuno ne abbia bisogno: senza, il primo che ne avrebbe avuto bisogno
avrebbe scritto un `DELETE` suo.

---

### Test

`db/pgtap/config/test-legami-profilo-lega-e-slega-v1.sql`.

---

{% include-markdown "signature-core.md" %}
