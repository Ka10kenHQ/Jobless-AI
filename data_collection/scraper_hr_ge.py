import requests
from bs4 import BeautifulSoup
import time
import json
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class JobScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )

    def normalize_keywords(self, keywords):
        """Convert keywords to string format if needed"""
        if isinstance(keywords, list):
            return " ".join(str(kw) for kw in keywords)
        return str(keywords) if keywords else ""

    def setup_selenium_driver(self):
        """Setup selenium driver for dynamic content"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        return webdriver.Chrome(options=chrome_options)

    def scrape_linkedin_jobs(
        self, keywords, location: str = "", limit: int = 20
    ) -> List[Dict]:
        """Scrape jobs from LinkedIn"""
        jobs = []
        try:
            # Normalize keywords to string
            keywords_str = self.normalize_keywords(keywords)

            # LinkedIn job search URL
            base_url = "https://www.linkedin.com/jobs/search"
            params = {
                "keywords": keywords_str,
                "location": location,
                "f_TPR": "r86400",  # Last 24 hours
            }

            response = self.session.get(base_url, params=params)
            soup = BeautifulSoup(response.content, "html.parser")

            job_cards = soup.find_all("div", class_="job-search-card")[:limit]

            for card in job_cards:
                try:
                    title_elem = card.find("h3", class_="base-search-card__title")
                    company_elem = card.find("h4", class_="base-search-card__subtitle")
                    location_elem = card.find(
                        "span", class_="job-search-card__location"
                    )
                    link_elem = card.find("a", class_="base-card__full-link")

                    if title_elem and company_elem:
                        job = {
                            "title": title_elem.get_text(strip=True),
                            "company": company_elem.get_text(strip=True),
                            "location": (
                                location_elem.get_text(strip=True)
                                if location_elem
                                else ""
                            ),
                            "url": link_elem["href"] if link_elem else "",
                            "source": "LinkedIn",
                            "description": "",
                        }
                        jobs.append(job)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error scraping LinkedIn: {e}")

        return jobs

    def scrape_indeed_jobs(
        self, keywords, location: str = "", limit: int = 20
    ) -> List[Dict]:
        jobs = []
        try:
            # Normalize keywords to string
            keywords_str = self.normalize_keywords(keywords)

            base_url = "https://www.indeed.com/jobs"
            params = {
                "q": keywords_str,
                "l": location,
                "fromage": "1",  # Last 24 hours
            }

            response = self.session.get(base_url, params=params)
            soup = BeautifulSoup(response.content, "html.parser")

            job_cards = soup.find_all("div", class_="job_seen_beacon")[:limit]

            for card in job_cards:
                try:
                    title_elem = card.find("h2", class_="jobTitle")
                    company_elem = card.find("span", class_="companyName")
                    location_elem = card.find("div", class_="companyLocation")
                    link_elem = title_elem.find("a") if title_elem else None

                    if title_elem and company_elem:
                        job = {
                            "title": title_elem.get_text(strip=True),
                            "company": company_elem.get_text(strip=True),
                            "location": (
                                location_elem.get_text(strip=True)
                                if location_elem
                                else ""
                            ),
                            "url": (
                                urljoin("https://www.indeed.com", link_elem["href"])
                                if link_elem
                                else ""
                            ),
                            "source": "Indeed",
                            "description": "",
                        }
                        jobs.append(job)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error scraping Indeed: {e}")

        return jobs

    def scrape_glassdoor_jobs(
        self, keywords, location: str = "", limit: int = 20
    ) -> List[Dict]:
        """Scrape jobs from Glassdoor using Selenium for dynamic content"""
        jobs = []
        driver = None
        try:
            keywords_str = self.normalize_keywords(keywords)

            driver = self.setup_selenium_driver()

            # Glassdoor job search URL
            search_url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={keywords_str.replace(' ', '%20')}&locT=C&locId=1147401"
            if location:
                search_url += f"&locKeyword={location.replace(' ', '%20')}"

            driver.get(search_url)
            time.sleep(3)

            # Wait for job listings to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-test="job-link"]')
                )
            )

            job_elements = driver.find_elements(
                By.CSS_SELECTOR, '[data-test="job-link"]'
            )[:limit]

            for job_elem in job_elements:
                try:
                    title = job_elem.find_element(
                        By.CSS_SELECTOR, '[data-test="job-title"]'
                    ).text
                    company = job_elem.find_element(
                        By.CSS_SELECTOR, '[data-test="employer-name"]'
                    ).text
                    location_elem = job_elem.find_element(
                        By.CSS_SELECTOR, '[data-test="job-location"]'
                    )
                    location_text = location_elem.text if location_elem else ""
                    job_url = job_elem.get_attribute("href")

                    job = {
                        "title": title,
                        "company": company,
                        "location": location_text,
                        "url": job_url,
                        "source": "Glassdoor",
                        "description": "",
                    }
                    jobs.append(job)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"Error scraping Glassdoor: {e}")
        finally:
            if driver:
                driver.quit()

        return jobs

    def scrape_hr_ge_jobs(self, keywords="", limit: int = 20) -> List[Dict]:
        """Scrape jobs from hr.ge (Georgian job site) - updated for working endpoints"""
        jobs = []
        try:
            # Normalize keywords to string
            keywords_str = self.normalize_keywords(keywords)

            # hr.ge main page and /companies page seem to work
            working_urls = [
                "https://hr.ge",
                "https://hr.ge/companies",
                "https://hr.ge/jobseeker",
            ]

            for url in working_urls:
                try:
                    response = self.session.get(url, timeout=10)
                    if response.status_code != 200:
                        continue

                    response.encoding = "utf-8"
                    soup = BeautifulSoup(response.content, "html.parser")

                    # Look for any job-related content
                    # Check for links that might lead to job listings
                    job_links = soup.find_all("a", href=True)
                    for link in job_links:
                        href = link.get("href", "").lower()
                        text = link.get_text().strip()

                        # If we find job-related links, try to follow them
                        if (
                            any(
                                word in href
                                for word in ["vacancy", "job", "position", "ვაკანსია"]
                            )
                            and len(text) > 5
                        ):
                            try:
                                job_url = urljoin("https://hr.ge", link["href"])
                                job = {
                                    "title": text,
                                    "company": "Available on hr.ge",
                                    "location": "Tbilisi, Georgia (country)",
                                    "salary": "",
                                    "url": job_url,
                                    "source": "hr.ge",
                                    "description": f"Job listing from hr.ge: {text}",
                                    "language": "georgian",
                                    "country": "Georgia",
                                }
                                jobs.append(job)
                                if len(jobs) >= limit:
                                    break
                            except Exception as e:
                                continue

                    if len(jobs) >= limit:
                        break

                except Exception as e:
                    print(f"Error with hr.ge URL {url}: {e}")
                    continue

        except Exception as e:
            print(f"Error scraping hr.ge: {e}")

        print(f"hr.ge: Found {len(jobs)} jobs")
        return jobs

    def scrape_jobs_ge_jobs(self, keywords="", limit: int = 20) -> List[Dict]:
        """Scrape jobs from jobs.ge (Georgian job site) - uses table-based layout"""
        jobs = []
        try:
            # Normalize keywords to string
            keywords_str = self.normalize_keywords(keywords)

            base_url = "https://jobs.ge"

            params = {}
            if keywords_str:
                params["q"] = keywords_str
                params["page"] = "1"

            response = self.session.get(base_url, params=params, timeout=10)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.content, "html.parser")

            print(f"jobs.ge search URL: {response.url}")

            # jobs.ge uses table structure - look for table rows with job data
            tables = soup.find_all("table")
            job_count = 0

            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    if job_count >= limit:
                        break

                    cells = row.find_all("td")
                    if len(cells) >= 2:  # Need at least 2 cells for job data
                        try:
                            # Extract text from cells
                            cell_texts = [cell.get_text(strip=True) for cell in cells]

                            # Skip header rows or empty rows
                            if not any(cell_texts) or len(" ".join(cell_texts)) < 10:
                                continue

                            # Look for job-related content (not navigation)
                            text_content = " ".join(cell_texts).lower()
                            if any(
                                skip_word in text_content
                                for skip_word in [
                                    "ყველა ვაკანსია",
                                    "all vacancies",
                                    "navigation",
                                ]
                            ):
                                continue

                            # Try to extract job information
                            # First cell often contains job title, second might have company/details
                            title = (
                                cell_texts[0]
                                if len(cell_texts) > 0
                                else "Unknown Position"
                            )
                            company_or_details = (
                                cell_texts[1] if len(cell_texts) > 1 else ""
                            )

                            # Look for links in the row
                            links = row.find_all("a", href=True)
                            job_url = ""
                            if links:
                                job_url = urljoin("https://jobs.ge", links[0]["href"])

                            # Basic validation - skip if title is too generic or empty
                            if len(title) > 5 and title not in [
                                "ყველა ვაკანსია",
                                "All Jobs",
                            ]:
                                job = {
                                    "title": title,
                                    "company": (
                                        company_or_details.split("\n")[0]
                                        if company_or_details
                                        else "Unknown Company"
                                    ),
                                    "location": "Tbilisi, Georgia (country)",  # Default to Tbilisi
                                    "salary": "",
                                    "url": job_url,
                                    "source": "jobs.ge",
                                    "description": company_or_details,
                                    "language": "georgian",  # Mark as Georgian content
                                    "country": "Georgia",
                                }
                                jobs.append(job)
                                job_count += 1

                        except Exception as e:
                            print(f"Error parsing jobs.ge table row: {e}")
                            continue

                if job_count >= limit:
                    break

        except Exception as e:
            print(f"Error scraping jobs.ge: {e}")

        print(f"jobs.ge: Found {len(jobs)} jobs")
        return jobs

    def get_detailed_job_info_georgian(self, job_url: str) -> Dict:
        details = {}
        try:
            response = self.session.get(job_url)
            response.encoding = "utf-8"
            soup = BeautifulSoup(response.content, "html.parser")

            description_selectors = [
                "div.job-description",
                "div.vacancy-description",
                "section.description",
                "div.content",
                ".job-details",
                ".vacancy-details",
            ]

            description = ""
            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    break

            salary_elem = soup.select_one(".salary, .salary-info, .compensation")
            requirements_elem = soup.select_one(
                ".requirements, .skills, .qualifications"
            )
            benefits_elem = soup.select_one(".benefits, .perks, .advantages")

            details = {
                "full_description": description,
                "salary_details": (
                    salary_elem.get_text(strip=True) if salary_elem else ""
                ),
                "requirements": (
                    requirements_elem.get_text(strip=True) if requirements_elem else ""
                ),
                "benefits": benefits_elem.get_text(strip=True) if benefits_elem else "",
                "language": "georgian",
            }

        except Exception as e:
            print(f"Error getting detailed job info: {e}")

        return details

    def scrape_all_sources(
        self, keywords, location: str = "", limit_per_source: int = 10
    ) -> List[Dict]:
        """Scrape jobs from all available sources including Georgian sites"""
        all_jobs = []

        # Normalize keywords to string for display
        keywords_str = self.normalize_keywords(keywords)
        print(f"🔍 Searching for '{keywords_str}' jobs...")

        # International sources
        print("📊 Scraping LinkedIn...")
        all_jobs.extend(self.scrape_linkedin_jobs(keywords, location, limit_per_source))

        print("📊 Scraping Indeed...")
        all_jobs.extend(self.scrape_indeed_jobs(keywords, location, limit_per_source))

        print("📊 Scraping Glassdoor...")
        all_jobs.extend(
            self.scrape_glassdoor_jobs(keywords, location, limit_per_source)
        )

        if "georgia" in keywords_str.lower() or any(
            city in keywords_str.lower() for city in ["tbilisi", "batumi", "kutaisi"]
        ):
            print("🇬🇪 Prioritizing Georgian job sites...")

        print("🇬🇪 Scraping hr.ge...")
        all_jobs.extend(self.scrape_hr_ge_jobs(keywords, limit_per_source))

        print("🇬🇪 Scraping jobs.ge...")
        all_jobs.extend(self.scrape_jobs_ge_jobs(keywords, limit_per_source))

        print(f"✅ Total jobs collected: {len(all_jobs)}")
        return all_jobs

    def get_job_details(self, job_url: str) -> str:
        try:
            response = self.session.get(job_url)
            soup = BeautifulSoup(response.content, "html.parser")

            # Try different selectors for job descriptions
            description_selectors = [
                'div[data-testid="jobDescriptionText"]',
                ".jobDescriptionContent",
                "#jobDescription",
                ".job-description",
            ]

            for selector in description_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    return desc_elem.get_text(strip=True)

            return ""
        except Exception as e:
            return ""
