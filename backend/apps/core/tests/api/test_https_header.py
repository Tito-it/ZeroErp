# ------------------------------------------------------------
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Tid (Michele Carlo Titini)
# Doc: Python
# Scopo: Presidio di HSTS e redirect HTTPS in Django
#        (brief-be-fe-sicurezza-header-token-mfa §1.6): il redirect scatta su
#        HTTP, non su `/health` e non su chi arriva da Nginx; l'header HSTS
#        porta il valore scelto e niente sottodomini/preload; la variabile
#        d'ambiente non ha ripiego fuori da DEBUG; ogni smoke bash si dichiara
#        HTTPS e dichiara una provenienza che `get_client_ip` accetta; ogni
#        login degli smoke passa dal BB `smoke_login` (`_smoke_auth.sh`), che
#        riusa SMOKE_TOKEN valido, e nessuno smoke cabla lo username.
# Note: il runner spegne `SECURE_SSL_REDIRECT` per tutta la suite
#       (`test_runner.py`): qui lo si riaccende apposta.
# ------------------------------------------------------------

"""
Indice test eseguiti:
1) RedirectHttpsTests.test_http_rediretto_in_https
2) RedirectHttpsTests.test_health_non_rediretto
3) RedirectHttpsTests.test_da_nginx_non_rediretto
4) HstsTests.test_header_col_valore_scelto_senza_sottodomini_ne_preload
5) HstsTests.test_zero_nessun_header
6) HstsSettingsTests.test_obbligatoria_fuori_da_debug
7) HstsSettingsTests.test_in_debug_ripiega_su_zero
8) HstsSettingsTests.test_valori_non_validi_rifiutati
9) HstsSettingsTests.test_valori_validi
10) SmokeBashTests.test_ogni_smoke_si_dichiara_https
11) HstsSettingsTests.test_intero_non_negativo_nomina_variabile_e_valore
12) SmokeBashTests.test_il_bb_dichiara_una_provenienza_che_il_login_accetta
13) SmokeBashTests.test_ogni_login_degli_smoke_passa_da_curl_login — secondo fattore (2026-10-02)
14) SmokeBashTests.test_curl_login_fa_il_secondo_passo_e_restituisce_la_forma_di_prima
15) SmokeBashTests.test_ogni_smoke_che_fa_login_passa_da_smoke_login — login unico (2026-10-02)
16) SmokeBashTests.test_nessuno_username_cablato_negli_smoke
17) SmokeBashTests.test_smoke_login_riusa_smoke_token_valido_e_suo
18) SmokeBashTests.test_smoke_login_fallito_lo_dice_ed_esce
19) SmokeBashTests.test_ogni_query_diretta_degli_smoke_passa_da_smoke_db_query — regola del 2 (2026-11-08)
"""

import os
import re
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import Client, RequestFactory, SimpleTestCase, override_settings

from apps.core.services.request_context import get_client_ip

from zeroerp_backend.settings import parse_hsts_seconds, parse_intero_non_negativo

# Una rotta qualunque che non e' `/health`: il redirect scatta prima di
# risolverla, quindi non serve che esista.
_ROTTA = "/api/v1/core/me/"


@override_settings(SECURE_SSL_REDIRECT=True)
class RedirectHttpsTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    # Scopo: Una richiesta HTTP va in HTTPS sulla stessa rotta.
    def test_http_rediretto_in_https(self):
        risposta = self.client.get(_ROTTA)
        self.assertEqual(risposta.status_code, 301)
        self.assertTrue(risposta["Location"].startswith("https://"))
        self.assertTrue(risposta["Location"].endswith(_ROTTA))

    # Scopo: `/health` risponde anche in HTTP diretto (controlli locali, smoke
    #        del container in CI): e' in `SECURE_REDIRECT_EXEMPT`.
    def test_health_non_rediretto(self):
        self.assertEqual(self.client.get("/health").status_code, 200)

    # Scopo: Dietro Nginx (`X-Forwarded-Proto: https`) la richiesta e' gia'
    #        sicura: nessun redirect, arriva alla rotta.
    def test_da_nginx_non_rediretto(self):
        risposta = self.client.get("/non-esiste/", headers={"X-Forwarded-Proto": "https"})
        self.assertEqual(risposta.status_code, 404)


class HstsTests(SimpleTestCase):
    def setUp(self) -> None:
        self.client = Client()

    # Scopo: Su HTTPS l'header porta il valore scelto; sottodomini e preload
    #        restano fuori (riguardano il dominio intero, non ZeroErp).
    @override_settings(SECURE_HSTS_SECONDS=300)
    def test_header_col_valore_scelto_senza_sottodomini_ne_preload(self):
        risposta = self.client.get("/health", secure=True)
        self.assertEqual(risposta["Strict-Transport-Security"], "max-age=300")
        self.assertFalse(settings.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        self.assertFalse(settings.SECURE_HSTS_PRELOAD)

    # Scopo: `0` dichiarato (macchina con certificato auto-firmato): nessun header.
    @override_settings(SECURE_HSTS_SECONDS=0)
    def test_zero_nessun_header(self):
        risposta = self.client.get("/health", secure=True)
        self.assertNotIn("Strict-Transport-Security", risposta)


class HstsSettingsTests(SimpleTestCase):
    # Scopo: Fuori da DEBUG nessun ripiego: chi installa deve scegliere.
    def test_obbligatoria_fuori_da_debug(self):
        for valore in (None, "", "  "):
            with self.subTest(valore=valore), self.assertRaises(ImproperlyConfigured):
                parse_hsts_seconds(valore, debug=False)

    # Scopo: In DEBUG (sviluppo col solo Vite) l'assenza vale 0.
    def test_in_debug_ripiega_su_zero(self):
        self.assertEqual(parse_hsts_seconds(None, debug=True), 0)

    # Scopo: Un numero negativo o non intero ferma l'avvio.
    def test_valori_non_validi_rifiutati(self):
        for valore in ("-1", "un anno", "1.5"):
            with self.subTest(valore=valore), self.assertRaises(ImproperlyConfigured):
                parse_hsts_seconds(valore, debug=False)

    # Scopo: `0` e' una scelta valida (dichiarata), non un'assenza.
    def test_valori_validi(self):
        self.assertEqual(parse_hsts_seconds("0", debug=False), 0)
        self.assertEqual(parse_hsts_seconds("31536000", debug=False), 31536000)


    # Scopo: il BB condiviso con DJANGO_TRUSTED_PROXY_COUNT: il messaggio dice
    #        QUALE variabile e cosa e' arrivato.
    def test_intero_non_negativo_nomina_variabile_e_valore(self):
        with self.assertRaises(ImproperlyConfigured) as ctx:
            parse_intero_non_negativo("DJANGO_TRUSTED_PROXY_COUNT", "due")
        self.assertIn("DJANGO_TRUSTED_PROXY_COUNT", str(ctx.exception))
        self.assertIn("'due'", str(ctx.exception))
        self.assertEqual(parse_intero_non_negativo("X", "1"), 1)


class SmokeBashTests(SimpleTestCase):
    # Scopo: Ogni smoke bash che chiama Gunicorn (`BASE_URL`) include
    #        `_smoke_https.sh` DOPO la riga `BASE_URL=`, e non aggira la
    #        funzione `curl` con `command curl`: altrimenti col redirect acceso
    #        ogni sua chiamata sarebbe un 301.
    def test_ogni_smoke_si_dichiara_https(self):
        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        smoke = sorted(p for p in cartella.glob("*.sh") if not p.name.startswith("_"))
        # `_smoke_auth.sh` (il login degli smoke) include a sua volta `_smoke_https.sh`.
        inclusione = re.compile(r'^source .*_smoke_(https|auth)\.sh"?( "\$@")?\s*$', re.MULTILINE)
        auth = (cartella / "_smoke_auth.sh").read_text(encoding="utf-8")
        self.assertRegex(auth, re.compile(r'^source .*/_smoke_https\.sh"\s*$', re.MULTILINE))
        controllati = 0
        for script in smoke:
            testo = script.read_text(encoding="utf-8")
            base_url = re.search(r"^BASE_URL=", testo, re.MULTILINE)
            if base_url is None:
                continue
            controllati += 1
            with self.subTest(script=script.name):
                trovata = inclusione.search(testo, base_url.end())
                self.assertIsNotNone(trovata, "manca `source .../_smoke_auth.sh` (o _smoke_https.sh) dopo BASE_URL=")
                self.assertNotIn("command curl", testo)
        # Il test non deve passare a vuoto se la cartella si sposta.
        self.assertGreater(controllati, 0)

    # Scopo: gli header che il BB manda davvero (eseguito in bash, con `curl`
    #        intercettato) passano la regola VERA della provenienza per 1 e 2
    #        proxy fidati: senza, il login risponde `E_AUTH_CHIAMATA_NON_VALIDA`
    #        e ogni smoke si ferma al passo 0 (successo fino al 2026-09-28).
    def test_il_bb_dichiara_una_provenienza_che_il_login_accetta(self):
        bb = Path(settings.BASE_DIR) / "scripts" / "tests" / "_smoke_https.sh"
        # `command` ridefinito stampa gli argomenti invece di lanciare curl.
        programma = f'command() {{ shift; printf "%s\\n" "$@"; }}; source "{bb}"; curl http://x/'
        for proxy_fidati in (1, 2):
            with self.subTest(proxy_fidati=proxy_fidati):
                uscita = subprocess.run(
                    ["bash", "-c", programma],
                    env={**os.environ, "DJANGO_TRUSTED_PROXY_COUNT": str(proxy_fidati)},
                    capture_output=True, text=True, check=True,
                ).stdout.splitlines()
                header = dict(
                    uscita[i + 1].split(": ", 1)
                    for i, arg in enumerate(uscita) if arg == "-H"
                )
                self.assertEqual(header.get("X-Forwarded-Proto"), "https")
                richiesta = RequestFactory().get(
                    "/", HTTP_X_FORWARDED_FOR=header.get("X-Forwarded-For", ""),
                )
                with override_settings(TRUSTED_PROXY_COUNT=proxy_fidati):
                    self.assertEqual(get_client_ip(richiesta), "127.0.0.1")

    # Scopo: Brief sicurezza §3.4-bis (2026-10-02). Col secondo fattore attivo
    #        il login degli smoke risponde con una sfida e nessun token: ogni
    #        chiamata di login passa da `curl_login` (`_smoke_secondo_fattore.sh`),
    #        che fa il secondo passo. Una sola chiamata con `curl` nudo ferma quello
    #        smoke al passo 0, il giorno in cui l'utente degli smoke configura il
    #        secondo fattore. Il login ordinario sta nel BB (`_smoke_auth.sh`); in
    #        uno smoke resta solo il login che il BB non copre, con
    #        `# login esplicito: <perche'>` sopra.
    def test_ogni_login_degli_smoke_passa_da_curl_login(self):
        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        login = re.compile(r'/(admin|portale|shop)/token/"')
        auth = (cartella / "_smoke_auth.sh").read_text(encoding="utf-8")
        self.assertRegex(auth, re.compile(r'^source .*/_smoke_secondo_fattore\.sh"\s*$', re.MULTILINE))
        controllati = 0
        for script in sorted(cartella.glob("*.sh")):
            if script.name == "_smoke_secondo_fattore.sh":
                continue
            righe = script.read_text(encoding="utf-8").split("\n")
            for i, riga in enumerate(righe):
                if not login.search(riga):
                    continue
                controllati += 1
                j = i
                while j >= 0 and "curl" not in righe[j]:
                    j -= 1
                with self.subTest(script=script.name, riga=i + 1):
                    self.assertIn("curl_login", righe[j])
                    if script.name.startswith("_"):
                        continue
                    sopra = "\n".join(righe[max(j - 6, 0):j])
                    self.assertIn(
                        "# login esplicito:", sopra,
                        "login fuori dal BB: si usa `smoke_login`, o si dice perche' no",
                    )
        self.assertGreater(controllati, 0)

    # Scopo: `curl_login` eseguito davvero in bash, con `curl` finto: alla
    #        sfida fa il secondo passo sul percorso della porta col codice del
    #        segreto, e restituisce cio' che lo smoke legge dal login di prima
    #        (`{"access"}` in testa, il cookie negli header, lo status nel
    #        formato di `-w`). Senza sfida e' `curl`, e basta.
    def test_curl_login_fa_il_secondo_passo_e_restituisce_la_forma_di_prima(self):
        import sys
        import tempfile

        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        # `curl` finto: il primo login dice la sfida (o il token, se SENZA_SFIDA);
        # il secondo passo da' il token nell'envelope e il cookie. Registra gli URL.
        finto = r"""
curl() {
  local o="" d="" url=""
  while (($#)); do case "$1" in -o) o="$2"; shift 2;; -D) d="$2"; shift 2;;
    -w|-H|-d) [[ "$1" == "-d" ]] && echo "CORPO $2" >> "$LOG"; shift 2;; -s) shift;; *) url="$1"; shift;; esac; done
  echo "URL $url" >> "$LOG"
  if [[ "$url" == *secondo-fattore/ ]]; then
    echo '{"data": {"access": "A2"}}' > "$o"; printf 'Set-Cookie: zeroerp_refresh=R2; Path=/\r\n' > "$d"
  elif [[ -n "${SENZA_SFIDA:-}" ]]; then
    echo '{"access": "A1"}' > "$o"; printf 'Set-Cookie: zeroerp_refresh=R1; Path=/\r\n' > "$d"
  else
    echo '{"two_factor_required": true, "sfida": "S1", "scade_in_secondi": 300}' > "$o"; : > "$d"
  fi
  printf '200'
}
"""
        programma = (
            f'source "{cartella / "_smoke_secondo_fattore.sh"}"\n{finto}\n'
            'curl_login -s -w "\\n%{http_code}" -D "$HDR" -d "{}" "http://x/api/v1/admin/token/"'
        )
        # ⛔ Senza la chiave: nessun ritorno non-zero (gli smoke hanno `set -e`
        #    e buttano lo stderr del login: si chiudevano IN SILENZIO al passo 0,
        #    collaudo del 2026-10-02), ma un login fallito che dice cosa manca.
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if k != "SMOKE_TOTP_SECRET"}
            env.update(SMOKE_PYTHON=sys.executable, TMPDIR=tmp, HDR=f"{tmp}/hdr", LOG=f"{tmp}/log")
            fatto = subprocess.run(
                ["bash", "-c", "set -e\n" + programma], env=env, capture_output=True, text=True,
            )
            self.assertEqual(fatto.returncode, 0, fatto.stderr)
            self.assertIn("SMOKE_TOTP_SECRET", fatto.stdout)
            self.assertTrue(fatto.stdout.endswith("\n401"), fatto.stdout)

        for senza_sfida in (False, True):
            with self.subTest(senza_sfida=senza_sfida), tempfile.TemporaryDirectory() as tmp:
                env = {
                    **os.environ,
                    "SMOKE_PYTHON": sys.executable,
                    "SMOKE_TOTP_SECRET": "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
                    "TMPDIR": tmp,  # il file dell'ultimo passo, isolato
                    "HDR": f"{tmp}/hdr",
                    "LOG": f"{tmp}/log",
                    **({"SENZA_SFIDA": "1"} if senza_sfida else {}),
                }
                uscita = subprocess.run(
                    ["bash", "-c", programma], env=env, capture_output=True, text=True, check=True,
                ).stdout
                log = Path(f"{tmp}/log").read_text().splitlines()
                header = Path(f"{tmp}/hdr").read_text()
                if senza_sfida:
                    self.assertEqual(uscita, '{"access": "A1"}\n\n200')
                    self.assertIn("zeroerp_refresh=R1", header)
                    self.assertEqual([r for r in log if r.startswith("URL")], ["URL http://x/api/v1/admin/token/"])
                else:
                    self.assertEqual(uscita, '{"access": "A2"}\n200')
                    self.assertIn("zeroerp_refresh=R2", header)
                    self.assertEqual(
                        [r for r in log if r.startswith("URL")],
                        ["URL http://x/api/v1/admin/token/", "URL http://x/api/v1/admin/token/secondo-fattore/"],
                    )
                    corpo = [r for r in log if r.startswith("CORPO")][-1]
                    self.assertRegex(corpo, r'^CORPO \{"sfida":"S1","codice":"\d{6}"\}$')

    # Scopo: Regola del 2 (decisione Tid 2026-10-02): il login degli smoke e'
    #        UNO, `smoke_login` di `_smoke_auth.sh`. Ogni smoke che parla col
    #        backend autenticato include il BB con un solo `source` (non i pezzi
    #        che il BB porta con se') e chiama `smoke_login`.
    def test_ogni_smoke_che_fa_login_passa_da_smoke_login(self):
        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        inclusione = re.compile(r'^source .*/_smoke_auth\.sh" "\$@"\s*$', re.MULTILINE)
        pezzi = re.compile(r'^source .*/_smoke_(https|secondo_fattore|refresh)\.sh', re.MULTILINE)
        chiamata = re.compile(r'^\s*smoke_login\b', re.MULTILINE)
        controllati = 0
        for script in sorted(p for p in cartella.glob("*.sh") if not p.name.startswith("_")):
            testo = script.read_text(encoding="utf-8")
            if "Authorization: Bearer" not in testo and script.name != "smoke-login.sh":
                continue
            controllati += 1
            with self.subTest(script=script.name):
                self.assertRegex(testo, inclusione)
                self.assertNotRegex(testo, pezzi)
                self.assertRegex(testo, chiamata)
        self.assertGreater(controllati, 0)

    # Scopo: Gli smoke girano con l'utente di SMOKE_USER (un utente dedicato):
    #        nessuno username scritto nel login, nelle query o nelle GUC, e
    #        nessun ripiego su un utente personale, nemmeno nel BB (fino al
    #        2026-10-16 `_smoke_auth.sh` ripiegava su `tid`). Vale anche per gli
    #        smoke Python, che leggono la stessa variabile.
    def test_nessuno_username_cablato_negli_smoke(self):
        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        nel_login = re.compile(r'username\\?"\s*:\s*\\?"(?!\$)')
        letterale = re.compile(r'''(["'])tid\1''')
        ripiego_bash = re.compile(r"SMOKE_USER:-[^}]")
        ripiego_py = re.compile(r'''["']SMOKE_USER["']\s*,\s*["'][^"']''')
        for script in sorted(cartella.glob("*.sh")):
            testo = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertNotRegex(testo, nel_login)
                self.assertNotRegex(testo, letterale)
                self.assertNotRegex(testo, ripiego_bash)
        for script in sorted(cartella.glob("*.py")):
            testo = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertNotRegex(testo, ripiego_py)

    # Esegue `smoke_login` in bash con `curl` finto: `/core/me/` risponde lo
    # username ME_USER, il login il token NUOVO (status LOGIN_STATUS). Torna
    # (esito, URL chiamati).
    def _smoke_login(self, opzioni: str = "", **env_extra: str):
        import tempfile

        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        finto = r"""
curl() {
  local o="" url=""
  while (($#)); do case "$1" in -o) o="$2"; shift 2;; -D|-w|-H|-d) shift 2;; -s|-X) shift;; *) url="$1"; shift;; esac; done
  echo "$url" >> "$LOG"
  if [[ "$url" == */core/me/ ]]; then echo "{\"data\": {\"utente\": {\"username\": \"${ME_USER}\"}}}"; return 0; fi
  echo '{"access": "NUOVO"}' > "$o"; printf '%s' "${LOGIN_STATUS:-200}"
}
"""
        programma = (
            f'set -euo pipefail\nBASE_URL=http://x\nsource "{cartella / "_smoke_auth.sh"}"\n{finto}\n'
            f'smoke_login {opzioni}\necho "TOKEN=$TOKEN FONTE=$SMOKE_LOGIN_FONTE"'
        )
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if not k.startswith("SMOKE_")}
            env.update({"SMOKE_USER": "smoke", "SMOKE_PASSWORD": "pw", "ME_USER": "smoke", **env_extra})
            env["LOG"] = f"{tmp}/log"
            esito = subprocess.run(
                ["bash", "-c", programma], env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL,
            )
            log = Path(f"{tmp}/log")
            chiamati = log.read_text().splitlines() if log.exists() else []
        return esito, chiamati

    @staticmethod
    def _jwt(scade_fra: int) -> str:
        import base64
        import json
        import time

        def parte(d: dict) -> str:
            return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
        return f"{parte({'alg': 'HS256'})}.{parte({'exp': int(time.time()) + scade_fra, 'user_id': 7})}.firma"

    # Scopo: Un solo login per una sessione di smoke (decisione Tid 2026-10-02).
    #        SMOKE_TOKEN valido, accettato dal backend e dell'utente dello smoke:
    #        nessun login. Scaduto/in scadenza, di un altro utente, o uno smoke
    #        che prova il login (`-D`, `--login-vero`): il login vero, e lo dice.
    def test_smoke_login_riusa_smoke_token_valido_e_suo(self):
        login = "http://x/api/v1/admin/token/"
        valido = self._jwt(600)
        esito, chiamati = self._smoke_login(SMOKE_TOKEN=valido)
        self.assertEqual(esito.returncode, 0, esito.stdout + esito.stderr)
        self.assertIn(f"TOKEN={valido} FONTE=SMOKE_TOKEN", esito.stdout)
        self.assertNotIn(login, chiamati)

        casi = {
            "in scadenza": ({"SMOKE_TOKEN": self._jwt(60)}, "", "scaduto o in scadenza"),
            "di un altro utente": ({"SMOKE_TOKEN": valido, "ME_USER": "tid"}, "", "non di 'smoke'"),
            "non accettato": ({"SMOKE_TOKEN": valido, "ME_USER": ""}, "", "non lo accetta"),
            "header del refresh": ({"SMOKE_TOKEN": valido}, '-D "$LOG.hdr"', "login vero"),
            "login vero": ({"SMOKE_TOKEN": valido}, "--login-vero", "login vero"),
        }
        for caso, (env, opzioni, perche) in casi.items():
            with self.subTest(caso=caso):
                esito, chiamati = self._smoke_login(opzioni, **env)
                self.assertEqual(esito.returncode, 0, esito.stdout + esito.stderr)
                self.assertIn("TOKEN=NUOVO FONTE=login", esito.stdout)
                self.assertIn(perche, esito.stdout)
                self.assertIn(login, chiamati)

    # Scopo: ⛔ sotto `set -e` mai un'uscita silenziosa: un login rifiutato,
    #        una password o un utente mancanti stampano la causa ed escono col codice scelto
    #        dallo smoke (`--uscita`), senza arrivare al primo passo.
    def test_smoke_login_fallito_lo_dice_ed_esce(self):
        esito, _ = self._smoke_login("--uscita 2", LOGIN_STATUS="401")
        self.assertEqual(esito.returncode, 2)
        self.assertIn("autenticazione fallita (HTTP 401)", esito.stdout)
        self.assertNotIn("TOKEN=", esito.stdout)

        esito, chiamati = self._smoke_login("--senza-prompt", SMOKE_PASSWORD="")
        self.assertEqual(esito.returncode, 1)
        self.assertIn("Password mancante", esito.stdout)
        self.assertEqual(chiamati, [])

        # Senza SMOKE_USER nessun ripiego su un utente personale: si ferma.
        esito, chiamati = self._smoke_login("--uscita 3", SMOKE_USER="")
        self.assertEqual(esito.returncode, 3)
        self.assertIn("utente degli smoke non impostato (SMOKE_USER)", esito.stdout)
        self.assertEqual(chiamati, [])

    # Scopo: la query diretta al DB degli smoke bash ha UNA sede,
    #        `_smoke_db.sh` (`smoke_db_query`). Le copie locali (`db_query()`)
    #        si comportavano in due modi diversi: un errore del DB diventava
    #        «nessuna riga» (`2>/dev/null ... || true`), oppure zero righe
    #        chiudevano lo smoke in silenzio (senza `|| true`, sotto
    #        `pipefail`). Una lettura `dbshell -- -t` fuori dal BB e' una copia.
    # ⚠️ Le scritture di pulizia con `dbshell -- -q` (es. -listini-v5) non sono
    #    letture e restano dello smoke.
    def test_ogni_query_diretta_degli_smoke_passa_da_smoke_db_query(self):
        cartella = Path(settings.BASE_DIR) / "scripts" / "tests"
        copia = re.compile(r"^\s*(function\s+)?db_query\s*\(\)", re.M)
        # Fra le opzioni anche la riga spezzata (`\` a capo).
        lettura = re.compile(r"dbshell[\s\\]+--[\s\\]+(-X[\s\\]+)?(-q[\s\\]+)?-t\b")
        bb = cartella / "_smoke_db.sh"
        self.assertRegex(bb.read_text(encoding="utf-8"), lettura)
        for script in sorted(cartella.glob("*.sh")):
            if script == bb:
                continue
            testo = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertNotRegex(testo, copia)
                self.assertNotRegex(testo, lettura)
