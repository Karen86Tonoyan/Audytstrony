"""
Moduł WebAudit - Audyty Bezpieczeństwa Stron
============================================
Obsługuje:
- Skanowanie SSL/TLS
- Analiza nagłówków bezpieczeństwa
- Wykrywanie podatności
- SEO audit
- Performance audit
- Sprawdzanie linków
- Screenshot strony
- Raportowanie
"""

import asyncio
import ssl
import socket
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from urllib.parse import urlparse, urljoin
import json

import httpx
import dns.resolver
from bs4 import BeautifulSoup
from loguru import logger

from agent.config.settings import get_settings
from agent.modules.file_generator import (
    get_file_generator, Report, ReportSection, TableData
)


class SeverityLevel(Enum):
    """Poziom ważności problemu."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Finding:
    """Znalezisko audytu."""
    title: str
    description: str
    severity: SeverityLevel
    category: str
    recommendation: str = ""
    references: List[str] = field(default_factory=list)


@dataclass
class SSLInfo:
    """Informacje o certyfikacie SSL."""
    valid: bool
    issuer: str
    subject: str
    valid_from: datetime
    valid_until: datetime
    days_until_expiry: int
    protocol_version: str
    cipher_suite: str
    certificate_chain: List[str] = field(default_factory=list)
    vulnerabilities: List[str] = field(default_factory=list)


@dataclass
class SecurityHeaders:
    """Nagłówki bezpieczeństwa."""
    headers: Dict[str, str]
    missing: List[str]
    score: int  # 0-100
    findings: List[Finding] = field(default_factory=list)


@dataclass
class PageInfo:
    """Informacje o stronie."""
    url: str
    title: str
    status_code: int
    response_time: float
    content_type: str
    size_bytes: int
    technologies: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    forms: List[Dict[str, Any]] = field(default_factory=list)
    scripts: List[str] = field(default_factory=list)
    cookies: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class SEOInfo:
    """Informacje SEO."""
    title: Optional[str]
    meta_description: Optional[str]
    meta_keywords: Optional[str]
    h1_tags: List[str]
    h2_tags: List[str]
    images_without_alt: int
    canonical_url: Optional[str]
    robots_txt: bool
    sitemap_xml: bool
    mobile_friendly: bool
    findings: List[Finding] = field(default_factory=list)


@dataclass
class AuditResult:
    """Pełny wynik audytu."""
    url: str
    timestamp: datetime
    page_info: PageInfo
    ssl_info: Optional[SSLInfo]
    security_headers: SecurityHeaders
    seo_info: SEOInfo
    findings: List[Finding]
    score: int  # 0-100
    scan_duration: float


class WebAuditModule:
    """
    Moduł audytu stron internetowych.
    Kompleksowa analiza bezpieczeństwa i jakości.
    """

    def __init__(self):
        self.settings = get_settings().web_audit
        self._client: Optional[httpx.AsyncClient] = None
        self._ensure_dirs()

        # Wymagane nagłówki bezpieczeństwa
        self.required_headers = {
            "Strict-Transport-Security": "HSTS - wymusza HTTPS",
            "X-Content-Type-Options": "Zapobiega sniffingowi MIME",
            "X-Frame-Options": "Ochrona przed clickjackingiem",
            "X-XSS-Protection": "Ochrona przed XSS (przestarzałe)",
            "Content-Security-Policy": "CSP - kontrola zasobów",
            "Referrer-Policy": "Kontrola nagłówka Referer",
            "Permissions-Policy": "Kontrola API przeglądarki",
        }

        logger.info("WebAuditModule zainicjalizowany")

    def _ensure_dirs(self):
        """Upewnij się że katalogi istnieją."""
        self.settings.reports_dir.mkdir(parents=True, exist_ok=True)

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy init klienta HTTP."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.settings.scan_timeout),
                follow_redirects=True,
                headers={"User-Agent": self.settings.user_agent}
            )
        return self._client

    async def close(self):
        """Zamknij klienta."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ==================== Główny Audyt ====================

    async def full_audit(self, url: str) -> AuditResult:
        """
        Przeprowadź pełny audyt strony.

        Args:
            url: URL strony do audytu

        Returns:
            Pełny wynik audytu
        """
        start_time = datetime.now()
        findings = []

        logger.info(f"Rozpoczynam audyt: {url}")

        # Normalizuj URL
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Pobierz informacje o stronie
        page_info = await self.scan_page(url)
        findings.extend(self._analyze_page_info(page_info))

        # SSL/TLS
        ssl_info = None
        if url.startswith("https://"):
            ssl_info = await self.check_ssl(url)
            if ssl_info:
                findings.extend(self._analyze_ssl(ssl_info))

        # Nagłówki bezpieczeństwa
        security_headers = await self.check_security_headers(url)
        findings.extend(security_headers.findings)

        # SEO
        seo_info = await self.check_seo(url, page_info)
        findings.extend(seo_info.findings)

        # Oblicz ogólny wynik
        score = self._calculate_score(findings, ssl_info, security_headers)

        duration = (datetime.now() - start_time).total_seconds()

        result = AuditResult(
            url=url,
            timestamp=datetime.now(),
            page_info=page_info,
            ssl_info=ssl_info,
            security_headers=security_headers,
            seo_info=seo_info,
            findings=findings,
            score=score,
            scan_duration=duration
        )

        logger.info(f"Audyt zakończony: {url} (wynik: {score}/100, czas: {duration:.2f}s)")

        return result

    # ==================== Skanowanie Strony ====================

    async def scan_page(self, url: str) -> PageInfo:
        """Skanuj stronę i zbierz informacje."""
        client = await self._get_client()

        start = datetime.now()
        response = await client.get(url)
        response_time = (datetime.now() - start).total_seconds()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Wyodrębnij informacje
        title = soup.title.string if soup.title else ""

        # Linki
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(url, href)
            links.append(full_url)

        # Formularze
        forms = []
        for form in soup.find_all('form'):
            forms.append({
                "action": form.get('action', ''),
                "method": form.get('method', 'get').upper(),
                "inputs": [
                    {"name": inp.get('name'), "type": inp.get('type', 'text')}
                    for inp in form.find_all('input')
                ]
            })

        # Skrypty
        scripts = [
            script.get('src', 'inline')
            for script in soup.find_all('script')
        ]

        # Technologie
        technologies = self._detect_technologies(response, soup)

        # Ciasteczka
        cookies = [
            {
                "name": c.name,
                "secure": c.secure,
                "httponly": c.has_nonstandard_attr('HttpOnly'),
                "samesite": c.get_nonstandard_attr('SameSite')
            }
            for c in response.cookies.jar
        ]

        return PageInfo(
            url=url,
            title=title,
            status_code=response.status_code,
            response_time=response_time,
            content_type=response.headers.get('content-type', ''),
            size_bytes=len(response.content),
            technologies=technologies,
            links=links[:100],  # Limit
            forms=forms,
            scripts=scripts,
            cookies=cookies
        )

    def _detect_technologies(
        self,
        response: httpx.Response,
        soup: BeautifulSoup
    ) -> List[str]:
        """Wykryj technologie użyte na stronie."""
        technologies = []

        headers = response.headers

        # Serwer
        if 'server' in headers:
            technologies.append(f"Server: {headers['server']}")

        if 'x-powered-by' in headers:
            technologies.append(f"Powered by: {headers['x-powered-by']}")

        # Framework JS
        html = str(soup)
        if 'react' in html.lower() or '_reactRootContainer' in html:
            technologies.append("React")
        if 'vue' in html.lower() or '__vue__' in html:
            technologies.append("Vue.js")
        if 'angular' in html.lower() or 'ng-' in html:
            technologies.append("Angular")
        if 'jquery' in html.lower():
            technologies.append("jQuery")

        # CMS
        if 'wp-content' in html or 'wordpress' in html.lower():
            technologies.append("WordPress")
        if 'drupal' in html.lower():
            technologies.append("Drupal")
        if 'joomla' in html.lower():
            technologies.append("Joomla")

        # Analytics
        if 'google-analytics' in html or 'gtag' in html:
            technologies.append("Google Analytics")
        if 'facebook' in html.lower() and 'pixel' in html.lower():
            technologies.append("Facebook Pixel")

        return technologies

    def _analyze_page_info(self, page_info: PageInfo) -> List[Finding]:
        """Analizuj informacje o stronie."""
        findings = []

        # Wolna odpowiedź
        if page_info.response_time > 3.0:
            findings.append(Finding(
                title="Wolna odpowiedź serwera",
                description=f"Czas odpowiedzi: {page_info.response_time:.2f}s",
                severity=SeverityLevel.MEDIUM,
                category="Performance",
                recommendation="Zoptymalizuj serwer lub użyj CDN"
            ))

        # Duży rozmiar strony
        size_mb = page_info.size_bytes / (1024 * 1024)
        if size_mb > 2:
            findings.append(Finding(
                title="Duży rozmiar strony",
                description=f"Rozmiar: {size_mb:.2f} MB",
                severity=SeverityLevel.LOW,
                category="Performance",
                recommendation="Kompresuj zasoby i optymalizuj obrazy"
            ))

        # Niezabezpieczone formularze
        for form in page_info.forms:
            if form['method'] == 'POST' and not page_info.url.startswith('https://'):
                findings.append(Finding(
                    title="Formularz POST przez HTTP",
                    description="Dane formularza mogą być przechwycone",
                    severity=SeverityLevel.HIGH,
                    category="Security",
                    recommendation="Używaj HTTPS dla wszystkich formularzy"
                ))
                break

        # Niezabezpieczone ciasteczka
        for cookie in page_info.cookies:
            if not cookie['secure']:
                findings.append(Finding(
                    title=f"Ciasteczko bez flagi Secure: {cookie['name']}",
                    description="Ciasteczko może być przesłane przez HTTP",
                    severity=SeverityLevel.MEDIUM,
                    category="Security",
                    recommendation="Dodaj flagę Secure do ciasteczek"
                ))
            if not cookie['httponly'] and 'session' in cookie['name'].lower():
                findings.append(Finding(
                    title=f"Ciasteczko sesji bez HttpOnly: {cookie['name']}",
                    description="Ciasteczko może być odczytane przez JavaScript",
                    severity=SeverityLevel.HIGH,
                    category="Security",
                    recommendation="Dodaj flagę HttpOnly do ciasteczek sesji"
                ))

        return findings

    # ==================== SSL/TLS ====================

    async def check_ssl(self, url: str) -> Optional[SSLInfo]:
        """Sprawdź certyfikat SSL/TLS."""
        parsed = urlparse(url)
        hostname = parsed.hostname
        port = parsed.port or 443

        try:
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED

            loop = asyncio.get_event_loop()

            def get_cert():
                with socket.create_connection((hostname, port), timeout=10) as sock:
                    with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                        cert = ssock.getpeercert()
                        cipher = ssock.cipher()
                        version = ssock.version()
                        return cert, cipher, version

            cert, cipher, version = await loop.run_in_executor(None, get_cert)

            # Parsuj daty
            valid_from = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
            valid_until = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            days_until_expiry = (valid_until - datetime.now()).days

            # Wyodrębnij informacje
            issuer = dict(x[0] for x in cert['issuer'])
            subject = dict(x[0] for x in cert['subject'])

            vulnerabilities = []

            # Sprawdź stare protokoły
            if version in ['SSLv2', 'SSLv3', 'TLSv1', 'TLSv1.1']:
                vulnerabilities.append(f"Przestarzały protokół: {version}")

            # Sprawdź słabe szyfry
            weak_ciphers = ['RC4', 'DES', '3DES', 'MD5']
            if cipher and any(wc in cipher[0] for wc in weak_ciphers):
                vulnerabilities.append(f"Słaby szyfr: {cipher[0]}")

            return SSLInfo(
                valid=True,
                issuer=issuer.get('organizationName', issuer.get('commonName', 'Unknown')),
                subject=subject.get('commonName', 'Unknown'),
                valid_from=valid_from,
                valid_until=valid_until,
                days_until_expiry=days_until_expiry,
                protocol_version=version,
                cipher_suite=cipher[0] if cipher else 'Unknown',
                vulnerabilities=vulnerabilities
            )

        except ssl.SSLCertVerificationError as e:
            logger.warning(f"Błąd weryfikacji SSL: {e}")
            return SSLInfo(
                valid=False,
                issuer="Unknown",
                subject="Unknown",
                valid_from=datetime.now(),
                valid_until=datetime.now(),
                days_until_expiry=0,
                protocol_version="Unknown",
                cipher_suite="Unknown",
                vulnerabilities=[f"Błąd weryfikacji: {str(e)}"]
            )

        except Exception as e:
            logger.error(f"Błąd sprawdzania SSL: {e}")
            return None

    def _analyze_ssl(self, ssl_info: SSLInfo) -> List[Finding]:
        """Analizuj wyniki SSL."""
        findings = []

        if not ssl_info.valid:
            findings.append(Finding(
                title="Nieprawidłowy certyfikat SSL",
                description="Certyfikat nie przeszedł weryfikacji",
                severity=SeverityLevel.CRITICAL,
                category="SSL/TLS",
                recommendation="Zainstaluj prawidłowy certyfikat SSL"
            ))

        if ssl_info.days_until_expiry < 0:
            findings.append(Finding(
                title="Certyfikat wygasł",
                description=f"Certyfikat wygasł {abs(ssl_info.days_until_expiry)} dni temu",
                severity=SeverityLevel.CRITICAL,
                category="SSL/TLS",
                recommendation="Natychmiast odnów certyfikat"
            ))
        elif ssl_info.days_until_expiry < 30:
            findings.append(Finding(
                title="Certyfikat wkrótce wygaśnie",
                description=f"Pozostało {ssl_info.days_until_expiry} dni",
                severity=SeverityLevel.HIGH,
                category="SSL/TLS",
                recommendation="Odnów certyfikat przed wygaśnięciem"
            ))

        for vuln in ssl_info.vulnerabilities:
            findings.append(Finding(
                title="Podatność SSL/TLS",
                description=vuln,
                severity=SeverityLevel.HIGH,
                category="SSL/TLS",
                recommendation="Zaktualizuj konfigurację SSL/TLS"
            ))

        return findings

    # ==================== Nagłówki Bezpieczeństwa ====================

    async def check_security_headers(self, url: str) -> SecurityHeaders:
        """Sprawdź nagłówki bezpieczeństwa."""
        client = await self._get_client()
        response = await client.head(url)

        headers = dict(response.headers)
        missing = []
        findings = []
        score = 100

        for header, description in self.required_headers.items():
            header_lower = header.lower()
            found = False

            for h in headers:
                if h.lower() == header_lower:
                    found = True
                    break

            if not found:
                missing.append(header)
                score -= 15

                severity = SeverityLevel.MEDIUM
                if header in ['Strict-Transport-Security', 'Content-Security-Policy']:
                    severity = SeverityLevel.HIGH

                findings.append(Finding(
                    title=f"Brakujący nagłówek: {header}",
                    description=description,
                    severity=severity,
                    category="Security Headers",
                    recommendation=f"Dodaj nagłówek {header}"
                ))

        # Sprawdź wartości nagłówków
        hsts = headers.get('strict-transport-security', '')
        if hsts:
            if 'max-age' in hsts.lower():
                max_age = int(hsts.split('max-age=')[1].split(';')[0])
                if max_age < 31536000:  # Mniej niż rok
                    findings.append(Finding(
                        title="HSTS max-age zbyt krótki",
                        description=f"Aktualny: {max_age}s, zalecany: 31536000s",
                        severity=SeverityLevel.LOW,
                        category="Security Headers",
                        recommendation="Ustaw max-age na minimum 1 rok"
                    ))

        return SecurityHeaders(
            headers=headers,
            missing=missing,
            score=max(0, score),
            findings=findings
        )

    # ==================== SEO ====================

    async def check_seo(self, url: str, page_info: PageInfo = None) -> SEOInfo:
        """Sprawdź SEO strony."""
        if not page_info:
            page_info = await self.scan_page(url)

        client = await self._get_client()
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        findings = []

        # Title
        title = soup.title.string if soup.title else None
        if not title:
            findings.append(Finding(
                title="Brak tytułu strony",
                description="Tag <title> jest pusty lub nie istnieje",
                severity=SeverityLevel.HIGH,
                category="SEO",
                recommendation="Dodaj unikalny tytuł do każdej strony"
            ))
        elif len(title) > 60:
            findings.append(Finding(
                title="Tytuł strony zbyt długi",
                description=f"Długość: {len(title)} znaków (zalecane: max 60)",
                severity=SeverityLevel.LOW,
                category="SEO",
                recommendation="Skróć tytuł do 60 znaków"
            ))

        # Meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        meta_description = meta_desc['content'] if meta_desc else None

        if not meta_description:
            findings.append(Finding(
                title="Brak meta description",
                description="Meta description jest puste lub nie istnieje",
                severity=SeverityLevel.MEDIUM,
                category="SEO",
                recommendation="Dodaj unikalny meta description (150-160 znaków)"
            ))

        # Meta keywords (mniej istotne)
        meta_kw = soup.find('meta', attrs={'name': 'keywords'})
        meta_keywords = meta_kw['content'] if meta_kw else None

        # Nagłówki
        h1_tags = [h.get_text().strip() for h in soup.find_all('h1')]
        h2_tags = [h.get_text().strip() for h in soup.find_all('h2')]

        if not h1_tags:
            findings.append(Finding(
                title="Brak nagłówka H1",
                description="Strona nie zawiera nagłówka H1",
                severity=SeverityLevel.MEDIUM,
                category="SEO",
                recommendation="Dodaj jeden nagłówek H1 z głównym słowem kluczowym"
            ))
        elif len(h1_tags) > 1:
            findings.append(Finding(
                title="Wiele nagłówków H1",
                description=f"Znaleziono {len(h1_tags)} nagłówków H1",
                severity=SeverityLevel.LOW,
                category="SEO",
                recommendation="Używaj tylko jednego H1 na stronę"
            ))

        # Obrazy bez alt
        images = soup.find_all('img')
        images_without_alt = sum(1 for img in images if not img.get('alt'))

        if images_without_alt > 0:
            findings.append(Finding(
                title="Obrazy bez atrybutu alt",
                description=f"{images_without_alt} obrazów bez alt text",
                severity=SeverityLevel.LOW,
                category="SEO",
                recommendation="Dodaj opisowy alt text do wszystkich obrazów"
            ))

        # Canonical
        canonical = soup.find('link', attrs={'rel': 'canonical'})
        canonical_url = canonical['href'] if canonical else None

        # robots.txt
        robots_txt = False
        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
            robots_response = await client.get(robots_url)
            robots_txt = robots_response.status_code == 200
        except:
            pass

        # sitemap.xml
        sitemap_xml = False
        try:
            parsed = urlparse(url)
            sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
            sitemap_response = await client.get(sitemap_url)
            sitemap_xml = sitemap_response.status_code == 200
        except:
            pass

        if not robots_txt:
            findings.append(Finding(
                title="Brak robots.txt",
                description="Plik robots.txt nie istnieje",
                severity=SeverityLevel.LOW,
                category="SEO",
                recommendation="Utwórz plik robots.txt"
            ))

        if not sitemap_xml:
            findings.append(Finding(
                title="Brak sitemap.xml",
                description="Mapa strony nie istnieje",
                severity=SeverityLevel.LOW,
                category="SEO",
                recommendation="Utwórz mapę strony sitemap.xml"
            ))

        # Mobile friendly (podstawowe sprawdzenie)
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        mobile_friendly = viewport is not None

        if not mobile_friendly:
            findings.append(Finding(
                title="Brak meta viewport",
                description="Strona może nie być responsywna",
                severity=SeverityLevel.MEDIUM,
                category="SEO",
                recommendation="Dodaj meta viewport dla urządzeń mobilnych"
            ))

        return SEOInfo(
            title=title,
            meta_description=meta_description,
            meta_keywords=meta_keywords,
            h1_tags=h1_tags,
            h2_tags=h2_tags,
            images_without_alt=images_without_alt,
            canonical_url=canonical_url,
            robots_txt=robots_txt,
            sitemap_xml=sitemap_xml,
            mobile_friendly=mobile_friendly,
            findings=findings
        )

    # ==================== Obliczanie Wyniku ====================

    def _calculate_score(
        self,
        findings: List[Finding],
        ssl_info: Optional[SSLInfo],
        security_headers: SecurityHeaders
    ) -> int:
        """Oblicz ogólny wynik bezpieczeństwa."""
        score = 100

        # Odejmij za znaleziska
        severity_penalties = {
            SeverityLevel.CRITICAL: 25,
            SeverityLevel.HIGH: 15,
            SeverityLevel.MEDIUM: 8,
            SeverityLevel.LOW: 3,
            SeverityLevel.INFO: 0
        }

        for finding in findings:
            score -= severity_penalties.get(finding.severity, 0)

        # Bonus za SSL
        if ssl_info and ssl_info.valid:
            score += 10

        return max(0, min(100, score))

    # ==================== Raportowanie ====================

    async def generate_report(
        self,
        result: AuditResult,
        format: str = "pdf"
    ) -> Path:
        """Generuj raport z audytu."""
        file_gen = get_file_generator()

        # Przygotuj sekcje raportu
        sections = []

        # Podsumowanie
        summary_content = f"""
URL: {result.url}
Data audytu: {result.timestamp.strftime('%Y-%m-%d %H:%M')}
Wynik: {result.score}/100
Czas skanowania: {result.scan_duration:.2f}s
Kod odpowiedzi: {result.page_info.status_code}
Czas odpowiedzi: {result.page_info.response_time:.2f}s
"""
        sections.append(ReportSection(
            title="Podsumowanie",
            content=summary_content,
            level=1
        ))

        # Znaleziska
        if result.findings:
            findings_content = "Wykryto następujące problemy:\n\n"
            for f in result.findings:
                findings_content += f"[{f.severity.value.upper()}] {f.title}\n"
                findings_content += f"   {f.description}\n"
                if f.recommendation:
                    findings_content += f"   Zalecenie: {f.recommendation}\n"
                findings_content += "\n"

            sections.append(ReportSection(
                title="Znaleziska",
                content=findings_content,
                level=1
            ))

        # SSL/TLS
        if result.ssl_info:
            ssl_content = f"""
Certyfikat ważny: {'Tak' if result.ssl_info.valid else 'Nie'}
Wystawca: {result.ssl_info.issuer}
Podmiot: {result.ssl_info.subject}
Ważny od: {result.ssl_info.valid_from.strftime('%Y-%m-%d')}
Ważny do: {result.ssl_info.valid_until.strftime('%Y-%m-%d')}
Dni do wygaśnięcia: {result.ssl_info.days_until_expiry}
Protokół: {result.ssl_info.protocol_version}
Szyfr: {result.ssl_info.cipher_suite}
"""
            sections.append(ReportSection(
                title="SSL/TLS",
                content=ssl_content,
                level=1
            ))

        # Nagłówki bezpieczeństwa
        headers_table = TableData(
            headers=["Nagłówek", "Status", "Wartość"],
            rows=[],
            title="Nagłówki bezpieczeństwa"
        )

        for header in self.required_headers:
            value = result.security_headers.headers.get(header, "")
            status = "OK" if value else "BRAK"
            headers_table.rows.append([header, status, value[:50] if value else "-"])

        sections.append(ReportSection(
            title="Nagłówki Bezpieczeństwa",
            content=f"Wynik: {result.security_headers.score}/100\nBrakujące: {', '.join(result.security_headers.missing)}",
            level=1,
            tables=[headers_table]
        ))

        # SEO
        seo_content = f"""
Tytuł: {result.seo_info.title or 'Brak'}
Meta description: {result.seo_info.meta_description or 'Brak'}
Nagłówki H1: {len(result.seo_info.h1_tags)}
Nagłówki H2: {len(result.seo_info.h2_tags)}
Obrazy bez alt: {result.seo_info.images_without_alt}
robots.txt: {'Tak' if result.seo_info.robots_txt else 'Nie'}
sitemap.xml: {'Tak' if result.seo_info.sitemap_xml else 'Nie'}
Mobile-friendly: {'Tak' if result.seo_info.mobile_friendly else 'Nie'}
"""
        sections.append(ReportSection(
            title="SEO",
            content=seo_content,
            level=1
        ))

        # Technologie
        if result.page_info.technologies:
            tech_content = "\n".join(f"- {t}" for t in result.page_info.technologies)
            sections.append(ReportSection(
                title="Wykryte Technologie",
                content=tech_content,
                level=1
            ))

        # Utwórz raport
        report = Report(
            title=f"Raport Audytu: {urlparse(result.url).netloc}",
            author="Ollama Agent - WebAudit",
            sections=sections,
            footer=f"Wygenerowano automatycznie przez Ollama Agent | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        # Generuj plik
        filename = f"audit_{urlparse(result.url).netloc}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}"

        if format == "pdf":
            return await file_gen.generate_pdf(report, f"{filename}.pdf")
        elif format == "docx":
            return await file_gen.generate_word(report, f"{filename}.docx")
        elif format == "json":
            return await file_gen.generate_json(
                {
                    "url": result.url,
                    "timestamp": result.timestamp.isoformat(),
                    "score": result.score,
                    "findings": [
                        {
                            "title": f.title,
                            "description": f.description,
                            "severity": f.severity.value,
                            "category": f.category,
                            "recommendation": f.recommendation
                        }
                        for f in result.findings
                    ]
                },
                f"{filename}.json"
            )
        else:
            raise ValueError(f"Nieobsługiwany format: {format}")


# ==================== Singleton ====================

_web_audit: Optional[WebAuditModule] = None


def get_web_audit() -> WebAuditModule:
    """Pobierz singleton modułu WebAudit."""
    global _web_audit
    if _web_audit is None:
        _web_audit = WebAuditModule()
    return _web_audit
